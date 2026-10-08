"""G1 placebo size / honest thresholds / episode share; family-wise for M1; DM checks for O4 (unemployment) and M5."""
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import vlib as V
warnings.filterwarnings('ignore')
pd.set_option('display.width', 220)
T, F, D = V.load()
idx = T.index
R = pd.read_csv(f'{V.OUT}/m3_lagscan_calibrated.csv')
out = []
# --- G1a: honest critical values (median placebo q95 by target), k=0 rows
for tg, g in R[R.k == 0].groupby('target'):
    out.append(dict(item='G1_q95_median_rt0', target=tg, value=g.q95.median(), p10=g.q95.quantile(.1), p90=g.q95.quantile(.9)))
# empirical size of nominal 5% HAC(4) and HAC(8) with AR(2) placebos matched to each core feature (coincident)
core = [c for c in D.index[D['core'] == True] if c in F.columns]
rng = np.random.default_rng(11)
sz = []
for tg in ['d_margin', 'og', 'd_og']:
    for f in rng.choice(core, 60, replace=False):
        x = V.X_at(F, D, 'coincident', idx=idx)[f]
        if x.notna().sum() < 40 or x.std() == 0:
            continue
        for L in (4, 8):
            pl = V.placebo_t(T, tg, x, nsim=500, L=L, F_source=F[f], seed=3)
            sz.append(dict(target=tg, feature=f, L=L, size5=pl['size5'], q95=pl['q95'], ar1=np.corrcoef(F[f].dropna()[1:], F[f].dropna()[:-1])[0, 1]))
SZ = pd.DataFrame(sz)
SZ.to_csv(f'{V.OUT}/g1_placebo_size.csv', index=False)
print(SZ.groupby(['target', 'L'])[['size5', 'q95']].median().round(3))
print('size by persistence (HAC4):')
SZ['pers'] = pd.cut(SZ.ar1, [-1, 0.5, 0.8, 0.9, 1.0])
print(SZ[SZ.L == 4].groupby('pers')[['size5', 'q95']].median().round(3))
# --- G1b: episode share: for rows with nominal |t|>2 (k=0..1), share of t^2 lost when dropping episode; coefficient ratio
sig = R[(R.k <= 1) & (R.t.abs() > 2.0)].copy()
sig['t_ratio'] = sig.t_exepi / sig.t
for tg, g in sig.groupby('target'):
    out.append(dict(item='G1_t_exepi_over_t_full_median', target=tg, value=g.t_ratio.median(),
                    share_keep_p10=float((np.sign(g.t_exepi) == np.sign(g.t)).mean() * ((g.t_exepi.abs() > 1.645).mean())),
                    n=len(g)))
# covariance share of the 10 episode quarters for the headline rows
Xc = V.X_at(F, D, 'coincident', idx=idx)
for tg, f in [('d_margin', 'packaging_eu_yoy'), ('d_margin', 'no_govbond_10y__d4'), ('og', 'w_food_cpi_xvat_yoy'),
              ('d_og', 'w_food_cpi_xvat_dyoy'), ('vol_proxy', 'w_food_rel_xvat_yoy'), ('d_margin', 'raw_mat_wloc_yoy')]:
    df = pd.concat([T[tg], Xc[f]], axis=1).dropna()
    dx, dy = df.iloc[:, 1] - df.iloc[:, 1].mean(), df.iloc[:, 0] - df.iloc[:, 0].mean()
    c = dx * dy
    m = (df.index >= V.EPI[0]) & (df.index <= V.EPI[1])
    out.append(dict(item='G1_episode_cov_share', target=tg, feature=f, value=c[m].sum() / c.sum(), n_epi=int(m.sum()), n=len(df)))
# --- M1 family-wise: rank of packaging/plastics among 200 core features at rt0 (k=0) with calibrated p
dm0 = R[(R.target == 'd_margin') & (R.k == 0)].copy()
dm0['holm'] = __import__('statsmodels.stats.multitest', fromlist=['x']).multipletests(dm0.p_cal, method='holm')[1]
dm0['by'] = V.by_adjust(dm0.p_cal)
dm0 = dm0.sort_values('p_cal')
print(dm0.head(8)[['feature', 't', 'q95', 'p_cal', 'holm', 'by', 't_exepi']].round(5).to_string())
for f in ['eu_ppi_plastic_products_idx__yoy', 'packaging_eu_yoy']:
    rr = dm0[dm0.feature == f].iloc[0]
    out.append(dict(item='M1_rt0_familywise', feature=f, value=rr.t, p_cal=rr.p_cal, holm200=rr.holm, by200=rr.by,
                    rank=int(list(dm0.feature).index(f) + 1)))
# ex-episode family: recompute calibrated p for all core features at rt0 ex-episode and see where packaging ranks
X0 = V.X_at(F, D, 'realtime', 0, idx=idx)
rows = []
for f in core:
    x = X0[f]
    if x.notna().sum() < 40 or x.std() == 0:
        continue
    pl = V.placebo_t(T, 'd_margin', x, nsim=500, sample='exepi', F_source=F[f], seed=5)
    rows.append(dict(feature=f, t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal']))
E = pd.DataFrame(rows)
E['by'] = V.by_adjust(E.p_cal)
E['holm'] = __import__('statsmodels.stats.multitest', fromlist=['x']).multipletests(E.p_cal, method='holm')[1]
E = E.sort_values('p_cal')
E.to_csv(f'{V.OUT}/m1_rt0_exepi_calibrated.csv', index=False)
print(E.head(8).round(4).to_string())
for f in ['eu_ppi_plastic_products_idx__yoy', 'packaging_eu_yoy']:
    rr = E[E.feature == f].iloc[0]
    out.append(dict(item='M1_rt0_exepi_familywise', feature=f, value=rr.t, p_cal=rr.p_cal, by200=rr.by, holm200=rr.holm,
                    rank=int(list(E.feature).index(f) + 1)))


# --- DM tests (unadjusted MSE difference, HAC) for O4 unemployment and M5 EURSEK
def dm(y, fb, fm):
    df = pd.concat([y, fb, fm], axis=1).dropna()
    d = (df.iloc[:, 0] - df.iloc[:, 1]) ** 2 - (df.iloc[:, 0] - df.iloc[:, 2]) ** 2
    pos = np.array([(p - df.index[0]).n for p in df.index])
    u = (d - d.mean()).values
    O = V._nw(u[:, None], pos, 4)[0, 0] / len(d)
    t = d.mean() / np.sqrt(O / len(d))
    adj = (df.iloc[:, 1] - df.iloc[:, 2]) ** 2
    return t, 1 - stats.norm.cdf(t), float(d.mean()), float(adj.mean())


XR2 = V.X_at(F, D, 'realtime', 2, idx=idx)
B = pd.DataFrame({'og3': T['og'].shift(3), 'og4': T['og'].shift(4)}, index=idx)
fb, fm, yy = V.oos_forecasts(T['og'], B, XR2[['w_unemp_d4']], T['w_og'].fillna(0), idx, h=2)
for en, m in [('full', None), ('exepi', pd.Series(V.sample_mask(T, 'exepi'), idx))]:
    df = pd.concat([yy, fb, fm], axis=1).dropna()
    if m is not None:
        df = df[m.reindex(df.index).values]
    t, p, dmean, adjmean = dm(df.iloc[:, 0], df.iloc[:, 1], df.iloc[:, 2])
    cw = V.cw_test(df.iloc[:, 0], df.iloc[:, 1], df.iloc[:, 2])
    out.append(dict(item='O4_unemp_h2_DM', sample=en, value=t, p_dm=p, mse_gain=dmean, cw_adj_term=adjmean, cw_t=cw[0], cw_p=cw[1],
                    n=len(df)))
# benchmark comparison for M5: AR1(+Easter) vs AR(1,4)
y = T['d_margin']
for nm, Bm, ex in [('AR1+Easter, covid in train', pd.DataFrame({'a1': y.shift(1), 'ew': T['d_easter_window_q1']}), ('1900Q1', '1900Q1')),
                   ('AR1, covid in train', pd.DataFrame({'a1': y.shift(1)}), ('1900Q1', '1900Q1')),
                   ('AR(1,4), covid excl', pd.DataFrame({'a1': y.shift(1), 'a4': y.shift(4)}), ('2020Q1', '2021Q2'))]:
    fb, fm, yy = V.oos_forecasts(y, pd.DataFrame(index=idx), Bm, None, idx, h=0, train_excl=ex,
                                 min_train=28 if ex[0] == '1900Q1' else 12)
    for en, m in [('full', None), ('exepi', pd.Series(V.sample_mask(T, 'exepi'), idx))]:
        df = pd.concat([yy, fm], axis=1).dropna()
        if m is not None:
            df = df[m.reindex(df.index).values]
        out.append(dict(item='M5_bench_rmse', feature=nm, sample=en, value=float(np.sqrt(((df.iloc[:, 0] - df.iloc[:, 1]) ** 2).mean())), n=len(df)))
O = pd.DataFrame(out)
O.to_csv(f'{V.OUT}/g1_misc_results.csv', index=False)
print(O.round(4).to_string())
