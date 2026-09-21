## Purpose

Makes text classification switchable between Modal (optional, operator-enabled, independent), Gemini structured output, and an offline keyword fallback, so the app runs without Modal while keeping Modal available as an independent second opinion. Without Modal, the cross-check is skipped instead of being done by the same Gemini model.

## ADDED Requirements

### Requirement: Switchable classifier backend
The system SHALL classify text against Pydantic schemas using one of three backends: `modal` (when the operator has enabled it with a server-side Modal token), `llm` (Gemini structured output using the run owner's Google key), or `heuristic` (offline keyword rules, news-paragraph labels only). `CLASSIFIER_BACKEND` (`auto`, `modal`, `llm`, `heuristic`; default `auto`) MAY force a backend. Users SHALL NOT supply Modal credentials, and the Modal token SHALL NOT appear in workflow input.

#### Scenario: Operator enabled Modal
- **WHEN** classification is requested and the worker has a Modal token and `CLASSIFIER_BACKEND` is `auto` or `modal`
- **THEN** the `modal` backend is used and returns validated `Classified` items with per-field confidence

#### Scenario: Google key only
- **WHEN** news-paragraph classification is requested, the worker has no Modal token, and the run has a Google key
- **THEN** the `llm` backend classifies with Gemini structured output and returns validated `Classified` items

### Requirement: Fallback on failure
A backend error SHALL step down to the next backend (`modal`, then `llm`, then `heuristic`) for news-paragraph classification without failing the assessment run.

#### Scenario: Modal unavailable
- **WHEN** the `modal` backend raises an error during news-paragraph classification
- **THEN** the classifier falls back to `llm`, or to `heuristic` if `llm` also fails, and the run continues

### Requirement: Heuristic fallback
The `heuristic` backend SHALL be the existing keyword fallback, unchanged. It SHALL run only when the model backends fail during a real run and SHALL cover only the news-paragraph labels.

#### Scenario: All model backends fail
- **WHEN** news-paragraph classification is requested and both `modal` and `llm` fail
- **THEN** the `heuristic` backend returns valid labels and the run continues

### Requirement: Independent cross-check
Policy `cross_check` SHALL run only on the `modal` backend, because a Gemini check of a Gemini finding is not independent. When `modal` is not enabled or fails, `cross_check` SHALL be skipped and the review SHALL keep the default confidence it has before any cross-check. No labels or fields SHALL be renamed or added.

#### Scenario: Cross-check with Modal
- **WHEN** a policy finding is cross-checked and the `modal` backend is available
- **THEN** each quote is independently labelled, disagreements are recorded, and confidence reflects the agreement

#### Scenario: Cross-check without Modal
- **WHEN** a policy finding would be cross-checked and Modal is not enabled or fails
- **THEN** the check is skipped and the review keeps its default confidence

### Requirement: Modal is an optional dependency
The application SHALL import and start without the `modal` package installed. Modal login checks in `scripts/check_env.py` SHALL run only when a server-side Modal token is configured.

#### Scenario: Start without Modal installed
- **WHEN** the API and worker start in an environment without `modal`
- **THEN** they start normally, news-paragraph classification uses `llm`, and the policy cross-check is skipped
