"""Out-of-sample forecasting engine for the Orkla Foods macro-predictor horse race (lens-oos).

Conventions (all real time; no future information):
  * Target quarter t, horizon h in {0,1,2}. The forecast is made at the end of quarter t-h.
    - Macro features: C.align(F, D, 'realtime', h) -> row t holds feature_{t-h-lag_q}.
    - Orkla target: known up to quarter t-h-1 (quarter t-h is not yet reported at that date).
      Hence the AR terms are y_{t-h-1} and the seasonal lag y_{t-4} (always known for h<=2),
      and the training sample contains only rows s <= t-h-1.
  * Expanding window, re-estimated every quarter.
  * Pandemic quarters 2020Q1-2021Q2 are never used as training observations (stockpiling and its
    base effect); they are still forecast and evaluated, and their values still enter as AR lags.
  * Observation weights: og -> w_og, d_og -> w_d_og (quality based, def-break halved), margins -> 1.
  * Calendar (Easter) regressors are deterministic and known in advance.

The core estimator for small linear models accumulates X'WX and X'Wy over rows (expanding window),
so each quarter's re-estimation is an exact WLS fit on the rows available at that origin.
"""
import os
import sys
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")   # small matrices: multithreaded BLAS is much slower
import numpy as np
import pandas as pd

sys.path.insert(0, '/home/user/nordic-quality-rank/research/orkla_foods/analysis')
import common as C  # noqa: E402

OUT = '/home/user/nordic-quality-rank/research/orkla_foods/analysis/oos'

TARGETS = ['d_margin', 'd_og', 'og', 'd_margin_r4']
HS = [0, 1, 2]
FIRST_FC = pd.Period('2006Q1', 'Q')      # burn-in forecasts (track record for combination ranking)
EVAL_START = pd.Period('2010Q1', 'Q')
EVAL_START2 = pd.Period('2015Q1', 'Q')
LAST = pd.Period('2026Q2', 'Q')
TRAIN_EXCL = pd.period_range('2020Q1', '2021Q2', freq='Q')
INFL = pd.period_range('2021Q3', '2023Q4', freq='Q')
COVID_EVAL = pd.period_range('2020Q1', '2021Q2', freq='Q')
MULTI_TRAIN_START = pd.Period('2003Q1', 'Q')   # penalised / PCA / ML models: complete-case features from here
MIN_TRAIN_UNI = 12
MIN_TRAIN_MULTI = 20

# Base (nested benchmark) variants on top of which every macro model is built:
#   'arcal' : AR terms + Easter calendar terms. This was the PRE-COMMITTED base (Easter shifts sales between
#             Q1 and Q2). The OOS benchmark race showed the calendar terms HURT out of sample (AR+cal RMSE
#             5-12% above pure AR), so it is kept only as a reported sensitivity.
#   'ar'    : target's own realtime AR terms (y_{t-h-1}, y_{t-4}); primary for d_margin, og, d_margin_r4.
#   'oglev' : for d_og only: og_{t-h-1} and og_{t-4} (organic-growth LEVEL lags). Because og_py ~ og_{t-4}
#             is known, d_og forecasting is the same problem as og forecasting, and the og-level
#             parameterisation is a far better benchmark (RMSE ~3.3 vs ~4.3 for the d_og AR). Primary for d_og.
# Switching the primary base away from the pre-committed one was decided from BENCHMARK performance only
# (before looking at any macro model) and makes the test harder for the macro models, not easier.
VARIANTS = {'d_margin': ['ar', 'arcal'], 'd_og': ['oglev', 'ar', 'arcal'], 'og': ['ar', 'arcal'],
            'd_margin_r4': ['ar']}
PRIMARY = {'d_margin': 'ar', 'd_og': 'oglev', 'og': 'ar', 'd_margin_r4': 'ar'}
BASE_BENCH = {'ar': 'ar', 'arcal': 'arcal', 'oglev': 'ar_oglev'}
BASE_NAME = {t: BASE_BENCH[PRIMARY[t]] for t in TARGETS}

# Small theory-guided multivariate models, fixed ex ante (features enter at their realtime alignment).
THEORY = {
    'd_margin': {
        'th_pcg_fx_energy': ['price_cost_gap_ppi', 'w_fx_vs_eur_yoy', 'elec_nordic_loc_yoy'],
        'th_input_costs': ['fao_ffpi_wloc_yoy', 'w_wage_yoy', 'packaging_eu_yoy'],
        'th_pass_through': ['w_food_cpi_xvat_dyoy', 'w_food_ppi_dyoy'],
        'th_pcg_fao_usd_oil': ['price_cost_gap_fao_wloc', 'w_fx_vs_usd_yoy', 'brent_nok_yoy'],
        'th_nordic_pcg': ['nw_price_cost_gap_ppi', 'nw_food_cpi_xvat_dyoy'],
    },
    'd_og': {
        'th_cpi_wage_conf': ['w_food_cpi_xvat_dyoy', 'w_real_wage_dyoy', 'w_cons_conf_z_d4'],
        'th_nordic_cpi_wage_conf': ['nw_food_cpi_xvat_dyoy', 'nw_real_wage_dyoy', 'nw_cons_conf_z_d4'],
        'th_price_volume': ['w_food_cpi_xvat_dyoy', 'w_retail_food_vol_dyoy'],
        'th_pipeline': ['w_food_ppi_dyoy', 'w_ec_food_ind_sell_price_exp_d4'],
        'th_nordic_cpi': ['nw_food_cpi_xvat_dyoy'],
    },
    'og': {
        'th_cpi_wage_conf': ['w_food_cpi_xvat_yoy', 'w_real_wage_yoy', 'w_cons_conf_z'],
        'th_nordic_cpi_wage_conf': ['nw_food_cpi_xvat_yoy', 'nw_real_wage_yoy', 'nw_cons_conf_z'],
        'th_price_volume': ['w_food_cpi_xvat_yoy', 'w_retail_food_vol_yoy'],
        'th_pipeline': ['w_food_ppi_yoy', 'w_ec_food_ind_sell_price_exp_lvl'],
        'th_nordic_cpi': ['nw_food_cpi_xvat_yoy'],
    },
    'd_margin_r4': {
        'th_pcg_fx_energy': ['price_cost_gap_ppi', 'w_fx_vs_eur_yoy', 'elec_nordic_loc_yoy'],
        'th_input_costs': ['fao_ffpi_wloc_yoy', 'w_wage_yoy', 'packaging_eu_yoy'],
        'th_pass_through': ['w_food_cpi_xvat_dyoy', 'w_food_ppi_dyoy'],
        'th_pcg_fao_usd_oil': ['price_cost_gap_fao_wloc', 'w_fx_vs_usd_yoy', 'brent_nok_yoy'],
        'th_nordic_pcg': ['nw_price_cost_gap_ppi', 'nw_food_cpi_xvat_dyoy'],
    },
}


# ----------------------------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------------------------
def load_all():
    T = C.load_targets()
    F, D = C.load_features(core_only=True)
    idx = T.index  # 2000Q1..2026Q2
    X = {h: C.align(F, D, 'realtime', h).reindex(idx) for h in HS}
    return T, F, D, X


def target_weights(T, tgt):
    if tgt == 'og':
        return T['w_og'].fillna(0.0)
    if tgt == 'd_og':
        return T['w_d_og'].fillna(0.0)
    return pd.Series(1.0, index=T.index)


def calendar_frame(T, tgt):
    B = pd.DataFrame(index=T.index)
    if tgt in ('d_margin', 'og'):
        B['easter_shift'] = T['easter_shift'].astype(float)
        B['d_easter_window'] = T['d_easter_window_q1'].astype(float)
    elif tgt == 'd_og':
        es = T['easter_shift'].astype(float)
        ew = T['d_easter_window_q1'].astype(float)
        B['d4_easter_shift'] = es - es.shift(4)
        B['d4_easter_window'] = ew - ew.shift(4)
    return B


def ar_frame(T, tgt, h, lags=None):
    y = T[tgt]
    if lags is None:
        lags = [h + 1] + ([4] if h + 1 < 4 else [])
    return pd.DataFrame({f'ar{l}': y.shift(l) for l in lags}, index=T.index)


def base_frame(T, tgt, h, variant):
    if variant == 'oglev':
        assert tgt == 'd_og'
        return ar_frame(T, 'og', h).add_prefix('og_')
    B = ar_frame(T, tgt, h)
    if variant == 'arcal':
        B = pd.concat([B, calendar_frame(T, tgt)], axis=1)
    elif variant != 'ar':
        raise ValueError(variant)
    return B


def train_ok_mask(index, start=None):
    ok = ~index.isin(TRAIN_EXCL)
    if start is not None:
        ok &= (index >= start)
    return np.asarray(ok)


# ----------------------------------------------------------------------------------------------
# Expanding-window WLS via cumulative cross-products
# ----------------------------------------------------------------------------------------------
class ExpandingWLS:
    """Exact expanding-window WLS forecasts. X excludes the constant (added here).

    forecast(i, h): fit on valid rows with position <= i-h-1, predict row i.
    Columns that are (near-)constant within the training window are dropped for that origin.
    """

    def __init__(self, y, X, w, train_ok):
        y = np.asarray(y, float)
        X = np.asarray(X, float)
        if X.ndim == 1:
            X = X[:, None]
        w = np.asarray(w, float)
        n, k = X.shape
        # Center / scale columns for numerical conditioning (OLS forecasts are invariant to this).
        mu = np.nanmean(X, 0) if k else np.zeros(0)
        sd = np.nanstd(X, 0) if k else np.ones(0)
        sd = np.where(np.isfinite(sd) & (sd > 0), sd, 1.0)
        mu = np.where(np.isfinite(mu), mu, 0.0)
        Xs = (X - mu) / sd
        Z = np.column_stack([np.ones(n), Xs])
        valid = np.asarray(train_ok, bool) & np.isfinite(y) & np.isfinite(Z).all(1) & (w > 0)
        sw = np.sqrt(np.where(valid, w, 0.0))
        Zw = np.where(valid[:, None], Z, 0.0) * sw[:, None]
        yw = np.where(valid, y, 0.0) * sw
        self.ZtZ = np.cumsum(np.einsum('ni,nj->nij', Zw, Zw), axis=0)
        self.Zty = np.cumsum(Zw * yw[:, None], axis=0)
        self.yty = np.cumsum(yw * yw)
        self.sw_sum = np.cumsum(sw ** 2)
        self.cnt = np.cumsum(valid)
        self.Z = Z
        self.k = Z.shape[1]
        self.n = n

    def fit_at(self, j, min_train):
        if j < 0 or self.cnt[j] < max(min_train, self.k + 6):
            return None
        A = self.ZtZ[j]
        b = self.Zty[j]
        W = self.sw_sum[j]
        # drop columns with ~zero weighted variance in the training window
        keep = [0]
        for c in range(1, self.k):
            m1 = A[0, c] / W
            m2 = A[c, c] / W
            if m2 - m1 * m1 > 1e-8:
                keep.append(c)
        keep = np.array(keep)
        Ak = A[np.ix_(keep, keep)]
        bk = b[keep]
        # pseudo-inverse: exact collinearity inside a short window (e.g. the two Easter measures coincide
        # in 2011-14) gives the minimum-norm solution instead of exploding coefficients
        beta = np.linalg.pinv(Ak, rcond=1e-10, hermitian=True) @ bk
        ssr = self.yty[j] - 2 * beta @ bk + beta @ Ak @ beta
        return keep, beta, max(ssr, 1e-12), int(self.cnt[j])

    def forecast(self, i, h, min_train):
        if not np.isfinite(self.Z[i]).all():
            return np.nan
        f = self.fit_at(i - h - 1, min_train)
        if f is None:
            return np.nan
        keep, beta, _, _ = f
        return float(self.Z[i, keep] @ beta)

    def forecasts(self, positions, h, min_train):
        return np.array([self.forecast(i, h, min_train) for i in positions])


def bic_at(model, j, min_train):
    f = model.fit_at(j, min_train)
    if f is None:
        return np.inf
    keep, beta, ssr, n = f
    return n * np.log(ssr / n) + len(keep) * np.log(n)


# ----------------------------------------------------------------------------------------------
# Penalised regressions with an unpenalised base (Frisch-Waugh-Lovell), and PCA / ML helpers
# ----------------------------------------------------------------------------------------------
def _fwl(y, A, X, w):
    s = np.sqrt(w)
    yt, At, Xt = y * s, A * s[:, None], X * s[:, None]
    Q, _ = np.linalg.qr(At)
    ry = yt - Q @ (Q.T @ yt)
    RX = Xt - Q @ (Q.T @ Xt)
    sd = RX.std(0)
    keep = sd > 1e-8
    Z = RX[:, keep] / sd[keep]
    return yt, At, Xt, ry, Z, sd, keep


def penalised_path(method, y, A, X, w, alphas):
    """Return (gammas k x L, betas p x L) for base coefs (unpenalised) and feature coefs on the alpha path."""
    from sklearn.linear_model import lasso_path, enet_path
    yt, At, Xt, ry, Z, sd, keep = _fwl(y, A, X, w)
    p = X.shape[1]
    L = len(alphas)
    B = np.zeros((p, L))
    if Z.shape[1] > 0:
        if method == 'lasso':
            _, coefs, _ = lasso_path(Z, ry, alphas=alphas, max_iter=5000, tol=1e-4)
        elif method == 'enet':
            _, coefs, _ = enet_path(Z, ry, l1_ratio=0.5, alphas=alphas, max_iter=5000, tol=1e-4)
        elif method == 'ridge':
            U, S, Vt = np.linalg.svd(Z, full_matrices=False)
            Uy = U.T @ ry
            coefs = np.stack([Vt.T @ (S / (S ** 2 + a) * Uy) for a in alphas], axis=1)
        else:
            raise ValueError(method)
        B[keep, :] = coefs / sd[keep][:, None]
    G = np.linalg.lstsq(At, yt[:, None] - Xt @ B, rcond=None)[0]
    return G, B


def alpha_grid(method, y, A, X, w, n_alpha=25):
    if method == 'ridge':
        return np.logspace(4, -1, n_alpha)
    yt, At, Xt, ry, Z, sd, keep = _fwl(y, A, X, w)
    n = len(ry)
    amax = np.max(np.abs(Z.T @ ry)) / n if Z.shape[1] else 1.0
    if method == 'enet':
        amax = amax / 0.5
    return amax * np.logspace(0, -2.5, n_alpha)


# ----------------------------------------------------------------------------------------------
# Evaluation helpers
# ----------------------------------------------------------------------------------------------
def hac_mean_test(d, lags=4):
    """t-stat of mean(d) with Newey-West SE; returns (t, one-sided p for mean>0)."""
    import statsmodels.api as sm
    from scipy import stats
    d = np.asarray(d, float)
    d = d[np.isfinite(d)]
    n = len(d)
    if n < 8 or np.allclose(d, d[0]):
        return np.nan, np.nan
    r = sm.OLS(d, np.ones(n)).fit(cov_type='HAC', cov_kwds={'maxlags': lags})
    t = r.tvalues[0]
    return t, 1 - stats.norm.cdf(t)


def clark_west(y, fb, fm, lags=4):
    adj = (y - fb) ** 2 - ((y - fm) ** 2 - (fb - fm) ** 2)
    return hac_mean_test(adj, lags)


def diebold_mariano(y, fb, fm, lags=4):
    d = (y - fb) ** 2 - (y - fm) ** 2
    return hac_mean_test(d, lags)


def pesaran_timmermann(actual_sign, fc_sign):
    """PT (1992) test of directional accuracy; returns (hit rate, one-sided p)."""
    from scipy import stats
    a = np.asarray(actual_sign) > 0
    f = np.asarray(fc_sign) > 0
    n = len(a)
    if n < 8:
        return np.nan, np.nan
    hit = np.mean(a == f)
    py, px = a.mean(), f.mean()
    pstar = py * px + (1 - py) * (1 - px)
    v_hit = pstar * (1 - pstar) / n
    v_star = ((2 * py - 1) ** 2 * px * (1 - px) / n + (2 * px - 1) ** 2 * py * (1 - py) / n
              + 4 * py * px * (1 - py) * (1 - px) / n ** 2)
    denom = v_hit - v_star
    if denom <= 0:
        return hit, np.nan
    s = (hit - pstar) / np.sqrt(denom)
    return hit, 1 - stats.norm.cdf(s)
