import pandas as pd

from bigdata_thematic_screener.retrieval import extract_sentences


def _universe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"RP_ENTITY_ID": "AAAAAA", "COMPANY_NAME": "Alpha"},
            {"RP_ENTITY_ID": "BBBBBB", "COMPANY_NAME": "Beta"},
        ]
    )


def test_extract_sentences_attributes_chunk_to_every_matching_universe_company():
    documents = [
        {
            "id": "D1",
            "headline": "Headline",
            "timestamp": "2025-06-01T00:00:00+00:00",
            "chunks": [
                {
                    "text": "Alpha and Beta both mentioned.",
                    "relevance": 0.9,
                    "entity_ids": ["AAAAAA", "BBBBBB"],
                }
            ],
        }
    ]

    sentences = extract_sentences(documents, _universe())

    assert [s["company_name"] for s in sentences] == ["Alpha", "Beta"]
    assert [s["sentence_id"] for s in sentences] == [0, 1]
    assert all(s["text"] == "Alpha and Beta both mentioned." for s in sentences)


def test_extract_sentences_skips_non_universe_ids_and_keeps_later_matches():
    documents = [
        {
            "id": "D1",
            "headline": "Headline",
            "timestamp": "2025-06-01T00:00:00+00:00",
            "chunks": [
                {
                    "text": "Quote",
                    "relevance": 0.9,
                    "entity_ids": ["XXXXXX", "BBBBBB"],
                }
            ],
        }
    ]

    sentences = extract_sentences(documents, _universe())

    assert [s["company_name"] for s in sentences] == ["Beta"]


def test_extract_sentences_drops_chunks_below_rerank_threshold():
    documents = [
        {
            "id": "D1",
            "headline": "Headline",
            "timestamp": "2025-06-01T00:00:00+00:00",
            "chunks": [
                {
                    "text": "Low",
                    "relevance": 0.2,
                    "entity_ids": ["AAAAAA"],
                },
                {
                    "text": "High",
                    "relevance": 0.8,
                    "entity_ids": ["AAAAAA"],
                },
            ],
        }
    ]

    sentences = extract_sentences(documents, _universe(), rerank_threshold=0.5)

    assert [s["text"] for s in sentences] == ["High"]


def test_extract_sentences_skips_chunks_with_no_entity_ids():
    documents = [
        {
            "id": "D1",
            "headline": "Headline",
            "timestamp": "2025-06-01T00:00:00+00:00",
            "chunks": [{"text": "No entities", "relevance": 0.9, "entity_ids": []}],
        }
    ]

    assert extract_sentences(documents, _universe()) == []
