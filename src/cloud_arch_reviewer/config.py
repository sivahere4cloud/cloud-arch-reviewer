from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: SecretStr
    openai_model: str = "gpt-6-luna"
    log_level: str = "INFO"
    request_timeout_seconds: float = 60.0
    max_retries: int = 3
    max_image_mb: int = 5


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    return settings 