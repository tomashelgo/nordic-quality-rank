# Era E3 (2010Q1-2013Q4): verification log (verify-E3)

**Input:** `era_E3.csv` (128 rows) and `era_E3_notes.md`.
**Output:** `era_E3_verified.csv`, the same 128 rows plus two columns, `verify_status` and `verify_note`.

**Result**
- 127 rows confirmed and 1 corrected (a text field only). No rows added.
- All 128 rows match the sources field by field on revenue, EBITA, margin, organic growth, FX effect and report URL. No numeric value was changed.

## 1. Method

**Downloads.** I downloaded every source again into my own directory, `scratchpad/dl/verify-E3/`:
- orkla.com: reports, presentations and the Excel "quarterly and accounting figures" files for Q1 2010-Q4 2013 (except Q2 2011), plus Q1-Q3 2014 reports and Annual Reports 2010-2012.
- Oslo Børs NewsWeb API, for the files orkla.com does not attach:
  - Q2 2011: message 286602, attachments 88016 (xls), 88017 (report), 88018 (presentation).
  - Q4 2011: message 298104, attachments 83124 (presentation), 83125 (xls), 83126 (report).
  - The Q4 2011 report on orkla.com, "presentation-4th-quarter-2011.pdf", is byte-identical to NewsWeb 83126 (1,170,709 bytes). So it is the report, as the extractor said.
- No proxy blocks occurred.

**Independent extraction, done before opening the CSV values** (I read only the CSV header first):
- 2010Q1-2012Q3: revenue and EBITA came from each quarter's Excel "Business areas" sheet. I parsed every vintage and cross-checked them against each other.
- 2012Q4-2013Q4: revenue and EBITA came from the report segment notes and business-area tables.
- Organic growth came from the report text and, for 2013, the presentation slides.
- FX came from the presentation "Currency translation effects" slides.
- I then compared the extractor's values with mine using a script (`scripts/verify-E3/build_verified.py`).

**Comparatives.** I checked all 64 comparative rows, not just a sample:
- 16 rows for 2009, checked against the Q1 2010 Excel and the verified era E2 values.
- 32 rows for 2010-2011, checked against the first-vintage current values.
- 16 restated rows for 2012, checked against the 2013 report tables and the 2014 report comparatives.

**Rows with `derived_from_ytd=true`:** there are none.
- I confirmed that every report prints the quarter itself: Q2, Q3 and Q4 columns or text figures, alongside the YTD figures.
- So no row needed to be derived from YTD.

## 2. Independent extraction for the main food segment (current vintage), compared with the CSV

All amounts are NOK million.

| Quarter | Segment | Revenue | EBITA | Margin % | Organic % | Organic source | CSV |
|---|---|---|---|---|---|---|---|
| 2010Q1 | Orkla Foods Nordic | 2,190 | 194 | 8.86 | -3.3 (Easter-adjusted) | Q1-10 report p.5 | match |
| 2010Q2 | Orkla Foods Nordic | 2,262 | 278 | 12.29 | -6 (H1 -4) | Q2-10 report p.5 | match |
| 2010Q3 | Orkla Foods Nordic | 2,267 | 290 | 12.79 | -4 | Q3-10 report p.5 | match |
| 2010Q4 | Orkla Foods Nordic | 2,719 | 353 | 12.98 | -3 | Q4-10 report p.5 | match |
| 2011Q1 | Orkla Foods Nordic | 2,213 | 186 | 8.40 | -1 (Easter-adjusted) | Q1-11 report p.5 | match |
| 2011Q2 | Orkla Foods Nordic | 2,391 | 277 | 11.59 | +0.2 (Easter-adjusted; H1 -0.5) | Q2-11 report p.5 (NewsWeb) | match |
| 2011Q3 | Orkla Foods Nordic | 2,242 | 262 | 11.69 | -1 | Q3-11 report p.5 | match |
| 2011Q4 | Orkla Foods Nordic | 2,650 | 357 | 13.47 | -1 | Q4-11 report p.5 | match |
| 2012Q1 | Orkla Foods Nordic | 2,026 | 197 | 9.72 | ~+5 (about half Easter) | Q1-12 report p.5; presentation p.13 | match |
| 2012Q2 | Orkla Foods Nordic | 2,063 | 259 | 12.55 | not published (H1 +1 / +0.8) | Q2-12 report p.4; presentation p.11 | match (blank) |
| 2012Q3 | Orkla Foods Nordic | 2,102 | 313 | 14.9 (printed) | +4 | Q3-12 report p.5; presentation p.25 | match |
| 2012Q4 | Orkla Foods Nordic | 2,378 | 392 | 16.5 (printed) | "small underlying decline" | Q4-12 report p.4-5 | match (blank) |
| 2013Q1 | Orkla Foods | 1,924 | 226 | 11.7 | "on a par", so 0 | Q1-13 report p.5; presentation p.26 | match |
| 2013Q2 | Orkla Foods | 2,382 | 263 | 11.0 | -4.2 incl. Rieber (-2.3 ex Rieber) | Q2-13 presentation p.24 | match |
| 2013Q3 | Orkla Foods | 2,597 | 364 | 14.0 | -3.5 | Q3-13 presentation p.17 | match |
| 2013Q4 | Orkla Foods | 2,894 | 422 | 14.6 | -6.0 (FY -4.2) | Q4-13 presentation p.21 | match |

**Context rows re-extracted the same way**, all matching:
- **Parent row** (Orkla Brands, later Branded Consumer Goods): 16 quarters of revenue, EBITA, printed margin and organic growth.
- **Parent FX:**
  - 10 values recomputed from the presentation translation slides: -152, -166, -142, +35, +39, +32, -86, -172, -121, and -124 (sum of segments), each divided by prior-year revenue.
  - Orkla Foods Nordic FX: Q1-12 -37/2,213 and Q2-12 -35/2,391.
- **Orkla Brands International / Orkla International:** revenue, EBITA and organic growth.
  - 2013 organic figures are from the presentations: Q2 -8.3 (p.27), Q3 -1.5 (p.25), Q4 -11.6 (p.28).
  - The report text gives -1 for Q3 and -12 for Q4.
- **Orkla Food Ingredients:** revenue, EBITA and organic growth, including:
  - Q2-11 +13: Q2-11 report p.6, "underlying change of 13% and -9%".
  - Q2-13 +0.6: Q2-13 presentation p.28.

## 3. Arithmetic and consistency checks (all passed)

**Margins**
- Every row with `margin_computed=true` equals EBITA / revenue to 2 decimals.
- Every printed margin is within 0.05pp of EBITA / revenue.
- I checked the printed margins against the report tables (Orkla Brands and BCG business-area tables 2010-2013) and the presentations (Orkla Foods Nordic Q3-12 14.9/11.7 on p.25 and Q4-12 16.5/13.5 on p.24; Orkla Foods 2013).
- The Q1-12 presentation p.13 margin chart (8.4 / 11.6 / 11.7 / 13.5 / 9.7) matches the computed Orkla Foods Nordic margins.

**Full-year sums.** The four quarters add up to the printed full year in every case:

| Segment | Full years checked |
|---|---|
| Orkla Foods Nordic | 9,438/1,115; 9,496/1,082; 8,569/1,161 (Q4-12 report p.12) |
| Orkla Foods 2013 | 9,797/1,275 |
| Orkla Foods 2012, restated | 7,972/1,144 |
| Orkla Brands | 23,627/2,967; 24,621/2,784 |
| BCG | 24,105/2,819 (original); 24,105/2,863 (restated); 27,731/2,982 |
| Orkla Brands International / Orkla International | 2,009/40; 2,113/8; 2,133/-5; 2,644/-86 |
| Orkla Food Ingredients | 4,560/268; 5,392/230; 5,435/228; 5,998/288 |

**Half-year and nine-month figures.** The H1 and 9M figures printed in the reports equal the sums of the quarters:
- Orkla Foods Nordic: H1-10 4,452/472; H1-11 4,604/463; 9M-11 6,846/725; H1-12 4,089/456.
- Orkla Foods: H1-13 4,306/489; 9M-13 6,903/853; 9M-12 restated 5,809/776.

**Vintage consistency in the Excel files.** Every 2010-2012 food value is identical across all later Excel vintages, with one exception:
- The Q1 2012 Excel labels its last EBITA column "2011" when it is actually Q1 2012.
- A naive parse therefore reads Orkla Foods Nordic Q1-11 EBITA as 197 and Orkla Brands Q1-11 as 523.
- This confirms the header glitch the extractor reported in notes §8. The CSV correctly uses 186 and 520.

**Comparatives compared with the originally reported values**
- **2009** (16 rows): equal to the era E2 verified current values. No restatement.
- **2010-2011** (32 rows): equal to the prior-year current values.
  - The Elkem reclassification (Feb 2011) and the Sapa/Borregaard reclassification (Oct 2012) did not touch the food rows.
  - The 26 Oct 2012 restated Orkla Foods Nordic figures in `restatements.csv` are identical as well.
- **2012 restated** (16 rows), from the 2013 reports:
  - **BCG EBITA** rose by 12, 10, 11 and 11 against the original 523, 587, 773 and 936. This is IAS 19R.
  - **Orkla Food Ingredients EBITA** rose by 1, 1, 1 and 2. This is IAS 19R.
  - **Orkla International** equals the original Orkla Brands International figures.
  - **Orkla Foods** 1,898/202, 1,938/262, 1,973/312 and 2,163/368 compare with Orkla Foods Nordic 2,026/197, 2,063/259, 2,102/313 and 2,378/392. The difference is the new structure (Panda and Kalev moved out) plus IAS 19R. Full-year EBITA was 1,114 pre-IAS 19R (Q4-12 report Note 12, p.16) and 1,144 after.
  - The Q1-Q3 2014 reports carry the 2013 Orkla Foods values unchanged.

**Organic growth against reported growth, FX and structure.** The signs and magnitudes are plausible:
- 2010-2011: reported y/y growth (-4.1, -7.1, -4.6, +2.3, +1.1, +5.7, -1.1, -2.5) is roughly organic growth, plus FX (parent level -2.9 to +0.7pp), plus small acquisitions (Kalev, Baltics, Dagens) and Easter shifts.
- 2012: reported y/y growth of -8.4, -13.7, -6.2 and -10.3 against organic growth of +5, ?, +4 and "small decline". The gap is the Bakers divestment (about -11 to -12pp a quarter) and FX (Q1 -1.7, Q2 -1.5).
- 2013: reported growth of +1.4, +22.9, +31.6 and +33.8 against organic growth of 0, -4.2, -3.5 and -6.0. The gap is Rieber, consolidated from 1 May 2013.

**Units and labels**
- All amounts are NOK million.
- Labels match each report:
  - "Orkla Brands" up to Q1 2012.
  - "The Branded Consumer Goods area" from Q2 2012. The Q2-12 Excel still says "Orkla Brands", while the Q3-12 Excel says "Branded Consumer Goods".
  - "Orkla Foods" and "Orkla International" in 2013. The Q1-13 report text still says "Orkla Brands International posted…" (p.6).

**Report URLs.** Every row's `report_url` points to that quarter's release.

## 4. Discrepancies found

| # | Location | Problem | Evidence | Action |
|---|---|---|---|---|
| 1 | CSV row 2011Q3 / Orkla Foods Nordic / current, `notes` | The note says "Q3-12 presentation later shows Q3-11 underlying -0.3% (likely restated basis)". This misreads the chart. On the rendered slide, Q3-12 presentation p.25 ("Underlying change in revenues (%)"), the grey bars are H1-11 = -0.3 and Q3-11 = -0.9, and the orange bars are H1-12 = +0.8 and Q3-12 = +4.0. Q3-11 = -0.9 agrees with the report's -1%, so there is no sign of a restated basis. | Q3-12 presentation p.25; Q2-12 presentation p.11 (H1-11 -0.3, H2-11 -0.9, H1-12 +0.8); Q3-11 report p.5 (-1%) | **corrected** the `notes` text. No numeric change. |
| 2 | `era_E3_notes.md` §4, the "Half-year underlying change" bullet | Same misreading. The notes give "H1-11 -0.9, H2-11 -0.3 … Q3-11 -0.3". The correct values are H1-11 -0.3, H2-11 -0.9, Q3-11 -0.9. The follow-on claim that the 2011 values "differ … which suggests a recomputed basis" is mostly an artefact of this misreading: H1-11 -0.3 vs -0.5 Easter-adjusted, and Q3-11 -0.9 vs -1. | Same slides | Logged only. I did not edit the notes file, which is outside my output scope. |
| 3 | Extractor summary, the `definition_changes` bullet on Bakers | It says reported y/y revenue for Orkla Foods Nordic "falls about 8-14%" in 2012. The actual quarters were -8.4%, -13.7%, -6.2% and -10.3%, so the range is 6-14%. Notes §2 says "roughly 10-14%". | Revenue figures above | Logged only (wording). |
| 4 | Extractor summary bullet: "'Orkla Foods' = Orkla Foods Nordic minus Panda and Kalev … Bakers was already gone" | This is true for 2013 actuals. The restated comparatives appear still to include Bakers until its 1 Feb 2012 sale. The gap between Orkla Foods Nordic and Orkla Foods is 111 (Q1-11), 128 (Q1-12) and 125 (Q2-12), and 590 for FY2011 (9,496 vs 8,906, from Q4-12 Note 12 p.16). That is consistent with Panda plus Kalev only. If Bakers (about NOK 1 bn a year) had been excluded, the gaps would be far larger. So the restated 2011 and January 2012 Orkla Foods figures, which are in `restatements.csv`, contain Bakers, and y/y comparisons on the 2013 basis for 2012 include a divestment effect. This is an inference, not a printed statement. | Q4-12 report p.16 (Note 12); Q1/Q2-13 report Note 2; Q1/Q2-12 Excel | Added as a caveat in the `verify_note` of the 2012Q1 Orkla Foods comparative row. |
| 5 | Notes §4 / CSV row 2013Q3 note: "the YTD Q3 -3.3% does not reconcile" | Confirmed, and the problem is wider. On the same slide (Q3-13 presentation p.6), the Orkla Confectionery & Snacks YTD figure (-3.3%) also fails to reconcile with H1 -3.6% (Q2-13 presentation p.25) and Q3 -3.6% (Q3-13 presentation p.20). So that slide uses a different basis, probably pro forma, rather than containing a one-off error for Orkla Foods. The column order (Foods, C&S, H&P) is confirmed by the FY2013 EBIT margins on the Q4-13 presentation p.7 (13.0, 14.3, 17.3, which equal 1,275/9,797, 682/4,784 and 823/4,770). | Q3-13 presentation p.6; Q4-13 presentation p.7 | Logged. No change: the CSV does not use the YTD figure. |
| 6 | CSV row 2012Q2 / Orkla Foods Nordic, `notes`: "implies Q2 roughly -3%" | The arithmetic is plausible (H1 +0.8, Q1 ~+5 gives about -2.5 to -4), but the figure is not published and the base excluding Bakers is unknown. The extractor correctly left it blank. | Q2-12 report p.4; presentation p.11 | Left blank, with a note in `verify_note`. |

No discrepancies were found in any revenue, EBITA, margin, organic growth, FX, vintage, period or URL field.

## 5. Missing fields: attempts to fill

I could not fill any gap with a published number. I searched the report text, all presentation slides (the segment slides and the "Underlying change" and "Organic revenue growth" charts) and the Q4-12 and Q1-13 annual charts.

| Gap | Why it stays blank |
|---|---|
| Orkla Foods Nordic 2012Q2 organic | Only H1 is published. |
| Orkla Foods Nordic 2012Q4 organic | Only "small underlying decline" is published. FY2012 +1% is on the Q4-12 presentation p.23. |
| BCG 2012Q2 organic | Only H1 +1.5% (Q2-12 report p.4). |
| BCG 2013Q2 organic | Only H1 -2%. |
| BCG 2013Q3 organic | Only "slightly weaker underlying sales growth" (Q3-13 report p.4). |
| BCG 2013Q4 organic | Only "underlying sales growth was weaker" (Q4-13 report p.3). |
| Orkla Food Ingredients 2012Q2 organic | Only H1 +3%. |
| `fx_effect_pct` outside 2010Q1-2012Q2 | No segment-level revenue translation split is published. The Q3-12 figure is group only (-23). Q3-13 and Q4-13 give only BCG EBITA FX (+20 and +50). |
| `price_mix_pct`, `volume_pct`, `structural_effect_pct` | Never stated numerically for the food segment in 2010-2013. |

## 6. Residual concerns

1. The Q1-12 organic figure for Orkla Foods Nordic (~+5%) does not bridge cleanly to the -8.4% reported change. With FX at -1.7pp, the implied structural effect is -11.8pp for a quarter in which Bakers was out for only two months. Either Bakers' January sales were small or excluded, or "about 5%" is generous. The published value is kept.
2. 2013 organic growth for Orkla Foods mixes bases:
   - Q1 is ex-Rieber by construction, since Rieber was not yet owned.
   - Q2 is incl. Rieber pro forma (-4.2; ex Rieber -2.3).
   - Q3 and Q4 do not say how Rieber is treated.
   - FY -4.2 is consistent with incl.-Rieber quarters.
   - Q1 is coded 0.0 from "on a par".
3. Several organic figures are Easter-adjusted while others are not. The `og_metric` column says which is which, and I confirmed each against the text:
   - Orkla Foods Nordic: Q1-10, Q1-11 and Q2-11 are adjusted. Q2-10 is not stated as adjusted. Q1-12 is unadjusted.
   - Parent row: Q1-10 is unadjusted; Q2-10 and Q2-11 are adjusted; Q1-11 is unadjusted; Q1-12 is unadjusted (about one third of it from Easter).
4. Statements in the notes that are not in the CSV were not re-verified in full: the other income and expenses amounts in notes §3, and the geographic split percentages.
