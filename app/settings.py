from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    default_h3_resolution: int = 12

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
