"""Margin claims M1-M6: timing, weights, definition/M&A artefacts, base effects."""
import numpy as np, pandas as pd
import vr_lib as V
pd.set_option('display.width', 250)

T, F, D = V.load()
idx = T.index
CV = pd.read_csv(f'{V.OUT}/composites_weight_variants.csv', index_col=0)
CV.index = pd.PeriodIndex(CV.index, freq='Q')
y = T['d_margin']
EX = V.ex_mask(idx, 'infl'); EXC = V.ex_mask(idx, 'infl covid')
ev = pd.DataFrame({
    'ev_bakers': V.win(idx, '2012Q1', '2012Q4'), 'ev_rieber': V.win(idx, '2013Q2', '2014Q1'),
    'ev_hame': V.win(idx, '2016Q2', '2017Q1'), 'ev_eastern': V.win(idx, '2021Q2', '2022Q1'),
    'ev_2007': V.win(idx, '2007Q2', '2007Q4'), 'ev_ifrs16': T['ifrs16'], 'covid': T['covid'],
    'ev_sladco': V.win(idx, '2005Q1', '2005Q4'), 'ev_krup': V.win(idx, '2006Q3', '2007Q2')})
exIndia = pd.Series(~((idx >= pd.Period('2014Q4')) & (idx <= pd.Period('2022Q2')) |
                      ((idx >= pd.Period('2007Q2')) & (idx <= pd.Period('2007Q4')))), index=idx)
rows = []

def rec(claim, test, res, var, **kw):
    c = V.coef(res, var); rows.append(dict(claim=claim, test=test, var=var, **c, **kw))

# ---------------- M1 packaging
for f in ['packaging_eu_yoy', 'eu_ppi_plastic_products_idx__yoy']:
    x = F[f].reindex(idx)
    for lab, xx in [('coincident', x), ('realtime h0 (lag1: t-1)', x.shift(1)), ('realtime h1 (t-2)', x.shift(2))]:
        for s, m in [('full', None), ('ex_infl', EX), ('ex_infl_covid', EXC)]:
            rec('M1', f'{lab} | {s}', V.ols(y, xx.rename(f), sample=m), f)
    rec('M1', 'coincident + M&A/event dummies | full', V.ols(y, pd.concat([x.rename(f), ev], axis=1)), f)
    rec('M1', 'coincident + M&A/event dummies | ex_infl', V.ols(y, pd.concat([x.rename(f), ev], axis=1), sample=EX), f)
    rec('M1', 'coincident | ex India quarters', V.ols(y, x.rename(f), sample=exIndia), f)
    rec('M1', 'coincident | 2008+ ex_infl', V.ols(y, x.rename(f), sample=EX & pd.Series(idx >= pd.Period('2008Q1'), index=idx)), f)
    rec('M1', 'coincident | pre-2021Q3 only', V.ols(y, x.rename(f), sample=pd.Series(idx <= pd.Period('2021Q2'), index=idx)), f)

# ---------------- M1 raw materials: avg lags 0-3 with weight variants (FX part of local-currency conversion)
for wv in ['orig', 'lag4', 'fixed']:
    rm = CV[f'{wv}|raw_mat_wloc_yoy'].reindex(idx)
    for lab, xx in [('avg L0-3', rm.rolling(4).mean()), ('L2', rm.shift(2))]:
        for s, m in [('full', None), ('ex_infl', EX)]:
            rec('M1', f'raw_mat_wloc {lab} weights={wv} | {s}', V.ols(y, xx.rename('rm'), sample=m), 'rm')
        rec('M1', f'raw_mat_wloc {lab} weights={wv} + events | full', V.ols(y, pd.concat([xx.rename('rm'), ev], axis=1)), 'rm')
        rec('M1', f'raw_mat_wloc {lab} weights={wv} + events | ex_infl', V.ols(y, pd.concat([xx.rename('rm'), ev], axis=1), sample=EX), 'rm')

# DL 0-6 cumulative response of d_margin to a one-off +10pp yoy (unrestricted, HAC) for raw materials
def dl(xs, K, extra=None, sample=None):
    Z = pd.concat({f'L{k}': xs.shift(k) for k in range(K + 1)}, axis=1)
    if extra is not None: Z = pd.concat([Z, extra], axis=1)
    return V.ols(y, Z, sample=sample)
dl_rows = []
for wv in ['orig', 'lag4']:
    rm = CV[f'{wv}|raw_mat_wloc_yoy'].reindex(idx)
    for evs in [None, ev]:
        for s, m in [('full', None), ('ex_infl', EX)]:
            r = dl(rm, 6, evs, m)
            b = r.params[[f'L{k}' for k in range(7)]]
            dl_rows.append(dict(weights=wv, events=evs is not None, sample=s, n=int(r.nobs),
                                **{f'b10_L{k}': 10 * b.iloc[k] for k in range(7)},
                                min10=10 * b.min(), argmin=int(np.argmin(b.values))))
dl_rows = pd.DataFrame(dl_rows)
print(dl_rows.to_string(float_format=lambda v: f'{v:.3f}'))
dl_rows.to_csv(f'{V.OUT}/m1_rawmat_dl.csv', index=False, float_format='%.4g')

# ---------------- M2 asymmetry: positive/negative parts DL 0-6 (cumulative sums)
asym = []
for wv in ['orig', 'lag4']:
    rm = CV[f'{wv}|raw_mat_wloc_yoy'].reindex(idx)
    pos, neg = rm.clip(lower=0), rm.clip(upper=0)
    for evs_lab, evs in [('none', None), ('events', ev), ('bakers_only', ev[['ev_bakers']]), ('covid+2007', ev[['covid', 'ev_2007']])]:
        for s, m in [('full', None), ('ex_infl', EX), ('ex_infl_covid', EXC)]:
            Z = pd.concat({**{f'P{k}': pos.shift(k) for k in range(7)}, **{f'N{k}': neg.shift(k) for k in range(7)}}, axis=1)
            if evs is not None: Z = pd.concat([Z, evs], axis=1)
            r = V.ols(y, Z, sample=m)
            cp = np.cumsum([r.params[f'P{k}'] for k in range(7)]) * 10
            cn = np.cumsum([r.params[f'N{k}'] for k in range(7)]) * -10
            # Note: d_margin is a y/y change, coefficients are on yoy inflation; we report cumulative sums of DL
            # coefficients (the claim's convention: +10pp -> sum of lag coefficients).
            asym.append(dict(weights=wv, events=evs_lab, sample=s, n=int(r.nobs),
                             pos10_L1=cp[1], pos10_L2=cp[2], pos10_L6=cp[6],
                             neg10_L2=cn[2], neg10_L3=cn[3], neg10_L6=cn[6]))
asym = pd.DataFrame(asym)
print(asym.to_string(float_format=lambda v: f'{v:.3f}'))
asym.to_csv(f'{V.OUT}/m2_asymmetry.csv', index=False, float_format='%.4g')

# ---------------- M3 lag 5-7 positive coefficients: base-effect controls
m3 = []
for f, k in [('eu_ppi_dom_c105_idx__yoy', 6), ('se_ppi_food_hmpi_idx__yoy', 6), ('eu_ppi_dom_c107_idx__yoy', 5),
             ('se_cpi_idx__yoy', 6), ('packaging_eu_yoy', 6), ('eu_agri_basket_yoy', 6)]:
    x = F[f].reindex(idx).shift(k).rename('x')
    specs = {
        'plain': None,
        'own d_margin_{t-k-1} (screen spec)': y.shift(max(4, k + 1)).rename('ylag'),
        'base d_margin_{t-4}': y.shift(4).rename('b4'),
        'base d_margin_{t-4..t-6}': pd.concat([y.shift(4).rename('b4'), y.shift(5).rename('b5'), y.shift(6).rename('b6')], axis=1),
        'base d_margin_{t-4} + x_{t-2}': pd.concat([y.shift(4).rename('b4'), F[f].reindex(idx).shift(2).rename('x2')], axis=1),
        'margin level_{t-4} dev from 8q mean': (T['margin'].shift(4) - T['margin'].shift(5).rolling(8).mean()).rename('mdev'),
        'events': ev,
    }
    for sl, ctrl in specs.items():
        Z = x if ctrl is None else pd.concat([x, ctrl], axis=1)
        for s, m in [('full', None), ('ex_infl', EX)]:
            r = V.ols(y, Z, sample=m); c = V.coef(r, 'x')
            m3.append(dict(feature=f, k=k, spec=sl, sample=s, **c))
    # two-year change m_t - m_{t-8} = d_margin_t + d_margin_{t-4} (same-report chain)
    y2 = (y + y.shift(4)).rename('d8')
    for s, m in [('full', None), ('ex_infl', EX)]:
        r = V.ols(y2, x, sample=m, hac=8); c = V.coef(r, 'x')
        m3.append(dict(feature=f, k=k, spec='target = 2-year margin change (d_m_t + d_m_{t-4}), HAC8', sample=s, **c))
m3 = pd.DataFrame(m3)
print(m3.to_string(float_format=lambda v: f'{v:.3f}'))
m3.to_csv(f'{V.OUT}/m3_base_effect.csv', index=False, float_format='%.4g')

# ---------------- M4 10y yield changes
for f in ['no_govbond_10y__d4']:
    x = F[f].reindex(idx).rename('x')
    for s, m in [('full', None), ('ex_infl', EX), ('ex_infl_covid', EXC)]:
        rec('M4', f'{f} coincident | {s}', V.ols(y, x, sample=m), 'x')
    rec('M4', f'{f} coincident + packaging | full', V.ols(y, pd.concat([x, F['packaging_eu_yoy'].reindex(idx)], axis=1)), 'x')
    rec('M4', f'{f} coincident + packaging | ex_infl', V.ols(y, pd.concat([x, F['packaging_eu_yoy'].reindex(idx)], axis=1), sample=EX), 'x')
for wv in ['orig', 'lag4', 'fixed']:
    x = CV[f'{wv}|w_gov10y_d4'].reindex(idx).rename('x')
    for s, m in [('full', None), ('ex_infl', EX)]:
        rec('M4', f'w_gov10y_d4 weights={wv} coincident | {s}', V.ols(y, x, sample=m), 'x')

# ---------------- M5 SEK
x = F['se_eursek__yoy'].reindex(idx).rename('x')
for lab, xx in [('L0', x), ('avg L0-1', x.rolling(2).mean().rename('x'))]:
    for s, m in [('full', None), ('ex_infl', EX), ('ex_infl_covid', EXC)]:
        rec('M5', f'eursek {lab} | {s}', V.ols(y, xx, sample=m), 'x')
    rec('M5', f'eursek {lab} + events | full', V.ols(y, pd.concat([xx, ev], axis=1)), 'x')
    rec('M5', f'eursek {lab} + FAO USD L0-3 | full', V.ols(y, pd.concat([xx, F['glob_fao_ffpi__yoy'].reindex(idx).rolling(4).mean().rename('fao')], axis=1)), 'x')

# ---------------- M6 nulls (real-time h0 with panel lags)
for f in ['w_real_wage_yoy', 'nw_real_wage_yoy', 'w_cons_conf_z', 'w_policy_rate_lvl', 'elec_nordic_loc_yoy',
          'natgas_eu_eur_yoy', 'brent_nok_yoy', 'w_wage_yoy']:
    lag = int(D.loc[f, 'realtime_min_lag_q'])
    for lab, xx in [('coincident', F[f].reindex(idx)), ('rt h0', F[f].reindex(idx).shift(lag)), ('rt h1', F[f].reindex(idx).shift(1 + lag))]:
        for s, m in [('full', None), ('ex_infl', EX)]:
            rec('M6', f'{f} {lab} | {s}', V.ols(y, xx.rename('x'), sample=m), 'x')

R = pd.DataFrame(rows)
print(R.to_string(float_format=lambda v: f'{v:.3f}'))
R.to_csv(f'{V.OUT}/margin_tests.csv', index=False, float_format='%.4g')
