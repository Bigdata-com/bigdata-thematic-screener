import pandas as pd
import pytest

from bigdata_thematic_screener.openai_utils import ChatRequest, ChatResponse
from bigdata_thematic_screener.pipeline import (
    LabelingResult,
    _company_evidence_block,
    build_content_chunks,
    build_theme_scoring,
    label_sentences,
    run_thematic_screening,
)
from bigdata_thematic_screener.taxonomy import Node


def _leaf_root() -> Node:
    return Node(
        node=1,
        label="Root",
        summary="Root theme",
        children=[Node(node=2, label="Leaf One", summary="A leaf")],
    )


def test_build_theme_scoring_zero_fills_every_leaf_label():
    screener_df = pd.DataFrame(
        [
            {"company_name": "A", "label": "Leaf One", "summary": "A summary"},
        ]
    )
    universe_df = pd.DataFrame(
        [
            {
                "RP_ENTITY_ID": "AAAAAA",
                "COMPANY_NAME": "A",
                "TICKER": "T1",
                "INDUSTRY": "I1",
            }
        ]
    )

    scoring = build_theme_scoring(
        screener_df, universe_df, all_labels=["Leaf One", "Leaf Two"]
    )

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
    rows = pd.DataFrame(
        [{"materiality": "high", "label": "Leaf One", "motivation": ""}]
    )
    assert _company_evidence_block(rows) == ""


def test_label_sentences_parses_flat_and_wrapped_payloads(monkeypatch):
    def fake_run(
        requests: list[ChatRequest], client=None, **kwargs: object
    ) -> list[ChatResponse]:
        _ = (requests, client, kwargs)
        return [
            ChatResponse(
                request_id="0",
                succeeded=True,
                content='{"motivation": "flat", "label": "Leaf One"}',
            ),
            ChatResponse(
                request_id="1",
                succeeded=True,
                content='{"1": {"motivation": "wrapped", "label": "Leaf One"}}',
            ),
        ]

    monkeypatch.setattr(
        "bigdata_thematic_screener.pipeline.run_chat_requests_parallel", fake_run
    )

    result = label_sentences(
        [
            {"sentence_id": 0, "text": "One", "company_name": "A"},
            {"sentence_id": 1, "text": "Two", "company_name": "B"},
        ],
        "Theme",
        "Focus",
        _leaf_root(),
        model="gpt-5.6-luna",
    )

    assert result.request_count == 2
    assert result.failed_count == 0
    assert result.parsed["0"]["motivation"] == "flat"
    assert result.parsed["1"]["motivation"] == "wrapped"


def test_label_sentences_counts_api_and_parse_failures(monkeypatch):
    def fake_run(
        requests: list[ChatRequest], client=None, **kwargs: object
    ) -> list[ChatResponse]:
        _ = (requests, client, kwargs)
        return [
            ChatResponse(request_id="0", succeeded=False, error="timeout"),
            ChatResponse(request_id="1", succeeded=True, content="not-json"),
            ChatResponse(request_id="2", succeeded=True, content='{"other": true}'),
        ]

    monkeypatch.setattr(
        "bigdata_thematic_screener.pipeline.run_chat_requests_parallel", fake_run
    )

    result = label_sentences(
        [
            {"sentence_id": 0, "text": "One", "company_name": "A"},
            {"sentence_id": 1, "text": "Two", "company_name": "B"},
            {"sentence_id": 2, "text": "Three", "company_name": "C"},
        ],
        "Theme",
        "Focus",
        _leaf_root(),
        model="gpt-5.6-luna",
    )

    assert result.parsed == {}
    assert result.api_failures == 1
    assert result.parse_failures == 2
    assert result.failed_count == 3


def test_run_thematic_screening_raises_when_every_label_request_fails(monkeypatch):
    root = _leaf_root()
    universe_df = pd.DataFrame([{"RP_ENTITY_ID": "AAAAAA", "COMPANY_NAME": "A"}])
    messages: list[str] = []

    monkeypatch.setattr(
        "bigdata_thematic_screener.taxonomy.generate_taxonomy", lambda **kwargs: root
    )
    monkeypatch.setattr(
        "bigdata_thematic_screener.taxonomy.get_leaf_search_queries",
        lambda node: ["query"],
    )
    monkeypatch.setattr(
        "bigdata_thematic_screener.retrieval.search_universe",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "bigdata_thematic_screener.retrieval.extract_sentences",
        lambda documents, universe_df, rerank_threshold=None: [
            {"sentence_id": 0, "text": "Quote", "company_name": "A"}
        ],
    )
    monkeypatch.setattr(
        "bigdata_thematic_screener.pipeline.label_sentences",
        lambda *args, **kwargs: LabelingResult(
            parsed={}, request_count=1, api_failures=1, parse_failures=0
        ),
    )

    with pytest.raises(RuntimeError, match="Labeling failed for all 1 chunks"):
        run_thematic_screening(
            main_theme="Theme",
            focus="Focus",
            keywords=None,
            start_date="2025-01-01",
            end_date="2025-06-01",
            model="gpt-5.6-luna",
            rerank_threshold=None,
            chunk_percentage=0.05,
            max_leaf_labels=15,
            universe_df=universe_df,
            on_progress=messages.append,
        )


def test_run_thematic_screening_assembles_report_from_mocked_steps(monkeypatch):
    root = _leaf_root()
    universe_df = pd.DataFrame(
        [
            {
                "RP_ENTITY_ID": "AAAAAA",
                "COMPANY_NAME": "A",
                "TICKER": "T1",
                "INDUSTRY": "I1",
                "SECTOR": "S1",
                "COUNTRY": "US",
            }
        ]
    )

    monkeypatch.setattr(
        "bigdata_thematic_screener.taxonomy.generate_taxonomy", lambda **kwargs: root
    )
    monkeypatch.setattr(
        "bigdata_thematic_screener.taxonomy.get_leaf_search_queries",
        lambda node: ["query"],
    )
    monkeypatch.setattr(
        "bigdata_thematic_screener.retrieval.search_universe",
        lambda **kwargs: [{"id": "D1"}],
    )
    monkeypatch.setattr(
        "bigdata_thematic_screener.retrieval.extract_sentences",
        lambda documents, universe_df, rerank_threshold=None: [
            {
                "sentence_id": 0,
                "text": "Quote",
                "company_name": "A",
                "document_id": "D1",
                "headline": "Headline",
                "timestamp": "2025-06-01T00:00:00+00:00",
            }
        ],
    )

    monkeypatch.setattr(
        "bigdata_thematic_screener.pipeline.label_sentences",
        lambda *args, **kwargs: LabelingResult(
            parsed={"0": {"label": "Leaf One", "motivation": "Because"}},
            request_count=1,
            api_failures=0,
            parse_failures=0,
        ),
    )
    monkeypatch.setattr(
        "bigdata_thematic_screener.pipeline.summarize_companies",
        lambda merged_df, main_theme, model, client=None: pd.DataFrame(
            [{"company_name": "A", "summary": "Summary for A"}]
        ),
    )

    report = run_thematic_screening(
        main_theme="Theme",
        focus="Focus",
        keywords=None,
        start_date="2025-01-01",
        end_date="2025-06-01",
        model="gpt-5.6-luna",
        rerank_threshold=None,
        chunk_percentage=0.05,
        max_leaf_labels=15,
        universe_df=universe_df,
        on_progress=lambda _message: None,
    )

    assert report["theme_scoring"]["A"]["themes"] == {"Leaf One": 1}
    assert report["content"][0]["quote"] == "Quote"
    assert report["theme_taxonomy"]["label"] == "Root"
