from datetime import datetime
from uuid import UUID

import pandas as pd

from bigdata_thematic_screener import pipeline
from bigdata_thematic_screener.api.models import ThematicScreenRequestBase, WorkflowStatus
from bigdata_thematic_screener.api.storage import StorageManager
from bigdata_thematic_screener.models import ThematicScreenerResponse
from bigdata_thematic_screener.taxonomy import Node
from bigdata_thematic_screener.universe import ID_COLUMN


def build_response(
    screener_df: pd.DataFrame,
    root: Node,
    universe_df: pd.DataFrame,
) -> ThematicScreenerResponse:
    """Assemble the API response from the labeled sentences, taxonomy, and universe."""
    report = pipeline.build_theme_report(screener_df, root, universe_df)
    return ThematicScreenerResponse(**report)


def process_request(
    request: ThematicScreenRequestBase,
    universe_df: pd.DataFrame,
    request_id: UUID,
    storage_manager: StorageManager,
):
    try:
        storage_manager.update_status(request_id, WorkflowStatus.IN_PROGRESS)

        def on_progress(message: str) -> None:
            storage_manager.log_message(request_id=request_id, message=message)

        workflow_execution_start = datetime.now()

        report = pipeline.run_thematic_screening(
            main_theme=request.theme,
            focus=request.focus or "",
            keywords=request.keywords,
            start_date=request.start_date,
            end_date=request.end_date,
            model=request.llm_model,
            rerank_threshold=request.rerank_threshold,
            chunk_percentage=request.chunk_percentage,
            max_leaf_labels=request.max_leaf_labels,
            max_taxonomy_depth=request.max_taxonomy_depth,
            universe_df=universe_df,
            on_progress=on_progress,
        )

        workflow_execution_end = datetime.now()
        on_progress(
            "Workflow completed in "
            f"{(workflow_execution_end - workflow_execution_start).total_seconds():.1f}s"
        )

        response = ThematicScreenerResponse(**report)

        storage_manager.mark_workflow_as_completed(
            request_id, request, universe_df[ID_COLUMN].tolist(), response
        )
        return response

    except Exception as e:
        storage_manager.log_message(
            request_id=request_id,
            message=f"Workflow failed with error: {str(e)}",
        )
        storage_manager.update_status(request_id, WorkflowStatus.FAILED)
        raise e
