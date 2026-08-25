from functools import partial
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    BackgroundTasks,
    Body,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Security,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlmodel import Session, SQLModel, create_engine

from bigdata_thematic_screener import LOG_LEVEL, __version__, logger
from bigdata_thematic_screener.api.fmp_etf import run_etf_exposure_pipeline
from bigdata_thematic_screener.api.models import (
    EXAMPLE_COMPANY_LISTS,
    EtfExposureItem,
    EtfExposureRequest,
    EtfExposureResponse,
    ThematicScreenerAcceptedResponse,
    ThematicScreenerStatusResponse,
    ThematicScreenRequest,
    ThematicScreenRequestBase,
    WorkflowStatus,
)
from bigdata_thematic_screener.api.secure import query_scheme
from bigdata_thematic_screener.api.storage import StorageManager
from bigdata_thematic_screener.api.utils import get_example_values_from_schema
from bigdata_thematic_screener.models import ThematicScreenerResponse
from bigdata_thematic_screener.service import process_request
from bigdata_thematic_screener.settings import settings
from bigdata_thematic_screener.templates import loader
from bigdata_thematic_screener.universe import build_universe_from_ids, load_universe_csv

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
    logger.info("Starting thematic screener service")
    create_db_and_tables()
    yield


app = FastAPI(
    title="Thematic screener API",
    description="API for analyzing corporate exposure to specific themes and events using Bigdata.com",
    version=__version__,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")


@app.get(
    "/health",
    summary="Health check endpoint",
)
def health_check():
    return {"status": "ok", "version": __version__}


@app.post(
    "/api/etf-exposure",
    summary="Aggregate ETF exposure for thematic tickers (FMP via server)",
    response_model=EtfExposureResponse,
)
def etf_exposure(
    body: Annotated[EtfExposureRequest, Body()],
    _: str = Security(query_scheme),
) -> EtfExposureResponse:
    if not settings.FMP_API_KEY.strip():
        raise HTTPException(
            status_code=503,
            detail="FMP API key is not configured. Set FMP_API_KEY to enable ETF lookups.",
        )
    raw_etfs, total_used, warnings = run_etf_exposure_pipeline(
        theme_scoring=body.theme_scoring,
        top_n=body.top_n,
        top_k=body.top_k,
        api_key=settings.FMP_API_KEY,
        extra_tickers=body.extra_tickers,
        etf_symbols_filter=body.etf_symbols_filter,
        tickers_mode=body.tickers_mode,
    )
    items = [EtfExposureItem(**e) for e in raw_etfs]
    return EtfExposureResponse(etfs=items, total_tickers_used=total_used, warnings=warnings)


@app.get(
    "/",
    summary="Example frontend for testing the thematic screener.",
    response_class=HTMLResponse,
)
async def sample_frontend(_: str = Security(query_scheme)) -> HTMLResponse:
    # Get example values from the schema for all fields
    template_values = get_example_values_from_schema(ThematicScreenRequest)
    template_values["example_companies"] = EXAMPLE_COMPANY_LISTS
    template_values["demo_mode"] = settings.DEMO_MODE
    template_values["version"] = f"v{__version__}"
    template_values["fmp_etf_lookup_enabled"] = bool(settings.FMP_API_KEY.strip())

    return HTMLResponse(
        content=loader.get_template("api/index.html.jinja").render(**template_values),
        media_type="text/html",
    )


def _queue_screening(
    request: ThematicScreenRequestBase,
    universe_df,
    background_tasks: BackgroundTasks,
    storage_manager: StorageManager,
) -> JSONResponse:
    request_id: UUID = uuid4()
    storage_manager.update_status(request_id, WorkflowStatus.QUEUED)

    background_tasks.add_task(
        partial(
            process_request,
            request,
            universe_df=universe_df,
            request_id=request_id,
            storage_manager=storage_manager,
        )
    )
    return JSONResponse(
        status_code=202,
        content=ThematicScreenerAcceptedResponse(
            request_id=str(request_id), status=WorkflowStatus.QUEUED
        ).model_dump(),
    )


@app.post(
    "/thematic-screener",
    summary="Generate a thematic screener report on your universe",
    response_model=ThematicScreenerResponse,
)
def screen_companies(
    request: Annotated[ThematicScreenRequest, Body()],
    background_tasks: BackgroundTasks,
    storage_manager: StorageManager = Depends(get_storage_manager),
    _: str = Security(query_scheme),
) -> JSONResponse:
    """This endpoint starts the generation of the thematic screener workflow on the background
    and will return a request_id that can be used to check the status of the request in the
    `/status/{request_id}` endpoint.

    `companies` must be a list of RavenPack entity IDs. Watchlists are not supported; upload
    a CSV via `/thematic-screener/upload` for larger or metadata-rich universes.
    """
    try:
        universe_df = build_universe_from_ids(request.companies, api_key=settings.BIGDATA_API_KEY)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _queue_screening(request, universe_df, background_tasks, storage_manager)


@app.post(
    "/thematic-screener/upload",
    summary="Generate a thematic screener report from an uploaded universe CSV",
    response_model=ThematicScreenerResponse,
)
def screen_companies_upload(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="Universe CSV with RP_ENTITY_ID + COMPANY_NAME columns.")],
    request: Annotated[
        str, Form(description="JSON-encoded request body (same fields as POST /thematic-screener, minus companies).")
    ],
    storage_manager: StorageManager = Depends(get_storage_manager),
    _: str = Security(query_scheme),
) -> JSONResponse:
    """Same as `POST /thematic-screener`, but the company universe comes from an uploaded CSV
    (columns: `RP_ENTITY_ID` [alias `RP_COMPANY_ID`], `COMPANY_NAME`, and optionally
    `TICKER`/`SECTOR`/`INDUSTRY`/`COUNTRY`) instead of a list of RP entity IDs.
    """
    try:
        parsed_request = ThematicScreenRequestBase.model_validate_json(request)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    try:
        universe_df = load_universe_csv(file.file, api_key=settings.BIGDATA_API_KEY)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _queue_screening(parsed_request, universe_df, background_tasks, storage_manager)


@app.get(
    "/status/{request_id}",
    summary="Get the status of a thematic screener report",
)
def get_status(
    request_id: UUID,
    storage_manager: StorageManager = Depends(get_storage_manager),
    _: str = Security(query_scheme),
) -> ThematicScreenerStatusResponse:
    """Get the status of a thematic screener report by its request_id. If the report is still
    running, you will get the current status and logs. If the report is completed, you will
    also get the complete report"""
    report = storage_manager.get_report(request_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Request ID not found")
    return report
