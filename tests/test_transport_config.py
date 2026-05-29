"""Tests for auth and transport configuration."""

import os

import pytest

from gsc_mcp.auth import get_gsc_service, reset_auth_cache
from gsc_mcp.config import load_settings
from gsc_mcp.server import create_server
from tests.conftest import bootstrap, restore_env, tool_names


def test_credentials_path_required():
    mcp, settings, creds, old = bootstrap({"GSC_CREDENTIALS_PATH": ""})
    try:
        with pytest.raises(FileNotFoundError, match="GSC_CREDENTIALS_PATH"):
            get_gsc_service()
    finally:
        restore_env(old, creds)


def test_missing_credentials_file_fails_fast():
    mcp, settings, creds, old = bootstrap(
        {"GSC_CREDENTIALS_PATH": "/tmp/definitely-missing-gsc-creds.json"}
    )
    try:
        with pytest.raises(FileNotFoundError, match="does not exist"):
            get_gsc_service()
    finally:
        restore_env(old, creds)


def test_default_transport_is_streamable_http():
    mcp, settings, creds, old = bootstrap()
    try:
        assert settings.mcp_transport == "streamable-http"
        assert settings.mcp_port == 3001
        assert mcp.settings.streamable_http_path == "/mcp"
    finally:
        restore_env(old, creds)


def test_skip_oauth_defaults_true():
    mcp, settings, creds, old = bootstrap()
    try:
        assert settings.skip_oauth is True
    finally:
        restore_env(old, creds)
