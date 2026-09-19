"""Model factories. Keys come from `settings` (.env), not the process environment."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import logfire
from openai.types.chat import ChatCompletion
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel, _ChatCompletion  # ruff: ignore[import-private-name]
from pydantic_ai.providers.gateway import gateway_provider
from pydantic_ai.providers.google import GoogleProvider

from bessible.config import settings

if TYPE_CHECKING:
    from pydantic import SecretStr

# Modal returns `metadata.weight_versions` as a list, but the OpenAI schema types
# `metadata` as `dict[str, str]`. Widen it on both models that see the payload.
for _model in (ChatCompletion, _ChatCompletion):
    _model.model_fields["metadata"].annotation = dict[str, Any] | None
    _model.model_rebuild(force=True)


def _secret(value: SecretStr | None, name: str) -> str:
    if value is None:
        msg = f"{name} is not set in .env"
        raise RuntimeError(msg)
    return value.get_secret_value()


def setup_logfire() -> None:
    """Trace agent runs to Logfire if LOGFIRE_TOKEN is set; otherwise do nothing."""
    try:
        token = settings.logfire_token.get_secret_value() if settings.logfire_token else None
        logfire.configure(token=token, send_to_logfire="if-token-present", console=False)
        logfire.instrument_pydantic_ai()
    except Exception as exc:  # ruff: ignore[blind-except]
        logging.getLogger(__name__).warning("Logfire setup failed; continuing without Logfire: %s", exc)


def gemini_model() -> GoogleModel:
    """Gemini, called directly with the DeepMind API key. For reasoning calls."""
    return GoogleModel(
        settings.gemini_model, provider=GoogleProvider(api_key=_secret(settings.google_api_key, "GOOGLE_API_KEY"))
    )


def modal_model() -> OpenAIChatModel:
    """Our open-weight model on Modal, routed through the Pydantic AI Gateway."""
    provider = gateway_provider(
        "openai-chat",
        route=settings.modal_gateway_route,
        api_key=_secret(settings.pydantic_ai_gateway_api_key, "PYDANTIC_AI_GATEWAY_API_KEY"),
        base_url=settings.pydantic_ai_gateway_base_url,
    )
    return OpenAIChatModel(settings.modal_model, provider=provider)
