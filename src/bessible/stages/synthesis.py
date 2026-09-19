"""Synthesis report generation stage."""

from __future__ import annotations

import asyncio
from pathlib import Path

from bessible.models import Artifact, Finding, ReportOutput, SynthesisInput, Verdict
from bessible.suitability.verdict import decide, generate_findings


def _write_report_file(run_id: str, file_name: str, content: str) -> None:
    run_dir = Path(f"out/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / file_name).write_text(content, encoding="utf-8")


def _render_markdown(
    inp: SynthesisInput,
    verdict: Verdict,
    rules: list[str],
    findings: list[Finding],
) -> str:
    sub = inp.capacity.substation or "N/A"
    volt = f"{inp.capacity.connection_voltage_kv:g} kV" if inp.capacity.connection_voltage_kv else "33 kV"
    direction = inp.capacity.binding_direction or "Import"
    season = inp.capacity.binding_season or "Winter"
    dist_km = f"{inp.capacity.distance_km:.2f} km" if inp.capacity.distance_km else "0.50 km"

    verdict_badge = {
        "go": "🟢 **GO** — Project clears feasibility and commercial criteria",
        "maybe": "🟡 **MAYBE** — Project has commercial, grid or community cautions",
        "no_go": "🔴 **NO-GO** — Project fails hurdle rate or faces severe opposition",
    }.get(verdict, verdict.upper())

    lines = [
        f"# Bessible BESS Suitability Assessment — Run `{inp.run_id}`",
        "",
        f"### Verdict: {verdict_badge}",
        "",
        "## Decision Rules Applied",
    ]
    for rule in rules:
        lines.append(f"- {rule}")

    lines.extend([
        "",
        "## Site & Grid Connection Summary",
        f"- **Coordinates:** {inp.site.position.lat:.4f}, {inp.site.position.lon:.4f}",
        f"- **Confirmed Capacity:** {inp.site.capacity_mw:g} MW",
        f"- **Firm Headroom:** {inp.capacity.firm_mw:g} MW",
        f"- **Ceiling Headroom:** {inp.capacity.ceiling_mw:g} MW",
        f"- **Substation:** {sub} ({dist_km})",
        f"- **Voltage:** {volt}",
        f"- **Binding Headroom Constraint:** {direction} ({season})",
        f"- **Project Budget:** {f'£{inp.request.budget_gbp:,.0f}' if inp.request.budget_gbp else 'Uncapped'}",
        "",
        "## Storage Duration Comparison",
        "| Duration | Mid CAPEX (£) | 25-Year NPV (£) | Equity IRR | Payback | Curtailment | Budget Status |",
        "|---|---|---|---|---|---|---|",
    ])

    for case in inp.financial.cases:
        irr_str = f"{case.irr * 100:.1f}%" if case.irr is not None else "N/A"
        pb_str = f"{case.payback_years:.1f}y" if case.payback_years else ">25y"
        curt_str = f"{case.curtailment_pct:.1f}%" if case.curtailment_pct is not None else "0.0%"
        budget_str = "⚠️ **Over Budget**" if case.over_budget else "✅ Within Budget"
        rec_marker = " ⭐️ *(Recommended)*" if case.duration_h == inp.financial.recommended_h else ""
        lines.append(
            f"| **{case.duration_h}h**{rec_marker} | £{case.capex_gbp:,.0f} | £{case.npv_gbp:,.0f} | {irr_str} | {pb_str} | {curt_str} | {budget_str} |"
        )

    # Local Community Sentiment Section
    lines.extend(["", "## Local Community Sentiment & Opposition"])
    if inp.sentiment is not None and inp.sentiment.opposition_index is not None:
        idx = inp.sentiment.opposition_index
        risk_level = "High Opposition" if idx >= 0.8 else ("Moderate Caution" if idx >= 0.5 else "Low Opposition / Supportive")
        lines.extend([
            f"- **Opposition Index:** `{idx:.2f}` / 1.00 ({risk_level})",
            f"- **Top Community Concerns:** {', '.join(inp.sentiment.top_concerns) if inp.sentiment.top_concerns else 'None specified'}",
            f"- **Research Coverage:** {inp.sentiment.sources} local news sources, {inp.sentiment.paragraphs} classified paragraphs",
        ])
    else:
        lines.append("- Local community sentiment analysis was not available for this run.")

    # Analyst Rationale
    if inp.financial.rationale:
        lines.extend([
            "",
            "## Analyst Recommendation & Trade-offs",
            f"> {inp.financial.rationale}",
        ])

    # Key Findings with Citations
    lines.extend(["", "## Key Findings & Evidence Trail"])
    for f in findings:
        cites = ", ".join(f"`{aid}`" for aid in f.artifact_ids)
        lines.append(f"- {f.text} (Evidence: {cites})")

    # Supporting Evidence Artifacts Registry
    lines.extend(["", "## Supporting Evidence Artifacts Registry"])
    for art in inp.artifacts:
        ref = str(art.source_url) if art.source_url else (art.file_path or art.image_path or "N/A")
        lines.append(
            f"- **`[{art.id}]`** (`{art.stage}`): {art.claim} [Source: {ref}] "
            f"(Confidence: {art.confidence * 100:.0f}%, Model: `{art.model_used}`)"
        )

    return "\n".join(lines) + "\n"


async def synthesise(inp: SynthesisInput) -> ReportOutput:
    """Synthesise findings, decision rules, and duration returns into an explainable Markdown report."""
    verdict, rules = decide(inp.financial, inp.sentiment)
    findings = await generate_findings(inp)

    report_content = _render_markdown(inp, verdict, rules, findings)
    report_file_name = "report.md"
    await asyncio.to_thread(_write_report_file, inp.run_id, report_file_name, report_content)

    art_synth = Artifact(
        id=f"synthesis-{inp.run_id[:8]}",
        stage="synthesis",
        claim=f"Assessment report compiled with rule-based verdict '{verdict.upper()}' and duration comparison",
        file_path=report_file_name,
        confidence=0.96,
        model_used="gemini-3.8-flash",
    )

    return ReportOutput(
        verdict=verdict,
        findings=findings,
        report_path=report_file_name,
        artifacts=[art_synth],
    )
