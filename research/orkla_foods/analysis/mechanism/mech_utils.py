"""Local helpers for the economic-mechanism lens (lens-mechanism).

Uses the shared module common.py for data loading, alignment (C.align) and HAC OLS (C.nw_ols).
This file only adds: derived features, sample masks, distributed-lag (DL) design matrices
(unrestricted, Almon/PDL, second-difference-penalised ridge), cumulative lag sums with HAC
covariance, Wald tests, and multiple-testing adjustment.

Conventions
-----------
* Targets are y/y changes. Regressors are y/y log-inflation rates (100*ln x_t/x_{t-4}).
  A DL  d_margin_t = sum_k b_k * pi_{t-k}  on y/y data is the y/y difference of the levels model
  margin_t = sum_k b_k * ln C_{t-k}. Hence cumsum_{j<=h} b_j * 10 is the response of the
  margin LEVEL (pp) at horizon h to a PERMANENT 10% rise in the cost level at h=0, and
  10 * sum_{j=h-3..h} b_j is the response of the y/y margin change.
* Lags of a coincident-aligned feature are taken with .shift(k) on C.align(..., 'coincident').
  Real-time versions start from C.align(..., 'realtime', h) and add .shift(k) on top.
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, '/home/user/nordic-quality-rank/research/orkla_foods/analysis')
import common as C  # noqa: E402

OUTDIR = '/home/user/nordic-quality-rank/research/orkla_foods/analysis/mechanism'
EPISODE = (pd.Period('2021Q3', 'Q'), pd.Period('2023Q4', 'Q'))
HAC_LAGS = 4


# ----------------------------------------------------------------------------- data
def load_all():
    """Targets T, full feature panel F (all 1,420 + derived), dictionary D, coincident X."""
    T = C.load_targets()
    F, D = C.load_features(core_only=False)
    F, D = add_derived(F, D)
    X = C.align(F, D, 'coincident')
    T = add_targets(T, X)
    return T, F, D, X


def add_derived(F, D):
    """Derived features (documented; each gets a realtime lag = max of its components)."""
    F = F.copy()
    D = D.copy()
    new = {}

    def reg(name, series, comps, desc, cat='derived'):
        new[name] = series
        lag = int(max(D.loc[c, 'realtime_min_lag_q'] for c in comps))
        D.loc[name, ['description', 'category', 'realtime_min_lag_q', 'core']] = [desc, cat, lag, False]

    # Food CPI incl. India (for organic growth under definition D 2014Q4-2022Q2 and A 2007Q2-Q4).
    g = pd.read_csv(f'{C.DATA}/macro_panel_geo_weights_quarterly.csv')
    g.index = pd.PeriodIndex(g['period'], freq='Q')
    w_in = g['IN'].reindex(F.index).fillna(0.0)
    ind = F['in_cpi_food_idx__yoy']
    base = F['w_food_cpi_xvat_yoy']
    incl = base.where(w_in == 0, (1 - w_in) * base + w_in * ind)
    reg('w_food_cpi_xvat_inclIN_yoy', incl, ['w_food_cpi_xvat_yoy', 'in_cpi_food_idx__yoy'],
        'Orkla-weighted food CPI ex VAT, India blended in with its revenue weight when India is in the segment')

    # Calibrated input-cost index (accounting weights, share of revenue): raw materials 0.40
    # (half EU agri basket in local ccy, half FAO in local ccy), packaging 0.08, energy 0.02
    # (electricity yoy scaled by 0.25: wholesale power is ~1/4 of delivered energy cost),
    # wages 0.20. Weights sum to 0.70 (contribution-ratio ~37-40% => variable costs ~60-63%
    # of revenue, plus labour in fixed costs). Output is the weighted *sum* (pp of revenue).
    raw = 0.5 * F['eu_agri_basket_wloc_yoy'] + 0.5 * F['fao_ffpi_wloc_yoy']
    elec = 0.25 * F['elec_nordic_loc_yoy'].clip(-100, 100)
    reg('raw_mat_wloc_yoy', raw, ['eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy'],
        'Raw-material inflation in Orkla-weighted local currency: mean of EU agri basket and FAO FFPI (local ccy)')
    cost_idx = (0.40 * raw + 0.08 * F['packaging_eu_yoy'] + 0.02 * elec + 0.20 * F['w_wage_yoy']) / 0.70
    reg('cost_idx_calib_yoy', cost_idx,
        ['eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy', 'packaging_eu_yoy', 'elec_nordic_loc_yoy', 'w_wage_yoy'],
        'Calibrated Orkla input-cost index (weights raw 0.40, packaging 0.08, energy 0.02, wages 0.20; normalised)')
    reg('gap_calib', F['w_food_cpi_xvat_yoy'] - cost_idx,
        ['w_food_cpi_xvat_yoy', 'eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy', 'packaging_eu_yoy',
         'elec_nordic_loc_yoy', 'w_wage_yoy'],
        'Price-cost gap: food CPI ex VAT minus calibrated cost index')
    reg('gap_agri_xvat_wloc', F['w_food_cpi_xvat_yoy'] - F['eu_agri_basket_wloc_yoy'],
        ['w_food_cpi_xvat_yoy', 'eu_agri_basket_wloc_yoy'],
        'Price-cost gap: food CPI ex VAT minus EU agri basket in local ccy')
    reg('gap_raw_xvat_wloc', F['w_food_cpi_xvat_yoy'] - raw,
        ['w_food_cpi_xvat_yoy', 'eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy'],
        'Price-cost gap: food CPI ex VAT minus raw-material inflation (local ccy)')
    # Relative price of food (for volume elasticity) ex VAT.
    reg('w_food_rel_xvat_yoy', F['w_food_cpi_xvat_yoy'] - F['w_cpi_yoy'], ['w_food_cpi_xvat_yoy', 'w_cpi_yoy'],
        'Relative food inflation ex VAT: food CPI ex VAT minus headline CPI')
    for k, v in new.items():
        F[k] = v
    return F, D


def add_targets(T, X):
    T = T.copy()
    T['vol_proxy'] = T['og'] - X['w_food_cpi_xvat_yoy']
    T['vol_proxy_in'] = T['og'] - X['w_food_cpi_xvat_inclIN_yoy']
    # Orkla price component minus food CPI (only 2022Q2+).
    T['price_gap_cpi'] = T['price'] - X['w_food_cpi_xvat_yoy']
    # Idiosyncratic event dummies (documented in orkla_foods_methodology.md §11.3-11.4, event_note).
    idx = T.index
    def win(a, b):
        return ((idx >= pd.Period(a, 'Q')) & (idx <= pd.Period(b, 'Q'))).astype(float)
    T['ev_bakers'] = win('2012Q1', '2012Q4')       # low-margin Bakers out, comparatives incl. it (+)
    T['ev_rieber'] = win('2013Q2', '2014Q1')       # Rieber dilution (-1.8pp of -2.5pp in 2013Q2)
    T['ev_hame'] = win('2016Q2', '2017Q1')         # Hame consolidation dilution
    T['ev_erp_se'] = win('2021Q1', '2021Q2')       # Sweden ERP one-offs, lapping 2020 Covid savings
    T['ev_distrib_og'] = win('2015Q1', '2016Q4')   # Tropicana/PepsiCo distribution counted as organic
    T['ev_stockpile'] = 0.0
    T.loc[T.index == pd.Period('2020Q1', 'Q'), 'ev_stockpile'] = 1.0
    T.loc[T.index == pd.Period('2021Q1', 'Q'), 'ev_stockpile'] = -1.0
    return T


# ----------------------------------------------------------------------------- samples
def mask(T, name):
    idx = T.index
    full = pd.Series(True, index=idx)
    if name == 'full':
        return full
    if name == 'ex_infl':
        return pd.Series(~((idx >= EPISODE[0]) & (idx <= EPISODE[1])), index=idx)
    if name == 'post2008':
        return pd.Series(idx >= pd.Period('2008Q1', 'Q'), index=idx)
    if name == 'post2008_ex_infl':
        return mask(T, 'post2008') & mask(T, 'ex_infl')
    if name == 'pre2021':
        return pd.Series(idx <= pd.Period('2021Q2', 'Q'), index=idx)
    raise ValueError(name)


SAMPLES = ['full', 'ex_infl']


# ----------------------------------------------------------------------------- DL design
def lags(x, K, name=None, k0=0):
    name = name or x.name
    return pd.DataFrame({f'{name}_L{k}': x.shift(k) for k in range(k0, K + 1)})


def pdl_basis(K, P, k0=0):
    """H: (K-k0+1) x (P+1) matrix with H[k, p] = (k/K)^p (scaled for conditioning). beta = H a."""
    ks = np.arange(k0, K + 1)
    return np.vstack([(ks / max(K, 1)) ** p for p in range(P + 1)]).T


def pdl_regressors(x, K, P, name=None, k0=0):
    L = lags(x, K, name, k0)
    H = pdl_basis(K, P, k0)
    Z = pd.DataFrame(L.values @ H, index=L.index, columns=[f'{name or x.name}_pdl{p}' for p in range(P + 1)])
    Z[L.isna().any(axis=1)] = np.nan
    return Z, H


def fit_dl(y, blocks, controls=None, sample=None, K=6, kind='unres', P=2, hac=HAC_LAGS,
           weights=None, k0=0, ridge_lambda=None):
    """Fit y on distributed lags of each series in `blocks` (dict name -> Series).

    kind: 'unres' (each lag free), 'pdl' (Almon polynomial degree P), 'ridge' (second-difference
    penalty on the lag profile, HAC sandwich covariance; lambda chosen by blocked CV if None).
    Returns dict with: res (statsmodels results, or None for ridge), profile (DataFrame: block, lag,
    beta, se), cum (DataFrame: block, lag, cum, se), cov (per block beta covariance), n, r2, wald (per block).
    """
    controls = controls if controls is not None else pd.DataFrame(index=y.index)
    parts, maps = [], {}
    for nm, x in blocks.items():
        if kind == 'pdl':
            Z, H = pdl_regressors(x, K, P, nm, k0)
        else:
            Z = lags(x, K, nm, k0)
            H = np.eye(K - k0 + 1)
        parts.append(Z)
        maps[nm] = (list(Z.columns), H)
    Xd = pd.concat(parts + [controls], axis=1)
    if sample is not None:
        yy = y.where(sample.reindex(y.index).fillna(False))
    else:
        yy = y
    # drop control columns that are constant zero within the estimation sample
    dfc = pd.concat([yy.rename('_y'), Xd], axis=1).dropna()
    keep = [c for c in Xd.columns if dfc[c].std() > 1e-12 or c in sum([m[0] for m in maps.values()], [])]
    Xd = Xd[keep]
    if kind in ('unres', 'pdl'):
        res = C.nw_ols(yy, Xd, lags=hac, weights=weights)
        b, V = res.params, res.cov_params()
        n, r2 = int(res.nobs), res.rsquared
        resid = res.resid
    else:
        res = None
        b, V, n, r2, resid, lam = _ridge_fit(yy, Xd, maps, hac, ridge_lambda)
    out_prof, out_cum, covs, walds = [], [], {}, {}
    for nm, (cols, H) in maps.items():
        a = b[cols].values
        Va = V.loc[cols, cols].values
        beta = H @ a
        Vb = H @ Va @ H.T
        se = np.sqrt(np.clip(np.diag(Vb), 0, None))
        ks = np.arange(k0, K + 1)
        out_prof.append(pd.DataFrame({'block': nm, 'lag': ks, 'beta': beta, 'se': se}))
        Lc = np.tril(np.ones((len(ks), len(ks))))
        cum = Lc @ beta
        Vc = Lc @ Vb @ Lc.T
        out_cum.append(pd.DataFrame({'block': nm, 'lag': ks, 'cum': cum, 'se': np.sqrt(np.clip(np.diag(Vc), 0, None))}))
        covs[nm] = Vb
        # joint Wald test that all lag coefficients of this block are zero
        # Reported p-value uses the F(df, n-k) reference distribution (W/df), which is less
        # oversized than chi2 for HAC Wald tests with many collinear lag coefficients.
        try:
            from scipy import stats
            Vi = np.linalg.pinv(Va)
            W = float(a @ Vi @ a)
            df = len(a)
            dfd = max(n - len(b), 1)
            walds[nm] = (W, df, 1 - stats.f.cdf(W / df, df, dfd))
        except Exception:
            walds[nm] = (np.nan, len(a), np.nan)
    return dict(res=res, params=b, V=V, profile=pd.concat(out_prof), cum=pd.concat(out_cum), cov=covs,
                n=n, r2=r2, wald=walds, maps=maps, resid=resid, X=Xd, kind=kind)


def _hac_meat(Xm, e, L):
    S = (Xm * e[:, None])
    O = S.T @ S
    for l in range(1, L + 1):
        w = 1 - l / (L + 1)
        G = S[l:].T @ S[:-l]
        O += w * (G + G.T)
    return O


def _ridge_fit(yy, Xd, maps, hac, lam=None):
    df = pd.concat([yy.rename('_y'), Xd], axis=1).dropna()
    y = df['_y'].values
    Xm = np.column_stack([np.ones(len(df)), df.drop(columns=['_y']).values])
    cols = ['const'] + list(df.columns[1:])
    # penalty: second differences within each DL block (not on controls/constant)
    Pm = np.zeros((len(cols), len(cols)))
    for nm, (bc, _) in maps.items():
        ix = [cols.index(c) for c in bc]
        m = len(ix)
        if m < 3:
            continue
        D2 = np.zeros((m - 2, m))
        for i in range(m - 2):
            D2[i, i:i + 3] = [1, -2, 1]
        Pm[np.ix_(ix, ix)] += D2.T @ D2
    if lam is None:
        lam = _ridge_cv(y, Xm, Pm)
    A = np.linalg.inv(Xm.T @ Xm + lam * Pm)
    b = A @ Xm.T @ y
    e = y - Xm @ b
    O = _hac_meat(Xm, e, hac)
    V = A @ O @ A
    r2 = 1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return (pd.Series(b, index=cols), pd.DataFrame(V, index=cols, columns=cols), len(y), r2,
            pd.Series(e, index=df.index), lam)


def _ridge_cv(y, Xm, Pm, grid=(1, 3, 10, 30, 100, 300, 1000, 3000), block=8):
    n = len(y)
    best, bl = np.inf, grid[0]
    folds = [np.arange(i, min(i + block, n)) for i in range(0, n, block)]
    for lam in grid:
        sse = 0.0
        for f in folds:
            tr = np.setdiff1d(np.arange(n), np.arange(max(0, f[0] - 4), min(n, f[-1] + 5)))
            A = np.linalg.pinv(Xm[tr].T @ Xm[tr] + lam * Pm)
            b = A @ Xm[tr].T @ y[tr]
            sse += ((y[f] - Xm[f] @ b) ** 2).sum()
        if sse < best:
            best, bl = sse, lam
    return bl


def wald_linear(params, V, R, r=None, dfd=None):
    """Wald test R b = r using the (HAC) covariance V. Returns (W, df, p); p from F(df, dfd) if dfd
    is given (recommended), else chi2(df)."""
    from scipy import stats
    b = np.asarray(params)
    R = np.atleast_2d(R)
    r = np.zeros(R.shape[0]) if r is None else np.asarray(r)
    d = R @ b - r
    W = float(d @ np.linalg.pinv(R @ np.asarray(V) @ R.T) @ d)
    q = R.shape[0]
    if dfd is not None:
        return W, q, 1 - stats.f.cdf(W / q, q, dfd)
    return W, q, 1 - stats.chi2.cdf(W, q)


def lag_stats_sim(fit, block, nsim=4000, seed=0):
    """Simulate lag-profile statistics from N(beta, V_beta) (HAC):
    trough lag of the cumulative (level) response, peak-negative lag of beta, recovery lag
    (first lag after the trough where the cumulative response is back above half the trough)."""
    rng = np.random.default_rng(seed)
    prof = fit['profile'][fit['profile'].block == block]
    b = prof['beta'].values
    ks = prof['lag'].values
    Vb = fit['cov'][block]
    draws = rng.multivariate_normal(b, Vb + 1e-12 * np.eye(len(b)), size=nsim)
    cum = np.cumsum(draws, axis=1)
    trough = ks[np.argmin(cum, axis=1)]
    peakneg = ks[np.argmin(draws, axis=1)]
    rec = []
    for c in cum:
        i = int(np.argmin(c))
        after = np.where(c[i:] > 0.5 * c[i])[0]
        rec.append(ks[i + after[0]] if (len(after) and c[i] < 0) else np.nan)
    rec = np.array(rec, dtype=float)
    def summ(v):
        v = v[~np.isnan(v)]
        return (np.median(v), np.percentile(v, 5), np.percentile(v, 95)) if len(v) else (np.nan,) * 3
    pt = (ks[np.argmin(np.cumsum(b))], ks[np.argmin(b)])
    peakcum = ks[np.argmax(cum, axis=1)]
    peakpos = ks[np.argmax(draws, axis=1)]
    return dict(trough_point=pt[0], trough=summ(trough.astype(float)), peakneg_point=pt[1],
                peakneg=summ(peakneg.astype(float)), recovery=summ(rec),
                recovery_share_na=float(np.isnan(rec).mean()),
                peakcum_point=ks[np.argmax(np.cumsum(b))], peakcum=summ(peakcum.astype(float)),
                peakpos_point=ks[np.argmax(b)], peakpos=summ(peakpos.astype(float)))


def mt_adjust(p, method='fdr_by'):
    from statsmodels.stats.multitest import multipletests
    p = np.asarray(p, dtype=float)
    out = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    if ok.sum():
        out[ok] = multipletests(p[ok], method=method)[1]
    return out


def std_controls(T, which=('d_easter_window_q1', 'covid')):
    return T[list(which)].astype(float)


def savefig(fig, name):
    fig.savefig(f'{OUTDIR}/{name}', dpi=130, bbox_inches='tight')
