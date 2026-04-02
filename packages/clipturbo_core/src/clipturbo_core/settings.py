from pydantic import BaseModel


class AppSettings(BaseModel):
    app_name: str = "clipturbo-api"
    app_version: str = "0.1.0"
    environment: str = "local"
