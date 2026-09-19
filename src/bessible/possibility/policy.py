"""The agentic possibility check: does local planning policy flatly refuse a battery here?

    brief = brief_for(proposal, hard_report)       Proposal -> PolicyBrief     what the agent is told (pure)
    review = await read_policy(brief)              PolicyBrief -> PolicyReview  Gemini reads the plan (search + fetch)
    check = policy_check(review)                   PolicyReview -> Check        slots in beside the hard checks

Councils block plain downloads of their plans (403 / SharePoint logins), so the documents in `Agentic` are given to
the model as URLs and read with its native web tools rather than fetched by us. That also means the quotes cannot be
checked against the source here: `cross_check` asks the typed classifier on Modal to label each quote independently,
and disagreement lowers the confidence.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.capabilities import WebFetch, WebSearch

from bessible.classifier import MODEL_NAME as CLASSIFIER_NAME
from bessible.classifier import classify
from bessible.llm import gemini_model
from bessible.location.models import SourceDocument

from .hard import assess
from .models import Check, Outcome, PossibilityReport, Proposal

if TYPE_CHECKING:
    from pydantic_ai.models import Model

POLICY_DOCUMENT_KINDS = ("local_plan", "article_4_direction")
Effect = Literal["supports", "conditions", "restricts", "prohibits"]
Stance = Literal["supportive", "conditional", "hard_denied", "silent"]
OUTCOME_OF: dict[Stance, Outcome] = {
    "supportive": "pass",
    "conditional": "warn",
    "hard_denied": "fail",
    "silent": "unknown",
}
GROUNDING_MARKERS = re.compile(r"\s*\[\d[\d., ]*\]")  # "[1.2.7, 6.1.1]" left in the text by search grounding
UNVERIFIED_CONFIDENCE = 0.6  # the model read the plan itself; nothing checked its quotes


# --------------------------------------------- classes ------------------------------------------ #


class PolicyBrief(BaseModel):
    """Everything the policy reader is told about the proposal. Sent to the model as JSON."""

    battery_mw: float
    duration_h: int
    site_area_ha: float | None = None
    address: str | None = None
    country: str | None = None
    planning_authority: str | None = None
    land_facts: list[str] = Field(default_factory=list, description="What the deterministic checks found on the site.")
    documents: list[SourceDocument] = Field(default_factory=list, description="The authority's plan documents to read.")


class PolicyFinding(BaseModel):
    """One policy that bears on a battery at this site."""

    policy: str = Field(description="The policy's reference in the plan, e.g. 'Core Policy 42'.")
    effect: Effect = Field(description="What the policy does to this proposal.")
    quote: str = Field(description="The policy's own wording, copied verbatim, at most 40 words.")
    source_url: str = Field(description="The URL the wording was read at.")


class PolicyOpinion(BaseModel):
    """The model's reading of local policy. `hard_denied` only when a policy prohibits the proposal outright."""

    stance: Stance = Field(
        description="supportive = policy backs it; conditional = allowed if site impacts are resolved; "
        "hard_denied = a policy flatly prohibits it here; silent = no relevant policy could be read."
    )
    summary: str = Field(description="Two or three sentences a developer can act on.")
    findings: list[PolicyFinding] = Field(default_factory=list)


class QuoteLabels(BaseModel):
    """What the typed classifier on Modal is asked about each quote (field descriptions are its questions)."""

    effect: Effect = Field(description="What this planning policy text does to a new battery energy storage site.")


class PolicyReview(BaseModel):
    """The opinion plus how it was produced."""

    brief: PolicyBrief
    opinion: PolicyOpinion
    model_used: str
    confidence: float = Field(default=UNVERIFIED_CONFIDENCE, ge=0, le=1)
    disputed_quotes: list[str] = Field(default_factory=list, description="Quotes the classifier labelled differently.")


# ---------------------------------------------- agent ------------------------------------------- #

INSTRUCTIONS = """\
You screen sites for battery energy storage systems (BESS) in the UK. You are given a proposal as JSON.
Decide one thing: does the local planning authority's adopted policy flatly refuse this development at this site?

- Read the documents listed in the brief with web fetch; use web search to find the plan's renewable, low-carbon
  energy, energy storage and countryside / settlement-boundary policies when a document cannot be opened.
- Weigh the policies against the site's land facts (green belt, farmland grade, flood zone, designations).
- Quote policy wording verbatim and give the URL you read it at. Never invent a policy reference or a quote.
- 'hard_denied' needs a policy that prohibits the proposal outright. Criteria to satisfy are 'conditional'.
- If you could not read any relevant policy, answer 'silent' with no findings.
"""


def stance_matches_findings(opinion: PolicyOpinion) -> PolicyOpinion:
    if opinion.stance != "silent" and not opinion.findings:
        msg = "Give at least one finding with a verbatim quote, or answer 'silent'."
        raise ModelRetry(msg)
    if opinion.stance == "hard_denied" and not any(f.effect == "prohibits" for f in opinion.findings):
        msg = "'hard_denied' needs a finding whose effect is 'prohibits'. Otherwise the stance is 'conditional'."
        raise ModelRetry(msg)
    if any(not f.source_url.startswith("http") for f in opinion.findings):
        msg = "Every finding needs the http(s) URL its wording was read at."
        raise ModelRetry(msg)
    return opinion.model_copy(update={"summary": GROUNDING_MARKERS.sub("", opinion.summary).strip()})


def _policy_reader(*, web: bool) -> Agent[None, PolicyOpinion]:
    agent = Agent(
        name="policy_reader" if web else "policy_reader_offline",
        output_type=PolicyOpinion,
        instructions=INSTRUCTIONS,
        capabilities=[WebSearch(), WebFetch()] if web else [],
        defer_model_check=True,  # the model needs a key from settings, so it is supplied per run
    )
    agent.output_validator(stance_matches_findings)
    return agent


policy_reader = _policy_reader(web=True)  # Gemini: opens the plan itself with native search + fetch
offline_policy_reader = _policy_reader(web=False)  # models without native web tools (Modal-hosted, tests)


# -------------------------------------------- functions ----------------------------------------- #


def brief_for(proposal: Proposal, hard_report: PossibilityReport | None = None) -> PolicyBrief:
    location, report = proposal.location, hard_report or assess(proposal)
    where = location.deterministic.locality
    return PolicyBrief(
        battery_mw=proposal.battery_mw,
        duration_h=proposal.duration_h,
        site_area_ha=location.title.area_ha if location.title else None,
        address=where.address,
        country=where.country,
        planning_authority=where.planning_authority,
        land_facts=report.blockers + report.caveats,
        documents=[d for d in location.agentic.documents if d.kind in POLICY_DOCUMENT_KINDS],
    )


async def read_policy(brief: PolicyBrief, model: Model | None = None, *, web: bool = True) -> PolicyReview:
    if not brief.planning_authority and not brief.documents:
        nothing_to_read = PolicyOpinion(stance="silent", summary="No planning authority or plan document is known.")
        return PolicyReview(brief=brief, opinion=nothing_to_read, model_used="none")
    reader, model = policy_reader if web else offline_policy_reader, model or gemini_model()
    run = await reader.run(brief.model_dump_json(indent=1, exclude_none=True), model=model)
    return PolicyReview(brief=brief, opinion=run.output, model_used=model.model_name)


async def cross_check(review: PolicyReview) -> PolicyReview:
    """A second, independent label for every quote from the typed classifier on Modal."""
    findings = review.opinion.findings
    if not findings:
        return review
    labelled = await classify([f.quote for f in findings], QuoteLabels)
    disputed = [f.quote for f, second in zip(findings, labelled, strict=True) if second.labels.effect != f.effect]
    agreement = 1 - len(disputed) / len(findings)
    return review.model_copy(
        update={
            "confidence": round(UNVERIFIED_CONFIDENCE + (0.9 - UNVERIFIED_CONFIDENCE) * agreement, 2),
            "disputed_quotes": disputed,
            "model_used": f"{review.model_used} + {CLASSIFIER_NAME}",
        }
    )


def policy_check(review: PolicyReview) -> Check:
    opinion = review.opinion
    return Check(
        name="policy_allows_battery_storage",
        outcome=OUTCOME_OF[opinion.stance],
        reason=opinion.summary,
        facts={f.policy: f.effect for f in opinion.findings},
        source_urls=list(dict.fromkeys(f.source_url for f in opinion.findings)),
        produced_by=review.model_used,
        confidence=review.confidence,
    )


async def assess_with_policy(proposal: Proposal, model: Model | None = None, *, web: bool = True) -> PossibilityReport:
    """The hard checks, then (only if nothing already blocks the site) the policy reader."""
    report = assess(proposal)
    if not report.possible:
        return report
    check = policy_check(await read_policy(brief_for(proposal, report), model, web=web))
    return PossibilityReport(
        possible=check.outcome != "fail",
        checks=[*report.checks, check],
        blockers=report.blockers + ([check.reason] if check.outcome == "fail" else []),
        caveats=report.caveats + ([check.reason] if check.outcome == "warn" else []),
        unknowns=report.unknowns + ([check.name] if check.outcome == "unknown" else []),
    )
