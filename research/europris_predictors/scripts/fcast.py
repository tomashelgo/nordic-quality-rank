"""Forecast-evaluation primitives shared by the Europris predictor scripts.

Direct h-step regressions, expanding-window out-of-sample (OOS) forecasts,
Clark-West tests for nested models and Newey-West HAC inference. Pure numpy /
scipy so the screen can run thousands of models quickly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def ols(y: np.ndarray, X: np.ndarray):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def nw_se(X: np.ndarray, resid: np.ndarray, lags: int) -> np.ndarray:
    """Newey-West HAC standard errors for OLS coefficients."""
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    u = X * resid[:, None]
    S = u.T @ u
    for L in range(1, lags + 1):
        w = 1.0 - L / (lags + 1.0)
        G = u[L:].T @ u[:-L]
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv * n / max(n - k, 1)
    return np.sqrt(np.clip(np.diag(V), 0, None))


def hac_mean_test(d: np.ndarray, lags: int):
    """t-stat of mean(d) with Newey-West variance (used for Clark-West / DM)."""
    d = np.asarray(d, float)
    n = len(d)
    m = d.mean()
    e = d - m
    s = e @ e / n
    for L in range(1, min(lags, n - 1) + 1):
        w = 1.0 - L / (lags + 1.0)
        s += 2 * w * (e[L:] @ e[:-L]) / n
    se = np.sqrt(max(s, 1e-12) / n)
    return m / se


def design(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    X = df[cols].to_numpy(float) if cols else np.empty((len(df), 0))
    return np.column_stack([np.ones(len(df)), X])


def oos_forecasts(
    data: pd.DataFrame,
    y_col: str,
    base_cols: list[str],
    extra_cols: list[str],
    h: int,
    min_train: int,
    origin_pos: np.ndarray,
):
    """Expanding-window direct forecasts.

    `data` is indexed by forecast origin t (rows are aligned so that y_col is
    the target y_{t+h} and every regressor is known at t). A forecast for the
    row at origin position i may only use rows j with j + h <= i, i.e. pairs
    whose target had been realised by time i.

    Returns a DataFrame indexed like the evaluated rows with columns
    y, f_bench, f_model.
    """
    y = data[y_col].to_numpy(float)
    Xb = design(data, base_cols)
    Xm = design(data, base_cols + extra_cols)
    out = []
    for i in range(len(data)):
        train = np.where(origin_pos <= origin_pos[i] - h)[0]
        if len(train) < min_train or np.isnan(y[i]):
            continue
        yb = y[train]
        Xbt, Xmt = Xb[train], Xm[train]
        # drop constant (zero-variance) control columns within the window
        keep_b = _varying(Xbt)
        keep_m = _varying(Xmt)
        bb = ols(yb, Xbt[:, keep_b])
        bm = ols(yb, Xmt[:, keep_m])
        out.append((data.index[i], y[i], Xb[i, keep_b] @ bb, Xm[i, keep_m] @ bm))
    res = pd.DataFrame(out, columns=["origin", "y", "f_bench", "f_model"]).set_index("origin")
    return res


def _varying(X: np.ndarray) -> np.ndarray:
    keep = np.ones(X.shape[1], bool)
    for j in range(1, X.shape[1]):
        col = X[:, j]
        if np.nanstd(col) < 1e-12:
            keep[j] = False
    return keep


def evaluate(res: pd.DataFrame, h: int) -> dict:
    if len(res) < 6:
        return {"n_oos": len(res), "oos_r2": np.nan, "cw_t": np.nan, "cw_p": np.nan,
                "dm_t": np.nan, "rmse_bench": np.nan, "rmse_model": np.nan}
    eb = res["y"] - res["f_bench"]
    em = res["y"] - res["f_model"]
    mse_b, mse_m = (eb ** 2).mean(), (em ** 2).mean()
    adj = (res["f_bench"] - res["f_model"]) ** 2
    f_cw = eb ** 2 - (em ** 2 - adj)
    lags = max(h - 1, 0) + 1
    cw_t = hac_mean_test(f_cw.to_numpy(), lags)
    dm_t = hac_mean_test((eb ** 2 - em ** 2).to_numpy(), lags)
    return {
        "n_oos": len(res),
        "oos_r2": 1 - mse_m / mse_b,
        "cw_t": cw_t,
        "cw_p": 1 - stats.norm.cdf(cw_t),
        "dm_t": dm_t,
        "rmse_bench": np.sqrt(mse_b),
        "rmse_model": np.sqrt(mse_m),
    }


def insample(data: pd.DataFrame, y_col: str, base_cols: list[str], x_col: str, h: int) -> dict:
    d = data.dropna(subset=[y_col] + base_cols + [x_col])
    if len(d) < 10:
        return {"n_is": len(d), "beta_std": np.nan, "t_hac": np.nan, "p_hac": np.nan, "partial_r2": np.nan}
    y = d[y_col].to_numpy(float)
    X = design(d, base_cols + [x_col])
    keep = _varying(X)
    keep[-1] = True
    X = X[:, keep]
    b = ols(y, X)
    r = y - X @ b
    se = nw_se(X, r, lags=max(h, 1) + 1)
    t = b[-1] / se[-1] if se[-1] > 0 else np.nan
    Xb = design(d, base_cols)
    Xb = Xb[:, _varying(Xb)]
    rb = y - Xb @ ols(y, Xb)
    partial = 1 - (r @ r) / (rb @ rb) if rb @ rb > 0 else np.nan
    sx, sy = d[x_col].std(), d[y_col].std()
    return {
        "n_is": len(d),
        "beta": b[-1],
        "beta_std": b[-1] * sx / sy if sy > 0 else np.nan,
        "t_hac": t,
        "p_hac": 2 * (1 - stats.t.cdf(abs(t), df=max(len(d) - X.shape[1], 1))) if np.isfinite(t) else np.nan,
        "partial_r2": partial,
    }


def bh_fdr(p: pd.Series) -> pd.Series:
    """Benjamini-Hochberg adjusted p-values (NaNs preserved)."""
    p = p.astype(float)
    mask = p.notna()
    pv = p[mask].to_numpy()
    n = len(pv)
    if n == 0:
        return p
    order = np.argsort(pv)
    ranked = pv[order] * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(adj, 0, 1)
    res = p.copy()
    res[mask] = out
    return res


def cv_forecasts(
    data: pd.DataFrame,
    y_col: str,
    base_cols: list[str],
    extra_cols: list[str],
    gap: int,
    block: np.ndarray,
    pos: np.ndarray,
    min_train: int = 12,
    gap_future: int | None = None,
):
    """hv-block cross-validation (Racine 2000).

    Each block (e.g. a calendar year of target dates) is predicted from a model
    fitted on the other rows whose origin lies more than `gap` quarters before
    or `gap_future` quarters after the block, so overlapping y/y windows (and
    test targets reappearing as a training row's lagged regressor) cannot leak.
    Returns DataFrame(origin -> y, f_bench, f_model).
    """
    gap_future = gap if gap_future is None else gap_future
    y = data[y_col].to_numpy(float)
    Xb = design(data, base_cols)
    Xm = design(data, base_cols + extra_cols)
    out = []
    for b in np.unique(block):
        test = np.where(block == b)[0]
        lo, hi = pos[test].min() - gap, pos[test].max() + gap_future
        train = np.where((pos < lo) | (pos > hi))[0]
        if len(train) < min_train:
            continue
        keep_b = _varying(Xb[train])
        keep_m = _varying(Xm[train])
        bb = ols(y[train], Xb[train][:, keep_b])
        bm = ols(y[train], Xm[train][:, keep_m])
        for i in test:
            out.append((data.index[i], y[i], Xb[i, keep_b] @ bb, Xm[i, keep_m] @ bm))
    return pd.DataFrame(out, columns=["origin", "y", "f_bench", "f_model"]).set_index("origin")
