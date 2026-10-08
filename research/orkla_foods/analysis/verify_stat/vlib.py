"""Independent statistical-validity checks (lens: sceptic-stat).

Fresh code. Only common.py alignment / loading is reused. Everything else (HAC with proper
handling of gaps, placebo calibration, circular-shift nulls, block bootstrap, OOS engine)
is re-implemented here.
"""
import sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, '/home/user/nordic-quality-rank/research/orkla_foods/analysis')
import common as C  # noqa: E402

OUT = '/home/user/nordic-quality-rank/research/orkla_foods/analysis/verify_stat'
EPI = (pd.Period('2021Q3', 'Q'), pd.Period('2023Q4', 'Q'))
COVID = (pd.Period('2020Q1', 'Q'), pd.Period('2021Q4', 'Q'))

# Target specs (follow the screen lens): controls, weight column
SPEC = {
    'd_margin': dict(controls=[], w=None),
    'og': dict(controls=['easter_shift'], w='w_og'),
    'd_og': dict(controls=['easter_shift', 'd_og_def_break'], w='w_d_og'),
    'vol_proxy': dict(controls=['easter_shift'], w='w_og'),
}


def load():
    T = C.load_targets()
    F, D = C.load_features(core_only=False)
    F = F.copy()
    raw = 0.5 * F['eu_agri_basket_wloc_yoy'] + 0.5 * F['fao_ffpi_wloc_yoy']
    F['raw_mat_wloc_yoy'] = raw
    elec = 0.25 * F['elec_nordic_loc_yoy'].clip(-100, 100)
    F['cost_idx_calib_yoy'] = (0.40 * raw + 0.08 * F['packaging_eu_yoy'] + 0.02 * elec + 0.20 * F['w_wage_yoy']) / 0.70
    F['w_food_rel_xvat_yoy'] = F['w_food_cpi_xvat_yoy'] - F['w_cpi_yoy']
    for nm, comps in [('raw_mat_wloc_yoy', ['eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy']),
                      ('cost_idx_calib_yoy', ['eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy', 'packaging_eu_yoy',
                                              'elec_nordic_loc_yoy', 'w_wage_yoy']),
                      ('w_food_rel_xvat_yoy', ['w_food_cpi_xvat_yoy', 'w_cpi_yoy'])]:
        D.loc[nm, 'realtime_min_lag_q'] = max(D.loc[c, 'realtime_min_lag_q'] for c in comps)
        D.loc[nm, 'core'] = False
    T['vol_proxy'] = T['og'] - F['w_food_cpi_xvat_yoy'].reindex(T.index)
    return T, F, D


def X_at(F, D, mode='coincident', h=0, idx=None):
    X = C.align(F, D, mode, h)
    return X.reindex(idx) if idx is not None else X


def mask_period(idx, a, b):
    return np.asarray((idx >= pd.Period(a, 'Q')) & (idx <= pd.Period(b, 'Q')))


def sample_mask(T, name):
    idx = T.index
    m = np.ones(len(idx), bool)
    for part in name.split('+'):
        if part == 'full':
            continue
        elif part == 'exepi':
            m &= ~mask_period(idx, '2021Q3', '2023Q4')
        elif part == 'excovid':
            m &= ~mask_period(idx, '2020Q1', '2021Q4')
        elif part == 'exbreak':
            # first four quarters after each definition change + India-flag 2007Q2-Q4 + d_og break flag
            brk = np.zeros(len(idx), bool)
            dd = T['def_id'].values
            for i in range(1, len(idx)):
                if dd[i] != dd[i - 1]:
                    brk[i:i + 4] = True
            brk |= mask_period(idx, '2007Q2', '2007Q4')
            brk |= (T['d_og_def_break'].values == 1)
            m &= ~brk
        elif part == 'execho':
            # quarters whose 5-7 quarter lags fall inside the 2021Q3-2023Q4 episode
            m &= ~mask_period(idx, '2022Q4', '2025Q3')
        elif part == 'ex0709':
            m &= ~mask_period(idx, '2007Q1', '2009Q4')
        elif part == 'pre2020':
            m &= mask_period(idx, '2000Q1', '2019Q4')
        elif part == 'post2008':
            m &= mask_period(idx, '2008Q1', '2026Q4')
        else:
            raise ValueError(part)
    return m


# ------------------------------------------------------------------ HAC regression (gap-aware)
def _nw(S, pos, L):
    """S: n x k scores, pos: integer time positions (strictly increasing). Bartlett kernel; pairs are
    matched by true time distance, so a gap is not treated as adjacency."""
    O = S.T @ S
    if L <= 0:
        return O
    grid = np.zeros((pos[-1] - pos[0] + 1, S.shape[1]))
    grid[pos - pos[0]] = S
    for l in range(1, L + 1):
        w = 1 - l / (L + 1)
        G = grid[l:].T @ grid[:-l]
        O += w * (G + G.T)
    return O


def hac_fit(y, X, w=None, L=4, gap_aware=True, names=None):
    """y: Series (PeriodIndex); X: DataFrame. Returns dict(b, se, t, n, df, p, resid, cols).
    Drops rows with NaN, zero weight; drops columns constant in the sample (except the constant)."""
    df = pd.concat([y.rename('_y'), X], axis=1)
    if w is not None:
        df['_w'] = w.reindex(df.index)
    df = df.dropna()
    if w is not None:
        df = df[df['_w'] > 0]
        ww = df['_w'].values
    else:
        ww = np.ones(len(df))
    cols = [c for c in X.columns if df[c].std() > 1e-10]
    Xm = np.column_stack([np.ones(len(df))] + [df[c].values for c in cols])
    yv = df['_y'].values
    sw = np.sqrt(ww)
    Xw, yw = Xm * sw[:, None], yv * sw
    XtX_inv = np.linalg.pinv(Xw.T @ Xw)
    b = XtX_inv @ Xw.T @ yw
    e = yw - Xw @ b
    S = Xw * e[:, None]
    idx = df.index
    if gap_aware:
        pos = np.array([(p - idx[0]).n for p in idx])
    else:
        pos = np.arange(len(idx))
    O = _nw(S, pos, L)
    V = XtX_inv @ O @ XtX_inv
    se = np.sqrt(np.clip(np.diag(V), 0, None))
    t = b / se
    n, k = Xm.shape
    names = ['const'] + cols
    out = dict(b=pd.Series(b, names), se=pd.Series(se, names), t=pd.Series(t, names), n=n, df=n - k,
               resid=pd.Series(e / sw, idx), V=pd.DataFrame(V, names, names), idx=idx,
               r2=1 - ((e) ** 2).sum() / ((yw - np.average(yv, weights=ww) * sw) ** 2).sum())
    return out


def design(T, target, x, extra_controls=None, sample='full', weighted=True):
    spec = SPEC[target]
    y = T[target].where(sample_mask(T, sample))
    ctr = list(spec['controls']) + (extra_controls or [])
    Z = T[ctr].astype(float) if ctr else pd.DataFrame(index=T.index)
    w = T[spec['w']] if (spec['w'] and weighted) else None
    if isinstance(x, pd.Series):
        X = pd.concat([x.rename('x'), Z], axis=1)
    else:
        X = pd.concat([x, Z], axis=1)
    return y, X, w


def fit_one(T, target, x, L=4, sample='full', weighted=True, extra_controls=None, gap_aware=True):
    y, X, w = design(T, target, x.reindex(T.index), extra_controls, sample, weighted)
    r = hac_fit(y, X, w, L, gap_aware)
    return r


# ------------------------------------------------------------------ placebo calibration
def ar_fit(x, p=2):
    x = pd.Series(x).dropna().values
    Y = x[p:]
    Xl = np.column_stack([np.ones(len(Y))] + [x[p - j:-j] for j in range(1, p + 1)])
    c = np.linalg.lstsq(Xl, Y, rcond=None)[0]
    phi = c[1:]
    # enforce stationarity by shrinking if needed
    for _ in range(50):
        roots = np.roots(np.r_[1, -phi])
        if np.all(np.abs(roots) < 0.995):
            break
        phi = phi * 0.98
    return phi


def ar_sim(phi, n, nsim, rng, burn=200):
    p = len(phi)
    e = rng.standard_normal((n + burn, nsim))
    x = np.zeros((n + burn, nsim))
    for t in range(p, n + burn):
        acc = e[t].copy()
        for j in range(p):
            acc += phi[j] * x[t - 1 - j]
        x[t] = acc
    return x[burn:]


def placebo_t(T, target, x, nsim=2000, L=4, sample='full', weighted=True, extra_controls=None, p=2, seed=0,
              phi=None, F_source=None):
    """Distribution of |t| when x is replaced by AR(p) placebos with x's persistence and missing pattern.
    Vectorised FWL: residualise y and placebo on [1, controls] with weights; HAC on scores (gap-aware)."""
    rng = np.random.default_rng(seed)
    xs = x.reindex(T.index)
    y, X, w = design(T, target, xs, extra_controls, sample, weighted)
    df = pd.concat([y.rename('_y'), X], axis=1)
    if w is not None:
        df['_w'] = w
    df = df.dropna()
    if w is not None:
        df = df[df['_w'] > 0]
    ww = df['_w'].values if w is not None else np.ones(len(df))
    Zc = [c for c in X.columns if c != 'x' and df[c].std() > 1e-10]
    Z = np.column_stack([np.ones(len(df))] + [df[c].values for c in Zc])
    sw = np.sqrt(ww)
    Zw = Z * sw[:, None]
    P = Zw @ np.linalg.pinv(Zw.T @ Zw) @ Zw.T
    yw = df['_y'].values * sw
    ytil = yw - P @ yw
    idx = df.index
    pos = np.array([(q - T.index[0]).n for q in idx])
    if phi is None:
        src = F_source if F_source is not None else x
        phi = ar_fit(src, p)
    n_all = len(T.index)
    sims = ar_sim(phi, n_all, nsim, rng)[pos]  # n x nsim on the estimation rows
    Xw = sims * sw[:, None]
    xtil = Xw - P @ Xw
    sxx = (xtil ** 2).sum(0)
    b = (xtil * ytil[:, None]).sum(0) / sxx
    e = ytil[:, None] - xtil * b[None, :]
    S = xtil * e
    grid = np.zeros((pos[-1] - pos[0] + 1, nsim))
    grid[pos - pos[0]] = S
    O = (grid ** 2).sum(0)
    for l in range(1, L + 1):
        O += 2 * (1 - l / (L + 1)) * (grid[l:] * grid[:-l]).sum(0)
    t = b / np.sqrt(O / sxx ** 2)
    # observed
    r = hac_fit(y, X, w, L)
    t_obs = r['t']['x']
    tabs = np.abs(t)
    return dict(t_obs=t_obs, b=r['b']['x'], n=r['n'], q95=np.quantile(tabs, 0.95), q99=np.quantile(tabs, 0.99),
                size5=(tabs > stats.t.ppf(0.975, r['df'])).mean(),
                p_emp=(np.sum(tabs >= abs(t_obs)) + 1) / (nsim + 1),
                p_cal=2 * (1 - stats.norm.cdf(abs(t_obs) * 1.959964 / np.quantile(tabs, 0.95))), phi=phi)


# ------------------------------------------------------------------ circular-shift null
def circ_shift_t(T, target, x, L=4, minshift=8, weighted=True, sample='full'):
    """Shift the target block (y, controls, weights) circularly within its valid span relative to x.
    Returns observed t and array of shifted t (one per admissible shift)."""
    spec = SPEC[target]
    m = sample_mask(T, sample)
    cols = [target] + list(spec['controls']) + ([spec['w']] if spec['w'] else [])
    B = T[cols].copy()
    B.loc[~m, target] = np.nan
    valid = B[target].notna() & B.notna().all(axis=1)
    first, last = valid.idxmax(), valid[::-1].idxmax()
    span = (T.index >= first) & (T.index <= last)
    Bs = B[span]
    n = len(Bs)
    xs = x.reindex(T.index)[span]
    out = []
    for s in range(minshift, n - minshift + 1):
        Br = pd.DataFrame(np.roll(Bs.values, s, axis=0), index=Bs.index, columns=Bs.columns)
        y = Br[target]
        Z = Br[list(spec['controls'])].astype(float) if spec['controls'] else pd.DataFrame(index=Br.index)
        w = Br[spec['w']] if (spec['w'] and weighted) else None
        r = hac_fit(y, pd.concat([xs.rename('x'), Z], axis=1), w, L)
        out.append(r['t'].get('x', np.nan))
    y = Bs[target]
    Z = Bs[list(spec['controls'])].astype(float) if spec['controls'] else pd.DataFrame(index=Bs.index)
    w = Bs[spec['w']] if (spec['w'] and weighted) else None
    t_obs = hac_fit(y, pd.concat([xs.rename('x'), Z], axis=1), w, L)['t']['x']
    out = np.array(out)
    return t_obs, out


# ------------------------------------------------------------------ block bootstrap
def mbb_coef(y, X, w=None, nboot=2000, block=8, seed=0, coef='x'):
    """Moving-block bootstrap (rows resampled in blocks of consecutive quarters) of an OLS/WLS coefficient."""
    rng = np.random.default_rng(seed)
    df = pd.concat([y.rename('_y'), X], axis=1)
    if w is not None:
        df['_w'] = w.reindex(df.index)
    df = df.dropna()
    if w is not None:
        df = df[df['_w'] > 0]
    n = len(df)
    cols = [c for c in X.columns if df[c].std() > 1e-10]
    j = cols.index(coef) + 1
    A = np.column_stack([np.ones(n)] + [df[c].values for c in cols])
    yv = df['_y'].values
    ww = df['_w'].values if w is not None else np.ones(n)
    nb = int(np.ceil(n / block))
    bs = []
    for _ in range(nboot):
        starts = rng.integers(0, n - block + 1, nb)
        ii = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        Aw = A[ii] * np.sqrt(ww[ii])[:, None]
        bb = np.linalg.lstsq(Aw, yv[ii] * np.sqrt(ww[ii]), rcond=None)[0]
        bs.append(bb[j])
    bs = np.array(bs)
    Aw = A * np.sqrt(ww)[:, None]
    b0 = np.linalg.lstsq(Aw, yv * np.sqrt(ww), rcond=None)[0][j]
    se = bs.std(ddof=1)
    return dict(b=b0, se_boot=se, t_boot=b0 / se, ci=(np.quantile(bs, 0.025), np.quantile(bs, 0.975)),
                p_boot=2 * min((bs <= 0).mean(), (bs >= 0).mean()))


# ------------------------------------------------------------------ OOS engine
def oos_forecasts(y, Zbase, Zx, w, idx, eval_start='2010Q1', h=0, train_excl=('2020Q1', '2021Q2'),
                  min_train=12, train_start=None):
    """Expanding window. At target t (position i) the model is fit on rows s <= i-h-1 with all regressors
    observed. Returns (bench_fc, model_fc) Series over eval positions."""
    yv = y.values.astype(float)
    wv = w.values.astype(float) if w is not None else np.ones(len(yv))
    excl = mask_period(idx, *train_excl)
    if train_start is not None:
        excl |= np.asarray(idx < pd.Period(train_start, 'Q'))
    A0 = np.column_stack([np.ones(len(yv)), Zbase.values]) if Zbase.shape[1] else np.ones((len(yv), 1))
    A1 = np.column_stack([A0, Zx.values])
    pos = [i for i, p in enumerate(idx) if p >= pd.Period(eval_start, 'Q') and np.isfinite(yv[i])]
    fb, fm = [], []
    valid_all = np.isfinite(yv) & np.isfinite(A1).all(1) & (wv > 0) & ~excl
    for i in pos:
        tr = valid_all.copy()
        tr[i - h:] = False
        tr[max(0, i - h):] = False
        out = []
        for A in (A0, A1):
            if tr.sum() < max(min_train, A.shape[1] + 6) or not np.isfinite(A[i]).all():
                out.append(np.nan)
                continue
            sw = np.sqrt(wv[tr])
            bb = np.linalg.lstsq(A[tr] * sw[:, None], yv[tr] * sw, rcond=None)[0]
            out.append(A[i] @ bb)
        fb.append(out[0])
        fm.append(out[1])
    ix = idx[pos]
    return pd.Series(fb, ix), pd.Series(fm, ix), pd.Series(yv[pos], ix)


def cw_test(y, fb, fm, L=4):
    df = pd.concat([y, fb, fm], axis=1).dropna()
    yy, b, m = df.iloc[:, 0].values, df.iloc[:, 1].values, df.iloc[:, 2].values
    adj = (yy - b) ** 2 - ((yy - m) ** 2 - (b - m) ** 2)
    n = len(adj)
    mu = adj.mean()
    u = adj - mu
    pos = np.array([(p - df.index[0]).n for p in df.index])
    O = _nw(u[:, None], pos, L)[0, 0] / n
    t = mu / np.sqrt(O / n)
    return t, 1 - stats.norm.cdf(t), n


def oos_summary(y, fb, fm, idx_mask=None):
    df = pd.concat([y.rename('y'), fb.rename('b'), fm.rename('m')], axis=1).dropna()
    if idx_mask is not None:
        df = df[idx_mask.reindex(df.index).fillna(False).values]
    rb = np.sqrt(((df.y - df.b) ** 2).mean())
    rm = np.sqrt(((df.y - df.m) ** 2).mean())
    t, p, n = cw_test(df.y, df.b, df.m)
    return dict(n=len(df), rmse_b=rb, rmse_m=rm, ratio=rm / rb, r2_vs_b=1 - (rm / rb) ** 2, cw_t=t, cw_p=p)


def by_adjust(p):
    from statsmodels.stats.multitest import multipletests
    p = np.asarray(p, float)
    out = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    if ok.sum():
        out[ok] = multipletests(p[ok], method='fdr_by')[1]
    return out
