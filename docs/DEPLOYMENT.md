# Google Search Console MCP — private deployment

## Required environment

| Variable | Default | Description |
|----------|---------|-------------|
| `GSC_CREDENTIALS_PATH` | — | **Required.** Absolute path to service account JSON key |
| `GSC_SKIP_OAUTH` | `true` | OAuth is disabled; keep `true` |
| `GSC_ALLOW_DESTRUCTIVE` | `false` | Hide destructive tools unless `true` |
| `GSC_DATA_STATE` | `all` | `all` or `final` |
| `PRIMARY_GSC_PROPERTY` | — | Default GSC property URL |
| `SECONDARY_GSC_PROPERTY` | — | Optional property for comparisons |
| `TARGET_PATH_PREFIX` | — | Filter analytics to URLs starting with this prefix |
| `DEFAULT_DAYS` | `90` | Default analytics lookback |
| `MIN_IMPRESSIONS` | `50` | Minimum impressions for opportunity tools |
| `MAX_ROWS` | `500` | Default row limit for analytics queries |
| `MCP_TRANSPORT` | `streamable-http` | `streamable-http` or `stdio` |
| `MCP_HOST` | `0.0.0.0` | Bind address for HTTP transport |
| `MCP_PORT` | `3001` | Bind port for HTTP transport |

Copy `.env.example` to `.env` and fill in values.

## Service account setup

1. Create a service account in Google Cloud Console.
2. Enable the Search Console API.
3. Download the JSON key and set `GSC_CREDENTIALS_PATH`.
4. Add the service account email to GSC → Settings → Users and permissions (Full access).

## Local stdio (Cursor / Claude Desktop)

```bash
uv sync
export GSC_CREDENTIALS_PATH=/absolute/path/to/service-account.json
export GSC_SKIP_OAUTH=true
export MCP_TRANSPORT=stdio
uv run mcp-gsc
```

Client config (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "gsc": {
      "command": "uv",
      "args": ["run", "mcp-gsc"],
      "env": {
        "GSC_CREDENTIALS_PATH": "/absolute/path/to/service-account.json",
        "GSC_SKIP_OAUTH": "true",
        "MCP_TRANSPORT": "stdio",
        "PRIMARY_GSC_PROPERTY": "https://example.com/"
      }
    }
  }
}
```

## Remote HTTP MCP (streamable-http)

The MCP endpoint is served at **`/mcp`** on the configured host and port.

```bash
uv sync
export GSC_CREDENTIALS_PATH=/absolute/path/to/service-account.json
export GSC_SKIP_OAUTH=true
export MCP_TRANSPORT=streamable-http
export MCP_HOST=0.0.0.0
export MCP_PORT=3001
uv run mcp-gsc
```

Remote client config:

```json
{
  "mcpServers": {
    "gsc-remote": {
      "url": "https://your-domain.example/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## HTTPS with Caddy

```caddy
your-domain.example {
    reverse_proxy localhost:3001
}
```

Caddy terminates TLS; the MCP server listens on HTTP internally at `http://127.0.0.1:3001/mcp`.

## HTTPS with Nginx

```nginx
server {
    listen 443 ssl;
    server_name your-domain.example;

    ssl_certificate     /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;

    location /mcp {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
    }
}
```

## Cloudflare Tunnel

```yaml
# config.yml
tunnel: YOUR_TUNNEL_ID
credentials-file: /path/to/credentials.json

ingress:
  - hostname: gsc-mcp.your-domain.example
    service: http://127.0.0.1:3001
  - service: http_status:404
```

Run: `cloudflared tunnel run YOUR_TUNNEL_NAME`

## Docker

```bash
docker build -t mcp-gsc .
docker run -d \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=3001 \
  -e GSC_SKIP_OAUTH=true \
  -e GSC_CREDENTIALS_PATH=/secrets/gsc-sa.json \
  -v /path/to/service-account.json:/secrets/gsc-sa.json:ro \
  -p 3001:3001 \
  mcp-gsc
```

## Security notes

- Single-user private deployment; no multi-tenant auth in the server.
- Restrict network access (VPN, firewall, or Cloudflare Access).
- Optional: add Basic Auth or mTLS at the reverse proxy layer.
- Never commit credentials; keep JSON keys outside the repo.

## Tests

```bash
uv sync --extra dev
uv run pytest tests/ -v
```

No live Google credentials required — tests mock all API calls.
