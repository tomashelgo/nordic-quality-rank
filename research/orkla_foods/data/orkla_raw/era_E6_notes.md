# Era E6 (2022Q1–2026Q2): Orkla Foods quarterly extraction notes

These notes go with `era_E6.csv`. The CSV has 104 rows: 18 reports x 2 vintages (current, comparative) x 2–3 segment labels.
- Main food segment: `Orkla Foods` (old definition), then `Orkla Foods Europe`, then `Orkla Foods` (renamed).
- `Orkla India`, from the Q3 2022 report onwards.
- Parent context row: `Branded Consumer Goods`, then `Consolidated Portfolio Companies`.

## Sources used
- All 18 English quarterly reports from Q1 2022 to Q2 2026, plus the matching investor presentations. Links are taken from the manifest; the report URLs are in the CSV. Nothing was missing from the manifest.
- The annual reports 2022–2025 were downloaded but not needed: every quarter, including Q4, is printed as a separate quarterly column ("1.10.–31.12." or "Fourth quarter"). **No figures were derived from YTD** (`derived_from_ytd=false` everywhere).
- No Excel quarterly-figures files exist for this era. The primary sources are the PDF tables, cross-checked against the presentation key-figure slides:
  - the business-area or portfolio-company table (revenue, EBIT (adj.), margin, organic growth, and from Q2 2023 also price and volume/mix);
  - Note 2 "Segments" (Note 3 from Q1 2025);
  - the APM table "Organic growth by business area/portfolio company" (organic, FX and structure, which add up to total growth).
- `page_ref` uses the printed page numbers, which equal the PDF page index in all 18 reports.

## Segment definitions (what each label includes)
| Label in report | Reports (own quarter) | Scope |
|---|---|---|
| **Orkla Foods** (old def.) | Q1 2022, Q2 2022 | Orkla Foods Norge/Sverige/Danmark/Finland/Baltics, Central Europe (CZ/SK, AT, HU …) **plus India**: MTR, and Eastern Condiments 67.8% from 1 Apr 2021. Same definition as era E5. Exit from Russia (Hamé Foods ZAO) in Q1 2022 is treated as structure. |
| **Orkla Foods Europe** | Q3 2022 – Q3 2024 | Old Orkla Foods **excluding Orkla India**. Orkla India became a separate business area on 11 Apr 2022, reported from the Q3 2022 report (Q3 2022 Note 1). Scope unchanged by the 2023 portfolio-company model (FY2022 = 17,820 in both old and new structure). |
| **Orkla Foods** (renamed) | Q4 2024 – Q2 2026 | Same scope as Orkla Foods Europe. The Q4 2024 report footnote says: "Orkla Foods Europe simplified its name to Orkla Foods effective from February 2025". Comparatives are identical to the Europe figures (Q4 2023 5,504/635; FY2024 20,594). |
| **Orkla India** | Q3 2022 – Q2 2026 (context rows) | MTR + Eastern; the two merged on 1 Sep 2023 (minority 9.99%, so Orkla held 90%). Orkla India IPO on BSE/NSE on 6 Nov 2025: Orkla sold 15% and now owns 75%. Still fully consolidated. |
| **Branded Consumer Goods** | Q1 2022 – Q1 2023 | Note 2 total **excluding HQ/Eliminations**, matching era E5. Comprises the food business areas, Confectionery & Snacks, Care, Food Ingredients and Consumer Investments. |
| **Consolidated Portfolio Companies** | Q2 2023 – Q2 2026 | Successor to BCG under the new operating model (1 Mar 2023, reported from Q2 2023). It is the Note 2/3 total **excluding "Headquarters & Business Services"** (later "Orkla ASA & Business Services"). FY2022 equals BCG FY2022 (55,402), but single quarters differ slightly because of the HQ reallocation: Q2 2022 13,522/1,237 vs BCG 13,524/1,232; Q4 2022 EBIT 1,366 vs 1,362; Q1 2023 15,754/1,473 vs 15,755/1,470. Includes Lilleborg until May 2024 and Pierre Robert until Q1 2025. |

### Splicing the food series across the 2022 break
- Old Orkla Foods = Orkla Foods Europe + Orkla India. This holds exactly:
  - Q1 2022: 4,239 + 550 = 4,789 (printed 4,788); EBIT 469 + 62 = 531.
  - Q2 2022: 4,318 + 638 = 4,956 (printed 4,957); EBIT 405 + 75 = 480.
  - FY2021: 16,891 + 1,869 = 18,760; EBIT 2,243 + 228 = 2,471.
- The old definition is **not printed** for 2022Q3 onwards. If a long series on the old definition is needed, it can be derived as Europe + India:
  - 2022Q3: 5,029 / 619 (12.3%)
  - 2022Q4: 5,588 / 646 (11.6%)
  - FY2022: 20,362 / 2,276

  These derived values are not in the CSV.
- Europe-only figures overlap with the old definition for these periods:
  - 2021Q3 and 2021Q4 (Q3/Q4 2022 reports);
  - 2022Q1 (Q1 2023 report);
  - 2022Q2 (Q2 2023 report);
  - H1 2021 (only as 9M 2021 − Q3 2021 = 12,313 − 4,312 = 8,001).

  Single quarters Q1 2021 and Q2 2021 on the Europe definition were never published in the quarterly reports.
- For a definition-consistent y/y series:
  - Use the "comparative" rows: each report prints the prior-year quarter on the report's own definition.
  - Use the organic growth printed for the Europe definition. Q1 2022 organic growth is 7.3% on the Europe definition vs 7.2% on the old one; Q2 2022 is 10.4% vs 11.6%.

## Metric definitions and changes
- **EBIT measure: "EBIT (adj.)"** throughout 2022–2026, in the business-area/portfolio-company tables and in Note 2/3. It is operating profit before "other income and expenses" (M&A and integration costs, restructuring, write-downs, gains or losses on disposals). The label and definition did not change.
  - From the Q2 2023 report, **reported "EBIT"** (after other income/expenses) is also printed per portfolio company. It is recorded in the `notes` column, e.g. Orkla Foods Q4 2025: EBIT (adj.) 718 vs EBIT 569.
- **EBIT margin:** "EBIT (adj.) margin" is printed for current and comparative columns in every food and India table. All printed margins match EBIT/revenue within 0.05pp, except the Orkla India Q3 margins (see Oddities). The BCG/CPC context-row margins are computed (`margin_computed=true`).
- **Organic growth labels:**
  - "Organic revenue growth" in business-area tables, Q1 2022 – Q1 2023 reports.
  - "Organic growth operating revenues" in portfolio-company tables, from the Q2 2023 report.
  - "Organic growth" in the APM table, used for the BCG/CPC context rows.

  The organic figure in the segment table always equals the APM-table figure.
  - **Definition:** excludes FX translation (current-year revenue at last year's rates) and acquisitions/divestments (12 months).
  - From Q2 2023 the definition is formally stated to also adjust for **material distribution agreements won or lost** and for **intra-group transfers between portfolio companies**. Examples treated as structure for Orkla Foods:
    - PepsiCo/Tropicana loss 2023;
    - internal transfer of plant-based production and part of Idun 2023;
    - Blomberg's Gløgg and Fruta Podivín sold 2024;
    - Quaker (PepsiCo) distribution ended and a small Danish distribution agreement moved to Orkla Food Ingredients in 2026;
    - Põltsamaa factory/brands (Estonia) sold Q2 2026.
- **Price and volume/mix split, from the Q2 2023 report:** "- relating to price" and "- relating to volume/mix", with comparatives back to Q2 2022.
  - Orkla splits organic growth into **price** and **volume/mix**, not price/mix vs volume. In the CSV, `price_mix_pct` holds Orkla's *price* component (net price at unchanged volume) and `volume_pct` holds *volume/mix* (organic growth minus price).
  - Price + volume/mix = organic growth in every row (checked).
  - **Orkla India:** government grants (production-linked incentives) are **booked as mix**, inflating volume/mix in the quarters they fall in: Q3 2023 NOK 6.5m, Q4 2023 22m, Q2 2024 20m, Q3 2024 6.4m, Q1 2025 26m, Q2 2025 6m.
  - From the Q3 2025 report, India's KPIs follow its listed-company reporting. Contribution ratio and the price vs volume/mix split are no longer shown, and "volume growth" is now **tonnage growth**: Q3 2025 7.7%, Q4 2025 10%, Q1 2026 2.2%, Q2 2026 1.7%. Tonnage growth is not a contribution to organic growth, so it is kept in `notes` and `volume_pct` is left empty.
- **FX / structure:** taken from the APM organic-growth table (organic + FX + structure = total; rounding ±0.3pp). In Q2 2022 the Orkla Foods FX cell is printed as "-", recorded as 0.0.
- **New KPIs from Q2 2023, recorded in `notes`:**
  - contribution ratio, i.e. (revenue − variable costs)/revenue, a gross-margin proxy that is useful for the input-cost analysis;
  - underlying EBIT (adj.) growth (excluding FX and structure);
  - underlying margin change;
  - ROCE.
  - Orkla Foods(-Europe) contribution ratio, Q2 2022 → Q2 2026: 37.3, 39.0 (Q3 22), 37.8 (Q4 22), 37.9 (Q1 23), 37.3, 38.4, 38.8, 38.0, 39.8, 40.2, 40.3, 40.2, 39.7, 40.2, 39.7, 40.2, 40.3.
- **IFRS / accounting:** no new standards with a material effect in 2022–2026; IFRS 16 has applied since 2019. Hydro Power is presented as discontinued from Q1 2025, and the segment note was renumbered from Note 2 to Note 3. Neither affects the food rows.

## Restatements noticed
1. **Q3 2022 report: Orkla India carve-out.** 2021 comparatives were restated to the Orkla Foods Europe / Orkla India split. For example, Q3 2021 old-definition 4,857/718 becomes Europe 4,312/652 + India 545/66.
2. **Q1, Q2 and Q3 2023 reports:** first Europe-only figures for Q1 2022 (4,239/469) and Q2 2022 (4,318/405). The Q3 2022 report's 9M 2022 already implied H1 2022 = 8,557.
3. **Q2 2023 report: new operating model.** Orkla Foods Europe figures were not changed. BCG was replaced by Consolidated Portfolio Companies, with small quarterly restatements of the parent total (see table above).
4. **Q4 2024 / Feb 2025: rename only.** No figure changes.
5. Apart from the label changes, **every comparative printed in 2023–2026 equals the originally published figure for the same label** (checked programmatically: revenue, EBIT (adj.), organic growth).

## Sanity checks performed
- Margin vs EBIT/revenue: all within 0.05pp, except the India Q3 cases below.
- Price + volume/mix = organic growth: all rows.
- Organic + FX + structure vs actual revenue growth from the same report's columns: all within 0.25pp, except Orkla India Q4 2023 (printed total 17.6% vs 17.9% computed from rounded revenue).
- Sum of four quarters equals the printed FY figure exactly:
  - Orkla Foods Europe 2022: 17,820 / 1,973. Q1/Q2 are taken from the 2023 comparatives.
  - Orkla Foods Europe 2023: 20,319 / 2,259.
  - Orkla Foods 2024: 20,594 / 2,532.
  - Orkla Foods 2025: 20,864 / 2,621.
  - Orkla India 2022–2025: 2,542/303, 2,947/386, 3,106/463, 2,981/486.
  - BCG 2022: 55,402 / 5,399.
  - CPC 2023: 65,916 / 6,432 (using restated Q1 2023). CPC 2024: 68,768 / 7,381. CPC 2025: 71,219 / 7,856.
- Every quarter 2022Q1–2026Q2 has a `current` row for the main food segment.
- Continuity with era E5: the Q1 2021 comparative in the Q1 2022 report (4,299/507) matches era E5.

## Data gaps and how they were handled
- **No price vs volume/mix split was published before the Q2 2023 report.** Current rows for 2022Q1–2023Q1 therefore have empty price/volume cells. The split for 2022Q2, 2022Q3, 2022Q4 and 2023Q1 is in the comparative rows of the Q2/Q3/Q4 2023 and Q1 2024 reports. Q1 2022 Europe price/volume was never printed in the quarterly reports.
  - The text only says "price-driven growth with weak volumes".
  - The 15 Jun 2023 "historical financial information" file for portfolio companies might contain it, but segment_history.md says it is no longer retrievable.
- Old-definition Orkla Foods (including India) is not printed after 2022Q2; see the splicing section.
- India price/volume split not printed from the Q3 2025 report; tonnage growth is in `notes`.
- No values were invented. Empty cells mean "not printed in that report".

## Oddities
- **Orkla India Q3 margins** are printed about 0.1pp below EBIT/revenue: Q3 2023 16.2% vs 126/773 = 16.30%; Q3 2024 17.1% vs 17.19%; Q3 2025 16.1% vs 16.18%. The values are consistent across reports, so they are probably computed on unrounded figures or include a rounding quirk. Printed values were kept.
- **Q3 2022 report APM table, Orkla India 9M 2021:** FX 58.8 and structure −15.5 look transposed. FY2021 shows FX −14.0 and structure 67.6. This is outside the quarterly columns used here, so it is noted only.
- The Q4 2022 report text says "earlier in 2002" (typo for 2022).
- From Q2 2023 the Orkla India contribution ratio and KPIs refer to a 90%-owned business (75% after the Nov 2025 IPO). Revenue and EBIT (adj.) remain 100% consolidated.
- **Q4 2025 Orkla India:** reported EBIT 69 vs EBIT (adj.) 102, because of a NOK 27m charge for India's new Labour Codes (retirement-benefit wage definition) booked in "other income and expenses".
- **Strong NOK in 2026:** Orkla Foods FX is −3.9% in Q2 2026 and Orkla India FX is −17 to −19%, so reported growth is far below organic growth.
- **Qualitative drivers relevant to the macro analysis** (`drivers_note`):
  - 2022 to Q1 2023: input-cost shock (raw materials, packaging, energy, Ukraine war) with lagging price increases. Margin fell 2–3pp y/y.
  - 2023: price +10–16%, volume/mix −4% to −9%. Reduced purchasing power and trading down to discounters; weak NOK/SEK raised purchasing costs.
  - 2024: cost programmes plus stabilising and then falling net input costs lifted the contribution ratio and margin, while volumes stabilised.
  - 2025–26: renewed input-cost inflation (meat, dairy, marine/mackerel, berries), Norwegian volume weakness, and from Q1 2026 Middle East conflict energy and packaging risk.
