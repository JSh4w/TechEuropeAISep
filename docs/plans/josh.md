# Josh — Bessible

## One-liner
Give Bessible a link to a property and it tells you whether a Battery Energy Storage System (BESS) could go there and whether it should, with evidence for every claim.

## Problem
Assessing a BESS site means manually checking grid connection, title boundaries, planning policy, local news and financials across many sources. It's slow, and the conclusions are hard to trust or audit.

## How the agent works
A durable Temporal workflow, with Pydantic validation on every input and output:
1. **Input:** property link plus what the user wants (battery size, budget, etc.).
2. **Grid check:** is the property connected to the grid?
3. **Title boundaries** from a government API.
4. **Human in the loop:** confirm the site/boundary at a CLI prompt.
5. **Feasibility engine:** planning policy, permissions and battery size. What is possible?
6. **Suitability engine (agentic):** local news and a financial model (interest, fees). Is it a good idea?
7. **Report:** a verdict built from explainable AI artifacts: source links, downloaded files and generated images.

## What I'm doing
- **Temporal framework:** worker and workflow, with dummy activities for every step so the flow runs end-to-end from the start and each step gets filled in later. Retries and resuming after a crash, plus a signal for the human-in-the-loop CLI prompt.
- **Pydantic:** input/output models for each step, the user's preferences, and a shared `Artifact` model for the explainable output.
- **Pydantic AI:** agent setup using its built-in Temporal integration.
- **Modal:** host a classification model (model TBD), called from the workflow.
- **CLI:** start a run, answer the prompt, and show the result and artifact folder.
