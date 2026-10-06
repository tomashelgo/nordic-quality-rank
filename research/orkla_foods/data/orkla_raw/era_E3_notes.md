# Orkla food segment quarterly data, era E3 (2010Q1 to 2013Q4): notes

These notes go with `era_E3.csv`. The CSV has 128 rows: 16 quarterly reports x 4 segment rows x 2 vintages (current and comparative).

**Main food series**
- 2010Q1 to 2012Q4: **Orkla Foods Nordic**.
- 2013Q1 to 2013Q4: **Orkla Foods**, in the new 2013 definition.

**Context rows in every report**
- Parent business area: "Orkla Brands" up to Q1 2012, then "Branded Consumer Goods".
- Orkla Brands International (2010-12), renamed Orkla International in 2013. It contains MTR Foods (India).
- Orkla Food Ingredients. It was part of the pre-2008 Orkla Foods, so era E2 captured it too.

There are no "Orkla India" rows. India (MTR Foods) was never reported as its own segment in this era.

## 1. Sources

| Report | Report PDF (`report_url`) | Excel "quarterly and accounting figures" | Presentation |
|---|---|---|---|
| Q1 2010 | orkla.com/files/Public/19690/3173431/1st-quarter-2010.pdf | …/Public/19690/3173431/quarterly-and-accounting-figures-1-st-quarter-2010.xls | …/Main/19690/3173431/presentation-of-1st-quarter.pdf |
| Q2 2010 | …/Main/19690/3173396/2nd-quarter-2010.pdf | …/Public/19690/3173396/quarterly-and-accounting-figures-2nd-quarter-2010.xls | …/Public/19690/3173396/presentation-of-2nd-quarter-2010.pdf |
| Q3 2010 | …/Public/19690/3173352/3rd-quarter-2010.pdf | …/Public/19690/3173352/quarterly-and-accounting-figures.xls | …/Main/19690/3173352/presentation-of-3rd-quarter-2010.pdf |
| Q4 2010 | …/Public/19690/3175738/4th-quarter-2010.pdf (the "Correction" release) | …/Public/19690/3175738/quarterly-and-accounting-figures-4th-quarter-2010.xls | …/Main/19690/3175738/presentation-of-4th-quarter-2010.pdf |
| Q1 2011 | …/Main/19690/3173210/1st-quarter-2011.pdf | …/Public/19690/3173210/quarterly-and-accounting-figures-1st-quarter-2011.xls | …/Public/19690/3173210/presentation-of-1st-quarter-2011.pdf |
| Q2 2011 | **Oslo Børs NewsWeb** message 286602, attachment 88017: `api3.oslo.oslobors.no/v1/newsreader/attachment?messageId=286602&attachmentId=88017` | NewsWeb attachment 88016 | NewsWeb attachment 88018 |
| Q3 2011 | …/Main/19690/3173108/3rd-quarter-2011.pdf | …/Public/19690/3173108/quarterly-and-accounting-figures-3rd-quarter-2011.xls | …/Public/19690/3173108/presentation-of-3rd-quarter-2011.pdf |
| Q4 2011 | …/Main/19690/3173055/presentation-4th-quarter-2011.pdf. Despite the file name, this is the **report**. The same file is NewsWeb 298104, attachment 83126. | NewsWeb 298104, attachment 83125 | NewsWeb 298104, attachment 83124 |
| Q1 2012 | …/Main/19690/3172937/1st-quarter-2012.pdf | …/Public/19690/3172937/quarterly-and-accounting-figures-1st-quarter-2012.xls | …/Public/19690/3172937/presentation-of-1st-quarter-2012.pdf |
| Q2 2012 | …/Main/19690/3172910/2nd-quarter-2012.pdf | …/Public/19690/3172910/quarterly-and-accounting-figures-2nd-quarter-2012.xls | …/Public/19690/3172910/presentation-of-2nd-quarter-2012.pdf |
| Q3 2012 | …/Public/19690/3172811/3rd-quarter-2012.pdf | …/Public/19690/3172811/quarterly-and-accounting-figures-3rd-quarter-2012.xls | …/Main/19690/3172811/presentation-of-3rd-quarter-2012.pdf |
| Q4 2012 | …/Public/19690/3172765/4th-quarter-2012.pdf | none published | …/Main/19690/3172765/presentation-of-4th-quarter-2012.pdf |
| Q1 2013 | …/Main/19690/3172682/1st-quarter-2013.pdf | none | …/Public/19690/3172682/presentation-of-1st-quarter-2013.pdf |
| Q2 2013 | …/Public/19690/3172614/2nd-quarter-2013.pdf | none | …/Main/19690/3172614/presentation-of-2nd-quarter-2013.pdf |
| Q3 2013 | …/Public/19690/3172569/3rd-quarter-2013.pdf | none | …/Main/19690/3172569/presentation-of-3rd-quarter-2013.pdf |
| Q4 2013 | …/Main/19690/3172504/4th-quarter-2013.pdf | none | …/Public/19690/3172504/presentation-of-4th-quarter-2013.pdf |

**Gaps in the manifest, and how I filled them**
- The 2011 page "2nd Quarter 2011" on orkla.com has no attachments. I got the English Q2 2011 report, Excel file and presentation from NewsWeb (`api3.oslo.oslobors.no/v1/newsreader/message?messageId=286602`).
- For Q4 2011, the orkla.com page links only the report, under a misleading file name. I took the English Excel file and presentation from NewsWeb message 298104.
- No proxy blocks occurred.
- Orkla published no Excel files for Q4 2012 to Q4 2013. For those quarters the report tables and presentations are the only sources.

**Supporting documents** (not quarterly reports)
- 26 Oct 2012, "Restated historical figures for 2011 and 2012" (xls, NewsWeb 314509). It restates the group for continuing operations after the Sapa JV and Borregaard IPO. **Orkla Foods Nordic figures are unchanged.**
- 11 Apr 2013, "Adjusted historical figures for 2011 and 2012" (pdf, NewsWeb 325007, attachment 70232). It gives 2011Q1-2012Q4 in the 2013 structure, after IAS 19R and IFRS 11. These rows are already in `restatements.csv` from the segment-history task, so I did **not** duplicate them in `era_E3.csv`.

**Primary source for amounts**
- 2010Q1-2012Q3: the Excel sheet "Business areas 2009-20xx". I cross-checked every food value against the report text or table and all match.
- 2012Q4-2013Q4: the report segment tables. Q4 2012 Note 2 is on p.12. The 2013 business-area tables are on p.4-7.
- Organic growth, drivers and margins: report text. I used presentations where the report gives no number: 2013 organic growth, FX translation slides, and some printed margins.

## 2. Segment structure (as printed)

| Reports | Main food row | Parent row | Other context rows |
|---|---|---|---|
| Q1 2010 - Q1 2012 | Orkla Foods Nordic | "Orkla Brands" (business area) | Orkla Brands International; Orkla Food Ingredients |
| Q2 2012 - Q4 2012 | Orkla Foods Nordic | "Branded Consumer Goods". Report heading: "The Branded Consumer Goods area". The Q2 2012 Excel still says "Orkla Brands"; from the Q3 2012 Excel it says "Branded Consumer Goods". | same |
| Q1 2013 - Q4 2013 | **Orkla Foods** (new 2013 definition) | "Branded Consumer Goods" | Orkla International; Orkla Food Ingredients |

**Orkla Foods Nordic (2008-2012)**
- Annual Report 2010 lists Stabburet and **Bakers** (Norway), Procordia and Abba Seafood (Sweden), Beauvais (Denmark), **Panda** (Finnish confectionery) and Felix Abba (Finland), and Põltsamaa Felix, Spilva and Suslavicius-Felix (Baltics).
- **Kalev** (Estonian chocolate, acquired 2010, about EUR 28m in sales) was booked here too.
- Bakers was sold with effect from **1 Feb 2012**.
  - The 2011 comparatives in the 2012 reports were **not** restated for this, so reported 2012 y/y revenue falls by roughly 10-14%.
  - Underlying growth excludes the Bakers effect.
- Other small acquisitions:
  - Dagens AS (Stabburet), from 9 Jun 2011.
  - Jokk brand (Procordia), Q3 2012, about SEK 65m.
  - Boyfood (Felix Abba), agreed in 2012, about EUR 18m.
- The 2012 revenue split is in Q4 2012 presentation p.22, read from a chart: Norway ~37%, Sweden ~38%, Finland ~11%, Denmark ~6%, Other ~9%.

**Orkla Foods (2013 definition)**
- It is Orkla Foods Nordic minus confectionery: Panda and Kalev moved to Orkla Confectionery & Snacks. Bakers was already gone.
- From **1 May 2013** it adds Rieber & Søn's Nordic food: Toro, Denja, K-Salat and others.
- Annual Report 2013 lists the companies as Orkla Foods Norge, Orkla Foods Sverige (Procordia and Abba Seafood merged on 1 Apr 2013), Orkla Foods Danmark, Orkla Foods Finland, Põltsamaa Felix, Spilva and Suslavicius-Felix.
- The 2012 revenue split is in Q1 2013 presentation p.25: Norway 40%, Sweden 40%, Finland 8%, Denmark 6%, Baltics 3%, Others 3%.
- Bridge for 2012: Orkla Foods Nordic was 8,569 / 1,161 (old basis, before IAS 19R) and Orkla Foods was 7,972 / 1,144 (restated basis, after IAS 19R).

**Orkla Brands International (2010-12) / Orkla International (2013)**
- 2010-12: Russian chocolate and biscuits (SladCo and Krupskaya, merged into Orkla Brands Russia in Feb 2011), **MTR Foods (India)** and Felix Austria.
- 2013 adds the Rieber units Vitana (Czech Republic), Delecta/Rieber Foods Polska and Rieber Russia.
- These are context rows only. In this era MTR, Felix Austria and Vitana were not in the food segment. They moved into Orkla Foods only from Dec 2014 (see `segment_history.md`).
- Some MTR growth figures from the text:
  - Q2 2013 underlying: India +13.9%, Russia -22.7%.
  - Q3 2013: India +18%, Russia -12%.
  - Q4 2012: MTR +14%.

**Orkla Food Ingredients**: the bakery-ingredients B2B business, a separate unit throughout this era. It is a context row only.

## 3. EBIT metric

All values are **EBITA**: operating profit before amortisation of intangibles and before "other income and expenses". I recorded the exact definitions:
- **Q1 2010**: "Operating result before amortisation, gain on sale of power plants, restructuring and significant impairments". The Q1 2010 Excel shows a separate "Write-downs, restructuring and significant impairment" block.
- **Q2 2010 to Q4 2013**: "Operating profit before amortisation and other income and expenses". The Excel sheets label it "Operating profit (EBITA)".

This is a change in wording only. The Q1 2010 numbers carry straight into later reports, so there is no break.

**Items not included**
- Amortisation for food is negligible: Orkla Brands had NOK 2-12m a quarter in total.
- Other income and expenses below EBITA that hit the food area:
  - Q4 2010: Orkla Brands -231, mainly the write-down of historical Bakers goodwill (NOK -276m). The Hovenäset factory-closure write-down was charged to Abba's profit, i.e. inside EBITA.
  - Q4 2011: -185, mainly the Bakers sale write-down and costs of NOK 155m.
  - Q2 2012: -103 (Russia factory closure, 92).

**IAS 19R and IFRS 11 restatement in 2013.** The 2012 comparatives in the 2013 reports are restated.
- The pension "corridor" approach was removed and the pension finance cost moved to financial items. This **raises EBITA**: by NOK 33m for the group in 2012 (17m in 2011), per NewsWeb 325007.
- Effect on Orkla Foods 2012: 1,114 before restatement (Q4 2012 report, Note 12) versus **1,144** after (Q1 2013 report onwards).
- Effect on Branded Consumer Goods (BCG) comparatives: Q1-12 523→535, Q2-12 587→597, Q3-12 773→784, Q4-12 936→947.
- Effect on Orkla Food Ingredients: +1 to 2 a quarter.
- Orkla International comparatives are unchanged.

Other accounting points:
- IFRS 16 is not relevant to this era.
- Elkem was reclassified as discontinued in Feb 2011, and Sapa/Borregaard/REC in Oct 2012. These change only group totals. The food sub-segment rows were not restated: comparatives equal the earlier reports' current values exactly, which I checked in the CSV.

## 4. Organic growth ("underlying")

The definition in the report footnote is "excluding acquisitions, divestments and currency translation effects", later "excluding acquired and sold operations and currency translation effects".
- The 2013 presentations call it "Organic revenue growth".
- Before Q3 2012 there are no segment tables of organic growth. All values come from the report text (`og_source=text`) unless marked `presentation`.

**Easter adjustments** (the `og_metric` column says which basis each value uses)
- Orkla Foods Nordic: Q1 2010 (-3.3%), Q1 2011 (-1%) and Q2 2011 (+0.2%) are given only on an Easter-adjusted basis.
- Q1 2012 (+5%) is unadjusted. The report says about half of it was due to Easter.
- Parent row: Q1 2010 3% is unadjusted (the adjusted figure is about 1%). Q2 2010 -0.8% and Q2 2011 3.0% are adjusted. Q1 2011 is 0% unadjusted, about 2% adjusted.

**Rieber in 2013 organic growth.** The Q2 2013 presentation gives Orkla Foods organic growth both ex Rieber (-2.3% for Q2, -1.1% for H1) and incl. Rieber pro forma (-4.2% for Q2, -2.3% for H1). The report's "H1 underlying -2%" matches the incl.-Rieber figure, so the CSV uses **-4.2%**.
- Q3 2013 (-3.5%) and Q4 2013 (-6.0%) are single figures. FY2013 is -4.2%.
- **Odd:** the Q3 2013 presentation's "YTD Q3" figure of -3.3% does not reconcile with H1 -2.3% and Q3 -3.5%.

**Missing quarterly organic figures**, left blank:
- **Orkla Foods Nordic 2012Q2.** The report gives H1 +1% (presentation: +0.8%) and Q1 about +5%, which implies Q2 of roughly -3%. That figure is not stated anywhere.
- **Orkla Foods Nordic 2012Q4.** The report says only "small underlying decline", due to fewer selling days.
- BCG 2012Q2 (H1 +1.5%), 2013Q2 (H1 -2%), 2013Q3 ("slightly weaker") and 2013Q4 ("decline").
- Orkla Food Ingredients 2012Q2 (H1 +3%).

**Other organic figures from presentations, not in the CSV**
- Orkla Foods Nordic annual organic growth, from a bar chart in the Q4 2012 presentation p.23. I matched the bars to years by order: 2008 +4%, 2009 -1%, 2010 -4%, 2011 -1%, 2012 +1%. The 2012 figure is +3% adjusted for lost Procordia contract production.
- Half-year underlying change: H1-11 -0.9, H2-11 -0.3, H1-12 +0.8 (Q2 2012 presentation p.11); Q3-11 -0.3 and Q3-12 +4.0 (Q3 2012 presentation p.25).
  - The 2011 values differ a little from the 2011 reports (H1-11 -0.5%, Q3-11 -1%), which suggests a recomputed basis. The CSV keeps the figures as printed in each report.

**Price/mix and volume:** no report or presentation gives numeric price or volume contributions for the food segment in 2010-2013. These columns are blank. Qualitative notes are in `drivers_note`, for example "4% sales growth primarily driven by price increases" at Orkla Brands level in Q3 2011.

## 5. FX translation and structural effects

- **`fx_effect_pct` is derived**: the presentation's "Currency translation effects" (revenue, NOK m) divided by the prior-year quarter's revenue.
  - Orkla Brands / BCG: 2010Q1-2012Q2, at business-area level only up to Q1 2012:
    - 2010: Q1 -152, Q2 -166, Q3 -142, Q4 +35
    - 2011: Q1 +39, Q2 +32, Q3 -86, Q4 -172
    - 2012: Q1 -121, Q2 -124 (sum of segments)
  - **Orkla Foods Nordic:** Q2 2012 -35 (presentation p.33). Q1 2012 -37 is derived as the H1 -72 on the Q2 2012 slide minus Q2. Translation effects on EBITA were -4 and -3.
  - The Q2 2010 presentation labels its FX column "Q1-10", but the values are Q2 2010 (-152 + -166 = H1 -318).
  - No segment-level FX was published for 2012Q3-2013Q4. The group or BCG numbers are mentioned in `notes`: BCG EBITA translation was +20 in Q3 2013 and +50 in Q4 2013.
- **`structural_effect_pct`** is never stated, so it is blank. The main structural items:
  - Bakers out from Feb 2012. The implied residual in Q1 2012 is about -11.8pp: reported -8.4% minus organic +5% minus FX -1.7%. This is noted but not entered.
  - Rieber in from May 2013. It contributed NOK 9m EBITA in May-June 2013 and NOK 71m in Q3 2013.

## 6. EBIT margins

- **Printed, so `margin_computed=false`:**
  - Orkla Brands / BCG business-area tables, all quarters.
  - Orkla Foods, Orkla International and Orkla Food Ingredients 2013 tables.
  - Orkla Foods Nordic Q3 2012 (14.9% vs 11.7%) and Q4 2012 (16.5% vs 13.5%), both from the presentations.
- **Computed, so `margin_computed=true`:** Orkla Foods Nordic in all other quarters, and Orkla Brands International / Orkla Food Ingredients 2010-12. These are EBITA divided by operating revenues, to 2 decimals.
- Presentation charts also print Orkla Foods Nordic annual EBITA margins: 2008 10.6, 2009 11.2, 2010 11.8, 2011 11.4, 2012 13.5. They also print Orkla Foods (2013 definition) quarterly margins: 2012 Q1-Q4 10.6 / 13.5 / 15.8 / 17.0 and 2013 Q1-Q4 11.7 / 11.0 / 14.0 / 14.6.
- Orkla Foods' margin fell in 2013 partly because Rieber diluted it: 1.8pp of the 2.5pp drop in Q2 2013, per presentation p.24.

## 7. Sanity checks performed

- Margin ≈ EBITA / revenue for every row: 0 deviations above 0.15pp.
- The four quarters sum exactly to the printed full year:
  - Orkla Foods Nordic: 9,438/1,115 (2010), 9,496/1,082 (2011), 8,569/1,161 (2012).
  - Orkla Foods 2013: 9,797/1,275.
  - Restated Orkla Foods 2012: 7,972/1,144.
  - Orkla Brands: 23,627/2,967 (2010), 24,621/2,784 (2011).
  - BCG: 24,105/2,819 (2012 as originally reported), 27,731/2,982 (2013).
  - Orkla Brands International / Orkla International: 2,009/40, 2,113/8, 2,133/-5, 2,644/-86.
  - Orkla Food Ingredients: 4,560/268, 5,392/230, 5,435/228, 5,998/288.
- Every quarter from 2010Q1 to 2013Q4 has a `current` row for the main food segment.
- The 2009 comparatives in the 2010 reports equal the era E2 2009 `current` values exactly.
- The 2010-2012 comparatives equal the prior-year `current` values. The only differences are the IAS 19R restatements in the 2013 reports (§3).
- `derived_from_ytd` is false everywhere. Every report prints the quarter itself, either as a column or in the text. Q2 and Q3 reports give quarter figures alongside YTD figures.

## 8. Oddities

- In the Q1 2012 Excel file, the EBITA, amortisation and other-income-and-expenses blocks label the last column's year as "2011". It is actually 1.1-31.3 2012. Header glitch only.
- The Q1 2013 report's Orkla International text still says "Orkla Brands International posted…".
- Orkla International Q4 2013: the report says underlying -12% and the presentation says -11.6%. The CSV uses -11.6. Q3 2013: report -1%, presentation -1.5%; the CSV uses -1.5.
- Q3 2012 Orkla Foods Nordic EBITA includes a NOK 11m property gain at Abba Seafood. The Q3 2013 presentation flags this for comparability.
- In the 2012 reports, "Orkla Brands" is the old name of the parent business area. Do not confuse it with the 2006-07 non-food sub-segment of the same name (see the era E2 notes).
