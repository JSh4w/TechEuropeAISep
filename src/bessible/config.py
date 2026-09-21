"""App configuration and settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App config, loaded from environment variables and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    google_api_key: SecretStr | None = None  # the developer's own key: CLI and scripts only, never a fallback for a run
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
    spen_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("spen_api_key", "sp_energy_api_key")
    )  # spenergynetworks.opendatasoft.com
    os_api_key: SecretStr | None = None  # osdatahub.os.uk (Ordnance Survey maps)

    data_dir: Path = Path(__file__).resolve().parents[2] / "data"  # committed fixtures and UKPN snapshot

    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"

    # Demo deployment: Firebase sign-in and encrypted per-user Google keys.
    firebase_project_id: str | None = None
    allowed_emails: str | None = None  # comma-separated; empty means anyone who signs in
    key_encryption_secret: SecretStr | None = None  # master secret; root-owned EnvironmentFile on the VM
    key_encryption_key_id: str = "k1"  # id stamped on new ciphertexts
    key_encryption_previous: dict[str, SecretStr] = {}  # old key_id -> secret, kept while rotating
    key_db_path: Path = Path("/var/lib/bessible/keys.db")


settings = Settings()
