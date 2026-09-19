"""Suitability assumptions loader: low/mid/high ranges with provenance."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
FINANCE_PATH = DATA_DIR / "assumptions" / "finance.json"

REQUIRED_KEYS = (
    "battery_gbp_per_mwh",
    "balance_of_plant_gbp_per_mw",
    "opex_gbp_per_mw_year",
    "revenue_2h_gbp_per_mw_year",
    "revenue_4h_gbp_per_mw_year",
    "revenue_8h_gbp_per_mw_year",
    "cable_33kv_gbp_per_km",
    "availability_pct",
    "curtailment_haircut",
    "debt_share_pct",
    "interest_rate_pct",
    "arrangement_fee_pct",
    "discount_rate_pct",
    "loan_term_years",
    "project_life_years",
    "hurdle_irr_pct",
    "opposition_threshold_maybe",
    "opposition_threshold_no",
)


class Range(BaseModel):
    """Low, mid, high range for financial assumptions and outputs."""

    low: float
    mid: float
    high: float


class Assumption(BaseModel):
    """One documented assumption with a range, unit, source and date."""

    value: Range
    unit: str
    source: str
    date: date


class FinanceAssumptions(BaseModel):
    """Validated finance assumptions table."""

    entries: dict[str, Assumption] = Field(default_factory=dict)

    def get(self, key: str) -> Assumption:
        """Get an assumption entry by key, raising KeyError naming the key if absent."""
        if key not in self.entries:
            msg = f"Missing assumption: {key}"
            raise KeyError(msg)
        return self.entries[key]

    def range(self, key: str) -> Range:
        """Get the Range value for a key."""
        return self.get(key).value


def load_finance_assumptions(path: Path = FINANCE_PATH) -> FinanceAssumptions:
    """Load and validate finance assumptions from JSON.

    Fails with KeyError naming the missing key if any required key is absent.
    """
    if not path.exists():
        msg = f"Assumptions file not found: {path}"
        raise FileNotFoundError(msg)

    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    # Check for required keys
    for key in REQUIRED_KEYS:
        if key not in raw:
            msg = f"Missing assumption: {key}"
            raise KeyError(msg)

    entries: dict[str, Assumption] = {}
    for key, item in raw.items():
        if not isinstance(item, dict):
            continue
        # Check if low, mid, high are present
        if "low" in item and "mid" in item and "high" in item:
            r = Range(low=float(item["low"]), mid=float(item["mid"]), high=float(item["high"]))
        elif "value" in item and isinstance(item["value"], list) and len(item["value"]) == 2:
            low, high = float(item["value"][0]), float(item["value"][1])
            r = Range(low=low, mid=(low + high) / 2, high=high)
        elif "value" in item and isinstance(item["value"], int | float):
            v = float(item["value"])
            r = Range(low=v, mid=v, high=v)
        else:
            continue

        raw_date = item.get("date", "2026-09-19")
        parsed_date = date.fromisoformat(raw_date) if isinstance(raw_date, str) else raw_date
        entries[key] = Assumption(
            value=r,
            unit=item.get("unit", ""),
            source=item.get("source", ""),
            date=parsed_date,
        )

    # Double check all required keys parsed successfully
    for key in REQUIRED_KEYS:
        if key not in entries:
            msg = f"Missing assumption: {key}"
            raise KeyError(msg)

    return FinanceAssumptions(entries=entries)
