## 1. Spike: per-run credentials with Temporal (do first, ~30 min)

- [x] 1.1 Check whether `TemporalAgent` can use a per-run Gemini key (`models=` / provider factory); if not, decide to call `agent.run(model=...)` inside our own activities, and record the decision in `design.md`
- [x] 1.2 Create the Firebase project (Spark plan, Google sign-in) and verify one real ID token end to end with `google.oauth2.id_token.verify_firebase_token` and no service-account file (a forged token is already confirmed to reach the cert lookup)

## 2. Per-run model resolution and key isolation

- [x] 2.1 Replace `gemini_model()` with `gemini_model(api_key)` in `src/bessible/llm.py` (Google only, `settings.gemini_model`); remove the server-key fallback for real runs
- [x] 2.2 Remove import-time models: update `suitability/research.py`, `suitability/analyst.py`, `suitability/verdict.py`, `planning/evidence.py`, `possibility/policy.py`, `location/extract.py` to receive the model per run, per the task 1.1 decision; keep existing tests passing
- [x] 2.3 Add `EncryptedCredentials` (plain `str` ciphertext, no `SecretStr`) to the workflow input in `src/bessible/models.py` and thread it through workflow and activities
- [x] 2.4 Add the required concurrency test: two concurrent runs with `KEY_A` and `KEY_B` and a recording fake model; assert no cross-use, no key in workflow history, logs or API responses, and a keyless run fails without using a server key
- [x] 2.5 Add a guard test that fails on `os.environ` key writes and module-level `gemini_model()` calls
- [x] 2.6 Address the `TemporalAgent` gap: resolved to keep one activity per stage and updated earlier design docs (`add-suitability-engine`, `add-regulatory-planning`). Stages encapsulate their caching, I/O, fallbacks, and agent runs cleanly within worker activities; `TemporalAgent` wrappers were dead code and are deprecated upstream
- [x] 2.7 Fix the one new `mypy` error from task 2.2 at `src/bessible/suitability/analyst.py:131` (`fallback_recommendation` gets `cases` typed `dict | None`; same cause as the existing error at line 149)

## 3. Auth, key storage and run ownership (backend)

- [x] 3.1 Add the `current_user` dependency (`verify_firebase_token` from `google-auth` plus explicit `iss` and `sub` checks, `cachecontrol`-cached certs, verify run off the event loop, optional `ALLOWED_EMAILS`) and apply it to all non-demo routes; unit-test with a fake verifier
- [x] 3.2 Implement the SQLite key store (`/var/lib/bessible/keys.db`, `0600`) with AES-GCM, HKDF per-user keys, the `uid` as associated data, and a `key_id` for rotation; test round trip, wrong-`uid` failure and rotation
- [x] 3.3 Add `PUT/DELETE /me/key`, `GET /me/key` (last4 only), and `POST /me/key/test`; verify no endpoint ever returns a key
- [x] 3.4 Update `POST /runs` to use `bessible-<uuid4>` ids, store `owner_uid` in the workflow memo, attach `EncryptedCredentials`, and return `401 missing_google_key` when absent; enforce the owner check (404 otherwise) on `status`, `decision`, `result` and `events`

## 4. Classifier backends

- [x] 4.1 Implement `classify(...)` with `modal | llm | heuristic` backends and `CLASSIFIER_BACKEND=auto|modal|llm|heuristic` (Modal only when the worker has a token) in `src/bessible/classifier.py`; lazy `import modal`; unit-test each backend with a mock or test model
- [x] 4.2 Move the keyword heuristic from `suitability/sentiment.py` into the `heuristic` backend (news-paragraph labels only), keeping its current labels and confidences unchanged
- [x] 4.3 Run policy `cross_check` only on the `modal` backend; when Modal is off or fails, skip it and leave the review's default confidence as is; test both paths
- [x] 4.4 Move `modal` to an optional extra in `pyproject.toml`; make `scripts/check_env.py` check Modal login only when a server-side Modal token is configured; verify the app starts without `modal` installed
- [x] 4.5 Test the `llm` backend live against real Gemini with a valid Google key (structured batch output, the missing-row retry, confidences compared with Modal)

## 5. Frontend: sign-in, key panel, demo button

- [x] 5.1 Add Firebase Auth (Google sign-in) to the Next.js app and attach the ID token to API calls in `web/src/lib/api.ts`
- [x] 5.2 Replace `EventSource` (`web/src/lib/api.ts`) with a `fetch`-based SSE reader that sends the bearer token
- [x] 5.3 Create the key panel in `web/src/components/` (Google key, "Test key", saved state shown as last4, delete)
- [x] 5.4 Add the first-load modal (Configure key / View demo run) and the signed-out landing with Sign in / View demo run; UI details to be configured later

## 6. Demo mode

- [x] 6.1 Implement the recorder that saves a completed run to `data/demo/<slug>/` (request, timed events, status snapshots, decision, result) and a scan that fails if key material is present
- [x] 6.2 Implement public replay routes (`/demo/runs...`) with recorded pacing, a pause at the site-confirmation gate, and `demo-` ids that never resolve to real runs; no Temporal, auth or LLM
- [x] 6.3 Wire the **View demo run** button and a "recorded example" label in the UI
- [x] 6.4 Record one real run end to end and commit the recording

## 7. Docker + Traefik deployment (GHCR, edge TLS)
 
- [x] 7.1 Configure `next.config.ts` for standalone output (`output: 'standalone'`) and verify `npm run build` produces `.next/standalone`
- [x] 7.2 Update Dockerfiles and `docker-compose.yml` for non-root execution (`appuser`), persistent volumes (`bessible-data`, `temporal-data`), and env-based master secret (`KEY_ENCRYPTION_SECRET`)
- [x] 7.3 Configure parameterized Traefik labels in `docker-compose.yml` with priority routing for API/SSE and same-origin relative URLs in frontend
- [ ] 7.4 Build and push backend and web images to GHCR
- [ ] 7.5 Deploy on server via `docker compose pull && docker compose up -d` and verify containers start cleanly without exposing host ports
- [ ] 7.6 Verify live functionality on custom domain and confirm no keys appear in container logs or Logfire spans
