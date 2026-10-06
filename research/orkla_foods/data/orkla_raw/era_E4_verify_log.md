# Era E4 (2014Q1-2017Q4): verification log (verify-E4)

**Input:** `era_E4.csv` (102 rows) and `era_E4_notes.md`.
**Output:** `era_E4_verified.csv`, the same 102 rows plus two columns, `verify_status` and `verify_note`.

**Result**
- 91 rows confirmed.
- 7 rows corrected, in the `og_metric` text only. No numeric value was changed.
- 4 rows had a missing field filled (`added`): organic growth on the BCG 2013 comparative rows.
- Every row matches the sources field by field on revenue, EBIT measure, margin and organic growth. The BCG rows also match on FX and structural effect.
- I found no numeric error in the extraction.

## 1. Method

**Downloads.** I downloaded every source again into my own directory, `scratchpad/dl/verify-E4/`, using the manifest's orkla.com links:
- English quarterly reports and presentations for Q4 2013 to Q3 2018 (40 PDFs);
- the Q3 2014 Excel file, `quarterly-and-accounting-figures-3rd-quarter-2014.xlsx`.

No proxy blocks occurred.

**Independent extraction, done before opening the CSV values** (I read only the CSV header first):
- Segment tables (Orkla Foods, Branded Consumer Goods, Orkla Food Ingredients, Orkla International): parsed from PyMuPDF text for every report with my own parser (`scripts/verify-E4/segtab.py`). The 2014-2015 BCG tables, whose heading the parser missed, I read by hand.
- Organic growth: taken from the report text and the presentation slides. For each Q2, the quarterly value comes from the presentation and was checked against the first-half figure in the report.
- BCG revenue bridges: label/value mapping done from PDF word coordinates (`scripts/verify-E4/bridge.py`).
- I then compared my values with the CSV using a script (`scripts/verify-E4/build_verified.py`). It reported zero numeric mismatches across 102 rows × 4 fields, plus FX and structure on the 16 BCG current rows.

**Comparatives.** I checked all 51 comparative rows, not just a sample. No row has `derived_from_ytd=true`.

## 2. Discrepancies and corrections

| # | Rows (CSV index, 0-based) | Field | Old | New | Evidence |
|---|---|---|---|---|---|
| 1 | 16 (Orkla Foods 2014Q3), 24 (Orkla Foods 2014Q4) | `og_metric` | "underlying growth (excl. acquired/sold companies, currency translation effects and other considerable structural changes)" | Same text, plus: "pres. footnote: reported growth adjusted for FX, M&A and timing of selling days (i.e. also selling-day adjusted, unlike 2015+)" | Q3-14 presentation p.4 and p.19; Q4-14 presentation p.4 and p.18. Footnote: "Reported growth adjusted for FX, M&A and timing of selling days". The report's "underlying" figure equals the slide figure (-3.4% and +2.2%), so the printed value is selling-day adjusted. The Q4-14 BCG bridge (pres p.16) shows the selling-day effect as a separate bar of -1.0%. From Q1 2015, the footnote reads only "Reported growth adjusted for FX and M&A". This matters because Q4 2014 is the first definition-D quarter that sits next to the 2015 values. |
| 2 | 18 (BCG 2014Q3), 26 (BCG 2014Q4), 20 (OFI 2014Q3), 28 (OFI 2014Q4), 22 (Orkla International 2014Q3) | `og_metric` | as in #1 | as in #1 | BCG: Q3-14 pres p.18 bridge footnote "Organic growth has been adjusted for timing of selling days"; Q4-14 pres p.16, where "Selling days -1.0%" is a separate bar. OFI: Q3-14 pres p.23 and Q4-14 pres p.21. Orkla International: Q3-14 pres p.22. All carry the same footnote. |
| 3 | 3, 11, 19, 27 (BCG comparatives 2013Q1-Q4) | `organic_growth_pct` (empty), `og_metric`, `og_source`, `page_ref` | empty | -0.5, -3.9, -2.8, -3.6 | **2013Q1:** Q3-14 pres p.4, BCG quarterly chart. By word coordinates, "-0.5%" sits at x=104-141 above the label "Q1'13" at x=106-138. **2013Q2:** Q2-14 pres p.3, "Adj. organic growth BCG ... Q2'13 -3.9%" (also Q3-14 pres p.4). **2013Q3:** Q3-14 pres p.4, "-2.8%" at x=182-219 above "Q3'13" at x=184-216. **2013Q4:** Q4-14 pres p.4, "Q4'13 -3.6%". All four are Easter- and selling-day-adjusted, on the old BCG perimeter including Orkla Brands Russia. **Caveat for row 27:** its revenue and EBITA (7,738/961) are restated to the Q4-14 perimeter, while -3.6% is on the old perimeter. The 2015 presentation footnotes say that OG data before Q4-14 include Orkla Brands Russia. |

No Orkla Foods value (revenue, EBITA/EBIT (adj.), margin or organic growth) was wrong in any of the 32 Orkla Foods rows.

## 3. Field-by-field confirmation: Orkla Foods, current vintage

Revenue, EBIT and margin come from each report's Orkla Foods table and Note 2. Organic growth comes from the source listed.

| Period | Revenue | EBIT | Margin | OG % | OG source (my extraction) |
|---|---|---|---|---|---|
| 2014Q1 | 2,548 | 295 (EBITA) | 11.6 | -2.7 | Q1-14 report p.5 (Easter-adj.); pres p.19 |
| 2014Q2 | 2,633 | 333 (EBITA) | 12.6 | -4.6 | Q2-14 pres p.5/p.18 (Easter-adj.); report p.5 H1 -3.7 |
| 2014Q3 | 2,526 | 343 (EBITA) | 13.6 | -3.4 | Q3-14 report p.5; pres p.4/p.19 |
| 2014Q4 | 3,371 | 470 (EBITA) | 13.9 | 2.2 | Q4-14 report p.5; pres p.4/p.18 (definition D) |
| 2015Q1 | 3,045 | 322 | 10.6 | 4.1 | Q1-15 report p.5; pres p.19 |
| 2015Q2 | 3,122 | 389 | 12.5 | 1.9 | Q2-15 pres p.14 (YTD 3.0 = report p.5) |
| 2015Q3 | 3,261 | 429 | 13.2 | 4.2 | Q3-15 report p.5; pres p.17 |
| 2015Q4 | 3,822 | 561 | 14.7 | 5.2 | Q4-15 report p.5; pres p.19 |
| 2016Q1 | 3,418 | 377 | 11.0 | 3.3 | Q1-16 report p.5; pres p.18 |
| 2016Q2 | 3,967 | 463 | 11.7 | 3.9 | Q2-16 pres p.17 (YTD 3.6 = report p.5) |
| 2016Q3 | 3,905 | 512 | 13.1 | 3.3 | Q3-16 report p.5; pres p.11 |
| 2016Q4 | 4,186 | 616 | 14.7 | -0.6 | Q4-16 report p.6; pres p.14; Q4-17 table comparative |
| 2017Q1 | 3,758 | 392 | 10.4 | 1.1 | Q1-17 report p.6; pres p.10 |
| 2017Q2 | 3,977 | 434 | 10.9 | 0.4 | Q2-17 pres p.11 (YTD 0.8 = report p.6) |
| 2017Q3 | 4,007 | 540 | 13.5 | 2.9 | Q3-17 report p.6; pres p.11 |
| 2017Q4 | 4,384 | 689 | 15.7 | 1.3 | Q4-17 report p.6 table row "Organic revenue growth (%)" |

EBIT is EBIT (adj.) from 2015Q1.

## 4. Consistency checks (all pass unless noted)

**Margins.** Printed margin equals EBIT/revenue within ±0.05 pp on all 102 rows.

**Four quarters against the printed full year**
- Orkla Foods: 2015 13,250/1,701; 2016 15,476/1,968; 2017 16,126/2,055.
- BCG: 2015 32,002/3,839; 2016 36,422/4,300; 2017 38,510/4,643.
- OFI: 2015 7,598/414; 2016 8,161/439; 2017 8,703/469.
- 2014 definition D, from the comparatives in the 2015 reports:
  - Orkla Foods 12,232/1,488.
  - BCG 28,584/3,378.
  - OFI 6,534/345.
- 2014 definition C: Orkla Foods Q1-Q3 sum to 7,707/971, equal to the Q3-14 YTD.
- 2013, from the comparatives in the 2014 reports: Orkla Foods 1,924+2,382+2,597+2,894 = 9,797, and EBITA 1,275, equal to FY2013.

**Excel cross-check.** The Q3-2014 Excel file ("Income statement" sheet) matches every 2013Q1-2014Q3 Orkla Foods, BCG, Orkla International and OFI value exactly.

**Orkla Foods organic growth against YTD/FY** (weighted by prior-year revenue)

| Year | Weighted | Printed | Note |
|---|---|---|---|
| 2014 H1 | -3.75 | -3.7 | |
| 2014 9M | -3.62 | -3.6 | |
| 2015 FY | 3.88 | 3.9 | |
| 2016 H1 | 3.60 | 3.6 | |
| 2016 9M | 3.50 | 3.4 | rounding |
| 2016 FY | 2.32 | 2.3 | Confirms Orkla Foods Q1-Q3 2016 were not affected by the BCG organic restatement. |
| 2017 H1 | 0.72 | 0.8 | Within rounding of the unrounded quarterly inputs. |
| 2017 FY | 1.43 | 1.4 | |

**Comparatives against first print**
- **2015 and 2016 Orkla Foods, BCG and OFI comparatives** in the 2016 and 2017 reports equal the first-print current values.
- **2014 comparatives in the 2015 reports** differ from the first print:
  - Orkla Foods: the definition C→D structure change (MTR, Vitana, Felix Austria and Delecta moved in; Q4-14 report notes, p.11) plus the EBITA→EBIT (adj.) switch.
  - BCG: the Q4-14 re-organisation (Orkla International wound up, Russia discontinued).
  - OFI: revenue is identical; EBIT differs only by amortisation.
- **Q4-13 Orkla Foods comparative** (3,321/436): restated from the original 2,894/422 (Q4-13 report p.5).
- **Q4-14 restated EBITA under definition D for 2014** (Q4-14 pres p.18): the margins 10.6/11.7/12.4 on revenue of 2,920/3,041/2,900 are consistent with the notes' EBITA of 309/357/359.
- **BCG organic growth for Q1-Q3 2016 restated** to 1.75/3.7/2.05 in the 2017 tables. Cause: the Q1-17 report footnote 5 on contract-manufacturing income. That footnote's text says "from 1.8 to 1.7%", while the table prints 1.75; the CSV uses the table value.

**2017 values are unchanged in the 2018 vintage.** The Q1-Q3 2018 reports print only Δ% and R12M, not comparative columns, so the notes file's statement that the Q1-18 comparative "equals" Q1-17 is loosely worded. The implied 2017 figures do match:
- Q1: 3,852/1.025 = 3,758 and 400/1.02 = 392.
- R12M: 16,220 = 16,126 + 3,852 - 3,758, and 2,063 = 2,055 + 400 - 392.
- Q2 and Q3 likewise give 3,977/434 and 4,007/540.

**BCG FX and structure**
- Every bridge label was mapped by word coordinates: Q2-14, Q3-14, Q4-14, Q1-15, Q2-15, Q3-15, Q4-15, Q1-16, Q2-16, Q3-16 and Q4-16.
- For 2017 the values come from the report's "Sales revenues changes" tables (p.5).
- Organic + FX + structure reproduces the reported growth in every quarter from Q3-14 on. Q2-14 also needs "Other 1.6%" and Q4-14 "Selling days -1.0%", as the CSV notes say.
- FX also matches the NOK translation amounts in the report text: Q3-15 454/6,984 = 6.5; Q4-15 453/7,854 = 5.8; Q1-16 394/7,220 = 5.5; Q3-16 29/8,064 = 0.4; Q4-16 -315/9,314 = -3.4; Q4-17 447/9,734 = 4.6.
- The 2016 YTD tables (H1 5.5/11.4, 9M 3.7/11.4, FY 1.6/10.4) and the 2017 H1/9M/FY tables match the quarterly values.

**Units and labels.** All amounts are in NOK million.
- Segment labels as printed: "Orkla Foods", "BRANDED CONSUMER GOODS", "Orkla Food Ingredients", "Orkla International".
- `ebit_metric`: EBITA in the 2014 reports, EBIT (adj.) from Q1 2015.
- `report_url` and page references were checked against the downloaded files.

**Organic growth against reported growth (Orkla Foods).** The residuals in the notes column (reported minus organic) were recomputed and all match. Their signs and sizes fit the stated scope events:
- Delecta sale: negative in Q4-14 and Q1-15.
- Hamé from 1 Apr 2016 (+23pp residual in Q2-16) and Kavli from 1 Mar 2016: both confirmed in the Q1/Q2-16 reports.
- Hamé anniversary in Q2-17, with a residual of about 0.
- Positive FX in Q4-17.

## 5. Residual concerns (not errors in the CSV)

1. **Definition break in the current-vintage Orkla Foods series.**
   - 2014Q1-Q3 use definition C (EBITA, excluding MTR, Vitana and Felix Austria). 2014Q4 onward use definition D.
   - The current rows for 2014 therefore do not sum to any FY2014 figure.
   - For a consistent y/y series, use the 2015-report comparatives (2,920/3,041/2,900/3,371).
2. **2014 organic growth is on a different basis from 2015 onward.**
   - Q1 and Q2 2014 are Easter-adjusted, and all of 2014 is selling-day adjusted.
   - From 2015, organic growth is adjusted for FX and M&A only.
   - From 2015 there is no Orkla Foods organic growth for 2014 quarters under definition D, except FY2014 at -1.1%.
3. **Q1-14 BCG FX of 5.61% is computed** as NOK 333m / 5,939.
   - This text-amount method agrees with the bridge slides in 2015-2016.
   - In 2017 it does not: Q1-17 report text gives NOK -386m, which is -4.6%, against -4.0% in the table and the presentation. H1-17 gives -424m (-2.4%) against a -2.0% table.
   - The CSV correctly uses the table values for 2017. The Q1-14 figure should be treated as approximate.
4. **Distribution agreements counted as organic growth.** Tropicana (2015) and the PepsiCo/Quaker expansion (2016) were counted as organic, as the notes say. Organic growth for 2015-2016 is therefore not comparable with later practice.
5. **BCG 2013Q4 comparative OG** (added, -3.6%) is on the old perimeter including Russia, while that row's revenue and EBITA are restated (see the caveat in item 3 of section 2).
