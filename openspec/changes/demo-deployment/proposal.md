## Why

We want to deploy a standalone demo version of Bessible on an Ubuntu VM where each visitor uses their own Google AI key (never the team's quota), the operator can optionally switch on the Modal classifier server-side, and anyone can still watch a full demo run with no keys at all. The VM must stay small (single modest VPS) and secure enough to hold other people's keys.

**Owner**: Josh

## What Changes

- **Locked BYOK**: Users supply one credential, a **Google AI (Gemini) API key (required)**. No other providers (OpenAI, Anthropic, OpenRouter are out of scope). Modal is **not** BYOK: it is an operator-side setting.
- **Firebase Auth (Google sign-in) on the free Spark plan** gates the config panel and every run endpoint. Runs are owned by the signed-in `uid`.
- **Encrypted key storage in SQLite on the VM**: keys are encrypted (AES-GCM, per-user key derived from a server master secret, `uid` bound as associated data) and never returned to the browser.
- **Per-run key isolation**: a run only ever uses its own owner's key, resolved at run time. No module-level models, no shared key state, no server-key fallback for real runs.
- **Switchable classifier backends** (`modal | llm | heuristic`): Modal stays as an optional, operator-configured backend (server-side token, independent second opinion for policy `cross_check`); when the operator has not enabled it, classification falls back to Gemini structured output using the run owner's key, then to the offline heuristic. `modal` becomes an optional dependency instead of being removed.
- **Demo mode**: record one real run (request, trace events, status snapshots, HITL decision, result) and replay it with no keys, no auth and no LLM calls. A first-load modal offers "Configure keys" or "View demo run" when no keys are configured (UI details to be configured later).
- **Lightweight VM deployment**: single Ubuntu VM with the standalone Temporal dev server (SQLite), Next.js standalone build, Caddy with automatic HTTPS, and a hardening baseline (firewall, loopback-only internals, non-root systemd units).

## Non-goals

- Payments, billing, roles, or multi-tenant admin.
- KMS / Secret Manager (paid Firebase Blaze plan required; we stay on the free Spark plan).
- Merging these changes back into `main` (this work is isolated to branch `demo-deployment`).
- Deploying a distributed multi-node Temporal cluster.

## Capabilities

### New Capabilities

- `byok-inference`: Google-key BYOK, Firebase-authenticated encrypted key storage, per-run key isolation.
- `classifier-backends`: Switchable `modal | llm | heuristic` text classification with recorded provenance.
- `demo-mode`: Record a real run and replay it keyless.
- `vm-deployment-runtime`: Lightweight single-VM orchestration, reverse proxy, and hardening baseline.

### Modified Capabilities

None.

## Impact

- Affected files: `src/bessible/llm.py`, `src/bessible/classifier.py`, `src/bessible/config.py`, `src/bessible/api/runs.py`, `src/bessible/api/events.py`, `src/bessible/models.py`, `src/bessible/workflow.py`, the agent modules (`suitability/research.py`, `suitability/analyst.py`, `suitability/verdict.py`, `planning/evidence.py`, `possibility/policy.py`, `location/extract.py`), `scripts/check_env.py`, `pyproject.toml`, `web/src/components/`, `web/src/lib/api.ts`, deployment configs / scripts.
- New: key store (SQLite), auth guard, `data/demo/` recordings, replay routes, Firebase project (Spark plan).
- Dependencies: `modal` moves to an optional extra; adds `cryptography` (key encryption) and `cachecontrol` (caches Google's public certs). Firebase ID tokens are verified with `google-auth`, which is already installed; `firebase-admin` is not used.
