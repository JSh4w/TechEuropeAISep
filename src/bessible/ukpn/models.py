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
