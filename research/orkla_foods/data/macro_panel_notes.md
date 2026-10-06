# Macro feature panel (quarterly) - method notes

Built by `macro_panel_build.py` (label macro-panel) on the data as of 2026-10-06 (latest Orkla report Q2 2026). Re-run with `python3 -I macro_panel_build.py`; the script reads only `data/macro/*/` and `data/orkla_raw/geo_weights.csv` and regenerates this file. Independent verification and fixes: `macro_panel_qa.md`.

## Outputs

| file | content |
|---|---|
| `macro_panel_quarterly.csv` | index `period` (YYYYQn) 1995Q1..2026Q3 (127 rows) x 1420 features |
| `feature_dictionary.csv` | one row per feature: base series, folder, transform, description, country, category, core flag, real-time lag, start/end/n_obs, notes |
| `macro_panel_geo_weights_quarterly.csv` | raw Orkla Foods country weights per quarter (before renormalisation over countries with data), with the segment definition and source year used |

## 1. Method

**Quarterly aggregation.** Monthly series: mean of the three months, only when all three are present (no partial quarters, so a quarter whose last month is not yet published is NaN). Quarterly series as published (first day of quarter -> quarter). Annual series: the annual value is assigned to all four quarters of the year (flagged `ANNUAL` in the dictionary notes); the agricultural settlement series (`no_jordbruk_*`, effective 1 July) are assigned by effective date to Q3(Y)..Q2(Y+1). Food VAT rates are monthly step series and are averaged within the quarter (so a mid-quarter change gives a fractional quarterly rate).

**Look-ahead guard.** Nothing dated after Sep-2026 enters: monthly obs > 2026-09, quarterly obs > 2026Q3. This removes the ECB wage tracker's projected quarters 2026Q4-2027Q2 and the legislated future VAT months (NO to 2026-12, SE to 2026-10). The 2026Q3 wage-tracker value (current quarter at its latest release) is kept.

**Transforms** (feature id = `<series_id>__<transform>`):

| series type | transforms |
|---|---|
| index, price, currency level, volume, wage index, FX rate, income level | `yoy` = 100*ln(x_t/x_t-4); `dyoy` = yoy_t - yoy_t-4 |
| interest rates, yields, unemployment and saving rates (percent) | `lvl`; `d4` = x_t - x_t-4 |
| survey balances, confidence indicators (EC, OECD, NIER, Finans Norge, UMich), diffusion indices, expectations in percent, GSCPI | `lvl`; `d4` |
| series already in y/y growth (wage growth, real wage growth, credit growth, negotiated wages, wage tracker, frontfag) | `lvl`; `d4` |
| food VAT rates, agricultural settlement (NOK million changes) | `lvl`; `d4` |

yoy is only computed for strictly positive values. Composites use `<name>_yoy`/`_dyoy`, `_lvl`/`_d4` or `_z`/`_z_d4`.

**Duplicates.** Identical or near-identical copies across folders are kept once (27 series dropped):

- `WAGES/no_cpi_idx`: identical to NO/no_cpi_total_idx (qa_B I11)
- `WAGES/se_cpi_idx`: identical to SE/se_cpi_idx (qa_B I11)
- `WAGES/se_cpif_idx`: identical to SE/se_cpif_idx (qa_B I11)
- `WAGES/dk_hicp_idx`: identical to EU/dk_hicp_all_idx (qa_B I11)
- `WAGES/fi_hicp_idx`: identical to EU/fi_hicp_all_idx (qa_B I11)
- `WAGES/cz_hicp_idx`: identical to EU/cz_hicp_all_idx (qa_B I11)
- `WAGES/ea_hicp_idx`: near-identical to EU/ea_hicp_all_idx (EA changing composition vs EA20; yoy corr 0.9999)
- `WAGES/ea_hh_real_disp_inc_pc_idx`: identical to EU/ea_hh_real_gdi_pc_idx (qa_B I11)
- `WAGES/no_exp_infl_12m_business`: identical to SURVEYS/no_nbes_bl_infl_exp_12m (qa_B I11)
- `WAGES/no_cpi_annual_idx`: annual average of NO/no_cpi_total_idx (redundant)
- `EU/no_gov_bond_10y`: identical to NO/no_govbond_10y (qa_B I11)
- `EU/no_retail_total_vol_idx`: identical to NO/no_retail_vol_sa_idx (qa_B I11)
- `SE/se_unemp_rate_sa`: same id and values as EU/se_unemp_rate_sa, which is longer (1983-) and is kept
- `EU/se_gov_bond_10y`: same id as SE/se_gov_bond_10y; Riksbank benchmark (SE) kept, EMU-convergence copy dropped (yoy corr 0.99)
- `EU/no_ppi_dom_food_mfg_idx`: near-identical to NO/no_ppi_food_dom_idx (SSB, 10-day lag) which is kept
- `EU/se_ppi_dom_food_mfg_idx`: near-identical to SE/se_ppi_food_hmpi_idx (SCB HMPI) which is kept (yoy corr 0.9998)
- `NO/no_lfs_unemp_rate_sa`: near-identical to EU/no_unemp_rate_sa (max diff 0.1pp), which is longer and kept
- `GLOBAL/no_elspot_no2_price`: identical to NO/no_elspot_no2_eur (qa_B I11)
- `GLOBAL/nordic_elspot_system_price`: identical to NO/no_elspot_system_eur (qa_B I11)
- `GLOBAL/se_elspot_se3_price`: near-identical to SE/se_elspot_se3_eur_mwh (kept); GLOBAL copy has 2011-01..10 gap
- `EU/ea_fx_nok_per_eur`: near-identical to NO/no_fx_eurnok (Norges Bank) which is kept
- `GLOBAL/glob_fx_eurnok`: near-identical to NO/no_fx_eurnok which is kept
- `EU/ea_fx_sek_per_eur`: near-identical to SE/se_eursek (Riksbank) which is kept
- `GLOBAL/glob_fx_eurusd`: near-identical to EU/ea_fx_usd_per_eur which is kept
- `GLOBAL/glob_fx_usdnok`: near-identical to NO/no_fx_usdnok which is kept
- `GLOBAL/glob_fx_usdsek`: near-identical to SE/se_usdsek which is kept
- `SE/se_noksek`: inverse of NO/no_fx_seknok (yoy would be exactly the negative)

**Real-time availability (`realtime_min_lag_q`).** From the catalog's `approx_release_lag_days` (days after the end of the reference period): 0 if <= 14 (available before a quarterly report published ~2 weeks after quarter end), 1 if <= 100, else 2. Negative lags (surveys fielded inside the quarter, legislated rates) give 0. Annual series assigned to all four quarters are measured from the end of Q1 (lag + 275 days, then ceil((d-14)/91.3)), so annual outcomes (e.g. TBU wage growth) get 4 and the agricultural price index (budget estimate published Aug/Sep) gets 2; known-in-advance policy values get 0 (July-effective agricultural settlement assigned from Q3; frontfag frame, agreed by mid-April). Composites and spreads take the maximum over all component series. Note: country HICPs have a 17-day lag, so the Orkla-weighted price composites are lag 1 while the Nordic (NO+SE, national CPI) versions are lag 0.

## 2. Orkla Foods geographic weights

Shares of external revenue by customer location from `geo_weights.csv`, stepped by year, using the segment definition that was the reported food segment in each quarter:

| quarters | definition used | source year of the split |
|---|---|---|
| 1995Q1-1999Q4 | 2000-2007 Orkla Foods (proxy = 2004 split) | 2000 row |
| 2000Q1-2006Q4 | 2000-2007 Orkla Foods (2000-03 proxy; 2004-06 exact) | same year |
| 2007Q1-2007Q4 | 2000-2007 Orkla Foods | 2006 (no 2007 split for this definition) |
| 2008Q1-2011Q4 | Orkla Foods Nordic (2008-2012 def.) | same year |
| 2012Q1-2012Q4 | Orkla Foods (2013-2014 def.) | 2012 (OFN 2012 split not published; Bakers sold Q1-2012) |
| 2013Q1-2014Q3 | Orkla Foods (2013-2014 def.) | 2013 |
| 2014Q4-2021Q4 | Orkla Foods (2015-2022 def., incl. India) | same year (AR rows) |
| 2022Q1-2022Q2 | Orkla Foods (2015-2022 def.) | 2021 |
| 2022Q3-2023Q4 | Orkla Foods Europe | same year |
| 2024Q1-2025Q4 | Orkla Foods (renamed, same scope) | same year |
| 2026Q1-2026Q3 | Orkla Foods | 2025 |

Region -> country mapping:

- Norway -> NO, Sweden -> SE, Denmark -> DK, Finland (and Iceland) -> FI.
- The Baltics -> EE, LV, LT (one third each). In the 2008-2014 definitions the Baltic food companies (and Kalev, 2010-2012) are booked as 'Central and Eastern Europe', which is therefore mapped to the Baltics as well.
- 2000-2007 definition: 'Rest of Western Europe' -> AT 60% (Felix Austria) / DE 40% (exports); 'Central and Eastern Europe' up to 9.6%: 2.0pp -> Baltics (Baltic food companies were in Orkla Foods International until the 2008 restatement moved ~257 MNOK to OF Nordic), the rest -> PL, CZ, HU (+RO from 2002) equally; the excess in 2005-07 (SladCo/Krupskaya) -> Russia (no data). Asia / rest of world dropped.
- 2008-2014 definitions: 'Rest of Western Europe' -> DE; Asia, North America, other -> dropped.
- 2015-2022 definition: 'Rest of Europe' split into CZ+SK / AT / other using the project estimates in geo_weights (2017 and 2021 rows; 2014-15 from the 2015 Investor Day CZ 4% / AT 3%; 2016 = 2017; 2018-20 linearly interpolated). CZ+SK -> CZ 75% / SK 25% (assumption). 'Other Europe' -> HU, RO, PL, DE, RU equally (RU has no data). 'Rest of the world' -> India (MTR, Eastern).
- Orkla Foods Europe / Orkla Foods (2022Q3-): 'Rest of Europe' split CZ+SK / AT / HU / other from the 2023 and 2025 estimate rows (2022 = 2023, 2024 = average). 'Other' -> RO, DE, UK equally (UK no data). 'Rest of the world' (exports, <1%) dropped.

Rest-of-Europe composition used (fractions of the 'Rest of Europe' share):

| year | CZ+SK | AT | HU | other |
|---|---|---|---|---|
| 2014 (2015-22 def.) | 0.380 | 0.285 | in other | 0.335 |
| 2015 (2015-22 def.) | 0.380 | 0.285 | in other | 0.335 |
| 2016 (2015-22 def.) | 0.594 | 0.139 | in other | 0.267 |
| 2017 (2015-22 def.) | 0.594 | 0.139 | in other | 0.267 |
| 2018 (2015-22 def.) | 0.591 | 0.137 | in other | 0.272 |
| 2019 (2015-22 def.) | 0.588 | 0.136 | in other | 0.277 |
| 2020 (2015-22 def.) | 0.584 | 0.134 | in other | 0.281 |
| 2021 (2015-22 def.) | 0.581 | 0.133 | in other | 0.286 |
| 2022 (Europe def.) | 0.618 | 0.130 | 0.071 | 0.181 |
| 2023 (Europe def.) | 0.618 | 0.130 | 0.071 | 0.181 |
| 2024 (Europe def.) | 0.620 | 0.130 | 0.072 | 0.178 |
| 2025 (Europe def.) | 0.622 | 0.129 | 0.073 | 0.176 |

Raw country weights (% of segment revenue; before renormalisation over countries with data). One row per change point:

| period | def. | yr | NO | SE | DK | FI | EE | LV | LT | CZ | SK | AT | HU | RO | PL | DE | IN | RU | UK | DROP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1995Q1 | A | 2000 | 36.8 | 32.5 | 11.1 | 5.2 | 0.7 | 0.7 | 0.7 | 2.5 | 0.0 | 2.5 | 2.5 | 0.0 | 2.5 | 1.7 | 0.0 | 0.0 | 0.0 | 0.5 |
| 2001Q1 | A | 2001 | 36.8 | 32.5 | 11.1 | 5.2 | 0.7 | 0.7 | 0.7 | 2.5 | 0.0 | 2.5 | 2.5 | 0.0 | 2.5 | 1.7 | 0.0 | 0.0 | 0.0 | 0.5 |
| 2002Q1 | A | 2002 | 36.8 | 32.5 | 11.1 | 5.2 | 0.7 | 0.7 | 0.7 | 1.9 | 0.0 | 2.5 | 1.9 | 1.9 | 1.9 | 1.7 | 0.0 | 0.0 | 0.0 | 0.5 |
| 2003Q1 | A | 2003 | 36.8 | 32.5 | 11.1 | 5.2 | 0.7 | 0.7 | 0.7 | 1.9 | 0.0 | 2.5 | 1.9 | 1.9 | 1.9 | 1.7 | 0.0 | 0.0 | 0.0 | 0.5 |
| 2004Q1 | A | 2004 | 36.8 | 32.5 | 11.1 | 5.2 | 0.7 | 0.7 | 0.7 | 1.9 | 0.0 | 2.5 | 1.9 | 1.9 | 1.9 | 1.7 | 0.0 | 0.0 | 0.0 | 0.6 |
| 2005Q1 | A | 2005 | 33.2 | 28.5 | 10.3 | 6.1 | 0.7 | 0.7 | 0.7 | 1.9 | 0.0 | 2.6 | 1.9 | 1.9 | 1.9 | 1.7 | 0.0 | 7.3 | 0.0 | 0.6 |
| 2006Q1 | A | 2006 | 32.4 | 28.9 | 10.1 | 6.9 | 0.7 | 0.7 | 0.7 | 1.9 | 0.0 | 2.7 | 1.9 | 1.9 | 1.9 | 1.8 | 0.0 | 7.2 | 0.0 | 0.5 |
| 2008Q1 | B | 2008 | 43.8 | 33.6 | 6.3 | 10.4 | 1.1 | 1.1 | 1.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2.1 | 0.0 | 0.0 | 0.0 | 0.5 |
| 2009Q1 | B | 2009 | 44.5 | 32.8 | 6.3 | 10.9 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2.1 | 0.0 | 0.0 | 0.0 | 0.5 |
| 2010Q1 | B | 2010 | 42.7 | 34.4 | 5.8 | 10.5 | 1.4 | 1.4 | 1.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.9 | 0.0 | 0.0 | 0.0 | 0.6 |
| 2011Q1 | B | 2011 | 42.2 | 35.0 | 5.4 | 9.9 | 1.7 | 1.7 | 1.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.8 | 0.0 | 0.0 | 0.0 | 0.5 |
| 2012Q1 | C | 2012 | 40.1 | 40.1 | 5.9 | 8.2 | 1.2 | 1.2 | 1.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.7 | 0.0 | 0.0 | 0.0 | 0.5 |
| 2013Q1 | C | 2013 | 42.9 | 37.0 | 7.6 | 7.2 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2.0 | 0.0 | 0.0 | 0.0 | 0.3 |
| 2014Q4 | D | 2014 | 37.6 | 30.7 | 7.0 | 6.3 | 0.9 | 0.9 | 0.9 | 3.0 | 1.0 | 3.0 | 0.7 | 0.7 | 0.7 | 0.7 | 5.1 | 0.7 | 0.0 | 0.0 |
| 2015Q1 | D | 2015 | 36.0 | 31.2 | 7.2 | 6.5 | 1.0 | 1.0 | 1.0 | 2.8 | 0.9 | 2.8 | 0.7 | 0.7 | 0.7 | 0.7 | 6.5 | 0.7 | 0.0 | 0.0 |
| 2016Q1 | D | 2016 | 31.2 | 28.4 | 8.0 | 5.7 | 1.0 | 1.0 | 1.0 | 8.0 | 2.7 | 2.5 | 1.0 | 1.0 | 1.0 | 1.0 | 6.0 | 1.0 | 0.0 | 0.0 |
| 2017Q1 | D | 2017 | 29.9 | 27.2 | 8.2 | 5.6 | 0.9 | 0.9 | 0.9 | 9.0 | 3.0 | 2.8 | 1.1 | 1.1 | 1.1 | 1.1 | 6.1 | 1.1 | 0.0 | 0.0 |
| 2018Q1 | D | 2018 | 29.4 | 26.8 | 6.5 | 6.0 | 1.0 | 1.0 | 1.0 | 9.7 | 3.2 | 3.0 | 1.2 | 1.2 | 1.2 | 1.2 | 6.3 | 1.2 | 0.0 | 0.0 |
| 2019Q1 | D | 2019 | 28.2 | 26.8 | 7.5 | 5.9 | 1.0 | 1.0 | 1.0 | 9.5 | 3.2 | 2.9 | 1.2 | 1.2 | 1.2 | 1.2 | 6.8 | 1.2 | 0.0 | 0.0 |
| 2020Q1 | D | 2020 | 26.4 | 28.3 | 7.8 | 6.0 | 1.1 | 1.1 | 1.1 | 9.3 | 3.1 | 2.9 | 1.2 | 1.2 | 1.2 | 1.2 | 7.0 | 1.2 | 0.0 | 0.0 |
| 2021Q1 | D | 2021 | 26.1 | 26.1 | 7.7 | 6.1 | 1.0 | 1.0 | 1.0 | 8.8 | 3.0 | 2.7 | 1.2 | 1.2 | 1.2 | 1.2 | 10.6 | 1.2 | 0.0 | 0.0 |
| 2022Q3 | E | 2022 | 28.1 | 28.3 | 9.1 | 7.8 | 1.1 | 1.1 | 1.1 | 10.6 | 3.5 | 3.0 | 1.6 | 1.4 | 0.0 | 1.4 | 0.0 | 0.0 | 1.4 | 0.6 |
| 2023Q1 | E | 2023 | 26.9 | 27.2 | 9.5 | 8.4 | 1.2 | 1.2 | 1.2 | 11.0 | 3.7 | 3.1 | 1.7 | 1.4 | 0.0 | 1.4 | 0.0 | 0.0 | 1.4 | 0.6 |
| 2024Q1 | F | 2024 | 27.3 | 27.9 | 9.7 | 8.0 | 1.2 | 1.2 | 1.2 | 10.7 | 3.6 | 3.0 | 1.7 | 1.4 | 0.0 | 1.4 | 0.0 | 0.0 | 1.4 | 0.5 |
| 2025Q1 | F | 2025 | 26.4 | 29.1 | 9.4 | 7.8 | 1.2 | 1.2 | 1.2 | 10.9 | 3.6 | 3.0 | 1.7 | 1.4 | 0.0 | 1.4 | 0.0 | 0.0 | 1.4 | 0.4 |

For each composite and quarter the weights of the countries that have data are renormalised to sum to 1 (checked in the build). Orkla-weighted composites are NaN when the covered share is below max(40%, 80% x the composite's median coverage over 2005Q1-2025Q4), so that a quarter is not computed from a much smaller country set than usual (typically the latest quarter, when only the fast-publishing Nordic data are out, or years before a large country's series starts). Nordic composites (prefix `nw_`) use NO/(NO+SE) and require both countries.

## 3. Composites and spreads

Notation: yoy_c = country yoy (log points); w_c,t = renormalised Orkla weight. `w_X_yoy` = sum_c w_c,t * yoy_c,t. The dyoy/d4 companions are computed as the weighted average of the country-level dyoy/d4 with weights at t (not as a difference of the composite), so that changes in the weights (e.g. India leaving the segment in 2022Q3) do not create spurious jumps.

| feature(s) | formula / components | lag |
|---|---|---|
| `w_food_cpi_yoy`, `w_food_cpi_dyoy` | Orkla-weighted food CPI inflation (national CPI food NO/SE, HICP CP011 EU countries). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE. Components: at_hicp_food_idx, cz_hicp_food_idx, de_hicp_food_idx, dk_hicp_food_idx, ee_hicp_food_idx, fi_hicp_food_idx, hu_hicp_food_idx, lt_hicp_food_idx, ... (14 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). India excluded (FAOSTAT food CPI: 120-day lag, 2025 FAO-imputed). | 1 |
| `w_cpi_yoy`, `w_cpi_dyoy` | Orkla-weighted headline CPI inflation (CPI NO/SE, HICP all items EU, CPI India). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE,IN. Components: at_hicp_all_idx, cz_hicp_all_idx, de_hicp_all_idx, dk_hicp_all_idx, ee_hicp_all_idx, fi_hicp_all_idx, hu_hicp_all_idx, in_cpi_all_idx, ... (15 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). | 1 |
| `w_food_cpi_rel_yoy`, `w_food_cpi_rel_dyoy` | Orkla-weighted relative food inflation (country food CPI yoy minus headline CPI yoy). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE. Components: at_hicp_all_idx, at_hicp_food_idx, cz_hicp_all_idx, cz_hicp_food_idx, de_hicp_all_idx, de_hicp_food_idx, dk_hicp_all_idx, dk_hicp_food_idx, ... (28 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). India excluded (FAOSTAT food CPI: 120-day lag, 2025 FAO-imputed). | 1 |
| `w_food_cpi_xvat_yoy`, `w_food_cpi_xvat_dyoy` | Orkla-weighted food CPI inflation with NO and SE adjusted for food-VAT changes (yoy - 100*ln((1+vat_t)/(1+vat_t-4))). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE. Components: at_hicp_food_idx, cz_hicp_food_idx, de_hicp_food_idx, dk_hicp_food_idx, ee_hicp_food_idx, fi_hicp_food_idx, hu_hicp_food_idx, lt_hicp_food_idx, ... (16 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). Other countries unadjusted (no VAT history in the data). India excluded (FAOSTAT food CPI: 120-day lag, 2025 FAO-imputed). | 1 |
| `w_wage_yoy`, `w_wage_dyoy` | Orkla-weighted nominal wage growth (LCI wages & salaries; national wage indices for SE (MI), DK (private earnings) and FI (wage & salary index)). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,HU,RO,PL,AT,DE. Components: at_lci_wages_idx, cz_lci_wages_idx, de_lci_wages_idx, dk_wage_idx_private_q, ee_lci_wages_idx, fi_wage_idx_q, hu_lci_wages_idx, lt_lci_wages_idx, ... (14 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). LT LCI yoy NaN 2019Q1-Q4 (tax-reform level break). | 1 |
| `w_real_wage_yoy`, `w_real_wage_dyoy` | Orkla-weighted real wage growth (country nominal wage yoy minus headline CPI yoy, log points). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,HU,RO,PL,AT,DE. Components: at_hicp_all_idx, at_lci_wages_idx, cz_hicp_all_idx, cz_lci_wages_idx, de_hicp_all_idx, de_lci_wages_idx, dk_hicp_all_idx, dk_wage_idx_private_q, ... (28 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). | 1 |
| `w_cons_conf_z`, `w_cons_conf_z_d4` | Orkla-weighted consumer confidence, z-scored per country over 2000Q1-2025Q4 (Norway: Finans Norge Forventningsbarometer SA; others: EC consumer confidence). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE. Components: at_ec_cons_conf, cz_ec_cons_conf, de_ec_cons_conf, dk_ec_cons_conf, ee_ec_cons_conf, fi_ec_cons_conf, hu_ec_cons_conf, lt_ec_cons_conf, ... (14 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). India excluded (OECD CCI only from 2012, 15-day lag). | 0 |
| `w_retail_food_vol_yoy`, `w_retail_food_vol_dyoy` | Orkla-weighted retail sales volume growth, food, beverages & tobacco (Eurostat G47_FOOD). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE. Components: at_retail_food_vol_idx, cz_retail_food_vol_idx, de_retail_food_vol_idx, dk_retail_food_vol_idx, ee_retail_food_vol_idx, fi_retail_food_vol_idx, hu_retail_food_vol_idx, lt_retail_food_vol_idx, ... (14 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). | 1 |
| `w_retail_total_vol_yoy`, `w_retail_total_vol_dyoy` | Orkla-weighted total retail sales volume growth (excl. motor vehicles). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE. Components: at_retail_total_vol_idx, cz_retail_total_vol_idx, de_retail_total_vol_idx, dk_retail_total_vol_idx, ee_retail_total_vol_idx, fi_retail_total_vol_idx, hu_retail_total_vol_idx, lt_retail_total_vol_idx, ... (14 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). | 1 |
| `w_gdp_vol_yoy`, `w_gdp_vol_dyoy` | Orkla-weighted real GDP growth (Mainland GDP for Norway). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE. Components: at_gdp_vol_idx, cz_gdp_vol_idx, de_gdp_vol_idx, dk_gdp_vol_idx, ee_gdp_vol_idx, fi_gdp_vol_idx, hu_gdp_vol_idx, lt_gdp_vol_idx, ... (14 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). | 1 |
| `w_hh_real_inc_yoy`, `w_hh_real_inc_dyoy` | Orkla-weighted household real disposable income growth (per capita where available; Norway excl. dividends, from 2007). Countries: NO,SE,DK,FI,CZ,AT,DE,HU,PL,RO. Components: at_hh_real_gdi_pc_idx, cz_hh_real_gdi_pc_idx, de_hh_real_gdi_pc_idx, dk_hh_real_gdi_pc_idx, fi_hh_real_gdi_pc_idx, hu_hh_real_gdi_pc_idx, no_hh_real_disp_inc_xdiv_sa_q, pl_hh_real_gdi_pc_idx, ... (10 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). | 1 |
| `w_food_ppi_yoy`, `w_food_ppi_dyoy` | Orkla-weighted domestic producer-price inflation, manufacture of food products (NACE C10). Countries: NO,SE,DK,FI,LT,CZ,AT,HU,RO,PL,DE. Components: at_ppi_dom_food_mfg_idx, cz_ppi_dom_food_mfg_idx, de_ppi_dom_food_mfg_idx, dk_ppi_dom_food_mfg_idx, fi_ppi_dom_food_mfg_idx, hu_ppi_dom_food_mfg_idx, lt_ppi_dom_food_mfg_idx, no_ppi_food_dom_idx, ... (11 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). No food PPI for EE, LV, SK, IN in the data (renormalised). | 1 |
| `w_unemp_lvl`, `w_unemp_d4` | Orkla-weighted unemployment rate (ILO/LFS, SA). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE. Components: at_unemp_rate_sa, cz_unemp_rate_sa, de_unemp_rate_sa, dk_unemp_rate_sa, ee_unemp_rate_sa, fi_unemp_rate_sa, hu_unemp_rate_sa, lt_unemp_rate_sa, ... (14 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). | 1 |
| `w_policy_rate_lvl`, `w_policy_rate_d4` | Orkla-weighted central-bank policy rate. Countries: NO,SE,DK,CZ,HU,PL,RO,IN,FI,AT,DE,EE,LV,LT,SK. Components: cz_policy_rate, dk_policy_rate, ea_ecb_dfr, ea_ecb_mro, hu_policy_rate, in_policy_rate, no_policy_rate, pl_policy_rate, ... (10 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). Euro members use the ECB effective rate (MRO to 2008-09, deposit rate from 2008-10) from 1999 (SK from 2009; Baltic pegs proxied by the ECB rate from 1999). | 0 |
| `w_gov10y_lvl`, `w_gov10y_d4` | Orkla-weighted 10-year government bond yield. Countries: NO,SE,DK,FI,CZ,AT,DE,HU,PL,RO,SK,LV. Components: at_gov_bond_10y, cz_gov_bond_10y, de_gov_bond_10y, dk_gov_bond_10y, fi_gov_bond_10y, hu_gov_bond_10y, lv_gov_bond_10y, no_govbond_10y, ... (12 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). LT (flat carried-forward yield) and EE (2020- only) excluded; Baltics = LV. | 0 |
| `w_fx_vs_eur_yoy`, `w_fx_vs_eur_dyoy` | Orkla-weighted yoy change of local currency per EUR (+ = local currencies weaker vs EUR). Countries: NO,SE,DK,CZ,HU,PL,RO,IN,FI,AT,DE,EE,LT,LV,SK. Components: ea_fx_czk_per_eur, ea_fx_dkk_per_eur, ea_fx_huf_per_eur, ea_fx_inr_per_eur, ea_fx_pln_per_eur, ea_fx_ron_per_eur, no_fx_czknok, no_fx_dkknok, ... (11 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). Euro members (and EUR-pegged EE from 1995, LT from 2003, LV from 2006) have zero yoy vs EUR; SK from 2010 (NaN before, SKK not in data). Before 1999 EUR = ECU: NO via NOK/SEK x SEK/ECU, DK and CZ via their NOK crosses; FI/AT/DE legacy currencies not in data (NaN before 1999). | 0 |
| `w_fx_vs_usd_yoy`, `w_fx_vs_usd_dyoy` | Orkla-weighted yoy change of local currency per USD (+ = local currencies weaker vs USD; cross rates via EUR). Countries: NO,SE,DK,CZ,HU,PL,RO,IN,FI,AT,DE,EE,LT,LV,SK. Components: ea_fx_czk_per_eur, ea_fx_dkk_per_eur, ea_fx_huf_per_eur, ea_fx_inr_per_eur, ea_fx_pln_per_eur, ea_fx_ron_per_eur, ea_fx_usd_per_eur, no_fx_czknok, ... (14 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). Euro members (and EUR-pegged EE from 1995, LT from 2003, LV from 2006) have zero yoy vs EUR; SK from 2010 (NaN before, SKK not in data). Before 1999 EUR = ECU: NO via NOK/SEK x SEK/ECU, DK and CZ via their NOK crosses; FI/AT/DE legacy currencies not in data (NaN before 1999). | 0 |
| `w_fx_vs_nok_yoy`, `w_fx_vs_nok_dyoy` | Orkla-weighted yoy change of local currency per NOK (+ = local currencies weaker vs NOK, i.e. negative translation effect for NOK reporting). Countries: NO,SE,DK,CZ,HU,PL,RO,IN,FI,AT,DE,EE,LT,LV,SK. Components: ea_fx_czk_per_eur, ea_fx_dkk_per_eur, ea_fx_huf_per_eur, ea_fx_inr_per_eur, ea_fx_pln_per_eur, ea_fx_ron_per_eur, no_fx_czknok, no_fx_dkknok, ... (11 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). Euro members (and EUR-pegged EE from 1995, LT from 2003, LV from 2006) have zero yoy vs EUR; SK from 2010 (NaN before, SKK not in data). Before 1999 EUR = ECU: NO via NOK/SEK x SEK/ECU, DK and CZ via their NOK crosses; FI/AT/DE legacy currencies not in data (NaN before 1999). | 0 |
| `w_ec_food_ind_sell_price_exp_lvl`, `w_ec_food_ind_sell_price_exp_d4` | Orkla-weighted selling-price expectations of food manufacturers (EC BCS NACE C10 balance; Norway: SSB BTS consumer-goods home-market price expectations). Countries: NO,SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE. Components: at_ec_food_ind_sell_price_exp, cz_ec_food_ind_sell_price_exp, de_ec_food_ind_sell_price_exp, dk_ec_food_ind_sell_price_exp, ee_ec_food_ind_sell_price_exp, fi_ec_food_ind_sell_price_exp, hu_ec_food_ind_sell_price_exp, lt_ec_food_ind_sell_price_exp, ... (14 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). | 1 |
| `w_ec_food_retail_sell_price_exp_lvl`, `w_ec_food_retail_sell_price_exp_d4` | Orkla-weighted selling-price expectations of food retailers (EC retail FBT balance). Countries: SE,DK,FI,EE,LV,CZ,SK,AT,HU,RO,PL,DE. Components: at_ec_food_retail_sell_price_exp, cz_ec_food_retail_sell_price_exp, de_ec_food_retail_sell_price_exp, dk_ec_food_retail_sell_price_exp, ee_ec_food_retail_sell_price_exp, fi_ec_food_retail_sell_price_exp, hu_ec_food_retail_sell_price_exp, lv_ec_food_retail_sell_price_exp, ... (12 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). No Norway data; LT excluded (noise). | 0 |
| `w_ec_cons_price_exp_lvl`, `w_ec_cons_price_exp_d4` | Orkla-weighted consumers' price expectations next 12 months (EC balance). Countries: SE,DK,FI,EE,LV,LT,CZ,SK,AT,HU,RO,PL,DE. Components: at_ec_cons_price_exp_12m, cz_ec_cons_price_exp_12m, de_ec_cons_price_exp_12m, dk_ec_cons_price_exp_12m, ee_ec_cons_price_exp_12m, fi_ec_cons_price_exp_12m, hu_ec_cons_price_exp_12m, lt_ec_cons_price_exp_12m, ... (13 series). Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). No Norway data (renormalised). | 0 |
| `w_hh_saving_lvl`, `w_hh_saving_d4` | Orkla-weighted gross household saving rate. Countries: SE,DK,FI,CZ,AT,DE,HU,PL. Components: at_hh_saving_rate, cz_hh_saving_rate, de_hh_saving_rate, dk_hh_saving_rate, fi_hh_saving_rate, hu_hh_saving_rate, pl_hh_saving_rate, se_hh_saving_rate. Orkla Foods time-varying country weights renormalised over countries with data; NaN if covered revenue share < max(40%, 80% of the composite's 2005-2025 median coverage). No Norway/Baltic/SK data; RO excluded (noisy). | 1 |
| `nw_food_cpi_yoy`, `nw_food_cpi_dyoy` | Nordic (NO+SE) food CPI inflation. Countries: NO,SE. Components: no_cpi_food_idx, se_cpi_food_idx. Nordic weights NO/(NO+SE) from geo_weights; both countries required. | 0 |
| `nw_food_cpi_xvat_yoy`, `nw_food_cpi_xvat_dyoy` | Nordic (NO+SE) food CPI inflation adjusted for food-VAT changes. Countries: NO,SE. Components: no_cpi_food_idx, no_vat_food_rate, se_cpi_food_idx, se_food_vat_rate. Nordic weights NO/(NO+SE) from geo_weights; both countries required. | 0 |
| `nw_real_wage_yoy`, `nw_real_wage_dyoy` | Nordic (NO+SE) real wage growth (NO LCI, SE MI wage index, minus CPI). Countries: NO,SE. Components: no_cpi_total_idx, no_lci_wages_idx, se_cpi_idx, se_wage_idx_m. Nordic weights NO/(NO+SE) from geo_weights; both countries required. | 1 |
| `nw_cons_conf_z`, `nw_cons_conf_z_d4` | Nordic (NO+SE) consumer confidence z-score (Finans Norge; EC Sweden). Countries: NO,SE. Components: no_fn_cci_sa, se_ec_cons_conf. Nordic weights NO/(NO+SE) from geo_weights; both countries required. | 0 |
| `nw_retail_food_vol_yoy`, `nw_retail_food_vol_dyoy` | Nordic (NO+SE) grocery retail volume growth (SSB non-specialised food stores; SCB dagligvaruhandel). Countries: NO,SE. Components: no_retail_foodstores_vol_sa_idx, se_retail_grocery_vol_sa_idx. Nordic weights NO/(NO+SE) from geo_weights; both countries required. | 1 |
| `nw_food_ppi_yoy`, `nw_food_ppi_dyoy` | Nordic (NO+SE) domestic food-manufacturing PPI inflation. Countries: NO,SE. Components: no_ppi_food_dom_idx, se_ppi_food_hmpi_idx. Nordic weights NO/(NO+SE) from geo_weights; both countries required. | 1 |
| `fao_ffpi_sek_yoy`, `fao_ffpi_sek_dyoy` | FAO Food Price Index in SEK (USD index yoy + SEK/USD yoy). Components: glob_fao_ffpi, se_usdsek.  | 0 |
| `wb_food_sek_yoy`, `wb_food_sek_dyoy` | World Bank food price index in SEK (USD index yoy + SEK/USD yoy). Components: glob_wb_food_idx, se_usdsek.  | 0 |
| `fao_ffpi_wloc_yoy`, `fao_ffpi_wloc_dyoy` | FAO Food Price Index in Orkla-weighted local currency (USD index yoy + w_fx_vs_usd_yoy). Components: ea_fx_czk_per_eur, ea_fx_dkk_per_eur, ea_fx_huf_per_eur, ea_fx_inr_per_eur, ea_fx_pln_per_eur, ea_fx_ron_per_eur, ea_fx_usd_per_eur, glob_fao_ffpi, ... (15 series).  | 0 |
| `wb_food_wloc_yoy`, `wb_food_wloc_dyoy` | World Bank food index in Orkla-weighted local currency (USD index yoy + w_fx_vs_usd_yoy). Components: ea_fx_czk_per_eur, ea_fx_dkk_per_eur, ea_fx_huf_per_eur, ea_fx_inr_per_eur, ea_fx_pln_per_eur, ea_fx_ron_per_eur, ea_fx_usd_per_eur, glob_wb_food_idx, ... (15 series).  | 0 |
| `eu_agri_basket_yoy`, `eu_agri_basket_dyoy` | EU agri raw-material basket in EUR: equal-weight mean of yoy of raw milk, butter, SMP, pig carcass, beef, broiler, white sugar (DG AGRI). Components: eu_agri_beef_young_bulls_r3_price, eu_agri_broiler_price, eu_agri_butter_price, eu_agri_pig_carcass_e_price, eu_agri_raw_milk_price, eu_agri_smp_price, eu_agri_sugar_white_price. Requires >=6 of 7 components (white sugar only from 2007Q3). Wheat kept separate (from 2015-11). | 1 |
| `eu_agri_basket_wloc_yoy`, `eu_agri_basket_wloc_dyoy` | EU agri basket converted to Orkla-weighted local currency (basket yoy + w_fx_vs_eur_yoy). Components: ea_fx_czk_per_eur, ea_fx_dkk_per_eur, ea_fx_huf_per_eur, ea_fx_inr_per_eur, ea_fx_pln_per_eur, ea_fx_ron_per_eur, eu_agri_beef_young_bulls_r3_price, eu_agri_broiler_price, ... (18 series). Requires >=6 of 7 basket components. | 1 |
| `elec_nordic_loc_yoy`, `elec_nordic_loc_dyoy` | Nordic wholesale electricity price in local currency (NO2 in NOK, SE3 in SEK), Nordic-weighted. Components: no_elspot_no2_eur, no_fx_eurnok, se_elspot_se3_sek_mwh. SE3 2011-01..10 is the system price (catalog splice). | 0 |
| `natgas_eu_eur_yoy`, `natgas_eu_eur_dyoy` | EU natural gas price (WB Europe/TTF) in EUR. Components: ea_fx_usd_per_eur, glob_wb_natgas_eu. NaN across WB definition changes 2000-06, 2010-04, 2015-04. | 0 |
| `brent_nok_yoy`, `brent_nok_dyoy` | Brent crude oil price in NOK. Components: glob_wb_brent, no_fx_usdnok.  | 0 |
| `packaging_eu_yoy`, `packaging_eu_dyoy` | EU packaging cost: mean of yoy of EU PPI paper & paperboard articles and plastic products. Components: eu_ppi_paper_packaging_idx, eu_ppi_plastic_products_idx.  | 1 |
| `packaging_us_yoy`, `packaging_us_dyoy` | US packaging inputs: mean of yoy of US PPI plastic resins and corrugated boxes. Components: us_ppi_corrugated_boxes_idx, us_ppi_plastic_resins_idx.  | 1 |
| `price_cost_gap_ppi`, `price_cost_gap_ppi_d4` | Price-cost gap: w_food_cpi_yoy - w_food_ppi_yoy (consumer food prices vs food-manufacturing PPI). Components: at_hicp_food_idx, at_ppi_dom_food_mfg_idx, cz_hicp_food_idx, cz_ppi_dom_food_mfg_idx, de_hicp_food_idx, de_ppi_dom_food_mfg_idx, dk_hicp_food_idx, dk_ppi_dom_food_mfg_idx, ... (25 series). Country coverage differs between the two composites (no food PPI for EE/LV/SK/IN). | 1 |
| `price_cost_gap_fao_nok`, `price_cost_gap_fao_nok_d4` | Price-cost gap: w_food_cpi_yoy - FAO Food Price Index in NOK yoy. Components: at_hicp_food_idx, cz_hicp_food_idx, de_hicp_food_idx, dk_hicp_food_idx, ee_hicp_food_idx, fi_hicp_food_idx, glob_fao_ffpi_nok, hu_hicp_food_idx, ... (15 series).  | 1 |
| `price_cost_gap_agri`, `price_cost_gap_agri_d4` | Price-cost gap: w_food_cpi_yoy - EU agri raw-material basket yoy (EUR). Components: at_hicp_food_idx, cz_hicp_food_idx, de_hicp_food_idx, dk_hicp_food_idx, ee_hicp_food_idx, eu_agri_beef_young_bulls_r3_price, eu_agri_broiler_price, eu_agri_butter_price, ... (21 series).  | 1 |
| `price_cost_gap_fao_wloc`, `price_cost_gap_fao_wloc_d4` | Price-cost gap: w_food_cpi_yoy - FAO Food Price Index in Orkla-weighted local currency yoy. Components: at_hicp_food_idx, cz_hicp_food_idx, de_hicp_food_idx, dk_hicp_food_idx, ea_fx_czk_per_eur, ea_fx_dkk_per_eur, ea_fx_huf_per_eur, ea_fx_inr_per_eur, ... (29 series).  | 1 |
| `nw_price_cost_gap_ppi`, `nw_price_cost_gap_ppi_d4` | Nordic price-cost gap: nw_food_cpi_yoy - nw_food_ppi_yoy. Components: no_cpi_food_idx, no_ppi_food_dom_idx, se_cpi_food_idx, se_ppi_food_hmpi_idx.  | 1 |
| `price_wage_gap`, `price_wage_gap_d4` | Price-wage gap: w_food_cpi_yoy - w_wage_yoy (selling prices vs labour-cost growth). Components: at_hicp_food_idx, at_lci_wages_idx, cz_hicp_food_idx, cz_lci_wages_idx, de_hicp_food_idx, de_lci_wages_idx, dk_hicp_food_idx, dk_wage_idx_private_q, ... (28 series).  | 1 |

## 4. Break and data-quality handling

| series | treatment |
|---|---|
| `lt_lci_wages_idx` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2019-01: LT 2019 tax reform: +30% level jump in 2019Q1 (qa_C 8) |
| `glob_wb_chicken` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2021-09: source US->Brazil 2021-09, -26% level step (qa_C 16) |
| `glob_wb_soybean_oil` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2025-01: basis Dutch->US Gulf 2025-01 (qa_C 16) |
| `glob_wb_palm_oil` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2001-07, 2024-11, 2025-02, 2026-01 (+ all quarters 2021Q1-2022Q4 for the 2021 change of unknown month): several basis changes (2001-07, 2021 [month unknown], 2024-11, 2025-02, 2026-01) (qa_C 16) |
| `glob_wb_natgas_eu` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2000-06, 2010-04, 2015-04: definition changes: import border price from 2000-06, incl. spot 2010-04, TTF 2015-04 (qa_C 16) |
| `glob_wb_barley` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2012-05: Canadian -> US feed barley 2012-05 (catalog) |
| `eu_agri_wheat_bread_price` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2026-08: reporting-stage change 2026-08 (qa_C 16) |
| `eu_agri_barley_feed_price` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2026-08: reporting-stage change 2026-08 (qa_C 16) |
| `eu_agri_barley_malting_price` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2026-08: reporting-stage change 2026-08 (qa_C 16) |
| `eu_agri_maize_feed_price` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2026-08: reporting-stage change 2026-08 (qa_C 16) |
| `eu_ppi_dom_c102_idx` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2009-01: -12% level jump 2009-01, composition effect (qa_C 14) |
| `no_nav_unemp_level_sa` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles 2025-04: NAV register modernisation break 2025-04 (qa_B I5) |
| `no_qna_wage_per_fte_q` | yoy NaN 2015Q2, 2015Q3, 2016Q2, 2016Q3: 2015 a-ordningen quarterly timing break (qa_B I5); annual sums fine |
| `no_qna_wage_per_fte_food_q` | yoy NaN 2015Q2, 2015Q3, 2016Q2, 2016Q3: 2015 a-ordningen quarterly timing break (qa_B I5); annual sums fine |
| `no_real_wage_qna_yoy_q` | level NaN 2015Q2, 2015Q3, 2016Q2, 2016Q3 (d4 follows): 2015 a-ordningen timing break (qa_B I5): 2015Q2/Q3 spurious and 2016Q2/Q3 base-affected |
| `no_nav_unemp_rate_sa` | d4 NaN across 2022-01, 2025-04: labour-force base change 2022-01; register break 2025-04 |
| `no_lfs_unemp_rate_q_nsa` | d4 NaN across 2006-01, 2021-01: LFS methodological breaks 2006 and 2021 (catalog) |
| `no_jordbruk_malpris_mnok` | d4 NaN across 2025-07: scope change: milk no longer target-priced from the 2025 settlement (effective 1 Jul 2025); lvl from 2025Q3 covers only cereals, potatoes, vegetables and fruit and is not comparable with earlier years (catalog) |
| `no_imp_price_coffee_cocoa_idx` | values 2003-01-01..2003-04-01 set NaN: qa_B I3 source anomaly 2003-01..04 |
| `no_imp_price_total_idx` | values 2003-01-01..2003-04-01 set NaN: qa_B I3 source anomaly 2003-01..04 |
| `no_imp_price_cereals_idx` | values start..2003-12-01 set NaN: qa_B I3 carried-forward prices; start 2004 |
| `se_ppi_electricity_hmpi_idx` | values start..1995-12-01 set NaN: qa_B I4 annual-only values 1990-95 |
| `no_hh_real_disp_inc_sa_q` | values start..2006-10-01 set NaN: qa_B I5 volatile income components before 2007 |
| `no_hh_real_disp_inc_xdiv_sa_q` | values start..2006-10-01 set NaN: qa_B I5 volatile income components before 2007 |
| CEE survey series (cz, ee, hu, lt, lv, pl, ro, sk in SURVEYS) | values before 2000-01 set NaN (transition-era artefacts, qa_C 10) |
| `no_border_trade_*_s1` / `_s2` | separate features, never chained (survey design break 2023) |
| `ea_wage_tracker_yoy_q` | projected quarters after 2026Q3 removed |
| `no_vat_food_rate`, `se_food_vat_rate` | months after 2026-09 removed; used for VAT-adjusted food CPI composites |
| `ro_hh_saving_rate` | kept as is: very noisy quarterly SCA data (qa_C 12); excluded from w_hh_saving composite |
| `lt_gov_bond_10y` | kept as is: flat carried-forward primary yield (qa_C 9); excluded from w_gov10y composite |
| `ee_gov_bond_10y` | kept as is: from 2020-06 only, not comparable (catalog); excluded from w_gov10y composite |
| `lt_ec_food_retail_sell_price_exp` | kept as is: extremely noisy (qa_C 11); excluded from composites |
| `se_elspot_se3_eur_mwh` | kept as is: 2011-01..10 filled with Nord Pool system price (documented splice in catalog; qa_B I5) |
| `no_elec_hh_energy_price` | kept as is: survey redesign 2012 (possible level break; no visible step, kept) |
| `in_cpi_food_idx` | kept as is: FAOSTAT; 2025 values FAO-imputed (qa_C 3); ends 2026-03; ~120-day lag, so left out of the food-CPI composites |
| `glob_wb_beef` | kept as is: replacement series Sep-2021 and Jan-2024 (no visible step; not masked) |
| `glob_wb_soybeans` | kept as is: delivery-basis changes 2021/2025 (no visible step; not masked) |

## 5. Coverage summary

- Features: **1420** (1330 base-series transforms from 665 series, 90 composites/spreads). Core: **200**.

By category:

| category | features | core |
|---|---|---|
| activity_retail | 160 | 16 |
| business_survey | 148 | 0 |
| commodities | 128 | 36 |
| consumer_prices | 178 | 22 |
| consumer_survey | 108 | 8 |
| energy | 34 | 6 |
| fx | 40 | 10 |
| labour_market | 40 | 2 |
| other | 14 | 12 |
| packaging_freight | 32 | 14 |
| price_expectations | 192 | 14 |
| producer_prices_input_costs | 74 | 22 |
| rates | 84 | 12 |
| tax_policy | 8 | 6 |
| wages_income | 180 | 20 |

By folder:

| folder | features | core |
|---|---|---|
| COMPOSITE | 90 | 90 |
| EU | 408 | 14 |
| GLOBAL | 160 | 34 |
| NO | 128 | 22 |
| SE | 96 | 18 |
| SURVEYS | 436 | 12 |
| WAGES | 102 | 10 |

Real-time lag distribution (all / core):

| realtime_min_lag_q | all | core |
|---|---|---|
| 0 | 784 | 102 |
| 1 | 620 | 98 |
| 2 | 4 | 0 |
| 4 | 12 | 0 |

Feature start year (non-missing), all features:

| start | features |
|---|---|
| 1995-1999 | 771 |
| 2000-2004 | 490 |
| 2005-2009 | 77 |
| 2010-2014 | 43 |
| 2015+ | 39 |

Composite coverage (share of Orkla Foods revenue in countries with data; mean over quarters with a value):

| composite | start | end | n_obs | mean coverage 2005-2026 | min coverage 2005-2026 |
|---|---|---|---|---|---|
| `w_food_cpi_yoy` | 1997Q1 | 2026Q2 | 118 | 0.95 | 0.88 |
| `w_food_cpi_dyoy` | 1998Q1 | 2026Q2 | 114 | 0.95 | 0.88 |
| `w_cpi_yoy` | 1997Q1 | 2026Q2 | 118 | 0.98 | 0.92 |
| `w_cpi_dyoy` | 1998Q1 | 2026Q2 | 114 | 0.98 | 0.92 |
| `w_food_cpi_rel_yoy` | 1997Q1 | 2026Q2 | 118 | 0.95 | 0.88 |
| `w_food_cpi_rel_dyoy` | 1998Q1 | 2026Q2 | 114 | 0.95 | 0.88 |
| `w_food_cpi_xvat_yoy` | 1997Q1 | 2026Q2 | 118 | 0.95 | 0.88 |
| `w_food_cpi_xvat_dyoy` | 1998Q1 | 2026Q2 | 114 | 0.95 | 0.88 |
| `w_wage_yoy` | 1997Q1 | 2026Q2 | 118 | 0.95 | 0.88 |
| `w_wage_dyoy` | 1998Q1 | 2026Q2 | 114 | 0.95 | 0.88 |
| `w_real_wage_yoy` | 1997Q1 | 2026Q2 | 118 | 0.95 | 0.88 |
| `w_real_wage_dyoy` | 1998Q1 | 2026Q2 | 114 | 0.95 | 0.88 |
| `w_cons_conf_z` | 1995Q4 | 2026Q3 | 124 | 0.95 | 0.88 |
| `w_cons_conf_z_d4` | 1996Q4 | 2026Q3 | 120 | 0.95 | 0.88 |
| `w_retail_food_vol_yoy` | 2001Q1 | 2026Q2 | 102 | 0.95 | 0.88 |
| `w_retail_food_vol_dyoy` | 2002Q1 | 2026Q2 | 98 | 0.95 | 0.88 |
| `w_retail_total_vol_yoy` | 2001Q1 | 2026Q2 | 102 | 0.95 | 0.88 |
| `w_retail_total_vol_dyoy` | 2002Q1 | 2026Q2 | 98 | 0.95 | 0.88 |
| `w_gdp_vol_yoy` | 1995Q1 | 2026Q2 | 126 | 0.95 | 0.88 |
| `w_gdp_vol_dyoy` | 1995Q1 | 2026Q2 | 126 | 0.95 | 0.88 |
| `w_hh_real_inc_yoy` | 2008Q1 | 2026Q1 | 73 | 0.91 | 0.82 |
| `w_hh_real_inc_dyoy` | 2009Q1 | 2026Q1 | 69 | 0.90 | 0.82 |
| `w_food_ppi_yoy` | 2001Q1 | 2026Q2 | 102 | 0.91 | 0.80 |
| `w_food_ppi_dyoy` | 2002Q1 | 2026Q2 | 98 | 0.91 | 0.80 |
| `w_unemp_lvl` | 1995Q1 | 2026Q2 | 126 | 0.95 | 0.88 |
| `w_unemp_d4` | 1995Q1 | 2026Q2 | 126 | 0.95 | 0.88 |
| `w_policy_rate_lvl` | 1995Q1 | 2026Q3 | 127 | 0.98 | 0.92 |
| `w_policy_rate_d4` | 1995Q3 | 2026Q3 | 125 | 0.98 | 0.92 |
| `w_gov10y_lvl` | 1995Q1 | 2026Q2 | 126 | 0.93 | 0.86 |
| `w_gov10y_d4` | 1995Q1 | 2026Q2 | 126 | 0.93 | 0.86 |
| `w_fx_vs_eur_yoy` | 1995Q1 | 2026Q3 | 127 | 0.98 | 0.91 |
| `w_fx_vs_eur_dyoy` | 1995Q1 | 2026Q3 | 127 | 0.98 | 0.91 |
| `w_fx_vs_usd_yoy` | 1995Q1 | 2026Q3 | 127 | 0.98 | 0.91 |
| `w_fx_vs_usd_dyoy` | 1995Q1 | 2026Q3 | 127 | 0.98 | 0.91 |
| `w_fx_vs_nok_yoy` | 1995Q1 | 2026Q3 | 127 | 0.98 | 0.91 |
| `w_fx_vs_nok_dyoy` | 1995Q1 | 2026Q3 | 127 | 0.98 | 0.91 |
| `w_ec_food_ind_sell_price_exp_lvl` | 1996Q1 | 2026Q2 | 122 | 0.95 | 0.88 |
| `w_ec_food_ind_sell_price_exp_d4` | 1997Q1 | 2026Q2 | 118 | 0.94 | 0.77 |
| `w_ec_food_retail_sell_price_exp_lvl` | 2010Q3 | 2026Q3 | 65 | 0.62 | 0.55 |
| `w_ec_food_retail_sell_price_exp_d4` | 2011Q3 | 2026Q3 | 61 | 0.63 | 0.56 |
| `w_ec_cons_price_exp_lvl` | 1995Q4 | 2026Q3 | 124 | 0.62 | 0.55 |
| `w_ec_cons_price_exp_d4` | 1996Q4 | 2026Q3 | 120 | 0.62 | 0.55 |
| `w_hh_saving_lvl` | 1999Q1 | 2026Q1 | 109 | 0.56 | 0.52 |
| `w_hh_saving_d4` | 2000Q1 | 2026Q1 | 105 | 0.56 | 0.52 |

## 6. Caveats

- Geographic weights before 2004 are a proxy (2004 split); the 'Rest of Europe' country split is a project estimate (+/-2pp) and the CZ/SK split is an assumption. Weights matter mainly for the non-Nordic 15-30% of revenue; NO+SE are 54-81% throughout.
- Early history: HICPs start in 1996 (yoy from 1997) and most Eurostat LCI/retail/PPI series in 2000, so Orkla-weighted composites start when enough countries are available (see the coverage table); Orkla's own quarterly segment data start in 2000, so this rarely binds. The latest quarter of a composite is NaN until most countries have published.
- Country data sources differ across composites (national CPI vs HICP, LCI vs national wage indices); the Nordic `nw_` versions use national sources only.
- Organic growth excludes FX, but reported revenue does not: `w_fx_vs_nok_yoy` captures the translation effect for NOK reporting. Food CPIs include VAT, so the Swedish food-VAT cut (12% -> 6%, 2026-04) depresses `se_cpi_food_idx__yoy`, `w_food_cpi_yoy` and the price-cost gaps from 2026Q2 although Orkla's net sales are ex VAT; use the `*_food_cpi_xvat_*` variants for that episode (and the 2001-07 Norwegian cut).
- All values are the latest vintage (revised national accounts, preliminary wage statistics, re-estimated seasonal factors). `realtime_min_lag_q` handles publication lags but not revisions.
- Other real-time caveats (QA verify-panel):
  - The geographic weights for year Y come from the annual report for Y, published in Feb-Mar of Y+1, so the weights are not strictly real-time. They are slow-moving structural shares, and the large steps (e.g. Hame in 2016, India leaving in 2022Q3) were announced in advance.
  - Consumer-confidence z-scores use each country's 2000-2025 mean and standard deviation. This scaling uses the full sample; it changes the relative country weights in `w_cons_conf_z`, not its timing.
  - `no_frontfag_frame_a` is lag 0 (frame agreed by mid-April), but the 2020 settlement was postponed (COVID-19), so its 2020Q1-Q2 values were not known in real time. The ECB wage tracker's 2013- history is a back-calculation. The latest month of euro-area countries' all-items HICP (Sep-2026) is a national flash estimate.
  - `no_jordbruk_malpris_mnok` changes scope from the 2025 settlement: milk is no longer target-priced. `d4` is masked for 2025Q3-2026Q2, and `lvl` from 2025Q3 is not comparable with earlier years.
- Quarterly means of daily/hourly prices (electricity, gas) are very volatile in log terms; electricity yoy reaches +/-150 log points in 2020-2023.
- Several series are flagged in the dictionary notes (preliminary latest values, discontinued series, documented splices). The screening stage should prefer `core` features and respect `realtime_min_lag_q` when lining features up with Orkla quarters.
