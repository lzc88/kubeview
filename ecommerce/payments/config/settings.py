from pathlib import Path
from typing import Self

from pydantic import SecretStr, model_validator
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

    pending_retry_after_seconds: int = 30
    checkout_create_deadline_seconds: int = 600

    orders_url: str = "http://localhost:8000"
    orders_timeout_seconds: float = 2.0

    stripe_api_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_currency: str = "sgd"
    stripe_success_url: str = "http://localhost:8080/orders/{order_id}"
    stripe_timeout_seconds: float = 5.0
    stripe_max_network_retries: int = 2
    stripe_checkout_expires_after_minutes: int = 60

    @model_validator(mode="after")
    def checkout_outlives_create_deadline(self) -> Self:
        if self.stripe_checkout_expires_after_minutes * 60 < (
            self.checkout_create_deadline_seconds + 31 * 60
        ):
            raise ValueError(
                "STRIPE_CHECKOUT_EXPIRES_AFTER_MINUTES must leave Stripe's 30 minute "
                "minimum after CHECKOUT_CREATE_DEADLINE_SECONDS"
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
