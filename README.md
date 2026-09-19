# TechEuropeAISep
Repo for AI hackathon for Tech {Europe}

50% on technical execution 
30% presentation??
20% does it actually solvve a problem


Problem statement  
Build an agent with >=2 tech partners from this event 


deepmind llama : do you save cache between those multiple models/ threads? Consumes a bunch of tokens

## Setup

```bash
npm install -g @fission-ai/openspec@latest   # OpenSpec CLI, used by the /opsx commands
python -m venv .venv && source .venv/bin/activate   # Python 3.14
pip install -r requirements.txt
modal setup                                   # log in to Modal (opens browser)
```

## Workflow

1. Everyone writes a 1-page plan in `docs/plans/<name>.md` (copy `docs/plans/TEMPLATE.md`).
2. Together: `/opsx:explore` in Claude Code to merge the plans, then `/opsx:propose <change>` once per person's workstream.
3. Each person builds their own change with `/opsx:apply <change>`. Pull often, only edit files you own.
