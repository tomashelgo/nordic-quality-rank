# Orkla Foods: univariate macro predictor screen

Workflow label `lens-screen`, run 2026-10-06. Orkla data run to 2026Q2 and macro data to 2026Q2/Q3. Scripts: `screen_lib.py`, `run_screen.py`, `make_figures.py` and `write_findings.py`. Reproduce with `python3 run_screen.py && python3 make_figures.py && python3 write_findings.py` (about 4 minutes).

## 0. Design and statistical hygiene

**Targets** (from `common.load_targets()`):
- Primary: `d_margin` (102 quarters, 2001Q1-2026Q2), `og` (102) and `d_og` (98, of which 12 cross a definition break).
- Secondary: `d_margin_r4` (99), `d_og_r4` (95) and the derived `vol_proxy` = og - `w_food_cpi_xvat_yoy` (102), an implied volume/mix series (validated in section 7).

**Base regression** y_t = a + b x_t + controls, with Newey-West HAC standard errors:
- `d_margin`: no controls, OLS, 4 lags.
- `og`, `vol_proxy`: + `easter_shift`; WLS with quality weights `w_og` (A = 1, B = 0.7, C = 0.4); 4 lags.
- `d_og`: + `easter_shift` + `d_og_def_break`; WLS with `w_d_og`; 4 lags.
- `d_margin_r4`: no controls, 8 lags, because the rolling windows overlap.
- `d_og_r4`: + a local definition-break dummy (see section 8), 8 lags.

The numpy HAC estimator reproduces `common.nw_ols` (statsmodels) to 1e-13 (`hac_validation.csv`).

**Alignments** (`common.align`):
- `coin`: same quarter. Explanatory only, not usable in advance.
- `rt0`: the feature lagged by its publication lag. Known at quarter end, before the Orkla report.
- `rt1`, `rt2`, `rt4`: forecasts made 1, 2 or 4 quarters earlier.

**Distributed-lag scan:** k = 0..6 quarters beyond the publication lag (k = h).

**Statistics reported for each feature x target x alignment:**
- n, Pearson r, Spearman rho, and the effect of a 1-sd move in x (`b x 1sd`, in target units).
- The HAC t-stat (`t HAC`).
- A leverage-adjusted HAC t (`t lev`): residuals scaled by 1/(1-h_ii). It guards against a few well-fitted, high-leverage quarters, chiefly 2022-23, shrinking the standard error.
- The incremental HAC t once the target's own real-time lag y_{t-L} is added (`t +own lag`; L = 4, or 5 at h = 4).
- For d_og and d_og_r4, the incremental t once the base-period organic growth og_{t-L} is added (`t +base`, see section 1). This is the dominant, real-time-known base effect: corr(d_og_t, og_{t-4}) = -0.64.
- Sub-sample HAC t: 2001-2012 (`t 01-12`), 2013-2026 (`t 13-26`), excluding 2021Q3-2023Q4 (`t ex-infl`) and excluding 2020-21 (`t ex-covid`).

**Flags in the tables:**
- `S`: the sign is the same in the full sample, 2001-12, 2013-26 and ex-infl.
- `R` (robust): BY q < 0.10 on both the HAC t and the leverage-adjusted t, plus `S`, plus p < 0.05 ex-infl.

**Multiple testing:**
- Benjamini-Yekutieli (BY) q-values are computed within each target x alignment family: about 200 tests for core features, about 1,400 for all features.
- Number of discovery tests: 5,964 (core), 42,180 (all features) and 8,316 (lag scan, 200 features x 7 lags x 6 targets, BY within each target over its 1,386 tests). The incremental, sub-sample and conditional regressions are diagnostics, not discovery tests.
- Stricter global families: across all core tests of all six targets and five alignments, 844 of 5,964 survive BY at 10% (`q_by_global_core`). Across the three primary targets, 406 of 2,982 survive (`q_by_global_primary`). Holm-adjusted p-values are in the CSVs (`p_holm`).

**Caveats on the statistics:**
- The sample is about 100 quarters and the targets are autocorrelated y/y changes. Even with HAC, small-sample t-stats are optimistic, so read |t| < 3 as weak evidence.
- The r4 targets overlap heavily: their effective sample is about a quarter of n, so their t-stats are descriptive.
- Univariate screens cannot separate proxies from causes. Section 2 runs targeted conditional checks.

## 1. Headline results

**1. EBIT margin change (`d_margin`) is driven by input-cost inflation, with a two-stage pattern.**

- **Stage 1: the cost squeeze is simultaneous.** In the same quarter, cost-inflation proxies predict a falling margin. The strongest are EU packaging PPI (`packaging_eu_yoy`, coincident t = -9.6, r = -0.49, about -0.59pp of margin per 1 sd) and EU plastic-products PPI (real-time nowcast t = -8.8). Food-industry selling-price expectations and Swedish CPI acceleration point the same way.
- **The episode inflates the full-sample t-stats.** These relations survive without 2021Q3-2023Q4, but much weaker: t ex-infl = -3.1 and -3.0. The 2022-23 squeeze (margin about -3pp y/y while EU packaging PPI rose 15-18% y/y) supplies most of the full-sample t.
- **Stage 2: delayed pass-through, 5-6 quarters later.** In the lag scan, cost and price inflation 5-6 quarters beyond the publication lag predicts margin **recovery**, i.e. a positive sign. Examples:
  - EU dairy PPI (`eu_ppi_dom_c105_idx__yoy`) at k = 6: t = +5.2, +5.6 ex-infl, +4.5 with the own lag.
  - Swedish food PPI at k = 6: t = +4.8.
  - EU bakery PPI at k = 5: t = +4.5.
  - Swedish CPI at k = 6: t = +4.2.

  For these four series, the k = 6 relations hold separately in 2001-12 (t 2.5-3.2) and 2013-26 (t 2.5-3.1). This is the classic pattern: price increases catch up with costs after a lag, and input costs normalise.
- **Practical reading.** Cost inflation now means lower margins this quarter and next, and higher margins about 1.5 years out.
- **Predictability by horizon.** At h = 2 and h = 4 no single core feature is BY-significant for quarterly `d_margin` in the full sample.
  - Excluding 2021Q3-2023Q4, 11 core features are BY-significant at h = 4. Almost all are lagged price or cost inflation with a positive sign, e.g. `eu_ppi_dom_c107_idx__yoy` ex-infl t = +5.6, which is the delayed pass-through again.
  - In the full sample, the 2022-24 squeeze-then-recovery sequence blurs this horizon.
  - The smoother `d_margin_r4` is predictable to h = 2.

**2. Rising long-term interest rates predict margin declines, and this is the most robust rates result.**

- The 4-quarter change in the Orkla-weighted 10-year yield (`w_gov10y_d4`) has t = -5.1 coincident and in the nowcast, and -3.7 at h = 1.
- The Norwegian 10-year yield change (`no_govbond_10y__d4`) ranks #2 at h = 1 (t = -4.1).
- The sign is stable: it holds in 2001-12, in 2013-26 and without the inflation episode (ex-infl t = -3.1).
- It survives a direct control for packaging PPI, food PPI or CPI acceleration (t about -3, section 2). Yields therefore carry cycle and inflation information beyond the cost indices.
- Policy-rate *levels* and yield *levels* show nothing for margins.

**3. Organic growth (`og`) is mostly price, so it tracks consumer and producer food inflation.**

- Swedish food CPI y/y has t = +11.5 coincident and in the nowcast, and +8.3 at h = 1. The Orkla-weighted food CPI ex VAT has t = +8.5.
- Survey price expectations lead: SSB consumer-goods price expectations (`no_ssb_bts_consgoods_home_price_exp`) have t = +6.0 at h = 2, and their 4-quarter change +4.5 at h = 4 (BY q = 0.02). EC food-industry selling-price expectations have t = +5.7 at h = 2.
- In the all-feature family, EC retail selling-price expectations for Sweden are the best h = 1-2 predictors (t = +9.0 and +8.0).
- **The episode dominates.** Without 2021Q3-2023Q4, the same variables keep their sign, but t falls to about 2-3.7, and only 0-3 core features pass BY within the ex-infl families.

**4. Change in organic growth (`d_og`) has the most real-time predictability, but read it with the base effect in mind.**

- **The base effect.** d_og = og_t - og_{t-4}, and og_{t-4} is known in real time with corr(d_og, og_{t-4}) = -0.64. Food inflation 4-5 quarters back therefore predicts d_og negatively, partly through the base alone:
  - `w_food_cpi_yoy` at h = 4: t = -5.1; controlling for og_{t-5}: -4.1.
- **Signals that survive the base and own-lag controls and the ex-infl sample:**
  - Accelerations in EU food-manufacturing PPIs at h = 0-2, such as `eu_ppi_dom_c106_idx__dyoy` (grain mill; t = +7.4 at h = 2, ex-infl +6.4).
  - Changes in EC food-industry selling-price expectations (`ea_ec_food_ind_sell_price_exp__d4`: t = +5.9 at h = 2 and +5.2 at h = 4; +base +6.2).
  - Packaging-cost accelerations at h = 4.
  - Activity at h = 2, for example `w_gdp_vol_dyoy` (t = +5.5), and in the all-feature family euro-area GDP y/y (t = +9.7) and OECD business confidence changes at h = 4 (`g7_oecd_bci__d4` t = +7.2).
- In the nowcast, falling real wages (`w_real_wage_dyoy`, t = -5.5) and falling Swedish confidence (`se_ec_cons_conf__d4`, t = -5.1) go with *rising* og growth. They partly survive a food-CPI-acceleration control (section 2), but the sign rules out a demand channel. They capture broad inflation acceleration that Orkla passes through.

**5. Volume is essentially unpredictable from macro data in real time.**

- The implied volume/mix proxy correlates with Orkla's reported volume/mix at r = 0.83 (2022Q2-2026Q2).
- It is explained coincidentally by Nordic grocery-market volumes: Swedish household food consumption (t = +6.4, ex-infl +3.6) and Swedish grocery volume acceleration (t = +5.1).
- From h = 1 no core feature passes BY, and nothing in the lag scan does either beyond the mechanical food-CPI term at k = 0.
- Real wages, real disposable income and consumer confidence do **not** predict volume robustly. Their sign even turns negative without the inflation episode.
- Bond-yield *levels* are weakly negative (t about -2.8 at h = 1, ex-infl -2.6, rank #15 of 200), but not significant after BY.

**6. Count of robust core predictors** (BY q < 0.10 on both t-stats, sign-stable, p < 0.05 ex-infl), by target and alignment:

Cells show (BY q < 0.10) / (robust) out of about 200 core tests.

| target | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `d_margin` | 26 / 16 | 16 / 12 | 12 / 2 | 0 / 0 | 0 / 0 |
| `og` | 33 / 12 | 39 / 15 | 44 / 19 | 33 / 9 | 3 / 2 |
| `d_og` | 42 / 26 | 52 / 35 | 57 / 32 | 47 / 35 | 56 / 44 |
| `d_margin_r4` | 58 / 26 | 65 / 33 | 61 / 37 | 43 / 23 | 3 / 0 |
| `d_og_r4` | 51 / 42 | 49 / 43 | 55 / 48 | 59 / 50 | 61 / 51 |
| `vol_proxy` | 12 / 4 | 10 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

## 2. The variables you asked about: real wages, surveys and interest rates

Each cell shows `t HAC full / t HAC excluding 2021Q3-2023Q4 (rank among ~200 core features)`. A `*` marks BY q < 0.10 and `R` marks robust. The tables cover the three primary targets plus the volume proxy.

### d_margin (EBIT-margin change y/y, pp)

**Real wages / real income**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_real_wage_yoy` | +1.6 / -0.7 (#108) | +0.6 / -1.9 (#167) | +0.2 / -2.6 (#186) | +0.5 / -0.7 (#166) | -0.3 / -0.6 (#180) |
| `w_real_wage_dyoy` | +1.8 / +0.7 (#96) | +0.7 / -0.5 (#157) | +0.7 / -0.5 (#129) | +1.0 / +0.2 (#124) | +0.6 / -0.1 (#144) |
| `nw_real_wage_yoy` | +1.2 / -0.8 (#129) | +0.2 / -2.0 (#182) | -0.2 / -2.7 (#187) | +0.5 / -0.6 (#165) | -0.1 / -0.6 (#193) |
| `nw_real_wage_dyoy` | +1.6 / +0.8 (#106) | +0.3 / -0.7 (#179) | +0.3 / -0.9 (#174) | +0.7 / +0.1 (#148) | +0.3 / -0.3 (#174) |
| `se_real_wage_yoy_q__lvl` | +3.0 / +1.5 (#33) | +1.7 / +0.2 (#97) | +0.6 / -1.2 (#139) | -0.3 / -2.1 (#176) | -2.8 / -3.6 (#16) |
| `se_real_wage_yoy_q__d4` | +3.8 / +3.4 (#17)*R | +4.2 / +4.1 (#9)*R | +3.6 / +3.4 (#7)* | +2.0 / +1.4 (#39) | -1.2 / -1.4 (#100) |
| `no_real_wage_qna_yoy_q__lvl` | +0.5 / -0.6 (#169) | +0.2 / -0.7 (#181) | +0.0 / -0.8 (#197) | +0.5 / -0.3 (#167) | +0.7 / +0.3 (#139) |
| `no_real_wage_qna_yoy_q__d4` | +0.4 / -0.3 (#177) | -0.2 / -0.8 (#184) | -0.1 / -0.5 (#192) | +0.8 / +0.5 (#143) | +1.6 / +1.3 (#78) |
| `w_hh_real_inc_yoy` | +0.9 / -0.5 (#143) | +0.8 / +0.4 (#141) | -0.4 / +0.0 (#154) | -1.0 / -0.7 (#119) | -1.0 / -1.6 (#121) |
| `w_hh_real_inc_dyoy` | +1.2 / +0.4 (#128) | +1.4 / +2.1 (#109) | -0.1 / +1.1 (#193) | -0.6 / +0.3 (#157) | -1.9 / -3.4 (#57) |

**Consumer surveys**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_cons_conf_z` | +0.2 / -2.8 (#182) | +0.2 / -2.8 (#187) | -0.2 / -2.8 (#178) | -0.9 / -2.8 (#136) | -1.8 / -2.1 (#65) |
| `w_cons_conf_z_d4` | +1.0 / -0.6 (#142) | +1.0 / -0.6 (#132) | +0.5 / -0.7 (#146) | -0.3 / -0.8 (#178) | -1.4 / -1.2 (#85) |
| `nw_cons_conf_z` | +0.2 / -2.5 (#183) | +0.2 / -2.5 (#188) | -0.4 / -2.7 (#166) | -1.1 / -2.7 (#111) | -1.9 / -2.2 (#54) |
| `nw_cons_conf_z_d4` | +1.1 / -0.2 (#130) | +1.1 / -0.2 (#121) | +0.5 / -0.6 (#147) | -0.4 / -0.8 (#173) | -1.6 / -1.4 (#75) |
| `no_fn_cci_sa__lvl` | -0.0 / -1.9 (#195) | -0.0 / -1.9 (#197) | -0.4 / -2.0 (#157) | -0.9 / -1.9 (#138) | -0.8 / -1.4 (#132) |
| `no_fn_cci_sa__d4` | +0.6 / -0.5 (#167) | +0.6 / -0.5 (#168) | -0.1 / -1.0 (#190) | -1.1 / -0.9 (#115) | -0.9 / -0.8 (#125) |
| `se_ec_cons_conf__lvl` | +0.3 / -2.3 (#180) | +0.3 / -2.3 (#176) | -0.3 / -2.7 (#173) | -1.2 / -3.0 (#106) | -2.3 / -2.9 (#35) |
| `se_ec_cons_conf__d4` | +1.5 / -0.1 (#116) | +1.5 / -0.1 (#104) | +0.9 / -0.3 (#124) | +0.0 / -0.5 (#198) | -1.6 / -1.4 (#77) |

**Business surveys (price expectations, core)**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_ec_food_ind_sell_price_exp_lvl` | -2.8 / -0.7 (#38) | -1.9 / -0.1 (#82) | -1.3 / +0.4 (#96) | -0.6 / +1.2 (#156) | +1.4 / +2.1 (#90) |
| `w_ec_food_ind_sell_price_exp_d4` | -2.4 / -1.5 (#62) | -2.7 / -1.7 (#39) | -2.8 / -2.2 (#24) | -2.7 / -2.1 (#13) | -0.3 / +0.1 (#179) |
| `ea_ec_food_ind_sell_price_exp__lvl` | -4.7 / -1.4 (#8)* | -4.7 / -1.4 (#7)* | -3.7 / -1.2 (#5)* | -2.1 / -0.3 (#38) | -0.1 / +1.4 (#192) |
| `ea_ec_food_ind_sell_price_exp__d4` | -2.7 / -2.0 (#41) | -2.7 / -2.0 (#38) | -3.1 / -2.5 (#18) | -3.0 / -2.4 (#8) | -1.7 / -0.9 (#70) |
| `no_ssb_bts_consgoods_home_price_exp__lvl` | -2.2 / -0.5 (#75) | -2.2 / -0.4 (#70) | -1.4 / +0.7 (#93) | -1.0 / +1.4 (#128) | +0.7 / +2.6 (#136) |
| `no_ssb_bts_consgoods_home_price_exp__d4` | -3.0 / -2.1 (#32) | -4.0 / -2.2 (#13)*R | -3.5 / -2.2 (#11)* | -3.2 / -2.4 (#7) | -0.3 / +0.3 (#182) |
| `se_nier_food_mfg_sell_price_exp__lvl` | -1.9 / -0.4 (#92) | -1.9 / -0.4 (#85) | -1.2 / +0.6 (#103) | -0.6 / +1.4 (#158) | +0.6 / +1.8 (#146) |
| `no_nbes_bl_sell_price_di__lvl` | -2.2 / -1.5 (#74) | -2.2 / -1.5 (#69) | -2.5 / -1.6 (#34) | -2.1 / -1.2 (#36) | -0.8 / -0.2 (#133) |
| `w_ec_food_retail_sell_price_exp_lvl` | -5.3 / -1.1 (#4)* | -5.3 / -1.1 (#3)* | -3.6 / -1.4 (#9)* | -2.5 / -1.1 (#18) | -0.3 / +1.8 (#171) |

**Interest rates**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_policy_rate_lvl` | -0.2 / -0.6 (#181) | -0.2 / -0.6 (#180) | +0.3 / -0.3 (#170) | +0.7 / +0.0 (#150) | +1.2 / +0.5 (#95) |
| `w_policy_rate_d4` | -2.6 / -1.9 (#48) | -2.6 / -1.9 (#42) | -1.9 / -1.3 (#61) | -1.0 / -0.6 (#125) | +0.9 / +1.0 (#127) |
| `w_gov10y_lvl` | -0.8 / -1.4 (#148) | -0.8 / -1.4 (#142) | -0.3 / -1.1 (#169) | +0.3 / -0.7 (#182) | +1.0 / -0.1 (#122) |
| `w_gov10y_d4` | -5.1 / -3.1 (#5)*R | -5.1 / -3.1 (#4)*R | -3.7 / -2.7 (#4)* | -2.3 / -1.6 (#28) | -0.3 / +0.3 (#172) |
| `no_policy_rate__d4` | -2.5 / -1.9 (#57) | -2.5 / -1.9 (#53) | -1.8 / -1.1 (#70) | -0.9 / -0.6 (#137) | +0.8 / +0.7 (#131) |
| `se_policy_rate__d4` | -2.5 / -1.9 (#55) | -2.5 / -1.9 (#52) | -1.6 / -1.2 (#82) | -0.6 / -0.5 (#155) | +1.0 / +1.2 (#115) |
| `no_govbond_10y__d4` | -4.9 / -3.6 (#6)*R | -4.9 / -3.6 (#5)*R | -4.1 / -2.7 (#2)*R | -2.5 / -1.5 (#21) | -0.2 / +0.5 (#184) |
| `se_gov_bond_10y__d4` | -4.1 / -2.9 (#13)*R | -4.1 / -2.9 (#11)*R | -3.2 / -2.5 (#13) | -2.2 / -1.7 (#32) | -0.5 / +0.0 (#160) |

**Labour market**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_unemp_lvl` | +1.5 / +0.8 (#113) | +0.7 / +0.1 (#153) | +0.0 / -0.5 (#196) | -1.0 / -1.4 (#118) | -2.9 / -2.5 (#12) |
| `w_unemp_d4` | +4.2 / +3.2 (#10)*R | +2.7 / +1.7 (#36) | +1.9 / +1.3 (#62) | +0.7 / +0.4 (#152) | -1.2 / -0.7 (#94) |

### og (organic growth, %)

**Real wages / real income**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_real_wage_yoy` | -5.2 / -1.0 (#22)* | -7.6 / -2.3 (#5)*R | -3.6 / -0.1 (#32)* | -2.2 / +0.6 (#71) | -0.7 / +0.8 (#158) |
| `w_real_wage_dyoy` | -1.2 / -0.9 (#114) | -2.1 / -1.5 (#73) | -1.7 / -0.4 (#98) | -2.1 / -0.8 (#80) | -1.2 / +0.3 (#122) |
| `nw_real_wage_yoy` | -4.0 / -1.6 (#27)* | -6.0 / -3.5 (#19)*R | -3.2 / -1.2 (#40)* | -2.0 / -0.2 (#85) | -0.9 / +0.5 (#148) |
| `nw_real_wage_dyoy` | -1.5 / -0.9 (#99) | -2.5 / -2.0 (#54) | -1.7 / -0.6 (#99) | -2.1 / -1.3 (#79) | -1.1 / +0.0 (#132) |
| `se_real_wage_yoy_q__lvl` | -7.1 / -0.9 (#15)* | -6.8 / -2.2 (#12)*R | -4.7 / -2.1 (#17)*R | -3.5 / -2.0 (#22)* | -2.1 / -1.6 (#54) |
| `se_real_wage_yoy_q__d4` | -0.7 / +1.4 (#150) | -1.5 / +0.2 (#106) | -2.0 / -0.5 (#80) | -2.7 / -1.6 (#50) | -3.1 / -2.5 (#13) |
| `no_real_wage_qna_yoy_q__lvl` | -2.1 / -0.8 (#62) | -3.0 / -2.4 (#40) | -2.1 / -0.8 (#72) | -2.9 / -2.0 (#39) | -2.2 / -1.4 (#44) |
| `no_real_wage_qna_yoy_q__d4` | -0.6 / +0.3 (#158) | -0.7 / +0.0 (#156) | -0.2 / +0.9 (#185) | -1.7 / -0.9 (#106) | -0.8 / +0.2 (#150) |
| `w_hh_real_inc_yoy` | -2.3 / -1.1 (#54) | -1.8 / -1.3 (#91) | -2.0 / -1.0 (#82) | -1.1 / -1.0 (#141) | -0.9 / -0.7 (#145) |
| `w_hh_real_inc_dyoy` | -1.0 / +0.4 (#135) | -0.8 / -0.2 (#148) | -0.9 / +0.0 (#140) | -0.3 / +0.1 (#184) | -0.5 / -0.5 (#169) |

**Consumer surveys**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_cons_conf_z` | -5.6 / -2.4 (#20)*R | -5.6 / -2.4 (#20)*R | -4.4 / -2.4 (#19)*R | -3.1 / -1.9 (#33)* | -1.2 / -0.0 (#124) |
| `w_cons_conf_z_d4` | -3.3 / -1.8 (#33)* | -3.3 / -1.8 (#37)* | -3.5 / -2.5 (#34)*R | -3.2 / -2.4 (#30)* | -1.8 / -1.4 (#72) |
| `nw_cons_conf_z` | -7.2 / -3.2 (#14)*R | -7.2 / -3.2 (#9)*R | -5.2 / -3.0 (#11)*R | -3.5 / -2.5 (#20)*R | -1.6 / -0.9 (#91) |
| `nw_cons_conf_z_d4` | -3.4 / -1.7 (#30)* | -3.4 / -1.7 (#36)* | -3.6 / -2.3 (#33)*R | -3.2 / -2.5 (#31)* | -1.7 / -1.7 (#78) |
| `no_fn_cci_sa__lvl` | -4.5 / -3.1 (#25)*R | -4.5 / -3.1 (#27)*R | -3.4 / -2.4 (#35)*R | -2.7 / -1.8 (#48) | -1.8 / -0.8 (#74) |
| `no_fn_cci_sa__d4` | -2.7 / -2.0 (#43) | -2.7 / -2.0 (#48) | -2.1 / -1.8 (#74) | -1.9 / -1.7 (#101) | -1.3 / -1.0 (#120) |
| `se_ec_cons_conf__lvl` | -7.3 / -2.9 (#12)*R | -7.3 / -2.9 (#8)*R | -5.5 / -3.2 (#7)*R | -3.2 / -2.7 (#27)* | -0.7 / -0.8 (#152) |
| `se_ec_cons_conf__d4` | -2.8 / -1.2 (#38) | -2.8 / -1.2 (#44) | -3.6 / -2.1 (#31)*R | -3.5 / -2.4 (#21)*R | -1.6 / -2.0 (#87) |

**Business surveys (price expectations, core)**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_ec_food_ind_sell_price_exp_lvl` | +3.3 / +1.4 (#32)* | +4.5 / +1.7 (#28)* | +5.3 / +2.0 (#10)*R | +5.7 / +2.4 (#3)*R | +2.6 / +1.2 (#24) |
| `w_ec_food_ind_sell_price_exp_d4` | +0.1 / +0.2 (#192) | +0.6 / +0.1 (#161) | +1.2 / +0.7 (#119) | +2.0 / +1.4 (#86) | +2.5 / +1.8 (#26) |
| `ea_ec_food_ind_sell_price_exp__lvl` | +2.7 / +0.1 (#41) | +2.7 / +0.1 (#46) | +3.7 / +0.6 (#29)* | +4.2 / +0.9 (#7)* | +3.4 / +0.9 (#7) |
| `ea_ec_food_ind_sell_price_exp__d4` | -0.1 / -0.8 (#188) | -0.1 / -0.8 (#192) | +0.6 / -0.4 (#158) | +1.2 / +0.4 (#133) | +2.2 / +1.1 (#48) |
| `no_ssb_bts_consgoods_home_price_exp__lvl` | +3.9 / +1.7 (#28)* | +3.9 / +1.4 (#33)* | +4.1 / +1.5 (#23)* | +6.0 / +2.8 (#1)*R | +4.3 / +2.7 (#2)*R |
| `no_ssb_bts_consgoods_home_price_exp__d4` | +0.2 / -0.2 (#186) | +0.5 / -0.8 (#172) | +1.3 / +0.2 (#116) | +3.0 / +2.3 (#35) | +4.5 / +2.7 (#1)*R |
| `se_nier_food_mfg_sell_price_exp__lvl` | +3.0 / +1.9 (#34) | +3.0 / +1.9 (#38)* | +3.8 / +2.5 (#26)*R | +4.2 / +2.7 (#8)*R | +2.6 / +1.2 (#23) |
| `no_nbes_bl_sell_price_di__lvl` | +0.7 / -0.5 (#151) | +0.7 / -0.5 (#154) | +0.8 / -0.4 (#147) | +1.1 / -0.0 (#139) | +1.4 / +0.4 (#106) |
| `w_ec_food_retail_sell_price_exp_lvl` | +3.8 / -0.5 (#29)* | +3.8 / -0.5 (#35)* | +4.9 / -0.4 (#16)* | +4.1 / -0.5 (#12)* | +3.2 / +0.7 (#12) |

**Interest rates**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_policy_rate_lvl` | +0.8 / +0.6 (#145) | +0.8 / +0.6 (#147) | +0.4 / +0.7 (#170) | -0.1 / +0.6 (#195) | -1.0 / +0.3 (#139) |
| `w_policy_rate_d4` | +2.3 / +0.5 (#50) | +2.3 / +0.5 (#57) | +2.9 / +1.4 (#45) | +3.8 / +2.7 (#14)*R | +3.5 / +3.6 (#5) |
| `w_gov10y_lvl` | -1.9 / -1.5 (#72) | -1.9 / -1.5 (#84) | -1.9 / -1.3 (#88) | -2.0 / -1.3 (#90) | -2.0 / -1.0 (#56) |
| `w_gov10y_d4` | +1.4 / -1.3 (#100) | +1.4 / -1.3 (#109) | +1.4 / -1.4 (#113) | +1.3 / -1.4 (#129) | +2.4 / +0.9 (#32) |
| `no_policy_rate__d4` | +1.5 / +0.2 (#94) | +1.5 / +0.2 (#104) | +2.1 / +1.1 (#78) | +3.0 / +2.3 (#37) | +2.5 / +3.3 (#28) |
| `se_policy_rate__d4` | +2.4 / +1.0 (#48) | +2.4 / +1.0 (#55) | +2.8 / +1.6 (#48) | +3.3 / +2.2 (#26)* | +3.0 / +3.0 (#15) |
| `no_govbond_10y__d4` | +0.9 / -1.6 (#140) | +0.9 / -1.6 (#141) | +1.0 / -1.5 (#133) | +1.3 / -0.9 (#130) | +2.4 / +1.2 (#31) |
| `se_gov_bond_10y__d4` | +1.3 / -1.2 (#113) | +1.3 / -1.2 (#118) | +1.1 / -1.3 (#128) | +0.9 / -1.4 (#148) | +1.8 / +0.5 (#68) |

**Labour market**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_unemp_lvl` | -2.7 / -2.2 (#45) | -2.8 / -2.4 (#42) | -3.2 / -3.1 (#39)*R | -2.7 / -2.9 (#51) | -1.0 / -1.7 (#137) |
| `w_unemp_d4` | -1.3 / -0.5 (#108) | -1.6 / -0.7 (#102) | -2.2 / -1.7 (#66) | -2.4 / -2.4 (#58) | -1.3 / -4.9 (#115) |

### d_og (organic-growth change y/y, pp)

**Real wages / real income**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_real_wage_yoy` | -2.2 / -0.2 (#70) | -2.2 / -1.9 (#74) | -0.1 / +1.4 (#189) | +0.2 / +1.3 (#186) | +3.9 / +6.5 (#20)*R |
| `w_real_wage_dyoy` | -2.9 / -1.6 (#43) | -5.5 / -5.6 (#2)*R | -1.9 / -0.8 (#92) | -2.5 / -1.9 (#63) | +0.9 / +1.2 (#143) |
| `nw_real_wage_yoy` | -1.4 / +0.2 (#120) | -2.1 / -1.7 (#81) | +0.3 / +1.7 (#172) | +0.6 / +1.4 (#165) | +3.0 / +3.4 (#52)* |
| `nw_real_wage_dyoy` | -1.8 / -1.0 (#96) | -4.2 / -3.6 (#18)*R | -1.0 / -0.2 (#144) | -1.8 / -1.4 (#110) | +0.9 / +1.4 (#147) |
| `se_real_wage_yoy_q__lvl` | -2.0 / -0.6 (#83) | -1.5 / -1.3 (#114) | -0.5 / +0.1 (#164) | +0.2 / +0.4 (#187) | +3.1 / +3.5 (#51)* |
| `se_real_wage_yoy_q__d4` | -3.1 / -1.6 (#38)* | -4.6 / -4.7 (#11)*R | -4.3 / -4.4 (#16)*R | -2.6 / -3.2 (#59) | -0.1 / -0.2 (#194) |
| `no_real_wage_qna_yoy_q__lvl` | -0.3 / +1.0 (#180) | -1.4 / -0.7 (#120) | -0.2 / +0.4 (#183) | -0.2 / -0.2 (#189) | +0.6 / +1.0 (#171) |
| `no_real_wage_qna_yoy_q__d4` | -0.8 / +0.0 (#149) | -1.9 / -1.5 (#94) | -0.1 / +0.1 (#191) | -1.8 / -1.9 (#115) | -0.1 / +0.7 (#195) |
| `w_hh_real_inc_yoy` | +0.7 / +1.0 (#157) | +1.5 / +1.4 (#118) | +1.9 / +2.0 (#94) | +2.4 / +1.8 (#67) | +1.7 / +3.8 (#103) |
| `w_hh_real_inc_dyoy` | -0.8 / -0.9 (#152) | -0.4 / -1.3 (#175) | -0.1 / -0.6 (#190) | +1.2 / +0.3 (#144) | +0.9 / +1.7 (#146) |

**Consumer surveys**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_cons_conf_z` | -0.5 / +1.0 (#166) | -0.5 / +1.0 (#167) | +0.8 / +2.0 (#148) | +1.7 / +2.8 (#118) | +3.6 / +4.3 (#34)*R |
| `w_cons_conf_z_d4` | -4.0 / -2.8 (#22)*R | -4.0 / -2.8 (#23)*R | -2.0 / -2.0 (#89) | -0.7 / -1.3 (#161) | +1.6 / +1.0 (#105) |
| `nw_cons_conf_z` | -0.5 / +0.7 (#164) | -0.5 / +0.7 (#166) | +1.0 / +1.9 (#141) | +1.9 / +2.8 (#106) | +4.1 / +4.6 (#17)*R |
| `nw_cons_conf_z_d4` | -4.2 / -3.5 (#19)*R | -4.2 / -3.5 (#16)*R | -2.0 / -2.3 (#85) | -0.5 / -1.4 (#170) | +1.9 / +1.2 (#92) |
| `no_fn_cci_sa__lvl` | +0.4 / +1.4 (#172) | +0.4 / +1.4 (#172) | +1.6 / +2.4 (#106) | +2.4 / +2.9 (#69) | +2.1 / +3.0 (#84) |
| `no_fn_cci_sa__d4` | -1.8 / -1.3 (#98) | -1.8 / -1.3 (#97) | +0.1 / -0.1 (#187) | +1.0 / +0.5 (#151) | +2.1 / +2.1 (#82) |
| `se_ec_cons_conf__lvl` | -2.0 / -0.9 (#84) | -2.0 / -0.9 (#87) | +0.3 / +0.7 (#178) | +1.5 / +1.7 (#130) | +3.6 / +5.4 (#35)*R |
| `se_ec_cons_conf__d4` | -5.1 / -4.9 (#9)*R | -5.1 / -4.9 (#4)*R | -3.5 / -4.4 (#35)*R | -1.7 / -3.3 (#117) | +1.2 / +0.4 (#125) |

**Business surveys (price expectations, core)**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_ec_food_ind_sell_price_exp_lvl` | +3.2 / +1.1 (#33)* | +3.0 / +1.1 (#52)* | +2.7 / +1.4 (#59) | +2.3 / +1.5 (#81) | -1.5 / -1.5 (#112) |
| `w_ec_food_ind_sell_price_exp_d4` | +2.2 / +1.5 (#71) | +2.9 / +1.8 (#55) | +4.2 / +3.1 (#17)*R | +5.4 / +4.6 (#5)*R | +1.6 / +2.3 (#106) |
| `ea_ec_food_ind_sell_price_exp__lvl` | +3.9 / +1.3 (#23)* | +3.9 / +1.3 (#25)* | +3.5 / +2.0 (#34)* | +2.8 / +2.2 (#51) | +0.3 / -0.3 (#185) |
| `ea_ec_food_ind_sell_price_exp__d4` | +2.2 / +1.2 (#69) | +2.2 / +1.2 (#73) | +3.6 / +2.5 (#30)*R | +5.9 / +5.1 (#2)*R | +5.2 / +5.3 (#4)*R |
| `no_ssb_bts_consgoods_home_price_exp__lvl` | +2.1 / +0.7 (#77) | +1.7 / +0.1 (#101) | +0.9 / -0.8 (#146) | +0.8 / -0.6 (#158) | -1.2 / -1.9 (#130) |
| `no_ssb_bts_consgoods_home_price_exp__d4` | +3.0 / +2.4 (#42)* | +3.3 / +1.9 (#37)* | +2.9 / +1.8 (#57)* | +4.5 / +3.7 (#16)*R | +2.0 / +2.3 (#90) |
| `se_nier_food_mfg_sell_price_exp__lvl` | +2.0 / +0.5 (#86) | +2.0 / +0.5 (#91) | +2.1 / +0.8 (#80) | +2.2 / +1.0 (#85) | -0.8 / -0.9 (#149) |
| `no_nbes_bl_sell_price_di__lvl` | +1.1 / +0.2 (#140) | +1.1 / +0.2 (#142) | +1.3 / +0.6 (#123) | +1.5 / +0.8 (#127) | +0.5 / -0.4 (#176) |
| `w_ec_food_retail_sell_price_exp_lvl` | +2.7 / +0.3 (#51) | +2.7 / +0.3 (#58) | +2.4 / +1.7 (#69) | +2.0 / +2.6 (#103) | -0.4 / -0.3 (#179) |

**Interest rates**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_policy_rate_lvl` | -1.1 / -0.8 (#137) | -1.1 / -0.8 (#139) | -1.7 / -1.3 (#103) | -1.9 / -1.5 (#107) | -2.2 / -1.7 (#76) |
| `w_policy_rate_d4` | +1.6 / +1.3 (#109) | +1.6 / +1.3 (#111) | +0.8 / +0.5 (#149) | +0.3 / +0.2 (#181) | -0.6 / -0.4 (#172) |
| `w_gov10y_lvl` | -1.4 / -1.0 (#118) | -1.4 / -1.0 (#124) | -1.2 / -0.6 (#126) | -1.4 / -0.7 (#135) | -1.4 / -0.5 (#117) |
| `w_gov10y_d4` | +0.8 / -1.3 (#147) | +0.8 / -1.3 (#148) | +0.7 / -0.8 (#153) | -0.1 / -2.1 (#192) | -0.7 / -1.3 (#163) |
| `no_policy_rate__d4` | +0.7 / +0.4 (#153) | +0.7 / +0.4 (#155) | +0.5 / +0.2 (#163) | +0.4 / +0.4 (#176) | -0.5 / -0.1 (#177) |
| `se_policy_rate__d4` | +1.6 / +1.9 (#106) | +1.6 / +1.9 (#108) | +0.6 / +0.6 (#160) | +0.0 / +0.1 (#198) | -0.5 / -0.6 (#173) |
| `no_govbond_10y__d4` | +0.1 / -2.3 (#193) | +0.1 / -2.3 (#195) | +0.5 / -1.4 (#165) | +0.3 / -1.4 (#179) | +0.1 / -0.5 (#196) |
| `se_gov_bond_10y__d4` | +0.7 / -0.7 (#156) | +0.7 / -0.7 (#158) | +0.3 / -0.5 (#171) | -0.6 / -1.9 (#166) | -0.8 / -1.6 (#150) |

**Labour market**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_unemp_lvl` | -1.8 / -1.1 (#101) | -1.1 / -0.3 (#140) | -0.5 / -0.2 (#166) | +0.9 / +0.6 (#156) | +2.3 / +1.7 (#69) |
| `w_unemp_d4` | -3.4 / -2.7 (#28)*R | -3.1 / -2.3 (#49)* | -3.8 / -2.9 (#23)*R | -2.8 / -2.6 (#53) | +0.7 / -0.8 (#164) |

### vol_proxy (implied volume/mix = og - Orkla-weighted food CPI ex VAT, pp)

**Real wages / real income**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_real_wage_yoy` | +0.6 / -1.3 (#160) | +0.7 / -2.7 (#153) | +1.5 / -0.8 (#77) | +1.9 / +0.1 (#39) | +1.3 / +0.6 (#63) |
| `w_real_wage_dyoy` | -0.4 / -1.0 (#174) | -0.2 / -1.6 (#187) | +0.4 / -0.7 (#168) | +0.4 / -1.0 (#161) | +0.4 / -0.5 (#160) |
| `nw_real_wage_yoy` | +0.1 / -1.8 (#193) | -0.0 / -3.7 (#198) | +0.6 / -1.6 (#150) | +1.2 / -0.2 (#91) | +1.3 / +0.7 (#64) |
| `nw_real_wage_dyoy` | -0.8 / -1.2 (#144) | -0.8 / -2.4 (#145) | -0.2 / -1.2 (#185) | -0.2 / -1.3 (#187) | +0.1 / -0.4 (#190) |
| `se_real_wage_yoy_q__lvl` | +1.3 / -1.2 (#104) | +1.2 / -2.1 (#110) | +1.2 / -1.5 (#98) | +0.7 / -1.6 (#136) | +0.1 / -1.0 (#196) |
| `se_real_wage_yoy_q__d4` | +1.3 / +0.6 (#105) | +1.2 / -0.3 (#116) | +0.9 / -0.7 (#129) | +0.2 / -2.3 (#183) | -1.6 / -4.1 (#34) |
| `no_real_wage_qna_yoy_q__lvl` | +0.2 / -1.2 (#183) | -0.1 / -3.3 (#193) | -0.1 / -1.9 (#195) | -0.8 / -3.1 (#129) | -1.7 / -2.1 (#29) |
| `no_real_wage_qna_yoy_q__d4` | +0.8 / +0.4 (#148) | +0.9 / -0.2 (#136) | +1.0 / +0.4 (#118) | -0.5 / -1.6 (#158) | -1.3 / -1.1 (#54) |
| `w_hh_real_inc_yoy` | +2.6 / +0.7 (#31) | +2.0 / -0.4 (#49) | +0.5 / -1.0 (#155) | -0.5 / -1.4 (#152) | -1.8 / -0.7 (#22) |
| `w_hh_real_inc_dyoy` | +3.1 / +1.6 (#19) | +2.3 / +0.2 (#37) | +1.3 / -0.2 (#93) | +0.5 / -0.6 (#155) | -2.2 / -1.2 (#9) |

**Consumer surveys**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_cons_conf_z` | +1.4 / -0.7 (#100) | +1.4 / -0.7 (#97) | +1.4 / -0.9 (#79) | +1.2 / -0.9 (#85) | +0.0 / -0.5 (#197) |
| `w_cons_conf_z_d4` | +1.5 / -0.3 (#85) | +1.5 / -0.3 (#86) | +1.3 / -1.1 (#87) | +0.9 / -1.4 (#113) | -0.8 / -1.7 (#123) |
| `nw_cons_conf_z` | +0.9 / -1.6 (#135) | +0.9 / -1.6 (#130) | +1.0 / -1.6 (#124) | +0.8 / -1.8 (#132) | -0.7 / -1.1 (#142) |
| `nw_cons_conf_z_d4` | +1.4 / -0.5 (#90) | +1.4 / -0.5 (#91) | +1.2 / -1.2 (#96) | +0.8 / -1.7 (#127) | -1.1 / -2.1 (#83) |
| `no_fn_cci_sa__lvl` | +0.3 / -2.0 (#178) | +0.3 / -2.0 (#183) | +0.4 / -1.5 (#162) | +0.2 / -1.4 (#185) | -0.9 / -0.8 (#113) |
| `no_fn_cci_sa__d4` | +0.9 / -1.0 (#141) | +0.9 / -1.0 (#140) | +0.8 / -1.1 (#135) | +0.3 / -1.4 (#172) | -1.8 / -1.5 (#26) |
| `se_ec_cons_conf__lvl` | +1.7 / -1.0 (#67) | +1.7 / -1.0 (#65) | +1.6 / -1.4 (#69) | +1.3 / -1.8 (#81) | -0.1 / -1.2 (#194) |
| `se_ec_cons_conf__d4` | +1.6 / -0.0 (#75) | +1.6 / -0.0 (#75) | +1.4 / -1.1 (#80) | +1.0 / -1.8 (#111) | -0.3 / -2.6 (#172) |

**Business surveys (price expectations, core)**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_ec_food_ind_sell_price_exp_lvl` | +0.0 / +0.0 (#195) | -1.2 / -0.8 (#113) | -2.0 / -0.6 (#46) | -1.9 / +0.1 (#38) | -1.5 / +0.0 (#42) |
| `w_ec_food_ind_sell_price_exp_d4` | +2.2 / +0.7 (#43) | +0.2 / -0.5 (#190) | -1.1 / -0.3 (#109) | -1.1 / +0.3 (#98) | -0.7 / +0.9 (#128) |
| `ea_ec_food_ind_sell_price_exp__lvl` | -0.3 / -0.2 (#180) | -0.3 / -0.2 (#185) | -1.1 / -0.7 (#115) | -2.1 / -0.8 (#21) | -2.5 / -0.8 (#6) |
| `ea_ec_food_ind_sell_price_exp__d4` | +1.9 / +0.5 (#54) | +1.9 / +0.5 (#56) | +0.4 / -0.2 (#160) | -0.8 / -0.1 (#128) | -1.4 / -0.0 (#49) |
| `no_ssb_bts_consgoods_home_price_exp__lvl` | +0.1 / +0.6 (#194) | -0.6 / -0.2 (#163) | -1.2 / +0.2 (#101) | -1.1 / +0.8 (#99) | -0.8 / +1.2 (#126) |
| `no_ssb_bts_consgoods_home_price_exp__d4` | +1.8 / +0.4 (#61) | +0.1 / -1.1 (#192) | -1.0 / -0.5 (#122) | -0.4 / +1.5 (#165) | -0.2 / +2.4 (#186) |
| `se_nier_food_mfg_sell_price_exp__lvl` | -0.0 / +0.2 (#196) | -0.0 / +0.2 (#196) | -1.1 / -0.5 (#113) | -1.5 / +0.2 (#60) | -1.8 / -0.6 (#21) |
| `no_nbes_bl_sell_price_di__lvl` | -0.6 / -0.8 (#167) | -0.6 / -0.8 (#169) | -1.2 / -1.2 (#104) | -1.5 / -1.5 (#62) | -1.9 / -1.3 (#19) |
| `w_ec_food_retail_sell_price_exp_lvl` | -1.1 / -1.2 (#121) | -1.1 / -1.2 (#120) | -2.4 / -1.4 (#29) | -4.1 / -1.2 (#1) | -1.4 / +1.0 (#50) |

**Interest rates**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_policy_rate_lvl` | -1.7 / -1.0 (#66) | -1.7 / -1.0 (#64) | -1.6 / -1.2 (#67) | -1.5 / -1.4 (#63) | -1.1 / -1.5 (#87) |
| `w_policy_rate_d4` | -0.8 / +0.6 (#149) | -0.8 / +0.6 (#147) | -0.8 / +0.6 (#136) | -0.5 / +0.9 (#160) | +0.3 / +1.3 (#167) |
| `w_gov10y_lvl` | -3.1 / -2.8 (#17) | -3.1 / -2.8 (#15) | -2.8 / -2.6 (#15) | -2.5 / -2.4 (#6) | -1.3 / -1.9 (#52) |
| `w_gov10y_d4` | -2.1 / -1.9 (#45) | -2.1 / -1.9 (#45) | -2.7 / -2.1 (#16) | -3.2 / -2.2 (#2) | -1.2 / -0.2 (#76) |
| `no_policy_rate__d4` | -0.9 / +0.0 (#133) | -0.9 / +0.0 (#128) | -1.0 / -0.1 (#119) | -0.7 / +0.3 (#138) | -0.2 / +0.7 (#188) |
| `se_policy_rate__d4` | -0.6 / +1.0 (#163) | -0.6 / +1.0 (#164) | -0.4 / +0.9 (#161) | +0.1 / +1.0 (#188) | +1.2 / +1.2 (#66) |
| `no_govbond_10y__d4` | -1.7 / -1.8 (#65) | -1.7 / -1.8 (#63) | -2.0 / -2.1 (#45) | -2.2 / -1.9 (#13) | -1.5 / -0.4 (#41) |
| `se_gov_bond_10y__d4` | -2.3 / -1.7 (#38) | -2.3 / -1.7 (#38) | -2.4 / -1.6 (#26) | -2.5 / -1.8 (#7) | -0.8 / -0.3 (#120) |

**Labour market**

| feature | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| `w_unemp_lvl` | +0.1 / -0.6 (#191) | +0.7 / -0.2 (#156) | +0.7 / -0.4 (#139) | +0.9 / -0.2 (#117) | +0.7 / -0.0 (#136) |
| `w_unemp_d4` | -1.5 / -1.0 (#82) | -0.0 / -0.4 (#200) | +0.5 / -0.9 (#156) | +0.7 / -1.1 (#142) | +0.7 / -1.8 (#137) |

### Business surveys in the all-feature family (top 3 per alignment)

The core set contains no `business_survey` features (confidence and PMI-type indices); they appear only among the 1,420. Ranks are out of about 1,400.

**d_margin**

| alignment | feature | n | t HAC | rank (of ~1,400) | q BY | t ex-infl | flags |
|---|---|---|---|---|---|---|---|
| coin | `pl_ec_retail_conf__d4` | 102 | -4.5 | 36 | 0.005 | -4.1 | SR |
| coin | `at_ec_food_ind_conf__d4` | 102 | -4.1 | 56 | 0.014 | -4.7 | SR |
| coin | `at_ec_food_ind_conf__lvl` | 102 | -3.7 | 89 | 0.041 | -3.3 | SR |
| rt0 | `pl_ec_retail_conf__d4` | 102 | -4.5 | 26 | 0.007 | -4.1 | SR |
| rt0 | `at_ec_food_ind_conf__d4` | 102 | -4.1 | 38 | 0.021 | -4.7 | SR |
| rt0 | `at_ec_food_ind_conf__lvl` | 102 | -3.7 | 57 | 0.064 | -3.3 | S |
| rt1 | `de_oecd_bci__d4` | 102 | -3.3 | 64 | 0.224 | -2.6 | S |
| rt1 | `ee_ec_retail_conf__d4` | 101 | -3.1 | 81 | 0.294 | -3.3 | S |
| rt1 | `ea_oecd_bci__d4` | 102 | -3.1 | 92 | 0.310 | -2.3 | S |
| rt2 | `ee_ec_retail_conf__d4` | 100 | -3.5 | 30 | 0.212 | -4.1 | S |
| rt2 | `lt_ec_esi__d4` | 100 | -3.5 | 36 | 0.212 | -3.0 | S |
| rt2 | `ee_ec_esi__d4` | 100 | -3.5 | 38 | 0.212 | -3.8 | S |
| rt4 | `no_nbrn_profit_retail__lvl` | 82 | -3.4 | 18 | 0.594 | -3.0 | S |
| rt4 | `dk_oecd_bci__d4` | 102 | -3.1 | 39 | 0.639 | -3.5 | S |
| rt4 | `pl_ec_retail_conf__lvl` | 102 | +2.6 | 106 | 0.990 | +2.6 | S |

**og**

| alignment | feature | n | t HAC | rank (of ~1,400) | q BY | t ex-infl | flags |
|---|---|---|---|---|---|---|---|
| coin | `no_nbrn_output_next_retail__lvl` | 86 | -5.4 | 59 | 0.000 | -3.1 | SR |
| coin | `no_nbrn_output_cur_retail__lvl` | 86 | -5.0 | 77 | 0.000 | -3.3 | SR |
| coin | `no_nbrn_profit_retail__lvl` | 86 | -4.2 | 101 | 0.007 | -2.5 | SR |
| rt0 | `no_nbrn_output_next_retail__lvl` | 86 | -5.4 | 56 | 0.000 | -3.1 | SR |
| rt0 | `no_nbrn_output_cur_retail__lvl` | 86 | -5.0 | 65 | 0.000 | -3.3 | SR |
| rt0 | `no_nbrn_profit_retail__lvl` | 86 | -4.2 | 103 | 0.007 | -2.5 | SR |
| rt1 | `no_ssb_bts_consgoods_profitability__lvl` | 57 | -4.9 | 52 | 0.002 | -1.9 |  |
| rt1 | `no_nbrn_output_next_retail__lvl` | 85 | -4.2 | 76 | 0.010 | -2.3 | SR |
| rt1 | `dk_ec_retail_conf__lvl` | 63 | -3.8 | 111 | 0.032 | -0.7 |  |
| rt2 | `se_oecd_bci__lvl` | 102 | +4.5 | 33 | 0.006 | +3.5 | SR |
| rt2 | `ea_oecd_bci__lvl` | 102 | +3.8 | 66 | 0.042 | +3.5 | SR |
| rt2 | `ro_ec_retail_conf__d4` | 100 | +3.7 | 71 | 0.062 | +2.8 | S |
| rt4 | `se_oecd_bci__lvl` | 102 | +5.5 | 4 | 0.001 | +4.8 | SR |
| rt4 | `de_oecd_bci__lvl` | 102 | +4.4 | 15 | 0.020 | +4.1 | SR |
| rt4 | `ea_oecd_bci__lvl` | 102 | +4.3 | 17 | 0.023 | +7.1 | SR |

**d_og**

| alignment | feature | n | t HAC | rank (of ~1,400) | q BY | t ex-infl | flags |
|---|---|---|---|---|---|---|---|
| coin | `ro_ec_retail_conf__d4` | 98 | +4.5 | 72 | 0.003 | +4.4 | SR |
| coin | `no_nbrn_profit_retail__d4` | 82 | -4.5 | 76 | 0.003 | -2.5 | SR |
| coin | `ro_ec_food_ind_conf__d4` | 82 | +4.5 | 81 | 0.004 | +5.0 | SR |
| rt0 | `ro_ec_retail_conf__d4` | 98 | +4.5 | 66 | 0.003 | +4.4 | SR |
| rt0 | `no_nbrn_profit_retail__d4` | 82 | -4.5 | 71 | 0.003 | -2.5 | SR |
| rt0 | `ro_ec_food_ind_conf__d4` | 82 | +4.5 | 75 | 0.004 | +5.0 | SR |
| rt1 | `sk_ec_retail_conf__lvl` | 98 | +4.7 | 42 | 0.003 | +4.6 | SR |
| rt1 | `sk_ec_retail_conf__d4` | 98 | +4.2 | 79 | 0.008 | +3.7 | SR |
| rt1 | `se_oecd_bci__lvl` | 98 | +3.6 | 154 | 0.041 | +2.7 | SR |
| rt2 | `sk_ec_retail_conf__d4` | 98 | +5.0 | 46 | 0.001 | +5.3 | SR |
| rt2 | `no_nbes_bl_profit_past12m__lvl` | 68 | +5.0 | 54 | 0.001 | +4.6 |  |
| rt2 | `ro_ec_retail_conf__d4` | 98 | +4.0 | 114 | 0.011 | +3.4 | SR |
| rt4 | `g7_oecd_bci__d4` | 98 | +7.2 | 3 | 0.000 | +6.2 | SR |
| rt4 | `de_oecd_bci__d4` | 98 | +6.7 | 5 | 0.000 | +5.8 | SR |
| rt4 | `se_oecd_bci__d4` | 98 | +6.6 | 6 | 0.000 | +6.4 | SR |

**vol_proxy**

| alignment | feature | n | t HAC | rank (of ~1,400) | q BY | t ex-infl | flags |
|---|---|---|---|---|---|---|---|
| coin | `ro_ec_esi__d4` | 102 | +4.3 | 24 | 0.016 | +5.1 | SR |
| coin | `no_nbrn_output_next_hhserv__d4` | 64 | +3.8 | 46 | 0.083 | +1.7 |  |
| coin | `hu_ec_retail_conf__lvl` | 102 | +3.7 | 47 | 0.083 | +3.3 | S |
| rt0 | `ro_ec_esi__d4` | 102 | +4.3 | 18 | 0.021 | +5.1 | SR |
| rt0 | `no_nbrn_output_next_hhserv__d4` | 64 | +3.8 | 38 | 0.099 | +1.7 |  |
| rt0 | `hu_ec_retail_conf__lvl` | 102 | +3.7 | 39 | 0.099 | +3.3 | S |
| rt1 | `hu_ec_retail_conf__lvl` | 102 | +4.4 | 6 | 0.049 | +3.8 | S |
| rt1 | `no_nbrn_output_next_hhserv__d4` | 63 | +3.7 | 29 | 0.182 | -0.2 |  |
| rt1 | `hu_ec_esi__lvl` | 102 | +3.4 | 43 | 0.216 | +3.1 | S |
| rt2 | `no_nbrn_output_next_hhserv__d4` | 62 | +6.1 | 1 | 0.001 | +1.2 |  |
| rt2 | `hu_ec_retail_conf__lvl` | 102 | +4.2 | 8 | 0.084 | +4.0 | S |
| rt2 | `no_nbrn_output_next_hhserv__lvl` | 66 | +3.9 | 16 | 0.149 | +0.9 |  |
| rt4 | `no_nbrn_profit_retail__d4` | 78 | +3.1 | 34 | 0.994 | +1.3 | S |
| rt4 | `at_ec_retail_conf__d4` | 102 | -2.8 | 46 | 1.000 | -1.8 | S |
| rt4 | `pl_ec_food_ind_conf__d4` | 56 | -2.6 | 73 | 1.000 | -0.9 |  |

### Conditional checks: does the variable survive a direct price or cost control?

Each cell shows the HAC t of the feature with the control added: `full / excluding 2021Q3-2023Q4`. The target specification is unchanged.

| target | feature | control | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|---|---|
| d_margin | `w_gov10y_d4` | `packaging_eu_yoy` | -3.2 / -3.0 | -3.2 / -3.1 | -2.6 / -2.8 | -1.7 / -1.7 | -0.9 / -0.2 |
| d_margin | `w_gov10y_d4` | `w_food_ppi_yoy` | -3.4 / -3.0 | -4.0 / -3.1 | -4.1 / -3.0 | -3.0 / -2.1 | -1.5 / -0.6 |
| d_margin | `w_gov10y_d4` | `w_cpi_dyoy` | -4.0 / -3.0 | -4.2 / -3.2 | -3.2 / -2.9 | -1.9 / -1.7 | -0.6 / +0.1 |
| d_margin | `se_real_wage_yoy_q__d4` | `se_cpi_idx__dyoy` | +0.5 / +0.7 | -0.1 / +0.9 | -0.3 / +0.5 | -1.1 / -0.4 | -3.1 / -3.2 |
| d_margin | `w_unemp_d4` | `packaging_eu_yoy` | +1.7 / +1.8 | +0.9 / +0.5 | +0.6 / +0.5 | -0.1 / +0.1 | -1.0 / +0.1 |
| og | `nw_cons_conf_z` | `w_food_cpi_xvat_yoy` | -3.0 / -2.7 | -3.2 / -2.6 | -3.0 / -2.3 | -2.8 / -2.3 | -1.9 / -1.1 |
| og | `w_real_wage_yoy` | `w_food_cpi_xvat_yoy` | -1.8 / -1.2 | -2.9 / -2.2 | -1.5 / +0.1 | -1.3 / +0.8 | -0.6 / +1.3 |
| og | `w_policy_rate_d4` | `w_food_cpi_xvat_yoy` | +1.0 / +0.6 | +1.4 / +0.9 | +2.1 / +1.4 | +3.1 / +2.6 | +4.6 / +5.4 |
| d_og | `se_ec_cons_conf__d4` | `w_food_cpi_xvat_dyoy` | -2.7 / -2.2 | -3.8 / -2.3 | -5.5 / -4.2 | -3.6 / -3.7 | -0.2 / -2.1 |
| d_og | `w_real_wage_dyoy` | `w_food_cpi_xvat_dyoy` | -1.2 / -0.6 | -3.5 / -3.4 | -0.9 / +0.6 | -2.2 / -1.5 | -0.2 / +0.4 |
| vol_proxy | `w_gov10y_lvl` | `w_food_cpi_xvat_yoy` | -2.8 / -2.4 | -2.8 / -2.6 | -2.7 / -2.6 | -2.3 / -2.4 | -1.5 / -2.0 |

### Verdict on the requested variables

**Real wages**
- **Margins.** Swedish real-wage acceleration (`se_real_wage_yoy_q__d4`) is a robust positive nowcast predictor (t = +4.2, #9). It disappears entirely once Swedish CPI acceleration is controlled (t about 0). It is an inflation proxy: real wages accelerate when inflation, and hence input costs, decelerate.
- **Organic growth.** Real wages are strongly negative (`w_real_wage_yoy` nowcast t = -7.6, #5), again because inflation lowers real wages and raises Orkla's prices.
- **Change in organic growth.** Real-wage deceleration predicts higher d_og in the nowcast (`w_real_wage_dyoy` t = -5.5; with a food-CPI-acceleration control, t = -3.5). Real-wage levels 4-5 quarters back predict d_og positively (`w_real_wage_yoy` h = 4 t = +3.9, +base +3.0), partly through the base effect: low real wages mean high inflation, hence high og in the base year.
- **Volume.** No robust positive effect on implied volume at any horizon.
- **Conclusion.** Real wages matter through the inflation term, not as a demand driver Orkla benefits from.

**Consumer confidence**
- **Levels vs og.** Levels are negatively related to og (`nw_cons_conf_z` nowcast t = -7.2, robust). The sign survives a food-CPI control (t about -3) and the ex-infl sample, but there is no matching positive volume effect.
- **Reading.** Food at home is defensive or counter-cyclical, and confidence also captures inflation perceptions.
- **Changes vs d_og.** Confidence changes predict d_og negatively in the nowcast (`se_ec_cons_conf__d4` t = -5.1). This survives a food-CPI-acceleration control (t = -3.8 nowcast, -5.5 at h = 1).
- **Levels 4-5 quarters back.** These predict d_og positively (`nw_cons_conf_z` h = 4 t = +4.1). Part of that is the base effect (+base t = +2.7).
- **Margins.** Nothing.

**Business surveys**
- **Selling-price expectations** in food manufacturing and retail are the main survey signal, and the best survey-based leading indicators of og and d_og at h = 1-4.
- **Same-quarter margins.** High selling-price expectations coincide with margin squeezes: firms expect to raise prices because costs have risen.
- **General business confidence** (OECD BCI) adds to d_og at h = 4 and to og levels at h = 4 (all-feature family).

**Interest rates**
- **Margins.** Changes in long yields are robust negative predictors at h = 0-1 and survive the cost controls. This is the best rates result.
- **og.** Policy-rate changes predict og positively at h = 2-4 (`w_policy_rate_d4` h = 4 t = +3.5; with a food-CPI control +4.6 full and +5.4 ex-infl). Central banks hike into the inflation that later shows up in Orkla's prices.
- **Volume.** Yield levels are weakly negative and not BY-significant.
- **Levels in general.** Rate levels are uninformative for margins.

## 3. Interpretation by category

**Prices: consumer food CPI, PPI and price expectations**
- **og and d_og.** Price variables are the backbone of the og and d_og results:
  - og: same-quarter levels.
  - d_og: accelerations (dyoy), plus the lagged levels that operate through the base effect.
- **Swedish food CPI vs the weighted composite.** Swedish food CPI is the single best og series, ahead of the Orkla-weighted composite. Sweden is about 27-29% of sales and its CPI has no publication lag.
- **Use the ex-VAT variants for 2026.** The Swedish food-VAT cut in 2026Q2 depresses `w_food_cpi_yoy` (-1.0 in 2026Q2, against +0.6 for `_xvat`). Use the `_xvat` variants for 2026 nowcasts.
- **Survey price expectations lead by 1-4 quarters:**
  - SSB consumer-goods price expectations.
  - EC food-industry and retail selling-price expectations.
  - NIER food selling prices.

**Input costs: packaging, food PPI, agricultural and FAO commodities, energy**
- **Packaging PPIs** (EU plastics and paper, US corrugated) are the best margin series. They lead commodity indices, presumably because they capture the broad industrial-cost wave and Orkla's packaging-heavy cost base.
- **Global food commodities** (FAO, World Bank, in local currency) are weaker for margins than European PPIs (e.g. `fao_ffpi_wloc_yoy` nowcast t = -2.5). They work better for d_og at h = 2 (`glob_fao_ffpi_eur__yoy` t = +4.9).
- **Energy** (Nordic electricity, EU gas) never survives BY for margins or og. EU gas and Nordic electricity inflation 1-4 quarters back do lead d_og positively (e.g. `natgas_eu_eur_yoy` h = 2 t = +4.1), as part of the inflation cycle.
- **Price-cost gaps** (food CPI minus PPI or commodities) relate positively to d_margin, as expected, but weaker than the raw cost series. They relate negatively to d_og, since gaps open when costs fall and prices stagnate.

**Wages and real wages**
- **Nominal wage growth.** Mostly insignificant for margins. The labour-cost shock is slow and smooth.
- **Real wages.** Real-wage measures load on their CPI component. See section 2.
- **All-feature family exception.** Euro-area compensation per employee acceleration (`ea_comp_per_employee_q__dyoy`, coincident t = -7.0, ex-infl -7.5) is a strong same-quarter margin correlate. It is not real-time.

**Surveys:** see section 2. In short, price-expectation surveys are useful and confidence surveys are mostly inflation proxies.

**Rates:** see section 2. Yield changes matter for margins, and policy-rate changes lead og at h = 2-4.

**FX**
- **Essentially nothing** for d_margin, og or volume: no FX feature passes BY. Organic growth excludes currency translation, and EBIT margin is a ratio, so translation largely cancels.
- **The one exception** is d_og at h = 4. A weaker NOK against EUR predicts lower d_og (`no_fx_eurnok__yoy` t = -3.9), most likely through imported inflation raising the base-period og.
- **Transactional FX** (NOK and SEK against EUR/USD for imported inputs) does not show up as a robust univariate predictor.

**Activity: retail volumes, GDP, household consumption**
- **Volume.** These explain volume coincidentally (Nordic grocery volumes, Swedish household food consumption).
- **Same-quarter margins.** Market-volume acceleration goes with margin gains (`nw_retail_food_vol_dyoy` coincident t = +4.1), i.e. operating leverage.
- **Lagged GDP growth** predicts d_og at h = 2.
- **Sign flip for Norwegian grocery volume.** Its acceleration is *negative* for d_og at h = 1 (t = -6.7), but the sign is unstable (2001-12 t = +0.1).
- **Unemployment changes** relate positively to same-quarter margins, but this is explained by cost deflation in downturns (section 2).

## 4. Distributed-lag profiles (core features, k = 0..6 beyond the publication lag)

- `best k` is the lag with the largest |HAC t|.
- The q-value is BY over all 200 x 7 = 1,386 lag tests of the target. This penalises the search over lags.
- The profile columns give t at k = 0..6, for the full sample and excluding 2021Q3-2023Q4.
- Full profiles: `lag_profiles.csv`, `lag_best.csv` and `figures/lagprofile_<target>.png`.

### d_margin (EBIT-margin change y/y, pp)

25 features have a BY-significant best lag. Distribution of best k among them: {0: 13, 3: 1, 5: 4, 6: 7}.

| feature | cat | best k | t best | q BY (lag family) | t +own lag | t ex-infl | t by k=0..6 | t ex-infl by k=0..6 |
|---|---|---|---|---|---|---|---|---|
| `eu_ppi_plastic_products_idx__yoy` | packaging | 0 | -8.8 | 0.000 | -7.7 | -3.0 | -8.8 -4.4 -2.5 -1.3 -0.0 +1.4 +2.3 | -3.0 -1.9 -0.9 -0.0 +1.5 +2.6 +2.5 |
| `packaging_eu_yoy` | packaging | 0 | -5.8 | 0.000 | -5.6 | -3.0 | -5.8 -3.0 -1.8 -0.6 +1.0 +2.2 +3.0 | -3.0 -1.5 -0.5 +0.6 +2.3 +3.5 +3.9 |
| `eu_ppi_dom_c105_idx__yoy` | PPI/input | 6 | +5.2 | 0.004 | +4.5 | +5.6 | -1.9 -0.8 +0.4 +1.4 +2.5 +4.0 +5.2 | -0.8 +0.2 +1.1 +1.8 +2.8 +4.6 +5.6 |
| `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 0 | -5.3 | 0.004 | -4.8 | -1.1 | -5.3 -3.6 -2.5 -1.6 -0.3 +1.6 +2.3 | -1.1 -1.4 -1.1 +0.2 +1.8 +2.6 +2.8 |
| `w_gov10y_d4` | rates | 0 | -5.1 | 0.004 | -4.7 | -3.1 | -5.1 -3.7 -2.3 -1.5 -0.3 +1.1 +2.6 | -3.1 -2.7 -1.6 -0.9 +0.3 +1.7 +2.8 |
| `no_govbond_10y__d4` | rates | 0 | -4.9 | 0.006 | -4.6 | -3.6 | -4.9 -4.1 -2.5 -1.4 -0.2 +0.9 +2.2 | -3.6 -2.7 -1.5 -0.7 +0.5 +1.5 +2.4 |
| `se_ppi_food_hmpi_idx__yoy` | PPI/input | 6 | +4.8 | 0.010 | +3.5 | +4.7 | -1.1 -0.6 +0.6 +2.1 +2.8 +3.9 +4.8 | +0.3 +0.7 +1.9 +2.7 +3.6 +4.5 +4.7 |
| `eu_ppi_paper_packaging_idx__yoy` | packaging | 0 | -4.7 | 0.010 | -4.7 | -2.7 | -4.7 -2.5 -1.4 +0.0 +1.7 +2.5 +3.0 | -2.7 -1.2 -0.2 +1.0 +2.6 +3.4 +3.6 |
| `ea_ec_food_ind_sell_price_exp__lvl` | price exp. | 0 | -4.7 | 0.012 | -4.9 | -1.4 | -4.7 -3.7 -2.1 -1.1 -0.1 +0.9 +2.0 | -1.4 -1.2 -0.3 +0.4 +1.4 +1.8 +2.6 |
| `eu_ppi_dom_c107_idx__yoy` | PPI/input | 5 | +4.5 | 0.024 | +3.4 | +5.7 | -0.9 -0.1 +1.2 +2.4 +3.5 +4.5 +3.6 | +0.5 +1.3 +2.1 +3.4 +5.6 +5.7 +3.3 |
| `se_cpi_idx__dyoy` | CPI | 0 | -4.2 | 0.046 | -3.7 | -3.5 | -4.2 -3.7 -2.8 -1.7 -0.0 +1.1 +2.2 | -3.5 -3.1 -2.1 -1.0 +0.5 +1.6 +2.5 |
| `se_cpi_idx__yoy` | CPI | 6 | +4.2 | 0.046 | +3.4 | +4.3 | -2.3 -1.1 -0.1 +1.0 +2.2 +3.3 +4.2 | -0.6 +0.7 +1.9 +2.8 +3.6 +4.1 +4.3 |

### og (organic growth, %)

52 features have a BY-significant best lag. Distribution of best k among them: {0: 28, 1: 7, 2: 8, 3: 5, 4: 1, 5: 1, 6: 2}.

| feature | cat | best k | t best | q BY (lag family) | t +own lag | t ex-infl | t by k=0..6 | t ex-infl by k=0..6 |
|---|---|---|---|---|---|---|---|---|
| `se_cpi_food_idx__yoy` | CPI | 0 | +11.5 | 0.000 | +11.7 | +3.5 | +11.5 +8.3 +4.1 +1.9 +0.6 -0.1 -0.5 | +3.5 +3.7 +1.9 +0.5 +0.2 -0.1 -0.0 |
| `no_ppi_food_dom_idx__yoy` | PPI/input | 0 | +9.1 | 0.000 | +8.5 | +1.6 | +9.1 +7.5 +4.8 +2.7 +1.5 +0.8 +0.0 | +1.6 +1.2 +0.7 +0.2 -0.1 -0.1 -0.0 |
| `w_food_ppi_yoy` | PPI/input | 0 | +8.3 | 0.000 | +7.2 | +1.5 | +8.3 +6.1 +3.9 +2.4 +1.3 +0.1 -0.7 | +1.5 +1.5 +0.9 +0.4 +0.2 -0.2 -0.5 |
| `nw_food_ppi_yoy` | PPI/input | 0 | +8.3 | 0.000 | +7.7 | +2.4 | +8.3 +6.1 +4.0 +2.6 +1.6 +0.2 -0.6 | +2.4 +2.2 +1.4 +0.9 +0.4 -0.1 -0.4 |
| `w_real_wage_yoy` | wages/inc. | 0 | -7.6 | 0.000 | -7.4 | -2.3 | -7.6 -3.6 -2.2 -1.6 -0.7 -0.4 +0.7 | -2.3 -0.1 +0.6 +0.5 +0.8 +0.4 +1.0 |
| `nw_food_cpi_xvat_yoy` | CPI | 0 | +7.5 | 0.000 | +7.9 | +2.7 | +7.5 +4.2 +2.7 +1.2 +0.4 -0.2 -0.7 | +2.7 +2.5 +2.4 +0.8 +0.5 +0.2 -0.1 |
| `eu_ppi_dom_c107_idx__yoy` | PPI/input | 0 | +7.4 | 0.000 | +7.0 | +2.7 | +7.4 +4.9 +3.2 +2.2 +1.0 -0.4 -1.2 | +2.7 +2.3 +1.7 +1.5 +0.9 -0.2 -0.8 |
| `se_ec_cons_conf__lvl` | cons. survey | 0 | -7.3 | 0.000 | -7.5 | -2.9 | -7.3 -5.5 -3.2 -1.9 -0.7 +0.3 +1.1 | -2.9 -3.2 -2.7 -2.0 -0.8 +0.5 +0.9 |
| `nw_cons_conf_z` | cons. survey | 0 | -7.2 | 0.000 | -7.8 | -3.2 | -7.2 -5.2 -3.5 -2.5 -1.6 -0.4 +0.4 | -3.2 -3.0 -2.5 -1.9 -0.9 +0.2 +0.7 |
| `se_ppi_food_hmpi_idx__yoy` | PPI/input | 0 | +7.1 | 0.000 | +6.7 | +2.3 | +7.1 +5.6 +3.6 +2.5 +1.6 +0.3 -0.8 | +2.3 +2.3 +1.3 +1.1 +0.7 -0.3 -0.8 |
| `se_cpi_idx__yoy` | CPI | 0 | +6.8 | 0.000 | +6.3 | +1.4 | +6.8 +5.8 +4.0 +3.0 +2.2 +1.4 +0.2 | +1.4 +2.1 +1.8 +1.6 +1.3 +1.0 +0.2 |
| `se_real_wage_yoy_q__lvl` | wages/inc. | 0 | -6.8 | 0.000 | -5.9 | -2.2 | -6.8 -4.7 -3.5 -2.6 -2.1 -1.4 -0.3 | -2.2 -2.1 -2.0 -1.8 -1.6 -1.1 +0.1 |

### d_og (organic-growth change y/y, pp)

145 features have a BY-significant best lag. Distribution of best k among them: {0: 28, 1: 18, 2: 22, 3: 10, 4: 17, 5: 25, 6: 25}.

| feature | cat | best k | t best | q BY (lag family) | t +own lag | t +base | t ex-infl | t by k=0..6 | t ex-infl by k=0..6 |
|---|---|---|---|---|---|---|---|---|---|
| `eu_ppi_dom_c106_idx__yoy` | PPI/input | 6 | -7.8 | 0.000 | -4.5 | -3.7 | -7.5 | +4.1 +3.2 +1.4 -0.1 -1.6 -3.7 -7.8 | +3.9 +3.1 +1.1 -0.3 -1.6 -3.5 -7.5 |
| `eu_ppi_dom_c106_idx__dyoy` | PPI/input | 2 | +7.4 | 0.000 | +7.7 | +2.9 | +6.4 | +4.6 +6.4 +7.4 +4.7 +1.9 -0.0 -1.6 | +3.9 +5.6 +6.4 +4.7 +2.1 +0.1 -1.5 |
| `w_ec_cons_price_exp_d4` | price exp. | 3 | +7.2 | 0.000 | +6.1 | +1.7 | +5.6 | +1.1 +2.4 +4.3 +7.2 +4.3 +2.8 +1.8 | +0.6 +2.5 +4.2 +5.6 +4.6 +3.3 +2.6 |
| `no_retail_foodstores_vol_sa_idx__dyoy` | activity | 1 | -6.7 | 0.000 | -7.2 | -3.1 | -2.5 | -3.6 -6.7 -5.3 -2.0 -0.0 +0.7 +1.4 | -0.9 -2.5 -3.7 -2.5 -2.8 -0.7 +0.3 |
| `eu_ppi_dom_c108_idx__yoy` | PPI/input | 4 | -6.6 | 0.000 | -7.0 | -4.4 | -4.9 | +0.7 -0.7 -2.0 -4.8 -6.6 -5.0 -4.0 | +0.1 -1.1 -3.1 -5.7 -4.9 -4.0 -3.6 |
| `se_ec_cons_conf__lvl` | cons. survey | 6 | +6.4 | 0.000 | +6.2 | +4.1 | +4.7 | -2.0 +0.3 +1.5 +2.2 +3.6 +6.0 +6.4 | -0.9 +0.7 +1.7 +2.3 +5.4 +6.2 +4.7 |
| `se_ppi_food_hmpi_idx__yoy` | PPI/input | 5 | -6.2 | 0.000 | -5.2 | -3.5 | -5.6 | +2.0 +1.0 -1.1 -2.5 -3.8 -6.2 -5.7 | +1.2 +0.6 -1.3 -2.8 -5.1 -5.6 -5.0 |
| `glob_gscpi__d4` | packaging | 5 | +6.1 | 0.000 | +5.8 | +4.5 | +3.8 | +0.7 +1.2 +1.3 +0.8 +3.4 +6.1 +3.7 | +0.3 +0.5 +0.3 +0.4 +2.3 +3.8 +3.7 |
| `ea_ec_food_ind_sell_price_exp__d4` | price exp. | 3 | +6.0 | 0.000 | +9.1 | +2.9 | +6.2 | +2.2 +3.6 +5.9 +6.0 +5.2 +2.1 +0.3 | +1.2 +2.5 +5.1 +6.2 +5.3 +3.4 +0.9 |
| `nw_food_cpi_xvat_yoy` | CPI | 6 | -6.0 | 0.000 | -5.4 | -2.5 | -4.9 | +0.0 -1.1 -1.8 -2.6 -3.7 -5.5 -6.0 | -1.8 -2.2 -3.4 -5.4 -5.1 -5.0 -4.9 |
| `nw_cons_conf_z_d4` | cons. survey | 6 | +6.0 | 0.000 | +3.5 | +4.0 | +6.2 | -4.2 -2.0 -0.5 +0.6 +1.9 +5.0 +6.0 | -3.5 -2.3 -1.4 -0.2 +1.2 +5.3 +6.2 |
| `no_qna_hh_food_cons_sa_mnok__yoy` | activity | 5 | +5.8 | 0.000 | +5.4 | +3.8 | +3.5 | -0.9 -0.8 +0.1 +2.2 +3.3 +5.8 +4.7 | +0.1 -0.7 -0.5 +0.9 +1.4 +3.5 +2.8 |

### d_margin_r4 (rolling-4Q margin change, pp)

88 features have a BY-significant best lag. Distribution of best k among them: {0: 34, 1: 19, 2: 10, 3: 12, 4: 1, 5: 7, 6: 5}.

| feature | cat | best k | t best | q BY (lag family) | t +own lag | t ex-infl | t by k=0..6 | t ex-infl by k=0..6 |
|---|---|---|---|---|---|---|---|---|
| `eu_ppi_plastic_products_idx__yoy` | packaging | 1 | -15.8 | 0.000 | -16.4 | -2.8 | -15.4 -15.8 -10.5 -6.0 -3.2 -1.3 +0.5 | -2.8 -2.8 -2.4 -1.7 -0.6 +0.6 +1.8 |
| `packaging_eu_yoy` | packaging | 0 | -13.9 | 0.000 | -10.9 | -2.9 | -13.9 -11.5 -7.5 -4.5 -2.1 -0.1 +1.7 | -2.9 -3.0 -2.3 -1.3 +0.0 +1.3 +2.3 |
| `eu_ppi_paper_packaging_idx__yoy` | packaging | 0 | -10.3 | 0.000 | -7.7 | -2.9 | -10.3 -9.7 -6.7 -3.9 -1.3 +0.8 +2.2 | -2.9 -3.1 -2.3 -1.0 +0.4 +1.5 +2.3 |
| `w_food_ppi_yoy` | PPI/input | 0 | -7.5 | 0.000 | -8.5 | -1.0 | -7.5 -4.5 -2.5 -0.8 +0.9 +2.3 +3.5 | -1.0 -0.6 +0.2 +1.1 +1.8 +2.2 +2.8 |
| `se_cpi_idx__yoy` | CPI | 0 | -7.4 | 0.000 | -9.3 | -2.3 | -7.4 -4.6 -2.5 -1.1 +0.3 +1.8 +3.1 | -2.3 -1.5 +0.0 +1.6 +2.5 +2.7 +3.2 |
| `eu_ppi_dom_c105_idx__yoy` | PPI/input | 0 | -6.3 | 0.000 | -5.9 | -3.6 | -6.3 -3.9 -1.9 -0.5 +0.8 +2.2 +3.8 | -3.6 -2.7 -0.7 +0.7 +1.5 +2.3 +3.4 |
| `se_real_wage_yoy_q__lvl` | wages/inc. | 0 | +6.1 | 0.000 | +7.4 | +2.1 | +6.1 +3.4 +1.7 +0.3 -1.0 -2.3 -3.7 | +2.1 +0.5 -0.9 -2.1 -2.4 -2.8 -3.4 |
| `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 2 | -6.1 | 0.000 | -4.9 | -1.0 | -3.5 -5.1 -6.1 -5.1 -3.6 -1.9 +0.3 | +1.8 -0.3 -1.0 -1.0 -0.4 +1.5 +2.2 |
| `eu_ppi_dom_food_mfg_idx__yoy` | PPI/input | 0 | -5.7 | 0.000 | -6.3 | -1.5 | -5.7 -4.2 -2.7 -1.4 -0.1 +1.5 +3.1 | -1.5 -1.5 -0.5 +0.3 +1.2 +2.0 +3.0 |
| `eu_ppi_dom_c103_idx__dyoy` | PPI/input | 1 | -5.7 | 0.000 | -4.4 | -5.0 | -5.1 -5.7 -5.2 -2.5 -0.1 +1.2 +2.1 | -3.5 -5.0 -3.9 -1.4 +0.3 +1.3 +2.2 |
| `w_gov10y_d4` | rates | 1 | -5.4 | 0.000 | -5.1 | -2.9 | -4.0 -5.4 -5.3 -4.3 -3.0 -1.5 +0.3 | -2.2 -2.9 -2.9 -2.7 -1.8 -0.5 +1.2 |
| `eu_ppi_dom_c107_idx__yoy` | PPI/input | 0 | -5.4 | 0.000 | -7.1 | -2.1 | -5.4 -2.5 -1.0 +0.4 +2.2 +3.8 +4.4 | -2.1 -0.4 +1.0 +1.9 +2.7 +3.6 +4.3 |

### d_og_r4 (rolling-4Q organic-growth change, pp)

130 features have a BY-significant best lag. Distribution of best k among them: {0: 30, 1: 7, 2: 25, 3: 14, 4: 13, 5: 12, 6: 29}.

| feature | cat | best k | t best | q BY (lag family) | t +own lag | t +base | t ex-infl | t by k=0..6 | t ex-infl by k=0..6 |
|---|---|---|---|---|---|---|---|---|---|
| `eu_ppi_dom_c106_idx__dyoy` | PPI/input | 2 | +8.8 | 0.000 | +9.8 | +5.1 | +7.3 | +3.2 +6.2 +8.8 +6.0 +3.2 +1.5 +0.3 | +2.5 +4.8 +7.3 +6.8 +3.9 +1.8 +0.5 |
| `eu_ppi_dom_c107_idx__dyoy` | PPI/input | 0 | +8.3 | 0.000 | +8.9 | +3.2 | +7.8 | +8.3 +5.5 +3.7 +1.9 +0.7 -0.3 -1.6 | +7.8 +7.7 +6.8 +3.1 +1.0 -0.2 -1.6 |
| `se_real_wage_yoy_q__lvl` | wages/inc. | 6 | +8.1 | 0.000 | +2.8 | +1.5 | +8.7 | -1.9 -1.0 -0.3 +0.2 +1.2 +2.8 +8.1 | -1.8 -0.9 -0.3 +0.2 +1.3 +3.2 +8.7 |
| `eu_ppi_dom_food_mfg_idx__dyoy` | PPI/input | 0 | +7.6 | 0.000 | +7.8 | +2.5 | +5.3 | +7.6 +7.0 +4.8 +2.5 +1.0 +0.1 -0.9 | +5.3 +7.3 +6.9 +3.5 +1.4 +0.3 -0.7 |
| `w_ec_cons_price_exp_d4` | price exp. | 3 | +7.6 | 0.000 | +6.8 | +2.8 | +7.4 | -0.7 +1.4 +4.1 +7.6 +7.2 +4.9 +2.9 | -1.2 +0.6 +3.2 +7.4 +8.0 +5.8 +3.8 |
| `eu_agri_wheat_bread_price__yoy` | commod. | 3 | +9.9 | 0.000 | +9.8 | +0.9 |  | +3.5 +5.2 +7.5 +9.9 +9.7 +5.5 +1.4 | na na na na na na na |
| `ea_ec_food_ind_sell_price_exp__d4` | price exp. | 3 | +7.4 | 0.000 | +7.4 | +3.6 | +6.8 | +0.5 +2.5 +6.1 +7.4 +5.7 +3.5 +1.6 | -1.1 +1.3 +4.1 +6.8 +7.0 +5.5 +2.8 |
| `w_cons_conf_z_d4` | cons. survey | 0 | -7.4 | 0.000 | -6.5 | -5.9 | -6.5 | -7.4 -5.9 -3.0 -0.7 +0.5 +2.1 +3.9 | -6.5 -6.7 -4.5 -1.8 -0.4 +1.4 +3.6 |
| `price_cost_gap_ppi` | gap/spread | 0 | -7.2 | 0.000 | -6.3 | -3.0 | -4.6 | -7.2 -6.3 -3.5 -1.5 -0.1 +1.2 +2.5 | -4.6 -4.1 -2.6 -1.2 -0.0 +1.0 +2.1 |
| `se_cpi_idx__dyoy` | CPI | 1 | +7.1 | 0.000 | +6.8 | +3.5 | +5.6 | +4.5 +7.1 +5.0 +3.2 +1.9 +0.9 +0.1 | +2.2 +5.6 +7.5 +5.5 +2.6 +1.2 +0.2 |
| `nw_price_cost_gap_ppi` | gap/spread | 0 | -7.1 | 0.000 | -6.6 | -3.6 | -4.7 | -7.1 -6.2 -3.4 -1.4 +0.1 +1.5 +2.5 | -4.7 -4.2 -2.6 -1.0 +0.2 +1.3 +2.2 |
| `w_gdp_vol_dyoy` | activity | 3 | +6.9 | 0.000 | +5.1 | +2.5 | +3.9 | -1.2 +0.7 +3.9 +6.9 +4.5 +2.8 +1.3 | -1.5 +0.1 +2.1 +3.9 +5.9 +7.2 +5.3 |

### vol_proxy (implied volume/mix = og - Orkla-weighted food CPI ex VAT, pp)

4 features have a BY-significant best lag. Distribution of best k among them: {0: 4}.

| feature | cat | best k | t best | q BY (lag family) | t +own lag | t ex-infl | t by k=0..6 | t ex-infl by k=0..6 |
|---|---|---|---|---|---|---|---|---|
| `w_food_ppi_yoy` | PPI/input | 0 | -5.5 | 0.003 | -5.4 | -1.2 | -5.5 -3.5 -2.1 -1.2 -0.4 -0.1 -0.3 | -1.2 -0.7 -0.5 -0.1 +0.2 -0.1 -0.6 |
| `nw_food_cpi_xvat_yoy` | CPI | 0 | -5.3 | 0.003 | -5.5 | -1.5 | -5.3 -3.3 -2.0 -1.1 +0.7 +1.3 +0.9 | -1.5 -0.7 +0.3 +0.2 +0.8 +0.5 -0.0 |
| `se_cpi_food_idx__yoy` | CPI | 0 | -5.1 | 0.006 | -4.8 | -1.5 | -5.1 -3.9 -2.6 -1.5 -0.5 +0.6 +0.8 | -1.5 -0.9 -0.7 -0.4 +0.2 +0.2 +0.2 |
| `nw_food_cpi_yoy` | CPI | 0 | -5.0 | 0.006 | -5.2 | -1.2 | -5.0 -3.3 -2.1 -1.3 +0.3 +1.1 +0.8 | -1.2 -0.8 +0.1 -0.0 +0.3 +0.1 -0.1 |
| `w_food_cpi_yoy` | CPI | 0 | -4.2 | 0.106 | -4.5 | -1.4 | -4.2 -2.5 -1.6 -0.5 +0.7 +0.7 -0.1 | -1.4 -0.5 -0.3 +0.1 +0.1 -0.2 -0.8 |
| `no_retail_foodstores_vol_sa_idx__dyoy` | activity | 3 | +4.2 | 0.106 | +3.8 | +0.4 | -1.3 +0.4 +2.0 +4.2 +3.0 +1.7 +0.1 | +0.5 +0.5 +0.1 +0.4 -0.7 -2.3 -4.9 |
| `w_food_cpi_xvat_yoy` | CPI | 0 | -4.2 | 0.106 | -4.5 | -1.4 | -4.2 -2.5 -1.5 -0.3 +0.9 +0.7 +0.1 | -1.4 -0.4 -0.2 +0.4 +0.3 -0.1 -0.6 |
| `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 2 | -4.1 | 0.159 | -4.2 | -1.2 | -1.1 -2.4 -4.1 -2.5 -1.4 -0.9 -0.1 | -1.2 -1.4 -1.2 +0.0 +1.0 +0.9 +1.0 |
| `nw_food_ppi_yoy` | PPI/input | 0 | -3.9 | 0.159 | -4.2 | +0.2 | -3.9 -2.8 -1.9 -1.0 -0.2 +0.1 -0.3 | +0.2 +0.2 -0.1 +0.2 +0.3 -0.0 -0.5 |
| `nw_food_cpi_xvat_dyoy` | CPI | 0 | -3.9 | 0.159 | -3.4 | -1.7 | -3.9 -3.2 -2.0 -0.9 +0.7 +2.2 +2.2 | -1.7 -0.9 +0.2 +0.6 +1.6 +1.9 +1.5 |
| `w_food_cpi_rel_yoy` | CPI | 0 | -3.8 | 0.218 | -3.7 | -1.4 | -3.8 -2.9 -1.0 +0.8 +1.3 +1.3 +0.5 | -1.4 -0.7 -0.7 -0.0 -0.1 -0.2 -0.8 |
| `glob_gscpi__d4` | packaging | 0 | +3.6 | 0.362 | +4.1 | +1.0 | +3.6 +2.5 +1.6 -1.1 -0.8 -0.0 +0.4 | +1.0 -0.1 -0.4 -1.7 -0.7 +0.2 +0.9 |

**Reading the d_margin profile**
- Cost and price variables run from negative at k = 0-2 to positive at k = 4-6 (see `figures/lagprofile_d_margin.png`).
- This is a pass-through cycle with a turning point after about 3-4 quarters.
- For forecasting d_margin 4-6 quarters ahead, the level of food-PPI and CPI inflation 5-7 quarters back is the most useful single input in the core set.

**Reading the d_og profile**
- Price levels switch sign between k = 0 (positive: current pricing) and k = 4-6 (negative: base effect).
- Price accelerations (dyoy) and expectation changes (d4) peak at k = 1-3.

## 5. Ranked tables per target and alignment (core family, top 15 by HAC p-value)

**Columns**
- `b x 1sd`: target change per 1-sd move in the feature.
- `t lev`: leverage-adjusted HAC t.
- `q BY`: Benjamini-Yekutieli q within the target x alignment family (about 200 tests).
- `t +own lag`: incremental t with the real-time own lag.
- `t +base`: incremental t with og_{t-L} (d_og and d_og_r4 only).
- `flags`: S = sign-stable, R = robust.

Every table is followed by the top 10 when ranked on the sample **excluding 2021Q3-2023Q4**, where `*` marks BY q < 0.10 within that family. Full results, including Spearman, the n of each sub-sample and Holm p, are in `screen_results_core.csv`.

### d_margin (EBIT-margin change y/y, pp)

Significance counts:

| family | alignment | tests | q_BY<0.10 | q_BY(lev)<0.10 | q_BY ex-infl<0.10 | q_BY +own lag<0.10 | robust |
|---|---|---|---|---|---|---|---|
| core | coin | 200 | 26 | 20 | 0 | 38 | 16 |
| core | rt0 | 200 | 16 | 15 | 2 | 28 | 12 |
| core | rt1 | 198 | 12 | 3 | 2 | 31 | 2 |
| core | rt2 | 198 | 0 | 0 | 1 | 10 | 0 |
| core | rt4 | 198 | 0 | 0 | 11 | 0 | 0 |
| all | coin | 1408 | 127 | 86 | 15 | 229 | 62 |
| all | rt0 | 1408 | 67 | 52 | 2 | 156 | 38 |
| all | rt1 | 1406 | 18 | 11 | 4 | 157 | 5 |
| all | rt2 | 1406 | 13 | 1 | 4 | 93 | 0 |
| all | rt4 | 1402 | 1 | 1 | 6 | 1 | 0 |

#### d_margin, coincident (same quarter, not real-time)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `packaging_eu_yoy` | packaging | 102 | -0.49 | -0.36 | -0.59 | -9.6 | -9.1 | 0.000 | -6.9 | -2.2 | -9.2 | -3.1 | -7.5 | SR |
| 2 | `eu_ppi_plastic_products_idx__yoy` | packaging | 102 | -0.47 | -0.33 | -0.57 | -8.6 | -7.9 | 0.000 | -7.0 | -2.0 | -8.3 | -2.6 | -5.7 | SR |
| 3 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 102 | -0.49 | -0.35 | -0.58 | -8.4 | -8.0 | 0.000 | -6.1 | -2.1 | -8.4 | -2.8 | -7.2 | SR |
| 4 | `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 64 | -0.49 | -0.29 | -0.62 | -5.3 | -4.8 | 0.000 | -4.8 |  | -5.0 | -1.1 | -4.7 |  |
| 5 | `w_gov10y_d4` | rates | 102 | -0.54 | -0.47 | -0.64 | -5.1 | -4.9 | 0.000 | -4.7 | -2.6 | -4.5 | -3.1 | -4.7 | SR |
| 6 | `no_govbond_10y__d4` | rates | 102 | -0.57 | -0.52 | -0.69 | -4.9 | -4.7 | 0.001 | -4.6 | -3.3 | -4.0 | -3.6 | -4.3 | SR |
| 7 | `no_retail_foodstores_vol_sa_idx__dyoy` | activity | 98 | +0.32 | +0.15 | +0.39 | +4.8 | +4.5 | 0.001 | +3.5 | -1.6 | +7.3 | +2.8 | +1.8 |  |
| 8 | `ea_ec_food_ind_sell_price_exp__lvl` | price exp. | 102 | -0.44 | -0.27 | -0.53 | -4.7 | -4.4 | 0.001 | -4.9 | -1.5 | -5.7 | -1.4 | -3.3 | S |
| 9 | `se_cpi_idx__dyoy` | CPI | 102 | -0.47 | -0.43 | -0.57 | -4.2 | -4.0 | 0.007 | -3.7 | -1.9 | -4.3 | -3.5 | -4.0 | SR |
| 10 | `w_unemp_d4` | labour | 102 | +0.42 | +0.43 | +0.51 | +4.2 | +4.0 | 0.008 | +5.0 | +2.6 | +3.2 | +3.2 | +3.6 | SR |
| 11 | `no_qna_hh_food_cons_sa_mnok__dyoy` | activity | 102 | +0.41 | +0.29 | +0.49 | +4.1 | +3.9 | 0.008 | +3.7 | -1.2 | +6.3 | +2.0 | +2.5 |  |
| 12 | `nw_retail_food_vol_dyoy` | activity | 98 | +0.41 | +0.32 | +0.50 | +4.1 | +3.9 | 0.008 | +3.4 | +0.4 | +5.3 | +2.5 | +2.4 | SR |
| 13 | `se_gov_bond_10y__d4` | rates | 102 | -0.47 | -0.42 | -0.57 | -4.1 | -3.9 | 0.009 | -3.8 | -2.3 | -3.5 | -2.9 | -3.9 | SR |
| 14 | `eu_agri_basket_yoy` | commod. | 102 | -0.48 | -0.36 | -0.58 | -4.0 | -3.8 | 0.009 | -3.7 | -1.5 | -4.2 | -2.4 | -3.6 | SR |
| 15 | `eu_agri_basket_wloc_yoy` | commod. | 102 | -0.49 | -0.34 | -0.59 | -3.9 | -3.7 | 0.013 | -3.7 | -1.4 | -4.2 | -2.1 | -3.7 | SR |

#### d_margin, real-time nowcast h=0 (info at quarter end, before report)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_plastic_products_idx__yoy` | packaging | 101 | -0.47 | -0.38 | -0.57 | -8.8 | -8.3 | 0.000 | -7.7 | -2.4 | -8.2 | -3.0 | -7.6 | SR |
| 2 | `packaging_eu_yoy` | packaging | 101 | -0.46 | -0.36 | -0.55 | -5.8 | -5.4 | 0.000 | -5.6 | -2.3 | -5.2 | -3.0 | -5.8 | SR |
| 3 | `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 64 | -0.49 | -0.29 | -0.62 | -5.3 | -4.8 | 0.001 | -4.8 |  | -5.0 | -1.1 | -4.7 |  |
| 4 | `w_gov10y_d4` | rates | 102 | -0.54 | -0.47 | -0.64 | -5.1 | -4.9 | 0.001 | -4.7 | -2.6 | -4.5 | -3.1 | -4.7 | SR |
| 5 | `no_govbond_10y__d4` | rates | 102 | -0.57 | -0.52 | -0.69 | -4.9 | -4.7 | 0.001 | -4.6 | -3.3 | -4.0 | -3.6 | -4.3 | SR |
| 6 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 101 | -0.43 | -0.32 | -0.52 | -4.7 | -4.3 | 0.002 | -4.7 | -2.2 | -4.1 | -2.7 | -4.7 | SR |
| 7 | `ea_ec_food_ind_sell_price_exp__lvl` | price exp. | 102 | -0.44 | -0.27 | -0.53 | -4.7 | -4.4 | 0.002 | -4.9 | -1.5 | -5.7 | -1.4 | -3.3 | S |
| 8 | `se_cpi_idx__dyoy` | CPI | 102 | -0.47 | -0.43 | -0.57 | -4.2 | -4.0 | 0.008 | -3.7 | -1.9 | -4.3 | -3.5 | -4.0 | SR |
| 9 | `se_real_wage_yoy_q__d4` | wages/inc. | 102 | +0.41 | +0.37 | +0.50 | +4.2 | +4.0 | 0.008 | +3.8 | +2.3 | +3.7 | +4.1 | +4.0 | SR |
| 10 | `us_ppi_corrugated_boxes_idx__yoy` | packaging | 102 | -0.45 | -0.36 | -0.54 | -4.1 | -3.9 | 0.010 | -3.8 | -1.7 | -5.4 | -2.5 | -3.4 | SR |
| 11 | `se_gov_bond_10y__d4` | rates | 102 | -0.47 | -0.42 | -0.57 | -4.1 | -3.9 | 0.010 | -3.8 | -2.3 | -3.5 | -2.9 | -3.9 | SR |
| 12 | `nw_retail_food_vol_dyoy` | activity | 97 | +0.38 | +0.26 | +0.47 | +4.1 | +3.9 | 0.010 | +3.5 | +0.6 | +5.2 | +2.5 | +2.9 | SR |
| 13 | `no_ssb_bts_consgoods_home_price_exp__d4` | price exp. | 102 | -0.41 | -0.32 | -0.49 | -4.0 | -3.9 | 0.010 | -3.5 | -2.7 | -2.6 | -2.2 | -4.2 | SR |
| 14 | `eu_ppi_dom_c103_idx__dyoy` | PPI/input | 97 | -0.32 | -0.26 | -0.39 | -3.6 | -3.4 | 0.045 | -4.6 | -2.5 | -2.8 | -3.4 | -3.9 | SR |
| 15 | `w_retail_food_vol_dyoy` | activity | 97 | +0.37 | +0.23 | +0.45 | +3.6 | +3.4 | 0.045 | +3.4 | -0.0 | +5.9 | +1.7 | +2.7 |  |

#### d_margin, real-time h=1 (1 quarter ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_plastic_products_idx__yoy` | packaging | 100 | -0.41 | -0.32 | -0.49 | -4.4 | -4.0 | 0.028 | -5.9 | -1.4 | -4.1 | -1.9 | -4.4 | S |
| 2 | `no_govbond_10y__d4` | rates | 102 | -0.49 | -0.42 | -0.59 | -4.1 | -3.9 | 0.041 | -4.3 | -2.9 | -3.5 | -2.7 | -3.7 | SR |
| 3 | `us_ppi_corrugated_boxes_idx__yoy` | packaging | 102 | -0.45 | -0.36 | -0.54 | -4.0 | -3.9 | 0.041 | -3.9 | -1.9 | -4.2 | -2.4 | -3.8 | SR |
| 4 | `w_gov10y_d4` | rates | 102 | -0.46 | -0.40 | -0.56 | -3.7 | -3.6 | 0.068 | -4.6 | -2.4 | -3.4 | -2.7 | -3.5 | S |
| 5 | `ea_ec_food_ind_sell_price_exp__lvl` | price exp. | 102 | -0.36 | -0.20 | -0.43 | -3.7 | -3.4 | 0.068 | -4.5 | -1.4 | -5.1 | -1.2 | -3.4 | S |
| 6 | `se_cpi_idx__dyoy` | CPI | 102 | -0.38 | -0.36 | -0.45 | -3.7 | -3.5 | 0.068 | -4.1 | -1.9 | -3.2 | -3.1 | -3.5 | S |
| 7 | `se_real_wage_yoy_q__d4` | wages/inc. | 102 | +0.32 | +0.31 | +0.39 | +3.6 | +3.4 | 0.074 | +4.7 | +3.2 | +2.2 | +3.4 | +3.6 | S |
| 8 | `us_ppi_corrugated_boxes_idx__dyoy` | packaging | 102 | -0.44 | -0.41 | -0.53 | -3.6 | -3.5 | 0.074 | -3.4 | -2.2 | -3.1 | -2.9 | -3.3 | S |
| 9 | `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 63 | -0.44 | -0.36 | -0.56 | -3.6 | -3.2 | 0.074 | -3.7 |  | -3.0 | -1.4 | -3.8 |  |
| 10 | `w_gdp_vol_dyoy` | activity | 102 | -0.28 | -0.23 | -0.33 | -3.5 | -3.1 | 0.074 | -3.2 | -2.7 | -2.6 | -2.1 | -2.7 | S |
| 11 | `no_ssb_bts_consgoods_home_price_exp__d4` | price exp. | 102 | -0.42 | -0.29 | -0.50 | -3.5 | -3.3 | 0.074 | -3.9 | -2.2 | -2.9 | -2.2 | -3.4 | S |
| 12 | `eu_ppi_plastic_products_idx__dyoy` | packaging | 96 | -0.42 | -0.40 | -0.52 | -3.4 | -3.1 | 0.098 | -2.8 | -3.4 | -3.2 | -5.7 | -3.2 | S |
| 13 | `se_gov_bond_10y__d4` | rates | 102 | -0.42 | -0.38 | -0.50 | -3.2 | -3.1 | 0.161 | -4.0 | -2.0 | -2.9 | -2.5 | -3.0 | S |
| 14 | `natgas_eu_eur_yoy` | energy | 91 | -0.36 | -0.25 | -0.45 | -3.2 | -2.9 | 0.167 | -2.7 | +0.7 | -5.0 | -1.1 | -2.0 |  |
| 15 | `packaging_eu_dyoy` | packaging | 96 | -0.43 | -0.43 | -0.52 | -3.1 | -2.8 | 0.167 | -2.7 | -2.6 | -2.9 | -4.1 | -3.0 | S |

#### d_margin, real-time h=2 (2 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_plastic_products_idx__dyoy` | packaging | 95 | -0.38 | -0.29 | -0.47 | -3.7 | -3.3 | 0.304 | -3.1 | -2.5 | -3.9 | -4.8 | -3.5 | S |
| 2 | `packaging_eu_dyoy` | packaging | 95 | -0.36 | -0.33 | -0.44 | -3.4 | -3.2 | 0.304 | -3.2 | -2.4 | -3.2 | -3.5 | -3.3 | S |
| 3 | `natgas_eu_eur_yoy` | energy | 90 | -0.37 | -0.23 | -0.46 | -3.4 | -3.2 | 0.304 | -3.0 | +0.5 | -5.6 | -1.1 | -2.6 |  |
| 4 | `eu_ppi_paper_packaging_idx__dyoy` | packaging | 95 | -0.32 | -0.30 | -0.40 | -3.3 | -3.2 | 0.304 | -3.3 | -1.8 | -2.9 | -2.8 | -3.2 | S |
| 5 | `us_ppi_corrugated_boxes_idx__dyoy` | packaging | 102 | -0.44 | -0.37 | -0.53 | -3.3 | -3.2 | 0.304 | -3.1 | -1.8 | -3.0 | -2.6 | -3.1 | S |
| 6 | `w_ec_food_retail_sell_price_exp_d4` | price exp. | 58 | -0.49 | -0.37 | -0.64 | -3.3 | -3.0 | 0.304 | -3.0 |  | -3.3 | -2.8 | -3.2 |  |
| 7 | `no_ssb_bts_consgoods_home_price_exp__d4` | price exp. | 102 | -0.34 | -0.23 | -0.40 | -3.2 | -2.9 | 0.308 | -3.3 | -1.5 | -4.2 | -2.4 | -3.1 | S |
| 8 | `ea_ec_food_ind_sell_price_exp__d4` | price exp. | 102 | -0.37 | -0.27 | -0.44 | -3.0 | -2.8 | 0.515 | -2.8 | -1.6 | -3.0 | -2.4 | -3.0 | S |
| 9 | `us_ppi_corrugated_boxes_idx__yoy` | packaging | 102 | -0.36 | -0.27 | -0.43 | -2.9 | -2.7 | 0.603 | -3.3 | -1.7 | -2.2 | -1.8 | -3.0 | S |
| 10 | `no_nbes_bl_sell_price_di__d4` | price exp. | 92 | -0.42 | -0.46 | -0.51 | -2.8 | -2.6 | 0.603 | -3.1 | -2.1 | -2.7 | -2.4 | -2.7 | S |
| 11 | `eu_agri_wheat_bread_price__yoy` | commod. | 36 | -0.60 | -0.47 | -0.73 | -3.0 | -2.6 | 0.603 | -3.0 |  | -3.0 |  |  |  |
| 12 | `se_cpi_idx__dyoy` | CPI | 102 | -0.27 | -0.29 | -0.33 | -2.8 | -2.6 | 0.670 | -4.7 | -2.4 | -1.9 | -2.1 | -2.8 | S |
| 13 | `w_ec_food_ind_sell_price_exp_d4` | price exp. | 102 | -0.32 | -0.24 | -0.39 | -2.7 | -2.6 | 0.672 | -3.1 | -1.4 | -3.0 | -2.1 | -2.8 | S |
| 14 | `w_gdp_vol_dyoy` | activity | 102 | -0.27 | -0.26 | -0.32 | -2.7 | -2.5 | 0.753 | -2.7 | -3.3 | -1.3 | -2.0 | -4.6 | S |
| 15 | `eu_ppi_dom_food_mfg_idx__dyoy` | PPI/input | 95 | -0.22 | -0.18 | -0.27 | -2.6 | -2.5 | 0.753 | -4.1 | -1.1 | -2.7 | -1.9 | -2.9 | S |

#### d_margin, real-time h=4 (4 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_dom_c103_idx__yoy` | PPI/input | 97 | +0.29 | +0.33 | +0.35 | +3.7 | +3.6 | 0.237 | +3.1 | +2.6 | +2.5 | +4.8 | +3.8 | S |
| 2 | `se_na_hhcons_food_sa__yoy` | activity | 102 | -0.33 | -0.28 | -0.40 | -3.7 | -3.5 | 0.237 | -3.2 | -1.6 | -3.8 | -3.6 | -3.3 | S |
| 3 | `eu_ppi_dom_c107_idx__yoy` | PPI/input | 97 | +0.25 | +0.32 | +0.31 | +3.5 | +3.3 | 0.237 | +2.8 | +2.5 | +2.8 | +5.6 | +3.7 | S |
| 4 | `glob_gscpi__lvl` | packaging | 102 | -0.35 | -0.14 | -0.42 | -3.3 | -3.0 | 0.364 | -3.8 | +0.3 | -3.7 | -1.0 | -2.6 |  |
| 5 | `se_retail_grocery_vol_sa_idx__yoy` | activity | 102 | -0.35 | -0.28 | -0.42 | -3.3 | -3.1 | 0.364 | -3.1 | -2.9 | -4.2 | -3.6 | -3.3 | S |
| 6 | `glob_gscpi__d4` | packaging | 102 | -0.36 | -0.27 | -0.43 | -3.2 | -3.0 | 0.393 | -2.6 | -1.1 | -3.2 | -3.1 | -2.5 | S |
| 7 | `ea_hicp_food_idx__yoy` | CPI | 97 | +0.21 | +0.22 | +0.25 | +3.1 | +2.9 | 0.416 | +2.1 | +1.6 | +2.5 | +3.8 | +3.2 | S |
| 8 | `ea_negotiated_wages_yoy_q__d4` | wages/inc. | 102 | +0.26 | +0.30 | +0.31 | +3.0 | +2.8 | 0.447 | +2.5 | +2.1 | +2.2 | +2.7 | +2.8 | S |
| 9 | `glob_wb_food_idx_eur__dyoy` | commod. | 98 | -0.29 | -0.26 | -0.36 | -3.0 | -2.9 | 0.447 | -2.8 | -2.3 | -2.4 | -2.6 | -3.0 | S |
| 10 | `elec_nordic_loc_dyoy` | energy | 96 | -0.37 | -0.30 | -0.45 | -2.9 | -2.8 | 0.447 | -2.7 | -1.8 | -2.3 | -2.2 | -3.6 | S |
| 11 | `eu_agri_wheat_bread_price__dyoy` | commod. | 30 | -0.41 | -0.48 | -0.54 | -3.1 | -2.9 | 0.447 | -3.5 |  | -3.1 |  |  |  |
| 12 | `w_unemp_lvl` | labour | 102 | -0.28 | -0.34 | -0.34 | -2.9 | -2.8 | 0.447 | -2.4 | -1.4 | -3.2 | -2.5 | -2.7 | S |
| 13 | `glob_fao_vegoils_idx__dyoy` | commod. | 102 | -0.23 | -0.22 | -0.27 | -2.9 | -2.8 | 0.447 | -2.9 | -3.0 | -1.3 | -2.5 | -2.7 | S |
| 14 | `natgas_eu_eur_dyoy` | energy | 76 | -0.37 | -0.31 | -0.45 | -2.9 | -2.6 | 0.447 | -2.6 | +0.5 | -3.3 | -2.1 | -2.6 |  |
| 15 | `se_ppi_food_hmpi_idx__yoy` | PPI/input | 102 | +0.24 | +0.26 | +0.29 | +2.8 | +2.6 | 0.447 | +2.5 | +2.1 | +2.1 | +3.6 | +2.7 | S |

#### d_margin: top 10 per alignment on the sample excluding 2021Q3-2023Q4 (ex-infl HAC t)

| # | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| 1 | `no_govbond_10y__d4` -3.6 | `se_real_wage_yoy_q__d4` +4.1* | `eu_ppi_plastic_products_idx__dyoy` -5.7* | `eu_ppi_plastic_products_idx__dyoy` -4.8* | `eu_ppi_dom_c107_idx__yoy` +5.6* |
| 2 | `se_cpi_idx__dyoy` -3.5 | `eu_ppi_plastic_products_idx__dyoy` -4.0* | `packaging_eu_dyoy` -4.1* | `packaging_eu_dyoy` -3.5 | `eu_ppi_dom_c103_idx__yoy` +4.8* |
| 3 | `se_real_wage_yoy_q__d4` +3.4 | `no_govbond_10y__d4` -3.6 | `eu_ppi_paper_packaging_idx__dyoy` -3.5 | `w_food_cpi_yoy` +3.2 | `w_cpi_yoy` +4.3* |
| 4 | `w_gdp_vol_yoy` -3.4 | `se_cpi_idx__dyoy` -3.5 | `se_real_wage_yoy_q__d4` +3.4 | `no_cpi_food_idx__yoy` +3.1 | `ea_hicp_food_idx__yoy` +3.8* |
| 5 | `w_unemp_d4` +3.2 | `eu_ppi_dom_c103_idx__dyoy` -3.4 | `nw_food_cpi_yoy` +3.2 | `nw_food_cpi_yoy` +3.1 | `se_retail_grocery_vol_sa_idx__yoy` -3.6* |
| 6 | `eu_ppi_dom_c103_idx__dyoy` -3.1 | `packaging_eu_dyoy` -3.4 | `se_cpi_idx__dyoy` -3.1 | `w_hh_saving_d4` -3.1 | `se_cpi_idx__yoy` +3.6* |
| 7 | `w_gov10y_d4` -3.1 | `eu_ppi_paper_packaging_idx__dyoy` -3.1 | `price_wage_gap` +3.1 | `w_retail_total_vol_yoy` -3.0 | `nw_food_ppi_yoy` +3.6* |
| 8 | `packaging_eu_yoy` -3.1 | `w_gov10y_d4` -3.1 | `no_cpi_food_idx__yoy` +3.0 | `se_ec_cons_conf__lvl` -3.0 | `se_na_hhcons_food_sa__yoy` -3.6* |
| 9 | `eu_ppi_dom_c106_idx__dyoy` -3.0 | `eu_ppi_plastic_products_idx__yoy` -3.0 | `us_ppi_corrugated_boxes_idx__dyoy` -2.9 | `eu_ppi_paper_packaging_idx__dyoy` -2.8 | `se_ppi_food_hmpi_idx__yoy` +3.6* |
| 10 | `se_gov_bond_10y__d4` -2.9 | `packaging_eu_yoy` -3.0 | `w_cons_conf_z` -2.8 | `w_cons_conf_z` -2.8 | `se_real_wage_yoy_q__lvl` -3.6* |

Figures: `figures/top10_d_margin_coincident.png`, `figures/top10_d_margin_realtime.png`, `figures/lagprofile_d_margin.png`.

### og (organic growth, %)

Significance counts:

| family | alignment | tests | q_BY<0.10 | q_BY(lev)<0.10 | q_BY ex-infl<0.10 | q_BY +own lag<0.10 | robust |
|---|---|---|---|---|---|---|---|
| core | coin | 200 | 33 | 31 | 3 | 36 | 12 |
| core | rt0 | 200 | 39 | 37 | 3 | 42 | 15 |
| core | rt1 | 198 | 44 | 40 | 1 | 47 | 19 |
| core | rt2 | 198 | 33 | 22 | 0 | 49 | 9 |
| core | rt4 | 198 | 3 | 3 | 1 | 2 | 2 |
| all | coin | 1408 | 169 | 144 | 3 | 193 | 58 |
| all | rt0 | 1408 | 165 | 143 | 2 | 184 | 55 |
| all | rt1 | 1406 | 159 | 125 | 1 | 178 | 51 |
| all | rt2 | 1406 | 102 | 64 | 7 | 138 | 23 |
| all | rt4 | 1402 | 28 | 22 | 21 | 44 | 14 |

#### og, coincident (same quarter, not real-time)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `se_cpi_food_idx__yoy` | CPI | 102 | +0.53 | +0.40 | +1.73 | +11.5 | +11.0 | 0.000 | +11.7 | +4.1 | +10.1 | +3.5 | +10.6 | SR |
| 2 | `no_ppi_food_dom_idx__yoy` | PPI/input | 102 | +0.51 | +0.38 | +1.70 | +9.1 | +8.5 | 0.000 | +8.5 | +0.7 | +8.2 | +1.6 | +8.7 | S |
| 3 | `w_food_cpi_yoy` | CPI | 102 | +0.50 | +0.31 | +1.68 | +8.6 | +8.0 | 0.000 | +8.9 | +3.2 | +8.8 | +2.1 | +8.3 | SR |
| 4 | `w_food_cpi_xvat_yoy` | CPI | 102 | +0.52 | +0.38 | +1.71 | +8.5 | +7.8 | 0.000 | +8.7 | +4.7 | +8.6 | +2.6 | +8.2 | SR |
| 5 | `ea_hicp_food_idx__yoy` | CPI | 102 | +0.56 | +0.41 | +1.84 | +8.4 | +8.0 | 0.000 | +8.4 | +7.1 | +7.8 | +2.9 | +8.3 | SR |
| 6 | `w_food_ppi_yoy` | PPI/input | 102 | +0.54 | +0.37 | +1.75 | +8.2 | +7.1 | 0.000 | +7.5 | +2.2 | +7.1 | +1.9 | +8.2 | S |
| 7 | `nw_food_ppi_yoy` | PPI/input | 102 | +0.57 | +0.47 | +1.86 | +7.9 | +6.6 | 0.000 | +7.6 | +2.0 | +6.5 | +2.7 | +8.1 | SR |
| 8 | `eu_ppi_dom_c107_idx__yoy` | PPI/input | 102 | +0.53 | +0.37 | +1.75 | +7.9 | +7.6 | 0.000 | +7.7 | +6.1 | +7.3 | +2.0 | +8.5 | S |
| 9 | `se_ppi_food_hmpi_idx__yoy` | PPI/input | 102 | +0.56 | +0.45 | +1.84 | +7.6 | +7.3 | 0.000 | +7.6 | +3.3 | +5.7 | +2.6 | +7.8 | SR |
| 10 | `nw_food_cpi_xvat_yoy` | CPI | 102 | +0.48 | +0.40 | +1.59 | +7.5 | +7.1 | 0.000 | +7.9 | +3.5 | +5.3 | +2.7 | +9.9 | SR |
| 11 | `w_cpi_yoy` | CPI | 102 | +0.57 | +0.46 | +1.84 | +7.4 | +6.8 | 0.000 | +7.6 | +1.4 | +6.2 | +1.5 | +7.6 | S |
| 12 | `se_ec_cons_conf__lvl` | cons. survey | 102 | -0.55 | -0.49 | -1.82 | -7.3 | -6.9 | 0.000 | -7.5 | -3.9 | -5.2 | -2.9 | -8.4 | SR |
| 13 | `price_wage_gap` | gap/spread | 102 | +0.47 | +0.35 | +1.71 | +7.3 | +6.9 | 0.000 | +7.8 | +1.2 | +8.2 | +1.7 | +7.3 | S |
| 14 | `nw_cons_conf_z` | cons. survey | 102 | -0.56 | -0.53 | -1.86 | -7.2 | -6.9 | 0.000 | -7.8 | -3.2 | -5.0 | -3.2 | -7.5 | SR |
| 15 | `se_real_wage_yoy_q__lvl` | wages/inc. | 102 | -0.52 | -0.40 | -1.71 | -7.1 | -6.8 | 0.000 | -6.2 | -0.1 | -6.6 | -0.9 | -7.2 | S |

#### og, real-time nowcast h=0 (info at quarter end, before report)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `se_cpi_food_idx__yoy` | CPI | 102 | +0.53 | +0.40 | +1.73 | +11.5 | +11.0 | 0.000 | +11.7 | +4.1 | +10.1 | +3.5 | +10.6 | SR |
| 2 | `no_ppi_food_dom_idx__yoy` | PPI/input | 102 | +0.51 | +0.38 | +1.70 | +9.1 | +8.5 | 0.000 | +8.5 | +0.7 | +8.2 | +1.6 | +8.7 | S |
| 3 | `w_food_ppi_yoy` | PPI/input | 101 | +0.50 | +0.34 | +1.64 | +8.3 | +8.0 | 0.000 | +7.2 | +2.4 | +9.1 | +1.5 | +8.1 | S |
| 4 | `nw_food_ppi_yoy` | PPI/input | 101 | +0.53 | +0.45 | +1.73 | +8.3 | +7.7 | 0.000 | +7.7 | +2.2 | +8.3 | +2.4 | +8.2 | SR |
| 5 | `w_real_wage_yoy` | wages/inc. | 102 | -0.51 | -0.41 | -1.81 | -7.6 | -7.4 | 0.000 | -7.4 | -1.0 | -7.2 | -2.3 | -7.8 | SR |
| 6 | `nw_food_cpi_xvat_yoy` | CPI | 102 | +0.48 | +0.40 | +1.59 | +7.5 | +7.1 | 0.000 | +7.9 | +3.5 | +5.3 | +2.7 | +9.9 | SR |
| 7 | `eu_ppi_dom_c107_idx__yoy` | PPI/input | 101 | +0.51 | +0.35 | +1.67 | +7.4 | +7.0 | 0.000 | +7.0 | +6.0 | +6.8 | +2.7 | +7.7 | SR |
| 8 | `se_ec_cons_conf__lvl` | cons. survey | 102 | -0.55 | -0.49 | -1.82 | -7.3 | -6.9 | 0.000 | -7.5 | -3.9 | -5.2 | -2.9 | -8.4 | SR |
| 9 | `nw_cons_conf_z` | cons. survey | 102 | -0.56 | -0.53 | -1.86 | -7.2 | -6.9 | 0.000 | -7.8 | -3.2 | -5.0 | -3.2 | -7.5 | SR |
| 10 | `se_ppi_food_hmpi_idx__yoy` | PPI/input | 102 | +0.52 | +0.42 | +1.70 | +7.1 | +6.8 | 0.000 | +6.7 | +3.9 | +5.3 | +2.3 | +7.6 | SR |
| 11 | `se_cpi_idx__yoy` | CPI | 102 | +0.55 | +0.44 | +1.76 | +6.8 | +6.6 | 0.000 | +6.3 | +1.9 | +5.8 | +1.4 | +7.0 | S |
| 12 | `se_real_wage_yoy_q__lvl` | wages/inc. | 102 | -0.55 | -0.48 | -1.80 | -6.8 | -6.4 | 0.000 | -5.9 | -1.5 | -5.4 | -2.2 | -6.7 | SR |
| 13 | `nw_food_cpi_yoy` | CPI | 102 | +0.44 | +0.32 | +1.54 | +6.7 | +6.3 | 0.000 | +7.6 | +1.6 | +5.7 | +2.0 | +8.4 | S |
| 14 | `w_cpi_yoy` | CPI | 102 | +0.56 | +0.50 | +1.80 | +6.7 | +6.2 | 0.000 | +6.7 | +3.9 | +5.6 | +2.4 | +6.9 | SR |
| 15 | `price_wage_gap` | gap/spread | 102 | +0.43 | +0.32 | +1.54 | +6.7 | +6.3 | 0.000 | +7.1 | +1.2 | +8.2 | +1.6 | +7.1 | S |

#### og, real-time h=1 (1 quarter ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `se_cpi_food_idx__yoy` | CPI | 102 | +0.46 | +0.37 | +1.51 | +8.3 | +7.6 | 0.000 | +8.0 | +3.1 | +6.6 | +3.7 | +9.4 | SR |
| 2 | `no_ppi_food_dom_idx__yoy` | PPI/input | 101 | +0.47 | +0.32 | +1.58 | +7.5 | +7.1 | 0.000 | +6.7 | +0.3 | +8.3 | +1.2 | +6.8 | S |
| 3 | `nw_food_ppi_yoy` | PPI/input | 100 | +0.46 | +0.39 | +1.52 | +6.1 | +5.4 | 0.000 | +5.7 | +1.8 | +5.7 | +2.2 | +6.3 | SR |
| 4 | `w_food_ppi_yoy` | PPI/input | 100 | +0.44 | +0.30 | +1.46 | +6.1 | +5.5 | 0.000 | +5.5 | +2.1 | +6.1 | +1.5 | +6.1 | S |
| 5 | `se_cpi_idx__yoy` | CPI | 102 | +0.55 | +0.48 | +1.74 | +5.8 | +5.5 | 0.000 | +5.6 | +3.7 | +4.7 | +2.1 | +5.7 | SR |
| 6 | `se_ppi_food_hmpi_idx__yoy` | PPI/input | 102 | +0.47 | +0.40 | +1.55 | +5.6 | +5.2 | 0.000 | +5.4 | +3.0 | +4.9 | +2.3 | +5.6 | SR |
| 7 | `se_ec_cons_conf__lvl` | cons. survey | 102 | -0.49 | -0.43 | -1.62 | -5.5 | -5.1 | 0.000 | -5.8 | -3.2 | -3.3 | -3.2 | -7.7 | SR |
| 8 | `packaging_eu_yoy` | packaging | 100 | +0.49 | +0.30 | +1.60 | +5.4 | +5.1 | 0.000 | +5.4 | +2.1 | +6.8 | +0.6 | +5.3 | S |
| 9 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 100 | +0.49 | +0.39 | +1.59 | +5.4 | +5.1 | 0.000 | +5.1 | +2.4 | +6.4 | +0.9 | +5.3 | S |
| 10 | `w_ec_food_ind_sell_price_exp_lvl` | price exp. | 102 | +0.48 | +0.34 | +1.68 | +5.3 | +5.0 | 0.000 | +5.3 | +2.8 | +4.6 | +2.0 | +5.3 | SR |
| 11 | `nw_cons_conf_z` | cons. survey | 102 | -0.48 | -0.46 | -1.59 | -5.2 | -4.8 | 0.000 | -6.8 | -2.3 | -3.1 | -3.0 | -5.9 | SR |
| 12 | `eu_ppi_plastic_products_idx__yoy` | packaging | 100 | +0.45 | +0.15 | +1.53 | +5.0 | +4.7 | 0.000 | +5.6 | +1.2 | +7.8 | -0.2 | +4.9 |  |
| 13 | `se_wage_idx_m__dyoy` | wages/inc. | 102 | +0.38 | +0.38 | +1.32 | +5.0 | +4.8 | 0.000 | +4.9 | +3.4 | +2.8 | +4.2 | +4.4 | SR |
| 14 | `eu_ppi_dom_c107_idx__yoy` | PPI/input | 100 | +0.44 | +0.32 | +1.45 | +4.9 | +4.5 | 0.000 | +5.1 | +3.6 | +4.5 | +2.3 | +5.2 | SR |
| 15 | `w_cpi_yoy` | CPI | 102 | +0.50 | +0.45 | +1.62 | +4.7 | +4.3 | 0.001 | +4.7 | +3.2 | +4.0 | +1.8 | +4.8 | S |

#### og, real-time h=2 (2 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `no_ssb_bts_consgoods_home_price_exp__lvl` | price exp. | 102 | +0.54 | +0.49 | +1.82 | +6.0 | +5.7 | 0.000 | +5.7 | +3.5 | +4.4 | +2.8 | +5.6 | SR |
| 2 | `eu_ppi_plastic_products_idx__yoy` | packaging | 99 | +0.48 | +0.21 | +1.64 | +6.0 | +5.6 | 0.000 | +5.7 | +2.8 | +7.6 | +0.7 | +5.8 | S |
| 3 | `w_ec_food_ind_sell_price_exp_lvl` | price exp. | 102 | +0.49 | +0.38 | +1.71 | +5.7 | +5.4 | 0.000 | +5.4 | +3.5 | +5.1 | +2.4 | +5.1 | SR |
| 4 | `packaging_eu_yoy` | packaging | 99 | +0.51 | +0.37 | +1.67 | +5.6 | +5.3 | 0.000 | +5.1 | +4.0 | +6.1 | +1.6 | +5.4 | S |
| 5 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 99 | +0.51 | +0.45 | +1.64 | +5.3 | +4.9 | 0.000 | +4.8 | +3.8 | +5.5 | +1.9 | +5.2 | S |
| 6 | `no_ppi_food_dom_idx__yoy` | PPI/input | 100 | +0.39 | +0.22 | +1.31 | +4.8 | +4.3 | 0.001 | +4.5 | -0.3 | +5.3 | +0.7 | +5.2 |  |
| 7 | `ea_ec_food_ind_sell_price_exp__lvl` | price exp. | 102 | +0.48 | +0.33 | +1.61 | +4.2 | +4.0 | 0.007 | +4.2 | +2.7 | +4.2 | +0.9 | +4.1 | S |
| 8 | `se_nier_food_mfg_sell_price_exp__lvl` | price exp. | 102 | +0.47 | +0.38 | +1.65 | +4.2 | +4.0 | 0.007 | +4.3 | +2.2 | +4.1 | +2.7 | +4.1 | SR |
| 9 | `se_cpi_food_idx__yoy` | CPI | 102 | +0.33 | +0.21 | +1.12 | +4.1 | +3.8 | 0.012 | +4.1 | +1.4 | +3.3 | +1.9 | +4.6 | S |
| 10 | `se_cpi_idx__yoy` | CPI | 102 | +0.48 | +0.42 | +1.52 | +4.0 | +3.7 | 0.012 | +4.0 | +4.1 | +3.3 | +1.8 | +4.1 | S |
| 11 | `nw_food_ppi_yoy` | PPI/input | 99 | +0.35 | +0.27 | +1.14 | +4.0 | +3.6 | 0.013 | +4.1 | +1.2 | +3.4 | +1.4 | +4.3 | S |
| 12 | `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 62 | +0.45 | +0.24 | +1.57 | +4.1 | +3.8 | 0.013 | +3.6 |  | +5.6 | -0.5 | +4.0 |  |
| 13 | `w_food_ppi_yoy` | PPI/input | 99 | +0.34 | +0.19 | +1.12 | +3.9 | +3.6 | 0.018 | +3.9 | +1.5 | +3.6 | +0.9 | +4.2 | S |
| 14 | `w_policy_rate_d4` | rates | 102 | +0.40 | +0.36 | +1.32 | +3.8 | +3.7 | 0.019 | +3.9 | +2.3 | +2.8 | +2.7 | +3.7 | SR |
| 15 | `no_earn_idx_food_manuf_q__yoy` | wages/inc. | 102 | -0.37 | -0.37 | -1.29 | -3.8 | -3.6 | 0.022 | -4.2 | -1.1 | -3.3 | -3.3 | -3.1 | SR |

#### og, real-time h=4 (4 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `no_ssb_bts_consgoods_home_price_exp__d4` | price exp. | 102 | +0.42 | +0.37 | +1.52 | +4.5 | +4.2 | 0.019 | +5.1 | +5.0 | +4.7 | +2.7 | +4.3 | SR |
| 2 | `no_ssb_bts_consgoods_home_price_exp__lvl` | price exp. | 102 | +0.42 | +0.43 | +1.43 | +4.3 | +4.1 | 0.026 | +3.7 | +2.0 | +2.6 | +2.7 | +4.4 | SR |
| 3 | `glob_gscpi__lvl` | packaging | 102 | +0.42 | +0.15 | +1.47 | +4.1 | +3.9 | 0.027 | +4.1 | -1.9 | +4.4 | -0.3 | +4.9 |  |
| 4 | `eu_ppi_plastic_products_idx__yoy` | packaging | 97 | +0.35 | +0.13 | +1.20 | +3.7 | +3.4 | 0.111 | +3.4 | +3.1 | +3.4 | +1.6 | +4.0 | S |
| 5 | `w_policy_rate_d4` | rates | 102 | +0.38 | +0.33 | +1.21 | +3.5 | +3.2 | 0.152 | +3.5 | +7.0 | +0.9 | +3.6 | +3.8 | S |
| 6 | `packaging_eu_yoy` | packaging | 97 | +0.35 | +0.24 | +1.19 | +3.5 | +3.1 | 0.152 | +3.4 | +4.7 | +2.9 | +2.4 | +3.7 | S |
| 7 | `ea_ec_food_ind_sell_price_exp__lvl` | price exp. | 102 | +0.40 | +0.23 | +1.36 | +3.4 | +3.2 | 0.163 | +3.2 | +4.7 | +2.4 | +0.9 | +3.8 | S |
| 8 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 97 | +0.34 | +0.31 | +1.14 | +3.3 | +2.9 | 0.163 | +3.4 | +4.6 | +2.7 | +2.5 | +3.5 | S |
| 9 | `eu_agri_wheat_bread_price__yoy` | commod. | 34 | +0.55 | +0.61 | +1.96 | +3.5 | +3.0 | 0.163 | +3.8 |  | +3.5 |  |  |  |
| 10 | `se_cpi_idx__dyoy` | CPI | 102 | +0.41 | +0.36 | +1.33 | +3.3 | +3.1 | 0.176 | +3.1 | +4.3 | +3.3 | +2.2 | +3.2 | S |
| 11 | `eu_ppi_dom_c106_idx__dyoy` | PPI/input | 93 | +0.33 | +0.24 | +1.30 | +3.1 | +3.0 | 0.237 | +3.4 | +4.7 | +3.0 | +2.5 | +3.1 | S |
| 12 | `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 60 | +0.39 | +0.25 | +1.32 | +3.2 | +2.9 | 0.237 | +3.0 |  | +3.3 | +0.7 | +3.1 |  |
| 13 | `se_real_wage_yoy_q__d4` | wages/inc. | 102 | -0.34 | -0.31 | -1.11 | -3.1 | -2.9 | 0.252 | -3.0 | -3.2 | -3.1 | -2.5 | -3.0 | S |
| 14 | `eu_ppi_dom_c107_idx__dyoy` | PPI/input | 93 | +0.28 | +0.28 | +0.99 | +3.0 | +2.7 | 0.291 | +3.0 | +3.3 | +3.7 | +2.3 | +3.0 | S |
| 15 | `se_policy_rate__d4` | rates | 102 | +0.34 | +0.33 | +1.09 | +3.0 | +2.7 | 0.291 | +2.8 | +9.0 | +0.6 | +3.0 | +3.0 | S |

#### og: top 10 per alignment on the sample excluding 2021Q3-2023Q4 (ex-infl HAC t)

| # | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| 1 | `se_food_vat_rate__d4` +4.6* | `se_food_vat_rate__d4` +4.6* | `se_wage_idx_m__dyoy` +4.2* | `no_earn_idx_food_manuf_q__yoy` -3.3 | `w_unemp_d4` -4.9* |
| 2 | `se_food_vat_rate__lvl` +4.6* | `se_food_vat_rate__lvl` +4.6* | `se_cpi_food_idx__yoy` +3.7 | `w_unemp_lvl` -2.9 | `no_vat_food_rate__lvl` +3.7 |
| 3 | `no_vat_food_rate__d4` -3.8* | `no_vat_food_rate__d4` -3.8* | `no_vat_food_rate__d4` -3.4 | `no_vat_food_rate__d4` -2.9 | `w_policy_rate_d4` +3.6 |
| 4 | `se_cpi_food_idx__yoy` +3.5 | `se_cpi_food_idx__yoy` +3.5 | `se_ec_cons_conf__lvl` -3.2 | `no_ssb_bts_consgoods_home_price_exp__lvl` +2.8 | `no_policy_rate__d4` +3.3 |
| 5 | `se_wage_idx_m__dyoy` +3.5 | `nw_real_wage_yoy` -3.5 | `w_unemp_lvl` -3.1 | `no_vat_food_rate__lvl` +2.7 | `se_policy_rate__d4` +3.0 |
| 6 | `nw_cons_conf_z` -3.2 | `se_wage_idx_m__dyoy` +3.3 | `nw_cons_conf_z` -3.0 | `se_ec_cons_conf__lvl` -2.7 | `w_gdp_vol_yoy` +2.8 |
| 7 | `no_fn_cci_sa__lvl` -3.1 | `nw_cons_conf_z` -3.2 | `w_cons_conf_z_d4` -2.5 | `w_policy_rate_d4` +2.7 | `no_ssb_bts_consgoods_home_price_exp__d4` +2.7 |
| 8 | `se_ec_cons_conf__lvl` -2.9 | `no_fn_cci_sa__lvl` -3.1 | `se_nier_food_mfg_sell_price_exp__lvl` +2.5 | `se_nier_food_mfg_sell_price_exp__lvl` +2.7 | `no_ssb_bts_consgoods_home_price_exp__lvl` +2.7 |
| 9 | `ea_hicp_food_idx__yoy` +2.9 | `se_ec_cons_conf__lvl` -2.9 | `nw_food_cpi_xvat_yoy` +2.5 | `wb_food_sek_yoy` +2.5 | `eu_ppi_dom_c106_idx__dyoy` +2.5 |
| 10 | `nw_food_ppi_yoy` +2.7 | `nw_food_cpi_xvat_yoy` +2.7 | `w_cons_conf_z` -2.4 | `nw_cons_conf_z` -2.5 | `eu_ppi_paper_packaging_idx__yoy` +2.5 |

Figures: `figures/top10_og_coincident.png`, `figures/top10_og_realtime.png`, `figures/lagprofile_og.png`.

### d_og (organic-growth change y/y, pp)

Significance counts:

| family | alignment | tests | q_BY<0.10 | q_BY(lev)<0.10 | q_BY ex-infl<0.10 | q_BY +own lag<0.10 | robust |
|---|---|---|---|---|---|---|---|
| core | coin | 200 | 42 | 31 | 20 | 64 | 26 |
| core | rt0 | 200 | 52 | 42 | 29 | 67 | 35 |
| core | rt1 | 198 | 57 | 45 | 35 | 71 | 32 |
| core | rt2 | 198 | 47 | 39 | 40 | 70 | 35 |
| core | rt4 | 198 | 56 | 46 | 49 | 55 | 44 |
| all | coin | 1408 | 217 | 154 | 94 | 305 | 128 |
| all | rt0 | 1408 | 215 | 147 | 127 | 283 | 131 |
| all | rt1 | 1406 | 225 | 138 | 135 | 312 | 121 |
| all | rt2 | 1406 | 257 | 185 | 183 | 363 | 170 |
| all | rt4 | 1402 | 259 | 205 | 280 | 275 | 196 |

#### d_og, coincident (same quarter, not real-time)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t +base | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `price_wage_gap_d4` | gap/spread | 98 | +0.33 | +0.33 | +1.40 | +5.6 | +5.2 | 0.000 | +6.1 | +2.3 | +2.1 | +5.2 | +4.4 | +5.4 | SR |
| 2 | `price_cost_gap_ppi` | gap/spread | 98 | -0.42 | -0.40 | -1.82 | -5.6 | -5.1 | 0.000 | -5.8 | -2.1 | -3.6 | -4.8 | -3.7 | -5.4 | SR |
| 3 | `eu_ppi_dom_c107_idx__dyoy` | PPI/input | 98 | +0.42 | +0.36 | +1.62 | +5.5 | +5.2 | 0.000 | +5.9 | +1.9 | +3.0 | +4.7 | +5.3 | +5.6 | SR |
| 4 | `eu_ppi_dom_c108_idx__dyoy` | PPI/input | 98 | +0.45 | +0.48 | +1.80 | +5.4 | +5.1 | 0.000 | +8.4 | +2.8 | +6.5 | +5.1 | +5.8 | +5.5 | SR |
| 5 | `ea_hicp_food_idx__dyoy` | CPI | 98 | +0.45 | +0.47 | +1.76 | +5.4 | +4.9 | 0.000 | +9.0 | +3.1 | +5.2 | +5.0 | +5.9 | +5.3 | SR |
| 6 | `nw_price_cost_gap_ppi` | gap/spread | 98 | -0.45 | -0.46 | -1.85 | -5.3 | -4.9 | 0.000 | -5.7 | -2.4 | -3.0 | -4.7 | -3.4 | -5.3 | SR |
| 7 | `eu_ppi_plastic_products_idx__yoy` | packaging | 98 | +0.36 | +0.26 | +1.65 | +5.3 | +4.7 | 0.000 | +5.7 | +3.3 | +2.3 | +4.6 | +2.0 | +5.0 | S |
| 8 | `eu_ppi_dom_c103_idx__dyoy` | PPI/input | 98 | +0.39 | +0.36 | +1.62 | +5.1 | +4.9 | 0.000 | +6.4 | +2.5 | +2.8 | +4.3 | +5.0 | +5.1 | SR |
| 9 | `se_ec_cons_conf__d4` | cons. survey | 98 | -0.43 | -0.44 | -1.64 | -5.1 | -4.3 | 0.000 | -6.9 | -4.0 | -2.6 | -4.7 | -4.9 | -4.8 | SR |
| 10 | `se_cpi_food_idx__dyoy` | CPI | 98 | +0.38 | +0.36 | +1.40 | +4.9 | +4.5 | 0.000 | +7.1 | +2.7 | +3.1 | +4.5 | +5.4 | +4.9 | SR |
| 11 | `se_ppi_food_hmpi_idx__dyoy` | PPI/input | 98 | +0.41 | +0.35 | +1.51 | +4.9 | +4.6 | 0.000 | +4.7 | +1.6 | +3.5 | +4.1 | +3.9 | +5.0 | SR |
| 12 | `no_ppi_food_dom_idx__dyoy` | PPI/input | 98 | +0.43 | +0.45 | +1.71 | +4.8 | +4.4 | 0.001 | +6.4 | +2.6 | +2.3 | +4.5 | +6.4 | +4.7 | SR |
| 13 | `w_food_cpi_dyoy` | CPI | 98 | +0.34 | +0.32 | +1.35 | +4.7 | +4.2 | 0.001 | +6.8 | +2.5 | +3.4 | +4.4 | +4.7 | +4.6 | SR |
| 14 | `w_food_cpi_xvat_dyoy` | CPI | 98 | +0.35 | +0.29 | +1.36 | +4.7 | +4.2 | 0.001 | +6.7 | +2.6 | +3.4 | +4.3 | +4.7 | +4.5 | SR |
| 15 | `nw_food_ppi_dyoy` | PPI/input | 98 | +0.45 | +0.51 | +1.67 | +4.5 | +4.1 | 0.001 | +5.8 | +2.1 | +3.8 | +4.4 | +5.9 | +4.5 | SR |

#### d_og, real-time nowcast h=0 (info at quarter end, before report)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t +base | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_dom_c107_idx__dyoy` | PPI/input | 97 | +0.39 | +0.43 | +1.49 | +5.6 | +5.2 | 0.000 | +7.4 | +2.5 | +3.7 | +4.6 | +6.4 | +5.8 | SR |
| 2 | `w_real_wage_dyoy` | wages/inc. | 98 | -0.45 | -0.44 | -1.89 | -5.5 | -5.3 | 0.000 | -7.5 | -3.0 | -3.2 | -4.6 | -5.6 | -5.8 | SR |
| 3 | `eu_ppi_dom_food_mfg_idx__dyoy` | PPI/input | 97 | +0.39 | +0.32 | +1.62 | +5.5 | +5.3 | 0.000 | +6.2 | +2.1 | +3.3 | +4.4 | +5.5 | +5.4 | SR |
| 4 | `se_ec_cons_conf__d4` | cons. survey | 98 | -0.43 | -0.44 | -1.64 | -5.1 | -4.3 | 0.000 | -6.9 | -4.0 | -2.6 | -4.7 | -4.9 | -4.8 | SR |
| 5 | `se_cpi_food_idx__dyoy` | CPI | 98 | +0.38 | +0.36 | +1.40 | +4.9 | +4.5 | 0.001 | +7.1 | +2.7 | +3.1 | +4.5 | +5.4 | +4.9 | SR |
| 6 | `w_food_ppi_dyoy` | PPI/input | 97 | +0.37 | +0.40 | +1.44 | +4.9 | +4.6 | 0.001 | +6.8 | +2.2 | +3.8 | +4.8 | +5.5 | +5.0 | SR |
| 7 | `price_wage_gap_d4` | gap/spread | 98 | +0.32 | +0.35 | +1.30 | +4.9 | +4.4 | 0.001 | +7.9 | +2.7 | +3.1 | +4.0 | +5.8 | +5.1 | SR |
| 8 | `no_ppi_food_dom_idx__dyoy` | PPI/input | 98 | +0.43 | +0.45 | +1.71 | +4.8 | +4.4 | 0.001 | +6.4 | +2.6 | +2.3 | +4.5 | +6.4 | +4.7 | SR |
| 9 | `eu_ppi_dom_c103_idx__dyoy` | PPI/input | 97 | +0.33 | +0.36 | +1.31 | +4.7 | +4.4 | 0.001 | +8.2 | +2.8 | +5.0 | +3.4 | +6.4 | +4.8 | SR |
| 10 | `eu_ppi_dom_c106_idx__dyoy` | PPI/input | 97 | +0.41 | +0.41 | +1.64 | +4.6 | +4.4 | 0.001 | +3.7 | +1.3 | +2.2 | +4.5 | +3.9 | +4.7 | SR |
| 11 | `se_real_wage_yoy_q__d4` | wages/inc. | 98 | -0.38 | -0.41 | -1.53 | -4.6 | -4.4 | 0.001 | -5.5 | -2.4 | -1.6 | -4.0 | -4.7 | -4.8 | SR |
| 12 | `nw_food_ppi_dyoy` | PPI/input | 97 | +0.38 | +0.45 | +1.40 | +4.5 | +4.2 | 0.002 | +7.4 | +2.4 | +4.2 | +4.3 | +5.5 | +4.6 | SR |
| 13 | `se_ppi_food_hmpi_idx__dyoy` | PPI/input | 98 | +0.36 | +0.35 | +1.27 | +4.5 | +4.1 | 0.002 | +6.5 | +2.1 | +4.9 | +3.0 | +5.2 | +5.3 | SR |
| 14 | `eu_ppi_dom_c108_idx__dyoy` | PPI/input | 97 | +0.38 | +0.49 | +1.46 | +4.3 | +3.9 | 0.003 | +7.4 | +2.9 | +8.5 | +3.7 | +4.7 | +4.2 | SR |
| 15 | `price_cost_gap_ppi` | gap/spread | 98 | -0.37 | -0.33 | -1.62 | -4.3 | -4.0 | 0.004 | -6.0 | -2.8 | -2.4 | -3.3 | -3.1 | -4.1 | SR |

#### d_og, real-time h=1 (1 quarter ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t +base | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `no_retail_foodstores_vol_sa_idx__dyoy` | activity | 96 | -0.36 | -0.15 | -1.66 | -6.7 | -5.7 | 0.000 | -7.2 | -3.1 | +0.1 | -7.6 | -2.5 | -5.4 |  |
| 2 | `eu_ppi_dom_c106_idx__dyoy` | PPI/input | 96 | +0.39 | +0.40 | +1.66 | +6.4 | +6.1 | 0.000 | +5.5 | +2.1 | +2.8 | +5.7 | +5.6 | +6.4 | SR |
| 3 | `eu_ppi_dom_food_mfg_idx__dyoy` | PPI/input | 96 | +0.35 | +0.30 | +1.50 | +5.7 | +5.4 | 0.000 | +7.9 | +2.5 | +4.1 | +4.3 | +6.0 | +5.6 | SR |
| 4 | `price_cost_gap_fao_wloc` | gap/spread | 98 | -0.48 | -0.44 | -1.88 | -5.1 | -4.8 | 0.001 | -5.2 | -2.2 | -3.6 | -4.0 | -4.2 | -4.9 | SR |
| 5 | `nw_retail_food_vol_dyoy` | activity | 96 | -0.36 | -0.18 | -1.65 | -4.9 | -4.3 | 0.001 | -6.6 | -3.0 | +0.5 | -6.4 | -2.2 | -4.1 |  |
| 6 | `eu_ppi_paper_packaging_idx__dyoy` | packaging | 96 | +0.36 | +0.39 | +1.45 | +4.9 | +4.7 | 0.001 | +4.9 | +1.5 | +2.5 | +4.8 | +4.6 | +5.0 | SR |
| 7 | `eu_ppi_plastic_products_idx__dyoy` | packaging | 96 | +0.36 | +0.28 | +1.67 | +4.8 | +4.4 | 0.001 | +5.3 | +1.5 | +2.8 | +4.5 | +5.5 | +4.7 | SR |
| 8 | `w_ec_cons_price_exp_lvl` | price exp. | 98 | +0.39 | +0.42 | +2.01 | +4.8 | +4.4 | 0.001 | +4.6 | +2.0 | +5.5 | +3.7 | +4.0 | +4.6 | SR |
| 9 | `no_qna_hh_food_cons_sa_mnok__dyoy` | activity | 98 | -0.32 | -0.20 | -1.58 | -4.8 | -4.3 | 0.001 | -6.1 | -4.3 | -0.4 | -4.7 | -3.5 | -3.5 | SR |
| 10 | `packaging_eu_dyoy` | packaging | 96 | +0.37 | +0.34 | +1.58 | +4.6 | +4.4 | 0.001 | +5.0 | +1.5 | +2.9 | +4.4 | +4.9 | +4.7 | SR |
| 11 | `price_cost_gap_fao_nok` | gap/spread | 98 | -0.44 | -0.42 | -1.79 | -4.6 | -4.3 | 0.002 | -4.5 | -2.1 | -3.2 | -3.5 | -3.9 | -4.6 | SR |
| 12 | `price_cost_gap_ppi_d4` | gap/spread | 96 | -0.35 | -0.29 | -1.58 | -4.4 | -4.2 | 0.003 | -4.2 | -1.6 | -1.8 | -4.2 | -3.3 | -4.1 | SR |
| 13 | `w_food_ppi_dyoy` | PPI/input | 96 | +0.29 | +0.31 | +1.20 | +4.3 | +4.0 | 0.003 | +5.8 | +2.3 | +1.9 | +4.1 | +4.1 | +4.4 | SR |
| 14 | `se_ppi_food_hmpi_idx__dyoy` | PPI/input | 98 | +0.32 | +0.36 | +1.23 | +4.3 | +4.0 | 0.003 | +7.4 | +2.8 | +2.5 | +3.5 | +4.7 | +4.3 | SR |
| 15 | `nw_price_cost_gap_ppi_d4` | gap/spread | 96 | -0.35 | -0.33 | -1.59 | -4.3 | -4.1 | 0.003 | -4.2 | -1.6 | -2.0 | -4.4 | -3.4 | -4.1 | SR |

#### d_og, real-time h=2 (2 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t +base | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_dom_c106_idx__dyoy` | PPI/input | 95 | +0.32 | +0.28 | +1.59 | +7.4 | +6.9 | 0.000 | +7.7 | +2.9 | +3.7 | +5.0 | +6.4 | +7.3 | SR |
| 2 | `ea_ec_food_ind_sell_price_exp__d4` | price exp. | 98 | +0.41 | +0.35 | +1.72 | +5.9 | +5.6 | 0.000 | +6.0 | +2.0 | +4.0 | +4.6 | +5.1 | +5.5 | SR |
| 3 | `eu_ppi_plastic_products_idx__dyoy` | packaging | 95 | +0.42 | +0.42 | +1.85 | +5.5 | +5.0 | 0.000 | +6.7 | +2.3 | +6.9 | +5.4 | +4.7 | +5.5 | SR |
| 4 | `w_gdp_vol_dyoy` | activity | 98 | +0.41 | +0.19 | +1.93 | +5.5 | +4.6 | 0.000 | +4.7 | +2.0 | +2.1 | +6.2 | +3.2 | +4.5 | SR |
| 5 | `w_ec_food_ind_sell_price_exp_d4` | price exp. | 98 | +0.41 | +0.31 | +1.75 | +5.4 | +5.2 | 0.000 | +7.4 | +2.9 | +2.7 | +4.3 | +4.6 | +5.8 | SR |
| 6 | `w_ec_cons_price_exp_lvl` | price exp. | 98 | +0.35 | +0.37 | +1.79 | +5.3 | +5.0 | 0.000 | +5.0 | +2.6 | +4.0 | +4.4 | +4.1 | +5.2 | SR |
| 7 | `no_retail_foodstores_vol_sa_idx__dyoy` | activity | 95 | -0.36 | -0.22 | -1.63 | -5.3 | -4.6 | 0.000 | -6.3 | -4.1 | -0.7 | -5.1 | -3.7 | -4.7 | SR |
| 8 | `w_gdp_vol_yoy` | activity | 98 | +0.47 | +0.36 | +2.05 | +5.0 | +4.3 | 0.000 | +5.4 | +3.0 | +2.1 | +7.1 | +3.7 | +3.3 | SR |
| 9 | `glob_fao_ffpi_eur__yoy` | commod. | 98 | +0.44 | +0.38 | +1.82 | +4.9 | +4.6 | 0.000 | +5.1 | +2.5 | +3.7 | +3.8 | +3.9 | +4.7 | SR |
| 10 | `packaging_us_yoy` | packaging | 98 | +0.39 | +0.35 | +1.91 | +4.9 | +4.5 | 0.000 | +4.5 | +2.3 | +2.7 | +4.7 | +3.1 | +5.0 | SR |
| 11 | `nw_retail_food_vol_dyoy` | activity | 95 | -0.31 | -0.26 | -1.39 | -4.8 | -4.4 | 0.001 | -6.8 | -3.5 | -0.1 | -5.0 | -2.9 | -4.2 | SR |
| 12 | `packaging_eu_dyoy` | packaging | 95 | +0.41 | +0.47 | +1.70 | +4.7 | +4.2 | 0.001 | +5.2 | +2.1 | +7.7 | +5.0 | +4.0 | +4.7 | SR |
| 13 | `fao_ffpi_wloc_yoy` | commod. | 98 | +0.45 | +0.42 | +1.83 | +4.7 | +4.4 | 0.001 | +5.4 | +3.0 | +3.0 | +3.7 | +3.7 | +4.5 | SR |
| 14 | `us_ppi_plastic_resins_idx__yoy` | packaging | 98 | +0.39 | +0.36 | +1.94 | +4.6 | +4.2 | 0.001 | +3.9 | +2.0 | +3.5 | +5.2 | +2.9 | +4.6 | SR |
| 15 | `eu_ppi_paper_packaging_idx__dyoy` | packaging | 95 | +0.38 | +0.47 | +1.53 | +4.6 | +4.1 | 0.001 | +5.1 | +2.1 | +5.1 | +4.9 | +3.8 | +4.6 | SR |

#### d_og, real-time h=4 (4 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t +base | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_dom_c108_idx__yoy` | PPI/input | 97 | -0.35 | -0.38 | -1.29 | -6.6 | -6.2 | 0.000 | -7.0 | -4.4 | -1.5 | -6.0 | -4.9 | -6.7 | SR |
| 2 | `packaging_us_dyoy` | packaging | 98 | +0.30 | +0.33 | +1.50 | +5.6 | +5.2 | 0.000 | +5.0 | +5.3 | +2.4 | +4.6 | +4.2 | +6.0 | SR |
| 3 | `ea_hicp_food_idx__yoy` | CPI | 97 | -0.36 | -0.37 | -1.42 | -5.4 | -5.1 | 0.000 | -5.9 | -4.2 | -3.6 | -5.3 | -5.1 | -5.4 | SR |
| 4 | `ea_ec_food_ind_sell_price_exp__d4` | price exp. | 98 | +0.29 | +0.24 | +1.28 | +5.2 | +4.9 | 0.000 | +5.2 | +6.2 | +4.6 | +3.3 | +5.3 | +6.2 | SR |
| 5 | `w_food_cpi_yoy` | CPI | 98 | -0.31 | -0.24 | -1.33 | -5.1 | -4.8 | 0.000 | -5.3 | -4.1 | -4.4 | -5.5 | -4.7 | -5.0 | SR |
| 6 | `eu_ppi_dom_c103_idx__yoy` | PPI/input | 97 | -0.32 | -0.34 | -1.23 | -5.1 | -4.8 | 0.000 | -5.5 | -3.4 | -1.4 | -4.3 | -5.4 | -5.0 | SR |
| 7 | `w_food_cpi_xvat_yoy` | CPI | 98 | -0.33 | -0.30 | -1.35 | -5.1 | -4.8 | 0.000 | -5.4 | -4.1 | -4.1 | -5.5 | -4.7 | -5.0 | SR |
| 8 | `price_wage_gap` | gap/spread | 98 | -0.37 | -0.42 | -1.45 | -4.9 | -4.6 | 0.001 | -4.8 | -4.5 | -3.6 | -5.6 | -4.6 | -4.7 | SR |
| 9 | `us_ppi_plastic_resins_idx__dyoy` | packaging | 98 | +0.26 | +0.28 | +1.42 | +4.8 | +4.6 | 0.001 | +4.2 | +4.2 | +1.9 | +4.5 | +3.3 | +5.0 | SR |
| 10 | `eu_ppi_dom_c107_idx__yoy` | PPI/input | 97 | -0.33 | -0.33 | -1.29 | -4.8 | -4.6 | 0.001 | -5.1 | -3.4 | -2.0 | -4.7 | -5.7 | -4.8 | SR |
| 11 | `nw_food_ppi_yoy` | PPI/input | 97 | -0.31 | -0.35 | -1.24 | -4.7 | -4.3 | 0.001 | -4.7 | -3.3 | -2.4 | -4.9 | -5.2 | -4.8 | SR |
| 12 | `w_food_cpi_rel_yoy` | CPI | 98 | -0.25 | -0.23 | -1.32 | -4.6 | -4.4 | 0.001 | -5.5 | -4.1 | -3.5 | -4.3 | -4.8 | -5.7 | SR |
| 13 | `us_ppi_corrugated_boxes_idx__dyoy` | packaging | 98 | +0.27 | +0.25 | +1.19 | +4.4 | +4.2 | 0.002 | +4.0 | +4.3 | +1.4 | +4.8 | +3.5 | +4.7 | SR |
| 14 | `w_ec_cons_price_exp_d4` | price exp. | 98 | +0.28 | +0.22 | +1.23 | +4.3 | +3.9 | 0.003 | +4.2 | +3.7 | +2.8 | +3.1 | +4.6 | +4.9 | SR |
| 15 | `w_food_ppi_yoy` | PPI/input | 97 | -0.31 | -0.31 | -1.21 | -4.2 | -3.9 | 0.004 | -4.1 | -2.8 | -2.3 | -4.2 | -5.2 | -4.3 | SR |

#### d_og: top 10 per alignment on the sample excluding 2021Q3-2023Q4 (ex-infl HAC t)

| # | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| 1 | `no_ppi_food_dom_idx__dyoy` +6.4* | `eu_ppi_dom_c103_idx__dyoy` +6.4* | `eu_ppi_dom_food_mfg_idx__dyoy` +6.0* | `eu_ppi_dom_c106_idx__dyoy` +6.4* | `no_ppi_food_dom_idx__yoy` -6.8* |
| 2 | `nw_food_ppi_dyoy` +5.9* | `no_ppi_food_dom_idx__dyoy` +6.4* | `eu_ppi_dom_c106_idx__dyoy` +5.6* | `ea_ec_food_ind_sell_price_exp__d4` +5.1* | `w_cpi_yoy` -6.7* |
| 3 | `ea_hicp_food_idx__dyoy` +5.9* | `eu_ppi_dom_c107_idx__dyoy` +6.4* | `eu_ppi_plastic_products_idx__dyoy` +5.5* | `w_food_cpi_xvat_yoy` -5.1* | `w_gdp_vol_dyoy` +6.7* |
| 4 | `eu_ppi_dom_c108_idx__dyoy` +5.8* | `price_wage_gap_d4` +5.8* | `se_cpi_food_idx__dyoy` +5.5* | `w_food_cpi_yoy` -4.8* | `w_real_wage_yoy` +6.5* |
| 5 | `w_food_ppi_dyoy` +5.5* | `w_cpi_dyoy` +5.7* | `se_cpi_idx__dyoy` +5.0* | `eu_ppi_plastic_products_idx__dyoy` +4.7* | `eu_ppi_dom_c107_idx__yoy` -5.7* |
| 6 | `se_cpi_food_idx__dyoy` +5.4* | `w_real_wage_dyoy` -5.6* | `packaging_eu_yoy` +5.0* | `w_ec_food_ind_sell_price_exp_d4` +4.6* | `se_cpi_food_idx__yoy` -5.5* |
| 7 | `eu_ppi_dom_c107_idx__dyoy` +5.3* | `nw_food_ppi_dyoy` +5.5* | `packaging_eu_dyoy` +4.9* | `price_wage_gap` -4.4* | `eu_ppi_dom_c103_idx__yoy` -5.4* |
| 8 | `eu_ppi_dom_c103_idx__dyoy` +5.0* | `w_food_ppi_dyoy` +5.5* | `se_ppi_food_hmpi_idx__dyoy` +4.7* | `eu_ppi_plastic_products_idx__yoy` +4.4* | `se_ec_cons_conf__lvl` +5.4* |
| 9 | `se_ec_cons_conf__d4` -4.9* | `eu_ppi_dom_food_mfg_idx__dyoy` +5.5* | `eu_ppi_paper_packaging_idx__dyoy` +4.6* | `eu_ppi_dom_food_mfg_idx__dyoy` +4.4* | `ea_ec_food_ind_sell_price_exp__d4` +5.3* |
| 10 | `w_food_cpi_xvat_dyoy` +4.7* | `ea_hicp_food_idx__dyoy` +5.5* | `eu_ppi_paper_packaging_idx__yoy` +4.5* | `w_ec_cons_price_exp_d4` +4.2* | `w_food_ppi_yoy` -5.2* |

Figures: `figures/top10_d_og_coincident.png`, `figures/top10_d_og_realtime.png`, `figures/lagprofile_d_og.png`.

### d_margin_r4 (rolling-4Q margin change, pp)

Significance counts:

| family | alignment | tests | q_BY<0.10 | q_BY(lev)<0.10 | q_BY ex-infl<0.10 | q_BY +own lag<0.10 | robust |
|---|---|---|---|---|---|---|---|
| core | coin | 200 | 58 | 52 | 2 | 64 | 26 |
| core | rt0 | 200 | 65 | 57 | 0 | 69 | 33 |
| core | rt1 | 198 | 61 | 52 | 2 | 75 | 37 |
| core | rt2 | 198 | 43 | 26 | 6 | 63 | 23 |
| core | rt4 | 198 | 3 | 0 | 0 | 29 | 0 |
| all | coin | 1408 | 293 | 246 | 60 | 320 | 131 |
| all | rt0 | 1408 | 296 | 245 | 28 | 326 | 143 |
| all | rt1 | 1406 | 287 | 229 | 28 | 354 | 151 |
| all | rt2 | 1406 | 192 | 156 | 18 | 291 | 115 |
| all | rt4 | 1402 | 73 | 42 | 15 | 167 | 32 |

#### d_margin_r4, coincident (same quarter, not real-time)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_dom_c107_idx__yoy` | PPI/input | 99 | -0.65 | -0.49 | -0.57 | -12.6 | -12.2 | 0.000 | -11.2 | -4.7 | -11.7 | -3.9 | -12.4 | SR |
| 2 | `w_cpi_yoy` | CPI | 99 | -0.61 | -0.43 | -0.55 | -11.1 | -10.9 | 0.000 | -11.5 | -3.7 | -8.0 | -2.4 | -11.9 | SR |
| 3 | `packaging_eu_yoy` | packaging | 99 | -0.60 | -0.50 | -0.53 | -11.1 | -10.6 | 0.000 | -12.3 | -2.4 | -15.2 | -2.6 | -10.0 | SR |
| 4 | `eu_ppi_plastic_products_idx__yoy` | packaging | 99 | -0.52 | -0.40 | -0.46 | -10.9 | -10.1 | 0.000 | -8.8 | -2.2 | -12.3 | -2.6 | -9.4 | SR |
| 5 | `se_real_wage_yoy_q__lvl` | wages/inc. | 99 | +0.61 | +0.48 | +0.54 | +9.9 | +9.6 | 0.000 | +10.7 | +3.0 | +6.2 | +2.4 | +10.9 | SR |
| 6 | `w_food_ppi_yoy` | PPI/input | 99 | -0.57 | -0.26 | -0.51 | -9.2 | -9.0 | 0.000 | -9.5 | -2.2 | -8.9 | -1.0 | -9.0 | S |
| 7 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 99 | -0.63 | -0.54 | -0.56 | -8.5 | -8.0 | 0.000 | -8.9 | -2.5 | -12.4 | -2.5 | -8.3 | SR |
| 8 | `w_food_cpi_xvat_yoy` | CPI | 99 | -0.50 | -0.17 | -0.45 | -8.5 | -7.4 | 0.000 | -7.8 | -1.7 | -11.8 | -1.0 | -8.9 | S |
| 9 | `ea_hicp_food_idx__yoy` | CPI | 99 | -0.55 | -0.29 | -0.49 | -7.6 | -7.2 | 0.000 | -8.1 | -3.0 | -6.2 | -1.1 | -7.4 | S |
| 10 | `w_food_cpi_yoy` | CPI | 99 | -0.49 | -0.12 | -0.44 | -7.5 | -6.6 | 0.000 | -7.6 | -1.2 | -11.2 | -0.6 | -8.1 | S |
| 11 | `se_cpi_idx__yoy` | CPI | 99 | -0.62 | -0.53 | -0.56 | -7.4 | -7.1 | 0.000 | -9.3 | -4.6 | -5.7 | -2.3 | -7.6 | SR |
| 12 | `eu_ppi_dom_c105_idx__yoy` | PPI/input | 99 | -0.70 | -0.55 | -0.62 | -7.2 | -7.0 | 0.000 | -7.1 | -4.5 | -5.6 | -3.3 | -7.2 | SR |
| 13 | `nw_food_ppi_yoy` | PPI/input | 99 | -0.54 | -0.16 | -0.48 | -7.0 | -6.5 | 0.000 | -8.2 | -2.1 | -6.6 | -0.5 | -6.9 | S |
| 14 | `eu_ppi_dom_c103_idx__yoy` | PPI/input | 99 | -0.55 | -0.37 | -0.49 | -6.6 | -6.2 | 0.000 | -7.1 | -3.1 | -5.3 | -1.7 | -6.5 | S |
| 15 | `eu_ppi_dom_food_mfg_idx__yoy` | PPI/input | 99 | -0.61 | -0.39 | -0.54 | -5.8 | -5.6 | 0.000 | -6.5 | -2.5 | -5.8 | -1.4 | -5.6 | S |

#### d_margin_r4, real-time nowcast h=0 (info at quarter end, before report)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_plastic_products_idx__yoy` | packaging | 99 | -0.60 | -0.46 | -0.53 | -15.4 | -14.5 | 0.000 | -17.9 | -3.1 | -18.2 | -2.8 | -13.1 | SR |
| 2 | `packaging_eu_yoy` | packaging | 99 | -0.65 | -0.54 | -0.58 | -13.9 | -13.3 | 0.000 | -10.9 | -2.6 | -16.7 | -2.9 | -15.1 | SR |
| 3 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 99 | -0.66 | -0.56 | -0.59 | -10.3 | -9.7 | 0.000 | -7.7 | -2.8 | -13.3 | -2.9 | -11.3 | SR |
| 4 | `w_food_ppi_yoy` | PPI/input | 99 | -0.51 | -0.26 | -0.45 | -7.5 | -7.0 | 0.000 | -8.5 | -1.5 | -9.6 | -1.0 | -7.5 | S |
| 5 | `se_cpi_idx__yoy` | CPI | 99 | -0.62 | -0.53 | -0.56 | -7.4 | -7.1 | 0.000 | -9.3 | -4.6 | -5.7 | -2.3 | -7.6 | SR |
| 6 | `eu_ppi_dom_c105_idx__yoy` | PPI/input | 99 | -0.63 | -0.54 | -0.56 | -6.3 | -6.0 | 0.000 | -5.9 | -4.2 | -6.1 | -3.6 | -6.2 | SR |
| 7 | `se_real_wage_yoy_q__lvl` | wages/inc. | 99 | +0.52 | +0.39 | +0.46 | +6.1 | +5.7 | 0.000 | +7.4 | +3.9 | +5.2 | +2.1 | +6.4 | SR |
| 8 | `eu_ppi_dom_food_mfg_idx__yoy` | PPI/input | 99 | -0.55 | -0.37 | -0.49 | -5.7 | -5.4 | 0.000 | -6.3 | -3.1 | -6.2 | -1.5 | -5.8 | S |
| 9 | `eu_ppi_dom_c107_idx__yoy` | PPI/input | 99 | -0.49 | -0.39 | -0.43 | -5.4 | -5.0 | 0.000 | -7.1 | -2.2 | -7.5 | -2.1 | -5.0 | SR |
| 10 | `w_cpi_yoy` | CPI | 99 | -0.51 | -0.38 | -0.46 | -5.4 | -5.1 | 0.000 | -7.4 | -1.0 | -6.0 | -0.9 | -5.3 | S |
| 11 | `se_cpi_idx__dyoy` | CPI | 99 | -0.63 | -0.61 | -0.56 | -5.3 | -5.0 | 0.000 | -6.0 | -2.5 | -5.0 | -3.2 | -5.3 | SR |
| 12 | `ea_hicp_food_idx__yoy` | CPI | 99 | -0.42 | -0.22 | -0.37 | -5.3 | -4.8 | 0.000 | -5.3 | -2.2 | -5.8 | -1.1 | -5.1 | S |
| 13 | `nw_food_ppi_yoy` | PPI/input | 99 | -0.46 | -0.16 | -0.41 | -5.1 | -4.6 | 0.000 | -6.2 | -1.1 | -7.1 | -0.2 | -5.1 | S |
| 14 | `eu_ppi_dom_c103_idx__dyoy` | PPI/input | 97 | -0.55 | -0.49 | -0.49 | -5.1 | -4.7 | 0.000 | -4.2 | -3.1 | -4.9 | -3.5 | -5.2 | SR |
| 15 | `w_unemp_d4` | labour | 99 | +0.54 | +0.58 | +0.48 | +4.9 | +4.7 | 0.000 | +5.4 | +3.8 | +3.5 | +3.9 | +4.5 | SR |

#### d_margin_r4, real-time h=1 (1 quarter ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_plastic_products_idx__yoy` | packaging | 99 | -0.62 | -0.48 | -0.55 | -15.8 | -15.1 | 0.000 | -16.4 | -2.8 | -19.4 | -2.8 | -15.0 | SR |
| 2 | `packaging_eu_yoy` | packaging | 99 | -0.63 | -0.51 | -0.56 | -11.5 | -10.9 | 0.000 | -8.4 | -2.5 | -11.7 | -3.0 | -12.8 | SR |
| 3 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 99 | -0.61 | -0.49 | -0.54 | -9.7 | -9.0 | 0.000 | -6.5 | -2.6 | -10.1 | -3.1 | -10.3 | SR |
| 4 | `eu_ppi_dom_c103_idx__dyoy` | PPI/input | 96 | -0.47 | -0.41 | -0.42 | -5.7 | -5.4 | 0.000 | -4.4 | -4.6 | -5.5 | -5.0 | -5.7 | SR |
| 5 | `w_gov10y_d4` | rates | 99 | -0.65 | -0.56 | -0.58 | -5.4 | -5.2 | 0.000 | -5.1 | -2.5 | -5.1 | -2.9 | -5.3 | SR |
| 6 | `se_cpi_idx__dyoy` | CPI | 99 | -0.63 | -0.64 | -0.56 | -5.3 | -5.1 | 0.000 | -4.8 | -2.7 | -5.3 | -3.8 | -5.5 | SR |
| 7 | `w_food_cpi_xvat_dyoy` | CPI | 99 | -0.38 | -0.27 | -0.34 | -5.2 | -4.8 | 0.000 | -4.4 | -1.3 | -6.1 | -3.0 | -5.8 | SR |
| 8 | `ea_ec_food_ind_sell_price_exp__lvl` | price exp. | 99 | -0.59 | -0.37 | -0.53 | -5.2 | -4.9 | 0.000 | -5.5 | -2.6 | -4.5 | -1.4 | -5.0 | S |
| 9 | `nw_food_cpi_xvat_dyoy` | CPI | 99 | -0.42 | -0.22 | -0.37 | -4.9 | -4.4 | 0.000 | -4.4 | -1.4 | -5.7 | -2.2 | -6.0 | SR |
| 10 | `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 63 | -0.63 | -0.31 | -0.58 | -5.1 | -4.6 | 0.000 | -5.0 |  | -5.2 | -0.3 | -5.9 |  |
| 11 | `se_real_wage_yoy_q__d4` | wages/inc. | 99 | +0.57 | +0.56 | +0.50 | +4.9 | +4.6 | 0.000 | +4.0 | +2.9 | +4.8 | +4.0 | +5.0 | SR |
| 12 | `nw_retail_food_vol_dyoy` | activity | 96 | +0.49 | +0.34 | +0.44 | +4.6 | +4.4 | 0.001 | +4.5 | +0.2 | +7.3 | +2.3 | +4.3 | SR |
| 13 | `se_cpi_idx__yoy` | CPI | 99 | -0.49 | -0.41 | -0.44 | -4.6 | -4.3 | 0.001 | -6.0 | -3.2 | -4.0 | -1.5 | -4.6 | S |
| 14 | `no_govbond_10y__d4` | rates | 99 | -0.66 | -0.60 | -0.58 | -4.6 | -4.4 | 0.001 | -4.5 | -3.0 | -4.4 | -3.0 | -4.3 | SR |
| 15 | `w_food_cpi_dyoy` | CPI | 99 | -0.36 | -0.19 | -0.32 | -4.5 | -4.1 | 0.001 | -4.3 | -0.8 | -5.7 | -2.5 | -5.2 | SR |

#### d_margin_r4, real-time h=2 (2 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_plastic_products_idx__yoy` | packaging | 99 | -0.57 | -0.45 | -0.51 | -10.5 | -9.8 | 0.000 | -11.4 | -1.7 | -11.9 | -2.4 | -9.6 | SR |
| 2 | `packaging_eu_yoy` | packaging | 99 | -0.53 | -0.41 | -0.48 | -7.5 | -6.9 | 0.000 | -7.2 | -1.7 | -7.5 | -2.3 | -7.2 | SR |
| 3 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 99 | -0.49 | -0.36 | -0.43 | -6.7 | -6.2 | 0.000 | -6.0 | -1.7 | -6.7 | -2.3 | -6.6 | SR |
| 4 | `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 62 | -0.63 | -0.40 | -0.59 | -6.1 | -5.5 | 0.000 | -4.9 |  | -5.8 | -1.0 | -7.0 |  |
| 5 | `ea_ec_food_ind_sell_price_exp__lvl` | price exp. | 99 | -0.56 | -0.34 | -0.50 | -5.3 | -4.9 | 0.000 | -5.5 | -3.3 | -4.7 | -1.5 | -5.3 | S |
| 6 | `w_gov10y_d4` | rates | 99 | -0.64 | -0.56 | -0.57 | -5.3 | -5.1 | 0.000 | -5.0 | -3.0 | -5.1 | -2.9 | -5.2 | SR |
| 7 | `se_real_wage_yoy_q__d4` | wages/inc. | 99 | +0.49 | +0.50 | +0.43 | +5.3 | +5.0 | 0.000 | +4.2 | +4.7 | +4.5 | +5.4 | +5.5 | SR |
| 8 | `se_cpi_idx__dyoy` | CPI | 99 | -0.56 | -0.57 | -0.50 | -5.2 | -5.0 | 0.000 | -4.2 | -3.1 | -5.2 | -4.6 | -5.4 | SR |
| 9 | `eu_ppi_dom_c103_idx__dyoy` | PPI/input | 95 | -0.34 | -0.30 | -0.31 | -5.2 | -4.9 | 0.000 | -4.9 | -3.2 | -5.1 | -3.9 | -5.3 | SR |
| 10 | `no_ssb_bts_consgoods_home_price_exp__d4` | price exp. | 99 | -0.54 | -0.40 | -0.48 | -4.9 | -4.7 | 0.000 | -4.9 | -3.3 | -3.9 | -2.9 | -5.4 | SR |
| 11 | `no_govbond_10y__d4` | rates | 99 | -0.66 | -0.59 | -0.59 | -4.6 | -4.4 | 0.001 | -4.3 | -3.3 | -4.3 | -2.9 | -4.4 | SR |
| 12 | `se_gov_bond_10y__d4` | rates | 99 | -0.58 | -0.53 | -0.51 | -4.5 | -4.4 | 0.002 | -4.4 | -2.7 | -4.2 | -2.8 | -4.4 | SR |
| 13 | `w_food_ppi_dyoy` | PPI/input | 95 | -0.39 | -0.27 | -0.35 | -4.5 | -4.3 | 0.002 | -3.9 | -1.0 | -4.8 | -3.2 | -4.8 | SR |
| 14 | `w_food_cpi_xvat_dyoy` | CPI | 99 | -0.28 | -0.21 | -0.25 | -4.4 | -4.2 | 0.002 | -5.3 | -1.1 | -4.8 | -3.0 | -5.3 | SR |
| 15 | `nw_food_ppi_dyoy` | PPI/input | 95 | -0.38 | -0.29 | -0.34 | -4.4 | -4.2 | 0.002 | -4.2 | -0.8 | -5.3 | -2.7 | -4.6 | SR |

#### d_margin_r4, real-time h=4 (4 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `natgas_eu_eur_yoy` | energy | 88 | -0.48 | -0.29 | -0.45 | -4.0 | -3.7 | 0.074 | -3.8 | +0.1 | -6.5 | -1.2 | -3.8 |  |
| 2 | `w_ec_food_retail_sell_price_exp_d4` | price exp. | 56 | -0.56 | -0.54 | -0.55 | -4.1 | -3.8 | 0.074 | -3.7 |  | -4.7 | -2.4 | -4.3 |  |
| 3 | `eu_agri_wheat_bread_price__yoy` | commod. | 34 | -0.68 | -0.68 | -0.68 | -4.1 | -3.7 | 0.099 | -4.2 |  | -4.1 |  |  |  |
| 4 | `ea_ec_food_ind_sell_price_exp__d4` | price exp. | 99 | -0.43 | -0.33 | -0.38 | -3.7 | -3.4 | 0.121 | -3.4 | -2.1 | -4.2 | -3.4 | -3.9 | S |
| 5 | `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 60 | -0.38 | -0.26 | -0.36 | -3.6 | -3.3 | 0.141 | -3.3 |  | -3.5 | -0.4 | -4.1 |  |
| 6 | `w_gdp_vol_dyoy` | activity | 99 | -0.36 | -0.28 | -0.32 | -3.4 | -3.1 | 0.164 | -3.6 | -3.2 | -2.3 | -3.7 | -5.1 | S |
| 7 | `no_ppi_food_dom_idx__dyoy` | PPI/input | 94 | -0.25 | -0.11 | -0.22 | -3.4 | -3.2 | 0.164 | -3.1 | -0.0 | -4.2 | -2.0 | -4.5 | S |
| 8 | `se_cpi_idx__dyoy` | CPI | 99 | -0.29 | -0.32 | -0.26 | -3.3 | -3.2 | 0.164 | -4.0 | -1.9 | -3.0 | -1.7 | -3.3 | S |
| 9 | `eu_ppi_paper_packaging_idx__dyoy` | packaging | 93 | -0.34 | -0.30 | -0.31 | -3.2 | -3.1 | 0.164 | -2.7 | -1.4 | -3.3 | -2.2 | -3.4 | S |
| 10 | `eu_ppi_plastic_products_idx__dyoy` | packaging | 93 | -0.42 | -0.30 | -0.38 | -3.2 | -3.0 | 0.164 | -2.7 | -0.6 | -3.8 | -2.9 | -3.2 | S |
| 11 | `eu_ppi_plastic_products_idx__yoy` | packaging | 97 | -0.30 | -0.21 | -0.27 | -3.2 | -3.0 | 0.164 | -5.0 | -0.4 | -4.0 | -0.6 | -3.1 | S |
| 12 | `se_nier_food_mfg_sell_price_exp__d4` | price exp. | 98 | -0.39 | -0.31 | -0.35 | -3.2 | -3.1 | 0.164 | -3.2 | -2.8 | -2.2 | -2.3 | -3.5 | S |
| 13 | `se_cpi_food_idx__dyoy` | CPI | 99 | -0.24 | -0.27 | -0.22 | -3.2 | -3.0 | 0.164 | -4.8 | -1.4 | -3.2 | -2.6 | -3.2 | S |
| 14 | `packaging_eu_dyoy` | packaging | 93 | -0.38 | -0.33 | -0.35 | -3.2 | -3.0 | 0.164 | -2.7 | -1.6 | -3.2 | -2.6 | -3.2 | S |
| 15 | `w_ec_food_ind_sell_price_exp_d4` | price exp. | 99 | -0.34 | -0.27 | -0.31 | -3.1 | -3.0 | 0.175 | -3.6 | -1.6 | -4.4 | -2.6 | -3.4 | S |

#### d_margin_r4: top 10 per alignment on the sample excluding 2021Q3-2023Q4 (ex-infl HAC t)

| # | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| 1 | `w_unemp_d4` +5.0* | `w_unemp_d4` +3.9 | `eu_ppi_dom_c103_idx__dyoy` -5.0* | `se_real_wage_yoy_q__d4` +5.4* | `w_gdp_vol_dyoy` -3.7 |
| 2 | `eu_ppi_dom_c107_idx__yoy` -3.9* | `no_imp_price_food_idx__yoy` +3.6 | `se_real_wage_yoy_q__d4` +4.0* | `se_cpi_idx__dyoy` -4.6* | `no_cpi_food_idx__yoy` +3.5 |
| 3 | `no_imp_price_food_idx__yoy` +3.6 | `eu_ppi_dom_c105_idx__yoy` -3.6 | `se_cpi_idx__dyoy` -3.8 | `eu_ppi_plastic_products_idx__dyoy` -3.9* | `ea_ec_food_ind_sell_price_exp__d4` -3.4 |
| 4 | `w_gdp_vol_yoy` -3.5 | `eu_ppi_dom_c103_idx__dyoy` -3.5 | `no_imp_price_food_idx__yoy` +3.6 | `eu_ppi_dom_c103_idx__dyoy` -3.9* | `ea_negotiated_wages_yoy_q__d4` +3.3 |
| 5 | `eu_ppi_dom_c105_idx__yoy` -3.3 | `eu_ppi_dom_c107_idx__dyoy` -3.3 | `eu_ppi_dom_c106_idx__dyoy` -3.5 | `no_cpi_food_idx__yoy` +3.9* | `w_fx_vs_eur_yoy` +3.1 |
| 6 | `se_cpi_idx__dyoy` -3.2 | `se_cpi_idx__dyoy` -3.2 | `no_jordbruk_malpris_mnok__d4` -3.5 | `eu_ppi_dom_c106_idx__dyoy` -3.7* | `no_ssb_bts_consgoods_home_price_exp__lvl` +2.9 |
| 7 | `se_policy_rate__d4` -3.2 | `se_policy_rate__d4` -3.2 | `eu_ppi_dom_c107_idx__dyoy` -3.3 | `eu_ppi_dom_c105_idx__dyoy` -3.3 | `eu_ppi_plastic_products_idx__dyoy` -2.9 |
| 8 | `w_cpi_dyoy` -3.1 | `w_policy_rate_d4` -3.1 | `eu_ppi_paper_packaging_idx__yoy` -3.1 | `ea_negotiated_wages_yoy_q__lvl` +3.2 | `glob_fao_cereals_idx__dyoy` -2.9 |
| 9 | `w_policy_rate_d4` -3.1 | `w_gdp_vol_yoy` -3.1 | `ea_negotiated_wages_yoy_q__lvl` +3.1 | `w_food_ppi_dyoy` -3.2 | `se_ec_cons_conf__lvl` -2.9 |
| 10 | `no_jordbruk_malpris_mnok__d4` -2.9 | `w_cpi_dyoy` -3.1 | `w_unemp_d4` +3.1 | `eu_ppi_dom_food_mfg_idx__dyoy` -3.2 | `w_cpi_yoy` +2.8 |

Figures: `figures/top10_d_margin_r4_coincident.png`, `figures/top10_d_margin_r4_realtime.png`, `figures/lagprofile_d_margin_r4.png`.

### d_og_r4 (rolling-4Q organic-growth change, pp)

Significance counts:

| family | alignment | tests | q_BY<0.10 | q_BY(lev)<0.10 | q_BY ex-infl<0.10 | q_BY +own lag<0.10 | robust |
|---|---|---|---|---|---|---|---|
| core | coin | 200 | 51 | 48 | 30 | 50 | 42 |
| core | rt0 | 200 | 49 | 45 | 38 | 47 | 43 |
| core | rt1 | 198 | 55 | 50 | 50 | 53 | 48 |
| core | rt2 | 198 | 59 | 54 | 59 | 66 | 50 |
| core | rt4 | 198 | 61 | 53 | 55 | 35 | 51 |
| all | coin | 1408 | 248 | 222 | 135 | 253 | 193 |
| all | rt0 | 1408 | 246 | 218 | 175 | 252 | 199 |
| all | rt1 | 1406 | 253 | 216 | 200 | 252 | 194 |
| all | rt2 | 1406 | 313 | 262 | 256 | 332 | 233 |
| all | rt4 | 1402 | 397 | 356 | 366 | 286 | 326 |

#### d_og_r4, coincident (same quarter, not real-time)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t +base | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `w_cons_conf_z_d4` | cons. survey | 95 | -0.71 | -0.65 | -2.06 | -7.4 | -6.8 | 0.000 | -6.5 | -5.9 | -3.5 | -7.2 | -6.5 | -6.9 | SR |
| 2 | `ea_hicp_food_idx__dyoy` | CPI | 95 | +0.55 | +0.51 | +1.65 | +7.2 | +6.5 | 0.000 | +6.5 | +3.8 | +5.1 | +6.0 | +6.1 | +7.2 | SR |
| 3 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 95 | +0.42 | +0.23 | +1.25 | +7.0 | +6.8 | 0.000 | +5.7 | +3.8 | +2.6 | +5.6 | +3.0 | +9.2 | SR |
| 4 | `eu_ppi_dom_c107_idx__dyoy` | PPI/input | 95 | +0.39 | +0.23 | +1.24 | +6.9 | +6.5 | 0.000 | +5.5 | +1.8 | +3.6 | +5.7 | +4.8 | +7.0 | SR |
| 5 | `eu_ppi_dom_c103_idx__dyoy` | PPI/input | 95 | +0.45 | +0.37 | +1.36 | +6.7 | +6.4 | 0.000 | +5.8 | +2.4 | +2.1 | +6.5 | +4.2 | +7.0 | SR |
| 6 | `se_ec_cons_conf__d4` | cons. survey | 95 | -0.65 | -0.58 | -1.87 | -6.7 | -6.2 | 0.000 | -5.8 | -4.2 | -4.2 | -7.7 | -4.6 | -6.4 | SR |
| 7 | `nw_cons_conf_z_d4` | cons. survey | 95 | -0.72 | -0.68 | -2.17 | -6.6 | -6.1 | 0.000 | -6.1 | -5.2 | -2.6 | -6.9 | -5.3 | -6.3 | SR |
| 8 | `eu_ppi_dom_c108_idx__dyoy` | PPI/input | 95 | +0.53 | +0.51 | +1.63 | +6.1 | +5.5 | 0.000 | +5.9 | +3.4 | +3.4 | +5.2 | +5.2 | +6.4 | SR |
| 9 | `no_ppi_food_dom_idx__dyoy` | PPI/input | 95 | +0.57 | +0.60 | +1.66 | +6.0 | +5.3 | 0.000 | +5.6 | +3.4 | +3.0 | +6.4 | +5.1 | +5.5 | SR |
| 10 | `nw_food_cpi_xvat_dyoy` | CPI | 95 | +0.54 | +0.48 | +1.52 | +5.6 | +5.2 | 0.000 | +5.7 | +3.3 | +3.3 | +6.9 | +3.9 | +5.7 | SR |
| 11 | `nw_food_cpi_dyoy` | CPI | 95 | +0.53 | +0.50 | +1.49 | +5.5 | +5.1 | 0.000 | +5.4 | +3.4 | +3.0 | +6.4 | +3.5 | +5.4 | SR |
| 12 | `nw_food_ppi_dyoy` | PPI/input | 95 | +0.50 | +0.49 | +1.52 | +5.3 | +4.8 | 0.000 | +5.2 | +2.4 | +2.1 | +4.9 | +3.9 | +5.3 | SR |
| 13 | `w_cpi_dyoy` | CPI | 95 | +0.40 | +0.17 | +1.20 | +5.3 | +5.0 | 0.000 | +4.7 | +1.9 | +0.8 | +10.1 | +2.3 | +5.8 | SR |
| 14 | `price_wage_gap_d4` | gap/spread | 95 | +0.55 | +0.52 | +1.62 | +5.3 | +4.8 | 0.000 | +4.8 | +3.0 | +5.6 | +4.5 | +4.2 | +5.3 | SR |
| 15 | `w_food_ppi_dyoy` | PPI/input | 95 | +0.45 | +0.41 | +1.44 | +5.2 | +4.7 | 0.000 | +5.5 | +2.1 | +2.4 | +5.2 | +3.5 | +5.1 | SR |

#### d_og_r4, real-time nowcast h=0 (info at quarter end, before report)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t +base | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_dom_c107_idx__dyoy` | PPI/input | 95 | +0.52 | +0.41 | +1.49 | +8.3 | +7.7 | 0.000 | +8.9 | +3.2 | +9.2 | +5.8 | +7.8 | +7.9 | SR |
| 2 | `eu_ppi_dom_food_mfg_idx__dyoy` | PPI/input | 95 | +0.44 | +0.34 | +1.41 | +7.6 | +7.2 | 0.000 | +7.8 | +2.5 | +3.7 | +5.6 | +5.3 | +7.5 | SR |
| 3 | `w_cons_conf_z_d4` | cons. survey | 95 | -0.71 | -0.65 | -2.06 | -7.4 | -6.8 | 0.000 | -6.5 | -5.9 | -3.5 | -7.2 | -6.5 | -6.9 | SR |
| 4 | `price_cost_gap_ppi` | gap/spread | 95 | -0.51 | -0.45 | -1.50 | -7.2 | -7.0 | 0.000 | -6.3 | -3.0 | -3.9 | -5.6 | -4.6 | -8.0 | SR |
| 5 | `nw_price_cost_gap_ppi` | gap/spread | 95 | -0.55 | -0.52 | -1.60 | -7.1 | -6.8 | 0.000 | -6.6 | -3.6 | -3.7 | -6.7 | -4.7 | -7.7 | SR |
| 6 | `se_ec_cons_conf__d4` | cons. survey | 95 | -0.65 | -0.58 | -1.87 | -6.7 | -6.2 | 0.000 | -5.8 | -4.2 | -4.2 | -7.7 | -4.6 | -6.4 | SR |
| 7 | `se_ppi_food_hmpi_idx__dyoy` | PPI/input | 95 | +0.49 | +0.37 | +1.41 | +6.6 | +6.2 | 0.000 | +6.4 | +2.7 | +5.6 | +5.0 | +5.1 | +6.7 | SR |
| 8 | `nw_cons_conf_z_d4` | cons. survey | 95 | -0.72 | -0.68 | -2.17 | -6.6 | -6.1 | 0.000 | -6.1 | -5.2 | -2.6 | -6.9 | -5.3 | -6.3 | SR |
| 9 | `eu_ppi_dom_c103_idx__dyoy` | PPI/input | 95 | +0.52 | +0.50 | +1.47 | +6.1 | +5.7 | 0.000 | +6.6 | +3.5 | +4.9 | +3.9 | +7.5 | +6.2 | SR |
| 10 | `no_ppi_food_dom_idx__dyoy` | PPI/input | 95 | +0.57 | +0.60 | +1.66 | +6.0 | +5.3 | 0.000 | +5.6 | +3.4 | +3.0 | +6.4 | +5.1 | +5.5 | SR |
| 11 | `eu_ppi_dom_c106_idx__yoy` | PPI/input | 95 | +0.57 | +0.52 | +1.62 | +5.7 | +5.4 | 0.000 | +5.4 | +3.5 | +4.2 | +4.7 | +4.6 | +5.7 | SR |
| 12 | `nw_food_cpi_xvat_dyoy` | CPI | 95 | +0.54 | +0.48 | +1.52 | +5.6 | +5.2 | 0.000 | +5.7 | +3.3 | +3.3 | +6.9 | +3.9 | +5.7 | SR |
| 13 | `w_cpi_dyoy` | CPI | 95 | +0.50 | +0.32 | +1.38 | +5.6 | +5.3 | 0.000 | +6.5 | +2.9 | +1.9 | +6.5 | +3.8 | +5.4 | SR |
| 14 | `w_real_wage_dyoy` | wages/inc. | 95 | -0.55 | -0.49 | -1.61 | -5.5 | -5.3 | 0.000 | -5.1 | -3.2 | -2.1 | -5.6 | -3.9 | -5.7 | SR |
| 15 | `ea_hicp_food_idx__dyoy` | CPI | 95 | +0.59 | +0.61 | +1.69 | +5.5 | +4.9 | 0.000 | +5.9 | +4.1 | +8.4 | +6.2 | +6.0 | +5.5 | SR |

#### d_og_r4, real-time h=1 (1 quarter ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t +base | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `se_cpi_idx__dyoy` | CPI | 95 | +0.51 | +0.41 | +1.43 | +7.1 | +6.7 | 0.000 | +6.8 | +3.5 | +2.5 | +6.1 | +5.6 | +7.0 | SR |
| 2 | `eu_ppi_dom_food_mfg_idx__dyoy` | PPI/input | 95 | +0.53 | +0.45 | +1.53 | +7.0 | +6.5 | 0.000 | +8.1 | +3.5 | +7.3 | +5.2 | +7.3 | +7.1 | SR |
| 3 | `se_real_wage_yoy_q__d4` | wages/inc. | 95 | -0.46 | -0.41 | -1.29 | -6.7 | -6.3 | 0.000 | -6.1 | -3.1 | -2.9 | -5.0 | -6.6 | -6.6 | SR |
| 4 | `price_cost_gap_ppi` | gap/spread | 95 | -0.54 | -0.49 | -1.53 | -6.3 | -6.0 | 0.000 | -7.0 | -3.7 | -3.4 | -4.1 | -4.1 | -6.5 | SR |
| 5 | `nw_price_cost_gap_ppi` | gap/spread | 95 | -0.57 | -0.54 | -1.60 | -6.2 | -6.0 | 0.000 | -7.5 | -4.1 | -3.2 | -5.0 | -4.2 | -6.4 | SR |
| 6 | `eu_ppi_dom_c106_idx__dyoy` | PPI/input | 95 | +0.51 | +0.49 | +1.54 | +6.2 | +5.9 | 0.000 | +6.2 | +2.9 | +3.8 | +5.8 | +4.8 | +6.1 | SR |
| 7 | `w_cons_conf_z_d4` | cons. survey | 95 | -0.63 | -0.61 | -1.86 | -5.9 | -5.4 | 0.000 | -5.7 | -5.5 | -3.3 | -5.9 | -6.7 | -5.6 | SR |
| 8 | `price_cost_gap_fao_wloc` | gap/spread | 95 | -0.48 | -0.44 | -1.48 | -5.6 | -5.4 | 0.000 | -4.9 | -2.3 | -4.3 | -4.0 | -4.0 | -5.4 | SR |
| 9 | `se_ppi_food_hmpi_idx__dyoy` | PPI/input | 95 | +0.54 | +0.47 | +1.52 | +5.6 | +5.2 | 0.000 | +6.2 | +3.7 | +15.3 | +6.5 | +7.0 | +5.6 | SR |
| 10 | `eu_ppi_dom_c107_idx__dyoy` | PPI/input | 95 | +0.55 | +0.51 | +1.55 | +5.5 | +5.1 | 0.000 | +6.4 | +3.8 | +8.5 | +4.6 | +7.7 | +5.5 | SR |
| 11 | `se_ec_cons_conf__d4` | cons. survey | 95 | -0.65 | -0.65 | -1.88 | -5.5 | -5.0 | 0.000 | -5.2 | -4.5 | -4.2 | -6.3 | -5.4 | -5.3 | SR |
| 12 | `nw_cons_conf_z_d4` | cons. survey | 95 | -0.63 | -0.62 | -1.94 | -5.4 | -5.0 | 0.000 | -5.9 | -5.1 | -2.3 | -6.1 | -5.6 | -5.1 | SR |
| 13 | `w_ec_food_ind_sell_price_exp_d4` | price exp. | 95 | +0.41 | +0.33 | +1.32 | +5.4 | +5.1 | 0.000 | +4.8 | +2.1 | +2.8 | +4.4 | +3.8 | +5.9 | SR |
| 14 | `no_ppi_food_dom_idx__dyoy` | PPI/input | 95 | +0.61 | +0.66 | +1.75 | +5.3 | +4.8 | 0.000 | +5.1 | +3.3 | +5.0 | +5.2 | +5.4 | +5.6 | SR |
| 15 | `glob_wb_food_idx_nok__yoy` | commod. | 95 | +0.55 | +0.54 | +1.58 | +5.2 | +5.0 | 0.000 | +5.3 | +3.6 | +4.3 | +3.4 | +5.1 | +5.4 | SR |

#### d_og_r4, real-time h=2 (2 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t +base | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_ppi_dom_c106_idx__dyoy` | PPI/input | 95 | +0.55 | +0.53 | +1.59 | +8.8 | +8.3 | 0.000 | +9.8 | +5.1 | +7.6 | +5.4 | +7.3 | +8.6 | SR |
| 2 | `eu_ppi_plastic_products_idx__dyoy` | packaging | 95 | +0.48 | +0.35 | +1.44 | +6.8 | +6.2 | 0.000 | +6.8 | +2.2 | +2.5 | +6.2 | +6.0 | +6.6 | SR |
| 3 | `price_cost_gap_fao_wloc` | gap/spread | 95 | -0.60 | -0.54 | -1.74 | -6.3 | -6.1 | 0.000 | -5.8 | -3.2 | -3.8 | -5.4 | -5.3 | -6.3 | SR |
| 4 | `eu_agri_wheat_bread_price__yoy` | commod. | 36 | +0.63 | +0.47 | +1.75 | +7.5 | +6.8 | 0.000 | +6.7 | +0.6 |  | +7.5 |  |  |  |
| 5 | `w_ec_food_ind_sell_price_exp_d4` | price exp. | 95 | +0.55 | +0.48 | +1.61 | +6.1 | +5.9 | 0.000 | +6.0 | +3.2 | +3.7 | +5.8 | +5.3 | +6.2 | SR |
| 6 | `ea_ec_food_ind_sell_price_exp__d4` | price exp. | 95 | +0.39 | +0.30 | +1.34 | +6.1 | +5.8 | 0.000 | +5.9 | +2.0 | +3.2 | +4.6 | +4.1 | +5.9 | SR |
| 7 | `w_gdp_vol_yoy` | activity | 95 | +0.52 | +0.54 | +1.57 | +5.5 | +5.0 | 0.000 | +4.6 | +3.1 | +4.0 | +3.6 | +5.3 | +5.8 | SR |
| 8 | `no_ssb_bts_consgoods_home_price_exp__d4` | price exp. | 95 | +0.56 | +0.56 | +1.59 | +5.5 | +5.2 | 0.000 | +4.8 | +3.0 | +2.7 | +5.5 | +3.9 | +5.1 | SR |
| 9 | `no_ppi_food_dom_idx__dyoy` | PPI/input | 95 | +0.53 | +0.56 | +1.50 | +5.5 | +5.1 | 0.000 | +6.3 | +3.2 | +2.0 | +6.1 | +5.7 | +5.4 | SR |
| 10 | `no_retail_foodstores_vol_sa_idx__dyoy` | activity | 95 | -0.45 | -0.23 | -1.24 | -5.5 | -5.0 | 0.000 | -4.1 | -2.8 | +1.7 | -14.2 | -1.6 | -4.9 |  |
| 11 | `glob_wb_food_idx_eur__yoy` | commod. | 95 | +0.52 | +0.45 | +1.49 | +5.4 | +5.2 | 0.000 | +5.3 | +3.3 | +4.6 | +3.5 | +4.6 | +5.6 | SR |
| 12 | `glob_wb_food_idx_nok__yoy` | commod. | 95 | +0.55 | +0.52 | +1.55 | +5.3 | +5.1 | 0.000 | +5.7 | +4.0 | +3.7 | +3.7 | +5.0 | +5.4 | SR |
| 13 | `packaging_eu_dyoy` | packaging | 95 | +0.48 | +0.41 | +1.40 | +5.2 | +4.8 | 0.000 | +5.8 | +2.1 | +3.7 | +4.8 | +4.8 | +4.9 | SR |
| 14 | `wb_food_wloc_yoy` | commod. | 95 | +0.55 | +0.50 | +1.55 | +5.2 | +5.0 | 0.000 | +5.3 | +3.8 | +4.1 | +3.6 | +4.5 | +5.4 | SR |
| 15 | `price_cost_gap_fao_nok` | gap/spread | 95 | -0.58 | -0.51 | -1.66 | -5.1 | -4.9 | 0.000 | -5.7 | -3.1 | -3.0 | -5.8 | -4.3 | -5.2 | SR |

#### d_og_r4, real-time h=4 (4 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t +base | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `eu_agri_wheat_bread_price__yoy` | commod. | 34 | +0.66 | +0.69 | +2.24 | +9.7 | +8.1 | 0.000 | +6.4 | +1.7 |  | +9.7 |  |  |  |
| 2 | `w_ec_cons_price_exp_d4` | price exp. | 95 | +0.46 | +0.44 | +1.46 | +7.2 | +6.9 | 0.000 | +4.8 | +3.0 | +7.5 | +5.7 | +8.0 | +7.2 | SR |
| 3 | `eu_ppi_dom_c108_idx__yoy` | PPI/input | 95 | -0.36 | -0.32 | -1.28 | -6.0 | -5.2 | 0.000 | -3.3 | -0.5 | -0.6 | -5.6 | -5.0 | -6.2 | SR |
| 4 | `ea_ec_food_ind_sell_price_exp__d4` | price exp. | 95 | +0.56 | +0.50 | +1.61 | +5.7 | +5.4 | 0.000 | +5.2 | +3.5 | +12.9 | +4.1 | +7.0 | +5.6 | SR |
| 5 | `w_food_cpi_rel_yoy` | CPI | 95 | -0.42 | -0.41 | -1.40 | -5.7 | -5.4 | 0.000 | -5.4 | -2.0 | -4.7 | -4.9 | -4.3 | -5.5 | SR |
| 6 | `w_retail_total_vol_yoy` | activity | 95 | +0.38 | +0.35 | +1.18 | +5.6 | +5.4 | 0.000 | +4.4 | +1.0 | +1.4 | +7.0 | +4.9 | +5.6 | SR |
| 7 | `glob_fao_ffpi_eur__dyoy` | commod. | 95 | +0.45 | +0.42 | +1.34 | +5.2 | +5.0 | 0.000 | +3.2 | +2.3 | +3.2 | +3.7 | +4.7 | +5.0 | SR |
| 8 | `fao_ffpi_sek_dyoy` | commod. | 95 | +0.54 | +0.51 | +1.52 | +5.1 | +4.9 | 0.000 | +3.6 | +2.7 | +2.7 | +4.4 | +4.5 | +4.8 | SR |
| 9 | `se_ec_cons_conf__lvl` | cons. survey | 95 | +0.33 | +0.33 | +1.20 | +4.9 | +4.6 | 0.001 | +2.5 | -0.2 | +2.3 | +3.9 | +5.3 | +4.9 | SR |
| 10 | `ea_hicp_food_idx__yoy` | CPI | 95 | -0.40 | -0.44 | -1.40 | -4.8 | -4.1 | 0.001 | -3.6 | -0.8 | -2.6 | -4.5 | -4.4 | -4.8 | SR |
| 11 | `eu_ppi_dom_c103_idx__yoy` | PPI/input | 95 | -0.33 | -0.31 | -1.15 | -4.8 | -4.6 | 0.001 | -2.3 | -0.2 | -0.6 | -5.8 | -4.6 | -4.6 | SR |
| 12 | `fao_ffpi_wloc_dyoy` | commod. | 95 | +0.47 | +0.44 | +1.36 | +4.8 | +4.6 | 0.001 | +3.0 | +2.3 | +2.5 | +4.3 | +4.2 | +4.5 | SR |
| 13 | `w_gdp_vol_dyoy` | activity | 95 | +0.45 | +0.38 | +1.28 | +4.5 | +4.1 | 0.002 | +3.0 | +3.4 | +4.5 | +4.2 | +5.9 | +4.5 | SR |
| 14 | `w_cons_conf_z` | cons. survey | 95 | +0.37 | +0.39 | +1.23 | +4.5 | +4.2 | 0.002 | +2.2 | -0.5 | +3.0 | +3.2 | +5.4 | +4.3 | SR |
| 15 | `glob_wb_food_idx_eur__dyoy` | commod. | 95 | +0.45 | +0.41 | +1.30 | +4.5 | +4.3 | 0.002 | +3.9 | +2.5 | +2.1 | +3.8 | +4.1 | +4.4 | SR |

#### d_og_r4: top 10 per alignment on the sample excluding 2021Q3-2023Q4 (ex-infl HAC t)

| # | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| 1 | `w_cons_conf_z_d4` -6.5* | `eu_ppi_dom_c107_idx__dyoy` +7.8* | `eu_ppi_dom_c107_idx__dyoy` +7.7* | `se_ppi_food_hmpi_idx__dyoy` +8.2* | `w_ec_cons_price_exp_d4` +8.0* |
| 2 | `ea_hicp_food_idx__dyoy` +6.1* | `eu_ppi_dom_c103_idx__dyoy` +7.5* | `eu_ppi_dom_food_mfg_idx__dyoy` +7.3* | `se_cpi_idx__dyoy` +7.5* | `ea_ec_food_ind_sell_price_exp__d4` +7.0* |
| 3 | `nw_cons_conf_z_d4` -5.3* | `w_cons_conf_z_d4` -6.5* | `se_ppi_food_hmpi_idx__dyoy` +7.0* | `eu_ppi_dom_c106_idx__dyoy` +7.3* | `w_gdp_vol_dyoy` +5.9* |
| 4 | `eu_ppi_dom_c108_idx__dyoy` +5.2* | `ea_hicp_food_idx__dyoy` +6.0* | `w_cons_conf_z_d4` -6.7* | `se_real_wage_yoy_q__d4` -7.0* | `w_cons_conf_z` +5.4* |
| 5 | `no_ppi_food_dom_idx__dyoy` +5.1* | `nw_cons_conf_z_d4` -5.3* | `se_real_wage_yoy_q__d4` -6.6* | `eu_ppi_dom_food_mfg_idx__dyoy` +6.9* | `se_ec_cons_conf__lvl` +5.3* |
| 6 | `eu_ppi_dom_c107_idx__dyoy` +4.8* | `eu_ppi_dom_food_mfg_idx__dyoy` +5.3* | `eu_ppi_dom_c103_idx__dyoy` +6.4* | `eu_ppi_dom_c107_idx__dyoy` +6.8* | `eu_ppi_dom_c108_idx__yoy` -5.0* |
| 7 | `se_ec_cons_conf__d4` -4.6* | `se_ppi_food_hmpi_idx__dyoy` +5.1* | `ea_hicp_food_idx__dyoy` +5.8* | `se_ec_cons_conf__d4` -6.1* | `no_ssb_bts_consgoods_home_price_exp__d4` +4.9* |
| 8 | `no_vat_food_rate__d4` +4.4* | `no_ppi_food_dom_idx__dyoy` +5.1* | `packaging_eu_yoy` +5.7* | `eu_ppi_plastic_products_idx__dyoy` +6.0* | `w_retail_total_vol_yoy` +4.9* |
| 9 | `glob_wb_food_idx_nok__yoy` +4.3* | `eu_ppi_paper_packaging_idx__yoy` +4.9* | `se_cpi_idx__dyoy` +5.6* | `packaging_eu_yoy` +5.7* | `nw_cons_conf_z` +4.8* |
| 10 | `no_ppi_food_dom_idx__yoy` +4.2* | `nw_price_cost_gap_ppi` -4.7* | `nw_cons_conf_z_d4` -5.6* | `no_ppi_food_dom_idx__dyoy` +5.7* | `eu_ppi_plastic_products_idx__dyoy` +4.7* |

Figures: `figures/top10_d_og_r4_coincident.png`, `figures/top10_d_og_r4_realtime.png`, `figures/lagprofile_d_og_r4.png`.

### vol_proxy (implied volume/mix = og - Orkla-weighted food CPI ex VAT, pp)

Significance counts:

| family | alignment | tests | q_BY<0.10 | q_BY(lev)<0.10 | q_BY ex-infl<0.10 | q_BY +own lag<0.10 | robust |
|---|---|---|---|---|---|---|---|
| core | coin | 200 | 12 | 9 | 2 | 16 | 4 |
| core | rt0 | 200 | 10 | 7 | 0 | 15 | 0 |
| core | rt1 | 198 | 0 | 0 | 0 | 6 | 0 |
| core | rt2 | 198 | 0 | 0 | 1 | 1 | 0 |
| core | rt4 | 198 | 0 | 0 | 0 | 0 | 0 |
| all | coin | 1408 | 67 | 29 | 10 | 96 | 13 |
| all | rt0 | 1408 | 55 | 24 | 6 | 108 | 7 |
| all | rt1 | 1406 | 21 | 3 | 1 | 81 | 0 |
| all | rt2 | 1406 | 11 | 1 | 4 | 70 | 0 |
| all | rt4 | 1402 | 9 | 8 | 15 | 29 | 1 |

#### vol_proxy, coincident (same quarter, not real-time)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `w_food_cpi_xvat_yoy` | CPI | 102 | -0.40 | -0.26 | -1.37 | -6.9 | -6.3 | 0.000 | -6.4 | -0.7 | -10.1 | -1.7 | -5.9 | S |
| 2 | `w_food_cpi_yoy` | CPI | 102 | -0.40 | -0.25 | -1.35 | -6.8 | -6.1 | 0.000 | -6.2 | -0.7 | -9.9 | -1.6 | -5.9 | S |
| 3 | `se_na_hhcons_food_sa__yoy` | activity | 102 | +0.49 | +0.37 | +1.66 | +6.4 | +6.0 | 0.000 | +5.8 | +1.1 | +9.5 | +3.6 | +4.5 | SR |
| 4 | `nw_food_cpi_xvat_yoy` | CPI | 102 | -0.40 | -0.20 | -1.38 | -5.3 | -4.8 | 0.000 | -5.5 | -1.3 | -7.4 | -1.5 | -4.6 | S |
| 5 | `se_cpi_food_idx__yoy` | CPI | 102 | -0.35 | -0.20 | -1.25 | -5.1 | -4.5 | 0.000 | -4.8 | -1.8 | -5.4 | -1.5 | -4.4 | S |
| 6 | `se_retail_grocery_vol_sa_idx__dyoy` | activity | 102 | +0.47 | +0.43 | +1.56 | +5.1 | +4.6 | 0.000 | +4.3 | +2.4 | +4.2 | +4.9 | +4.6 | SR |
| 7 | `nw_food_cpi_yoy` | CPI | 102 | -0.39 | -0.19 | -1.35 | -5.0 | -4.5 | 0.000 | -5.2 | -1.5 | -7.0 | -1.2 | -4.4 | S |
| 8 | `se_na_hhcons_food_sa__dyoy` | activity | 102 | +0.40 | +0.37 | +1.35 | +3.9 | +3.7 | 0.021 | +3.7 | +1.5 | +3.6 | +4.2 | +3.3 | SR |
| 9 | `nw_food_cpi_xvat_dyoy` | CPI | 102 | -0.36 | -0.26 | -1.20 | -3.9 | -3.4 | 0.021 | -3.4 | +0.3 | -4.3 | -1.7 | -3.4 |  |
| 10 | `se_retail_grocery_vol_sa_idx__yoy` | activity | 102 | +0.42 | +0.30 | +1.44 | +3.8 | +3.6 | 0.031 | +3.4 | +2.3 | +6.0 | +2.2 | +3.3 | SR |
| 11 | `glob_gscpi__d4` | packaging | 102 | +0.41 | +0.31 | +1.30 | +3.6 | +3.4 | 0.046 | +4.1 | +0.4 | +3.7 | +1.0 | +3.8 | S |
| 12 | `w_food_cpi_rel_yoy` | CPI | 102 | -0.44 | -0.34 | -1.45 | -3.6 | -3.4 | 0.050 | -3.4 | -0.4 | -7.1 | -1.2 | -3.5 | S |
| 13 | `ea_hicp_food_idx__yoy` | CPI | 102 | -0.29 | -0.09 | -1.09 | -3.3 | -2.9 | 0.105 | -3.3 | +2.3 | -5.9 | -0.4 | -3.0 |  |
| 14 | `w_retail_total_vol_yoy` | activity | 102 | +0.34 | +0.19 | +1.14 | +3.3 | +3.0 | 0.115 | +3.3 | +2.6 | +4.9 | +1.3 | +3.1 | S |
| 15 | `nw_food_cpi_dyoy` | CPI | 102 | -0.33 | -0.19 | -1.11 | -3.3 | -2.8 | 0.115 | -2.7 | +1.7 | -4.2 | -1.0 | -2.8 |  |

#### vol_proxy, real-time nowcast h=0 (info at quarter end, before report)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `w_food_ppi_yoy` | PPI/input | 101 | -0.36 | -0.17 | -1.23 | -5.5 | -4.8 | 0.000 | -5.4 | +0.0 | -7.9 | -1.2 | -5.2 |  |
| 2 | `nw_food_cpi_xvat_yoy` | CPI | 102 | -0.40 | -0.20 | -1.38 | -5.3 | -4.8 | 0.000 | -5.5 | -1.3 | -7.4 | -1.5 | -4.6 | S |
| 3 | `se_cpi_food_idx__yoy` | CPI | 102 | -0.35 | -0.20 | -1.25 | -5.1 | -4.5 | 0.001 | -4.8 | -1.8 | -5.4 | -1.5 | -4.4 | S |
| 4 | `nw_food_cpi_yoy` | CPI | 102 | -0.39 | -0.19 | -1.35 | -5.0 | -4.5 | 0.001 | -5.2 | -1.5 | -7.0 | -1.2 | -4.4 | S |
| 5 | `w_food_cpi_yoy` | CPI | 102 | -0.39 | -0.30 | -1.34 | -4.2 | -3.9 | 0.013 | -4.5 | -0.6 | -4.7 | -1.4 | -4.1 | S |
| 6 | `w_food_cpi_xvat_yoy` | CPI | 102 | -0.39 | -0.28 | -1.33 | -4.2 | -3.9 | 0.013 | -4.5 | -0.4 | -4.7 | -1.4 | -4.0 | S |
| 7 | `nw_food_ppi_yoy` | PPI/input | 101 | -0.31 | -0.03 | -1.11 | -3.9 | -3.4 | 0.024 | -4.2 | -0.2 | -5.8 | +0.2 | -3.8 |  |
| 8 | `nw_food_cpi_xvat_dyoy` | CPI | 102 | -0.36 | -0.26 | -1.20 | -3.9 | -3.4 | 0.024 | -3.4 | +0.3 | -4.3 | -1.7 | -3.4 |  |
| 9 | `w_food_cpi_rel_yoy` | CPI | 102 | -0.41 | -0.34 | -1.35 | -3.8 | -3.6 | 0.032 | -3.7 | -0.9 | -7.7 | -1.4 | -3.7 | S |
| 10 | `glob_gscpi__d4` | packaging | 102 | +0.41 | +0.31 | +1.30 | +3.6 | +3.4 | 0.051 | +4.1 | +0.4 | +3.7 | +1.0 | +3.8 | S |
| 11 | `nw_food_cpi_dyoy` | CPI | 102 | -0.33 | -0.19 | -1.11 | -3.3 | -2.8 | 0.148 | -2.7 | +1.7 | -4.2 | -1.0 | -2.8 |  |
| 12 | `eu_ppi_dom_c107_idx__yoy` | PPI/input | 101 | -0.30 | -0.15 | -1.13 | -3.2 | -3.0 | 0.148 | -3.6 | +1.3 | -5.4 | -0.9 | -2.9 |  |
| 13 | `natgas_eu_eur_dyoy` | energy | 80 | +0.36 | +0.32 | +1.23 | +3.3 | +3.0 | 0.148 | +3.9 | +1.8 | +3.1 | +0.8 | +3.1 | S |
| 14 | `ea_hicp_food_idx__yoy` | CPI | 101 | -0.32 | -0.20 | -1.14 | -3.2 | -3.0 | 0.148 | -3.7 | +1.2 | -4.2 | -0.7 | -2.9 |  |
| 15 | `w_gov10y_lvl` | rates | 102 | -0.29 | -0.29 | -1.07 | -3.1 | -3.0 | 0.191 | -3.5 | -0.0 | -3.2 | -2.8 | -2.3 | S |

#### vol_proxy, real-time h=1 (1 quarter ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `se_cpi_food_idx__yoy` | CPI | 102 | -0.34 | -0.17 | -1.20 | -3.9 | -3.7 | 0.179 | -4.5 | -1.6 | -4.2 | -0.9 | -3.9 | S |
| 2 | `w_food_ppi_yoy` | PPI/input | 100 | -0.33 | -0.19 | -1.10 | -3.5 | -3.2 | 0.284 | -4.4 | -0.2 | -3.9 | -0.7 | -3.4 | S |
| 3 | `se_na_hhcons_food_sa__yoy` | activity | 102 | +0.33 | +0.32 | +1.06 | +3.4 | +3.2 | 0.284 | +3.9 | +0.5 | +3.7 | +2.5 | +3.1 | S |
| 4 | `eu_agri_basket_wloc_yoy` | commod. | 100 | -0.37 | -0.26 | -1.24 | -3.3 | -3.1 | 0.284 | -3.2 | +1.0 | -5.8 | -1.7 | -3.2 |  |
| 5 | `nw_food_cpi_yoy` | CPI | 102 | -0.35 | -0.21 | -1.24 | -3.3 | -3.1 | 0.284 | -3.9 | -1.5 | -3.9 | -0.8 | -3.0 | S |
| 6 | `nw_food_cpi_xvat_yoy` | CPI | 102 | -0.35 | -0.19 | -1.21 | -3.3 | -3.0 | 0.284 | -3.9 | -1.0 | -3.8 | -0.7 | -2.9 | S |
| 7 | `nw_food_cpi_xvat_dyoy` | CPI | 102 | -0.39 | -0.28 | -1.25 | -3.2 | -3.0 | 0.284 | -3.0 | +0.3 | -3.4 | -0.9 | -2.9 |  |
| 8 | `eu_ppi_paper_packaging_idx__yoy` | packaging | 100 | -0.29 | -0.05 | -1.04 | -3.1 | -2.7 | 0.332 | -3.1 | +0.7 | -4.1 | -0.2 | -2.9 |  |
| 9 | `w_food_cpi_rel_yoy` | CPI | 102 | -0.24 | -0.23 | -0.77 | -2.9 | -2.8 | 0.445 | -3.0 | -2.2 | -3.8 | -0.7 | -3.3 | S |
| 10 | `eu_agri_basket_yoy` | commod. | 100 | -0.35 | -0.29 | -1.21 | -2.9 | -2.7 | 0.445 | -2.8 | +1.3 | -5.0 | -1.8 | -2.9 |  |
| 11 | `nw_food_cpi_dyoy` | CPI | 102 | -0.36 | -0.24 | -1.20 | -2.9 | -2.7 | 0.445 | -2.6 | +1.0 | -3.4 | -0.6 | -2.6 |  |
| 12 | `eu_ppi_dom_food_mfg_idx__yoy` | PPI/input | 100 | -0.32 | -0.22 | -1.09 | -2.8 | -2.6 | 0.445 | -2.9 | +1.0 | -5.7 | -0.8 | -2.8 |  |
| 13 | `no_ppi_food_dom_idx__yoy` | PPI/input | 101 | -0.28 | -0.02 | -0.95 | -2.8 | -2.4 | 0.445 | -3.2 | -1.6 | -3.0 | +0.6 | -2.9 |  |
| 14 | `nw_food_ppi_yoy` | PPI/input | 100 | -0.28 | -0.07 | -0.97 | -2.8 | -2.6 | 0.445 | -3.7 | -0.4 | -3.3 | +0.2 | -2.7 |  |
| 15 | `w_gov10y_lvl` | rates | 102 | -0.27 | -0.27 | -1.00 | -2.8 | -2.7 | 0.445 | -3.2 | +0.2 | -2.8 | -2.6 | -2.0 |  |

#### vol_proxy, real-time h=2 (2 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `w_ec_food_retail_sell_price_exp_lvl` | price exp. | 62 | -0.39 | -0.22 | -1.57 | -4.1 | -3.5 | 0.145 | -4.2 |  | -4.1 | -1.2 | -4.2 |  |
| 2 | `w_gov10y_d4` | rates | 102 | -0.29 | -0.17 | -1.10 | -3.2 | -3.0 | 1.000 | -3.6 | -2.7 | -4.1 | -2.2 | -3.2 | S |
| 3 | `eu_agri_basket_wloc_yoy` | commod. | 99 | -0.31 | -0.20 | -1.06 | -2.8 | -2.6 | 1.000 | -3.0 | +1.1 | -5.2 | -1.1 | -2.7 |  |
| 4 | `eu_agri_basket_yoy` | commod. | 99 | -0.32 | -0.27 | -1.12 | -2.7 | -2.5 | 1.000 | -2.8 | +1.9 | -5.8 | -1.3 | -2.6 |  |
| 5 | `se_cpi_food_idx__yoy` | CPI | 102 | -0.27 | -0.23 | -0.93 | -2.6 | -2.3 | 1.000 | -3.7 | -2.5 | -2.6 | -0.7 | -2.5 | S |
| 6 | `w_gov10y_lvl` | rates | 102 | -0.24 | -0.27 | -0.90 | -2.5 | -2.4 | 1.000 | -2.9 | +0.1 | -2.8 | -2.4 | -1.6 |  |
| 7 | `se_gov_bond_10y__d4` | rates | 102 | -0.26 | -0.19 | -0.99 | -2.5 | -2.3 | 1.000 | -2.8 | -1.8 | -3.1 | -1.8 | -2.7 | S |
| 8 | `no_qna_hh_food_cons_sa_mnok__dyoy` | activity | 102 | +0.29 | +0.14 | +0.94 | +2.5 | +2.2 | 1.000 | +2.5 | +0.4 | +2.3 | +0.1 | +1.5 | S |
| 9 | `no_earn_idx_food_manuf_q__dyoy` | wages/inc. | 102 | -0.24 | -0.25 | -0.77 | -2.4 | -2.3 | 1.000 | -2.0 | -2.8 | -1.3 | -2.6 | -2.0 | S |
| 10 | `no_ppi_food_dom_idx__yoy` | PPI/input | 100 | -0.26 | -0.11 | -0.87 | -2.4 | -2.2 | 1.000 | -3.1 | -1.8 | -2.5 | +0.4 | -2.1 |  |
| 11 | `w_ec_food_retail_sell_price_exp_d4` | price exp. | 58 | -0.34 | -0.24 | -1.33 | -2.3 | -2.0 | 1.000 | -1.9 |  | -2.2 | -1.7 | -2.3 |  |
| 12 | `se_gov_bond_10y__lvl` | rates | 102 | -0.23 | -0.25 | -0.81 | -2.2 | -2.2 | 1.000 | -2.8 | +0.3 | -2.9 | -2.5 | -1.3 |  |
| 13 | `no_govbond_10y__d4` | rates | 102 | -0.22 | -0.13 | -0.92 | -2.2 | -2.1 | 1.000 | -2.5 | -2.1 | -2.8 | -1.9 | -2.4 | S |
| 14 | `eu_ppi_plastic_products_idx__yoy` | packaging | 99 | -0.26 | -0.15 | -0.89 | -2.2 | -1.9 | 1.000 | -2.2 | +2.0 | -3.4 | +0.2 | -1.9 |  |
| 15 | `us_ppi_corrugated_boxes_idx__yoy` | packaging | 102 | -0.26 | -0.18 | -0.94 | -2.2 | -2.0 | 1.000 | -2.7 | -0.1 | -3.1 | -1.1 | -2.0 | S |

#### vol_proxy, real-time h=4 (4 quarters ahead)

| # | feature | cat | n | r | rho | b x 1sd | t HAC | t lev | q BY | t +own lag | t 01-12 | t 13-26 | t ex-infl | t ex-covid | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `no_retail_foodstores_vol_sa_idx__dyoy` | activity | 93 | +0.40 | +0.17 | +1.34 | +3.0 | +2.8 | 1.000 | +2.8 | -0.3 | +3.1 | -0.7 | +2.6 |  |
| 2 | `se_retail_grocery_vol_sa_idx__dyoy` | activity | 102 | -0.27 | -0.24 | -1.00 | -2.7 | -2.6 | 1.000 | -2.6 | -0.1 | -2.8 | -1.9 | -2.8 | S |
| 3 | `se_retail_grocery_vol_sa_idx__yoy` | activity | 102 | -0.23 | -0.23 | -0.78 | -2.6 | -2.5 | 1.000 | -2.4 | -0.6 | -1.6 | -2.0 | -2.8 | S |
| 4 | `elec_nordic_loc_yoy` | energy | 100 | -0.28 | -0.21 | -0.96 | -2.5 | -2.3 | 1.000 | -2.5 | -0.8 | -2.2 | -1.0 | -1.8 | S |
| 5 | `elec_nordic_loc_dyoy` | energy | 96 | -0.22 | -0.20 | -0.73 | -2.5 | -2.3 | 1.000 | -2.5 | -0.7 | -2.4 | -2.0 | -1.8 | S |
| 6 | `ea_ec_food_ind_sell_price_exp__lvl` | price exp. | 102 | -0.29 | -0.25 | -1.02 | -2.5 | -2.3 | 1.000 | -2.6 | +0.7 | -3.8 | -0.8 | -2.2 |  |
| 7 | `w_fx_vs_nok_yoy` | FX | 102 | -0.19 | -0.16 | -0.72 | -2.4 | -2.3 | 1.000 | -2.4 | +2.0 | -2.7 | -1.7 | -1.8 |  |
| 8 | `natgas_eu_eur_yoy` | energy | 89 | -0.27 | -0.18 | -0.93 | -2.3 | -2.1 | 1.000 | -2.5 | +0.8 | -2.7 | -0.7 | -1.9 |  |
| 9 | `w_hh_real_inc_dyoy` | wages/inc. | 65 | -0.30 | -0.30 | -1.14 | -2.2 | -2.0 | 1.000 | -2.2 |  | -2.2 | -1.2 | -2.1 |  |
| 10 | `no_qna_hh_food_cons_sa_mnok__dyoy` | activity | 102 | +0.30 | +0.14 | +1.04 | +2.1 | +1.9 | 1.000 | +2.2 | +0.3 | +2.2 | -1.6 | +1.7 |  |
| 11 | `no_retail_foodstores_vol_sa_idx__yoy` | activity | 97 | +0.27 | +0.05 | +0.97 | +2.1 | +1.9 | 1.000 | +2.3 | -1.2 | +3.0 | -2.0 | +1.3 |  |
| 12 | `se_wage_idx_m__yoy` | wages/inc. | 102 | -0.23 | -0.25 | -0.78 | -2.1 | -2.0 | 1.000 | -2.4 | -0.5 | -2.4 | -2.6 | -1.4 | S |
| 13 | `w_food_cpi_xvat_dyoy` | CPI | 102 | +0.13 | +0.02 | +0.46 | +2.0 | +1.8 | 1.000 | +1.2 | -0.3 | +1.8 | +2.1 | +2.1 |  |
| 14 | `glob_fao_meat_idx__yoy` | commod. | 102 | -0.29 | -0.26 | -0.94 | -2.0 | -1.9 | 1.000 | -2.0 | +0.3 | -2.6 | -1.0 | -1.6 |  |
| 15 | `no_fx_eurnok__yoy` | FX | 102 | +0.19 | +0.18 | +0.69 | +1.9 | +1.9 | 1.000 | +2.1 | -3.6 | +3.4 | +1.4 | +1.4 |  |

#### vol_proxy: top 10 per alignment on the sample excluding 2021Q3-2023Q4 (ex-infl HAC t)

| # | coin | rt0 | rt1 | rt2 | rt4 |
|---|---|---|---|---|---|
| 1 | `se_retail_grocery_vol_sa_idx__dyoy` +4.9* | `nw_real_wage_yoy` -3.7 | `se_gov_bond_10y__lvl` -2.6 | `no_earn_idx_food_manuf_q__yoy` -4.1* | `se_real_wage_yoy_q__d4` -4.1 |
| 2 | `se_na_hhcons_food_sa__dyoy` +4.2* | `no_real_wage_qna_yoy_q__lvl` -3.3 | `w_gov10y_lvl` -2.6 | `no_real_wage_qna_yoy_q__lvl` -3.1 | `w_cpi_dyoy` +3.7 |
| 3 | `se_na_hhcons_food_sa__yoy` +3.6 | `us_ppi_corrugated_boxes_idx__yoy` -2.9 | `us_ppi_corrugated_boxes_idx__dyoy` -2.5 | `eu_ppi_dom_c108_idx__dyoy` +3.0 | `eu_ppi_dom_c107_idx__dyoy` +3.4 |
| 4 | `ea_negotiated_wages_yoy_q__d4` +3.2 | `se_gov_bond_10y__lvl` -2.9 | `se_na_hhcons_food_sa__yoy` +2.5 | `no_earn_idx_food_manuf_q__dyoy` -2.6 | `se_cpi_idx__dyoy` +3.0 |
| 5 | `se_gov_bond_10y__lvl` -2.9 | `w_gov10y_lvl` -2.8 | `packaging_eu_dyoy` -2.4 | `se_gov_bond_10y__lvl` -2.5 | `w_food_ppi_dyoy` +2.9 |
| 6 | `w_gov10y_lvl` -2.8 | `w_real_wage_yoy` -2.7 | `eu_ppi_paper_packaging_idx__dyoy` -2.4 | `w_gov10y_lvl` -2.4 | `eu_ppi_dom_c103_idx__dyoy` +2.9 |
| 7 | `us_ppi_corrugated_boxes_idx__yoy` -2.7 | `us_ppi_corrugated_boxes_idx__dyoy` -2.6 | `us_ppi_corrugated_boxes_idx__yoy` -2.3 | `se_real_wage_yoy_q__d4` -2.3 | `eu_ppi_paper_packaging_idx__dyoy` +2.9 |
| 8 | `no_earn_idx_food_manuf_q__yoy` -2.7 | `no_govbond_10y__lvl` -2.6 | `no_govbond_10y__lvl` -2.3 | `w_gov10y_d4` -2.2 | `nw_food_ppi_dyoy` +2.7 |
| 9 | `se_wage_idx_m__dyoy` +2.7 | `nw_real_wage_dyoy` -2.4 | `eu_ppi_plastic_products_idx__dyoy` -2.2 | `se_wage_idx_m__yoy` -2.1 | `se_wage_idx_m__yoy` -2.6 |
| 10 | `no_govbond_10y__lvl` -2.6 | `eu_ppi_paper_packaging_idx__dyoy` -2.4 | `packaging_us_yoy` -2.2 | `eu_ppi_dom_c103_idx__dyoy` +2.1 | `packaging_eu_dyoy` +2.6 |

Figures: `figures/top10_vol_proxy_coincident.png`, `figures/top10_vol_proxy_realtime.png`, `figures/lagprofile_vol_proxy.png`.

## 6. All 1,420 features (second family)

**How to read this family**
- BY within each target x alignment family is over about 1,400 tests.
- Many hits are country-level duplicates of core composites: individual HICPs, PPIs, and EC survey balances for single countries.
- The series that are new relative to the core set:
  - EC selling-price expectations for industry and retail (DE, EA, SE, CZ).
  - OECD business confidence (G7, DE, SE).
  - Euro-area GDP and compensation per employee.
  - Swedish retail grocery *value*.
  - The Norwegian NAV unemployment level.
- **Likely spurious or very-small-weight series:** Romanian, Latvian and Lithuanian bond yields, the Czech policy rate, Norwegian cross-border shopping (from 2009), short EU cereal series (n < 40) and the Norwegian agricultural frame (annual).

#### All features, d_margin, coin

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `packaging_eu_yoy` | packaging | yes | 102 | -9.6 | -9.1 | 0.000 | -6.9 | -3.1 | SR |
| 2 | `eu_ppi_plastic_products_idx__yoy` | packaging | yes | 102 | -8.6 | -7.9 | 0.000 | -7.0 | -2.6 | SR |
| 3 | `eu_ppi_paper_packaging_idx__yoy` | packaging | yes | 102 | -8.4 | -8.0 | 0.000 | -6.1 | -2.8 | SR |
| 4 | `ea_comp_per_employee_q__dyoy` | wages/inc. |  | 102 | -7.0 | -6.5 | 0.000 | -6.1 | -7.5 | SR |
| 5 | `de_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | -6.9 | -6.4 | 0.000 | -6.7 | -2.3 | SR |
| 6 | `ea_ppi_paper_idx__yoy` | packaging |  | 102 | -6.5 | -6.1 | 0.000 | -5.2 | -2.4 | SR |
| 7 | `eu_agri_barley_malting_price__yoy` | commod. |  | 38 | -7.6 | -6.8 | 0.000 | -7.9 |  |  |
| 8 | `ea_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | -6.1 | -5.8 | 0.000 | -6.4 | -2.1 | SR |
| 9 | `eu_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | -6.0 | -5.7 | 0.000 | -6.4 | -2.1 | SR |
| 10 | `ea_real_negotiated_wages_yoy_q__lvl` | wages/inc. |  | 102 | +5.8 | +5.1 | 0.000 | +5.9 | +1.6 | S |

#### All features, d_margin, rt1

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `de_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | -6.6 | -6.0 | 0.000 | -7.7 | -1.4 | S |
| 2 | `no_nav_unemp_level_sa__dyoy` | labour |  | 98 | +5.9 | +5.6 | 0.000 | +4.9 | +3.5 | SR |
| 3 | `ee_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | -5.5 | -5.2 | 0.001 | -5.6 | -3.1 | SR |
| 4 | `ea_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | -5.5 | -5.1 | 0.001 | -7.0 | -1.4 | S |
| 5 | `ee_ec_food_ind_sell_price_exp__lvl` | price exp. |  | 63 | -5.6 | -4.8 | 0.001 | -5.1 | -1.1 |  |
| 6 | `eu_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | -5.3 | -4.9 | 0.001 | -6.9 | -1.3 | S |
| 7 | `eu_agri_barley_malting_price__yoy` | commod. |  | 37 | -5.9 | -5.1 | 0.002 | -4.6 |  |  |
| 8 | `lt_ec_food_ind_sell_price_exp__lvl` | price exp. |  | 85 | -5.0 | -4.7 | 0.005 | -5.7 | -3.2 | SR |
| 9 | `at_gdp_vol_idx__dyoy` | activity |  | 102 | -4.9 | -4.5 | 0.005 | -4.4 | -2.4 | SR |
| 10 | `at_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | -4.6 | -4.3 | 0.012 | -5.4 | -1.4 | S |

#### All features, d_margin, rt4

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `no_nav_unemp_rate_sa__lvl` | labour |  | 58 | -5.6 | -5.3 | 0.008 | -4.4 | -6.3 |  |
| 2 | `lv_ec_ind_sell_price_exp__d4` | price exp. |  | 98 | -4.0 | -3.8 | 0.568 | -4.0 | -4.1 | S |
| 3 | `at_ec_ind_sell_price_exp__d4` | price exp. |  | 102 | -3.8 | -3.5 | 0.568 | -3.7 | -2.8 | S |
| 4 | `se_retail_total_vol_idx__yoy` | activity |  | 102 | -3.8 | -3.6 | 0.568 | -3.4 | -3.7 | S |
| 5 | `eu_ppi_dom_c103_idx__yoy` | PPI/input | yes | 97 | +3.7 | +3.6 | 0.568 | +3.1 | +4.8 | S |
| 6 | `pl_retail_total_vol_idx__dyoy` | activity |  | 93 | -3.7 | -3.5 | 0.568 | -3.8 | -3.1 | S |
| 7 | `se_na_hhcons_food_sa__yoy` | activity | yes | 102 | -3.7 | -3.5 | 0.568 | -3.2 | -3.6 | S |
| 8 | `glob_wb_wheat_us_srw__dyoy` | commod. |  | 102 | -3.6 | -3.5 | 0.568 | -3.8 | -3.5 | S |
| 9 | `ee_ec_ind_sell_price_exp__d4` | price exp. |  | 98 | -3.6 | -3.4 | 0.568 | -3.1 | -2.8 | S |
| 10 | `lt_gov_bond_10y__d4` | rates |  | 94 | +3.6 | +3.4 | 0.594 | +3.1 | +4.1 | S |

#### All features, og, coin

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `se_cpi_food_ready_other_idx__yoy` | CPI |  | 102 | +11.7 | +11.1 | 0.000 | +10.1 | +2.8 | SR |
| 2 | `se_cpi_food_idx__yoy` | CPI | yes | 102 | +11.5 | +11.0 | 0.000 | +11.7 | +3.5 | SR |
| 3 | `se_hicp_food_idx__yoy` | CPI |  | 102 | +11.5 | +10.9 | 0.000 | +11.6 | +4.0 | SR |
| 4 | `se_hicp_food_bev_idx__yoy` | CPI |  | 102 | +10.4 | +9.9 | 0.000 | +10.4 | +3.2 | SR |
| 5 | `se_cpi_food_nab_idx__yoy` | CPI |  | 102 | +10.4 | +9.9 | 0.000 | +10.5 | +3.1 | SR |
| 6 | `se_cpi_food_cereals_bread_idx__yoy` | CPI |  | 102 | +9.1 | +8.8 | 0.000 | +8.4 | +3.8 | SR |
| 7 | `no_ppi_food_dom_idx__yoy` | PPI/input | yes | 102 | +9.1 | +8.5 | 0.000 | +8.5 | +1.6 | S |
| 8 | `de_hicp_food_idx__yoy` | CPI |  | 102 | +9.0 | +8.7 | 0.000 | +7.6 | +1.1 | S |
| 9 | `de_hicp_food_bev_idx__yoy` | CPI |  | 102 | +8.8 | +8.5 | 0.000 | +7.6 | +1.2 | S |
| 10 | `w_food_cpi_yoy` | CPI | yes | 102 | +8.6 | +8.0 | 0.000 | +8.9 | +2.1 | SR |

#### All features, og, rt1

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `se_ec_retail_sell_price_exp__lvl` | price exp. |  | 91 | +9.0 | +8.4 | 0.000 | +9.1 | +3.0 | SR |
| 2 | `se_cpi_food_nab_idx__yoy` | CPI |  | 102 | +8.5 | +7.7 | 0.000 | +8.3 | +3.5 | SR |
| 3 | `se_cpi_food_idx__yoy` | CPI | yes | 102 | +8.3 | +7.6 | 0.000 | +8.0 | +3.7 | SR |
| 4 | `se_cpi_food_cereals_bread_idx__yoy` | CPI |  | 102 | +7.7 | +7.1 | 0.000 | +7.0 | +3.6 | SR |
| 5 | `cz_ec_retail_sell_price_exp__lvl` | price exp. |  | 91 | +7.7 | +7.3 | 0.000 | +9.5 | +3.2 | SR |
| 6 | `no_ppi_food_dom_idx__yoy` | PPI/input | yes | 101 | +7.5 | +7.1 | 0.000 | +6.7 | +1.2 | S |
| 7 | `at_ec_retail_sell_price_exp__lvl` | price exp. |  | 91 | +7.4 | +7.1 | 0.000 | +7.2 | +2.3 | SR |
| 8 | `se_cpif_idx__yoy` | CPI |  | 102 | +7.1 | +6.9 | 0.000 | +6.7 | +1.5 | S |
| 9 | `cz_policy_rate__d4` | rates |  | 102 | +7.0 | +6.8 | 0.000 | +7.6 | +2.4 | SR |
| 10 | `ea_ec_retail_sell_price_exp__lvl` | price exp. |  | 102 | +6.8 | +6.5 | 0.000 | +6.9 | +1.3 | S |

#### All features, og, rt4

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `cz_ec_retail_sell_price_exp__lvl` | price exp. |  | 88 | +6.8 | +6.4 | 0.000 | +7.3 | +3.3 | SR |
| 2 | `se_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | +6.4 | +6.1 | 0.000 | +5.9 | +2.6 | SR |
| 3 | `de_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | +6.0 | +5.6 | 0.000 | +5.8 | +2.1 | SR |
| 4 | `se_oecd_bci__lvl` | bus. survey |  | 102 | +5.5 | +5.2 | 0.001 | +5.0 | +4.8 | SR |
| 5 | `ea_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | +5.2 | +4.9 | 0.003 | +4.9 | +1.5 | S |
| 6 | `eu_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | +5.1 | +4.9 | 0.003 | +4.8 | +1.5 | S |
| 7 | `at_ec_ind_sell_price_exp__lvl` | price exp. |  | 102 | +5.0 | +4.7 | 0.003 | +4.9 | +1.4 | S |
| 8 | `eu_agri_barley_malting_price__yoy` | commod. |  | 34 | +5.7 | +4.8 | 0.004 | +4.7 |  |  |
| 9 | `lt_gov_bond_10y__lvl` | rates |  | 98 | -4.8 | -4.7 | 0.007 | -4.8 | -4.8 | SR |
| 10 | `se_exp_wage_1y_all__d4` | wages/inc. |  | 75 | +4.7 | +4.4 | 0.012 | +4.5 | +4.0 | SR |

#### All features, d_og, coin

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `se_retail_grocery_value_idx__dyoy` | activity |  | 98 | +7.1 | +6.6 | 0.000 | +8.7 | +7.1 | SR |
| 2 | `fi_hicp_food_bev_idx__dyoy` | CPI |  | 98 | +6.9 | +6.4 | 0.000 | +7.3 | +5.7 | SR |
| 3 | `fi_hicp_food_idx__dyoy` | CPI |  | 98 | +6.7 | +6.3 | 0.000 | +7.9 | +5.5 | SR |
| 4 | `se_na_hhcons_food_cp_sa__dyoy` | activity |  | 98 | +6.4 | +6.0 | 0.000 | +7.2 | +5.5 | SR |
| 5 | `dk_ec_cons_price_past_12m__d4` | cons. survey |  | 98 | +6.0 | +5.6 | 0.000 | +6.4 | +4.3 | SR |
| 6 | `fi_oecd_cci__d4` | cons. survey |  | 98 | -5.9 | -5.1 | 0.000 | -6.3 | -4.9 | SR |
| 7 | `sk_hicp_all_idx__dyoy` | CPI |  | 98 | +5.6 | +5.3 | 0.000 | +7.0 | +4.8 | SR |
| 8 | `price_wage_gap_d4` | gap/spread | yes | 98 | +5.6 | +5.2 | 0.000 | +6.1 | +4.4 | SR |
| 9 | `price_cost_gap_ppi` | gap/spread | yes | 98 | -5.6 | -5.1 | 0.000 | -5.8 | -3.7 | SR |
| 10 | `eu_ppi_dom_c107_idx__dyoy` | PPI/input | yes | 98 | +5.5 | +5.2 | 0.000 | +5.9 | +5.3 | SR |

#### All features, d_og, rt1

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `no_retail_foodstores_vol_sa_idx__dyoy` | activity | yes | 96 | -6.7 | -5.7 | 0.000 | -7.2 | -2.5 |  |
| 2 | `no_retail_food_vol_idx__dyoy` | activity |  | 96 | -6.6 | -5.7 | 0.000 | -7.2 | -2.3 |  |
| 3 | `ea_ec_retail_sell_price_exp__d4` | price exp. |  | 98 | +6.6 | +6.0 | 0.000 | +6.7 | +6.9 | SR |
| 4 | `eu_ppi_dom_c106_idx__dyoy` | PPI/input | yes | 96 | +6.4 | +6.1 | 0.000 | +5.5 | +5.6 | SR |
| 5 | `at_ec_cons_price_exp_12m__lvl` | price exp. |  | 98 | +6.4 | +6.0 | 0.000 | +7.1 | +4.4 | SR |
| 6 | `eu_ec_food_retail_sell_price_exp__d4` | price exp. |  | 98 | +6.2 | +5.8 | 0.000 | +6.8 | +5.5 | SR |
| 7 | `eu_ec_retail_sell_price_exp__d4` | price exp. |  | 93 | +6.2 | +5.6 | 0.000 | +6.5 | +7.3 | SR |
| 8 | `ea_ec_food_retail_sell_price_exp__d4` | price exp. |  | 98 | +6.1 | +5.8 | 0.000 | +6.6 | +5.3 | SR |
| 9 | `sk_ec_cons_price_past_12m__d4` | cons. survey |  | 98 | +5.9 | +5.6 | 0.000 | +5.3 | +5.5 | SR |
| 10 | `ea_ppi_dom_food_mfg_idx__dyoy` | PPI/input |  | 98 | +5.8 | +5.5 | 0.000 | +7.8 | +6.2 | SR |

#### All features, d_og, rt4

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `ee_retail_total_vol_idx__dyoy` | activity |  | 98 | +8.0 | +7.3 | 0.000 | +7.8 | +8.8 | SR |
| 2 | `ee_ec_ind_sell_price_exp__d4` | price exp. |  | 98 | +7.8 | +7.3 | 0.000 | +7.3 | +5.7 | SR |
| 3 | `g7_oecd_bci__d4` | bus. survey |  | 98 | +7.2 | +6.7 | 0.000 | +6.7 | +6.2 | SR |
| 4 | `at_ec_ind_sell_price_exp__d4` | price exp. |  | 98 | +6.7 | +6.3 | 0.000 | +6.6 | +5.4 | SR |
| 5 | `de_oecd_bci__d4` | bus. survey |  | 98 | +6.7 | +6.2 | 0.000 | +6.8 | +5.8 | SR |
| 6 | `se_oecd_bci__d4` | bus. survey |  | 98 | +6.6 | +6.0 | 0.000 | +6.4 | +6.4 | SR |
| 7 | `lt_ec_ind_sell_price_exp__d4` | price exp. |  | 98 | +6.6 | +6.2 | 0.000 | +7.0 | +6.7 | SR |
| 8 | `se_cpi_food_fruit_nuts_idx__yoy` | CPI |  | 98 | -6.6 | -6.2 | 0.000 | -6.5 | -5.9 | SR |
| 9 | `eu_ppi_dom_c108_idx__yoy` | PPI/input | yes | 97 | -6.6 | -6.2 | 0.000 | -7.0 | -4.9 | SR |
| 10 | `eu_ec_ind_sell_price_exp__d4` | price exp. |  | 98 | +6.5 | +6.2 | 0.000 | +7.4 | +5.3 | SR |

#### All features, vol_proxy, coin

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `w_food_cpi_xvat_yoy` | CPI | yes | 102 | -6.9 | -6.3 | 0.000 | -6.4 | -1.7 | S |
| 2 | `w_food_cpi_yoy` | CPI | yes | 102 | -6.8 | -6.1 | 0.000 | -6.2 | -1.6 | S |
| 3 | `se_cpi_food_dairy_eggs_idx__yoy` | CPI |  | 102 | -6.5 | -6.0 | 0.000 | -5.1 | -2.3 |  |
| 4 | `se_na_hhcons_food_sa__yoy` | activity | yes | 102 | +6.4 | +6.0 | 0.000 | +5.8 | +3.6 | SR |
| 5 | `no_jordbruk_ramme_mnok__lvl` | tax/policy |  | 100 | -5.9 | -5.2 | 0.000 | -5.9 | -1.0 | S |
| 6 | `nw_food_cpi_xvat_yoy` | CPI | yes | 102 | -5.3 | -4.8 | 0.001 | -5.5 | -1.5 | S |
| 7 | `hu_retail_total_vol_idx__yoy` | activity |  | 102 | +5.2 | +5.0 | 0.002 | +5.7 | +4.2 | SR |
| 8 | `no_nbes_hh_infl_exp_2_3y__lvl` | price exp. |  | 98 | -5.2 | -5.0 | 0.002 | -6.5 | -4.7 | SR |
| 9 | `se_cpi_food_idx__yoy` | CPI | yes | 102 | -5.1 | -4.5 | 0.002 | -4.8 | -1.5 | S |
| 10 | `se_retail_grocery_vol_sa_idx__dyoy` | activity | yes | 102 | +5.1 | +4.6 | 0.002 | +4.3 | +4.9 | SR |

#### All features, vol_proxy, rt1

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `se_nier_hh_infl_exp_12m_median__lvl` | price exp. |  | 44 | -6.4 | -5.5 | 0.001 | -9.9 | -3.4 |  |
| 2 | `se_cpi_food_dairy_eggs_idx__yoy` | CPI |  | 102 | -5.6 | -5.2 | 0.001 | -5.6 | -2.5 |  |
| 3 | `dk_hicp_all_idx__yoy` | CPI |  | 102 | -5.3 | -4.9 | 0.003 | -5.6 | -1.9 |  |
| 4 | `lt_hicp_all_idx__yoy` | CPI |  | 102 | -4.6 | -4.2 | 0.035 | -5.1 | -2.1 | S |
| 5 | `ee_hicp_all_idx__yoy` | CPI |  | 102 | -4.5 | -4.2 | 0.046 | -4.8 | -1.6 |  |
| 6 | `hu_ec_retail_conf__lvl` | bus. survey |  | 102 | +4.4 | +4.2 | 0.049 | +4.1 | +3.8 | S |
| 7 | `us_ppi_metal_cans_idx__yoy` | packaging |  | 102 | -4.3 | -3.8 | 0.049 | -4.3 | -2.7 | S |
| 8 | `fi_hicp_all_idx__yoy` | CPI |  | 102 | -4.3 | -4.0 | 0.049 | -5.7 | -1.9 |  |
| 9 | `no_jordbruk_ramme_mnok__lvl` | tax/policy |  | 99 | -4.3 | -3.8 | 0.049 | -6.0 | -0.8 | S |
| 10 | `lv_gov_bond_10y__lvl` | rates |  | 101 | -4.2 | -4.0 | 0.051 | -4.6 | -4.9 | S |

#### All features, vol_proxy, rt4

| # | feature | cat | core | n | t HAC | t lev | q BY | t +own lag | t ex-infl | flags |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `no_border_trade_exp_mnok_s1__yoy` | activity |  | 72 | -10.3 | -9.7 | 0.000 | -9.0 | -0.6 | S |
| 2 | `no_border_trade_trips_s1__yoy` | activity |  | 72 | -7.7 | -7.1 | 0.000 | -7.5 | +1.1 |  |
| 3 | `de_hh_saving_rate__d4` | wages/inc. |  | 101 | +6.6 | +5.5 | 0.000 | +7.2 | +1.7 |  |
| 4 | `no_border_trade_trips_s1__dyoy` | activity |  | 68 | -6.7 | -5.7 | 0.000 | -6.3 | +0.2 |  |
| 5 | `no_border_trade_exp_mnok_s1__dyoy` | activity |  | 68 | -6.1 | -4.7 | 0.000 | -5.7 | -1.6 | S |
| 6 | `se_hhcons_ind_old_total_sa__dyoy` | activity |  | 93 | -4.8 | -4.4 | 0.009 | -4.5 | -0.9 |  |
| 7 | `ea_hh_saving_rate__d4` | wages/inc. |  | 101 | +4.8 | +4.4 | 0.009 | +5.3 | +0.2 |  |
| 8 | `ro_gov_bond_10y__lvl` | rates |  | 81 | -4.7 | -4.5 | 0.015 | -7.5 | -5.0 | SR |
| 9 | `no_retail_foodstores_val_sa_idx__dyoy` | activity |  | 93 | +4.4 | +4.0 | 0.032 | +4.2 | +0.6 |  |
| 10 | `eu_hh_saving_rate__d4` | wages/inc. |  | 101 | +4.1 | +3.8 | 0.101 | +4.4 | -0.4 |  |

The secondary targets in the all-feature family are in `screen_results_all.csv`.

## 7. Implied volume/mix proxy: validation

`vol_proxy` = og - `w_food_cpi_xvat_yoy` (same quarter). It is checked against Orkla's reported price and volume/mix split, which exists from 2022Q2 only. Note that 2022Q2 is on the E basis inside a D row.

| sample | n | corr_price_vs_w_food_cpi_xvat | corr_price_vs_nw_food_cpi_xvat | corr_volmix_vs_proxy | mae_volmix_vs_proxy | mean_bias_proxy_minus_volmix |
|---|---|---|---|---|---|---|
| 2022Q2-2026Q2 | 17 | 0.923 | 0.954 | 0.826 | 1.85 | -0.347 |
| 2022Q3-2026Q2 | 16 | 0.923 | 0.958 | 0.794 | 1.956 | -0.378 |

**How well the proxy works**
- The proxy tracks the direction of reported volume/mix well (r about 0.8). The weighted food CPI tracks Orkla's price effect at r about 0.92 (0.95-0.96 for the Nordic variant).
- **It fails in 2025.** Consumer food inflation (about 4%) ran ahead of Orkla's own pricing (about 1%), so the proxy understated volume by about 3pp per quarter. Before 2022 there is no ground truth.
- **Mechanical correlations.** Any feature correlated with food CPI correlates negatively with the proxy. The coincident food-CPI hits for `vol_proxy` are partly mechanical.

## 8. Caveats and notes on the shared module

**Data caveats**
- **Latest-vintage data.** Publication lags are respected, but revisions are not. National accounts, preliminary wages and seasonal factors are latest vintage.
- **Look-ahead in the inputs.** The Orkla-weighted composites use geographic weights from annual reports published after year end (mild look-ahead). Confidence z-scores use full-sample scaling.
- **Definition mix.**
  - India is inside the headline in 2014Q4-2022Q2. Rieber, Hamé and Eastern acquisitions are inside `d_margin`.
  - The 2015-16 organic growth includes distribution agreements.
  - 2001-05 organic growth is low precision (quality C, down-weighted).
  - Definition-break dummies and quality weights handle these only partly.
- **Episode dominance.** 2022-23 is the only large cost shock with a well-measured response. The ex-infl columns are the honest test, and several "top" features are much weaker there (e.g. packaging PPI t falls from about -9 to about -3).
- **Easter.** `easter_shift` is a proxy. Sell-in timing makes the effect sign-ambiguous (methodology section 5.3).
- **Redundancy.** Many features are near-duplicates (FAO and WB indices in several currencies; packaging sub-indices). BY is valid under positive dependence, but the effective number of independent signals is much smaller than the test count. The figures de-duplicate at |corr| > 0.9.

**Notes on `common.py`** (not modified; worked around locally)
1. `d_og_r4` = og_r4_t - og_r4_{t-4} uses the headline `og_est` shifted by 4 quarters, not the same-report comparatives. It therefore compares across definitions whenever any quarter in the 8-quarter window crosses a break: 2008Q1-2009Q1, 2013Q1-2015Q4 and 2022Q3-2024Q1. That includes the D->E break that `d_og` itself avoids, where E is compared with D including India. `load_targets` provides no break flag for it. I built `d_og_r4_break` (a rolling 4-quarter max of def_id(t) != def_id(t-4)) and used it as a control.
2. `nw_ols` drops NaN and zero-weight rows before the HAC sum, so quarters on either side of a gap (e.g. the excluded 2021Q3-2023Q4 window) are treated as adjacent in the Newey-West lags. The effect is minor. My numpy estimator does the same, for consistency.
3. `align()` falls back to a 1-quarter lag for any feature missing from the dictionary. This never triggers for panel features.

## 9. Files

| file | content |
|---|---|
| `screen_results_core.csv` | 200 core features x 6 targets x 5 alignments (6,000 rows), all statistics and q-values |
| `screen_results_all.csv` | 1,420 features x 6 targets x 5 alignments (42,600 rows) |
| `lag_profiles.csv` | core features x targets x k = 0..6: r, b, HAC t, leverage-adjusted t, ex-infl t, incremental t |
| `lag_best.csv` | best lag per target x feature with full profiles and BY q over the lag family |
| `figures/top10_<target>_{coincident,realtime}.png` | scatter + time-series overlay for the top 10 distinct features |
| `figures/lagprofile_<target>.png` | heatmap of t by lag for the top 15 features |
| `figure_selection.csv` | features and alignments shown in the figures |
| `vol_proxy_validation.csv`, `vol_proxy_series_2022on.csv` | proxy vs reported price and volume/mix |
| `hac_validation.csv` | numpy HAC vs common.nw_ols check |
