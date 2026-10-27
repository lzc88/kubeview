from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        extra="ignore",
    )

    failure_rate: float = Field(default=0.2, ge=0, le=1)
    latency_ms: int = Field(default=0, ge=0)


settings = Settings()
