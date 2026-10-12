"""Calibrated inference for small, persistent, overlapping samples.

Newey-West t-statistics are badly oversized here (n ~ 15-40, persistent x and
overlapping y/y targets): pure-noise predictors reach |t| > 2.5 in 10-40% of
draws (code audit). Instead we use a conditional randomisation test:

  H0: x is independent of y.
  Simulate B series x* from an AR(p) model fitted to all non-NaN values of x
  (p by AIC, residual bootstrap; explosive / unit-root fits are shrunk to a
  maximum root modulus of 0.98), keep x's NaN pattern, and recompute the OLS
  t-statistic of x* in the SAME regression (same y, same controls, same rows).
  The p-value is the share of |t*| >= |t|. Degenerate cases (x collinear with
  the controls, non-finite t, degenerate null) return NaN.

Everything is vectorised over B with the Frisch-Waugh-Lovell theorem, so
B = 20,000 per test is cheap. Simulations use a seed derived from the feature
name, so the same x* draws are reused across targets and horizons.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd


def _seed(name: str) -> int:
    return int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)


def fit_ar(x: np.ndarray, pmax: int = 4):
    best = None
    for p in range(1, pmax + 1):
        if len(x) <= p + 5:
            break
        Y = x[p:]
        Z = np.column_stack([np.ones(len(Y))] + [x[p - j:-j] for j in range(1, p + 1)])
        b, *_ = np.linalg.lstsq(Z, Y, rcond=None)
        e = Y - Z @ b
        aic = len(Y) * np.log(e @ e / len(Y)) + 2 * (p + 1)
        if best is None or aic < best[0]:
            best = (aic, p, b, e)
    return best[1], best[2], best[3]


def max_root(phi: np.ndarray) -> float:
    p = len(phi)
    C = np.zeros((p, p))
    C[0] = phi
    if p > 1:
        C[1:, :-1] = np.eye(p - 1)
    return float(np.abs(np.linalg.eigvals(C)).max())


def simulate(x: pd.Series, B: int, name: str, burn: int = 100, max_mod: float = 0.98) -> np.ndarray:
    """Return array (len(x), B) of AR-sieve draws placed on x's observed positions (NaN elsewhere)."""
    obs = x.notna().to_numpy()
    vals = x.dropna().to_numpy(float)
    p, b, e = fit_ar(vals)
    r = max_root(b[1:])
    if r > max_mod:
        b = b.copy()
        b[1:] = b[1:] * (max_mod / r) ** np.arange(1, p + 1)
        b[0] = vals.mean() * (1 - b[1:].sum())
    e = e - e.mean()
    rng = np.random.default_rng(_seed(name))
    n = len(vals)
    out = np.empty((n + burn, B))
    out[:p] = vals[:p, None]
    shocks = rng.choice(e, size=(n + burn, B), replace=True)
    for t in range(p, n + burn):
        out[t] = b[0] + (b[1:][:, None] * out[t - p:t][::-1]).sum(axis=0) + shocks[t]
    full = np.full((len(x), B), np.nan)
    full[obs] = out[burn:]
    return full


def ols_t_many(y: np.ndarray, Z: np.ndarray, X: np.ndarray) -> np.ndarray:
    """OLS t-statistic of each column of X when added to y ~ Z (Z includes a constant).

    y: (n,), Z: (n, k), X: (n, m). Returns (m,) t-statistics.
    """
    Q, _ = np.linalg.qr(Z)
    my = y - Q @ (Q.T @ y)
    MX = X - Q @ (Q.T @ X)
    sxx = (MX * MX).sum(axis=0)
    beta = (MX * my[:, None]).sum(axis=0) / sxx
    resid = my[:, None] - MX * beta
    dof = len(y) - Z.shape[1] - 1
    s2 = (resid * resid).sum(axis=0) / max(dof, 1)
    return beta / np.sqrt(s2 / sxx)


def boot_pvalue(y: np.ndarray, Z: np.ndarray, x: np.ndarray, Xsim: np.ndarray) -> tuple[float, float]:
    """Two-sided bootstrap p-value of the OLS t of x, and the observed t (NaN if degenerate)."""
    Q, _ = np.linalg.qr(Z)
    xc = x - x.mean()
    mx = x - Q @ (Q.T @ x)
    if (xc @ xc) == 0 or (mx @ mx) < 1e-8 * (xc @ xc):
        return np.nan, np.nan
    t = ols_t_many(y, Z, x[:, None])[0]
    if not np.isfinite(t):
        return np.nan, t
    tb = ols_t_many(y, Z, Xsim)
    tb = tb[np.isfinite(tb)]
    if len(tb) < 0.99 * Xsim.shape[1]:
        return np.nan, t
    return (1 + np.sum(np.abs(tb) >= abs(t))) / (1 + len(tb)), t
