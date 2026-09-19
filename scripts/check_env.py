"""Check the dev environment is ready: secrets, Temporal server, Modal login."""

import asyncio
import subprocess

from temporalio.client import Client

from bessible.config import settings


def check(name: str, ok: bool, hint: str = "") -> bool:
    print(f"{'OK ' if ok else 'MISSING'}  {name}" + ("" if ok else f"  ({hint})"))
    return ok


async def temporal_reachable() -> bool:
    try:
        await asyncio.wait_for(
            Client.connect(settings.temporal_address, namespace=settings.temporal_namespace), timeout=3
        )
        return True
    except Exception:
        return False


def main() -> None:
    results = [
        check("PYDANTIC_AI_GATEWAY_API_KEY", settings.pydantic_ai_gateway_api_key is not None, "set it in .env"),
        check("TYPESAFE_API_KEY", settings.typesafe_api_key is not None, "set it in .env"),
        check(
            f"Temporal server at {settings.temporal_address}",
            asyncio.run(temporal_reachable()),
            "run `temporal server start-dev` in another terminal",
        ),
        check(
            "Modal login",
            subprocess.run(["modal", "profile", "current"], capture_output=True).returncode == 0,
            "run `uv run modal setup`",
        ),
    ]
    raise SystemExit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
