## Context

Bessible was built to run locally on a Mac with Google Gemini for LLM reasoning, Modal for GPU-backed DeBERTa classification, and a local Temporal dev server. Deploying a self-serve demo on an Ubuntu VPS requires:
1. Each visitor brings their own **Google AI key** (required), so no one burns the team's quota. Modal, if used, is switched on by the operator server-side.
2. Holding other people's keys safely on a small VM, and guaranteeing one user's key can never reach another user's run.
3. A keyless **demo replay** so a visitor can see the product before configuring anything.
4. A small footprint so the full stack runs on a modest VM (target <1 GB RAM total; to be measured).

## Goals / Non-Goals

**Goals:**
- One user credential: the Google key. No other providers. Modal is operator-side, not BYOK.
- Firebase Auth (Google sign-in, free Spark plan) identifies users; runs and stored keys are owned by `uid`.
- Keys encrypted at rest in SQLite on the VM, never returned to the browser, never plaintext in Temporal history.
- Structural guarantee of per-run key isolation, proven by a concurrency test.
- Switchable classifier backend (`modal | llm | heuristic`) with provenance in `model_used`.
- Record a real run once, replay it with no keys, auth, Temporal, or LLM.
- Single-VM runtime: standalone `temporal server start-dev` (SQLite), systemd, Caddy, hardened baseline.

**Non-Goals:**
- Payments, billing, roles, admin UI.
- KMS / Secret Manager (needs paid Blaze plan).
- Multi-region or HA distributed Temporal cluster setups.

## Decisions

### 1. Identity: Firebase Auth (Google sign-in)
**Decision:** The web app signs users in with the Firebase JS SDK. Every non-demo request carries `Authorization: Bearer <Firebase ID token>`. FastAPI verifies it with `google-auth` (see below) in a `current_user` dependency and yields `uid` (and email). An optional `ALLOWED_EMAILS` env list restricts who may sign in for the demo.
- Free tier: Google sign-in is covered by the Spark plan (50K monthly users). Avoid Identity Platform features (MFA, blocking functions), which need an upgrade.
- **Verify with `google-auth`, not `firebase-admin`.** Tested: `firebase-admin` (7.6.0) initializes Application Default Credentials and raises `DefaultCredentialsError` on `verify_id_token` when none exist, so it would need a service-account file on the VM. `google.oauth2.id_token.verify_firebase_token(token, request, audience=<project id>)` needs no credentials: it fetches Google's public certs and checks signature, expiry and audience. `google-auth` and `requests` are already installed. Add an explicit `iss == https://securetoken.google.com/<project id>` check (the library does not check it) and a non-empty `sub`. Wrap the request in a `cachecontrol` session so Google's certs are cached instead of fetched on every call, and run the sync verify off the event loop.
- Test coverage so far: a forged token reaches Google's cert lookup without any credentials and fails only on the unknown key id. A real Firebase token has not been verified end to end; do that once in the auth task.
- `EventSource` cannot set headers, so the SSE client switches to a `fetch`-based stream that sends the bearer token. ID tokens are re-checked per request; the Firebase SDK refreshes them.
- Demo replay routes are **public** (no sign-in) so visitors can see the product first.
*Alternatives considered:* per-run bearer token / cookie (no accounts, but no key persistence and more bespoke code); Caddy basic auth (10 minutes, no per-user ownership).

### 2. Run ownership
**Decision:** `POST /runs` creates the workflow with id `bessible-<uuid4>` (full 122-bit UUID, not 8 hex) and stores `owner_uid` in the workflow memo. Every `/runs/{id}/status|decision|result|events` handler loads the owner and returns 404 (not 403) if it differs from the caller's `uid`. Event files stay in `out/<run_id>/`, gated by the same check.

### 3. Key storage: encrypted SQLite on the VM
**Decision:** Keys live in `/var/lib/bessible/keys.db` (owned by the service user, mode `0600`), table `user_keys(uid, ciphertext, key_id, last4, updated_at)`: one Google key per user.
- Encryption: AES-GCM. The per-user key is `HKDF(master_secret, info=uid)`; the associated data is the `uid`. A ciphertext copied into another user's row fails to decrypt.
- The master secret (`KEY_ENCRYPTION_SECRET`) lives only in a root-owned `0600` systemd `EnvironmentFile` on the VM, shared by the API and worker units. It is never in the repo. The ciphertext carries a `key_id` so the master secret can be rotated (accept old and new during rotation).
- API: `PUT /me/key` (encrypt and store), `DELETE /me/key`, `GET /me/key` (returns only `{last4, updated_at}`; a key is never returned once saved), `POST /me/key/test` (cheap Gemini ping using the supplied or stored key).
- Honest limit: someone who compromises the VM gets the master secret and can read all keys. Without KMS on the free plan this cannot be avoided; the config panel tells users to use a restricted or throwaway key.
*Alternatives considered:* Firestore (works on Spark, survives a VM rebuild, but adds a dependency and a service-account secret with no security gain, since the master secret is on the VM either way); per-run keys only with no persistence (simplest, worse UX).

### 4. Per-run key isolation (Temporal-safe)
**Problem found in review:** (a) `SecretStr` serializes as `"**********"` through Temporal's Pydantic converter, so a real key would arrive masked, and if it did not, it would sit in plaintext in `temporal.db`; (b) `research.py:50` and `planning/evidence.py:122` call `gemini_model()` when the module loads and wrap the agent in `TemporalAgent`, so one key would serve every user.
**Decision:**
- Workflow input carries `credentials: EncryptedCredentials` (`uid`, `key_id`, `google_ct`): plain-`str` ciphertext copied from the key store, never a `SecretStr`. The API sets it server-side and ignores any client-supplied value. The operator's Modal token is never in workflow input; the worker reads it from its own environment.
- The key travels as an explicit argument on one path only: workflow input, activity, model constructor, dropped. Rules:
  1. No module-level model or key; agents receive their model per run.
  2. Never write keys to `os.environ`.
  3. No caches of models or credentials.
  4. No server-key fallback for real runs: no stored Google key returns `401 missing_google_key`.
  5. Logging and Logfire spans exclude credentials and request headers.
- Model construction: `gemini_model(api_key)` builds `GoogleModel` from an explicit key and `settings.gemini_model` (no OpenAI, Anthropic, or OpenRouter). Google models support native `WebSearch` and `WebFetch`, so the earlier multi-provider tool-support risk disappears.
- **Spike first:** `TemporalAgent` registers models at worker start (`models=`), which may not allow per-run credentials. If a per-run model cannot be supplied cleanly, call `agent.run(..., model=...)` inside our own activities instead of `TemporalAgent`. Decide before rewriting the agent sites.
- **Required test:** two concurrent runs with `KEY_A` and `KEY_B` and a fake model that records the key it was built with. Assert each run saw only its own key, neither key appears in workflow history, logs or API responses, and a run with no key fails without using any server key.

### 5. Classifier backends
**Decision:** `classify[T](paragraphs, schema, credentials)` in `src/bessible/classifier.py` chooses a backend: `modal` if the **operator** has enabled it (the worker has `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`, and `CLASSIFIER_BACKEND` is `auto` or `modal`), else `llm` (Gemini structured output with the same Pydantic schemas, using the run owner's key) if a Google key exists, else `heuristic` (the keyword rules currently inline in `suitability/sentiment.py`, moved here so `cross_check` and sentiment share them). `CLASSIFIER_BACKEND=auto|modal|llm|heuristic` (default `auto`) can force one. Any backend error steps down to the next.
- Modal usage is billed to the operator's workspace and is not per-user. It is only reachable by signed-in users (rate-limited at the proxy), and demo replays never call it. For the public VM demo the operator can leave Modal off; the `llm` backend still gives a second label, just not an independent one.
- `import modal` moves inside the `modal` backend so the app starts without the optional dependency.
- **Provenance:** `model_used` and the confidence note the backend. Policy `cross_check` is an *independent* second opinion only on `modal`. On `llm` or `heuristic` the result is labelled non-independent and confidence is not uplifted.
- `scripts/check_env.py` checks the Modal login only when a server-side Modal token is configured.

### 6. Demo mode (record and replay)
**Decision:** A recorder captures one real run into `data/demo/<slug>/`: `request.json`, `events.jsonl` with relative timings, a `status` snapshot per stage transition, the HITL `decision.json`, and `result.json`. Recorded artifacts must contain no keys or personal data.
- Replay routes (`/demo/runs`, `/demo/runs/{id}/status|events|decision|result`, public) never touch Temporal, auth, or any LLM. Events are re-emitted using the recorded timings; the replay pauses at the site-confirmation gate and accepts any decision.
- Demo run ids are prefixed `demo-` and can never resolve to a real run.
- The UI marks replays as a recording, not live output. Recordings go stale as the pipeline changes, so re-record after stage or model changes.

### 7. First-load keys modal (details later)
**Decision:** With no session, the landing view offers **Sign in** and **View demo run**. Once signed in with no Google key stored, a modal offers **Configure key** (Google key, "Test key", saved-state shown as `last4` only) or **View demo run**. Detailed UX is deferred.

### 8. Temporal standalone dev binary for VM deployment
**Decision:** Use the standalone `temporal` CLI binary with embedded SQLite rather than the `temporalio/auto-setup` Docker container.
- Command: `temporal server start-dev --db-filename /var/lib/bessible/temporal.db --headless --ip 127.0.0.1`
- Footprint: expected to be small (roughly tens of MB; **to be measured on the VM**, not assumed), SQLite persistence across restarts.
- Supervised by systemd units.

### 9. Reverse proxy and hardening baseline
**Decision:** Caddy terminates HTTPS via Let's Encrypt:
- `/runs/{id}/events` -> FastAPI (`flush_interval -1` so SSE is not buffered).
- `/runs`, `/me`, `/demo`, `/capacity`, `/site-data` -> FastAPI (`:8000`).
- Everything else -> Next.js standalone server (`:3000`).
Hardening baseline:
1. `ufw` allows only 80 and 443. Temporal (`7233`, `8233`) and FastAPI bind to `127.0.0.1`.
2. SSH keys only, password login off.
3. Caddy rate limiting and security headers.
4. systemd units run as a non-root user with `NoNewPrivileges` and `ProtectSystem`.
5. No headers, bodies or keys in logs or Logfire spans.

## Risks / Trade-offs

- **[Risk] VM compromise exposes all stored keys** (master secret and DB on one host) → *Mitigation*: file modes and non-root units, restricted-key warning in the UI, delete-key button, master-secret rotation. Accepted limit on the free plan.
- **[Risk] `TemporalAgent` cannot take per-run credentials** → *Mitigation*: task 1 spike; fall back to `agent.run(model=...)` in activities.
- **[Risk] Operator's Modal usage is unmetered per user** → *Mitigation*: default `CLASSIFIER_BACKEND=auto` only uses Modal when the operator sets a token; auth plus proxy rate limits bound usage; demo replays never call Modal.
- **[Risk] Recorded demo goes stale or leaks data** → *Mitigation*: re-record after pipeline changes, review recorded artifacts for secrets, label replays in the UI.
- **[Risk] Invalid Google key** → *Mitigation*: "Test key" pings Gemini before a run starts.
- **[Risk] Temporal SQLite corruption on abrupt VM shutdown** → *Mitigation*: WAL mode; runs can be cleared or re-created in demo environments.
- **[Risk] Temporal history keeps ciphertext after a user deletes a key** → *Mitigation*: ciphertext only; clear old runs periodically; master-secret rotation invalidates it.

## Open Questions

- **Should the public VM demo turn Modal on?** It costs the operator (Josh) GPU time and adds cold-start latency, but keeps the independent cross-check and the Modal partner story. Decide at deploy time; the code path works either way via `CLASSIFIER_BACKEND`.
- **Real Firebase token check.** Verify one real ID token end to end (task 1.2); only a forged token has been tested.
