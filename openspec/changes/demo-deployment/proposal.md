## Why

We want to deploy a standalone demo version of Bessible on an Ubuntu VM without requiring a personal Gemini API quota, without depending on external Modal GPU infrastructure or accounts, and with minimal overhead for running Temporal on a single modest VPS.

**Owner**: Josh

## What Changes

- **Multi-provider BYOK inference**: Allow users/testers to provide their own API key (OpenAI, Gemini, Anthropic, OpenRouter) via the web UI or server environment variables instead of hardcoding Google Gemini.
- **Decouple Modal**: Eliminate the dependency on the remote `bessible-classifier` Modal app by replacing it with a structured-output LLM call using the active BYOK provider, backed by an offline heuristic fallback.
- **Lightweight VM deployment**: Configure the app stack to run on a single Ubuntu VM using the lightweight standalone Temporal CLI dev server (`temporal server start-dev` with SQLite), Next.js standalone build, and Caddy reverse proxy with automatic HTTPS.

## Non-goals

- Production multi-tenant auth or database billing.
- Merging these changes back into `main` (this work is isolated to branch `demo-deployment`).
- Deploying a distributed multi-node Temporal cluster.

## Capabilities

### New Capabilities

- `byok-inference`: Dynamic LLM provider selection and API key injection from UI or environment.
- `modal-decoupling`: In-process / LLM-based text classification replacing external Modal GPU calls.
- `vm-deployment-runtime`: Lightweight single-VM orchestration and service management for Temporal, API, worker, and web frontend.

### Modified Capabilities

None.

## Impact

- Affected files: `src/bessible/llm.py`, `src/bessible/classifier.py`, `src/bessible/config.py`, `src/bessible/api/runs.py`, `src/bessible/models.py`, `web/src/components/`, `web/src/lib/api.ts`, deployment configs / scripts.
- Dependencies: Removes `modal` requirement for running the app; adds support for standard OpenAI/Anthropic/OpenRouter providers via Pydantic AI.
