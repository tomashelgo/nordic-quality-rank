"""Organic-growth claims O1-O6: weights, India/distribution/VAT/Easter artefacts, mechanical relations."""
import numpy as np, pandas as pd
import vr_lib as V
pd.set_option('display.width', 250)
T, F, D = V.load(); idx = T.index
CV = pd.read_csv(f'{V.OUT}/composites_weight_variants.csv', index_col=0); CV.index = pd.PeriodIndex(CV.index, freq='Q')
EX = V.ex_mask(idx, 'infl'); EXC = V.ex_mask(idx, 'infl covid')
og, dog = T['og'], T['d_og']
w_og, w_dog = T['w_og'], T['w_d_og']
es = T['easter_shift'].rename('easter')
inD = pd.Series((idx >= pd.Period('2014Q4')) & (idx <= pd.Period('2022Q2')), index=idx)
inIndia = inD | pd.Series((idx >= pd.Period('2007Q2')) & (idx <= pd.Period('2007Q4')), index=idx)
distrib = V.win(idx, '2015Q1', '2016Q4').rename('distrib')
defd = T[['def_B', 'def_C', 'def_D', 'def_E']]
rows = []
def rec(claim, test, res, var, **kw):
    rows.append(dict(claim=claim, test=test, var=var, **V.coef(res, var), **kw))

# ---------------- O1 og vs food CPI ex VAT (coincident)
for wv in ['orig', 'lag4', 'fixed']:
    x = CV[f'{wv}|w_food_cpi_xvat_yoy'].reindex(idx).rename('x')
    for s, m in [('full', None), ('ex_infl', EX), ('ex_infl_covid', EXC)]:
        rec('O1', f'w_food_cpi_xvat weights={wv} | {s}', V.ols(og, pd.concat([x, es], axis=1), w=w_og, sample=m), 'x')
x = F['w_food_cpi_xvat_yoy'].reindex(idx).rename('x')
Z0 = pd.concat([x, es], axis=1)
for lab, Z, m in [('+ def dummies', pd.concat([Z0, defd], axis=1), None),
                  ('+ def dummies | ex_infl', pd.concat([Z0, defd], axis=1), EX),
                  ('+ distrib 2015-16 dummy', pd.concat([Z0, distrib], axis=1), None),
                  ('+ distrib dummy | ex_infl', pd.concat([Z0, distrib], axis=1), EX),
                  ('ex India quarters', Z0, ~inIndia), ('ex India quarters | ex_infl', Z0, ~inIndia & EX),
                  ('ex 2015-16', Z0, distrib == 0), ('ex 2026Q2 (SE VAT cut)', Z0, pd.Series(idx != pd.Period('2026Q2'), index=idx)),
                  ('2008+ only', Z0, pd.Series(idx >= pd.Period('2008Q1'), index=idx)),
                  ('2008+ ex_infl', Z0, pd.Series(idx >= pd.Period('2008Q1'), index=idx) & EX),
                  ('quality A only', Z0, T['og_quality'] == 'A'), ('quality A only | ex_infl', Z0, (T['og_quality'] == 'A') & EX),
                  ('Q3/Q4 only (no Easter)', Z0, T['q'].isin([3, 4])), ('Q3/Q4 only | ex_infl', Z0, T['q'].isin([3, 4]) & EX)]:
    rec('O1', f'w_food_cpi_xvat {lab}', V.ols(og, Z, w=w_og, sample=m), 'x')
# real-time nowcast versions (h0): Orkla-weighted lag 1, Nordic lag 0
for f, lag in [('w_food_cpi_xvat_yoy', 1), ('nw_food_cpi_xvat_yoy', 0), ('w_food_cpi_yoy', 1)]:
    xx = F[f].reindex(idx).shift(lag).rename('x')
    for s, m in [('full', None), ('ex_infl', EX)]:
        rec('O1', f'{f} realtime h0 (lag {lag}) | {s}', V.ols(og, pd.concat([xx, es], axis=1), w=w_og, sample=m), 'x')
# India-blended CPI for D quarters
g = V.load_weights(); w_in = g['IN'].reindex(idx).fillna(0)
xin = x.where(w_in == 0, (1 - w_in) * x + w_in * F['in_cpi_food_idx__yoy'].reindex(idx))
for s, m in [('full', None), ('ex_infl', EX)]:
    rec('O1', f'food CPI incl India blended | {s}', V.ols(og, pd.concat([xin.rename('x'), es], axis=1), w=w_og, sample=m), 'x')

# price component regression 2022Q2-2026Q2
P = T['price']
pc = []
for f, lag in [('w_food_cpi_xvat_yoy', 0), ('nw_food_cpi_xvat_yoy', 0), ('w_food_cpi_yoy', 0), ('nw_food_cpi_yoy', 0),
               ('w_food_ppi_yoy', 1), ('nw_food_ppi_yoy', 1), ('w_food_cpi_xvat_yoy', 1)]:
    for wv in (['orig', 'lag4'] if f in ('w_food_cpi_xvat_yoy', 'nw_food_cpi_xvat_yoy', 'w_food_ppi_yoy') else ['orig']):
        xx = (CV[f'{wv}|{f}'] if f'{wv}|{f}' in CV else F[f]).reindex(idx).shift(lag)
        d = pd.concat([P.rename('p'), xx.rename('x')], axis=1).dropna()
        b = np.polyfit(d.x, d.p, 1); r2 = np.corrcoef(d.x, d.p)[0, 1] ** 2
        res = d.p - np.polyval(b, d.x)
        pc.append(dict(feature=f, lag=lag, weights=wv, n=len(d), slope=b[0], intercept=b[1], r2=r2,
                       resid_2026Q2=res.get(pd.Period('2026Q2')), resid_2025_mean=res[[p for p in res.index if p.year == 2025]].mean(),
                       x_2026Q2=d.x.get(pd.Period('2026Q2'))))
        if f in ('w_food_cpi_xvat_yoy', 'nw_food_cpi_xvat_yoy') and lag == 0 and wv == 'orig':
            d2 = d.drop(pd.Period('2026Q2'), errors='ignore')
            b2 = np.polyfit(d2.x, d2.p, 1)
            pc.append(dict(feature=f + ' ex 2026Q2', lag=0, weights=wv, n=len(d2), slope=b2[0], intercept=b2[1],
                           r2=np.corrcoef(d2.x, d2.p)[0, 1] ** 2))
            d3 = d.drop([p for p in d.index if p <= pd.Period('2023Q1')])
            b3 = np.polyfit(d3.x, d3.p, 1)
            pc.append(dict(feature=f + ' only quarters printed in own report (2023Q2+)', lag=0, weights=wv, n=len(d3),
                           slope=b3[0], intercept=b3[1], r2=np.corrcoef(d3.x, d3.p)[0, 1] ** 2))
pc = pd.DataFrame(pc)
print(pc.to_string(float_format=lambda v: f'{v:.3f}'))
pc.to_csv(f'{V.OUT}/o1_price_component.csv', index=False, float_format='%.4g')
print(pd.concat([P, F[['w_food_cpi_xvat_yoy', 'w_food_cpi_yoy', 'nw_food_cpi_xvat_yoy', 'nw_food_cpi_yoy', 'se_cpi_food_idx__yoy']].reindex(idx)], axis=1).loc['2024Q4':].round(2).to_string())

# ---------------- O2: selling-price expectations: d_og at h=4 and base effects
for f, lag in [('ea_ec_food_ind_sell_price_exp__d4', 0), ('w_ec_food_ind_sell_price_exp_d4', 1), ('w_ec_food_ind_sell_price_exp_lvl', 1)]:
    for h in (1, 2, 4):
        xx = F[f].reindex(idx).shift(h + lag).rename('x')
        specs = {'plain': pd.concat([xx, es, T['d_og_def_break']], axis=1),
                 '+ og_{t-5} (real-time base, screen)': pd.concat([xx, es, T['d_og_def_break'], og.shift(max(4, h + 1) if h < 4 else 5).rename('b')], axis=1),
                 '+ og_{t-4} (mechanical base)': pd.concat([xx, es, T['d_og_def_break'], og.shift(4).rename('b4')], axis=1)}
        for sl, Z in specs.items():
            for s, m in [('full', None), ('ex_infl', EX)]:
                rec('O2', f'd_og ~ {f} h={h} {sl} | {s}', V.ols(dog, Z, w=w_dog, sample=m), 'x')
        # og level with AR(og_{t-h-1}, og_{t-4 or t-5})
        Zl = pd.concat([xx, es, og.shift(h + 1).rename('a1'), og.shift(4 if h < 4 else 5).rename('a4')], axis=1)
        for s, m in [('full', None), ('ex_infl', EX)]:
            rec('O2', f'og ~ {f} h={h} + AR | {s}', V.ols(og, Zl, w=w_og, sample=m), 'x')

# ---------------- O3: real wage / confidence vs og; channel horse race
for f, lag in [('w_real_wage_yoy', 1), ('nw_real_wage_yoy', 1), ('w_cons_conf_z', 0), ('nw_cons_conf_z', 0)]:
    xx = F[f].reindex(idx).rename('x')
    for s, m in [('full', None), ('ex_infl', EX)]:
        rec('O3', f'og ~ {f} coincident | {s}', V.ols(og, pd.concat([xx, es], axis=1), w=w_og, sample=m), 'x')
        rec('O3', f'og ~ {f} coincident + food CPI xvat | {s}', V.ols(og, pd.concat([xx, es, F['w_food_cpi_xvat_yoy'].reindex(idx)], axis=1), w=w_og, sample=m), 'x')
# decomposition of the real wage: nominal wage vs headline CPI
for s, m in [('full', None), ('ex_infl', EX)]:
    r = V.ols(og, pd.concat([F['w_wage_yoy'].reindex(idx).rename('wage'), F['w_cpi_yoy'].reindex(idx).rename('cpi'), es], axis=1), w=w_og, sample=m)
    rec('O3', f'og ~ nominal wage + headline CPI | {s}', r, 'wage'); rec('O3', f'og ~ nominal wage + headline CPI | {s}', r, 'cpi')

# ---------------- O4: volume proxy and relative food inflation; mechanical decomposition
vp = og - F['w_food_cpi_xvat_yoy'].reindex(idx)
for nm, rel in [('mech def: xvat food - w_cpi(incl India)', CV['orig|w_food_rel_xvat_yoy']),
                ('consistent: xvat food - cpi ex India', CV['orig|w_food_rel_xvat_exIN_yoy']),
                ('country-consistent (xvat_c - cpi_c)', CV['orig|w_food_rel_xvat_cc_yoy']),
                ('lag4 weights, consistent', CV['lag4|w_food_rel_xvat_exIN_yoy'])]:
    xx = rel.reindex(idx).rename('x')
    for s, m in [('full', None), ('ex_infl', EX)]:
        rec('O4', f'vol_proxy ~ rel food [{nm}] | {s}', V.ols(vp, pd.concat([xx, es], axis=1), w=w_og, sample=m), 'x')
        rec('O4', f'vol_proxy ~ rel food [{nm}] + def dummies | {s}', V.ols(vp, pd.concat([xx, es, defd], axis=1), w=w_og, sample=m), 'x')
# mechanical decomposition: og = a + b1*food CPI + b2*headline CPI ; volume story implies b2 = +0.84 (= -d)
for s, m in [('full', None), ('ex_infl', EX)]:
    r = V.ols(og, pd.concat([F['w_food_cpi_xvat_yoy'].reindex(idx).rename('fcpi'), CV['orig|w_cpi_exIN_yoy'].reindex(idx).rename('hcpi'), es], axis=1), w=w_og, sample=m)
    rec('O4', f'og ~ food CPI xvat + headline CPI exIN | {s}', r, 'fcpi'); rec('O4', f'og ~ food CPI xvat + headline CPI exIN | {s}', r, 'hcpi')
    r = V.ols(vp, pd.concat([F['w_food_cpi_xvat_yoy'].reindex(idx).rename('fcpi'), es], axis=1), w=w_og, sample=m)
    rec('O4', f'vol_proxy ~ food CPI xvat only (mechanical -(1-theta)) | {s}', r, 'fcpi')
    r = V.ols(vp, pd.concat([CV['orig|w_food_rel_xvat_exIN_yoy'].reindex(idx).rename('x'), F['w_food_cpi_xvat_yoy'].reindex(idx).rename('fcpi'), es], axis=1), w=w_og, sample=m)
    rec('O4', f'vol_proxy ~ rel food (exIN) + food CPI xvat | {s}', r, 'x')
# 2022-26 reported volume/mix (no mechanical link)
vm = T['volume_mix']
for nm, rel in [('consistent exIN', CV['orig|w_food_rel_xvat_exIN_yoy']), ('mech def', CV['orig|w_food_rel_xvat_yoy'])]:
    d = pd.concat([vm.rename('v'), rel.reindex(idx).rename('x')], axis=1).dropna()
    rows.append(dict(claim='O4', test=f'reported volume_mix 2022Q2-26Q2 ~ rel food [{nm}] (OLS)', var='x', b=np.polyfit(d.x, d.v, 1)[0],
                     t=np.nan, p=np.nan, n=len(d), corr=np.corrcoef(d.x, d.v)[0, 1]))
# income / GDP coincident vs real-time with national-accounts lag
for f in ['w_hh_real_inc_yoy', 'w_gdp_vol_yoy']:
    for lab, xx in [('coincident', F[f].reindex(idx)), ('rt h0 (lag1)', F[f].reindex(idx).shift(1)), ('rt h1', F[f].reindex(idx).shift(2))]:
        for s, m in [('full', None), ('ex_infl', EX)]:
            rec('O4', f'vol_proxy ~ {f} {lab} | {s}', V.ols(vp, pd.concat([xx.rename('x'), es], axis=1), w=w_og, sample=m), 'x')

# ---------------- O5 base-effect identity
o = pd.concat([dog.rename('d'), og.rename('o'), og.shift(4).rename('o4'), T['d_og_def_break'].rename('brk')], axis=1).dropna()
rho4 = np.corrcoef(o.o, o.o4)[0, 1]
c = np.corrcoef(o.d, o.o4)[0, 1]
sd_ratio = o.o.std() / o.o4.std()
implied = (rho4 * sd_ratio - 1) / np.sqrt(sd_ratio ** 2 + 1 - 2 * rho4 * sd_ratio)
nb = o[o.brk == 0]
rows.append(dict(claim='O5', test='corr(d_og, og_{t-4}) actual / implied from rho4 only', var='-', b=c, t=implied, p=rho4, n=len(o)))
rows.append(dict(claim='O5', test='same, excl def-break quarters; p column = rho4', var='-', b=np.corrcoef(nb.d, nb.o4)[0, 1],
                 t=np.nan, p=np.corrcoef(nb.o, nb.o4)[0, 1], n=len(nb)))
# d_og vs food CPI acceleration (dyoy) coincident, with base control
for f in ['w_food_cpi_xvat_dyoy', 'w_food_ppi_dyoy', 'nw_food_cpi_xvat_dyoy']:
    xx = F[f].reindex(idx).rename('x')
    for sl, Z in [('plain', pd.concat([xx, es, T['d_og_def_break']], axis=1)),
                  ('+ og_{t-4}', pd.concat([xx, es, T['d_og_def_break'], og.shift(4).rename('b4')], axis=1))]:
        for s, m in [('full', None), ('ex_infl', EX)]:
            rec('O5', f'd_og ~ {f} coincident {sl} | {s}', V.ols(dog, Z, w=w_dog, sample=m), 'x')
    # mechanical part: dyoy = yoy_t - yoy_{t-4}; og_t - og_{t-4} on yoy_t and yoy_{t-4} separately
    Z = pd.concat([F[f.replace('dyoy', 'yoy')].reindex(idx).rename('x0'), F[f.replace('dyoy', 'yoy')].reindex(idx).shift(4).rename('x4'), es, T['d_og_def_break']], axis=1)
    for s, m in [('full', None), ('ex_infl', EX)]:
        r = V.ols(dog, Z, w=w_dog, sample=m)
        rec('O5', f'd_og ~ yoy_t + yoy_t-4 [{f}] | {s}', r, 'x0'); rec('O5', f'd_og ~ yoy_t + yoy_t-4 [{f}] | {s}', r, 'x4')

# ---------------- O6 policy-rate changes lead og
for wv in ['orig', 'lag4']:
    pr = CV[f'{wv}|w_policy_rate_d4'].reindex(idx)
    for k in (0, 2, 3, 4):
        xx = pr.shift(k).rename('x')
        for sl, Z in [('plain', pd.concat([xx, es], axis=1)),
                      ('+ AR og_{t-k-1}, og_{t-4}', pd.concat([xx, es, og.shift(max(k + 1, 1)).rename('a1'), og.shift(4 if k < 4 else 5).rename('a4')], axis=1)),
                      ('+ food CPI xvat_{t-k} (lag-matched)', pd.concat([xx, es, F['w_food_cpi_xvat_yoy'].reindex(idx).shift(k).rename('c')], axis=1)),
                      ('+ food CPI xvat_t (coincident)', pd.concat([xx, es, F['w_food_cpi_xvat_yoy'].reindex(idx).rename('c')], axis=1))]:
            for s, m in [('full', None), ('ex_infl', EX), ('ex_infl_covid', EXC)]:
                rec('O6', f'og ~ w_policy_rate_d4 weights={wv} k={k} {sl} | {s}', V.ols(og, Z, w=w_og, sample=m), 'x')

R = pd.DataFrame(rows)
print(R.to_string(float_format=lambda v: f'{v:.3f}'))
R.to_csv(f'{V.OUT}/organic_tests.csv', index=False, float_format='%.4g')
