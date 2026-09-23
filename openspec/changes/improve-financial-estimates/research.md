# Research: justification for decisions and numbers

Checked on 2026-09-23. Each number shows the value we use, the evidence, and a verdict:

- **Confirmed**: a public source supports the value.
- **Changed**: the evidence moved the value or the decision. design.md shows the new value.
- **Unverified**: no public source found. The value stays a flagged assumption, and the team must decide.

## UK scope

Bessible assesses sites in **Great Britain** (England, Scotland, Wales). All market and tariff sources below are GB-specific: Elexon, NESO, the GB Capacity Market, Modo's GB index, UK corporation tax, and GB DNO data.

- **Northern Ireland is out of scope.** It trades in the all-island SEM market and has its own capacity auctions (for example SEM-O's T-4 for 2029/30). None of the GB revenue or tariff figures apply there.
- **Three inputs are not UK-specific**, because no UK public figure was found:
  - battery system cost: BNEF's European average, converted to £.
  - round-trip efficiency and O&M share: NREL (US). These are technology figures, so they transfer better than market figures.
- **Scottish transmission areas** have lower thresholds for when a generator stops counting as "embedded" (commonly cited: 30 MW SPT, 10 MW SHETL). Section 3 uses the England and Wales figure of 100 MW. The Scottish thresholds were not checked in this pass. For Scottish sites between those limits, the model will overstate the embedded export credit, which is small anyway.

## 1. Cost inputs

| Input | Value | Evidence | Verdict |
|---|---|---|---|
| Battery system cost | £140k/MWh mid (£110k–£180k) | BNEF 2025 survey: turnkey system average $117/kWh globally, **$177/kWh in Europe**, down 31% on 2024 ([BNEF](https://about.bnef.com/insights/clean-energy/battery-storage-costs-hit-record-lows-as-costs-of-other-clean-power-technologies-increased-bloombergnef/), [Energy-Storage.News](https://www.energy-storage.news/battery-storage-system-prices-continue-to-fall-sharply-bnef-and-ember-reports-find/)). At about $1.30–1.35 per £, $177/kWh is about £131k–£136k/MWh. | **Confirmed** for mid. The current `value` of £250k/MWh has no support, so D1 removes it. |
| Balance of plant | £80k/MW mid | The cited "NREL / DNV UK BESS Cost Benchmark 2025" was not found. NREL's cost structure is: total $/kW = pack $/kWh × hours + balance-of-system $/kW ([NREL ATB 2025](https://atb.nlr.gov/electricity/2025/utility-scale_battery_storage)). That supports the *shape* of our formula, not the figure. BNEF "turnkey" already includes power conversion and installation, so adding £80k/MW on top can partly double-count. | **Unverified**. See open question Q2. |
| Whole project cross-check | 2 h: £140k × 2 + £80k = £360k/MW, before grid connection and development | Modo capex survey (2024): total project cost averages **£580k/MW** ([Modo](https://modoenergy.com/research/gb-november-2024-research-roundup-battery-energy-storage-capex-long-duration-carbon-emmisions-connections-reform-recycling-clean-power-2030)). That survey includes grid connection and development and predates the 31% price fall in 2025. | Plausible. Our total lands near Modo once connection and development cost are added. |
| 33 kV cable | £500k–£700k/km | Roadnight Taylor: "£500-700k per kilometre" for 33 kV ([Roadnight Taylor](https://roadnighttaylor.co.uk/connectology/proximity-to-ehv-network/)) | **Confirmed**. |
| 132 kV cable | £1.25m–£2m/km | Same source: "about £1.25-£2m per kilometre" | **Confirmed**. |
| Opex | £7k/MW/yr | The cited "Modo Energy BESS Operating Cost Benchmark 2025" was not found. NREL puts fixed O&M at **4% of capex per year, including augmentation** (about £14k/MW/yr for a 2 h system at £360k/MW). Land lease is a separate cost at **£10k–£40k per acre per year** ([SolarGridCheck](https://solargridcheck.co.uk/battery), a weak source). | **Changed**. £7k/MW/yr is too low once land is added. D5 adds land lease as its own line, using the reserved acres the footprint stage already computes. Augmentation is modelled on its own (D8), so opex stays without augmentation. |
| Development cost | Fixed per project | No public £/MW figure was found for planning, legal and grid application costs. | **Unverified**. It ships as a placeholder. It still matters because it gives the economies of scale (see D5). |
| Balance-of-plant scale exponent (−0.15) | Proposed in the first design | No source. BNEF's "larger DC blocks are 39% cheaper" is about block size, not project size. | **Changed**: removed. The fixed development cost alone makes cost per MW fall with size, with no invented exponent. |
| Decommissioning | Per MWh at end of life | £8k–£15k/MWh for lithium-ion ([Greener Power Solutions](https://greenerpowersolutions.com/article/what-are-the-decommissioning-costs-for-end-of-life-battery-systems/), a vendor source) | Weak, but the only figure found. It ships as ranged £8k/£11.5k/£15k per MWh, marked placeholder. |

## 2. Revenue inputs

| Input | Value | Evidence | Verdict |
|---|---|---|---|
| 2 h total revenue | £64k/MW/yr mid (£52k–£76k) | A typical 2 h GB battery earned **£73,145/MW/yr** in the 12 months to April 2026. Monthly index figures: £41k (Feb 2026) to £76k (Jun 2025) ([Modo](https://modoenergy.com/research/en/how-does-battery-energy-storage-make-money), [Modo Feb 2026](https://modoenergy.com/research/en/me-bess-gb-revenues-february-2026-wholesale-battery-energy-storage-balancing-mechanism)). | **Confirmed**. Our range covers the observed figures. |
| 8 h total revenue | £122k/MW/yr mid | Modo's forecast for an 8 h asset: £173k–£192k/MW/yr ([Modo July 2026 forecast](https://modoenergy.com/research/en/july-2026-gb-forecast-bess-update-modelling-non-physical-trading)). That is a forecast, not an outturn. | Conservative. It is kept, because no 8 h assets have operating data yet. |
| Stream mix | Wholesale / balancing / Capacity Market | GB: about **60% arbitrage, 33% ancillary, 10% capacity** ([Modo](https://modoenergy.com/research/en/how-does-battery-energy-storage-make-money)). | Supports the three-stream stack. |
| Capacity Market clearing price | Fixture: £60/kW/yr | The T-4 auction for 2029/30 cleared at **£27.10/kW/yr** on 10 March 2026. The T-1 for 2026/27 cleared at **£5/kW/yr** ([Energy UK](https://www.energy-uk.org.uk/wp-content/uploads/2026/03/Energy-UK-Explains-Capacity-Market-Auctions-16-March-2026.pdf), [Modo](https://modoenergy.com/research/en/gb-capacity-market-t4-2029-30-battery-energy-storage-march-2026)). £60/kW was the 2028/29 price. | **Changed**: use £27.10/kW/yr. The GB average Capacity Market income was **£7,454/MW/yr** in the 12 months to April 2026, which agrees. |
| De-rating factors | Placeholder 0.20 / 0.40 / 0.65 | Scaled equivalent firm capacity (EFC), the method NESO now uses for batteries, gives **10.47% for 1 h and 20.94% for 2 h** (T-4 2028/29) ([Modo](https://modoenergy.com/research/gb-capacity-market-2025-bess-derating-factors-confirmed-target-capacity)). The expert panel's review of the 2025 capacity report says these changed only "relatively small[ly]" for 2029/30 ([PTE 2025](https://assets.publishing.service.gov.uk/media/68762902a8d0255f9fe28e94/2025-panel-of-technical-experts-report-on-neso-ecr.pdf)). The 4 h and 8 h values are in NESO's capacity report table, which I could not download. | **Changed**: 2 h = 0.2094. 4 h and 8 h stay placeholder until someone copies them from the NESO table (task 8.1). Do not assume a straight-line scale-up: the factors level off for long durations. |
| Round-trip efficiency | 88% in the first spec | NREL ATB 2025: **85%** | **Changed**: 85% mid (range 85–90%). |
| Arbitrage capture factor | 70% in the first design | A search summary attributed two figures to Modo: an 80% calibration factor between simulated and real GB revenue, and GB day-ahead capture rates falling from 85% (2026) to 58% (2035). **Neither figure appears on the Modo pages I could open** (paywalled or different article). Perfect-foresight revenue is an upper bound, so a factor below 100% is needed. | **Unverified**. Mid stays at 80% as a judgement (range 60–90%), marked placeholder until someone reads it in a Modo methodology page. |
| Revenue decline | Ancillary only in the first design | Modo: every market goes "ancillary-dominated, then saturation, then arbitrage-led" ([Modo](https://modoenergy.com/research/en/how-does-battery-energy-storage-make-money)). As more batteries and solar compete for the same daily price spreads, wholesale revenue per MW also falls. | **Changed**: the decline applies to both ancillary and wholesale, each at its own documented rate (placeholder values). |
| Elexon market index API | 7-day requests, provider APXMIDP | Tested live on 2026-09-23. A 7-day request returns 674 rows. A 31-day request returns HTTP 400: "date range … must not exceed 7 days". All **N2EXMIDP rows have price 0**, so only APXMIDP is usable. | **Confirmed**. 12 months takes 53 requests of about 0.2 s each, so the monthly cache is needed. |

## 3. Network charges

| Input | Evidence | Verdict |
|---|---|---|
| Embedded Export Tariff | NESO final 2026/27 tariffs: **average £3.05/kW** (about £3k/MW/yr). It is paid only on metered export during the three Triad peak periods, to embedded generators **under 100 MW** ([NESO final TNUoS 2026/27](https://www.neso.energy/document/376336/download)). The zonal table in that PDF is an image, so it cannot be extracted as text. | **Changed**. At about 4% of revenue, the charge is too small to justify a zonal table and a generation-TNUoS branch. D4 now uses one ranged national figure: low £0 (misses Triads), mid £3.05/kW, high at the highest zone. Sites over 100 MW get a flagged "not modelled" artifact. |

## 4. Financing and tax

| Input | Value | Evidence | Verdict |
|---|---|---|---|
| Interest rate | 6.5% (5.5–7.5%) | SONIA was **3.73%** in September 2026 ([global-rates](https://www.global-rates.com/en/interest-rates/sonia/)). Our own source note says SONIA + 250–350 bps, which gives 6.2–7.2%. | **Confirmed**. |
| Discount rate and hurdle | 8% | The cited "Clean Energy Infrastructure Fund Hurdle Rate Benchmark" was not found. Industry guides quote 8–12% for contracted projects and **15–20% for merchant BESS** ([Financely](https://www.financely.io/battery-energy-storage-project-finance), a weak source). GB BESS income is mostly merchant. | **Unverified** and probably low. See open question Q1. |
| Corporation tax | 25% | UK main rate since April 2023 | **Confirmed**. |
| Capital allowances | 100% first year on plant | Full expensing: 100% first-year deduction on plant and machinery. It was made **permanent by Finance Act 2024**. Buildings, structures and land do not qualify ([PwC](https://www.pwc.co.uk/services/tax/insights/full-expensing-new-valuable-capital-allowance.html)). | **Confirmed**. The eligible share excludes cable civils and land, so it starts at about 85% of capex, marked as an assumption. |
| Inflation | 2% | Bank of England CPI target | **Confirmed** as a policy anchor. |

## 5. Degradation and life

| Input | Value | Evidence | Verdict |
|---|---|---|---|
| Capacity fade | 2%/yr (1.5–3%) | NREL ATB models a **15-year life** and keeps rated capacity by counting augmentation inside fixed O&M. Warranty terms are commonly 70–80% capacity after about 10 years or 8,000 cycles ([Earth Energy Log](https://earthenergylog.com/articles/bess-warranty-decoded-2026)), which is 2–3%/yr. | Plausible. |
| Augmentation year | 11 | Industry practice ranges from overbuilding 15–20% at the start to augmenting in years 5–7 ([Burns & McDonnell](https://blog.burnsmcd.com/navigating-battery-energy-storage-augmentation)). | **Changed**: the design now allows one augmentation event, with year 8 mid (range 5–11). |
| Project life | 25 years | NREL assumes 15 years. The cited "BESS Warranty & Asset Life Standard" was not found. 25 years only holds with augmentation. | Kept, because D8 models augmentation. The low bound uses 20 years. |

## 6. Curtailment fallback

The UKPN primary-substation data we already ship (`data/ukpn/heatmap.json`, 967 primaries) gives:

- minimum ÷ maximum demand: **median 0.287**, interquartile range 0.243–0.329, with 9 negative (reverse flow).
- maximum demand: **median 15.8**, 10th percentile 6.7, 90th percentile 61.9 (MVA as published).

The fixed fallback of 40/10 MW sits near the 85th percentile, so most sites were modelled as far larger than they are. **Changed**: the fallback is the UKPN median (15.8 max, ratio 0.29), and the per-site values replace it wherever published.

## 7. Source names in `finance.json` that could not be found

These entries cite documents that no search turned up. They must be replaced with real sources or marked `placeholder`, because the report shows them as evidence:

- "NREL / DNV UK BESS Cost Benchmark 2025" (balance of plant)
- "Modo Energy BESS Operating Cost Benchmark 2025" (opex)
- "Modo Energy GB BESS Revenue Benchmark 2025/2026 (2h/4h/8h)" (the figures are near Modo's real index, but no document has this name)
- "DNV Energy Storage Technical Availability Standard" (availability)
- "NESO Operability & Curtailment Analysis 2025" (curtailment haircut)
- "Commercial Infrastructure Project Finance Terms", "Commercial Debt Tenor for Battery Infrastructure", "BESS Warranty & Asset Life Standard", "Clean Energy Infrastructure Fund Hurdle Rate Benchmark"
- "Planning Assessment Stance Threshold Matrix" / "Rejection Threshold Matrix" (opposition thresholds)

Task 2.2 now includes this clean-up.

## Open questions for the team

- **Q1. Discount rate and hurdle.** 8% suits contracted projects. Merchant GB BESS is usually judged at 10%+. Recommendation: mid 10%, range 8–12%.
- **Q2. Balance of plant.** BNEF turnkey already includes power conversion and installation. Recommendation: cut balance of plant to the items outside turnkey (transformer, substation works, civils). Until someone finds a sourced figure, mark it placeholder.
