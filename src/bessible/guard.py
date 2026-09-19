"""Narration guard: validates numbers in generated text against typed run state."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

TOLERANCE = 0.05

# Pattern matching numbers with optional magnitude (m, k, bn) and units (%, £, MW, MWh, km, months, years):
# e.g., £1.2m, £500,000, 14%, 20 MW, 40 MWh, 1.5 km, 12 months, 25 years
_NUMBER_RE = re.compile(
    r"(?:£\s*)?(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:(m|k|bn)(?![a-z]))?\s*(%|£|MW|MWh|km|months?|years?)?",
    re.IGNORECASE,
)


def _parse_number_match(match: re.Match[str]) -> tuple[float, str]:
    num_str = match.group(1).replace(",", "")
    val = float(num_str)
    mult = (match.group(2) or "").lower()
    if mult == "m":
        val *= 1_000_000
    elif mult == "k":
        val *= 1_000
    elif mult == "bn":
        val *= 1_000_000_000

    unit = (match.group(3) or "").lower()
    return val, unit


def _is_close(val: float, target: float, unit: str) -> bool:
    """Check if val is within 5% relative tolerance of target."""
    denom = max(abs(target), 1e-5)
    if abs(val - target) / denom <= TOLERANCE:
        return True
    # If unit is %, also check target * 100 or target / 100 (e.g. 0.13 vs 13%)
    if unit == "%":
        if abs(val - target * 100) / max(abs(target * 100), 1e-5) <= TOLERANCE:
            return True
        if abs(val / 100 - target) / max(abs(target), 1e-5) <= TOLERANCE:
            return True
    return False


def check_narration(text: str, state: dict[str, float]) -> list[str]:
    """Return unmatched numbers from text against state values. Empty list means pass."""
    targets = list(state.values())
    unmatched: list[str] = []

    for match in _NUMBER_RE.finditer(text):
        raw_text = match.group(0).strip()
        try:
            val, unit = _parse_number_match(match)
        except ValueError:
            continue

        matched = any(_is_close(val, t, unit) for t in targets)
        if not matched:
            unmatched.append(raw_text)

    return unmatched


async def guarded(
    narrate: Callable[[str | None], Awaitable[str]],
    state: dict[str, float],
    template: str,
    max_retries: int = 2,
) -> str:
    """Run a narration callback guarded against invented numbers, falling back to template."""
    prompt_hint: str | None = None
    for _ in range(max_retries + 1):
        text = await narrate(prompt_hint)
        unmatched = check_narration(text, state)
        if not unmatched:
            return text
        bad_nums = ", ".join(unmatched)
        prompt_hint = f"The following numbers did not match run state: {bad_nums}. Use only values from run state."

    return template
