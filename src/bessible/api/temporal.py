"""Temporal client connection management and error helpers for the FastAPI server."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException
from temporalio.client import Client, RPCError, RPCStatusCode
from temporalio.contrib.pydantic import pydantic_data_converter

from bessible.config import settings

TEMPORAL_DOWN_MSG = "Temporal server is unavailable. Start it with: temporal server start-dev"


class _TemporalHolder:
    client: Client | None = None


_holder = _TemporalHolder()


async def get_temporal_client() -> Client:
    """Return a connected Temporal client or raise HTTP 503 if unavailable."""
    if _holder.client is not None:
        return _holder.client

    try:
        client = await asyncio.wait_for(
            Client.connect(
                settings.temporal_address,
                namespace=settings.temporal_namespace,
                data_converter=pydantic_data_converter,
            ),
            timeout=3.0,
        )
    except (TimeoutError, ConnectionError, OSError, RuntimeError, RPCError) as exc:
        _holder.client = None
        raise HTTPException(
            status_code=503,
            detail=TEMPORAL_DOWN_MSG,
        ) from exc
    else:
        _holder.client = client
        return client


def reset_temporal_client() -> None:
    """Reset cached Temporal client."""
    _holder.client = None


def handle_temporal_error(exc: Exception, run_id: str | None = None) -> None:
    """Convert Temporal RPC/connection errors into appropriate HTTP exceptions."""
    if isinstance(exc, RPCError):
        if exc.status == RPCStatusCode.NOT_FOUND or "not found" in str(exc).lower():
            target = f"Run '{run_id}'" if run_id else "Resource"
            raise HTTPException(status_code=404, detail=f"{target} not found") from exc
        if exc.status == RPCStatusCode.UNAVAILABLE:
            raise HTTPException(status_code=503, detail=TEMPORAL_DOWN_MSG) from exc
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        raise HTTPException(status_code=503, detail=TEMPORAL_DOWN_MSG) from exc
    raise exc
