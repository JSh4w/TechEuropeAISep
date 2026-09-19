# TechEuropeAISep
Repo for AI hackathon for Tech {Europe}

50% on technical execution 
30% presentation??
20% does it actually solvve a problem


Problem statement  
Build an agent with >=2 tech partners from this event 


deepmind llama : do you save cache between those multiple models/ threads? Consumes a bunch of tokens

## Setup (macOS or Linux)

```bash
./scripts/setup.sh    # installs uv + Temporal CLI (via Homebrew on Mac), Python deps, creates .env, logs in to Modal
```

1. Fill in `.env` with the keys (get them from Josh privately, never commit `.env`).
2. Accept the invite to Josh's Modal workspace, then `uv run modal profile activate <workspace>` if you're in more than one.
3. Start Temporal in its own terminal: `temporal server start-dev` (UI at http://localhost:8233).
4. Check everything: `uv run python scripts/check_env.py`

Run Python with `uv run ...` (or `source .venv/bin/activate`). Add packages with `uv add <pkg>`, not pip.
For OpenSpec's `/opsx` commands: `npm install -g @fission-ai/openspec@latest`.

## Workflow

1. Everyone writes a 1-page plan in `docs/plans/<name>.md` (copy `docs/plans/TEMPLATE.md`).
2. Together: `/opsx:explore` in Claude Code to merge the plans, then `/opsx:propose <change>` once per person's workstream.
3. Each person builds their own change with `/opsx:apply <change>`. Pull often, only edit files you own.
