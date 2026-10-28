from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        extra="ignore",
    )

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "payments"
    postgres_user: str
    postgres_password: SecretStr

    provider: Literal["fake", "stripe"] = "fake"
    pending_retry_after_seconds: int = 30

    failure_rate: float = Field(default=0.2, ge=0, le=1)
    latency_ms: int = Field(default=0, ge=0)

    orders_url: str = "http://localhost:8000"
    orders_timeout_seconds: float = 2.0

    stripe_api_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_currency: str = "sgd"
    stripe_success_url: str = "http://localhost:8000/orders/{order_id}"
    stripe_timeout_seconds: float = 10.0

    @model_validator(mode="after")
    def stripe_needs_secrets(self) -> Self:
        if self.provider == "stripe" and (
            self.stripe_api_key is None or self.stripe_webhook_secret is None
        ):
            raise ValueError(
                "STRIPE_API_KEY and STRIPE_WEBHOOK_SECRET are required when PROVIDER=stripe"
            )
        return self

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


settings = Settings()  # pyright: ignore[reportCallIssue]
