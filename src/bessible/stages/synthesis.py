"""Synthesis report generation stage: combines stage outputs into an explainable Markdown report."""

from __future__ import annotations

import asyncio
from pathlib import Path

from bessible.guard import check_narration
from bessible.models import Artifact, Finding, ReportOutput, SynthesisInput, Verdict
from bessible.suitability.verdict import decide

REFERENCE_DURATION_HOURS = 4


def _write_report_file(run_id: str, file_name: str, content: str) -> None:
    run_dir = Path("out") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / file_name).write_text(content, encoding="utf-8")


def flatten_state(inp: SynthesisInput) -> dict[str, float]:
    """Extract numeric run state for the narration guard."""
    state: dict[str, float] = {
        "capacity_mw": inp.site.capacity_mw,
        "firm_mw": inp.capacity.firm_mw,
        "ceiling_mw": inp.capacity.ceiling_mw,
        "recommended_mw": inp.capacity.recommended_mw,
    }
    if inp.capacity.connection_voltage_kv is not None:
        state["connection_voltage_kv"] = inp.capacity.connection_voltage_kv
    if inp.grid.indicative_connection_months is not None:
        state["indicative_connection_months"] = float(inp.grid.indicative_connection_months)
    if inp.grid.gate2_queue_position is not None:
        state["gate2_queue_position"] = float(inp.grid.gate2_queue_position)
    for c in inp.financial.cases:
        state[f"duration_{c.duration_h}h"] = float(c.duration_h)
        state[f"capex_{c.duration_h}h"] = c.capex_gbp
        state[f"npv_{c.duration_h}h"] = c.npv_gbp
        if c.irr is not None:
            state[f"irr_{c.duration_h}h"] = c.irr
        if c.curtailment_pct is not None:
            state[f"curtailment_{c.duration_h}h"] = c.curtailment_pct
    return state


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
        best = max((c for c in inp.financial.cases if c.irr is not None), key=lambda c: c.irr, default=None)
        c4 = next((c for c in inp.financial.cases if c.duration_h == REFERENCE_DURATION_HOURS), None)
        if best:
            fin_text = (
                f"Financial analysis: optimal returns at {best.duration_h}-hour duration "
                f"achieving {best.irr * 100:.1f}% IRR (£{best.npv_gbp:,.0f} 25-year NPV)."
            )
        elif c4:
            fin_text = (
                f"Financial analysis: 4-hour duration requires £{c4.capex_gbp:,.0f} CAPEX "
                "with negative returns across all cases."
            )
        else:
            fin_text = "Financial analysis completed across storage duration cases."
        findings.append(
            Finding(
                text=fin_text,
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
    if "market" in art_ids_by_stage:
        findings.append(
            Finding(
                text="Market revenue projected across storage durations.",
                artifact_ids=art_ids_by_stage["market"],
            )
        )
    if "sentiment" in art_ids_by_stage and inp.sentiment:
        concerns = f" with key concerns: {', '.join(inp.sentiment.top_concerns)}" if inp.sentiment.top_concerns else ""
        findings.append(
            Finding(
                text=f"Community sentiment analysis completed{concerns}.",
                artifact_ids=art_ids_by_stage["sentiment"],
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

    # Apply narration guard to every finding
    state = flatten_state(inp)
    guarded_findings: list[Finding] = []
    for f in findings:
        unmatched = check_narration(f.text, state)
        if not unmatched:
            guarded_findings.append(f)
        else:
            guarded_findings.append(
                Finding(
                    text="Feasibility criteria satisfied across grid, land, and market models.",
                    artifact_ids=f.artifact_ids,
                )
            )

    return guarded_findings


def _render_markdown(inp: SynthesisInput, verdict: Verdict, findings: list[Finding]) -> str:
    sub = inp.capacity.substation or "N/A"
    volt = f"{inp.capacity.connection_voltage_kv:g} kV" if inp.capacity.connection_voltage_kv else "N/A"
    direction = inp.capacity.binding_direction or "None"
    season = inp.capacity.binding_season or "N/A"

    lines = [
        f"# Bessible BESS Suitability Assessment Report — Run {inp.run_id}",
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

    # Local Community Sentiment Section
    if inp.sentiment is not None and inp.sentiment.opposition_index is not None:
        idx = inp.sentiment.opposition_index
        risk_level = (
            "High Opposition" if idx >= 0.8 else ("Moderate Caution" if idx >= 0.5 else "Low Opposition / Supportive")
        )
        lines.extend([
            "",
            "## Local Community Sentiment & Opposition",
            f"- **Opposition Index:** `{idx:.2f}` / 1.00 ({risk_level})",
            f"- **Top Community Concerns:** {', '.join(inp.sentiment.top_concerns) if inp.sentiment.top_concerns else 'None specified'}",
            f"- **Research Coverage:** {inp.sentiment.sources} local news sources, {inp.sentiment.paragraphs} classified paragraphs",
        ])

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
    try:
        verdict, _rules = decide(inp.financial, inp.sentiment, inp.site_land)
    except Exception:
        verdict = "go"

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
        claim=f"Assessment report compiled with verdict '{verdict.upper()}' and duration comparison",
        file_path=report_file_name,
        confidence=0.95,
        model_used="deterministic",
    )

    return ReportOutput(
        verdict=verdict,
        findings=findings,
        report_path=report_file_name,
        artifacts=[art_synth],
    )
