from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Literal, Optional

from bigdata_client.models.search import DocumentType
from pydantic import BaseModel, Field, model_validator

from bigdata_thematic_screener.models import ThematicScreenerResponse


def two_months_ago() -> date:
    return date.today() - timedelta(days=60)


def yesterday() -> date:
    return date.today() - timedelta(days=1)


class FrequencyEnum(StrEnum):
    daily = "D"
    weekly = "W"
    monthly = "M"
    quarterly = "3M"
    yearly = "Y"


class WorkflowStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ThematicScreenRequest(BaseModel):
    theme: str = Field(
        ...,
        example="Supply Chain Reshaping",
        description="The central concept to explore.",
    )
    focus: str | None = Field(
        default=None,
        description="Specific focus area within the theme.",
        example="Logistics automation, nearshoring strategies, and supply chain digitalization",
    )
    companies: list[str] | str = Field(
        ...,
        description="List of RavenPack entity IDs  or a watchlist ID representing the companies to screen.",
        example="44118802-9104-4265-b97a-2e6d88d74893",
    )
    start_date: str = Field(
        description="Start date of the analysis window (format: YYYY-MM-DD).",
        example="2024-01-01",
    )
    end_date: str = Field(
        default=yesterday().isoformat(),
        description="End date of the analysis window (format: YYYY-MM-DD).",
        example="2024-12-31",
    )
    llm_model: str = Field(
        default="openai::gpt-4o-mini",
        description="LLM model identifier used for taxonomy creation and semantic analysis.",
    )
    fiscal_year: int | None = Field(
        description="If the document type is transcripts or filings, fiscal year needs to be specified.",
        example=2024,
    )

    document_type: Literal[DocumentType.TRANSCRIPTS] = Field(
        default=DocumentType.TRANSCRIPTS,
        description="Type of documents to analyze (only transcript supported for now).",
    )
    rerank_threshold: Optional[float] = Field(
        default=None,
        description="Optional threshold (0-1) to rerank and filter search results by relevance.",
    )
    frequency: FrequencyEnum = Field(
        default=FrequencyEnum.monthly,
        description="Search frequency interval. Supported values: D (daily), W (weekly), M (monthly), Y (yearly).",
    )
    document_limit: int = Field(
        default=100,
        description="Maximum number of documents to retrieve per query to Bigdata API.",
    )
    batch_size: int = Field(
        default=10,
        description="Number of entities to include in each batch for parallel querying.",
    )

    @model_validator(mode="before")
    def check_date_range(cls, values):
        try:
            start_date = values["start_date"]
            end_date = values["end_date"]
            if (
                start_date > end_date
            ):  # We can compare directly as they are both ISO format strings
                raise ValueError("start_date must be earlier than end_date")
        except Exception as e:
            raise ValueError(f"Invalid date format or range: {e}")
        return values

    @model_validator(mode="before")
    def check_fiscal_year_when_transcript_or_filing(cls, values):
        doc_type = values.get("document_type", None)
        if doc_type is None:
            raise ValueError("document_type must be specified.")
        if doc_type.upper() not in DocumentType.__members__:
            raise ValueError(
                f"Invalid document_type: {doc_type}, possible values are: {list(DocumentType.__members__.keys())}"
            )
        doc_type = DocumentType[doc_type.upper()]
        if doc_type in [
            DocumentType.TRANSCRIPTS,
            DocumentType.FILINGS,
        ] and not values.get("fiscal_year"):
            raise ValueError(
                "fiscal_year must be specified when document_type is TRANSCRIPT or FILING."
            )
        elif (
            doc_type
            and doc_type
            not in [
                DocumentType.TRANSCRIPTS,
                DocumentType.FILINGS,
            ]
            and values.get("fiscal_year") is not None
        ):
            raise ValueError(
                "fiscal_year must not be specified when document_type is not TRANSCRIPT or FILING."
            )
        return values

    @model_validator(mode="before")
    def check_frequency_vs_date_range(cls, values):
        start_date = values["start_date"]
        end_date = values["end_date"]
        freq = values.get("frequency")
        delta_days = (
            datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)
        ).days + 1  # Adjust for inclusive range
        freq_min_days = {"D": 1, "W": 7, "M": 30, "3M": 90, "Y": 365}
        if isinstance(freq, str):
            freq = FrequencyEnum(freq)
        if not isinstance(freq, FrequencyEnum):
            raise ValueError(f"Invalid frequency: {freq}")
        if delta_days < freq_min_days[freq.value]:
            raise ValueError(
                f"The number of days in the range between start_date={start_date} and end_date={end_date} ({delta_days} days) should be higher than the minimum required for the selected frequency '{freq.value}' ({freq_min_days[freq.value]} days)."
            )
        return values


class ThematicScreenerAcceptedResponse(BaseModel):
    request_id: str
    status: WorkflowStatus


class ThematicScreenerStatusResponse(BaseModel):
    request_id: str
    last_updated: datetime
    status: WorkflowStatus
    logs: list[str] = Field(default_factory=list)
    report: ThematicScreenerResponse | None = None
