"""M4 ex-episode in-sample robustness vs second episode; M6 OOS packaging at h0 and conditional nulls."""
import numpy as np, pandas as pd
import vr_lib as V, oos_engine as E
pd.set_option('display.width', 250)
T, F, D = V.load(); idx = T.index; y = T['d_margin']
EX = V.ex_mask(idx, 'infl')
ex07 = EX & ~pd.Series((idx >= pd.Period('2007Q2')) & (idx <= pd.Period('2009Q2')), index=idx)
rows = []
g = F['no_govbond_10y__d4'].reindex(idx).rename('x'); pk = F['packaging_eu_yoy'].reindex(idx).rename('pk')
for lab, m in [('ex_infl', EX), ('ex_infl & ex 2007Q2-09Q2', ex07), ('2010+ ex_infl', EX & pd.Series(idx >= pd.Period('2010Q1'), index=idx))]:
    rows.append(dict(test=f'd_margin ~ NO 10y d4 | {lab}', **V.coef(V.ols(y, g, sample=m), 'x')))
    rows.append(dict(test=f'd_margin ~ NO 10y d4 + packaging + raw_mat avg | {lab}',
                     **V.coef(V.ols(y, pd.concat([g, pk, F['eu_agri_basket_yoy'].reindex(idx).rolling(4).mean().rename('rm')], axis=1), sample=m), 'x')))
for f in ['w_cons_conf_z', 'w_real_wage_yoy']:
    lag = int(D.loc[f, 'realtime_min_lag_q'])
    for h in (0, 1):
        x = F[f].reindex(idx).shift(h + lag).rename('x')
        for lab, m in [('ex_infl', EX)]:
            rows.append(dict(test=f'd_margin ~ {f} rt h{h} | {lab}', **V.coef(V.ols(y, x, sample=m), 'x')))
            rows.append(dict(test=f'd_margin ~ {f} rt h{h} + packaging(rt) | {lab}',
                             **V.coef(V.ols(y, pd.concat([x, pk.shift(1 + h)], axis=1), sample=m), 'x')))
            rows.append(dict(test=f'd_margin ~ {f} rt h{h} + NO 10y d4 (rt) | {lab}',
                             **V.coef(V.ols(y, pd.concat([x, g.shift(h).rename('g')], axis=1), sample=m), 'x')))
R = pd.DataFrame(rows); print(R.to_string(float_format=lambda v: f'{v:.3f}'))
R.to_csv(f'{V.OUT}/m4_m6_insample.csv', index=False, float_format='%.4g')
MK = E.masks(idx); out = []
for h in (0, 1):
    base = pd.DataFrame({'a1': y.shift(h + 1), 'a4': y.shift(4)})
    for nm, x in [('packaging_eu_yoy (lag1)', F['packaging_eu_yoy'].reindex(idx).shift(1 + h)),
                  ('eu_ppi_plastic (lag1)', F['eu_ppi_plastic_products_idx__yoy'].reindex(idx).shift(1 + h)),
                  ('w_cons_conf_z (lag0)', F['w_cons_conf_z'].reindex(idx).shift(h)),
                  ('w_real_wage_yoy (lag1)', F['w_real_wage_yoy'].reindex(idx).shift(1 + h))]:
        fb = E.expanding(y, base, h); fm = E.expanding(y, pd.concat([base, x.rename('x')], axis=1), h)
        for mn in ('all', 'ex_infl', 'ex_infl_covid'):
            out.append(dict(model=nm, h=h, eval=mn, **E.evaluate(y, fb, fm, MK[mn])))
O = pd.DataFrame(out); print(O[['model', 'h', 'eval', 'n', 'rmse_ratio', 'cw_t', 'cw_p']].to_string(float_format=lambda v: f'{v:.3f}'))
O.to_csv(f'{V.OUT}/m6_oos.csv', index=False, float_format='%.4g')
