# Europris ASA: quarterly financials, part 1 (2014Q1 to 2019Q4). Sources and definitions

Output: `data/europris_part1.csv` (24 rows, one per quarter 2014Q1 to 2019Q4).

All figures come from Europris ASA quarterly reports and presentations published on Oslo Børs newsweb (issuer EPR). I fetched them with the newsreader API (`list`, `message`, `attachment`) and converted the PDFs with `pdftotext -layout`. I used no other website. I did not try any blocked site.

## Scope
- Every quarter in this range has scope `group_pre_segment`. Each report's segment note says that "the group as a whole is defined and identified as one segment" (all stores in Norway).
- The 20% stake in Runsvengruppen AB (ÖoB) appears from 2018 to 2019 as an associate. "Profit (loss) from associated companies" sits below operating profit, so ÖoB is not consolidated in any of these figures.
- `norway_revenue_nok_m` therefore equals `group_revenue_nok_m` (Total operating income, also called "Group revenue").
- No quarter in this range has a Norway/Sweden segment split.

## Messages and attachments used per quarter

| Quarter | Values taken from (report_message_id, published) | Attachment(s) | Cross-checks |
|---|---|---|---|
| 2014Q1 | 383379 (2015-08-14), Q2 2015 report | Europris_Q2_2015_Interim_report.pdf, Q2_2015_presentation.pdf | Derived as H1 2014 minus Q2 2014. Q2 2015 presentation chart: revenue 854, adj. EBITDA 33 |
| 2014Q2 | 383379 (2015-08-14) | Europris_Q2_2015_Interim_report.pdf | none |
| 2014Q3 | 389237 (2015-11-12) | Q3_Europris_report.pdf | YTD figures in same report |
| 2014Q4 | 394831 (2016-02-12) | Europris_Q4_15_report___FINAL.pdf. Store split: 383921 (2015-08-20) 2015_08_20_Analyst_Presentation.pdf | FY2014 in 2015 reports |
| 2015Q1 | 401937 (2016-05-13), Q1 2016 report | Europris_Q1_16_final.pdf | H1 2015 minus Q2 2015 (383379) agrees within 0.1. LFL 11.7% also shown in Q2 2015 presentation |
| 2015Q2 | 383379 (2015-08-14) | Europris_Q2_2015_Interim_report.pdf | Q2 2016 report comparatives (406964) agree |
| 2015Q3 | 389237 (2015-11-12) | Q3_Europris_report.pdf | Q3 2016 report (412614) agrees |
| 2015Q4 | 394831 (2016-02-12) | Europris_Q4_15_report___FINAL.pdf | Q4 2016 report (420458) has small audit revisions, see below |
| 2016Q1 | 401937 (2016-05-13) | Europris_Q1_16_final.pdf | Q1 2017 report (425742) agrees |
| 2016Q2 | 406964 (2016-08-11) | Europris_ASA_Q2_2016_report.pdf | Q2 2017 (431362) agrees |
| 2016Q3 | 412614 (2016-11-03) | Europris_ASA_Q3_2016_report.pdf | Q3 2017 (437631) agrees |
| 2016Q4 | 420458 (2017-02-17) | Europris_ASA_Q4_2016_report.pdf | Q4 2017 (443231) agrees |
| 2017Q1 | 425742 (2017-04-27) | Europris_ASA_Q1_2017_report.pdf | Q1 2018 (449042) agrees |
| 2017Q2 | 431362 (2017-07-14) | Europris_ASA_Q2_2017_report.pdf | Q2 2018 (455545) agrees except a misprinted chain-sales comparative (see below) |
| 2017Q3 | 437631 (2017-11-01) | Europris_ASA_Q3_2017_report.pdf | Q3 2018 (462430) agrees |
| 2017Q4 | 443231 (2018-02-01) | Europris_ASA_Q4_2017_report.pdf | Q4 2018 (468352) agrees |
| 2018Q1 | 449042 (2018-04-19) | Europris_ASA_Q1_2018_report.pdf | Q1 2019 (475037) agrees |
| 2018Q2 | 455545 (2018-07-13) | Europris_ASA_Q2_2018_report.pdf | Q2 2019 (481309) agrees |
| 2018Q3 | 462430 (2018-10-31) | Europris_ASA_Q3_2018_report.pdf | Q3 2019 (488371) agrees |
| 2018Q4 | 468352 (2019-01-31) | Europris_ASA_Q4_2018_report.pdf | Q4 2019 (494202) agrees |
| 2019Q1 | 475037 (2019-04-25) | Europris_ASA_Q1_2019_report.pdf, Europris_ASA_Q1_2019_presentation.pdf | Q1 2020 (501532) agrees |
| 2019Q2 | 481309 (2019-07-12) | Europris_ASA_Q2_2019_report.pdf | Q2 2020 (509653) agrees |
| 2019Q3 | 488371 (2019-11-01) | Europris_ASA_Q3_2019_report.pdf | Q3 2020 (516777) agrees |
| 2019Q4 | 494202 (2020-01-30) | Europris_ASA_Q4_2019_report.pdf | Q4 2020 (523770, 2021-02-04) agrees |

Other documents I read: the annual report 2015 (399674), for the write-down of contractual rights in 2014.

## Availability of early reports
- No Q1 2015 report exists. The IPO was 19 June 2015 and the first interim report is Q2 2015 (2015-08-14). A newsweb listing for issuer EPR from 2015-01-01 returns nothing before 2015-06-08. The IPO prospectus is not attached to any newsweb message.
- **2014Q1** is DERIVED by subtraction: H1 2014 minus Q2 2014, both from the comparatives in the Q2 2015 report. The values agree with the rounded Q1 2014 bars in the Q2 2015 presentation (revenue 854, adjusted EBITDA 33).
  - Not available for 2014Q1: LFL growth, chain-sales growth and store count. These cells are empty.
- **2015Q1** comes from the comparatives in the Q1 2016 report. I cross-checked it against H1 2015 minus Q2 2015.
- Every 2014 row and 2015Q1 is marked `restated=1` because the values come from a later report's comparatives. They are not restatements in the accounting sense.
- Store split (directly operated / franchise):
  - Missing for 2014Q1 to 2014Q3 and for 2015Q1.
  - The YE2014 split (149 / 71) comes from the analyst presentation of 2015-08-20.
  - The 2015 to 2016 splits come from the report text. From 2017 the key-figure table gives them, with comparatives.

## Definitions used (identical across all rows)
- **Revenue** is the IFRS line "Total operating income (group revenue)": sales by directly operated stores, plus wholesale to franchise stores, plus franchise fees and other income. One exception: in 2014Q3 the key-figure table shows 1,054.3 while the income statement shows 1,054,168 thousand. I used the key-figure value.
- **Chain sales and growth** are "Total retail sales" for the Europris chain, including franchise stores, and its y/y growth, both from the key-figure table.
- **LFL** is "Like-for-like sales growth" for the chain. It covers stores open in every month of both the current and the previous calendar year, including franchise stores. The market reference is the Kvarud shopping-centre index (not captured here).
- **gross_profit_nok_m** is the company's key-figure gross profit: group revenue minus "COGS excluding unrealised foreign exchange effects". `gross_margin_pct` is my calculation, gross_profit / revenue. It matches the reported % margin within rounding.
- **unrealised_fx_gain_nok_m** is the unrealised FX on inventory hedges and inventory trade payables included in **IFRS COGS** (gain positive).
  - From 2016: IFRS gross profit = `gross_profit_nok_m + unrealised_fx_gain_nok_m`.
  - Sources: APM tables where they exist (2018 and 2019 reports, and the 2018 reports for 2017 comparatives) and the Q3 2016 income-statement footnote (-10.3).
  - Q1, Q2 and Q4 2016 are derived as key-figure COGS minus IFRS COGS, rounded to 0.1. The report text confirms the sign and size of each.
  - **2014 to 2015 are empty on purpose.** Up to 2015 the unrealised FX on hedges was booked in net financial items, not in COGS, so the 2014 to 2015 gross profit and EBITDA contain no unrealised FX.
  - The Q1 2016 report (note 2, repeated in the Q2 to Q4 2016 reports) gives pro-forma amounts for 2015 under the new principle. Converted to gain-positive: Q1 -5.0, Q2 -26.9, Q3 +10.6, Q4 -4.3, FY -25.5. They are in the row notes only.
  - In that note's table a positive number means a loss. The Q4 2016 report text confirms this ("last year … unrealised loss of NOK 4 million").
- **opex_nok_m** is the key-figure "Opex": employee benefits plus other operating expenses, **including** non-recurring items. In 2019 it is after the IFRS 16 reduction in rent. The ex-IFRS 16 opex is in the notes.
- **ebitda_nok_m** is EBITDA as reported, unadjusted: IFRS operating profit plus depreciation and impairment. This matches the company's own definition ("operating profit excluding depreciation").
  - It includes non-recurring items and, from 2016, unrealised FX. For 2014 to 2015 it equals the key-figure "EBITDA" line.
  - Identity that holds in every row (within 0.1): `ebitda = gross_profit + unrealised_fx - opex`.
  - The company's headline **Adjusted EBITDA** (excluding NRI and unrealised FX) is in each row's notes as `adj_EBITDA=`. Also: `adj = ebitda - unrealised_fx + NRI`.
- **ebit_nok_m** is IFRS "Operating profit". Margins are my calculation, value / revenue.
- **IFRS 16** (from 1 Jan 2019, modified retrospective, 2018 not restated): `ifrs16_applied=1` for the 2019 rows.
  - `ebitda_pre_ifrs16_nok_m` for 2019 = EBITDA minus the reported line "Other operating expenses - IFRS 16 effect" (102.0 / 111.5 / 115.8 / 120.6).
  - The reported "Adjusted EBITDA ex IFRS 16" (23.2 / 184.1 / 146.6 / 329.6) is in the notes.
  - Before 2019, `ebitda_pre_ifrs16_nok_m` equals `ebitda_nok_m`, since IFRS 16 was not applied. This gives one continuous series.
- **easter_effect_pp** is filled only where management states the effect as a percentage: 2019Q1 = -5.0 ("around five per cent (NOK 60 million)").
  - 2019Q2 says only "around NOK 60 million", positive. I left the cell empty; 60 is about 4.2% of Q2 2018 revenue.
  - Other years mention only the selling-day differences caused by Easter's timing, recorded in the notes:
    - Q1 2016: 2 fewer days (2.6%)
    - Q2 2016: 3 more days in April
    - Q1 2017: 3 more days, but the Easter peak was in Q2
    - Q2 2017: 4 fewer days, but Easter was in Q2
    - Q1 2018: 2 fewer days, Easter in Q1
    - Q2 2018: 2 more days, no Easter
  - From Q4 2018 the presentations give a rule of thumb: "the Easter impact is approximately NOK 50 million in revenue and NOK 10 million of EBITDA".
  - Easter dates: 20 Apr 2014, 5 Apr 2015 (peak days in March), 27 Mar 2016, 16 Apr 2017, 1 Apr 2018, 21 Apr 2019.

## Definition changes and comparability breaks
1. **2014 EBIT is not comparable with later years.**
   - Contractual rights were amortised in 2014: NOK 38m in H1 2014, so quarterly D&A was about 31 against about 18 in 2015.
   - Q4 2014 also includes an impairment of 78.3 that wrote contractual rights to nil.
   - EBITDA is not affected.
2. **Unrealised FX reclassified into COGS from 1 Jan 2016.** Earlier periods were not restated in the financial statements; see the FX definition above.
3. **Non-recurring items** (included in opex and EBITDA, excluded from adjusted figures):
   - 2014: Q3 3.7, Q4 6.8
   - 2015: Q1 6.7, Q2 30.0 (IPO)
   - 2019: Q2 8.0, Q3 4.4, Q4 6.2 (move of the central warehouse and rent on vacated warehouses)
   - No other quarter has any.
4. **Annual stocktaking.** Europris books a calculated gross margin during the year and adjusts it to actual at the annual stocktaking. This makes the gross margin seasonal and lumpy:
   - The 2014 stocktaking ran Sep to Nov and +25.4 was booked in Q4 2014.
   - From 2015 the effect falls in Q3:
     - Q3 2015: +20.9, of which about 15 belongs to earlier quarters
     - Q3 2016: GM 41.5% excluding stocktaking, against 41.9% reported
     - Q3 2018: +30, about 24 from earlier quarters
     - Q3 2019: +33, about 29 from earlier quarters, GM 42.6% excluding stocktaking
5. **IFRS 16 from 2019** (see above).
6. **Franchise takeovers** move sales from "wholesale to franchise" to "directly operated stores". This raises group revenue and gross margin but also opex. Takeovers were heavy in 2016 to 2018: franchise stores fell from 71 at YE2014 to 33 at YE2019. One-off GP charges from takeovers: Q4 2016 (amount not stated) and Q1 2017 (7.8).

## Restatements and revisions found
- **Q4 2015.** The audited FY2015 comparatives in the Q4 2016 report differ slightly from the original Q4 2015 report:
  - opex 362.9 vs 362.8
  - adjusted EBITDA 283.2 vs 283.3
  - operating profit 265,195 vs 265,292 thousand
  - chain sales 1,591.4 vs 1,591.0

  FY2015 net profit was 272.7 in the Q4 report and 277.6 audited. I kept the original Q4 2015 report values (`restated=0`).
- **FY2017.** The audited comparatives in the Q1 2018 report reclassify about 1.1 between employee costs and other opex. Operating profit changed by 0.002. No quarterly column is affected.
- **Q2 2018 report misprints:**
  - the Q2 2017 chain-sales comparative (1,409.4, which is the Q2 2016 figure; the correct value 1,539.9 is consistent with the -0.3% growth shown)
  - the Q2 2017 revenue in the text ("NOK 1,206 million"; the table shows 1,406.3)

  I used the original Q2 2017 report values.
- I found no restatement of 2016 to 2019 quarterly key figures in the following year's comparatives.

## Uncertain items / caveats
- 2014Q1 values are derived by subtraction, not printed as a quarter, although the presentation chart is consistent. Precision is ±0.1.
- 2016 Q1, Q2 and Q4 unrealised FX is derived from two rounded figures (±0.05 to 0.1). It agrees with the text: loss 12, gain (no amount in text, matches adjusted vs IFRS EBITDA), gain 15.
- 2017 quarterly unrealised FX uses the more precise APM comparatives from the 2018 reports. The original 2017 reports' text gives -5, -4, -1, +4 (whole NOK m).
- The unrealised FX amounts cover both currency derivatives and inventory trade payables. The reports do not split them.
- `easter_effect_pp` is mostly empty because management rarely quantified the effect before 2019.
- Store splits are missing for 2014Q1 to Q3 and 2015Q1. The 2014Q1 store total is unknown.

## Verification log
- 2026-10-11, independent verifier (task europris-verify-p1). I listed issuer EPR messages on newsweb for 2015-2021 myself and downloaded the 2015-2020 interim reports again: 383379, 389237, 394831, 401937, 406964, 412614, 420458, 425742, 431362, 437631, 443231, 449042, 455545, 462430, 468352, 475037, 481309, 488371, 494202, 501532, 509653, 516777 and 523770, plus 383921 (analyst presentation). I re-extracted all 24 quarters, comparing each against its own report and against the following year's comparatives. Every figure, including LFL, chain sales and store split, matched the CSV except one.
- FIX 2014Q3 `norway_revenue_nok_m` / `group_revenue_nok_m`: changed 1054.3 to **1054.2**, and recomputed `gross_margin_pct` from 41.03 to **41.04**. The EBITDA and EBIT margins are unchanged.
  - Why: the column is defined as the IFRS line "Total operating income (group revenue)".
    - In the Q3 2015 report (msg 389237) the income statement shows the Q3 2014 column as 1,054,168 thousand.
    - A second calculation gives the same figure: YTD Q3 2014 of 2,961,371 (389237) minus H1 2014 of 1,907,202 (Q2 2015 report, 383379) = 1,054,169 thousand.
    - The 1,054.3 in the key-figure table is the sum of rounded components (784.5 + 244.1 + 25.7).
  - Gross profit (432.6), EBITDA (108.8) and EBIT (77.1) are unchanged.
  - Q3 2015 y/y growth computed from the CSV is now 7.64%, against the 7.6% reported.
- Kept (not errors):
  - 2015Q4 keeps the original Q4 2015 report values, as documented. The audited comparatives in Q4 2016 (420458) are chain sales 1,591.4, opex 362.9 and operating profit 265,195 thousand.
  - Margin cells differ from rounded value / rounded revenue by up to 0.008 pp, because they were computed from figures in NOK thousand.
