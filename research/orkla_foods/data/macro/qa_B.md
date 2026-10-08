# QA-B: macro series in NO/, SE/, WAGES/

QA run on 2026-10-06 (label qa-B). Scope: every series in `NO/catalog.csv` (65), `SE/catalog.csv` (50) and `WAGES/catalog.csv` (61), **176 series** in total. Scripts and downloaded files are in the session scratchpad (`scripts/qa-B/`, `dl/qa-B/`), not in the repo. A copy of the three folders as they were before any qa-B edit is also in the scratchpad (`qa-B-backup/`).

## 1. What was checked

1. **Structure**, for every file:
   - it parses, the header is exactly `date,value`, the dates are ISO and the values are numeric with no NaN;
   - dates are the first day of the period (quarters in Jan/Apr/Jul/Oct, years in January), strictly increasing, with no duplicates;
   - the frequency inferred from the dates matches the catalog;
   - there are no internal gaps (the expected number of periods between start and end equals n_obs);
   - catalog `start`, `end` and `n_obs` match the file, `file` = `series_id.csv`, and there are no orphan files or duplicate IDs.
2. **Recency.** I flagged anything ending before 2025, and I compared every end date with what the source publishes today (item 5).
3. **Plausibility.**
   - Rates are in percent, not fractions. Index and level series are positive. "Index YYYY=100" series average about 100 in the base year.
   - Outliers and rebasing jumps: robust z-score (MAD) on log changes (levels) or first differences (rates), flagged at |z| > 8 together with a change above 8% (or 1 pp). I looked at every flagged point.
   - I looked for runs of identical values and for years in which every month (or quarter) has the same value, which means annual data has been repeated.
4. **Cross-folder duplicates.** I compared each series with all 690 series in NO, SE, WAGES, EU, GLOBAL and SURVEYS.
5. **Independent re-fetch from the original sources**, compared point by point. I wrote my own queries and parsing code rather than running `fetch.py`:
   - SSB PxWeb: 59 series. This includes the 12 spliced CPI food groups (levels compared from 2000-07; earlier months compared as growth rates against closed table 03013) and the 2 spliced earnings indices (y/y compared by segment against tables 06787, 07235 and 11654/12314).
   - Norges Bank: FX, the policy rate (from daily data) and the Regional Network. Also OECD (NIBOR, 10y yield), NIBIO, NAV (csv and xlsx) and the Norges Bank Expectations Survey xlsx.
   - SCB PxWeb: all 40 SCB series in SE, plus 3 in WAGES.
   - Riksbank SWEA: I rebuilt the monthly means myself from the daily `Observations` endpoint, rather than taking `ObservationAggregates`.
   - Medlingsinstitutet PxWeb: 5 series.
   - Eurostat (4 HICPs, the `namq_10_a10`/`namq_10_a10_e` ratio, `nasq_10_ki`), ECB (INW, EWT), Statistics Denmark (SBLON1, ILON12, ILON2X, NKN3), StatFin and CZSO DataStat.
   - Energinet Energi Data Service: hourly and 15-minute prices, aggregated to months again.
   - Prospera/Origo survey spreadsheets: 28 of the 84 quarterly rounds (2005Q4-2010Q4 complete, 2012, 2016, 2019, 2025Q4-2026Q3), parsed independently.
   - All 14 derived WAGES series (real wages, expected real wages) and `se_elspot_se3_sek_mwh`, recomputed from their stored components.
   - Hand-compiled values, spot-checked against official pages or press releases where these could be reached.

## 2. Summary

- **Structure: no defects remain.** All 176 files parse. All dates are first-of-period and strictly increasing. There are no duplicates, NaN values, internal gaps or frequency mismatches. After the fixes, every catalog start/end/n_obs matches its file. There are no orphan files and no duplicate IDs. All rates are in percent, and every "Index YYYY=100" series has a base-year mean of 100 ± 1. The one exception is `no_fx_i44`, whose 1990 mean is 102.2 (I10).
- **Values: every re-fetched series matches its source.** The only differences are rounding (SE files store 6 significant digits, so Riksbank rates differ by at most 6e-5 pp) and one missing boundary hour in SE3 1999-07 (0.03%, I10). The spliced segments, the derived series and the hand-parsed survey files reproduce exactly. No source had newer data than the files, so every series is as current as its source on 2026-10-06.
- **Fixed in place:**
  - line endings and frequency codes in all 50 SE files and the SE catalog;
  - a 6-day partial last month in `no_elspot_system_eur`, fixed by re-fetching from the source (which also extended the series back to 1999);
  - catalog notes added for 15 series, and one misleading note corrected.
- **What remains are flags, not errors:**
  - 4 discontinued or closed series families;
  - anomalies in SSB's import price indices for 2001-2003, as published;
  - annual-only data in the early SE electricity PPI (1990-1995);
  - known structural breaks (2015 Norwegian wage bill, pre-2007 Norwegian household income);
  - a dating quirk in four 2006-2009 Prospera rounds;
  - forward-dated values in the ECB wage tracker.

## 3. Fixes applied (in place)

| # | Series | Problem | Fix |
|---|---|---|---|
| F1 | all 50 `SE/*.csv` | Files written with CRLF line endings (Python `csv.writer` default). They still parsed, but differed from every other folder. | Converted to LF. I checked that each file parses to identical values before and after. `SE/fetch.py` now writes with `lineterminator="\n"`. |
| F2 | `SE/catalog.csv` (50 rows) | `frequency` was `monthly`/`quarterly`, while NO, WAGES, EU, GLOBAL and SURVEYS use `M`/`Q`/`A`. | Set to `M` (46 rows) and `Q` (4 rows). `SE/fetch.py` now uses `M, Q = "M", "Q"`. No other catalog field changed. |
| F3 | `NO/no_elspot_system_eur` | The last row, 2025-02 = 51.70, was the mean of only 144 hours (1-6 Feb 2025), because Energinet `Elspotprices` stops carrying SYSTEM on 2025-02-06 23:00. The catalog note also said the source only holds the system price from 2011; before 2011 it is coded `SYS`. | Re-fetched `SYS` (1999-07..2010-12) and `SYSTEM` (2011-01..2025-01) from Energinet and dropped the partial month. The series is now 1999-07..2025-01 (n=307, was 2011-01..2025-02, n=170). It is identical to GLOBAL/nordic_elspot_system_price on their overlap (max diff 5e-8). Catalog start/end/n_obs/source_query/notes updated. `NO/fetch.py` now requests `SYS` too and drops months with less than 95% source coverage. This does not change `no_elspot_no2_eur`. |
| F4 | catalog notes (15 rows) | Caveats not documented in the catalogs. | Appended `[qa-B] ...` notes to: NO `no_imp_price_coffee_cocoa_idx`, `no_imp_price_total_idx`, `no_imp_price_cereals_idx`, `no_cpi_total_idx`, `no_hh_goods_cons_vol_sa_idx`; SE `se_ppi_electricity_hmpi_idx`; WAGES `no_real_wage_qna_yoy_q`, `no_hh_real_disp_inc_xdiv_sa_q`, `no_cpi_idx`, `ea_wage_tracker_yoy_q`, `se_exp_wage_1y_lmp`, `se_exp_wage_1y_all`, `se_exp_cpi_1y_lmp`, `se_exp_cpi_1y_all`, `se_exp_real_wage_1y_lmp`. The `no_elspot_system_eur` note was rewritten (F3). Note: NO/ and WAGES/ `fetch.py` regenerate their catalogs, so re-running them drops the F4 notes (the F3 note becomes the script's own text). |
| F5 | `NO/no_cpi_ate_sa_idx` | The catalog note said "SSB backcast to 1985", but table 14708 and the file start in 2002-12. | Note corrected in the catalog and in `NO/fetch.py`. |

## 4. Issues flagged (not errors, or as published by the source)

**I1. Discontinued or closed series (end date explained).** Only one family ends before 2025.
- `no_border_trade_exp_mnok_s1`, `no_border_trade_trips_s1` end 2022Q4. SSB closed table 08460. The new survey (`*_s2`, table 14044) runs from 2023Q1 to 2026Q1 and is not comparable (design break), so do not chain the two mechanically.
- `no_hh_goods_cons_vol_sa_idx`, `no_hh_food_cons_vol_sa_idx` end 2025-06: SSB discontinued table 05333.
  - The successor `no_mna_hh_goods_cons_sa_mnok` (monthly national accounts, 2016-01..2026-06) covers total goods only.
  - There is no monthly Norwegian food-consumption successor. Use `no_qna_hh_food_cons_sa_mnok` (quarterly) or retail `no_retail_foodstores_vol_sa_idx` (monthly).
- `se_hhcons_ind_old_total_sa`, `se_hhcons_ind_old_grocery_sa` end 2026-03 (old SCB indicator discontinued). Successors `se_hhcons_ind_total_sa` and `se_hhcons_ind_food_sa` start 2019-01; the overlap allows growth-rate splicing.
- `no_elspot_system_eur` ends 2025-01. The free Energinet source stopped carrying the system price on 2025-02-06, `DayAheadPrices` has no system price, and Nord Pool's own history needs a login. Use `no_elspot_no2_eur` or the area prices in GLOBAL. qa-C found the same for GLOBAL.

**I2. Dates after today (legitimate, but watch for look-ahead).**
- `ea_wage_tracker_yoy_q` runs to 2027Q2. The ECB wage tracker projects pay from agreements already signed, and the forward quarters get revised. In a backtest, use only the vintage available at each date.
- `no_vat_food_rate` runs to 2026-12 and `se_food_vat_rate` to 2026-10. Both are legislated step series. Current rates verified: NO food 15% in 2026 (Skatteetaten rates page); SE 6% from 2026-04-01 (Skatteverket).
- `no_frontfag_frame_a`, `no_jordbruk_ramme_mnok`, `no_jordbruk_malpris_mnok` and `no_agri_price_idx` carry a 2026 value. These are agreed or budgeted in spring and summer 2026, so they are known before year-end.

**I3. SSB import price index (table 03675) anomalies, as published.** Re-fetched today, identical to source.
- `no_imp_price_coffee_cocoa_idx` jumps from about 46 to about 80 in 2003-01..2003-04 and falls back in 2003-05 (log change +55%, then -56%).
- `no_imp_price_total_idx` dips at the same time (-9.7%, then +10%). Food SITC 0 is unaffected.
- `no_imp_price_cereals_idx` is flat at 78.5 for 20 months (2001-03..2002-10) and at 79.3 for 2003-05..2003-12, which looks like carried-forward prices.
- Recommendation: treat 2003-01..04 as outliers in the first two and start cereals in 2004. This does not matter if the sample starts at Orkla's segment data (2014+).

**I4. `se_ppi_electricity_hmpi_idx`, 1990-1995 annual only.** SCB holds one value per year, repeated in every month. Monthly changes are therefore 0 within the year and jump in January. Use it from 1996 onward. It is also very volatile in 2021-2026 (energy crisis), which is genuine.

**I5. Structural breaks (documented in the catalogs; handle in modelling).**
- **Norwegian wage bill per FTE.** `no_qna_wage_per_fte_q` and `_food_q` have a timing break from the 2015 switch to a-ordningen, and `no_real_wage_qna_yoy_q` inherits it (2015Q2 +7.7, 2015Q3 -3.9, both spurious). These series are NSA with a strong Q2 holiday-pay seasonal, so use y/y changes.
- **Norwegian household income.** `no_hh_real_disp_inc_sa_q` jumps by more than 8% q/q in 2001Q2-Q3, 2006Q1-Q4 and 2021Q4-2022Q1 (dividends paid out around tax changes). `no_hh_real_disp_inc_xdiv_sa_q` removes the 2021-22 spike and has no move above 5% q/q after 2006. Before 2007 it is still volatile: 2001Q3 +14%, 2004Q3 +10%, 2006Q2 +18%, 2006Q4 -23%. This volatility is in SSB's income-excluding-dividends component (I3491UAB_H) itself, so use the series from 2007 or add dummies.
- **Spliced series (verified segment by segment, y/y-preserving):**
  - NO earnings indices: switches in 2006Q1 and 2017Q1;
  - DK wage indices: ILON2X to 2005, ILON12 to 2025Q4, SBLON1 for 2026Q1-Q2;
  - NO CPI food groups: COICOP 2018 from 2000-07, earlier COICOP 1999 growth. Sub-group definitions differ slightly.
- **Other breaks noted in the catalogs:**
  - NAV registered unemployment: register modernisation, April 2025;
  - LFS quarterly unemployment (NSA): 2006 and 2021;
  - household electricity energy price: survey redesign in 2012;
  - `se_elspot_se3_eur_mwh`: 2011-01..10 is filled with the system price.

**I6. Prospera/Origo (Riksbank survey) dating, 2006-2009.**
- The fetcher dates the early rounds by round number ("n/YY" → quarter n). In 2006-2009 the rounds were not one per quarter:
  - 3/06 (fieldwork 11 Oct 2006) and 3/07 (10 Oct 2007) are dated Q3 but were fielded in Q4;
  - 3/08 (18 Jun 2008) and 3/09 (17 Jun 2009) are dated Q3 but were fielded in Q2.
- So 4 observations carry a timing error of up to one quarter. A clean fix by fieldwork date would create quarters with two rounds (2006Q4, 2007Q4, 2008Q2, 2009Q2) and quarters with none (2006Q3, 2007Q3, 2008Q3, 2009Q3). I left the series as is and documented it in the catalog.
- Affects `se_exp_wage_1y_lmp`, `se_exp_wage_1y_all`, `se_exp_cpi_1y_lmp`, `se_exp_cpi_1y_all` and `se_exp_real_wage_1y_lmp`. All values match the source files: 28 rounds checked, including every 2005-2010 round and 2026Q3.

**I7. Preliminary and revisable latest values.**
- **`se_wage_yoy_m`**: MI's latest ~12 months are preliminary and usually revised up. MI's own "estimated final" values are 3.5 vs 3.4 for 2026-06 and 2.9 vs 2.7 for 2026-07. `se_wage_idx_m` and the Swedish real-wage series inherit this.
- **Other preliminary latest values:**
  - `fi_wage_idx_q`: latest quarters preliminary;
  - `no_frontfag_outcome_a`: 2024 (5.3) and 2025 (5.1) are TBU preliminary. Both confirmed in TBU/Norsk Industri reporting.
- **Revised with each release:** the quarterly national accounts series in all countries.

**I8. Precision.**
- NO CPI (`no_cpi_total_idx`, `no_cpi_idx`, `no_cpi_annual_idx`) is published with one decimal on base 2025=100. Pre-1960 levels of 2-10 are therefore coarse: for example, 2.0 throughout 1931-05..1935-10, and all-identical years such as 1932-1934. This does not matter after 1960.
- SE files carry 6 significant digits.

**I9. Extreme moves checked and genuine (do not treat as data errors).**
- **VAT changes:**
  - Norwegian food VAT 24% → 12% on 2001-07: NO CPI food groups -9% to -10% m/m;
  - Swedish food VAT 12% → 6% on 2026-04: SE food CPIs -5% to -8% m/m (oils and fats -7.8%).
- **COVID, 2020-03..06:** NAV fully unemployed went from 61k to 287k (x4.7) and the rate rose 7.9 pp; NO retail food +9..11%; Q2 dips in NO/SE consumption and GDP.
- **EV VAT, Norway:** cars bought ahead of VAT on EVs from 2023-01, giving `no_hh_goods_cons_vol_sa_idx` +12.6% then -29.6%.
- **Energy and commodity prices:**
  - the 2022-2023 energy crisis: NO2 spot up to 443 EUR/MWh in 2022-08, and SE PPI electricity monthly log changes of 25-60%;
  - `no_cpi_food_sugar_confect_idx`: Jan 2018 +9.8% (sugar/chocolate tax rise), January/April jumps of 8-9% in 2023-2026 (chocolate price increases), and promotion-driven swings.
- **Interest rates and wages:**
  - Sweden's 1992-09 rate defence (3m T-bill 22%), 1970s Finnish wage inflation, and the ECB wage tracker's drop from 4.2 (2025Q2) to 2.3 (2025Q3), a base effect from the 2024 one-off payments;
  - zero centrally agreed wage increases in 1993-04..06 in `se_wage_central_agreed_yoy_m` (as published by MI).
- **Agricultural settlement:** the 2022 extraordinary agreement (10.9 bn, `no_jordbruk_ramme_mnok`). The negative values in 2000 and 2004 are real cuts. `no_jordbruk_*` are annual changes in NOK million, not levels.

**I10. Minor metadata notes (left as is).**
- `no_fx_i44`'s unit says "index (1990=100)", but its 1990 average is 102.2 (Norges Bank's published levels). This is immaterial for growth rates.
- `se_kix_idx` starts 1992-12 (the source also has a partial 1992-11, which is fine to leave out).
- `no_real_wage_tbu_yoy_a` differs from SSB's official real-earnings change by up to 0.3 pp. This is already stated in the catalog; the cause is the different CPI averaging.
- Month boundaries for electricity differ slightly between folders. `se_elspot_se3_eur_mwh` averages on a fixed CET clock (UTC+1), while NO/ and GLOBAL/ use Danish local time (CET/CEST). The SE3 series differs from GLOBAL/se_elspot_se3_price by at most 0.22% (median 0.01%). GLOBAL also lacks 2011-01..10, which SE fills with the system price. The first SE3 month, 1999-07, is missing its first CET hour because the fetch window starts at 00:00 UTC, so it is 0.03% off (9.7106 vs 9.7132). Left as is: negligible.

**I11. Duplicates across folders (all identical; use one copy).**
- **Within this scope:**
  - NO/no_cpi_total_idx = WAGES/no_cpi_idx;
  - SE/se_cpi_idx = WAGES/se_cpi_idx;
  - SE/se_cpif_idx = WAGES/se_cpif_idx.
- **Against EU/ (same values):**
  - DK/FI/CZ HICPs in WAGES vs the EU HICPs;
  - WAGES/ea_hh_real_disp_inc_pc_idx = EU/ea_hh_real_gdi_pc_idx;
  - NO/no_govbond_10y = EU/no_gov_bond_10y;
  - NO/no_retail_vol_sa_idx = EU/no_retail_total_vol_idx;
  - SE/se_unemp_rate_sa = EU/se_unemp_rate_sa.
- **Against GLOBAL/ and SURVEYS/ (same values):**
  - NO/no_elspot_no2_eur = GLOBAL/no_elspot_no2_price;
  - NO/no_elspot_system_eur = GLOBAL/nordic_elspot_system_price;
  - WAGES/no_exp_infl_12m_business = SURVEYS/no_nbes_bl_infl_exp_12m.
- **Different source:** NO/no_lfs_unemp_rate_sa vs EU/no_unemp_rate_sa, and NO/no_ppi_food_dom_idx vs EU/no_ppi_dom_food_mfg_idx: SSB vs Eurostat, at most 0.1 apart through rounding.

**I12. Access notes.**
- regjeringen.no (TBU reports) returned HTTP 403 through the proxy, so it is policy-blocked. TBU and frontfag figures were verified from NHO, Norsk Industri and LO reporting instead: frame 5.2 / 4.4 / 4.4 for 2024-2026, outcome 5.3 / 5.1 for 2024-2025.
- The 2026 agricultural settlement (frame 3,660 MNOK, target prices +233 MNOK) was confirmed in press reports. Earlier settlement years and pre-2024 frontfag values were not re-verified; they come from Storting/TBU documents cited in `fetch.py`.

## 5. Coverage table

Status legend:
- **OK**: structure clean and values identical to the source (or verified).
- **DISC**: discontinued or closed, end explained in I1.
- **FLAG**: usable, with a data caveat (see issue).
- **FIXED**: corrected in place (section 3).
- **F1/F2**: SE format fixes (line endings and frequency code; values unchanged).
- Issue numbers refer to section 4.

### NO (65 series)

| series_id | freq | start | end | n_obs | status | source check |
|---|---|---|---|---|---|---|
| no_agri_price_idx | A | 1960-01-01 | 2026-01-01 | 67 | OK (I2) | re-fetched: identical |
| no_border_trade_exp_mnok_s1 | Q | 2004-01-01 | 2022-10-01 | 76 | DISC (I1) | re-fetched: identical |
| no_border_trade_exp_mnok_s2 | Q | 2023-01-01 | 2026-01-01 | 13 | OK (I5 break vs s1) | re-fetched: identical |
| no_border_trade_trips_s1 | Q | 2004-01-01 | 2022-10-01 | 76 | DISC (I1) | re-fetched: identical |
| no_border_trade_trips_s2 | Q | 2023-01-01 | 2026-01-01 | 13 | OK (I5 break vs s1) | re-fetched: identical |
| no_cpi_at_food_bev_idx | M | 2002-12-01 | 2026-08-01 | 285 | OK | re-fetched: identical |
| no_cpi_at_idx | M | 2002-12-01 | 2026-08-01 | 285 | OK | re-fetched: identical |
| no_cpi_ate_idx | M | 2002-12-01 | 2026-08-01 | 285 | OK | re-fetched: identical |
| no_cpi_ate_sa_idx | M | 2002-12-01 | 2026-08-01 | 285 | OK; FIXED F5 (note) | re-fetched: identical |
| no_cpi_food_bev_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK (I5, I9) | re-fetched: identical |
| no_cpi_food_cereals_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK | re-fetched: identical |
| no_cpi_food_dairy_eggs_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK | re-fetched: identical |
| no_cpi_food_fish_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK | re-fetched: identical |
| no_cpi_food_fruit_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK | re-fetched: identical |
| no_cpi_food_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK (I5, I9) | re-fetched: identical |
| no_cpi_food_meat_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK | re-fetched: identical |
| no_cpi_food_oils_fats_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK | re-fetched: identical |
| no_cpi_food_other_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK | re-fetched: identical |
| no_cpi_food_sugar_confect_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK | re-fetched: identical |
| no_cpi_food_vegetables_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK | re-fetched: identical |
| no_cpi_nonalc_bev_idx | M | 1979-01-01 | 2026-08-01 | 572 | OK | re-fetched: identical |
| no_cpi_total_idx | M | 1920-03-01 | 2026-08-01 | 1278 | OK (I8) | re-fetched: identical |
| no_credit_hh_c2_yoy | M | 1988-12-01 | 2026-08-01 | 453 | OK | re-fetched: identical |
| no_dom_price_food_pif_idx | M | 1990-01-01 | 2026-08-01 | 440 | OK | re-fetched: identical |
| no_elec_hh_energy_price | Q | 1998-01-01 | 2026-04-01 | 114 | OK (I5) | re-fetched: identical |
| no_elec_hh_total_price | Q | 2003-01-01 | 2026-04-01 | 94 | OK | re-fetched: identical |
| no_elspot_no2_eur | M | 1999-07-01 | 2026-09-01 | 327 | OK | re-fetched: identical |
| no_elspot_system_eur | M | 1999-07-01 | 2025-01-01 | 307 | FIXED F3; DISC (I1) | re-fetched: identical |
| no_fx_czknok | M | 1994-01-01 | 2026-09-01 | 393 | OK | re-fetched: identical |
| no_fx_dkknok | M | 1960-01-01 | 2026-09-01 | 801 | OK | re-fetched: identical |
| no_fx_eurnok | M | 1999-01-01 | 2026-09-01 | 333 | OK | re-fetched: identical |
| no_fx_i44 | M | 1989-07-01 | 2026-09-01 | 447 | OK (I10) | re-fetched: identical |
| no_fx_seknok | M | 1960-01-01 | 2026-09-01 | 801 | OK | re-fetched: identical |
| no_fx_usdnok | M | 1960-01-01 | 2026-09-01 | 801 | OK | re-fetched: identical |
| no_gdp_mainland_sa_mnok | Q | 1978-01-01 | 2026-04-01 | 194 | OK | re-fetched: identical |
| no_govbond_10y | M | 1985-01-01 | 2026-09-01 | 501 | OK | re-fetched: identical |
| no_hh_food_cons_vol_sa_idx | M | 2000-01-01 | 2025-06-01 | 306 | DISC (I1) | re-fetched: identical |
| no_hh_goods_cons_vol_sa_idx | M | 2000-01-01 | 2025-06-01 | 306 | DISC (I1, I9) | re-fetched: identical |
| no_hh_loan_rate_q | Q | 2002-01-01 | 2026-04-01 | 98 | OK | re-fetched: identical |
| no_hh_mortgage_rate | M | 2013-12-01 | 2026-08-01 | 153 | OK | re-fetched: identical |
| no_house_price_idx | Q | 1992-01-01 | 2026-04-01 | 138 | OK | re-fetched: identical |
| no_imp_price_cereals_idx | M | 2000-12-01 | 2026-08-01 | 309 | FLAG (I3) | re-fetched: identical |
| no_imp_price_coffee_cocoa_idx | M | 2000-12-01 | 2026-08-01 | 309 | FLAG (I3) | re-fetched: identical |
| no_imp_price_food_idx | M | 2000-12-01 | 2026-08-01 | 309 | OK | re-fetched: identical |
| no_imp_price_total_idx | M | 2000-12-01 | 2026-08-01 | 309 | FLAG (I3) | re-fetched: identical |
| no_jordbruk_malpris_mnok | A | 2000-01-01 | 2026-01-01 | 27 | OK (I2, I9) | hand-compiled; 2026 (+233) confirmed in press reports |
| no_jordbruk_ramme_mnok | A | 2001-01-01 | 2026-01-01 | 26 | OK (I2, I9) | hand-compiled; 2026 (3,660) confirmed in press reports |
| no_lfs_unemp_rate_q_nsa | Q | 1988-04-01 | 2026-04-01 | 153 | OK (I5) | re-fetched: identical |
| no_lfs_unemp_rate_sa | M | 2006-01-01 | 2026-08-01 | 248 | OK | re-fetched: identical |
| no_mna_hh_goods_cons_sa_mnok | M | 2016-01-01 | 2026-06-01 | 126 | OK | re-fetched: identical |
| no_nav_unemp_level_sa | M | 1951-01-01 | 2026-09-01 | 909 | OK (I5) | re-fetched: identical on overlap (720 extra file obs) |
| no_nav_unemp_rate_sa | M | 2011-01-01 | 2026-09-01 | 189 | OK (I5) | re-fetched: identical |
| no_nibor_3m | M | 1979-01-01 | 2026-09-01 | 573 | OK | re-fetched: identical |
| no_policy_rate | M | 1991-01-01 | 2026-09-01 | 429 | OK | re-fetched: identical |
| no_ppi_food_dom_idx | M | 2000-01-01 | 2026-08-01 | 320 | OK | re-fetched: identical |
| no_ppi_meat_dom_idx | M | 2000-01-01 | 2026-08-01 | 320 | OK | re-fetched: identical |
| no_ppi_otherfood_dom_idx | M | 2000-01-01 | 2026-08-01 | 320 | OK | re-fetched: identical |
| no_qna_hh_cons_sa_mnok | Q | 1978-01-01 | 2026-04-01 | 194 | OK | re-fetched: identical |
| no_qna_hh_food_cons_sa_mnok | Q | 1978-01-01 | 2026-04-01 | 194 | OK | re-fetched: identical |
| no_qna_hh_goods_cons_sa_mnok | Q | 1978-01-01 | 2026-04-01 | 194 | OK | re-fetched: identical |
| no_retail_foodstores_val_sa_idx | M | 2000-01-01 | 2026-08-01 | 320 | OK | re-fetched: identical |
| no_retail_foodstores_vol_sa_idx | M | 2000-01-01 | 2026-08-01 | 320 | OK | re-fetched: identical |
| no_retail_vol_sa_idx | M | 2000-01-01 | 2026-08-01 | 320 | OK | re-fetched: identical |
| no_trade_imp_price_food_q_idx | Q | 1989-01-01 | 2026-04-01 | 150 | OK | re-fetched: identical |
| no_vat_food_rate | M | 1990-01-01 | 2026-12-01 | 444 | OK (I2) | hand-compiled; 2026 rate 15% confirmed (Skatteetaten) |

### SE (50 series)

| series_id | freq | start | end | n_obs | status | source check |
|---|---|---|---|---|---|---|
| se_cpi_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpif_idx | M | 1987-01-01 | 2026-08-01 | 476 | OK; F1/F2 | re-fetched: identical |
| se_cpifxe_idx | M | 1987-01-01 | 2026-08-01 | 476 | OK; F1/F2 | re-fetched: identical |
| se_cpif_ct_idx | M | 1987-01-01 | 2026-08-01 | 476 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_nab_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_cereals_bread_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_meat_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_fish_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_dairy_eggs_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_oils_fats_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_fruit_nuts_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_vegetables_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_sugar_confect_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_food_ready_other_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_cpi_nonalc_bev_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK; F1/F2 | re-fetched: identical |
| se_ppi_food_hmpi_idx | M | 1990-01-01 | 2026-08-01 | 440 | OK; F1/F2 | re-fetched: identical |
| se_ppi_food_impi_idx | M | 1990-01-01 | 2026-08-01 | 440 | OK; F1/F2 | re-fetched: identical |
| se_ppi_food_itpi_idx | M | 1990-01-01 | 2026-08-01 | 440 | OK; F1/F2 | re-fetched: identical |
| se_ppi_agri_hmpi_idx | M | 1990-01-01 | 2026-08-01 | 440 | OK; F1/F2 | re-fetched: identical |
| se_ppi_agri_impi_idx | M | 1990-01-01 | 2026-08-01 | 440 | OK; F1/F2 | re-fetched: identical |
| se_ppi_paper_packaging_itpi_idx | M | 1990-01-01 | 2026-08-01 | 440 | OK; F1/F2 | re-fetched: identical |
| se_ppi_plastic_packaging_itpi_idx | M | 1990-01-01 | 2026-08-01 | 440 | OK; F1/F2 | re-fetched: identical |
| se_ppi_total_itpi_idx | M | 1990-01-01 | 2026-08-01 | 440 | OK; F1/F2 | re-fetched: identical |
| se_ppi_electricity_hmpi_idx | M | 1990-01-01 | 2026-08-01 | 440 | FLAG (I4); F1/F2 | re-fetched: identical |
| se_retail_vol_sa_idx | M | 1991-01-01 | 2026-08-01 | 428 | OK; F1/F2 | re-fetched: identical |
| se_retail_grocery_vol_sa_idx | M | 1991-01-01 | 2026-08-01 | 428 | OK; F1/F2 | re-fetched: identical |
| se_retail_grocery_value_idx | M | 1991-01-01 | 2026-08-01 | 428 | OK; F1/F2 | re-fetched: identical |
| se_hhcons_ind_total_sa | M | 2019-01-01 | 2026-08-01 | 92 | OK; F1/F2 | re-fetched: identical |
| se_hhcons_ind_food_sa | M | 2019-01-01 | 2026-08-01 | 92 | OK; F1/F2 | re-fetched: identical |
| se_hhcons_ind_old_total_sa | M | 2000-01-01 | 2026-03-01 | 315 | DISC (I1); F1/F2 | re-fetched: identical |
| se_hhcons_ind_old_grocery_sa | M | 2000-01-01 | 2026-03-01 | 315 | DISC (I1); F1/F2 | re-fetched: identical |
| se_na_hhcons_total_sa | Q | 1981-01-01 | 2026-04-01 | 182 | OK; F1/F2 | re-fetched: identical |
| se_na_hhcons_food_sa | Q | 1981-01-01 | 2026-04-01 | 182 | OK; F1/F2 | re-fetched: identical |
| se_na_hhcons_food_cp_sa | Q | 1981-01-01 | 2026-04-01 | 182 | OK; F1/F2 | re-fetched: identical |
| se_gdp_sa | Q | 1981-01-01 | 2026-04-01 | 182 | OK; F1/F2 | re-fetched: identical |
| se_gdp_indicator_sa_idx | M | 2000-01-01 | 2026-07-01 | 319 | OK; F1/F2 | re-fetched: identical |
| se_unemp_rate_sa | M | 2001-01-01 | 2026-08-01 | 308 | OK; F1/F2 | re-fetched: identical |
| se_mortgage_rate_new | M | 2005-09-01 | 2026-08-01 | 252 | OK; F1/F2 | re-fetched: identical |
| se_mortgage_rate_outstanding | M | 2005-09-01 | 2026-08-01 | 252 | OK; F1/F2 | re-fetched: identical |
| se_policy_rate | M | 1994-06-01 | 2026-09-01 | 388 | OK; F1/F2 | re-fetched: identical |
| se_tbill_3m | M | 1983-01-01 | 2026-09-01 | 525 | OK; F1/F2 | re-fetched: within rounding (max abs diff 5e-05) |
| se_gov_bond_10y | M | 1987-01-01 | 2026-09-01 | 477 | OK; F1/F2 | re-fetched: within rounding (max abs diff 5e-05) |
| se_kix_idx | M | 1992-12-01 | 2026-09-01 | 406 | OK (I10); F1/F2 | re-fetched: identical on overlap (1 extra source obs) |
| se_eursek | M | 1993-01-01 | 2026-09-01 | 405 | OK; F1/F2 | re-fetched: identical |
| se_usdsek | M | 1993-01-01 | 2026-09-01 | 405 | OK; F1/F2 | re-fetched: identical |
| se_noksek | M | 1993-01-01 | 2026-09-01 | 405 | OK; F1/F2 | re-fetched: identical |
| se_elspot_se3_eur_mwh | M | 1999-07-01 | 2026-09-01 | 327 | OK (I5, I10); F1/F2 | re-fetched (Energinet SE, SYSTEM, SE3, DayAhead): identical except 1999-07 (-0.03%, I10) |
| se_elspot_se3_sek_mwh | M | 1999-07-01 | 2026-09-01 | 327 | OK (I5); F1/F2 | recomputed (SE3 EUR x EUR/SEK): identical within 6 sig. digits |
| se_food_vat_rate | M | 1991-01-01 | 2026-10-01 | 430 | OK (I2); F1/F2 | hand-compiled; steps re-checked; 6% from 2026-04-01 confirmed (Skatteverket) |

### WAGES (61 series)

| series_id | freq | start | end | n_obs | status | source check |
|---|---|---|---|---|---|---|
| cz_avg_gross_wage_q | Q | 2000-01-01 | 2026-04-01 | 106 | OK | re-fetched: identical |
| cz_hicp_idx | M | 1996-01-01 | 2026-08-01 | 368 | OK | re-fetched: identical |
| cz_real_wage_yoy_q | Q | 2001-01-01 | 2026-04-01 | 102 | OK | recomputed from components: identical |
| dk_hh_real_disp_inc_sa_q | Q | 1999-01-01 | 2026-04-01 | 110 | OK | re-fetched: identical |
| dk_hicp_idx | M | 1996-01-01 | 2026-08-01 | 368 | OK | re-fetched: identical |
| dk_real_wage_yoy_q | Q | 1997-01-01 | 2026-04-01 | 118 | OK | recomputed from components: identical |
| dk_wage_idx_food_manuf_q | Q | 1996-01-01 | 2026-04-01 | 122 | OK (I5) | re-fetched: spliced segments verified (levels/y/y identical) |
| dk_wage_idx_private_q | Q | 1994-01-01 | 2026-04-01 | 130 | OK (I5) | re-fetched: spliced segments verified (levels/y/y identical) |
| dk_wage_idx_total_q | Q | 2016-01-01 | 2026-04-01 | 42 | OK | re-fetched: identical |
| ea_comp_per_employee_q | Q | 1995-01-01 | 2026-04-01 | 126 | OK | re-fetched: identical |
| ea_hh_real_disp_inc_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | OK | re-fetched: identical |
| ea_hicp_idx | M | 1996-01-01 | 2026-09-01 | 369 | OK | re-fetched: identical |
| ea_negotiated_wages_yoy_q | Q | 1991-01-01 | 2026-04-01 | 142 | OK | re-fetched: identical |
| ea_real_comp_per_employee_yoy_q | Q | 1997-01-01 | 2026-04-01 | 118 | OK | recomputed from components: identical |
| ea_real_negotiated_wages_yoy_q | Q | 1997-01-01 | 2026-04-01 | 118 | OK | recomputed from components: identical |
| ea_wage_tracker_yoy_q | Q | 2013-01-01 | 2027-04-01 | 58 | FLAG (I2) | re-fetched: identical |
| fi_hicp_idx | M | 1996-01-01 | 2026-09-01 | 369 | OK | re-fetched: identical |
| fi_real_wage_yoy_q | Q | 1997-01-01 | 2026-04-01 | 118 | OK | recomputed from components: identical |
| fi_wage_idx_q | Q | 1964-01-01 | 2026-04-01 | 250 | OK (I7) | re-fetched: identical |
| no_annual_earnings_a | A | 1970-01-01 | 2025-01-01 | 56 | OK | re-fetched: identical |
| no_avg_monthly_earnings_q | Q | 2016-01-01 | 2026-04-01 | 42 | OK | re-fetched: identical |
| no_cpi_annual_idx | A | 1921-01-01 | 2025-01-01 | 105 | OK (I8) | re-fetched: identical |
| no_cpi_idx | M | 1920-03-01 | 2026-08-01 | 1278 | OK (I8) | re-fetched: identical |
| no_earn_idx_food_manuf_q | Q | 1998-01-01 | 2026-04-01 | 114 | OK (I5) | re-fetched: spliced segments verified (levels/y/y identical) |
| no_earn_idx_manuf_q | Q | 1998-01-01 | 2026-04-01 | 114 | OK (I5) | re-fetched: spliced segments verified (levels/y/y identical) |
| no_exp_infl_12m_business | Q | 2002-01-01 | 2026-07-01 | 99 | OK | re-fetched: identical |
| no_exp_infl_12m_econ | Q | 2002-01-01 | 2026-07-01 | 99 | OK | re-fetched: identical |
| no_exp_infl_12m_social | Q | 2002-01-01 | 2026-07-01 | 99 | OK | re-fetched: identical |
| no_exp_real_wage_business_q | Q | 2002-10-01 | 2026-07-01 | 96 | OK | recomputed from components: identical |
| no_exp_real_wage_cy_econ | Q | 2023-01-01 | 2026-07-01 | 15 | OK | re-fetched: identical |
| no_exp_real_wage_econ_q | Q | 2002-10-01 | 2026-07-01 | 96 | OK | recomputed from components: identical |
| no_exp_real_wage_social_q | Q | 2002-10-01 | 2026-07-01 | 96 | OK | recomputed from components: identical |
| no_exp_wage_cy_business | Q | 2002-10-01 | 2026-07-01 | 96 | OK | re-fetched: identical |
| no_exp_wage_cy_econ | Q | 2002-10-01 | 2026-07-01 | 96 | OK | re-fetched: identical |
| no_exp_wage_cy_social | Q | 2002-10-01 | 2026-07-01 | 96 | OK | re-fetched: identical |
| no_frontfag_frame_a | A | 2014-01-01 | 2026-01-01 | 13 | OK (I2) | hand-compiled; 2024-26 confirmed (NHO, Norsk Industri) |
| no_frontfag_outcome_a | A | 2014-01-01 | 2025-01-01 | 12 | OK (I7) | hand-compiled; 2024-25 (TBU preliminary) confirmed |
| no_hh_real_disp_inc_sa_q | Q | 1999-01-01 | 2026-04-01 | 110 | FLAG (I5) | re-fetched: identical |
| no_hh_real_disp_inc_xdiv_sa_q | Q | 1999-01-01 | 2026-04-01 | 110 | FLAG (I5) | re-fetched: identical |
| no_qna_wage_per_fte_food_q | Q | 1995-01-01 | 2026-04-01 | 126 | FLAG (I5) | re-fetched: identical |
| no_qna_wage_per_fte_q | Q | 1995-01-01 | 2026-04-01 | 126 | FLAG (I5) | re-fetched: identical |
| no_real_earnings_yoy_q | Q | 2017-01-01 | 2026-04-01 | 38 | OK | recomputed from components: identical |
| no_real_wage_qna_yoy_q | Q | 1996-01-01 | 2026-04-01 | 122 | FLAG (I5) | recomputed from components: identical |
| no_real_wage_tbu_yoy_a | A | 1971-01-01 | 2025-01-01 | 55 | OK (I10) | recomputed from components: identical |
| no_regnet_exp_wage_cy | Q | 2005-01-01 | 2026-07-01 | 87 | OK | re-fetched: identical |
| no_tbu_wage_growth_a | A | 1971-01-01 | 2025-01-01 | 55 | OK | re-fetched: identical |
| se_cpi_idx | M | 1980-01-01 | 2026-08-01 | 560 | OK | re-fetched: identical |
| se_cpif_idx | M | 1987-01-01 | 2026-08-01 | 476 | OK | re-fetched: identical |
| se_exp_cpi_1y_all | Q | 2005-10-01 | 2026-07-01 | 84 | FLAG (I6) | 28 of 84 rounds re-parsed from source files (2005-26): identical |
| se_exp_cpi_1y_lmp | Q | 2005-10-01 | 2026-07-01 | 84 | FLAG (I6) | 28 of 84 rounds re-parsed from source files (2005-26): identical |
| se_exp_real_wage_1y_lmp | Q | 2005-10-01 | 2026-07-01 | 84 | FLAG (I6) | recomputed from components: identical (inputs verified against survey files) |
| se_exp_wage_1y_all | Q | 2005-10-01 | 2026-07-01 | 84 | FLAG (I6) | 28 of 84 rounds re-parsed from source files (2005-26): identical |
| se_exp_wage_1y_lmp | Q | 2005-10-01 | 2026-07-01 | 84 | FLAG (I6) | 28 of 84 rounds re-parsed from source files (2005-26): identical |
| se_hh_real_disp_inc_q | Q | 1981-01-01 | 2026-04-01 | 182 | OK | re-fetched: identical |
| se_real_wage_growth_a | A | 1960-01-01 | 2025-01-01 | 66 | OK | re-fetched: identical |
| se_real_wage_kpif_yoy_q | Q | 1993-01-01 | 2026-04-01 | 134 | OK | recomputed from components: identical |
| se_real_wage_yoy_q | Q | 1993-01-01 | 2026-04-01 | 134 | OK | recomputed from components: identical |
| se_wage_central_agreed_yoy_m | M | 1992-01-01 | 2026-07-01 | 415 | OK | re-fetched: identical |
| se_wage_growth_a | A | 1960-01-01 | 2025-01-01 | 66 | OK | re-fetched: identical |
| se_wage_idx_m | M | 1992-01-01 | 2026-07-01 | 415 | OK | re-fetched: identical |
| se_wage_yoy_m | M | 1992-07-01 | 2026-07-01 | 409 | OK (I7) | re-fetched: identical |
