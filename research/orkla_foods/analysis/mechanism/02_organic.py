"""Section 2: organic-growth decomposition (lens-mechanism).

og = price + volume/mix. Orkla reports the split only from 2022Q2 (17 quarters). We
(a) validate macro price proxies against Orkla's reported price component (pass-through ratio, timing),
(b) validate volume drivers against the reported volume/mix component,
(c) build an implied volume proxy for the full sample, vol_proxy = og - Orkla-weighted food CPI ex VAT
    (India-blended variant vol_proxy_in), validate it on 2022Q2+, and test volume drivers on it
    (coincident, real-time h=0/1/2 via C.align, lead/lag profile),
(d) estimate the full-sample price pass-through ratio of og to food CPI,
(e) cross-border shopping and out-of-home/COVID effects.

Outputs: og_price_validation.csv, og_price_levels.csv, og_volume_validation.csv, og_volproxy_validation.csv,
og_volume_drivers.csv, og_leadlag.csv, og_passthrough.csv, og_joint_volume_model.csv, og_covid_border.csv,
mt_tests_organic.csv, fig_og_*.png
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import mech_utils as M

C = M.C
T, F, D, X = M.load_all()
# Cross-border shopping collapsed and rebounded with the 2020-22 border closures: blank the feature itself
# for those observation dates (before any lag/alignment) so the closure/reopening cannot leak into any target.
_CLOSE = (F.index >= pd.Period('2020Q1', 'Q')) & (F.index <= pd.Period('2022Q4', 'Q'))
for _c in [c for c in F.columns if c.startswith('no_border_trade')]:
    F.loc[_CLOSE, _c] = np.nan
    X.loc[_CLOSE, _c] = np.nan
XT = X.reindex(T.index)
tests = []
P22 = T.index >= pd.Period('2022Q2', 'Q')
P22E = T.index >= pd.Period('2022Q3', 'Q')       # pure definition E (2022Q2 split is E-basis inside a D row)


def ols(yv, Xd, lags=4, weights=None):
    """C.nw_ols after dropping regressors that are constant within the estimation sample
    (e.g. def_A after 2008), which would otherwise make the design rank-deficient."""
    df = pd.concat([yv.rename('_y'), Xd], axis=1).dropna()
    keep = [c for c in Xd.columns if df[c].std() > 1e-12]
    return C.nw_ols(yv, Xd[keep], lags=lags, weights=weights)


def small_p(r, name):
    """Conservative small-sample p-value (n~17): max of HAC-t and classical-OLS-t p-values, t(df_resid)."""
    from scipy import stats
    import statsmodels.api as sm
    df = int(r.df_resid)
    p_hac = 2 * (1 - stats.t.cdf(abs(r.tvalues[name]), df))
    ro = sm.OLS(r.model.endog, r.model.exog).fit()
    i = list(r.params.index).index(name)
    p_ols = 2 * (1 - stats.t.cdf(abs(ro.tvalues[i]), df))
    return max(p_hac, p_ols), p_hac, p_ols


# ============================================================================ 2a price validation
PRICE_PROXIES = {'w_food_cpi_xvat_yoy': 'food CPI ex VAT (Orkla-wtd)', 'nw_food_cpi_xvat_yoy': 'food CPI ex VAT (NO+SE)',
                 'w_food_cpi_yoy': 'food CPI incl. VAT (Orkla-wtd)', 'w_food_ppi_yoy': 'food-manufacturing PPI (Orkla-wtd)',
                 'nw_food_ppi_yoy': 'food-manufacturing PPI (NO+SE)', 'no_cpi_food_idx__yoy': 'NO food CPI',
                 'se_cpi_food_idx__yoy': 'SE food CPI', 'ea_hicp_food_idx__yoy': 'euro-area food HICP',
                 'w_ec_food_ind_sell_price_exp_lvl': 'food manufacturers selling-price expectations (EC, level)'}
pv_rows = []
for c, lab in PRICE_PROXIES.items():
    for k in range(-2, 4):          # k>0: proxy lagged k quarters (proxy leads Orkla); k<0: proxy is later
        z = X[c].shift(k).reindex(T.index).rename('z')
        for smp_name, smp in [('2022Q2-2026Q2', P22), ('2022Q3-2026Q2 (def E)', P22E)]:
            yv = T['price'].where(smp)
            r = ols(yv, pd.concat([z], axis=1), lags=2)
            d = pd.concat([yv, z], axis=1).dropna()
            pv_rows.append(dict(proxy=c, label=lab, shift_k=k, timing=('proxy leads Orkla by %d q' % k if k > 0 else
                                                                        ('coincident' if k == 0 else 'proxy lags Orkla by %d q' % -k)),
                                sample=smp_name, n=int(r.nobs), corr=d.corr().iloc[0, 1], slope=r.params['z'],
                                slope_se=r.bse['z'], intercept=r.params['const'], r2=r.rsquared,
                                rmse=np.sqrt(r.mse_resid), p=small_p(r, 'z')[0],
                                mean_price_minus_proxy=(d.iloc[:, 0] - d.iloc[:, 1]).mean()))
            if smp_name.startswith('2022Q2') and k in (0, 1):
                tests.append(('og_price_validation', f'{c}|k={k}', smp_name, r.tvalues['z'] ** 2, 1, small_p(r, 'z')[0], int(r.nobs)))
pv = pd.DataFrame(pv_rows)
pv.to_csv(f'{M.OUTDIR}/og_price_validation.csv', index=False, float_format='%.4g')
print(pv[pv['sample'].str.startswith('2022Q2')].sort_values(['proxy', 'shift_k'])[
    ['proxy', 'shift_k', 'n', 'corr', 'slope', 'slope_se', 'intercept', 'r2', 'rmse']].to_string(float_format=lambda v: f'{v:.3g}'))

# Price LEVEL comparison: compound y/y rates for each calendar quarter over the episode
lv_rows = []
for q in (1, 2, 3, 4):
    qi = [p for p in T.index if p.quarter == q and not np.isnan(T.loc[p, 'price'])]
    if len(qi) < 2:
        continue
    start, end = qi[0] - 4, qi[-1]
    orkla = np.prod([1 + T.loc[p, 'price'] / 100 for p in qi]) - 1
    row = dict(quarter=f'Q{q}', base=str(start), end=str(end), years=len(qi), orkla_price_cum_pct=100 * orkla)
    for c in ['w_food_cpi_xvat_yoy', 'nw_food_cpi_xvat_yoy', 'w_food_ppi_yoy']:
        row[f'{c}_cum_pct'] = 100 * (np.exp(sum(X.loc[p, c] for p in qi) / 100) - 1)
    row['ratio_orkla_to_wCPIxvat'] = row['orkla_price_cum_pct'] / row['w_food_cpi_xvat_yoy_cum_pct']
    row['ratio_orkla_to_nwCPIxvat'] = row['orkla_price_cum_pct'] / row['nw_food_cpi_xvat_yoy_cum_pct']
    row['ratio_orkla_to_wPPI'] = row['orkla_price_cum_pct'] / row['w_food_ppi_yoy_cum_pct']
    lv_rows.append(row)
lv = pd.DataFrame(lv_rows)
lv.to_csv(f'{M.OUTDIR}/og_price_levels.csv', index=False, float_format='%.4g')
print(lv.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 2b volume validation (n=17)
VOL = {
    'w_real_wage_yoy': 'real wage growth (Orkla-wtd)', 'nw_real_wage_yoy': 'real wage growth (NO+SE)',
    'w_hh_real_inc_yoy': 'real disposable income (Orkla-wtd)', 'w_cons_conf_z': 'consumer confidence (z)',
    'nw_cons_conf_z': 'consumer confidence NO+SE (z)', 'w_cons_conf_z_d4': 'consumer confidence, y/y change',
    'w_unemp_d4': 'unemployment rate, y/y change', 'w_unemp_lvl': 'unemployment rate, level',
    'w_retail_food_vol_yoy': 'retail food volumes (Orkla-wtd)', 'nw_retail_food_vol_yoy': 'grocery volumes (NO+SE)',
    'no_qna_hh_food_cons_sa_mnok__yoy': 'NO household food consumption (QNA)',
    'se_na_hhcons_food_sa__yoy': 'SE household food consumption (NA)', 'w_gdp_vol_yoy': 'real GDP growth (Orkla-wtd)',
    'w_food_rel_xvat_yoy': 'relative food price (food CPI ex VAT - CPI)', 'w_food_cpi_xvat_yoy': 'food CPI ex VAT (own price)',
    'w_policy_rate_d4': 'policy rate, y/y change', 'w_policy_rate_lvl': 'policy rate, level',
    'w_hh_saving_d4': 'household saving rate, y/y change',
    'no_border_trade_exp_mnok_s1__yoy': 'NO cross-border shopping spend (2005-22)',
    'no_fx_seknok__yoy': 'SEK per NOK (+ = NOK stronger, cheaper SE shopping)',
}
vv_rows = []
for c, lab in VOL.items():
    for k in (0, 1):
        z = X[c].shift(k).reindex(T.index).rename('z')
        yv = T['volume_mix'].where(P22)
        if z[P22].notna().sum() < 10:
            continue
        r = ols(yv, pd.concat([z, T['d_easter_window_q1']], axis=1), lags=2)
        d = pd.concat([yv, z], axis=1).dropna()
        pc, ph, po = small_p(r, 'z')
        vv_rows.append(dict(driver=c, label=lab, lag=k, n=int(r.nobs), corr=d.corr().iloc[0, 1], slope=r.params['z'],
                            se_hac=r.bse['z'], t_hac=r.tvalues['z'], p_hac_t=ph, p_ols_t=po, p=pc, r2=r.rsquared,
                            easter_coef=r.params['d_easter_window_q1']))
        tests.append(('og_volume_validation', f'{c}|L{k}', '2022Q2-2026Q2', r.tvalues['z'] ** 2, 1, pc, int(r.nobs)))
vv = pd.DataFrame(vv_rows)
vv['p_BY'] = M.mt_adjust(vv['p'], 'fdr_by'); vv['n_tests'] = len(vv)
vv.sort_values('p').to_csv(f'{M.OUTDIR}/og_volume_validation.csv', index=False, float_format='%.4g')
print(vv.sort_values('p').to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 2c volume proxy validation
vp_rows = []
for vpn in ['vol_proxy', 'vol_proxy_in']:
    for smp_name, smp in [('2022Q2-2026Q2', P22), ('2022Q3-2026Q2 (def E)', P22E)]:
        yv = T['volume_mix'].where(smp)
        r = ols(yv, T[[vpn]], lags=2)
        d = pd.concat([yv, T[vpn]], axis=1).dropna()
        vp_rows.append(dict(proxy=vpn, sample=smp_name, n=int(r.nobs), corr=d.corr().iloc[0, 1], slope=r.params[vpn],
                            slope_se=r.bse[vpn], intercept=r.params['const'], r2=r.rsquared,
                            mean_gap_reported_minus_proxy=(d.iloc[:, 0] - d.iloc[:, 1]).mean(),
                            corr_ex2025=d[~d.index.year.isin([2025])].corr().iloc[0, 1]))
# alternative proxy: og - theta*CPI with theta from price validation (coincident, Orkla-wtd CPI ex VAT)
th = pv.query('proxy=="w_food_cpi_xvat_yoy" and shift_k==0 and sample=="2022Q2-2026Q2"')['slope'].iloc[0]
ic = pv.query('proxy=="w_food_cpi_xvat_yoy" and shift_k==0 and sample=="2022Q2-2026Q2"')['intercept'].iloc[0]
T['vol_proxy_theta'] = T['og'] - (ic + th * XT['w_food_cpi_xvat_yoy'])
d = T.loc[P22, ['volume_mix', 'vol_proxy_theta']].dropna()
vp_rows.append(dict(proxy=f'og - ({ic:.2f} + {th:.2f}*CPIxvat) [in-sample fit, circular]', sample='2022Q2-2026Q2', n=len(d),
                    corr=d.corr().iloc[0, 1]))
vpdf = pd.DataFrame(vp_rows)
vpdf.to_csv(f'{M.OUTDIR}/og_volproxy_validation.csv', index=False, float_format='%.4g')
print(vpdf.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 2d volume drivers on vol_proxy
CTRL_OG = T[['d_easter_window_q1', 'ev_stockpile', 'covid', 'def_A', 'india', 'ev_distrib_og']]
# cross-border shopping collapsed during the 2020-22 border closures: always evaluate it excluding 2020Q1-2022Q4
EXCOV = pd.Series(~((T.index >= pd.Period('2020Q1', 'Q')) & (T.index <= pd.Period('2022Q4', 'Q'))), index=T.index)
W = T['w_og']
F_, D_ = F, D
vd_rows, ALIGNED = [], {}
for mode, h in [('coincident', 0), ('realtime', 0), ('realtime', 1), ('realtime', 2)]:
    Xa = C.align(F_[list(VOL)], D_.loc[list(VOL)], mode=mode, h=h)
    ALIGNED[(mode, h)] = Xa
    cpi_al = C.align(F_[['w_food_cpi_xvat_inclIN_yoy']], D_.loc[['w_food_cpi_xvat_inclIN_yoy']], mode=mode, h=h)[
        'w_food_cpi_xvat_inclIN_yoy'].reindex(T.index).rename('cpi')
    for c, lab in VOL.items():
        z = Xa[c].reindex(T.index).rename('z')
        for target in ['vol_proxy_in', 'og']:
            for s in ['full', 'ex_infl', 'post2008']:
                yv = T[target].where(M.mask(T, s))
                if c.startswith('no_border_trade'):
                    yv = yv.where(EXCOV)
                Xd = pd.concat([z, CTRL_OG] + ([cpi_al] if target == 'og' and c != 'w_food_cpi_xvat_yoy' else []), axis=1)
                try:
                    r = ols(yv, Xd, weights=W)
                except Exception:
                    continue
                if r.nobs < 30:
                    continue
                sd = z[M.mask(T, s) & yv.notna()].std()
                vd_rows.append(dict(target=target, driver=c, label=lab, mode=mode, h=h, sample=s, n=int(r.nobs),
                                    coef=r.params['z'], se=r.bse['z'], t=r.tvalues['z'], p=r.pvalues['z'],
                                    effect_1sd=r.params['z'] * sd, r2=r.rsquared))
                tests.append(('og_volume_drivers', f'{target}|{c}|{mode}{h}', s, r.tvalues['z'] ** 2, 1, r.pvalues['z'], int(r.nobs)))
vd = pd.DataFrame(vd_rows)
for (tg, mo, hh), g in vd.groupby(['target', 'mode', 'h']):
    vd.loc[g.index, 'p_BY_within_target_alignment'] = M.mt_adjust(g['p'], 'fdr_by')
vd['p_BY_family'] = M.mt_adjust(vd['p'], 'fdr_by')
vd['n_tests_family'] = len(vd)
vd.to_csv(f'{M.OUTDIR}/og_volume_drivers.csv', index=False, float_format='%.4g')
show = vd.query('target=="vol_proxy_in" and sample!="post2008"').pivot_table(
    index='driver', columns=['mode', 'h', 'sample'], values='t').round(1)
print(show.to_string())

# lead/lag profile: vol_proxy_in_t on driver_{t-k}, k=-4..+4 (k<0 uses future driver values: explanatory only)
ll_rows = []
for c in ['w_real_wage_yoy', 'nw_real_wage_yoy', 'w_hh_real_inc_yoy', 'w_cons_conf_z', 'w_cons_conf_z_d4',
          'w_retail_food_vol_yoy', 'nw_retail_food_vol_yoy', 'w_food_rel_xvat_yoy', 'w_unemp_d4', 'w_policy_rate_d4']:
    for k in range(-4, 5):
        z = X[c].shift(k).reindex(T.index).rename('z')
        for s in ['full', 'ex_infl']:
            yv = T['vol_proxy_in'].where(M.mask(T, s))
            r = ols(yv, pd.concat([z, CTRL_OG], axis=1), weights=W)
            ll_rows.append(dict(driver=c, k=k, sample=s, n=int(r.nobs), coef=r.params['z'], se=r.bse['z'], t=r.tvalues['z'],
                                p=r.pvalues['z'], r2=r.rsquared))
ll = pd.DataFrame(ll_rows)
ll.to_csv(f'{M.OUTDIR}/og_leadlag.csv', index=False, float_format='%.4g')
print(ll.pivot_table(index='driver', columns=['sample', 'k'], values='t').round(1).to_string())

# Granger-style incremental test: vol_proxy_in_t ~ own lags available + driver (real-time h)
gr_rows = []
for h in (0, 1, 2):
    own = pd.concat({f'own{j}': T['vol_proxy_in'].shift(h + 1 + j) for j in range(2)}, axis=1)
    Xa = ALIGNED[('realtime', h)]
    for c in ['w_real_wage_yoy', 'nw_real_wage_yoy', 'w_cons_conf_z', 'w_cons_conf_z_d4', 'w_retail_food_vol_yoy',
              'w_food_rel_xvat_yoy', 'w_hh_real_inc_yoy', 'w_unemp_d4']:
        z = pd.concat({f'{c}_L{j}': Xa[c].shift(j).reindex(T.index) for j in range(2)}, axis=1)
        for s in ['full', 'ex_infl']:
            yv = T['vol_proxy_in'].where(M.mask(T, s))
            base = pd.concat([own, CTRL_OG], axis=1)
            dfc = pd.concat([yv, base, z], axis=1).dropna()
            r0 = ols(dfc.iloc[:, 0], dfc[base.columns], weights=W)
            r1 = ols(dfc.iloc[:, 0], dfc[list(base.columns) + list(z.columns)], weights=W)
            Rm = np.zeros((2, len(r1.params)))
            for i, cc in enumerate(z.columns):
                Rm[i, list(r1.params.index).index(cc)] = 1
            Wst, dfw, p = M.wald_linear(r1.params.values, r1.cov_params().values, Rm, dfd=int(r1.df_resid))
            gr_rows.append(dict(driver=c, h=h, sample=s, n=int(r1.nobs), r2_base=r0.rsquared, r2_with=r1.rsquared,
                                sum_coef=r1.params[z.columns].sum(), p_joint=p))
            tests.append(('og_granger_volproxy', f'{c}|h{h}', s, Wst, dfw, p, int(r1.nobs)))
gr = pd.DataFrame(gr_rows)
gr['p_BY'] = M.mt_adjust(gr['p_joint'], 'fdr_by')
gr.to_csv(f'{M.OUTDIR}/og_granger.csv', index=False, float_format='%.4g')
print(gr.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 2e full-sample pass-through of food CPI into og
pt_rows = []
for cpi in ['w_food_cpi_xvat_inclIN_yoy', 'w_food_cpi_xvat_yoy', 'nw_food_cpi_xvat_yoy', 'w_food_ppi_yoy']:
    for s in ['full', 'ex_infl', 'post2008', 'pre2021']:
        yv = T['og'].where(M.mask(T, s))
        # contemporaneous
        r = ols(yv, pd.concat([XT[cpi].rename('cpi'), CTRL_OG], axis=1), weights=W)
        # with real-wage and confidence volume controls
        r2 = ols(yv, pd.concat([XT[cpi].rename('cpi'), XT[['w_real_wage_yoy', 'w_cons_conf_z']], CTRL_OG], axis=1), weights=W)
        # DL 0-3 (sum)
        f = M.fit_dl(T['og'], {cpi: X[cpi]}, CTRL_OG, M.mask(T, s), K=3, kind='unres', weights=W)
        cu = f['cum'].set_index('lag')
        pt_rows.append(dict(cpi=cpi, sample=s, n=int(r.nobs), theta_L0=r.params['cpi'], theta_L0_se=r.bse['cpi'],
                            theta_L0_with_vol_controls=r2.params['cpi'], theta_L0_with_vol_se=r2.bse['cpi'],
                            theta_DL_sum_L0_3=cu.loc[3, 'cum'], theta_DL_sum_se=cu.loc[3, 'se'],
                            DL_betas=' '.join(f'{v:+.2f}' for v in f['profile']['beta']), r2=r.rsquared))
        tests.append(('og_cpi_passthrough', cpi, s, r.tvalues['cpi'] ** 2, 1, r.pvalues['cpi'], int(r.nobs)))
ptd = pd.DataFrame(pt_rows)
ptd.to_csv(f'{M.OUTDIR}/og_passthrough.csv', index=False, float_format='%.4g')
print(ptd.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 2f joint volume model (pre-specified)
jm_rows = []
JOINT = ['w_real_wage_yoy', 'w_cons_conf_z', 'w_food_rel_xvat_yoy', 'w_unemp_d4']
for mode, h in [('coincident', 0), ('realtime', 1)]:
    Xa = ALIGNED[(mode, h)]
    for s in ['full', 'ex_infl', 'post2008']:
        for target in ['vol_proxy_in']:
            yv = T[target].where(M.mask(T, s))
            r = ols(yv, pd.concat([Xa[JOINT].reindex(T.index), CTRL_OG], axis=1), weights=W)
            for c in JOINT:
                jm_rows.append(dict(target=target, mode=mode, h=h, sample=s, n=int(r.nobs), driver=c, coef=r.params[c],
                                    se=r.bse[c], t=r.tvalues[c], p=r.pvalues[c], r2=r.rsquared))
jm = pd.DataFrame(jm_rows)
jm.to_csv(f'{M.OUTDIR}/og_joint_volume_model.csv', index=False, float_format='%.4g')
print(jm.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 2g COVID / out-of-home and cross-border
cb_rows = []
T['covid_stockpile_q1_2020'] = (T.index == pd.Period('2020Q1', 'Q')).astype(float)
T['covid_lockdown'] = ((T.index >= pd.Period('2020Q2', 'Q')) & (T.index <= pd.Period('2021Q2', 'Q'))).astype(float)
T['covid_base_2021q1'] = (T.index == pd.Period('2021Q1', 'Q')).astype(float)
T['reopening'] = ((T.index >= pd.Period('2021Q3', 'Q')) & (T.index <= pd.Period('2022Q2', 'Q'))).astype(float)
ctrl2 = T[['d_easter_window_q1', 'def_A', 'india', 'ev_distrib_og']]
r = ols(T['vol_proxy_in'], pd.concat([T[['covid_stockpile_q1_2020', 'covid_lockdown', 'covid_base_2021q1', 'reopening']],
                                      XT[['w_real_wage_yoy']], ctrl2], axis=1), weights=W)
for c in ['covid_stockpile_q1_2020', 'covid_lockdown', 'covid_base_2021q1', 'reopening']:
    cb_rows.append(dict(test='covid phases on vol_proxy_in', term=c, coef=r.params[c], se=r.bse[c], p=r.pvalues[c], n=int(r.nobs)))
# cross-border: Norwegian grocery volumes and vol_proxy on cross-border spend and SEK/NOK
for dep in ['no_retail_foodstores_vol_sa_idx__yoy', 'vol_proxy_in']:
    for c in ['no_border_trade_exp_mnok_s1__yoy', 'no_fx_seknok__yoy']:
        for k in (0, 1, 2):
            yv = (XT[dep] if dep in XT else T[dep]).rename('y').where(EXCOV)   # excl. 2020-22 border closures
            if dep == 'vol_proxy_in':
                Xd = pd.concat([X[c].shift(k).reindex(T.index).rename('z'), CTRL_OG], axis=1)
                rr = ols(yv, Xd, weights=W)
            else:
                Xd = pd.concat([X[c].shift(k).reindex(T.index).rename('z'), T[['covid', 'd_easter_window_q1']]], axis=1)
                rr = ols(yv, Xd)
            cb_rows.append(dict(test=f'{dep} ~ {c} (excl. 2020-22)', term=f'lag{k}', coef=rr.params['z'], se=rr.bse['z'], p=rr.pvalues['z'],
                                n=int(rr.nobs)))
            tests.append(('og_crossborder', f'{dep}~{c}|L{k}', 'excl_2020_22', rr.tvalues['z'] ** 2, 1, rr.pvalues['z'], int(rr.nobs)))
cb = pd.DataFrame(cb_rows)
cb.to_csv(f'{M.OUTDIR}/og_covid_border.csv', index=False, float_format='%.4g')
print(cb.to_string(float_format=lambda v: f'{v:.3g}'))

pd.DataFrame(tests, columns=['family', 'test', 'sample', 'stat', 'df', 'p', 'n']).to_csv(
    f'{M.OUTDIR}/mt_tests_organic.csv', index=False, float_format='%.4g')

# ============================================================================ figures
BLUE, ORANGE, AQUA, GRAY, INK, INK2 = '#2a78d6', '#eb6834', '#1baf7a', '#8a8984', '#0b0b0b', '#52514e'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': '#c9c8c3', 'axes.labelcolor': INK2, 'xtick.color': INK2,
                     'ytick.color': INK2, 'axes.titlesize': 9.5, 'axes.titlecolor': INK, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#ebeae6', 'grid.linewidth': 0.6,
                     'legend.frameon': False})

# Fig A: price & volume validation (scatter + time series)
fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.1))
d = pd.concat([T['price'], T['volume_mix'], T['vol_proxy'], XT['w_food_cpi_xvat_yoy'], XT['nw_food_cpi_xvat_yoy'],
               X['w_food_ppi_yoy'].shift(1).reindex(T.index).rename('ppi_L1')], axis=1)[P22]
ax = axes[0]
mx = 18
ax.plot([-1, mx], [-1, mx], color=GRAY, lw=1, ls=':', label='45° line (full pass-through)')
ax.scatter(d['w_food_cpi_xvat_yoy'], d['price'], s=40, color=BLUE, edgecolor='white', lw=1.2, zorder=3,
           label='Orkla-wtd food CPI ex VAT (same quarter)')
ax.scatter(d['ppi_L1'], d['price'], s=40, color=ORANGE, marker='s', edgecolor='white', lw=1.2, zorder=3,
           label='Orkla-wtd food PPI (1 quarter earlier)')
for p in [pd.Period('2022Q2', 'Q'), pd.Period('2023Q2', 'Q'), pd.Period('2025Q1', 'Q'), pd.Period('2026Q2', 'Q')]:
    ax.annotate(str(p), (d.loc[p, 'w_food_cpi_xvat_yoy'], d.loc[p, 'price']), xytext=(4, -10), textcoords='offset points',
                fontsize=7.5, color=INK2)
ax.set_xlabel('macro price inflation, % y/y'); ax.set_ylabel('Orkla reported price component, %')
ax.set_title('Price: Orkla price vs food CPI / PPI, 2022Q2-2026Q2', fontsize=9.5)
ax.legend(fontsize=7.5, loc='upper left')
ax = axes[1]
ax.scatter(d['vol_proxy'], d['volume_mix'], s=40, color=AQUA, edgecolor='white', lw=1.2, zorder=3)
ax.plot([-11, 4], [-11, 4], color=GRAY, lw=1, ls=':')
for p in d.index:
    if p.year in (2025,) or p in (pd.Period('2022Q3', 'Q'), pd.Period('2023Q2', 'Q')):
        ax.annotate(str(p), (d.loc[p, 'vol_proxy'], d.loc[p, 'volume_mix']), xytext=(4, 3), textcoords='offset points',
                    fontsize=7.5, color=INK2)
cc = d[['vol_proxy', 'volume_mix']].corr().iloc[0, 1]
ax.set_xlabel('implied volume proxy = organic growth - food CPI ex VAT, pp')
ax.set_ylabel('Orkla reported volume/mix, %')
ax.set_title(f'Volume: reported volume/mix vs implied proxy (corr {cc:.2f})', fontsize=9.5)
ax = axes[2]
idx = [str(p) for p in d.index]
ax.plot(idx, d['price'], color=BLUE, lw=2, marker='o', ms=4, label='Orkla price')
ax.plot(idx, d['w_food_cpi_xvat_yoy'], color=BLUE, lw=1.4, ls='--', label='food CPI ex VAT (Orkla-wtd)')
ax.plot(idx, d['volume_mix'], color=AQUA, lw=2, marker='o', ms=4, label='Orkla volume/mix')
ax.plot(idx, d['vol_proxy'], color=AQUA, lw=1.4, ls='--', label='implied volume proxy')
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(idx[::2]); ax.tick_params(axis='x', rotation=60)
ax.set_title('Reported split vs macro-implied split', fontsize=9.5)
ax.set_ylabel('%'); ax.legend(fontsize=7.5, loc='upper right')
fig.tight_layout()
M.savefig(fig, 'fig_og_price_volume_validation.png'); plt.close(fig)

# Fig B: full-sample implied volume proxy with drivers
fig, axes = plt.subplots(2, 1, figsize=(12, 6.2), sharex=True)
idx = T.index[T.index >= pd.Period('2001Q1', 'Q')]
xs = idx.to_timestamp()
ax = axes[0]
ax.plot(xs, T.loc[idx, 'og'], color=GRAY, lw=1.3, label='organic growth (reported)')
ax.plot(xs, T.loc[idx, 'vol_proxy_in'], color=AQUA, lw=2, label='implied volume proxy (og - food CPI ex VAT, India-blended)')
ax.plot(xs, T.loc[idx, 'volume_mix'], color=INK, lw=0, marker='o', ms=4, label='reported volume/mix (2022Q2+)')
ax.axhline(0, color=INK2, lw=0.8); ax.set_ylabel('%'); ax.legend(fontsize=8, loc='lower left', ncol=3)
ax.set_title('Organic growth and implied volume, 2001-2026', fontsize=9.5)
ax = axes[1]
ax.plot(xs, XT.loc[idx, 'w_real_wage_yoy'], color=BLUE, lw=2, label='real wage growth, % y/y (Orkla-wtd)')
ax.plot(xs, XT.loc[idx, 'w_food_rel_xvat_yoy'], color=ORANGE, lw=2, ls='--', label='relative food inflation, pp (food CPI ex VAT - CPI)')
ax.plot(xs, XT.loc[idx, 'w_cons_conf_z'], color=AQUA, lw=1.6, ls='-.', label='consumer confidence, z-score')
ax.axhline(0, color=INK2, lw=0.8); ax.legend(fontsize=8, loc='lower left', ncol=3)
ax.set_title('Candidate volume drivers', fontsize=9.5)
fig.tight_layout()
M.savefig(fig, 'fig_og_volume_proxy.png'); plt.close(fig)

# Fig C: lead/lag profile
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
for j, s in enumerate(['full', 'ex_infl']):
    ax = axes[j]
    for c, col, ls, lab in [('w_real_wage_yoy', BLUE, '-', 'real wage growth'), ('w_cons_conf_z', AQUA, '-.', 'consumer confidence (z)'),
                            ('w_food_rel_xvat_yoy', ORANGE, '--', 'relative food inflation')]:
        g = ll.query('driver==@c and sample==@s')
        ax.plot(g['k'], g['t'], color=col, lw=2, ls=ls, marker='o', ms=4, label=lab)
    ax.axhline(1.96, color=GRAY, lw=0.8, ls=':'); ax.axhline(-1.96, color=GRAY, lw=0.8, ls=':'); ax.axhline(0, color=INK2, lw=0.8)
    ax.axvline(0, color=GRAY, lw=0.8)
    ax.set_title({'full': 'full sample', 'ex_infl': 'excl. 2021Q3-2023Q4'}[s], fontsize=9.5)
    ax.set_xlabel('k: driver measured k quarters before the volume quarter (k<0 = after)')
axes[0].set_ylabel('HAC t-statistic'); axes[0].legend(fontsize=8)
fig.suptitle('Do real wages / confidence lead volumes? vol_proxy_t on driver_{t-k}, one driver at a time (controls incl.)',
             fontsize=10.5, color=INK, x=0.01, ha='left')
fig.tight_layout()
M.savefig(fig, 'fig_og_leadlag.png'); plt.close(fig)
print('done')
