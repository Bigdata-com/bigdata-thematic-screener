from bigdata_thematic_screener import LOG_LEVEL
from bigdata_thematic_screener.api.app import app
from bigdata_thematic_screener.settings import settings

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host=settings.HOST, port=settings.PORT, log_level=LOG_LEVEL.lower()
    )
