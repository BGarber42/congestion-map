from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Congestion Map Settings
    default_h3_resolution: int = 12
    default_congestion_window: int = 30

    # Ping validation settings
    max_clock_skew_seconds: int = 15 * 60  # 15 m
    max_ping_age_seconds: int = 30 * 60  # 30 minutes
    queue_warnings_seconds: int = 60  # 1 minute

    # AWS Settings
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # SQS Settings
    sqs_endpoint_url: str | None = None
    sqs_queue_name: str = "pings-queue"
    max_pings: int = 10
    wait_time_seconds: int = 20

    # DynamoDB Settings
    dynamodb_endpoint_url: str | None = None
    dynamodb_table_name: str = "congestion-table"

    model_config = SettingsConfigDict(
        env_file=[
            ".env.test",
            ".env.dev",
            ".env",
        ],  # Load .env.test first, then .env (later files override earlier)
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
