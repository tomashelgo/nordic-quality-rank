# QA-C: macro series in EU/, SURVEYS/, GLOBAL/

QA run on 2026-10-06 (label qa-C). The scope was every series listed in `EU/catalog.csv` (211), `SURVEYS/catalog.csv` (218) and `GLOBAL/catalog.csv` (87): **516 series**. Scripts and downloaded files are in the session scratchpad (`scripts/qa-C/`, `dl/qa-C/`), not in the repo.

## 1. What was checked

1. **Structure.** For every series I checked that:
   - the file parses, with header exactly `date,value`, 2 columns and ISO dates;
   - dates are day-1 (quarterly dates fall in Jan/Apr/Jul/Oct), strictly increasing, with no duplicates and no NaN;
   - the frequency inferred from the dates matches the catalog;
   - there are no internal gaps;
   - there are no future dates.
2. **Catalog against files.** I compared `start`, `end` and `n_obs` with each file, checked that `file` equals `series_id.csv`, and looked for orphan files and duplicate IDs.
3. **Recency.** I flagged any series ending before 2025, and any series ending well short of the usual publication lag for its source.
4. **Plausibility.**
   - Rates are in percent, not fractions. Indices and prices are positive. Balances fall within [-100, 100]. Unemployment and saving rates are in a plausible range.
   - Base-period means are about 100 for "Index YYYY=100" units.
   - I screened for outliers and rebasing jumps with a robust z-score (MAD) on log changes or differences, flagging |z| > 10 for log changes above 8%.
   - I looked for runs of identical values, especially at the tail of a series, to catch forward-filled data.
5. **Independent re-fetch from the original sources** and point-by-point comparison. This was done for all 516 series except some early history: Energinet and DG AGRI were compared from 2023 onward (2026 only for the DG AGRI cereals), and spliced series were checked through growth rates. Results:
   - Eurostat: 193 series, SDMX 2.1 API by catalog key. 186 are identical. The 7 back-spliced series match in the base-2021 period, and every pre-splice growth rate matches the older-base source (I10/I15).
   - ECB and BIS: 18 series. Daily data were rebuilt as calendar-day monthly means. All identical.
   - IMF India CPI and OECD Norway 10y yield: identical.
   - FAOSTAT India food CPI: identical.
   - EC BCS: 150 series from the 6 nace2_ecfin_2609 zip files. All identical.
   - OECD BCI/CCI/CLI: 26 series. All identical.
   - NIER (12), SSB (5), Finans Norge (7), Norges Bank Regional Network (8), Norges Bank Expectations Survey (9) and UMich (1): all identical. For the Expectations Survey the column headers were also re-checked; differences are below 1e-6 rounding.
   - World Bank Pink Sheet (38) and FRED (16, including the spliced broad USD index and the derived EUR/NOK rate): all identical.
   - FAO FFPI (7), NY Fed GSCPI and Ember (2): all identical.
   - Energinet DK1, NO2, SE3 and system price: identical, both for 2023-2025 hourly data and for 2025-10 to 2026-09 15-minute data.
   - DG AGRI: all 12 series identical. Pig, milk, butter, SMP, WMP, beef, broiler and sugar were compared from 2023; cereals for 2026.
   - Derived FAO/WB EUR- and NOK-term indices: recomputed, matching within 0.15-1.5% (they are labelled "approx.").

## 2. Summary

- **Structure: no defects.** All 516 files parse. All dates are first-of-period and strictly increasing, with no duplicates and no NaN values. Every frequency matches its catalog, and every catalog start, end and n_obs matches its file. There are 0 orphan files and 0 duplicate IDs. Every rate series is in percent; none is a fraction.
- **All files match their sources.** Every comparison listed in section 1, item 5 matched; no file was found to differ from its source. Each series is also as current as its source was on 2026-10-06. The only exceptions were DK 3m (now fixed) and India's policy rate, where I kept the BIS month-completeness rule (see issue 3).
- **Status:**

  | Status | Series |
  |---|---|
  | OK, no remarks | 463 |
  | Flagged as a material caveat (bold in the table) | 31 |
  | Information-only remarks | 22 |

  The material caveats are 1 fixed, 2 discontinued, 10 suspended, 2 lagging, 6 with gaps, 5 with breaks or flat stretches, and 5 noisy or with outliers. Most material flags are properties of the source data rather than collection errors.

## 3. Fixes applied (in place)

| series | problem | fix |
|---|---|---|
| EU/dk_mm_rate_3m | Stale: ended 2026-01-01. Eurostat `irt_st_m` stopped updating DK. | Re-fetched OECD MEI `DNK.M.IR3TIB` (DSD_STES@DF_FINMARK). It is identical to the Eurostat series over all 433 overlapping months from 1990-01 to 2026-01 (max abs diff 1e-5). I appended 2026-02..2026-09 (1.99, 2.10, 2.17, 2.21, 2.29, 2.38, 2.48, 2.57) and updated the catalog row: end 2026-09-01, n_obs 681, source, source_query and notes. The original file and catalog are backed up in the scratchpad (`qa_C_backup/`). |

No other trivial problems were found: there was no sorting, duplicate, date-format or catalog-metadata problem anywhere in the three folders.

## 4. Issues flagged (not fixable, or as published by the source)

### A. Stale or discontinued series (end date)
1. **GLOBAL/glob_wb_barley ends 2020-08.** The World Bank discontinued the barley quote; the file matches the current Pink Sheet. Use `eu_agri_barley_feed_price` / `eu_agri_barley_malting_price` (2015-11 onward) for recent data.
2. **GLOBAL/nordic_elspot_system_price ends 2025-01.** I confirmed that Energi Data Service `Elspotprices` carries SYSTEM only until 2025-02-06 23:00. The successor dataset `DayAheadPrices` has only DE, DK1, DK2, NO2, SE3 and SE4, and Nord Pool's own history needs a login. Use the area prices instead: `no_elspot_no2_price`, `se_elspot_se3_price`, `dk_elspot_dk1_price`, `fi_elspot_price`, `no_elspot_country_avg_price`.
3. **Shorter-than-usual source lags.** These series all end after 2025 and match their sources:
   - **SURVEYS/ee_ec_\*** (10 series) end 2026-04. The EC suspended the Estonian surveys from May 2026 (partner institute change); the EC file has no later data.
   - **SURVEYS/in_oecd_bci** ends 2026-02, which is also the OECD's last observation.
   - **in_oecd_cci** and **no_oecd_bci** end 2026-06. The OECD's Norway BCI is built from the quarterly SSB survey.
   - **EU/in_cpi_food_idx** ends 2026-03, the FAOSTAT lag. FAOSTAT flags the **2025 values as "I" (imputed by FAO)** and the 2026 values as "A" (official), so treat 2025 y/y values for India food CPI with caution. The official MoSPI API refused TLS during collection.
   - **EU/in_policy_rate** ends 2026-06. BIS daily data stop on 2026-07-23, so July is an incomplete month. RBI did not meet between then and the end of July, so July could be filled with 5.25 if needed. I left it, to keep the collector's rule of complete months only.
   - **GLOBAL/eu_agri_sugar_white_price** (2026-06) and the IMF indices via FRED (2026-07) have normal source lags.

### B. Internal gaps (all present in the source; left as gaps, not interpolated)
4. **GLOBAL/se_elspot_se3_price is missing 2011-01..2011-10.** I verified this in Energi Data Service: the single Sweden area `SE` ends 2010-12, and SE3 rows for 2011-01..10 exist but with null prices. SE3 prices start 2011-11, when Sweden was split into SE1-SE4. If a continuous series is needed, the Nordic system price (`nordic_elspot_system_price`) is the closest proxy for those 10 months. Do not splice it in silently.
5. **SURVEYS/eu_ec_food_retail_sell_price_exp is missing 1995-09..1999-12** (the EC has no EU aggregate for those months).
6. **SURVEYS/lv_ec_cons_conf, lv_ec_cons_price_exp_12m and lv_ec_cons_price_past_12m are missing 2000-04..2001-04** (gap in the Latvian consumer survey).
7. **GLOBAL/glob_wb_sunflower_oil is missing 2002-07 and 2002-09..12** (also missing in the Pink Sheet).

### C. Structural breaks, flat stretches and outliers (as published; handle in modelling)
8. **EU/lt_lci_wages_idx: +30% level jump in 2019Q1** (66.7 to 86.8). Lithuania's 2019 tax reform moved employer social contributions into gross wages, which were grossed up by about 1.289. This is not real wage growth. Use a 2019 dummy or rescale pre-2019 levels by about 1.289 before computing y/y.
9. **EU/lt_gov_bond_10y is constant at 2.88% from 2022-11 to 2026-08** (46 months). It was also constant at 0.31 from 2016-10 to 2020-05 and at 0.16 from 2020-07 to 2022-10. The Eurostat value is identical: Lithuania has no secondary-market benchmark, so the last primary-market yield is carried forward. It carries no monthly information; use `ea_gov_bond_10y` / `de_gov_bond_10y` instead.
10. **SURVEYS/ro_ec_esi has implausible values for 1991-1994** (minimum -10.2 in 1992-07, about 11 standard deviations below the long-term average of 100). The values come in quarterly blocks with seasonal-adjustment artefacts and are as published by the EC. Other EC early transition-era data are also extreme: lv_ec_esi 35.9 (1993), pl_ec_esi 178 (1990s), sk_ec_esi, lt_ec_esi and ee_ec_esi before 1999. The EE and LV consumer price balances for 1993-1998 are constant in 6-month blocks. **Recommendation: start CEE survey series no earlier than 2000.**
11. **SURVEYS/lt_ec_food_retail_sell_price_exp is extremely noisy**, with month-to-month swings of 60-97 points (for example 67.4 to -30.0 in 2011-06) and blocky plateaus. This reflects a tiny sample, so the series is unsuitable as a predictor. Several small-country food-industry confidence series (fi, hu, sk, at, dk `_ec_food_ind_conf`) also have first-order autocorrelation of only about 0.5. Use quarterly averages.
12. **EU/ro_hh_saving_rate is very volatile quarterly SCA data**: -44.5% in 2007Q4 and swings of more than 10pp in 2008-2012. This matches Eurostat. Use a 4-quarter average or exclude it.
13. **EU/dk_unemp_rate_sa: Eurostat's monthly LFS-based series for Denmark is noisy**, for example 5.4 to 7.1 to 6.8 to 5.2 in 2025-02..05. It matches the source. Use a 3-month or quarterly average.
14. **EU/eu_ppi_dom_c102_idx (fish processing PPI) falls -12% in 2009-01** (92.3 to 81.6). This matches Eurostat and is likely a weighting or composition effect.
15. **EU/sk_retail_food_vol_idx** has December spikes of about +11% in 2000-2003, residual seasonality present in the Eurostat SCA I15 source. The back-splice itself is correct.
16. **Price-series breaks documented in the catalog:**
    - glob_wb_chicken: US to Brazil in 2021-09, a -26% step;
    - glob_wb_soybean_oil: Dutch to US Gulf basis in 2025-01;
    - glob_wb_palm_oil: several basis changes;
    - glob_wb_natgas_eu: import border price to TTF over 2010-2015;
    - eu_agri cereals (4 series): the reporting stage changed in 2026-08. The July-to-August step is wheat 201.7 to 200.8, feed barley 182.2 to 172.4, malting barley 185.9 to 182.3 and maize 224.8 to 218.2, which mixes harvest seasonality with the possible break.
17. **World Bank series before about 1980 are piecewise constant** (administered or annual contract prices; for example energy index constant for 60 months 1964-68, urea 48 months, aluminium 42 months). Use them from 1980 onward.
18. **Minor or information-only items:**
    - Three SA balances slightly exceed 100: ee_ec_food_ind_sell_price_exp 103.3, hu_ec_food_retail_sell_price_exp 101.6 and ro_ec_cons_price_past_12m 101.6.
    - The last three observations of hu_retail_food_vol_idx are identical at 102.0, as published.
    - Some volume indices in base 2021 have SCA base-year means of 99.3-100.8, as published by Eurostat.
    - The derived EUR/NOK-term FAO and WB indices have base-period means of 98.6-99.9 rather than exactly 100. They are labelled approx.; y/y values are unaffected.
    - ee_gov_bond_10y starts only in 2020-06 (documented).
    - DK 3m money-market data for the 1970s and 1980s are erratic and integer-valued.

### D. Extreme recent moves verified as genuine (do not treat as data errors)
- **2026 energy shock.** Brent rose from 71.1 to 103.7 to 120.4 USD/bbl (2026-02 to 2026-04) and reached 116.8 in 2026-09. TTF gas went from 11.24 to 17.91 USD/mmbtu in 2026-03 and to 25.42 in 2026-09. DK1 power was 140.9 EUR/MWh in 2026-09. All values are identical in the World Bank and Energinet sources and consistent across series.
- **Interest rates turned up in 2026.** The ECB DFR went from 2.00 to 2.25 to 2.375 (monthly averages, 2026-06 to 2026-09), and DK, Euribor and the US 10y (4.99%) moved with it. UMich sentiment was 48.1 in 2026-09, below the 2022 low. All values match their sources.
- **Historic crisis and policy episodes:**
  - COVID drops in 2020Q2 across GDP, retail and ESI;
  - Romania 1997 (3m rate 184%, HICP +27% in a month);
  - CZ 1997 currency crisis (3m rate 26%);
  - CZ PPI price liberalisation in 1991 (flat through 1990, then jumps);
  - Romanian food VAT cut in 2015-06 (-8.6% in HICP food).

## 5. Coverage table

Status "OK" means all checks passed and the series is identical to its source. **Bold** marks a material caveat; plain text marks information only. In the "verified" column, "= src" means re-fetched and identical, "= src (2023+)" means compared for recent years, "splice ok" means the growth rates of each splice segment match their source, and "derived ok" means recomputed from inputs.

### EU (211 series)

| series_id | freq | start | end | n_obs | verified vs source | status |
|---|---|---|---|---|---|---|
| at_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| at_gov_bond_10y | M | 1985-01-01 | 2026-08-01 | 500 | = src | OK |
| at_hh_real_gdi_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| at_hh_saving_rate | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| at_hicp_all_idx | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| at_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| at_hicp_food_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| at_lci_wages_idx | Q | 2009-01-01 | 2026-04-01 | 70 | = src | OK |
| at_ppi_dom_food_mfg_idx | M | 1996-01-01 | 2026-08-01 | 368 | splice ok | OK |
| at_retail_food_vol_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| at_retail_total_vol_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| at_unemp_rate_sa | M | 1995-01-01 | 2026-08-01 | 380 | = src | OK |
| cz_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| cz_gov_bond_10y | M | 2000-04-01 | 2026-08-01 | 317 | = src | OK |
| cz_hh_real_gdi_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| cz_hh_saving_rate | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| cz_hicp_all_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| cz_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| cz_hicp_food_idx | M | 1999-12-01 | 2026-08-01 | 321 | = src | OK |
| cz_lci_wages_idx | Q | 2000-01-01 | 2026-04-01 | 106 | = src | OK |
| cz_mm_rate_3m | M | 1993-01-01 | 2026-08-01 | 404 | = src | 1997 spike to 26% (genuine) |
| cz_policy_rate | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| cz_ppi_dom_food_mfg_idx | M | 1990-01-01 | 2026-08-01 | 440 | = src | OK |
| cz_retail_food_vol_idx | M | 2000-01-01 | 2026-07-01 | 319 | = src | OK |
| cz_retail_total_vol_idx | M | 2000-01-01 | 2026-07-01 | 319 | = src | OK |
| cz_unemp_rate_sa | M | 1993-01-01 | 2026-08-01 | 404 | = src | OK |
| de_gdp_vol_idx | Q | 1991-01-01 | 2026-04-01 | 142 | = src | OK |
| de_gov_bond_10y | M | 1980-01-01 | 2026-08-01 | 560 | = src | OK |
| de_hh_real_gdi_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| de_hh_saving_rate | Q | 1999-01-01 | 2026-04-01 | 110 | = src | OK |
| de_hicp_all_idx | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| de_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| de_hicp_food_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| de_lci_wages_idx | Q | 1996-01-01 | 2026-04-01 | 122 | = src | OK |
| de_ppi_dom_food_mfg_idx | M | 1995-01-01 | 2026-08-01 | 380 | = src | OK |
| de_retail_food_vol_idx | M | 1994-01-01 | 2026-08-01 | 392 | = src | OK |
| de_retail_total_vol_idx | M | 1994-01-01 | 2026-08-01 | 392 | = src | OK |
| de_unemp_rate_sa | M | 1991-01-01 | 2026-08-01 | 428 | = src | OK |
| dk_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| dk_gov_bond_10y | M | 1983-06-01 | 2026-08-01 | 519 | = src | OK |
| dk_hh_real_gdi_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| dk_hh_saving_rate | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| dk_hicp_all_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| dk_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| dk_hicp_food_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| dk_lci_wages_idx | Q | 2001-01-01 | 2026-04-01 | 102 | = src | OK |
| dk_mm_rate_3m | M | 1970-01-01 | 2026-09-01 | 681 | = src (Eurostat+OECD) | **FIXED: extended 2026-02..09 (OECD IR3TIB = Eurostat); 1970s-80s erratic (integer-valued) data** |
| dk_policy_rate | M | 1990-02-01 | 2026-09-01 | 440 | = src | OK |
| dk_ppi_dom_food_mfg_idx | M | 2005-01-01 | 2026-08-01 | 260 | = src | OK |
| dk_retail_food_vol_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| dk_retail_total_vol_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| dk_unemp_rate_sa | M | 1983-01-01 | 2026-08-01 | 524 | = src | **NOISY monthly LFS (+/-1.7pp m/m in 2025)** |
| ea_ecb_dfr | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| ea_ecb_mro | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| ea_euribor_3m | M | 1994-01-01 | 2026-09-01 | 393 | = src | OK |
| ea_fx_czk_per_eur | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| ea_fx_dkk_per_eur | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| ea_fx_huf_per_eur | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| ea_fx_inr_per_eur | M | 2000-01-01 | 2026-09-01 | 321 | = src | OK |
| ea_fx_nok_per_eur | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| ea_fx_pln_per_eur | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| ea_fx_ron_per_eur | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| ea_fx_sek_per_eur | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| ea_fx_usd_per_eur | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| ea_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| ea_gov_bond_10y | M | 1990-01-01 | 2026-08-01 | 440 | = src | OK |
| ea_hh_real_gdi_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| ea_hh_saving_rate | Q | 1999-01-01 | 2026-04-01 | 110 | = src | OK |
| ea_hicp_all_idx | M | 1999-12-01 | 2026-09-01 | 322 | = src | OK |
| ea_hicp_food_bev_idx | M | 1999-12-01 | 2026-08-01 | 321 | = src | OK |
| ea_hicp_food_idx | M | 1999-12-01 | 2026-08-01 | 321 | = src | OK |
| ea_lci_wages_idx | Q | 2009-01-01 | 2026-04-01 | 70 | = src | OK |
| ea_ppi_dom_food_mfg_idx | M | 1995-01-01 | 2026-08-01 | 380 | = src | OK |
| ea_retail_food_vol_idx | M | 1999-01-01 | 2026-07-01 | 331 | = src | OK |
| ea_retail_total_vol_idx | M | 2000-01-01 | 2026-07-01 | 319 | = src | OK |
| ea_unemp_rate_sa | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| ee_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| ee_gov_bond_10y | M | 2020-06-01 | 2026-08-01 | 75 | = src | starts 2020-06 (no earlier EE benchmark; documented) |
| ee_hicp_all_idx | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| ee_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| ee_hicp_food_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| ee_lci_wages_idx | Q | 2001-01-01 | 2026-04-01 | 102 | = src | OK |
| ee_retail_food_vol_idx | M | 1998-01-01 | 2026-08-01 | 344 | splice ok | OK |
| ee_retail_total_vol_idx | M | 1998-01-01 | 2026-08-01 | 344 | splice ok | OK |
| ee_unemp_rate_sa | M | 2000-02-01 | 2026-08-01 | 319 | = src | OK |
| eu_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| eu_gov_bond_10y | M | 2001-01-01 | 2026-08-01 | 308 | = src | OK |
| eu_hh_real_gdi_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| eu_hh_saving_rate | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| eu_hicp_all_idx | M | 1999-12-01 | 2026-08-01 | 321 | = src | OK |
| eu_hicp_food_bev_idx | M | 1999-12-01 | 2026-08-01 | 321 | = src | OK |
| eu_hicp_food_idx | M | 1999-12-01 | 2026-08-01 | 321 | = src | OK |
| eu_lci_wages_idx | Q | 2009-01-01 | 2026-04-01 | 70 | = src | OK |
| eu_ppi_dom_c101_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| eu_ppi_dom_c102_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | **JUMP 2009-01 -12% (as published)** |
| eu_ppi_dom_c103_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| eu_ppi_dom_c104_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| eu_ppi_dom_c105_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| eu_ppi_dom_c106_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| eu_ppi_dom_c107_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| eu_ppi_dom_c108_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| eu_ppi_dom_food_mfg_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| eu_retail_food_vol_idx | M | 1999-01-01 | 2026-07-01 | 331 | splice ok | OK |
| eu_retail_total_vol_idx | M | 2000-01-01 | 2026-07-01 | 319 | = src | OK |
| eu_unemp_rate_sa | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| fi_gdp_vol_idx | Q | 1990-01-01 | 2026-04-01 | 146 | = src | OK |
| fi_gov_bond_10y | M | 1987-11-01 | 2026-08-01 | 466 | = src | OK |
| fi_hh_real_gdi_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| fi_hh_saving_rate | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| fi_hicp_all_idx | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| fi_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| fi_hicp_food_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| fi_lci_wages_idx | Q | 2000-01-01 | 2026-04-01 | 106 | = src | OK |
| fi_ppi_dom_food_mfg_idx | M | 1995-01-01 | 2026-08-01 | 380 | = src | OK |
| fi_retail_food_vol_idx | M | 1995-01-01 | 2026-08-01 | 380 | = src | OK |
| fi_retail_total_vol_idx | M | 1995-01-01 | 2026-08-01 | 380 | = src | OK |
| fi_unemp_rate_sa | M | 1988-01-01 | 2026-08-01 | 464 | = src | OK |
| hu_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| hu_gov_bond_10y | M | 2001-01-01 | 2026-08-01 | 308 | = src | OK |
| hu_hh_real_gdi_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| hu_hh_saving_rate | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| hu_hicp_all_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| hu_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| hu_hicp_food_idx | M | 2000-12-01 | 2026-08-01 | 309 | = src | OK |
| hu_lci_wages_idx | Q | 2000-01-01 | 2026-04-01 | 106 | = src | OK |
| hu_policy_rate | M | 1990-01-01 | 2026-09-01 | 441 | = src | OK |
| hu_ppi_dom_food_mfg_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| hu_retail_food_vol_idx | M | 2000-01-01 | 2026-07-01 | 319 | = src | last 3 obs identical 102.0 (as published) |
| hu_retail_total_vol_idx | M | 2000-01-01 | 2026-07-01 | 319 | = src | OK |
| hu_unemp_rate_sa | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| in_cpi_all_idx | M | 1990-01-01 | 2026-07-01 | 439 | = src | OK |
| in_cpi_food_idx | M | 2000-01-01 | 2026-03-01 | 315 | = src | **LAG: FAOSTAT ends 2026-03; 2025 values FAO-imputed** |
| in_policy_rate | M | 1990-01-01 | 2026-06-01 | 438 | = src | lag: BIS daily data end 2026-07-23 |
| lt_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| lt_gov_bond_10y | M | 2001-01-01 | 2026-08-01 | 308 | = src | **FLAT 2.88 since 2022-11 (carried-forward primary yield)** |
| lt_hicp_all_idx | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| lt_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| lt_hicp_food_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| lt_lci_wages_idx | Q | 2000-01-01 | 2026-04-01 | 106 | = src | **BREAK 2019Q1 +30% (LT social-contribution reform)** |
| lt_ppi_dom_food_mfg_idx | M | 1998-01-01 | 2026-08-01 | 344 | = src | OK |
| lt_retail_food_vol_idx | M | 1998-01-01 | 2026-08-01 | 344 | = src | OK |
| lt_retail_total_vol_idx | M | 1998-01-01 | 2026-08-01 | 344 | = src | OK |
| lt_unemp_rate_sa | M | 1998-01-01 | 2026-08-01 | 344 | = src | OK |
| lv_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| lv_gov_bond_10y | M | 2001-01-01 | 2026-08-01 | 308 | = src | OK |
| lv_hicp_all_idx | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| lv_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| lv_hicp_food_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| lv_lci_wages_idx | Q | 2000-01-01 | 2026-04-01 | 106 | = src | OK |
| lv_retail_food_vol_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| lv_retail_total_vol_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| lv_unemp_rate_sa | M | 1998-04-01 | 2026-08-01 | 341 | = src | OK |
| no_gdp_vol_idx | Q | 1978-01-01 | 2026-04-01 | 194 | = src | OK |
| no_gov_bond_10y | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| no_hicp_all_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| no_hicp_food_bev_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| no_hicp_food_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| no_lci_wages_idx | Q | 1996-01-01 | 2026-04-01 | 122 | = src | OK |
| no_ppi_dom_food_mfg_idx | M | 1999-12-01 | 2026-08-01 | 321 | = src | OK |
| no_retail_food_vol_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| no_retail_total_vol_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| no_unemp_rate_sa | M | 1989-01-01 | 2026-08-01 | 452 | = src | OK |
| pl_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| pl_gov_bond_10y | M | 2001-01-01 | 2026-08-01 | 308 | = src | OK |
| pl_hh_real_gdi_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| pl_hh_saving_rate | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| pl_hicp_all_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| pl_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| pl_hicp_food_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| pl_lci_wages_idx | Q | 2001-01-01 | 2026-04-01 | 102 | = src | OK |
| pl_mm_rate_3m | M | 1995-01-01 | 2026-08-01 | 380 | = src | OK |
| pl_policy_rate | M | 1993-02-01 | 2026-09-01 | 404 | = src | OK |
| pl_ppi_dom_food_mfg_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| pl_retail_food_vol_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| pl_retail_total_vol_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| pl_unemp_rate_sa | M | 1997-01-01 | 2026-08-01 | 356 | = src | OK |
| ro_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| ro_gov_bond_10y | M | 2005-04-01 | 2026-08-01 | 257 | = src | OK |
| ro_hh_real_gdi_pc_idx | Q | 1999-01-01 | 2026-01-01 | 109 | = src | OK |
| ro_hh_saving_rate | Q | 1999-01-01 | 2026-01-01 | 109 | = src | **NOISY: -44.5 in 2007Q4, quarterly swings of 10pp** |
| ro_hicp_all_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| ro_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| ro_hicp_food_idx | M | 2000-12-01 | 2026-08-01 | 309 | = src | OK |
| ro_lci_wages_idx | Q | 2000-01-01 | 2026-04-01 | 106 | = src | OK |
| ro_mm_rate_3m | M | 1995-08-01 | 2026-08-01 | 373 | = src | 1997 spike to 184% (genuine, as published) |
| ro_policy_rate | M | 2003-02-01 | 2026-09-01 | 284 | = src | OK |
| ro_ppi_dom_food_mfg_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| ro_retail_food_vol_idx | M | 2000-01-01 | 2026-07-01 | 319 | = src | OK |
| ro_retail_total_vol_idx | M | 2000-01-01 | 2026-07-01 | 319 | = src | OK |
| ro_unemp_rate_sa | M | 1997-01-01 | 2026-08-01 | 356 | = src | OK |
| se_gdp_vol_idx | Q | 1993-01-01 | 2026-04-01 | 134 | = src | OK |
| se_gov_bond_10y | M | 1987-01-01 | 2026-08-01 | 476 | = src | OK |
| se_hh_real_gdi_pc_idx | Q | 1993-01-01 | 2026-01-01 | 133 | = src | OK |
| se_hh_saving_rate | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| se_hicp_all_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| se_hicp_food_bev_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| se_hicp_food_idx | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| se_lci_wages_idx | Q | 2008-01-01 | 2026-04-01 | 74 | = src | OK |
| se_ppi_dom_food_mfg_idx | M | 1990-01-01 | 2026-08-01 | 440 | = src | OK |
| se_retail_food_vol_idx | M | 1991-01-01 | 2026-08-01 | 428 | splice ok | OK |
| se_retail_total_vol_idx | M | 1991-01-01 | 2026-08-01 | 428 | splice ok | OK |
| se_unemp_rate_sa | M | 1983-01-01 | 2026-08-01 | 524 | = src | OK |
| sk_gdp_vol_idx | Q | 1995-01-01 | 2026-04-01 | 126 | = src | OK |
| sk_gov_bond_10y | M | 2001-01-01 | 2026-08-01 | 308 | = src | OK |
| sk_hicp_all_idx | M | 1996-12-01 | 2026-09-01 | 358 | = src | OK |
| sk_hicp_food_bev_idx | M | 1996-12-01 | 2026-08-01 | 357 | = src | OK |
| sk_hicp_food_idx | M | 1996-12-01 | 2026-08-01 | 357 | = src | OK |
| sk_lci_wages_idx | Q | 2000-01-01 | 2026-04-01 | 106 | = src | OK |
| sk_retail_food_vol_idx | M | 2000-01-01 | 2026-07-01 | 319 | splice ok | residual Dec seasonality 2000-03 in SCA source |
| sk_retail_total_vol_idx | M | 2000-01-01 | 2026-07-01 | 319 | = src | OK |
| sk_unemp_rate_sa | M | 1998-01-01 | 2026-08-01 | 344 | = src | OK |

### SURVEYS (218 series)

| series_id | freq | start | end | n_obs | verified vs source | status |
|---|---|---|---|---|---|---|
| at_ec_cons_conf | M | 1995-10-01 | 2026-09-01 | 372 | = src | OK |
| at_ec_cons_price_exp_12m | M | 1995-10-01 | 2026-09-01 | 372 | = src | OK |
| at_ec_cons_price_past_12m | M | 1995-10-01 | 2026-09-01 | 372 | = src | OK |
| at_ec_esi | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| at_ec_food_ind_conf | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| at_ec_food_ind_sell_price_exp | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| at_ec_food_retail_sell_price_exp | M | 2003-05-01 | 2026-09-01 | 281 | = src | OK |
| at_ec_ind_sell_price_exp | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| at_ec_retail_conf | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| at_ec_retail_sell_price_exp | M | 2003-05-01 | 2026-09-01 | 281 | = src | OK |
| at_oecd_bci | M | 1985-01-01 | 2026-08-01 | 500 | = src | OK |
| at_oecd_cci | M | 1977-01-01 | 2026-08-01 | 596 | = src | OK |
| cz_ec_cons_conf | M | 1995-01-01 | 2026-09-01 | 381 | = src | OK |
| cz_ec_cons_price_exp_12m | M | 1995-01-01 | 2026-09-01 | 381 | = src | OK |
| cz_ec_cons_price_past_12m | M | 1995-01-01 | 2026-09-01 | 381 | = src | OK |
| cz_ec_esi | M | 1995-01-01 | 2026-09-01 | 381 | = src | OK |
| cz_ec_food_ind_conf | M | 2001-01-01 | 2026-09-01 | 309 | = src | OK |
| cz_ec_food_ind_sell_price_exp | M | 2001-01-01 | 2026-09-01 | 309 | = src | OK |
| cz_ec_food_retail_sell_price_exp | M | 2003-01-01 | 2026-09-01 | 285 | = src | OK |
| cz_ec_ind_sell_price_exp | M | 1995-01-01 | 2026-09-01 | 381 | = src | OK |
| cz_ec_retail_conf | M | 1995-01-01 | 2026-09-01 | 381 | = src | OK |
| cz_ec_retail_sell_price_exp | M | 2003-05-01 | 2026-09-01 | 281 | = src | OK |
| cz_oecd_bci | M | 1993-02-01 | 2026-08-01 | 403 | = src | OK |
| cz_oecd_cci | M | 1995-01-01 | 2026-08-01 | 380 | = src | OK |
| de_ec_cons_conf | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| de_ec_cons_price_exp_12m | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| de_ec_cons_price_past_12m | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| de_ec_esi | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| de_ec_food_ind_conf | M | 1991-01-01 | 2026-09-01 | 429 | = src | OK |
| de_ec_food_ind_sell_price_exp | M | 1991-01-01 | 2026-09-01 | 429 | = src | OK |
| de_ec_food_retail_sell_price_exp | M | 1991-01-01 | 2026-09-01 | 429 | = src | OK |
| de_ec_ind_sell_price_exp | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| de_ec_retail_conf | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| de_ec_retail_sell_price_exp | M | 1991-01-01 | 2026-09-01 | 429 | = src | OK |
| de_oecd_bci | M | 1962-12-01 | 2026-08-01 | 765 | = src | OK |
| de_oecd_cci | M | 1973-01-01 | 2026-08-01 | 644 | = src | OK |
| de_oecd_cli | M | 1961-01-01 | 2026-08-01 | 788 | = src | OK |
| dk_ec_cons_conf | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| dk_ec_cons_price_exp_12m | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| dk_ec_cons_price_past_12m | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| dk_ec_esi | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| dk_ec_food_ind_conf | M | 2005-01-01 | 2026-09-01 | 261 | = src | OK |
| dk_ec_food_ind_sell_price_exp | M | 2005-01-01 | 2026-09-01 | 261 | = src | OK |
| dk_ec_food_retail_sell_price_exp | M | 2010-05-01 | 2026-09-01 | 197 | = src | OK |
| dk_ec_ind_sell_price_exp | M | 1998-01-01 | 2026-09-01 | 345 | = src | OK |
| dk_ec_retail_conf | M | 2010-05-01 | 2026-09-01 | 197 | = src | OK |
| dk_ec_retail_sell_price_exp | M | 2010-05-01 | 2026-09-01 | 197 | = src | OK |
| dk_oecd_bci | M | 1985-01-01 | 2026-08-01 | 500 | = src | OK |
| dk_oecd_cci | M | 1974-01-01 | 2026-08-01 | 632 | = src | OK |
| ea_ec_cons_conf | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| ea_ec_cons_price_exp_12m | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| ea_ec_cons_price_past_12m | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| ea_ec_esi | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| ea_ec_food_ind_conf | M | 1990-02-01 | 2026-09-01 | 440 | = src | OK |
| ea_ec_food_ind_sell_price_exp | M | 1990-11-01 | 2026-09-01 | 431 | = src | OK |
| ea_ec_food_retail_sell_price_exp | M | 1991-01-01 | 2026-09-01 | 429 | = src | OK |
| ea_ec_ind_sell_price_exp | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| ea_ec_retail_conf | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| ea_ec_retail_sell_price_exp | M | 1991-01-01 | 2026-09-01 | 429 | = src | OK |
| ea_oecd_bci | M | 1985-01-01 | 2026-08-01 | 500 | = src | OK |
| ea_oecd_cci | M | 1973-01-01 | 2026-08-01 | 644 | = src | OK |
| ee_ec_cons_conf | M | 1992-10-01 | 2026-04-01 | 403 | = src | **STALE: EC suspended Estonian surveys from 2026-05** |
| ee_ec_cons_price_exp_12m | M | 1993-04-01 | 2026-04-01 | 397 | = src | **STALE: EC suspended Estonian surveys from 2026-05; 1993-98 values constant in 6-month blocks (source)** |
| ee_ec_cons_price_past_12m | M | 1993-04-01 | 2026-04-01 | 397 | = src | **STALE: EC suspended Estonian surveys from 2026-05; 1993-98 values constant in 6-month blocks (source)** |
| ee_ec_esi | M | 1992-04-01 | 2026-04-01 | 409 | = src | **STALE: EC suspended Estonian surveys from 2026-05; transition-era extremes pre-1999 (as published)** |
| ee_ec_food_ind_conf | M | 2010-05-01 | 2026-04-01 | 192 | = src | **STALE: EC suspended Estonian surveys from 2026-05** |
| ee_ec_food_ind_sell_price_exp | M | 2010-05-01 | 2026-04-01 | 192 | = src | **STALE: EC suspended Estonian surveys from 2026-05; SA balance slightly >100 (as published)** |
| ee_ec_food_retail_sell_price_exp | M | 2010-05-01 | 2026-04-01 | 192 | = src | **STALE: EC suspended Estonian surveys from 2026-05** |
| ee_ec_ind_sell_price_exp | M | 1992-04-01 | 2026-04-01 | 409 | = src | **STALE: EC suspended Estonian surveys from 2026-05** |
| ee_ec_retail_conf | M | 1995-01-01 | 2026-04-01 | 376 | = src | **STALE: EC suspended Estonian surveys from 2026-05** |
| ee_ec_retail_sell_price_exp | M | 2003-05-01 | 2026-04-01 | 276 | = src | **STALE: EC suspended Estonian surveys from 2026-05** |
| eu_ec_cons_conf | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| eu_ec_cons_price_exp_12m | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| eu_ec_cons_price_past_12m | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| eu_ec_esi | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| eu_ec_food_ind_conf | M | 1990-04-01 | 2026-09-01 | 438 | = src | OK |
| eu_ec_food_ind_sell_price_exp | M | 1991-01-01 | 2026-09-01 | 429 | = src | OK |
| eu_ec_food_retail_sell_price_exp | M | 1991-01-01 | 2026-09-01 | 377 | = src | **GAP 1995-09..1999-12 (source)** |
| eu_ec_ind_sell_price_exp | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| eu_ec_retail_conf | M | 1985-10-01 | 2026-09-01 | 492 | = src | OK |
| eu_ec_retail_sell_price_exp | M | 2002-01-01 | 2026-09-01 | 297 | = src | OK |
| fi_ec_cons_conf | M | 1995-10-01 | 2026-09-01 | 372 | = src | OK |
| fi_ec_cons_price_exp_12m | M | 1995-10-01 | 2026-09-01 | 372 | = src | OK |
| fi_ec_cons_price_past_12m | M | 1995-10-01 | 2026-09-01 | 372 | = src | OK |
| fi_ec_esi | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| fi_ec_food_ind_conf | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| fi_ec_food_ind_sell_price_exp | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| fi_ec_food_retail_sell_price_exp | M | 2007-01-01 | 2026-09-01 | 237 | = src | OK |
| fi_ec_ind_sell_price_exp | M | 1985-01-01 | 2026-09-01 | 501 | = src | OK |
| fi_ec_retail_conf | M | 1997-05-01 | 2026-09-01 | 353 | = src | OK |
| fi_ec_retail_sell_price_exp | M | 2003-05-01 | 2026-09-01 | 281 | = src | OK |
| fi_oecd_bci | M | 1993-01-01 | 2026-08-01 | 404 | = src | OK |
| fi_oecd_cci | M | 1987-11-01 | 2026-08-01 | 466 | = src | OK |
| g7_oecd_bci | M | 1962-12-01 | 2026-08-01 | 765 | = src | OK |
| g7_oecd_cci | M | 1973-01-01 | 2026-08-01 | 644 | = src | OK |
| g7_oecd_cli | M | 1959-01-01 | 2026-08-01 | 812 | = src | OK |
| hu_ec_cons_conf | M | 1993-02-01 | 2026-09-01 | 404 | = src | OK |
| hu_ec_cons_price_exp_12m | M | 1993-02-01 | 2026-09-01 | 404 | = src | OK |
| hu_ec_cons_price_past_12m | M | 1993-02-01 | 2026-09-01 | 404 | = src | OK |
| hu_ec_esi | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| hu_ec_food_ind_conf | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| hu_ec_food_ind_sell_price_exp | M | 1997-01-01 | 2026-09-01 | 357 | = src | OK |
| hu_ec_food_retail_sell_price_exp | M | 1996-01-01 | 2026-09-01 | 369 | = src | SA balance slightly >100 (as published) |
| hu_ec_ind_sell_price_exp | M | 2000-01-01 | 2026-09-01 | 321 | = src | OK |
| hu_ec_retail_conf | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| hu_ec_retail_sell_price_exp | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| in_oecd_bci | M | 2000-05-01 | 2026-02-01 | 310 | = src | **LAG: OECD source ends 2026-02** |
| in_oecd_cci | M | 2012-08-01 | 2026-06-01 | 167 | = src | lag: OECD source ends 2026-06 |
| in_oecd_cli | M | 1994-04-01 | 2026-08-01 | 389 | = src | OK |
| lt_ec_cons_conf | M | 2001-05-01 | 2026-09-01 | 305 | = src | OK |
| lt_ec_cons_price_exp_12m | M | 2001-05-01 | 2026-09-01 | 305 | = src | OK |
| lt_ec_cons_price_past_12m | M | 2001-05-01 | 2026-09-01 | 305 | = src | OK |
| lt_ec_esi | M | 1993-05-01 | 2026-09-01 | 401 | = src | transition-era extremes pre-1999 (as published) |
| lt_ec_food_ind_conf | M | 2005-01-01 | 2026-09-01 | 261 | = src | OK |
| lt_ec_food_ind_sell_price_exp | M | 2005-01-01 | 2026-09-01 | 261 | = src | OK |
| lt_ec_food_retail_sell_price_exp | M | 2005-01-01 | 2026-09-01 | 261 | = src | **NOISY: jumps of +/-60-97 pts, little signal** |
| lt_ec_ind_sell_price_exp | M | 1993-08-01 | 2026-09-01 | 398 | = src | OK |
| lt_ec_retail_conf | M | 1995-04-01 | 2026-09-01 | 378 | = src | OK |
| lt_ec_retail_sell_price_exp | M | 2003-05-01 | 2026-09-01 | 281 | = src | OK |
| lv_ec_cons_conf | M | 1993-01-01 | 2026-09-01 | 392 | = src | **GAP 2000-04..2001-04 (source)** |
| lv_ec_cons_price_exp_12m | M | 1993-01-01 | 2026-09-01 | 392 | = src | **GAP 2000-04..2001-04 (source); 1993-98 values constant in 6-month blocks (source)** |
| lv_ec_cons_price_past_12m | M | 1993-01-01 | 2026-09-01 | 392 | = src | **GAP 2000-04..2001-04 (source); 1993-98 values constant in 6-month blocks (source)** |
| lv_ec_esi | M | 1993-04-01 | 2026-09-01 | 402 | = src | transition-era extremes pre-1999 (as published) |
| lv_ec_food_ind_conf | M | 2004-01-01 | 2026-09-01 | 273 | = src | OK |
| lv_ec_food_ind_sell_price_exp | M | 2004-01-01 | 2026-09-01 | 273 | = src | OK |
| lv_ec_food_retail_sell_price_exp | M | 2003-01-01 | 2026-09-01 | 285 | = src | OK |
| lv_ec_ind_sell_price_exp | M | 1993-04-01 | 2026-09-01 | 402 | = src | OK |
| lv_ec_retail_conf | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| lv_ec_retail_sell_price_exp | M | 2003-05-01 | 2026-09-01 | 281 | = src | OK |
| no_fn_big_purchases | Q | 1992-07-01 | 2026-07-01 | 137 | = src | OK |
| no_fn_cci_nsa | Q | 1992-07-01 | 2026-07-01 | 137 | = src | OK |
| no_fn_cci_sa | Q | 1992-07-01 | 2026-07-01 | 137 | = src | OK |
| no_fn_country_econ_next_yr | Q | 1992-07-01 | 2026-07-01 | 137 | = src | OK |
| no_fn_country_econ_past_yr | Q | 1992-10-01 | 2026-07-01 | 136 | = src | OK |
| no_fn_own_econ_next_yr | Q | 1992-07-01 | 2026-07-01 | 137 | = src | OK |
| no_fn_own_econ_past_yr | Q | 1992-07-01 | 2026-07-01 | 137 | = src | OK |
| no_nbes_bl_infl_exp_12m | Q | 2002-01-01 | 2026-07-01 | 99 | = src | OK |
| no_nbes_bl_infl_exp_2y | Q | 2002-01-01 | 2026-07-01 | 99 | = src | OK |
| no_nbes_bl_profit_next12m | Q | 2009-01-01 | 2026-07-01 | 71 | = src | OK |
| no_nbes_bl_profit_past12m | Q | 2009-01-01 | 2026-07-01 | 71 | = src | OK |
| no_nbes_bl_purch_price_di | Q | 2002-01-01 | 2026-07-01 | 99 | = src | OK |
| no_nbes_bl_sell_price_di | Q | 2002-01-01 | 2026-07-01 | 99 | = src | OK |
| no_nbes_econ_infl_exp_2y | Q | 2002-01-01 | 2026-07-01 | 99 | = src | OK |
| no_nbes_hh_infl_exp_12m | Q | 2002-07-01 | 2026-07-01 | 97 | = src | OK |
| no_nbes_hh_infl_exp_2_3y | Q | 2002-01-01 | 2026-07-01 | 99 | = src | OK |
| no_nbrn_output_cur_hhserv | Q | 2005-01-01 | 2026-07-01 | 87 | = src | OK |
| no_nbrn_output_cur_retail | Q | 2005-01-01 | 2026-07-01 | 87 | = src | OK |
| no_nbrn_output_cur_total | Q | 2005-01-01 | 2026-07-01 | 87 | = src | OK |
| no_nbrn_output_next_hhserv | Q | 2009-07-01 | 2026-07-01 | 69 | = src | OK |
| no_nbrn_output_next_retail | Q | 2005-01-01 | 2026-07-01 | 87 | = src | OK |
| no_nbrn_output_next_total | Q | 2005-01-01 | 2026-07-01 | 87 | = src | OK |
| no_nbrn_profit_retail | Q | 2005-01-01 | 2026-07-01 | 87 | = src | OK |
| no_nbrn_profit_total | Q | 2005-01-01 | 2026-07-01 | 87 | = src | OK |
| no_oecd_bci | M | 1987-03-01 | 2026-06-01 | 472 | = src | lag: OECD source ends 2026-06 (from quarterly SSB BTS) |
| no_ssb_bts_consgoods_conf | Q | 1990-01-01 | 2026-04-01 | 146 | = src | OK |
| no_ssb_bts_consgoods_home_price_exp | Q | 1990-01-01 | 2026-04-01 | 146 | = src | OK |
| no_ssb_bts_consgoods_input_price_exp | Q | 2011-10-01 | 2026-04-01 | 59 | = src | OK |
| no_ssb_bts_consgoods_profitability | Q | 2011-10-01 | 2026-04-01 | 59 | = src | OK |
| no_ssb_bts_mfg_conf | Q | 1990-01-01 | 2026-04-01 | 146 | = src | OK |
| oecd_oecd_bci | M | 1974-06-01 | 2026-08-01 | 627 | = src | OK |
| oecd_oecd_cci | M | 1973-01-01 | 2026-08-01 | 644 | = src | OK |
| pl_ec_cons_conf | M | 2001-05-01 | 2026-09-01 | 305 | = src | OK |
| pl_ec_cons_price_exp_12m | M | 2001-05-01 | 2026-09-01 | 305 | = src | OK |
| pl_ec_cons_price_past_12m | M | 2001-05-01 | 2026-09-01 | 305 | = src | OK |
| pl_ec_esi | M | 1993-10-01 | 2026-09-01 | 396 | = src | transition-era extremes pre-1999 (as published) |
| pl_ec_food_ind_conf | M | 2010-05-01 | 2026-09-01 | 197 | = src | OK |
| pl_ec_food_ind_sell_price_exp | M | 2010-05-01 | 2026-09-01 | 197 | = src | OK |
| pl_ec_food_retail_sell_price_exp | M | 2000-01-01 | 2026-09-01 | 321 | = src | OK |
| pl_ec_ind_sell_price_exp | M | 1992-06-01 | 2026-09-01 | 412 | = src | OK |
| pl_ec_retail_conf | M | 1993-10-01 | 2026-09-01 | 396 | = src | OK |
| pl_ec_retail_sell_price_exp | M | 2002-01-01 | 2026-09-01 | 297 | = src | OK |
| pl_oecd_bci | M | 1997-07-01 | 2026-08-01 | 350 | = src | OK |
| pl_oecd_cci | M | 2001-05-01 | 2026-08-01 | 304 | = src | OK |
| ro_ec_cons_conf | M | 2001-05-01 | 2026-09-01 | 305 | = src | OK |
| ro_ec_cons_price_exp_12m | M | 2001-05-01 | 2026-09-01 | 305 | = src | OK |
| ro_ec_cons_price_past_12m | M | 2001-05-01 | 2026-09-01 | 305 | = src | SA balance slightly >100 (as published) |
| ro_ec_esi | M | 1991-07-01 | 2026-09-01 | 423 | = src | **OUTLIERS 1991-94 (negative ESI, quarterly blocks)** |
| ro_ec_food_ind_conf | M | 2005-01-01 | 2026-09-01 | 261 | = src | OK |
| ro_ec_food_ind_sell_price_exp | M | 2005-01-01 | 2026-09-01 | 261 | = src | OK |
| ro_ec_food_retail_sell_price_exp | M | 2005-01-01 | 2026-09-01 | 261 | = src | OK |
| ro_ec_ind_sell_price_exp | M | 1993-04-01 | 2026-09-01 | 402 | = src | OK |
| ro_ec_retail_conf | M | 1994-01-01 | 2026-09-01 | 393 | = src | OK |
| ro_ec_retail_sell_price_exp | M | 2003-05-01 | 2026-09-01 | 281 | = src | OK |
| se_ec_cons_conf | M | 1995-10-01 | 2026-09-01 | 372 | = src | OK |
| se_ec_cons_price_exp_12m | M | 1995-10-01 | 2026-09-01 | 372 | = src | OK |
| se_ec_cons_price_past_12m | M | 1995-10-01 | 2026-09-01 | 372 | = src | OK |
| se_ec_esi | M | 1990-01-01 | 2026-09-01 | 441 | = src | OK |
| se_ec_food_ind_conf | M | 1990-04-01 | 2026-09-01 | 438 | = src | OK |
| se_ec_food_ind_sell_price_exp | M | 1990-04-01 | 2026-09-01 | 438 | = src | OK |
| se_ec_food_retail_sell_price_exp | M | 2010-05-01 | 2026-09-01 | 197 | = src | OK |
| se_ec_ind_sell_price_exp | M | 1990-01-01 | 2026-09-01 | 441 | = src | OK |
| se_ec_retail_conf | M | 1996-08-01 | 2026-09-01 | 362 | = src | OK |
| se_ec_retail_sell_price_exp | M | 2003-05-01 | 2026-09-01 | 281 | = src | OK |
| se_nier_cons_conf | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| se_nier_cons_macro | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| se_nier_cons_micro | M | 1996-01-01 | 2026-09-01 | 369 | = src | OK |
| se_nier_eti | M | 1996-07-01 | 2026-09-01 | 363 | = src | OK |
| se_nier_food_mfg_conf | M | 2000-01-01 | 2026-09-01 | 321 | = src | OK |
| se_nier_food_mfg_sell_price_exp | M | 2000-01-01 | 2026-09-01 | 321 | = src | OK |
| se_nier_grocery_purch_price_exp | M | 2015-10-01 | 2026-09-01 | 132 | = src | OK |
| se_nier_grocery_retail_conf | M | 2000-01-01 | 2026-09-01 | 321 | = src | OK |
| se_nier_grocery_sell_price_exp | M | 2003-05-01 | 2026-09-01 | 281 | = src | OK |
| se_nier_hh_infl_exp_12m_mean | M | 2001-12-01 | 2026-09-01 | 298 | = src | OK |
| se_nier_hh_infl_exp_12m_median | M | 2015-04-01 | 2026-09-01 | 138 | = src | OK |
| se_nier_retail_conf | M | 1996-07-01 | 2026-09-01 | 363 | = src | OK |
| se_oecd_bci | M | 1996-01-01 | 2026-08-01 | 368 | = src | OK |
| se_oecd_cci | M | 1995-10-01 | 2026-08-01 | 371 | = src | OK |
| sk_ec_cons_conf | M | 1999-04-01 | 2026-09-01 | 330 | = src | OK |
| sk_ec_cons_price_exp_12m | M | 1999-04-01 | 2026-09-01 | 330 | = src | OK |
| sk_ec_cons_price_past_12m | M | 1999-04-01 | 2026-09-01 | 330 | = src | OK |
| sk_ec_esi | M | 1993-08-01 | 2026-09-01 | 398 | = src | transition-era extremes pre-1999 (as published) |
| sk_ec_food_ind_conf | M | 1998-04-01 | 2026-09-01 | 342 | = src | OK |
| sk_ec_food_ind_sell_price_exp | M | 1998-04-01 | 2026-09-01 | 342 | = src | OK |
| sk_ec_food_retail_sell_price_exp | M | 2002-01-01 | 2026-09-01 | 297 | = src | OK |
| sk_ec_ind_sell_price_exp | M | 1993-08-01 | 2026-09-01 | 398 | = src | OK |
| sk_ec_retail_conf | M | 1993-09-01 | 2026-09-01 | 397 | = src | OK |
| sk_ec_retail_sell_price_exp | M | 2002-01-01 | 2026-09-01 | 297 | = src | OK |
| us_umich_sentiment | M | 1978-01-01 | 2026-09-01 | 585 | = src | OK |

### GLOBAL (87 series)

| series_id | freq | start | end | n_obs | verified vs source | status |
|---|---|---|---|---|---|---|
| dk_elspot_dk1_price | M | 2000-01-01 | 2026-09-01 | 321 | = src (2023+) | OK |
| ea_ppi_paper_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| eu_agri_barley_feed_price | M | 2015-11-01 | 2026-09-01 | 131 | = src (2023+) | possible BREAK 2026-08 (reporting stage change, documented) |
| eu_agri_barley_malting_price | M | 2015-11-01 | 2026-09-01 | 131 | = src (2023+) | possible BREAK 2026-08 (reporting stage change, documented) |
| eu_agri_beef_young_bulls_r3_price | M | 1999-12-01 | 2026-09-01 | 322 | = src (2023+) | OK |
| eu_agri_broiler_price | M | 1991-01-01 | 2026-08-01 | 428 | = src (2023+) | OK |
| eu_agri_butter_price | M | 2000-01-01 | 2026-09-01 | 321 | = src (2023+) | OK |
| eu_agri_maize_feed_price | M | 2015-11-01 | 2026-09-01 | 131 | = src (2023+) | possible BREAK 2026-08 (reporting stage change, documented) |
| eu_agri_pig_carcass_e_price | M | 1991-01-01 | 2026-09-01 | 429 | = src (2023+) | OK |
| eu_agri_raw_milk_price | M | 1990-01-01 | 2026-08-01 | 440 | = src (2023+) | OK |
| eu_agri_smp_price | M | 2000-01-01 | 2026-09-01 | 321 | = src (2023+) | OK |
| eu_agri_sugar_white_price | M | 2006-07-01 | 2026-06-01 | 240 | = src (2023+) | OK |
| eu_agri_wheat_bread_price | M | 2015-11-01 | 2026-09-01 | 131 | = src (2023+) | possible BREAK 2026-08 (reporting stage change, documented) |
| eu_agri_wmp_price | M | 2000-01-01 | 2026-09-01 | 321 | = src (2023+) | OK |
| eu_ppi_paper_packaging_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| eu_ppi_plastic_products_idx | M | 2000-01-01 | 2026-08-01 | 320 | = src | OK |
| fi_elspot_price | M | 2015-01-01 | 2026-09-01 | 141 | = src | OK |
| glob_fao_cereals_idx | M | 1990-01-01 | 2026-09-01 | 441 | = src | OK |
| glob_fao_dairy_idx | M | 1990-01-01 | 2026-09-01 | 441 | = src | OK |
| glob_fao_ffpi | M | 1990-01-01 | 2026-09-01 | 441 | = src | OK |
| glob_fao_ffpi_eur | M | 1999-01-01 | 2026-09-01 | 333 | derived ok | derived; base-period mean 98.6-99.9 (labelled approx.) |
| glob_fao_ffpi_nok | M | 1990-01-01 | 2026-09-01 | 441 | derived ok | derived; base-period mean 98.6-99.9 (labelled approx.) |
| glob_fao_ffpi_real | M | 1990-01-01 | 2026-09-01 | 441 | = src | OK |
| glob_fao_meat_idx | M | 1990-01-01 | 2026-09-01 | 441 | = src | OK |
| glob_fao_sugar_idx | M | 1990-01-01 | 2026-09-01 | 441 | = src | OK |
| glob_fao_vegoils_idx | M | 1990-01-01 | 2026-09-01 | 441 | = src | OK |
| glob_fx_eurnok | M | 1999-01-01 | 2026-09-01 | 333 | derived ok | OK |
| glob_fx_eurusd | M | 1999-01-01 | 2026-09-01 | 333 | = src | OK |
| glob_fx_usd_broad_idx | M | 1973-01-01 | 2026-09-01 | 645 | = src | OK |
| glob_fx_usdnok | M | 1971-01-01 | 2026-09-01 | 669 | = src | OK |
| glob_fx_usdsek | M | 1971-01-01 | 2026-09-01 | 669 | = src | OK |
| glob_gscpi | M | 1998-01-01 | 2026-08-01 | 344 | = src | OK |
| glob_imf_allcomm_idx | M | 1992-01-01 | 2026-07-01 | 415 | = src | OK |
| glob_imf_food_idx | M | 1992-01-01 | 2026-07-01 | 415 | = src | OK |
| glob_imf_foodbev_idx | M | 1992-01-01 | 2026-07-01 | 415 | = src | OK |
| glob_wb_agri_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_aluminum | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_banana_eu | M | 1997-01-01 | 2026-09-01 | 357 | = src | OK |
| glob_wb_barley | M | 1960-01-01 | 2020-08-01 | 728 | = src | **DISCONTINUED by World Bank after 2020-08** |
| glob_wb_beef | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_beverages_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_brent | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_chicken | M | 1960-01-01 | 2026-09-01 | 801 | = src | **BREAK 2021-09 US->Brazil (documented)** |
| glob_wb_coal_aus | M | 1970-01-01 | 2026-09-01 | 681 | = src | OK |
| glob_wb_cocoa | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_coffee_arabica | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_coffee_robusta | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_dap | M | 1967-01-01 | 2026-09-01 | 717 | = src | OK |
| glob_wb_energy_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_fertilizers_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_food_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_food_idx_eur | M | 1999-01-01 | 2026-09-01 | 333 | derived ok | derived; base-period mean 98.6-99.9 (labelled approx.) |
| glob_wb_food_idx_nok | M | 1971-01-01 | 2026-09-01 | 669 | derived ok | derived; base-period mean 98.6-99.9 (labelled approx.) |
| glob_wb_grains_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_maize | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_metals_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_natgas_eu | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_nonenergy_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_oilsmeals_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_orange | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_otherfood_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_palm_oil | M | 1960-01-01 | 2026-09-01 | 801 | = src | **BREAKS: several basis changes (documented)** |
| glob_wb_rapeseed_oil | M | 2002-02-01 | 2026-09-01 | 296 | = src | OK |
| glob_wb_rawmat_idx | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_rice_thai5 | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_soybean_oil | M | 1960-01-01 | 2026-09-01 | 801 | = src | **BREAK 2025-01 basis change (documented)** |
| glob_wb_soybeans | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_sugar_eu | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_sugar_world | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_sunflower_oil | M | 2002-02-01 | 2026-09-01 | 291 | = src | **GAP 5 months in 2002 (source)** |
| glob_wb_tea | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_tin | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_urea | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_wheat_us_hrw | M | 1960-01-01 | 2026-09-01 | 801 | = src | OK |
| glob_wb_wheat_us_srw | M | 1979-01-01 | 2026-09-01 | 573 | = src | OK |
| no_elspot_country_avg_price | M | 2015-01-01 | 2026-09-01 | 141 | = src | OK |
| no_elspot_no2_price | M | 2000-01-01 | 2026-09-01 | 321 | = src (2023+) | OK |
| nordic_elspot_system_price | M | 2000-01-01 | 2025-01-01 | 301 | = src (2023+) | **DISCONTINUED in free source after 2025-01** |
| se_elspot_se3_price | M | 2000-01-01 | 2026-09-01 | 311 | = src (2023+) | **GAP 2011-01..10 (null in source)** |
| us_fed_funds_rate | M | 1954-07-01 | 2026-09-01 | 867 | = src | OK |
| us_ppi_corrugated_boxes_idx | M | 1980-03-01 | 2026-08-01 | 558 | = src | OK |
| us_ppi_deep_sea_freight_idx | M | 1988-06-01 | 2026-08-01 | 459 | = src | OK |
| us_ppi_glass_containers_idx | M | 1965-01-01 | 2026-08-01 | 740 | = src | OK |
| us_ppi_metal_cans_idx | M | 1967-01-01 | 2026-08-01 | 716 | = src | OK |
| us_ppi_plastic_resins_idx | M | 1976-06-01 | 2026-08-01 | 603 | = src | OK |
| us_ppi_wood_pulp_idx | M | 1926-01-01 | 2026-08-01 | 1208 | = src | OK |
| us_treasury_10y | M | 1953-04-01 | 2026-09-01 | 882 | = src | OK |
