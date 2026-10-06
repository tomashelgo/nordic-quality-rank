# Orkla Foods quarterly dataset: methodology

Built 2026-10-06 from the Q1 2001 to Q2 2026 reports, which are the latest available. All amounts are NOK million.

## 1. Files

| File | Content |
|---|---|
| `orkla_foods_quarterly.csv` | **Headline series**, one row per quarter, 2000Q1 to 2026Q2 (106 rows). For each quarter it holds the figures *as originally reported* under the food-segment definition in force at the time. Y/y changes use the prior-year comparative printed in the same report. |
| `orkla_foods_alt_definitions.csv` | Restated and alternative definitions, kept separate from the headline: A sub-segments 2004-07, B 2007, C 2011-12, D 2013Q1-2014Q4, E 2021Q3-2022Q2, Orkla India 2021Q3-2026Q2, and D derived as E + India for 2022Q3-2026Q2. It also holds alternative profit metrics of the headline definition (A 2001 NGAAP EBITA, A 2004 IFRS). |
| `orkla_foods_annual.csv` | Annual figures 1992-2025, one row per year, definition and metric, with `is_headline` marking the main series. 2026 is not included because only H1 is reported. |
| `build_orkla_quarterly.py` | Reproducible build from `orkla_raw/*.csv`. Every manual override or estimate is an explicit dictionary in the script, with its source cited. The script also refreshes the tables between the AUTO markers at the end of this file. |

Rebuild with `python3 -I data/build_orkla_quarterly.py`. The script prints the coverage and consistency checks (section 10).

Inputs: `orkla_raw/era_E1_verified.csv` to `era_E6_verified.csv`, the verified extractions with every value re-extracted independently. Also `restatements.csv`, `segment_history.json` (pre-2001 annual figures), and the era notes and verification logs, which are the source of the caveats in this document.

## 2. Segment definitions

| id | Label in reports | Headline quarters | Scope | India? |
|---|---|---|---|---|
| A | Orkla Foods | 2000Q1-2007Q4 (2000 = comparatives printed in the 2001 reports) | All food. **Nordic** (Stabburet, Bakers, Procordia, Abba Seafood, Beauvais, Felix Abba) + **Orkla Food Ingredients** (Idun, KåKå, Credin 2003-, Odense Marcipan ...) + **Orkla Foods International** (CEE; SladCo RU 2005-, Krupskaya RU 2006Q3-, Baltics). Panda (FI confectionery) from 2005Q2. | MTR from 2007Q2 (inside International) |
| B | Orkla Foods Nordic | 2008Q1-2012Q4 | Nordic + Baltic food, inside "Orkla Brands". Includes Bakers to 31 Jan 2012, Panda, and Kalev (EE chocolate) from 2010Q2. Excludes Ingredients and International. | no |
| C | Orkla Foods | 2013Q1-2014Q3 | B without Panda/Kalev confectionery. Bakers was already sold. Rieber & Søn Nordic food from 1 May 2013. MTR, Vitana and Felix Austria sat in Orkla International, outside C. | no |
| D | Orkla Foods | 2014Q4-2022Q2 | C + MTR India, Vitana CZ and Felix Austria (Orkla Foods International). Kavli DK 2016Q1-, Hamé CZ/SK 2016Q2-, Easyfood 2019Q2-, Eastern Condiments India 2021Q2-. | **yes** (about 5% of revenue, rising to about 11-13% after Eastern) |
| E | Orkla Foods Europe, renamed Orkla Foods from the Q4 2024 report | 2022Q3-2026Q2 | D without Orkla India. The 2023 operating model and the 2025 rename did not change the scope (FY2022 = 17,820 and FY2024 = 20,594 in both versions). | no |

Sub-segment and derived ids, used only in the alternative and annual files:
- `A_NORDIC`: Orkla Foods Nordic, the 2005-07 sub-segment of A. Includes Bakers and Panda; excludes the Baltics.
- `A_OFI`, `A_INTL`, `A_ELIM`: Orkla Food Ingredients, Orkla Foods International, and the eliminations within A. A = sum of the sub-segments less eliminations. Most eliminations are derived as a residual.
- `IND`: Orkla India.
- `D_DERIVED`: D continued after 2022Q2 as E + India.
- `PRE`: the 1990s Orkla Foods business area, annual figures only.

The segment history labels the renamed segment "F". It has exactly the same scope as E, so it shares id `E`, and only `segment_label` changes.

## 3. Profit metric history

| Quarters | `ebit_metric` | Notes |
|---|---|---|
| 2000Q1-2001Q4 | NGAAP operating profit **after** goodwill amortisation | Only basis printed for 2000. The 2002 reports restate 2001 to EBITA, about +40m per quarter (2001 FY: 791 becomes 952). |
| 2002Q1-2004Q4 | NGAAP EBITA (before goodwill amortisation) | Excludes "other revenues and expenses" (restructuring, gains). |
| 2005Q1-2014Q4 | EBITA (IFRS): operating profit before amortisation and other income/expenses | IFRS adoption: the 2004 comparatives were restated (FY 1,178 becomes 1,164) and the quarterly profile shifts. **IAS 19R**: the 2012 comparatives in the 2013 reports, and all C/D restatements, include the pension change, which raises EBITA (C 2012: 1,114 becomes 1,144). B 2008-12 is pre-IAS 19R. |
| 2015Q1- | EBIT (adj.): operating profit before other income and expenses, i.e. after amortisation of intangibles | The 2014 comparatives were restated: FY2014 EBITA 1,495 becomes EBIT (adj.) 1,488, and quarters move by 0-4m. |
| 2019Q1- | EBIT (adj.) under IFRS 16 | 2018 was **not restated**. The group EBIT effect is about +20m a year, so for Orkla Foods it is below about 0.1pp of margin. EBITDA would jump, which is why the dataset does not use it. `ifrs16_transition` = true for 2019Q1-Q4. |

`ebit_margin_pct` is always computed from NOK as EBIT / revenue. `ebit_margin_printed` keeps the printed margin where one exists (57 quarters); the two agree within 0.05pp. The one exception is 2025Q4: printed 12.8 against 718/5,633 = 12.75, a print-rounding quirk.

Items **excluded** from segment EBIT by definition include: Q3 2007 NOK -324m (Romania goodwill, Superfish), Q4 2010 Bakers goodwill -276m, Q4 2011 Bakers sale -155m, the Öland closure, and the Bakehuset acquisition costs. From 2023, reported EBIT, i.e. after other income and expenses, is in `reported_ebit_nokm`.

## 4. How the y/y series avoids every break

**Rule.** For each quarter, `revenue_py_samedef` and `ebit_py_samedef` are the prior-year figures **printed as comparatives in the same report** as the current figure. They are therefore always on the same definition, metric and accounting basis as the current quarter. This holds for all 102 quarters from 2001Q1 (`dm_source = same_report`). 2000 has no prior-year quarters, because Orkla reported four-monthly until 2000 (`dm_source = none`).

From these:
- `d_margin_yoy_pp = 100 × (EBIT/revenue − EBIT_py/revenue_py)`, computed from NOK, not from rounded margins.
- `rev_growth_samedef_pct` and `ebit_growth_samedef_pct` are the corresponding growth rates.

| Break | Quarter | Change | How the y/y series handles it |
|---|---|---|---|
| Metric | 2002Q1 | Goodwill amortisation dropped (EBITA) | 2002 reports compare with 2001 restated to EBITA. 2001 reports compare after-goodwill with after-goodwill. |
| Accounting | 2005Q1 | NGAAP to IFRS | 2005 reports compare with 2004 restated to IFRS. |
| Definition A→B | 2008Q1 | Orkla Foods dissolved into Orkla Brands. Headline becomes Orkla Foods Nordic, with the Baltics added (+257m/yr). | 2008 reports compare with 2007 restated to B (9,548 vs 9,291 old basis). |
| Divestment | 2012Q1-Q4 | Bakers (about 1.2bn/yr) deconsolidated 1 Feb 2012; comparatives **not** restated | Not a break in definition. It is an M&A effect inside reported revenue growth (-6 to -14%); organic growth excludes it. |
| Definition B→C, IAS 19R | 2013Q1 | Panda/Kalev out. Pension restatement. | 2013 reports compare with 2012 restated to C incl. IAS 19R. Note the restated 2012 still includes Bakers in January 2012 (verify-E3 #4). |
| Definition C→D | 2014Q4 | International food units (incl. India) added | Q4 2014 report compares with 2013Q4 restated to D (3,321/436). D quarters 2014Q1-Q3 exist only in the alternative file. |
| Metric | 2015Q1 | EBITA to EBIT (adj.) | 2015 reports compare with 2014 restated to D and EBIT (adj.). |
| IFRS 16 | 2019 | Lease accounting, not restated | Residual break (EBIT effect negligible), flagged by `ifrs16_transition`. |
| Definition D→E | 2022Q3 | India carved out | The Q3 2022 to Q2 2023 reports compare with Europe-only comparatives (2021Q3/Q4 and 2022Q1/Q2). |
| Rename | 2024Q4 | Orkla Foods Europe renamed Orkla Foods | Identical figures; no break. |

**Levels jump at each definition change.** For example, 2014Q3 C 2,526 is followed by 2014Q4 D 3,371, and 2022Q2 D 4,957 by 2022Q3 E 4,340. Analyse growth rates and margin changes, not raw levels across definitions. For a level series use the chain indices (section 7).

**Organic growth needs no splice.** It is a like-for-like rate printed for the definition in force. At breaks, though, the prior-year rate used for `d_og_yoy_pp` may come from a different definition; see section 5.4.

## 5. Organic growth

### 5.1 Definition history

| Quarters | Term | Definition |
|---|---|---|
| 2001Q1-2003Q1 | "growth for continuing business" | Adjusted for M&A and currency. 2001Q1 does not state an FX adjustment and is probably not FX-adjusted. |
| 2003Q2-2014Q4 | "underlying growth" | Excludes acquisitions/divestments and currency translation. From about 2013 it also excludes "other considerable structural changes". |
| 2015Q1-2016Q1 | "organic growth" | Excludes acquired/sold companies and FX. |
| 2016Q2-2023Q1 | organic growth, ESMA APM | Acquisitions excluded for 12 months; divestments pro forma for the prior 12 months; FX at prior-year rates. Table split organic / FX / structure from 2016Q2 (BCG) and 2018Q4 (Orkla Foods). Organic row in the segment table from 2017Q4. |
| 2021 (in practice), 2023Q2 (formally) | same | **Material distribution agreements** won or lost and **intra-group transfers** count as structure, not organic. Examples: Panzani 2020, OTA Solgryn 2021, Tropicana/Alpro 2022-24, Quaker 2026, Frödinge 2020, plant-based production 2023. |
| 2023Q2- | price vs volume/mix | `price_pct` = net price at unchanged volume; `volume_mix_pct` = organic growth − price. |

**Distribution agreements before 2021 were counted as ORGANIC.** Tropicana (SE/DK) from 2015 and the expanded PepsiCo deal (Tropicana NO, Quaker Nordics) from 2016 inflate 2015-16 organic growth relative to later practice. Orkla explicitly credits them for Orkla Foods' growth in those years. They are flagged in `event_note`.

**Hyperinflation:** none in the food segment. Organic growth includes local price inflation, e.g. the 2022-23 price growth of +10-16%.

### 5.2 Quality flags (`og_quality`)

| Flag | Meaning | Count | Quarters |
|---|---|---|---|
| A | Quarterly figure stated in a table, text or slide, on the standard unadjusted basis | 67 | the rest from 2002Q4 |
| B | Stated, but calendar-adjusted; or verbal "about / approximately / on a par"; or incl. pro-forma acquisitions; or doubtful per the verification notes | 23 | 2001Q1 (FX adjustment not stated), 2002Q1-Q2 (approx.), 2006Q1 and 2006Q4 ("on a par"), 2008Q1 (approx., no explicit FX exclusion), 2008Q3-Q4 and 2009Q1-Q3 (about / on a par), 2010Q1, 2011Q1 and 2011Q2 (Easter-adjusted), 2012Q1 (about 5%, half of it Easter), 2013Q1 (on a par), 2013Q2 (incl. Rieber pro forma) and 2013Q3-Q4 (Rieber basis not stated; the printed FY -4.2 does not reconcile with the quarters, which weight to -3.5), 2014Q1-Q4 (Easter- and/or selling-day-adjusted) |
| C | Derived from YTD differencing, filled with a period average, or estimated | 12 | 2001Q2-Q4, 2002Q3, 2004Q2-Q3, 2005Q1-Q3 (a 9M average assigned to each quarter), 2008Q2, 2012Q2 and 2012Q4 (estimates) |
| blank | not available | 4 | 2000Q1-Q4 |

`organic_growth_pct` holds the published value, or the YTD-derived value from the verified extraction. `og_est` equals `organic_growth_pct` where that exists. Otherwise it holds a documented estimate:
- **2012Q2 = -3.1**: H1 +0.8 (Q2 2012 presentation) and Q1 about +5, weighted by 2011 revenue.
- **2012Q4 = -1.2**: FY2012 +1% (Q4 2012 presentation) less H1 and Q3. This matches the report's "small underlying decline".

Both are quality C, with the formula in `og_est_note`. The 2000 quarters are blank. The YTD-derived and averaged quarters carry their rounding ranges in `og_est_note`. In particular, 2001Q2 -1.4 mixes an FX-adjusted H1 with a probably non-FX-adjusted Q1: a basis-consistent value is about -3.4, so treat -1.4 as an upper bound.

### 5.3 Easter and calendar adjustment

- From 2015 all organic growth is **unadjusted** for Easter. The text only describes Easter effects.
- Seven quarters are printed only on a calendar-adjusted basis (`og_easter_adjusted` = true, quality B): 2010Q1, 2011Q1 and 2011Q2 (Easter); 2014Q1 and 2014Q2 (Easter and selling days); 2014Q3 and 2014Q4 (selling days). The 2010Q2 figure, -6%, is *not* stated as adjusted.
- 2012Q1 (+5%) is unadjusted, and about half of it came from Easter.
- Calendar variables computed with the anonymous Gregorian algorithm:
  - `easter_date`.
  - `easter_q`: the quarter containing Easter Sunday.
  - `easter_shift`: +1 if Easter falls in this quarter this year but not last year; −1 for the reverse; 0 otherwise (always 0 in Q3/Q4).
  - `easter_window_q1_share`: the share of the 9-day Palm Sunday to Easter Monday shopping and holiday window that falls in Q1.
  - `d_easter_window_q1`: the y/y change in that share, with Q2 = minus the Q1 value.

  The window measure picks up years such as **2018** (Easter Sunday 1 April, so `easter_q` = 2 and `easter_shift` = 0, but 78% of the Easter window was in Q1). The Q1 2018 report blames Easter for lost selling days. Easter Sunday quarters: Q1 in 2002, 2005, 2008, 2013, 2016 and 2024; Q2 in all other years.
- **Both calendar variables are proxies, and the sign of the Easter effect is not fixed** (splice QA, from the `drivers_note` texts):
  - Orkla's revenue is sell-in to retailers, and deliveries run ahead of the consumer window. Q1 2012 (Easter 8 April) had about half of its +5% from Easter, and Q1 2015 (Easter 5 April) reports "Easter timing positive". Both quarters have `easter_shift` = 0 and a small or zero window change.
  - An Easter inside Q1 can also cost selling days. Q1 2016 (Easter 27 March) reports "Easter timing negative", and Q1 2018 reports fewer sales days.
  - Treat the coefficient sign as an empirical question. As a sensitivity, try a wider pre-Easter window.
- For regressions on y/y organic growth or margin change, include `easter_shift` or `d_easter_window_q1`, or work with H1 (Q1+Q2) aggregates.

### 5.4 Prior-year organic growth (`og_py`, `d_og_yoy_pp`)

`og_py` is the same-quarter prior-year organic growth, taken from the most comparable source, in this order:
1. The prior-year organic growth printed as a comparative in the same report (`same_report_comparative`, 32 quarters, from 2017Q4). This matters at the D→E break: 2023Q1 uses E 7.3 rather than D 7.2, and 2023Q2 uses E 10.4 rather than D 11.6.
2. The prior-year headline `og_est` on the same definition (`prior_headline_same_def`, 54 quarters).
3. For 2008Q1-Q4, the 2007 organic growth of the Orkla Foods Nordic sub-segment (`alt_def_proxy`). This is closer to B than the A total, because B = that sub-segment plus the Baltics.
4. Otherwise the prior-year headline on a different definition (`prior_headline_other_def`): 2013Q1-Q4 against B, and 2014Q4 and 2015Q1-Q3 against C. The 2015Q1-Q3 comparison is also against calendar-adjusted 2014 figures.

`d_og_yoy_pp = og_est − og_py`. `d_og_quality` is the worse of the two components' flags. `d_og_def_break` = true for the 12 quarters whose `og_py` comes from another definition (2008Q1-Q4, 2013Q1-Q4, 2014Q4, 2015Q1-Q3); down-weight or dummy them. Coverage: 98 quarters, 52 A / 28 B / 18 C.

### 5.5 Decomposition columns

- `fx_effect_pct` and `structural_effect_pct`:
  - Orkla Foods APM table 2018Q1-2026Q2. 2018Q1-Q3 are filled from the 2019 report comparatives; 2017Q4 from the Q4 2018 comparative.
  - 2012Q1-Q2 FX is derived from the presentation translation slides (NOK m / prior-year revenue).
  - Not published for Orkla Foods otherwise. The 2014-17 notes give only the combined residual, reported minus organic.
- `price_pct` and `volume_mix_pct`:
  - Printed from the Q2 2023 report.
  - 2022Q3, 2022Q4 and 2023Q1 come from the comparatives in the Q3/Q4 2023 and Q1 2024 reports.
  - **2022Q2 (7.4 / 3.0) is the Orkla Foods Europe (E) split from the Q2 2023 comparative.** It sums to E organic growth of 10.4, not to the headline D figure of 11.6 (see `kpi_source`).
  - The 2022Q1 split was never published; verify-E6 approximates it as price about 4.4 and volume/mix about 2.8, which is not used.
- `contribution_ratio_pct`, `underlying_ebit_growth_pct` and `reported_ebit_nokm`:
  - E-basis KPIs from 2022Q2 (the 2022Q2-2023Q1 values are from later comparatives).
  - For **2022Q2** (a definition-D row) only the E-basis *rates* are kept: price, volume/mix, contribution ratio and underlying EBIT growth. `reported_ebit_nokm` is left blank there (splice QA fix). The E-basis level, 389 against an E EBIT (adj.) of 405, sitting next to the D EBIT of 480 would imply a spurious -91m of other income and expenses. The value is quoted in `kpi_source`.
  - The contribution ratio, (revenue − variable costs) / revenue, is a gross-margin proxy useful for input-cost analysis.

## 6. Flags and event notes

- `india_included`: true for 2007Q2-2007Q4 (MTR inside A's Orkla Foods International) and 2014Q4-2022Q2 (D). India grew fast, at +13-20% organic in 2013-14, and added Eastern in 2021Q2, so organic growth and margins in those quarters partly reflect Indian conditions. `D_DERIVED` in the alternative file allows an India-inclusive check after 2022Q2.
- `covid`: true for 2020Q1-2021Q4. Q1 2020 stockpiling gave +10.8% organic, and the Q1 2021 comparison was -4.7%.
- `ifrs16_transition`: true for 2019Q1-2019Q4.
- `event_note`: definition breaks, acquisitions and divestments (with approximate annual revenue), distribution agreements, and internal transfers. `drivers_note` is the management commentary paraphrased in the current-vintage row.

## 7. Chain-linked indices

`rev_chain_idx` and `ebit_chain_idx` are chained quarter by quarter: each quarter is linked to the same quarter one year earlier using the same-definition growth rates:
- forward: idx(t) = idx(t−4) × X(t) / X_py_samedef(t)
- backward: idx(t−4) = idx(t) × X_py_samedef(t) / X(t)

Each 2015 quarter starts at 100 × X(2015Qk) / mean(X 2015). The 2015 average is therefore 100 and the seasonal pattern is kept.

Within a definition, the index is proportional to the reported level. Across breaks, it moves only by the same-definition growth, so it contains **no definition jumps**. It still **includes M&A and FX**, e.g. Rieber 2013-14, Hamé 2016-17, Eastern 2021-22 and Bakers out 2012. The EBIT index spans metric changes using growth rates on a consistent metric each year. It is volatile in low-profit Q1s.

## 8. Alternative definitions file

The columns are `period, def_id, segment_label` (as printed), `revenue_nokm, ebit_nokm, ebit_margin_pct, organic_growth_pct, source, ebit_metric, derived, def_desc, notes`. A (period, def_id) pair can appear twice when two profit metrics exist, e.g. D 2014Q1-Q3 as EBITA (Jan-2015 restatement) and as EBIT (adj.) (2015 comparatives).

| def | Periods | Source |
|---|---|---|
| A (other metric) | 2001Q1-Q4 NGAAP EBITA; 2004Q1-Q4 IFRS | 2002 and 2005 report comparatives; Feb-2006 xls |
| A_NORDIC, A_OFI, A_INTL | 2004Q1-2007Q4 (organic growth for Nordic 2006Q1-2007Q4) | Feb-2006 xls; Q4-2007 xls; 2005-07 reports |
| A_ELIM | 2004Q1-2007Q4 (2004Q4 and 2005Q4 printed, others derived residual) | derived |
| B | 2007Q1-Q4 (restated to the 2008 definition) | Q1-2008 xls; 2008 report comparatives |
| C | 2011Q1-2012Q4 (incl. IAS 19R) | Apr-2013 restatement pdf; 2013 report comparatives |
| D | 2013Q1-2014Q3 EBITA; 2014Q1-Q4 EBIT (adj.) | Jan-2015 restatement pdf; Q4 2014 and 2015 report comparatives |
| E | 2021Q3-2022Q2 | Q3 2022 to Q2 2023 report comparatives |
| IND | 2021Q3-2026Q2 | 2022-2026 reports |
| D_DERIVED | 2022Q3-2026Q2 = E + India | derived. Eliminations are negligible: Q1 2022 4,239 + 550 = 4,789 vs 4,788 printed. Organic growth is the prior-year-revenue-weighted mean of E and India (an approximation). |

Not available: E for single quarters 2021Q1 and 2021Q2. Only H1 2021 is known (8,001/928), derived as 9M − Q3. Also unavailable: C for 2014Q4 and later, D for quarters before 2013 (only FY2012 = 8,681/1,145), and organic growth for C 2011-12 and D 2013-14 quarters.

## 9. Annual file

- 1992-1999 (`PRE`): Orkla Foods business area, NGAAP operating profit after goodwill amortisation. Before-goodwill figures from 1995 are in `ebit_alt_nokm`. There is a large M&A break in 1995-96, when Procordia/Abba roughly doubled revenue.
- 2000-2025: the headline row (`is_headline`) is the definition in force at year-end, with the metric as reported that year. Four quarters always sum to the printed full year (section 10).
  - **2014**: the headline annual figure is D (12,232/1,495 EBITA), but headline *quarters* 2014Q1-Q3 are C. C has only 9M 2014 (7,707/971).
  - **2022**: the headline annual figure is E (17,820/1,973), but headline quarters 2022Q1-Q2 are D. D for 2022 is in `D_DERIVED` (20,362/2,276).
- Same-definition annual y/y comes from the sums of the same-report comparatives, or from the prior-year restated annual figure for 2014 (D 2013) and 2022 (E 2021). `ebit_alt_nokm` gives the next year's restated basis where it differs: 2001 EBITA 952, 2004 IFRS 1,164, 2014 EBIT (adj.) 1,488.
- Organic growth: the reported full-year figure where available (2001-2022, sources in `og_source`). The B 2008-11 values are read from a bar chart and are approximate. Otherwise it is computed as quarterly `og_est` weighted by prior-year same-definition revenue (E 2023-2025, India, D_DERIVED).
  - Two printed full-year figures differ noticeably from their revenue-weighted quarters (splice QA; see `notes`): B 2008, bar chart 4 vs quarters 4.7; C 2013, printed -4.2 vs quarters -3.5.
  - All other reported full-year values agree with the weighted quarters within whole-percent rounding (at most 0.5pp, e.g. A 2003 and 2006).
  - 2014 and 2022 are not comparable this way, because their headline quarters mix definitions. On the E basis, the 2022 quarters (H1 8.8, Q3 4.2, Q4 7.2) give 7.19 against the printed 7.2.

The adversarial verification of this dataset (traces to raw rows, checks and fixes) is in `orkla_foods_splice_qa.md`.

## 10. Checks (printed by the build script)

- Every quarter 2000Q1 to 2026Q2 is present (106 rows).
- `d_margin_yoy_pp` is available for every quarter from 2001Q1 (102 of 106). All 102 use same-report comparatives.
- Margins equal EBIT/revenue. Printed margins agree within 0.05pp, except 2025Q4 (0.054pp, print rounding).
- **Four quarters equal the printed full year** for all 38 definition/year/metric sets checked: A 2000-2007 (incl. 2001 EBITA and 2004 IFRS), A_NORDIC 2006-07, B 2007-2012, C 2012-13, D 2013-2021 (2014 both metrics), E 2022-2025, and India 2022-2025.
- Organic-growth coverage: og_est for 102 of 106 quarters (A 67, B 23, C 12, missing 4). d_og: 98 quarters (A 52, B 28, C 18), of which 12 cross a definition break.
- Price/volume available for all 17 quarters from 2022Q2.

## 11. Caveats for the macro analysis

1. **Definition mix over time.**
   - The geographic exposure shifts: A includes CEE/Russia and B2B ingredients; B/C are almost purely Nordic and Baltic; D adds India and CZ/SK; E is Nordic plus about 23% Central Europe.
   - Macro weights should follow `def_id` (see `orkla_raw/geo_weights.csv`).
   - India sits inside the headline in 2007Q2-Q4 and 2014Q4-2022Q2.
2. **Organic growth basis changes.**
   - Calendar-adjusted quarters: 2010Q1, 2011Q1-Q2 and 2014.
   - Rieber pro forma: 2013Q2 (stated). The 2013Q3-Q4 basis is not stated.
   - Distribution agreements counted as organic in 2015-16, and as structure from 2021.
   - The early-2000s "continuing business" figures are rounded to whole percent.
   - Use `og_quality` and `d_og_quality` as weights or filters. A robustness sample of A only, or A and B, from 2015 is cleanest.
3. **Bakers (2012).** Same-definition revenue growth in 2012 is distorted by the divestment (−6 to −14%), and the 2012 margin rise partly reflects losing a low-margin bakery business. Organic growth is unaffected. The C restatement of 2012 still contains January 2012 Bakers.
4. **Large acquisitions inside same-definition growth.** Rieber (2013Q2-2014Q1), Hamé (2016Q2-2017Q1), Eastern (2021Q2-2022Q1), SladCo (2005) and Krupskaya (2006Q3-2007Q2) dilute or lift margins. `d_margin_yoy_pp` includes these mix effects. In 2013 Rieber cut the margin by about 1.8pp of a 2.5pp decline (Q2 2013 presentation).
5. **Metric levels.**
   - EBIT levels jump in 2002 (goodwill), 2005 (IFRS) and 2015 (EBITA to EBIT (adj.), small). Y/y measures are unaffected because they use same-report comparatives.
   - IFRS 16 in 2019 is a small unrestated break.
   - IAS 19R raised C/D EBITA from 2012 onward compared with B.
6. **2001 organic growth** comes from rounded YTD figures, and Q1 is probably not FX-adjusted. The 2005Q1-Q3 values are one 9M average. Treat 2001-2005 organic growth as low-precision.
7. **Seasonality.** Q1 has the lowest margin (about 10-12%) and Q4 the highest (about 14-17%). Always compare y/y, as the dataset does, and control for Easter.
8. **Covid (2020-21)** and the **2022-23 input-cost shock** are large, well-identified episodes. The 2022-23 shock shows as margins −2 to −3pp y/y, price +10-16% and volume/mix −4 to −9%. Treat the Covid quarters as outliers or dummy them.
9. **One-offs inside EBIT (adj.)** are not removed: the Q3 2012 property gain of 11m, the Q3 2021 recall of about 20m, the Q3 2023 ketchup recall of about 25m, and Q4 2025 periodisation. See `drivers_note`.

## 12. Headline series (auto-generated)

<!-- BEGIN AUTO (build_orkla_quarterly.py) -->
| period | def | revenue | EBIT | margin % | d margin pp | OG est % | OG q | d OG pp | price % | vol/mix % | Easter shift |
|---|---|---:|---:|---:|---:|---:|:-:|---:|---:|---:|---:|
| 2000Q1 | A | 2,487 | 89 | 3.58 |  |  |  |  |  |  | +0 |
| 2000Q2 | A | 2,830 | 218 | 7.70 |  |  |  |  |  |  | +0 |
| 2000Q3 | A | 2,693 | 196 | 7.28 |  |  |  |  |  |  | +0 |
| 2000Q4 | A | 3,029 | 284 | 9.38 |  |  |  |  |  |  | +0 |
| 2001Q1 | A | 2,706 | 128 | 4.73 | 1.15 | 5.0 | B |  |  |  | +0 |
| 2001Q2 | A | 2,691 | 175 | 6.50 | -1.20 | -1.4 | C |  |  |  | +0 |
| 2001Q3 | A | 2,682 | 204 | 7.61 | 0.33 | 2.5 | C |  |  |  | +0 |
| 2001Q4 | A | 3,054 | 284 | 9.30 | -0.08 | 4.1 | C |  |  |  | +0 |
| 2002Q1 | A | 2,688 | 167 | 6.21 | -0.03 | 4.0 | B | -1.0 |  |  | +1 |
| 2002Q2 | A | 2,641 | 185 | 7.00 | -0.98 | 1.0 | B | 2.4 |  |  | -1 |
| 2002Q3 | A | 2,692 | 239 | 8.88 | -0.22 | 1.0 | C | -1.5 |  |  | +0 |
| 2002Q4 | A | 3,041 | 311 | 10.23 | -0.38 | 2.0 | A | -2.1 |  |  | +0 |
| 2003Q1 | A | 2,663 | 144 | 5.41 | -0.81 | -3.0 | A | -7.0 |  |  | -1 |
| 2003Q2 | A | 2,898 | 241 | 8.32 | 1.31 | 3.0 | A | 2.0 |  |  | +1 |
| 2003Q3 | A | 2,973 | 286 | 9.62 | 0.74 | 1.0 | A | 0.0 |  |  | +0 |
| 2003Q4 | A | 3,379 | 359 | 10.62 | 0.40 | 1.0 | A | -1.0 |  |  | +0 |
| 2004Q1 | A | 3,112 | 205 | 6.59 | 1.18 | 4.0 | A | 7.0 |  |  | +0 |
| 2004Q2 | A | 3,006 | 241 | 8.02 | -0.30 | -1.8 | C | -4.8 |  |  | +0 |
| 2004Q3 | A | 3,112 | 320 | 10.28 | 0.66 | -1.9 | C | -2.9 |  |  | +0 |
| 2004Q4 | A | 3,481 | 412 | 11.84 | 1.21 | -1.0 | A | -2.0 |  |  | +0 |
| 2005Q1 | A | 3,154 | 181 | 5.74 | -0.69 | -2.4 | C | -6.4 |  |  | +1 |
| 2005Q2 | A | 3,310 | 280 | 8.46 | -0.12 | -2.4 | C | -0.6 |  |  | -1 |
| 2005Q3 | A | 3,324 | 319 | 9.60 | -0.36 | -2.4 | C | -0.5 |  |  | +0 |
| 2005Q4 | A | 3,862 | 433 | 11.21 | -0.16 | -1.0 | A | 0.0 |  |  | +0 |
| 2006Q1 | A | 3,199 | 174 | 5.44 | -0.30 | 0.0 | B | 2.4 |  |  | -1 |
| 2006Q2 | A | 3,360 | 304 | 9.05 | 0.59 | 1.0 | A | 3.4 |  |  | +1 |
| 2006Q3 | A | 3,506 | 341 | 9.73 | 0.13 | 1.0 | A | 3.4 |  |  | +0 |
| 2006Q4 | A | 4,201 | 459 | 10.93 | -0.29 | 0.0 | B | 1.0 |  |  | +0 |
| 2007Q1 | A | 3,325 | 159 | 4.78 | -0.66 | -2.0 | A | -2.0 |  |  | +0 |
| 2007Q2 | A | 3,618 | 208 | 5.75 | -3.30 | -2.0 | A | -3.0 |  |  | +0 |
| 2007Q3 | A | 3,553 | 245 | 6.90 | -2.83 | -1.7 | A | -2.7 |  |  | +0 |
| 2007Q4 | A | 4,229 | 388 | 9.17 | -1.75 | 0.6 | A | 0.6 |  |  | +0 |
| 2008Q1 | B | 2,293 | 160 | 6.98 | 0.09 | 6.0 | B | 6.0 |  |  | +1 |
| 2008Q2 | B | 2,436 | 262 | 10.76 | 1.71 | 4.0 | C | 5.0 |  |  | -1 |
| 2008Q3 | B | 2,392 | 287 | 12.00 | 1.82 | 5.0 | B | 6.6 |  |  | +0 |
| 2008Q4 | B | 2,792 | 341 | 12.21 | 1.22 | 4.0 | B | 4.5 |  |  | +0 |
| 2009Q1 | B | 2,283 | 171 | 7.49 | 0.51 | -2.0 | B | -8.0 |  |  | -1 |
| 2009Q2 | B | 2,436 | 279 | 11.45 | 0.70 | 0.0 | B | -4.0 |  |  | +1 |
| 2009Q3 | B | 2,377 | 297 | 12.49 | 0.50 | -2.0 | B | -7.0 |  |  | +0 |
| 2009Q4 | B | 2,658 | 341 | 12.83 | 0.62 | -0.5 | A | -4.5 |  |  | +0 |
| 2010Q1 | B | 2,190 | 194 | 8.86 | 1.37 | -3.3 | B | -1.3 |  |  | +0 |
| 2010Q2 | B | 2,262 | 278 | 12.29 | 0.84 | -6.0 | A | -6.0 |  |  | +0 |
| 2010Q3 | B | 2,267 | 290 | 12.79 | 0.30 | -4.0 | A | -2.0 |  |  | +0 |
| 2010Q4 | B | 2,719 | 353 | 12.98 | 0.15 | -3.0 | A | -2.5 |  |  | +0 |
| 2011Q1 | B | 2,213 | 186 | 8.40 | -0.45 | -1.0 | B | 2.3 |  |  | +0 |
| 2011Q2 | B | 2,391 | 277 | 11.59 | -0.70 | 0.2 | B | 6.2 |  |  | +0 |
| 2011Q3 | B | 2,242 | 262 | 11.69 | -1.11 | -1.0 | A | 3.0 |  |  | +0 |
| 2011Q4 | B | 2,650 | 357 | 13.47 | 0.49 | -1.0 | A | 2.0 |  |  | +0 |
| 2012Q1 | B | 2,026 | 197 | 9.72 | 1.32 | 5.0 | B | 6.0 |  |  | +0 |
| 2012Q2 | B | 2,063 | 259 | 12.55 | 0.97 | -3.1 | C | -3.3 |  |  | +0 |
| 2012Q3 | B | 2,102 | 313 | 14.89 | 3.21 | 4.0 | A | 5.0 |  |  | +0 |
| 2012Q4 | B | 2,378 | 392 | 16.48 | 3.01 | -1.2 | C | -0.2 |  |  | +0 |
| 2013Q1 | C | 1,924 | 226 | 11.75 | 1.10 | 0.0 | B | -5.0 |  |  | +1 |
| 2013Q2 | C | 2,382 | 263 | 11.04 | -2.48 | -4.2 | B | -1.1 |  |  | -1 |
| 2013Q3 | C | 2,597 | 364 | 14.02 | -1.80 | -3.5 | B | -7.5 |  |  | +0 |
| 2013Q4 | C | 2,894 | 422 | 14.58 | -2.43 | -6.0 | B | -4.8 |  |  | +0 |
| 2014Q1 | C | 2,548 | 295 | 11.58 | -0.17 | -2.7 | B | -2.7 |  |  | -1 |
| 2014Q2 | C | 2,633 | 333 | 12.65 | 1.61 | -4.6 | B | -0.4 |  |  | +1 |
| 2014Q3 | C | 2,526 | 343 | 13.58 | -0.44 | -3.4 | B | 0.1 |  |  | +0 |
| 2014Q4 | D | 3,371 | 470 | 13.94 | 0.81 | 2.2 | B | 8.2 |  |  | +0 |
| 2015Q1 | D | 3,045 | 322 | 10.57 | -0.01 | 4.1 | A | 6.8 |  |  | +0 |
| 2015Q2 | D | 3,122 | 389 | 12.46 | 0.75 | 1.9 | A | 6.5 |  |  | +0 |
| 2015Q3 | D | 3,261 | 429 | 13.16 | 0.84 | 4.2 | A | 7.6 |  |  | +0 |
| 2015Q4 | D | 3,822 | 561 | 14.68 | 0.85 | 5.2 | A | 3.0 |  |  | +0 |
| 2016Q1 | D | 3,418 | 377 | 11.03 | 0.46 | 3.3 | A | -0.8 |  |  | +1 |
| 2016Q2 | D | 3,967 | 463 | 11.67 | -0.79 | 3.9 | A | 2.0 |  |  | -1 |
| 2016Q3 | D | 3,905 | 512 | 13.11 | -0.04 | 3.3 | A | -0.9 |  |  | +0 |
| 2016Q4 | D | 4,186 | 616 | 14.72 | 0.04 | -0.6 | A | -5.8 |  |  | +0 |
| 2017Q1 | D | 3,758 | 392 | 10.43 | -0.60 | 1.1 | A | -2.2 |  |  | -1 |
| 2017Q2 | D | 3,977 | 434 | 10.91 | -0.76 | 0.4 | A | -3.5 |  |  | +1 |
| 2017Q3 | D | 4,007 | 540 | 13.48 | 0.36 | 2.9 | A | -0.4 |  |  | +0 |
| 2017Q4 | D | 4,384 | 689 | 15.72 | 1.00 | 1.3 | A | 1.9 |  |  | +0 |
| 2018Q1 | D | 3,852 | 400 | 10.38 | -0.05 | 1.6 | A | 0.5 |  |  | +0 |
| 2018Q2 | D | 3,845 | 439 | 11.42 | 0.51 | 0.4 | A | 0.0 |  |  | +0 |
| 2018Q3 | D | 3,937 | 558 | 14.17 | 0.70 | 1.1 | A | -1.8 |  |  | +0 |
| 2018Q4 | D | 4,366 | 651 | 14.91 | -0.81 | 2.7 | A | 1.4 |  |  | +0 |
| 2019Q1 | D | 3,889 | 430 | 11.06 | 0.67 | 1.7 | A | 0.1 |  |  | +0 |
| 2019Q2 | D | 4,070 | 496 | 12.19 | 0.77 | 3.1 | A | 2.7 |  |  | +0 |
| 2019Q3 | D | 4,145 | 616 | 14.86 | 0.69 | 0.8 | A | -0.3 |  |  | +0 |
| 2019Q4 | D | 4,672 | 734 | 15.71 | 0.80 | 1.5 | A | -1.2 |  |  | +0 |
| 2020Q1 | D | 4,618 | 535 | 11.59 | 0.53 | 10.8 | A | 9.1 |  |  | +0 |
| 2020Q2 | D | 4,338 | 606 | 13.97 | 1.78 | -0.7 | A | -3.8 |  |  | +0 |
| 2020Q3 | D | 4,474 | 683 | 15.27 | 0.41 | 3.7 | A | 2.9 |  |  | +0 |
| 2020Q4 | D | 4,871 | 817 | 16.77 | 1.06 | 1.7 | A | 0.2 |  |  | +0 |
| 2021Q1 | D | 4,299 | 507 | 11.79 | 0.21 | -4.7 | A | -15.5 |  |  | +0 |
| 2021Q2 | D | 4,465 | 517 | 11.58 | -2.39 | 3.0 | A | 3.7 |  |  | +0 |
| 2021Q3 | D | 4,857 | 718 | 14.78 | -0.48 | 4.7 | A | 1.0 |  |  | +0 |
| 2021Q4 | D | 5,139 | 729 | 14.19 | -2.59 | 4.1 | A | 2.4 |  |  | +0 |
| 2022Q1 | D | 4,788 | 531 | 11.09 | -0.70 | 7.2 | A | 11.9 |  |  | +0 |
| 2022Q2 | D | 4,957 | 480 | 9.68 | -1.90 | 11.6 | A | 8.6 | 7.4 | 3.0 | +0 |
| 2022Q3 | E | 4,340 | 526 | 12.12 | -3.00 | 4.2 | A | -0.5 | 13.6 | -9.4 | +0 |
| 2022Q4 | E | 4,923 | 573 | 11.64 | -2.84 | 7.2 | A | 3.3 | 13.9 | -6.7 | +0 |
| 2023Q1 | E | 4,903 | 510 | 10.40 | -0.66 | 10.3 | A | 3.0 | 15.2 | -4.9 | +0 |
| 2023Q2 | E | 5,087 | 534 | 10.50 | 1.12 | 7.0 | A | -3.4 | 16.3 | -9.3 | +0 |
| 2023Q3 | E | 4,825 | 580 | 12.02 | -0.10 | 4.4 | A | 0.2 | 9.9 | -5.4 | +0 |
| 2023Q4 | E | 5,504 | 635 | 11.54 | -0.10 | 5.1 | A | -2.1 | 8.8 | -3.8 | +0 |
| 2024Q1 | E | 5,100 | 564 | 11.06 | 0.66 | 3.2 | A | -7.1 | 5.5 | -2.3 | +1 |
| 2024Q2 | E | 4,963 | 612 | 12.33 | 1.83 | 0.7 | A | -6.3 | 2.3 | -1.6 | -1 |
| 2024Q3 | E | 5,026 | 675 | 13.43 | 1.41 | 2.7 | A | -1.7 | 1.4 | 1.3 | +0 |
| 2024Q4 | E | 5,505 | 681 | 12.37 | 0.83 | 1.1 | A | -4.0 | 0.9 | 0.2 | +0 |
| 2025Q1 | E | 4,995 | 589 | 11.79 | 0.73 | -2.9 | A | -6.1 | 0.9 | -3.8 | -1 |
| 2025Q2 | E | 5,107 | 614 | 12.02 | -0.31 | 1.0 | A | 0.3 | 1.0 | 0.0 | +1 |
| 2025Q3 | E | 5,129 | 700 | 13.65 | 0.22 | 0.8 | A | -1.9 | 1.6 | -0.8 | +0 |
| 2025Q4 | E | 5,633 | 718 | 12.75 | 0.38 | 0.4 | A | -0.7 | 0.2 | 0.2 | +0 |
| 2026Q1 | E | 5,146 | 614 | 11.93 | 0.14 | 3.5 | A | 6.4 | 1.2 | 2.3 | +0 |
| 2026Q2 | E | 4,799 | 606 | 12.63 | 0.60 | -1.3 | A | -2.3 | 1.0 | -2.3 | +0 |

**Annual headline series** (year-end definition):

| year | def | revenue | EBIT | metric | margin % | organic % | rev growth (same def) % | d margin pp |
|---|---|---:|---:|---|---:|---:|---:|---:|
| 1992 | PRE | 4,114 | 334 | NGAAP operating profit after goodwill amortisation | 8.12 |  |  |  |
| 1993 | PRE | 4,527 | 359 | NGAAP operating profit after goodwill amortisation | 7.93 |  | 10.0 | -0.19 |
| 1994 | PRE | 5,286 | 362 | NGAAP operating profit after goodwill amortisation | 6.85 |  | 16.8 | -1.08 |
| 1995 | PRE | 7,003 | 368 | NGAAP operating profit after goodwill amortisation | 5.25 |  | 32.5 | -1.59 |
| 1996 | PRE | 10,527 | 608 | NGAAP operating profit after goodwill amortisation | 5.78 |  | 50.3 | 0.52 |
| 1997 | PRE | 10,094 | 655 | NGAAP operating profit after goodwill amortisation | 6.49 |  | -4.1 | 0.71 |
| 1998 | PRE | 10,238 | 579 | NGAAP operating profit after goodwill amortisation | 5.66 |  | 1.4 | -0.83 |
| 1999 | PRE | 10,757 | 709 | NGAAP operating profit after goodwill amortisation | 6.59 |  | 5.1 | 0.94 |
| 2000 | A | 11,039 | 787 | NGAAP operating profit after goodwill amortisation | 7.13 |  | 2.6 | 0.54 |
| 2001 | A | 11,133 | 791 | NGAAP operating profit after goodwill amortisation | 7.11 | 2.5 | 0.8 | -0.02 |
| 2002 | A | 11,062 | 902 | NGAAP EBITA (before goodwill amortisation) | 8.15 | 2.0 | -0.6 | -0.40 |
| 2003 | A | 11,913 | 1,030 | NGAAP EBITA (before goodwill amortisation) | 8.65 | 1.0 | 7.7 | 0.49 |
| 2004 | A | 12,711 | 1,178 | NGAAP EBITA (before goodwill amortisation) | 9.27 | 0.0 | 6.7 | 0.62 |
| 2005 | A | 13,650 | 1,213 | EBITA (IFRS) | 8.89 | -2.0 | 7.4 | -0.27 |
| 2006 | A | 14,266 | 1,278 | EBITA (IFRS) | 8.96 | 0.0 | 4.5 | 0.07 |
| 2007 | A | 14,725 | 1,000 | EBITA (IFRS) | 6.79 | -1.1 | 3.2 | -2.17 |
| 2008 | B | 9,913 | 1,050 | EBITA (IFRS) | 10.59 | 4.0 | 3.8 | 1.24 |
| 2009 | B | 9,754 | 1,088 | EBITA (IFRS) | 11.15 | -1.0 | -1.6 | 0.56 |
| 2010 | B | 9,438 | 1,115 | EBITA (IFRS) | 11.81 | -4.0 | -3.2 | 0.66 |
| 2011 | B | 9,496 | 1,082 | EBITA (IFRS) | 11.39 | -1.0 | 0.6 | -0.42 |
| 2012 | B | 8,569 | 1,161 | EBITA (IFRS) | 13.55 | 1.0 | -9.8 | 2.15 |
| 2013 | C | 9,797 | 1,275 | EBITA (IFRS) | 13.01 | -4.2 | 22.9 | -1.34 |
| 2014 | D | 12,232 | 1,495 | EBITA (IFRS) | 12.22 | -1.1 | 10.1 | 0.41 |
| 2015 | D | 13,250 | 1,701 | EBIT (adj.) | 12.84 | 3.9 | 8.3 | 0.67 |
| 2016 | D | 15,476 | 1,968 | EBIT (adj.) | 12.72 | 2.3 | 16.8 | -0.12 |
| 2017 | D | 16,126 | 2,055 | EBIT (adj.) | 12.74 | 1.4 | 4.2 | 0.03 |
| 2018 | D | 16,000 | 2,048 | EBIT (adj.) | 12.80 | 1.5 | -0.8 | 0.06 |
| 2019 | D | 16,776 | 2,276 | EBIT (adj.) | 13.57 | 1.8 | 4.8 | 0.77 |
| 2020 | D | 18,301 | 2,641 | EBIT (adj.) | 14.43 | 3.7 | 9.1 | 0.86 |
| 2021 | D | 18,760 | 2,471 | EBIT (adj.) | 13.17 | 1.8 | 2.5 | -1.26 |
| 2022 | E | 17,820 | 1,973 | EBIT (adj.) | 11.07 | 7.2 | 5.5 | -2.21 |
| 2023 | E | 20,319 | 2,259 | EBIT (adj.) | 11.12 | 6.6 | 14.0 | 0.05 |
| 2024 | E | 20,594 | 2,532 | EBIT (adj.) | 12.29 | 1.9 | 1.4 | 1.18 |
| 2025 | E | 20,864 | 2,621 | EBIT (adj.) | 12.56 | -0.2 | 1.3 | 0.27 |

**Quarters where organic growth is missing, derived or estimated (quality C or blank):**

- 2000Q1: og_est = blank (missing). no quarterly organic growth available (2000 quarters exist only as 2001 comparatives)
- 2000Q2: og_est = blank (missing). no quarterly organic growth available (2000 quarters exist only as 2001 comparatives)
- 2000Q3: og_est = blank (missing). no quarterly organic growth available (2000 quarters exist only as 2001 comparatives)
- 2000Q4: og_est = blank (missing). no quarterly organic growth available (2000 quarters exist only as 2001 comparatives)
- 2001Q2: og_est = -1.4 (quality C). Derived from H1 +1.6 (FX-adj.) minus Q1 +5 (probably not FX-adj.); basis-consistent estimate ~-3.4 (range -4.5 to -1.4); treat -1.4 as an upper bound (verify-E1 D4).
- 2001Q3: og_est = 2.5 (quality C). Derived from 9M 'just under 2%' (1.9) and H1 1.6; range +2.2 to +2.6 (verify-E1 D5).
- 2001Q4: og_est = 4.1 (quality C). Derived from FY 'approximately 2.5%' and 9M ~1.9; range +3.4 to +5.1 (verify-E1 D5).
- 2002Q3: og_est = 1.0 (quality C). Derived from 9M 2% minus Q1 ~4% and Q2 ~1%; +/-0.5pp on 9M moves Q3 +/-1.5pp (verify-E1 D5).
- 2004Q2: og_est = -1.8 (quality C). Derived from H1 1% minus Q1 4%; range -2.7 to -0.8 (verify-E1 D5).
- 2004Q3: og_est = -1.9 (quality C). Derived from 9M 'on a par' minus H1 1%; range -4.2 to +0.5 (verify-E1 D5).
- 2005Q1: og_est = -2.4 (quality C). 9M-2005 AVERAGE (-2.4) implied by FY -2% and Q4 -1% (Q4 2005 report p.3); same value in Q1-Q3; range -3.3 to -1.5; Q1 text 'slightly lower' (verify-E1 D3).
- 2005Q2: og_est = -2.4 (quality C). 9M-2005 AVERAGE implied by FY -2% and Q4 -1%; quarterly split unknown (verify-E1 D3).
- 2005Q3: og_est = -2.4 (quality C). 9M-2005 AVERAGE implied by FY -2% and Q4 -1%; quarterly split unknown (verify-E1 D3).
- 2008Q2: og_est = 4.0 (quality C). Derived from H1 5% and Q1 ~6% with 2007 restated weights: (5 x 4,629 - 6 x 2,207) / 2,422 = 4.09; the verified extraction keeps the rounded 'about 4'; range 2.7 to 5.5 (verify-E2 #2).
- 2012Q2: og_est = -3.1 (quality C). ESTIMATE: (H1 0.8 x H1-11 rev - Q1 5.0 x Q1-11 rev) / Q2-11 rev = -3.09; H1 +0.8 from Q2 2012 pres p.11 (report +1%), Q1 'about 5%' (Q1 2012 report p.5); weights = 2011 revenue as printed (incl. Bakers; ex-Bakers weights give ~-3.0); Q1 read as 4.5-5.5 gives -2.6 to -3.6; Q1+Q2 together (H1) are well determined
- 2012Q4: og_est = -1.2 (quality C). ESTIMATE: FY2012 +1% (Q4 2012 pres p.23) less Q1 5.0, Q2 est. -3.1, Q3 4.0, weighted by 2011 revenue = -1.19 (equivalently FY less H1 0.8 and Q3; the Q1 split cancels); consistent with report text 'small underlying decline' (fewer selling days); FY read as 0.5-1.5 gives -3.0 to +0.6
<!-- END AUTO -->
