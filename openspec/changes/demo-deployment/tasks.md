## 1. Decouple Modal & Implement Pluggable Classifier

- [ ] 1.1 Implement structured LLM-based classification in `src/bessible/classifier.py` and verify with unit tests using a mock/test model
- [ ] 1.2 Wire the offline heuristic classifier fallback into `src/bessible/classifier.py` and verify classification returns valid labels without Modal
- [ ] 1.3 Remove `modal` import requirement and remove Modal login checks from `scripts/check_env.py`, verifying `uv run python scripts/check_env.py` passes

## 2. Multi-Provider BYOK Inference Backend

- [ ] 2.1 Implement `get_model(provider, api_key, model_name)` in `src/bessible/llm.py` supporting Google, OpenAI, Anthropic, and OpenRouter, verifying with unit tests
- [ ] 2.2 Extend `AssessmentRequest` and workflow stage inputs with optional `llm_provider`, `llm_api_key`, and `llm_model` fields in `src/bessible/models.py`
- [ ] 2.3 Update FastAPI `/runs` router in `src/bessible/api/runs.py` to extract `X-LLM-*` headers and payload credentials and forward them to the workflow
- [ ] 2.4 Update agent runners in `research.py`, `analyst.py`, `evidence.py`, and `policy.py` to use the dynamic model and verify stage execution with pytest

## 3. Frontend BYOK Settings Interface

- [ ] 3.1 Create `SettingsDialog.tsx` in `web/src/components/` with provider selection (OpenAI, Gemini, Anthropic, OpenRouter) and `localStorage` persistence
- [ ] 3.2 Add a lightweight model test endpoint `POST /llm/test` in FastAPI and verify the UI "Test Key" button receives connection status
- [ ] 3.3 Update `web/src/lib/api.ts` to attach stored BYOK credentials to `startRun` calls and verify via browser request headers

## 4. Ubuntu Deployment Runtime & Scripts

- [ ] 4.1 Configure `next.config.ts` for standalone output (`output: 'standalone'`) and verify `npm run build` produces `.next/standalone`
- [ ] 4.2 Create systemd service templates for standalone `temporal server start-dev`, FastAPI, worker, and Next.js standalone server
- [ ] 4.3 Create a `Caddyfile` with automatic HTTPS and unbuffered SSE proxying for `/runs/{id}/events`, verifying syntax with `caddy validate`
- [ ] 4.4 Create an Ubuntu setup and run script `scripts/deploy_ubuntu.sh` that installs dependencies and launches the stack under 500 MB RAM
