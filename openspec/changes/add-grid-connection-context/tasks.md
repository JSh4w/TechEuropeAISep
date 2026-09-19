## 1. F3 gate2-timescales (start here: it fills a placeholder stage)

Depends on: `add-ukpn-capacity-proposal` tasks 1.x done.

- [ ] 1.1 Write `ukpn/timescales.py` `gsp_queue` and `timescales` over GSP Project Status; verify by printing them for one GSP with many records, one with 2 records (low confidence), and an unknown GSP (None)
- [ ] 1.2 Replace the `stages/grid.py` placeholder with a real stage returning queue position, median months and one artifact per figure; verify a Temporal run shows real values for a UKPN postcode and each artifact cites dataset and snapshot date

## 2. F1 connection-competition

Depends on: `add-ukpn-capacity-proposal` tasks 1.x done. Independent of F2, F3, F4.

- [ ] 2.1 Add the Table 6 fetch to `ukpn/ingest.py` and its model; verify the snapshot loads with the new dataset and the manifest lists it
- [ ] 2.2 Write `ukpn/competition.py` (`competition`, weights, bands); verify by printing it for a substation with records and one without, and that effective headroom is unchanged
- [ ] 2.3 Emit competition artifacts and the queue-shrinkage caveat from `stages/capacity.py`; verify a demo run's artifact list includes both

## 3. F2 export-ceiling

Depends on: `add-ukpn-capacity-proposal` tasks 1.x and 2.2 done. Independent of F1, F3, F4.

- [ ] 3.1 Fetch Table 2a, record the real field names, and add the model; verify one sample row loads
- [ ] 3.2 Write `ukpn/export_ceiling.py` and `validate_export_ceiling`, and write the result to the manifest at ingest; verify by printing the failing substation ids (or an empty list) from the manifest
- [ ] 3.3 Use the export ceiling in `ukpn/capacity.py` only when validation passed; verify by printing a proposal with the flag on and off and seeing the ceiling change only when on

## 4. F4 snapshot-refresh

Depends on: `add-ukpn-capacity-proposal` task 1.3 done. Independent of F1, F2, F3.

- [ ] 4.1 Write `ukpn/refresh.py` with temp-folder build and atomic swap; verify that forcing one dataset to fail leaves the existing snapshot files unchanged (compare file hashes before and after)
- [ ] 4.2 Add `ingest --refresh` with the diff summary; verify a refresh prints added, removed and changed counts per dataset
- [ ] 4.3 Add snapshot age to the report and the 6-month CLI warning; verify by editing the manifest date to 7 months ago (warning appears) and 2 months ago (no warning)
