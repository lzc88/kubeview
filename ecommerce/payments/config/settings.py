from pathlib import Path

from pydantic import SecretStr
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

    orders_url: str = "http://localhost:8000"
    orders_timeout_seconds: float = 2.0

    stripe_api_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_currency: str = "sgd"
    stripe_success_url: str = "http://localhost:8000/orders/{order_id}"
    stripe_timeout_seconds: float = 10.0

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
