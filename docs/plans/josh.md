# Josh — Bessible (BESS site assessment agent)

## One-liner
An agent that takes a link to a property and tells you whether a **Battery Energy Storage System** could go there and whether it should, with every claim backed by an artifact you can check.

## Problem
Finding BESS sites means manually checking grid connection, land title boundaries, planning policy, local sentiment and financials across many sources. It's slow, and the results are hard to trust or audit. Bessible automates this and shows its reasoning (explainable AI).

## How the agent works
A **Temporal** workflow (durable: every step is retried/resumable, and a crash mid-run doesn't lose work):

1. **Input** — property link + user preferences (battery size, budget, timeline), validated with **Pydantic**.
2. **Grid check** — is the property connected to / near the grid? Stop early if clearly not.
3. **Title boundaries** — fetch boundaries from a government API (e.g. HM Land Registry INSPIRE polygons — *to verify*).
4. **Human in the loop** — CLI prompt: "Is this the right boundary/site?" (a Temporal signal; the workflow waits for the answer).
5. **Feasibility engine** (rules-based, sequential) — planning policy, permission requirements, feasible battery size vs. the user's inputs. Answers *what is possible?*
6. **Suitability engine** (agentic, broad) — local news about the area, financial model (interest rates, fees, returns). Answers *is it a good idea?*
7. **Report** — verdict + score, and the list of artifacts behind it.

**Explainable AI:** every step returns a Pydantic `Artifact` (claim, source link or downloaded file, generated image/map, confidence). The final report is built only from artifacts, so every conclusion links to its evidence.

## Partner tech (need at least 2)
- **Modal** — hosts the classification model (e.g. a vision model on satellite/site imagery — which model is TBD) and any heavy compute.
- **Temporal** — durable workflow orchestration + human-in-the-loop signals *(check it's on the partner list)*.
- **LLM for the Pydantic AI agents** — use a partner model if one fits.

## Demo
Paste a real property link in the CLI → watch the workflow steps run → confirm the boundary at the prompt → get a verdict with a folder of artifacts (map image, planning excerpts, news links, financial chart). The "wow" moment: kill the worker mid-run and restart it, and it carries on where it left off (Temporal), then click any claim through to its source.

## What I'd build
- **Temporal infrastructure:** worker, the workflow, and **dummy activities** for every step above, each with typed Pydantic inputs/outputs, so teammates can fill them in without touching the orchestration.
- The **human-in-the-loop CLI** (start a run, answer prompts, show results).
- The **Pydantic AI agent setup** (Pydantic AI has built-in Temporal support) plus the **Modal** classification endpoint.
- The shared `Artifact` model and the artifact output folder.

**From the others:** the real feasibility engine (policy/planning/sizing) and suitability engine (news + financial model), written as activities that follow the agreed Pydantic models. Possibly a web UI on top if we have time (not required).

## Risks
- Government/grid data APIs may be slow, need keys, or not cover the area → cache a few demo properties.
- Classification model choice + Modal cold starts → fall back to an LLM vision call.
- 2 hours is tight → agree the Pydantic models in the first 15 minutes; the dummy workflow must run end-to-end within 45 minutes.
- Temporal needs a server → use `temporal server start-dev` locally.
