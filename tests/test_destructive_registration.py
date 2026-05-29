"""Tests for destructive tool registration."""

from tests.conftest import bootstrap, restore_env, tool_names

DESTRUCTIVE = {"add_site", "delete_site", "submit_sitemap", "delete_sitemap", "manage_sitemaps"}


def test_destructive_tools_hidden_by_default():
    mcp, settings, creds, old = bootstrap({"GSC_ALLOW_DESTRUCTIVE": "false"})
    try:
        names = tool_names(mcp)
        assert DESTRUCTIVE.isdisjoint(names)
    finally:
        restore_env(old, creds)


def test_destructive_tools_registered_when_enabled():
    mcp, settings, creds, old = bootstrap({"GSC_ALLOW_DESTRUCTIVE": "true"})
    try:
        names = tool_names(mcp)
        assert DESTRUCTIVE.issubset(names)
    finally:
        restore_env(old, creds)
