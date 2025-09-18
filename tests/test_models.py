import pytest
from pydantic import ValidationError

from bigdata_thematic_screener.api.models import (
    DocumentType,
    FrequencyEnum,
    ThematicScreenRequest,
)


@pytest.mark.parametrize(
    "theme,companies,start_date,end_date,llm_model,fiscal_year,document_type,rerank_threshold,frequency,document_limit,batch_size,expected_error",
    [
        # Missing companies
        (
            "US Import Tariffs against China",
            None,
            "2025-06-01",
            "2025-08-01",
            "openai::gpt-4o-mini",
            None,
            DocumentType.NEWS,
            None,
            FrequencyEnum.monthly,
            100,
            10,
            "Input should be a valid",
        ),
        # start_date after end_date
        (
            "US Import Tariffs against China",
            ["4A6F00"],
            "2025-08-01",
            "2025-06-01",
            "openai::gpt-4o-mini",
            2025,
            DocumentType.TRANSCRIPTS,
            None,
            FrequencyEnum.monthly,
            100,
            10,
            "The number of days in the range between start_date",
        ),
        # Frequency interval too large for date range
        (
            "US Import Tariffs against China",
            ["4A6F00"],
            "2025-08-01",
            "2025-08-10",
            "openai::gpt-4o-mini",
            2025,
            DocumentType.TRANSCRIPTS,
            None,
            FrequencyEnum.monthly,
            100,
            10,
            "The number of days in the range between start_date",
        ),
        # Invalid frequency value
        (
            "US Import Tariffs against China",
            ["4A6F00"],
            "2025-06-01",
            "2025-08-01",
            "openai::gpt-4o-mini",
            2025,
            DocumentType.TRANSCRIPTS,
            None,
            "invalid_freq",
            100,
            10,
            "invalid_freq",
        ),
    ],
)
def test_thematic_screen_request_model_invalid(
    theme,
    companies,
    start_date,
    end_date,
    llm_model,
    fiscal_year,
    document_type,
    rerank_threshold,
    frequency,
    document_limit,
    batch_size,
    expected_error,
):
    with pytest.raises((ValidationError, ValueError)) as exc_info:
        ThematicScreenRequest(
            theme=theme,
            companies=companies,
            start_date=start_date,
            end_date=end_date,
            llm_model=llm_model,
            fiscal_year=fiscal_year,
            document_type=document_type,
            rerank_threshold=rerank_threshold,
            frequency=frequency,
            document_limit=document_limit,
            batch_size=batch_size,
        )
    assert expected_error in str(exc_info.value)


@pytest.mark.parametrize(
    "theme,companies,start_date,end_date,llm_model,fiscal_year,document_type,rerank_threshold,frequency,document_limit,batch_size",
    [
        # Minimal valid input with companies
        (
            "US Import Tariffs against China",
            ["4A6F00", "D8442A"],
            "2025-06-01",
            "2025-08-01",
            "openai::gpt-4o-mini",
            2025,
            DocumentType.TRANSCRIPTS,
            None,
            FrequencyEnum.monthly,
            100,
            10,
        ),
        # Minimal valid input with watchlist_id
        (
            "US Import Tariffs against China",
            "44118802-9104-4265-b97a-2e6d88d74893",
            "2025-06-01",
            "2025-08-01",
            "openai::gpt-4o-mini",
            2025,
            DocumentType.TRANSCRIPTS,
            0.8,
            FrequencyEnum.weekly,
            50,
            5,
        ),
        # Different frequency and document type
        (
            "Supply Chain Reshaping",
            ["A12345"],
            "2025-01-01",
            "2025-12-31",
            "openai::gpt-4o-mini",
            2025,
            DocumentType.TRANSCRIPTS,
            None,
            FrequencyEnum.yearly,
            200,
            20,
        ),
        # Control entities with multiple places
        (
            "Supply Chain Reshaping",
            ["B67890"],
            "2025-07-01",
            "2025-08-01",
            "openai::gpt-4o-mini",
            2025,
            DocumentType.TRANSCRIPTS,
            None,
            FrequencyEnum.daily,
            10,
            1,
        ),
    ],
)
def test_thematic_screen_request_model(
    theme,
    companies,
    start_date,
    end_date,
    llm_model,
    fiscal_year,
    document_type,
    rerank_threshold,
    frequency,
    document_limit,
    batch_size,
):
    req = ThematicScreenRequest(
        theme=theme,
        companies=companies,
        start_date=start_date,
        end_date=end_date,
        llm_model=llm_model,
        fiscal_year=fiscal_year,
        document_type=document_type,
        rerank_threshold=rerank_threshold,
        frequency=frequency,
        document_limit=document_limit,
        batch_size=batch_size,
    )
    assert req.theme == theme
    assert req.start_date == start_date
    assert req.end_date == end_date
    assert req.llm_model == llm_model
    assert req.document_type == document_type
    assert req.frequency == frequency
    assert req.document_limit == document_limit
    assert req.batch_size == batch_size
    if companies:
        assert req.companies == companies
    if rerank_threshold is not None:
        assert req.rerank_threshold == rerank_threshold
