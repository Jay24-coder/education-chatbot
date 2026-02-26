"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_env: str = "development"
    port: int = 8000

    # General environment / workers
    env: str = "local"
    worker_concurrency: int = 1

    # Queues
    queue_code_execution: str = "code_execution"
    queue_topic_search: str = "topic_search"

    # Context store mode: "memory" or "persistent"
    context_store_mode: str = "memory"

    # Database (legacy single URL – still supported)
    database_url: str = "postgresql://user:password@localhost:5432/education"

    # Postgres (preferred granular config)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "education"
    postgres_user: str = "user"
    postgres_password: str = "password"
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db_cache: int = 0
    redis_db_queues: int = 1
    redis_pool_max_size: int = 10

    # Vector store (optional for Phase 1)
    vector_db_url: str = ""
    vector_index_name: str = ""

    # LLM
    llm_provider: str = "openai"
    llm_api_key: str = ""
    model_id: str = "gpt-4o-mini"

    # Storage (optional)
    storage_bucket: str = ""
    cdn_base_url: str = ""

    # Auth
    auth_secret: str = ""
    jwt_secret: str = ""  # alternative to auth_secret

    # Observability
    telemetry_endpoint: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
