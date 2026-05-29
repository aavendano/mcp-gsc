"""SEO opportunity analysis built on GSC analytics data."""

from __future__ import annotations

from typing import Optional

from gsc_mcp.config import Settings
from gsc_mcp.gsc_client import fetch_analytics_rows, property_totals
from gsc_mcp.scoring import (
    classify_query_intent,
    content_expansion_score,
    ctr_opportunity_score,
    expected_ctr_for_position,
    page_opportunity_score,
)


def find_query_opportunities(
    site_url: str,
    settings: Settings,
    *,
    days: Optional[int] = None,
    min_impressions: Optional[int] = None,
    position_min: float = 11.0,
    position_max: float = 20.0,
    max_ctr: float = 0.03,
    limit: int = 20,
) -> dict[str, Any]:
    min_imp = min_impressions if min_impressions is not None else settings.min_impressions
    rows, date_range = fetch_analytics_rows(
        site_url,
        days=days,
        dimensions=["query", "page"],
        row_limit=settings.max_rows,
    )
    opportunities = []
    for row in rows:
        pos = row["position"]
        imp = row["impressions"]
        ctr = row["ctr"]
        if pos < position_min or pos > position_max:
            continue
        if imp < min_imp:
            continue
        if ctr >= max_ctr:
            continue
        query = row.get("query") or ""
        intent = classify_query_intent(query)
        ctr_score = ctr_opportunity_score(imp, ctr, pos)
        opportunities.append(
            {
                **row,
                "intent": intent,
                "expected_ctr": round(expected_ctr_for_position(pos), 4),
                "ctr_opportunity_score": ctr_score,
                "page_opportunity_score": page_opportunity_score(imp, ctr, pos),
            }
        )
    opportunities.sort(key=lambda x: x["ctr_opportunity_score"], reverse=True)
    return {
        "site_url": site_url,
        "date_range": date_range,
        "filters": {
            "position_min": position_min,
            "position_max": position_max,
            "min_impressions": min_imp,
            "max_ctr": max_ctr,
        },
        "count": len(opportunities),
        "opportunities": opportunities[:limit],
    }


def rank_pages_for_content_expansion(
    site_url: str,
    settings: Settings,
    *,
    days: Optional[int] = None,
    min_impressions: Optional[int] = None,
    position_min: float = 11.0,
    position_max: float = 30.0,
    limit: int = 20,
) -> dict[str, Any]:
    min_imp = min_impressions if min_impressions is not None else settings.min_impressions
    rows, date_range = fetch_analytics_rows(
        site_url,
        days=days,
        dimensions=["page", "query"],
        row_limit=settings.max_rows,
    )
    by_page: dict[str, dict[str, Any]] = {}
    for row in rows:
        page = row.get("page")
        if not page:
            continue
        pos = row["position"]
        imp = row["impressions"]
        if pos < position_min or pos > position_max or imp < min_imp:
            continue
        agg = by_page.setdefault(
            page,
            {
                "page": page,
                "impressions": 0,
                "clicks": 0,
                "queries": 0,
                "position_sum": 0.0,
            },
        )
        agg["impressions"] += imp
        agg["clicks"] += row["clicks"]
        agg["queries"] += 1
        agg["position_sum"] += pos * imp

    ranked = []
    for page, agg in by_page.items():
        avg_pos = agg["position_sum"] / agg["impressions"] if agg["impressions"] else 0
        score = content_expansion_score(agg["impressions"], avg_pos)
        ranked.append(
            {
                "page": page,
                "impressions": agg["impressions"],
                "clicks": agg["clicks"],
                "query_count": agg["queries"],
                "avg_position": round(avg_pos, 1),
                "content_expansion_score": score,
            }
        )
    ranked.sort(key=lambda x: x["content_expansion_score"], reverse=True)
    return {
        "site_url": site_url,
        "date_range": date_range,
        "count": len(ranked),
        "pages": ranked[:limit],
    }


def detect_low_ctr_pages(
    site_url: str,
    settings: Settings,
    *,
    days: Optional[int] = None,
    min_impressions: Optional[int] = None,
    limit: int = 20,
) -> dict[str, Any]:
    min_imp = min_impressions if min_impressions is not None else settings.min_impressions
    rows, date_range = fetch_analytics_rows(
        site_url,
        days=days,
        dimensions=["page"],
        row_limit=settings.max_rows,
    )
    low_ctr = []
    for row in rows:
        imp = row["impressions"]
        if imp < min_imp:
            continue
        pos = row["position"]
        ctr = row["ctr"]
        expected = expected_ctr_for_position(pos)
        if ctr >= expected:
            continue
        gap = expected - ctr
        low_ctr.append(
            {
                **row,
                "expected_ctr": round(expected, 4),
                "ctr_gap": round(gap, 4),
                "ctr_opportunity_score": ctr_opportunity_score(imp, ctr, pos),
            }
        )
    low_ctr.sort(key=lambda x: x["ctr_opportunity_score"], reverse=True)
    return {
        "site_url": site_url,
        "date_range": date_range,
        "count": len(low_ctr),
        "pages": low_ctr[:limit],
    }


def compare_properties(
    primary: str,
    secondary: str,
    settings: Settings,
    *,
    days: Optional[int] = None,
) -> dict[str, Any]:
    days = days if days is not None else settings.default_days
    primary_totals = property_totals(primary, days)
    secondary_totals = property_totals(secondary, days)
    _, date_range = fetch_analytics_rows(primary, days=days, dimensions=["query"], row_limit=1)

    def _delta(a: float, b: float) -> float:
        return round(b - a, 4)

    def _pct(a: float, b: float) -> Optional[float]:
        if a == 0:
            return None
        return round((b - a) / a * 100, 1)

    return {
        "date_range": date_range,
        "days": days,
        "primary": {"site_url": primary, **primary_totals},
        "secondary": {"site_url": secondary, **secondary_totals},
        "delta": {
            "clicks": _delta(primary_totals["clicks"], secondary_totals["clicks"]),
            "impressions": _delta(
                primary_totals["impressions"], secondary_totals["impressions"]
            ),
            "ctr": _delta(primary_totals["ctr"], secondary_totals["ctr"]),
            "position": _delta(primary_totals["position"], secondary_totals["position"]),
        },
        "percent_change": {
            "clicks": _pct(primary_totals["clicks"], secondary_totals["clicks"]),
            "impressions": _pct(
                primary_totals["impressions"], secondary_totals["impressions"]
            ),
        },
    }


def generate_seo_opportunity_report(
    site_url: str,
    settings: Settings,
    *,
    days: Optional[int] = None,
    include_property_compare: bool = True,
) -> dict[str, Any]:
    days = days if days is not None else settings.default_days
    query_ops = find_query_opportunities(site_url, settings, days=days, limit=10)
    expansion = rank_pages_for_content_expansion(site_url, settings, days=days, limit=10)
    low_ctr = detect_low_ctr_pages(site_url, settings, days=days, limit=10)

    report: dict[str, Any] = {
        "site_url": site_url,
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "days": days,
        "summary": {
            "query_opportunities": query_ops["count"],
            "content_expansion_pages": expansion["count"],
            "low_ctr_pages": low_ctr["count"],
        },
        "top_query_opportunities": query_ops["opportunities"],
        "top_content_expansion_pages": expansion["pages"],
        "top_low_ctr_pages": low_ctr["pages"],
    }

    if (
        include_property_compare
        and settings.secondary_gsc_property
        and settings.secondary_gsc_property != site_url
    ):
        report["property_comparison"] = compare_properties(
            site_url,
            settings.secondary_gsc_property,
            settings,
            days=days,
        )

    return report
