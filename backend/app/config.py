from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-exp"
    lobster_trap_url: str = "http://localhost:8080"
    lobster_trap_backend: str = "https://generativelanguage.googleapis.com"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
