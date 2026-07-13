from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    secret_key: str = "insecure-dev-secret-change-me"
    access_token_expire_minutes: int = 480
    algorithm: str = "HS256"

    database_url: str = "sqlite+aiosqlite:///./femas.db"
    evidence_storage_dir: str = "./evidence_store"

    agents_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    mcp_base_url: str = "http://127.0.0.1:8000"

    @property
    def evidence_storage_path(self) -> Path:
        path = Path(self.evidence_storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
