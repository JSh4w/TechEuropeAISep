## 1. Snapshot

- [x] 1.1 Add `shapely` and `httpx` (runtime) with `uv add`, add `UKPN_API_KEY` to `.env.example` and `settings`; verify `uv run python -c "import shapely, httpx"` works and `uv run python scripts/check_env.py` still passes
- [x] 1.2 Fetch one page of each of the five datasets with the key and record the real field names in `ukpn/models.py`; verify one sample row per dataset loads into its model from a Python shell
- [x] 1.3 Write `ukpn/ingest.py` (fetch all five datasets, parse voltage from name when blank, simplify polygons, write `tables.json`, `areas.geojson`, `manifest.json`); verify `uv run python -m bessible.ukpn.ingest` produces the three files, the manifest lists five datasets, and the folder is under 10 MB
- [x] 1.4 Commit the snapshot under `data/ukpn/`; verify a fresh checkout loads it with no key set
- [x] 1.5 Write `ukpn/snapshot.py` (validated load, STRtree, cached `get_snapshot()`); verify loading takes under 1 s and a blank-voltage substation shows the voltage parsed from its name

## 2. Capacity proposal (rough end-to-end first)

- [x] 2.1 Write `ukpn/capacity.py` for containment, out of area, and effective headroom per direction with queue subtraction and reverse power flow; verify from a Python shell that a position inside one area but nearer another gives the containing substation, and a Manchester position gives out of area
- [x] 2.2 Add seasonal firm capacity, `min(export, import)` with binding direction and season, voltage cap, and the range; verify by printing the result for three known substations (one summer-constrained, one import-bound, one 11 kV with high headroom capped at 8 MW)
- [x] 2.3 Add the 5 MW floor with flexible on/off and the hint message; verify by printing a below-floor site with flexible off (not viable, message names both figures) and on (viable)
- [x] 2.4 Wire `stages/capacity.py` to `propose` and replace the skeleton placeholder; verify a Temporal run with a real UKPN postcode reaches `awaiting_confirmation` showing a real substation
- [x] 2.5 Add distance-weighted ranking with alternates within 5 km and the marginal flag; verify a printed result lists a 3 km alternate flagged marginal

## 3. Provenance, context and logging

- [x] 3.1 Emit key-figure artifacts (dataset id and snapshot date in each claim); verify by printing the artifacts for one proposal
- [x] 3.2 Add context artifacts for RAG, parent GSP status and TIA threshold, and add the optional `CapacityOutput` fields; verify the capacity figures are the same when the RAG values are edited in memory
- [x] 3.3 Append the JSONL check log; verify `out/capacity_checks.jsonl` gains one line per check, including an out-of-area one
- [x] 3.4 Time a warm proposal; verify it prints under 1 s

## 4. Geocoding and demo readiness

- [x] 4.1 Write `ukpn/geocode.py` with the fixture cache and hook it into `stages/location.py` for postcode requests; verify a cached postcode resolves with the network off
- [x] 4.2 Pick 3 demo postcodes (one viable, one below the floor that passes with `--flexible`, one out of area), commit their fixtures; verify `start --postcode <pc> --yes` for each gives the expected outcome
