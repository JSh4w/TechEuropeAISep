"""Tests for location/extract.py structured extraction and link resolution."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic_ai.models.test import TestModel

from bessible.location.extract import (
    ExtractedLocation,
    LocationNotFound,
    extract_location,
    is_uk_country,
    resolve_from_link,
)
from bessible.location.fetch import page_cache_path


def test_is_uk_country():
    assert is_uk_country(None) is True
    assert is_uk_country("") is True
    assert is_uk_country("UK") is True
    assert is_uk_country("United Kingdom") is True
    assert is_uk_country("England") is True
    assert is_uk_country("Scotland") is True
    assert is_uk_country("Wales") is True
    assert is_uk_country("France") is False
    assert is_uk_country("United States") is False
    assert is_uk_country("Germany") is False


@pytest.mark.anyio
async def test_extract_location_empty():
    res = await extract_location("")
    assert res.postcode is None
    assert res.address is None
    assert res.confidence == 0.0


@pytest.mark.anyio
async def test_resolve_from_link_with_postcode(monkeypatch, tmp_path):
    monkeypatch.setattr("bessible.config.settings.data_dir", tmp_path)
    url = "https://example.com/property-didcot"

    cache_file = page_cache_path(url)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"url": url, "text": "Land at Didcot, Oxfordshire, OX14 4TE"}))

    test_model = TestModel(
        custom_output_args=ExtractedLocation(
            address="Land at Didcot",
            postcode="OX14 4TE",
            country="United Kingdom",
            confidence=0.92,
        )
    )

    pc_fixture = Path("data/fixtures/postcodes/OX144TE.json")
    if pc_fixture.exists():
        dest = tmp_path / "fixtures" / "postcodes" / "OX144TE.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(pc_fixture.read_text(encoding="utf-8"), encoding="utf-8")

    out = await resolve_from_link(url, "run-12345678", model=test_model)
    assert out.postcode == "OX14 4TE"
    assert out.position.lat == pytest.approx(51.625656, abs=0.01)
    assert out.position.lon == pytest.approx(-1.275612, abs=0.01)
    assert len(out.artifacts) == 1
    art = out.artifacts[0]
    assert str(art.source_url) == "https://example.com/property-didcot"
    assert art.confidence == pytest.approx(0.92, abs=0.01)
    assert "OX14 4TE" in art.claim


@pytest.mark.anyio
async def test_resolve_from_link_with_coordinates_only(monkeypatch, tmp_path):
    monkeypatch.setattr("bessible.config.settings.data_dir", tmp_path)
    url = "https://example.com/property-coords"

    cache_file = page_cache_path(url)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"url": url, "text": "Development site at 51.625656, -1.275612"}))

    test_model = TestModel(
        custom_output_args=ExtractedLocation(
            address="Development site",
            lat=51.625656,
            lon=-1.275612,
            country="UK",
            confidence=0.88,
        )
    )

    # Mock reverse geocode response to return OX14 4TE
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_rev_resp = httpx.Response(
        status_code=200,
        json={"status": 200, "result": [{"postcode": "OX14 4TE"}]},
        request=httpx.Request("GET", "https://api.postcodes.io/postcodes"),
    )
    mock_client.get.return_value = mock_rev_resp

    # Copy the OX144TE postcode fixture so geocode_postcode works offline
    pc_fixture = Path("data/fixtures/postcodes/OX144TE.json")
    if pc_fixture.exists():
        dest = tmp_path / "fixtures" / "postcodes" / "OX144TE.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(pc_fixture.read_text(encoding="utf-8"), encoding="utf-8")

    out = await resolve_from_link(url, "run-coords", model=test_model, client=mock_client)
    assert out.postcode == "OX14 4TE"
    assert out.position.lat == pytest.approx(51.625656, abs=0.001)
    assert out.position.lon == pytest.approx(-1.275612, abs=0.001)
    assert len(out.artifacts) == 1


@pytest.mark.anyio
async def test_resolve_from_link_non_uk_fails(monkeypatch, tmp_path):
    monkeypatch.setattr("bessible.config.settings.data_dir", tmp_path)
    url = "https://example.com/property-spain"

    cache_file = page_cache_path(url)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"url": url, "text": "Finca in Madrid, Spain"}))

    test_model = TestModel(
        custom_output_args=ExtractedLocation(
            address="Finca Madrid",
            country="Spain",
            confidence=0.9,
        )
    )

    with pytest.raises(LocationNotFound, match="Only UK sites are supported"):
        await resolve_from_link(url, "run-non-uk", model=test_model)


@pytest.mark.anyio
async def test_resolve_from_link_no_address_fails(monkeypatch, tmp_path):
    monkeypatch.setattr("bessible.config.settings.data_dir", tmp_path)
    url = "https://example.com/property-empty"

    cache_file = page_cache_path(url)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"url": url, "text": "Terms and conditions apply"}))

    test_model = TestModel(
        custom_output_args=ExtractedLocation(
            address=None,
            postcode=None,
            confidence=0.0,
        )
    )

    with pytest.raises(LocationNotFound, match="--postcode"):
        await resolve_from_link(url, "run-empty", model=test_model)


@pytest.mark.anyio
async def test_resolve_from_link_invalid_postcode_fails(monkeypatch, tmp_path):
    monkeypatch.setattr("bessible.config.settings.data_dir", tmp_path)
    url = "https://example.com/property-invalid-pc"

    cache_file = page_cache_path(url)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"url": url, "text": "Invalid postcode XX1 1XX"}))

    test_model = TestModel(
        custom_output_args=ExtractedLocation(
            address="Somewhere",
            postcode="XX1 1XX",
            country="UK",
            confidence=0.5,
        )
    )

    with pytest.raises(LocationNotFound, match="--postcode"):
        await resolve_from_link(url, "run-invalid", model=test_model)
