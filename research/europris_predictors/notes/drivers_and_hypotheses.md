# Europris (Norway): what drives sales, gross margin and EBIT, with priors for testing

Task key: `drivers-context`. Compiled 2026-10-11. The latest reported quarter is Q2 2026, published 2026-07-09.

This note gives the econometric screen (`scripts/screen_predictors.py`, `scripts/fcast.py`) evidence-based priors on **sign** and **lead time** for each candidate predictor of Europris' Norwegian financials. It also documents the control dummies in `data/events_quarterly.csv`.

**Sources.**
- **Primary sources** are Europris' own stock-exchange releases on Oslo Børs NewsWeb. I read the release bodies for every quarterly report from Q2 2015 to Q2 2026, plus all 46 interim-report PDFs and 11 annual reports (2015 to 2025). I also read the Capital Markets Day 2018 deck, the Capital Markets Update 2022 deck and the company presentation from January 2024.
- **Secondary sources** are SSB, OxCGRT, Euromonitor and press or analyst snippets.
- **Citation format.** "NW 123456" means https://newsweb.oslobors.no/message/123456. The same content is available through the API at `https://api3.oslo.oslobors.no/v1/newsreader/message?messageId=123456`.
- Quotes are verbatim from the source.
- Raw downloads are kept outside the repo, in the scratchpad `dl/drivers-context/`.

---

## 0. Executive summary: the strongest priors

| # | Driver (repo series id) | Target | Expected sign | Expected lead (quarters) | Evidence strength |
|---|---|---|---|---|---|
| 1 | **USD/NOK, EUR/NOK, I-44** (`mkt_nok_per_usd_avg`, `mkt_nok_per_eur_avg`, `mkt_nok_i44_import_weighted_avg`). Year-on-year % change, i.e. a weaker NOK | Gross margin, excluding unrealised FX | **−** | **2–4** (centre about 3). The effect fades after about 4–6 quarters as retail prices are reset | Strong: hedging policy, management statements, and the 2015–16, 2022–24 and 2025–26 episodes |
| 1b | Same FX series, measured as the change *within* the reported quarter (end-of-period on end-of-period) | **Reported** gross margin, which includes the unrealised mark-to-market | **+**, the opposite sign | 0 (contemporaneous) | Strong: unrealised gains and losses are booked in COGS from 2016 (see §1.3) |
| 2 | Inbound container freight, as spot rates (`mkt_us_ppi_deep_sea_freight`, `mkt_gscpi`) and as the contract-regime dummies in §2 | Gross margin | **−** | **3–6**: works through fixed annual or two-year contracts, then inventory | Strong in 2021–23 (management quantified it). Spot-to-P&L timing is irregular |
| 3 | **Easter timing** (`easter_q_yoy_effect14`, `easter_week_split_q1_share`) | Sales growth in Q1 (+) and Q2 (−). Gross margin (− when Easter falls in the quarter). EBIT (+) | as stated | 0, known years ahead | Very strong: management quantifies it every year (−5% to +7pp) |
| 4 | **COVID border closure and cross-border trade** (`covid_border_restrictions`, `ssb_crossborder_daytrips_*`, `mkt_nok_per_100sek_avg`) | Sales growth | Closure +. NOK weaker vs SEK + | 0–1 | Strong for 2020–22. Moderate otherwise |
| 5 | **Household purchasing power**: policy rate (`mkt_no_policy_rate_avg`), real wages (`ssb_earnings_*` deflated by `ssb_cpi_total`), consumer confidence (`mkt_no_finansnorge_cci_*`) | Sales growth (ambiguous because of trade-down) and gross margin (− via mix when budgets are squeezed) | Rate ↑: sales ±/−, GM −. Real wages ↑: sales +, GM +. CCI ↑: sales +, GM + | Rates 2–6. Real wages 1–4. CCI 1–2 | Moderate: management names "interest rates, inflation and real wages" as key, but trade-down offsets volume |
| 6 | **Store count growth** (net openings, franchise takeovers) | Total sales growth (not like-for-like) | + | 0–4, because the pipeline is pre-announced | Mechanical |
| 7 | **Weather**: Q1 temperature (−), Q2 and Q3 warmth (+), with July heat waves an exception (`mkt_oslo_blindern_temp_mean_c`) | Sales and GM (seasonal mix) | as stated | 0, nowcast only | Strong qualitatively, weak for forecasting |

Suggested short-horizon (1–4q) candidates for the final top 5: Easter and calendar (known in advance), the FX lag at 2–3q (USD/NOK or I-44 year-on-year), the freight contract regime, the policy rate or consumer-confidence change, and the cross-border proxy (NOK/SEK and SSB day trips). Suggested long-horizon (≥4q) candidates: I-44 or USD/NOK year-on-year at lag 4 (margin), the policy rate at lag 4–6 (sales and margin, via mortgage costs), real-wage growth (sales), house prices (weak prior), and the store-count pipeline.

---

## 1. FX: NOK vs USD, EUR and I-44. Hedging policy and its timing

### 1.1 What is hedged, how far ahead, and what share is in foreign currency
- **Policy, repeated in every annual report from 2015 to 2025.** The 2015 annual report (NW 399674, Board of Directors' report, "Currency risk"), verbatim: *"Given the share of sourcing from low-cost countries in Asia and Europe, a considerable part of these purchases is denominated in USD and to a lesser extent in EUR. The group aims to achieve predictable cash outflows in NOK by using forward contracts (consistently on a six-month basis for purchase orders) as a hedging strategy for its exposure to USD and EUR. The hedging strategy is based on an assessment of the opportunities and the estimated time period required to adjust the business to the changes in foreign exchange rates. Six-month forward hedging has provided sufficient time for planning and well-timed execution."*
- **Annual reports 2016–2020** (for example NW 423726 and 499571, risk table): *"all purchase orders in USD and EUR are hedged for six months. That allows sufficient time to adjust the retail price. Historically, this has proved to work well in periods with large fluctuations in the currency market."*
- **From the 2021 annual report onward** the wording becomes *"hedged for up to six months"* (NW 557584, 586084, 613923, 641912). The 2025 annual report (NW 668777): *"...a currency hedging strategy whereby purchase orders in USD and EUR are hedged for up to six months. This provides flexibility to adjust retail prices and has historically proven effective during periods of significant volatility in currency, or for other input factors."*
- **Q1 2020 report** (NW 501532): *"Europris is keeping to its currency hedging policy, which specifies that all purchase orders placed in USD and EUR are hedged six months ahead. This has historically provided sufficient time to adjust retail prices. Purchase prices are also renegotiated, particularly with suppliers who do not have their cost base in USD or EUR."* The Q2 2020 report (NW 509653) adds: *"The Norwegian krone strengthened during the second quarter but is still volatile... Over time, this will affect purchase prices for Europris."*
- **USD share of purchases.** This is the only explicit figure I found. Q3 2025 report (NW 658269): *"USD is the largest foreign sourcing currency, accounting for around 30 per cent of Europris' purchases and around 10 per cent of ÖoB's"*. The same report: *"it takes time before any changes in the value of NOK and SEK versus sourcing currencies impacts the cost of goods sold. This is due to the group's hedging strategy (up to six months) and also from inventory turnover."* I found **no explicit EUR share**. The EUR/NOK post-tax sensitivity is roughly 1/4 to 1/2 of the USD/NOK sensitivity:

  | Annual report | USD/NOK ±10% | EUR/NOK ±10% | NOK/SEK ±10% |
  |---|---|---|---|
  | 2025 | ∓49.1m | ∓15.1m | ∓26.4m |
  | 2024 | ∓52.1m | ∓22.5m | – |
  | 2019 | ∓25.8m | ∓17.0m | – |

  These sensitivities are measured on balance-sheet exposures (forwards and payables), not on annual purchases. The NOK/SEK line relates to an internal SEK loan.
- **Q1 2025 report** (NW 643362): *"Stronger local currencies will isolated have a positive effect on cost of goods sold and the gross margin. However, as the group practices a six-month hedging strategy it will take some time before this materialises."*
- **Pass-through.** Annual-report risk table, 2020 (NW 529162) and 2022–2025: *"Purchase prices and general cost developments will affect competitors in the same way, and historically these types of cost increases have been absorbed by the market."*

### 1.2 Implied lag from a spot FX move to COGS
1. **Rate locked at purchase order.** A forward of up to 6 months is struck when the order is placed. Realised hedge results go to COGS, so the effective FX rate is the forward rate at order date.
2. **Transit.** Shipping from Asia is not quantified in total. The Q4 2023 report says the Red Sea rerouting added *"up to two weeks in transit time"* (NW 609575).
3. **Inventory holding.** Calculated from the annual reports:

   | Year-end | Inventory (NOK m) | COGS (NOK m) | Ratio | ≈ months of COGS |
   |---|---|---|---|---|
   | 2019 | 1,550 | 3,544 | 0.44 | about 5 |
   | 2022 | 2,384 | 4,833 | 0.49 | about 6 |
   | 2023 | 2,143 | 5,276 | 0.41 | about 5 |

   Sources: NW 499571, 586084, 613923. Seasonal goods are ordered well ahead (for example, *"long lead times for seasonal items"*, Q4 2020 report, NW 523770).
4. **Price response.** Management uses the hedge window to reprice. In Q1 2016 the *"process of adjusting end customer selling prices continued during the first quarter, however with limited effect in the first quarter"* (NW 401937). In Q2 2016 the *"gross margin improved from the first quarter this year due to price adjustments coming in"* (NW 406964).

**Prior.** A spot move at t reaches COGS at about t+2 to t+4 quarters, peaking around t+3. It is then partly or fully offset by retail repricing over the following 1–3 quarters, so the margin effect is **transitory**. Repricing makes the effect on **sales value** (price inflation) positive with a similar lag.

**Rough magnitude, from sourced inputs.** USD is about 30% of purchases and COGS is about 55–57% of sales (gross margin 43–45%). A 10% USD/NOK rise that is fully unhedged and not repriced would therefore add about 0.30 × 0.10 × 0.56 ≈ **1.7% of sales to COGS, about −1.7pp gross margin**, before EUR exposure and before price pass-through.

### 1.3 Accounting: why the reported gross margin moves the other way in the same quarter
- **Hedge accounting is never applied.** Forwards are carried at fair value through profit or loss (all annual reports).
- **Up to 2015**, unrealised gains and losses on FX forwards sat in **financial items**, while realised gains and losses went to COGS (2015 annual report, accounting principles, NW 399674).
- **From 2016** *"the classification of unrealised gains and losses on foreign currency derivatives that are economic hedges of inventory purchases has changed. These unrealised gains and losses are now classified as part of cost of goods sold"* (Q1 2016 report, NW 401937). The 2025 annual report adds: *"unrealised foreign currency exchange gains and losses on inventory trade payables are also included as part of COGS. All gains and losses, both realised and unrealised, related to the purchase of inventory are included as part of COGS"* (NW 668777).
- **Consequence for modelling.** When NOK weakens during a quarter, the outstanding long-USD forwards gain value, so **reported** gross margin gets an unrealised gain the same quarter. The economic hit arrives 2–4 quarters later. **Use gross margin excluding unrealised FX as the target where possible.** Otherwise include the within-quarter change in USD/NOK (end-of-period) as a contemporaneous control.

**Quarterly net unrealised FX in gross profit (group, NOK m; + = gain).** Each figure is taken from the quarterly report text, or from the "COGS excluding unrealised foreign exchange effects" alternative-performance-measure (APM) row for 2016–2020.

| Q | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | −12 | −5 | −7 | −7.0 | +30.9 | +21 | −5 | +5 | +19 | −34 (Norway −23.7) | −4 (Norway −8.6) |
| Q2 | +6 | −4 | +9 | −3.9 | −30.0 | +24 | +20 | −8 | −17 | +10 (Norway +4.x) | +19 (Norway +15.4) |
| Q3 | −10 | −1 | −8 | +9.0 | +5.2 | +4 | +11 | +2 | −7 | +7 (Norway +6.2) | |
| Q4 | +15 | +4 | +17 | −18.5 | −36.0 | 0 | −39 | −14 | +15 | +10 (Norway +10.2) | |

Notes on the table:
- 2015: Q3 +10.6 and Q4 −4 were booked in financial items, not in the gross margin.
- Segment Norway figures come from NW 643362, 658269, 664387, 671239 and 677868. "4.x" means the PDF text was truncated after the integer.
- 2016–2020 figures are derived as reported COGS minus "COGS excluding unrealised FX" (NW 401937 … 523770). 2021 onward figures are stated directly in the text, for example NW 531534: *"net unrealised gain of NOK 21 million"*.
- The size matters: Q1 2025's −34m moved the group gross margin by −2.1pp (NW 643362).

### 1.4 Episodes that support the lag
- **2014–16.** Quarterly-average USD/NOK (`mkt_nok_per_usd_avg`) went from 5.99 (2014Q2) to 7.75 (2015Q1) and 8.65 (2016Q1). FY2015 gross margin was *"positively influenced by foreign exchange currency rates (especially NOK/USD) in 2015"* (NW 420458). The margin then fell to 41.6% in Q1 2016 from 43.2% (NW 401937), and FY2016 to 42.9% from 44.5%. The trough came about 4–6 quarters after NOK began weakening and about 3–4 quarters after the steepest year-on-year move. It recovered as prices were adjusted in Q2 2016.
- **2022–24.** USD/NOK went from 8.85 (2022Q1) to 10.19 (2022Q4) and 10.5–11.0 through 2023–24. Management cites margin pressure *"throughout the year [2023] ... from higher input costs owing to a weak NOK"* (Q4 2023 report, NW 609575). In Q1 2024: *"higher input costs mainly reflecting the weaker NOK"* (NW 616738). In Q3 2024: *"impact from a continued weak Norwegian krone put pressure on the gross margin"* (NW 630818). Freight and mix shifts confound this episode.
- **2025–26.** USD/NOK went from 11.08 (2025Q1) to 10.10 (2025Q3) and 9.41 (2026Q2). Results:
  - Organic (Norway) gross margin ex-unrealised FX was +1.7pp in Q1 2025 (NW 643362).
  - Norway gross margin was +0.9pp in Q3 2025 (NW 658269).
  - But H1 2026 Norway gross margin ex-FX was **−0.4pp** (NW 677868), with campaigns, consumables and Easter mix dominating.
  - Lesson: lower COGS from a stronger NOK is partly competed away, as management warned the impact *"will depend on sales prices in the market"* (NW 658269).

---

## 2. Inbound freight (Asia → Norway)
**Mechanism.** Europris buys long-haul freight on fixed contracts. Freight is capitalised into inventory cost, so contract changes reach gross margin with an inventory lag of about 1–2 quarters. Spot rates matter only when contracts are renewed.

| Period | Contract regime and effect | Source |
|---|---|---|
| 2021 | *"Europris has a fixed agreement with a freight carrier to fix both price and volume for 2021"*, signed while spot rates spiked. Q2 2021 gross margin +4.6pp (*"Positive effects from hedging currency and inbound freight rates"*). Q3 2021 +1.8pp. Q4 2021 50.0% vs 44.2% | 2020 annual report NW 529162; NW 538131, 545906, 552536 |
| From Mar 2022 | New two-year agreement: *"The annualised increase in costs for inbound freight is estimated at NOK 170-200 million, and will affect the financial figures from March 2022."* Q3 2022 underlying margin −0.9pp *"explained by higher costs for inbound freight"*. Q4 2022 margin 45.5% vs 50.0% | 2021 annual report NW 557584; NW 574601, 581191 |
| From Jan 2023 | *"negotiated a new two-year freight agreement commencing in January 2023, in which the rates have been reduced by approximately 50 per cent compared to the current agreement"*. Old-cost carry-overs still hit Q2 2023 (*"Seasonal carry-overs ... reflecting higher costs in the old freight agreement"*) | CMU NW 577619; NW 595225 |
| Dec 2023–2024 | Red Sea rerouting. *"capacity constraints due to a lack of containers and higher war surcharges"* (Q2 2024). *"cost for inbound freight from Asia was negatively impacted by surcharges"* (Q4 2024) | NW 609575, 623406, 637305 |
| 2026 | *"renewed its inbound freight agreement for overseas shipments, securing capacity for deliveries at competitive rates through next summer"* | NW 671239 |

**Prior for gross margin.**
- Spot freight indices (`mkt_us_ppi_deep_sea_freight`, `mkt_gscpi`): **negative sign, 3–6 quarter lead**. This is unstable because of contract timing.
- A better input is a regime variable built from the table above.
- No sales effect is expected beyond supply availability. Management says the 2021 contract *"secured the flow of goods"* (NW 552536).

---

## 3. Household purchasing power, trade-down and the macro cycle

| Variable | Mechanism | Sales growth | Gross margin | Lead (q) | Evidence |
|---|---|---|---|---|---|
| Policy rate, mortgage rates (`mkt_no_policy_rate_avg`, `mkt_no_fci_lending_rates_avg`) | Higher debt service lowers discretionary spend. High-ticket seasonal items fall while consumables and campaign items rise | − (small; offset by trade-down traffic) | − (mix moves toward consumables and campaigns) | 2–6 | Q4 2023: *"yet another interest-rate hike in December 2023 ... Although this will take some time to filter through to mortgage payments, consumer spending is expected to remain cautious in 2024"* (NW 609575). Q3 2019: *"increased interest rates and a weak Norwegian currency gradually affect the consumer economy"* (NW 488371). Q2 2026: the hike to 4.25% *"may weigh on consumer confidence and spending patterns"* (NW 677868) |
| Real wage growth (`ssb_earnings_idx_*` or `ssb_avg_cash_pay_*` deflated by `ssb_cpi_total`; `ssb_hh_real_disp_income_2015p_sa`) | More purchasing power | + | + (more non-food and seasonal) | 1–4 | Q1 2024: *"interest rates, inflation and real wages remaining key for consumers' ability and willingness to spend"* (NW 616738). Q3 2024: *"it will likely take some time until higher purchasing power translates into higher sales volumes"* (NW 630818), which points to a long lag. Repeated in 2025–26 (NW 643362, 650986, 658269, 664387) |
| CPI and food inflation (`ssb_cpi_coicop_01_food_nonalc_bev`, `ssb_cpi_total`) | Inflation feeds nominal sales (Europris' prices rise too) and drives trade-down to discounters. It also intensifies grocery price competition on consumables | + (nominal) | − (consumables mix, price competition) | 0–2 | Q2 2022: items under NOK 100 +8.5% while items over NOK 1,000 −25.1% (NW 566962). Q3 2022: *"the combination of 'all round' higher prices and rising interest rates is affecting consumer behaviour"* (NW 574601). Q2 2023: conditions *"should be supportive of low-price, campaign-driven retail concepts"* (NW 595225). Q3 2024: *"Campaigns and consumables help drive sales, but these trends also put pressure on the gross margin"* (NW 630818) |
| Consumer confidence (`mkt_no_finansnorge_cci_sa`, `..._major_purchases`) | Willingness to buy higher-ticket seasonal goods | + | + | 1–2 | Q3 2024: *"as inflation slows down and consumer confidence strengthens, we're optimistic about our mid-term growth prospects"* (NW 630818). Q1 2026: *"Consumer sentiment has strengthened ... supported by lower inflation, real wage increases and declining interest rates"* (NW 671239). Note the counter-example: like-for-like was +3.8% in Q3 2023 and +5.0% in Q1 2024 while sentiment was weak (trade-down) |
| Unemployment (`ssb_lfs_unemp_rate_sa`) | Income channel (−) vs trade-down (+) | ambiguous, weak | − | 1–4 | No management mention found. Treat as a weak prior |
| House prices, housing turnover (`ssb_house_price_idx_total_sa`, `ssb_dwelling_starts_sa`) | Home, interior, garden and DIY categories; wealth effect | + (weak) | + (weak) | 1–4 | Only a passing reference: Q4 2017 outlook, *"the housing market has experienced, and may continue to experience, some pressure"* (NW 443231). Weak prior |
| Household electricity price (`ssb_elec_hh_total_price_net_support`, `ssb_cpi_coicop_0451_electricity`) | (a) Squeezes discretionary budgets. (b) Store and warehouse **opex**, which is hedged far ahead | sales − (0–2q) | opex/EBIT − with lag **4–7q** | see text | Q1 2022: *"very high prices for electricity and fuel, a general increase in inflation, and rising interest and mortgage rates"* (NW 560306). Q3 2022: *"Europris hedges electricity costs 12-21 months ahead"* (NW 574601). Q1 2024: hedging *"over time yielded large savings ... this led to a cost increase year-over-year"* (NW 616738) |

**Counter-cyclicality.** Management repeatedly describes discount variety retail as thriving in weak markets. Q3 2019: *"Discount variety retailing is thriving in a challenging retail market"* (NW 488371). Q4 2023: chain sales +36% vs 2019 against a market *"stacked growth of 23 per cent for the years 2019 to 2023, according to Statistics Norway"* (NW 609575).

Expect macro-squeeze variables to show **weaker effects on sales growth than on gross margin**. The mix shift toward consumables and campaigns is the clearest channel.

**Nowcast.** SSB's monthly retail index for NACE 47.19 non-specialised non-food stores (`ssb_rti_4719_*`) is the benchmark Europris itself quotes as "broad variety retail (Statistics Norway)" (NW 637305, 658269). Its first two months are published before Europris reports, which makes it a strong 0–1 quarter predictor of sales growth.

---

## 4. Cross-border shopping, NOK/SEK, and the COVID border closure
**Mechanism.** Norwegians shop groceries, candy and snacks, and alcohol in Sweden. When border trade stops, demand moves to Norwegian stores, especially in central eastern Norway. A weaker NOK vs SEK makes Sweden less attractive.

**Evidence: COVID.**
- Q2 2020: *"the closure of the frontier with Sweden has led to increased sales because of the temporary halt to cross-border shopping"* (NW 509653).
- Q3 2020: *"The best performance was in the central part of eastern Norway, which has benefited most from the disappearance of cross-border trade"*, and *"Travel outside the country has virtually ceased, with the exception of some regions in Sweden for certain periods"* (NW 516777).
- Q4 2020: geographic growth *"greatest in the central part of eastern Norway, where the absence of cross-border trade has increased demand"* (NW 523770).
- Q3 2021: Norway *"ended all infection control measures in late September and fully opened the borders to Sweden early October"* (NW 545906).
- Q4 2021: *"restrictions were reimposed in mid-December, including restrictions making it less attractive to cross the border"* (NW 552536).
- Q1 2022: *"the lifting of all restrictions from the middle of February this year led to increased cross border shopping ... The Europris stores closest to the Swedish border have experienced larger declines in sales than the chain average"* (NW 560306).
- Q2 2022: *"progress for the four stores closest to the Swedish frontier was weaker than the chain average"* (NW 566962).
- Q3 2021: candy and snacks are a category *"exposed to cross-border trade"* (NW 545906).

**Evidence: NOK/SEK and Swedish VAT.**
- SSB (12 May 2026, https://www.ssb.no/varehandel-og-tjenesteyting/varehandel/statistikk/grensehandel/artikler/grensehandelen-holdt-seg-stabil-i-1.kvartal-2026): *"En sterk svensk krone gjør det mindre lønnsomt for nordmenn å handle i Sverige"* ("A strong Swedish krona makes it less worthwhile for Norwegians to shop in Sweden").
- The same article reports that Swedish authorities cut VAT on food from 1 April 2026, which matters for cross-border shopping from 2026Q2.
- SSB day-trip data (repo series `ssb_crossborder_daytrips_old`, table 08460) show a collapse in same-day trips. For example, 2020Q2 was 38k trips against 1,895k in 2018Q2 and 2,579k in 2019Q2.
- Trips were still 31–46% below the 2018–19 average for the same quarter throughout 2022, even after restrictions ended. That points to lasting behaviour change and NOK/SEK effects, not policy.

**Priors.**
- `covid_border_restrictions` → sales **+**, lead 0. Remove the closure from the estimation sample, or dummy it. Expect large negative base effects in the following year: 2021Q3–2022Q2 year-on-year growth.
- NOK/SEK (`mkt_nok_per_100sek_avg`), higher value meaning a weaker NOK: Norway sales **+**, lead 0–1, small outside border regions.
- SSB day trips: **−** for Europris sales, lead 0. SSB publishes about 6–8 weeks after the quarter, so this is a nowcast or lagged use only.
- NOK/SEK also affects the *group* via translation of segment Sweden (NOK 1,020–1,283m a quarter in 2025). Use **segment Norway** for the target.

---

## 5. Seasons and weather
Europris is a "seasonal champion". Weather comments are frequent, but they only help with nowcasting (lead 0).

- **Q1 winter (cold → +, mild → −).**
  - Mild: 2017Q1 (*"warm start to the winter season"*, NW 425742), 2019Q1, 2020Q1 (*"unusually mild winter, particularly in southern Norway"*, NW 501532), 2022Q1 (NW 560306), 2025Q1 (NW 643362).
  - Cold: 2021Q1 (*"a cold winter with higher sales of seasonal goods"*, NW 531534).
  - The Q1 2022 report tabulates *"Winter season: Neutral / Neg / Pos / Neg"* for 2019–2022.
- **Q2 spring (warm → +).**
  - Warm: 2016Q2 (NW 406964), 2020Q2 (NW 509653), 2024Q2 (*"warm spring in May"*, NW 623406).
  - Cold May/June 2019 hurt *"higher-margin seasonal products"* (NW 481309).
- **Q3 summer (ambiguous).**
  - Cold July 2015 was negative (NW 389237).
  - The *exceptionally hot* summer of 2018 hurt the first half of Q3 (NW 462430).
  - The warm summer of 2025 was strongly positive: chain +12.1% (NW 658269).
  - A warm spring can pull demand forward from Q3. Q3 2016: *"A long and warm spring season resulted in consumer demand for summer products largely being satisfied ahead of the commencement of the third quarter"* (NW 412614).
- **Gross margin.** Good seasonal sell-through raises gross margin (seasonal items carry higher margin). Overstock leads to clearance and carry-overs, for example 2017Q2 (NW 431362) and 2023Q2 (NW 595225).

---

## 6. Easter and calendar effects (known years in advance; ideal short-horizon regressors)
**Management quantification.**

| Quarter | Easter effect on sales growth | Source |
|---|---|---|
| Q1 2019 | about −5% (NOK 60m) | NW 475037 |
| Q1 2025 | −4 to −5pp, including one fewer calendar day | NW 643362 |
| Q1 2026 | about +6pp group, about +7pp Norway | NW 671239 |
| Q2 2026 | about −4.5pp group, about −5.5pp Norway | NW 677868 |

Further comments:
- 2015: *"peak sales days of Easter being in March this year and April in 2014"* (NW 383379).
- 2018: *"you need to look at both the first and the second quarter combined"* (NW 449042).

**Why a 14-day window matters.** Q1 2023 (Easter 9 April) was described as boosted by an *"earlier Easter"* (NW 588704), although none of the 7 days before Easter Sunday 2023 fell in Q1. Easter shopping evidently starts more than a week ahead. The CSV therefore carries both `easter_week_split_q1_share` (7-day window, as specified) and `easter_window14_q1_share` (14-day window). It also carries a ready-made year-on-year regressor, `easter_q_yoy_effect14`: Δshare in Q1, −Δshare in Q2, 0 in Q3 and Q4.

**Other effects.**
- **Gross margin and EBIT.** Easter items are lower margin. Q2 2019 gross margin was hit by about 0.8pp by Easter (NW 481309). Q1 2026 Norway mix was hurt *"partly attributable to the earlier timing of Easter"* (NW 671239). Opex scale effects help EBIT: Q2 2025 opex ratio was *"positively impacted by scale effects from timing of Easter"* (NW 650986).
- **Holidays.** Maundy Thursday, Good Friday and Easter Monday are shop-closing holidays in Norway. When they fall in Q1 they remove trading days. This is column `easter_closed_days_q1`. Management notes sales-day differences often: Q1 2016 −2, Q2 2016 +3, Q1 2017 +3, Q1 2018 −2, Q2 2018 +2, Q3 2018 −1, Q4 2023 −2, Q1 2024 −2, Q2 2024 +2, Q4 2024 +1, Q1 2025 −1 calendar day. A trading-day count is a worthwhile extra control.

---

## 7. Store network, franchise takeovers and acquisitions (structural growth)
- **Store count.**
  - The chain had 225 stores in Q2 2015 (NW 383379) and 286 by spring 2025 (Bekkestua press release, via search).
  - The CMU 2022 reiterated the ambition to *"expand the store network by five new stores net per year"* (NW 577619).
  - The board pre-approves the pipeline. Q3 2020, for example: *"The board has approved an additional eight stores for 2020 and beyond"* (NW 516777). The pipeline is therefore a 1–4 quarter-ahead predictor of **total** sales growth, but not of like-for-like growth.
- **Franchise takeovers.** Franchise stores buy at wholesale. Taking a store over moves retail sales into group revenue and raises gross margin and opex. Q3 2017: *"positive effects resulting from franchise takeovers"* on gross margin (NW 437631). Takeovers: 8 in Q1 2017 (NW 422931); 15 in the twelve months to Q3 2017; 8 in 2018; 4 in 2019 (NW 468352, 494202).
- **Pure-play acquisitions**, part of segment Norway (NW 630818: *"The Norway segment includes Europris and the pure play companies Lekekassen, Strikkemekka and Lunehjem"*; by Q2 2026 only Lekekassen and Strikkemekka are listed). Their gross margin is dilutive (*"gross margin was somewhat diluted by the margin from acquired companies"*, NW 560306).

  | Company | Consolidated from | Source |
  |---|---|---|
  | Lunehjem | March 2021 | NW 545906 |
  | Lekekassen (67%) | 1 Aug 2021 | NW 545906 |
  | Strikkemekka | 1 Jul 2022 | NW 574601 |
  | Remaining 33% of Lekekassen | bought Q1 2023 | NW 588704 |

---

## 8. Competition
- **Grocery chains are the most-cited competitive pressure.**
  - 2016Q1: *"the 'price war' initiated by the grocery retailers on pick & mix candy"* (NW 401937).
  - 2018Q2: personal care and laundry *"increased price competition, especially from the grocery sector"* (NW 455545).
  - 2023: *"fierce price competition"* on consumables and Easter items (NW 588704, 595225, 609575).
  - Q4 2024: *"consumables were negatively impacted by intense price competition from grocery stores"* (NW 637305).
  - Prior: gross margin **−**, contemporaneous. A small negative for like-for-like.
- **Variety discounters.**
  - Europris benchmarks itself against *"Clas Ohlson, Nille, Jysk, Biltema, Coop OBS, Normal, Rusta and Jula"* (MediaCom brand tracker, CMU 2022, NW 577619).
  - CMD 2018 market shares (Virke/Proff) list Biltema, Clas Ohlson, Jula, Nille and Rusta as the main discount-variety peers (NW 465054).
  - **Rusta** entered Norway in Oct 2014 and had about 25 stores in 2018, 30 in 2019 and 37 in 2021. Source: Rusta press releases on mynewsdesk, seen via search summaries; the page returned 403.
  - **Normal** opened its first Norwegian store in 2017 and now has about 198–200 stores (finn.no job ads, via search).
  - **Euromonitor** (June 2026, https://www.euromonitor.com/general-merchandise-stores-in-norway/report): *"Europris's share declined from 67% in 2020 to 64% in 2025"*, while *"Rusta increased its share from 13% to 18%"*, and *"exit of Dollarstore in 2026"*.
  - **Action**: no evidence that it has entered Norway or Sweden. It had 15 countries in June 2026 and was entering Slovenia and Bulgaria (search summaries of retail-news.de and RetailDetail, 2026).
  - **Søstrene Grene and Flying Tiger**: no Europris commentary found.
- **Prior.** Competitor entry is gradual and hard to date, so no reliable quarterly variable exists. Treat competition as a slow-moving trend or a dummy for grocery price-war episodes. Do not include it in the top-5 screen.

---

## 9. Structural breaks and controls needed (all in `data/events_quarterly.csv`)
- **IFRS 16 (`ifrs16` = 1 from 2019Q1).** EBITDA jumps; prior-year figures were not restated (NW 488371). Model EBIT, or EBITDA excluding IFRS 16, for continuity.
- **ÖoB.**
  - The 20% stake was an associate from 13 Dec 2019 (NW 491657).
  - Full ownership closed 2 May 2024 (NW 617600). Segment Sweden is consolidated *"with effect from 1 May 2024"* (NW 630818).
  - `oob_consolidated` = 1 from 2024Q2, a partial quarter.
  - Group totals after this point are not comparable. Use *segment Norway* (organic), which Europris reports as "organic" for 2024 and as segment Norway from 2025.
- **COVID.**
  - `covid_border_restrictions` is a judgement score. Policy facts come from the Europris releases quoted in §4. It is cross-checked against the SSB 08460 day-trip collapse versus the 2018–19 same-quarter average, and against the OxCGRT C8 international-travel index.
  - Values: 2020Q1 0.2, Q2 1.0, Q3 0.9, Q4 1.0; 2021Q1 1.0, Q2 1.0, Q3 0.6, Q4 0.25; 2022Q1 0.25; 0 otherwise.
  - Rationale: closure from mid-March 2020; *"virtually ceased"* travel in Q3 2020 *"with the exception of some regions in Sweden"*; reopening for vaccinated travellers over summer 2021; full opening early October 2021; restrictions reimposed mid-December; everything lifted mid-February 2022. The SSB day-trip drops were −40%, −98%, −93%, −96%, −98%, −98%, −67%, −67% and −46% respectively.
  - `covid_domestic_lockdown` is the OxCGRT Stringency Index for Norway (quarterly mean ÷ 100). Source: https://github.com/OxCGRT/covid-policy-dataset, file `OxCGRT_compact_national_v1.csv`. It is set to 0 from 2022Q2, after all measures were lifted on 12 Feb 2022.
  - Europris-specific store closures: 25 stores from 23 Jan 2021 (NW 523084); about 30% of stores from 16 Mar 2021 (NW 527864); an average of 10% closed in Q1 2021 and 8% in Q2 2021 (NW 531534, 538131).
- **Stocktaking timing (gross-margin noise in Q3 and Q4).** The annual stocktaking true-up was booked in Q3, or Q4 when delayed:

  | Year | Quarter booked | Effect |
  |---|---|---|
  | 2014 | Q4 | +NOK 25.4m |
  | 2018 | Q3 | +24m |
  | 2020 | Q4 | +21.5m |
  | 2021 | Q4 | +24.2m |
  | 2022 | Q3 | +2.8pp gross margin |

  From Q1 2023 the calculation differences are booked in the quarter they arise (NW 602805). Sources: NW 389237, 462430, 523770, 552536, 574601.
- **Unrealised-FX reclassification in 2016** (see §1.3). This creates a break in gross-margin volatility between 2015 and 2016.
- **Sugar tax.** Increase from 1 Jan 2018 (+NOK 5m in Q1 2018; about 12m of savings in total). Reduction from 1 Jan 2019 (one-off −NOK 8m in Q1 2019). A change from 1 Jan 2021 caused a NOK 17.9m inventory write-down in Q4 2020. Sources: NW 462430, 475037, 523770.
- **Other one-offs.**
  - 2019Q1–Q3: central-warehouse fill-rate problems. Extra opex of NOK 11m, 35m and 5m; NOK 51m for the year (NW 475037, 481309, 488371, 494202).
  - 2019Q2: supplier-bankruptcy provision (NW 481309).
  - 2018Q3: change in freight-cost recognition, NOK 14m one-off opex (NW 462430).
  - 2020Q2: removal of the NOK 350 VAT exemption on low-value imports from 1 Apr 2020. This helps domestic retail against foreign online shops; the CMD 2018 cited the *"potential removal of Norwegian toll-free limit"* (NW 465054). Source: regjeringen.no.
  - 2023Q1: hoarding ahead of 1 Feb grocery price increases (NW 588704).
- **Not found.** I found no evidence of a Norwegian food-VAT change or of retail strikes affecting Europris in 2015–2026.

---

## 10. Recommended targets for the screen
- **Sales.** Use segment Norway sales growth year-on-year (organic Europris group before 2024Q2) and Europris chain like-for-like growth. Control for Easter (`easter_q_yoy_effect14`), trading days, the COVID dummies, and the pure-play acquisition quarters (2021Q1, 2021Q3, 2022Q3).
- **Gross margin.** Use Norway gross margin *excluding unrealised FX*, using the table in §1.3. Alternatively, keep reported gross margin and add the within-quarter change in end-of-period USD/NOK as a contemporaneous regressor. Dummy the stocktaking quarters up to 2022.
- **EBIT.** Use EBIT rather than EBITDA, because IFRS 16 breaks EBITDA. Note that electricity is hedged 12–21 months ahead (opex).

## 11. Sources

**Europris releases and reports** (NewsWeb, `https://newsweb.oslobors.no/message/<id>`):
- **Quarterly reports, Q2 2015 → Q2 2026:** 383379, 389237, 394831, 401937, 406964, 412614, 420458, 425742, 431362, 437631, 443231, 449042, 455545, 462430, 468352, 475037, 481309, 488371, 494202, 501532, 509653, 516777, 523770, 531534, 538131, 545906, 552536, 560306, 566962, 574601, 581191, 588704, 595225, 602805, 609575, 616738, 623406, 630818, 637305, 643362, 650986, 658269, 664387, 671239, 677868.
- **Annual reports 2015 → 2025:** 399674, 423726, 449045, 473112, 499571, 529162, 557584, 586084, 613923, 641912, 668777.
- **Capital Markets Day 2018:** 465054. **Capital Markets Update 2022:** 577619.
- **COVID updates:** 498533, 508306, 523084, 523700, 527864.
- **Transactions:** ÖoB 453844, 491657, 606982, 609555, 614254, 617600; Lekekassen 537165.

**Other sources:**
- Company presentation, January 2024: https://s21.q4cdn.com/815767348/files/doc_events/2024/01/1/2024-01-europris-company-presentation.pdf
- SSB:
  - Border-trade article, Q1 2026 (link in §4).
  - StatBank table 08460: https://www.ssb.no/en/statbank/table/08460
  - "Redusert grensehandel ga økt handel i Norge i koronaåret 2020": https://www.ssb.no/varehandel-og-tjenesteyting/artikler-og-publikasjoner/redusert-grensehandel-ga-okt-handel-i-norge-i-koronaaret-2020 (search summary only)
- OxCGRT: https://github.com/OxCGRT/covid-policy-dataset
- Euromonitor: https://www.euromonitor.com/general-merchandise-stores-in-norway/report
- Press and analysts:
  - DNB upgrade, 10 Dec 2024, citing *"förbättringen av bruttomarginalen i Norge"* ("the improvement in the gross margin in Norway"): https://www.aktiespararna.se/nyheter/europris-rusar-efter-dnbs-hojning-till-kop
  - Pareto, 10 Jul 2026: *"Den tidigare påsken tyngde det andra kvartalet"* ("The earlier Easter weighed on the second quarter"): https://www.placera.se/telegram/europris-pareto-securities-sanker-riktkursen-men-upprepar-kop-ny-20260710
  - Placera, 9 Jul 2026: gross margin 42.4% vs consensus 41.2% (search summary): https://www.placera.se/telegram/europris-europris-resultat-lagre-an-vantat-20260709
  - Finansavisen headline, 31 Oct 2024, *"Svak krone og høye kostnader legger press på Europris' marginer"* ("Weak krone and high costs put pressure on Europris' margins"). Seen in a search listing only (https://finansavisen.no/tema/EPR); the article was not read.
- VOEC / NOK 350 limit: https://www.regjeringen.no/no/aktuelt/na-fjernes-350-kronersgrensen-ved-handel-fra-utlandet/id2682933/ (search summary)

**Blocked or unavailable.** The following could not be read:
- investor.europris.no (known blocked; not used)
- DN articles (paywall or SSO redirect)
- dnb.no news articles (returned a security.txt stub)
- financialfilings.com transcript (403)
- rusta.mynewsdesk.com (403)

Capital-markets material was taken from the NewsWeb attachments instead (NW 465054, 577619). No call transcripts were obtained, and the Quartr connector was not authorised.
