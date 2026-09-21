from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from bessible.classifier import Classified
from bessible.location.models import SourceDocument
from bessible.models import SynthesisInput
from bessible.possibility import assess, policy
from bessible.possibility.pipeline import artifact_from, site_land_output
from bessible.possibility.policy import PolicyFinding, PolicyOpinion, PolicyReview, QuoteLabels

from .test_hard import FloodRisk, Locality, propose

PLAN = SourceDocument(kind="local_plan", title="Test Local Plan", url="https://example.org/plan.pdf")
QUOTE = "Proposals for standalone renewable energy schemes will be supported."


@pytest.fixture
def anyio_backend():
    return "asyncio"


def finding(effect="conditions"):
    return PolicyFinding(policy="Core Policy 42", effect=effect, quote=QUOTE, source_url=PLAN.url)


def opinion(stance="conditional", findings=None):
    return PolicyOpinion(
        stance=stance, summary="Allowed if impacts are resolved [1.2].", findings=findings or [finding()]
    )


def with_plan(**site):
    proposal = propose(locality=Locality(country="England", planning_authority="Testshire"), **site)
    proposal.location.agentic.documents = [
        PLAN,
        SourceDocument(kind="designation", title="A church", url="https://x.org"),
    ]
    return proposal


def answering(reply: PolicyOpinion) -> TestModel:
    return TestModel(custom_output_args=reply.model_dump(), call_tools=[])


def test_brief_carries_the_site_facts_and_only_policy_documents():
    brief = policy.brief_for(with_plan(flood=FloodRisk(zone=2, zone_2_pct=30, zone_3_pct=0)))
    assert brief.planning_authority == "Testshire"
    assert [d.kind for d in brief.documents] == ["local_plan"]
    assert any("Flood Zone" in fact for fact in brief.land_facts)


@pytest.mark.anyio
async def test_read_policy_returns_a_typed_review():
    review = await policy.read_policy(policy.brief_for(with_plan()), model=answering(opinion()), web=False)
    assert review.opinion.stance == "conditional"
    assert review.opinion.summary == "Allowed if impacts are resolved."  # grounding markers stripped
    check = policy.policy_check(review)
    assert (check.outcome, check.facts, check.source_urls) == ("warn", {"Core Policy 42": "conditions"}, [PLAN.url])
    assert check.produced_by != "deterministic rule"


@pytest.mark.anyio
async def test_nothing_to_read_never_calls_the_model():
    review = await policy.read_policy(policy.brief_for(propose()), model=None)
    assert (review.opinion.stance, review.model_used) == ("silent", "none")
    assert policy.policy_check(review).outcome == "unknown"


@pytest.mark.parametrize(
    "bad",
    [
        PolicyOpinion(stance="conditional", summary="No findings."),
        PolicyOpinion(stance="hard_denied", summary="Says denied, cites only a condition.", findings=[finding()]),
    ],
)
def test_validator_rejects_unsupported_stances(bad):
    with pytest.raises(policy.ModelRetry):
        policy.stance_matches_findings(bad)
    assert policy.stance_matches_findings(opinion("hard_denied", [finding("prohibits")])).stance == "hard_denied"


@pytest.mark.anyio
async def test_cross_check_lowers_confidence_when_the_classifier_disagrees(monkeypatch):
    async def fake_classify(quotes, _schema, **_kwargs):
        return [
            Classified[QuoteLabels](text=q, labels=QuoteLabels(effect="prohibits"), confidence={"effect": 0.8})
            for q in quotes
        ]

    monkeypatch.setattr(policy, "classify", fake_classify)
    review = PolicyReview(brief=policy.brief_for(with_plan()), opinion=opinion(), model_used="gemini")
    checked = await policy.cross_check(review)
    assert (checked.confidence, checked.disputed_quotes) == (policy.UNVERIFIED_CONFIDENCE, [QUOTE])
    assert "Modal" in checked.model_used


@pytest.mark.anyio
async def test_cross_check_is_skipped_without_modal(monkeypatch):
    monkeypatch.setattr("bessible.classifier.modal_enabled", lambda: False)
    review = PolicyReview(brief=policy.brief_for(with_plan()), opinion=opinion(), model_used="gemini")
    assert await policy.cross_check(review) == review  # default confidence, nothing disputed, no model added


@pytest.mark.anyio
async def test_cross_check_is_skipped_when_modal_fails(monkeypatch):
    class Down:
        classify = remote = property(lambda self: self)

        async def aio(self, *_args):
            msg = "modal is down"
            raise RuntimeError(msg)

    import modal

    monkeypatch.setattr("bessible.classifier.modal_enabled", lambda: True)
    monkeypatch.setattr(modal.Cls, "from_name", lambda *_a, **_k: Down)
    review = PolicyReview(brief=policy.brief_for(with_plan()), opinion=opinion(), model_used="gemini")
    assert await policy.cross_check(review) == review


@pytest.mark.anyio
async def test_blocked_sites_skip_the_agent():
    blocked = with_plan(flood=FloodRisk(zone=3, zone_2_pct=0, zone_3_pct=95))
    report = await policy.assess_with_policy(blocked, model=None)  # would raise if the model were needed
    assert not report.possible
    assert "policy_allows_battery_storage" not in {c.name for c in report.checks}


@pytest.mark.anyio
async def test_hard_denied_policy_blocks_the_site():
    denied = opinion("hard_denied", [finding("prohibits")])
    report = await policy.assess_with_policy(with_plan(), model=answering(denied), web=False)
    assert not report.possible
    assert report.checks[-1].name == "policy_allows_battery_storage"


def test_checks_become_pipeline_artifacts():
    proposal = with_plan(flood=FloodRisk(zone=2, zone_2_pct=30, zone_3_pct=0))
    report = assess(proposal)
    output = site_land_output(proposal, report, run_id="bessible-1234")
    assert output.constraints == report.caveats
    assert {a.stage for a in output.artifacts} == {"site_land"}
    assert len({a.id for a in output.artifacts}) == len(output.artifacts)
    assert artifact_from(report.checks[0].model_copy(update={"source_urls": []}), "run") is None
    assert "site_land" in SynthesisInput.model_fields  # the collation class these feed
