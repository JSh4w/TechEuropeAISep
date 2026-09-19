## Context

Bessible was built to run locally on a Mac with Google Gemini for LLM reasoning, Modal for GPU-backed DeBERTa classification, and a local Temporal dev server. Deploying a public or self-serve demo on an Ubuntu VPS requires:
1. Enabling evaluators to bring their own LLM keys (OpenAI, Gemini, Anthropic, OpenRouter) or running on server defaults without burning specific Gemini quotas.
2. Decoupling Modal entirely to eliminate GPU cold starts and Modal billing/credentials.
3. Keeping Temporal's resource footprint ultra-light so the full stack operates reliably on a modest VM (<1 GB RAM total).

## Goals / Non-Goals

**Goals:**
- Provide a unified LLM factory supporting OpenAI, Gemini, Anthropic, and OpenRouter with runtime key injection.
- Add a BYOK settings dialog to the Next.js web UI persisting keys to `localStorage`.
- Replace `src/bessible/classifier.py`'s Modal dependency with an LLM structured-output classifier and heuristic fallback.
- Standardize the single-VM deployment runtime using standalone `temporal server start-dev` (embedded SQLite) supervised by systemd or Docker Compose.

**Non-Goals:**
- User accounts, server-side database persistence for user keys, or payment metering.
- Multi-region or HA distributed Temporal cluster setups.

## Decisions

### 1. Unified Model Factory in `bessible.llm`
**Decision:** Replace the static `gemini_model()` factory with a parameterised `get_model(provider, api_key, model_name)` function backed by Pydantic AI's native providers (`GoogleModel`, `OpenAIChatModel`, `AnthropicModel`).
**Interface:**
```python
def get_model(
    provider: Literal["google", "openai", "anthropic", "openrouter"] | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
) -> Model: ...
```
*Rationale:* Pydantic AI already supports all these providers. Passing `api_key` explicitly avoids polluting global process environment variables across concurrent demo requests.
*Alternatives considered:* LiteLLM proxy (adds another running daemon and memory overhead) vs direct Pydantic AI providers (chosen: zero overhead, native typing).

### 2. Request Payload & Header BYOK Propagation
**Decision:** Extend `AssessmentRequest` with optional model credentials:
```python
class AssessmentRequest(BaseModel):
    # existing fields...
    llm_provider: Literal["google", "openai", "anthropic", "openrouter"] | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
```
The FastAPI router extracts `X-LLM-Provider`, `X-LLM-Key`, and `X-LLM-Model` headers or request body fields and passes them into the workflow input.
*Alternatives considered:* Server-only `.env` (doesn't let different demo users supply their own keys).

### 3. Modal Elimination via Structured LLM Classification
**Decision:** Re-implement `classify[T: BaseModel](paragraphs: list[str], schema: type[T])` in `src/bessible/classifier.py`:
- Formats paragraphs and the schema into a structured prompt using Pydantic AI's output validation.
- Runs against the active BYOK LLM (or falls back to the deterministic keyword heuristic if no keys are available).
*Rationale:* `open-jev-deberta-v3-large` on Modal was only doing zero-shot boolean and literal choice labelling. Modern small models (`gpt-4o-mini`, `gemini-1.5-flash`) perform this with higher reliability, lower latency (400ms vs 20s cold start), and zero GPU infrastructure.

### 4. Temporal Standalone Dev Binary for VM Deployment
**Decision:** Use the standalone `temporal` CLI binary with embedded SQLite rather than the `temporalio/auto-setup` Docker container.
- Command: `temporal server start-dev --db-filename /var/lib/bessible/temporal.db --headless --ip 127.0.0.1`
- Footprint: ~50 MB RAM, SQLite persistence across restarts, zero Docker compose network overhead.
- Supervised via a simple `systemd` unit or lightweight compose service.

### 5. Web Proxy & Reverse Proxy Configuration
**Decision:** Provide a Caddy configuration (`Caddyfile`) handling HTTPS automatically via Let's Encrypt:
- `/runs/{id}/events` -> FastAPI (SSE proxying with `flush_interval -1` to prevent event buffering).
- `/runs`, `/capacity`, `/site-data` -> FastAPI (`:8000`).
- Everything else -> Next.js standalone server (`:3000`).

## Risks / Trade-offs

- **[Risk] WebSearch grounding differs across providers** → *Mitigation*: When using providers without native Google Search grounding (like OpenAI/Anthropic), fallback to the deterministic cached news fixtures in `data/fixtures/news/`, which are already supported by `research.py`.
- **[Risk] User enters invalid API key** → *Mitigation*: The settings UI provides a "Test Key" button that runs a quick, cheap completion ping (`Agent.run("ping")`) to verify validity before starting a run.
- **[Risk] Single-node SQLite database corruption on abrupt VM shutdown** → *Mitigation*: Temporal dev server handles SQLite transactions cleanly with WAL mode; runs can be cleared or re-created freely in demo environments.
