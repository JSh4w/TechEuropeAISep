"""Direct capacity check endpoint outside the Temporal workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter
from pydantic import BaseModel, model_validator

from bessible.models import CapacityOutput, Position
from bessible.stages.capacity import propose, propose_live
from bessible.ukpn.snapshot import get_snapshot

if TYPE_CHECKING:
    from typing import Any

router = APIRouter(tags=["capacity"])


class CapacityCheckRequest(BaseModel):
    """Payload for fast capacity check on map pin movement."""

    position: Position
    flexible: bool = False
    requested_mw: float | None = None
    battery_mw: float | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:  # ruff: ignore[any-type]
        """Normalize flexible_connection alias to flexible and battery_mw to requested_mw."""
        if isinstance(data, dict):
            data = dict(data)
            if "flexible_connection" in data and "flexible" not in data:
                data["flexible"] = data["flexible_connection"]
            if "battery_mw" in data and "requested_mw" not in data:
                data["requested_mw"] = data["battery_mw"]
            elif "target_mw" in data and "requested_mw" not in data:
                data["requested_mw"] = data["target_mw"]
        return data


@router.post("/capacity/check", response_model=CapacityOutput)
async def check_capacity(req: CapacityCheckRequest) -> CapacityOutput:
    """Run direct grid capacity proposal for a coordinate under 1 second."""
    snapshot = get_snapshot()
    mw = req.requested_mw if req.requested_mw is not None else req.battery_mw
    out = propose(req.position, snapshot, run_id="check", flexible=req.flexible, requested_mw=mw)
    if out.out_of_area:
        out = await propose_live(req.position, "check", fallback=out)
    return out
