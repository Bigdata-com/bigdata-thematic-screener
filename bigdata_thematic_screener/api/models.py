from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator
from pydantic_core import ValidationError

from bigdata_thematic_screener.models import ThematicScreenerResponse
from bigdata_thematic_screener.taxonomy import DEFAULT_MAX_LEAF_LABELS
from bigdata_thematic_screener.universe import WATCHLIST_REJECTED_MESSAGE


def one_year_ago() -> date:
    return date.today() - timedelta(days=365)


def yesterday() -> date:
    return date.today() - timedelta(days=1)


class WorkflowStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TickersBasketMode(StrEnum):
    """How the Tickers text field combines with top N from the report."""

    merge = "merge"
    only = "only"


# Example RP entity IDs for the demo UI's "quick fill" dropdown, sourced from
# Internal/mag7.csv. Watchlists are not supported (see WATCHLIST_REJECTED_MESSAGE).
EXAMPLE_COMPANY_LISTS: dict[str, list[str]] = {
    "MAG_7": ["E09E2B", "D8442A", "228D42", "0157B1", "4A6F00", "12E454", "DD3BB1"],
}

DEFAULT_LLM_MODEL = "gpt-5.6-luna"
DEFAULT_CHUNK_PERCENTAGE = 0.05


class ThematicScreenRequestBase(BaseModel):
    """Shared thematic-screener request fields.

    Used directly by the CSV-upload endpoint (whose company universe comes
    from the uploaded file, not this model) and extended by
    :class:`ThematicScreenRequest` for the JSON endpoint (which additionally
    takes a `companies` list of RP entity IDs).
    """

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
    start_date: str = Field(
        default="2024-01-01",
        description="Start date of the analysis window (format: YYYY-MM-DD).",
        example=one_year_ago().isoformat(),
    )
    end_date: str = Field(
        default="2024-12-31",
        description="End date of the analysis window (format: YYYY-MM-DD).",
        example=yesterday().isoformat(),
    )
    keywords: list[str] | None = Field(
        default=None,
        description="Key terms to emphasize when generating the theme taxonomy.",
        example=None,
    )
    llm_model: str = Field(
        default=DEFAULT_LLM_MODEL,
        description="OpenAI model used for taxonomy generation, chunk labeling, and company summaries.",
        example=DEFAULT_LLM_MODEL,
    )
    rerank_threshold: float | None = Field(
        default=None,
        description="Optional relevance threshold (0-1); chunks scoring below it are discarded.",
        example=None,
    )
    chunk_percentage: float = Field(
        default=DEFAULT_CHUNK_PERCENTAGE,
        ge=0.0,
        le=1.0,
        description="Fraction (0-1, not a percentage — e.g. 0.05 = 5%) of the estimated available chunks to retrieve per taxonomy leaf. Higher values cost more and take longer.",
        example=DEFAULT_CHUNK_PERCENTAGE,
    )
    max_leaf_labels: int | None = Field(
        default=DEFAULT_MAX_LEAF_LABELS,
        description="Maximum number of leaf exposure pathways in the generated theme taxonomy. Use 0 or null for no cap.",
        example=DEFAULT_MAX_LEAF_LABELS,
    )
    max_taxonomy_depth: int | None = Field(
        default=None,
        ge=2,
        description=(
            "Maximum number of levels in the generated theme taxonomy, counting the root "
            "theme node as level 1. Defaults to the model's natural structure."
        ),
        example=None,
    )

    @model_validator(mode="before")
    @classmethod
    def check_date_range(cls, values):
        start_date = values.get("start_date", cls.model_fields["start_date"].default)
        end_date = values.get("end_date", cls.model_fields["end_date"].default)
        try:
            if (
                start_date > end_date
            ):  # We can compare directly as they are both ISO format strings
                raise ValueError("start_date must be earlier than end_date")
        except Exception as e:
            raise ValidationError.from_exception_data(
                title=cls.__name__,
                line_errors=[
                    {
                        "type": "value_error",
                        "loc": ("start_date", "end_date"),
                        "ctx": {"error": f"Invalid date format or range: {e}"},
                        "input": {
                            "start_date": start_date,
                            "end_date": end_date,
                        },
                    }
                ],
            )
        return values


class ThematicScreenRequest(ThematicScreenRequestBase):
    companies: list[str] | str = Field(
        ...,
        description="List of RavenPack entity IDs representing the companies to screen. Watchlists are not supported.",
        example=EXAMPLE_COMPANY_LISTS["MAG_7"],
    )

    @model_validator(mode="after")
    def reject_watchlist(self) -> Self:
        if isinstance(self.companies, str):
            raise ValueError(WATCHLIST_REJECTED_MESSAGE)
        return self


class ThematicScreenerAcceptedResponse(BaseModel):
    request_id: str
    status: WorkflowStatus


class ThematicScreenerStatusResponse(BaseModel):
    request_id: str
    last_updated: datetime
    status: WorkflowStatus
    logs: list[str] = Field(default_factory=list)
    report: ThematicScreenerResponse | None = None


# ---------------------------------------------------------------------------
# ETF exposure feature (FMP-based; no Bigdata SDK dependency, untouched by
# the SDK-to-REST migration).
# ---------------------------------------------------------------------------


class EtfExposureRequest(BaseModel):
    """Body for server-side ETF asset-exposure aggregation (FMP key stays on server)."""

    theme_scoring: dict[str, Any] = Field(
        ...,
        description="Same shape as report.theme_scoring: company name -> scoring object with ticker, composite_score.",
    )
    top_n: int = Field(
        ...,
        ge=1,
        le=50,
        description="How many top-scored companies to include from theme_scoring.",
    )
    top_k: int = Field(
        ..., ge=1, le=50, description="Max ETFs to return after ranking."
    )
    extra_tickers: list[str] = Field(
        default_factory=list,
        description="Symbols in the Tickers box (comma/space separated). Meaning depends on tickers_mode.",
    )
    tickers_mode: TickersBasketMode = Field(
        default=TickersBasketMode.merge,
        description="merge: top_n from theme_scoring plus Tickers. only: basket is only Tickers (top_n ignored).",
    )
    etf_symbols_filter: list[str] | None = Field(
        default=None,
        description=(
            "If set, only these ETF symbols are analyzed: holdings are fetched per fund and "
            "theme scores are basket overlap weights (not global ETF discovery)."
        ),
    )


class EtfExposureItem(BaseModel):
    etfSymbol: str
    themeScore: float
    matchCount: int
    matchedTickers: list[str]
    totalTickers: int
    estAum: float
    rank: int
    aliases: list[str] | None = None


class EtfExposureResponse(BaseModel):
    etfs: list[EtfExposureItem]
    total_tickers_used: int
    warnings: list[str] = Field(default_factory=list)
