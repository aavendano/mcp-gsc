"""FastMCP server instance and tool registration."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from gsc_mcp.auth import configure
from gsc_mcp.config import Settings, load_settings
from gsc_mcp.tools import register_tools

logger = logging.getLogger(__name__)

_mcp: FastMCP | None = None
_settings: Settings | None = None


def create_server(settings: Settings | None = None) -> FastMCP:
    """Create and configure the MCP server."""
    global _mcp, _settings
    settings = settings or load_settings()
    configure(settings)

    mcp = FastMCP(
        "gsc-mcp",
        stateless_http=True,
        json_response=True,
        host=settings.mcp_host,
        port=settings.mcp_port,
        streamable_http_path="/mcp",
    )
    register_tools(mcp, settings)
    _mcp = mcp
    _settings = settings
    return mcp


def get_mcp_instance() -> FastMCP:
    if _mcp is None:
        return create_server()
    return _mcp


def get_settings_instance() -> Settings:
    if _settings is None:
        return load_settings()
    return _settings
