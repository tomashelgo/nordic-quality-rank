# Orkla Foods spliced dataset: adversarial QA (verify-splice)

Date: 2026-10-06. Verifier label: `verify-splice`.

**Scope.** The five outputs of the splice task:
- `orkla_foods_quarterly.csv`
- `orkla_foods_alt_definitions.csv`
- `orkla_foods_annual.csv`
- `orkla_foods_methodology.md`
- `build_orkla_quarterly.py`

**Ground truth.** The verified raw extractions in `orkla_raw/`: `era_E1..E6_verified.csv`, the era notes and verify logs, `restatements.csv`, `segment_history.md` / `.json` and `ma_events.csv`.

I did not download the source PDFs again. Each era verifier had already re-extracted every raw row independently, so the raw rows are treated as ground truth.

**Method.** I wrote independent checking scripts. They do not reuse the builder's definition mapping (`assign_def`): they map each period to the expected printed label and report themselves, then compare every output cell with the raw rows. The scripts are in `scratchpad/scripts/verify-splice/`:
- `trace.py`: headline levels, comparatives, margins and organic growth (OG) against raw rows.
- `trace_table.py`: the sample trace table in section 1.
- `check_calc.py`: chain indices, Easter fields, growth and margin arithmetic, d_og arithmetic.
- `check_ogpy.py`: `og_py` against its source rows, and the definition-break flags.

## Bottom line

- **The headline numbers are correct.** All 106 headline quarters trace exactly to the right raw row (report, vintage, printed label) for revenue, EBIT, the printed margin and organic growth. All 102 prior-year values are the same-report comparative on the same definition and metric. `d_margin_yoy_pp`, the growth rates, the chain indices, the Easter fields and the annual sums all recompute exactly.
- **No cross-definition comparison slipped into `d_margin_yoy_pp`.**
- **Cross-definition comparisons in `d_og_yoy_pp` are all flagged.** There are 12 such quarters (`d_og_def_break`) and no unflagged ones.
- **Fixes were made.** One cross-definition value was blanked (2022Q2 `reported_ebit_nokm`). Seven organic-growth labels and seven notes overstated or omitted caveats and were corrected. Two annual reconciliation notes were added, and the methodology text was updated to match.
- **No headline revenue, EBIT, margin, `og_est`, `d_margin` or `d_og` value changed.**
- **The build is reproducible.** After the fixes it runs cleanly (exit 0, all internal checks pass) and two consecutive runs give byte-identical outputs.

## 1. Trace of headline quarters to raw rows (check a)

**Coverage.** `trace.py` checked all 106 quarters, with 0 mismatches:
- revenue, EBIT and `report`;
- the prior-year comparative in the same report (revenue and EBIT);
- `d_margin_yoy_pp` recomputed from NOK;
- the computed margin and the printed margin;
- `organic_growth_pct`;
- the metric label class of the current row against the comparative row.

**Sample.** The table below shows 29 quarters across all five definitions and every break. Row references are 0-based data-row indices in `era_E<k>_verified.csv`.

| period | def | raw current row (era file:row, report, label, vintage) | rev/EBIT | raw comparative row | py rev/EBIT | d_margin pp | OG raw -> og_est (quality) |
|---|---|---|---|---|---|---|---|
| 2000Q1 | A | E1:1 (Q1 2001, 'Orkla Foods', comparative, 'Operating profit') | 2487/89 | n/a | | n/a | none |
| 2001Q1 | A | E1:0 (Q1 2001, 'Orkla Foods', current, 'Operating profit') | 2706/128 | E1:1 (Q1 2001, comparative) | 2487/89 | 1.152 | 5.0 -> 5.0 (B) |
| 2001Q4 | A | E1:12 (Q4 2001, 'Orkla Foods', current, after goodwill) | 3054/284 | E1:13 (Q4 2001, comparative) | 3029/284 | -0.077 | 4.1 -> 4.1 (C) |
| 2002Q1 | A | E1:16 (Q1 2002, 'Orkla Foods', current, 'before goodwill') | 2688/167 | E1:17 (Q1 2002; 2001 restated to EBITA) | 2706/169 | -0.033 | 4.0 -> 4.0 (B) |
| 2003Q2 | A | E1:36 (Q2 2003, current) | 2898/241 | E1:37 (Q2 2003, comparative) | 2641/185 | 1.311 | 3.0 -> 3.0 (A) |
| 2004Q4 | A | E1:60 (Q4 2004 Norwegian report, 'Driftsresultat før goodwill...') | 3481/412 | E1:61 | 3379/359 | 1.211 | -1.0 -> -1.0 (A) |
| 2005Q1 | A | E1:64 (Q1 2005, IFRS) | 3154/181 | E1:65 (2004 restated to IFRS) | 3112/200 | -0.688 | -2.4 -> -2.4 (C) |
| 2005Q4 | A | E1:76 (Q4 2005) | 3862/433 | E1:77 | 3481/396 | -0.164 | -1.0 -> -1.0 (A) |
| 2006Q3 | A | E2:20 (Q3 2006) | 3506/341 | E2:21 | 3324/319 | 0.129 | 1.0 -> 1.0 (A) |
| 2007Q4 | A | E2:70 (Q4 2007) | 4229/388 | E2:71 | 4201/459 | -1.751 | 0.6 -> 0.6 (A) |
| 2008Q1 | B | E2:80 (Q1 2008, 'Orkla Foods Nordic') | 2293/160 | E2:81 (2007 restated to B, incl. Baltics) | 2207/152 | 0.091 | 6.0 -> 6.0 (B) |
| 2008Q2 | B | E2:88 (Q2 2008, 'Orkla Foods Nordic') | 2436/262 | E2:89 | 2422/219 | 1.713 | 4.0 -> 4.0 (C) |
| 2009Q3 | B | E2:128 (Q3 2009) | 2377/297 | E2:129 | 2392/287 | 0.496 | -2.0 -> -2.0 (B) |
| 2010Q1 | B | E3:0 (Q1 2010) | 2190/194 | E3:1 | 2283/171 | 1.368 | -3.3 -> -3.3 (B, Easter-adjusted) |
| 2012Q1 | B | E3:64 (Q1 2012) | 2026/197 | E3:65 (2011, incl. Bakers) | 2213/186 | 1.319 | 5.0 -> 5.0 (B) |
| 2012Q4 | B | E3:88 (Q4 2012) | 2378/392 | E3:89 | 2650/357 | 3.013 | blank -> -1.2 (C, estimate) |
| 2013Q1 | C | E3:96 (Q1 2013, 'Orkla Foods') | 1924/226 | E3:97 (2012 restated to C, incl. IAS 19R) | 1898/202 | 1.104 | 0.0 -> 0.0 (B) |
| 2013Q2 | C | E3:104 (Q2 2013) | 2382/263 | E3:105 | 1938/262 | -2.478 | -4.2 -> -4.2 (B) |
| 2014Q3 | C | E4:16 (Q3 2014) | 2526/343 | E4:17 | 2597/364 | -0.437 | -3.4 -> -3.4 (B) |
| 2014Q4 | D | E4:24 (Q4 2014, EBITA) | 3371/470 | E4:25 (2013Q4 restated to D) | 3321/436 | 0.814 | 2.2 -> 2.2 (B) |
| 2015Q1 | D | E4:30 (Q1 2015, EBIT (adj.)) | 3045/322 | E4:31 (2014 restated to D and EBIT (adj.)) | 2920/309 | -0.007 | 4.1 -> 4.1 (A) |
| 2016Q2 | D | E4:60 (Q2 2016) | 3967/463 | E4:61 | 3122/389 | -0.789 | 3.9 -> 3.9 (A) |
| 2018Q4 | D | E5:12 (Q4 2018) | 4366/651 | E5:14 | 4384/689 | -0.806 | 2.7 -> 2.7 (A) |
| 2020Q1 | D | E5:32 (Q1 2020) | 4618/535 | E5:34 | 3889/430 | 0.528 | 10.8 -> 10.8 (A) |
| 2022Q2 | D | E6:4 (Q2 2022, old definition incl. India) | 4957/480 | E6:5 | 4465/517 | -1.896 | 11.6 -> 11.6 (A) |
| 2022Q3 | E | E6:8 (Q3 2022, 'Orkla Foods Europe') | 4340/526 | E6:9 (2021Q3 restated to E) | 4312/652 | -3.001 | 4.2 -> 4.2 (A) |
| 2023Q1 | E | E6:20 (Q1 2023) | 4903/510 | E6:21 (2022Q1 on E) | 4239/469 | -0.662 | 10.3 -> 10.3 (A) |
| 2024Q4 | E | E6:62 (Q4 2024, renamed 'Orkla Foods') | 5505/681 | E6:63 | 5504/635 | 0.834 | 1.1 -> 1.1 (A) |
| 2026Q2 | E | E6:98 (Q2 2026) | 4799/606 | E6:99 | 5107/614 | 0.605 | -1.3 -> -1.3 (A) |

**Cross-check against the separately published restatements (`restatements.csv`).** The comparatives used at each break equal the restated figures:

| Restatement | Values (revenue/EBIT) | Used at |
|---|---|---|
| B 2007 (Q1-2008 xls) | 2,207/152, 2,422/219, 2,308/235, 2,611/287 | 2008 |
| C 2012 (Apr-2013 pdf) | 1,898/202, 1,938/262, 1,973/312, 2,163/368 | 2013 |
| D 2013Q4 (Jan-2015 pdf) | 3,321/436 | 2014Q4 |
| D 2014Q1-Q3 | 2,920 / 3,041 / 2,900 | 2015 |
| E 2021Q3/Q4 | 4,312/652 (OG 4.7), 4,578/663 (OG 3.9) | 2022Q3/Q4 |
| E 2022Q1/Q2 | 4,239/469 (OG 7.3), 4,318/405 (OG 10.4) | 2023Q1/Q2 |

**Alternative-definitions file.** Spot-checked against the raw rows and `restatements.csv`; all match:
- A 2001 EBITA (169 / 215 / 244 / 324) and A 2004 IFRS (200 / 258 / 310 / 396).
- A sub-segments 2004-07, which reconcile to A. Example, 2004Q1: 2,243 + 624 + 293 − 48 = 3,112.
- D 2014 in both metrics (EBITA 309 / 357 / 359; EBIT (adj.) 309 / 356 / 357 / 466).
- E 2021Q3-2022Q2 and India 2021Q3-2026Q2.
- `D_DERIVED` = E + India. Example OG, 2022Q3: (4.2 × 4,312 + 20.1 × 545) / 4,857 = 5.98. The 2022 annual figure is 8.05.

## 2. `d_margin_yoy_pp` and cross-definition slips (check b)

- **All 102 quarters from 2001Q1 use same-report comparatives** (`dm_source = same_report`). The code's fallback (`other_same_def`) is never used.
- **The break quarters checked one by one are all clean:**

| Quarter | Change | Comparison used |
|---|---|---|
| 2002Q1 | goodwill amortisation dropped | 2001 restated to EBITA, 169 vs 128 originally |
| 2005Q1 | IFRS | 2004 IFRS 200 vs NGAAP 205 |
| 2008Q1 | A→B | restated B 2007 |
| 2013Q1 | B→C, IAS 19R | restated C 2012 |
| 2014Q4 | C→D | restated D 2013Q4, both EBITA |
| 2015Q1 | metric change to EBIT (adj.) | EBIT (adj.) against EBIT (adj.), 309 |
| 2022Q3 | D→E | E-basis 2021Q3 |
| 2024Q4 | rename | identical figures |

- **No quarter compares across definitions or metrics.**
- **Not definition breaks, but contained in `d_margin` by design (already documented):**
  - Bakers divestment, 2012: the 2011 comparatives include Bakers.
  - The restated C 2012Q1 still contains January 2012 Bakers (verify-E3 #4).
  - Rieber, 2013Q2-2014Q1.
  - IFRS 16, 2019 (not restated).
  - Unrestated internal transfers: Frödinge 2020Q4, Scoop/Pastella 2018Q1, NP Foods 2015Q4, and the Danish distribution agreement 2026Q1.
- **`d_og_yoy_pp` crosses definitions in exactly 12 quarters, all flagged with `d_og_def_break` and `og_py_source`.** `check_ogpy.py` confirmed every `og_py` value against its source row and found no unflagged break:
  - 2008Q1-Q4 against the A_NORDIC 2007 proxy;
  - 2013Q1-Q4 against B;
  - 2014Q4 and 2015Q1-Q3 against C.
- **The same-report OG comparative is preferred wherever it exists.** This puts 2023Q1/Q2 on the E basis (7.3 / 10.4), not the D basis (7.2 / 11.6). No same-report comparative OG was ignored.

## 3. Organic-growth quality flags and estimates (check c)

Every headline `og_quality` was compared with the raw `og_metric` wording and the verify logs:

| Item to check | Finding |
|---|---|
| Easter- or calendar-adjusted 2010-2014 | 2010Q1, 2011Q1, 2011Q2 (Easter) and 2014Q1-Q2 (Easter and selling days) are adjusted, as are 2014Q3-Q4 (selling days; verify-E4 #1). All are `og_easter_adjusted` = true, quality B. 2010Q2 (-6) and 2012Q1 (+5) are correctly unadjusted. **OK.** |
| YTD-derived values 2001-2004 | 2001Q2-Q4, 2002Q3 and 2004Q2-Q3 are quality C, and all recompute from the YTD inputs: -1.39, 2.49, 4.09, 0.99, -1.76, -1.87. **OK.** |
| 2005Q1-Q3 filled average | Quality C; (-2 × 12,711 + 1 × 3,481) / 9,230 = -2.38. **Label fixed:** it said "derived from YTD" (fix F2). |
| 2008Q2 derived | Quality C. The formula gives 4.09, while the verified extraction keeps the rounded 4.0. **Note added** (fix F3); value kept. |
| 2013 Rieber pro forma | 2013Q2 is stated as incl. Rieber pro forma (quality B). 2013Q3-Q4 are quality B because the Rieber treatment is **not stated**. **Labels fixed:** they claimed "incl. Rieber pro forma". The claim "FY -4.2 consistent with incl. Rieber" was wrong: the quarters weight to -3.5, or -3.7 with Rieber pro forma in the base (fix F2/F3). |
| 2009Q1 doubtful | The food value is "decline of about 2%", quality B. The "doubtful" item in verify-E2 #3 is the **parent Orkla Brands** 0%, which is not used. **Note added** (fix F3). |
| 2001Q1 / 2008Q1 doubtful | Quality B overrides with notes. 2001Q1 is probably not FX-adjusted; 2008Q1 has no explicit FX exclusion. **OK.** |
| Verbal approximations | 2002Q1-Q2 ("approximately"), 2006Q1/Q4 and 2009Q2 ("on a par"), 2008Q3-Q4 and 2009Q1/Q3 ("about" / "roughly"), 2012Q1 ("about 5%") and 2013Q1 ("on a par") are all quality B. **OK.** Notes added for 2002Q1/Q2 and 2012Q3 (fix F3). |
| 2012Q2 estimate (-3.1) | Recomputed: (0.8 × 4,604 − 5 × 2,213) / 2,391 = -3.09. Sourced, with sensitivity in the note. Defensible. **Label fixed** to say ESTIMATE (fix F2). |
| 2012Q4 estimate (-1.2) | Recomputed: (1 × 9,496 − 0.8 × 4,604 − 4 × 2,242) / 2,650 = -1.19. It is consistent with "small underlying decline". It rests on the bar-chart FY +1%, so the range is -3.0 to +0.6, as documented. Defensible. **Label fixed** (fix F2). |

Counts are unchanged: `og_est` quality A 67, B 23, C 12, missing 4; `d_og` quality A 52, B 28, C 18.

## 4. Easter (check d)

- **`easter_date`.** Equal to `dateutil.easter` for every year from 2000 to 2026. The 1999 date, used for the 2000 shift and window change, comes from the same algorithm.
- **`easter_q` and `easter_shift`.** Recomputed: +1/−1 when the Easter Sunday quarter changes, 0 in Q3/Q4. Q1 Easter years are 2002, 2005, 2008, 2013, 2016 and 2024. **Correct.**
- **`easter_window_q1_share` and `d_easter_window_q1`.** The 9-day window runs from Palm Sunday to Easter Monday; Q2 = −Q1. Recomputed for all rows. **Correct.**
- **Caveat** (documented in methodology §5.3; not a defect). The `drivers_note` texts show two things:
  - Orkla's sell-in to retailers runs ahead of the consumer window. Q1 2012 (Easter 8 April) had "half" of its +5% from Easter, and Q1 2015 (Easter 5 April) reports "Easter timing positive". Both quarters have `easter_shift` = 0.
  - The sign varies. Q1 2016 (Easter in Q1) reports "Easter timing negative", and Q1 2018 reports fewer sales days.

  `easter_shift` keys on Easter Sunday, so 2018 is coded 0 even though 78% of the window fell in Q1. The window measure captures this. Treat both as proxies.

## 5. Chain indices (check e)

- **Recomputation.** `check_calc.py` rebuilt `rev_chain_idx` and `ebit_chain_idx` independently: same-quarter chains forward from 2015 and backward to 2000. They match to the 3rd decimal, and the 2015 mean is exactly 100.0.
- **Ratio of index to level.**
  - Revenue: constant within each definition, so there is no hidden restatement within a definition.
  - EBIT: piecewise constant, with a spread under 3e-5. It steps only at the metric changes inside A (2002 goodwill, 2005 IFRS) and at D 2014Q4 (EBITA) to 2015Q4 (EBIT (adj.)). That is the intended behaviour.

## 6. Annual file (check f)

**Full-year sums.** All 38 printed full-year sets (definition / year / metric) equal the four-quarter sums. I checked every hard-coded `PRINTED_FY` constant against the era verify logs and segment history, and all match.

**Headline selection and y/y.** All correct:
- the year-end definition with the metric as reported that year;
- 2014 = D EBITA 12,232/1,495 against D 2013 restated 11,110/1,312;
- 2022 = E 17,820/1,973 against E 2021 16,891/2,243;
- 2008, 2013 and 2015 compare with the sums of the same-report comparatives.

**Reported full-year OG against revenue-weighted headline quarters.**
- **Agreement:** within whole-percent rounding (at most 0.5pp) for A 2001-07, B 2009-12 and D 2015-21. The computed E 2023-25 values recompute: 6.63, 1.89, -0.18.
- **Two outliers, now annotated in `notes`** (fix F5):
  - B 2008: bar chart 4.0 against quarters 4.7.
  - C 2013: printed -4.2 against quarters -3.5.
- **Not comparable:** 2014 and 2022, whose headline quarters mix definitions. On the E basis, 2022 gives 7.19 against the printed 7.2.

## 7. Script and reproducibility (check g)

- **Original state.** The script reproduced the delivered files byte for byte before any edit.
- **After the fixes.** It exits 0 with all internal checks passing, and two consecutive runs give byte-identical files.
- **What changed.**
  - `orkla_foods_alt_definitions.csv` is unchanged.
  - `orkla_foods_annual.csv` changed only in two `notes` cells.
  - `orkla_foods_quarterly.csv` changed only in the cells listed in section 8.
  - The methodology auto block was regenerated.
- **Out of scope.** Other agents' `macro_panel_*` and `feature_dictionary` files were not touched.

## 8. Fixes made (all in `build_orkla_quarterly.py`, then rebuilt)

| # | Fix | Cells changed |
|---|---|---|
| F1 | **Cross-definition level removed.** 2022Q2 is a definition-D row (EBIT (adj.) 480), but it carried `reported_ebit_nokm` = 389, the Orkla Foods **Europe** reported EBIT. Its own EBIT (adj.) is 405. Next to the D EBIT this implies a spurious -91m of other income and expenses, or a 7.8% "reported margin". The value is now blank and quoted in `kpi_source`. The E-basis rates (price 7.4, volume/mix 3.0, contribution ratio 37.3, underlying EBIT growth -9.4) are kept, as the builder decided, and flagged. | `reported_ebit_nokm` and `kpi_source`, 2022Q2 |
| F2 | **Organic-growth labels corrected.** 2013Q3/Q4: "incl. Rieber pro forma" became "Rieber treatment not stated (Q2 2013 was incl. Rieber pro forma)". 2005Q1-Q3: "derived from YTD" became "9M-2005 average implied by FY and Q4 (not quarter-specific)". 2012Q2/Q4: added "ESTIMATE (no quarterly figure published; og_est only)". | `og_label`, 7 rows |
| F3 | **Caveat notes corrected or added.** 2013Q3/Q4: the "FY -4.2 consistent with incl.-Rieber" claim is replaced by the actual reconciliation. Added: 2008Q2 (formula 4.09 against the extraction's 4.0); 2009Q1 (the verify-E2 doubt concerns the parent row); 2002Q1/Q2 ("approximately"); 2012Q3 (timing effects reversing in Q4). | `og_est_note`, 7 rows |
| F4 | **Methodology text updated.** §5.2 (2013Q3-Q4 basis), §5.3 (Easter proxies and sell-in timing), §5.5 (2022Q2 `reported_ebit_nokm`), §9 (full-year OG reconciliation and a pointer to this file) and §11.2 (Rieber). | `orkla_foods_methodology.md` |
| F5 | **Annual reconciliation notes added** for B 2008 and C 2013. | `orkla_foods_annual.csv` `notes`, 2 rows |

No numeric headline series value changed: revenue, EBIT, margins, `og_est`, `og_py`, `d_margin_yoy_pp`, `d_og_yoy_pp`, the quality flags and the indices are all identical to the delivered files.

## 9. Open issues (judgement calls, documented, not changed)

1. **2022Q2 price/volume and KPIs are on the E basis inside a D row.** They sum to E organic 10.4, not D 11.6. They are kept because the specification asks for 2022Q2, and they are flagged in `kpi_source`. Drop them if strict definition purity is needed.
2. **12 `d_og` quarters cross a definition break** (2008, 2013, 2014Q4-2015Q3). Dummy or down-weight them. 2015Q1-Q3 also compare with Easter- and selling-day-adjusted 2014 values.
3. **Mixed calendar bases inside a year.**
   - 2010Q1 is Easter-adjusted while 2010Q2 is not, so the 2011Q2 `d_og` compares adjusted with unadjusted.
   - 2002Q1 compares with 2001Q1, which is probably not FX-adjusted (the FX-adjusted value is about 7-8%). That `d_og` of -1.0 could be about -3.5.
   - 2002Q2 uses 2001Q2 -1.4, which is an upper bound (about -3.4 on a consistent basis).
4. **`easter_shift` is keyed on Easter Sunday.** For a sell-in business, consider a wider pre-Easter window as a sensitivity.
5. **2008Q2 OG is 4.0 in the verified extraction against 4.09 by formula.** The difference is within the documented ±1.4pp; the value was kept.
6. **Two printed full-year OG values differ noticeably from their quarters** (B 2008, C 2013), and the annual file uses the printed values. For C 2013, the quarterly mix of Rieber bases (Q2 pro forma, Q3/Q4 unstated) is the most likely cause.
7. **Not verified here: driver and event narrative text.** I spot-checked about 10 event notes against `ma_events.csv` and `segment_history.md`, and all are consistent. The rest of the narrative text was not checked line by line.
