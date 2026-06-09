from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    voyage_api_key: str = ""
    anthropic_api_key: str = ""
    supabase_url: str = ""
    supabase_service_key: str = ""

    qdrant_collection: str = "nyvia_brain"
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    anthropic_model: str = "claude-sonnet-4-6"
    judge_model: str = "claude-haiku-4-5-20251001"
    embedding_model: str = "voyage-3-large"
    embedding_dim: int = 1024

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"


settings = Settings()
