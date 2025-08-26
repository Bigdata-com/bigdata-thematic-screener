from typing import Annotated

from bigdata_client import Bigdata
from fastapi import Body, FastAPI
from fastapi.responses import HTMLResponse

from bigdata_thematic_screener import __version__, logger
from bigdata_thematic_screener.api.models import ThematicScreenRequest
from bigdata_thematic_screener.api.utils import get_example_values_from_schema
from bigdata_thematic_screener.models import ThematicScreenerResponse
from bigdata_thematic_screener.service import DocumentType, process_request
from bigdata_thematic_screener.settings import settings
from bigdata_thematic_screener.templates import loader
from bigdata_thematic_screener.traces import TraceEventName, send_trace

BIGDATA: Bigdata | None = None


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
    yield


app = FastAPI(
    title="Thematic screener API",
    description="API for analyzing corporate exposure to specific themes and events using Bigdata.com",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": __version__}


@app.get("/")
async def sample_frontend():
    # Get example values from the schema for all fields
    example_values = get_example_values_from_schema(ThematicScreenRequest)

    return HTMLResponse(
        content=loader.get_template("api/frontend.html.jinja").render(**example_values)
    )


@app.post("/thematic-screener", response_model=ThematicScreenerResponse)
def screen_companies(request: Annotated[ThematicScreenRequest, Body()]):
    # While we improve the UX of working with several document types with different sets of parameters
    # we will limit the document type to transcripts
    DOCUMENT_TYPE = DocumentType.TRANSCRIPTS

    return process_request(
        companies=request.companies,
        llm_model=request.llm_model,
        theme=request.theme,
        focus=request.focus,
        start_date=request.start_date,
        end_date=request.end_date,
        document_type=DOCUMENT_TYPE,
        fiscal_year=request.fiscal_year,
        rerank_threshold=request.rerank_threshold,
        frequency=request.frequency,
        document_limit=request.document_limit,
        batch_size=request.batch_size,
        bigdata=BIGDATA,
    )
