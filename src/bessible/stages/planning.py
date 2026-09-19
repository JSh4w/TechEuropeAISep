"""Regulatory and planning consenting stage placeholder."""

from __future__ import annotations

from pydantic import HttpUrl

from bessible.models import Artifact, PlanningInput, PlanningOutput
from bessible.planning.route import consenting_route, lookup_lpa

DEFAULT_RISKS = [
    "Landscape and visual impact mitigation required for adjacent countryside",
    "Battery safety management plan required for fire authority approval",
    "Noise assessment required for night-time operation",
]


async def regulatory_planning(inp: PlanningInput) -> PlanningOutput:
    """Assess planning jurisdiction, consenting pathways, and statutory risk factors."""
    lpa = await lookup_lpa(inp.site.position)
    statement = consenting_route(lpa)

    if lpa:
        claim = f"{statement.route}. Authority: {lpa.name} ({lpa.reference}). {statement.note}"
        source_url = HttpUrl(lpa.source_url)
        confidence = 0.95
    else:
        claim = f"{statement.route}. Authority unknown. {statement.note}"
        source_url = HttpUrl("https://www.planning.data.gov.uk/dataset/local-planning-authority")
        confidence = 0.6

    art = Artifact(
        id=f"planning-{inp.run_id[:8]}",
        stage="planning",
        claim=claim,
        source_url=source_url,
        confidence=confidence,
        model_used="none (planning.data.gov.uk lookup)",
    )

    return PlanningOutput(
        consenting_route=f"{statement.route} - {lpa.name}" if lpa else statement.route,
        risks=list(DEFAULT_RISKS),
        artifacts=[art],
    )
