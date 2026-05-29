"""Google Search Console API client helpers."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Optional

from gsc_mcp import auth


def site_not_found_error(site_url: str) -> str:
    lines = [f"Property '{site_url}' not found (404). Possible causes:\n"]
    lines.append(
        "1. The site_url doesn't exactly match what is in GSC. "
        "Run list_gsc_properties to get the exact string to use."
    )
    if site_url.startswith("sc-domain:"):
        lines.append(
            "2. Domain properties require the service account to be added "
            "under GSC Settings > Users and permissions."
        )
    else:
        lines.append(
            "2. If your property is a domain property, use 'sc-domain:example.com'."
        )
    lines.append("3. The service account may not have access to this property.")
    return "\n".join(lines)


def error_json(message: str, code: str = "error") -> str:
    return json.dumps({"error": message, "code": code})


def date_range(days: int, end: Optional[date] = None) -> tuple[str, str]:
    end_date = end or datetime.now().date()
    start_date = end_date - timedelta(days=days)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def normalize_rows(rows: list[dict], dimensions: list[str]) -> list[dict]:
    result = []
    for row in rows:
        entry: dict[str, Any] = {}
        keys = row.get("keys", [])
        for i, dim in enumerate(dimensions):
            entry[dim] = keys[i] if i < len(keys) else None
        entry["clicks"] = row.get("clicks", 0)
        entry["impressions"] = row.get("impressions", 0)
        entry["ctr"] = round(row.get("ctr", 0), 4)
        entry["position"] = round(row.get("position", 0), 1)
        result.append(entry)
    return result


def matches_path_prefix(page_url: Optional[str], prefix: Optional[str]) -> bool:
    if not prefix:
        return True
    if not page_url:
        return False
    return page_url.startswith(prefix)


def query_search_analytics(
    site_url: str,
    *,
    start_date: str,
    end_date: str,
    dimensions: list[str],
    row_limit: int = 500,
    start_row: int = 0,
    search_type: str = "WEB",
    data_state: Optional[str] = None,
    filters: Optional[list[dict]] = None,
    order_by: Optional[list[dict]] = None,
) -> dict[str, Any]:
    settings = auth.get_settings()
    service = auth.get_gsc_service()
    request: dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": min(row_limit, 25000),
        "startRow": start_row,
        "searchType": search_type.upper(),
        "dataState": data_state or settings.data_state,
    }
    if filters:
        request["dimensionFilterGroups"] = [{"filters": filters}]
    if order_by:
        request["orderBy"] = order_by
    return service.searchanalytics().query(siteUrl=site_url, body=request).execute()


def fetch_analytics_rows(
    site_url: str,
    *,
    days: Optional[int] = None,
    dimensions: list[str],
    row_limit: Optional[int] = None,
    filters: Optional[list[dict]] = None,
    path_prefix: Optional[str] = None,
) -> tuple[list[dict], dict[str, str]]:
    settings = auth.get_settings()
    days = days if days is not None else settings.default_days
    row_limit = row_limit if row_limit is not None else settings.max_rows
    start, end = date_range(days)
    response = query_search_analytics(
        site_url,
        start_date=start,
        end_date=end,
        dimensions=dimensions,
        row_limit=row_limit,
        filters=filters,
    )
    rows = normalize_rows(response.get("rows", []), dimensions)
    prefix = path_prefix if path_prefix is not None else settings.target_path_prefix
    if prefix and "page" in dimensions:
        rows = [r for r in rows if matches_path_prefix(r.get("page"), prefix)]
    return rows, {"start": start, "end": end}


def property_totals(site_url: str, days: int) -> dict[str, Any]:
    start, end = date_range(days)
    response = query_search_analytics(
        site_url,
        start_date=start,
        end_date=end,
        dimensions=[],
        row_limit=1,
    )
    rows = response.get("rows", [])
    if not rows:
        return {
            "clicks": 0,
            "impressions": 0,
            "ctr": 0.0,
            "position": 0.0,
        }
    row = rows[0]
    return {
        "clicks": row.get("clicks", 0),
        "impressions": row.get("impressions", 0),
        "ctr": round(row.get("ctr", 0), 4),
        "position": round(row.get("position", 0), 1),
    }


def list_properties() -> list[dict]:
    service = auth.get_gsc_service()
    site_list = service.sites().list().execute()
    return site_list.get("siteEntry", [])
