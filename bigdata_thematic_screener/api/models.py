from datetime import date, datetime, timedelta
from enum import Enum, StrEnum
from typing import Literal, Optional

from bigdata_client.models.search import DocumentType
from pydantic import BaseModel, Field, model_validator

from bigdata_thematic_screener.models import ThematicScreenerResponse


def one_year_ago() -> date:
    return date.today() - timedelta(days=365)


def yesterday() -> date:
    return date.today() - timedelta(days=1)


def select_fiscal_year() -> list[int]:
    today = date.today()
    # Create a fiscal year window from last year to next year
    fiscal_window = [today.year - 1, today.year, today.year + 1]
    return fiscal_window


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


class WatchlistExample(BaseModel):
    id: str = Field(..., description="The unique identifier for the watchlist.")
    name: str = Field(..., description="The name of the watchlist.")


class ExampleWatchlists(Enum):
    TOP_100_UK = WatchlistExample(
        id="33d6f577-9256-4a53-944f-09127e42fdc2", name="Top 100 UK"
    )
    TOP_50_EU = WatchlistExample(
        id="9baef470-8cf5-46fa-b30a-352bcb35cd94", name="Top 50 Europe"
    )
    US_LARGE_CAP_100 = WatchlistExample(
        id="44118802-9104-4265-b97a-2e6d88d74893", name="Top 100 US"
    )
    TOP_40_DE = WatchlistExample(
        id="8453c26f-47c5-4e78-b5c8-acf245caccad", name="Top 40 Germany"
    )
    TOP_40_FR = WatchlistExample(
        id="9fb6ac2d-a552-4dbb-b62f-8657ef18bf29", name="Top 40 France"
    )
    DOW_30 = WatchlistExample(id="5b78837c-343d-4559-8f06-98668b09d1df", name="Dow 30")
    NASDAQ_100 = WatchlistExample(
        id="402acbcd-f1d8-4a55-997a-598819be0bbf", name="Nasdaq 100"
    )
    MAG_7 = WatchlistExample(
        id="814d0944-a2c1-44f6-8b42-a70c0795428e", name="Magnificent 7"
    )

    def __iter__(self):
        """Allows to create a dict from the enum
        >>> dict(ExampleWatchlists)
        {'POINT_72': {'id': '9ab396cf-a2bb-4c91-b9bf-ed737905803e', 'name': 'Point 72 Holdings'}, ...}
        """
        yield self.name
        yield self.value.model_dump()


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
        example=ExampleWatchlists.US_LARGE_CAP_100.value.id,
    )
    start_date: str = Field(
        ...,
        description="Start date of the analysis window (format: YYYY-MM-DD).",
        example=one_year_ago().isoformat(),
    )
    end_date: str = Field(
        ...,
        description="End date of the analysis window (format: YYYY-MM-DD).",
        example=yesterday().isoformat(),
    )
    llm_model: str = Field(
        default="openai::gpt-4o-mini",
        example="openai::gpt-4o-mini",
        description="LLM model identifier used for taxonomy creation and semantic analysis.",
    )
    fiscal_year: int | list[int] | None = Field(
        description="If the document type is transcripts or filings, fiscal year needs to be specified.",
        example=select_fiscal_year(),
    )

    document_type: Literal[DocumentType.TRANSCRIPTS] = Field(
        default=DocumentType.TRANSCRIPTS,
        description="Type of documents to analyze (only transcript supported for now).",
    )
    rerank_threshold: Optional[float] = Field(
        default=None,
        example=None,
        description="Optional threshold (0-1) to rerank and filter search results by relevance.",
    )
    frequency: FrequencyEnum = Field(
        default=FrequencyEnum.yearly,
        example=FrequencyEnum.yearly,
        description="Search frequency interval. Supported values: D (daily), W (weekly), M (monthly), 3M (quarterly), Y (yearly).",
    )
    document_limit: int = Field(
        default=100,
        example=100,
        description="Maximum number of documents to retrieve per query to Bigdata API.",
    )
    batch_size: int = Field(
        default=10,
        example=10,
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
