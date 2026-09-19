"""Check the dev environment is ready: secrets, Temporal server, Modal login.

    uv run python scripts/check_env.py          # config only
    uv run python scripts/check_env.py --live   # also send one tiny prompt to Gemini and the Modal model
"""

import asyncio
import subprocess
import sys

from pydantic_ai import Agent
from temporalio.client import Client

from bessible import llm
from bessible.config import settings


def check(name: str, ok: bool, hint: str = "", required: bool = True) -> bool:
    label = "OK " if ok else ("MISSING" if required else "skip")
    print(f"{label:8} {name}" + ("" if ok else f"  ({hint})"))
    return ok or not required


async def temporal_reachable() -> bool:
    try:
        await asyncio.wait_for(
            Client.connect(settings.temporal_address, namespace=settings.temporal_namespace), timeout=3
        )
        return True
    except Exception:
        return False


def ping(name: str, make_model) -> bool:
    try:
        out = Agent(make_model()).run_sync("Reply with exactly: pong").output
        return check(f"{name} replies", "pong" in out.lower(), f"got {out[:60]!r}")
    except Exception as e:
        return check(f"{name} replies", False, f"{type(e).__name__}: {str(e)[:120]}")


def main() -> None:
    results = [
        check("GOOGLE_API_KEY", settings.google_api_key is not None, "set it in .env"),
        check("PYDANTIC_AI_GATEWAY_API_KEY", settings.pydantic_ai_gateway_api_key is not None, "set it in .env"),
        check("LOGFIRE_TOKEN", settings.logfire_token is not None, "optional: tracing", required=False),
        check("TYPESAFE_API_KEY", settings.typesafe_api_key is not None, "optional: Jev", required=False),
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
    if "--live" in sys.argv:
        llm.setup_logfire()
        results += [
            ping(f"Gemini ({settings.gemini_model})", llm.gemini_model),
            ping(f"Modal via gateway ({settings.modal_model})", llm.modal_model),
        ]
    raise SystemExit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
