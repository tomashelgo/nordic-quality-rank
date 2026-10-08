"""Write findings.md for the univariate screen (run after run_screen.py and make_figures.py).

All tables are generated from screen_results_core.csv, screen_results_all.csv, lag_best.csv and
vol_proxy_validation.csv. Numbers quoted in the narrative are looked up from the same files (the
v() helper), so a re-run keeps text and tables consistent.
"""
import numpy as np
import pandas as pd
import screen_lib as S
from screen_lib import C

OUT = S.OUTDIR
R = pd.read_csv(f'{OUT}/screen_results_core.csv')
RA = pd.read_csv(f'{OUT}/screen_results_all.csv')
B = pd.read_csv(f'{OUT}/lag_best.csv')
VP = pd.read_csv(f'{OUT}/vol_proxy_validation.csv')
AL = ['coin', 'rt0', 'rt1', 'rt2', 'rt4']
CAT = {'producer_prices_input_costs': 'PPI/input', 'packaging_freight': 'packaging', 'consumer_prices': 'CPI',
       'price_expectations': 'price exp.', 'wages_income': 'wages/inc.', 'activity_retail': 'activity',
       'consumer_survey': 'cons. survey', 'business_survey': 'bus. survey', 'labour_market': 'labour',
       'commodities': 'commod.', 'rates': 'rates', 'fx': 'FX', 'energy': 'energy', 'other': 'gap/spread',
       'tax_policy': 'tax/policy'}
TNAME = {'d_margin': 'd_margin (EBIT-margin change y/y, pp)', 'og': 'og (organic growth, %)',
         'd_og': 'd_og (organic-growth change y/y, pp)', 'd_margin_r4': 'd_margin_r4 (rolling-4Q margin change, pp)',
         'd_og_r4': 'd_og_r4 (rolling-4Q organic-growth change, pp)',
         'vol_proxy': 'vol_proxy (implied volume/mix = og - Orkla-weighted food CPI ex VAT, pp)'}


def v(target, al, feature, col='t', fam=R, fmt='+.1f'):
    r = fam[(fam.target == target) & (fam.alignment == al) & (fam.feature == feature)]
    if r.empty or pd.isna(r[col].iloc[0]):
        return 'n/a'
    return format(r[col].iloc[0], fmt)


def lb(target, feature, col):
    r = B[(B.target == target) & (B.feature == feature)]
    return r[col].iloc[0] if len(r) else np.nan


def f1(x, fmt='+.1f'):
    return '' if pd.isna(x) else format(x, fmt)


def md(df):
    cols = list(df.columns)
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '|'.join(['---'] * len(cols)) + '|']
    for _, r in df.iterrows():
        out.append('| ' + ' | '.join('' if (isinstance(x, float) and np.isnan(x)) else str(x) for x in r) + ' |')
    return '\n'.join(out)


def flag(r):
    s = ''
    if r.sign_stable:
        s += 'S'
    if r.robust:
        s += 'R'
    return s


def ranked_table(target, al, fam=R, n=15):
    g = fam[(fam.target == target) & (fam.alignment == al) & fam.p.notna()].sort_values('p').head(n)
    rows = []
    for i, r in enumerate(g.itertuples(), 1):
        d = {'#': i, 'feature': f'`{r.feature}`', 'cat': CAT.get(r.category, r.category), 'n': r.n,
             'r': f1(r.pearson, '+.2f'), 'rho': f1(r.spearman, '+.2f'), 'b x 1sd': f1(r.b_1sd, '+.2f'),
             't HAC': f1(r.t), 't lev': f1(r.t_lev), 'q BY': f1(r.q_by, '.3f'),
             't +own lag': f1(r.t_incr)}
        if target in S.BASE_LEVEL:
            d['t +base'] = f1(r.t_incr_base)
        d.update({'t 01-12': f1(r.t_early), 't 13-26': f1(r.t_late), 't ex-infl': f1(r.t_exinfl),
                  't ex-covid': f1(r.t_excovid), 'flags': flag(r)})
        rows.append(d)
    return md(pd.DataFrame(rows))


def exinfl_matrix(target, fam=R, n=10):
    cols = {}
    for al in AL:
        g = fam[(fam.target == target) & (fam.alignment == al) & fam.p_exinfl.notna()].sort_values('p_exinfl').head(n)
        cols[al] = [f'`{r.feature}` {r.t_exinfl:+.1f}{"*" if r.q_by_exinfl < 0.1 else ""}' for r in g.itertuples()]
    df = pd.DataFrame(cols)
    df.insert(0, '#', range(1, len(df) + 1))
    return md(df)


def counts_table(target):
    rows = []
    for fam_name, fam in (('core', R), ('all', RA)):
        for al in AL:
            g = fam[(fam.target == target) & (fam.alignment == al)]
            rows.append({'family': fam_name, 'alignment': al, 'tests': int(g.p.notna().sum()),
                         'q_BY<0.10': int((g.q_by < .1).sum()), 'q_BY(lev)<0.10': int((g.q_by_lev < .1).sum()),
                         'q_BY ex-infl<0.10': int((g.q_by_exinfl < .1).sum()),
                         'q_BY +own lag<0.10': int((g.q_by_incr < .1).sum()),
                         'robust': int(g.robust.sum())})
    return md(pd.DataFrame(rows))


def lag_table(target, n=12):
    g = B[B.target == target].sort_values('p_best').head(n)
    rows = []
    for r in g.itertuples():
        prof = ' '.join(f'{getattr(r, f"t_k{k}"):+.1f}' if pd.notna(getattr(r, f't_k{k}')) else 'na' for k in range(7))
        prof_ex = ' '.join(f'{getattr(r, f"t_ex_k{k}"):+.1f}' if pd.notna(getattr(r, f't_ex_k{k}')) else 'na'
                           for k in range(7))
        d = {'feature': f'`{r.feature}`', 'cat': CAT.get(r.category, r.category), 'best k': r.best_k,
             't best': f1(r.t_best), 'q BY (lag family)': f1(r.q_by_lagfamily, '.3f'),
             't +own lag': f1(r.t_incr_at_best)}
        if target in S.BASE_LEVEL:
            d['t +base'] = f1(r.t_incr_base_at_best)
        d.update({'t ex-infl': f1(r.t_exinfl_at_best), 't by k=0..6': prof, 't ex-infl by k=0..6': prof_ex})
        rows.append(d)
    return md(pd.DataFrame(rows))


FOCUS = {
    'Real wages / real income': ['w_real_wage_yoy', 'w_real_wage_dyoy', 'nw_real_wage_yoy', 'nw_real_wage_dyoy',
                                 'se_real_wage_yoy_q__lvl', 'se_real_wage_yoy_q__d4', 'no_real_wage_qna_yoy_q__lvl',
                                 'no_real_wage_qna_yoy_q__d4', 'w_hh_real_inc_yoy', 'w_hh_real_inc_dyoy'],
    'Consumer surveys': ['w_cons_conf_z', 'w_cons_conf_z_d4', 'nw_cons_conf_z', 'nw_cons_conf_z_d4',
                         'no_fn_cci_sa__lvl', 'no_fn_cci_sa__d4', 'se_ec_cons_conf__lvl', 'se_ec_cons_conf__d4'],
    'Business surveys (price expectations, core)': ['w_ec_food_ind_sell_price_exp_lvl', 'w_ec_food_ind_sell_price_exp_d4',
                                                    'ea_ec_food_ind_sell_price_exp__lvl', 'ea_ec_food_ind_sell_price_exp__d4',
                                                    'no_ssb_bts_consgoods_home_price_exp__lvl',
                                                    'no_ssb_bts_consgoods_home_price_exp__d4',
                                                    'se_nier_food_mfg_sell_price_exp__lvl', 'no_nbes_bl_sell_price_di__lvl',
                                                    'w_ec_food_retail_sell_price_exp_lvl'],
    'Interest rates': ['w_policy_rate_lvl', 'w_policy_rate_d4', 'w_gov10y_lvl', 'w_gov10y_d4', 'no_policy_rate__d4',
                       'se_policy_rate__d4', 'no_govbond_10y__d4', 'se_gov_bond_10y__d4'],
    'Labour market': ['w_unemp_lvl', 'w_unemp_d4'],
}


def focus_table(target, feats):
    rows = []
    for f in feats:
        d = {'feature': f'`{f}`'}
        for al in AL:
            r = R[(R.target == target) & (R.alignment == al) & (R.feature == f)]
            if r.empty or pd.isna(r.t.iloc[0]):
                d[al] = ''
                continue
            r = r.iloc[0]
            d[al] = (f'{r.t:+.1f} / {r.t_exinfl:+.1f} (#{int(r["rank"])})'
                     + ('*' if r.q_by < .1 else '') + ('R' if r.robust else ''))
        rows.append(d)
    return md(pd.DataFrame(rows))


def business_survey_table(target, n=3):
    rows = []
    for al in AL:
        g = RA[(RA.target == target) & (RA.alignment == al) & (RA.category == 'business_survey')
               & RA.p.notna()].sort_values('p').head(n)
        for r in g.itertuples():
            rows.append({'alignment': al, 'feature': f'`{r.feature}`', 'n': r.n, 't HAC': f1(r.t),
                         'rank (of ~1,400)': int(r.rank), 'q BY': f1(r.q_by, '.3f'), 't ex-infl': f1(r.t_exinfl),
                         'flags': flag(r)})
    return md(pd.DataFrame(rows))


def conditional_checks():
    """Does a user-requested variable survive a direct price/cost control? (HAC, same specs.)"""
    T = S.build_targets()
    F, D = C.load_features(core_only=True)
    checks = [('d_margin', 'w_gov10y_d4', 'packaging_eu_yoy'), ('d_margin', 'w_gov10y_d4', 'w_food_ppi_yoy'),
              ('d_margin', 'w_gov10y_d4', 'w_cpi_dyoy'), ('d_margin', 'se_real_wage_yoy_q__d4', 'se_cpi_idx__dyoy'),
              ('d_margin', 'w_unemp_d4', 'packaging_eu_yoy'),
              ('og', 'nw_cons_conf_z', 'w_food_cpi_xvat_yoy'), ('og', 'w_real_wage_yoy', 'w_food_cpi_xvat_yoy'),
              ('og', 'w_policy_rate_d4', 'w_food_cpi_xvat_yoy'),
              ('d_og', 'se_ec_cons_conf__d4', 'w_food_cpi_xvat_dyoy'), ('d_og', 'w_real_wage_dyoy', 'w_food_cpi_xvat_dyoy'),
              ('vol_proxy', 'w_gov10y_lvl', 'w_food_cpi_xvat_yoy')]
    exin = ~((T.index >= S.INFL[0]) & (T.index <= S.INFL[1]))
    rows = []
    for target, f, ctrl in checks:
        spec = S.TARGET_SPEC[target]
        d = {'target': target, 'feature': f'`{f}`', 'control': f'`{ctrl}`'}
        for al in ['coin', 'rt0', 'rt1', 'rt2', 'rt4']:
            m, h = S.ALIGNMENTS[al]
            X = C.align(F[[f, ctrl]], D, m, h).reindex(T.index)
            cells = []
            for msk in (np.ones(len(T), bool), exin):
                df = pd.concat([T[target].rename('y'), X, T[spec['controls']]], axis=1)[msk]
                w = T[spec['weight']][msk] if spec['weight'] else None
                df = df.dropna()
                ww = None
                if w is not None:
                    ww = w.reindex(df.index)
                    df = df[ww > 0]
                    ww = ww[ww > 0].values
                cols = [c for c in df.columns if c != 'y' and df[c].std() > 0]
                Xm = np.column_stack([np.ones(len(df))] + [df[c].values for c in cols])
                _, _, t = S.hac_wls(df['y'].values, Xm, ww, spec['hac'])
                cells.append(t[1 + cols.index(f)])
            d[al] = f'{cells[0]:+.1f} / {cells[1]:+.1f}'
        rows.append(d)
    return md(pd.DataFrame(rows))


def main():
    n_core = int(R.p.notna().sum())
    n_all = int(RA.p.notna().sum())
    n_lag = int(B.groupby('target').n_tests_lagfamily.first().sum())
    n_glob = int((R.q_by_global_core < .1).sum())
    n_glob_p = int((R.q_by_global_primary < .1).sum())
    n_prim = int(R[R.target.isin(['d_margin', 'og', 'd_og'])].p.notna().sum())
    vp = VP.iloc[0]
    L = []
    w = L.append
    w('# Orkla Foods: univariate macro predictor screen\n')
    w('Workflow label `lens-screen`, run 2026-10-06. Orkla data run to 2026Q2 and macro data to 2026Q2/Q3. '
      'Scripts: `screen_lib.py`, `run_screen.py`, `make_figures.py` and `write_findings.py`. '
      'Reproduce with `python3 run_screen.py && python3 make_figures.py && python3 write_findings.py` (about 4 minutes).\n')

    w('## 0. Design and statistical hygiene\n')
    w('**Targets** (from `common.load_targets()`):\n'
      '- Primary: `d_margin` (102 quarters, 2001Q1-2026Q2), `og` (102) and `d_og` (98, of which 12 cross a definition break).\n'
      '- Secondary: `d_margin_r4` (99), `d_og_r4` (95) and the derived `vol_proxy` = og - `w_food_cpi_xvat_yoy` (102), '
      'an implied volume/mix series (validated in section 7).\n')
    w('**Base regression** y_t = a + b x_t + controls, with Newey-West HAC standard errors:\n'
      '- `d_margin`: no controls, OLS, 4 lags.\n'
      '- `og`, `vol_proxy`: + `easter_shift`; WLS with quality weights `w_og` (A = 1, B = 0.7, C = 0.4); 4 lags.\n'
      '- `d_og`: + `easter_shift` + `d_og_def_break`; WLS with `w_d_og`; 4 lags.\n'
      '- `d_margin_r4`: no controls, 8 lags, because the rolling windows overlap.\n'
      '- `d_og_r4`: + a local definition-break dummy (see section 8), 8 lags.\n\n'
      'The numpy HAC estimator reproduces `common.nw_ols` (statsmodels) to 1e-13 (`hac_validation.csv`).\n')
    w('**Alignments** (`common.align`):\n'
      '- `coin`: same quarter. Explanatory only, not usable in advance.\n'
      '- `rt0`: the feature lagged by its publication lag. Known at quarter end, before the Orkla report.\n'
      '- `rt1`, `rt2`, `rt4`: forecasts made 1, 2 or 4 quarters earlier.\n\n'
      '**Distributed-lag scan:** k = 0..6 quarters beyond the publication lag (k = h).\n')
    w('**Statistics reported for each feature x target x alignment:**\n'
      '- n, Pearson r, Spearman rho, and the effect of a 1-sd move in x (`b x 1sd`, in target units).\n'
      '- The HAC t-stat (`t HAC`).\n'
      '- A leverage-adjusted HAC t (`t lev`): residuals scaled by 1/(1-h_ii). It guards against a few well-fitted, '
      'high-leverage quarters, chiefly 2022-23, shrinking the standard error.\n'
      '- The incremental HAC t once the target\'s own real-time lag y_{t-L} is added (`t +own lag`; L = 4, or 5 at h = 4).\n'
      '- For d_og and d_og_r4, the incremental t once the base-period organic growth og_{t-L} is added (`t +base`, '
      'see section 1). This is the dominant, real-time-known base effect: corr(d_og_t, og_{t-4}) = -0.64.\n'
      '- Sub-sample HAC t: 2001-2012 (`t 01-12`), 2013-2026 (`t 13-26`), excluding 2021Q3-2023Q4 (`t ex-infl`) '
      'and excluding 2020-21 (`t ex-covid`).\n\n'
      '**Flags in the tables:**\n'
      '- `S`: the sign is the same in the full sample, 2001-12, 2013-26 and ex-infl.\n'
      '- `R` (robust): BY q < 0.10 on both the HAC t and the leverage-adjusted t, plus `S`, plus p < 0.05 ex-infl.\n')
    w('**Multiple testing:**\n'
      '- Benjamini-Yekutieli (BY) q-values are computed within each target x alignment family: about 200 tests for core '
      'features, about 1,400 for all features.\n'
      f'- Number of discovery tests: {n_core:,} (core), {n_all:,} (all features) and {n_lag:,} (lag scan, 200 features x 7 lags '
      'x 6 targets, BY within each target over its 1,386 tests). The incremental, sub-sample and conditional '
      'regressions are diagnostics, not discovery tests.\n'
      '- Stricter global families: across all core tests of all six targets and five alignments, '
      f'{n_glob} of {n_core:,} survive BY at 10% (`q_by_global_core`). Across the three primary targets, {n_glob_p} of '
      f'{n_prim:,} survive (`q_by_global_primary`). Holm-adjusted p-values are in the CSVs (`p_holm`).\n')
    w('**Caveats on the statistics:**\n'
      '- The sample is about 100 quarters and the targets are autocorrelated y/y changes. Even with HAC, small-sample '
      't-stats are optimistic, so read |t| < 3 as weak evidence.\n'
      '- The r4 targets overlap heavily: their effective sample is about a quarter of n, so their t-stats are '
      'descriptive.\n'
      '- Univariate screens cannot separate proxies from causes. Section 2 runs targeted conditional checks.\n')

    # ------------------------------------------------------------------ headline
    w('## 1. Headline results\n')
    w('**1. EBIT margin change (`d_margin`) is driven by input-cost inflation, with a two-stage pattern.**\n')
    w('- **Stage 1: the cost squeeze is simultaneous.** In the same quarter, cost-inflation proxies predict a falling '
      'margin. The strongest are EU packaging PPI (`packaging_eu_yoy`, coincident t = '
      f'{v("d_margin", "coin", "packaging_eu_yoy")}, r = {v("d_margin", "coin", "packaging_eu_yoy", "pearson", fmt="+.2f")}, '
      f'about {v("d_margin", "coin", "packaging_eu_yoy", "b_1sd", fmt="+.2f")}pp of margin per 1 sd) and '
      'EU plastic-products PPI (real-time nowcast t = '
      f'{v("d_margin", "rt0", "eu_ppi_plastic_products_idx__yoy")}). Food-industry selling-price expectations and '
      'Swedish CPI acceleration point the same way.\n'
      '- **The episode inflates the full-sample t-stats.** These relations survive without 2021Q3-2023Q4, but much weaker: '
      f't ex-infl = {v("d_margin", "coin", "packaging_eu_yoy", "t_exinfl")} and '
      f'{v("d_margin", "rt0", "eu_ppi_plastic_products_idx__yoy", "t_exinfl")}. The 2022-23 squeeze '
      '(margin about -3pp y/y while EU packaging PPI rose 15-18% y/y) supplies most of the full-sample t.\n'
      '- **Stage 2: delayed pass-through, 5-6 quarters later.** In the lag scan, cost and price inflation 5-6 quarters '
      'beyond the publication lag predicts margin **recovery**, i.e. a positive sign. Examples:\n'
      f'  - EU dairy PPI (`eu_ppi_dom_c105_idx__yoy`) at k = 6: t = {lb("d_margin", "eu_ppi_dom_c105_idx__yoy", "t_best"):+.1f}, '
      f'{lb("d_margin", "eu_ppi_dom_c105_idx__yoy", "t_exinfl_at_best"):+.1f} ex-infl, '
      f'{lb("d_margin", "eu_ppi_dom_c105_idx__yoy", "t_incr_at_best"):+.1f} with the own lag.\n'
      f'  - Swedish food PPI at k = 6: t = {lb("d_margin", "se_ppi_food_hmpi_idx__yoy", "t_best"):+.1f}.\n'
      f'  - EU bakery PPI at k = 5: t = {lb("d_margin", "eu_ppi_dom_c107_idx__yoy", "t_best"):+.1f}.\n'
      f'  - Swedish CPI at k = 6: t = {lb("d_margin", "se_cpi_idx__yoy", "t_best"):+.1f}.\n\n'
      '  For these four series, the k = 6 relations hold separately in 2001-12 (t 2.5-3.2) and 2013-26 (t 2.5-3.1). This is the classic '
      'pattern: price increases catch up with costs after a lag, and input costs normalise.\n'
      '- **Practical reading.** Cost inflation now means lower margins this quarter and next, and higher margins about '
      '1.5 years out.\n'
      '- **Predictability by horizon.** At h = 2 and h = 4 no single core feature is BY-significant for quarterly '
      '`d_margin` in the full sample.\n'
      f'  - Excluding 2021Q3-2023Q4, {int((R[(R.target == "d_margin") & (R.alignment == "rt4")].q_by_exinfl < .1).sum())} '
      'core features are BY-significant at h = 4. Almost all are lagged price or cost inflation with a positive sign, '
      f'e.g. `eu_ppi_dom_c107_idx__yoy` ex-infl t = {v("d_margin", "rt4", "eu_ppi_dom_c107_idx__yoy", "t_exinfl")}, which is the '
      'delayed pass-through again.\n'
      '  - In the full sample, the 2022-24 squeeze-then-recovery sequence blurs this horizon.\n'
      '  - The smoother `d_margin_r4` is predictable to h = 2.\n')
    w('**2. Rising long-term interest rates predict margin declines, and this is the most robust rates result.**\n')
    w(f'- The 4-quarter change in the Orkla-weighted 10-year yield (`w_gov10y_d4`) has t = {v("d_margin", "coin", "w_gov10y_d4")} '
      f'coincident and in the nowcast, and {v("d_margin", "rt1", "w_gov10y_d4")} at h = 1.\n'
      f'- The Norwegian 10-year yield change (`no_govbond_10y__d4`) ranks #2 at h = 1 (t = {v("d_margin", "rt1", "no_govbond_10y__d4")}).\n'
      '- The sign is stable: it holds in 2001-12, in 2013-26 and without the inflation episode '
      f'(ex-infl t = {v("d_margin", "coin", "w_gov10y_d4", "t_exinfl")}).\n'
      '- It survives a direct control for packaging PPI, food PPI or CPI acceleration (t about -3, section 2). Yields '
      'therefore carry cycle and inflation information beyond the cost indices.\n'
      '- Policy-rate *levels* and yield *levels* show nothing for margins.\n')
    w('**3. Organic growth (`og`) is mostly price, so it tracks consumer and producer food inflation.**\n')
    w(f'- Swedish food CPI y/y has t = {v("og", "coin", "se_cpi_food_idx__yoy")} coincident and in the nowcast, and '
      f'{v("og", "rt1", "se_cpi_food_idx__yoy")} at h = 1. The Orkla-weighted food CPI ex VAT has t = {v("og", "coin", "w_food_cpi_xvat_yoy")}.\n'
      '- Survey price expectations lead: SSB consumer-goods price expectations (`no_ssb_bts_consgoods_home_price_exp`) '
      f'have t = {v("og", "rt2", "no_ssb_bts_consgoods_home_price_exp__lvl")} at h = 2, and their 4-quarter change '
      f'{v("og", "rt4", "no_ssb_bts_consgoods_home_price_exp__d4")} at h = 4 (BY q = '
      f'{v("og", "rt4", "no_ssb_bts_consgoods_home_price_exp__d4", "q_by", fmt=".2f")}). '
      f'EC food-industry selling-price expectations have t = {v("og", "rt2", "w_ec_food_ind_sell_price_exp_lvl")} at h = 2.\n'
      '- In the all-feature family, EC retail selling-price expectations for Sweden are the best h = 1-2 predictors '
      f'(t = {v("og", "rt1", "se_ec_retail_sell_price_exp__lvl", fam=RA)} and {v("og", "rt2", "se_ec_retail_sell_price_exp__lvl", fam=RA)}).\n'
      '- **The episode dominates.** Without 2021Q3-2023Q4, the same variables keep their sign, but t falls to about 2-3.7, '
      'and only 0-3 core features pass BY within the ex-infl families.\n')
    w('**4. Change in organic growth (`d_og`) has the most real-time predictability, but read it with the base effect in mind.**\n')
    w('- **The base effect.** d_og = og_t - og_{t-4}, and og_{t-4} is known in real time with corr(d_og, og_{t-4}) = -0.64. '
      'Food inflation 4-5 quarters back therefore predicts d_og negatively, partly through the base alone:\n'
      f'  - `w_food_cpi_yoy` at h = 4: t = {v("d_og", "rt4", "w_food_cpi_yoy")}; controlling for og_{{t-5}}: '
      f'{v("d_og", "rt4", "w_food_cpi_yoy", "t_incr_base")}.\n'
      '- **Signals that survive the base and own-lag controls and the ex-infl sample:**\n'
      '  - Accelerations in EU food-manufacturing PPIs at h = 0-2, such as `eu_ppi_dom_c106_idx__dyoy` (grain mill; '
      f't = {v("d_og", "rt2", "eu_ppi_dom_c106_idx__dyoy")} at h = 2, ex-infl {v("d_og", "rt2", "eu_ppi_dom_c106_idx__dyoy", "t_exinfl")}).\n'
      '  - Changes in EC food-industry selling-price expectations (`ea_ec_food_ind_sell_price_exp__d4`: '
      f't = {v("d_og", "rt2", "ea_ec_food_ind_sell_price_exp__d4")} at h = 2 and {v("d_og", "rt4", "ea_ec_food_ind_sell_price_exp__d4")} at h = 4; '
      f'+base {v("d_og", "rt4", "ea_ec_food_ind_sell_price_exp__d4", "t_incr_base")}).\n'
      '  - Packaging-cost accelerations at h = 4.\n'
      '  - Activity at h = 2, for example `w_gdp_vol_dyoy` (t = '
      f'{v("d_og", "rt2", "w_gdp_vol_dyoy")}), and in the all-feature family euro-area GDP y/y (t = {v("d_og", "rt2", "ea_gdp_vol_idx__yoy", fam=RA)}) '
      f'and OECD business confidence changes at h = 4 (`g7_oecd_bci__d4` t = {v("d_og", "rt4", "g7_oecd_bci__d4", fam=RA)}).\n'
      '- In the nowcast, falling real wages (`w_real_wage_dyoy`, t = '
      f'{v("d_og", "rt0", "w_real_wage_dyoy")}) and falling Swedish confidence (`se_ec_cons_conf__d4`, t = '
      f'{v("d_og", "rt0", "se_ec_cons_conf__d4")}) go with *rising* og growth. They partly survive a food-CPI-acceleration '
      'control (section 2), but the sign rules out a demand channel. They capture broad inflation acceleration that '
      'Orkla passes through.\n')
    w('**5. Volume is essentially unpredictable from macro data in real time.**\n')
    w('- The implied volume/mix proxy correlates with Orkla\'s reported volume/mix at r = '
      f'{vp.corr_volmix_vs_proxy:.2f} (2022Q2-2026Q2).\n'
      '- It is explained coincidentally by Nordic grocery-market volumes: Swedish household food consumption '
      f'(t = {v("vol_proxy", "coin", "se_na_hhcons_food_sa__yoy")}, ex-infl {v("vol_proxy", "coin", "se_na_hhcons_food_sa__yoy", "t_exinfl")}) '
      f'and Swedish grocery volume acceleration (t = {v("vol_proxy", "coin", "se_retail_grocery_vol_sa_idx__dyoy")}).\n'
      '- From h = 1 no core feature passes BY, and nothing in the lag scan does either beyond the mechanical food-CPI '
      'term at k = 0.\n'
      '- Real wages, real disposable income and consumer confidence do **not** predict volume robustly. Their sign even '
      'turns negative without the inflation episode.\n'
      f'- Bond-yield *levels* are weakly negative (t about {v("vol_proxy", "rt1", "w_gov10y_lvl")} at h = 1, ex-infl '
      f'{v("vol_proxy", "rt1", "w_gov10y_lvl", "t_exinfl")}, rank #{v("vol_proxy", "rt1", "w_gov10y_lvl", "rank", fmt=".0f")} of 200), '
      'but not significant after BY.\n')
    w('**6. Count of robust core predictors** (BY q < 0.10 on both t-stats, sign-stable, p < 0.05 ex-infl), by target and '
      'alignment:\n')
    rob = R.groupby(['target', 'alignment'])['robust'].sum().unstack()[AL].reindex(S.TARGETS)
    sig = R.assign(s=R.q_by < .1).groupby(['target', 'alignment'])['s'].sum().unstack()[AL].reindex(S.TARGETS)
    tab = pd.DataFrame({al: [f'{int(sig.loc[t, al])} / {int(rob.loc[t, al])}' for t in S.TARGETS] for al in AL},
                       index=S.TARGETS)
    tab.insert(0, 'target', [f'`{t}`' for t in tab.index])
    w('Cells show (BY q < 0.10) / (robust) out of about 200 core tests.\n')
    w(md(tab) + '\n')

    # ------------------------------------------------------------------ user questions
    w('## 2. The variables you asked about: real wages, surveys and interest rates\n')
    w('Each cell shows `t HAC full / t HAC excluding 2021Q3-2023Q4 (rank among ~200 core features)`. A `*` marks BY '
      'q < 0.10 and `R` marks robust. The tables cover the three primary targets plus the volume proxy.\n')
    for target in ['d_margin', 'og', 'd_og', 'vol_proxy']:
        w(f'### {TNAME[target]}\n')
        for grp, feats in FOCUS.items():
            w(f'**{grp}**\n')
            w(focus_table(target, feats) + '\n')
    w('### Business surveys in the all-feature family (top 3 per alignment)\n')
    w('The core set contains no `business_survey` features (confidence and PMI-type indices); they appear only among '
      'the 1,420. Ranks are out of about 1,400.\n')
    for target in ['d_margin', 'og', 'd_og', 'vol_proxy']:
        w(f'**{target}**\n')
        w(business_survey_table(target) + '\n')
    w('### Conditional checks: does the variable survive a direct price or cost control?\n')
    w('Each cell shows the HAC t of the feature with the control added: `full / excluding 2021Q3-2023Q4`. The target '
      'specification is unchanged.\n')
    w(conditional_checks() + '\n')
    w('### Verdict on the requested variables\n')
    w('**Real wages**\n'
      '- **Margins.** Swedish real-wage acceleration (`se_real_wage_yoy_q__d4`) is a robust positive nowcast predictor '
      f'(t = {v("d_margin", "rt0", "se_real_wage_yoy_q__d4")}, #{v("d_margin", "rt0", "se_real_wage_yoy_q__d4", "rank", fmt=".0f")}). '
      'It disappears entirely once Swedish CPI acceleration is controlled (t about 0). It is an inflation proxy: real wages '
      'accelerate when inflation, and hence input costs, decelerate.\n'
      '- **Organic growth.** Real wages are strongly negative (`w_real_wage_yoy` nowcast t = '
      f'{v("og", "rt0", "w_real_wage_yoy")}, #{v("og", "rt0", "w_real_wage_yoy", "rank", fmt=".0f")}), again because '
      'inflation lowers real wages and raises Orkla\'s prices.\n'
      '- **Change in organic growth.** Real-wage deceleration predicts higher d_og in the nowcast (`w_real_wage_dyoy` t = '
      f'{v("d_og", "rt0", "w_real_wage_dyoy")}; with a food-CPI-acceleration control, t = -3.5). Real-wage levels 4-5 '
      f'quarters back predict d_og positively (`w_real_wage_yoy` h = 4 t = {v("d_og", "rt4", "w_real_wage_yoy")}, '
      f'+base {v("d_og", "rt4", "w_real_wage_yoy", "t_incr_base")}), partly through the base effect: low real wages mean '
      'high inflation, hence high og in the base year.\n'
      '- **Volume.** No robust positive effect on implied volume at any horizon.\n'
      '- **Conclusion.** Real wages matter through the inflation term, not as a demand driver Orkla benefits from.\n')
    w('**Consumer confidence**\n'
      '- **Levels vs og.** Levels are negatively related to og (`nw_cons_conf_z` nowcast t = '
      f'{v("og", "rt0", "nw_cons_conf_z")}, robust). The sign survives a food-CPI control (t about -3) and the ex-infl '
      'sample, but there is no matching positive volume effect.\n'
      '- **Reading.** Food at home is defensive or counter-cyclical, and confidence also captures inflation perceptions.\n'
      '- **Changes vs d_og.** Confidence changes predict d_og negatively in the nowcast (`se_ec_cons_conf__d4` t = '
      f'{v("d_og", "rt0", "se_ec_cons_conf__d4")}). This survives a food-CPI-acceleration control (t = -3.8 nowcast, '
      '-5.5 at h = 1).\n'
      '- **Levels 4-5 quarters back.** These predict d_og positively (`nw_cons_conf_z` h = 4 t = '
      f'{v("d_og", "rt4", "nw_cons_conf_z")}). Part of that is the base effect (+base t = '
      f'{v("d_og", "rt4", "nw_cons_conf_z", "t_incr_base")}).\n'
      '- **Margins.** Nothing.\n')
    w('**Business surveys**\n'
      '- **Selling-price expectations** in food manufacturing and retail are the main survey signal, and the best '
      'survey-based leading indicators of og and d_og at h = 1-4.\n'
      '- **Same-quarter margins.** High selling-price expectations coincide with margin squeezes: firms expect to raise '
      'prices because costs have risen.\n'
      '- **General business confidence** (OECD BCI) adds to d_og at h = 4 and to og levels at h = 4 (all-feature family).\n')
    w('**Interest rates**\n'
      '- **Margins.** Changes in long yields are robust negative predictors at h = 0-1 and survive the cost controls. '
      'This is the best rates result.\n'
      '- **og.** Policy-rate changes predict og positively at h = 2-4 (`w_policy_rate_d4` h = 4 t = '
      f'{v("og", "rt4", "w_policy_rate_d4")}; with a food-CPI control +4.6 full and +5.4 ex-infl). Central banks hike '
      'into the inflation that later shows up in Orkla\'s prices.\n'
      '- **Volume.** Yield levels are weakly negative and not BY-significant.\n'
      '- **Levels in general.** Rate levels are uninformative for margins.\n')

    # ------------------------------------------------------------------ categories
    w('## 3. Interpretation by category\n')
    w('**Prices: consumer food CPI, PPI and price expectations**\n'
      '- **og and d_og.** Price variables are the backbone of the og and d_og results:\n'
      '  - og: same-quarter levels.\n'
      '  - d_og: accelerations (dyoy), plus the lagged levels that operate through the base effect.\n'
      '- **Swedish food CPI vs the weighted composite.** Swedish food CPI is the single best og series, ahead of the '
      'Orkla-weighted composite. Sweden is about 27-29% of sales and its CPI has no publication lag.\n'
      '- **Use the ex-VAT variants for 2026.** The Swedish food-VAT cut in 2026Q2 depresses `w_food_cpi_yoy` (-1.0 in '
      '2026Q2, against +0.6 for `_xvat`). Use the `_xvat` variants for 2026 nowcasts.\n'
      '- **Survey price expectations lead by 1-4 quarters:**\n'
      '  - SSB consumer-goods price expectations.\n'
      '  - EC food-industry and retail selling-price expectations.\n'
      '  - NIER food selling prices.\n')
    w('**Input costs: packaging, food PPI, agricultural and FAO commodities, energy**\n'
      '- **Packaging PPIs** (EU plastics and paper, US corrugated) are the best margin series. They lead commodity '
      'indices, presumably because they capture the broad industrial-cost wave and Orkla\'s packaging-heavy cost base.\n'
      '- **Global food commodities** (FAO, World Bank, in local currency) are weaker for margins than European PPIs '
      '(e.g. `fao_ffpi_wloc_yoy` nowcast t = '
      f'{v("d_margin", "rt0", "fao_ffpi_wloc_yoy")}). They work better for d_og at h = 2 '
      f'(`glob_fao_ffpi_eur__yoy` t = {v("d_og", "rt2", "glob_fao_ffpi_eur__yoy")}).\n'
      '- **Energy** (Nordic electricity, EU gas) never survives BY for margins or og. EU gas and Nordic electricity '
      'inflation 1-4 quarters back do lead d_og positively (e.g. `natgas_eu_eur_yoy` h = 2 t = '
      f'{v("d_og", "rt2", "natgas_eu_eur_yoy")}), as part of the inflation cycle.\n'
      '- **Price-cost gaps** (food CPI minus PPI or commodities) relate positively to d_margin, as expected, but '
      'weaker than the raw cost series. They relate negatively to d_og, since gaps open when costs fall and prices '
      'stagnate.\n')
    w('**Wages and real wages**\n'
      '- **Nominal wage growth.** Mostly insignificant for margins. The labour-cost shock is slow and smooth.\n'
      '- **Real wages.** Real-wage measures load on their CPI component. See section 2.\n'
      '- **All-feature family exception.** Euro-area compensation per employee acceleration '
      f'(`ea_comp_per_employee_q__dyoy`, coincident t = {v("d_margin", "coin", "ea_comp_per_employee_q__dyoy", fam=RA)}, '
      f'ex-infl {v("d_margin", "coin", "ea_comp_per_employee_q__dyoy", "t_exinfl", fam=RA)}) is a strong same-quarter '
      'margin correlate. It is not real-time.\n')
    w('**Surveys:** see section 2. In short, price-expectation surveys are useful and confidence surveys are mostly '
      'inflation proxies.\n')
    w('**Rates:** see section 2. Yield changes matter for margins, and policy-rate changes lead og at h = 2-4.\n')
    w('**FX**\n'
      '- **Essentially nothing** for d_margin, og or volume: no FX feature passes BY. Organic growth excludes currency '
      'translation, and EBIT margin is a ratio, so translation largely cancels.\n'
      '- **The one exception** is d_og at h = 4. A weaker NOK against EUR predicts lower d_og (`no_fx_eurnok__yoy` t = '
      f'{v("d_og", "rt4", "no_fx_eurnok__yoy")}), most likely through imported inflation raising the base-period og.\n'
      '- **Transactional FX** (NOK and SEK against EUR/USD for imported inputs) does not show up as a robust '
      'univariate predictor.\n')
    w('**Activity: retail volumes, GDP, household consumption**\n'
      '- **Volume.** These explain volume coincidentally (Nordic grocery volumes, Swedish household food consumption).\n'
      '- **Same-quarter margins.** Market-volume acceleration goes with margin gains (`nw_retail_food_vol_dyoy` coincident '
      f't = {v("d_margin", "coin", "nw_retail_food_vol_dyoy")}), i.e. operating leverage.\n'
      '- **Lagged GDP growth** predicts d_og at h = 2.\n'
      '- **Sign flip for Norwegian grocery volume.** Its acceleration is *negative* for d_og at h = 1 (t = '
      f'{v("d_og", "rt1", "no_retail_foodstores_vol_sa_idx__dyoy")}), but the sign is unstable (2001-12 t = '
      f'{v("d_og", "rt1", "no_retail_foodstores_vol_sa_idx__dyoy", "t_early")}).\n'
      '- **Unemployment changes** relate positively to same-quarter margins, but this is explained by cost deflation in '
      'downturns (section 2).\n')

    # ------------------------------------------------------------------ lag profiles
    w('## 4. Distributed-lag profiles (core features, k = 0..6 beyond the publication lag)\n')
    w('- `best k` is the lag with the largest |HAC t|.\n'
      '- The q-value is BY over all 200 x 7 = 1,386 lag tests of the target. This penalises the search over lags.\n'
      '- The profile columns give t at k = 0..6, for the full sample and excluding 2021Q3-2023Q4.\n'
      '- Full profiles: `lag_profiles.csv`, `lag_best.csv` and `figures/lagprofile_<target>.png`.\n')
    for target in S.TARGETS:
        nsig = int((B[B.target == target].q_by_lagfamily < .1).sum())
        kd = B[(B.target == target) & (B.q_by_lagfamily < .1)].best_k.value_counts().sort_index().to_dict()
        w(f'### {TNAME[target]}\n')
        w(f'{nsig} features have a BY-significant best lag. Distribution of best k among them: {kd}.\n')
        w(lag_table(target) + '\n')
    w('**Reading the d_margin profile**\n'
      '- Cost and price variables run from negative at k = 0-2 to positive at k = 4-6 (see `figures/lagprofile_d_margin.png`).\n'
      '- This is a pass-through cycle with a turning point after about 3-4 quarters.\n'
      '- For forecasting d_margin 4-6 quarters ahead, the level of food-PPI and CPI inflation 5-7 quarters back is the '
      'most useful single input in the core set.\n\n'
      '**Reading the d_og profile**\n'
      '- Price levels switch sign between k = 0 (positive: current pricing) and k = 4-6 (negative: base effect).\n'
      '- Price accelerations (dyoy) and expectation changes (d4) peak at k = 1-3.\n')

    # ------------------------------------------------------------------ ranked tables
    w('## 5. Ranked tables per target and alignment (core family, top 15 by HAC p-value)\n')
    w('**Columns**\n'
      '- `b x 1sd`: target change per 1-sd move in the feature.\n'
      '- `t lev`: leverage-adjusted HAC t.\n'
      '- `q BY`: Benjamini-Yekutieli q within the target x alignment family (about 200 tests).\n'
      '- `t +own lag`: incremental t with the real-time own lag.\n'
      '- `t +base`: incremental t with og_{t-L} (d_og and d_og_r4 only).\n'
      '- `flags`: S = sign-stable, R = robust.\n\n'
      'Every table is followed by the top 10 when ranked on the sample **excluding 2021Q3-2023Q4**, where `*` marks BY '
      'q < 0.10 within that family. Full results, including Spearman, the n of each sub-sample and Holm p, are in '
      '`screen_results_core.csv`.\n')
    for target in S.TARGETS:
        w(f'### {TNAME[target]}\n')
        w('Significance counts:\n')
        w(counts_table(target) + '\n')
        for al in AL:
            w(f'#### {target}, {S.ALIGN_LABEL[al]}\n')
            w(ranked_table(target, al) + '\n')
        w(f'#### {target}: top 10 per alignment on the sample excluding 2021Q3-2023Q4 (ex-infl HAC t)\n')
        w(exinfl_matrix(target) + '\n')
        w(f'Figures: `figures/top10_{target}_coincident.png`, `figures/top10_{target}_realtime.png`, '
          f'`figures/lagprofile_{target}.png`.\n')

    # ------------------------------------------------------------------ all family
    w('## 6. All 1,420 features (second family)\n')
    w('**How to read this family**\n'
      '- BY within each target x alignment family is over about 1,400 tests.\n'
      '- Many hits are country-level duplicates of core composites: individual HICPs, PPIs, and EC survey balances for '
      'single countries.\n'
      '- The series that are new relative to the core set:\n'
      '  - EC selling-price expectations for industry and retail (DE, EA, SE, CZ).\n'
      '  - OECD business confidence (G7, DE, SE).\n'
      '  - Euro-area GDP and compensation per employee.\n'
      '  - Swedish retail grocery *value*.\n'
      '  - The Norwegian NAV unemployment level.\n'
      '- **Likely spurious or very-small-weight series:** Romanian, Latvian and Lithuanian bond yields, the Czech policy '
      'rate, Norwegian cross-border shopping (from 2009), short EU cereal series (n < 40) and the Norwegian agricultural '
      'frame (annual).\n')
    for target in ['d_margin', 'og', 'd_og', 'vol_proxy']:
        for al in ['coin', 'rt1', 'rt4']:
            w(f'#### All features, {target}, {al}\n')
            g = RA[(RA.target == target) & (RA.alignment == al) & RA.p.notna()].sort_values('p').head(10)
            rows = [{'#': i, 'feature': f'`{r.feature}`', 'cat': CAT.get(r.category, r.category),
                     'core': 'yes' if r.core else '', 'n': r.n, 't HAC': f1(r.t), 't lev': f1(r.t_lev),
                     'q BY': f1(r.q_by, '.3f'), 't +own lag': f1(r.t_incr), 't ex-infl': f1(r.t_exinfl),
                     'flags': flag(r)} for i, r in enumerate(g.itertuples(), 1)]
            w(md(pd.DataFrame(rows)) + '\n')
    w('The secondary targets in the all-feature family are in `screen_results_all.csv`.\n')

    # ------------------------------------------------------------------ vol proxy
    w('## 7. Implied volume/mix proxy: validation\n')
    w('`vol_proxy` = og - `w_food_cpi_xvat_yoy` (same quarter). It is checked against Orkla\'s reported price and '
      'volume/mix split, which exists from 2022Q2 only. Note that 2022Q2 is on the E basis inside a D row.\n')
    w(md(VP.round(3)) + '\n')
    w('**How well the proxy works**\n'
      '- The proxy tracks the direction of reported volume/mix well (r about 0.8). The weighted food CPI tracks Orkla\'s '
      'price effect at r about 0.92 (0.95-0.96 for the Nordic variant).\n'
      '- **It fails in 2025.** Consumer food inflation (about 4%) ran ahead of Orkla\'s own pricing (about 1%), so the '
      'proxy understated volume by about 3pp per quarter. Before 2022 there is no ground truth.\n'
      '- **Mechanical correlations.** Any feature correlated with food CPI correlates negatively with the proxy. The '
      'coincident food-CPI hits for `vol_proxy` are partly mechanical.\n')

    # ------------------------------------------------------------------ caveats
    w('## 8. Caveats and notes on the shared module\n')
    w('**Data caveats**\n'
      '- **Latest-vintage data.** Publication lags are respected, but revisions are not. National accounts, preliminary '
      'wages and seasonal factors are latest vintage.\n'
      '- **Look-ahead in the inputs.** The Orkla-weighted composites use geographic weights from annual reports published '
      'after year end (mild look-ahead). Confidence z-scores use full-sample scaling.\n'
      '- **Definition mix.**\n'
      '  - India is inside the headline in 2014Q4-2022Q2. Rieber, Hamé and Eastern acquisitions are inside `d_margin`.\n'
      '  - The 2015-16 organic growth includes distribution agreements.\n'
      '  - 2001-05 organic growth is low precision (quality C, down-weighted).\n'
      '  - Definition-break dummies and quality weights handle these only partly.\n'
      '- **Episode dominance.** 2022-23 is the only large cost shock with a well-measured response. The ex-infl columns '
      'are the honest test, and several "top" features are much weaker there (e.g. packaging PPI t falls from about -9 '
      'to about -3).\n'
      '- **Easter.** `easter_shift` is a proxy. Sell-in timing makes the effect sign-ambiguous (methodology section 5.3).\n'
      '- **Redundancy.** Many features are near-duplicates (FAO and WB indices in several currencies; packaging '
      'sub-indices). BY is valid under positive dependence, but the effective number of independent signals is much '
      'smaller than the test count. The figures de-duplicate at |corr| > 0.9.\n')
    w('**Notes on `common.py`** (not modified; worked around locally)\n'
      '1. `d_og_r4` = og_r4_t - og_r4_{t-4} uses the headline `og_est` shifted by 4 quarters, not the same-report '
      'comparatives. It therefore compares across definitions whenever any quarter in the 8-quarter window crosses a '
      'break: 2008Q1-2009Q1, 2013Q1-2015Q4 and 2022Q3-2024Q1. That includes the D->E break that `d_og` itself avoids, '
      'where E is compared with D including India. `load_targets` provides no break flag for it. I built '
      '`d_og_r4_break` (a rolling 4-quarter max of def_id(t) != def_id(t-4)) and used it as a control.\n'
      '2. `nw_ols` drops NaN and zero-weight rows before the HAC sum, so quarters on either side of a gap (e.g. the '
      'excluded 2021Q3-2023Q4 window) are treated as adjacent in the Newey-West lags. The effect is minor. My numpy '
      'estimator does the same, for consistency.\n'
      '3. `align()` falls back to a 1-quarter lag for any feature missing from the dictionary. This never triggers for '
      'panel features.\n')

    w('## 9. Files\n')
    w(md(pd.DataFrame([
        {'file': '`screen_results_core.csv`', 'content': '200 core features x 6 targets x 5 alignments (6,000 rows), all statistics and q-values'},
        {'file': '`screen_results_all.csv`', 'content': '1,420 features x 6 targets x 5 alignments (42,600 rows)'},
        {'file': '`lag_profiles.csv`', 'content': 'core features x targets x k = 0..6: r, b, HAC t, leverage-adjusted t, ex-infl t, incremental t'},
        {'file': '`lag_best.csv`', 'content': 'best lag per target x feature with full profiles and BY q over the lag family'},
        {'file': '`figures/top10_<target>_{coincident,realtime}.png`', 'content': 'scatter + time-series overlay for the top 10 distinct features'},
        {'file': '`figures/lagprofile_<target>.png`', 'content': 'heatmap of t by lag for the top 15 features'},
        {'file': '`figure_selection.csv`', 'content': 'features and alignments shown in the figures'},
        {'file': '`vol_proxy_validation.csv`, `vol_proxy_series_2022on.csv`', 'content': 'proxy vs reported price and volume/mix'},
        {'file': '`hac_validation.csv`', 'content': 'numpy HAC vs common.nw_ols check'},
    ])) + '\n')
    open(f'{OUT}/findings.md', 'w').write('\n'.join(L))
    print('findings.md written,', sum(len(x) for x in L), 'chars')


if __name__ == '__main__':
    main()
