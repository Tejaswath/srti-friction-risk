from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    trafikverket_api_key: str
    admin_token: str = "default-dev-token"
    allowed_origins: str = "http://localhost:3000"
    cache_ttl_seconds: int = 600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
