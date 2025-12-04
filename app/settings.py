from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    default_h3_resolution: int = 12

    # AWS Settings
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    sqs_endpoint_url: str | None = None
    sqs_queue_name: str = "congestion-map-queue"

    model_config = SettingsConfigDict(
        env_file=[
            ".env.test",
            ".env",
        ],  # Load .env.test first, then .env (later files override earlier)
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
