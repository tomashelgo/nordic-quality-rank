"""Helpers for the robustness / stability lens (label: lens-robust).

Uses the shared module common.py for data loading and real-time alignment; this file only
adds (i) target-specific control sets, (ii) a fast numpy Newey-West OLS/WLS that reproduces
statsmodels' HAC (checked in 00_check_hac.py) so that thousands of regressions in the battery
run quickly, and (iii) multiple-testing helpers.
"""
import sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, '/home/user/nordic-quality-rank/research/orkla_foods/analysis')
import common as C  # noqa: E402

OUT = '/home/user/nordic-quality-rank/research/orkla_foods/analysis/robust'
HAC_LAGS = 4
TARGETS = ['d_margin', 'og', 'd_og', 'vol_proxy']

# Era boundaries follow the segment definition actually reported (def_id), see methodology.
ERAS = {
    'A_2001_07': ('2001Q1', '2007Q4'),
    'BC_2008_14': ('2008Q1', '2014Q3'),
    'D_2014Q4_22Q2': ('2014Q4', '2022Q2'),
    'E_2022Q3_26': ('2022Q3', '2026Q2'),
}
INFL = ('2021Q3', '2023Q4')
COVID = ('2020Q1', '2021Q4')
DEF_BREAKS = ['2008Q1', '2013Q1', '2014Q4', '2022Q3']


def load_T():
    """Targets + controls with a few derived control columns."""
    T = C.load_targets()
    # Easter control for organic growth: y/y change in the share of the Easter window in Q1
    # (Q2 = minus Q1); switched off where the printed OG is already calendar adjusted.
    T['easter_og'] = T['d_easter_window_q1'] * (1 - T['og_easter_adjusted'].fillna(0))
    # d_og = og_t - og_{t-4}: Easter enters as the change of the og Easter term.
    T['easter_dog'] = T['easter_og'] - T['easter_og'].shift(4)
    # Implied volume/mix proxy: organic growth minus Orkla-weighted food CPI inflation ex VAT (same
    # quarter). Ex-post construction (not a real-time variable); validated against the reported
    # 2022Q2-2026Q2 volume/mix split in 01_screen.py (corr ~0.83, level bias in 2025).
    F, _ = C.load_features(core_only=True)
    T['vol_proxy'] = T['og'] - F['w_food_cpi_xvat_yoy'].reindex(T.index)
    T['trend'] = np.arange(len(T), dtype=float)
    T['year'] = T.index.year
    T['qtr'] = T.index.quarter
    return T


def controls_for(target, T):
    """Control matrix (DataFrame) used for every regression of `target`.

    India inclusion (2014Q4-2022Q2) coincides exactly with def D, so it is absorbed by def_D
    (india flag differs only in 2007Q2-Q4, where MTR was a ~1% unit inside A); a separate india
    dummy would just act as an outlier dummy for 2007Q2-Q4 and is therefore not used. The
    ex-India robustness is the subsample excluding the D era.
    """
    defs = T[['def_B', 'def_C', 'def_D', 'def_E']]
    if target == 'd_margin':
        cols = [defs, T[['covid', 'd_easter_window_q1']]]
    elif target in ('og', 'vol_proxy'):
        cols = [defs, T[['covid', 'easter_og']]]
    elif target == 'd_og':
        cols = [defs, T[['covid', 'easter_dog', 'd_og_def_break']]]
    else:
        cols = [defs, T[['covid', 'd_easter_window_q1']]]
    return pd.concat(cols, axis=1)


def weights_for(target, T):
    if target in ('og', 'vol_proxy'):
        return T['w_og']
    if target == 'd_og':
        return T['w_d_og']
    return None


# ---------------------------------------------------------------- fast HAC regression
def _hac_cov(Xw, u, lags):
    """Bartlett-kernel Newey-West covariance of OLS beta for (whitened) X and residuals u."""
    n, k = Xw.shape
    XtX_inv = np.linalg.pinv(Xw.T @ Xw)
    g = Xw * u[:, None]
    S = g.T @ g
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = g[L:].T @ g[:-L]
        S += w * (G + G.T)
    return XtX_inv @ S @ XtX_inv


def hac_ols(y, X, w=None, lags=HAC_LAGS, drop_const_cols=True):
    """y: 1d array, X: 2d array WITHOUT constant (constant added). Rows with NaN must be removed
    beforehand. Returns dict(beta, se, t, p, n, resid). Columns that are constant (zero variance)
    within the sample are dropped (e.g. era dummies inside a subsample); the regressor of interest
    must be column 0 of X and is never dropped.
    Reproduces statsmodels OLS/WLS(...).fit(cov_type='HAC', cov_kwds={'maxlags': lags})
    (no small-sample correction, normal p-values)."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n = len(y)
    if drop_const_cols and X.shape[1] > 1:
        keep = [0] + [j for j in range(1, X.shape[1]) if np.nanstd(X[:, j]) > 1e-12]
        X = X[:, keep]
    Xc = np.column_stack([X, np.ones(n)])
    # drop collinear controls (rank deficiency inside small subsamples)
    if np.linalg.matrix_rank(Xc) < Xc.shape[1]:
        cols = [0]
        for j in range(1, Xc.shape[1]):
            if np.linalg.matrix_rank(Xc[:, cols + [j]]) == len(cols) + 1:
                cols.append(j)
        Xc = Xc[:, cols]
    if w is not None:
        sw = np.sqrt(np.asarray(w, float))
        yw, Xw = y * sw, Xc * sw[:, None]
    else:
        yw, Xw = y, Xc
    beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    u = yw - Xw @ beta
    V = _hac_cov(Xw, u, lags)
    se = np.sqrt(np.maximum(np.diag(V), 1e-300))
    t = beta / se
    p = 2 * (1 - stats.norm.cdf(np.abs(t)))
    return {'beta': beta, 'se': se, 't': t, 'p': p, 'n': n, 'V': V, 'resid': u, 'k': Xw.shape[1]}


def wald(res, idx):
    """HAC Wald statistic for H0: beta[idx] = 0 (idx list of positions)."""
    b = res['beta'][idx]
    V = res['V'][np.ix_(idx, idx)]
    W = float(b @ np.linalg.pinv(V) @ b)
    return W, 1 - stats.chi2.cdf(W, len(idx))


def frame(y, x, Ctrl, w=None, extra=None, sample=None):
    """Assemble regression frame: returns (yv, Xv, wv, index) with x first, then extra, then controls."""
    parts = [y.rename('_y'), x.rename('_x')]
    if extra is not None:
        parts.append(extra)
    parts.append(Ctrl)
    df = pd.concat(parts, axis=1)
    if w is not None:
        df['_w'] = w
    df = df.dropna()
    if w is not None:
        df = df[df['_w'] > 0]
    if sample is not None:
        df = df[sample(df.index)]
    yv = df['_y'].values
    Xv = df.drop(columns=['_y'] + (['_w'] if w is not None else [])).values
    wv = df['_w'].values if w is not None else None
    return yv, Xv, wv, df.index


# ---------------------------------------------------------------- multiple testing
def by_qvalues(p):
    """Benjamini-Yekutieli adjusted p-values (valid under arbitrary dependence)."""
    p = np.asarray(p, float)
    m = np.sum(~np.isnan(p))
    q = np.full_like(p, np.nan)
    if m == 0:
        return q
    idx = np.where(~np.isnan(p))[0]
    ps = p[idx]
    order = np.argsort(ps)
    cm = np.sum(1.0 / np.arange(1, m + 1))
    ranked = ps[order] * m * cm / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.minimum(ranked, 1)
    q[idx] = out
    return q


def holm(p):
    p = np.asarray(p, float)
    idx = np.where(~np.isnan(p))[0]
    m = len(idx)
    q = np.full_like(p, np.nan)
    ps = p[idx]
    order = np.argsort(ps)
    adj = np.maximum.accumulate(ps[order] * (m - np.arange(m)))
    out = np.empty(m)
    out[order] = np.minimum(adj, 1)
    q[idx] = out
    return q


def in_range(idx, a, b):
    a, b = pd.Period(a, 'Q'), pd.Period(b, 'Q')
    return (idx >= a) & (idx <= b)


# Andrews (1993) / Stock-Watson QLR critical values, 15% trimming, 1 restriction.
QLR_CV = {0.10: 7.12, 0.05: 8.68, 0.01: 12.16}
