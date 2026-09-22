"""Defenses against prompt injection carried in third-party text (news articles, scraped pages).

Applies at the boundary where untrusted text becomes part of an LLM prompt or an `Artifact.claim`
that later re-enters a prompt (e.g. `suitability/verdict.py`'s findings agent reads every stage's
claims). Not a security boundary on its own: a determined, non-literal rephrasing of an injection
can still slip through. Pair with prompt-side hardening (state plainly that this content is data,
not instructions) at the point each field is consumed. See the OWASP LLM Prompt Injection
Prevention Cheat Sheet's "remote content sanitization" and "encoding detection" guidance.
"""

from __future__ import annotations

import base64
import binascii
import re

REDACTED = "[redacted: content matched a known prompt-injection pattern]"

_INJECTION_PATTERNS = re.compile(
    r"ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+instructions?"
    r"|disregard\s+(all\s+|any\s+)?(the\s+)?(above|previous|prior)\s+instructions?"
    r"|new\s+instructions?\s*:"
    r"|system\s*[:\-]?\s*prompt"
    r"|you\s+are\s+now\s+(a|an)\b"
    r"|act\s+as\s+(a|an)\s+"
    r"|\bdeveloper\s+mode\b"
    r"|\bjailbreak\b",
    re.IGNORECASE,
)

# Long base64/hex runs can carry an obfuscated instruction past the plain-text check above.
_BASE64_RUN = re.compile(r"(?:[A-Za-z0-9+/]{4}){6,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")
_HEX_RUN = re.compile(r"(?:[0-9a-fA-F]{2}[\s:]?){16,}")


def _decoded_candidates(text: str) -> list[str]:
    """Best-effort decode of base64/hex runs in text, so an obfuscated payload can still be matched."""
    candidates: list[str] = []
    for match in _BASE64_RUN.finditer(text):
        try:
            candidates.append(base64.b64decode(match.group(0), validate=True).decode("utf-8", errors="ignore"))
        except (binascii.Error, ValueError):
            continue
    for match in _HEX_RUN.finditer(text):
        cleaned = re.sub(r"[\s:]", "", match.group(0))
        try:
            candidates.append(bytes.fromhex(cleaned).decode("utf-8", errors="ignore"))
        except ValueError:
            continue
    return candidates


def sanitize_untrusted_text(text: str, *, max_len: int = 500) -> str:
    """Truncate and redact `text` on a known prompt-injection pattern.

    Checks `text` itself and any base64/hex-decoded run inside it. Returns the original
    (truncated) text when nothing matches.
    """
    trimmed = text[:max_len]
    haystacks = (trimmed, *_decoded_candidates(trimmed))
    if any(_INJECTION_PATTERNS.search(h) for h in haystacks):
        return REDACTED
    return trimmed
