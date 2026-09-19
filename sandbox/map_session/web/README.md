# Map session prototype

Working prototype, kept as the base for the final build. Next.js map UI talking to the Python Temporal workflow
(`../workflow.py`) through route handlers in
`app/api/session/`; the browser never talks to Temporal directly.

One command from the repo root: `./scripts/dev.sh`. Or by hand:

```bash
temporal server start-dev                 # terminal 1
uv run python sandbox/map_session/worker.py        # terminal 2 (repo root)
cd sandbox/map_session/web && npm install && npm run dev   # terminal 3 → http://localhost:3000
```

- `lib/temporal.ts`: Temporal client + the name contract (workflow/query/update names).
- `lib/types.ts`: mirrors `../models.py`. Keep in sync.
- `components/SessionMap.tsx`: Leaflet map with draggable polygon handles.
- `app/session/[id]/page.tsx`: polls `GET /api/session/{id}` every second and renders by `stage`.
