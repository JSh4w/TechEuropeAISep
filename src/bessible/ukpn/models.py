"""Data models for UKPN grid-level substations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, model_validator

from bessible.models import Position


def _extract_position(data: dict[str, Any]) -> dict[str, float] | None:
    """Extract latitude and longitude from various raw formats."""
    sc = data.get("spatial_coordinates")
    if isinstance(sc, dict) and "lat" in sc and "lon" in sc:
        return {"lat": sc["lat"], "lon": sc["lon"]}
    if "latitude" in data and "longitude" in data:
        return {"lat": data["latitude"], "lon": data["longitude"]}
    if "lat" in data and "lon" in data:
        return {"lat": data["lat"], "lon": data["lon"]}
    return None


def _extract_headroom(data: dict[str, Any]) -> tuple[float, float, float, float]:
    """Derive (headroom_import, headroom_export, firm_capacity, max_demand)."""
    trans = data.get("transratingsummer") or data.get("transrating_summer_mva")
    firm_mva = 0.0
    if isinstance(trans, str):
        parts = [float(p.strip()) for p in trans.split(",") if p.strip()]
        if parts:
            firm_mva = parts[0]
    elif isinstance(trans, (int, float)):
        firm_mva = float(trans)

    demand_summer = data.get("maxdemandsummer") or data.get("max_demand_mva") or 0.0
    demand_val = float(demand_summer) if isinstance(demand_summer, (int, float)) else 0.0

    imp = max(0.0, firm_mva - demand_val)
    exp = firm_mva
    return imp, exp, firm_mva, demand_val


class GridSubstation(BaseModel):
    """Grid-level substation (132 kV) with location and headroom figures."""

    id: str
    name: str
    position: Position
    voltage_kv: Literal[132] = 132
    headroom_import_mw: float
    headroom_export_mw: float
    site_type: str = "Grid Substation"
    licence_area: str | None = None
    gsp: str | None = None
    bsp: str | None = None
    max_demand_mva: float | None = None
    firm_capacity_mva: float | None = None

    @model_validator(mode="before")
    @classmethod
    def from_api_row(cls, data: Any) -> Any:  # ruff: ignore[any-type]
        """Normalize field names and compute headroom if missing."""
        if not isinstance(data, dict):
            return data
        res = dict(data)
        if "id" not in res and "sitefunctionallocation" in res:
            res["id"] = res["sitefunctionallocation"]
        if "name" not in res and "sitename" in res:
            res["name"] = res["sitename"]
        if "licence_area" not in res and "licencearea" in res:
            res["licence_area"] = res["licencearea"]
        if "site_type" not in res and "sitetype" in res:
            res["site_type"] = res["sitetype"]

        if "position" not in res:
            pos = _extract_position(res)
            if pos:
                res["position"] = pos

        if "headroom_import_mw" not in res or "headroom_export_mw" not in res:
            imp, exp, firm, dem = _extract_headroom(res)
            res.setdefault("headroom_import_mw", imp)
            res.setdefault("headroom_export_mw", exp)
            res.setdefault("firm_capacity_mva", firm)
            res.setdefault("max_demand_mva", dem)

        return res


class GspQueue(BaseModel):
    """Parent Grid Supply Point queue figures."""

    projects: int
    total_mw: float
    by_status: dict[str, int]
    next_position: int


class Timescales(BaseModel):
    """Indicative connection timescales from past outcome records."""

    p25_months: float
    p75_months: float
    median_months: float
    records: int
    low_confidence: bool


class GspProjectStatusRecord(BaseModel):
    """Row of UKPN GSP Project Status or connection queue / outcome record."""

    gsp: str
    technology_type: str | None = None
    measure: str | None = None  # "MW" or "#"
    sortby: str | None = None
    gate_2_protected_26_27: float | None = None
    gate_2_phase_1: float | None = None
    gate_2_phase_2: float | None = None
    gate_1: float | None = None
    has_not_undergone_gated_process: float | None = None

    # Outcome / timescales fields
    application_date: Any = None
    offer_date: Any = None
    energisation_date: Any = None
    months: float | None = None
    status: str | None = None
    mw: float | None = None


class Competition(BaseModel):
    """Substation competition from offers not accepted, budget estimates, and enquiries."""

    offers_not_accepted_mw: float
    budget_estimates_mw: float
    enquiries_mw: float
    weighted_mw: float
    pressure: Literal["low", "medium", "high"]


class Table6InterestRecord(BaseModel):
    """Row of LTDS Table 6: New Connection Interest."""

    gridsupplypoint: str | None = None
    substation: str | None = None
    proposed_connection_voltage_kv: str | None = None
    status_of_connection: str | None = None
    demand_numbers_received_total_number: float | None = None
    demand_numbers_received_total_capacity: float | None = None
    generation_numbers_received_total_number: float | None = None
    generation_numbers_received_total_capacity: float | None = None
    spatial_coordinates: dict[str, float] | None = None
    sitefunctionallocation: str | None = None
    licencearea: str | None = None
    id: int | None = None


class Table2aTransformerRecord(BaseModel):
    """Row of LTDS Table 2a: Transformer Data (2-Winding)."""

    gridsupplypoint: str | None = None
    hv_node: str | None = None
    hv_substation: str | None = None
    voltage_hv: float | None = None
    lv_node: str | None = None
    lv_substation: str | None = None
    voltage_lv: float | None = None
    vector_group: str | None = None
    positive_sequence_impedance_r_percent: float | None = None
    positive_sequence_impedance_x_percent: float | None = None
    zero_sequence_impedance_x_percent: float | None = None
    tap_range_max_percent: float | None = None
    tap_range_min_percent: float | None = None
    transformer_rating_mva_winter: float | None = None
    transformer_rating_mva_summer: float | None = None
    reverse_power_capability_percent: str | float | None = None
    method_of_earthing_hv: str | None = None
    method_of_earthing_lv: str | None = None
    sitefunctionallocation: str | None = None
    licencearea: str | None = None
    id: int | None = None
