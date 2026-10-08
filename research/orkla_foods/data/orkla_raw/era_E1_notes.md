# Era E1 (2001Q1-2005Q4): Orkla Foods quarterly data, notes

Companion to `era_E1.csv` (88 rows, 20 quarterly reports). Each report gives one "current" row for its own quarter and one "comparative" row for the same quarter a year earlier, as printed in that report. Context rows: "Branded Consumer Goods" (BCG) for every report. The Q4 2005 report also has the Orkla Foods sub-segments, which no earlier quarterly report shows.

## Sources
- Quarterly reports from the manifest (orkla.com/files links, the same files as the mb.cision.com mirrors). I used the English versions, except where noted below.
- **Q1 2001:** the manifest has no English quarterly report PDF (page "ORK - First Quarter Results" has no files). I used the English press release with figures, "Positive growth for Orkla" (10 May 2001, 3175493). It has the full segment table (p.4) and an Orkla Foods paragraph (p.2).
- **Q4 2004:** the English page ("Orkla Fourth Quarter 2004", 3174606) links a PDF that is the **Norwegian** report. The cision mirror is byte-identical. I transcribed the figures from the Norwegian tables. Labels: "Driftsresultat før goodwillavskrivninger" means "operating profit before goodwill amortisation", and "Merkevarer" means Branded Consumer Goods.
- Annual reports 2002, 2003 and 2004 have no quarterly segment tables. I used them only for structure, annual underlying growth and "Other revenues and expenses" detail. The manifest has no file for Annual Report 2005.
- No investor presentations from 2001-2005 are in the manifest (the presentation pages have no files), and a web search found none. Price/mix and volume splits for Orkla Foods are therefore **not available** for this era. The reports never quantify them.
- Downloads: `scratchpad/dl/orkla-E1-2001-2005/`. Text extracts and the build script are in `scratchpad/scripts/orkla-E1-2001-2005/` (`build_csv.py` regenerates the CSV).

## Segment definitions (as reported)
- **Orkla Foods (2001-2005):** a business area inside Branded Consumer Goods. It covers Stabburet (NO), Procordia Food (SE), Abba Seafood (SE, incl. Superfish PL until 2003), Beauvais (DK), Felix Abba / Felix Fenno-Baltic (FI and Baltics), Orkla Foods International (CEE: Kotlin PL, Felix Austria, Guseppe CZ, Hungary, Romania from June 2002, SladCo Russia from 1 Jan 2005), Orkla Food Ingredients (Idun, Dragsbæk, KåKå, Credin from 2003, Odense Marcipan, Bæchs from 2005, etc.) and Bakers (NO bread; Bakehuset Norge from Jan 2004).
  - In 2001 about 40-45% of sales were in Sweden. In 2002 about 64% of sales were outside Norway and about 86% in the Nordics.
  - From March 2003 the business was organised as Orkla Foods Nordic, Orkla Foods International, Orkla Food Ingredients and Bakers (AR 2003/2004), but quarterly reports showed one "Orkla Foods" line until Q4 2005.
  - The Q4 2005 report shows three sub-segments: Orkla Foods Nordic, "Orkla Foods Ingredients" (sic; elsewhere "Orkla Food Ingredients") and Orkla Foods International, plus "Eliminations Orkla Foods". Bakers appears to sit inside Orkla Foods Nordic.
  - Sub-segment rows sum exactly to Orkla Foods (Q4 2005: 2,444+795+701-78 = 3,862; 307+58+68 = 433).
- **Branded Consumer Goods (BCG):**
  - 2001-2003: Orkla Foods + Orkla Beverages + Orkla Brands + Orkla Media - eliminations. Orkla Beverages was 40% of Carlsberg Breweries, proportionally consolidated from 2001.
  - From the Q1 2004 report, BCG excludes Beverages (the Carlsberg stake was sold in Q1 2004 and shown as discontinued), and 2003 comparatives were restated.
  - 2005: Foods + Brands + Media. Chips Abp entered Orkla Brands on 1 Mar 2005, and the pro forma comparatives (in notes) include Chips.
  - BCG changes composition, so use it only as context.
- **Orkla India:** not applicable in this era.

## EBIT metric definitions and changes
| Reports | Segment profit measure (label used) | Basis |
|---|---|---|
| Q1-Q4 2001 | "Operating profit" (table; text says "operating profit before other revenues and expenses") | NGAAP. **After goodwill amortisation**, excluding "Other revenues and expenses" |
| Q1 2002 - Q4 2004 | "Operating profit before goodwill amortisation" (EBITA) | NGAAP. Excludes goodwill amortisation and "Other revenues and expenses" |
| Q1 2005 | "Operating profit before intangibles and other revenues and expenses" | IFRS (no goodwill amortisation). Excludes amortisation of intangibles and other rev./exp. |
| Q2 2005 | "Operating profit" with footnote "Before intangibles and other revenues and expenses" | IFRS |
| Q3-Q4 2005 | "Operating profit" with footnote "Before amortisation and other revenues and expenses" | IFRS. Same concept as Q1-Q2 2005 |

- **The 2001-to-2002 switch matters.** The 2002 reports restate 2001 Orkla Foods to EBITA: Q1 169 (vs 128 after goodwill amortisation), Q2 215 (175), Q3 244 (204), Q4 324 (284); FY 952 (791). Implied Orkla Foods goodwill amortisation was about NOK 40m per quarter (161m in 2001).
  - For 2001 vs 2000 y/y you have to use the 2001-report rows (both years after goodwill amortisation).
  - For 2002 vs 2001 use the 2002-report comparatives (both EBITA).
  - The 2000 comparatives exist only on the after-goodwill basis.
- **The NGAAP-to-IFRS switch (2005).** The 2005 reports restate 2004 Orkla Foods to IFRS. EBIT: Q1 200 (NGAAP 205), Q2 258 (241), Q3 310 (320), Q4 396 (412); FY 1,164 (1,178). Revenue is unchanged (3,112 / 3,006 / 3,112 / 3,481).
  - The quarterly profile shifts (Q2 up, Q3/Q4 down), so use the IFRS comparatives for 2005 y/y changes.
  - The reports do not itemise the Orkla Foods-specific IFRS adjustments. Group-level they mention pensions, share-based pay, dividend provisions, Presspublica consolidation (Media) and no goodwill amortisation.
- No other definition changes were seen within the NGAAP 2002-2004 period. Comparatives match previously reported figures exactly.
- IFRS 16 is not relevant here (2019).
- **Margins:** no quarterly Orkla Foods margin is printed anywhere. All `ebit_margin_pct` values are computed (EBIT / revenue, `margin_computed=true`).
  - The only printed margin is in the Q2 2001 text: H1 2001 "operating margin before goodwill amortisation" 7.1% (7.4%). This matches the 2002-restated H1 2001 EBITA 384 / 5,397 = 7.1%.
- **Items excluded from segment EBIT** (booked in "Other revenues and expenses"):
  - Orkla Foods restructuring: NOK -49m in Q2 2002 (SEK 60m Procordia Eslöv), FY2002 total -59m.
  - Improvement programmes: about -50m in Q2 2003 (FY2003 -50m), plus further unspecified Orkla Foods restructuring in Q4 2003.
  - Bakehuset acquisition costs: -35m in Q1 2004.
  - Orkla Foods Öland plant closure: -24m in Q4 2005.

## Organic / underlying growth
- **Labels evolve:**
  - 2001-Q1 2003: "growth for continuing business, adjusted for currency (exchange rate / translation) effects". Q1 2002 says "with currency rates unchanged"; Q2 2002 says "measured in local currency".
  - From Q2 2003: "underlying growth", defined as "excluding acquisitions and divestments and currency translation effects".
  - Effectively the same concept throughout. None of these adjust for Easter timing.
- **Quarter values stated in the text:** Q1 2001 +5 (FX adjustment not stated, so possibly nominal-continuing), Q1 2002 +4, Q2 2002 +1, Q4 2002 +2, Q1 2003 -3, Q2 2003 +3, Q3 2003 +1, Q4 2003 +1, Q1 2004 +4, Q4 2004 -1, Q4 2005 -1.
- **Quarters derived from YTD percentages** (`og_source=derived`, `derived_from_ytd=true`). Formula: Q% = (YTD% x prior-year YTD revenue - sum of earlier quarters' % x their prior-year revenue) / prior-year quarter revenue. The weights are reported prior-year revenue, not the true continuing-business base, so these values are **approximate (about ±1pp or worse)**:
  - Q2 2001: -1.4 (H1 +1.6, Q1 +5; Q1 may not be FX-adjusted)
  - Q3 2001: +2.5 (9M "just under 2%", 1.9 used)
  - Q4 2001: +4.1 (FY "approximately 2.5%")
  - Q3 2002: +1.0 (9M +2)
  - Q2 2004: -1.8 (H1 +1). Range about -2.8 to -0.9 given rounding.
  - Q3 2004: -1.9 (9M "on a par")
- **YTD/FY cross-checks are consistent:**
  - 2002 quarters weight to the reported FY +2%.
  - 2003: H1 "on a par" is consistent with Q1 -3 / Q2 +3, and FY +1 holds.
  - 2004: FY "on a par" is consistent with Q1 +4, the derived Q2/Q3 values and Q4 -1.
- **2005 Q1-Q3: no numeric underlying growth published for Orkla Foods.**
  - Q1 2005: "slightly lower" adjusted for new business and FX, so `og_source=text` with an empty value.
  - Q2 and Q3 2005: only "increase largely ascribable to structural growth".
  - FY2005 underlying was -2% and Q4 -1%, which implies 9M 2005 of about -2.4% (derived, not in the CSV as a quarterly value).
- **FX and structural effects:** not quantified as percentages for Orkla Foods in any report, so those columns are empty. Notes record the reported-vs-underlying gaps where large: Q4 2003 reported +11% vs underlying +1%; Q4 2005 +11% vs -1%; FY2005 +7% vs -2%.
  - Quantified currency effects on EBITA: Q2 2002 -NOK 6m; H1 2002 about -NOK 10m.
  - SEK weakness in 2001 is described (H1 -8%, Q3 -12%, FY -9% on average vs NOK), but its revenue effect is not split out.

## Qualitative drivers (useful for the macro work)
- **2001:** weak SEK (translation, plus higher import/raw material costs for the Swedish units). Raw material price increases from late 2000 were passed on with a lag, largely offset by year-end.
- **2002:** seafood raw material inflation and the Polish recession (Superfish/Abba Seafood). Strong NOK translation drag. Acrylamide scare (marginal impact). Start of cost programmes (Procordia "Lyftet").
- **2003-2004:** margin expansion driven by cost cuts. The NOK 500m programme cut about 1,200 man-years, 15%. Easter timing swings Q1/Q2. Norwegian transport strike in Q2 2004 (NOK 30-40m, Foods+Brands). Growing private label and hard-discount pressure in Sweden and Finland: per the Q4 2003 report, new foreign low-price retailers had entered both countries and would soon enter Norway. EU enlargement raised CEE purchasing costs in 2004.
- **2005:** acquisition-led growth (SladCo from Jan 2005, Spilva from Jul 2004, Romania/Poland deals) with negative underlying growth. Swedish grocery price and discount pressure squeezed Orkla Foods Nordic profit (Q4 Nordic EBIT 307 vs 327). Higher advertising and launches.

## Sanity checks performed
- **Quarterly sums equal the printed full-year figures:**

  | Year | Basis | Revenue (NOK m) | EBIT (NOK m) | Check |
  |---|---|---|---|---|
  | 2000 | comparatives, after goodwill amortisation | 11,039 | 787 | ok |
  | 2001 | after goodwill amortisation | 11,133 | 791 | ok |
  | 2001 | EBITA, 2002 comparatives | 11,133 | 952 | ok |
  | 2002 | EBITA | 11,062 | 902 | ok |
  | 2003 | EBITA | 11,913 | 1,030 | ok |
  | 2004 | NGAAP EBITA | 12,711 | 1,178 | ok |
  | 2004 | IFRS comparatives | 12,711 | 1,164 | ok |
  | 2005 | IFRS | 13,650 | 1,213 | ok |

- YTD columns in every report reconcile with differences of the quarterly columns (e.g. 2001 H1 303 = 128+175).
- Computed margins equal EBIT/revenue for all rows.
- Every quarter 2001Q1-2005Q4 has a "current" row for Orkla Foods. No quarter is missing.

## Oddities and handover notes
- The Q1 2006 report (outside this era) gives Q1 2005 sub-segment comparatives: Nordic 2,059/151, Ingredients 622/18, International 537/12, eliminations -64; total 3,154/181. These are useful for the next era if sub-segment history is wanted.
- From 2006, Orkla Foods keeps the three sub-segments inside Branded Consumer Goods.
- 2005 reports show a "Pro forma" 2004 column (Elkem from 1 Jan 2004, Chips Abp from 1 Mar 2004). For Orkla Foods it equals the IFRS-restated column, so only one comparative row is kept. The BCG pro forma values are in the notes column.
- Carlsberg Breweries' 2002 Danish accounting change affects BCG (Beverages) comparability in Q4 2002, not Orkla Foods.
