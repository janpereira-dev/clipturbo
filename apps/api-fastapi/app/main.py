from fastapi import FastAPI

from clipturbo_core.version import APP_NAME, APP_VERSION


def create_app() -> FastAPI:
    app = FastAPI(title=APP_NAME, version=APP_VERSION)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": APP_NAME, "version": APP_VERSION}

    return app


app = create_app()
