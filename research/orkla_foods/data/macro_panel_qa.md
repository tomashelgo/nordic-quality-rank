# Macro feature panel: adversarial QA (verify-panel)

**Scope:** `macro_panel_quarterly.csv` (127 quarters x 1,420 features, 1995Q1-2026Q3), `feature_dictionary.csv`, `macro_panel_build.py`, `macro_panel_notes.md`, `macro_panel_geo_weights_quarterly.csv`.

**Inputs:** the raw series in `macro/*/` and the weights in `orkla_raw/geo_weights.csv`.

**Date:** 2026-10-06 (latest Orkla report Q2 2026).

## Verdict

The panel is correct.

- Every recomputed feature matches the raw files to the 6 significant digits the CSV stores.
- The country weights reproduce exactly from `geo_weights.csv`.
- The build script runs end to end and is deterministic.

One substantive error was found and fixed: an undocumented scope break in a core series (`no_jordbruk_malpris_mnok`). Five missing data-quality and real-time caveats were added to the script, so the dictionary and the notes now regenerate with them.

## Checks

The verification scripts are independent: they do not import the build. They live in the session scratchpad under `scripts/verify-panel/`.

| Script | Checks |
|---|---|
| `recompute_base.py` | (a) base features |
| `indep_weights.py` | (d) weights |
| `recompute_comp.py`, `recompute_comp2.py` | (a) composites |
| `check_dates.py`, `check_lags.py` | (b) labelling, (e) look-ahead |
| `check_types.py` | (c) transforms |
| `check_dict.py` | dictionary and lags |
| `check_excl.py` | duplicate exclusions |
| `check_endcov.py` | end-of-sample coverage |

### (a) Recomputation from raw files: PASS

**Base features: 60 checked.** All were re-derived from raw CSV, catalog and frequency: quarterly mean of three complete months, then yoy = 100·ln(x/x₋₄), dyoy, lvl and d4.

- **Draw 1** (seed 20261006): 20 random features plus 10 targeted ones (masked, annual, July-effective and forward-looking series).
- **Draw 2** (seed 99): 30 random features.

Results:

- Every overlapping value agrees to a relative error below 5e-6, which is the 6-significant-digit rounding of the CSV.
- Every coverage difference is a documented mask:
  - LT LCI 2019;
  - WB chicken, palm oil and barley;
  - CEE surveys before 2000;
  - NO QNA wage 2015-16;
  - NAV rate d4 2022 and 2025;
  - the July-effective assignment of the jordbruk series.

**Composites and spreads: 38 checked.** These were recomputed from raw files with independently derived weights:

- 28 chosen to cover every construction type: renormalised W composites, Nordic composites, z-score, FX crosses including pre-1999 ECU, the ECB effective rate, VAT adjustment, the agri basket, local-currency conversions and the spreads with their `_d4`.
- 10 drawn at random (seed 7) from the remaining 62.

All 38 match to a relative error below 5e-6, with identical start, end and NaN pattern.

Examples: `w_food_cpi_yoy/dyoy`, `w_real_wage_*`, `w_policy_rate_*`, `w_cons_conf_z*`, `w_fx_vs_{eur,usd,nok}_*`, `nw_food_cpi_xvat_yoy`, `eu_agri_basket_*`, `price_cost_gap_ppi*`, `w_hh_saving_*`, `fao_ffpi_wloc_yoy`, `elec_nordic_loc_yoy`, `w_hh_real_inc_*`, `w_gov10y_lvl`, `w_food_cpi_rel_dyoy`.

### (b) Quarter labelling: PASS

**Date conventions in all 692 raw files:**

- Every date is the first of a month.
- Quarterly dates fall only in months 1, 4, 7 and 10.
- Annual dates are 1 January.
- There are no duplicate dates, no non-numeric values and no unsorted files.

**Hand checks of 2015Q3:**

| Series | Check | Result |
|---|---|---|
| NO CPI food | mean of Jul, Aug, Sep 2015 (72.8, 72.1, 72.3) | yoy 3.03833 = panel |
| NO QNA food consumption (quarterly) | 2015-07-01 maps to 2015Q3 | matches |
| SE policy rate | quarterly mean | matches |
| Finans Norge CCI | quarterly value | matches |

**Timing test.** Native-quarterly series and their monthly counterparts peak at lag 0 (correlations 1.00, 1.00, 1.00 and 0.95), against 0.62-0.93 at ±1 quarter. Pairs tested: QNA vs MNA goods consumption, SE GDP vs its monthly indicator, `se_real_wage_yoy_q` vs SE wage index minus CPI, and household vs spot electricity.

### (c) Transforms vs series type: PASS

- **yoy/dyoy (339 series):** all are index, price, volume, FX or income levels. None has a rate-like unit, and none has a value ≤ 0 after 1979.
- **lvl/d4 (326 series):** all are percent rates, survey balances, confidence or diffusion indices, OECD amplitude-adjusted indices, NIER indices, GSCPI, series already in y/y growth, VAT rates, or the NOK-million settlement changes. No nominal index gets a level transform.
- **yoy horizon:** 4 quarters, confirmed by the recomputation.

### (d) Composite weights: PASS

An independent re-derivation from `geo_weights.csv` reproduces `macro_panel_geo_weights_quarterly.csv` to within 5e-7 in every quarter and country. It used the segment-by-period mapping in `segment_history.md` (A 2000-07, B 2008-12, C 2013-14Q3, D 2014Q4-2022Q2, E/F 2022Q3-) and the documented region-to-country rules. Region totals are 99.9-100.01%.

- Weights over countries with data sum to 1 in every quarter; the build asserts this.
- Countries without data drop out through renormalisation: RU (7% in 2005-07, about 1% in 2015-21), UK, and other regions.
- The coverage floor blanks thin quarters. In the last quarter published, coverage is 0.91-0.98 for all main composites; the only gap is EE, whose EC surveys are suspended from 2026-05. Partial quarters are correctly NaN, for example `w_hh_real_inc` 2026Q2 at 26% coverage and `w_gov10y` 2026Q3 at 56%.

### (e) Look-ahead: PASS, with documented caveats

- Only three raw files carry dates after Sep 2026: `ea_wage_tracker_yoy_q` (to 2027Q2), `no_vat_food_rate` (to 2026-12) and `se_food_vat_rate` (to 2026-10). All three are truncated to Sep 2026.
- No raw series has data earlier than its catalog lag allows, judged from its last observation as of 2026-10-06. The exceptions err on the safe side:
  - euro-area all-items HICP for Sep 2026 is a national flash, available at about t+1 against a catalog lag of 17 days, so lag 1 is conservative;
  - DG AGRI weekly prices appear 1-4 days ahead of their stated lag.
- `realtime_min_lag_q` was recomputed independently for all 1,420 features: 0 mismatches.
  - Rule: 0 if the lag is at most 14 days, 1 if at most 100, else 2.
  - Annual series are measured from the end of Q1. July-effective settlements count from Q3. The frontfag frame is lag 0. Composites take the maximum over their components.
- The lags are plausible for the key sources:
  - lag 0: NO CPI (10 days), SE CPI (13), FAO (6), Pink Sheet (3), EC surveys (-2), Norges Bank surveys (-40);
  - lag 1: HICP (17), Eurostat PPI and retail (35), LCI (77), saving rate (97);
  - lag 4: annual TBU outcomes.

### (f) Documented breaks: PASS after one fix

Every break listed in `qa_B.md` (I1-I7) and `qa_C.md` (items 8-16) and every break flagged in the catalog notes is masked or documented:

- LT LCI 2019;
- WB chicken, soybean oil, palm oil, EU gas and barley;
- the EU cereals 2026-08 change;
- EU fish PPI 2009;
- NAV level and rate breaks;
- LFS d4 breaks in 2006 and 2021;
- NO QNA wage and real wage 2015-16;
- the NO import-price anomalies;
- NO household income before 2007;
- SE electricity PPI before 1996;
- CEE surveys before 2000;
- the cross-border shopping s1/s2 series, never chained.

The palm-oil 2001 month (2001-07) is backed by a +26% step in the data. One break was missing and has been fixed (see Fixes).

### (g) Core flags: PASS

- The core set has exactly 200 features: all 90 composites plus 55 base series × 2 transforms. Key NO, SE and global variables are present: food CPI, PPI, import prices, grocery volumes, wages, real wages, policy rates, 10-year yields, EURNOK and EURSEK, Finans Norge and EC confidence, selling-price expectations, VAT, FAO/WB indices, GSCPI, packaging, and EA food HICP/PPI.
- There are no junk series, but three caveats apply:
  - `eu_agri_wheat_bread_price` has yoy only from 2017Q1 (38 obs).
  - Three core composites have no Norway data (55-63% coverage): `w_hh_saving`, `w_ec_cons_price_exp` and `w_ec_food_retail_sell_price_exp`.
  - The FAO/WB currency variants are heavily redundant, which matters for multiple testing.

### (h) Reproducibility: PASS

- The original script reproduced the delivered files byte for byte (md5).
- After the fixes, two consecutive runs give byte-identical outputs.
- The builder's own `spot_checks.py` still reports ALL OK.
- Diff against the original outputs: the panel changes only in `no_jordbruk_malpris_mnok__d4` (2025Q3-2026Q2). The dictionary changes in 10 notes or n_obs cells, and the notes gain the additions below.

### Other checks

- The 27 duplicate exclusions are confirmed identical or near-identical. Identical pairs have yoy correlation 1.0; near-identical pairs are at least 0.9997, with yoy differences up to 1pp for the FRED FX copies.
  - Minor: the dropped `WAGES/ea_hicp_idx` starts in 1996 and the kept `EU/ea_hicp_all_idx` in 1999, so EA headline HICP yoy starts in 2000Q1 rather than 1997Q1. The series is not core.
- Dictionary and panel: column sets and order match, with no duplicate ids, no all-NaN columns and no infinite values. n_obs, start and end match for all 1,420 features.
- Sign conventions of the FX crosses are confirmed: + means the local currency is weaker against EUR, USD or NOK. The pre-1999 ECU crosses are confirmed too.

## Fixes (edited in `macro_panel_build.py`, re-run)

1. **`no_jordbruk_malpris_mnok` scope break (core series).**
   - The NO catalog states that milk is no longer target-priced from the 2025 settlement, so the NOK-million amount shrinks structurally: 627 in 2024, then 288 in 2025 and 233 in 2026.
   - The build had neither masked nor noted this, so `__d4` showed a spurious -339 in 2025Q3-2026Q2.
   - Added to `D4_BREAK_MONTHS` (2025-07): d4 is now NaN in 2025Q3-2026Q2 and n_obs falls from 101 to 97. The dictionary note states that lvl from 2025Q3 is not comparable with earlier years.
2. **Dictionary notes added** (`NOISY_NOTES`):
   - `no_frontfag_frame_a`: the 2020 settlement was postponed (COVID-19), so the 2020Q1-Q2 values at lag 0 are not real-time.
   - `no_hh_real_disp_inc_sa_q`: the dividend spike in 2021Q4-2022Q1 distorts yoy in 2021Q4-2023Q1 (qa_B I5).
   - `no_jordbruk_ramme_mnok`: definitions vary between years, per the catalog (2002/2006 and the 2022 two-year total).
   - `ea_wage_tracker_yoy_q`: the 2013- history is a back-calculation.
3. **`macro_panel_notes.md`**, regenerated by the script:
   - a new block of real-time caveats in section 6 (weights from annual reports published after year end, full-sample z-score scaling, frontfag 2020, wage-tracker back-calculation, the HICP flash month, the jordbruk scope change);
   - the new break row in section 4;
   - a pointer to this file.

## Open issues (not changed; judgement calls or data limits)

- **Weights.**
  - The year-Y weights come from the annual report published in Feb-Mar of Y+1. That is mild look-ahead in the weighting only.
  - Before 2004 the weights are a proxy.
  - The Rest-of-Europe split, CZ/SK 75/25 and AT/DE 60/40 are assumptions. They are documented and affect 15-30% of revenue.
- **Vintage.** All series are the latest vintage: national accounts revisions, preliminary SE MI wages, and the re-estimated OECD, GSCPI and seasonal-adjustment histories. The ECB wage tracker's pre-publication history is a back-calculation.
- **`ea_wage_tracker_yoy_q` 2026Q3 is kept** (2.46, the current quarter from signed agreements). This is the builder's documented choice and is acceptable. Drop it if only official negotiated-wage quarters should count.
- **Approximations:**
  - the Baltic policy rate is proxied by the ECB rate from 1999, and EEK is treated as having zero yoy against the ECU in 1995-98;
  - the SE3 electricity splice means yoy in 2011Q1-2012Q3 partly compares the system price with area prices;
  - EE drops out of the survey composites from 2026Q2 (survey suspended; weight about 1.2%).
- **Screening.** Start from the core set or apply multiple-testing control, and shift each feature by `realtime_min_lag_q`. For quarters with VAT changes (2001-07 in Norway, 2026-04 in Sweden), use the `*_food_cpi_xvat_*` variants.
