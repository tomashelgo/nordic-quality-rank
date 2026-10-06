"""Extra checks: second-episode dependence (2007-09), O4 unemployment by quarter type, O3 nowcast decomposition,
M2 PDL asymmetry, M3 real-time OOS at h=1..4, M1 Easter control."""
import numpy as np, pandas as pd
import vr_lib as V, oos_engine as E
pd.set_option('display.width', 250)
T, F, D = V.load(); idx = T.index
CV = pd.read_csv(f'{V.OUT}/composites_weight_variants.csv', index_col=0); CV.index = pd.PeriodIndex(CV.index, freq='Q')
EX = V.ex_mask(idx, 'infl')
ex07 = EX & ~pd.Series((idx >= pd.Period('2007Q2')) & (idx <= pd.Period('2009Q2')), index=idx)
ex0810 = EX & ~pd.Series((idx >= pd.Period('2008Q1')) & (idx <= pd.Period('2010Q4')), index=idx)
og, es, w_og = T['og'], T['easter_shift'].rename('easter'), T['w_og']
rows = []
def rec(claim, test, res, var):
    rows.append(dict(claim=claim, test=test, var=var, **V.coef(res, var)))

x = F['w_food_cpi_xvat_yoy'].reindex(idx).rename('x')
for lab, m in [('ex_infl', EX), ('ex_infl & ex 2007Q2-09Q2', ex07), ('ex_infl & ex 2008-10', ex0810),
               ('ex_infl & ex 2007Q2-09Q2, quality A/B', ex07 & T['og_quality'].isin(['A', 'B']))]:
    rec('O1', f'og ~ w_food_cpi_xvat | {lab}', V.ols(og, pd.concat([x, es], axis=1), w=w_og, sample=m), 'x')
pr = F['w_policy_rate_d4'].reindex(idx)
for k in (3, 4):
    for lab, m in [('ex_infl', EX), ('ex_infl & ex 2007Q2-09Q2', ex07), ('ex_infl & ex 2008-10', ex0810),
                   ('2011+ ex_infl', EX & pd.Series(idx >= pd.Period('2011Q1'), index=idx))]:
        rec('O6', f'og ~ w_policy_rate_d4 k={k} | {lab}', V.ols(og, pd.concat([pr.shift(k).rename('x'), es], axis=1), w=w_og, sample=m), 'x')
y = T['d_margin']
pk = F['packaging_eu_yoy'].reindex(idx).rename('x')
for lab, m in [('ex_infl', EX), ('ex_infl & ex 2007Q2-09Q2', ex07)]:
    rec('M1', f'd_margin ~ packaging coincident | {lab}', V.ols(y, pk, sample=m), 'x')
    rec('M1', f'd_margin ~ packaging + easter_shift + d_easter_window | {lab}', V.ols(y, pd.concat([pk, es, T['d_easter_window_q1']], axis=1), sample=m), 'x')
rm = CV['orig|raw_mat_wloc_yoy'].reindex(idx)
for lab, m in [('full', None), ('ex_infl', EX), ('ex_infl & ex 2007Q2-09Q2', ex07)]:
    rec('M1', f'd_margin ~ raw_mat_wloc avg L0-3 | {lab}', V.ols(y, rm.rolling(4).mean().rename('x'), sample=m), 'x')
for f, k in [('eu_ppi_dom_c105_idx__yoy', 6), ('se_ppi_food_hmpi_idx__yoy', 6)]:
    for lab, m in [('ex_infl', EX), ('ex_infl & ex 2007Q2-09Q2', ex07), ('2010+ ex_infl', EX & pd.Series(idx >= pd.Period('2010Q1'), index=idx))]:
        rec('M3', f'd_margin ~ {f} k={k} | {lab}', V.ols(y, F[f].reindex(idx).shift(k).rename('x'), sample=m), 'x')
R = pd.DataFrame(rows)
print(R.to_string(float_format=lambda v: f'{v:.3f}'))
R.to_csv(f'{V.OUT}/extra_insample.csv', index=False, float_format='%.4g')

# ---- M2 with quadratic PDL (as in the mechanism lens) over lags 0-6
def pdlZ(x, nm):
    return E.pdl(x, 6, 2, nm)
pos, neg = rm.clip(lower=0), rm.clip(upper=0)
ev = pd.DataFrame({'ev_bakers': V.win(idx, '2012Q1', '2012Q4'), 'ev_rieber': V.win(idx, '2013Q2', '2014Q1'),
                   'ev_hame': V.win(idx, '2016Q2', '2017Q1'), 'ev_eastern': V.win(idx, '2021Q2', '2022Q1'),
                   'ev_sladco': V.win(idx, '2005Q1', '2005Q4'), 'ev_krup': V.win(idx, '2006Q3', '2007Q2')})
out = []
for evlab, evs in [('none', None), ('pure M&A dummies', ev), ('Rieber only', ev[['ev_rieber']]),
                   ('pure M&A + covid', pd.concat([ev, T['covid']], axis=1))]:
    for s, m in [('full', None), ('ex_infl', EX)]:
        Z = pd.concat([pdlZ(pos, 'P'), pdlZ(neg, 'N')], axis=1)
        if evs is not None: Z = pd.concat([Z, evs], axis=1)
        r = V.ols(y, Z, sample=m)
        def lagcoef(pref):
            b = [r.params[f'{pref}_pdl{p}'] for p in range(3)]
            return np.array([b[0] + b[1] * k + b[2] * k * k for k in range(7)])
        cp, cn = np.cumsum(lagcoef('P')) * 10, np.cumsum(lagcoef('N')) * -10
        out.append(dict(events=evlab, sample=s, n=int(r.nobs), pos10_L1=cp[1], pos10_L2=cp[2], pos10_L6=cp[6],
                        neg10_L2=cn[2], neg10_L3=cn[3], neg10_L6=cn[6]))
out = pd.DataFrame(out); print(out.to_string(float_format=lambda v: f'{v:.2f}'))
out.to_csv(f'{V.OUT}/m2_asymmetry_pdl.csv', index=False, float_format='%.4g')

# ---- OOS: O4 unemployment by quarter type; O3 decomposition; M3 multi-quarter
MK = E.masks(idx)
MK['Q3Q4 ex_infl'] = MK['ex_infl'] & pd.Series(T['q'].isin([3, 4]).values, index=idx)
MK['Q1Q2 ex_infl'] = MK['ex_infl'] & pd.Series(T['q'].isin([1, 2]).values, index=idx)
MK['ex_infl ex 2010-12'] = MK['ex_infl'] & pd.Series((idx < pd.Period('2010Q1')) | (idx > pd.Period('2012Q4')), index=idx)
orow = []
def ar(tgt, h):
    lags = [h + 1] + ([4] if h + 1 < 4 else [5])
    return pd.DataFrame({f'ar{l}': T[tgt].shift(l) for l in lags}, index=idx)
def run(claim, lab, tgt, h, feats, base, w=None, masks=('all', 'ex_infl')):
    fb = E.expanding(T[tgt], base, h, w); fm = E.expanding(T[tgt], pd.concat([base, feats], axis=1), h, w)
    for mn in masks:
        orow.append(dict(claim=claim, model=lab, h=h, eval=mn, **E.evaluate(T[tgt], fb, fm, MK[mn])))
ux = F['w_unemp_d4'].reindex(idx)
run('O4', 'w_unemp_d4 h=2', 'og', 2, ux.shift(3).rename('x').to_frame(), ar('og', 2), w_og.fillna(0),
    masks=('all', 'ex_infl', 'Q3Q4 ex_infl', 'Q1Q2 ex_infl', 'ex_infl ex 2010-12', '2015+'))
base_e = pd.concat([ar('og', 2), T['easter_shift']], axis=1)
run('O4', 'w_unemp_d4 h=2, base AR+easter_shift', 'og', 2, ux.shift(3).rename('x').to_frame(), base_e, w_og.fillna(0),
    masks=('all', 'ex_infl', 'Q3Q4 ex_infl'))
for k in (2, 3, 4, 5):
    run('O4', f'w_unemp_d4 at t-{k} (h=1 base)', 'og', 1, ux.shift(k).rename('x').to_frame(), ar('og', 1), w_og.fillna(0), masks=('all', 'ex_infl'))
# O3 nowcast decomposition (h=0)
b0 = ar('og', 0)
c0 = F['nw_food_cpi_xvat_yoy'].reindex(idx).rename('fc'); cf = F['nw_cons_conf_z'].reindex(idx).rename('cf')
for lab, extra in [('fc + cf + real wage(t-1)', F['nw_real_wage_yoy'].reindex(idx).shift(1).rename('rw')),
                   ('fc + cf + headline CPI(t-1) [no revisions]', F['no_cpi_total_idx__yoy'].reindex(idx).shift(1).rename('hc') * 0.5 + F['se_cpi_idx__yoy'].reindex(idx).shift(1).rename('hc') * 0.5),
                   ('fc + cf + nominal wage(t-1)', (F['no_lci_wages_idx__yoy'].reindex(idx).shift(1) * 0.5 + F['se_wage_idx_m__yoy'].reindex(idx).shift(1) * 0.5).rename('nw')),
                   ('fc + cf + NO real wage only(t-1)', (F['no_lci_wages_idx__yoy'] - F['no_cpi_total_idx__yoy']).reindex(idx).shift(1).rename('rwno')),
                   ('fc + cf + SE real wage only(t-1)', (F['se_wage_idx_m__yoy'] - F['se_cpi_idx__yoy']).reindex(idx).shift(1).rename('rwse'))]:
    run('O3', lab, 'og', 0, pd.concat([c0, cf, extra.rename('z')], axis=1), b0, w_og.fillna(0), masks=('all', 'ex_infl', 'ex_infl_covid'))
# M3: real-time multi-quarter forecasts of d_margin with lagged PPI (x_{t-6}, lag1 -> usable up to h=5)
for f in ['eu_ppi_dom_c105_idx__yoy', 'se_ppi_food_hmpi_idx__yoy', 'se_cpi_idx__yoy']:
    for h in (1, 2, 3, 4):
        xx = F[f].reindex(idx).shift(6).rename('x')
        run('M3', f'{f} at t-6', 'd_margin', h, xx.to_frame(), ar('d_margin', h), masks=('all', 'ex_infl', 'ex_infl_covid'))
O = pd.DataFrame(orow)
print(O[['claim', 'model', 'h', 'eval', 'n', 'rmse_ratio', 'r2_vs_base', 'cw_t', 'cw_p']].to_string(float_format=lambda v: f'{v:.3f}'))
O.to_csv(f'{V.OUT}/extra_oos.csv', index=False, float_format='%.4g')
