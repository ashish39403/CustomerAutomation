from functools import lru_cache
from urllib.parse import urlparse, urlunparse

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_secret_key: str = "dev-insecure-change-me"

    database_url: str
    database_url_direct: str | None = None

    qdrant_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("QDRANT_URL", "QDRANT_CLUSTER_ENDPOINT"),
    )
    qdrant_api_key: str | None = None
    qdrant_collection: str = "knowledge_base"
    qdrant_vector_size: int = 1536

    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    llm_model: str | None = None
    embedding_model: str | None = None

    anthropic_api_key: str | None = None
    anthropic_base_url: str | None = None
    classifier_model: str = "gpt-4o-mini"
    agent_model: str = "anthropic/claude-haiku-5.5"

    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "customerautomation"

    aws_endpoint_url_s3: str | None = None
    aws_region: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    neon_storage_bucket: str | None = "knowledgebase"

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    google_refresh_token: str | None = None
    google_token_encryption_key: str | None = None
    google_api_key: str | None = None
    google_project_id: str | None = None

    gmail_poll_interval_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "GMAIL_POLL_INTERVAL_SECONDS",
            "POLL_INTERVAL_SECONDS",
        ),
    )
    job_poll_interval_seconds: int = 2
    job_lease_seconds: int = 60
    gmail_backfill_max: int = 25
    gmail_excluded_senders: str = ""
    # Run the jobs worker (which drives the Gmail poller) inside the API
    # process, so `fastapi dev app/main.py` alone starts the whole system.
    # Tests turn this off (see tests/conftest.py) to avoid hitting Gmail.
    worker_in_process: bool = True

    cors_origins: str = "http://localhost:5173"

    dashboard_username: str = Field(
        default="admin",
        validation_alias=AliasChoices("DASHBOARD_USERNAME", "EMAIL"),
    )
    dashboard_admin_email: str = "admin@local"
    dashboard_password: str = Field(
        validation_alias=AliasChoices("DASHBOARD_PASSWORD", "PASSWORD"),
    )
    seed_operator_email: str = "operator@local"
    seed_operator_password: str = "operator1234@@@"

    knowledge_chunk_characters: int = 2800
    knowledge_chunk_overlap: int = 400
    knowledge_docs_dir: str = "knowledge_docs"
    upload_dir: str = "data/uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    retrieval_k: int = 6
    auto_send_enabled: bool = True
    auto_send_min_confidence: float = 0.45

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().strip('"').strip("'")
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def admin_email(self) -> str:
        if "@" in self.dashboard_admin_email:
            return self.dashboard_admin_email
        return f"{self.dashboard_username}@local"

    @property
    def excluded_sender_set(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.gmail_excluded_senders.split(",")
            if item.strip()
        }

    @property
    def llm_api_key(self) -> str:
        return self.openai_api_key or self.anthropic_api_key or ""

    @property
    def llm_base_url(self) -> str | None:
        return self.openai_base_url or self.anthropic_base_url

    @property
    def embedding_model_name(self) -> str:
        return self.embedding_model or self.openai_embedding_model

    @property
    def chat_model_name(self) -> str:
        return self.llm_model or self.classifier_model

    @property
    def sqlalchemy_database_url(self) -> str:
        return _as_sqlalchemy_url(self.database_url)

    @property
    def sqlalchemy_direct_url(self) -> str:
        raw = self.database_url_direct or _without_neon_pooler(self.database_url)
        return _as_sqlalchemy_url(raw)


def _as_sqlalchemy_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    return url


def _without_neon_pooler(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if "-pooler." in host:
        host = host.replace("-pooler.", ".", 1)
        netloc = host
        if parsed.port:
            netloc = f"{host}:{parsed.port}"
        if parsed.username:
            user = parsed.username
            if parsed.password:
                user = f"{user}:{parsed.password}"
            netloc = f"{user}@{netloc}"
        return urlunparse(parsed._replace(netloc=netloc))
    return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
