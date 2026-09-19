"""Transmission Impact Assessment (TIA) statement based on substation threshold."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import HttpUrl

from bessible.models import TiaStatement

if TYPE_CHECKING:
    from datetime import date

TIA_DATASET_URL = "https://ukpowernetworks.opendatasoft.com/explore/dataset/ukpn-capacity-heatmap/"


def tia_statement(
    threshold_mw: Literal[1, 5] | None,
    capacity_mw: float,
    snapshot_date: date | None = None,
) -> TiaStatement:
    """Evaluate whether a TIA is triggered given the capacity and substation threshold."""
    if threshold_mw is None:
        statement = "Transmission Impact Assessment (TIA) threshold is unknown for the serving substation."
        return TiaStatement(
            threshold_mw=None,
            triggered=None,
            statement=statement,
            source_url=HttpUrl(TIA_DATASET_URL),
            snapshot_date=snapshot_date,
        )

    triggered = capacity_mw >= threshold_mw
    date_str = f" dated {snapshot_date.isoformat()}" if snapshot_date else ""
    if triggered:
        statement = (
            f"Transmission Impact Assessment (TIA) triggered: confirmed capacity ({capacity_mw:g} MW) "
            f"is at or above the serving substation's {threshold_mw} MW threshold (from UKPN capacity snapshot"
            f"{date_str}). NESO involvement and Gate 2 timescales apply."
        )
    else:
        statement = (
            f"Transmission Impact Assessment (TIA) not triggered: confirmed capacity ({capacity_mw:g} MW) "
            f"is below the serving substation's {threshold_mw} MW threshold (from UKPN capacity snapshot"
            f"{date_str})."
        )

    return TiaStatement(
        threshold_mw=threshold_mw,
        triggered=triggered,
        statement=statement,
        source_url=HttpUrl(TIA_DATASET_URL),
        snapshot_date=snapshot_date,
    )
