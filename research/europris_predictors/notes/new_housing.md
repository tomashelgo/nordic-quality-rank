# New candidate: housing activity (key `housing`)

Task key `housing`. Written 2026-10-12, **before** running `scripts/test_new.py`. The results section at the end was added after the single run, and nothing above it was changed afterwards.

## Question

Does housing-market **activity** predict the Norwegian business's sales growth, LFL, gross-margin change (ex unrealised FX) or adjusted EBIT-margin change 1–8 quarters ahead? Activity means the number of moves, not prices: house prices (`ssb_house_price_idx_total_nsa`) and dwelling starts (`ssb_dwelling_starts_sa`) are already in `scripts/candidates.py` and are not repeated here.

**Mechanism.** A move triggers purchases of home, interior, garden, storage, cleaning and DIY goods, a large part of Europris's non-food range. Buyers furnish and fix up the new home, and sellers buy boxes, cleaning and small repairs. These purchases continue for several quarters after take-over. Completed new dwellings add households moving into empty homes.

## Sources

**Eiendom Norge monthly main reports (Hovedrapport).**
- 81 free PDFs, January 2020 to September 2026, from the "Statistikkbank – Månedsrapporter" page on eiendomnorge.no. Each is downloaded with the site's own download button, which works without login.
- Only the files marked as free were downloaded: "Hovedrapport", with `data-have-access="true"`. The subscriber Excel files (Volum/Solgte, Lagt ut for salg, Usolgte, Omsetningstid) were **not** accessed.
- The statistic is produced by Eiendomsverdi AS from broker-confirmed sales of homes advertised on FINN.no. It includes housing co-op (borettslag) units, but it is not a census.
- It is published at 11:00 on the third working day of the following month. For example, the September 2026 report came out on 5 Oct 2026.

**SSB StatBank (PxWebApi v0, json-stat2).**
- Table **08968**: registered sales ("omsetninger med hjemmelsoverføring") of dwelling properties with building in free sale, whole country, all dwelling types. Quarterly, 2000K1–2026K2.
- Table **03723**: dwelling building statistics, whole country, all building types. Monthly, 2000M01–2026M08. Used for:
  - completed dwellings (`BoligerFullf`);
  - dwellings under construction (`BoligIArbeid`).
  - The starts (`BoligIgang`) in the same table are already in the project and are not used.

**Where files are kept.** Raw downloads are in the scratchpad `new/housing/dl/` (`dl/ssb_*.json`, `dl/en/pdf/main_<articleid>.pdf`, `dl/en/txt/`). Scripts are in `new/housing/scripts/`:
- `jsonstat.py`
- `extract_en.py`, which reads the PDFs with pdfplumber
- `validate_en.py`
- `build_series.py`

## Construction

| series_id | What it is | Coverage |
|---|---|---|
| `new_housing_en_sold` | Homes sold per month (Eiendom Norge "Solgte", broker-confirmed sales) | 2016-01 – 2026-09 |
| `new_housing_en_listed` | Homes newly listed for sale per month ("Lagt ut for salg"). Collected, **not tested** | 2016-01 – 2026-09 |
| `new_housing_en_dom` | Average days on market ("omsetningstid": days from first FINN ad to registered sale) | 2016-01 – 2026-09 |
| `new_housing_ssb_trans` | SSB registered dwelling-property sales per quarter (08968) | 2000Q1 – 2026Q2 |
| `new_housing_ssb_compl` | SSB dwellings completed per month (03723) | 2000-01 – 2026-08 |
| `new_housing_ssb_compl12` | Rolling 12-month sum of the above | 2000-12 – 2026-08 |
| `new_housing_ssb_uc` | SSB dwellings under construction, stock (03723 "under arbeid") | 2000-01 – 2026-08 |

### How the Eiendom Norge figures were extracted

The free main report shows three kinds of figures.

**Key-figure sentences ("Nøkkeltall").** These give the month's number sold and listed with the y/y %, and the month's days on market together with the same month a year earlier.

**Bar charts ("Solgte" and "Lagt ut for salg").** Each shows the **same calendar month for the last 5 years** in 2020 reports, and the last 6 years in later reports, with the printed value on each bar. The January–December 2020 reports therefore give every month back to January 2016.
- Values are read from the PDF text layer.
- Later layouts print every label twice, 11–15 pt apart. The duplicates are removed, and each value is assigned to the nearest year label.

**Days-on-market line chart.** It has one coloured line per year for 5 years, with printed data labels.
- Each year's line is read from the vector polyline. Lines are matched to years through the legend colours.
- Positions are converted to days with a linear fit on the y-axis tick labels.
- Each point is then snapped to the printed data label within ±1.6 days in the same month column.
- 98.7% of points matched a label. The remaining 1.3%, mostly July points where labels overlap, use the rounded axis estimate, which is within about ±1 day.

**Validation**, done with `validate_en.py`:
- The current-month bar equals the key-figure number in all 81 reports, for both sold and listed.
- The y/y % implied by the previous-year bar matches the printed y/y % in 80 of 81 reports. The exception is January 2022, where the printed −22.0% compares with −21.5% computed. The base was apparently revised.
- **Across vintages,** 105 of 129 months appear in more than one report. Their maximum spread is 1.9%, from late-registered sales in July and December. In January 2024 Eiendomsverdi re-estimated the history, including volumes, and the cross-vintage check shows only small changes.
- **Days-on-market chart vs printed key figure in the same report:**
  - 157 of 162 identical;
  - 5 differ by 1 day, which is rounding;
  - across vintages, only 2 months differ by more than 1 day: 2018-03 (49–51) and 2020-12 (59–61).
- **Latest vintage used:** the most recent report that shows the month. Within a report, printed text is preferred over chart labels.

### SSB construction

- **08968** is used as published. It counts registered (tinglyst) title transfers of freehold dwelling properties in free sale with a known price. It **excludes housing co-op shares** (borettslag, a sizeable share of second-hand sales, concentrated in the cities) and leasehold sites. Registration happens at take-over, so the series runs about one quarter behind Eiendom Norge's sales, which are dated at the sale agreement. That is visible in the data. The SSB series is close to the actual move date.
- **Completions** are lumpy month to month, because municipalities register completion certificates in batches. The candidate therefore uses the **rolling 12-month sum**. g4 of that is the growth of the last 12 months' completions against the 12 months before, measured at the quarter's last three months. This was chosen before testing.

### Release lags and real-time use (`typical_release_lag_days`)

| Series | Lag (days) | Effect at the 45-day origin |
|---|---|---|
| Eiendom Norge | 5 | Whole quarter known |
| SSB 03723 | 14 | Whole quarter known. 2026M08 was published on 2026-09-14 |
| SSB 08968 | 60 | Quarter *t* not yet published (2026K2 came out on 2026-08-27, day 58), so the feature at origin *t* uses quarter *t−1* |

## Pre-registered candidates (5 features)

Spec: `data/new/housing_spec.csv`. The signs and leads below were set from economics before any test was run.

| feature | prior sales/LFL | prior gm_d4 / ebitm_d4 | expected lead |
|---|---|---|---|
| `hs_en_sold__g4`: homes sold (Eiendom Norge), y/y log growth | **+** | **+** | 1–3q |
| `hs_ssb_trans__g4`: registered dwelling sales (SSB), y/y log growth (uses *t−1*) | **+** | **+** | 1–4q |
| `hs_en_dom__d4`: days on market, y/y change in days | **−** | **−** | 1–4q |
| `hs_compl12__g4`: completions, 12-month sum, y/y log growth | **+** | ? | 1–6q |
| `hs_uc__g4`: dwellings under construction, y/y log growth | **+** | ? | 4–8q |

**Reasoning.**

*Sales and moves → sales/LFL "+".* More transactions means more households moving. Both buyer and seller buy home, storage, cleaning, garden and DIY goods around the move and while furnishing over the next 1–3 quarters. The SSB series is dated near take-over, so its spending effect is closer in time, but it is published a quarter late.

*Sales and moves → margins "+".* The extra demand falls on non-food home, interior and seasonal categories, which carry higher gross margins than consumables and food. A busy housing market also coincides with confident households and less dependence on campaigns. EBIT margin should follow through mix and operating leverage on LFL. This is a weak prior.

*Days on market "−" / "−".* Rising time-to-sell signals a cooling market: fewer moves ahead, falling price expectations and cautious households. That means less non-food and more campaign- and consumables-driven trade, which pressures gross margin. Days on market is also a known leading indicator of house prices, and house prices already predict LFL 1–2 quarters out, so a lead of 1–4 quarters is expected.

*Completions "+", margin "?".* Each completed new dwelling is a household moving into an empty home, with heavy first-year purchases. The effect should appear within about a year (1–6 quarters, given lumpy registration). The margin channel is the same mix argument, but it is diluted and timed uncertainly, so the margin prior is "?".

*Dwellings under construction "+", margin "?".* The stock under construction is the pipeline of completions over the next 1–2 years, so it should lead Europris sales by 4–8 quarters through future moves. This is the only candidate pre-registered for the long horizon. It differs from the already tested starts flow: it is a stock that integrates starts over the build time, net of completions. The margin prior is "?" for the reasons given for completions.

**Not tested (documented to avoid hidden multiplicity):**
- Newly listed homes (`new_housing_en_listed`) was collected but not put in the spec. Its sign is ambiguous, because listings rise both with mobility and when the market stalls.
- Unsold stock is only published as a daily-line chart and in subscriber Excel files, so it was not collected.

## Data caveats

1. **Short Eiendom Norge history.** The free archive starts in January 2020, and the charts take it back to January 2016. The g4 and d4 features therefore start in 2017Q1, about 76% of the Europris sample. No pre-2015 values exist, so the **pre-2015 category-proxy check ("pxpre") is impossible** for `hs_en_sold` and `hs_en_dom`. Under the strict rule they cannot be shortlisted for sales or LFL, only for margins. The SSB series run from 2000 and get the full proxy test.
2. **Latest vintages.** Eiendom Norge volumes were re-based in January 2024, though the change is small (≤1.9% between vintages). SSB completions are registered late and revised up for months afterwards, so the recent months of `ssb_compl12` and `ssb_uc` are understated in real time. Late completion registration also leaves dwellings too long in "under construction".
3. **Easter.** Easter moves housing sales between March and April: Eiendom Norge sales were −20% y/y in March 2024 and +43% in April 2024. Quarter averages remove most of it, but a Q1/Q2 Easter shift still leaves a few percent in g4. The benchmark controls Europris's own Easter effect, not this one.
4. **COVID.** 2020–21 housing turnover boomed, which overlaps the border-closure quarters. Those quarters are excluded or controlled by the harness.
5. **SSB 08968 excludes borettslag.** The most recent two quarters are preliminary.
6. **Chart extraction.** Days on market for 2016–2018 rests only on chart labels, with no printed key figures for those years. The validation above bounds the error at about 1 day.

---

## Results (added after the single run on 2026-10-12; nothing above was changed)

**The run.**
- Command: `python3 scripts/test_new.py data/new/housing_spec.csv`
- 5 features × 4 targets × 6 horizons = 120 rows. No feature was dropped for coverage.
- The screen is saved in the scratchpad as `new/housing/screen.csv`.
- No data error was found afterwards, so there was no rerun.

**Family calibration.**
- **Primary spec:** 56 tests with n ≥ 15, of which 3 have p ≤ 0.05 (5.4%). That is exactly the rate chance produces.
- **Strict shortlist:** 1 pass against about 0.2 expected by chance, out of 44 eligible tests.
- **Control spec (COVID quarters kept):** 10 of 120 have p ≤ 0.05, all with the prior sign. All 10 come from two features, SSB transactions and days on market. In each case the primary spec is either insignificant or cannot be estimated.

| feature → target, h | primary t / p (n) | control t / p (n) | other checks | verdict |
|---|---|---|---|---|
| `hs_ssb_trans__g4` → LFL, h=8 (**the one strict-shortlist pass**) | +3.20 / 0.019 (15) | +0.51 / 0.67 | proxy p 0.47, pre-2015 p 0.79; holdout (control) −0.57; same feature at h=4 has t −2.65 (p 0.019) and sales at h=3 has t −2.83 (p 0.047), both against the prior | chance |
| `hs_ssb_trans__g4` → EBIT-margin change, h=3 / h=4 | +1.56 / 0.12 (14); +0.63 / 0.57 (13) | **+5.40 / 0.001; +4.63 / 0.004** (30) | holdout (control) −1.72 / −1.36; gross margin h=1 / h=4 control p 0.04 / 0.05 with primary p 0.98 / 0.27 | significance comes only from COVID-era quarters; not robust |
| `hs_en_dom__d4` → LFL, h=1 / h=3 | −0.87 / 0.39 (15); n/a (11) | −2.31 / 0.039; −2.99 / 0.043 | proxy n/a (starts 2016); holdout +0.17 / +0.20 at h=1, −0.19 at h=3 | right sign but only in the control spec. Correlation with house-price growth is −0.85, so this is mostly the known house-price signal |
| `hs_en_dom__d4` → EBIT margin, h=1 / h=4; gross margin, h=4 | −0.66 / 0.59 (15); n/a | −3.41 / 0.031; **−5.93 / 0.001**; −2.64 / 0.021 | holdout (control) −0.07 / −3.48 / −0.32 | control-spec only, few observations, bad holdout |
| `hs_en_sold__g4` (all targets) | best p 0.18 | best p 0.14 | holdout ≈ 0 | null |
| `hs_compl12__g4` (all targets) | best p 0.12; the sales/LFL sign is mostly **negative**, against the prior | best p 0.12 | holdout negative | null |
| `hs_uc__g4`, the 4–8 quarter candidate (all targets) | sales/LFL p ≥ 0.36 at every horizon | p ≥ 0.31 | pre-2015 proxy p ≥ 0.62; holdout ≈ 0 | null |

**Conclusion.**
- No housing-activity variable is supported. None reaches even the README's "fragile" grade, which requires significance in both COVID treatments.
- Neither the number of moves (Eiendom Norge sales, SSB registered transactions) nor new-build completions or the under-construction pipeline adds predictive power for Europris Norway beyond the benchmark (calendar, own lags, base effects, store growth, margin mean reversion), at 1–8 quarters.
- Days on market behaves like a timelier version of house-price growth, which is already tested, and has no independent value on this sample.
- The pre-registered long-horizon candidate (dwellings under construction) shows no signal at 4–8 quarters.
