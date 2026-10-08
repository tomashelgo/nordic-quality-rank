# Era E5 (2018Q1-2021Q4) verification log (label: verify-E5)

The input was `era_E5.csv` (64 rows) plus `era_E5_notes.md`. The output is `era_E5_verified.csv`: the same 64 rows and the same columns, plus `verify_status` and `verify_note`.

**Result: 0 value discrepancies. 61 rows are confirmed and 3 rows are `added`.** The 3 `added` rows are current rows where empty FX/structure cells were filled. No row is `corrected` or `unverifiable`.

Status definitions used here:
- **confirmed:** every populated value was re-extracted independently and matches.
- **added:** all existing values are confirmed, and the verifier filled previously empty fields.
- **corrected:** an existing value was changed. No row needed this.

## 1. Sources (downloaded independently)

- **Location:** `scratchpad/dl/verify-E5/`, with text extracts in `scratchpad/scripts/verify-E5/txt/`.
- **E5 reports:** English quarterly reports Q1 2018 to Q4 2021 (16 files) and the matching investor presentations (16). The URLs are identical to the `report_url` values in the CSV, which were checked programmatically.
- **Cross-check documents:**
  - Original 2017 quarterly reports Q1-Q4.
  - Q1, Q2 and Q3 2022 reports.
  - Orkla's "restated segment financials 2018-2019" workbook (6 Feb 2020), from https://www.orkla.com/files/Public/19690/3176571/orkla--restated-segment-financials-2018-2019.docx. The file is really an xlsx.

## 2. Independent re-extraction, done before reading the CSV values

All figures are for Orkla Foods, current vintage. Amounts are NOK million and percentages are %.

| Q | Revenue | EBIT (adj.) | Margin (printed) | Organic | FX | Structure | Business-area table p. | Note 2 p. | APM p. |
|---|---|---|---|---|---|---|---|---|---|
| 2018Q1 | 3 852 | 400 | 10.4 | 1.6 | n.p. | n.p. | 6 | 12 | - |
| 2018Q2 | 3 845 | 439 | 11.4 | 0.4 | n.p. | n.p. | 6 | 12 | - |
| 2018Q3 | 3 937 | 558 | 14.2 | 1.1 | n.p. | n.p. | 6 | 12 | - |
| 2018Q4 | 4 366 | 651 | 14.9 | 2.7 | -2.0 | -1.1 | 6 | 12 | 17 |
| 2019Q1 | 3 889 | 430 | 11.1 | 1.7 | -0.7 | 0.0 | 7 | 13 | 17 |
| 2019Q2 | 4 070 | 496 | 12.2 | 3.1 | 0.5 | 2.3 | 7 | 14 | 18 |
| 2019Q3 | 4 145 | 616 | 14.9 | 0.8 | 1.6 | 2.8 | 7 | 13 | 18 |
| 2019Q4 | 4 672 | 734 | 15.7 | 1.5 | 2.9 | 2.6 | 7 | 14 | 19 |
| 2020Q1 | 4 618 | 535 | 11.6 | 10.8 | 5.7 | 2.3 | 7 | 14 | 18 |
| 2020Q2 | 4 338 | 606 | 14.0 | -0.7 | 8.1 | -0.9 | 7 | 14 | 18 |
| 2020Q3 | 4 474 | 683 | 15.3 | 3.7 | 5.5 | -1.2 | 7 | 14 | 19 |
| 2020Q4 | 4 871 | 817 | 16.8 | 1.7 | 4.2 | -1.6 | 7 | 14 | 19 |
| 2021Q1 | 4 299 | 507 | 11.8 | -4.7 | -1.3 | -0.9 | 7 | 14 | 18 |
| 2021Q2 | 4 465 | 517 | 11.6 | 3.0 | -5.9 | 5.9 | 8 | 15 | 20 |
| 2021Q3 | 4 857 | 718 | 14.8 | 4.7 | -1.8 | 5.8 | 7 | 14 | 19 |
| 2021Q4 | 5 139 | 729 | 14.2 | 4.1 | -4.6 | 6.0 | 7 | 14 | 19 |

"n.p." means not printed for Orkla Foods in that report. The Q1-Q3 2018 reports print only the BCG-level split, on p.3.

How the APM column order was resolved:
- The order was read from the header text: FX | Structure | Organic | Total in the Q4 2018 to Q3 2019 reports, and Organic | FX | Structure | Total from the Q4 2019 report onwards (Q4 2018 p.17; Q4 2019 p.19; Q2 2021 p.20).
- In every report the organic figure in the APM table equals the "Organic revenue growth" row of the business-area table, which pins down which column is which.

I also re-extracted the Branded Consumer Goods context rows (Note 2 BCG total excl. HQ, plus the BCG organic/FX/structure figures) for all 16 current and 16 comparative rows.

## 3. Field-by-field comparison with era_E5.csv

- **Scope:** all 64 rows, comparing period label, revenue, EBIT, printed or computed margin, organic growth, FX and structure.
- **Result:** 0 mismatches.
- **Other columns:** `page_ref` page numbers for the business-area table, Note 2, APM table and presentation slide all match the pages I located for each of the 16 reports. Every row has `report_url`, `ebit_metric` = "EBIT (adj.)" and `derived_from_ytd` = false.
- **No YTD derivation:** every report, including the Q4 reports, prints a stand-alone quarterly column, so there are no `derived_from_ytd=true` rows to check.

## 4. Comparative rows (all 32 checked, more than the 6 required)

### Orkla Foods 2018-2020 comparatives (12 rows)
- Every one equals the corresponding current-vintage value: revenue, EBIT, margin, organic, FX and structure.
- No restatement of Orkla Foods occurred.
- The Feb-2020 restated segment workbook shows Orkla Foods 2018-2019 revenue/EBIT, and 2019 quarterly organic growth (1.7 / 3.1 / 0.8 / 1.5), identical to the reports.
- The Q1 2022 report repeats Q1 2021 as 4 299 / 507. The Q2 2022 report repeats 1H 2021 as 8 764 / 1 024.

### Orkla Foods 2017 comparatives (4 rows)
These match the original 2017 reports:

| Quarter | Revenue / EBIT | Margin | Source in the original report |
|---|---|---|---|
| Q1 2017 | 3 758 / 392 | 10.4 | Q1 2017 report Note p.13 and table p.6 |
| Q2 2017 | 3 977 / 434 | 10.9 | Q2 2017 report Note p.14 and table p.6 |
| Q3 2017 | 4 007 / 540 | 13.5 | Q3 2017 report Note p.12 and table p.5 |
| Q4 2017 | 4 384 / 689 | 15.7; organic 1.3 | Q4 2017 report Note p.12 and table p.6 |

- The extractor said the original 2017 reports were "not re-checked". They are now checked and match.
- The 2017Q1/Q2 comparative margins come from presentation slides: Q1 2018 presentation p.11/p.28 and Q2 2018 presentation p.26. The original reports print the same values.

### BCG comparatives
- The 2019 comparatives in the 2020 reports are restated because Orkla Consumer Investments was created in Q1 2020. They match the restated columns in the Q1-Q4 2020 Note 2 / APM tables and the Feb-2020 workbook (9 868 / 1 027; 10 337 / 1 142; 10 649 / 1 428; 11 778 / 1 551).
- The original vintages were 9 687 / 1 017, 10 051 / 1 124, 10 336 / 1 401 and 11 471 / 1 534.
- Organic growth for Q2 2019 changed from 1.1 to 1.0, and for Q4 2019 from 2.0 to 1.9.
- The extractor's documentation of this restatement is correct.
- BCG 2017 comparatives match the original 2017 Note 2 figures: 8 834 / 921, 9 505 / 1 016, 9 584 / 1 267 and 10 587 / 1 439.

## 5. Arithmetic and consistency checks

- **Margins:** every printed margin is within 0.05pp of EBIT/revenue. The computed BCG margins (`margin_computed=true`) equal EBIT/revenue to 2 decimals.
- **Quarterly sums equal the printed full year:**

  | Year | Orkla Foods revenue / EBIT | BCG revenue / EBIT |
  |---|---|---|
  | 2017 | 16 126 / 2 055 | 38 510 / 4 643 |
  | 2018 | 16 000 / 2 048 | 39 592 / 4 671 |
  | 2019 | 16 776 / 2 276 | 41 545 / 5 076 original; 42 632 / 5 148 restated |
  | 2020 | 18 301 / 2 641 | 46 521 / 5 767 |
  | 2021 | 18 760 / 2 471 | 49 204 / 5 794 |

- **Revenue-weighted quarterly organic growth reproduces the printed full-year organic growth:**

  | Year | Weighted quarters | Printed full year |
  |---|---|---|
  | 2018 | 1.48 | 1.5 |
  | 2019 | 1.76 | 1.8 |
  | 2020 | 3.72 | 3.7 |
  | 2021 | 1.77 | 1.8 |

- **Organic + FX + structure vs actual revenue growth (current vs comparative):** the sum is within 0.1pp in every quarter except Orkla Foods 2021Q3. There the components sum to 4.7 - 1.8 + 5.8 = 8.7, against actual growth of 8.56% and a printed APM total of 8.6, a gap of 0.14pp.
  - This is rounding of the three components, not an error.
  - The extractor's statement that every quarter is "within 0.1pp" is slightly overstated. No data change is needed.
- **Signs and magnitudes are plausible.** Examples:
  - 2020Q1: organic 10.8 from Covid stockpiling, with FX 5.7 from the weak NOK/SEK.
  - 2021Q1: organic -4.7 when lapping the stockpiling quarter.
  - 2021Q2-Q4: structure +5.8 to +6.0 from Eastern Condiments, consolidated from 1 Apr 2021 (Q4 2021 report p.15: purchase completed 31 Mar 2021).
  - 2018: structure -1.7 to -2.7 from the K-Salat, Pastella and Mrs. Cheng's disposals (Q4 2018 report pp.6, 17).
- **Units:** NOK million throughout ("Amounts in NOK million").
- **Labels and scope:** the segment is "Orkla Foods" in all 16 reports, and India (MTR, plus Eastern from Q2 2021) is inside it. The Q3 2022 report (p.11 and p.22) first splits out Orkla India and Orkla Foods Europe, outside this era.

### Narrative and definition claims spot-checked

All of the following were confirmed:
- About NOK 20m of recall costs in Q3 2021 (Q3 2021 report p.7).
- Frödinge moved to Orkla Food Ingredients in Q4 2020 and was handled as structure (Q4 2020 report p.4 and APM p.19).
- The Panzani distribution agreement (NOK 111m of 2019 sales) ended 1 Mar 2020 (Q1 2020 report p.16).
- Eastern 67.8% and Fort Deli (Q1 2021 report p.4).
- Stranda pizza start-up costs (Q3 2020 report p.7).
- IFRS 16 adds about NOK 20m to group operating profit, using the modified retrospective method (Q1 2019 report Note 1, p.12).
- IFRS 15 has no material effect (Q1 2018 report Note 1, p.11).
- Management split Orkla Foods into Nordics/Baltics and International from 1 Oct 2018 (Q2 2018 presentation p.5).
- Kotipizza was consolidated from 1 Feb 2019 and sat outside Orkla Foods (Q1 2019 report p.4).
- Orkla Latvija was sold in Q4 2021 (Q4 2021 report p.15).
- All `drivers_note` margin changes equal the printed margin deltas.

One small nuance: the 2018Q2 `drivers_note` paraphrases the report's first-half text, since the report has no Q2-only narrative. This is acceptable.

## 6. Fields filled

These are the 3 rows marked `added`. The FX/structure cells in the 2018Q1, 2018Q2 and 2018Q3 current Orkla Foods rows were empty because the Q1-Q3 2018 reports print the split only for BCG. The split for those quarters is printed in the next year's APM comparative tables:

| Row | FX | Structure | Source | Organic in source | Printed total |
|---|---|---|---|---|---|
| 2018Q1 current | +3.3 | -2.3 | Q1 2019 report p.17 | 1.6 | 2.5 |
| 2018Q2 current | -1.0 | -2.7 | Q2 2019 report p.18 | 0.4 | -3.3 |
| 2018Q3 current | -1.1 | -1.7 | Q3 2019 report p.18 | 1.1 | -1.8 |

- These values come from a later vintage. In each case the organic figure is identical to the current-vintage figure, so the two vintages do not conflict.
- `page_ref` and `verify_note` record where each value came from.

## 7. Fields that could not be filled

- **Organic/FX/structure for the 2017Q1-Q3 comparative rows (Orkla Foods and BCG):** these are not printed in the 2018 reports or presentations. I checked the Q1-Q3 2018 presentation key-figure slides (pp.11/28, 10/26, 8/23), and none shows prior-year organic growth.
  - The original-vintage values are Q1 2017 = 1.1 (Q1 2017 report text p.6) and Q3 2017 = 2.9 (Q3 2017 report text p.6).
  - The Q2 2017 report prints only the 1H figure (0.8). Era E4 has Q2 = 0.4 from elsewhere, which this pass did not check.
  - These cells are left empty to keep the comparative vintage faithful, because the values already sit in the E4 current rows.
- **Price/mix and volume:** there is no quantified split for Orkla Foods in any 2018-2021 report or presentation; only qualitative statements exist. These cells stay empty.

## 8. Residual concerns (not errors)

1. **IFRS 16 from 2019:** 2018 comparatives are not restated, and the effect on Orkla Foods EBIT (adj.) is not disclosed. The group effect is about +NOK 20m per year, so the Orkla Foods share is likely below about 0.1pp of margin. The y/y margin change for 2019 still carries a small definitional break.
2. **Series break around India:** the 2021 Orkla Foods figures in this era include India, and from Q2 2021 also Eastern Condiments. The Q3 2022 report restates 2021 into Orkla Foods Europe and Orkla India. Downstream series must not splice E5 "Orkla Foods" with later "Orkla Foods Europe" without adjusting.
3. **Frödinge:** it moved out of Orkla Foods in Q4 2020 without a restatement of reported revenue/EBIT; organic growth adjusts for it. Level comparisons from Q4 2020 onward lose a small Swedish business.
4. **Mixed vintage in 2018Q1-Q3 FX/structure:** the filled values come from the 2019 reports. This is noted, and the risk is small.
5. **BCG context rows:** the 2019 comparatives in the 2020 reports are on the restated basis, while the 2019 current rows are on the original basis. Do not compute BCG y/y figures across that boundary from the current rows alone.
