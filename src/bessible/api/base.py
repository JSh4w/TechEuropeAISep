"""Base models shared by every external API client."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, model_validator


class ApiRequest(BaseModel):
    """Input to an external API. Unknown params are a bug on our side, so forbid them."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def params(self) -> dict[str, Any]:
        """Query params / form body as the API expects them (aliases, no unset values)."""
        return self.model_dump(by_alias=True, exclude_none=True, mode="json")


class ApiResponse(BaseModel):
    """Output from an external API. We model every field, so an unknown one means our model is stale."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class NullMarkerResponse(ApiResponse):
    """An ApiResponse for APIs that write "no value" as text (``""``, ``"N/A"``...) instead of null.

    Those markers are read as None so that typed fields (dates, numbers) parse. This is the only
    normalisation the API models do; anything else belongs in the refined models built on top of them.
    """

    NULL_MARKERS: ClassVar[frozenset[str]] = frozenset({""})  # compared upper-cased and stripped

    @model_validator(mode="before")
    @classmethod
    def _null_markers(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        # Only marker strings are nulled; 0 / False / [] must survive.
        return {k: None if isinstance(v, str) and v.strip().upper() in cls.NULL_MARKERS else v for k, v in data.items()}
