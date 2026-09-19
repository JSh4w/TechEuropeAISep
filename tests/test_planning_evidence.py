from __future__ import annotations

from datetime import date

import pytest
from pydantic_ai.models.test import TestModel

from bessible.models import NearbyProject, Position
from bessible.planning.evidence import (
    CitedStatement,
    PlanningSummary,
    load_policy,
    summarise,
    validate_citations,
)
from bessible.planning.ingest_repd import nearby_batteries

PROJECTS = [
    NearbyProject(
        id="repd-101",
        name="Dorking BESS Facility",
        mw=49.5,
        status="Application Approved",
        status_date=date(2024, 4, 18),
        distance_km=0.88,
    ),
    NearbyProject(
        id="repd-102",
        name="Brockham Battery Energy Storage",
        mw=20.0,
        status="Awaiting Construction",
        status_date=date(2023, 11, 22),
        distance_km=2.42,
    ),
]


def test_load_policy_all_have_sources():
    """Requirement 3.1: verify each policy item has an id and valid source."""
    policy = load_policy()
    assert len(policy) >= 3
    for item in policy:
        assert item.id.startswith("policy-")
        assert item.title
        assert item.statement
        assert str(item.source_url).startswith("http")


def test_validate_citations_accepts_valid():
    summary = PlanningSummary(
        statements=[
            CitedStatement(text="Dorking project was approved.", cites=["repd-101"]),
            CitedStatement(text="Batteries carved out of NSIP.", cites=["policy-nsip-carveout"]),
        ]
    )
    valid_ids = {"repd-101", "repd-102", "policy-nsip-carveout"}
    assert validate_citations(summary, valid_ids) is True


def test_validate_citations_rejects_empty_cites():
    summary = PlanningSummary(
        statements=[
            CitedStatement(text="Dorking project was approved.", cites=[]),
        ]
    )
    valid_ids = {"repd-101", "policy-nsip-carveout"}
    assert validate_citations(summary, valid_ids) is False


def test_validate_citations_rejects_unknown_id():
    summary = PlanningSummary(
        statements=[
            CitedStatement(text="Dorking project was approved.", cites=["repd-unknown-999"]),
        ]
    )
    valid_ids = {"repd-101", "policy-nsip-carveout"}
    assert validate_citations(summary, valid_ids) is False


@pytest.mark.anyio
async def test_summarise_with_valid_stub_model():
    valid_reply = {
        "statements": [
            {
                "text": "1 nearby battery facility is approved within 1 km.",
                "cites": ["repd-101"],
            },
            {
                "text": "Standalone battery storage is determined by the LPA.",
                "cites": ["policy-nsip-carveout"],
            },
        ]
    }
    stub = TestModel(custom_output_args=valid_reply)
    policy = load_policy()

    result = await summarise(PROJECTS, policy, model=stub)
    assert result is not None
    assert len(result.statements) == 2
    assert result.statements[0].cites == ["repd-101"]


@pytest.mark.anyio
async def test_summarise_rejects_uncited_statement():
    """Requirement: A summary with an uncited statement SHALL be rejected."""
    uncited_reply = {
        "statements": [
            {
                "text": "Several batteries are located nearby without citations.",
                "cites": [],
            }
        ]
    }
    stub = TestModel(custom_output_args=uncited_reply)
    policy = load_policy()

    result = await summarise(PROJECTS, policy, model=stub)
    assert result is None


@pytest.mark.anyio
async def test_summarise_rejects_unknown_citation_id():
    """Requirement: Citations must reference real records or fixed policy only."""
    invented_cite_reply = {
        "statements": [
            {
                "text": "The local council approved a huge battery project.",
                "cites": ["hallucinated-repd-id-9999"],
            }
        ]
    }
    stub = TestModel(custom_output_args=invented_cite_reply)
    policy = load_policy()

    result = await summarise(PROJECTS, policy, model=stub)
    assert result is None


def test_nearby_batteries_dorking_vs_darlington():
    # Position with nearby batteries (Dorking)
    pos_dorking = Position(lat=51.2336, lon=-0.3385)
    nearby_d = nearby_batteries(pos_dorking)
    assert len(nearby_d) == 3
    assert [p.id for p in nearby_d] == ["repd-101", "repd-102", "repd-103"]
    assert all(p.distance_km <= 5.0 for p in nearby_d)

    # Position without nearby batteries (Darlington)
    pos_darlington = Position(lat=54.52, lon=-1.55)
    nearby_none = nearby_batteries(pos_darlington)
    assert len(nearby_none) == 0


@pytest.mark.anyio
async def test_regulatory_planning_wiring_with_stub():
    from bessible.models import (
        AssessmentRequest,
        CapacityOutput,
        ConfirmedSite,
        GridOutput,
        PlanningInput,
        SiteLandOutput,
        TitleOutput,
    )
    from bessible.stages.planning import regulatory_planning

    pos = Position(lat=51.2336, lon=-0.3385)
    inp = PlanningInput.model_construct(
        run_id="testrun-98765432",
        request=AssessmentRequest(postcode="RH4 3LZ"),
        site=ConfirmedSite.model_construct(
            position=pos,
            capacity_mw=15.0,
            boundary=TitleOutput.model_construct(),
            capacity=None,
            flexible_connection=False,
        ),
        capacity=CapacityOutput.model_construct(tia_threshold_mw=5),
        grid=GridOutput(),
        site_land=SiteLandOutput(land_use="Industrial", constraints=[]),
    )

    stub = TestModel(
        custom_output_args={
            "statements": [
                {
                    "text": "Dorking BESS Facility is an approved battery nearby.",
                    "cites": ["repd-101"],
                }
            ]
        }
    )

    out = await regulatory_planning(inp, summary_model=stub)
    assert len(out.nearby) == 3
    repd_art = next(a for a in out.artifacts if a.stage == "planning" and "planning-repd" in a.id)
    assert "Found 3 battery storage project(s)" in repd_art.claim
    assert "DESNZ REPD" in str(repd_art.source_url) or "renewable-energy-planning-database" in str(repd_art.source_url)

    summary_art = next(a for a in out.artifacts if a.stage == "planning" and "planning-summary" in a.id)
    assert "Dorking BESS Facility" in summary_art.claim
    assert "test" in summary_art.model_used


@pytest.mark.anyio
async def test_regulatory_planning_omits_summary_artifact_when_uncited():
    from bessible.models import (
        AssessmentRequest,
        CapacityOutput,
        ConfirmedSite,
        GridOutput,
        PlanningInput,
        SiteLandOutput,
        TitleOutput,
    )
    from bessible.stages.planning import regulatory_planning

    pos = Position(lat=51.2336, lon=-0.3385)
    inp = PlanningInput.model_construct(
        run_id="testrun-98765432",
        request=AssessmentRequest(postcode="RH4 3LZ"),
        site=ConfirmedSite.model_construct(
            position=pos,
            capacity_mw=15.0,
            boundary=TitleOutput.model_construct(),
            capacity=None,
            flexible_connection=False,
        ),
        capacity=CapacityOutput.model_construct(tia_threshold_mw=5),
        grid=GridOutput(),
        site_land=SiteLandOutput(land_use="Industrial", constraints=[]),
    )

    stub_uncited = TestModel(
        custom_output_args={
            "statements": [
                {
                    "text": "Uncited statement that must be rejected.",
                    "cites": [],
                }
            ]
        }
    )

    out = await regulatory_planning(inp, summary_model=stub_uncited)
    # The records are shown alone: out.nearby has 3 records, but no summary artifact exists!
    assert len(out.nearby) == 3
    summary_arts = [a for a in out.artifacts if "planning-summary" in a.id]
    assert len(summary_arts) == 0
