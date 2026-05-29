"""SEO opportunity MCP tools."""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from gsc_mcp.config import Settings, settings_to_public_dict
from gsc_mcp.gsc_client import (
    error_json,
    fetch_analytics_rows,
    list_properties as fetch_properties,
    site_not_found_error,
)
from gsc_mcp.seo_analysis import compare_properties as compare_properties_analysis
from gsc_mcp.seo_analysis import detect_low_ctr_pages as analyze_low_ctr_pages
from gsc_mcp.seo_analysis import find_query_opportunities as analyze_query_opportunities
from gsc_mcp.seo_analysis import generate_seo_opportunity_report as build_seo_report
from gsc_mcp.seo_analysis import rank_pages_for_content_expansion as analyze_content_expansion


def register_seo_tools(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool()
    async def get_config() -> str:
        """Return non-sensitive server configuration and credential status."""
        return json.dumps(settings_to_public_dict(settings))

    @mcp.tool()
    async def list_gsc_properties() -> str:
        """List all GSC properties accessible to the service account."""
        try:
            sites = fetch_properties()
            if not sites:
                return json.dumps({"count": 0, "properties": []})
            return json.dumps(
                {
                    "count": len(sites),
                    "properties": [
                        {
                            "site_url": s.get("siteUrl", "Unknown"),
                            "permission_level": s.get("permissionLevel", "Unknown"),
                        }
                        for s in sites
                    ],
                }
            )
        except FileNotFoundError as e:
            return error_json(str(e), "credentials_missing")
        except Exception as e:
            return error_json(str(e))

    @mcp.tool()
    async def get_search_analytics(
        site_url: Optional[str] = None,
        days: Optional[int] = None,
        dimensions: str = "query",
        row_limit: Optional[int] = None,
    ) -> str:
        """Search analytics with config defaults (PRIMARY_GSC_PROPERTY, DEFAULT_DAYS, MAX_ROWS)."""
        resolved_site = site_url or settings.primary_gsc_property
        if not resolved_site:
            return error_json(
                "site_url is required when PRIMARY_GSC_PROPERTY is not set.",
                "missing_property",
            )
        try:
            dimension_list = [d.strip() for d in dimensions.split(",") if d.strip()]
            rows, date_range = fetch_analytics_rows(
                resolved_site,
                days=days,
                dimensions=dimension_list,
                row_limit=row_limit,
            )
            if not rows:
                return json.dumps(
                    {
                        "site_url": resolved_site,
                        "date_range": date_range,
                        "dimensions": dimension_list,
                        "row_count": 0,
                        "rows": [],
                    }
                )
            return json.dumps(
                {
                    "site_url": resolved_site,
                    "date_range": {**date_range, "days": days or settings.default_days},
                    "dimensions": dimension_list,
                    "row_count": len(rows),
                    "rows": rows,
                }
            )
        except Exception as e:
            if "404" in str(e):
                return error_json(site_not_found_error(resolved_site), "not_found")
            return error_json(str(e))

    @mcp.tool()
    async def compare_properties(
        primary_site_url: Optional[str] = None,
        secondary_site_url: Optional[str] = None,
        days: Optional[int] = None,
    ) -> str:
        """Compare aggregate metrics between two GSC properties."""
        primary = primary_site_url or settings.primary_gsc_property
        secondary = secondary_site_url or settings.secondary_gsc_property
        if not primary or not secondary:
            return error_json(
                "Both primary and secondary site URLs are required "
                "(via params or PRIMARY_GSC_PROPERTY / SECONDARY_GSC_PROPERTY).",
                "missing_property",
            )
        try:
            return json.dumps(
                compare_properties_analysis(primary, secondary, settings, days=days)
            )
        except Exception as e:
            if "404" in str(e):
                return error_json(str(e), "not_found")
            return error_json(str(e))

    @mcp.tool()
    async def find_query_opportunities(
        site_url: Optional[str] = None,
        days: Optional[int] = None,
        min_impressions: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """Find query/page pairs on page 2 with high impressions and low CTR."""
        resolved = site_url or settings.primary_gsc_property
        if not resolved:
            return error_json("site_url or PRIMARY_GSC_PROPERTY required.", "missing_property")
        try:
            return json.dumps(
                analyze_query_opportunities(
                    resolved,
                    settings,
                    days=days,
                    min_impressions=min_impressions,
                    limit=limit,
                )
            )
        except Exception as e:
            if "404" in str(e):
                return error_json(site_not_found_error(resolved), "not_found")
            return error_json(str(e))

    @mcp.tool()
    async def rank_pages_for_content_expansion(
        site_url: Optional[str] = None,
        days: Optional[int] = None,
        min_impressions: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """Rank pages best suited for content expansion (positions 11-30, high impressions)."""
        resolved = site_url or settings.primary_gsc_property
        if not resolved:
            return error_json("site_url or PRIMARY_GSC_PROPERTY required.", "missing_property")
        try:
            return json.dumps(
                analyze_content_expansion(
                    resolved,
                    settings,
                    days=days,
                    min_impressions=min_impressions,
                    limit=limit,
                )
            )
        except Exception as e:
            if "404" in str(e):
                return error_json(site_not_found_error(resolved), "not_found")
            return error_json(str(e))

    @mcp.tool()
    async def detect_low_ctr_pages(
        site_url: Optional[str] = None,
        days: Optional[int] = None,
        min_impressions: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """Detect pages with CTR below the expected benchmark for their position."""
        resolved = site_url or settings.primary_gsc_property
        if not resolved:
            return error_json("site_url or PRIMARY_GSC_PROPERTY required.", "missing_property")
        try:
            return json.dumps(
                analyze_low_ctr_pages(
                    resolved,
                    settings,
                    days=days,
                    min_impressions=min_impressions,
                    limit=limit,
                )
            )
        except Exception as e:
            if "404" in str(e):
                return error_json(site_not_found_error(resolved), "not_found")
            return error_json(str(e))

    @mcp.tool()
    async def generate_seo_opportunity_report(
        site_url: Optional[str] = None,
        days: Optional[int] = None,
        include_property_compare: bool = True,
    ) -> str:
        """Generate an aggregated SEO opportunity report."""
        resolved = site_url or settings.primary_gsc_property
        if not resolved:
            return error_json("site_url or PRIMARY_GSC_PROPERTY required.", "missing_property")
        try:
            return json.dumps(
                build_seo_report(
                    resolved,
                    settings,
                    days=days,
                    include_property_compare=include_property_compare,
                )
            )
        except Exception as e:
            if "404" in str(e):
                return error_json(site_not_found_error(resolved), "not_found")
            return error_json(str(e))

    # Alias for existing skills/docs
    @mcp.tool()
    async def list_properties() -> str:
        """Alias for list_gsc_properties (backward compatible)."""
        return await list_gsc_properties()
