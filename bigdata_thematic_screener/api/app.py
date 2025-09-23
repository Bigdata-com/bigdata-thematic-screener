from functools import partial
from typing import Annotated
from uuid import uuid4

from bigdata_client import Bigdata
from bigdata_client.models.search import DocumentType
from fastapi import BackgroundTasks, Body, Depends, FastAPI, HTTPException, Security
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, SQLModel, create_engine

from bigdata_thematic_screener import LOG_LEVEL, __version__, logger
from bigdata_thematic_screener.api.models import (
    ThematicScreenerAcceptedResponse,
    ThematicScreenerStatusResponse,
    ThematicScreenRequest,
    WorkflowStatus,
)
from bigdata_thematic_screener.api.secure import query_scheme
from bigdata_thematic_screener.api.storage import StorageManager
from bigdata_thematic_screener.api.utils import get_example_values_from_schema
from bigdata_thematic_screener.service import process_request
from bigdata_thematic_screener.settings import settings
from bigdata_thematic_screener.templates import loader
from bigdata_thematic_screener.traces import TraceEventName, send_trace

BIGDATA: Bigdata | None = None
engine = create_engine(settings.DB_STRING, echo=LOG_LEVEL == "DEBUG")


def create_db_and_tables():
    logger.info("Setting up data storage", db_string=settings.DB_STRING)
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def get_storage_manager(session: Session = Depends(get_session)) -> StorageManager:
    return StorageManager(session)


def lifespan(app: FastAPI):
    global BIGDATA
    logger.info("Starting thematic screener service")

    # Instantiate Bigdata client
    BIGDATA = Bigdata(api_key=settings.BIGDATA_API_KEY)

    send_trace(
        BIGDATA,
        event_name=TraceEventName.SERVICE_START,
        trace={
            "version": __version__,
        },
    )
    create_db_and_tables()
    yield


app = FastAPI(
    title="Thematic screener API",
    description="API for analyzing corporate exposure to specific themes and events using Bigdata.com",
    version=__version__,
    lifespan=lifespan,
)


@app.get(
    "/health",
    summary="Health check endpoint",
)
def health_check():
    return {"status": "ok", "version": __version__}


@app.get(
    "/",
    summary="Example frontend for testing the thematic screener.",
    response_class=HTMLResponse,
)
async def sample_frontend(_: str = Security(query_scheme)) -> HTMLResponse:
    # Get example values from the schema for all fields
    example_values = get_example_values_from_schema(ThematicScreenRequest)

    return HTMLResponse(
        #content=loader.get_template("api/frontend.html.jinja").render(**example_values),
        content=loader.get_template("api/main_frontend.html.jinja").render(**example_values),
        media_type="text/html",
    )


@app.post(
    "/thematic-screener",
    summary="Generate a thematic screener report on your universe",
    response_model=ThematicScreenerAcceptedResponse,
)
def screen_companies(
    request: Annotated[ThematicScreenRequest, Body()],
    background_tasks: BackgroundTasks,
    storage_manager: StorageManager = Depends(get_storage_manager),
    _: str = Security(query_scheme),
) -> JSONResponse:
    """This endpoints starts the generation of the thematic screener workflow on the background
    and will return a request_id that can be used to check the status of the request in the
    `/status/{request_id}` endpoint.

    Note: for now, it only supports transcripts as document type.
    """
    # While we improve the UX of working with several document types with different sets of parameters
    # we will limit the document type to transcripts
    DOCUMENT_TYPE = DocumentType.TRANSCRIPTS
    request.document_type = DOCUMENT_TYPE
    request_id = str(uuid4())

    storage_manager.update_status(request_id, WorkflowStatus.QUEUED)

    background_tasks.add_task(
        partial(
            process_request,
            request,
            bigdata=BIGDATA,
            request_id=request_id,
            storage_manager=storage_manager,
        )
    )

    return JSONResponse(
        status_code=202,
        content=ThematicScreenerAcceptedResponse(
            request_id=request_id, status=WorkflowStatus.QUEUED
        ).model_dump(),
    )


@app.get(
    "/status/{request_id}",
    summary="Get the status of a thematic screener report",
)
def get_status(
    request_id: str,
    storage_manager: StorageManager = Depends(get_storage_manager),
    _: str = Security(query_scheme),
) -> ThematicScreenerStatusResponse:
    """Get the status of a thematic screener report by its request_id. If the report is still running,
    you will get the current status and logs. If the report is completed, you will also get the
    complete report"""
    report = storage_manager.get_report(request_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Request ID not found")
    return report
