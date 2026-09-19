# Bessible web

Next.js map UI. Talks to the Python Temporal workflow (`src/bessible/workflow.py`) through route handlers in
`app/api/session/`; the browser never talks to Temporal directly.

```bash
temporal server start-dev                 # terminal 1
uv run python -m bessible.worker          # terminal 2 (repo root)
cd web && npm install && npm run dev      # terminal 3 → http://localhost:3000
```

- `lib/temporal.ts`: Temporal client + the name contract (workflow/query/update names).
- `lib/types.ts`: mirrors `src/bessible/models.py`. Keep in sync.
- `components/SessionMap.tsx`: Leaflet map with draggable polygon handles.
- `app/session/[id]/page.tsx`: polls `GET /api/session/{id}` every second and renders by `stage`.
