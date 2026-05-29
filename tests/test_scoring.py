"""Tests for deterministic SEO scoring helpers."""

from gsc_mcp.scoring import (
    classify_query_intent,
    content_expansion_score,
    ctr_opportunity_score,
    expected_ctr_for_position,
    page_opportunity_score,
)


def test_expected_ctr_decreases_with_position():
    assert expected_ctr_for_position(1) > expected_ctr_for_position(10)
    assert expected_ctr_for_position(10) > expected_ctr_for_position(20)


def test_ctr_opportunity_score_zero_when_at_benchmark():
    expected = expected_ctr_for_position(10)
    assert ctr_opportunity_score(1000, expected, 10) == 0.0


def test_ctr_opportunity_score_positive_when_below_benchmark():
    score = ctr_opportunity_score(1000, 0.01, 10)
    assert score > 0


def test_content_expansion_score_peaks_on_page_two():
    mid = content_expansion_score(500, 15)
    edge = content_expansion_score(500, 11)
    top = content_expansion_score(500, 5)
    assert mid > top
    assert mid >= edge


def test_classify_query_intent():
    assert classify_query_intent("how to bake bread") == "informational"
    assert classify_query_intent("buy running shoes online") == "transactional"
    assert classify_query_intent("best crm software") == "commercial"


def test_page_opportunity_score_bounded():
    score = page_opportunity_score(5000, 0.01, 12)
    assert 0 <= score <= 100
