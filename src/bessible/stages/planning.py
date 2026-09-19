"""Regulatory and planning consenting stage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import HttpUrl

from bessible.models import Artifact, PlanningInput, PlanningOutput
from bessible.planning.route import consenting_route, lookup_lpa
from bessible.planning.tia import tia_statement

if TYPE_CHECKING:
    from bessible.models import SiteLandOutput

DEFAULT_RISKS = [
    "Landscape and visual impact mitigation required for adjacent countryside",
    "Battery safety management plan required for fire authority approval",
    "Noise assessment required for night-time operation",
]


def derive_planning_risks(site_land: SiteLandOutput, planning_art_id: str) -> list[str]:
    """Derive planning risks citing evidence artifacts from site_land and planning."""
    risks: list[str] = []
    land_art_id = site_land.artifacts[0].id if site_land.artifacts else None

    # Risks derived from site land constraints
    for constraint in site_land.constraints:
        c_lower = constraint.lower()
        if "green belt" in c_lower:
            risk = "Green Belt designation: very special circumstances justification required"
        elif "flood" in c_lower and "low" not in c_lower and "zone 1" not in c_lower:
            risk = "Flood risk: sequential and exception tests required"
        elif "sssi" in c_lower and "no sssi" not in c_lower:
            risk = "Ecological designation: SSSI impact assessment required"
        elif "ancient woodland" in c_lower:
            risk = "Ancient woodland: minimum buffer zone required"
        elif "listed building" in c_lower or "heritage" in c_lower:
            risk = "Heritage asset: setting impact assessment required"
        elif "aonb" in c_lower or "national park" in c_lower:
            risk = "Landscape designation: major development test applies"
        else:
            continue

        if land_art_id:
            risks.append(f"{risk} [{land_art_id}]")
        else:
            risks.append(risk)

    # Standard statutory planning risks citing the planning stage artifact
    risks.extend(f"{default_risk} [{planning_art_id}]" for default_risk in DEFAULT_RISKS)

    return risks


async def regulatory_planning(inp: PlanningInput) -> PlanningOutput:
    """Assess planning jurisdiction, consenting pathways, and statutory risk factors."""
    lpa = await lookup_lpa(inp.site.position)
    statement = consenting_route(lpa, mw=inp.site.capacity_mw)

    if lpa and lpa.country != "England":
        claim = f"{statement.route}. Site in {lpa.country} ({lpa.name}). {statement.note}"
        source_url = HttpUrl(lpa.source_url)
        confidence = 0.95
        route_display = f"{statement.route} ({lpa.country})"
    elif lpa:
        claim = f"{statement.route}. Authority: {lpa.name} ({lpa.reference}). {statement.note}"
        source_url = HttpUrl(lpa.source_url)
        confidence = 0.95
        route_display = f"{statement.route} - {lpa.name}"
    else:
        claim = f"{statement.route}. Authority unknown. {statement.note}"
        source_url = HttpUrl("https://www.planning.data.gov.uk/dataset/local-planning-authority")
        confidence = 0.6
        route_display = statement.route

    planning_art = Artifact(
        id=f"planning-{inp.run_id[:8]}",
        stage="planning",
        claim=claim,
        source_url=source_url,
        confidence=confidence,
        model_used="none (planning.data.gov.uk lookup)",
    )

    risks = derive_planning_risks(inp.site_land, planning_art.id)

    # F2: Transmission Impact Assessment
    threshold = inp.capacity.tia_threshold_mw if inp.capacity else None
    capacity_mw = inp.site.capacity_mw
    tia = tia_statement(threshold, capacity_mw)
    tia_art = Artifact(
        id=f"planning-tia-{inp.run_id[:8]}",
        stage="planning",
        claim=tia.statement,
        source_url=tia.source_url,
        confidence=0.95 if tia.threshold_mw is not None else 0.5,
        model_used="none (deterministic rule)",
    )

    return PlanningOutput(
        consenting_route=route_display,
        risks=risks,
        artifacts=[planning_art, tia_art],
        tia=tia,
    )
