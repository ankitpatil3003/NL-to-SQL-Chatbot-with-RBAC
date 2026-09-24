"""Application settings, loaded from environment variables (12-factor)."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    # Owner connection: app schema (chat, credentials, traces) and reading public.users.
    database_url: str = Field(
        default="postgresql+asyncpg://pharma:pharma_dev_pw@localhost:5433/pharma"
    )
    db_pool_size: int = 5
    db_connect_timeout_s: float = 5.0
    # Least-privilege logins that run LLM-generated SQL (db/20_rbac.sql). Same host/db as above.
    db_scoped_reader_password: str = "scoped_reader_dev_pw"
    db_exec_reader_password: str = "exec_reader_dev_pw"
    query_timeout_ms: int = 15_000
    query_row_limit: int = 1_000

    # --- LLM ---------------------------------------------------------------------------------
    # Comma-separated provider:model targets, tried in order (router.py). Per-task overrides:
    # LLM_CHAIN_SQL, LLM_CHAIN_ROUTER, LLM_CHAIN_REWRITE, LLM_CHAIN_ANSWER, LLM_CHAIN_TITLE.
    llm_chain: str = (
        "openrouter:nvidia/nemotron-3-super-120b-a12b:free,openrouter:qwen/qwen3.8-27b:free"
    )
    llm_chain_sql: str | None = None
    llm_chain_router: str | None = None
    llm_chain_rewrite: str | None = None
    llm_chain_answer: str | None = None
    llm_chain_title: str | None = None
    llm_timeout_s: float = 60.0
    openrouter_api_key: str | None = None
    anthropic_api_key: str | None = None
    public_url: str = "http://localhost:3000"

    jwt_secret: str = DEV_JWT_SECRET
    jwt_ttl_minutes: int = 720
    # When set, every user's login password is this value (bcrypt-hashed at startup).
    demo_password: str | None = None
    # Show demo accounts + password on the login page (graders test all roles quickly).
    demo_show_credentials: bool = True

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    def llm_task_chains(self) -> dict[str, str]:
        overrides = {
            "sql": self.llm_chain_sql,
            "router": self.llm_chain_router,
            "rewrite": self.llm_chain_rewrite,
            "answer": self.llm_chain_answer,
            "title": self.llm_chain_title,
        }
        return {task: chain for task, chain in overrides.items() if chain}

    def reader_url(self, role: str, password: str) -> str:
        url = make_url(self.database_url).set(username=role, password=password)
        return url.render_as_string(hide_password=False)

    @model_validator(mode="after")
    def _no_dev_secrets_outside_local(self) -> "Settings":
        if not self.is_local and (self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32):
            raise ValueError("JWT_SECRET must be a random value of 32+ chars outside local")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
