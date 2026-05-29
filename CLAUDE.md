# CLAUDE.md

Context for AI coding assistants working in this repo.

## What this is

Private single-user MCP server for Google Search Console. Package layout under `gsc_mcp/`. Built with FastMCP from the official MCP Python SDK.

## Running locally

```bash
uv sync
export GSC_CREDENTIALS_PATH=/absolute/path/to/service-account.json
export GSC_SKIP_OAUTH=true
export MCP_TRANSPORT=stdio
uv run mcp-gsc
```

## Remote HTTP/HTTPS deployment

```bash
export MCP_TRANSPORT=streamable-http
export MCP_HOST=0.0.0.0
export MCP_PORT=3001
uv run mcp-gsc
```

MCP endpoint: `http://HOST:PORT/mcp` — put TLS termination on Caddy/Nginx/Cloudflare Tunnel. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Auth

Service account only. Set `GSC_CREDENTIALS_PATH` to the JSON key file. Add the SA email to GSC property users.

## Key environment variables

| Variable | Default | Description |
|---|---|---|
| `GSC_CREDENTIALS_PATH` | — | Service account JSON (required) |
| `GSC_SKIP_OAUTH` | `true` | OAuth disabled |
| `GSC_ALLOW_DESTRUCTIVE` | `false` | Hide destructive tools unless `true` |
| `GSC_DATA_STATE` | `all` | `all` or `final` |
| `PRIMARY_GSC_PROPERTY` | — | Default property for SEO tools |
| `SECONDARY_GSC_PROPERTY` | — | Optional comparison property |
| `TARGET_PATH_PREFIX` | — | URL prefix filter |
| `DEFAULT_DAYS` | `90` | Analytics lookback |
| `MIN_IMPRESSIONS` | `50` | Opportunity threshold |
| `MAX_ROWS` | `500` | Default row limit |
| `MCP_TRANSPORT` | `streamable-http` | `stdio` or `streamable-http` |
| `MCP_HOST` | `0.0.0.0` | HTTP bind host |
| `MCP_PORT` | `3001` | HTTP bind port |

## Package layout

- `gsc_mcp/config.py` — env settings
- `gsc_mcp/auth.py` — service account auth
- `gsc_mcp/gsc_client.py` — GSC API helpers
- `gsc_mcp/scoring.py` — deterministic SEO scoring
- `gsc_mcp/seo_analysis.py` — opportunity analysis
- `gsc_mcp/tools/` — MCP tool registration
- `gsc_mcp/server.py` — FastMCP instance
- `gsc_mcp/main.py` — transport entrypoint

## Adding a new tool

1. Add a `register_*_tools(mcp, settings)` function under `gsc_mcp/tools/`
2. Call it from `gsc_mcp/tools/__init__.py`
3. Use `get_gsc_service()` for API access
4. Return `json.dumps(dict)` — structured JSON only
5. Add tests with mocked API calls in `tests/`

## Running tests

```bash
uv sync --extra dev
uv run pytest tests/ -v
```

No credentials needed — all Google API calls are mocked.

## Docker

```bash
docker build -t mcp-gsc .
docker run -e GSC_CREDENTIALS_PATH=/secrets/sa.json \
  -v /path/to/sa.json:/secrets/sa.json:ro \
  -p 3001:3001 mcp-gsc
```
