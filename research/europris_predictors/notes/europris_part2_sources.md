# Europris ASA: quarterly financials, part 2 (2020Q1 to 2026Q2). Sources and definitions

Output: `data/europris_part2.csv` (26 rows, one per quarter from 2020Q1 to 2026Q2). The columns are identical to `europris_part1.csv`, and the definitions continue those of part 1 (see the definitions section below).

All figures come from Europris ASA quarterly reports published on Oslo Børs newsweb (issuer EPR). I also used three presentations and a few stock-exchange notices. I fetched everything with the newsreader API (`list`, `message`, `attachment`) and converted the PDFs with `pdftotext -layout`. I used no other website and did not try any blocked site. Raw downloads stay in the session scratchpad and are not in the repo.

## Scope: when segment reporting starts
- **2020Q1 to 2024Q1: `group_pre_segment`.**
  - The 20% stake in Runsvengruppen AB (ÖoB), bought 13 Dec 2019, was an associate. Its result sits below operating profit, so it is not in any figure here.
  - The group in this period is the Norwegian business: the Europris chain plus the Norwegian pure plays, which are Lunehjem (67%, consolidated from March 2021), Lekekassen (67%, consolidated from August 2021, 100% from Q1 2023) and Strikkemekka (consolidated from July 2022).
  - `norway_revenue_nok_m` therefore equals `group_revenue_nok_m`.
- **ÖoB timeline:**
  - Arbitration award in Europris's favour: 18 Dec 2023 (msg 606982).
  - Decision to exercise the option: 31 Jan 2024 (msg 609555).
  - Share purchase agreement, final price NOK 200.5m: 21 Mar 2024 (msg 614254).
  - Closing: 2 May 2024 (msg 617600).
  - ÖoB is consolidated from **1 May 2024**.
- **2024Q2 onwards: `segment_norway`.** The first report with segments Norway and Sweden is Q2 2024 (msg 623406, published 2024-07-11).
  - Segment Norway = the Europris chain plus the pure plays (note 4: "Lekekassen, Strikkemekka and Lunehjem … are integrated into the Norway segment"). Lunehjem was divested on 2 Jan 2025.
  - Segment Sweden = ÖoB.
- **No separate restatement was needed.** The segment-Norway comparatives printed for 2023 and 2024Q1 are exactly the former group figures; for example, Q2 2023 segment Norway is 2,310 = group 2,310. So the switch in `scope` does not break the series.
  - The "organic" figures in the 2024 reports equal segment Norway.

## Messages and attachments used per quarter

| Quarter | report_message_id (published) | Attachment(s) read | Cross-checks / later sources |
|---|---|---|---|
| 2020Q1 | 501532 (2020-04-23) | Europris_ASA_Q1_2020_report.pdf, _presentation.pdf | Q1 2021 report (531534) comparatives agree. Covid notice 498533 |
| 2020Q2 | 509653 (2020-07-10) | Europris_ASA_Q2_2020_report.pdf, _presentation.pdf | Q2 2021 (538131) agrees. Trading update 508306 (2020-06-18) |
| 2020Q3 | 516777 (2020-10-30) | Europris_ASA_Q3_2020_report.pdf | Q3 2021 (545906) agrees |
| 2020Q4 | 523770 (2021-02-04) | Europris_ASA_Q4_2020_report.pdf, _presentation.pdf | Q4 2021 (552536) and audited FY2020 in 531534 agree |
| 2021Q1 | 531534 (2021-04-29) | Europris_ASA_Q1_2021_report.pdf, _presentation.pdf | Q1 2022 (560306) agrees. Covid notices 523084, 523700, 527864 |
| 2021Q2 | 538131 (2021-07-15) | Europris_ASA_Q2_2021_report.pdf, _presentation.pdf | Q2 2022 (566962) agrees. Lekekassen notice 537165 |
| 2021Q3 | 545906 (2021-11-04) | Europris_ASA_Q3_2021_report.pdf | Q3 2022 (574601) agrees |
| 2021Q4 | 552536 (2022-02-03) | Europris_ASA_Q4_2021_report.pdf | Q4 2022 (581191) prints the same quarterly figures. Audited FY differs slightly (see below) |
| 2022Q1 | 560306 (2022-04-28) | Europris_ASA_Q1_2022_report.pdf, _presentation.pdf | Q1 2023 (588704) agrees |
| 2022Q2 | 566962 (2022-07-14) | Europris_ASA_Q2_2022_report.pdf, _presentation.pdf | Q2 2023 (595225) agrees |
| 2022Q3 | 574601 (2022-11-03) | Europris_ASA_Q3_2022_report.pdf | Q3 2023 (602805) agrees |
| 2022Q4 | 581191 (2023-02-02) | Europris_ASA_Q4_2022_report.pdf, _presentation.pdf | Q4 2023 (609575) agrees |
| 2023Q1 | 588704 (2023-04-27) | Europris_ASA_Q1_2023_report.pdf, _presentation.pdf | Q1 2024 (616738) agrees |
| 2023Q2 | 595225 (2023-07-13) | Europris_ASA_Q2_2023_report.pdf, _presentation.pdf | Q2 2024 (623406) agrees, including the segment-Norway comparatives |
| 2023Q3 | 602805 (2023-11-02) | Europris_ASA_Q3_2023_report.pdf | Q3 2024 (630818) agrees |
| 2023Q4 | 609575 (2024-02-01) | Europris_ASA_Q4_2023_report.pdf | Q4 2024 (637305) agrees |
| 2024Q1 | 616738 (2024-04-25) | Europris_ASA_Q1_2024_report.pdf, _presentation.pdf | Q1 2025 (643362) segment-Norway comparatives agree |
| 2024Q2 | 623406 (2024-07-11) | Europris_ASA_Q2_2024_report.pdf, _presentation.pdf | Q2 2025 (650986) agrees. FX: see below |
| 2024Q3 | 630818 (2024-10-31) | Europris_ASA_Q3_2024_report.pdf | Q3 2025 (658269) agrees. Norway FX taken from 658269 |
| 2024Q4 | 637305 (2025-01-29) | Europris_ASA_Q4_2024_report.pdf, _presentation.pdf | Q4 2025 (664387) agrees. Norway FX taken from 664387 |
| 2025Q1 | 643362 (2025-04-10) | Europris_ASA_Q1_2025_report.pdf, _presentation.pdf | Q1 2026 (671239) agrees. Norway FX taken from 671239 |
| 2025Q2 | 650986 (2025-07-10) | Europris_ASA_Q2_2025_report.pdf | Q2 2026 (677868) agrees. Norway FX taken from 677868 |
| 2025Q3 | 658269 (2025-10-30) | Europris_ASA_Q3_2025_report.pdf | none (Q3 2026 not yet published) |
| 2025Q4 | 664387 (2026-01-29) | Europris_ASA_Q4_2025_report.pdf, _presentation.pdf | Audited FY2025 in 671239: group revenue 14,878.4 vs 14,878.5; Norway FY EBIT 1,475 vs 1,476 |
| 2026Q1 | 671239 (2026-04-23) | Europris_ASA_Q1_2026_report.pdf, _presentation.pdf | none |
| 2026Q2 | 677868 (2026-07-09) | Europris_ASA_Q2_2026_report.pdf, _presentation.pdf | none |

Each quarterly results message has two attachments: the report and the presentation. Newsweb titles are headline sentences, for example 523770 "Strong fourth quarter - solid merchandising and improved operationally efficiency" and 677868 "Norway delivers, Sweden progresses and margin strengthen across the group in the first half of 2026". I listed the messages with POST `list?issuer=EPR` in half-year windows from 2020-01-01 to 2026-10-11 (227 messages).

## Definitions (kept consistent with part 1)
- **Revenue** is the IFRS "Total operating income": retail sales (directly operated stores and pure-play online sales), wholesale to franchise stores, and franchise fees/other.
  - 2020Q1 to 2024Q1: group revenue from the income statement (NOK thousand), rounded to 0.1.
  - 2024Q2 onwards: segment-Norway "Total operating income" from the segment key-figure table. These are **whole NOK million only**; the reports give segments no finer precision. `group_revenue_nok_m` is taken from the consolidated income statement.
  - Revenue growth from 2021Q1 includes acquired pure plays. Lekekassen alone had about NOK 545m revenue in 2020. Organic or "excluding acquisitions" growth, where the report gives it, is in the row notes:
    - 2021Q3 +1.9%
    - 2021Q4 -1.3%
    - 2022Q1 -5.5%
    - 2022Q2 +1.3%
    - 2022Q3 -0.8%
    - Q1 to Q2 2023 excluding Strikkemekka: +9.6% and +2.7%
  - LFL and chain sales are not affected by acquisitions.
- **Chain sales and LFL** cover the Europris chain, including franchise stores ("Total chain sales", "% growth in like-for-like chain sales").
  - LFL = stores open in every month of both the current and the previous calendar year.
  - From 2021Q1 chain sales are printed in whole NOK million (2020: one decimal).
  - From 2024Q2 they come from the segment-Norway "EUROPRIS CHAIN KEY FIGURES" block.
- **gross_profit_nok_m = gross profit EXCLUDING unrealised FX**, the same definition as part 1 (revenue minus COGS excluding unrealised FX).
  - 2020: the key-figure "Gross profit" as reported. It still excluded FX in 2020.
  - **Definition change in the reports from Q1 2021.** Europris dropped the APMs "COGS excluding unrealised FX", "non-recurring items" and "adjusted EBITDA/EBIT" (Q1 2021 report, APM page). From then on it reports IFRS gross profit including unrealised FX. Its restated Q1 2020 gross profit becomes 589 instead of 558.
  - To keep one series I compute `gross_profit_nok_m = IFRS gross profit - unrealised_fx_gain_nok_m` for 2021Q1 onwards. The IFRS gross profit of every row is written in its notes.
  - Precision: the FX amount is printed only in whole NOK million in 2021 to 2024 report text, and segment GP is in whole millions. Derived GP is therefore accurate to about ±0.5 to 1.
  - `gross_margin_pct` = gross_profit / norway revenue, my calculation. For 2020 it matches the reported margins (40.4, 43.9, 43.6, 45.7).
- **unrealised_fx_gain_nok_m** is the net unrealised FX on currency hedging contracts and accounts payable included in IFRS COGS (gain positive).
  - 2020: the APM table, one decimal.
  - 2021Q1 to 2024Q1: report text, whole NOK million. 2021Q4 was 0 ("did not recognise any net unrealised gain/loss").
  - Segment era: the **segment-Norway** figure. The early segment reports print only a group figure, so later reports' segment comparatives are used:
    - 2024Q3: -4.4 (Q3 2025 report; Q3 2024 report group -7)
    - 2024Q4: +11.9 (Q4 2025 report; group +15)
    - 2025Q1: -23.7 (Q1 2026 report; Q1 2025 report "organic" -24, group -34)
    - 2025Q2: +4.0 (Q2 2026 report; Q2 2025 report group +10)
    - 2025Q3: +6.2
    - 2025Q4: +10.2
    - 2026Q1: -8.6
    - 2026Q2: +15.4
  - **2024Q2: -10.3 is DERIVED.** No Norway-only figure is printed for this quarter. It is FY2024 Norway +16.2 (Q4 2025 report) minus 2024Q1 +19 (pre-segment), 2024Q3 -4.4 and 2024Q4 +11.9. It is consistent with "H1 2024 gain of NOK 9 million" in the Q2 2025 report. The Q2 2024 report's group figure is -17.
  - Check: Norway 2025 quarters sum to -3.3 against the reported FY2025 Norway -3.4.
- **opex_nok_m** = employee benefits plus other operating expenses (company "Opex"). It includes items that were classed as non-recurring in 2020 and is after the IFRS 16 rent reduction.
- **ebitda_nok_m** = IFRS EBITDA = operating profit plus depreciation and amortisation. It includes unrealised FX and any one-offs, the same as part 1.
  - Identity: `ebitda = gross_profit + unrealised_fx - opex`. Within 0.1 for 2020 to 2024Q1 and within rounding (±1) for segment rows.
  - 2020's company "Adjusted EBITDA" (excluding FX and NRI) is in the notes as `adj_EBITDA=`. Non-recurring items in 2020: Q1 4.9, Q2 4.9, Q3 0.5, Q4 2.2.
- **ebit_nok_m** = IFRS operating profit, or segment EBIT. Margins are my calculation (value / norway revenue).
- **IFRS 16**: `ifrs16_applied = 1` for every row.
  - `ebitda_pre_ifrs16_nok_m` is filled only for 2020, as EBITDA minus the reported "Other operating expenses - IFRS 16 effect" (119.4 / 122.6 / 124.4 / 124.8), the same method as part 1.
  - From Q1 2021 the reports no longer show the IFRS 16 effect on opex or EBITDA, so the column is empty for 2021Q1 onwards.
- **Stores**: Europris chain stores at period end (total, directly operated, franchise), from the key-figure tables. ÖoB stores are excluded.
- **easter_effect_pp** is filled only where management states a number of percentage points on sales growth:
  - 2025Q1: **-4.5**, the midpoint of "4-5 percentage points" (NOK 80-100m in segment Norway). This estimate **includes** the one-less-calendar-day (leap year 2024) effect.
  - 2026Q1: **+7** (segment Norway; group about +6).
  - 2026Q2: **-5.5** (segment Norway; group about -4.5).
  - The other Easter-affected quarters are described only qualitatively and the cells are empty:
    - 2021Q1 positive, 2021Q2 negative
    - 2022Q1 negative, 2022Q2 positive
    - 2023Q1 positive, 2023Q2 negative
    - 2024Q1 positive, 2024Q2 negative
    - 2025Q2 positive
  - The presentations' rule of thumb for the Easter shift:

    | Period | Revenue | EBITDA |
    |---|---|---|
    | 2020 | NOK 50m | 10m |
    | 2021 to 2023 | NOK 60-75m | 12-15m |
    | 2024 to Q3 2025 | NOK 65-80m | 13-16m |
    | Q4 2025 | NOK 85-110m | NOK 7-10m EBIT (EBITDA not given) |
    | Q1 to Q2 2026 | NOK 130-200m (the slide does not say whether this is group or Norway) | not given |

  - Easter Sundays: 12 Apr 2020, 4 Apr 2021, 17 Apr 2022, 9 Apr 2023, 31 Mar 2024, 20 Apr 2025, 5 Apr 2026.
- `restated = 0` for every row. All main values come from the quarter's own report. The only later-report inputs are the segment-Norway FX values listed above, and each row's notes say where they come from.

## Definition changes and comparability breaks inside part 2
1. **Q1 2021 APM change** (see gross profit). Handled by deriving GP excluding FX.
2. **Q1 2023: stocktaking calculation differences are now booked in the quarter they occur.** Before this they were lumped into Q3/Q4 at the annual count. Examples:
   - Q3 2020 +22, of which about 16 belongs to earlier quarters
   - Q4 2020 +21.5
   - Q3 2021 +4 (delayed count)
   - Q4 2021 +24.2
   - Q3 2022 +62 (+2.8pp on the GM change)
   - Q4 2022 +27.7
   - After the change: Q1 2023 +15, Q2 2023 +20, Q3 2023 +59

   The seasonal pattern of the gross margin therefore changes from 2023. The Q4 2023 report says the timing of the 2022 count cost 0.7pp of the y/y GM change.
3. **Acquisitions** of pure plays raise revenue and opex from 2021 (see revenue). OoB is excluded from every norway_* column.
4. **Segment era precision.** From 2024Q2 the Norway figures are whole NOK million, so margins carry about ±0.02 to 0.05pp of rounding error. The segment table GP sometimes differs by 1 from revenue minus COGS (2025Q4, 2026Q1); I used the printed GP.
5. **Covid-19 (2020 to 2022)** produced extreme y/y swings. Management's explanations are in each row's notes:
   - Q2 2020: closed Swedish border, staycation and home-and-garden demand. LFL +34.6%.
   - 2021: temporary store closures:
     - Q1 2021: 10% of stores on average, up to 94 stores (35%) in late March
     - Q2 2021: 8% on average, 22% in April
   - Reopening on 25 Sep 2021 and the border on 6 Oct 2021.
   - Restrictions again in mid-December 2021, lifted mid-February 2022.
   - Normalisation and negative LFL in 2021Q2, Q4 2021, Q1 2022 and Q3 2022.
   - The fixed-rate inbound freight agreement (2021) supported record gross margins, peaking at 50.0% in Q4 2021.

## Restatements and revisions found
- **FY2021 audited** (Q1 2022 report) against the sum of the 2021 quarterly reports:
  - revenue 8,648.2 vs 8,649.1
  - COGS 4,592.1 vs 4,583.8
  - other opex 742.7 vs 751.0
  - operating profit 1,511.8 vs 1,512.8

  The Q4 2022 report still prints the original unaudited Q4 2021 figures, so I kept them. The implied audited Q4 2021 GP would be about 8.3 lower and opex 8.2 lower, with EBITDA almost unchanged.
- **FY2022 audited**: COGS +0.01m, other opex -0.02m. Negligible, and quarters not restated.
- **FY2025 audited** (Q1 2026 report): group revenue -0.08m, Norway FY EBIT 1,475 vs 1,476. Quarters not restated.
- **2020Q3.** Key-figure GP (excluding FX) is 827.6, while income-statement revenue minus COGS minus FX gives 827.5. I used the reported 827.6. EBITDA is from the income statement (406.8). The key-figure identity gives 406.9.
- **2024 group-level FX is internally inconsistent across reports.**
  - Q2 2024 report: H1 = +2, i.e. Q1 +19 and Q2 -17.
  - Q3 2024 report: 9M = +3, while Q3 is -7.
  - Q4 2024 report: FY = +18 with Q4 +15.
  - Q2 2025 report: H1 2024 = +9 and Q2 2024 = -17.

  The segment-Norway figures from the 2025 and 2026 reports reconcile: Q1 +19, Q2 -10.3 derived, Q3 -4.4, Q4 +11.9, which sum to FY +16.2. The likely cause is that the 2024 group figures mix in ÖoB's hedges from May 2024.
- I found no restatement of quarterly key figures (revenue, COGS, opex, EBITDA, EBIT, chain sales, LFL, stores) in any following-year comparative from 2020 to 2025.

## Uncertain items / caveats
- 2024Q2 unrealised FX (-10.3) is derived and not printed, so 2024Q2 `gross_profit_nok_m` (1,075.3) carries the same uncertainty. Using the group figure of -17 would give GP 1,082 and a GM 0.28pp higher.
- From 2021, GP excluding FX relies on FX rounded to whole NOK million (±0.5).
- 2025Q1 `easter_effect_pp` = -4.5 is a midpoint, and it includes the leap-day effect (about 1pp).
- `ebitda_pre_ifrs16_nok_m` cannot be filled after 2020 from these sources.
- **For the downstream builder:** `gross_profit_nok_m` in BOTH part 1 and part 2 already EXCLUDES unrealised FX. So:
  - IFRS gross margin = (gross_profit + unrealised_fx) / revenue.
  - `scripts/build_dataset.py` computes `gm_exfx = (gp - fx)/rev`. That assumes GP includes FX, so it subtracts FX a second time. `gm` itself is already the ex-FX margin.

## Verification log
- 2026-10-11, independent verifier (task europris-verify-p2). I rebuilt the message list myself: newsweb `list?issuer=EPR`, half-year windows from 2020-01-01 to 2026-10-11. I then downloaded all 26 quarterly report PDFs and the presentations again and re-extracted every quarter from 2020Q1 to 2026Q2 from the original income statements (NOK thousand), the segment-Norway key-figure tables and the report text.
  - Fields checked: norway/group revenue, LFL, chain sales and growth, gross profit and margin (excluding FX), unrealised FX, opex, EBITDA, EBIT, margins, stores (total, directly operated, franchise) and easter_effect_pp.
  - Each value was cross-checked against the comparative printed in the following year's report.
  - **Result: no CSV value was wrong, so no corrections were made.** The only differences are 0.05 rounding ties, for example 2023Q2 EBIT 362,150 thousand → 362.2.
- Reported y/y revenue growth matches the CSV's computed growth in every row. Computed GP/revenue, EBIT/revenue and EBITDA/revenue match the margin columns within 0.01pp. GP + FX − opex = EBITDA holds within ±1 (segment rounding).
- **Still unconfirmed: 2024Q2 unrealised FX (-10.3, derived).** No Norway figure is printed for this quarter, and the reports disagree:
  - The Q2 2024 report says Norway GM was "+0.4pp ex-FX". That implies a Norway FX of roughly -11 to -14. With -10.3 the result is +0.3pp; with the group -17 it is +0.6pp.
  - Group-level arithmetic gives Q2 2024 ≈ -9 to -10:
    - 9M 2024 +3 (Q3 2024 report)
    - FY 2024 +18 (Q4 2024 report)
    - H1 2024 +9 (Q2 2025 report)
  - The value was left at -10.3, because it reconciles to the printed FY2024 Norway +16.2. Treat 2024Q2 GP/GM as accurate to only about ±3 NOK m (±0.1pp).
- The note above saying `scripts/build_dataset.py` subtracts FX twice is stale. The current script computes `gm = gp/rev`, where gp already excludes FX, and has no `gm_exfx`.
