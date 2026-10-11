# Verification log

Independent agents checked this analysis in three rounds. They wrote their own code and did not modify the project files. This note records what each round found and what changed as a result.

## Round 0: data extraction (Europris quarterly figures)

- **How the data was built.** Two extractors pulled all 50 quarters (2014Q1–2026Q2) from Europris's Oslo Børs NewsWeb reports. Two verifiers then re-downloaded and re-extracted every quarter on their own and cross-checked each one against the next year's printed comparatives.
- **Result.** One correction: 2014Q3 revenue 1,054.3 → 1,054.2 (IFRS line, not the rounded key-figure sum). Everything else matched. All internal identities hold: GP/revenue, EBIT/revenue, EBITDA = GP + FX − opex, and y/y growth versus the growth printed in the reports.
- **Weak point.** The 2024Q2 Norway unrealised FX (−10.3) is derived from the full-year figure rather than printed, so the 2024Q2 gross margin is accurate to only about ±0.1 pp.

## Round 1: replicate and attack the v2 finalists, code audit, completeness critic

Every finalist replicated exactly from the raw files: predictor rebuilds matched to ~1e-15, and targets, t-statistics and holdout R² all matched.

| v2 finalist | Verdict |
|---|---|
| CNY/NOK → gross margin | Fragile: one krone cycle (2015–16) |
| Unemployment → gross margin | Spurious: the same 2015–16 shock |
| Financial conditions index → gross margin | Spurious: FX in disguise, and not real-time |
| Real disposable income → EBIT | Fragile: dividend-tax timing |
| House prices → sales | Moderate: real at category level |
| Saving ratio → sales | Fragile |

**The code audit** found no look-ahead bugs. It did find that the inference was invalid:

- Newey-West t-statistics are 2–15× oversized at n ≈ 20.
- The confirmation rule had no multiplicity control.
- The "COVID-control" in-sample test reused the primary rows, so it counted the same evidence twice.
- Clark-West p-values on 8-quarter samples are unreliable.
- Some horizons were silently dropped from the screen.

**The completeness critic** showed three things:

- The benchmark lacked the trading-day calendar, which is the strongest predictor.
- Finans Norge sub-indices were missing from the candidates.
- The 25-year proxy is largely Europris's own pre-2014 history.

**What changed (v3):**

- p-values now come from a conditional-randomisation (AR-sieve) bootstrap.
- The benchmark now includes calendar, base effect, store growth and margin mean reversion.
- The FCI was dropped.
- Candidates were expanded.
- Benjamini–Hochberg control was added.

## Round 2: cross-company validation, v3 code audit, attacks on new findings

**Clas Ohlson** (97 fiscal quarters 2002–2026; USD/SEK). There is no 4-quarter FX → gross-margin effect (h=4: p 0.48). A short 1–2 quarter effect appears only when COVID rows are kept, and before 2015 the 5–6 quarter sign is reversed. **Inconclusive:** it does not confirm the Europris lag.

**Kid ASA** (2015–2026; USD/NOK). Nothing significant (best case h=4: p 0.13). The weak signal disappears without 2016 and on the restated hedge-accounting basis. **Inconclusive.**

**v3 code audit.** The machinery is correct. The bootstrap's size is 4.8–5.6% at the 5% level, checked both with simulated x on real y and with real x on simulated y. The trading-day count matches all 11 sales-day differences management quotes. Fixes applied:

- An explosive or degenerate null guard in `inference.py`.
- Exact placebo-calendar tests for the calendar terms.
- Ex-ante stocktaking timing only.
- GSCPI excluded (not real-time).
- Collinear cells guarded.
- A pre-2015-only proxy test (independent of the Europris sample).
- The COVID-control spec demoted to a robustness check (45–70% of its rows are COVID-era).
- Calibrated tier rules that report the number of passes expected under the null.

**Attacks on new v3 findings:**

| Finding | Verdict | Why |
|---|---|---|
| Store growth → EBIT, h=2 | Fragile | Rests on 2019 central-warehouse overruns |
| Consumer-goods import volume → gross margin, h=6 | Spurious | One-quarter unit-value glitch in SSB's 2017Q2 import index |
| Finans Norge "Norway's economy next year" → gross margin | Fragile | Needs COVID rows; correlated with the krone |
| House prices → sales/LFL, h=1 | Moderate | Category slope stable in every sub-period; Europris evidence only in the primary spec; sensitive to extra own lags |

## Final state (v3)

| Check | Result |
|---|---|
| Family calibration | Share of primary-spec p ≤ 0.05 is 3.3–5.6% per target, against 5% nominal. Nothing survives Benjamini–Hochberg. |
| Strict exploratory shortlist | 5 passes against about 1.6 expected by chance |
| Calendar block | Exact placebo p 0.004–0.034 for LFL at h = 1–8 |
| Holdout (2024Q3–2026Q2) | Easter positive in all 15 cells; house prices → LFL positive in all 4; store pace → EBIT positive in both specs; krone → gross margin mixed |

The scripts and outputs from each round are kept in the session scratchpad, not in the repo. Their conclusions are recorded here and in the README.
