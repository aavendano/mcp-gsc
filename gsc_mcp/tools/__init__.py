"""MCP tool registration."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from gsc_mcp.config import Settings
from gsc_mcp.tools.destructive import register_destructive_tools
from gsc_mcp.tools.gsc_read import register_gsc_read_tools
from gsc_mcp.tools.seo_opportunities import register_seo_tools


def register_tools(mcp: FastMCP, settings: Settings) -> None:
    register_seo_tools(mcp, settings)
    register_gsc_read_tools(mcp, settings)
    if settings.allow_destructive:
        register_destructive_tools(mcp, settings)
