# Orkla Foods quarterly data, era E2 (2006Q1 to 2009Q4): notes

Companion to `era_E2.csv`, which has 144 rows: 16 reports x 4-5 segments x (current + comparative).

## Sources
- I used all 16 English quarterly reports from Q1 2006 to Q4 2009, taken from the manifest at `www.orkla.com/files/...`. None were missing, so I did not need the Norwegian versions or any other fallback. No proxy blocks.
- For Q4 2007 to Q4 2009 the primary source is the Excel file "quarterly(-and-accounting)-figures", sheet `Business areas ...`. I checked every food row in each Excel file against the report PDF's segment table (the appendix up to Q1 2008, then Note 2 Segments on p.13/14). All values match exactly.
- I used the presentations from Q4 2007 to Q4 2009 for printed EBITA margins and organic-growth wording. The manifest has no presentations for Q1 2006 to Q3 2007; those report pages link only the report and a press release.
- I used Annual Report 2007 only for context: the restated FY2006 EBITA for Orkla Foods Nordic.
- Every report shows the quarter and the prior-year quarter side by side, so nothing had to be differenced from year-to-date (YTD) figures. The exceptions are three Q2 2008 organic-growth values; see "Gaps".

## Segment structure (as printed)

| Reports | Food rows captured | Parent / context row |
|---|---|---|
| Q1 2006 | Orkla Foods; Orkla Foods Nordic; Orkla Foods International; Orkla Food Ingredients | "Branded Consumer Goods". **Includes Orkla Media.** |
| Q2 to Q4 2006 | same | "Branded Consumer Goods" excluding Orkla Media. Media was sold to Mecom (agreed July 2006, completed 11 Oct 2006) and reported as discontinued, with comparatives restated. |
| Q1 to Q4 2007 | same | "Orkla Branded Consumer Goods" = Orkla Foods + Orkla Brands - eliminations. |
| Q1 2008 to Q4 2009 | Orkla Foods Nordic; Orkla Brands International; Orkla Food Ingredients | "Orkla Brands" = the renamed Orkla Branded Consumer Goods. Its 2007 comparatives are identical to the old BCG. |

- **Orkla Foods (2006-07)** = Orkla Foods Nordic + Orkla Food Ingredients + Orkla Foods International - "Eliminations Orkla Foods". The eliminations run at about NOK -70m to -105m a quarter and are not captured as rows.
  - Orkla Foods Nordic: Stabburet, Procordia Food, Abba Seafood, Bakers, Beauvais, Felix Abba, Panda.
  - Orkla Foods International: SladCo; Krupskaya from 1 Jul 2006; Poland, Czech Republic, Romania (Royal Brinkers from 1 Jun 2006), Austria, the Baltics; MTR Foods (India) from 1 Apr 2007.
  - Orkla Food Ingredients: Idun, KåKå, Jästbolaget, Odense Marcipan, Credin, Dragsbæk.
- **Q4 2007 is the last report with an "Orkla Foods" segment.** Orkla Branded Consumer Goods was reorganised on 18 Feb 2008 into "Orkla Brands" with four units:
  - **Orkla Foods Nordic** now includes Orkla Foods Baltic, which moved from Orkla Foods International. The Baltic business was about NOK 250m revenue and NOK 20m EBITA in 2007 (Q4 2007 presentation p.59).
  - **Orkla Brands Nordic** = the old Orkla Brands sub-segment (Lilleborg, snacks, biscuits, confectionery, textiles, dietary supplements). It is not captured because it is not part of Orkla Foods.
  - **Orkla Brands International** is roughly the old Orkla Foods International minus the Baltics: Russia, CEE, Austria, India/MTR. Its 2007 quarters were restated, e.g. Q1 2007 484/-22 versus Orkla Foods International at 549/-17.
  - **Orkla Food Ingredients** is unchanged.
- **Naming trap: "Orkla Brands" means two different things.**
  - In 2006-07 it is a non-food sibling sub-segment of Orkla Foods.
  - From 2008 it is the parent business area.
  - The CSV includes "Orkla Brands" rows only for the 2008-09 parent meaning.
- **For 2008-09 the main food series is Orkla Foods Nordic.** There is no "Orkla Foods" total in this period.
  - An approximate old-definition total would be Orkla Foods Nordic + Orkla Food Ingredients + Orkla Brands International - eliminations. Orkla Brands eliminations were NOK -71m to -124m a quarter, but they also include Brands Nordic flows.
  - This is not a clean like-for-like with the 2006-07 Orkla Foods total.
- **Romania moved from Orkla Brands International to Orkla Food Ingredients from Q1 2009.** The 2008 comparatives were **not** restated: Q1 2008 is 526 / 780 in both the 2008 and 2009 Excel files. The 2009 reported y/y figures for Orkla Brands International and Orkla Food Ingredients therefore include this shift.
- Other changes in Orkla Brands International: Kotlin and Elbro (Poland) were sold on 1 Jul 2009, Guseppe (Czech Republic) in Q3 2008, and Superfish (Poland) at the end of 2007.
- **Orkla India:** MTR Foods was acquired in April 2007. It sat inside Orkla Foods International in 2007 and inside Orkla Brands International in 2008-09. It was never reported separately, so there are no "Orkla India" rows.

## EBIT metric (all are EBITA-type; no metric break in substance)
| Reports | Label used in `ebit_metric` |
|---|---|
| Q1-Q4 2006 | Operating profit before amortisation and other revenues and expenses |
| Q1-Q3 2007 | Operating profit before amortisation and other income and expenses. Only the wording changed. |
| Q4 2007-Q3 2008 | EBITA (before amortisation, restructuring and significant impairments). The line "other income and expenses" was renamed "restructuring and significant impairments". |
| Q4 2008 | Operating profit - EBITA (before amortisation, write-down of inventory in Sapa Profiles, restructuring and significant impairments). The Sapa item does not affect food. |
| 2009 | Operating profit - EBITA (before amortisation, restructuring and significant impairments) |

- Items below EBITA that affect food are not in the CSV EBIT column:
  - Q3 2007: Orkla Foods charge of NOK -324m (Romania goodwill, Superfish sale, Polish restructuring). Orkla Foods EBIT for 2007, per the Q4 2007 Excel file: Q1 159, Q2 207, Q3 -79, Q4 379.
  - Q4 2008: Orkla Brands charge of NOK -533m (SladCo goodwill -547m).
  - Q2 2009: NOK -10m on the Kotlin/Elbro sale.
- Food amortisation is negligible: NOK 0-9m a quarter for Orkla Foods.
- IFRS: IAS 34 interim reports throughout. IFRS 8 was adopted in 2009, and the Q4 2009 Note 2 states the segment breakdown did not change. IFRS 16 is not relevant to this era.

## EBIT margins
- **Printed margins**, used as printed (`margin_computed=false`):
  - Orkla Foods, Q4 2007: 9.2% (10.9%), from presentation p.31.
  - Orkla Brands, Q1 2008 (presentation) and Q2 2008 to Q4 2009 (report business-area tables): EBITA margin / "Operating margin (%)".
  - These agree with EBITA/revenue to within 0.05 pp.
- All other margins are computed as EBITA/revenue to 2 decimals (`margin_computed=true`).

## Organic growth
- **Definition:** every report uses "underlying" growth, defined as "excluding acquisitions, divestments and currency translation effects" (footnote 2 or 3). Approximate wording such as "about", "some" or "around" is kept in `og_metric`, and "on a par" / "flat" is recorded as 0.
- **Coverage for the main food series:**
  - Orkla Foods: underlying growth stated for all quarters 2006Q1 to 2007Q4.
  - Orkla Foods Nordic: stated in all quarters except 2006Q4 (not stated) and 2008Q2 (derived; see "Gaps").
  - Q1 2008 Orkla Foods Nordic: the wording is "taking into account acquisitions and disposals, growth was around 6 %", with no explicit FX exclusion.
- **Parent-level growth:**
  - BCG / Orkla Brands: given for 2006Q3, 2006Q4, 2007Q1, 2007Q3 (as "organic growth"), 2008Q1 to Q4, 2009Q1 (presentation says "flat", report says "somewhat lower"), 2009Q3 and 2009Q4.
  - 2007Q2 BCG is derived from the stated underlying revenue decline: NOK -75m / 5,056 = -1.5%.
- **Not stated anywhere in these reports or presentations:** price/mix vs. volume splits in %, and FX or structural effects in % for the food segments.
  - The qualitative drivers are in `drivers_note`. Examples: Q3 2008 growth was "primarily driven by price increases"; Q4 2008 had "volume reductions in all units except Orkla Brands Nordic"; Q4 2009 had a "significantly lower price contribution" and "improved volume/mix".
  - BCG-level structural revenue was stated in NOK: about +150m in Q2 2006, +260m in Q3 2006 and +400m in Q4 2006. These amounts are in `notes`; I did not convert them to %.

## Restatements noticed
1. **Orkla Media removed from BCG.** The Q1 2006 report includes Media in "Branded Consumer Goods": 7,078 / 500, with comparative 6,525 / 439. From the Q2 2006 report onward BCG excludes Media; Q1 2006 restated is 4,878 / 425 (Q1 2007 report). The BCG 2005 comparatives in the CSV therefore mix bases: Q1 includes Media, Q2-Q4 do not.
2. **2007 restated to the 2008 structure** (2008 reports and Excel files):
   - Orkla Foods Nordic quarters, old basis -> restated: Q1 2,145/147 -> 2,207/152; Q2 2,353/214 -> 2,422/219; Q3 2,253/232 -> 2,308/235; Q4 2,540/280 -> 2,611/287. FY 9,291/873 -> 9,548/893.
   - FY2006 Orkla Foods Nordic EBITA restated to 1,074 (Annual Report 2007; no restated 2006 quarters were published). The old basis was 1,057.
   - Orkla Brands International 2007: 484/-22, 501/-52, 528/-30, 749/33.
3. **No other restatements of food figures.** Orkla Foods 2005-2006 quarterly figures are identical across the 2006 reports, the 2007 reports and the Q4 2007 Excel sheet "Business areas 2005-2006". 2008 food figures are identical in the 2008 and 2009 Excel files.
   - Orkla Group totals were restated in several vintages, for example in the Q4 2008 Excel file and when Elkem Energy Trading moved to Orkla Financial Investments from Q3 2009. This does not affect food rows.

## Gaps and how they were handled
- **2008Q2 organic growth for Orkla Foods Nordic, Orkla Brands International and Orkla Food Ingredients.** The report gives only H1 figures (5%, about 14% and about 8%) plus the Q1 figures (about 6%, 10% and about 5%).
  - I implied Q2 by weighting with the 2007 bases, for example Orkla Foods Nordic = (0.05 x 4,629 - 0.06 x 2,207) / 2,422 = about 4%. That gives about 4, 18 and 11.
  - These rows have `og_source=derived` and `derived_from_ytd=true`. Only the growth figure is derived; revenue and EBITA are printed quarterly figures.
  - The rounding uncertainty is about ±1 pp for Orkla Foods Nordic and wider for the small units. **Treat these values with care.**
- **Organic growth missing:**
  - Orkla Foods Nordic 2006Q4.
  - Orkla Foods International in all quarters except 2007Q4.
  - Orkla Food Ingredients 2006Q1 to 2007Q3. 2007Q1 gives only profit growth (+42%).
  - BCG 2006Q1, 2006Q2 and 2007Q4.
  - Orkla Brands 2009Q2: Q2 revenue growth is not stated; underlying EBITA growth for H1 was about 4%.
- **No presentations for 2006 to Q3 2007** in the manifest. I did not search further because the reports cover growth and drivers well.
- **Comparative rows** carry no organic-growth or drivers values, because the reports give these only for the current period.

## Oddities
- Q3 2006: the bullet says "5 % top-line growth for Orkla Foods Nordic", which matches reported growth of +5.4%. The text says underlying growth was 6%, and the CSV uses 6.
- Q4 2008: right after the Orkla Foods Nordic EBITA figure, the text says "The underlying growth in revenue was about 15 %". This is evidently a typo for underlying EBITA growth (about 15%). The CSV uses about 4% underlying revenue growth, as stated earlier in the same paragraph.
- In the Q4 2008, Q1 2009 and Q2 2009 Excel files, the header cell of the 2008 "1.10-31.12" EBIT column contains a stray number (3512). This is cosmetic; the EBITA blocks are correct.
- Underlying EBITA growth is often stated, for example Orkla Foods Nordic 2008Q3 +27% and 2008Q4 about +15%. Where useful it is in `notes`, but there is no column for it.

## Sanity checks performed
- Printed margin vs EBITA/revenue: maximum difference 0.045 pp.
- Four quarters vs printed full year, all exact:
  - Orkla Foods: 2005 13,650/1,213; 2006 14,266/1,278; 2007 14,725/1,000.
  - Orkla Foods Nordic: 2006 9,283/1,057; restated 2007 9,548/893; 2008 9,913/1,050; 2009 9,754/1,088.
  - Orkla Foods International, Orkla Food Ingredients, Orkla Brands International, BCG and Orkla Brands: exact for the years printed.
- Every quarter from 2006Q1 to 2009Q4 has a "current" row for the main food segment (Orkla Foods for 2006-07, Orkla Foods Nordic for 2008-09). Orkla Foods Nordic also has a current row in all 16 quarters, with a definition break at 2008 for the Baltics; use the 2008 reports' restated comparatives to bridge 2007-to-2008 changes.
