"""Tests for SEO analysis orchestration."""

from unittest.mock import patch

from tests.conftest import bootstrap, restore_env


SAMPLE_ROWS = [
    {
        "query": "how to seo",
        "page": "https://example.com/guide",
        "clicks": 10,
        "impressions": 500,
        "ctr": 0.02,
        "position": 14.0,
    },
    {
        "query": "buy seo tool",
        "page": "https://example.com/product",
        "clicks": 5,
        "impressions": 200,
        "ctr": 0.025,
        "position": 18.0,
    },
    {
        "query": "example brand",
        "page": "https://example.com/",
        "clicks": 100,
        "impressions": 1000,
        "ctr": 0.10,
        "position": 3.0,
    },
]


def test_find_query_opportunities_filters_page_two():
    mcp, settings, creds, old = bootstrap(
        {"PRIMARY_GSC_PROPERTY": "https://example.com/"}
    )
    try:
        from gsc_mcp.seo_analysis import find_query_opportunities

        with patch(
            "gsc_mcp.seo_analysis.fetch_analytics_rows",
            return_value=(SAMPLE_ROWS, {"start": "2026-01-01", "end": "2026-03-01"}),
        ):
            result = find_query_opportunities("https://example.com/", settings)
        assert result["count"] == 2
        assert result["opportunities"][0]["query"] == "how to seo"
        assert "intent" in result["opportunities"][0]
    finally:
        restore_env(old, creds)


def test_rank_pages_for_content_expansion():
    mcp, settings, creds, old = bootstrap()
    try:
        from gsc_mcp.seo_analysis import rank_pages_for_content_expansion

        with patch(
            "gsc_mcp.seo_analysis.fetch_analytics_rows",
            return_value=(SAMPLE_ROWS, {"start": "2026-01-01", "end": "2026-03-01"}),
        ):
            result = rank_pages_for_content_expansion("https://example.com/", settings)
        assert result["count"] >= 1
        assert "content_expansion_score" in result["pages"][0]
    finally:
        restore_env(old, creds)


def test_detect_low_ctr_pages():
    mcp, settings, creds, old = bootstrap()
    try:
        from gsc_mcp.seo_analysis import detect_low_ctr_pages

        page_rows = [
            {
                "page": "https://example.com/low",
                "clicks": 5,
                "impressions": 500,
                "ctr": 0.005,
                "position": 8.0,
            }
        ]
        with patch(
            "gsc_mcp.seo_analysis.fetch_analytics_rows",
            return_value=(page_rows, {"start": "2026-01-01", "end": "2026-03-01"}),
        ):
            result = detect_low_ctr_pages("https://example.com/", settings)
        assert result["count"] == 1
        assert result["pages"][0]["ctr_gap"] > 0
    finally:
        restore_env(old, creds)


def test_compare_properties():
    mcp, settings, creds, old = bootstrap()
    try:
        from gsc_mcp.seo_analysis import compare_properties

        with patch(
            "gsc_mcp.seo_analysis.property_totals",
            side_effect=[
                {"clicks": 100, "impressions": 1000, "ctr": 0.1, "position": 5.0},
                {"clicks": 80, "impressions": 900, "ctr": 0.09, "position": 6.0},
            ],
        ), patch(
            "gsc_mcp.seo_analysis.fetch_analytics_rows",
            return_value=([], {"start": "2026-01-01", "end": "2026-03-01"}),
        ):
            result = compare_properties(
                "https://a.com/", "https://b.com/", settings
            )
        assert result["delta"]["clicks"] == -20
    finally:
        restore_env(old, creds)


def test_generate_seo_opportunity_report_includes_compare():
    mcp, settings, creds, old = bootstrap(
        {
            "PRIMARY_GSC_PROPERTY": "https://a.com/",
            "SECONDARY_GSC_PROPERTY": "https://b.com/",
        }
    )
    try:
        from gsc_mcp.seo_analysis import generate_seo_opportunity_report

        with patch(
            "gsc_mcp.seo_analysis.find_query_opportunities",
            return_value={"count": 1, "opportunities": []},
        ), patch(
            "gsc_mcp.seo_analysis.rank_pages_for_content_expansion",
            return_value={"count": 1, "pages": []},
        ), patch(
            "gsc_mcp.seo_analysis.detect_low_ctr_pages",
            return_value={"count": 1, "pages": []},
        ), patch(
            "gsc_mcp.seo_analysis.compare_properties",
            return_value={"delta": {"clicks": 0}},
        ):
            report = generate_seo_opportunity_report("https://a.com/", settings)
        assert "property_comparison" in report
        assert report["summary"]["query_opportunities"] == 1
    finally:
        restore_env(old, creds)
