from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.mutable import MutableList
from sqlmodel import JSON, Column, Field, SQLModel

from bigdata_thematic_screener.api.models import ThematicScreenRequestBase
from bigdata_thematic_screener.models import ThematicScreenerResponse


class SQLWorkflowStatus(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    last_updated: datetime
    status: str
    logs: list[str] = Field(
        default_factory=list, sa_column=Column(MutableList.as_mutable(JSON))
    )


class SQLThematicScreenerReport(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    companies: list[str] = Field(sa_column=Column(JSON))
    llm_model: str
    theme: str
    focus: str | None = None
    start_date: datetime
    end_date: datetime
    rerank_threshold: float | None = None
    chunk_percentage: float
    screener_report: dict = Field(sa_column=Column(JSON))

    @staticmethod
    def from_thematic_screener_response(
        request_id: UUID,
        request: ThematicScreenRequestBase,
        company_ids: list[str],
        response: ThematicScreenerResponse,
    ) -> "SQLThematicScreenerReport":
        return SQLThematicScreenerReport(
            id=request_id,
            companies=company_ids,
            llm_model=request.llm_model,
            theme=request.theme,
            focus=request.focus,
            start_date=datetime.fromisoformat(request.start_date),
            end_date=datetime.fromisoformat(request.end_date),
            rerank_threshold=request.rerank_threshold,
            chunk_percentage=request.chunk_percentage,
            screener_report=response.model_dump(),
        )
