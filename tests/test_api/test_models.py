import pytest
from pydantic import ValidationError

from bigdata_thematic_screener.api.models import (
    EXAMPLE_COMPANY_LISTS,
    ThematicScreenRequestBase,
)


def test_example_company_lists_are_rp_entity_ids():
    assert "MAG_7" in EXAMPLE_COMPANY_LISTS
    assert len(EXAMPLE_COMPANY_LISTS["MAG_7"]) == 7
    for entity_id in EXAMPLE_COMPANY_LISTS["MAG_7"]:
        assert isinstance(entity_id, str) and entity_id


def test_thematic_screen_request_base_valid():
    req = ThematicScreenRequestBase(
        theme="Supply Chain Reshaping",
        start_date="2025-06-01",
        end_date="2025-08-01",
        chunk_percentage=0.05,
    )
    assert req.theme == "Supply Chain Reshaping"
    assert req.chunk_percentage == 0.05
    assert req.llm_model == "gpt-5.6-luna"
    assert req.focus is None


@pytest.mark.parametrize("chunk_percentage", [-0.1, 1.5])
def test_thematic_screen_request_base_chunk_percentage_out_of_range(chunk_percentage):
    with pytest.raises(ValidationError):
        ThematicScreenRequestBase(
            theme="Theme",
            start_date="2025-06-01",
            end_date="2025-08-01",
            chunk_percentage=chunk_percentage,
        )


def test_thematic_screen_request_base_max_taxonomy_depth_rejects_below_two():
    with pytest.raises(ValidationError):
        ThematicScreenRequestBase(
            theme="Theme",
            start_date="2025-06-01",
            end_date="2025-08-01",
            max_taxonomy_depth=1,
        )
