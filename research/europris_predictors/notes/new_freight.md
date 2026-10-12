# New candidate: inbound container freight (KEY = `freight`)

Pre-registered 2026-10-12 04:25 UTC, before `scripts/test_new.py` was run. The "Results" section at the end was added after the single test run, and the priors and transforms above it were not changed.

## Why freight

Europris buys long-haul freight from Asia on fixed contracts: a one-year contract for 2021, a two-year contract from March 2022 (+NOK 170–200m a year), a two-year contract from January 2023 (rates about 50% lower), Red Sea surcharges in 2024, and a renewal in April 2026 running through summer 2027 (see `notes/drivers_and_hypotheses.md` §2). The project's earlier freight proxy, US PPI deep-sea freight (US export routes), had the wrong sign. This note tests a price measure that reflects what a European importer pays for sea freight, plus a contract-regime variable built only from Europris's own announcements.

## Sources tried

**The goal was a true Asia–North Europe spot index (SCFI, CCFI, FBX, WCI, Harpex). No such history was reachable without a login or subscription.**

| Source | Result |
|---|---|
| Shanghai Shipping Exchange, English site (en.sse.net.cn): SCFI/CCFI history and weekly SCFI reports | Login required ("please login", report pages "Please Login"). Only the current week is public |
| Shanghai Shipping Exchange, Chinese site (www.sse.net.cn): CCFI multi-period query `/index/mutipleIndex` and single-date query | Server answers "对不起你没有登陆!" (not logged in), and single-date queries return empty tables. Only the current week is public |
| chineseshipping.com.cn weekly CCFI reports | Subscription page ("用户订阅") |
| Freightos FBX (fbx.freightos.com, terminal pages) | Redirects to the paid Terminal product. FBX history starts in 2016 in any case |
| Harper Petersen HARPEX (charter rates) | The public page embeds only the last 24 months (2024-10 to 2026-10) |
| Drewry WCI | Known blocked (429). Not retried |
| Hapag-Lloyd and Maersk IR (average freight rates by trade) | HTTP 403 |
| GlobeNewswire (Maersk releases) | HTTP 403 |
| Bank of Japan SPPI ocean-freight (container) series, stat-search.boj.or.jp | Proxy denies the connection (502) |
| Ningbo Containerized Freight Index (nbsei.cn) | Proxy denies the connection (502) |
| US Census import charges per kg (api.census.gov) | API key required |
| Statistics Denmark services PPI for sea transport (PRIS1521, Maersk-dominated) | Confidential ("..") for every quarter |
| Eurostat services PPI for water transport (sts_sepp_q, H50): DE (Hapag-Lloyd) and EU27 | Reachable but unusable. The DE series has a methodological break in 2015 (I10 −6% vs I15 −28% in 2015Q2), and the EU27 I15/I21 overlap ratio drifts from 0.58 to 0.69, so it cannot be chained |
| FRED | No container spot series. Only the US PPIs already tested |

## Series built

| series_id | What it is | Span | Release lag (days) |
|---|---|---|---|
| `new_freight_fr_seafreight_ppi_btob` | INSEE IDBANK **010766550**: price index of sea and coastal freight transport services (CPA 50.20) sold to French businesses, *purchaser's price for contract escalation* (IPPS base 2021, indicator `BTOB_PM_IPSE`, "prix de marché (indexation de contrats)") | 2010Q1–2026Q2 (66 q) | 60 |
| `new_freight_fr_seafreight_ppi_btob_4qavg` | Trailing 4-quarter mean of the series above | 2010Q4–2026Q2 | 60 |
| `new_freight_epr_contract_regime` | Europris contract regime: sign of the y/y change in the contracted freight cost in effect in the quarter | 2014Q1–2026Q2 | 0 (see construction) |

**Why the INSEE series.** It is an official price index of sea freight bought by French businesses. CMA CGM is the dominant French provider, and French importers' cargo is mostly Asia–Europe containers.

Its y/y profile tracks the known container cycle:

| Period | y/y change | Container-market event |
|---|---|---|
| 2015Q4–2016Q2 | −11% to −15% | 2015–16 rate collapse |
| 2017Q1–Q3 | +8% to +13% | Recovery after Hanjin |
| 2021Q3 | +78% | 2021 boom |
| 2023Q3 | −85% | Collapse |
| 2024Q3 | +39% | Red Sea |
| 2025Q3 | −31% | Easing |

**It is not a spot index.** It is a realised price, a mix of contract and spot rates, lagging spot by roughly 0–2 quarters. It is in EUR, so it carries no NOK FX effect; FX was already tested separately.

**Series rejected and why:**
- **INSEE BtoE and BtoAll versions.** Before 2017 they include a dry-bulk spot component ("Dry Baltic Index" sub-index of French ship-owners). Their 2014–15 y/y moves disagree with the container market.
- **BtoB basic-price variant (010766403).** It barely moves in 2021–22, so it is not container-driven.

**Release lag.** INSEE publishes this index in the quarterly IPSE *Informations Rapides* about 57–59 days after the quarter ends: Q1 2025 on 2025-05-28, Q2 on 2025-08-28, Q3 on 2025-11-27, Q4 on 2026-02-26. A 60-day lag is used. At the project's forecast origin (quarter end + 45 days), the latest value available is therefore the previous quarter's.

**4-quarter mean.** This is the contract-renewal proxy. Annual and two-year contracts are negotiated against the market level of roughly the past year. Its y/y growth is the change in the past year's average freight price versus the year before.

**Contract regime.** Each quarter is coded with the sign of the y/y change in the contracted freight cost in effect. The code uses only facts Europris had published by the forecast origin (quarter end + 45 days); the build script asserts this.

Run-rate arithmetic behind the signs (NOK m per year), from the CMU 2022 facts:

| Period | Run-rate |
|---|---|
| Up to 2021 | ≈ 65 (historical 60–70) |
| 2022 from March | 65 + 185 = 250 |
| 2022Q1 average | (65 + 65 + 250) / 3 ≈ 127 |
| 2023–24 base contract | 250 × 0.5 = 125 |

| Quarters | Code | Basis | Announcement (NW id, date) |
|---|---|---|---|
| 2014Q1–2021Q4 | 0 | No contract change announced. The 2021 fixed price-and-volume agreement was announced in the Q4 2020 report (NW 523770, 2021-02-04) with no direction versus 2020. The CMU later put historical annual freight cost at NOK 60–70m. Zeros before the 2015 IPO are an assumption | — |
| 2022Q1–Q4 | +1 | New two-year agreement, annualised cost +NOK 170–200m from March 2022. The direction ("freight costs will increase in 2022") was already given in NW 545906 on 2021-11-04 | NW 552536, 2022-02-03 |
| 2023Q1 | 0 | New contract rate (≈125) vs Q1 2022 average (≈127): about −1% y/y | NW 577619, 2022-12-08 |
| 2023Q2–Q4 | −1 | Rates about 50% below the previous agreement | NW 577619, 2022-12-08 |
| 2024Q1–Q4 | +1 | Same base contract plus Red Sea war surcharges: "currently exposed to the rise in shipping costs". Confirmed in NW 623406 (2024-07-11), NW 630818 (2024-10-31) and NW 637305 (2025-01-29) | NW 609575, 2024-02-01 |
| 2025Q1–2026Q2 | 0 | No y/y direction announced. The April 2026 renewal is at "competitive rates" | NW 671239, 2026-04-23 |

Construction is in `<scratchpad>/new/freight/scripts/build_freight.py`, and raw downloads are in `<scratchpad>/new/freight/dl/` (`insee/`, `nw/`).

## Pre-registered candidates and priors (decided before testing)

| key × transform | prior_sales | prior_margin | Expected lead | Reasoning |
|---|---|---|---|---|
| `freight_fr_seafreight_ppi__g4` | ? | **−** | Gross margin 2–6 q (centre about 3–4). Adjusted EBIT margin: same sign and lead, smaller | Higher freight prices feed into the next contract (renewed at year-end or every two years) and, through capitalised freight, into inventory cost. Inventory turns in about 5 months, so cost of goods sold is hit 1–2 q after shipment. Before freight reaches the margin there are: the 60-day publication lag; a 0–4 q wait for the next renewal; and 1–2 q of inventory turnover. Around h ≥ 6 the y/y base effect may reverse the sign. **Sales: no clear prior.** Higher import costs can lift nominal prices, while supply shortages cut availability (in 2021 Europris's contract "secured the flow of goods") |
| `freight_fr_seafreight_ppi_4qavg__g4` | ? | **−** | Gross margin 4–8 q | Contract-renewal proxy. A dearer past-year average means a dearer next contract, which hits the margin a year or more ahead. This is the long-horizon candidate |
| `freight_epr_contract_regime__lvl` | ? | **−** | Gross margin 1–2 q. Sign may reverse at h ≥ 4 because of the y/y base effect | A contract that costs more than a year earlier lowers the y/y gross-margin change while it is in effect and as its inventory is sold |

There are three candidate features, well under the cap of 8. Sales and LFL priors are "?", so sales tests are reported but cannot enter the strict shortlist.

## Data caveats

- **Not a spot index.** The INSEE index is a realised price for sea freight bought by French businesses; it blends contract and spot. It covers all sea and coastal freight, though container-dominated. It is not Asia–North Europe specific, and it is in EUR.
- **Latest vintage.** INSEE revises recent quarters. The release lag is set from the 2025–26 publication dates.
- **Short history.** The series starts in 2010, so g4 starts in 2011 and the 4-quarter-mean g4 in 2011Q4. The pre-2015 category-proxy test therefore only has 2011–2014.
- **The regime variable is thin.** It is an event variable with three non-zero spells (2022, 2023Q2–Q4, 2024), all after 2021. Most of its in-sample variation falls in quarters that the COVID exclusion drops or that sit in the holdout. Its randomisation p-value uses AR-sieve draws, which do not resemble a sparse −1/0/+1 dummy, so treat it as descriptive. Its 2024 sign rests on qualitative management statements; the surcharge was not quantified.
- **Unknowable in real time.** The magnitude of the 2021 contract versus 2020, and the 2025 terms, were never published. Both are coded 0.

## Results (added after the single test run, 2026-10-12)

The test was run once: `python3 scripts/test_new.py data/new/freight_spec.csv`. A copy of the screen is at `<scratchpad>/new/freight/screen.csv`. No data error was found afterwards, and there was no rerun. The harness's real-time features were checked: the origin-2021Q4 value of the price g4 equals the index's 2021Q3 y/y (+78%), so the 60-day lag works as intended.

**Headline: null result.**
- The strict shortlist has **0 passes vs ~0.1 expected by chance**, out of 18 eligible margin tests. Sales tests had "?" priors and were not eligible.
- Calibration: 1 of 12 gross-margin tests has p ≤ 0.05, and 0 of 6 EBIT-margin tests. Minimum BH q is 0.18.

| Feature → target, h | t (primary) | p (primary) | t (COVID control) | p (control) | t (no 2016) | Holdout R² (primary / control) |
|---|---|---|---|---|---|---|
| Contract regime → gm_d4, h=2 | −3.41 | **0.015** | +0.69 | 0.48 | −2.69 | −6.59 / −0.39 |
| Contract regime → gm_d4, h=3 | −2.52 | 0.071 | −0.85 | 0.47 | −1.42 | −5.66 / −0.99 |
| Freight price g4 → gm_d4, h=2 | −2.57 | 0.071 | +1.72 | 0.11 | −1.77 | −1.44 / +0.28 |
| Freight price g4 → gm_d4, h=1 | −2.15 | 0.108 | **+2.80** | 0.030 | −2.13 | −0.90 / +0.26 |
| Freight price g4 → ebitm_d4, h=2 | −0.97 | 0.106 | +1.37 | 0.29 | −0.97 | −0.01 / +0.36 |
| 4q-mean g4 → gm_d4, h=1 | −1.94 | 0.180 | +1.51 | 0.24 | −1.56 | −0.45 / +0.30 |
| Freight price g4 → gm_d4, h=4 | −1.15 | 0.319 | +1.67 | 0.27 | +0.07 | −1.20 / −4.62 |
| 4q-mean g4 → gm_d4, h=4 | +0.30 | 0.809 | +1.68 | 0.34 | −0.25 | +0.20 / −5.56 |
| Freight price g4 → lfl, h=6 (no prior) | +0.77 | 0.409 | +4.18 | 0.003 | +0.90 | −1.51 / −6.67 |

**Reading.**
1. **Short-horizon sign matches the prior but is not significant.** In the COVID-excluded primary spec, the freight-price y/y has the prior sign (−) for gross margin at h=1–2, but p is 0.07–0.11. In the COVID-control spec the sign flips to positive (h=1, p 0.03). That flip is the 2021 episode: spot freight exploded while Europris's fixed 2021 contract and higher shelf prices lifted its margin. This is the same reason the US PPI deep-sea proxy had the "wrong" sign. A real freight-price series does not fix it, because Europris's contract timing decouples its cost from the market for up to two years.
2. **No long-horizon signal.** Nothing works at ≥ 4 quarters. The contract-renewal proxy (4-quarter mean y/y) has p ≥ 0.18 at every margin horizon, and p 0.35–0.96 at h ≥ 4. Holdout R² is mostly negative.
3. **The contract-regime hit is not credible.** Its one p < 0.05 (h=2) rests on four in-sample quarters (targets 2023Q2, 2023Q4, 2024Q1, 2024Q2). It fails the control-sign rule, and the holdout is strongly negative: after the +1 Red Sea year, gm_d4 was +1.4 and +1.7 pp in 2024Q4 and 2025Q1, the opposite of the prior. The raw gm_d4 was also negative in 2023Q4 and 2024Q1 despite the 50% cheaper contract, because the weak NOK and seasonal carry-overs dominated.
4. **The sales hits are COVID artefacts.** They appear only in the control spec (lfl h=6: p_isc 0.003, but primary p 0.41, holdout −1.5/−6.7).

**Conclusion.** Freight does not qualify as a new predictor. Europris's announcements already quantify the cost of each contract renewal (+NOK 170–200m in 2022; −50% from 2023) when it is signed. Use those statements directly in forecasts rather than a market freight index.
