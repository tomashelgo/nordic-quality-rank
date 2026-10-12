# New candidate: Europris's own inventory (key `inventory`)

Task key `inventory`. Written 2026-10-12, **before** running `scripts/test_new.py`. The results section at the end was added after the single run, and nothing above it was changed afterwards.

## Question

Does Europris's own stock position at the end of quarter *t*, published about 45 days later, predict the Norwegian business's sales growth, LFL, gross-margin change (ex unrealised FX) or adjusted EBIT-margin change 1–8 quarters ahead?

## Sources

- **Quarterly interim reports Q2 2015 to Q2 2026**, all 45 of them, downloaded fresh from the Oslo Børs NewsWeb API (`/v1/newsreader/attachment?messageId=..&attachmentId=..`) and converted with `pdftotext -layout`. The report message ids are the ones listed in `notes/drivers_and_hypotheses.md` §11 (383379 … 677868).
- **Annual reports** 2015 (NW 399674), 2024 (NW 641912) and 2025 (NW 668777), used only for cross-checks: the year-end inventory, the segment inventory and the obsolescence provision.
- **Release bodies** (`/v1/newsreader/message?messageId=`), used for management commentary.
- **COGS** comes from the project's verified company panel, `data/europris_norway_quarterly.csv`: total operating income minus key-figure gross profit excluding unrealised hedge FX. This is the same base the `gm_d4` target uses.
- Raw files are kept outside the repo, in the scratchpad `new/inventory/dl/{pdf,txt,msg}`. The scripts are in `new/inventory/scripts/` (`extract_inventory.py`, `build_series.py`).

## Construction

| series_id | What it is | Coverage |
|---|---|---|
| `new_inventory_group_bs` | Consolidated balance-sheet "Inventories", NOK m, latest reported vintage | 2014Q2–2026Q2 |
| `new_inventory_norway` | **Norwegian-business inventory**: the group balance sheet up to 2024Q1, when ÖoB was not consolidated (an associate), then **segment Norway** from Note 4 "Segment information" from 2024Q2 | 2014Q2–2026Q2 |
| `new_inventory_norway_cogs_q` | Norwegian-business COGS excluding unrealised FX, per quarter | 2014Q1–2026Q2 |
| `new_inventory_norway_dio` | Days of inventory: quarter-end stock / LTM COGS × 365 | 2014Q4– |
| `new_inventory_norway_dio4q` | Days of inventory on **average** stock: mean of the last 4 quarter-end stocks / LTM COGS × 365 | 2015Q1– |
| `new_inventory_norway_excess` | Excess inventory growth: 100·ln(inv_t/inv_t−4) − 100·ln(LTM revenue_t / LTM revenue_t−4), in pp | 2015Q4– |

**Extraction checks.**
- Every quarterly report gives three balance-sheet columns: the current quarter end, the same quarter a year earlier and the previous year end. Each date is therefore read from 1 to 5 different reports.
- All readings agree to the NOK thousand, with two exceptions:
  - **2021Q4:** 1,999.1 first published, restated to 1,997.3. This is presumably the Lekekassen purchase-price allocation.
  - **2024Q4:** the group figure was 3,262.3 first and 3,292.3 restated, an ÖoB purchase-price-allocation change. The 2024 annual report shows the restatement sits in Sweden (777 → 807). **Norway stays at 2,485.**
- The latest vintage is used. For the Norway series this matters only for 2021Q4 (−1.8m).
- Two PDF-text artefacts ("1 761,113" in Q3 2019 and "1 ,711,699" in Q2 2022) are parsed correctly, and the cross-report agreement confirms them.

**The ÖoB break.**
- Segment Norway inventory has been disclosed since the Q2 2024 report: 2,332 / 2,645 / 2,485 / 2,747 / 2,584 / 2,844 / 2,584 / 2,742 / 2,429 for 2024Q2–2026Q2.
- Norway plus Sweden equals the consolidated balance sheet within rounding, with no elimination column.
- Before 2024Q2 the group was the Norwegian business, so the series has no break. The segment figures are rounded to NOK 1m.
- The YE2025 Norway figure of 2,584 equals the Q2 2025 figure. The 2025 annual report confirms it, so this is a coincidence and not a copy error.

**The COGS cross-check.**
- Panel COGS ex FX minus unrealised FX matches the reported segment-Norway COGS for 2024Q2–2026Q2 within NOK 1m.
- It also matches reported group COGS for 2015Q2 (607.5), 2016Q1 (605.2) and 2019Q1 (732.1).
- LTM COGS for 2019 (3,523 ex FX, 3,544 incl. FX) matches the 2019 annual report figure in `drivers_and_hypotheses.md` §1.2.

**Release timing.** `typical_release_lag_days = 45`, the report lag, so stock at the end of *t* is known at the forecast origin of *t*. The 2014Q2–2015Q1 values were only published as comparatives in 2015–16, because the IPO was in June 2015. As with the rest of the Europris panel, they are treated as if known 45 days after the quarter. 2014Q1 is not available.

## Pre-registered candidates (4 features)

Spec: `data/new/inventory_spec.csv`.

| feature | prior sales/LFL | prior gm_d4 / ebitm_d4 | expected lead |
|---|---|---|---|
| `inv_nor__g4`: Norway inventory, y/y log growth | **+** | **−** | sales 1–2q; margins 1–4q |
| `inv_excess__lvl`: inventory growth − LTM sales growth | ? | **−** | margins 1–4q |
| `inv_dio__d4`: days of inventory (quarter-end), y/y change | ? | **−** | margins 1–4q |
| `inv_dio4q__lvl`: days of inventory on 4-quarter average stock, level | ? | **−** | margins 2–8q (slow) |

**Why the margin priors are negative.**

1. **Stock beyond what sells has to be cleared.** Clearance means campaigns and markdowns, which lower gross margin. Two episodes in Europris's own reports:
   - **Q2 2017 (NW 431362).** *"The mild winter resulted in surplus stock of seasonal items, which will be held in the stores and at the central warehouse until the next winter season."* The quarter had high campaign sales and lower gross margin. Q3 2017 (NW 437631) followed with *"measures to reduce excess inventory in-store"*, and Q4 2017 (NW 443231) with *"Sales from wholesale to franchise stores temporary affected by planned inventory reduction"*.
   - **Q2 2023 (NW 595225).** *"Seasonal carry-overs from last year's summer period also affected the gross margin negatively, reflecting higher costs in the old freight agreement and campaign activities to support sales volumes."* Q4 2023 (NW 609575) adds: *"2022 was negatively affected by seasonal summer overliers"*.
2. **Seasonal carry-overs wait for the same season next year.** This is why the expected lead runs to 3–4 quarters and not only 1.
3. **Obsolescence write-downs.** The provision rose from 26.6m to 86.6m in 2024, partly because ÖoB joined (2025 annual report, note 19).
4. **EBIT margin also carries the cost of holding stock.** Q1 2019 (NW 475037): *"logistical costs rose by NOK 11 million owing to the high fill-rate at the central warehouse"*, linked to *"excessively high inventory levels for the base range in some categories"*. Hence the same "−" prior for `ebitm_d4`.
5. **Literature.** Bernard & Noel (1991, *Journal of Accounting, Auditing & Finance*) report that retailers' inventory build-ups precede lower margins, even though they also precede higher sales. Abarbanell & Bushee (1997) find that the "inventory signal" (inventory growth minus sales growth) predicts lower future earnings. Kesavan, Gaur & Raman (2010) find that inventory and gross margin carry information for retailer sales forecasts.

**Why the sales prior is "+" only for raw inventory growth.**

*Raw growth.* Stock is an input to sales: availability and seasonal depth support LFL. Management deliberately builds stock ahead of expected demand:
- Q1 2021: *"Inventory level is increased to meet the higher demand"*.
- Q1 2025 (NW 643362): *"a planned inventory build-up to improve service level in the stores and higher seasonal inventories"*.
- The 2025 annual report: *"Strategic investments in inventory ensured well-stocked stores"*.

Kesavan et al. (2010) also find lagged inventory positively related to retailer sales.

*Excess-stock and days measures.* Here the sign is genuinely ambiguous, so it is left as "?" (not eligible for the shortlist on sales):
- Unintended overstock signals a demand shortfall that may persist ("−").
- Clearance campaigns lift volumes ("+").

**Why `dio4q` level rather than the quarter-end DIO level.** Quarter-end stock is strongly seasonal: end-Q1 and end-Q3 DIO is typically 15–40 days above end-Q4, for example 205 vs 166 in 2017Q1 vs 2016Q4, and 206 vs 174 in 2019Q1 vs 2018Q4. A level regressor on y/y targets would mostly carry that seasonal swing. The 4-quarter-average version removes it and measures structural stock-holding. It ranged from about 134 days (2021, the COVID sales surge) to about 182 (2019 and 2022). For the quarter-end measure only the y/y change (`d4`) is used.

## Known confounders and data caveats (written before testing)

- **Inventory growth is not all "excess".**
  - Store openings and franchise takeovers raise stock: 8 takeovers in Q1 2017 and 15 in the 12 months to Q3 2017 (NW 431362).
  - The 2018–19 central-warehouse transition raised central stock: *"Net working capital in 2018 was affected by a rise in inventory levels, mainly at the central warehouse"* (Q4 2019 report, NW 494202).
  - In 2021–22 management deliberately shipped early because of supply-chain risk (*"This will probably result in higher-than-normal inventory levels in the time to come"*, Q3 2021, NW 545906).
  - In 2022 higher purchase prices and freight raised stock *value* (Q3 2022, NW 574601). Inventory is valued at cost, so freight and FX (from a weak NOK) push it up without more units.
  - **Overlap with the FX and freight story:** a high-cost-stock period is also a low-margin period. The benchmark has no FX term, so any margin signal here may partly be FX or freight in disguise.
- **COVID.** The 2020–21 sales surge collapsed DIO and the excess measure: excess was about −20pp in 2020Q2–2021Q1. The base effect then pushed excess to +12 to +20pp in 2021Q4–2022Q3. Those origins mostly fall in the COVID-excluded scoring window, but 2022Q2–Q3 origins are scored. This is also the 2022→2023 carry-over episode.
- **Acquisitions.**
  - The pure-play web shops add stock and sales: Lunehjem from March 2021, Lekekassen from August 2021, Strikkemekka from July 2022. They are small, and no separate inventory is disclosed.
  - ÖoB is excluded via the segment note from 2024Q2, but its stock (860m at acquisition) is not in the Norway series.
- **COGS** includes the stocktaking true-ups booked in Q3 or Q4 up to 2022 (±20–25m). These are minor relative to LTM COGS of 3–6bn.
- **Vintages.** The latest vintage is used. The only restatement affecting the Norway series is 2021Q4 (−1.8m).
- **Sample.** With 4 features × 4 targets × 6 horizons and about 20 scored quarters, some p ≤ 0.05 cells are expected by chance. The harness reports the expected count.

---

## Results (one run of `scripts/test_new.py data/new/inventory_spec.csv`, 2026-10-12)

**Run details.**
- The screen is saved as `results/new_candidates_screen.csv`. Other agents overwrite that file, so a copy is kept in the scratchpad at `new/inventory/screen.csv`.
- I made no data fixes and no second run. The transforms and priors are unchanged.
- **Headline: null for the pre-registered hypothesis.** The strict shortlist has 0 passes, against about 0.2 expected by chance (30 eligible tests).

**Calibration.**
- 50 cells have at least 15 primary-spec observations. Of these, 5 have p ≤ 0.05, and all 5 are sales cells.
- None of the 22 margin cells reaches p ≤ 0.05.
- 64% of the margin cells have the predicted negative sign.

### Margins (the pre-registered "−" hypothesis): not supported

**Gross margin at h=1.** All three growth-type measures have the predicted negative sign. The primary spec just misses: p 0.07–0.08, t about −2.2. Without 2016 the t-stat is about −2.5.

| Measure | Primary p | Primary t | Control p | Holdout R² (primary / control) |
|---|---|---|---|---|
| `inv_dio__d4` | 0.068 | −2.16 | 0.44 | −0.45 / −0.17 |
| `inv_excess__lvl` | 0.074 | −2.17 | 0.41 | −0.45 / −0.18 |
| `inv_nor__g4` | 0.083 | −2.20 | 0.98 | −0.43 / 0.00 |

The primary-spec CV R² is +0.33 for all three, but the control-spec CV R² is −0.53 to −1.10. The control spec is far weaker and the holdout R² is zero or negative (at most +0.004). Direction consistent with the carry-over story, but not detectable.

**Gross margin at h=2–4.** Nothing: p ≥ 0.33 for the growth-type measures. `inv_dio4q__lvl` has the **wrong** (positive) sign at h=3–4 (p 0.067 and 0.068), and the control-spec sign is negative.

**EBIT margin.**
- h=1–3: negative signs, p ≥ 0.09.
- h=4: the **wrong** (positive) sign with n=13 (`inv_nor__g4` p 0.031, `inv_excess__lvl` 0.027, `inv_dio__d4` 0.027). Control p is 0.41–0.79 and the holdout is negative (4 quarters). Treat this as noise.
- No inventory measure works at 4+ quarters for either margin.

### Sales (exploratory: priors "?", except "+" for `inv_nor__g4`)

**Revenue growth at h=3.** Strong in-sample *negative* effect:

| Measure | Primary t | Primary p | BH q | Control p | Without 2016 t |
|---|---|---|---|---|---|
| `inv_excess__lvl` | −4.7 | 0.0003 | 0.004 | 0.027 | −3.9 |
| `inv_dio__d4` | −4.2 | 0.0008 | 0.006 | 0.17 | — |
| `inv_nor__g4` | −3.4 | 0.022 | — | — | — |

The `inv_nor__g4` sign is the **opposite** of its "+" prior. Even so, I do **not** believe the h=3 effect:
1. It is absent in LFL at the same horizon (p 0.62–0.72).
2. It is absent at h=2 and h=4.
3. It has no category-proxy support (p_px 0.53–0.59).
4. It **fails the holdout badly** (R² −1.65 / −1.51 for excess). High excess stock in 2024Q3–2025Q1 (+8 to +14pp) was followed by strong sales: log y/y revenue growth of +11.1 in 2025Q2, +10.9 in 2025Q3 and +4.5 in 2025Q4.
5. In-sample it rests on the Q1-stock → Q4-sales pairs (2017, 2019) and a horizon-specific seasonal alignment.

**LFL at h=1.** `inv_nor__g4` has p 0.030 with the "+" prior and is robust without 2016 (t 2.35). However:
- control p is 0.39;
- CV R² is −0.35;
- holdout R² is −0.04 / +0.09;
- p_px is 0.23;
- the shortlist rule needs a pre-2015 proxy sign, which cannot exist for a series that starts in 2014.

Too weak to use.

**`inv_dio4q__lvl` on sales.**
- The control spec gives negative LFL and revenue effects at h=2–4 (p 0.008–0.03), and the category proxy p is 0.005–0.006 at h=2–3.
- The primary spec is weak (LFL h=3 p 0.035; revenue p 0.25–0.49), and the sign **flips** to positive at LFL h=6 (p 0.005). The holdout is negative.
- This looks like the COVID episode, when the sales surge collapsed days-of-inventory and then reversed. It is not a stable relation.

### Assessment

Europris's inventory, measured in growth, excess-over-sales or days-of-inventory terms, does **not** add predictive power over the v3 benchmark for any target at the pre-registered horizons. The management anecdotes (2017Q2 and 2023Q2 carry-overs) are real but too few and too confounded to be detected:
- the 2017 stock jump coincided with franchise takeovers;
- the 2022 build-up was partly deliberate early shipping, plus higher unit costs from freight and a weak NOK.

The only directionally consistent signal is a small, insignificant negative next-quarter gross-margin effect. Inventory is not a 4+ quarter predictor.
