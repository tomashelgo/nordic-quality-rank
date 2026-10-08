# Era E5 (2018Q1–2021Q4): Orkla Foods quarterly extraction notes

Companion to `era_E5.csv`: 64 rows = 16 reports x 2 vintages (current, comparative) x 2 segment labels (`Orkla Foods`, `Branded Consumer Goods`).

## Sources used
- All 16 English quarterly reports, Q1 2018 to Q4 2021 (`www.orkla.com/files/...`; the URLs are in the CSV), plus the matching investor presentations.
- Cross-checks:
  - Q4 2017 report: its Q4 2017 and FY 2017 figures equal the comparatives printed in the 2018 reports.
  - Q1 2022 report: its Q1 2021 comparative is 4,299 / 507, unchanged.
  - Orkla's "restated segment financials 2018–2019" file (6 Feb 2020; https://www.orkla.com/files/Public/19690/3176571/orkla--restated-segment-financials-2018-2019.docx, which is really an xlsx). Its Orkla Foods revenue, EBIT (adj.) and 2019 quarterly organic growth match the reports exactly.
- Nothing was missing from the manifest. No Excel quarterly-figures files exist for this era, so the PDF tables (business-area table, Note 2 Segments, APM organic-growth table) are the primary source.
- Every quarter, including Q4, is printed directly as a quarterly column. No figures had to be derived from YTD values (`derived_from_ytd=false` everywhere).

## Segment definitions
- **Orkla Foods** is a business area inside **Branded Consumer Goods (BCG)**. The label is "Orkla Foods" in every 2018–2021 report.
  - No Nordic/International sub-segments are reported in this era. Management did split the area from 1 Oct 2018 into "Orkla Foods (Nordics and Baltics)" and "Orkla Foods (International)" under two CEOs (Q2 2018 presentation p.5), but that split is not reported.
  - **Scope:** Orkla Foods Norge, Sverige, Danmark, Finland and the Baltics (Latvia, among others; Orkla Latvija was sold in Q4 2021), plus Central Europe and India.
  - Central Europe is mainly Orkla Foods Česko a Slovensko: Hamé and Vitana, whose merger was decided in Q3 2018. The Panzani distribution agreement also covered Hungary. Felix Austria and other small units are listed in segment_history.md; the reports do not give a country list.
  - India is MTR, plus Eastern Condiments (67.8%) from 1 Apr 2021.
  - **India is inside Orkla Foods throughout 2018–2021.** The reports print no separate Orkla India figures, so there are no Orkla India rows. India was split out as a separate business area only from the Q3 2022 report, which restated 2021 comparatives. The Q1 2022 report announces the organisational change.
  - **Kotipizza was never part of Orkla Foods.** It was consolidated in Orkla Financial Investments from 1 Feb 2019, and in Orkla Consumer Investments (inside BCG) from 2020.
- **Branded Consumer Goods** (context rows) uses the Note 2 total excluding HQ.
  - 2018–2019 it comprises Orkla Foods, Orkla Confectionery & Snacks, Orkla Care and Orkla Food Ingredients, less eliminations.
  - From the Q1 2020 report it also includes **Orkla Consumer Investments**, built from Orkla Care units (House Care, Lilleborg, Pierre Robert) plus Kotipizza and Gorm's, which previously sat outside BCG.
  - From Q4 2018 Orkla's headline key figures (report p.2) use "BCG incl. HQ". The CSV keeps the excl.-HQ total for consistency. Its margin is computed and flagged, except for 2018Q1–Q3 current rows, where p.2 prints the same excl.-HQ margin (9.9 / 10.8 / 13.4%).

## Metric definitions and changes
- **EBIT measure: "EBIT (adj.)"** in the business-area tables. Note 2 labels it "Operating profit - EBIT (adj.)" in 2018 and "EBIT (adj.)" from 2019. It is operating profit before "other income and expenses" (M&A/integration costs, restructuring, write-downs, gains on disposals). The label and definition are unchanged through 2018–2021.
- **Margin:** "EBIT (adj.) margin", printed to one decimal in the Orkla Foods table for both current and comparative columns from Q4 2018. For Q1–Q3 2018 the comparative margin is not in the report table, which shows only the bps/pp change:
  - Q1 2017 10.4% and Q2 2017 10.9% are taken from the presentation key-figures slides.
  - Q3 2017 13.5% is printed in the report text ("14.2% (13.5%)").
  - All printed margins agree with EBIT/revenue to within 0.05pp.
- **Organic growth:** "Organic revenue growth" (business-area table row) is the same figure as "Organic growth" in the APM table "Organic growth by business area". Under the ESMA APM definition it:
  - excludes FX translation (current revenue converted at last year's rates);
  - excludes acquisitions for 12 months and divestments pro forma for the prior 12 months;
  - treats lost or won distribution agreements and internal transfers as structure. Examples: Panzani distribution in CZ/SK, NOK 111m in 2019, ended 1 Mar 2020. OTA Solgryn distribution was also lost. Frödinge moved from Orkla Foods Sverige to Orkla Food Ingredients in Q4 2020, as a "structural adjustment at business area level".
- **FX / structure:** these come from the APM table, which splits total sales change into organic, FX and structure. Column order changed at Q4 2019: Q4 2018 to Q3 2019 print FX | Structure | Organic | Total, and Q4 2019 onwards print Organic | FX | Structure | Total. Every parsed row was checked against the organic figure in the business-area table and against actual revenue growth (organic + FX + structure = total within ±0.1pp rounding). A "-" in this table means zero.
  - The **Q1–Q3 2018 reports** give FX/structure only for BCG as a whole, not for Orkla Foods, so these three current rows have empty FX/structure cells. The Q1/Q2/Q3 2019 reports print the split for those quarters, and it sits in the 2018 comparative rows:
    - Q1 2018: FX +3.3, structure −2.3
    - Q2 2018: FX −1.0, structure −2.7
    - Q3 2018: FX −1.1, structure −1.7
- **Price/mix and volume:** no quantified split for Orkla Foods appears in any 2018–2021 report or presentation, so these columns are empty. Only qualitative statements exist, e.g. "positive contributions from price increases" (Q1 2018) and "organic growth predominantly volume driven" (BCG, Q3 2021 presentation). According to segment_history.md, formal price vs volume/mix reporting began in 2023.
- **Underlying EBIT (adj.) growth:** introduced in Q4 2018, but printed only for BCG incl. HQ, not per business area in the tables. Not captured.
- **IFRS 15 (1 Jan 2018):** no material effect and no restatement (Q1 2018 Note 1).
- **IFRS 16 (1 Jan 2019):**
  - Applied with the modified retrospective method, so **2018 comparatives are not restated**.
  - Group effect: operating profit about +NOK 20m/yr, depreciation about +390m, other opex about −410m (Q1 2019 Note 1).
  - The Orkla Foods share is not disclosed; it is negligible for the EBIT (adj.) margin, but would matter for EBITDA.
  - y/y comparisons for 2019 therefore set IFRS 16 against IAS 17 figures (flagged in the 2019 comparative rows).

## Restatements found
- **Orkla Foods:** none. Every comparative printed in 2018–2021 (and the Q1 2021 comparative in the Q1 2022 report) equals the originally published current figure, and the Feb-2020 restated file leaves Orkla Foods unchanged.
- **Branded Consumer Goods:** restated in the 2020 reports when Orkla Consumer Investments was created.

  | Quarter (FY) | Originally published (revenue / EBIT (adj.)) | Restated (revenue / EBIT (adj.)) | Organic growth, original → restated |
  |---|---|---|---|
  | Q1 2019 | 9,687 / 1,017 | 9,868 / 1,027 | 0.9 → 0.9 |
  | Q2 2019 | 10,051 / 1,124 | 10,337 / 1,142 | 1.1 → 1.0 |
  | Q3 2019 | 10,336 / 1,401 | 10,649 / 1,428 | 1.5 → 1.5 |
  | Q4 2019 | 11,471 / 1,534 | 11,778 / 1,551 | 2.0 → 1.9 |
  | FY 2019 | 41,545 / 5,076 | 42,632 / 5,148 | – |

  - The structure effects changed as well.
  - The Feb-2020 file also restates BCG 2018 (e.g. Q2 2018 9,731 / 1,052). The CSV does not use those figures, because no 2018–2021 quarterly report prints them as comparatives.

## Sanity checks (all passed)
- Margins: every printed margin is within 0.05pp of EBIT/revenue.
- **Orkla Foods** sums of four quarters equal the printed full year:

  | Year | Revenue (NOK m) | EBIT (adj.) (NOK m) | Notes |
  |---|---|---|---|
  | 2017 | 16,126 | 2,055 | comparatives |
  | 2018 | 16,000 | 2,048 | |
  | 2019 | 16,776 | 2,276 | |
  | 2020 | 18,301 | 2,641 | |
  | 2021 | 18,760 | 2,471 | |

- **BCG** sums also equal the printed full year: 2017 38,510 / 4,643; 2018 39,592 / 4,671; 2019 41,545 / 5,076 (original) or 42,632 / 5,148 (restated); 2020 46,521 / 5,767; 2021 49,204 / 5,794.
- Every quarter 2018Q1–2021Q4 has a "current" Orkla Foods row with revenue, EBIT (adj.), printed margin and organic growth.

## Data gaps and handling
- Organic growth and FX/structure for the comparative quarters 2017Q1–Q3 (in the Q1–Q3 2018 reports) are not printed for Orkla Foods. Those cells are left empty. Q4 2017 is available from the Q4 2018 APM table: organic 1.3, FX 4.5, structure −1.1.
- For BCG, comparative organic growth for 2017Q1–Q3 is not printed either; those cells are empty.
- Orkla India was not reported separately, so it has no rows (see Segment definitions).

## Odd or notable items for the macro analysis
- **2018:**
  - Weak SEK against EUR raised Orkla Foods' input costs, especially in Sweden.
  - The higher Norwegian sugar tax and changed retailer campaign patterns hit volumes in Norway (Q2–Q3 2018).
  - Divestments in Denmark (K-Salat, Pastella) and Sweden (Mrs. Cheng's) depressed structure.
  - Q1 2018 Easter timing cut sales days.
- **2019:** price increases and "revenue management" offset weak SEK/NOK and higher raw-material prices. The margin rose about 0.7–0.8pp every quarter. Denmark deliberately exited low-margin volume.
- **2020:** Covid stockpiling lifted Q1 organic growth to +10.8%, which partly reversed in Q2 (−0.7%). Out-of-home sales were weak while grocery was strong. A weak NOK hurt input costs, but FX translation helped reported EBIT. Pricing caught up with a lag in Q4, when the margin hit 16.8%.
- **2021:**
  - Q1 organic growth of −4.7% reflects lapping the stockpiling.
  - The new ERP rollout in Orkla Foods Sverige weighed on sales and costs from Q1 to Q4 2021.
  - Raw-material, packaging, transport and energy inflation hit H2 2021 and price increases lagged, so the Q4 margin fell 2.6pp to 14.2%.
  - Q3 had about NOK 20m of product-recall costs.
  - Large structural growth (+5.8–6.0pp in Q2–Q4) came from Eastern Condiments, which raises the India weight inside Orkla Foods.
- **Havrefras:** distributed for PepsiCo until the brand was bought in June 2020, after which it is treated as an acquisition (structure).
- The Q3 2021 report text says "down 0.5%" for the margin; it means 0.5 percentage points.
