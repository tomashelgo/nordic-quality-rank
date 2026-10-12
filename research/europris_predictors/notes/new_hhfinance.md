# New candidates: household interest burden and the market's view (KEY = `hhfinance`)

Pre-registered 2026-10-12 04:40 UTC, before `scripts/test_new.py` was run. The "Results" section at the end was added after the single test run. The priors, transforms and data above it were not changed afterwards.

## Why these variables

- **Household interest burden and the rate on outstanding loans.** Most Norwegian mortgage debt is floating-rate. A policy-rate change reaches existing borrowers' payments after the 6–8 week notice period, and households adjust spending slowly. The burden (interest paid relative to income) measures the cash-flow squeeze directly, and it scales with household debt, which is about 2.3× disposable income. Management names rates as a key driver. Q4 2023: *"yet another interest-rate hike in December 2023 ... Although this will take some time to filter through to mortgage payments, consumer spending is expected to remain cautious in 2024"* (NW 609575). Q2 2026: the hike to 4.25% *"may weigh on consumer confidence and spending patterns"* (NW 677868). The project tested the policy rate, NIBOR and the 10-year yield, but not the rate households actually pay or the burden.
- **Europris share price relative to OSEBX.** The market prices expected earnings, informed by analysts, channel checks and peer data. A relative return removes market-wide moves (oil, banks, rates). If investors anticipate Europris's sales and margins, the y/y relative return should lead them by 1–4 quarters.
- **Card transactions and search interest.** The task asked for a card-transaction or search-interest index. No usable source was reachable (see below), so none is tested.

## Sources tried

| Source | Result |
|---|---|
| SSB 07200, rates on outstanding loans (total count) | **Used.** Households (04b), banks and mortgage companies, all loans, 2002Q1–2026Q2 |
| SSB 11020, quarterly income and capital accounts by sector | **Used.** Households' interest expenses (U3222_) and disposable income excluding dividends (I3491UAB_H), 1999Q1–2026Q2 |
| Yahoo Finance chart API: EPR.OL (close and dividends) and OSEBX.OL ("Oslo Børs Benchmark Index_GI", total-return) | **Used.** EPR from 2015-06-19 (IPO), OSEBX from 2013-03-05 |
| stooq (epr.no, ^osebx, osebx.no) | **Blocked.** Connections reset, and osebx.no returned a JavaScript proof-of-work bot check. I did not try to get around it |
| Google Trends ("Europris", NO) | **Blocked.** HTTP 429. Not retried |
| Card-transaction indices: BankAxept, Nets/Nexi, DNB, SpareBank 1 | **Not available.** No public statistics page or API (bankaxept.no /statistikk returns 404). DNB and SpareBank 1 card data appear only in bank research notes |
| SSB StatBank search ("kort", "korttransaksjoner", "betalingskort") | No card-spending table |
| Norges Bank SDMX LENDINGSURVEY (household credit demand) | Dataflow exists, but the API returns "No data" |
| Norges Bank SDMX SETTLEMENT_STATISTICS (NICS net turnover, daily, from 2009-04) | **Reachable but not used.** It covers all interbank retail payments (wages, bills, giro), not consumption, in whole NOK billions per day. It is not a card-spending index |

## Series built (`data/new/hhfinance_long.csv`, catalog in `hhfinance_catalog.csv`)

| series_id | Construction | Span | Release lag used (days) |
|---|---|---|---|
| `new_hhfinance_hh_interest_burden` | 100 × Σ₄ interest expenses / Σ₄ (disposable income excl. dividends + interest expenses). Unadjusted flows, 4-quarter rolling sums (removes seasonality). Norges Bank's definition of the interest burden | 1999Q4–2026Q2 | 70 (2026K2 published 2026-09-08). At the t+45 origin the harness uses quarter t−1 |
| `new_hhfinance_hh_loan_rate` | Weighted average rate in force at quarter end on outstanding household loans from banks and mortgage companies (incl. commissions) | 2002Q1–2026Q2 | **60, conservative.** Since 2015 SSB publishes 6 weeks after quarter end (2026K2 on 2026-08-07, 38 days). In 2011–2014 it took 52–61 days (2012K1 on 05-31, 2014K1 on 05-26, 2014K2 on 08-27, 2014K3 on 11-25). With 60 days the harness always uses quarter t−1 |
| `new_hhfinance_epr_rel_osebx` | Daily ratio of an own Europris total-return index (dividends reinvested at the ex-date close; 11 dividends 2016–2026) to OSEBX (gross index). Monthly mean, rebased 2015-06-19 = 100 | 2015-06–2026-09 | 0 (market data). The harness uses the three months of quarter t |
| `new_hhfinance_hh_interest_paid_nsa`, `new_hhfinance_epr_tr_idx`, `new_hhfinance_osebx_gi` | Components, kept for transparency; not candidates | | |

**Checks.**
- **Interest burden.** Its profile matches Norges Bank's published burden: 10.5% in 2002, 12.5% at the 2008Q4 peak, 5.5% at the 2021 trough, 11.7% in 2024Q4 and 10.8% in 2026Q2.
- **Loan rate.** It tracks the policy-rate cycle with a lag of about one quarter: 2.1% in 2021Q3, 5.9% in 2024Q1, 5.3% in 2026Q2.
- **Europris total-return index.** It agrees with Yahoo's dividend-adjusted close within 1.5% over 11 years.
- **OSEBX.** Year-end levels are plausible (2021: 1,201; 2022: 1,189).

## Candidates and pre-registered priors (`data/new/hhfinance_spec.csv`, 4 features)

| Feature | Transform | Sales / LFL prior | Margin prior (GM and EBIT y/y change) | Expected lead (q) | Reasoning |
|---|---|---|---|---|---|
| `hhf_int_burden` | d4 (pp y/y change) | **−** | **−** | 2–8 | A rising burden cuts discretionary cash flow with a lag. Spending shifts from higher-ticket seasonal goods (garden, leisure, home) to consumables and campaign items, which carry lower margins. Some trade-down traffic into discounters partly offsets the sales effect, so the expected sales effect is small |
| `hhf_int_burden` | lvl (% level) | **−** | **−** | 4–8 | A persistently high burden keeps spending growth subdued and the mix tilted toward consumables. This is the long-horizon variant |
| `hhf_loan_rate` | d4 (pp y/y change) | **−** | **−** | 2–6 | Same channel. This is the actual rate households pay, which lags the policy rate by about one quarter |
| `hhf_epr_rel_osebx` | g4 (y/y log %, quarterly mean) | **+** | **+** | 1–4 | The market anticipates Europris's own results (relative to the market) |

### What was known before testing (collinearity only; target relationships were not examined)

Over 2014Q1–2026Q2, as built by the harness:

| New feature | Already-tested feature | Correlation |
|---|---|---|
| `hhf_loan_rate__d4` | `policy_rate__d4` | 0.90 |
| `hhf_loan_rate__d4` | `nibor_3m__d4` | 0.80 |
| `hhf_int_burden__d4` | `policy_rate__d4` | 0.63 |
| `hhf_int_burden__lvl` | `policy_rate__lvl` | 0.86 |
| `hhf_int_burden__d4` | `house_prices__g4` | −0.64 |
| `hhf_loan_rate__d4` | `house_prices__g4` | −0.68 |
| `hhf_epr_rel_osebx__g4` | `cnynok__g4` | 0.31 |
| `hhf_epr_rel_osebx__g4` | any rate or house-price feature | below 0.15 in absolute value |

So the loan-rate change is close to the already-tested policy-rate change, which showed nothing. The burden differs more, because it scales with the debt-to-income ratio and uses 4-quarter flows.

### Data caveats

- **Vintages.** All data are latest vintages. The SSB sector accounts (burden) are revised after first publication. The loan-rate statistic is revised for about six months.
- **Not a pure debt-service ratio.** National-accounts interest is SNA interest (FISIM-adjusted), and principal repayments are not included.
- **Loan-rate sector break.** SSB changed the household sector grouping in 2012Q1. There is no visible jump (2011Q4 4.59%, 2012Q1 4.55%). Household rows are missing before 2002.
- **Share-price history.** It starts at the IPO (June 2015), so the y/y relative return exists only from 2016Q3. The 25-year category proxy test (2001–2024) and the pre-2015 test are therefore not possible for this feature.
- **Share price is not pure Norway.** Europris held an associate stake in Sweden's ÖoB and has consolidated it since May 2024. The share price also moves with valuation multiples and, from 2024, ÖoB news, so it is not a pure Norway-earnings signal.
- **One overlap with the old screen.** The old project's market file has an EPR close series (`mkt_epr_*`), but it was a sanity-check series only. It was never a candidate in `scripts/candidates.py`. The relative return here is built independently.

---

## Results (added after the single test run, 2026-10-12)

Command: `python3 scripts/test_new.py data/new/hhfinance_spec.csv`, run once. The screen is saved as `screen.csv` in the scratchpad `new/hhfinance/` folder. No data were changed afterwards.

**Strict shortlist: 0 passes, against about 0.2 expected by chance (56 eligible tests).**

Share of tests with p ≤ 0.05 in the primary spec:

| Target | Share with p ≤ 0.05 | Tests | Note |
|---|---|---|---|
| Sales | 0.00 | 14 | |
| LFL | 0.00 | 20 | |
| EBIT margin | 0.00 | 8 | |
| Gross margin | 0.21 | 14 | All three hits have the sign opposite to the prior |

**The verdict is null for all three variables. None is recommended.**

### Interest burden, y/y change (`hhf_int_burden__d4`)

- **Sales at 2–4 quarters: right sign (−), but only in the COVID-control spec.**
  - Control spec: h=2 t −3.7 (p 0.012); h=3 t −3.0 (p 0.036); h=4 t −2.7 (p 0.030).
  - Primary spec: p 0.19–0.52.
  - Category proxy, before 2015: t −0.4 to −1.5 (p 0.45–0.77). Full proxy: p 0.41–0.66.
  - Holdout R²: mixed, −0.45 to +0.28.
  - LFL: nothing (control-spec p ≥ 0.18).
  - **Long-horizon proxy:** h=6–8 has the right sign (proxy t −2.5, p 0.17–0.18; pre-2015 p 0.13–0.18) but is not significant.
- **Gross margin at 1–2 quarters: wrong sign (+).**
  - Primary spec: t 3.2–3.4, p 0.036–0.043.
  - Control spec: sign flips, p 0.49–0.86.
  - Holdout: negative in the primary spec.
  - This is a sign reversal that also fails the control spec, so it is not a signal. It most likely reflects the 2023–24 freight-cost collapse, which coincided with the rate hikes.

### Interest burden, level (`hhf_int_burden__lvl`)

Nothing. The best cell is GM h=1, p 0.10 with the wrong sign. Holdout R² is strongly negative at h ≥ 3.

### Loan rate, y/y change (`hhf_loan_rate__d4`)

Same picture as the burden change, and close to the already-tested policy-rate change (correlation 0.90).

- **Gross margin h=2:** t 3.9, p 0.013, but with the wrong sign. Control spec t 0.1 (p 0.96).
- **Sales h=4:** right sign. Primary spec t −2.1 (p 0.11); control spec t −3.3 (p 0.017).
  - Without 2016: t −1.3.
  - Pre-2015 proxy: p 0.88.
  - Holdout R²: +0.46 (primary) and −0.65 (control).
- **LFL h=8:** proxy p 0.09 (right sign), but on Europris data the sign is positive.

### Europris share price relative to OSEBX (`hhf_epr_rel_osebx__g4`)

Only 11–17 primary-spec observations, because the series starts at the 2015 IPO. Horizons of 4 quarters or more cannot be scored (n < 15), and no proxy test is possible.

- **EBIT margin h=2:** right sign (+). Primary spec p 0.062; control spec t 2.7 (p 0.084). Holdout R² +0.17 (primary) and −0.39 (control).
- **Gross margin h=3:** right sign. p 0.14 (primary) and 0.071 (control).
- **Sales and LFL:** nothing (p ≥ 0.37; LFL h=1 has the wrong sign).

### Interpretation

- **Household interest burden and loan rate.** Higher household debt service is associated with weaker Europris sales growth about a year later only when the COVID quarters are kept with controls. That means the evidence rests on the 2022–24 hiking cycle. It does not show up when COVID-affected quarters are dropped, nor in the 25-year category proxy.
- **Share price.** The market's relative view of Europris does not lead its Norwegian sales. It shows a weak, insignificant lead on EBIT-margin changes.
- **Card spending and search interest** could not be tested.
