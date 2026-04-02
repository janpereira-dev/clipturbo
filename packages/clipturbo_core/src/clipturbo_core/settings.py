from pydantic import BaseModel

from clipturbo_core.version import APP_NAME, APP_VERSION


class AppSettings(BaseModel):
    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    environment: str = "local"
