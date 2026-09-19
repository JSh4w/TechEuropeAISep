"""The map session workflow: AI suggests an area, the human edits it on the map, then the engines run.

Contract with `web/` (called by name from the TypeScript client — don't rename without updating it):
    workflow  AssessWorkflow(AssessmentInput) -> SessionState
    query     state() -> SessionState
    update    submit_area(Polygon) -> AreaFeedback
    update    confirm_area() -> SessionState
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    import activities
    from models import (
        AreaFeedback,
        AssessmentInput,
        EngineInput,
        Polygon,
        SessionState,
        ValidateInput,
    )

TASK_QUEUE = "bessible-web"  # separate from sandbox/workflow_demo.py, whose worker uses "bessible"
ACTIVITY_OPTS = {"start_to_close_timeout": timedelta(seconds=60), "retry_policy": RetryPolicy(maximum_attempts=3)}


@workflow.defn
class AssessWorkflow:
    """One map session: one property, from AI suggestion through human edits to the verdict."""

    def __init__(self) -> None:
        """Start with an empty session; `run` fills it in."""
        self._state = SessionState()
        self._confirmed = False

    @workflow.query
    def state(self) -> SessionState:
        """Everything the map renders; polled by the frontend."""
        return self._state

    @workflow.update
    async def submit_area(self, area: Polygon) -> AreaFeedback:
        """Human moved points on the map: validate the new area and return feedback straight to the map."""
        s = self._state
        # guaranteed by the validator (stage is awaiting_human)
        assert s.input is not None  # ruff: ignore[assert]
        assert s.title_boundary is not None  # ruff: ignore[assert]
        feedback = await workflow.execute_activity(
            activities.validate_area,
            ValidateInput(inp=s.input, area=area, title_boundary=s.title_boundary),
            **ACTIVITY_OPTS,
        )
        s.current_area, s.feedback = area, feedback
        s.edits += 1
        return feedback

    @submit_area.validator
    def _validate_submit(self, area: Polygon) -> None:
        if self._state.stage != "awaiting_human":
            msg = f"Not accepting edits while {self._state.stage}"
            raise ValueError(msg)
        if not area.coordinates or len(area.coordinates[0]) < 4:  # ruff: ignore[magic-value-comparison]
            msg = "Polygon needs at least 3 points"
            raise ValueError(msg)

    @workflow.update
    def confirm_area(self) -> SessionState:
        """Human accepts the current area; the engines run next."""
        self._confirmed = True
        return self._state

    @confirm_area.validator
    def _validate_confirm(self) -> None:
        if self._state.stage != "awaiting_human":
            msg = f"Not accepting confirmation while {self._state.stage}"
            raise ValueError(msg)
        if not (self._state.feedback and self._state.feedback.ok):
            msg = "Fix the issues with the area before confirming"
            raise ValueError(msg)

    @workflow.run
    async def run(self, inp: AssessmentInput) -> SessionState:
        """Suggest an area, wait for the human to confirm it, then run the engines."""
        s = self._state
        s.input = inp

        s.step = "AI agent is suggesting an area"
        suggestion = await workflow.execute_activity(activities.suggest_area, inp, **ACTIVITY_OPTS)
        s.title_boundary, s.suggested_area = suggestion.title_boundary, suggestion.area
        s.suggestion_rationale = suggestion.rationale
        s.artifacts += suggestion.artifacts
        s.current_area = suggestion.area
        s.feedback = await workflow.execute_activity(
            activities.validate_area,
            ValidateInput(inp=inp, area=suggestion.area, title_boundary=suggestion.title_boundary),
            **ACTIVITY_OPTS,
        )

        # Human in the loop: wait for the map to confirm (submit_area may be called any number of times first)
        s.stage, s.step = "awaiting_human", "Waiting for you to adjust and confirm the area"
        await workflow.wait_condition(lambda: self._confirmed)
        await workflow.wait_condition(workflow.all_handlers_finished)

        s.stage = "assessing"
        assert s.current_area is not None  # ruff: ignore[assert]
        assert s.feedback is not None  # ruff: ignore[assert]
        engine_in = EngineInput(inp=inp, area=s.current_area, feedback=s.feedback)

        s.step = "Feasibility: planning policy and battery size"
        s.feasibility = await workflow.execute_activity(activities.run_feasibility, engine_in, **ACTIVITY_OPTS)
        s.artifacts += s.feasibility.artifacts

        s.step = "Suitability: local news and financials"
        s.suitability = await workflow.execute_activity(activities.run_suitability, engine_in, **ACTIVITY_OPTS)
        s.artifacts += s.suitability.artifacts

        score = (s.feasibility.score + s.suitability.score) / 2
        s.verdict = f"{'Promising' if score >= 0.5 else 'Not recommended'} (score {score:.2f})"  # ruff: ignore[magic-value-comparison]
        s.stage, s.step = "done", "Done"
        return s
