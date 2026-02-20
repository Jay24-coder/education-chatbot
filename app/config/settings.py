"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_env: str = "development"
    port: int = 8000

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/education"

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
