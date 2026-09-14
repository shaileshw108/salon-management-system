from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Salon Queue"
    environment: str = "development"
    debug: bool = False
    database_url: str = "postgresql+psycopg://salon:salon@localhost:5432/salon_queue"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:8081,http://127.0.0.1:8081"

    # Notifications
    sms_provider: str = "mock"
    sms_near_turn_threshold: int = 2
    msg91_authkey: str = ""
    msg91_flow_id: str = ""
    msg91_sender_id: str = ""
    msg91_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
