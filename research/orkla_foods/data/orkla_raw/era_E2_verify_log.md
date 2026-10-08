# Verification log: era E2 (2006Q1-2009Q4), label verify-E2

Input: `era_E2.csv` (144 rows: 72 current, 72 comparative) and `era_E2_notes.md`.
Output: `era_E2_verified.csv`. It has the same 21 columns plus `verify_status` and `verify_note`.

## Bottom line
- **No value errors found.** All 72 current-vintage rows were re-extracted independently before I opened the CSV. Revenue, EBITA, margin and organic growth matched on every one (script `scripts/verify-E2/compare.py`, with my values in `mine.py`).
- **All 72 comparative rows were checked** against the prior-year columns of the source segment tables. All match. Every gap to the originally reported value is explained by a documented restatement.
- **Status counts:** 141 confirmed, 3 added, 0 corrected. The 3 "added" rows are parent-level organic-growth values I derived: 2006Q2 BCG, 2007Q4 Orkla BCG and 2009Q2 Orkla Brands.
- **Caveats:** the derived 2008Q2 values carry wider rounding bounds than the notes say, and the 2009Q1 Orkla Brands growth of 0 is doubtful. See below.

## Sources re-downloaded (own dir `scratchpad/dl/verify-E2/`, `dl/verify-E2-ar/`)
- **Quarterly reports (English):**
  - 2006: Q1 `Public/3174247/1-quarter-2006.pdf`, Q2 `Public/3174186/2-quarter-2006.pdf`, Q3 `Public/3174121/3-quarter-2006.pdf`, Q4 `Public/3174086/4th-quarter-2006-report.pdf`.
  - 2007: Q1 `Public/3174036/1-quarter-2007-pdf.pdf`, Q2 `Main/3173989/2-quarter-2007.pdf`, Q3 `Main/3173953/3rd-quarter-2007.pdf`, Q4 `Main/3173887/quarterly-report-q4-2007.pdf`.
  - 2008-2009: Q1 2008 through Q4 2009.
- **Presentations** from Q4 2007 to Q4 2009.
- **Excel "quarterly(-and-accounting)-figures"** for Q4 2007, Q1-Q4 2008, Q1-Q4 2009 and Q1 2010.
- **Annual Reports 2006-2009** and the Q4 2006 press release, used to look for missing organic growth and to check restatements.
- No proxy blocks.

## Field-by-field results (current vintage)
Revenue / EBITA / organic growth, as I extracted them; all identical to the CSV.

| Quarter | Orkla Foods | Orkla Foods Nordic | OFI / OBI (from 2008) | Orkla Food Ingredients | Parent (BCG / OBCG / Orkla Brands) |
|---|---|---|---|---|---|
| 2006Q1 | 3,199/174/0 | 2,111/152/3 | 505/3/na | 651/19/na | 7,078/500/na (incl. Media) |
| 2006Q2 | 3,360/304/1 | 2,287/281/~4 | 469/-17/na | 677/40/na | 5,056/574/na -> **added 1.0 (derived)** |
| 2006Q3 | 3,506/341/1 | 2,287/288/6 | 607/18/na | 692/35/na | 5,215/668/2 |
| 2006Q4 | 4,201/459/0 | 2,598/336/na | 848/51/na | 837/72/na | 6,249/788/3 |
| 2007Q1 | 3,325/159/-2 | 2,145/147/0 | 549/-17/na | 701/29/na | 5,285/468/2 |
| 2007Q2 | 3,618/208/-2 | 2,353/214/-1 | 576/-47/na | 759/41/na | 5,465/458/-1.5 (derived) |
| 2007Q3 | 3,553/245/-1.7 | 2,253/232/-1.6 | 599/-27/na | 785/40/na | 5,326/596/1 |
| 2007Q4 | 4,229/388/0.6 | 2,540/280/-0.5 | 839/40/0 | 955/68/7 | 6,177/696/na -> **added 1.4 (derived)** |
| 2008Q1 | - | 2,293/160/~6 | 526/-27/10 | 780/32/~5 | 5,361/492/~5 |
| 2008Q2 | - | 2,436/262/~4 (derived) | 525/-30/~18 (derived) | 880/50/~11 (derived) | 5,650/586/~8 |
| 2008Q3 | - | 2,392/287/~5 | 565/9/~19 | 902/52/~7 | 5,646/708/7 |
| 2008Q4 | - | 2,792/341/~4 | 824/53/~6 | 1,108/77/~2 | 6,741/804/5 |
| 2009Q1 | - | 2,283/171/~-2 | 430/-3/0 | 898/27/~1 | 5,398/522/0 (see caveat) |
| 2009Q2 | - | 2,436/279/0 | 460/4/3 | 972/60/0 | 5,663/638/na -> **added 0.0 (derived)** |
| 2009Q3 | - | 2,377/297/~-2 | 459/31/3 | 1,018/64/~-2 | 5,661/759/~0 |
| 2009Q4 | - | 2,658/341/-0.5 | 590/57/>3 | 1,078/85/-5 | 6,324/874/0 |

**Where each figure comes from:**
- Segment tables: report p.4 (2006); report p.8 appendix (Q1-Q3 2007, Q1 2008); report p.9 (Q4 2007); Note p.13 (Q2-Q3 2008 and Q1-Q3 2009); Note p.14 (Q4 2008 and Q4 2009).
- Business-area text: report p.2-3 (2006-07); p.4-6 (2008-09).
- Excel cross-check, exact match:
  - Q4 2007 xls sheets "Business areas 2005-2006" and "Business areas 2007".
  - Q4 2008 xls "Business areas 2007-2008", which has the restated 2007 figures.
  - Q4 2009 xls "Business areas 2008-2009".

## Discrepancies and observations, with evidence
Numbers are file units in NOK million unless marked as %.

1. **No discrepancy in any revenue, EBITA, margin or stated organic-growth value.**
2. **The derived 2008Q2 organic growth is less precise than the notes claim.** The notes say ±1pp; it is closer to ±1.4pp for Orkla Foods Nordic. The values were recomputed from Q2 2008 report p.5:
   - Orkla Foods Nordic: (0.05 x 4,629 - 0.06 x 2,207) / 2,422 = 4.1%. Rounding bounds (H1 "5 %" read as 4.5-5.5, Q1 "around 6 %" as 5.5-6.5) give 2.7% to 5.5%.
   - Orkla Brands International: (0.14 x 985 - 0.10 x 484) / 501 = 17.9%, bounds 16.4% to 19.3%.
   - Orkla Food Ingredients: (0.08 x 1,460 - 0.05 x 701) / 759 = 10.8%, bounds 9.3% to 12.2%.
   - Cross-check: the revenue-weighted unit average (with Orkla Brands Nordic Q2 also derived at about 9%) gives 8.0%, which matches the stated Orkla Brands Q2 figure of about 8% (report p.4, presentation p.18). The values are kept; only the notes are refined.
3. **2009Q1 Orkla Brands organic growth = 0 is doubtful.**
   - The 0 comes from presentation p.22: "Flat organic top line growth".
   - The report (p.4) says underlying sales were "somewhat lower".
   - The revenue-weighted average of the four unit figures (Orkla Foods Nordic about -2, Orkla Brands Nordic about -1, Orkla Brands International 0, Orkla Food Ingredients about +1; report p.5) is -1.1%.
   - Kept at 0 because it is the company's own number, but it is flagged. The true figure is probably about -1%. This is a parent-level row, not the main food series.
4. **Restated FY2006 revenue for Orkla Foods Nordic is not in the notes.** Annual Report 2007 gives FY2006 on the new basis (including the Baltics) as 9,483 / 1,074; the notes give only EBITA 1,074. The old basis was 9,283 / 1,057. No restated 2006 quarters were published.
5. **2005Q1 BCG comparative (6,525 / 439, Q1 2006 report p.4) includes Orkla Media.** This is already documented. An excluding-Media figure that matches the 2005Q2-Q4 rows can be derived from the Q2 2006 report p.4: H1 2005 9,369 / 953 minus Q2 2005 4,930 / 542 = 4,439 / 411. The four quarters 4,439 + 4,930 + 4,811 + 5,557 sum to 19,737, which equals FY2005 excluding Media. Recorded in `verify_note`; the row is not changed.
6. **The Q4 2007 Excel sheet "Business areas 2005-2006" shows 2005 BCG including Media** (for example Q2 7,145 / 712, FY 28,408), while the 2006 reports' 2005 comparatives exclude it. This is a vintage/scope difference worth knowing if 2005 BCG is ever taken from that Excel file. No CSV row is affected.
7. **The extractor's typo handling is correct:**
   - Q4 2008 report p.5: "underlying growth in revenue was about 15 %" sits right after the EBITA sentence and refers to EBITA (reported EBITA +18.8%). Revenue growth of about 4% is stated earlier in the paragraph.
   - Q3 2006 report p.2: the bullet "5 % top-line growth" is reported growth (+5.4%); the text says underlying 6%.
8. **The Baltic transfer in the 2008 reorganisation is confirmed:**
   - Q4 2007 presentation p.59: about NOK 250m revenue and 20m EBITA in 2007.
   - Restated 2007 Orkla Foods Nordic quarters: 2,207/152, 2,422/219, 2,308/235, 2,611/287. These sum to 9,548 / 893, against 9,291 / 873 on the old basis.
9. **The Romania move from Orkla Brands International to Orkla Food Ingredients without restatement is confirmed.** The Q1 2009 report shows the Q1 2008 comparatives as 526 and 780, identical to the 2008 originals; p.5 describes the move. As a result, 2009 reported y/y for these two units is distorted: Orkla Brands International -18% to -28% reported against about +3% organic; Orkla Food Ingredients +10% to +15% reported against about 0% organic.

## Arithmetic and consistency checks
- **Margins:** EBITA/revenue for all computed rows matches exactly at 2 decimals. All 18 printed margins (presentation and report tables) are within 0.04pp of the computed value.
- **Four quarters vs full year (exact):**
  - Orkla Foods: 2006 14,266 / 1,278; 2007 14,725 / 1,000.
  - Orkla Foods Nordic: 2006 9,283 / 1,057; 2007 old basis 9,291 / 873; 2007 restated 9,548 / 893; 2008 9,913 / 1,050; 2009 9,754 / 1,088.
  - Orkla Foods International: 2006 2,429 / 55; 2007 2,563 / -51.
  - Orkla Food Ingredients: 2006 2,857 / 166; 2007 3,200 / 178; 2008 3,670 / 211; 2009 3,966 / 236.
  - Orkla Brands International: 2008 2,440 / 5; 2009 1,939 / 89.
  - BCG excluding Media: 2006 21,398 / 2,455; 2007 22,253 / 2,218.
  - Orkla Brands: 2008 23,398 / 2,590; 2009 23,046 / 2,793.
- **Units:** all NOK million. Labels and scope agree with each report's own segment names.
- **Below-EBITA items confirmed** from the Q4 2007, Q4 2008 and Q4 2009 Excel files:
  - Orkla Foods Q3 2007: -324 (EBIT -79).
  - Orkla Brands Q4 2008: -533.
  - Orkla Brands Q2 2009: -10.
- **Organic vs reported growth (main series), with plausible gaps throughout.**
  - Orkla Foods Nordic, reported / organic (%):
    - 2006: Q1 +2.5 / 3; Q2 +4.4 / 4; Q3 +5.4 / 6.
    - 2007: Q1 +1.6 / 0; Q2 +2.9 / -1 (Pastella acquisition); Q3 -1.5 / -1.6; Q4 -2.2 / -0.5.
    - 2008: Q1 +3.9 / 6; Q2 +0.6 / ~4; Q3 +3.6 / 5; Q4 +6.9 / 4 (weak NOK).
    - 2009: Q1 -0.4 / -2; Q2 0 / 0; Q3 -0.6 / -2; Q4 -4.8 / -0.5 (NOK strengthening against SEK).
  - Orkla Foods: reported growth runs 1-10pp above organic in 2006-07, consistent with acquisitions (Krupskaya, Royal Brinkers, MTR, Setuza, Pastella). No sign conflicts.
- **Parent figures reconcile with the unit figures (revenue-weighted):**
  - 2008Q1: 5.1% (stated about 5).
  - 2008Q2: 8.0% (stated about 8).
  - 2009Q3: -0.5% (stated "approximately flat").
  - 2009Q4: +0.3% (stated "on a par").
  - 2009Q1 does not reconcile: -1.1% against the 0 recorded (item 3).

## Fills
These three parent-level organic-growth values are now marked `og_source=derived`, `verify_status=added`. No figure was stated at parent level.
- **2006Q2 BCG: 1.0%.** Weighted from Orkla Foods +1% (base 3,310) and the Orkla Brands sub-segment at about 1% (base 1,666), Q2 2006 report p.2-3. The range is 0.7-1.0%, because the Orkla Brands paragraph also says revenue was "on a par" after adjusting for Collett Pharma and FX.
- **2007Q4 Orkla BCG: 1.4%.** Weighted from Orkla Foods +0.6% (base 4,201) and Orkla Brands +3% (base 2,085), Q4 2007 report p.3-4 and presentation p.30. A full-year consistency check (Annual Report 2007 / Q4 report: Orkla Foods -1.1%, Orkla Brands +4%) implies about 0.9%. Treat as about 1% ±0.5.
- **2009Q2 Orkla Brands: 0.0%.** Weighted from the units' Q2 2009 figures (Orkla Foods Nordic 0, Orkla Brands Nordic -1, Orkla Brands International +3, Orkla Food Ingredients 0), Q2 2009 report p.5; the result is -0.05%.

**Not fillable** (searched the reports, the presentations available from Q4 2007, Annual Reports 2006-2007 and the Q4 2006 press release):
- Orkla Foods Nordic 2006Q4. Annual Report 2006's "underlying growth of 6%" for Orkla Foods Nordic refers to EBITA, not revenue.
- Orkla Foods International 2006Q1-2007Q3.
- Orkla Food Ingredients 2006Q1-2007Q3.
- BCG 2006Q1, because the Orkla Brands sub-segment growth is qualitative only.
- Price/mix, volume, FX and structural splits in %: not published for this era.

## Residual concerns
- Orkla Foods Nordic 2006Q4 organic growth is still missing from the main series. Reported growth was +6.3%; total Orkla Foods underlying growth was "on a par".
- **Series break at 2008:** there is no Orkla Foods total for 2008-09, and Orkla Foods Nordic changes scope (Baltics added). Use the restated 2007 comparatives for 2008 y/y. In 2009, y/y for Orkla Brands International and Orkla Food Ingredients is distorted by Romania (not restated).
- The derived organic-growth values (2008Q2 x3, 2007Q2 BCG and the three fills) rest on rounded "about" figures and on 2007 reported revenue used as an approximate base. Weight them lower in any regression.
- Orkla Foods Nordic 2008Q1 growth ("around 6 %") excludes M&A but has no explicit FX exclusion in the wording.
