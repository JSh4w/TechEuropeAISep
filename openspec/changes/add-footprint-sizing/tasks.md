## 1. F1 footprint-area

- [ ] 1.1 Write `footprint.py` `reserved_acres` and `reserved_acres_by_duration`; verify by printing 10 MW at 2 h (1.0–1.5 acres) and that doubling the duration doubles the range

## 2. F2 footprint-geometry (independent of F1 except for the area input)

- [ ] 2.1 Write `footprint_polygon`; verify by printing the area of a 1.0-acre polygon centred on a London position using shapely with a metric projection (1.0 acre within 1%)

## 3. F3 cli-footprint (needs F1 and F2, and the skeleton CLI)

- [ ] 3.1 Add optional `footprint_geojson` to `SiteDecision` and copy it into `ConfirmedSite` in the workflow; verify a Temporal run shows the polygon in the confirmed site
- [ ] 3.2 Show the area range (with 2 h and 8 h) at the CLI prompt and update it when the capacity changes; verify by running `start --postcode <pc>` and entering two different capacities
- [ ] 3.3 Add the reserved-area finding and `footprint.json` artifact in `stages/synthesis.py`; verify the report has the finding, it cites an existing artifact, and `footprint.json` is in the run folder
