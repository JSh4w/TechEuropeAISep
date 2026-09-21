"""Local sentiment analysis stage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bessible import events
from bessible.models import NodeInput, SentimentOutput
from bessible.suitability.research import research_local_news
from bessible.suitability.sentiment import process_sentiment

if TYPE_CHECKING:
    from pydantic_ai.models import Model


async def local_sentiment(inp: NodeInput, *, model: Model | None = None) -> SentimentOutput:
    """Assess local community sentiment from local news and planning coverage."""
    postcode = inp.request.postcode
    lat = inp.site.position.lat
    lon = inp.site.position.lon

    # Derive place description
    place = f"substation area {inp.capacity.substation}" if inp.capacity.substation else "site area"

    events.emit(inp.run_id, "sentiment", f"Gathering news articles and planning notices for {place}")

    research = await research_local_news(
        place=place,
        lat=lat,
        lon=lon,
        postcode=postcode,
        model=model,
    )

    events.emit(inp.run_id, "sentiment", f"Retrieved {len(research.sources)} sources; analyzing planning sentiment")

    return await process_sentiment(inp.run_id, research, model=model)
