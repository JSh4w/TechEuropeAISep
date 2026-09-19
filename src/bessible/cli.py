"""Bessible command-line interface for starting assessments and managing site confirmation."""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from typing import TYPE_CHECKING, Any

from pydantic import HttpUrl, ValidationError
from temporalio.client import Client, WorkflowFailureError
from temporalio.contrib.pydantic import pydantic_data_converter

from bessible.config import settings
from bessible.models import AssessmentRequest, AssessmentResult, RunStatus, SiteDecision
from bessible.workflow import TASK_QUEUE, AssessmentWorkflow

if TYPE_CHECKING:
    from temporalio.client import WorkflowHandle

ACTIVE_STATUSES = {"running", "awaiting_confirmation"}
TERMINAL_STATUSES = {"completed", "rejected", "out_of_area", "not_viable", "failed"}
AFFIRMATIVE_RESPONSES = {"y", "yes"}


async def _get_client() -> Client:
    """Connect to the Temporal server or exit with a helpful instruction."""
    try:
        return await asyncio.wait_for(
            Client.connect(
                settings.temporal_address,
                namespace=settings.temporal_namespace,
                data_converter=pydantic_data_converter,
            ),
            timeout=3.0,
        )
    except (TimeoutError, ConnectionError, OSError, RuntimeError):
        print(  # ruff: ignore[print]
            f"Error: Could not connect to Temporal server at {settings.temporal_address}.\n"
            "Please ensure the server is running:\n"
            "  temporal server start-dev",
            file=sys.stderr,
        )
        sys.exit(1)


def _print_result(raw_result: AssessmentResult | dict[str, Any]) -> None:
    """Print detailed summary of an assessment result."""
    result = (
        AssessmentResult.model_validate(raw_result)
        if isinstance(raw_result, dict)
        else raw_result
    )
    print(f"\nStatus: {result.status.upper()}")  # ruff: ignore[print]
    if result.message:
        print(f"Message: {result.message}")  # ruff: ignore[print]

    if result.status == "rejected":
        print("Site confirmation was rejected.")  # ruff: ignore[print]
        return

    if result.report:
        print(f"Verdict: {result.report.verdict.upper()}")  # ruff: ignore[print]
        print("\nFindings:")  # ruff: ignore[print]
        for f in result.report.findings:
            cites = ", ".join(f.artifact_ids)
            print(f"  - {f.text} [{cites}]")  # ruff: ignore[print]

    if result.financial:
        print("\nStorage Duration Comparison:")  # ruff: ignore[print]
        print(f"  {'Duration':<10} {'CAPEX (£)':<15} {'25-Yr NPV (£)':<16} {'IRR':<8}")  # ruff: ignore[print]
        print("  " + "-" * 50)  # ruff: ignore[print]
        for c in result.financial.cases:
            irr_str = f"{c.irr * 100:.1f}%" if c.irr is not None else "N/A"
            print(f"  {f'{c.duration_h} hours':<10} £{c.capex_gbp:<14,.0f} £{c.npv_gbp:<15,.0f} {irr_str:<8}")  # ruff: ignore[print]

    print(f"\nArtifacts Directory: {result.run_dir}")  # ruff: ignore[print]
    if result.report:
        print(f"Report File: {result.run_dir}/{result.report.report_path}")  # ruff: ignore[print]


async def _handle_confirmation_prompt(
    handle: WorkflowHandle[Any, Any],
    status: RunStatus,
    *,
    auto_yes: bool,
) -> None:
    """Prompt the user for site confirmation and submit the update."""
    cap = status.capacity
    if cap is None:
        return

    print("\n--- Site Confirmation Required ---")  # ruff: ignore[print]
    print(f"Substation:         {cap.substation or 'N/A'}")  # ruff: ignore[print]
    print(f"Connection Voltage: {cap.connection_voltage_kv or 0:g} kV")  # ruff: ignore[print]
    print(f"Firm Headroom:      {cap.firm_mw:g} MW")  # ruff: ignore[print]
    print(f"Ceiling Headroom:   {cap.ceiling_mw:g} MW")  # ruff: ignore[print]
    print(f"Recommended:        {cap.recommended_mw:g} MW")  # ruff: ignore[print]
    print(f"Binding Direction:  {cap.binding_direction or 'None'} ({cap.binding_season or 'N/A'})")  # ruff: ignore[print]

    if status.boundary:
        print(f"Title Number:       {status.boundary.title_number} ({status.boundary.area_m2:,.0f} m²)")  # ruff: ignore[print]

    if auto_yes:
        print(f"Auto-confirming recommended capacity: {cap.recommended_mw:g} MW (--yes)")  # ruff: ignore[print]
        await handle.execute_update(
            AssessmentWorkflow.decide_site,
            SiteDecision(confirmed=True, capacity_mw=cap.recommended_mw),
        )
        return

    raw_input = await asyncio.to_thread(input, "\nConfirm site? [y/N]: ")
    resp = raw_input.strip().lower()
    if resp not in AFFIRMATIVE_RESPONSES:
        print("Rejecting site assessment.")  # ruff: ignore[print]
        await handle.execute_update(
            AssessmentWorkflow.decide_site,
            SiteDecision(confirmed=False),
        )
        return

    while True:
        prompt_msg = f"Enter capacity in MW [{cap.recommended_mw:g}]: "
        cap_str = (await asyncio.to_thread(input, prompt_msg)).strip()
        chosen_mw = float(cap_str) if cap_str else cap.recommended_mw
        try:
            await handle.execute_update(
                AssessmentWorkflow.decide_site,
                SiteDecision(confirmed=True, capacity_mw=chosen_mw),
            )
            print(f"Confirmed site at {chosen_mw:g} MW.")  # ruff: ignore[print]
            break
        except Exception as exc:  # ruff: ignore[blind-except]
            print(f"Error: {exc}. Please enter a valid capacity between 0 and {cap.ceiling_mw:g} MW.")  # ruff: ignore[print]


async def _watch_workflow(handle: WorkflowHandle[Any, Any], *, auto_yes: bool) -> None:
    """Watch workflow progress, prompting for confirmation and printing output."""
    last_stages: list[str] = []
    has_prompted = False

    while True:
        status: RunStatus = await handle.query(AssessmentWorkflow.status)
        if status.stages != last_stages and status.stages:
            print(f"Running stage(s): {', '.join(status.stages)}...")  # ruff: ignore[print]
            last_stages = list(status.stages)

        if status.status == "awaiting_confirmation" and not has_prompted:
            has_prompted = True
            await _handle_confirmation_prompt(handle, status, auto_yes=auto_yes)

        if status.status in TERMINAL_STATUSES:
            break

        await asyncio.sleep(0.5)

    try:
        result = await handle.result()
        _print_result(result)
    except WorkflowFailureError as err:
        print(f"\nWorkflow failed: {err}", file=sys.stderr)  # ruff: ignore[print]
        sys.exit(1)


async def cmd_start(args: argparse.Namespace) -> None:
    """Start an assessment workflow."""
    property_url = HttpUrl(args.url) if args.url else None
    try:
        req = AssessmentRequest(
            property_url=property_url,
            postcode=args.postcode,
            battery_mw=args.battery_mw,
            budget_gbp=args.budget_gbp,
            flexible_connection=args.flexible,
        )
    except ValidationError as err:
        print(f"Validation error: {err}", file=sys.stderr)  # ruff: ignore[print]
        sys.exit(1)

    client = await _get_client()
    run_id = f"bessible-{uuid.uuid4().hex[:8]}"

    handle = await client.start_workflow(
        AssessmentWorkflow.run,
        req,
        id=run_id,
        task_queue=TASK_QUEUE,
    )

    print(f"Started assessment run: {run_id}")  # ruff: ignore[print]
    if args.detach:
        return

    await _watch_workflow(handle, auto_yes=args.yes)


async def cmd_confirm(args: argparse.Namespace) -> None:
    """Submit a confirmation or rejection update for a paused run."""
    client = await _get_client()
    handle = client.get_workflow_handle(args.run_id, result_type=AssessmentResult)

    if args.reject:
        await handle.execute_update(
            AssessmentWorkflow.decide_site,
            SiteDecision(confirmed=False),
        )
        print(f"Run {args.run_id} rejected.")  # ruff: ignore[print]
        return

    decision = SiteDecision(confirmed=True, capacity_mw=args.capacity_mw)
    await handle.execute_update(AssessmentWorkflow.decide_site, decision)
    cap_msg = f"with {args.capacity_mw:g} MW" if args.capacity_mw else "with default capacity"
    print(f"Run {args.run_id} confirmed {cap_msg}.")  # ruff: ignore[print]


async def cmd_result(args: argparse.Namespace) -> None:
    """Retrieve and display the status or result of a run."""
    client = await _get_client()
    handle = client.get_workflow_handle(args.run_id, result_type=AssessmentResult)

    status: RunStatus = await handle.query(AssessmentWorkflow.status)
    if status.status in ACTIVE_STATUSES:
        active = ", ".join(status.stages) if status.stages else "none"
        print(f"Run {args.run_id} is currently {status.status} (active stages: {active}).")  # ruff: ignore[print]
        return

    result = await handle.result()
    _print_result(result)


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(prog="bessible", description="Bessible BESS Assessment CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # start
    start_p = subparsers.add_parser("start", help="Start a site assessment")
    start_p.add_argument("url", nargs="?", help="Property link URL")
    start_p.add_argument("--postcode", help="UK postcode (e.g. 'OX14 4TE')")
    start_p.add_argument("--battery-mw", type=float, help="Target battery capacity in MW")
    start_p.add_argument("--budget-gbp", type=float, help="Total project budget in GBP")
    start_p.add_argument("--flexible", action="store_true", help="Enable flexible grid connection above firm headroom")
    start_p.add_argument("--detach", action="store_true", help="Print run ID and exit without waiting")
    start_p.add_argument("--yes", "-y", action="store_true", help="Automatically accept proposal defaults")

    # confirm
    confirm_p = subparsers.add_parser("confirm", help="Confirm or reject site for an awaiting run")
    confirm_p.add_argument("run_id", help="Workflow run ID")
    confirm_p.add_argument("--capacity-mw", type=float, help="Confirmed capacity in MW")
    confirm_p.add_argument("--reject", action="store_true", help="Reject the site")

    # result
    result_p = subparsers.add_parser("result", help="View result or status of a run")
    result_p.add_argument("run_id", help="Workflow run ID")

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "start":
        asyncio.run(cmd_start(args))
    elif args.command == "confirm":
        asyncio.run(cmd_confirm(args))
    elif args.command == "result":
        asyncio.run(cmd_result(args))


if __name__ == "__main__":
    main()
