# Verification log: era E6 (2022Q1 to 2026Q2), Orkla Foods quarterly extraction

Verifier label: verify-E6. Input: `era_E6.csv` (104 rows) and `era_E6_notes.md`. Output: `era_E6_verified.csv`, which has the same 21 columns plus `verify_status` and `verify_note`.

## Method
1. I downloaded all 18 English quarterly reports myself, Q1 2022 to Q2 2026, using the manifest URLs on orkla.com. I also downloaded:
   - the Q1 2021 to Q4 2021 reports, to check the 2021 comparatives against the original figures;
   - the presentations for Q1 2022 to Q1 2023 and Q2 2024.
2. I re-extracted every number before looking at any CSV value. This covered both the current and the comparative columns of each report, for Orkla Foods (old definition), Orkla Foods Europe / Orkla Foods, Orkla India and BCG/CPC. Sources:
   - business-area / portfolio-company KPI tables;
   - Note 2/3 segments;
   - APM tables: organic growth (FX and structure) and EBIT (adj.) margin.

   I then compared the two extractions field by field, by script.
3. Arithmetic and consistency checks: margin vs EBIT/revenue; OG + FX + structure vs the printed total; printed total vs revenue growth computed from the report's own columns; price + volume/mix vs OG; four quarters vs the printed FY; each comparative vs the originally published figure.
4. I checked the secondary claims in `notes` and `drivers_note` by text search in the reports: contribution ratio, reported EBIT, underlying EBIT growth, government grants, tonnage growth and structure items.

Page numbers below are PDF page indices. They equal the printed page numbers.

## Result summary
- **104 of 104 rows: all numeric fields confirmed exactly.** The fields are revenue, EBIT (adj.), margin, organic growth, price, volume/mix, FX and structure.
  - No numeric value was changed and no row was added.
  - Every quarter 2022Q1 to 2026Q2 has a current row for the main food segment. Organic growth is present in all of them.
- **3 rows corrected (notes text only):** rows 0 and 1 (Q1 2022 report) and row 50 (Q2 2024 report, Orkla Foods Europe).
- `derived_from_ytd=false` everywhere is correct. Every report prints a stand-alone quarter column, including the Q4 reports ("1.10.–31.12.") and Q2 2026 ("Second quarter", first column).
- **Contribution ratio, reported EBIT and underlying EBIT (adj.) growth in `notes`:** all 52 food and India rows that carry them were checked against the KPI tables, and all match.
- **Page references** were checked for all 18 reports: the KPI table, note and APM pages are correct.
  - Presentation pages were checked for Q1 2022 to Q1 2023 (p15/p15/p21+p23/p16+p17/p15+p16) and for Q2 2024 India (p19). All correct.

## Discrepancies found in CSV cells (corrected in `era_E6_verified.csv`)

| # | Row | Field | Old | New | Evidence |
|---|---|---|---|---|---|
| 1 | 0 (2022Q1, Q1 2022 report, Orkla Foods current) | notes | "...last report before India carve-out..." | "...one of the two last reports (Q1 and Q2 2022) on the old definition; India carve-out reported from the Q3 2022 report..." | The Q2 2022 report p11 still prints old-definition Orkla Foods (4,957/480). The Q3 2022 report Note 1 (p22) says the carve-out was implemented "as from the third quarter of 2022". |
| 2 | 1 (2021Q1, Q1 2022 report, Orkla Foods comparative) | notes | same phrase | same replacement | same as row 0 |
| 3 | 50 (2024Q2, Q2 2024 report, Orkla Foods Europe current) | notes | "structure = Blomberg's Glogg and Fruta Podivin divestments" | "structure (-1.6%) = per the Q2 2024 report APM text (p.33) the loss of the Tropicana and Alpro distribution agreements; Blomberg's Glogg and a Czech company (Fruta Podivin) were sold in May 2024 (p.25-26) but are named as structure only from the Q3 2024 report (p.33)" | Q2 2024 report p33: "Adjustments were also made for the loss of distribution agreements with Tropicana and Alpro in Orkla Foods Europe" (no Blomberg's or Fruta Podivín). Q3 2024 report p33 adds "divestment of Fruta Podivín, the brand Blomberg's". Blomberg's Gløgg had about NOK 12m of 2023 revenue (Q2 2024 report p26), so the -1.6% is mainly the distribution losses. |

## Discrepancies in the extractor's notes and summary (not CSV cells; reported, not edited)
1. **"All printed margins within 0.05pp except the India Q3 margins" is slightly overstated.** Two more printed margins round inconsistently with EBIT/revenue. Printed values were kept, which is correct.
   - Orkla Foods Q4 2025: printed 12.8%, but 718/5,633 = 12.75% (Q4 2025 report p10; APM margin table p36 also shows 12.8).
   - Orkla India Q4 2024: printed 13.3%, but 102/770 = 13.25% (Q4 2024 report p14; repeated as a comparative in the Q4 2025 report p14).
2. **The list of CPC vs BCG differences is incomplete. "Same FY2022 total" holds for revenue only.** The Q2 2022, Q4 2022 and Q1 2023 differences the extractor listed are confirmed. Also:
   - Q3 2022 EBIT: CPC 1,530 (Q3 2023 report p24) vs BCG 1,528 (Q3 2022 report p22).
   - FY2022 EBIT: CPC 5,416 (Q2 2023 report p26) vs BCG 5,399 (Q4 2022 report p22).
   - Implied CPC Q1 2022 is 12,793/1,283, from H1 26,315/2,520 minus Q2 13,522/1,237 (Q2 2023 report p26). BCG printed 12,791/1,277.
   - These are context rows only.
3. **India Q4 2023 government grant is printed inconsistently by Orkla:** NOK 22m in the Q4 2023 report p13, NOK 23.5m in the Q4 2024 report p14.
   - The notes file lists 22m; `drivers_note` for 2024Q4 India uses 23.5m.
   - Both figures are printed. Treat the grant as about NOK 22–23.5m.
4. **"Price + volume/mix = organic growth in every row" holds only within ±0.1pp rounding.** Five rows are off by 0.1pp:
   - Europe Q3 2023: 9.9 − 5.4 = 4.5 vs OG 4.4 (Q3 2023 report p9; also its comparative in the Q3 2024 report);
   - Europe Q4 2023: 8.8 − 3.8 = 5.0 vs OG 5.1 (Q4 2023 report p9; also its comparative in the Q4 2024 report);
   - India Q2 2025: −3.2 + 1.9 = −1.3 vs OG −1.4 (Q2 2025 report p13).
5. Confirmed oddities the extractor already flagged:
   - India Q3 margin quirks: 16.2 vs 16.30, 17.1 vs 17.19, 16.1 vs 16.18.
   - India Q4 2023 printed total growth 17.6% vs 784/665 = 17.89% (Q4 2023 report p33).
   - Q3 2022 report p32 prints India 9M 2021 as "6.6 | 58.8 | −15.5 | 49.9", so FX and structure look transposed.
   - Q4 2025 India reported EBIT 69 includes the NOK 27m Labour Codes charge (p14).

## Consistency checks performed (all passed unless noted)
- **Margin vs EBIT/revenue, all rows with a printed margin:** within 0.05pp, except the five India Q3 cases and the two Q4 cases in item 1 above.
  - BCG/CPC margins are computed (`margin_computed=true`).
  - From the Q2 2023 report, CPC margins are also printed in the APM margin table, and the printed values agree with the computed ones after rounding.
- **OG + FX + structure vs printed total:** within 0.15pp in all 104 rows.
- **Printed total vs revenue growth from the same report's current and comparative columns:** within 0.15pp, except India Q4 2023 (0.3pp; rounding).
- **Four quarters vs printed FY (revenue/EBIT):**

  | Segment | Year | Sum of quarters (revenue / EBIT) |
  |---|---|---|
  | Orkla Foods Europe | 2022 | 17,820 / 1,973 |
  | Orkla Foods Europe | 2023 | 20,319 / 2,259 |
  | Orkla Foods | 2024 | 20,594 / 2,532 |
  | Orkla Foods | 2025 | 20,864 / 2,621 |
  | Orkla India | 2022 | 2,542 / 303 |
  | Orkla India | 2023 | 2,947 / 386 |
  | Orkla India | 2024 | 3,106 / 463 |
  | Orkla India | 2025 | 2,981 / 486 |
  | BCG | 2022 | 55,402 / 5,399 |
  | CPC | 2023 | 65,916 / 6,432 |
  | CPC | 2024 | 68,768 / 7,381 |
  | CPC | 2025 | 71,219 / 7,856 |

  Old-definition Orkla Foods H1 2022: 4,788 + 4,957 = 9,745 and 531 + 480 = 1,011, matching the printed H1 (Q2 2022 report p11).
- **Comparatives vs the originally published figure:**
  - 2021 comparatives in the 2022 reports vs the original 2021 reports:
    - Orkla Foods Q1 2021 4,299/507/11.8%/−4.7/−1.3/−0.9 (Q1 2021 report p7 and APM): identical.
    - Orkla Foods Q2 2021 4,465/517/11.6%/3.0/−5.9/5.9 (Q2 2021 report p8 and APM): identical.
    - BCG Q1 to Q4 2021 (11,276/1,288, 11,532/1,240, 12,914/1,695, 13,482/1,571, with OG, FX and structure): identical.
  - Europe Q3 2021 (4,312/652) and Q4 2021 (4,578/663), and India Q3 2021 (545/66) and Q4 2021 (561/66), are restatements from the India carve-out. Europe + India equals the original old-definition Q3 2021 4,857/718 and Q4 2021 5,139/729 exactly (Q3 and Q4 2021 reports, p7).
  - Europe Q1 2022 (4,239/469, OG 7.3) and Q2 2022 (4,318/405, OG 10.4) vs the originally published old-definition 4,788/531 (OG 7.2) and 4,957/480 (OG 11.6): the difference is the definition change (India carve-out). Europe + India equals the old definition: 4,789 vs 4,788 printed, and 4,956 vs 4,957 printed (rounding).
  - All 2023–2026 comparatives with the same scope are identical to the original current figures. The only difference is that the price/volume split was added from the Q2 2023 report, or dropped for India from the Q3 2025 report.
  - CPC vs BCG differences: see item 2 above.
- **Units:** NOK million throughout. No billion or thousand mix-ups.
- **Labels:** checked against the reports.
  - "Orkla Foods" (old definition) in the Q1 and Q2 2022 reports.
  - "Orkla Foods Europe" in the Q3 2022 to Q3 2024 reports.
  - "Orkla Foods1" in the Q4 2024 report, with the footnote "simplified its name to Orkla Foods effective from February 2025" (p10).
  - "Orkla India".
  - "Branded Consumer Goods" in the Note 2 total excluding HQ.
  - "Consolidated Portfolio Companies" in Note 2/3. It is printed in lowercase as "Consolidated portfolio companies" in the 2026 APM tables.
  - The organic-growth labels match the extractor's description.

## Missing fields: search and outcome
- **Organic growth:** none missing. It is printed for every food and India row, current and comparative.
- **Price and volume/mix split for the current rows 2022Q3, 2022Q4 and 2023Q1:** not printed in the quarter's own report. The values are already in the CSV as comparative rows from later reports:

  | Quarter | Source report | Orkla Foods Europe (price / volume/mix) | Orkla India (price / volume/mix) |
  |---|---|---|---|
  | 2022Q2 | Q2 2023 | 7.4 / 3.0 | 10.3 / 10.7 |
  | 2022Q3 | Q3 2023 | 13.6 / −9.4 | 14.4 / 5.7 |
  | 2022Q4 | Q4 2023 | 13.9 / −6.7 | 17.9 / −6.7 |
  | 2023Q1 | Q1 2024 | 15.2 / −4.9 | 17.2 / 0.4 |

  I did not copy these into the current-vintage rows, to keep the vintages separate. The `verify_note` of each affected current row points to them.
- **2022Q1 Orkla Foods Europe price and volume/mix:** never printed in the quarterly reports or the presentations. The presentations only describe it qualitatively.
  - The 15 Jun 2023 "Historical Financial Information" page (investors.orkla.com/English/resources/Historical-Financial-Information/) now redirects to orkla.com/investors/ and no file is linked. The orkla.com "Key financials" page has group-level data only.
  - **Approximate derivation, not added to the CSV:** from H1 2022 (price 5.9, volume/mix 2.9; Q2 2023 report p10) and Q2 2022 (7.4 / 3.0), using H1 2021 base weights (Q1 2021 ≈ 4,033 and Q2 2021 ≈ 3,968 on the Europe definition), Q1 2022 works out to roughly price 4.4 and volume/mix 2.8. That sums to 7.2, against a printed OG of 7.3.
- I did not add the old-definition values after 2022Q2 (Europe + India: 2022Q3 5,029/619, 2022Q4 5,588/646), because they are derived, not printed. I confirmed the arithmetic.

## Not fully verified
- Qualitative `drivers_note` text was spot-checked rather than checked exhaustively; about 20 statements were checked and all were supported. Examples: CZ ERP go-live, North America tariffs, mackerel/meat/dairy costs, ketchup recall about NOK 25m, GST 2.0, the Q2 2024 India volume/mix of 6.7% excluding the grant (presentation p19), and tonnage growth of 7.7/10/2.2/1.7%.
- Presentation page references for the Q2 2023 to Q2 2026 reports were not checked, except Q2 2024 India.
