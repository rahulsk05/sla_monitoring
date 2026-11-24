
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SLA Monitoring Dashboard API"
    app_env: str = "development"
    debug: bool = False

    database_url: str

    sla_threshold: float = 99.9
    csv_chunk_size: int = 5000

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
