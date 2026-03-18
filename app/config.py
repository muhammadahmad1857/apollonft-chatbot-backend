from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Single key fallback (old style)
    google_api_key: str = ""
    # Comma-separated list — preferred. E.g.: GOOGLE_API_KEYS=key1,key2,key3
    google_api_keys: str = ""

    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str = "knowledge_base"
    groq_api_key: str
    model_name: str = "gemini-2.0-flash-exp"
    embed_model: str = "models/text-embedding-004"

    # NeonDB
    database_url: str

    # Pinata IPFS
    pinata_jwt: str = ""

    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent / ".env", extra="ignore")

    def parsed_api_keys(self) -> list[str]:
        """Return deduplicated list of Gemini API keys."""
        raw = self.google_api_keys or self.google_api_key
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        # deduplicate while preserving order
        seen: set[str] = set()
        unique = []
        for k in keys:
            if k not in seen:
                seen.add(k)
                unique.append(k)
        return unique


settings = Settings()

# Bootstrap the key rotator once at import time
from app.agent.key_rotator import KeyRotator  # noqa: E402

key_rotator = KeyRotator(settings.parsed_api_keys())
