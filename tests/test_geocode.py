from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from bessible.config import settings
from bessible.geocode import PostcodeNotFoundError, format_postcode, geocode_postcode, normalise_postcode

REAL_FIXTURE = Path(__file__).parent.parent / "data" / "fixtures" / "postcodes" / "RH41AD.json"


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return tmp_path


def client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_normalise_and_format():
    assert normalise_postcode(" rh4  1ad ") == "RH41AD"
    assert format_postcode("rh41ad") == "RH4 1AD"
    assert format_postcode("M11AE") == "M1 1AE"


@pytest.mark.anyio
async def test_lookup_calls_api_once_then_caches(data_dir):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json=json.loads(REAL_FIXTURE.read_text()))

    async with client(handler) as c:
        first = await geocode_postcode("rh4 1ad", client=c)
        second = await geocode_postcode("RH4 1AD", client=c)
    assert calls == ["https://api.postcodes.io/postcodes/RH41AD"]
    assert first.latitude == second.latitude == pytest.approx(51.232882)
    assert (data_dir / "fixtures" / "postcodes" / "RH41AD.json").exists()


@pytest.mark.anyio
async def test_committed_fixture_needs_no_network():
    def handler(_request: httpx.Request) -> httpx.Response:
        pytest.fail("network must not be used for a cached postcode")

    async with client(handler) as c:
        result = await geocode_postcode("RH4 1AD", client=c)
    assert result.postcode == "RH4 1AD"


@pytest.mark.anyio
async def test_unknown_postcode_is_not_found(data_dir):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"status": 404, "error": "Postcode not found"})

    async with client(handler) as c:
        with pytest.raises(PostcodeNotFoundError, match="not found"):
            await geocode_postcode("ZZ99 9ZZ", client=c)
    assert not list(data_dir.rglob("*.json"))


@pytest.mark.anyio
async def test_malformed_postcode_never_hits_network():
    with pytest.raises(PostcodeNotFoundError, match="valid UK postcode"):
        await geocode_postcode("not a postcode")


@pytest.mark.anyio
@pytest.mark.usefixtures("data_dir")
async def test_server_error_is_retryable():
    async with client(lambda _request: httpx.Response(503)) as c:
        with pytest.raises(httpx.HTTPStatusError):
            await geocode_postcode("RH4 1AB", client=c)
