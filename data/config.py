"""
config.py — Central settings loaded from environment variables.
Uses pydantic-settings so all values are validated at startup.
"""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── Database ──────────────────────────────────────────────────────────────
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "algotrading"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        password = f":{self.postgres_password}" if self.postgres_password else ""
        return (
            f"postgresql+asyncpg://{self.postgres_user}{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        password = f":{self.postgres_password}" if self.postgres_password else ""
        return (
            f"postgresql+psycopg2://{self.postgres_user}{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}" if self.redis_password else ""
        return f"redis://{auth}@{self.redis_host}:{self.redis_port}/0"

    # ── Data Feed ─────────────────────────────────────────────────────────────
    alpha_vantage_api_key: str = "MQSUV0FTMN01488L"
    twelve_data_api_key: str = "88fb723afb3749b0b001d244ab1309f4"

    # ── Broker ────────────────────────────────────────────────────────────────
    zerodha_api_key: str = ""
    zerodha_api_secret: str = ""
    zerodha_user_id: str = ""
    upstox_api_key: str = ""
    upstox_api_secret: str = ""

    # ── Alerting ──────────────────────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    sendgrid_api_key: str = ""
    alert_email: str = ""

    # ── MLflow ────────────────────────────────────────────────────────────────
    mlflow_tracking_uri: str = "http://localhost:5000"

    # ── Trading System ────────────────────────────────────────────────────────
    environment: str = "development"  # development | paper | live
    log_level: str = "INFO"
    feature_version: str = "v1.0.0"

    # Risk parameters
    max_daily_loss_pct: float = 2.0       # halt if daily loss > 2%
    max_drawdown_pct: float = 10.0        # halt if drawdown > 10%
    max_position_pct: float = 10.0        # max 10% capital per stock
    max_sector_pct: float = 25.0          # max 25% per sector
    signal_confidence_threshold: float = 0.65  # minimum confidence to execute
    india_vix_pause_threshold: float = 25.0    # reduce sizing above this VIX
    india_vix_halt_threshold: float = 30.0     # halt new entries above this VIX
    min_adv_crore: float = 5.0            # min avg daily value in crores (liquidity)

    @property
    def is_paper(self) -> bool:
        return self.environment == "paper"

    @property
    def is_live(self) -> bool:
        return self.environment == "live"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
