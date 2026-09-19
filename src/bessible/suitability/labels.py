"""Classification schemas for local news and community sentiment."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ParagraphLabels(BaseModel):
    """Labels assigned to one paragraph by the typed classifier."""

    relevant: bool = Field(
        description="The text is about an energy project or infrastructure near a local community."
    )
    stance: Literal["against", "neutral", "supportive"] = Field(
        description="The text's attitude to the project."
    )
    concern: Literal[
        "fire safety", "noise", "visual impact", "traffic", "land use", "ecology", "other"
    ] = Field(description="The main concern raised.")
    mentions_risk: bool = Field(
        description="The text mentions a risk for a battery storage project."
    )
