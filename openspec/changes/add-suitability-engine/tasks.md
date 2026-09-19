## 1. Spikes and end-to-end wiring (rough version first)

- [x] 1.1 Spike Gemini + Google Search: one `Agent(gemini_model(), ...)` with the `WebSearchTool` native tool asked for local battery news near a demo postcode, output type `Research`; verify it returns at least one UK source with a URL and paragraphs (if not, switch to hand-written fixtures and note it in design.md)
- [x] 1.2 Write `suitability/labels.py` (`ParagraphLabels`) and classify three sample paragraphs (one objection, one supportive, one irrelevant) through `classify()`; verify the labels and confidences look right and share the module name with Jack
- [x] 1.3 In the skeleton, add the `sentiment` stage, `SentimentOutput`, the `local_sentiment` placeholder activity in the first parallel group, and `sentiment` on `SynthesisInput`; verify a full placeholder run still completes and the Temporal UI shows `local_sentiment` running in parallel with market

## 2. Local sentiment

- [x] 2.1 Write `suitability/research.py` (research agent + fixture cache under `data/fixtures/news/`); verify a second call for the same site reads the cache and makes no search request
- [x] 2.2 Write `suitability/sentiment.py` (classify per source concurrently, opposition index, top concerns); verify with fixed labels that 2 against at 0.9 and 1 supportive at 0.6 give an index above 0.5, and no relevant paragraphs give `None`
- [x] 2.3 Wire `stages/sentiment.py` with artifacts (one per relevant paragraph, one for the index; `model_used` = Gemini for research, `classifier.MODEL_NAME` for labels); verify a Temporal run for a demo site shows real sources in the artifacts
- [x] 2.4 Wrap the research agent in `TemporalAgent` and register it through `PydanticAIPlugin`; verify the Temporal UI shows the model request and search steps as separate activities

## 3. Financial analysis

- [x] 3.1 Write `data/assumptions/finance.json` with low/mid/high, unit, source and date for every input (battery £/MWh, balance of plant, OPEX, revenue per duration, cable £/km, availability, curtailment haircut, debt share, interest, arrangement fee, discount rate, life, hurdle and opposition thresholds), plus `suitability/assumptions.py` to load it; verify loading fails with the key name when a value is removed
- [x] 3.2 Write `suitability/finance.py` `evaluate()` (CAPEX, OPEX, revenue with curtailment, financing, NPV, IRR by bisection, payback, low/mid/high, budget flag); verify by hand for one 10 MW 4 h case that CAPEX and NPV match a spreadsheet-style calculation, and that a loss-making case gives IRR `None`
- [x] 3.3 Replace `stages/market.py` and `stages/financial.py`: compute all three cases in code and emit per-case and assumptions artifacts; verify a run shows three cases in the result, with the budget flag set when a small budget is given
- [x] 3.4 Add the analyst agent (`evaluate_case` tool, `Recommendation` output) as a `TemporalAgent`; verify the rationale names the chosen duration and quotes only numbers present in the three cases

## 4. Verdict and report

- [x] 4.1 Write `suitability/verdict.py` `decide()` with thresholds from `finance.json`; verify go, maybe (opposition 0.75) and unknown-sentiment cases by calling it with hand-built inputs
- [x] 4.2 Add the number guard; verify a finding stating "IRR 14%" against a computed 9% is flagged, and one stating the correct figure passes
- [x] 4.3 Add Gemini findings (`list[Finding]`, cited ids) with one guarded rewrite and a template fallback, and replace `stages/synthesis.py` to write the report (verdict, rules, duration table, opposition index, top concerns, cited findings); verify every finding cites an existing artifact id and the report file is in the run folder

## 5. Demo readiness

- [x] 5.1 Run the three demo sites end to end and commit their news fixtures; verify each completes with the network for search turned off
- [x] 5.2 Pre-demo checklist in `README.md`: `modal` `min_containers=1`, Temporal UI tab open on the run, the cache warm; verify a cold Modal start is avoided by timing one run after setting it
