"""Typed classification on Modal (open-jev, see sandbox/modal_classifier.py), driven by Pydantic models.

Each field of the schema becomes one question: `Literal[...]` → pick one option, `bool` → yes/no.
The field description is the question. Every answer comes back with a calibrated confidence.

    class ParagraphLabels(BaseModel):
        kind: Literal["planning policy", "local news", "other"] = Field(description="What kind of text is this?")
        mentions_risk: bool = Field(description="The text mentions a risk for a battery storage project.")

    results = await classify(paragraphs, ParagraphLabels)
    results[0].labels.kind, results[0].confidence["kind"]
"""

from __future__ import annotations

from typing import Any, Literal, get_args, get_origin

import modal
from pydantic import BaseModel

MODAL_APP = "bessible-classifier"
MODEL_NAME = "open-jev-deberta-v3-large (Modal)"


class Classified[T: BaseModel](BaseModel):
    """One paragraph with its validated labels and a confidence (0-1) per field."""

    text: str
    labels: T
    confidence: dict[str, float]


def _questions(schema: type[BaseModel]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for name, field in schema.model_fields.items():
        instructions = field.description or name.replace("_", " ")
        if field.annotation is bool:
            questions.append({"type": "noul", "instructions": instructions})
        elif get_origin(field.annotation) is Literal:
            options = list(get_args(field.annotation))
            questions.append({"type": "choice", "instructions": instructions, "options": options})
        else:
            msg = f"{schema.__name__}.{name}: only Literal[...] and bool fields are supported"
            raise TypeError(msg)
    return questions


async def classify[T: BaseModel](paragraphs: list[str], schema: type[T]) -> list[Classified[T]]:
    """Ask every field of `schema` about every paragraph, on Modal."""
    classifier = modal.Cls.from_name(MODAL_APP, "Classifier")()
    raw = await classifier.classify.remote.aio(paragraphs, _questions(schema))

    results: list[Classified[T]] = []
    for text, answers in zip(paragraphs, raw, strict=True):
        values: dict[str, Any] = {}
        confidence: dict[str, float] = {}
        for name, answer in zip(schema.model_fields, answers, strict=True):
            if "noul" in answer:
                p_yes = answer["noul"]
                values[name], confidence[name] = p_yes >= 0.5, max(p_yes, 1 - p_yes)  # ruff: ignore[magic-value-comparison]
            else:
                values[name], confidence[name] = answer["choice"], answer["confidence"]
        results.append(Classified[T](text=text, labels=schema.model_validate(values), confidence=confidence))
    return results
