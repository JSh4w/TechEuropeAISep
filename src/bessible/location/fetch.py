"""Web page fetching and caching for property link location extraction."""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import UTC, datetime
from http import HTTPStatus
from typing import TYPE_CHECKING

import httpx

from bessible.config import settings

if TYPE_CHECKING:
    from pathlib import Path

FETCH_TIMEOUT_S = 15.0
DEFAULT_USER_AGENT = "Bessible/1.0 (+https://bessible.example.com; property site assessment bot)"


class PageUnavailable(Exception):  # ruff: ignore[error-suffix-on-exception-name]
    """Raised when a property web page cannot be fetched, timed out, or returned an error."""


def page_cache_path(url: str) -> Path:
    """Return the fixture cache file path for a URL."""
    norm = hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()
    return settings.data_dir / "fixtures" / "pages" / f"{norm}.json"


def html_to_text(raw_html: str) -> str:
    """Extract readable text content from raw HTML."""
    clean = re.sub(r"(?is)<(script|style|svg|noscript)[^>]*>.*?</\1>", " ", raw_html)
    clean = re.sub(r"(?s)<!--.*?-->", " ", clean)
    clean = re.sub(r"(?i)<(br|p|div|tr|li|h[1-6])[^>]*>", "\n", clean)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = html.unescape(clean)
    lines: list[str] = []
    for line in clean.splitlines():
        stripped = re.sub(r"\s+", " ", line).strip()
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


async def _execute_fetch(url: str, client: httpx.AsyncClient | None) -> httpx.Response:
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    if client is None:
        async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_S, follow_redirects=True, headers=headers) as own:
            return await own.get(url)
    return await client.get(url, follow_redirects=True, headers=headers)


async def fetch_page_text(url: str, *, client: httpx.AsyncClient | None = None) -> str:
    """Fetch property page text with URL-keyed disk caching.

    If cached under data/fixtures/pages/<sha1>.json, the cached text is returned
    without making any network requests.

    Raises:
        PageUnavailable: if the page cannot be reached, times out, or returns a 4xx/5xx status.
    """
    cache = page_cache_path(url)
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        return str(data.get("text", ""))

    try:
        resp = await _execute_fetch(url, client)
    except Exception as exc:
        msg = f"Could not fetch property page at '{url}': {exc}"
        raise PageUnavailable(msg) from exc

    if resp.status_code >= HTTPStatus.BAD_REQUEST:
        msg = f"HTTP {resp.status_code} fetching page '{url}'"
        raise PageUnavailable(msg)

    content_type = resp.headers.get("content-type", "")
    text = (
        html_to_text(resp.text)
        if ("html" in content_type or "<html" in resp.text[:500].lower())
        else resp.text
    )

    cache.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "url": url,
        "fetched_at": datetime.now(UTC).isoformat(),
        "text": text,
    }
    cache.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return text
