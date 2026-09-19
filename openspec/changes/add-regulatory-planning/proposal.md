## Why

The skeleton's `regulatory_planning` returns fixed text. The real consenting route is simple and often misunderstood, and every proposal at the 5 MW floor triggers a Transmission Impact Assessment. Both facts change how a developer plans, and both come from documented rules, so they can be stated with sources.

**Owner:** TBD.

## What Changes

Three independent features.

- **F1 consenting-route:** state that standalone battery storage in England was removed from the Nationally Significant Infrastructure regime in 2020. Any size is consented by the local planning authority (LPA), with no DCO threshold, so capacity alone never changes the route. Name the LPA from the position. List planning risks from the land analysis.
- **F2 transmission-impact:** every site publishes a Transmission Impact Assessment (TIA) threshold of 1 MW or 5 MW. With a 5 MW floor, every proposal triggers a TIA, so NESO involvement and Gate 2 timescales apply to every run. State this with the substation's threshold.
- **F3 planning-evidence:** list nearby battery projects and their planning status from the DESNZ Renewable Energy Planning Database (REPD), and add a Gemini-written summary that cites only those records. A small fixed policy set goes in the prompt. No RAG.

## Capabilities

### New Capabilities

- `consenting-route`: England consenting route, LPA and planning risks.
- `transmission-impact`: TIA threshold and its consequences.
- `planning-evidence`: nearby REPD projects and a cited summary.

### Modified Capabilities

None.

## Impact

- New `src/bessible/planning/` package; REPD added to the snapshot; replaces `stages/planning.py`.
- Uses Gemini (Google DeepMind) through Pydantic AI for F3 only; F1 and F2 are deterministic.
- Uses `tia_threshold_mw` from `add-ukpn-capacity-proposal` (F2 depends on it).

## Non-goals

- Scotland, Wales and Northern Ireland routes. UKPN areas are in England.
- Predicting planning outcomes or approval chances.
- RAG over planning documents.
- Site constraints such as flood zones (the land analysis owns those).
