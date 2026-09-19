"""App configuration and settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App config, loaded from environment variables and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    google_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"

    pydantic_ai_gateway_api_key: SecretStr | None = None
    pydantic_ai_gateway_base_url: str = "https://gateway-eu.pydantic.dev/proxy"
    modal_gateway_route: str = "modal"
    modal_model: str = "google/gemma-4-31B-it"

    logfire_token: SecretStr | None = None
    typesafe_api_key: SecretStr | None = None
    ukpn_api_key: SecretStr | None = None  # ukpowernetworks.opendatasoft.com
    ssen_api_key: SecretStr | None = None  # ssentransmission.opendatasoft.com
    nged_api_key: SecretStr | None = None  # connecteddata.nationalgrid.co.uk
    os_api_key: SecretStr | None = None  # osdatahub.os.uk (Ordnance Survey maps)

    data_dir: Path = Path(__file__).resolve().parents[2] / "data"  # committed fixtures and UKPN snapshot

    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"


settings = Settings()
