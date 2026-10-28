from pathlib import Path
from sqlalchemy import URL
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        extra="ignore",
    )

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ecommerce"
    postgres_user: str
    postgres_password: SecretStr

    payments_url: str = "http://localhost:8001"
    payments_timeout_seconds: float = 2.0

    reconcile_processing_after_seconds: int = 30
    pending_order_ttl_minutes: int = 15
    idempotency_key_ttl_hours: int = 24

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
