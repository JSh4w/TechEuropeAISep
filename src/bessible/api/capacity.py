"""Direct capacity check endpoint outside the Temporal workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter
from pydantic import BaseModel, model_validator

from bessible.models import CapacityOutput, Position
from bessible.stages.capacity import propose
from bessible.ukpn.snapshot import get_snapshot

if TYPE_CHECKING:
    from typing import Any

router = APIRouter(tags=["capacity"])


class CapacityCheckRequest(BaseModel):
    """Payload for fast capacity check on map pin movement."""

    position: Position
    flexible: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:  # ruff: ignore[any-type]
        """Normalize flexible_connection alias to flexible."""
        if isinstance(data, dict):
            data = dict(data)
            if "flexible_connection" in data and "flexible" not in data:
                data["flexible"] = data["flexible_connection"]
        return data


@router.post("/capacity/check", response_model=CapacityOutput)
async def check_capacity(req: CapacityCheckRequest) -> CapacityOutput:
    """Run direct grid capacity proposal for a coordinate under 1 second."""
    snapshot = get_snapshot()
    return propose(req.position, snapshot, run_id="check", flexible=req.flexible)
