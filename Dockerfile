FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app

COPY pyproject.toml README.md ./
COPY gsc_mcp ./gsc_mcp
RUN uv sync --no-cache --no-install-project

ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=3001
ENV GSC_SKIP_OAUTH=true

EXPOSE 3001
CMD ["uv", "run", "--no-sync", "mcp-gsc"]
