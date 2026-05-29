"""Tests for GSC MCP tools (mocked API)."""

import asyncio
import json

from tests.conftest import bootstrap, make_service, patch_gsc_service, restore_env, tool_names


def _tool_fn(mcp, name):
    return mcp._tool_manager._tools[name].fn


def test_list_gsc_properties_returns_json():
    mcp, settings, creds, old = bootstrap()
    try:
        service = make_service()
        service.sites.return_value.list.return_value.execute.return_value = {
            "siteEntry": [
                {"siteUrl": "https://example.com/", "permissionLevel": "siteOwner"},
            ]
        }
        fn = _tool_fn(mcp, "list_gsc_properties")
        with patch_gsc_service(service):
            result = asyncio.run(fn())
        data = json.loads(result)
        assert data["count"] == 1
        assert data["properties"][0]["site_url"] == "https://example.com/"
    finally:
        restore_env(old, creds)


def test_get_config_returns_settings():
    mcp, settings, creds, old = bootstrap({"PRIMARY_GSC_PROPERTY": "https://example.com/"})
    try:
        fn = _tool_fn(mcp, "get_config")
        result = asyncio.run(fn())
        data = json.loads(result)
        assert data["primary_gsc_property"] == "https://example.com/"
        assert data["default_days"] == 90
    finally:
        restore_env(old, creds)


def test_get_search_analytics_with_defaults():
    mcp, settings, creds, old = bootstrap({"PRIMARY_GSC_PROPERTY": "https://example.com/"})
    try:
        service = make_service()
        service.searchanalytics.return_value.query.return_value.execute.return_value = {
            "rows": [
                {
                    "keys": ["test query"],
                    "clicks": 10,
                    "impressions": 100,
                    "ctr": 0.1,
                    "position": 5.0,
                }
            ]
        }
        fn = _tool_fn(mcp, "get_search_analytics")
        with patch_gsc_service(service):
            result = asyncio.run(fn())
        data = json.loads(result)
        assert data["row_count"] == 1
        assert data["rows"][0]["query"] == "test query"
    finally:
        restore_env(old, creds)


def test_get_performance_overview():
    mcp, settings, creds, old = bootstrap()
    try:
        service = make_service()
        service.searchanalytics.return_value.query.return_value.execute.side_effect = [
            {"rows": [{"clicks": 50, "impressions": 500, "ctr": 0.1, "position": 8.0}]},
            {
                "rows": [
                    {
                        "keys": ["2026-01-01"],
                        "clicks": 10,
                        "impressions": 100,
                        "ctr": 0.1,
                        "position": 8.0,
                    },
                ]
            },
        ]
        fn = _tool_fn(mcp, "get_performance_overview")
        with patch_gsc_service(service):
            result = asyncio.run(fn("https://example.com/", 28))
        data = json.loads(result)
        assert data["totals"]["clicks"] == 50
        assert len(data["daily_trend"]) == 1
    finally:
        restore_env(old, creds)


def test_get_capabilities_json():
    mcp, settings, creds, old = bootstrap()
    try:
        fn = _tool_fn(mcp, "get_capabilities")
        with patch_gsc_service(make_service()):
            result = asyncio.run(fn())
        data = json.loads(result)
        assert data["auth"]["mode"] == "service_account"
        assert "get_config" in data["tool_groups"]["config_seo"]
    finally:
        restore_env(old, creds)


def test_compare_search_periods():
    mcp, settings, creds, old = bootstrap()
    try:
        service = make_service()
        service.searchanalytics.return_value.query.return_value.execute.side_effect = [
            {"rows": [{"keys": ["q1"], "clicks": 10, "impressions": 100, "ctr": 0.1, "position": 5.0}]},
            {"rows": [{"keys": ["q1"], "clicks": 20, "impressions": 120, "ctr": 0.15, "position": 4.0}]},
        ]
        fn = _tool_fn(mcp, "compare_search_periods")
        with patch_gsc_service(service):
            result = asyncio.run(
                fn(
                    "https://example.com/",
                    "2026-01-01",
                    "2026-01-31",
                    "2026-02-01",
                    "2026-02-28",
                )
            )
        data = json.loads(result)
        assert data["comparison"][0]["click_diff"] == 10
    finally:
        restore_env(old, creds)


def test_seo_tools_registered():
    mcp, settings, creds, old = bootstrap()
    try:
        names = tool_names(mcp)
        for tool in [
            "get_config",
            "list_gsc_properties",
            "compare_properties",
            "find_query_opportunities",
            "generate_seo_opportunity_report",
        ]:
            assert tool in names
    finally:
        restore_env(old, creds)
