from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App config, loaded from environment variables and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    pydantic_ai_gateway_api_key: SecretStr | None = None
    typesafe_api_key: SecretStr | None = None
    logfire_token: SecretStr | None = None

    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"


settings = Settings()
