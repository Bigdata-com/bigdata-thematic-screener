import math
from datetime import datetime
from importlib.metadata import version
from uuid import UUID

import pandas as pd
from bigdata_client import Bigdata
from bigdata_client.models.entities import Company
from bigdata_research_tools.themes import ThemeTree
from bigdata_research_tools.utils.observer import OberserverNotification, Observer
from bigdata_research_tools.workflows.thematic_screener import ThematicScreener

from bigdata_thematic_screener.api.models import ThematicScreenRequest, WorkflowStatus
from bigdata_thematic_screener.api.storage import StorageManager
from bigdata_thematic_screener.models import (
    CompanyScoring,
    LabeledChunk,
    LabeledContent,
    ThematicScreenerResponse,
    ThemeScore,
    ThemeScoring,
    ThemeTaxonomy,
)
from bigdata_thematic_screener.traces import TraceEventName, send_trace


class WorkflowObserver(Observer):
    def __init__(self, request_id: UUID, storage_manager: StorageManager):
        self.request_id = request_id
        self.storage_manager = storage_manager

    def update(self, message: OberserverNotification):
        self.storage_manager.log_message(
            request_id=self.request_id,
            message=message.message,
        )


def prepare_companies(
    companies: list[str] | str,
    bigdata: Bigdata,
) -> list[Company]:
    """Prepare the list of companies for analysis. Ensure at least one of the forms of providing
    the companies is present and ensures all elements are companies."""
    if isinstance(companies, list):
        entities = bigdata.knowledge_graph.get_entities(companies)
    elif isinstance(companies, str):
        entities = bigdata.knowledge_graph.get_entities(
            bigdata.watchlists.get(companies).items
        )
    else:
        raise ValueError(
            "Companies must be either a list of RP entity IDs or a string representing a watchlist ID."
        )

    # Ensure there is entities, there is no duplicates and all entities are companies
    if len(entities) == 0:
        raise ValueError("No entities found in the provided universe or watchlist.")

    companies = [
        Company(**e.model_dump())  # ty: ignore[missing-argument]
        for e in entities
        if e is not None and e.entity_type == "COMP"
    ]

    dedupped_companies = {c.id: c for c in companies}

    return list(dedupped_companies.values())


def build_response(
    df_company: pd.DataFrame,
    df_motivation: pd.DataFrame,
    df_labeled: pd.DataFrame,
    theme_tree: ThemeTree,
) -> ThematicScreenerResponse:
    """
    Build the response for the output of the thematic screener workflow.
    """
    theme_scoring = {}
    for record in df_company.to_dict(orient="records"):
        company = record.pop("Company")
        ticker = record.pop("Ticker")
        industry = record.pop("Industry")
        motivation = df_motivation.loc[df_motivation["Company"] == company][
            "Motivation"
        ].values[0]
        composite_score = record.pop("Composite Score")
        theme_scoring[company] = CompanyScoring(
            ticker=ticker,
            industry=industry,
            motivation=motivation,
            composite_score=composite_score,
            themes=ThemeScore(
                root={
                    k: v
                    for k, v in record.items()
                    if isinstance(v, int) and not math.isnan(v)
                }
            ),
        )

    # Return results
    return ThematicScreenerResponse(
        theme_taxonomy=ThemeTaxonomy(**theme_tree._to_dict()),  # ty: ignore[missing-argument]
        theme_scoring=ThemeScoring(root=theme_scoring),
        content=LabeledContent(
            root=[
                LabeledChunk(
                    time_period=record["Time Period"],
                    date=record["Date"],
                    company=record["Company"],
                    sector=record["Sector"],
                    industry=record["Industry"],
                    country=record["Country"],
                    ticker=record["Ticker"],
                    document_id=record["Document ID"],
                    headline=record["Headline"],
                    quote=record["Quote"],
                    motivation=record["Motivation"],
                    theme=record["Theme"],
                )
                for record in df_labeled.to_dict(orient="records")
            ]
        ),
    )


def process_request(
    request: ThematicScreenRequest,
    bigdata: Bigdata | None,
    request_id: UUID,
    storage_manager: StorageManager,
):
    storage_manager.update_status(request_id, WorkflowStatus.IN_PROGRESS)
    if not bigdata:
        storage_manager.update_status(request_id, WorkflowStatus.FAILED)
        raise ValueError("Bigdata client is not initialized.")

    # Research tools marks it as optional, but expects an empty screen if not available
    if request.focus is None:
        request.focus = ""

    workflow_execution_start = datetime.now()

    resolved_companies = prepare_companies(request.companies, bigdata)

    thematic_screener = ThematicScreener(
        llm_model=request.llm_model,
        main_theme=request.theme,
        focus=request.focus,
        companies=resolved_companies,
        start_date=request.start_date,
        end_date=request.end_date,
        document_type=request.document_type,
        fiscal_year=request.fiscal_year,
        rerank_threshold=request.rerank_threshold,
    )

    thematic_screener.register_observer(
        WorkflowObserver(request_id=request_id, storage_manager=storage_manager)
    )

    results = thematic_screener.screen_companies(
        document_limit=request.document_limit,
        batch_size=request.batch_size,
        frequency=request.frequency.value,
    )
    df_labeled = results["df_labeled"]
    df_company = results["df_company"]
    df_motivation = results["df_motivation"]
    theme_tree = results["theme_tree"]

    workflow_execution_end = datetime.now()

    # Send log
    send_trace(
        bigdata,
        event_name=TraceEventName.THEMATIC_SCREENER_REPORT_GENERATED,
        trace={
            "bigdataClientVersion": version("bigdata-client"),
            "workflowStartDate": workflow_execution_start.isoformat(timespec="seconds"),
            "workflowEndDate": workflow_execution_end.isoformat(timespec="seconds"),
            "watchlistLength": len(resolved_companies),
        },
    )

    response = build_response(
        df_company=df_company,
        df_motivation=df_motivation,
        df_labeled=df_labeled,
        theme_tree=theme_tree,
    )

    storage_manager.mark_workflow_as_completed(request_id, request, response)
    return response
