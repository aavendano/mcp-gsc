"""Deterministic SEO scoring helpers (pure functions, no I/O)."""

from __future__ import annotations

import re
from typing import Literal

QueryIntent = Literal["informational", "commercial", "navigational", "transactional"]

# Fixed CTR benchmarks by position band (deterministic curve).
_POSITION_CTR = {
    1: 0.28,
    2: 0.15,
    3: 0.11,
    4: 0.08,
    5: 0.06,
    6: 0.05,
    7: 0.04,
    8: 0.035,
    9: 0.032,
    10: 0.03,
    11: 0.025,
    12: 0.022,
    13: 0.02,
    14: 0.018,
    15: 0.016,
    16: 0.014,
    17: 0.012,
    18: 0.011,
    19: 0.0105,
    20: 0.01,
}

_INFORMATIONAL = re.compile(
    r"\b(how|what|why|when|where|guide|tutorial|tips|meaning|definition|vs|versus)\b",
    re.I,
)
_COMMERCIAL = re.compile(
    r"\b(best|top|review|compare|comparison|alternative|vs|pricing|cost)\b",
    re.I,
)
_TRANSACTIONAL = re.compile(
    r"\b(buy|price|cheap|discount|coupon|order|shop|purchase|deal|free shipping)\b",
    re.I,
)
_NAVIGATIONAL = re.compile(
    r"\b(login|sign in|official|website|contact|support)\b",
    re.I,
)


def expected_ctr_for_position(position: float) -> float:
    """Return expected CTR for a given average position."""
    pos = max(1, min(100, int(round(position))))
    if pos in _POSITION_CTR:
        return _POSITION_CTR[pos]
    if pos > 20:
        return max(0.001, 0.01 - (pos - 20) * 0.0002)
    # Interpolate between known points for positions 1-20
    lower = max(k for k in _POSITION_CTR if k <= pos)
    upper = min(k for k in _POSITION_CTR if k >= pos)
    if lower == upper:
        return _POSITION_CTR[lower]
    ratio = (pos - lower) / (upper - lower)
    return _POSITION_CTR[lower] + ratio * (_POSITION_CTR[upper] - _POSITION_CTR[lower])


def ctr_opportunity_score(impressions: int, ctr: float, position: float) -> float:
    """Estimated click gain if CTR reaches the position benchmark."""
    expected = expected_ctr_for_position(position)
    gap = max(0.0, expected - ctr)
    return round(impressions * gap, 2)


def content_expansion_score(impressions: int, position: float) -> float:
    """Higher score for page-2 rankings with meaningful impression volume."""
    if position < 11 or position > 20:
        position_factor = 0.5 if position > 20 else 0.2
    else:
        # Peak weight at position 15 (middle of page 2)
        position_factor = 1.0 - abs(position - 15) / 10.0
        position_factor = max(0.3, position_factor)
    position_gap = max(0.0, position - 10.0)
    return round(impressions * position_factor * (position_gap / 10.0 + 0.5), 2)


def classify_query_intent(query: str) -> QueryIntent:
    """Heuristic query intent classification without ML."""
    q = query.strip()
    if not q:
        return "informational"
    if _TRANSACTIONAL.search(q):
        return "transactional"
    if _COMMERCIAL.search(q):
        return "commercial"
    if _NAVIGATIONAL.search(q):
        return "navigational"
    if _INFORMATIONAL.search(q):
        return "informational"
    # Short branded-looking queries tend to be navigational
    if len(q.split()) <= 2 and not _INFORMATIONAL.search(q):
        return "navigational"
    return "informational"


def page_opportunity_score(
    impressions: int,
    ctr: float,
    position: float,
    *,
    max_impressions: int = 10000,
) -> float:
    """Combined opportunity score normalized to 0-100."""
    ctr_component = ctr_opportunity_score(impressions, ctr, position)
    expansion_component = content_expansion_score(impressions, position)
    raw = ctr_component + expansion_component
    cap = max(max_impressions * 0.05, 1.0)
    normalized = min(100.0, (raw / cap) * 100.0)
    return round(normalized, 2)
