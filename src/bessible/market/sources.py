"""Revenue sources: a protocol, a fixture loader, and a live-with-fallback wrapper."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from datetime import date
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, HttpUrl

from bessible.assumptions import FIXTURES_DIR
from bessible.models import StreamValue

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

MARKET_FIXTURES = FIXTURES_DIR / "market"


class RevenueSource(Protocol):
    """Any source, public or paid, implements one method."""

    name: str

    async def fetch(self, duration_h: int) -> StreamValue:
        """Return this stream's revenue for one duration."""
        ...


class Fixture(BaseModel):
    """A committed fallback for one stream."""

    stream: str
    source: str
    source_url: HttpUrl
    as_of: date
    status: str = "agreed"
    note: str = ""
    gbp_per_mw_year_by_duration: dict[str, float]


class FixtureSource:
    """Serves a committed fixture. Always flagged cached."""

    def __init__(self, name: str, path: Path | None = None) -> None:
        """Initialize the fixture source with a stream name and optional path."""
        self.name = name
        self.path = path or MARKET_FIXTURES / f"{name}.json"

    async def fetch(self, duration_h: int) -> StreamValue:
        """Return the fixture value for one duration, flagged cached."""
        fixture = Fixture.model_validate(json.loads(self.path.read_text(encoding="utf-8")))
        return StreamValue(
            stream=fixture.stream,
            gbp_per_mw_year=fixture.gbp_per_mw_year_by_duration[str(duration_h)],
            source=fixture.source,
            source_url=fixture.source_url,
            as_of=fixture.as_of,
            cached=True,
            placeholder=fixture.status == "placeholder",
        )


class FallbackSource:
    """Try a live source. On any error, use the fixture. The run never fails on one source."""

    def __init__(self, live: RevenueSource, fixture: FixtureSource) -> None:
        """Wrap a live source with a fixture fallback."""
        self.name = fixture.name
        self.live = live
        self.fixture = fixture

    async def fetch(self, duration_h: int) -> StreamValue:
        """Return the live value, or the cached fixture if the live source fails."""
        try:
            return await self.live.fetch(duration_h)
        except Exception:
            logger.warning("Live source %s failed; using cached fixture", self.live.name, exc_info=True)
            return await self.fixture.fetch(duration_h)


# No verified live endpoint is wired yet (see add-market-revenue blocker). Wrap one with `FallbackSource`.
STREAM_NAMES = ("capacity_market", "balancing_ancillary", "wholesale")
LiveFetch = Callable[[int], Awaitable[StreamValue]]


def default_sources() -> list[RevenueSource]:
    """The demo sources: committed fixtures for all three streams."""
    return [FixtureSource(name) for name in STREAM_NAMES]
