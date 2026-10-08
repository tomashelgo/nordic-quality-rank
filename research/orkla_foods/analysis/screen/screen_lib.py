"""Univariate predictor screen for Orkla Foods targets (lens-screen).

Uses the shared module common.py for targets, features and real-time alignment
(C.load_targets, C.load_features, C.align). The only thing re-implemented here is a
fast numpy WLS + Newey-West (Bartlett) HAC estimator, which is validated against
C.nw_ols in validate_hac() (it reproduces statsmodels to machine precision) and is
needed because the full screen runs ~300k regressions.

Conventions
-----------
Alignments (quarter t = Orkla reporting quarter):
  coin : X_t = feature_t                              (coincident; explanatory only)
  rt0  : X_t = feature_{t - lag_q}                    (nowcast before the Q report)
  rt1  : X_t = feature_{t - 1 - lag_q}                (1 quarter ahead)
  rt2  : X_t = feature_{t - 2 - lag_q}
  rt4  : X_t = feature_{t - 4 - lag_q}
Own-lag term for the incremental test: y_{t-L} with L = max(4, h+1) (h=0 for coin), i.e. the
same-quarter-last-year value of the target, which is published long before the forecast date
for h<=3; at h=4 the t-4 report is not yet out, so y_{t-5} is used.
For d_og and d_og_r4 a second incremental test (t_incr_base) controls for the base-period
level og_{t-L} (og_r4_{t-L}): d_og = og_t - og_{t-4}, so anything correlated with last year's
organic growth (e.g. food inflation 4-5 quarters ago) predicts d_og through the base effect alone.
Leverage-adjusted HAC t (t_lev): residuals scaled by 1/(1-h_ii) before the Newey-West sum.

Target specifications (base regression y_t = a + b x_t + controls):
  d_margin    : no controls, OLS, HAC(4)
  og          : + easter_shift, WLS weights w_og (quality A=1, B=.7, C=.4), HAC(4)
  d_og        : + easter_shift + d_og_def_break, WLS weights w_d_og, HAC(4)
  d_margin_r4 : no controls, OLS, HAC(8) (overlapping 4Q windows)
  d_og_r4     : + local def-break dummy for the 8-quarter comparison window, OLS, HAC(8)
  vol_proxy   : og - w_food_cpi_xvat_yoy (implied volume/mix); + easter_shift, WLS w_og, HAC(4)
"""
import sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, '/home/user/nordic-quality-rank/research/orkla_foods/analysis')
import common as C  # noqa: E402

OUTDIR = '/home/user/nordic-quality-rank/research/orkla_foods/analysis/screen'

ALIGNMENTS = {  # name -> (mode, h)
    'coin': ('coincident', 0),
    'rt0': ('realtime', 0),
    'rt1': ('realtime', 1),
    'rt2': ('realtime', 2),
    'rt4': ('realtime', 4),
}
ALIGN_LABEL = {
    'coin': 'coincident (same quarter, not real-time)',
    'rt0': 'real-time nowcast h=0 (info at quarter end, before report)',
    'rt1': 'real-time h=1 (1 quarter ahead)',
    'rt2': 'real-time h=2 (2 quarters ahead)',
    'rt4': 'real-time h=4 (4 quarters ahead)',
}

TARGET_SPEC = {
    'd_margin':    dict(controls=[], weight=None, hac=4, primary=True),
    'og':          dict(controls=['easter_shift'], weight='w_og', hac=4, primary=True),
    'd_og':        dict(controls=['easter_shift', 'd_og_def_break'], weight='w_d_og', hac=4, primary=True),
    'd_margin_r4': dict(controls=[], weight=None, hac=8, primary=False),
    'd_og_r4':     dict(controls=['d_og_r4_break'], weight=None, hac=8, primary=False),
    'vol_proxy':   dict(controls=['easter_shift'], weight='w_og', hac=4, primary=False),
}
TARGETS = list(TARGET_SPEC)
# Base-period level for the second incremental test (y/y changes of organic growth).
BASE_LEVEL = {'d_og': 'og', 'd_og_r4': 'og_r4'}

# Sub-samples (inclusive).
INFL = (pd.Period('2021Q3', 'Q'), pd.Period('2023Q4', 'Q'))
COVID = (pd.Period('2020Q1', 'Q'), pd.Period('2021Q4', 'Q'))
EARLY_END = pd.Period('2012Q4', 'Q')
MIN_N = 30        # minimum full-sample observations for a test
MIN_N_SUB = 15    # minimum observations in a sub-sample estimate


def build_targets():
    """C.load_targets() plus the implied volume/mix proxy and a d_og_r4 break dummy."""
    T = C.load_targets()
    Fall, _ = C.load_features(core_only=False)
    cpi = Fall['w_food_cpi_xvat_yoy'].reindex(T.index)
    T['food_cpi_xvat'] = cpi
    T['vol_proxy'] = T['og'] - cpi
    # d_og_r4 (common.py) = og_r4_t - og_r4_{t-4} uses headline og_est at t-4 (no same-report
    # comparative), so it crosses a definition whenever def_id(t-j) != def_id(t-j-4) for any
    # j in 0..3 (incl. the D->E break 2022Q3-2023Q2 that d_og itself avoids).
    dd = T['def_id']
    naive_break = (dd != dd.shift(4)) & dd.shift(4).notna()
    T['d_og_r4_break'] = naive_break.astype(float).rolling(4, min_periods=1).max()
    T.loc[T['d_og_r4'].isna(), 'd_og_r4_break'] = np.nan
    return T


def hac_wls(y, X, w=None, lags=4, leverage=False):
    """WLS/OLS with Newey-West (Bartlett) HAC covariance, matching statsmodels
    fit(cov_type='HAC', cov_kwds={'maxlags': lags}) (no small-sample correction).
    leverage=True scales residuals by 1/(1-h_ii) (HC3-type) before forming the HAC scores, a
    conservative variant that stops a few high-leverage, well-fitted quarters (e.g. the 2022-23
    inflation cluster) from shrinking the standard error. X must include the constant.
    Returns (b, se, t)."""
    if w is not None:
        sw = np.sqrt(w)
        y = y * sw
        X = X * sw[:, None]
    XtX = X.T @ X
    XtX_inv = np.linalg.pinv(XtX)
    b = XtX_inv @ (X.T @ y)
    e = y - X @ b
    if leverage:
        h = np.einsum('ij,jk,ik->i', X, XtX_inv, X)
        e = e / np.clip(1.0 - h, 0.05, None)
    u = X * e[:, None]
    S = u.T @ u
    n = len(y)
    for j in range(1, min(lags, n - 1) + 1):
        wj = 1.0 - j / (lags + 1.0)
        G = u[j:].T @ u[:-j]
        S += wj * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.clip(np.diag(V), 0, None))
    with np.errstate(divide='ignore', invalid='ignore'):
        t = b / se
    return b, se, t


def _fit(y, x, Z, w, lags, min_n, extra=False):
    """Regress y on [1, x, Z] (drop constant control columns). Returns (b_x, t_x, n, df);
    with extra=True also returns the leverage-adjusted HAC t and the classical (iid) t."""
    n = len(y)
    if n < min_n or np.nanstd(x) == 0:
        return (np.nan, np.nan, n, np.nan, np.nan, np.nan) if extra else (np.nan, np.nan, n, np.nan)
    cols = [np.ones(n), x]
    if Z is not None and Z.shape[1] > 0:
        for j in range(Z.shape[1]):
            z = Z[:, j]
            if np.std(z) > 0:
                cols.append(z)
    Xm = np.column_stack(cols)
    if np.linalg.matrix_rank(Xm) < Xm.shape[1]:
        return (np.nan, np.nan, n, np.nan, np.nan, np.nan) if extra else (np.nan, np.nan, n, np.nan)
    b, se, t = hac_wls(y, Xm, w, lags)
    df = n - Xm.shape[1]
    if not extra:
        return b[1], t[1], n, df
    _, _, t_lev = hac_wls(y, Xm, w, lags, leverage=True)
    yy, XX = (y * np.sqrt(w), Xm * np.sqrt(w)[:, None]) if w is not None else (y, Xm)
    XtX_inv = np.linalg.pinv(XX.T @ XX)
    e = yy - XX @ (XtX_inv @ XX.T @ yy)
    s2 = (e @ e) / df
    t_cls = b[1] / np.sqrt(s2 * XtX_inv[1, 1])
    return b[1], t[1], n, df, t_lev[1], t_cls


def pval(t, df):
    if not np.isfinite(t) or not np.isfinite(df) or df <= 0:
        return np.nan
    return 2 * stats.t.sf(abs(t), df)


def spearman(a, b):
    ra = stats.rankdata(a)
    rb = stats.rankdata(b)
    return np.corrcoef(ra, rb)[0, 1]


def prepare_target(T, target, L):
    spec = TARGET_SPEC[target]
    y = T[target]
    Z = T[spec['controls']] if spec['controls'] else pd.DataFrame(index=T.index)
    w = T[spec['weight']] if spec['weight'] else pd.Series(1.0, index=T.index)
    ylag = y.shift(L)
    return y, Z, w, ylag


def screen(F, D, T, targets=TARGETS, alignments=ALIGNMENTS, family='core', verbose=True):
    """Univariate screen. Returns one row per (target, alignment, feature)."""
    per = T.index
    early = np.asarray(per <= EARLY_END)
    late = ~early
    exinfl = np.asarray(~((per >= INFL[0]) & (per <= INFL[1])))
    excovid = np.asarray(~((per >= COVID[0]) & (per <= COVID[1])))
    rows = []
    aligned = {a: C.align(F, D, mode=m, h=h).reindex(per) for a, (m, h) in alignments.items()}
    for target in targets:
        spec = TARGET_SPEC[target]
        lags = spec['hac']
        wtd = spec['weight'] is not None
        for a, (m, h) in alignments.items():
            L = max(4, h + 1)
            y, Z, w, ylag = prepare_target(T, target, L)
            Xa = aligned[a]
            base_ok = y.notna() & Z.notna().all(axis=1) & (w > 0)
            yv, Zv, wv, ylv = y.values, Z.values, w.values, ylag.values
            if target in BASE_LEVEL:
                basev = {a: T[BASE_LEVEL[target]].shift(L).values}
            for f in Xa.columns:
                x = Xa[f].values
                ok = base_ok.values & np.isfinite(x)
                n = ok.sum()
                rec = dict(target=target, alignment=a, feature=f, family=family, n=int(n))
                if n < MIN_N or np.std(x[ok]) == 0:
                    rows.append(rec)
                    continue
                yy, xx, zz = yv[ok], x[ok], Zv[ok]
                ww = wv[ok] if wtd else None
                b, t, nn, df, t_lev, t_cls = _fit(yy, xx, zz, ww, lags, MIN_N, extra=True)
                rec.update(pearson=np.corrcoef(xx, yy)[0, 1], spearman=spearman(xx, yy),
                           b=b, t=t, p=pval(t, df), t_lev=t_lev, p_lev=pval(t_lev, df), t_classical=t_cls,
                           sd_x=np.std(xx, ddof=1), sd_y=np.std(yy, ddof=1),
                           start=str(per[ok][0]), end=str(per[ok][-1]))
                rec['b_1sd'] = b * rec['sd_x']
                # incremental over own lag (real-time available)
                ok2 = ok & np.isfinite(ylv)
                if ok2.sum() >= MIN_N:
                    Z2 = np.column_stack([Zv[ok2], ylv[ok2]]) if Zv.shape[1] else ylv[ok2][:, None]
                    b2, t2, n2, df2 = _fit(yv[ok2], x[ok2], Z2, wv[ok2] if wtd else None, lags, MIN_N)
                    rec.update(b_incr=b2, t_incr=t2, p_incr=pval(t2, df2), n_incr=int(n2))
                # incremental over the base-period level (d_og: og_{t-L}; d_og_r4: og_r4_{t-L}),
                # the real-time-known base effect that dominates y/y changes in organic growth
                if target in BASE_LEVEL:
                    bl = basev[a]
                    ok3 = ok & np.isfinite(bl)
                    if ok3.sum() >= MIN_N:
                        Z3 = np.column_stack([Zv[ok3], bl[ok3]]) if Zv.shape[1] else bl[ok3][:, None]
                        b3, t3, n3, df3 = _fit(yv[ok3], x[ok3], Z3, wv[ok3] if wtd else None, lags, MIN_N)
                        rec.update(b_incr_base=b3, t_incr_base=t3, p_incr_base=pval(t3, df3))
                # sub-samples
                for nm, msk in (('early', early), ('late', late), ('exinfl', exinfl), ('excovid', excovid)):
                    okk = ok & msk
                    mn = MIN_N if nm in ('exinfl', 'excovid') else MIN_N_SUB
                    bs, ts, ns, dfs = _fit(yv[okk], x[okk], Zv[okk], wv[okk] if wtd else None, lags, mn)
                    rec[f'b_{nm}'] = bs
                    rec[f't_{nm}'] = ts
                    rec[f'n_{nm}'] = int(ns)
                    if nm == 'exinfl':
                        rec['p_exinfl'] = pval(ts, dfs)
                        if ns >= mn:
                            rec['pearson_exinfl'] = np.corrcoef(x[okk], yv[okk])[0, 1]
                rows.append(rec)
            if verbose:
                print(f'  {family} {target:12s} {a}: {len(Xa.columns)} features', flush=True)
    R = pd.DataFrame(rows)
    sgn = np.sign(R['b'])
    stab = pd.Series(True, index=R.index)
    for nm in ('early', 'late', 'exinfl'):
        stab &= np.sign(R[f'b_{nm}']) == sgn
    R['sign_stable'] = stab & R['b'].notna()
    R['n_sign_agree'] = sum((np.sign(R[f'b_{nm}']) == sgn).astype(int) for nm in ('early', 'late', 'exinfl', 'excovid'))
    return R


def adjust(R, pcol, by=('target', 'alignment'), method='fdr_by', out=None):
    from statsmodels.stats.multitest import multipletests
    out = out or f'q_{pcol}_{method}'
    R[out] = np.nan
    for _, g in R.groupby(list(by)):
        p = g[pcol].dropna()
        if len(p):
            R.loc[p.index, out] = multipletests(p.values, method=method)[1]
    return R


def add_adjustments(R):
    R = adjust(R, 'p', method='fdr_by', out='q_by')
    R = adjust(R, 'p', method='holm', out='p_holm')
    R = adjust(R, 'p_lev', method='fdr_by', out='q_by_lev')
    R = adjust(R, 'p_exinfl', method='fdr_by', out='q_by_exinfl')
    R = adjust(R, 'p_incr', method='fdr_by', out='q_by_incr')
    if 'p_incr_base' in R:
        R = adjust(R, 'p_incr_base', method='fdr_by', out='q_by_incr_base')
    R['n_tests_family'] = R.groupby(['target', 'alignment'])['p'].transform(lambda s: s.notna().sum())
    R['rank'] = R.groupby(['target', 'alignment'])['p'].rank(method='min')
    R['rank_exinfl'] = R.groupby(['target', 'alignment'])['p_exinfl'].rank(method='min')
    # 'robust': BY-significant on the HAC t AND on the leverage-adjusted HAC t, same sign in
    # 2001-12, 2013-26 and ex-2021Q3-23Q4, and significant at 5% without the inflation episode.
    R['robust'] = ((R['q_by'] < 0.10) & (R['q_by_lev'] < 0.10) & R['sign_stable']
                   & (R['p_exinfl'] < 0.05))
    return R


def lag_scan(F, D, T, targets=TARGETS, kmax=6):
    """Distributed-lag scan: X_t = feature_{t - lag_q - k}, k = 0..kmax (== realtime h=k)."""
    per = T.index
    exinfl = np.asarray(~((per >= INFL[0]) & (per <= INFL[1])))
    rows = []
    aligned = {k: C.align(F, D, mode='realtime', h=k).reindex(per) for k in range(kmax + 1)}
    for target in targets:
        spec = TARGET_SPEC[target]
        wtd = spec['weight'] is not None
        y, Z, w, _ = prepare_target(T, target, 4)
        base_ok = (y.notna() & Z.notna().all(axis=1) & (w > 0)).values
        yv, Zv, wv = y.values, Z.values, w.values
        ylags = {k: y.shift(max(4, k + 1)).values for k in range(kmax + 1)}
        if target in BASE_LEVEL:
            bases = {k: T[BASE_LEVEL[target]].shift(max(4, k + 1)).values for k in range(kmax + 1)}
        for k in range(kmax + 1):
            Xa = aligned[k]
            for f in Xa.columns:
                x = Xa[f].values
                ok = base_ok & np.isfinite(x)
                rec = dict(target=target, feature=f, k=k, n=int(ok.sum()))
                if ok.sum() >= MIN_N and np.std(x[ok]) > 0:
                    b, t, n, df, t_lev, _ = _fit(yv[ok], x[ok], Zv[ok], wv[ok] if wtd else None,
                                                 spec['hac'], MIN_N, extra=True)
                    okk = ok & exinfl
                    be, te, ne, dfe = _fit(yv[okk], x[okk], Zv[okk], wv[okk] if wtd else None, spec['hac'], MIN_N)
                    rec.update(r=np.corrcoef(x[ok], yv[ok])[0, 1], b=b, t=t, p=pval(t, df), t_lev=t_lev,
                               b_1sd=b * np.std(x[ok], ddof=1), t_exinfl=te, p_exinfl=pval(te, dfe))
                    # incremental over the real-time own lag y_{t-L}, L = max(4, k+1)
                    ylag = ylags[k]
                    ok2 = ok & np.isfinite(ylag)
                    if ok2.sum() >= MIN_N:
                        Z2 = np.column_stack([Zv[ok2], ylag[ok2]]) if Zv.shape[1] else ylag[ok2][:, None]
                        _, t2, _, _ = _fit(yv[ok2], x[ok2], Z2, wv[ok2] if wtd else None, spec['hac'], MIN_N)
                        rec['t_incr'] = t2
                    if target in BASE_LEVEL:
                        bl = bases[k]
                        ok3 = ok & np.isfinite(bl)
                        if ok3.sum() >= MIN_N:
                            Z3 = np.column_stack([Zv[ok3], bl[ok3]]) if Zv.shape[1] else bl[ok3][:, None]
                            _, t3, _, _ = _fit(yv[ok3], x[ok3], Z3, wv[ok3] if wtd else None, spec['hac'], MIN_N)
                            rec['t_incr_base'] = t3
                rows.append(rec)
    return pd.DataFrame(rows)


def validate_hac(n_checks=6, seed=0):
    """Compare hac_wls with C.nw_ols (statsmodels) on random real features."""
    T = build_targets()
    F, D = C.load_features(core_only=True)
    X = C.align(F, D, 'realtime', 1).reindex(T.index)
    rng = np.random.default_rng(seed)
    out = []
    for target in ['d_margin', 'og', 'd_og', 'd_og_r4']:
        spec = TARGET_SPEC[target]
        for f in rng.choice(X.columns, n_checks, replace=False):
            Z = T[spec['controls']]
            Xdf = pd.concat([X[f], Z], axis=1)
            wser = T[spec['weight']] if spec['weight'] else None
            r = C.nw_ols(T[target], Xdf, lags=spec['hac'], weights=wser)
            df = pd.concat([T[target].rename('_y'), Xdf], axis=1).dropna()
            if wser is not None:
                ww = wser.reindex(df.index).fillna(0)
                df = df[ww > 0]
                ww = ww[ww > 0].values
            else:
                ww = None
            Xm = np.column_stack([np.ones(len(df))] + [df[c].values for c in Xdf.columns])
            b, se, t = hac_wls(df['_y'].values, Xm, ww, spec['hac'])
            out.append(dict(target=target, feature=f, t_sm=r.tvalues[f], t_np=t[1],
                            b_sm=r.params[f], b_np=b[1]))
    V = pd.DataFrame(out)
    V['abs_diff_t'] = (V['t_sm'] - V['t_np']).abs()
    return V
