"""Small independent expanding-window OOS engine (sceptic-realtime lens)."""
import numpy as np, pandas as pd
from scipy import stats

TRAIN_EXCL = pd.period_range('2020Q1', '2021Q2', freq='Q')
INFL = pd.period_range('2021Q3', '2023Q4', freq='Q')
COVID = pd.period_range('2020Q1', '2021Q4', freq='Q')
EVAL0 = pd.Period('2010Q1', 'Q')


def hac_mean(d, lags=4):
    d = np.asarray(d, float); d = d[np.isfinite(d)]; n = len(d)
    if n < 8: return np.nan, np.nan
    u = d - d.mean(); v = u @ u / n
    for l in range(1, lags + 1):
        v += 2 * (1 - l / (lags + 1)) * (u[l:] @ u[:-l]) / n
    t = d.mean() / np.sqrt(v / n)
    return t, 1 - stats.norm.cdf(t)


def expanding(y, X, h, w=None, min_train=20, excl=TRAIN_EXCL, start=EVAL0, train_start=None):
    """y: Series; X: DataFrame of regressors already aligned to t (no constant). Returns Series of forecasts."""
    idx = y.index
    if w is None: w = pd.Series(1.0, index=idx)
    out = {}
    Xv = X.reindex(idx)
    for t in idx[idx >= start]:
        if pd.isna(y.get(t)) or Xv.loc[t].isna().any():
            continue
        tr = idx[(idx <= t - h - 1) & ~idx.isin(excl)]
        if train_start is not None: tr = tr[tr >= train_start]
        d = pd.concat([y.reindex(tr).rename('_y'), Xv.reindex(tr), w.reindex(tr).rename('_w')], axis=1).dropna()
        d = d[d['_w'] > 0]
        if len(d) < max(min_train, X.shape[1] + 6):
            continue
        keep = [c for c in X.columns if d[c].std() > 1e-10]
        A = np.column_stack([np.ones(len(d))] + [d[c].values for c in keep])
        sw = np.sqrt(d['_w'].values)
        b = np.linalg.lstsq(A * sw[:, None], d['_y'].values * sw, rcond=None)[0]
        out[t] = float(np.r_[1.0, Xv.loc[t, keep].values.astype(float)] @ b)
    return pd.Series(out, dtype=float)


def evaluate(y, fb, fm, mask=None):
    df = pd.concat([y.rename('y'), fb.rename('b'), fm.rename('m')], axis=1).dropna()
    if mask is not None:
        df = df[mask.reindex(df.index).fillna(False).astype(bool)]
    if len(df) < 10:
        return dict(n=len(df), rmse_ratio=np.nan, r2_vs_base=np.nan, cw_t=np.nan, cw_p=np.nan, dm_t=np.nan)
    eb, em = df.y - df.b, df.y - df.m
    cw = eb ** 2 - (em ** 2 - (df.b - df.m) ** 2)
    cwt, cwp = hac_mean(cw.values)
    dmt, _ = hac_mean((eb ** 2 - em ** 2).values)
    return dict(n=len(df), rmse_base=np.sqrt((eb ** 2).mean()), rmse_ratio=np.sqrt((em ** 2).mean() / (eb ** 2).mean()),
                r2_vs_base=1 - (em ** 2).sum() / (eb ** 2).sum(), cw_t=cwt, cw_p=cwp, dm_t=dmt)


def masks(idx):
    return {'all': pd.Series(True, index=idx),
            'ex_infl': pd.Series(~idx.isin(INFL), index=idx),
            'ex_infl_covid': pd.Series(~idx.isin(INFL) & ~idx.isin(COVID), index=idx),
            '2015+': pd.Series(idx >= pd.Period('2015Q1'), index=idx)}


def pdl(x, K=6, P=2, name='x'):
    """Quadratic Almon PDL regressors over lags 0..K of x."""
    L = pd.concat({k: x.shift(k) for k in range(K + 1)}, axis=1)
    out = {}
    for p in range(P + 1):
        out[f'{name}_pdl{p}'] = sum((k ** p) * L[k] for k in range(K + 1))
    return pd.DataFrame(out)
