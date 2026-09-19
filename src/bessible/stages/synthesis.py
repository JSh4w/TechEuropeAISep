"""Synthesis report generation stage placeholder."""

from __future__ import annotations

import asyncio
from pathlib import Path

from bessible.models import Artifact, Finding, ReportOutput, SynthesisInput, Verdict


def _write_report_file(run_id: str, file_name: str, content: str) -> None:
    run_dir = Path(f"out/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / file_name).write_text(content, encoding="utf-8")


def _build_findings(inp: SynthesisInput, art_ids_by_stage: dict[str, list[str]]) -> list[Finding]:
    findings: list[Finding] = []
    if "capacity" in art_ids_by_stage:
        sub = inp.capacity.substation or "substation"
        findings.append(
            Finding(
                text=(
                    f"Grid capacity confirmed: {inp.capacity.firm_mw:g} MW firm connection "
                    f"({inp.capacity.ceiling_mw:g} MW ceiling) at {sub}."
                ),
                artifact_ids=art_ids_by_stage["capacity"],
            )
        )
    if "grid" in art_ids_by_stage:
        findings.append(
            Finding(
                text=(
                    f"Gate 2 queue position {inp.grid.gate2_queue_position} with indicative connection "
                    f"timescale of {inp.grid.indicative_connection_months} months."
                ),
                artifact_ids=art_ids_by_stage["grid"],
            )
        )
    if "site_land" in art_ids_by_stage:
        findings.append(
            Finding(
                text=f"Land classification: {inp.site_land.land_use}; constraints manageable with standard mitigation.",
                artifact_ids=art_ids_by_stage["site_land"],
            )
        )
    if "financial" in art_ids_by_stage:
        findings.append(
            Finding(
                text="Financial analysis confirms positive returns with 4-hour duration achieving 13% IRR.",
                artifact_ids=art_ids_by_stage["financial"],
            )
        )
    if "planning" in art_ids_by_stage:
        findings.append(
            Finding(
                text=f"Consenting pathway via {inp.planning.consenting_route}.",
                artifact_ids=art_ids_by_stage["planning"],
            )
        )
    if not findings:
        fallback_art_id = f"synthesis-{inp.run_id[:8]}"
        findings.append(
            Finding(
                text="Feasibility criteria satisfied across grid, land, and market models.",
                artifact_ids=[fallback_art_id],
            )
        )
    return findings


def _render_markdown(inp: SynthesisInput, verdict: Verdict, findings: list[Finding]) -> str:
    sub = inp.capacity.substation or "N/A"
    volt = f"{inp.capacity.connection_voltage_kv:g} kV" if inp.capacity.connection_voltage_kv else "N/A"
    direction = inp.capacity.binding_direction or "None"
    season = inp.capacity.binding_season or "N/A"

    lines = [
        f"# Bessible Assessment Report — Run {inp.run_id}",
        "",
        f"**Verdict:** `{verdict.upper()}`",
        "",
        "## Site & Connection Summary",
        f"- **Coordinates:** {inp.site.position.lat:.4f}, {inp.site.position.lon:.4f}",
        f"- **Confirmed Capacity:** {inp.site.capacity_mw:g} MW",
        f"- **Firm Headroom:** {inp.capacity.firm_mw:g} MW",
        f"- **Ceiling Headroom:** {inp.capacity.ceiling_mw:g} MW",
        f"- **Substation:** {sub}",
        f"- **Voltage:** {volt}",
        f"- **Binding Constraint:** {direction} ({season})",
        "",
        "## Storage Duration Comparison",
        "| Duration | CAPEX (£) | 25-Year NPV (£) | IRR |",
        "|---|---|---|---|",
    ]

    for case in inp.financial.cases:
        irr_str = f"{case.irr * 100:.1f}%" if case.irr is not None else "N/A"
        lines.append(f"| {case.duration_h} hours | £{case.capex_gbp:,.0f} | £{case.npv_gbp:,.0f} | {irr_str} |")

    lines.extend(["", "## Key Findings"])
    for f in findings:
        cites = ", ".join(f"`{aid}`" for aid in f.artifact_ids)
        lines.append(f"- {f.text} (Evidence: {cites})")

    lines.extend(["", "## Supporting Evidence Artifacts"])
    for art in inp.artifacts:
        ref = art.source_url or art.file_path or art.image_path or "N/A"
        lines.append(
            f"- **[{art.id}]** ({art.stage}): {art.claim} [Source: {ref}] "
            f"(Confidence: {art.confidence * 100:.0f}%, Model: {art.model_used})"
        )

    return "\n".join(lines) + "\n"


async def synthesise(inp: SynthesisInput) -> ReportOutput:
    """Synthesise findings and duration returns into an explainable Markdown report."""
    verdict: Verdict = "go"

    art_ids_by_stage: dict[str, list[str]] = {}
    for art in inp.artifacts:
        art_ids_by_stage.setdefault(art.stage, []).append(art.id)

    findings = _build_findings(inp, art_ids_by_stage)
    report_content = _render_markdown(inp, verdict, findings)

    report_file_name = "report.md"
    await asyncio.to_thread(_write_report_file, inp.run_id, report_file_name, report_content)

    art_synth = Artifact(
        id=f"synthesis-{inp.run_id[:8]}",
        stage="synthesis",
        claim=f"Assessment report compiled with verdict '{verdict}' and duration comparison",
        file_path=report_file_name,
        confidence=0.95,
        model_used="dummy",
    )

    return ReportOutput(
        verdict=verdict,
        findings=findings,
        report_path=report_file_name,
        artifacts=[art_synth],
    )
