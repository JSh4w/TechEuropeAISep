## 1. F1 grid-substation-data

- [ ] 1.1 Team decision, 20 min: pick the dataset that covers grid substations and 132 kV; write its name, URL and licence in `design.md`; verify the choice has a downloadable form the team can reach with the existing key or without one
- [ ] 1.2 Fetch a sample and record the real field names in `GridSubstation`; verify one row loads into the model
- [ ] 1.3 Add the ingest function and snapshot loading with provenance; verify `uv run python -m bessible.ukpn.ingest` includes the dataset in the manifest and the snapshot loads

## 2. F2 large-site-capacity (needs F1)

- [ ] 2.1 Extend `propose` with `requested_mw` and the grid-level tier (5 km search, 100 MW cap, 132 kV label, no primary fallback); verify by running it for an 80 MW request near a grid substation and far from one, and for 150 MW
- [ ] 2.2 Pass `battery_mw` from the request into the capacity stage; verify `start --postcode <pc> --battery-mw 80 --yes` shows a 132 kV proposal, and a 20 MW request is unchanged
- [ ] 2.3 If `add-financial-model` is merged, switch connection cost to the 132 kV rate for these proposals; verify the report's connection cost uses £1.25m to £2m per km

## 3. Wrap-up

- [ ] 3.1 Run the full demo flow for an 80 MW postcode; verify the report shows the 132 kV label and the source dataset
