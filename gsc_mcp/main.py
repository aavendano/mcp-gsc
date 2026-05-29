"""Entry point for local stdio and remote streamable-http MCP transport."""

from __future__ import annotations

import logging
import sys

from gsc_mcp.config import load_settings
from gsc_mcp.server import create_server

logger = logging.getLogger(__name__)

DEPRECATED_TRANSPORTS = {"sse", "http"}


def main() -> None:
    settings = load_settings()
    mcp = create_server(settings)
    transport = settings.mcp_transport

    if transport in DEPRECATED_TRANSPORTS:
        logger.warning(
            "MCP_TRANSPORT=%s is deprecated; using streamable-http instead.", transport
        )
        transport = "streamable-http"

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        raise ValueError(
            f"Unknown MCP_TRANSPORT '{transport}'. "
            "Use 'stdio' or 'streamable-http'."
        )


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    main()
