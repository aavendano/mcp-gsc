"""Read-only Google Search Console MCP tools."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

from mcp.server.fastmcp import FastMCP

from gsc_mcp import auth
from gsc_mcp.config import Settings
from gsc_mcp.gsc_client import normalize_rows, site_not_found_error


def register_gsc_read_tools(mcp: FastMCP, settings: Settings) -> None:
    data_state = settings.data_state

    @mcp.tool()
    async def get_capabilities() -> str:
        """List available tools, auth status, and getting-started guidance."""
        try:
            auth.get_gsc_service()
            auth_status = "authenticated"
            auth_detail = "Service account credentials loaded."
        except Exception as e:
            auth_status = "not_authenticated"
            auth_detail = str(e)

        destructive_note = (
            "Destructive tools are enabled (GSC_ALLOW_DESTRUCTIVE=true)."
            if settings.allow_destructive
            else "Destructive tools are hidden. Set GSC_ALLOW_DESTRUCTIVE=true to enable."
        )

        return json.dumps(
            {
                "server": "gsc-mcp",
                "auth": {"status": auth_status, "detail": auth_detail, "mode": "service_account"},
                "destructive_tools": settings.allow_destructive,
                "destructive_note": destructive_note,
                "getting_started": [
                    "Set GSC_CREDENTIALS_PATH to your service account JSON key.",
                    "Call list_gsc_properties to get exact site_url values.",
                    "Use get_config to inspect non-sensitive settings.",
                ],
                "tool_groups": {
                    "config_seo": [
                        "get_config",
                        "list_gsc_properties",
                        "list_properties",
                        "get_search_analytics",
                        "compare_properties",
                        "find_query_opportunities",
                        "rank_pages_for_content_expansion",
                        "detect_low_ctr_pages",
                        "generate_seo_opportunity_report",
                    ],
                    "analytics": [
                        "get_performance_overview",
                        "get_advanced_search_analytics",
                        "compare_search_periods",
                        "get_search_by_page_query",
                    ],
                    "indexing": [
                        "inspect_url_enhanced",
                        "batch_url_inspection",
                        "check_indexing_issues",
                    ],
                    "sitemaps": [
                        "get_sitemaps",
                        "list_sitemaps_enhanced",
                        "get_sitemap_details",
                    ],
                    "properties": ["get_site_details"],
                    "destructive_if_enabled": (
                        ["add_site", "delete_site", "submit_sitemap", "delete_sitemap", "manage_sitemaps"]
                        if settings.allow_destructive
                        else []
                    ),
                },
            }
        )

    @mcp.tool()
    async def get_site_details(site_url: str) -> str:
        """Get verification and ownership details for a GSC property."""
        try:
            service = auth.get_gsc_service()
            site_info = service.sites().get(siteUrl=site_url).execute()
            result = {
                "site_url": site_url,
                "permission_level": site_info.get("permissionLevel", "Unknown"),
            }
            if "siteVerificationInfo" in site_info:
                verify_info = site_info["siteVerificationInfo"]
                result["verification"] = {
                    "state": verify_info.get("verificationState", "Unknown"),
                    "verified_user": verify_info.get("verifiedUser"),
                    "method": verify_info.get("verificationMethod"),
                }
            if "ownershipInfo" in site_info:
                owner_info = site_info["ownershipInfo"]
                result["ownership"] = {
                    "owner": owner_info.get("owner", "Unknown"),
                    "verification_method": owner_info.get("verificationMethod"),
                }
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def get_sitemaps(site_url: str) -> str:
        """List all sitemaps for a GSC property."""
        try:
            service = auth.get_gsc_service()
            sitemaps = service.sitemaps().list(siteUrl=site_url).execute()
            if not sitemaps.get("sitemap"):
                return json.dumps({"site_url": site_url, "count": 0, "sitemaps": []})

            sitemap_list = []
            for sitemap in sitemaps.get("sitemap", []):
                last_downloaded = sitemap.get("lastDownloaded")
                if last_downloaded:
                    try:
                        dt = datetime.fromisoformat(last_downloaded.replace("Z", "+00:00"))
                        last_downloaded = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass
                errors = int(sitemap.get("errors", 0))
                warnings = int(sitemap.get("warnings", 0))
                status = "Valid"
                if errors > 0:
                    status = "Has errors"
                elif warnings > 0:
                    status = "Has warnings"
                indexed_urls = None
                if "contents" in sitemap:
                    for content in sitemap["contents"]:
                        if content.get("type") == "web":
                            indexed_urls = content.get("submitted")
                            break
                sitemap_list.append(
                    {
                        "path": sitemap.get("path", "Unknown"),
                        "last_downloaded": last_downloaded,
                        "status": status,
                        "indexed_urls": indexed_urls,
                        "errors": errors,
                        "warnings": warnings,
                    }
                )
            return json.dumps({"site_url": site_url, "count": len(sitemap_list), "sitemaps": sitemap_list})
        except Exception as e:
            if "404" in str(e):
                return json.dumps({"error": site_not_found_error(site_url), "code": "not_found"})
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def inspect_url_enhanced(site_url: str, page_url: str) -> str:
        """Inspect indexing status and rich results for a URL."""
        try:
            service = auth.get_gsc_service()
            request = {"inspectionUrl": page_url, "siteUrl": site_url}
            response = service.urlInspection().index().inspect(body=request).execute()
            if not response or "inspectionResult" not in response:
                return json.dumps({"error": f"No inspection data for {page_url}", "code": "no_data"})

            inspection = response["inspectionResult"]
            index_status = inspection.get("indexStatusResult", {})
            last_crawled = None
            if "lastCrawlTime" in index_status:
                try:
                    crawl_time = datetime.fromisoformat(
                        index_status["lastCrawlTime"].replace("Z", "+00:00")
                    )
                    last_crawled = crawl_time.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    last_crawled = index_status["lastCrawlTime"]

            rich_results = None
            if "richResultsResult" in inspection:
                rich = inspection["richResultsResult"]
                rich_results = {
                    "verdict": rich.get("verdict", "UNKNOWN"),
                    "detected_types": [
                        item.get("richResultType", "Unknown")
                        for item in rich.get("detectedItems", [])
                    ],
                    "issues": [
                        {"severity": issue.get("severity"), "message": issue.get("message")}
                        for issue in rich.get("richResultsIssues", [])
                    ],
                }

            return json.dumps(
                {
                    "page_url": page_url,
                    "site_url": site_url,
                    "inspection_result_link": inspection.get("inspectionResultLink"),
                    "verdict": index_status.get("verdict", "UNKNOWN"),
                    "coverage_state": index_status.get("coverageState"),
                    "last_crawled": last_crawled,
                    "page_fetch_state": index_status.get("pageFetchState"),
                    "robots_txt_state": index_status.get("robotsTxtState"),
                    "indexing_state": index_status.get("indexingState"),
                    "google_canonical": index_status.get("googleCanonical"),
                    "user_canonical": index_status.get("userCanonical"),
                    "crawled_as": index_status.get("crawledAs"),
                    "referring_urls": index_status.get("referringUrls", [])[:5],
                    "rich_results": rich_results,
                }
            )
        except Exception as e:
            if "404" in str(e):
                return json.dumps({"error": site_not_found_error(site_url), "code": "not_found"})
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def batch_url_inspection(site_url: str, urls: str) -> str:
        """Inspect up to 10 URLs in batch."""
        try:
            service = auth.get_gsc_service()
            url_list = [url.strip() for url in urls.split("\n") if url.strip()]
            if not url_list:
                return json.dumps({"error": "No URLs provided.", "code": "invalid_input"})
            if len(url_list) > 10:
                return json.dumps(
                    {
                        "error": f"Too many URLs ({len(url_list)}). Limit is 10.",
                        "code": "invalid_input",
                    }
                )

            results = []
            for page_url in url_list:
                request = {"inspectionUrl": page_url, "siteUrl": site_url}
                try:
                    response = service.urlInspection().index().inspect(body=request).execute()
                    if not response or "inspectionResult" not in response:
                        results.append({"url": page_url, "error": "No inspection data"})
                        continue
                    inspection = response["inspectionResult"]
                    index_status = inspection.get("indexStatusResult", {})
                    last_crawl = "Never"
                    if "lastCrawlTime" in index_status:
                        try:
                            crawl_time = datetime.fromisoformat(
                                index_status["lastCrawlTime"].replace("Z", "+00:00")
                            )
                            last_crawl = crawl_time.strftime("%Y-%m-%d")
                        except Exception:
                            last_crawl = index_status["lastCrawlTime"]
                    rich_results = "None"
                    if "richResultsResult" in inspection:
                        rich = inspection["richResultsResult"]
                        if rich.get("verdict") == "PASS" and rich.get("detectedItems"):
                            rich_types = [
                                item.get("richResultType", "Unknown")
                                for item in rich["detectedItems"]
                            ]
                            rich_results = ", ".join(rich_types)
                    results.append(
                        {
                            "url": page_url,
                            "verdict": index_status.get("verdict", "UNKNOWN"),
                            "coverage_state": index_status.get("coverageState"),
                            "last_crawled": last_crawl,
                            "rich_results": rich_results,
                        }
                    )
                except Exception as e:
                    results.append({"url": page_url, "error": str(e)})

            return json.dumps({"site_url": site_url, "count": len(results), "results": results})
        except Exception as e:
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def check_indexing_issues(site_url: str, urls: str) -> str:
        """Check multiple URLs for indexing problems."""
        try:
            service = auth.get_gsc_service()
            url_list = [url.strip() for url in urls.split("\n") if url.strip()]
            if not url_list:
                return json.dumps({"error": "No URLs provided.", "code": "invalid_input"})
            if len(url_list) > 10:
                return json.dumps(
                    {
                        "error": f"Too many URLs ({len(url_list)}). Limit is 10.",
                        "code": "invalid_input",
                    }
                )

            issues_summary = {
                "not_indexed": [],
                "canonical_issues": [],
                "robots_blocked": [],
                "fetch_issues": [],
                "indexed": [],
            }

            for page_url in url_list:
                request = {"inspectionUrl": page_url, "siteUrl": site_url}
                try:
                    response = service.urlInspection().index().inspect(body=request).execute()
                    if not response or "inspectionResult" not in response:
                        issues_summary["not_indexed"].append(
                            f"{page_url} - No inspection data found"
                        )
                        continue
                    inspection = response["inspectionResult"]
                    index_status = inspection.get("indexStatusResult", {})
                    verdict = index_status.get("verdict", "UNKNOWN")
                    coverage = index_status.get("coverageState", "Unknown")
                    if verdict != "PASS" or "not indexed" in coverage.lower() or "excluded" in coverage.lower():
                        issues_summary["not_indexed"].append(f"{page_url} - {coverage}")
                    else:
                        issues_summary["indexed"].append(page_url)
                    google_canonical = index_status.get("googleCanonical", "")
                    user_canonical = index_status.get("userCanonical", "")
                    if google_canonical and user_canonical and google_canonical != user_canonical:
                        issues_summary["canonical_issues"].append(
                            f"{page_url} - Google: {google_canonical} vs user: {user_canonical}"
                        )
                    if index_status.get("robotsTxtState", "") == "BLOCKED":
                        issues_summary["robots_blocked"].append(page_url)
                    fetch_state = index_status.get("pageFetchState", "")
                    if fetch_state != "SUCCESSFUL":
                        issues_summary["fetch_issues"].append(f"{page_url} - {fetch_state}")
                except Exception as e:
                    issues_summary["not_indexed"].append(f"{page_url} - Error: {str(e)}")

            return json.dumps(
                {
                    "site_url": site_url,
                    "summary": {
                        "total_checked": len(url_list),
                        "indexed": len(issues_summary["indexed"]),
                        "not_indexed": len(issues_summary["not_indexed"]),
                        "canonical_issues": len(issues_summary["canonical_issues"]),
                        "robots_blocked": len(issues_summary["robots_blocked"]),
                        "fetch_issues": len(issues_summary["fetch_issues"]),
                    },
                    "issues": {
                        "not_indexed": issues_summary["not_indexed"],
                        "canonical_issues": issues_summary["canonical_issues"],
                        "robots_blocked": issues_summary["robots_blocked"],
                        "fetch_issues": issues_summary["fetch_issues"],
                    },
                    "indexed_urls": issues_summary["indexed"],
                }
            )
        except Exception as e:
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def get_performance_overview(site_url: str, days: int = 28) -> str:
        """Performance summary with totals and daily trend."""
        try:
            service = auth.get_gsc_service()
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            total_request = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": [],
                "rowLimit": 1,
                "dataState": data_state,
            }
            total_response = service.searchanalytics().query(
                siteUrl=site_url, body=total_request
            ).execute()
            date_request = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": ["date"],
                "rowLimit": days,
                "dataState": data_state,
            }
            date_response = service.searchanalytics().query(
                siteUrl=site_url, body=date_request
            ).execute()
            if not total_response.get("rows"):
                return json.dumps(
                    {
                        "site_url": site_url,
                        "error": f"No performance data for last {days} days.",
                        "code": "no_data",
                    }
                )
            totals_row = total_response["rows"][0]
            totals = {
                "clicks": totals_row.get("clicks", 0),
                "impressions": totals_row.get("impressions", 0),
                "ctr": round(totals_row.get("ctr", 0), 4),
                "position": round(totals_row.get("position", 0), 1),
            }
            daily_trend = []
            if date_response.get("rows"):
                sorted_rows = sorted(date_response["rows"], key=lambda x: x["keys"][0])
                for row in sorted_rows:
                    daily_trend.append(
                        {
                            "date": row["keys"][0],
                            "clicks": row.get("clicks", 0),
                            "impressions": row.get("impressions", 0),
                            "ctr": round(row.get("ctr", 0), 4),
                            "position": round(row.get("position", 0), 1),
                        }
                    )
            return json.dumps(
                {
                    "site_url": site_url,
                    "date_range": {
                        "start": start_date.strftime("%Y-%m-%d"),
                        "end": end_date.strftime("%Y-%m-%d"),
                        "days": days,
                    },
                    "totals": totals,
                    "daily_trend": daily_trend,
                }
            )
        except Exception as e:
            if "404" in str(e):
                return json.dumps({"error": site_not_found_error(site_url), "code": "not_found"})
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def get_advanced_search_analytics(
        site_url: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        dimensions: str = "query",
        search_type: str = "WEB",
        row_limit: int = 1000,
        start_row: int = 0,
        sort_by: str = "clicks",
        sort_direction: str = "descending",
        filter_dimension: Optional[str] = None,
        filter_operator: str = "contains",
        filter_expression: Optional[str] = None,
        filters: Optional[str] = None,
        data_state: Optional[str] = None,
    ) -> str:
        """Advanced search analytics with sorting, filtering, and pagination."""
        try:
            service = auth.get_gsc_service()
            if not end_date:
                end_date = datetime.now().date().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now().date() - timedelta(days=28)).strftime("%Y-%m-%d")
            resolved_data_state = (data_state or settings.data_state).lower().strip()
            if resolved_data_state not in ("all", "final"):
                return json.dumps(
                    {
                        "error": f"Invalid data_state '{data_state}'. Use 'all' or 'final'.",
                        "code": "invalid_input",
                    }
                )
            dimension_list = [d.strip() for d in dimensions.split(",") if d.strip()]
            request = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": dimension_list,
                "rowLimit": min(row_limit, 25000),
                "startRow": start_row,
                "searchType": search_type.upper(),
                "dataState": resolved_data_state,
            }
            if sort_by:
                metric_map = {
                    "clicks": "CLICK_COUNT",
                    "impressions": "IMPRESSION_COUNT",
                    "ctr": "CTR",
                    "position": "POSITION",
                }
                if sort_by in metric_map:
                    request["orderBy"] = [
                        {"metric": metric_map[sort_by], "direction": sort_direction.lower()}
                    ]
            active_filters = []
            if filters:
                try:
                    filter_list = json.loads(filters)
                except json.JSONDecodeError:
                    return json.dumps({"error": "Invalid filters JSON.", "code": "invalid_input"})
                if not isinstance(filter_list, list) or not filter_list:
                    return json.dumps(
                        {"error": "filters must be a non-empty JSON array.", "code": "invalid_input"}
                    )
                for f in filter_list:
                    if not all(k in f for k in ("dimension", "operator", "expression")):
                        return json.dumps(
                            {"error": f"Invalid filter object: {f}", "code": "invalid_input"}
                        )
                request["dimensionFilterGroups"] = [{"filters": filter_list}]
                active_filters = filter_list
            elif filter_dimension and filter_expression:
                single_filter = {
                    "dimension": filter_dimension,
                    "operator": filter_operator,
                    "expression": filter_expression,
                }
                request["dimensionFilterGroups"] = [{"filters": [single_filter]}]
                active_filters = [single_filter]

            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if not response.get("rows"):
                return json.dumps(
                    {
                        "site_url": site_url,
                        "date_range": {"start": start_date, "end": end_date},
                        "row_count": 0,
                        "rows": [],
                        "filters_applied": active_filters,
                    }
                )
            rows = normalize_rows(response.get("rows", []), dimension_list)
            has_more = len(response.get("rows", [])) == row_limit
            return json.dumps(
                {
                    "site_url": site_url,
                    "date_range": {"start": start_date, "end": end_date},
                    "search_type": search_type,
                    "dimensions": dimension_list,
                    "filters_applied": active_filters,
                    "pagination": {
                        "start_row": start_row,
                        "row_count": len(rows),
                        "has_more": has_more,
                        "next_start_row": start_row + row_limit if has_more else None,
                    },
                    "rows": rows,
                }
            )
        except Exception as e:
            if "404" in str(e):
                return json.dumps({"error": site_not_found_error(site_url), "code": "not_found"})
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def compare_search_periods(
        site_url: str,
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str,
        dimensions: str = "query",
        limit: int = 10,
    ) -> str:
        """Compare search analytics between two time periods."""
        try:
            service = auth.get_gsc_service()
            dimension_list = [d.strip() for d in dimensions.split(",") if d.strip()]
            period1_request = {
                "startDate": period1_start,
                "endDate": period1_end,
                "dimensions": dimension_list,
                "rowLimit": 1000,
                "dataState": data_state,
            }
            period2_request = {
                "startDate": period2_start,
                "endDate": period2_end,
                "dimensions": dimension_list,
                "rowLimit": 1000,
                "dataState": data_state,
            }
            period1_response = service.searchanalytics().query(
                siteUrl=site_url, body=period1_request
            ).execute()
            period2_response = service.searchanalytics().query(
                siteUrl=site_url, body=period2_request
            ).execute()
            period1_rows = period1_response.get("rows", [])
            period2_rows = period2_response.get("rows", [])
            if not period1_rows and not period2_rows:
                return json.dumps(
                    {"site_url": site_url, "error": "No data for either period.", "code": "no_data"}
                )
            period1_data = {tuple(row.get("keys", [])): row for row in period1_rows}
            period2_data = {tuple(row.get("keys", [])): row for row in period2_rows}
            all_keys = set(period1_data.keys()) | set(period2_data.keys())
            comparison_data = []
            for key in all_keys:
                p1_row = period1_data.get(
                    key, {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}
                )
                p2_row = period2_data.get(
                    key, {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}
                )
                click_diff = p2_row.get("clicks", 0) - p1_row.get("clicks", 0)
                click_pct = (
                    (click_diff / p1_row.get("clicks", 1)) * 100
                    if p1_row.get("clicks", 0) > 0
                    else float("inf")
                )
                imp_diff = p2_row.get("impressions", 0) - p1_row.get("impressions", 0)
                imp_pct = (
                    (imp_diff / p1_row.get("impressions", 1)) * 100
                    if p1_row.get("impressions", 0) > 0
                    else float("inf")
                )
                ctr_diff = p2_row.get("ctr", 0) - p1_row.get("ctr", 0)
                pos_diff = p1_row.get("position", 0) - p2_row.get("position", 0)
                comparison_data.append(
                    {
                        "key": key,
                        "p1_clicks": p1_row.get("clicks", 0),
                        "p2_clicks": p2_row.get("clicks", 0),
                        "click_diff": click_diff,
                        "click_pct": click_pct,
                        "p1_impressions": p1_row.get("impressions", 0),
                        "p2_impressions": p2_row.get("impressions", 0),
                        "imp_diff": imp_diff,
                        "imp_pct": imp_pct,
                        "p1_ctr": p1_row.get("ctr", 0),
                        "p2_ctr": p2_row.get("ctr", 0),
                        "ctr_diff": ctr_diff,
                        "p1_position": p1_row.get("position", 0),
                        "p2_position": p2_row.get("position", 0),
                        "pos_diff": pos_diff,
                    }
                )
            comparison_data.sort(key=lambda x: abs(x["click_diff"]), reverse=True)
            serialisable = []
            for item in comparison_data[:limit]:
                click_pct = item["click_pct"] if item["click_pct"] != float("inf") else None
                imp_pct = item["imp_pct"] if item["imp_pct"] != float("inf") else None
                serialisable.append(
                    {
                        "key": list(item["key"]),
                        "p1_clicks": item["p1_clicks"],
                        "p2_clicks": item["p2_clicks"],
                        "click_diff": item["click_diff"],
                        "click_pct": round(click_pct, 1) if click_pct is not None else None,
                        "p1_impressions": item["p1_impressions"],
                        "p2_impressions": item["p2_impressions"],
                        "imp_diff": item["imp_diff"],
                        "imp_pct": round(imp_pct, 1) if imp_pct is not None else None,
                        "p1_ctr": round(item["p1_ctr"], 4),
                        "p2_ctr": round(item["p2_ctr"], 4),
                        "ctr_diff": round(item["ctr_diff"], 4),
                        "p1_position": round(item["p1_position"], 1),
                        "p2_position": round(item["p2_position"], 1),
                        "position_diff": round(item["pos_diff"], 1),
                    }
                )
            return json.dumps(
                {
                    "site_url": site_url,
                    "period1": {"start": period1_start, "end": period1_end},
                    "period2": {"start": period2_start, "end": period2_end},
                    "dimensions": dimension_list,
                    "total_items": len(comparison_data),
                    "showing": len(serialisable),
                    "comparison": serialisable,
                }
            )
        except Exception as e:
            if "404" in str(e):
                return json.dumps({"error": site_not_found_error(site_url), "code": "not_found"})
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def get_search_by_page_query(
        site_url: str,
        page_url: str,
        days: int = 28,
        row_limit: int = 20,
    ) -> str:
        """Get queries driving traffic to a specific page."""
        try:
            service = auth.get_gsc_service()
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            request = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": ["query"],
                "dimensionFilterGroups": [
                    {
                        "filters": [
                            {
                                "dimension": "page",
                                "operator": "equals",
                                "expression": page_url,
                            }
                        ]
                    }
                ],
                "rowLimit": min(max(1, row_limit), 500),
                "orderBy": [{"metric": "CLICK_COUNT", "direction": "descending"}],
                "dataState": data_state,
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if not response.get("rows"):
                return json.dumps(
                    {
                        "site_url": site_url,
                        "page_url": page_url,
                        "row_count": 0,
                        "rows": [],
                    }
                )
            rows = []
            for row in response.get("rows", []):
                rows.append(
                    {
                        "query": row.get("keys", ["Unknown"])[0],
                        "clicks": row.get("clicks", 0),
                        "impressions": row.get("impressions", 0),
                        "ctr": round(row.get("ctr", 0), 4),
                        "position": round(row.get("position", 0), 1),
                    }
                )
            total_clicks = sum(r["clicks"] for r in rows)
            total_impressions = sum(r["impressions"] for r in rows)
            return json.dumps(
                {
                    "site_url": site_url,
                    "page_url": page_url,
                    "date_range": {
                        "start": start_date.strftime("%Y-%m-%d"),
                        "end": end_date.strftime("%Y-%m-%d"),
                        "days": days,
                    },
                    "totals": {
                        "clicks": total_clicks,
                        "impressions": total_impressions,
                        "avg_ctr": round(total_clicks / total_impressions, 4)
                        if total_impressions > 0
                        else 0,
                    },
                    "row_count": len(rows),
                    "rows": rows,
                }
            )
        except Exception as e:
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def list_sitemaps_enhanced(site_url: str, sitemap_index: Optional[str] = None) -> str:
        """List sitemaps with detailed status information."""
        try:
            service = auth.get_gsc_service()
            if sitemap_index:
                sitemaps = service.sitemaps().list(
                    siteUrl=site_url, sitemapIndex=sitemap_index
                ).execute()
            else:
                sitemaps = service.sitemaps().list(siteUrl=site_url).execute()
            if not sitemaps.get("sitemap"):
                return json.dumps({"site_url": site_url, "count": 0, "sitemaps": []})

            def _fmt_date(raw):
                if not raw:
                    return None
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                except Exception:
                    return raw

            sitemap_list = []
            for sitemap in sitemaps.get("sitemap", []):
                errors = int(sitemap.get("errors", 0))
                warnings = int(sitemap.get("warnings", 0))
                url_count = None
                if "contents" in sitemap:
                    for content in sitemap["contents"]:
                        if content.get("type") == "web":
                            url_count = content.get("submitted")
                            break
                sitemap_list.append(
                    {
                        "path": sitemap.get("path", "Unknown"),
                        "last_submitted": _fmt_date(sitemap.get("lastSubmitted")),
                        "last_downloaded": _fmt_date(sitemap.get("lastDownloaded")),
                        "type": "Index" if sitemap.get("isSitemapsIndex", False) else "Sitemap",
                        "is_pending": sitemap.get("isPending", False),
                        "url_count": url_count,
                        "errors": errors,
                        "warnings": warnings,
                    }
                )
            pending_count = sum(1 for s in sitemap_list if s["is_pending"])
            return json.dumps(
                {
                    "site_url": site_url,
                    "sitemap_index": sitemap_index,
                    "count": len(sitemap_list),
                    "pending_count": pending_count,
                    "sitemaps": sitemap_list,
                }
            )
        except Exception as e:
            if "404" in str(e):
                return json.dumps({"error": site_not_found_error(site_url), "code": "not_found"})
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def get_sitemap_details(site_url: str, sitemap_url: str) -> str:
        """Get detailed information about a specific sitemap."""
        try:
            service = auth.get_gsc_service()
            details = service.sitemaps().get(siteUrl=site_url, feedpath=sitemap_url).execute()
            if not details:
                return json.dumps(
                    {"error": f"No details for sitemap {sitemap_url}", "code": "no_data"}
                )

            def _fmt_date(raw):
                if not raw:
                    return None
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                except Exception:
                    return raw

            is_index = details.get("isSitemapsIndex", False)
            content_breakdown = [
                {
                    "type": content.get("type", "unknown").upper(),
                    "submitted": content.get("submitted", 0),
                    "indexed": content.get("indexed"),
                }
                for content in details.get("contents", [])
            ]
            return json.dumps(
                {
                    "sitemap_url": sitemap_url,
                    "site_url": site_url,
                    "type": "Index" if is_index else "Sitemap",
                    "status": "pending" if details.get("isPending", False) else "processed",
                    "last_submitted": _fmt_date(details.get("lastSubmitted")),
                    "last_downloaded": _fmt_date(details.get("lastDownloaded")),
                    "errors": int(details.get("errors", 0)),
                    "warnings": int(details.get("warnings", 0)),
                    "content_breakdown": content_breakdown,
                    "is_index": is_index,
                }
            )
        except Exception as e:
            return json.dumps({"error": str(e), "code": "error"})
