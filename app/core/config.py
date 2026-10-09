from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://task_user:replace_me@localhost:5432/tasks_db"
    redis_url: str = ""
    cache_ttl_seconds: int = Field(default=30, ge=1)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

