"""Data-snooping reality check for the univariate ARDL horse race.

Under the null that no macro feature carries information, how many of ~200 univariate models would
beat the base out of sample, how good would the best one look, and how many would have CW p < 0.05?
The REAL feature panel is kept (so the strong cross-correlation between features is preserved) and the
TARGET is replaced by a bootstrap series generated under the null: an AR(4) fitted to the target
(og for d_og, since d_og = og - og_{t-4}), driven by moving-block-bootstrapped residuals (block 4),
with the actual missing-data pattern. Every univariate ARDL(p=1) model is then run through exactly the
same expanding-window engine on the primary base. Repeated NREP times per target x horizon.

Output: null_check.csv (actual vs null distribution), null_check_draws.csv
"""
import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import numpy as np
import pandas as pd
from scipy import stats
from joblib import Parallel, delayed

import oos_lib as L

NREP = 40


def fast_cw_p(y, fb, fm, lags=4):
    d = (y - fb) ** 2 - ((y - fm) ** 2 - (fb - fm) ** 2)
    n = len(d)
    u = d - d.mean()
    v = u @ u / n
    for l in range(1, lags + 1):
        v += 2 * (1 - l / (lags + 1)) * (u[l:] @ u[:-l]) / n
    t = d.mean() / np.sqrt(v / n) if v > 0 else np.nan
    return 1 - stats.norm.cdf(t)


def simulate_target(T, tgt, rng):
    """Null DGP: AR(4) on the target (og for d_og) with moving-block-bootstrap residuals."""
    src = 'og' if tgt == 'd_og' else tgt
    s = T[src].astype(float)
    Z = pd.concat([s.shift(k) for k in range(1, 5)], axis=1)
    ok = s.notna() & Z.notna().all(axis=1) & ~T.index.isin(L.TRAIN_EXCL)
    A = np.column_stack([np.ones(ok.sum()), Z[ok].values])
    beta = np.linalg.lstsq(A, s[ok].values, rcond=None)[0]
    e = s[ok].values - A @ beta
    first = np.where(s.notna().values)[0][0]
    sim = s.values.copy()
    n = len(sim)
    nb = int(np.ceil(n / 4)) + 1
    starts = rng.integers(0, len(e) - 4, nb)
    eb = np.concatenate([e[st:st + 4] for st in starts])
    for t in range(first + 4, n):
        sim[t] = beta[0] + beta[1:] @ sim[t - 1:t - 5:-1] + eb[t]
    sim = pd.Series(sim, index=T.index)
    T2 = T.copy()
    if tgt == 'd_og':
        T2['og'] = sim.where(T['og'].notna())
        T2['d_og'] = (sim - sim.shift(4)).where(T['d_og'].notna())
    else:
        T2[tgt] = sim.where(T[tgt].notna())
    return T2


def stats_for(T, tgt, h, Xh):
    idx = T.index
    pos = [i for i, p in enumerate(idx) if L.EVAL_START <= p <= L.LAST]
    y = T[tgt].values.astype(float)
    w = L.target_weights(T, tgt).values
    ok = L.train_ok_mask(idx)
    B = L.base_frame(T, tgt, h, L.PRIMARY[tgt])
    base = L.ExpandingWLS(y, B.values, w, ok).forecasts(pos, h, L.MIN_TRAIN_UNI)
    yy = y[pos]
    ratios, ps = [], []
    for j, f in enumerate(Xh.columns):
        x = Xh[f].values
        Z = np.column_stack([B.values, x])
        fc = L.ExpandingWLS(y, Z, w, ok).forecasts(pos, h, L.MIN_TRAIN_UNI)
        m = np.isfinite(fc) & np.isfinite(base) & np.isfinite(yy)
        if m.sum() < 0.9 * len(pos):
            continue
        ratios.append(np.sqrt(np.mean((yy[m] - fc[m]) ** 2) / np.mean((yy[m] - base[m]) ** 2)))
        ps.append(fast_cw_p(yy[m], base[m], fc[m]))
    ratios, ps = np.array(ratios), np.array(ps)
    return {'n_models': len(ratios), 'share_beat_base': np.mean(ratios < 1), 'best_ratio': ratios.min(),
            'n_cw_p05': int(np.sum(ps < 0.05)), 'n_cw_p01': int(np.sum(ps < 0.01)),
            'median_ratio': np.median(ratios)}


def run(tgt, h, T, Xh, seed):
    rng = np.random.default_rng(seed)
    act = stats_for(T, tgt, h, Xh)
    draws = [stats_for(simulate_target(T, tgt, rng), tgt, h, Xh) for _ in range(NREP)]
    return tgt, h, act, draws


if __name__ == '__main__':
    T, F, D, X = L.load_all()
    jobs = []
    for k, tgt in enumerate(L.TARGETS):
        for h in L.HS:
            jobs.append((tgt, h, X[h], 1000 + 10 * k + h))
    res = Parallel(n_jobs=2)(delayed(run)(tgt, h, T, Xh, sd) for tgt, h, Xh, sd in jobs)
    rows, drows = [], []
    for tgt, h, act, draws in res:
        Dd = pd.DataFrame(draws)
        Dd['target'], Dd['h'] = tgt, h
        drows.append(Dd)
        r = {'target': tgt, 'h': h, 'variant': L.PRIMARY[tgt], 'n_models': act['n_models'], 'nrep': NREP}
        for k in ['share_beat_base', 'best_ratio', 'n_cw_p05', 'n_cw_p01', 'median_ratio']:
            r[f'actual_{k}'] = act[k]
            r[f'null_mean_{k}'] = Dd[k].mean()
            r[f'null_p05_{k}'] = Dd[k].quantile(0.05)
            r[f'null_p95_{k}'] = Dd[k].quantile(0.95)
            # share of null draws at least as favourable to 'predictability' as the actual result
            better = (Dd[k] <= act[k]) if k in ('best_ratio', 'median_ratio') else (Dd[k] >= act[k])
            r[f'null_pval_{k}'] = better.mean()
        rows.append(r)
    pd.DataFrame(rows).to_csv(f'{L.OUT}/null_check.csv', index=False, float_format='%.4g')
    pd.concat(drows).to_csv(f'{L.OUT}/null_check_draws.csv', index=False, float_format='%.4g')
    print(pd.DataFrame(rows)[['target', 'h', 'actual_share_beat_base', 'null_mean_share_beat_base',
                              'null_p95_share_beat_base', 'actual_best_ratio', 'null_p05_best_ratio',
                              'actual_n_cw_p05', 'null_mean_n_cw_p05', 'null_p95_n_cw_p05',
                              'null_pval_n_cw_p05']].round(3).to_string())
