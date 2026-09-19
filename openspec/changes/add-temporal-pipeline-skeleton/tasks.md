## 1. Models and placeholder stages

- [x] 1.1 Write `src/bessible/models.py` with every model from design.md and its validators; verify `uv run python -c "import bessible.models"` works and building an `Artifact` with no evidence raises `ValidationError` in a one-line check
- [x] 1.2 Add `src/bessible/stages/` with the pre-confirmation placeholders (`location`, `capacity`, `title`), including `ZZ99 9ZZ` → out of area and `ZZ99 8ZZ` → not viable; verify calling each with sample input from a Python shell returns a valid output model
- [x] 1.3 Add the analysis placeholders (`grid`, `site_land`, `market`, `financial` with 2/4/8 h cases, `planning`); verify calling each from a Python shell returns a valid output model
- [x] 1.4 Implement `stages/synthesis.py` so every finding cites artifact ids and the report shows the capacity range and duration table; verify calling it with placeholder outputs writes `out/<run_id>/report.md`

## 2. Workflow and worker (rough end-to-end)

- [x] 2.1 Write `activities.py`: nine thin wrappers converting `ValidationError` to a non-retryable `ApplicationError`; verify `uv run python -c "import bessible.activities"` works
- [x] 2.2 Write `workflow.py` with the sequential front (location → capacity → title), the `decide_site` update with validator, the `status` query, and `ConfirmedSite` construction
- [x] 2.3 Write `worker.py` (client with `PydanticAIPlugin`, task queue `bessible`); verify the worker starts against `temporal server start-dev`, and a run started from `temporal workflow start` shows `awaiting_confirmation` through `temporal workflow query --type status`
- [x] 2.4 Add the two parallel groups and synthesis to the workflow; verify in the Temporal UI (http://localhost:8233) that grid, site/land and market start at the same time and the run completes after a confirm update
- [x] 2.5 Check the early exits by hand with the Temporal CLI: reject ends `rejected`, an out-of-range capacity returns an update error and the run stays paused, `ZZ99 9ZZ` ends `out_of_area` and `ZZ99 8ZZ` ends `not_viable`

## 3. CLI

- [x] 3.1 Write `cli.py` `start --detach` and `result`; verify `uv run python -m bessible.cli start <url> --detach` prints a run id and `result` prints the status of an unfinished run
- [x] 3.2 Add the attached `start` flow with progress lines, the y/n and capacity prompt (re-ask on range error), `--yes`, and the final report output; verify a full demo run by hand: start, answer `y`, see the report and folder path
- [x] 3.3 Add `confirm <run-id> [--capacity-mw N] [--reject]`, `--postcode`, `--flexible`, and the Temporal-unavailable message; verify by running with the server stopped (message names `temporal server start-dev`, non-zero exit)

## 4. Resilience and handoff

- [x] 4.1 Add the `BESSIBLE_DEMO_FAIL_ONCE` failure injection in the grid placeholder; verify with the env var set that the run still completes and the Temporal UI shows 2 attempts
- [x] 4.2 Kill the worker after the location stage, restart it, and verify the run resumes at capacity (check the Temporal UI event history)
- [x] 4.3 Add a short "How to replace a stage" section to `README.md` with the nine function signatures; verify a teammate can follow it to swap `site_land` without touching `workflow.py`
