"""Application settings, loaded from environment variables (12-factor)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+asyncpg://pharma:pharma_dev_pw@localhost:5433/pharma"
    )
    db_pool_size: int = 5
    db_connect_timeout_s: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
