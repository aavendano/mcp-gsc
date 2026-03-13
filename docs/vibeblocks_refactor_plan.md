# Plan de refactorización hacia paradigma VibeBlocks (mcp-gsc)

## A) Capability Discovery

- **Dependencias objetivo del plan**
  - `vibeblocks==0.1.3` instalable vía `pip install vibeblocks==0.1.3`.
  - `mcp[cli]>=1.3.0` ya presente en el proyecto actual.
  - El proyecto actual requiere Python `>=3.11`; VibeBlocks 0.1.3 es compatible con ese runtime.

- **APIs confirmadas de VibeBlocks 0.1.3**
  - `ExecutionContext[T]`
  - `@block(...)`
  - `Block`, `Chain`, `Flow`
  - `FailureStrategy.ABORT | CONTINUE | COMPENSATE`
  - `SyncRunner().run(executable, ctx)`
  - `AsyncRunner().run(executable, ctx)`
  - `execute_flow(flow, data, async_mode=False)`
  - `flow.get_manifest()`
  - `generate_function_schema(flow_manifest, context_model)`
  - `VibeBlocks.run_from_json(...)`

- **Semántica confirmada de VibeBlocks 0.1.3**
  - `Outcome.status` solo admite: `"SUCCESS"`, `"FAILED"`, `"ABORTED"`.
  - Los retries se configuran con `RetryPolicy` y `BackoffStrategy.FIXED | LINEAR | EXPONENTIAL`.
  - `retry_on` y `give_up_on` son reglas por tipo de excepción, no por predicado dinámico.
  - `undo` y `timeout` existen a nivel de bloque.
  - `ExecutionContext` incluye `data`, `trace`, `metadata`, `completed_blocks` y `exception_sanitizer`.

- **Capacidades confirmadas en el código actual**
  - MCP server basado en `FastMCP`.
  - Transporte `stdio` y `http`.
  - Configuración tipada con `ServerConfig`.
  - Fábrica de autenticación `create_auth_verifier` para modos `static` y `jwt`.
  - `gsc_server.py` concentra herramientas, auth GSC, formateo de respuestas y manejo de errores.
  - Existe batería de tests unitarios, de integración y property-based.

- **Observación estructural importante**
  - `gsc_server.py` es actualmente el principal candidato a extracción: mezcla adquisición de credenciales, creación de cliente GSC, validación de entradas, llamadas a Google, retries implícitos y formateo de salida en un solo módulo.

- **Gaps / unknowns**
  - La semántica exacta de rollback de algunas mutaciones GSC debe validarse contra la API real antes de prometer compensación automática en todos los casos.
  - Debe decidirse si las tools MCP seguirán devolviendo `str` o migrarán gradualmente a salidas JSON estructuradas.

### Capability Matrix

| Capability | Estado | Evidencia |
|---|---|---|
| MCP server con FastMCP | **Confirmed** | `gsc_server.py`, `server.py` |
| Configuración y validación centralizadas | **Confirmed** | `config.py` |
| Autenticación pluggable (static/jwt) | **Confirmed** | `auth.py` |
| Test suite (unit, integration, property) | **Confirmed** | `tests/` |
| VibeBlocks como dependencia objetivo | **Confirmed for plan scope** | premisa explícita: `pip install vibeblocks==0.1.3` |
| API real de VibeBlocks 0.1.3 | **Confirmed** | revisión de la librería |
| Rollback exacto para todas las mutaciones GSC | **Hypothesis** | depende de límites de la API GSC |
| Retorno final MCP como string vs JSON estructurado | **Open decision** | requiere decisión de compatibilidad |

---

## B) State Contract

### Regla de modelado

- `ctx.data` debe contener solo estado funcional y auditable, idealmente JSON-serializable.
- `ctx.metadata` debe reservarse para handles no serializables o efímeros de runtime, por ejemplo:
  - cliente GSC construido,
  - snapshot de `ServerConfig`,
  - objetos temporales de autenticación,
  - métricas internas de ejecución no expuestas al contrato.

Esto corrige un riesgo del plan anterior: el cliente de Google Search Console no debe vivir en `ctx.data`.

### Contrato recomendado

No conviene un único `GSCWorkflowState` genérico con `payload: Dict[str, Any]` para todo. Es mejor:

1. un estado base compartido;
2. estados tipados por familia de operación.

```python
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


class BaseGSCWorkflowState(BaseModel):
    # Versionado
    context_version: str = "1.0.0"
    previous_context_version: Optional[str] = None

    # Auditoría
    run_id: str
    started_at: str
    finished_at: Optional[str] = None
    decision: Optional[str] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)

    # Contexto técnico serializable
    transport: Literal["http", "stdio"]
    auth_mode: Optional[Literal["static", "jwt"]] = None

    # Resultado de negocio
    result: Optional[Dict[str, Any]] = None
    business_status: Literal[
        "pending",
        "running",
        "succeeded",
        "failed",
        "compensated",
        "partial_success",
    ] = "pending"


class SearchAnalyticsState(BaseGSCWorkflowState):
    request_type: Literal["search_analytics"] = "search_analytics"
    site_url: str
    days: int = 28
    dimensions: List[str] = Field(default_factory=lambda: ["query"])


class SiteMutationState(BaseGSCWorkflowState):
    request_type: Literal["add_site", "delete_site"]
    site_url: str


class SitemapMutationState(BaseGSCWorkflowState):
    request_type: Literal["submit_sitemap", "delete_sitemap"]
    site_url: str
    sitemap_url: str
```

### Rationale de diseño

- `context_version` y `previous_context_version`: soportan evolución compatible del contrato.
- `decision`: expresa semántica de negocio sin abusar de `Outcome.status`.
- `business_status`: permite distinguir `compensated` o `partial_success` aunque `Outcome.status` siga siendo `"FAILED"` o `"SUCCESS"` según la librería.
- `errors[]`: acumula errores/warnings normalizados por bloque.
- Los parámetros específicos de cada tool viven en modelos tipados, no en un `payload` abierto por defecto.

### Versioning notes

- Introducir `migrate_context(v_old) -> v_new` para estados persistidos o reinyectados.
- Si llega un `context_version` no soportado y no existe migración definida, el flujo debe fallar con `FailureStrategy.ABORT`.

---

## C) Block Design

### Principios

- Bloques pequeños, semánticos y con una sola responsabilidad.
- Los bloques mutan `ctx.data`; los objetos de runtime no serializables van a `ctx.metadata`.
- Los retries deben basarse en tipos de excepción compatibles con `RetryPolicy`.
- Para distinguir errores transientes de permanentes en `HttpError`, hay que normalizarlos a excepciones propias.

### Excepciones de dominio recomendadas

```python
class TransientGSCError(Exception):
    pass


class PermanentGSCError(Exception):
    pass


class UnsupportedContextVersionError(Exception):
    pass
```

### Bloques atómicos propuestos

1. `init_run_metadata`
   - Propósito: inicializar `started_at`, `business_status="running"` y campos de auditoría faltantes.
   - Retry: no.
   - Undo: no.

2. `validate_context_version`
   - Propósito: verificar `context_version` y aplicar migración si existe.
   - Retry: no.
   - Give-up: `UnsupportedContextVersionError`.

3. `load_runtime_config`
   - Propósito: copiar a `ctx.data` el snapshot serializable mínimo (`transport`, `auth_mode`) y guardar el `ServerConfig` completo en `ctx.metadata["server_config"]`.
   - Retry: no, salvo que la configuración venga de una fuente externa dinámica.
   - Undo: no.

4. `validate_request_contract`
   - Propósito: validar parámetros requeridos por cada estado concreto.
   - Retry: no.
   - Failure domain: ABORT.

5. `build_gsc_client`
   - Propósito: resolver credenciales y crear el cliente GSC.
   - Salida técnica: guardar cliente en `ctx.metadata["gsc_service"]`.
   - Retry: `max_attempts=2`, `delay=1.0`, `backoff=BackoffStrategy.FIXED`.
   - `give_up_on=[FileNotFoundError, ValueError, PermanentGSCError]`
   - Nota: no conviene retry agresivo si el camino puede disparar flujo OAuth interactivo.

6. `execute_gsc_operation`
   - Propósito: ejecutar la operación GSC específica.
   - Retry: solo sobre errores transientes normalizados.
   - Configuración recomendada:
     - `max_attempts=3`
     - `delay=1.0`
     - `backoff=BackoffStrategy.EXPONENTIAL`
     - `retry_on=[TransientGSCError]`
     - `give_up_on=[PermanentGSCError, ValueError, FileNotFoundError]`
   - Regla:
     - `HttpError` 429/500/503 -> `TransientGSCError`
     - `HttpError` 400/401/403/404 -> `PermanentGSCError`

7. `normalize_output`
   - Propósito: transformar respuesta GSC a la forma canónica que usarán las tools MCP.
   - Retry: no.
   - Undo: no.

8. `persist_audit_event`
   - Propósito: registrar evento estructurado adicional si existe sink externo.
   - Retry en flujo principal: no.
   - Importante:
     - Si su fallo no debe romper negocio, este bloque no debe propagar la excepción como fallo del flujo principal.
     - Debe capturar el error, anexarlo como warning en `ctx.data.errors` y completar con éxito.
     - Si se requiere entrega confiable con retry real, mover ese envío fuera del flujo principal a un mecanismo operacional separado.

9. `finalize_run`
   - Propósito: completar `finished_at`, `decision` y `business_status`.
   - Retry: no.
   - Undo: no.

### Política de compensación por bloque

- `add_site`
  - `undo`: `delete_site`
- `submit_sitemap`
  - `undo`: `delete_sitemap`
- Operaciones read-only (`list_properties`, `search_analytics`, `inspect_url`, etc.)
  - sin `undo`

### Nota importante sobre compensación

En VibeBlocks, una compensación ejecutada con éxito bajo `FailureStrategy.COMPENSATE` no cambia `Outcome.status` a un estado especial. El resultado del flujo seguirá siendo `"FAILED"`, por lo que la señal de “compensado” debe vivir en `ctx.data.business_status` y/o `ctx.data.decision`.

---

## D) Chain/Flow Design

### Principio de composición

No conviene un único `Flow("gsc_tool_workflow")` para todas las tools. Es mejor componer flujos por familia:

- flujos read-only,
- flujos mutables de sitios,
- flujos mutables de sitemaps.

### Chains propuestas

- `Chain("preflight", [init_run_metadata, validate_context_version, load_runtime_config, validate_request_contract])`
- `Chain("execution", [build_gsc_client, execute_gsc_operation, normalize_output])`
- `Chain("postflight", [persist_audit_event, finalize_run])`

### Flujos top-level propuestos

#### 1. Read-only flow

```python
Flow(
    "gsc_read_workflow",
    blocks=[preflight, execution, postflight],
    strategy=FailureStrategy.ABORT,
)
```

Uso sugerido:
- `list_properties`
- `get_search_analytics`
- `inspect_url_enhanced`
- `get_sitemaps`
- consultas avanzadas y comparativas

#### 2. Site mutation flow

```python
Flow(
    "gsc_site_mutation_workflow",
    blocks=[preflight, execution, postflight],
    strategy=FailureStrategy.COMPENSATE,
)
```

Uso sugerido:
- `add_site`
- `delete_site`

#### 3. Sitemap mutation flow

```python
Flow(
    "gsc_sitemap_mutation_workflow",
    blocks=[preflight, execution, postflight],
    strategy=FailureStrategy.COMPENSATE,
)
```

Uso sugerido:
- `submit_sitemap`
- `delete_sitemap`

### Failure policy por dominio

- **ABORT inmediato**
  - contrato inválido de entrada,
  - versión de contexto no soportada,
  - credenciales faltantes,
  - auth inválida o configuración imposible,
  - `PermanentGSCError`.

- **Retry**
  - solo ante `TransientGSCError`,
  - sin retry sobre errores semánticos de usuario o configuración.

- **Compensación**
  - `add_site` exitoso y luego fallo crítico -> `undo_add_site` usando `delete_site`.
  - `submit_sitemap` exitoso y luego fallo crítico -> `undo_submit_sitemap` usando `delete_sitemap`, si la API y el contexto de negocio lo permiten.

- **No crítico / warning**
  - fallos de auditoría secundaria o telemetría no deben modelarse como fallo del flujo principal si el resultado de negocio ya fue obtenido.

---

## E) Execution

### Instalación objetivo

```bash
pip install vibeblocks==0.1.3
```

Además, la dependencia deberá declararse en:
- `pyproject.toml`
- `requirements.txt`

### Runner snippets correctos

#### Opción 1: helper recomendado

```python
from vibeblocks.utils.execution import execute_flow

state = SearchAnalyticsState(
    run_id="run-123",
    started_at="2026-03-13T00:00:00Z",
    site_url="https://example.com",
    transport="http",
)

outcome = execute_flow(gsc_read_workflow, state)
```

#### Opción 2: runner explícito

```python
from vibeblocks import ExecutionContext, SyncRunner

ctx = ExecutionContext(data=state)
outcome = SyncRunner().run(gsc_read_workflow, ctx)
```

#### Opción 3: si existen bloques async

```python
from vibeblocks.utils.execution import execute_flow

outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
```

### Semántica correcta de `Outcome`

- `Outcome.status == "SUCCESS"`
  - el flujo terminó sin fallos no manejados.
  - `ctx.data.business_status` normalmente será `"succeeded"`.

- `Outcome.status == "FAILED"`
  - hubo fallo terminal.
  - también cubre el caso de flujos con `FailureStrategy.COMPENSATE` que compensaron correctamente.
  - para distinguir compensación efectiva:
    - `ctx.data.business_status == "compensated"`
    - o `ctx.data.decision == "compensated"`

- `Outcome.status == "ABORTED"`
  - el flujo abortó por estrategia `ABORT`.

- `partial_success`
  - no es un `Outcome.status` de VibeBlocks.
  - si se necesita, debe representarse en:
    - `ctx.data.decision = "partial_success"`
    - o `ctx.data.business_status = "succeeded"` con warnings en `ctx.data.errors`.

### Integración sugerida con las tools MCP

- Las funciones decoradas con `@mcp.tool()` deben quedar como capa delgada.
- Cada tool:
  1. construye el estado tipado;
  2. ejecuta el flow adecuado;
  3. transforma `outcome` + `ctx.data.result` a la respuesta MCP.

---

## F) Observability + DoD Checklist

### Eventos estándar

VibeBlocks ya aporta trazas mínimas en `ctx.trace`:
- inicio de bloque,
- fin de bloque,
- fallo de bloque,
- inicio de flow,
- fin de flow,
- compensación.

Además, el dominio GSC debería emitir:
- `gsc.request.started`
- `gsc.request.completed`
- `gsc.request.failed`
- `gsc.request.compensated`

### KPIs mínimos

- `workflow_duration_ms`
- `block_duration_ms`
- `retry_count_by_block`
- `error_count_by_type`
- `decision_distribution`
- `compensation_count`

### Alertas mínimas

- no-run en ventana esperada,
- high error rate,
- repeated compensation,
- repeated auth failures,
- repeated quota/transient failures (`429`, `503`).

### Estrategia de implementación recomendada

1. Añadir `vibeblocks==0.1.3` como dependencia.
2. Extraer primero un flujo read-only pequeño:
   - `list_properties`
   - o `get_search_analytics`
3. Introducir normalización de errores GSC:
   - `TransientGSCError`
   - `PermanentGSCError`
4. Mover luego una mutación con rollback claro:
   - `submit_sitemap` / `delete_sitemap`
   - o `add_site` / `delete_site`
5. Mantener `server.py`, `config.py` y `auth.py` casi sin cambios.
6. Dejar `gsc_server.py` como capa de registro MCP y adaptación de entrada/salida.

### DoD status

1. Dependencia `vibeblocks==0.1.3` declarada → **pendiente**
2. Contratos de estado tipados por familia de operación → **pendiente**
3. Bloques atómicos con descripciones semánticas → **pendiente**
4. Flujos read-only y mutation separados → **pendiente**
5. Adaptador de errores transientes/permanentes → **pendiente**
6. MCP tools convertidas en wrappers delgados → **pendiente**
7. `flow.get_manifest()` y `generate_function_schema(...)` donde aplique → **pendiente**
8. Pruebas happy/failure/compensation → **pendiente**
9. Notas operativas de observabilidad → **definidas en este plan**

---

## G) Evidence Map

- **EVIDENCE: confirmed**
  - El repo actual usa `FastMCP`, `ServerConfig` y autenticación static/jwt.
  - `gsc_server.py` concentra actualmente la mayor parte de la lógica operativa.
  - VibeBlocks 0.1.3 expone `ExecutionContext`, `@block`, `Chain`, `Flow`, `SyncRunner`, `AsyncRunner`, `execute_flow`, `FailureStrategy`, `flow.get_manifest()` y `generate_function_schema(...)`.
  - `Outcome.status` no soporta `partial_success` ni `compensated` como valores nativos.
  - `RetryPolicy` trabaja por tipo de excepción y `BackoffStrategy` enum.

- **EVIDENCE: inferred**
  - El mayor valor de migrar a VibeBlocks en este proyecto será estructural: separación de responsabilidades, retries consistentes, mejor trazabilidad y testabilidad.
  - La extracción inicial más rentable es empezar por una tool read-only antes de mover flujos mutables.

- **EVIDENCE: hypothesis**
  - La API GSC permitirá compensación suficiente para todos los casos mutables que hoy expone el servidor.
  - Algunas tools podrían beneficiarse de respuesta JSON estructurada sin romper compatibilidad con clientes MCP existentes.

---

## Example Illustration (hypothetical)

> Hipotético, útil como patrón de implementación, no como claim de estado actual.

- Ejemplo: `get_search_analytics`
  - `SearchAnalyticsState` como input tipado
  - `preflight`:
    - `init_run_metadata`
    - `validate_context_version`
    - `load_runtime_config`
    - `validate_request_contract`
  - `execution`:
    - `build_gsc_client`
    - `execute_gsc_operation`
    - `normalize_output`
  - `postflight`:
    - `persist_audit_event`
    - `finalize_run`
  - Flow strategy: `ABORT`
  - Ejecución:
    - `outcome = execute_flow(gsc_read_workflow, state)`
  - Resultado esperado:
    - `Outcome.status == "SUCCESS"`
    - `ctx.data.business_status == "succeeded"`
    - `ctx.data.result` contiene los datos listos para responder por MCP
