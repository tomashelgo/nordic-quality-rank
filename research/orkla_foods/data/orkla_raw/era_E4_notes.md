# Orkla food segment quarterly data, era E4 (2014Q1 to 2017Q4): notes

These notes go with `era_E4.csv`. The CSV has 102 rows: 16 quarterly reports x (Orkla Foods, Branded Consumer Goods, Orkla Food Ingredients, plus Orkla International in Q1-Q3 2014) x 2 vintages (current, comparative).

**Main food series:** "Orkla Foods" in every report. The definition changes once, in the Q4 2014 report (see section 2).

**Context rows**
- **Branded Consumer Goods (BCG):** the parent business area.
- **Orkla International:** Q1-Q3 2014 reports only. It holds MTR Foods (India), Vitana (CZ) and Felix Austria, which moved into Orkla Foods from Q4 2014. It also holds Orkla Brands Russia, Delecta (PL) and Chaka (RU), which did not.
- **Orkla Food Ingredients (OFI):** kept for continuity with eras E2/E3. It is not part of the food segment in this era.

**No "Orkla India" rows.** India (MTR) was never reported as its own segment in 2014-2017. See section 7.

## 1. Sources

All links are on `https://www.orkla.com/files/` and come from the manifest. Every report and presentation in range was present, so no fallback was needed. No proxy blocks occurred.

| Report | Quarterly report (`report_url`) | Presentation |
|---|---|---|
| Q1 2014 | Main/19690/3172427/1st-quarter-2014.pdf | Public/19690/3172427/presentation-of-1st-quarter-2014.pdf |
| Q2 2014 | Public/19690/3172349/2nd-quarter-2014.pdf | Main/19690/3172349/presentation-of-2nd-quarter-2014.pdf |
| Q3 2014 | Public/19690/3172265/3rd-quarter-2014.pdf | Main/19690/3172265/presentation-of-3rd-quarter-2014.pdf |
| Q4 2014 | Main/19690/3172180/4th-quarter-2014.pdf | Public/19690/3172180/presentation-of-4th-quarter-2014.pdf |
| Q1 2015 | Main/19690/3172028/1st-quarter-2015.pdf | Public/19690/3172028/presentation-of-1st-quarter-2015.pdf |
| Q2 2015 | Public/19690/3171973/2nd-quarter-2015.pdf | Main/19690/3171973/presentation-of-2nd-quarter-2015.pdf |
| Q3 2015 | Main/19690/3171907/3rd-quarter-2015.pdf | Public/19690/3171907/presentation-of-3rd-quarter-2015.pdf |
| Q4 2015 | Public/19690/3171850/4th-quarter-2015.pdf | Main/19690/3171850/presentation-of-4th-quarter-2015.pdf |
| Q1 2016 | Main/19690/3171742/1st-quarter-2016.pdf | Public/19690/3171742/presentation-of-1st-quarter-2016.pdf |
| Q2 2016 | Main/19690/3171700/2nd-quarter-2016.pdf | Public/19690/3171700/presentation-of-2nd-quarter-2016.pdf |
| Q3 2016 | Main/19690/3171641/3rd-quarter-2016.pdf | Public/19690/3171641/presentation-of-3rd-quarter-2016.pdf |
| Q4 2016 | Main/19690/3171612/4th-quarter-2016.pdf | Public/19690/3171612/presentation-of-4th-quarter-2016.pdf |
| Q1 2017 | Main/19690/3171517/1st-quarter-2017.pdf | Public/19690/3171517/presentation-of-1st-quarter-2017.pdf |
| Q2 2017 | Main/19690/3171479/2nd-quarter-2017.pdf | Public/19690/3171479/presentation-of-2nd-quarter-2017.pdf |
| Q3 2017 | Public/19690/3171417/3rd-quarter-2017.pdf | Main/19690/3171417/presentation-of-3rd-quarter-2017.pdf |
| Q4 2017 | Main/19690/3171368/4th-quarter-2017.pdf | Public/19690/3171368/presentation-of-4th-quarter-2017.pdf |

**Excel files.** The only Excel "quarterly and accounting figures" file in range is `Public/19690/3172268/quarterly-and-accounting-figures-3rd-quarter-2014.xlsx`. It holds 2013Q1 to 2014Q3 by segment, old structure, EBITA. I cross-checked all 2014Q1-Q3 and 2013 comparative values for Orkla Foods, BCG, Orkla International and OFI against it, and they are identical. Orkla published no Excel files after Q3 2014.

**Supporting documents** (not quarterly reports, so I did not add rows for them)
- `111/R/1887727/restated-figures-bcg-2013-2014.pdf` (16 Jan 2015): 2013Q1 to 2014Q3 restated to the new BCG structure, EBITA. Orkla Foods 2014: Q1 2,920/309, Q2 3,041/357, Q3 2,900/359. 2013 total: 11,110/1,312. These rows are already in `restatements.csv` (segment-history task).
- `Public/19690/3172048/segment-information-2012-2014--annual-report-note-8.xlsx`: annual figures, already in `restatements.csv`.
- Annual reports 2013-2017 and the Q1 2018 report were downloaded for checks only. The Q1 2018 comparative for Q1 2017 (3,758/392) equals the Q1 2017 current row.

**Primary source for amounts.** Revenue and EBIT come from Note 2 (segments) in each report. I cross-checked them against the business-area tables (p.4-7). Margins are as printed in the business-area tables; I did not have to compute any (all `margin_computed=false`).

**Organic growth** comes from the report text where the report gives a quarterly figure. In Q2 reports the text gives only first-half figures, so the quarterly number comes from the presentation slide (`og_source=presentation`). From Q4 2017 it comes from the segment table.

## 2. Segment structure and definitions (as printed)

| Reports | Main food row | Definition | Parent | Other context rows |
|---|---|---|---|---|
| Q1-Q3 2014 | Orkla Foods | **2013-14 definition (C):** Nordic and Baltic food. It includes Rieber & Søn's Nordic food from 1 May 2013 and excludes the Panda/Kalev confectionery. It does not include MTR, Vitana or Felix Austria. | BCG (heading "BRANDED CONSUMER GOODS") | Orkla International; OFI |
| Q4 2014 - Q4 2017 | Orkla Foods | **2015-22 definition (D):** C plus the former Orkla International food businesses MTR Foods (India), Vitana (CZ) and Felix Austria. Delecta (PL) is included until its Q3 2014 sale. Organised internally as Nordic businesses plus "Orkla Foods International"; Orkla Foods Central Europe (Felix Austria, Vitana, Hamé) was created in 2016. | BCG | OFI |

**The Q4 2014 switch**
- Orkla International was wound up in Q4 2014. Its food units moved to Orkla Foods. Chaka went to Orkla Confectionery & Snacks, and moved again to Financial Investments from 1 Jul 2015, without restatement. Orkla Brands Russia was sold and shown as discontinued.
- The Q4 2014 report restated the Q4 2013 comparative: Orkla Foods 3,321/436, against 2,894/422 originally.
- The Q1-Q3 2015 reports carry 2014 comparatives in the new definition and in EBIT (adj.).
- **No Orkla Foods figure under the old definition C exists for 2014Q4 or FY2014.** The definition-consistent pair for Q4 is the D pair: Q4 2014 3,371 against Q4 2013 3,321.

**Changes in scope inside definition D, none restated**
- Krögarklass (SE) from 1 Oct 2014, ~SEK 35m a year.
- Tropicana distribution agreement (SE/DK) from 1 Jan 2015. It was expanded into a broader PepsiCo deal (Tropicana Norway and Quaker in the Nordics) from early 2016.
- Anamma (SE, Q2 2015) and Bioquelle (AT, via Felix Austria, Q3 2015).
- NP Foods' drinks business moved into Orkla Foods Latvija from 1 Oct 2015.
- O. Kavli (DK) from 1 Mar 2016, ~DKK 170m a year.
- **Hamé (CZ/SK) from 1 Apr 2016,** ~NOK 1.7bn a year.
- Agrimex (CZ) from 30 Sep 2017.
- K-Salat (DK) sold in Q4 2017. Exit from mayonnaise-based salads in Norway (2017).
- Struer Brød was signed on 1 Feb 2018, outside this range.

## 3. Metric definitions and changes

**Revenue.** "Operating revenues" for the segment. It includes intra-group sales; BCG eliminations are shown separately.

**Profit measure**
- Q1-Q4 2014 reports: **EBITA**, "operating profit before amortisation and other income and expenses" (footnote 1).
- From Q1 2015: **EBIT (adj.)**, "operating profit before other income and expenses". Orkla switched with the 2014 annual report; Q1 2015 report Note 1 says the difference is that EBIT (adj.) is after amortisation of intangibles.
- 2014 comparatives were restated. For Orkla Foods the gap is tiny: Q1 309 against 309, Q2 356 against 357, Q3 357 against 359, Q4 466 against 470. FY2014 is 1,488 against 1,495.
- No IFRS changes affected the segment in 2014-2017. IFRS 9 and 15 came in 2018, IFRS 16 in 2019.

**Organic growth: three definitions in this era**

| Reports | Term and definition | Easter? |
|---|---|---|
| 2014 | **"Underlying" growth**: excludes acquired/sold companies, currency translation effects and other considerable structural changes (footnote 3). In the presentations it is called "adj. organic revenue growth", adjusted for Easter effects and timing of selling days. | **Q1 and Q2 2014 Orkla Foods values (-2.7%, -4.6%) are Easter-adjusted.** The Q3 2014 slide footnote also mentions Easter and selling days. |
| Q1 2015 - Q1 2016 | **"Organic growth"**: excludes acquired and sold companies and currency translation effects. Presentation footnote: "reported growth adjusted for FX and M&A". | **Not Easter-adjusted.** Easter effects are discussed only in the text. |
| From Q2 2016 | ESMA APM wording: "adjusted for currency translation effects and structural changes". The Q4 2016 and 2017 footnotes add that acquired and sold companies are adjusted for 12 months. | Not Easter-adjusted. |

- From Q2 2016, a BCG-level table splits sales growth into FX, structure and organic. It is year-to-date in 2016 and also quarterly from Q2 2017. **Orkla gives no FX/structure split for Orkla Foods.**
- **From Q4 2017**, each business-area table has an "Organic revenue growth (%)" row with a prior-year comparative.
- **New distribution agreements were counted as organic growth in this era.** This applies to Tropicana from 2015 and the expanded PepsiCo/Quaker agreement from 2016. Orkla explicitly credits them for Orkla Foods' organic growth in 2015-2016 and calls them margin-dilutive. Later practice (2021+) treats material distribution agreements as structure, so 2015-2016 organic growth is somewhat inflated relative to later definitions.

**Price/volume.** No numeric price/mix or volume split exists for Orkla Foods in 2014-2017; the columns are empty. Qualitative statements:
- Q3 2015, Q4 2015 and Q1 2016: "price and volume".
- Q3 2016: "volume/mix".
- Q1 2017: "price and volume".
- Q3 2017: volume growth plus "slightly higher prices".
- Q4 2017: "primarily price increases".
- For BCG, Q4 2017 says "strong volume/mix".

**FX/structure for Orkla Foods.** These columns are empty. For each Orkla Foods current row, the `notes` field gives:
- the reported revenue growth, computed from the report's own columns;
- the residual "reported minus organic" (FX plus structure combined, computed).

**FX/structure for BCG.** These come from the revenue-bridge slides in the presentations; from 2017 they come from the report's sales-change table. I mapped the bridge numbers to labels using the PDF word coordinates and checked each set against the reported total. All are percent of prior-year revenue.
- Q1 2014: FX = NOK 333m / 5,939 (computed).
- Q2 2014: the bridge also has "Other 1.6%" (Easter and selling days).
- Q4 2014: the bridge also has "Selling days -1.0%".

## 4. Restatements noticed

1. **Jan-2015 restatement pdf and Q4 2014 report:** 2013Q1 to 2014Q3 restated to definition D (EBITA). In `restatements.csv`, not duplicated here.
2. **Q1-Q4 2015 reports:** 2014 comparatives restated to definition D and EBIT (adj.). For Orkla Foods the CSV comparative rows show 2,920/309, 3,041/356, 2,900/357 and 3,371/466. The originals were 2,548/295, 2,633/333 and 2,526/343 (old definition C, EBITA) and 3,371/470 (same definition, EBITA).
3. **Q1-Q3 2017 reports:** BCG organic growth for Q1-Q3 2016 restated from 1.8/3.8/2.0 to 1.75/3.7/2.05. Contract-manufacturing income for a brand sold at end-2015 was taken out of organic growth (Q1 2017 footnote 5). This is BCG-level. No restatement of Orkla Foods' organic growth was reported: Q4 2016 is -0.6% and FY2016 2.3%, the same in the Q4 2016 and Q4 2017 reports.
4. **2016-2017 Orkla Foods comparatives:** identical to the previous year's current figures in every case. The CSV check passes for 2015Q1 to 2016Q4.
5. **Group-level restatements** for discontinued operations (Gränges and Orkla Brands Russia in 2014/15, Sapa in 2017) do not affect the food segment.

## 5. Sanity checks (all pass)

**Margins.** Printed margin equals EBIT/revenue within ±0.05 pp for every row.

**Sum of four quarters equals the printed full year (current rows)**

| Year | Orkla Foods | BCG | OFI |
|---|---|---|---|
| 2015 | 13,250 / 1,701 | 32,002 / 3,839 | 7,598 / 414 |
| 2016 | 15,476 / 1,968 | 36,422 / 4,300 | 8,161 / 439 |
| 2017 | 16,126 / 2,055 | 38,510 / 4,643 | 8,703 / 469 |

- **2014, definition D:** the comparatives in the 2015 reports sum to 12,232 / 1,488, equal to the FY2014 EBIT (adj.) in the Q1-Q4 2015 reports. With EBITA, the Jan-2015 quarters sum to 12,232 / 1,495, equal to the FY in the Q4 2014 report.
- **2014, old definition C:** Q1-Q3 sum to 7,707 / 971, equal to the Q3 2014 year-to-date. There is no FY figure.

**Coverage.** Every quarter from 2014Q1 to 2017Q4 has an Orkla Foods "current" row.

**Organic growth against YTD/FY figures (weighted)**
- 2014: Q1 -2.7 and Q2 -4.6 give H1 -3.7 (printed -3.7); adding Q3 -3.4 gives YTD -3.6 (printed -3.6).
- 2015: 4.1, 1.9, 4.2 and 5.2 give FY 3.9 (printed 3.9).
- 2016: 3.3, 3.9, 3.3 and -0.6 give FY 2.3 (printed 2.3).
- 2017: 1.1, 0.4, 2.9 and 1.3 give FY 1.45 (printed 1.4).

**Year-to-date and full-year organic growth for Orkla Foods (in the `notes` column)**

| Year | H1 | 9M | FY |
|---|---|---|---|
| 2014 | -3.7 | -3.6 | -1.1 (definition D, Q4 2014 presentation p.18) |
| 2015 | 3.0 | 3.4 | 3.9 |
| 2016 | 3.6 | 3.4 | 2.3 |
| 2017 | 0.8 | 1.5 | 1.4 |

## 6. Data gaps and how I handled them

- **Q2 organic growth for Orkla Foods** (2014, 2015, 2016, 2017): the reports give H1 only, so I took the quarterly figure from the presentation (`og_source=presentation`). Each one is consistent with the H1 figure by revenue weighting. No YTD differencing was needed, so `derived_from_ytd` is false in every row.
- **Organic growth on comparative rows:** printed only for BCG in the 2016-2017 key-figure tables, and for Orkla Foods and OFI in the Q4 2017 table. Otherwise it is left empty. Use the previous year's "current" row instead; it has the same definition, except for the 2014 Easter adjustment.
- **2014 y/y in a consistent definition**
  - Q1-Q3: definition C (current against comparative in the 2014 reports), or definition D (comparatives in the 2015 reports against the restated 2013 quarters in `restatements.csv`).
  - Q4: definition D only.
- **Price/mix, volume and FX/structure for Orkla Foods** are not published. Left empty; the computed residual is in `notes`.
- No values were invented. Empty cells mean "not printed".

## 7. India (MTR) and other context for later analysis

- **2014Q1-Q3:** MTR sat inside Orkla International. MTR underlying growth was +18% in Q1, about +20% in Q2 (H1 revenue +19%) and +19% in Q3. EBITA dipped in Q3 on marketing spend.
- **From Q4 2014:** MTR is inside Orkla Foods and is not split out. Report text mentions India growth (Q4 2014, 2015, Q2 2016, Q1 2017). In H1 2017 there was destocking and disruption from India's new national tax regime (GST); by Q3 2017 trade was back to normal and margins improved after measures to rationalise production and purchasing.

**Macro-relevant drivers in the text, quarter by quarter (paraphrased in `drivers_note`)**
- **2014:** weak Nordic volumes during the Rieber integration and tail-cutting. Cost synergies (run-rate ~NOK 275m by end-2014) lifted margins. A weaker SEK raised costs in Q3.
- **2015-2016: weak NOK.** Orkla repeatedly cites higher purchasing costs from the weaker Norwegian krone, plus higher prices for key raw materials (Q4 2015, 2016). Cost-improvement programmes offset this. Margins were diluted by distribution agreements (Tropicana/PepsiCo) and acquisitions (Hamé).
- **2016:** Nordic delivery problems from changes to the factory footprint (Q2-Q4).
- **2017: raw material price inflation.** Higher input costs in Sweden and the Czech Republic and generally high raw material prices hit margins (H1, Q3). Price increases implemented through H2 2017 led to "price-driven" organic growth in Q4 2017. Restructuring in Norwegian grocery retail caused destocking in H1 2017.
- **Seasonality:** Q4 has the highest margin (14-16%) and Q1 the lowest (10-11%). Easter timing shifts sales between Q1 and Q2; there were Easter effects in 2014, 2015, 2016 and 2017. Campaign timing between Q4 and Q1 mattered in 2014/15 and 2015/16.

## 8. Odd or noteworthy items

- In Q3 2014, Orkla Foods and Orkla International both had underlying growth of exactly -3.4% (report and presentation p.4). This is not a transcription error.
- The Q1 2017 BCG table prints the comparative organic growth as "1.75" and Q3 2017 as "2.05". These are two-decimal restated values (section 4).
- In the Q1 2017 report, BCG structure is printed as "8.06" (two decimals) in the sales-change table.
- The Q4 2016 and Q4 2017 reports use decimal commas in a few places ("1,4", "(0,6)"). I converted them to points.
- The Q1-2015 EBIT (adj.) comparative for Q1 2014 (309) equals the restated EBITA (309); amortisation rounds to zero in that quarter.
