"""Shared test helpers."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

from gsc_mcp.auth import configure, reset_auth_cache
from gsc_mcp.config import load_settings
from gsc_mcp.server import create_server


def bootstrap(env_overrides: dict | None = None, *, allow_destructive: bool = False):
    """Load settings and MCP server with a fake credentials file."""
    creds_fd, creds_path = tempfile.mkstemp(suffix=".json")
    os.write(creds_fd, b'{"type":"service_account","project_id":"test"}')
    os.close(creds_fd)

    env = {
        "GSC_SKIP_OAUTH": "true",
        "GSC_CREDENTIALS_PATH": creds_path,
        "GSC_DATA_STATE": "all",
        "GSC_ALLOW_DESTRUCTIVE": "true" if allow_destructive else "false",
        "MCP_TRANSPORT": "streamable-http",
        "MCP_HOST": "0.0.0.0",
        "MCP_PORT": "3001",
        "DEFAULT_DAYS": "90",
        "MIN_IMPRESSIONS": "50",
        "MAX_ROWS": "500",
        **(env_overrides or {}),
    }
    old_env = os.environ.copy()
    os.environ.clear()
    os.environ.update(env)
    reset_auth_cache()

    settings = load_settings()
    configure(settings)
    mcp = create_server(settings)
    return mcp, settings, creds_path, old_env


def restore_env(old_env: dict, creds_path: str) -> None:
    os.environ.clear()
    os.environ.update(old_env)
    if os.path.exists(creds_path):
        os.remove(creds_path)
    reset_auth_cache()


def make_service():
    service = MagicMock()
    service.sites.return_value.list.return_value.execute.return_value = {"siteEntry": []}
    service.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
    return service


def patch_gsc_service(service):
    """Patch GSC service getter."""
    import gsc_mcp.auth as auth_module

    return patch.object(auth_module, "get_gsc_service", return_value=service)


def tool_names(mcp) -> set[str]:
    return set(mcp._tool_manager._tools.keys())
