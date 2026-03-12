# Plan de refactorización hacia paradigma VibeBlocks (mcp-gsc)

## A) Capability Discovery

- **Framework version (mcp-gsc actual):**
  - `mcp[cli]>=1.3.0` definido en `pyproject.toml` y `requirements.txt`.
  - No se detecta `vibeblocks` instalado en el entorno Python (`importlib.util.find_spec("vibeblocks") -> False`).
- **APIs confirmadas en el código actual:**
  - Uso de `FastMCP` y `AuthSettings` para transporte/autenticación HTTP/STDIO.
  - Configuración tipada con `ServerConfig` (`dataclass`) y validación explícita.
  - Fábrica de autenticación (`create_auth_verifier`) con modos static/jwt.
- **Gaps / unknowns:**
  - No fue posible clonar `git@github.com:aavendano/vibeblocks.git` ni vía HTTPS por restricción de red (SSH unreachable / HTTPS 403), por lo que no se puede verificar implementación real de VibeBlocks en ese repo.
  - La superficie API de VibeBlocks en este plan se toma como **inferencia** desde los elementos exigidos por el requerimiento: `ExecutionContext`, `@block`, `Chain`, `Flow`, `FailureStrategy`, `SyncRunner.run()`, `execute_flow()`, `flow.get_manifest()`, `generate_function_schema(...)`.

### Capability Matrix

| Capability | Estado | Evidencia |
|---|---|---|
| MCP server con FastMCP | **Confirmed** | `gsc_server.py`, `server.py` |
| Configuración y validación centralizadas | **Confirmed** | `config.py` |
| Autenticación pluggable (static/jwt) | **Confirmed** | `auth.py` |
| Test suite (unit, integration, property) | **Confirmed** | carpeta `tests/` |
| Runtime de VibeBlocks instalado | **Confirmed: NO** | `find_spec("vibeblocks") == False` |
| Semántica exacta de VibeBlocks repo externo | **Hypothesis** | no accesible desde entorno |
| APIs de orquestación listadas arriba | **Inferred** | derivadas del requerimiento del usuario |

---

## B) State Contract

Se propone que **todo estado de ejecución viva en `ExecutionContext.data`** con contrato versionado.

```python
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional

class GSCWorkflowState(BaseModel):
    # Versionado
    context_version: str = Field(default="1.0.0")
    previous_context_version: Optional[str] = None

    # Auditoría
    run_id: str
    started_at: str  # ISO-8601
    finished_at: Optional[str] = None
    decision: Optional[str] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)

    # Entrada funcional
    request_type: Literal[
        "list_properties",
        "search_analytics",
        "inspect_url",
        "sitemaps",
        "site_admin"
    ]
    site_url: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    # Estado técnico/infra
    transport: Literal["http", "stdio"]
    auth_mode: Optional[Literal["static", "jwt"]] = None
    retries: Dict[str, int] = Field(default_factory=dict)

    # Salidas
    result: Optional[Dict[str, Any]] = None
    status: Literal["pending", "running", "succeeded", "failed", "compensated"] = "pending"
```

### Rationale de campos
- `context_version` y `previous_context_version`: habilitan migraciones compatibles al evolucionar el workflow.
- `decision`: decisión final auditable (ej: `allow`, `deny`, `partial_success`, `retry_later`).
- `errors[]`: acumulación determinística de fallos por bloque (sin estado oculto).
- `retries`: telemetría por bloque para control operacional.

### Versioning notes
- Introducir migrador `migrate_context(v_old) -> v_new` para soportar ejecuciones con contexto legado.
- Fallar temprano (ABORT) si llega un `context_version` no soportado y no hay migración declarada.

---

## C) Block Design

Bloques atómicos propuestos (mutan solo `ctx.data`):

1. `init_run_metadata`
   - Propósito: inicializar `run_id`, `started_at`, `status=running`.
   - Retry: no aplica (determinístico local).
   - Undo: no aplica.

2. `load_runtime_config`
   - Propósito: mapear `ServerConfig` actual al contexto.
   - Retry: `max_attempts=2`, `retry_on=(ValueError,)` cuando exista fuente temporal inválida.
   - Undo: no aplica.

3. `validate_request_contract`
   - Propósito: validar campos requeridos según `request_type`.
   - Retry: no (error de datos de entrada).
   - Failure domain: ABORT ante contrato inválido.

4. `acquire_gsc_client`
   - Propósito: resolver autenticación OAuth/service account y crear cliente GSC.
   - Retry: `max_attempts=3`, `delay=1`, `backoff=2`, `retry_on=(ConnectionError, TimeoutError)`.
   - Give-up: `FileNotFoundError` (credenciales ausentes) → ABORT.

5. `execute_gsc_operation`
   - Propósito: ejecutar operación concreta (list, analytics, inspect, sitemap, admin).
   - Retry: `max_attempts=3`, `retry_on=(HttpError,)` solo para códigos transientes (429/500/503).
   - Undo: para operaciones mutables (`add_site`, `submit_sitemap`) registrar compensación.

6. `normalize_output`
   - Propósito: estandarizar salida JSON para MCP tool response.
   - Retry: no.
   - Undo: no.

7. `persist_audit_event`
   - Propósito: emitir evento estructurado (`started/completed/failed/compensated`).
   - Retry: `max_attempts=2` (si sink es externo).
   - Strategy: errores aquí no deben romper resultado de negocio (CONTINUE opcional por dominio).

8. `finalize_run`
   - Propósito: set `finished_at`, `status`, `decision`.
   - Retry: no.
   - Undo: no.

---

## D) Chain/Flow Design

### Chain composition

- `Chain("preflight", [init_run_metadata, load_runtime_config, validate_request_contract])`
- `Chain("execution", [acquire_gsc_client, execute_gsc_operation, normalize_output])`
- `Chain("postflight", [persist_audit_event, finalize_run])`

### Top-level flow

- `Flow("gsc_tool_workflow", blocks=[preflight, execution, postflight], strategy=FailureStrategy.COMPENSATE)` para operaciones mutables.
- `Flow(... strategy=FailureStrategy.ABORT)` para operaciones read-only puras donde no aplica compensación.

### Failure policy por dominio

- **ABORT inmediato**
  - Contrato inválido de entrada.
  - Credenciales faltantes o inválidas no transientes.
  - Incompatibilidad de versión de contexto sin migración.
- **CONTINUE permitido**
  - Fallo de logging/auditoría secundaria (`persist_audit_event`) si resultado principal ya fue obtenido.
- **COMPENSATE requerido**
  - `add_site` exitoso pero fallo posterior crítico → `undo_add_site`.
  - `submit_sitemap` exitoso y falla de consistencia posterior → `undo_submit_sitemap` (si API lo permite; si no, compensación lógica con marca de remediación manual).

---

## E) Execution

### Runner snippet (objetivo)

```python
# Hipotético según API inferida
state = GSCWorkflowState(
    run_id="...",
    started_at="...",
    request_type="search_analytics",
    transport="http",
)
outcome = SyncRunner.run(flow=gsc_tool_workflow, data=state)
# o execute_flow(gsc_tool_workflow, state)
```

### Expected Outcome states

- `succeeded`: `result` poblado, `errors=[]`, `decision` final definido.
- `failed`: error terminal sin compensación aplicable.
- `compensated`: error terminal con rollback exitoso.
- `partial_success`: resultado primario exitoso con warnings no críticos (ej. auditoría).

---

## F) Observability + DoD Checklist

### Eventos estándar por bloque
- `block.started`
- `block.completed`
- `block.failed`
- `block.compensated`

### KPIs mínimos
- `workflow_duration_ms`
- `block_duration_ms`
- `retry_count_by_block`
- `error_count_by_type`
- `decision_distribution`

### Alertas mínimas
- **No-run**: no ejecuciones en ventana esperada.
- **High error rate**: tasa de fallo > umbral configurado.
- **Repeated compensation**: compensaciones consecutivas por misma operación/sitio.

### DoD status (para implementación futura)
1. Contrato de estado tipado y versionado → **pendiente**
2. Bloques atómicos con descripciones semánticas → **pendiente**
3. Chains + Flow con estrategia explícita → **pendiente**
4. Manifest/schema (`get_manifest`, `generate_function_schema`) → **pendiente**
5. Plan de pruebas happy/failure/compensation → **pendiente**
6. Notas operativas de ejecución/observabilidad → **definidas en este plan**

---

## G) Evidence Map

- **EVIDENCE: confirmed**
  - El repo actual usa `FastMCP`, `ServerConfig`, y fábrica de auth static/jwt.
  - Existe una batería de tests unit/integration/property.
  - `vibeblocks` no está instalado en el runtime.
  - El repositorio externo de VibeBlocks no fue accesible desde este entorno.

- **EVIDENCE: inferred**
  - El set de primitives de VibeBlocks (`ExecutionContext`, `@block`, `Chain`, `Flow`, etc.) se asume por requerimientos explícitos del usuario.
  - La transición natural de este proyecto a VibeBlocks pasa por encapsular `get_gsc_service` y operaciones MCP en bloques atómicos.

- **EVIDENCE: hypothesis**
  - Disponibilidad exacta de `undo_*` para todas las mutaciones (depende de límites de API GSC).
  - Firma exacta de `SyncRunner.run()` y `execute_flow()` en la versión de VibeBlocks objetivo.

---

## Example Illustration (hypothetical)

> **Hipotético, no implementado ni verificado en este entorno.**

- Ejemplo: “shadow mode para validación de analytics”
  - Chain A: cargar baseline histórico
  - Chain B: consultar API GSC actual
  - Chain C: calcular drift entre baseline y snapshot actual
  - Flow strategy: `CONTINUE` en fase shadow
  - `decision`: `diff_passed: bool`
  - Uso: habilitar adopción progresiva antes de bloquear ejecuciones productivas.
