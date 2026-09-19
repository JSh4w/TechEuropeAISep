## 1. F1 consenting-route (start here, no model call)

- [x] 1.1 Write `planning/route.py` `consenting_route` and `lookup_lpa` (postcodes.io with cached fixtures); verify by printing the route for 6 MW and 49 MW (same route), and for a known district, an unknown one, and a Welsh postcode
- [x] 1.2 Add planning risks from `site_land` constraints with artifact citations; verify each printed risk cites an existing artifact id
- [x] 1.3 Replace `stages/planning.py` with F1 output and artifacts (NSIP fact with source link, LPA); verify a Temporal run prints the route and LPA

## 2. F2 transmission-impact (independent of F1; needs `tia_threshold_mw` from the capacity change)

- [x] 2.1 Write `planning/tia.py` `tia_statement`; verify by printing threshold 5 at 5 MW, threshold 1 at 8 MW, and unknown threshold
- [x] 2.2 Add the TIA artifact and optional `tia` field to `PlanningOutput`; verify a Temporal run shows "TIA triggered" for a UKPN postcode

## 3. F3 planning-evidence (independent of F1, F2)

- [ ] 3.1 Team check, 10 min: confirm REPD and write `planning/policy.json` (a handful of items with source links); verify each item has a source
- [ ] 3.2 Write `planning/ingest_repd.py` and `nearby_batteries`; verify by printing results for a position with nearby batteries and one without
- [ ] 3.3 Write `planning/evidence.py` `summarise` with `gemini_model()` and the citation check; verify a stub model that returns an uncited statement has it rejected
- [ ] 3.4 Wire F3 into the planning stage, recording `model_used`; verify one live run with `GOOGLE_API_KEY` set prints a cited summary and the artifact names the Gemini model
