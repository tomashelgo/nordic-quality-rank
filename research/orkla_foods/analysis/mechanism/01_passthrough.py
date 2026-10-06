"""Section 1: margin pass-through models (lens-mechanism).

d_margin_t (y/y EBIT-margin change, pp) on distributed lags of y/y input-cost inflation and
output-price inflation (Orkla-weighted food CPI ex VAT; food-manufacturing PPI as the
manufacturer-price alternative). Coincident alignment = explanatory. Real-time use: 04_realtime.py.

Specifications
  'K6'  : lags 0-6 (the brief), unrestricted / Almon PDL (quadratic) / ridge (2nd-difference penalty)
  'K12' : lags 0-12, PDL cubic (long enough to see margins being restored after a cost shock)
Interpretation: cumsum(beta)*10 = response of the margin LEVEL (pp) to a permanent +10% cost-level
shock (see mech_utils docstring).

Outputs: pt_candidates.csv, pt_lag_profiles.csv, pt_lag_stats.csv, pt_gap_vs_separate.csv,
pt_rules_of_thumb.csv, pt_price_formation.csv, pt_asymmetry.csv, pt_fx.csv, pt_multicost.csv,
pt_robustness.csv, mt_tests_passthrough.csv and fig_pt_*.png
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import mech_utils as M

T, F, D, X = M.load_all()
y = T['d_margin']
XT = X.reindex(T.index)          # sample statistics only (lags are built on the full X index)
CTRL = M.std_controls(T)         # d_easter_window_q1, covid
CTRL_EV = pd.concat([CTRL, T[['ev_bakers', 'ev_rieber', 'ev_hame', 'ev_erp_se']]], axis=1)
PRICE = 'w_food_cpi_xvat_yoy'
PPI = 'w_food_ppi_yoy'
SPECS = {'K6_unres': dict(K=6, kind='unres', P=2), 'K6_pdl': dict(K=6, kind='pdl', P=2),
         'K6_ridge': dict(K=6, kind='ridge', P=2), 'K12_pdl': dict(K=12, kind='pdl', P=3)}
tests = []   # (family, test, sample, stat, df, p, n)
X['elec_scaled'] = 0.25 * X['elec_nordic_loc_yoy'].clip(-100, 100)


def fit(yv, blocks, sample, spec, ctrl=CTRL, hac=M.HAC_LAGS):
    sp = SPECS[spec] if isinstance(spec, str) else spec
    return M.fit_dl(yv, blocks, ctrl, M.mask(T, sample) if isinstance(sample, str) else sample,
                    K=sp['K'], kind=sp['kind'], P=sp.get('P', 2), hac=hac)


def cumget(f, b, L):
    c = f['cum'].query('block==@b').set_index('lag')
    return c.loc[L, 'cum'], c.loc[L, 'se']


# ============================================================================ 1a candidate screen
CANDS = {
    'raw_mat_wloc_yoy': 'raw materials (EU agri + FAO), local ccy',
    'fao_ffpi_wloc_yoy': 'FAO food index, Orkla local ccy',
    'glob_fao_ffpi_nok__yoy': 'FAO food index, NOK',
    'fao_ffpi_sek_yoy': 'FAO food index, SEK',
    'glob_fao_ffpi_eur__yoy': 'FAO food index, EUR',
    'glob_fao_ffpi__yoy': 'FAO food index, USD',
    'wb_food_wloc_yoy': 'World Bank food, local ccy',
    'eu_agri_basket_wloc_yoy': 'EU agri basket, local ccy',
    'eu_agri_basket_yoy': 'EU agri basket, EUR',
    'eu_agri_raw_milk_price__yoy': 'EU raw milk, EUR',
    'eu_agri_pig_carcass_e_price__yoy': 'EU pig carcass, EUR',
    'glob_fao_dairy_idx__yoy': 'FAO dairy, USD',
    'glob_fao_meat_idx__yoy': 'FAO meat, USD',
    'glob_fao_cereals_idx__yoy': 'FAO cereals, USD',
    'glob_fao_vegoils_idx__yoy': 'FAO veg oils, USD',
    'glob_fao_sugar_idx__yoy': 'FAO sugar, USD',
    'w_food_ppi_yoy': 'food-manufacturing PPI (Orkla-wtd)',
    'nw_food_ppi_yoy': 'food-manufacturing PPI (NO+SE)',
    'se_ppi_agri_hmpi_idx__yoy': 'SE agricultural producer prices',
    'se_ppi_food_impi_idx__yoy': 'SE food import prices',
    'no_imp_price_food_idx__yoy': 'NO food import prices',
    'packaging_eu_yoy': 'EU packaging PPI (paper+plastic)',
    'packaging_us_yoy': 'US packaging inputs',
    'se_ppi_paper_packaging_itpi_idx__yoy': 'SE paper packaging prices',
    'se_ppi_plastic_packaging_itpi_idx__yoy': 'SE plastic packaging prices',
    'elec_nordic_loc_yoy': 'Nordic electricity, local ccy',
    'natgas_eu_eur_yoy': 'EU natural gas, EUR',
    'brent_nok_yoy': 'Brent, NOK',
    'w_wage_yoy': 'wages (Orkla-wtd)',
    'no_earn_idx_food_manuf_q__yoy': 'NO food-manufacturing earnings',
    'glob_gscpi__lvl': 'global supply-chain pressure (level)',
    'cost_idx_calib_yoy': 'calibrated cost index',
}
rows = []
for c, lab in CANDS.items():
    for s in M.SAMPLES:
        smp = M.mask(T, s)
        fu = fit(y, {c: X[c]}, s, 'K6_unres')
        fp = fit(y, {c: X[c]}, s, 'K6_pdl')
        fl = fit(y, {c: X[c]}, s, 'K12_pdl')
        cp = fp['cum'].set_index('lag'); cl = fl['cum'].set_index('lag')
        sd = XT[c][smp & y.notna()].std()
        rows.append(dict(feature=c, label=lab, sample=s, n=fp['n'], r2_pdl=fp['r2'], r2_unres=fu['r2'],
                         p_pdl=fp['wald'][c][2], p_unres=fu['wald'][c][2], p_K12=fl['wald'][c][2],
                         cum10_L0=10 * cp.loc[0, 'cum'], cum10_L2=10 * cp.loc[2, 'cum'], cum10_L6=10 * cp.loc[6, 'cum'],
                         trough_lag_K6=int(cp['cum'].idxmin()), trough10_K6=10 * cp['cum'].min(),
                         trough_lag_K12=int(cl['cum'].idxmin()), cum10_L12_K12=10 * cl.loc[12, 'cum'],
                         sd_feature=sd, trough_per_1sd=cp['cum'].min() * sd))
        tests.append(('pt_candidates_costonly_PDL', c, s, *fp['wald'][c], fp['n']))
cand = pd.DataFrame(rows)
for s in M.SAMPLES:
    m = cand['sample'] == s
    cand.loc[m, 'p_BY_within_sample'] = M.mt_adjust(cand.loc[m, 'p_pdl'], 'fdr_by')
    cand.loc[m, 'p_Holm_within_sample'] = M.mt_adjust(cand.loc[m, 'p_pdl'], 'holm')
cand['p_BY_family'] = M.mt_adjust(cand['p_pdl'], 'fdr_by')
cand['n_tests_family'] = len(cand)
cand = cand.sort_values(['sample', 'p_pdl'])
cand.to_csv(f'{M.OUTDIR}/pt_candidates.csv', index=False, float_format='%.4g')
print('candidate tests:', len(cand))
print(cand[['feature', 'sample', 'n', 'r2_pdl', 'p_pdl', 'p_BY_family', 'cum10_L0', 'cum10_L2', 'cum10_L6',
            'trough_lag_K6', 'trough_lag_K12', 'cum10_L12_K12', 'trough_per_1sd']].to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 1b main models
MAIN_COSTS = ['raw_mat_wloc_yoy', 'eu_agri_basket_wloc_yoy', 'cost_idx_calib_yoy', 'packaging_eu_yoy', PPI]
prof_rows, stat_rows, FITS = [], [], {}
for c in MAIN_COSTS:
    for s in M.SAMPLES:
        models = [('cost_only', {c: X[c]})]
        if c != PPI:
            models += [('cost_plus_cpi', {c: X[c], PRICE: X[PRICE]}), ('cost_plus_ppi', {c: X[c], PPI: X[PPI]})]
        for model, blocks in models:
            for spec in SPECS:
                f = fit(y, blocks, s, spec)
                FITS[(c, s, model, spec)] = f
                pr = f['profile'].merge(f['cum'], on=['block', 'lag'], suffixes=('', '_cum')).rename(columns={'se_cum': 'cum_se'})
                pr = pr.assign(cost=c, sample=s, model=model, spec=spec, n=f['n'], r2=f['r2'])
                prof_rows.append(pr)
                for b in blocks:
                    st = M.lag_stats_sim(f, b, nsim=3000, seed=1)
                    stat_rows.append(dict(cost=c, sample=s, model=model, spec=spec, block=b, n=f['n'], r2=f['r2'],
                                          p_block=f['wald'][b][2],
                                          min_cum10=10 * f['cum'].query('block==@b')['cum'].min(),
                                          max_cum10=10 * f['cum'].query('block==@b')['cum'].max(),
                                          trough_lag_point=st['trough_point'], trough_p5=st['trough'][1],
                                          trough_med=st['trough'][0], trough_p95=st['trough'][2],
                                          recovery_half_med=st['recovery'][0], recovery_half_p5=st['recovery'][1],
                                          recovery_half_p95=st['recovery'][2],
                                          share_no_half_recovery=st['recovery_share_na'],
                                          peakcum_lag_point=st['peakcum_point'], peakpos_lag_point=st['peakpos_point'],
                                          peakpos_p5=st['peakpos'][1], peakpos_p95=st['peakpos'][2]))
                if spec == 'K6_pdl':
                    for b in blocks:
                        tests.append((f'pt_main_{model}', f'{c}|{b}', s, *f['wald'][b], f['n']))
prof = pd.concat(prof_rows)
prof.to_csv(f'{M.OUTDIR}/pt_lag_profiles.csv', index=False, float_format='%.4g')
lagst = pd.DataFrame(stat_rows)
lagst.to_csv(f'{M.OUTDIR}/pt_lag_stats.csv', index=False, float_format='%.3g')
print(lagst[lagst.spec.isin(['K6_pdl', 'K12_pdl'])].to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 1c price formation
# How fast do raw-material costs pass into manufacturer prices (food PPI ~ Orkla-type selling prices)
# and retail food prices (CPI ex VAT)? Cumulative elasticity = long-run pass-through of a permanent
# 1% cost-level shock into the price level.
pf_rows, PF = [], {}
for dep in [PPI, PRICE, 'nw_food_cpi_xvat_yoy']:
    for c in ['raw_mat_wloc_yoy', 'eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy', 'cost_idx_calib_yoy']:
        for s in M.SAMPLES:
            f = fit(X[dep].reindex(T.index), {c: X[c]}, s, 'K12_pdl', ctrl=T[['covid']], hac=8)  # persistent residuals
            PF[(dep, c, s)] = f
            cu = f['cum'].query('block==@c').set_index('lag')
            lr = cu.loc[12, 'cum']
            half = next((k for k in cu.index if lr > 0 and cu.loc[k, 'cum'] >= 0.5 * lr), np.nan)
            pf_rows.append(dict(price=dep, cost=c, sample=s, n=f['n'], r2=f['r2'], p=f['wald'][c][2],
                                cum_L0=cu.loc[0, 'cum'], cum_L2=cu.loc[2, 'cum'], cum_L4=cu.loc[4, 'cum'],
                                cum_L6=cu.loc[6, 'cum'], cum_L8=cu.loc[8, 'cum'], cum_L12=lr, cum_L12_se=cu.loc[12, 'se'],
                                lag_half_of_L12=half))
            tests.append(('pt_price_formation', f'{dep}~{c}', s, *f['wald'][c], f['n']))
pf = pd.DataFrame(pf_rows)
pf.to_csv(f'{M.OUTDIR}/pt_price_formation.csv', index=False, float_format='%.4g')
print(pf.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 1d gap vs separate
gap_rows = []
for out in [PRICE, PPI]:
    for c in ['raw_mat_wloc_yoy', 'eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy', 'cost_idx_calib_yoy']:
        for s in M.SAMPLES:
            sep = fit(y, {c: X[c], out: X[out]}, s, 'K6_unres')
            res = sep['res']; names = list(res.params.index); dfd = int(res.df_resid)
            cc, pc = sep['maps'][c][0], sep['maps'][out][0]
            R = np.zeros((7, len(names)))
            for k in range(7):
                R[k, names.index(cc[k])] = 1; R[k, names.index(pc[k])] = 1
            W1, df1, p1 = M.wald_linear(res.params.values, res.cov_params().values, R, dfd=dfd)
            W2, df2, p2 = M.wald_linear(res.params.values, res.cov_params().values, R.sum(0, keepdims=True), dfd=dfd)
            g = fit(y, {'gap': (X[out] - X[c]).rename('gap')}, s, 'K6_unres')
            sepp = fit(y, {c: X[c], out: X[out]}, s, 'K6_pdl')
            gp = fit(y, {'gap': (X[out] - X[c]).rename('gap')}, s, 'K6_pdl')
            best = None
            for sc in np.arange(0.02, 3.01, 0.02):
                gg = fit(y, {'gap': (X[out] - sc * X[c]).rename('gap')}, s, 'K6_pdl')
                ssr = (gg['resid'] ** 2).sum()
                if best is None or ssr < best[1]:
                    best = (sc, ssr, gg)
            gcum = gp['cum'].set_index('lag')
            gap_rows.append(dict(output_price=out, cost=c, sample=s, n=sep['n'],
                                 r2_sep_unres=sep['r2'], r2_gap_unres=g['r2'], bic_sep_unres=res.bic, bic_gap_unres=g['res'].bic,
                                 r2_sep_pdl=sepp['r2'], r2_gap_pdl=gp['r2'], bic_sep_pdl=sepp['res'].bic, bic_gap_pdl=gp['res'].bic,
                                 p_unit_gap_all_lags=p1, p_longrun_homogeneity=p2,
                                 sum_cost_unres=cumget(sep, c, 6)[0], sum_price_unres=cumget(sep, out, 6)[0],
                                 gap_pdl_p=gp['wald']['gap'][2], gap_pdl_cum_L0=gcum.loc[0, 'cum'],
                                 gap_pdl_cum_L2=gcum.loc[2, 'cum'], gap_pdl_cum_L6=gcum.loc[6, 'cum'],
                                 scaled_gap_weight_on_cost=best[0], r2_scaled_gap_pdl=best[2]['r2'],
                                 bic_scaled_gap_pdl=best[2]['res'].bic + np.log(sep['n'])))
            tests.append(('pt_gap_unit_restriction', f'{out}-{c}', s, W1, df1, p1, sep['n']))
            tests.append(('pt_gap_PDL', f'{out}-{c}', s, *gp['wald']['gap'], gp['n']))
for gname in ['price_cost_gap_agri', 'price_cost_gap_fao_wloc', 'price_cost_gap_fao_nok', 'price_cost_gap_ppi',
              'nw_price_cost_gap_ppi', 'price_wage_gap', 'gap_calib', 'gap_raw_xvat_wloc']:
    for s in M.SAMPLES:
        gp = fit(y, {gname: X[gname]}, s, 'K6_pdl')
        gcum = gp['cum'].set_index('lag')
        gap_rows.append(dict(output_price='[panel gap]', cost=gname, sample=s, n=gp['n'], r2_gap_pdl=gp['r2'],
                             bic_gap_pdl=gp['res'].bic, gap_pdl_p=gp['wald'][gname][2],
                             gap_pdl_cum_L0=gcum.loc[0, 'cum'], gap_pdl_cum_L2=gcum.loc[2, 'cum'],
                             gap_pdl_cum_L6=gcum.loc[6, 'cum']))
        tests.append(('pt_gap_PDL', gname, s, *gp['wald'][gname], gp['n']))
gapdf = pd.DataFrame(gap_rows)
gapdf.to_csv(f'{M.OUTDIR}/pt_gap_vs_separate.csv', index=False, float_format='%.4g')
print(gapdf.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 1e rules of thumb
# Single-index models: d_margin on moving averages of y/y inflation / gaps (coincident and lagged).
rt_rows = []
RT = {'raw_mat_wloc_yoy': X['raw_mat_wloc_yoy'], 'cost_idx_calib_yoy': X['cost_idx_calib_yoy'],
      'packaging_eu_yoy': X['packaging_eu_yoy'], 'gap_raw_xvat_wloc': X['gap_raw_xvat_wloc'],
      'gap_calib': X['gap_calib'], 'price_cost_gap_agri': X['price_cost_gap_agri'],
      'ppi_minus_raw (manufacturer gap)': X[PPI] - X['raw_mat_wloc_yoy']}
WINDOWS = {'avg L0-2': (0, 2), 'avg L1-4': (1, 4), 'avg L0-3 minus avg L4-7 (acceleration)': None}
for nm, x in RT.items():
    for wn, w in WINDOWS.items():
        if w is None:
            z = x.rolling(4).mean() - x.shift(4).rolling(4).mean()
        else:
            z = x.shift(w[0]).rolling(w[1] - w[0] + 1).mean()
        for s in M.SAMPLES:
            r = M.C.nw_ols(y.where(M.mask(T, s)), pd.concat([z.rename('z'), CTRL], axis=1), lags=M.HAC_LAGS)
            sd = z.reindex(T.index)[M.mask(T, s) & y.notna()].std()
            rt_rows.append(dict(index=nm, window=wn, sample=s, n=int(r.nobs), slope=r.params['z'], se=r.bse['z'],
                                t=r.tvalues['z'], p=r.pvalues['z'], r2=r.rsquared, effect_of_10pp=10 * r.params['z'],
                                effect_of_1sd=r.params['z'] * sd))
            tests.append(('pt_rules_of_thumb', f'{nm}|{wn}', s, r.tvalues['z'] ** 2, 1, r.pvalues['z'], int(r.nobs)))
rt = pd.DataFrame(rt_rows)
rt.to_csv(f'{M.OUTDIR}/pt_rules_of_thumb.csv', index=False, float_format='%.4g')
print(rt.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 1f asymmetry
asy_rows, ASY = [], {}
for c in ['raw_mat_wloc_yoy', 'eu_agri_basket_wloc_yoy', 'cost_idx_calib_yoy', 'packaging_eu_yoy']:
    for s in M.SAMPLES:
        smp = M.mask(T, s)
        xp, xn = X[c].clip(lower=0), X[c].clip(upper=0)
        for spec in ['K6_pdl', 'K6_unres', 'K12_pdl']:
            f = fit(y, {'pos': xp, 'neg': xn}, s, spec)
            ASY[(c, s, spec)] = f
            res = f['res']; names = list(res.params.index); dfd = int(res.df_resid)
            pc, nc = f['maps']['pos'][0], f['maps']['neg'][0]
            R = np.zeros((len(pc), len(names)))
            for i in range(len(pc)):
                R[i, names.index(pc[i])] = 1; R[i, names.index(nc[i])] = -1
            W, df, p = M.wald_linear(res.params.values, res.cov_params().values, R, dfd=dfd)
            H = f['maps']['pos'][1]
            pe = {}
            for L in (1, 2, 6):
                w = np.zeros(len(names)); cw = H[:L + 1].sum(0)
                for i in range(len(pc)):
                    w[names.index(pc[i])] += cw[i]; w[names.index(nc[i])] -= cw[i]
                pe[L] = M.wald_linear(res.params.values, res.cov_params().values, w[None, :], dfd=dfd)[2]
            row = dict(cost=c, sample=s, spec=spec, n=f['n'], r2=f['r2'],
                       n_pos=int((XT[c][smp & y.notna()] > 0).sum()), n_neg=int((XT[c][smp & y.notna()] <= 0).sum()),
                       p_equal_profile=p, p_equal_cum_L1=pe[1], p_equal_cum_L2=pe[2], p_equal_cum_L6=pe[6])
            for b in ('pos', 'neg'):
                for L in (0, 1, 2, 4, 6):
                    v, se = cumget(f, b, L)
                    # margin effect of a +10pp (pos) or -10pp (neg) y/y move
                    row[f'{b}_effect10_L{L}'] = (10 if b == 'pos' else -10) * v
                row[f'{b}_effect10_L2_se'] = 10 * cumget(f, b, 2)[1]
            asy_rows.append(row)
            if spec == 'K6_pdl':
                tests.append(('pt_asymmetry_profile', c, s, W, df, p, f['n']))
asy = pd.DataFrame(asy_rows)
asy.to_csv(f'{M.OUTDIR}/pt_asymmetry.csv', index=False, float_format='%.4g')
print(asy.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 1g FX channel
fx_rows, FX = [], {}
FXS = {'w_fx_vs_usd_yoy': 'Orkla-wtd ccy vs USD', 'w_fx_vs_eur_yoy': 'Orkla-wtd ccy vs EUR',
       'no_fx_usdnok__yoy': 'USD/NOK', 'se_usdsek__yoy': 'USD/SEK',
       'no_fx_eurnok__yoy': 'EUR/NOK', 'se_eursek__yoy': 'EUR/SEK'}
USDC = 'glob_fao_ffpi__yoy'
for fx, lab in FXS.items():
    for s in M.SAMPLES:
        for specname, blocks in [('fx_only', {fx: X[fx]}), ('fx+usd_commod', {fx: X[fx], USDC: X[USDC]}),
                                 ('fx+usd_commod+cpi', {fx: X[fx], USDC: X[USDC], PRICE: X[PRICE]})]:
            for spec in ['K6_pdl', 'K12_pdl']:
                f = fit(y, blocks, s, spec)
                FX[(fx, s, specname, spec)] = f
                cu = f['cum'].query('block==@fx').set_index('lag')
                row = dict(fx=fx, label=lab, sample=s, controls=specname, spec=spec, n=f['n'], r2=f['r2'],
                           p_fx=f['wald'][fx][2], eff10_L0=10 * cu.loc[0, 'cum'], eff10_L2=10 * cu.loc[2, 'cum'],
                           eff10_L4=10 * cu.loc[4, 'cum'], eff10_L6=10 * cu.loc[6, 'cum'], eff10_L6_se=10 * cu.loc[6, 'se'],
                           trough_lag=int(cu['cum'].idxmin()), trough_eff10=10 * cu['cum'].min())
                if spec == 'K12_pdl':
                    row.update(eff10_L8=10 * cu.loc[8, 'cum'], eff10_L12=10 * cu.loc[12, 'cum'])
                if USDC in blocks:
                    res = f['res']; names = list(res.params.index)
                    a, bb = f['maps'][fx][0], f['maps'][USDC][0]
                    R = np.zeros((len(a), len(names)))
                    for k in range(len(a)):
                        R[k, names.index(a[k])] = 1; R[k, names.index(bb[k])] = -1
                    row['p_fx_eq_usd_commod'] = M.wald_linear(res.params.values, res.cov_params().values, R,
                                                              dfd=int(res.df_resid))[2]
                    cuu = f['cum'].query('block==@USDC').set_index('lag')
                    row['usd_commod_eff10_L2'] = 10 * cuu.loc[2, 'cum']; row['usd_commod_eff10_L6'] = 10 * cuu.loc[6, 'cum']
                fx_rows.append(row)
                if specname == 'fx+usd_commod' and spec == 'K6_pdl':
                    tests.append(('pt_fx_given_usd_commod', fx, s, *f['wald'][fx], f['n']))
fxdf = pd.DataFrame(fx_rows)
fxdf.to_csv(f'{M.OUTDIR}/pt_fx.csv', index=False, float_format='%.4g')
print(fxdf.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 1h multi-cost
mc_rows, MC_FITS = [], {}
MC = ['raw_mat_wloc_yoy', 'packaging_eu_yoy', 'elec_scaled', 'w_wage_yoy', PRICE]
for s in M.SAMPLES:
    for spec in ['K6_pdl', 'K6_ridge']:
        f = fit(y, {b: X[b] for b in MC}, s, spec)
        MC_FITS[(s, spec)] = f
        for b in MC:
            row = dict(sample=s, spec=spec, block=b, n=f['n'], r2=f['r2'],
                       p_block=f['wald'][b][2] if spec == 'K6_pdl' else np.nan)
            for L in (0, 1, 2, 4, 6):
                row[f'eff10_L{L}'] = 10 * cumget(f, b, L)[0]
            row['eff10_L2_se'] = 10 * cumget(f, b, 2)[1]; row['eff10_L6_se'] = 10 * cumget(f, b, 6)[1]
            mc_rows.append(row)
            if spec == 'K6_pdl':
                tests.append(('pt_multicost_block', b, s, *f['wald'][b], f['n']))
mc = pd.DataFrame(mc_rows)
mc.to_csv(f'{M.OUTDIR}/pt_multicost.csv', index=False, float_format='%.4g')
print(mc.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 1i robustness
rb_rows = []
RSPEC = {
    'baseline K6 PDL2 HAC4': dict(y=y, ctrl=CTRL, spec='K6_pdl', hac=4),
    'HAC 8 lags': dict(y=y, ctrl=CTRL, spec='K6_pdl', hac=8),
    'K8 PDL3': dict(y=y, ctrl=CTRL, spec=dict(K=8, kind='pdl', P=3), hac=4),
    'K12 PDL3': dict(y=y, ctrl=CTRL, spec='K12_pdl', hac=4),
    'unrestricted K6': dict(y=y, ctrl=CTRL, spec='K6_unres', hac=4),
    'ridge K6': dict(y=y, ctrl=CTRL, spec='K6_ridge', hac=4),
    '+ event dummies': dict(y=y, ctrl=CTRL_EV, spec='K6_pdl', hac=4),
    'easter_shift control': dict(y=y, ctrl=T[['easter_shift', 'covid']], spec='K6_pdl', hac=4),
    'no controls': dict(y=y, ctrl=pd.DataFrame(index=T.index), spec='K6_pdl', hac=4),
    'target d_margin_r4': dict(y=T['d_margin_r4'], ctrl=T[['covid']], spec='K6_pdl', hac=6),
}
for c in ['raw_mat_wloc_yoy', 'cost_idx_calib_yoy', 'eu_agri_basket_wloc_yoy', 'packaging_eu_yoy']:
    for sname in ['full', 'ex_infl', 'post2008', 'post2008_ex_infl', 'pre2021']:
        for spn, sp in RSPEC.items():
            for model in ['cost_only', 'cost_plus_cpi']:
                blocks = {c: X[c]} if model == 'cost_only' else {c: X[c], PRICE: X[PRICE]}
                f = fit(sp['y'], blocks, sname, sp['spec'], ctrl=sp['ctrl'], hac=sp['hac'])
                cu = f['cum'].query('block==@c').set_index('lag')
                row = dict(cost=c, sample=sname, spec=spn, model=model, n=f['n'], r2=f['r2'], p_cost=f['wald'][c][2],
                           cost_eff10_L0=10 * cu.loc[0, 'cum'], cost_eff10_L1=10 * cu.loc[1, 'cum'],
                           cost_eff10_L2=10 * cu.loc[2, 'cum'], cost_eff10_L2_se=10 * cu.loc[2, 'se'],
                           cost_eff10_L6=10 * cu.loc[6, 'cum'], cost_eff10_L6_se=10 * cu.loc[6, 'se'],
                           cost_trough_lag=int(cu['cum'].idxmin()), cost_trough_eff10=10 * cu['cum'].min())
                if model == 'cost_plus_cpi':
                    pu = f['cum'].query('block==@PRICE').set_index('lag')
                    row.update(cpi_eff1_L2=pu.loc[2, 'cum'], cpi_eff1_L6=pu.loc[6, 'cum'], p_cpi=f['wald'][PRICE][2])
                rb_rows.append(row)
rb = pd.DataFrame(rb_rows)
rb.to_csv(f'{M.OUTDIR}/pt_robustness.csv', index=False, float_format='%.4g')

pd.DataFrame(tests, columns=['family', 'test', 'sample', 'stat', 'df', 'p', 'n']).to_csv(
    f'{M.OUTDIR}/mt_tests_passthrough.csv', index=False, float_format='%.4g')

# ============================================================================ figures
BLUE, ORANGE, AQUA, GRAY, INK, INK2 = '#2a78d6', '#eb6834', '#1baf7a', '#8a8984', '#0b0b0b', '#52514e'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': '#c9c8c3', 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.titlesize': 9.5, 'axes.titlecolor': INK,
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True,
                     'grid.color': '#ebeae6', 'grid.linewidth': 0.6, 'legend.frameon': False})
SLAB = {'full': 'full sample', 'ex_infl': 'excl. 2021Q3-2023Q4'}


def band(ax, lag, v, se, col, label=None, ls='-', mk='o', scale=1.0):
    v, se = np.asarray(v) * scale, np.asarray(se) * scale
    ax.plot(lag, v, color=col, lw=2, ls=ls, marker=mk, ms=4, label=label)
    ax.fill_between(lag, v - 1.645 * se, v + 1.645 * se, color=col, alpha=0.13, lw=0)


# Fig 1: per-lag beta, K6, three estimators; rows = raw materials / calibrated cost index; cols = cost-only, cost+CPI cost term, CPI term
fig, axes = plt.subplots(2, 3, figsize=(12.5, 6.8), sharex=True)
for i, c in enumerate(['raw_mat_wloc_yoy', 'cost_idx_calib_yoy']):
    for j, (model, blk, ttl) in enumerate([('cost_only', c, 'cost-only model: cost lags'),
                                            ('cost_plus_cpi', c, 'cost + food CPI model: cost lags'),
                                            ('cost_plus_cpi', PRICE, 'cost + food CPI model: food CPI ex VAT lags')]):
        ax = axes[i, j]
        d = prof.query('cost==@c and sample=="full" and model==@model and spec=="K6_unres" and block==@blk')
        ax.errorbar(d['lag'] - 0.12, d['beta'], yerr=1.645 * d['se'], fmt='o', color=GRAY, ms=3.5, lw=1, label='unrestricted')
        for spec, col, ls, mk, lab in [('K6_pdl', BLUE, '-', 's', 'Almon PDL (quadratic)'),
                                       ('K6_ridge', ORANGE, '--', '^', 'ridge (2nd-difference penalty)')]:
            d = prof.query('cost==@c and sample=="full" and model==@model and spec==@spec and block==@blk')
            band(ax, d['lag'], d['beta'], d['se'], col, lab, ls, mk)
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_title(f"{CANDS[c]}\n{ttl}", fontsize=9)
        if j == 0:
            ax.set_ylabel('pp of y/y margin change per 1pp inflation')
        if i == 1:
            ax.set_xlabel('lag (quarters)')
axes[0, 0].legend(loc='lower right', fontsize=8)
fig.suptitle('Margin pass-through lag profiles: d_margin on y/y inflation at lags 0-6 (full sample, 90% HAC bands)',
             fontsize=10.5, color=INK, x=0.01, ha='left')
fig.tight_layout()
M.savefig(fig, 'fig_pt_lag_profiles.png'); plt.close(fig)

# Fig 2: margin LEVEL response to permanent +10% cost-level shock (K12 PDL cubic, cost-only)
fig, axes = plt.subplots(1, 4, figsize=(14, 3.9), sharey=False)
for j, c in enumerate(['raw_mat_wloc_yoy', 'eu_agri_basket_wloc_yoy', 'cost_idx_calib_yoy', 'packaging_eu_yoy']):
    ax = axes[j]
    for s, col, ls in [('full', BLUE, '-'), ('ex_infl', ORANGE, '--')]:
        d = prof.query('cost==@c and sample==@s and model=="cost_only" and spec=="K12_pdl" and block==@c')
        band(ax, d['lag'], d['cum'], d['cum_se'], col, SLAB[s], ls, scale=10)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_title(CANDS[c], fontsize=9)
    ax.set_xlabel('quarters after the shock')
    if j == 0:
        ax.set_ylabel('EBIT-margin level response, pp')
axes[0].legend(loc='lower right', fontsize=8)
fig.suptitle('Margin-level response to a permanent +10% input-cost shock (cost-only DL, lags 0-12, cubic PDL; prices respond endogenously; 90% bands)',
             fontsize=10.5, color=INK, x=0.01, ha='left')
fig.tight_layout()
M.savefig(fig, 'fig_pt_level_response.png'); plt.close(fig)

# Fig 3: price formation (pass-through of raw materials into PPI and CPI)
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for j, s in enumerate(M.SAMPLES):
    ax = axes[j]
    for dep, col, lab in [(PPI, BLUE, 'food-manufacturing PPI (manufacturer prices)'),
                          (PRICE, ORANGE, 'food CPI ex VAT (retail prices)')]:
        f = PF[(dep, 'raw_mat_wloc_yoy', s)]
        d = f['cum']
        band(ax, d['lag'], d['cum'], d['se'], col, lab, '-' if dep == PPI else '--')
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_title(SLAB[s], fontsize=9); ax.set_xlabel('quarters after a permanent +1% raw-material shock')
axes[0].set_ylabel('price-level response, %')
axes[0].legend(fontsize=8, loc='upper left')
fig.suptitle('Price formation: cumulative pass-through of raw-material costs (local ccy) into food prices (lags 0-12, cubic PDL, 90% bands)',
             fontsize=10.5, color=INK, x=0.01, ha='left')
fig.tight_layout()
M.savefig(fig, 'fig_pt_price_formation.png'); plt.close(fig)

# Fig 4: asymmetry
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for j, s in enumerate(M.SAMPLES):
    ax = axes[j]
    f = ASY[('raw_mat_wloc_yoy', s, 'K6_pdl')]
    for blk, col, lab, sg in [('pos', ORANGE, '+10pp cost increase', 10), ('neg', BLUE, '-10pp cost decrease', -10)]:
        d = f['cum'].query('block==@blk')
        band(ax, d['lag'], d['cum'], d['se'], col, lab, scale=sg)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_title(SLAB[s], fontsize=9); ax.set_xlabel('lag (quarters)')
axes[0].set_ylabel('cumulative margin effect, pp')
axes[0].legend(fontsize=8, loc='lower left')
fig.suptitle('Asymmetry: raw-material inflation (local ccy) split by sign; cumulative effect of a 10pp move (K6 PDL, 90% bands)',
             fontsize=10.5, color=INK, x=0.01, ha='left')
fig.tight_layout()
M.savefig(fig, 'fig_pt_asymmetry.png'); plt.close(fig)

# Fig 5: FX
fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8), sharey=True)
for j, fx in enumerate(['w_fx_vs_usd_yoy', 'se_eursek__yoy', 'no_fx_eurnok__yoy']):
    ax = axes[j]
    for s, col, ls in [('full', BLUE, '-'), ('ex_infl', ORANGE, '--')]:
        d = FX[(fx, s, 'fx+usd_commod', 'K12_pdl')]['cum'].query('block==@fx')
        band(ax, d['lag'], d['cum'], d['se'], col, SLAB[s], ls, scale=10)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_title(f'{FXS[fx]} (+ = local currency weaker)', fontsize=9)
    ax.set_xlabel('lag (quarters)')
axes[0].set_ylabel('cumulative margin effect of a 10% depreciation, pp')
axes[0].legend(fontsize=8, loc='lower left')
fig.suptitle('FX import-cost channel: depreciation effect controlling for FAO food prices in USD (lags 0-12, cubic PDL, 90% bands)',
             fontsize=10.5, color=INK, x=0.01, ha='left')
fig.tight_layout()
M.savefig(fig, 'fig_pt_fx.png'); plt.close(fig)
print('done')
