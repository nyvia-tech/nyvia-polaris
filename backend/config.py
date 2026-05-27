from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    supabase_url: str = ""
    supabase_service_key: str = ""

    qdrant_collection: str = "nyvia_brain"
    qdrant_url: str = ""        # Qdrant Cloud URL (producción)
    qdrant_api_key: str = ""    # Qdrant Cloud API key (producción)

    openai_model: str = "gpt-4o"
    judge_model: str = "gpt-5.2"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"


settings = Settings()
