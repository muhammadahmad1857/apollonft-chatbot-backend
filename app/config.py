from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_api_key: str
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str = "knowledge_base"
    groq_api_key: str
    model_name: str = "gemini-2.0-flash-exp"
    embed_model: str = "models/text-embedding-004"

    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent / ".env", extra="ignore")


settings = Settings()

import os
os.environ["GOOGLE_API_KEY"] = settings.google_api_key
