import pandas as pd

from bigdata_thematic_screener.pipeline import (
    _company_evidence_block,
    build_content_chunks,
    build_theme_scoring,
)


def test_build_theme_scoring_zero_fills_every_leaf_label():
    screener_df = pd.DataFrame(
        [
            {"company_name": "A", "label": "Leaf One", "summary": "A summary"},
        ]
    )
    universe_df = pd.DataFrame(
        [{"RP_ENTITY_ID": "AAAAAA", "COMPANY_NAME": "A", "TICKER": "T1", "INDUSTRY": "I1"}]
    )

    scoring = build_theme_scoring(screener_df, universe_df, all_labels=["Leaf One", "Leaf Two"])

    assert scoring["A"]["themes"] == {"Leaf One": 1, "Leaf Two": 0}
    assert scoring["A"]["composite_score"] == 1
    # No `sector` key — CompanyScoring doesn't have one (unlike LabeledChunk).
    assert "sector" not in scoring["A"]


def test_build_content_chunks_defaults_missing_country_to_empty_string():
    screener_df = pd.DataFrame(
        [
            {
                "company_name": "A",
                "label": "Leaf One",
                "text": "Quote",
                "motivation": "Motivation",
                "document_id": "D1",
                "headline": "Headline",
                "timestamp": "2025-06-01T00:00:00+00:00",
            }
        ]
    )
    # No COUNTRY column at all in the universe.
    universe_df = pd.DataFrame([{"RP_ENTITY_ID": "AAAAAA", "COMPANY_NAME": "A"}])

    chunks = build_content_chunks(screener_df, universe_df)

    assert chunks[0]["country"] == ""
    assert chunks[0]["theme"] == "Leaf One"


def test_company_evidence_block_includes_materiality_revenue_cost():
    rows = pd.DataFrame(
        [
            {
                "materiality": "high",
                "label": "Leaf One",
                "revenue_generation": "medium",
                "cost_efficiency": "low",
                "motivation": "Target Company benefits from X.",
            }
        ]
    )

    block = _company_evidence_block(rows)

    assert "materiality=high" in block
    assert "revenue_generation=medium" in block
    assert "cost_efficiency=low" in block
    assert "Target Company benefits from X." in block


def test_company_evidence_block_skips_rows_without_motivation():
    rows = pd.DataFrame([{"materiality": "high", "label": "Leaf One", "motivation": ""}])
    assert _company_evidence_block(rows) == ""
