## Purpose

Makes text classification switchable between Modal (optional, operator-enabled, independent), Gemini structured output, and an offline heuristic, so the app runs without Modal while keeping Modal available as an independent second opinion.

## ADDED Requirements

### Requirement: Switchable classifier backend
The system SHALL classify text against Pydantic schemas using one of three backends: `modal` (when the operator has enabled it with a server-side Modal token), `llm` (Gemini structured output using the run owner's Google key), or `heuristic` (offline keyword rules). `CLASSIFIER_BACKEND` (`auto`, `modal`, `llm`, `heuristic`; default `auto`) MAY force a backend. Users SHALL NOT supply Modal credentials, and the Modal token SHALL NOT appear in workflow input.

#### Scenario: Operator enabled Modal
- **WHEN** classification is requested and the worker has a Modal token and `CLASSIFIER_BACKEND` is `auto` or `modal`
- **THEN** the `modal` backend is used and returns validated `Classified` items with per-field confidence

#### Scenario: Google key only
- **WHEN** classification is requested, the worker has no Modal token, and the run has a Google key
- **THEN** the `llm` backend classifies with Gemini structured output and returns validated `Classified` items

#### Scenario: No keys
- **WHEN** classification is requested with no credentials
- **THEN** the `heuristic` backend returns valid labels without any network call

### Requirement: Fallback on failure
A backend error SHALL step down to the next backend (`modal`, then `llm`, then `heuristic`) without failing the assessment run.

#### Scenario: Modal unavailable
- **WHEN** the `modal` backend raises an error
- **THEN** the classifier falls back to `llm`, or to `heuristic` if `llm` is unavailable, and the run continues

### Requirement: Backend provenance and independence
The recorded `model_used` SHALL name the backend that produced each label. Policy `cross_check` SHALL count as an independent second opinion, and raise confidence, only when produced by the `modal` backend.

#### Scenario: Cross-check on Gemini or heuristic
- **WHEN** `cross_check` is labelled by the `llm` or `heuristic` backend
- **THEN** the result is marked non-independent and confidence is not uplifted

### Requirement: Modal is an optional dependency
The application SHALL import and start without the `modal` package installed. Modal login checks in `scripts/check_env.py` SHALL run only when a server-side Modal token is configured.

#### Scenario: Start without Modal installed
- **WHEN** the API and worker start in an environment without `modal`
- **THEN** they start normally and classification uses `llm` or `heuristic`
