"""M3: lag-scan search correction (placebo-calibrated p, BY/Holm/Bonferroni over 7 lags x 200 features x 6 targets),
single-cycle diagnostics, and an out-of-sample test of long-lag (5-7 quarter) cost inflation vs the AR benchmark."""
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import vlib as V

warnings.filterwarnings('ignore')
T, F, D = V.load()
idx = T.index
core = [c for c in D.index[D['core'] == True] if c in F.columns]
XA = {k: V.X_at(F, D, 'realtime', k, idx=idx) for k in range(7)}

# ------------------------------------------------------------------ 1. lag scan with placebo calibration
rows = []
phis = {f: V.ar_fit(F[f], 2) for f in core if F[f].notna().sum() > 30}
TG = ['d_margin', 'og', 'd_og', 'vol_proxy']
for tg in TG:
    for f in core:
        if f not in phis:
            continue
        for k in range(7):
            x = XA[k][f]
            y, X, w = V.design(T, tg, x)
            ok = pd.concat([y, X], axis=1).dropna()
            if len(ok) < 30 or ok['x'].std() == 0:
                continue
            pl = V.placebo_t(T, tg, x, nsim=1000, phi=phis[f], seed=k)
            r_ex = V.fit_one(T, tg, x, sample='exepi')
            rows.append(dict(target=tg, feature=f, k=k, n=pl['n'], b=pl['b'], t=pl['t_obs'], q95=pl['q95'],
                             p_nom=2 * (1 - stats.t.cdf(abs(pl['t_obs']), pl['n'] - 2)), p_cal=pl['p_cal'],
                             p_emp=pl['p_emp'], t_exepi=r_ex['t']['x']))
    print('done', tg, flush=True)
R = pd.DataFrame(rows)
# multiple testing: within target (1,400), and over the full 6-target family (8,400: pad 2 missing targets with p=1)
for fam, grp in [('tgt', ['target'])]:
    R['by_cal_tgt'] = R.groupby('target')['p_cal'].transform(lambda p: V.by_adjust(p))
    R['by_nom_tgt'] = R.groupby('target')['p_nom'].transform(lambda p: V.by_adjust(p))
m_all = 200 * 7 * 6
pc = R['p_cal'].values
pad = np.r_[pc, np.ones(m_all - len(pc))]
R['by_cal_all8400'] = V.by_adjust(pad)[:len(pc)]
R['bonf_cal_all8400'] = np.minimum(1, R['p_cal'] * m_all)
pn = np.r_[R['p_nom'].values, np.ones(m_all - len(pc))]
R['by_nom_all8400'] = V.by_adjust(pn)[:len(pc)]
R.to_csv(f'{V.OUT}/m3_lagscan_calibrated.csv', index=False)
dm = R[R.target == 'd_margin']
print(dm.sort_values('t', ascending=False).head(15).round(4).to_string())
print('d_margin positive-sign, k>=4 rows passing BY(cal, 8400)<0.10:',
      ((dm.k >= 4) & (dm.t > 0) & (dm.by_cal_all8400 < 0.10)).sum(), ' within-target BY(cal)<0.10:',
      ((dm.k >= 4) & (dm.t > 0) & (dm.by_cal_tgt < 0.10)).sum())

# ------------------------------------------------------------------ 2. single-cycle diagnostics for the headline rows
diag = []
heads = [('eu_ppi_dom_c105_idx__yoy', 6), ('se_ppi_food_hmpi_idx__yoy', 6), ('eu_ppi_dom_c107_idx__yoy', 5),
         ('se_cpi_idx__yoy', 6), ('w_food_ppi_yoy', 6), ('packaging_eu_yoy', 6)]
for f, k in heads:
    x = XA[k][f]
    for s in ['full', 'exepi', 'exepi+execho', 'ex0709', 'exepi+execho+ex0709', 'pre2020', 'post2008',
              'post2008+exepi+execho', 'excovid', 'exbreak']:
        for L in (4, 8):
            r = V.fit_one(T, 'd_margin', x, L=L, sample=s)
            diag.append(dict(feature=f, k=k, sample=s, L=L, b=r['b']['x'], t=r['t']['x'], n=r['n']))
    # control for own y_{t-4} (base) and for short-lag cost (k=0..1)
    r = V.fit_one(T, 'd_margin', pd.concat([x.rename('x'), T['d_margin'].shift(max(4, k + 1)).rename('ylag')], axis=1))
    diag.append(dict(feature=f, k=k, sample='full+ownlag', L=4, b=r['b']['x'], t=r['t']['x'], n=r['n']))
    r = V.fit_one(T, 'd_margin', pd.concat([x.rename('x'), T['margin'].shift(4).rename('mlev4'),
                                            T['margin'].shift(max(5, k + 1)).rename('mlev')], axis=1))
    diag.append(dict(feature=f, k=k, sample='full+marginlevel_lags', L=4, b=r['b']['x'], t=r['t']['x'], n=r['n']))
    pl = V.placebo_t(T, 'd_margin', x, nsim=2000, sample='exepi+execho', phi=phis[f])
    diag.append(dict(feature=f, k=k, sample='exepi+execho|placebo', L=4, t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal']))
    y, X, w = V.design(T, 'd_margin', x, sample='full')
    bb = V.mbb_coef(y, X, w, nboot=2000, block=8)
    diag.append(dict(feature=f, k=k, sample='full|mbb8', L=0, b=bb['b'], t=bb['t_boot'], p_boot=bb['p_boot']))
    y, X, w = V.design(T, 'd_margin', x, sample='exepi+execho')
    bb = V.mbb_coef(y, X, w, nboot=2000, block=8)
    diag.append(dict(feature=f, k=k, sample='exepi+execho|mbb8', L=0, b=bb['b'], t=bb['t_boot'], p_boot=bb['p_boot']))
DG = pd.DataFrame(diag)
DG.to_csv(f'{V.OUT}/m3_single_cycle.csv', index=False)
print(DG.round(3).to_string())

# contribution of quarters to the covariance (full sample) for the headline row
x = XA[6]['eu_ppi_dom_c105_idx__yoy']
df = pd.concat([T['d_margin'], x], axis=1).dropna()
dx, dy = df.iloc[:, 1] - df.iloc[:, 1].mean(), df.iloc[:, 0] - df.iloc[:, 0].mean()
contrib = (dx * dy) / (dx * dy).sum()
print('top contributing quarters to cov(d_margin, c105 lag k=6):')
print(contrib.sort_values(ascending=False).head(12).round(3).to_string())
for a, b in [('2008Q1', '2009Q4'), ('2021Q3', '2023Q4'), ('2022Q4', '2025Q3'), ('2011Q1', '2013Q4')]:
    print(a, b, 'share', round(contrib[(contrib.index >= pd.Period(a)) & (contrib.index <= pd.Period(b))].sum(), 3))

# ------------------------------------------------------------------ 3. out-of-sample: long-lag cost inflation vs AR
Fc = V.X_at(F, D, 'coincident', idx=idx)
cands = ['eu_ppi_dom_c105_idx__yoy', 'se_ppi_food_hmpi_idx__yoy', 'eu_ppi_dom_c107_idx__yoy', 'se_cpi_idx__yoy',
         'w_food_ppi_yoy', 'nw_food_ppi_yoy', 'raw_mat_wloc_yoy', 'cost_idx_calib_yoy', 'packaging_eu_yoy',
         'w_food_cpi_xvat_yoy']
y = T['d_margin']
oos = []
evalmasks = {'full2010': None,
             'exepi': pd.Series(V.sample_mask(T, 'exepi'), idx),
             'exepi+echo': pd.Series(V.sample_mask(T, 'exepi+execho'), idx),
             '2015+': pd.Series(np.asarray(idx >= pd.Period('2015Q1')), idx)}


def ar_base(h):
    lags = [h + 1] + ([4] if h + 1 < 4 else [])
    return pd.DataFrame({f'ar{l}': y.shift(l) for l in lags}, index=idx)


for h in (0, 1, 2, 4):
    B = ar_base(h)
    for f in cands:
        q = int(D.loc[f, 'realtime_min_lag_q'])
        ks = [k for k in (5, 6, 7) if k >= h + q]
        xl = pd.concat([Fc[f].shift(k) for k in ks], axis=1).mean(axis=1).rename('x57')
        fb, fm, yy = V.oos_forecasts(y, B, xl.to_frame(), None, idx, h=h)
        for en, em in evalmasks.items():
            s = V.oos_summary(yy, fb, fm, em)
            oos.append(dict(model=f'AR+{f}[lag5-7]', h=h, eval=en, **s))
        # full profile: short-lag (most recent available) + long-lag
        k0 = h + q
        xs = Fc[f].shift(k0).rename('xs')
        fb2, fm2, yy2 = V.oos_forecasts(y, B, pd.concat([xs, xl], axis=1), None, idx, h=h)
        for en, em in evalmasks.items():
            s = V.oos_summary(yy2, fb2, fm2, em)
            oos.append(dict(model=f'AR+{f}[short+lag5-7]', h=h, eval=en, **s))
    # Real-time selection: at each origin choose the feature x lag (5..7) among all core features with the
    # largest positive in-sample t on the training window (mimics the lag scan), then forecast.
    yv = y.values
    pos = [i for i, p in enumerate(idx) if p >= pd.Period('2010Q1') and np.isfinite(yv[i])]
    excl = V.mask_period(idx, '2020Q1', '2021Q2')
    Bv = B.values
    cand_series = {}
    for f in core:
        q = int(D.loc[f, 'realtime_min_lag_q'])
        for k in (5, 6, 7):
            if k >= h + q:
                cand_series[(f, k)] = Fc[f].shift(k).values
    fsel, fbase, chosen = [], [], []
    for i in pos:
        tr = np.isfinite(yv) & np.isfinite(Bv).all(1) & ~excl
        tr[i - h:] = False
        # benchmark
        A0 = np.column_stack([np.ones(len(yv)), Bv])
        bb = np.linalg.lstsq(A0[tr], yv[tr], rcond=None)[0]
        fbase.append(A0[i] @ bb)
        best, bt = None, -np.inf
        for key, xv in cand_series.items():
            m = tr & np.isfinite(xv)
            if m.sum() < 24 or not np.isfinite(xv[i]):
                continue
            xm = xv[m] - xv[m].mean()
            ym = yv[m] - yv[m].mean()
            sxx = (xm ** 2).sum()
            if sxx <= 0:
                continue
            bcoef = (xm * ym).sum() / sxx
            e = ym - bcoef * xm
            tt = bcoef / np.sqrt((e ** 2).sum() / (m.sum() - 2) / sxx)
            if tt > bt:
                bt, best = tt, key
        xv = cand_series[best]
        A1 = np.column_stack([A0, xv])
        m = tr & np.isfinite(xv)
        bb = np.linalg.lstsq(A1[m], yv[m], rcond=None)[0]
        fsel.append(A1[i] @ bb)
        chosen.append(f'{best[0]}|k{best[1]}')
    ix = idx[pos]
    fb, fm, yy = pd.Series(fbase, ix), pd.Series(fsel, ix), pd.Series(yv[pos], ix)
    for en, em in evalmasks.items():
        s = V.oos_summary(yy, fb, fm, em)
        oos.append(dict(model='AR+realtime_selected_best_lag5-7', h=h, eval=en, **s))
    print('h', h, 'chosen features (counts):', pd.Series(chosen).value_counts().head(6).to_dict())
O = pd.DataFrame(oos)
O.to_csv(f'{V.OUT}/m3_oos_longlag.csv', index=False)
pd.set_option('display.width', 250)
print(O[O['eval'].isin(['full2010', 'exepi', 'exepi+echo'])].pivot_table(index=['model', 'h'], columns='eval',
                                                                     values=['ratio', 'cw_p']).round(3).to_string())
