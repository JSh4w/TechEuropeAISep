from __future__ import annotations

import pytest
from pydantic import HttpUrl, ValidationError

from bessible.models import (
    Artifact,
    AssessmentRequest,
    CapacityOutput,
    ConfirmedSite,
    DurationCase,
    FinancialOutput,
    Finding,
    Position,
    TitleOutput,
)


def test_assessment_request_validation():
    # Valid with URL only
    req1 = AssessmentRequest(property_url=HttpUrl("https://example.com"))
    assert req1.property_url is not None

    # Valid with postcode only
    req2 = AssessmentRequest(postcode="SW1A 1AA")
    assert req2.postcode == "SW1A 1AA"

    # Valid with both
    req3 = AssessmentRequest(property_url=HttpUrl("https://example.com"), postcode="SW1A 1AA")
    assert req3.postcode == "SW1A 1AA"

    # Invalid without either
    with pytest.raises(ValidationError):
        AssessmentRequest()


def test_artifact_validation():
    # Valid with source_url
    art = Artifact(
        id="a1",
        stage="location",
        claim="Location resolved",
        source_url=HttpUrl("https://example.com"),
        confidence=0.8,
        model_used="dummy",
    )
    assert art.id == "a1"

    # Valid with file_path
    art_file = Artifact(
        id="a2",
        stage="title",
        claim="Title boundary found",
        file_path="boundary.geojson",
        confidence=0.9,
        model_used="dummy",
    )
    assert art_file.file_path == "boundary.geojson"

    # Invalid without evidence
    with pytest.raises(ValidationError):
        Artifact(
            id="a3",
            stage="capacity",
            claim="No evidence",
            confidence=0.5,
            model_used="dummy",
        )

    # Invalid confidence > 1.0
    with pytest.raises(ValidationError):
        Artifact(
            id="a4",
            stage="location",
            claim="High confidence",
            source_url=HttpUrl("https://example.com"),
            confidence=1.4,
            model_used="dummy",
        )


def test_capacity_output_validation():
    # Valid normal output
    cap = CapacityOutput(
        viable=True,
        firm_mw=10.0,
        ceiling_mw=20.0,
        recommended_mw=10.0,
    )
    assert cap.viable is True

    # Ceiling below firm fails
    with pytest.raises(ValidationError):
        CapacityOutput(
            viable=True,
            firm_mw=20.0,
            ceiling_mw=10.0,
            recommended_mw=10.0,
        )

    # Out of area must not be viable
    with pytest.raises(ValidationError):
        CapacityOutput(
            viable=True,
            out_of_area=True,
            firm_mw=0.0,
            ceiling_mw=0.0,
            recommended_mw=0.0,
        )

    # Non-viable without message fails
    with pytest.raises(ValidationError):
        CapacityOutput(
            viable=False,
            message=None,
            firm_mw=0.0,
            ceiling_mw=0.0,
            recommended_mw=0.0,
        )


def test_confirmed_site_limits():
    title = TitleOutput(
        title_number="BK123",
        boundary_geojson={"type": "Polygon", "coordinates": []},
        area_m2=20000,
    )
    cap = CapacityOutput(viable=True, firm_mw=12.0, ceiling_mw=20.0, recommended_mw=12.0)

    # Above ceiling fails
    with pytest.raises(ValidationError):
        ConfirmedSite(
            position=Position(lat=51.6, lon=-1.2),
            capacity_mw=25.0,
            boundary=title,
            capacity=cap,
            flexible_connection=True,
        )

    # Above firm without flexible fails
    with pytest.raises(ValidationError):
        ConfirmedSite(
            position=Position(lat=51.6, lon=-1.2),
            capacity_mw=15.0,
            boundary=title,
            capacity=cap,
            flexible_connection=False,
        )

    # Above firm with flexible succeeds
    site = ConfirmedSite(
        position=Position(lat=51.6, lon=-1.2),
        capacity_mw=15.0,
        boundary=title,
        capacity=cap,
        flexible_connection=True,
    )
    assert site.capacity_mw == 15.0


def test_financial_output_duration_cases():
    # Exactly 2, 4, 8 hours required
    cases = [
        DurationCase(duration_h=2, capex_gbp=100, npv_gbp=10, irr=0.1),
        DurationCase(duration_h=4, capex_gbp=200, npv_gbp=20, irr=0.12),
        DurationCase(duration_h=8, capex_gbp=400, npv_gbp=30, irr=0.08),
    ]
    fin = FinancialOutput(cases=cases)
    assert len(fin.cases) == 3

    # Missing duration fails
    bad_cases = [
        DurationCase(duration_h=2, capex_gbp=100, npv_gbp=10, irr=0.1),
        DurationCase(duration_h=4, capex_gbp=200, npv_gbp=20, irr=0.12),
    ]
    with pytest.raises(ValidationError):
        FinancialOutput(cases=bad_cases)


def test_finding_requires_artifact_ids():
    with pytest.raises(ValidationError):
        Finding(text="No citations", artifact_ids=[])
