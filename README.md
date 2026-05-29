# Google Search Console MCP — Private Server

Private single-user MCP server for Google Search Console. Service account auth, structured JSON responses, and remote deployment over HTTP/HTTPS at `/mcp`.

## Features

- **Remote MCP** via streamable HTTP at `/mcp` (default transport)
- **Local stdio** for Cursor / Claude Desktop
- **Service account only** — no OAuth, no multi-user
- **Read-only GSC tools** — analytics, indexing, sitemaps
- **SEO opportunity tools** — query opportunities, content expansion, low-CTR detection, reports
- **Deterministic scoring** — reproducible CTR and opportunity scores
- **Destructive tools hidden** by default (`GSC_ALLOW_DESTRUCTIVE=false`)

## Quick start

```bash
uv sync
cp .env.example .env
# Edit .env — set GSC_CREDENTIALS_PATH and PRIMARY_GSC_PROPERTY
uv run mcp-gsc
```

Endpoint: `http://localhost:3001/mcp`

## Environment variables

See [`.env.example`](.env.example) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Tools

### SEO / config
- `get_config`, `list_gsc_properties`, `list_properties` (alias)
- `get_search_analytics`, `compare_properties`
- `find_query_opportunities`, `rank_pages_for_content_expansion`
- `detect_low_ctr_pages`, `generate_seo_opportunity_report`

### GSC read-only
- `get_capabilities`, `get_site_details`, `get_performance_overview`
- `get_advanced_search_analytics`, `compare_search_periods`, `get_search_by_page_query`
- `inspect_url_enhanced`, `batch_url_inspection`, `check_indexing_issues`
- `get_sitemaps`, `list_sitemaps_enhanced`, `get_sitemap_details`

### Destructive (only when `GSC_ALLOW_DESTRUCTIVE=true`)
- `add_site`, `delete_site`, `submit_sitemap`, `delete_sitemap`, `manage_sitemaps`

## Deployment

Full HTTPS setup with Caddy, Nginx, Cloudflare Tunnel, and Docker: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Tests

```bash
uv sync --extra dev
uv run pytest tests/ -v
```

## License

MIT
