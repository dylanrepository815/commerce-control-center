from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://cc_app@db/control_center"
    app_origin: str = "http://localhost:3000"
    cookie_secure: bool = False
    enable_fixtures: bool = False
    session_hours: int = 12
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def settings():
    return Settings()
