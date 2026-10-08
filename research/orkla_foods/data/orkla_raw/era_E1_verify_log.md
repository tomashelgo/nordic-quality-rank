# Era E1 (2001Q1-2005Q4) verification log (verify-E1)

Input: `era_E1.csv` (88 rows) and `era_E1_notes.md`. Output: `era_E1_verified.csv`, which has the same columns plus `verify_status` and `verify_note`.

## Method
- I downloaded all 20 quarterly reports again myself: English versions; the Q1 2001 English press release with figures; the Q4 2004 PDF, which is the Norwegian report. I also downloaded:
  - the Q2 2001, Q2 2002, Q4 2003 and Q4 2005 press releases with figures;
  - the Q1-Q4 2006 reports, for the 2005 comparatives;
  - the annual reports for 2002, 2003 and 2004.
- Files are in `scratchpad/dl/verify-E1/`. Text extracts are in `scratchpad/txt/verify-E1/` (raw, plus column-aware copies in `cols/`). Scripts are in `scratchpad/scripts/verify-E1/` (`build_verified.py` rebuilds the verified CSV).
- I wrote down my own revenue, EBIT and organic growth values for every report (current and comparative columns, Orkla Foods and BCG, plus the Q4 2005 sub-segments) before opening the CSV values. I then compared them field by field in code.
- I checked every row, all 44 comparative rows and all 6 `derived_from_ytd=true` rows.

## Result summary
- **Numbers:** all 88 rows match my re-extraction exactly for revenue, EBIT and computed margin (to within 0.01pp). All 17 stated OG values match, and all 6 YTD derivations reproduce.
- **Units:** NOK million throughout. The Q4 2004 Norwegian table uses "." as the thousands separator (12.711 = 12,711), and it was read correctly.
- **No value corrections were needed.** 9 rows got note corrections (wrong statements in `notes`), and 3 rows got an added OG value.
- **Status counts:** confirmed 76, corrected 9 (notes only), added 3 (OG field).

## Discrepancies and changes

### D1. BCG 2004 comparatives in the 2005 reports: "revenue unchanged" is false (4 rows corrected, notes only)
These are rows 2004Q1-Q4 BCG from the Q1, Q2, Q3 and Q4 2005 reports. Their notes said "NGAAP figure printed in the 2004 report differs; revenue unchanged". That is true for Orkla Foods, but not for BCG.

| Quarter | Original NGAAP report (rev / EBITA) | IFRS comparative in 2005 report (rev / EBIT) |
|---|---|---|
| Q1 2004 | 6,228 / 482 (Q1 2004 report p.3) | 6,241 / 446 (Q1 2005 report p.3) |
| Q2 2004 | 6,170 / 600 (Q2 2004 report p.3) | 6,190 / 630 (Q2 2005 report p.3) |
| Q3 2004 | 6,130 / 580 (Q3 2004 report p.3) | 6,146 / 596 (Q3 2005 report p.3) |
| Q4 2004 | 6,954 / 855 (Q4 2004 report p.3, "Merkevarer") | 6,975 / 814 (Q4 2005 report p.4) |

The revenue difference comes from Orkla Media's IFRS restatement: Q1 2004 Media revenue went from 1,970 to 1,983, and FY 2004 from 8,210 to 8,280 (Q1 2004 p.3 vs Q1 2005 p.3). The values in the CSV are correct; only the note was wrong.

### D2. Q4 2005 sub-segment notes (5 rows corrected, notes only)
- **2005Q4 Orkla Foods Nordic and Orkla Foods International (current):** the notes had a copy-pasted remark ("Printed label 'Orkla Foods Ingredients' ...") that belongs only to the Ingredients row. I removed it.
- **2004Q4 Nordic, Ingredients and International (comparatives):** the notes said "NGAAP figure printed in the 2004 report differs". No NGAAP sub-segment figures were ever printed. The Q4 2004 report p.3 shows Orkla Foods as a single line. I replaced the note.
- The values themselves (Nordic 2,455/327, Ingredients 737/51, International 356/18, eliminations -67) match Q4 2005 p.4. They also match the 3 Feb 2006 historic-quarterly xls entries in `restatements.csv`.

### D3. Organic growth for 2005Q1-Q3 was missing (3 rows, OG added)
- The Q4 2005 report p.3 gives underlying growth of -1% for Q4 and -2% for FY2005. Weighted by 2004 revenue, 9M 2005 = (-2% x 12,711 + 1% x 3,481) / 9,230 = **-2.4%**.
- I put -2.4 into 2005Q1, Q2 and Q3 with `og_source=derived` and `derived_from_ytd=true`, and an explicit `og_metric` saying it is a 9M average with no quarterly split.
- The value is very approximate. Rounding of the inputs alone gives a range of about -3.3 to -1.5.
- It is consistent with Q1 2005 p.2 ("adjusted for new business and negative currency translation effects, revenues were slightly lower"). The Q2 and Q3 2005 reports (p.2) give only "increase largely ascribable to structural growth". Q2 2005 p.1 says BCG underlying growth year to date was on a par with last year.
- Users who want only published quarterly numbers should filter on `verify_status=added`.

### D4. 2001Q1 and 2001Q2 OG may be on mixed bases (flagged, values kept)
- **The Q1 2001 +5% may not be FX-adjusted.** The release (p.2, English and Norwegian) says "for continuing business" with no currency adjustment. The H1 2001 figure in the Q2 2001 report p.2 is explicitly "adjusted for exchange rate effects" (+1.6%).
- **The internal arithmetic points the same way.** Reported Q1 revenue grew 2,487 to 2,706 (+8.8%). The H1 data imply a structural effect of about +3.5pp: H1 reported +1.5% and FX-adjusted +1.6%, while SEK was about 8% weaker on average in H1 (p.2) and about 45% of sales were in Sweden (Q3 2001 p.2). That fits Q1 only if the 5% excludes FX. In that case FX-adjusted Q1 was roughly +7 to +8%.
- **Q2 2001 derivation.** The value (1.6% x 5,317 - 5% x 2,487) / 2,830 = -1.4 reproduces. A basis-consistent estimate is about **-3.4%** (range about -4.5 to -1.4).
- I kept the extractor's values, because they are what the documents support directly. Both rows carry an "OG CAVEAT" in `verify_note`. Treat 2001Q2 -1.4 as an upper bound.

### D5. Sensitivity notes added to the other derived OG rows (values confirmed)

| Quarter | Value | Inputs and range |
|---|---|---|
| 2001Q3 | +2.5 | 9M "just under 2%" (Q3 2001 p.2) gives +2.2 to +2.6 |
| 2001Q4 | +4.1 | FY "approximately 2.5%" (Q4 2001 p.2) gives +3.4 to +5.1 |
| 2002Q3 | +1.0 | 9M 2% (Q3 2002 p.2); Q1 approx. 4% (Q1 2002 p.2); Q2 approx. 1% (Q2 2002 p.2). The FY2002 +2% (AR 2002 Orkla Foods section; Q4 2002 p.2) reproduces |
| 2004Q2 | -1.8 | H1 1% (Q2 2004 p.2) gives -2.7 to -0.8 |
| 2004Q3 | -1.9 | 9M "on a par" (Q3 2004 p.2) gives -4.2 to +0.5. The negative sign is supported by the Q3 2004 group text (p.2): weaker Swedish sales, only partly offset by Stabburet |

## Checks that passed (no change)
- **Current Orkla Foods values for all 20 quarters**, revenue / EBIT in NOK million (tables on p.3; p.4 for Q1 2001 and Q4 2005):

  | Year | Q1 | Q2 | Q3 | Q4 |
  |---|---|---|---|---|
  | 2001 | 2,706 / 128 | 2,691 / 175 | 2,682 / 204 | 3,054 / 284 |
  | 2002 | 2,688 / 167 | 2,641 / 185 | 2,692 / 239 | 3,041 / 311 |
  | 2003 | 2,663 / 144 | 2,898 / 241 | 2,973 / 286 | 3,379 / 359 |
  | 2004 | 3,112 / 205 | 3,006 / 241 | 3,112 / 320 | 3,481 / 412 |
  | 2005 | 3,154 / 181 | 3,310 / 280 | 3,324 / 319 | 3,862 / 433 |

- **Quarterly sums equal the printed full-year and YTD figures:**

  | Year | Basis | Revenue | EBIT |
  |---|---|---|---|
  | 2000 | comparatives | 11,039 | 787 |
  | 2001 | after goodwill amortisation | 11,133 | 791 |
  | 2001 | EBITA restated in 2002 | 11,133 | 952 |
  | 2002 | EBITA | 11,062 | 902 |
  | 2003 | EBITA | 11,913 | 1,030 |
  | 2004 | NGAAP | 12,711 | 1,178 |
  | 2004 | IFRS | 12,711 | 1,164 |
  | 2005 | IFRS | 13,650 | 1,213 |

  H1 and 9M columns reconcile in every report.
- **Comparatives match the originally reported figures, with each difference explained:**
  - 2001 EBIT was restated in the 2002 reports to EBITA (before goodwill amortisation): 128 to 169, 175 to 215, 204 to 244, 284 to 324. That is about 40 per quarter of goodwill amortisation, a definition change.
  - The 2002 and 2003 comparatives equal the originals exactly.
  - 2004 EBIT was restated to IFRS in the 2005 reports: 205 to 200, 241 to 258, 320 to 310, 412 to 396. Orkla Foods revenue is unchanged.
  - The 2005 values reappear unchanged as comparatives in the Q1-Q4 2006 reports (3,154/181, 3,310/280, 3,324/319, 3,862/433).
  - BCG 2003 comparatives were restated in the 2004 reports to exclude Orkla Beverages. For example, Q1 2003 went from 8,358/364 to 5,512/373, and 373 = Foods 144 + Brands 213 + Media 16.
- **Stated OG values match the text** (p.2 of each report; p.3 for Q4 2005):
  - Q1 2002 approx. +4 (constant FX); Q2 2002 approx. +1 (local currency); Q4 2002 +2.
  - 2003: Q1 -3, Q2 +3, Q3 +1, Q4 +1.
  - Q1 2004 +4; Q4 2004 -1 (Norwegian: "underliggende nedgang på 1 %").
  - Q4 2005 -1.
  - The cross-checks hold: 2003 H1 on a par and 9M on a par, FY +1 (AR 2003); FY2004 on a par (AR 2004; Q4 2004 p.2).
- **Signs and magnitudes against reported revenue growth** are plausible given the described FX and acquisitions:
  - Q4 2003: reported +11.1% vs underlying +1% (Credin consolidated from 1 Jan 2003, per Q3 2002 p.2; weaker NOK).
  - Q1 2004: +16.9% vs +4% (Bakehuset, SEK strength).
  - Q4 2005: +10.9% vs -1% (SladCo).
- **Units and labels:**
  - The labels match: "Operating profit" (2001); "Operating profit before goodwill amortisation" (2002-2004); "Driftsresultat før goodwillavskrivninger" (Q4 2004); IFRS "before intangibles / amortisation and other revenues and expenses" (2005).
  - The only printed margin, H1 2001 7.1% (7.4%), is on Q2 2001 p.2.
  - Sub-segments sum to the total: 2,444 + 795 + 701 - 78 = 3,862, and 307 + 58 + 68 = 433.
- **Driver notes:** I spot-checked the driver notes against the text and confirmed them. Examples: SEK -8% in H1 2001 (Q2 2001 p.2); FX NOK -6m in Q2 2002 and about NOK -10m in H1 2002 (press release p.2); FUN Light and about 600 man-years (Q3 2003 p.2); about 700 man-years (Q4 2003 p.2); Grandiosa +70%, Bakehuset and about 850 man-years (Q1 2004 p.2); EU enlargement purchasing costs (Q2 2004 p.3); KåKå and Odense Marcipan (Q4 2005 p.3).
- **Report URLs:** all 20 point to the files I downloaded. The Q4 2004 English link serves the Norwegian report (same md5 as the Norwegian link).

## Not fillable
- Price/mix, volume, and percentage FX or structural effects for Orkla Foods are never published in 2001-2005 reports or annual reports.
- No presentations for this era are in the manifest. web.archive.org was unreachable through the proxy (connection closed), and a web search found nothing.
- I did not add 2005Q1-Q3 sub-segment rows. They exist only as comparatives in the 2006 reports and are already in `era_E2.csv`: Q1 2005 Nordic 2,059/151, Ingredients 622/18, International 537/12. The 2004Q1-Q3 sub-segment values exist in the 3 Feb 2006 xls (`restatements.csv`).
