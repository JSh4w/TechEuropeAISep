from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr
from pydantic_ai.models.function import AgentInfo, FunctionModel
from temporalio import activity

from bessible.config import settings
from bessible.credentials import encrypt_google_key
from bessible.planning.route import LpaLookup

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic_ai.messages import ModelMessage, ModelResponse

    from bessible.models import EncryptedCredentials


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse] - every stage test must stay offline
def offline_lpa_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep stage tests off the network; route tests exercise lookup_lpa with a mock transport."""

    async def fake(*_args: object, **_kwargs: object) -> LpaLookup:
        return LpaLookup(entity=626002, reference="E60000002", name="Darlington LPA")

    monkeypatch.setattr("bessible.stages.planning.lookup_lpa", fake)


class FakeGemini:
    """Stands in for `bessible.llm.gemini_model`: no network, and it records which key built each model."""

    def __init__(self) -> None:
        self.built: list[tuple[str | None, str]] = []  # (workflow id, api key), one per model built

    def __call__(self, api_key: str) -> FunctionModel:
        try:
            workflow_id: str | None = activity.info().workflow_id
        except RuntimeError:  # called outside an activity
            workflow_id = None
        self.built.append((workflow_id, api_key))

        def offline(_messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
            msg = "offline"
            raise RuntimeError(msg)  # every agent then takes its deterministic fallback

        return FunctionModel(offline)


@pytest.fixture
def fake_gemini(monkeypatch: pytest.MonkeyPatch) -> FakeGemini:
    fake = FakeGemini()
    monkeypatch.setattr("bessible.llm.gemini_model", fake)
    return fake


@pytest.fixture
def seal(monkeypatch: pytest.MonkeyPatch) -> Callable[[str, str], EncryptedCredentials]:
    """`seal(uid, api_key)` with a test master secret, as the API would."""
    monkeypatch.setattr(settings, "key_encryption_secret", SecretStr("test-master-secret"))
    return encrypt_google_key


@pytest.fixture
def run_credentials(seal: Callable[[str, str], EncryptedCredentials]) -> EncryptedCredentials:
    return seal("test-user", "test-google-key")
