"""Shared data loading and alignment for the Orkla Foods macro-predictor analysis.

Every analysis script should import this module so that targets, controls and
real-time feature alignment are identical across analyses:

    import sys; sys.path.insert(0, '/home/user/nordic-quality-rank/research/orkla_foods/analysis')
    import common as C
    T = C.load_targets()                 # targets + controls, PeriodIndex (quarterly)
    F, D = C.load_features(core_only=True)
    X = C.align(F, D, mode='realtime', h=1)   # feature values usable to forecast quarter t, 1 quarter ahead

Alignment conventions (quarter t = the Orkla reporting quarter being explained):
  mode='coincident'      X_t = feature_t (same calendar quarter; explanatory, NOT real-time).
  mode='realtime', h=0   nowcast at quarter end: X_t = feature_{t - lag_q}, where lag_q is the
                         feature's realtime_min_lag_q (0 if published within ~14 days of quarter end,
                         1 if within ~100 days, 2 longer, 4 for annual outcomes). Orkla reports 2-6
                         weeks after quarter end, so h=0 is information available before the report.
  mode='realtime', h>=1  forecast made at the end of quarter t-h: X_t = feature_{t - h - lag_q}.
"""
import numpy as np
import pandas as pd

ROOT = '/home/user/nordic-quality-rank/research/orkla_foods'
DATA = f'{ROOT}/data'
OUT = f'{ROOT}/analysis'

QUALITY_WEIGHT = {'A': 1.0, 'B': 0.7, 'C': 0.4}

# Primary targets.
TARGETS = {
    'd_margin': 'd_margin_yoy_pp',   # y/y change in EBIT margin, pp, same-report same-definition comparatives
    'og': 'og_est',                  # organic growth, %
    'd_og': 'd_og_yoy_pp',           # y/y change in organic growth, pp
}


def _to_period(s):
    return pd.PeriodIndex(s.astype(str), freq='Q')


def load_orkla():
    q = pd.read_csv(f'{DATA}/orkla_foods_quarterly.csv')
    q.index = _to_period(q['period'])
    return q


def load_targets():
    """Targets plus controls and observation weights, indexed by quarterly Period."""
    q = load_orkla()
    t = pd.DataFrame(index=q.index)
    t['d_margin'] = q['d_margin_yoy_pp']
    t['margin'] = q['ebit_margin_pct']
    t['og'] = q['og_est']
    t['d_og'] = q['d_og_yoy_pp']
    t['ebit_growth'] = q['ebit_growth_samedef_pct']
    t['rev_growth'] = q['rev_growth_samedef_pct']
    t['price'] = q['price_pct']
    t['volume_mix'] = q['volume_mix_pct']
    # Smoother 4-quarter versions: change in rolling-4Q margin and rolling-4Q average organic growth.
    # Rolling-4Q margin change from same-definition comparatives: sum(EBIT)/sum(rev) vs prior-year sums.
    e, r = q['ebit_nokm'], q['revenue_nokm']
    epy, rpy = q['ebit_py_samedef'], q['revenue_py_samedef']
    m4 = e.rolling(4).sum() / r.rolling(4).sum() * 100
    m4py = epy.rolling(4).sum() / rpy.rolling(4).sum() * 100
    t['d_margin_r4'] = m4 - m4py
    t['og_r4'] = q['og_est'].rolling(4).mean()
    t['d_og_r4'] = t['og_r4'] - t['og_r4'].shift(4)
    # Controls.
    t['easter_shift'] = q['easter_shift']
    t['d_easter_window_q1'] = q['d_easter_window_q1']
    t['og_easter_adjusted'] = q['og_easter_adjusted'].astype(float)
    t['d_og_def_break'] = q['d_og_def_break'].fillna(False).astype(float)
    t['covid'] = q['covid'].astype(float)
    t['ifrs16'] = q['ifrs16_transition'].astype(float)
    t['india'] = q['india_included'].astype(float)
    t['def_id'] = q['def_id']
    for d in ['A', 'B', 'C', 'D', 'E']:
        t[f'def_{d}'] = (q['def_id'] == d).astype(float)
    t['og_quality'] = q['og_quality']
    t['d_og_quality'] = q['d_og_quality']
    t['w_og'] = q['og_quality'].map(QUALITY_WEIGHT)
    t['w_d_og'] = q['d_og_quality'].map(QUALITY_WEIGHT)
    t.loc[t['d_og_def_break'] == 1, 'w_d_og'] = t.loc[t['d_og_def_break'] == 1, 'w_d_og'] * 0.5
    t['q'] = q['q']
    for k in (1, 2, 3, 4):
        t[f'q{k}'] = (q['q'] == k).astype(float)
    return t


def load_features(core_only=True):
    """Return (panel, dictionary). Panel: PeriodIndex x feature columns."""
    p = pd.read_csv(f'{DATA}/macro_panel_quarterly.csv')
    p.index = _to_period(p['period'])
    p = p.drop(columns=['period'])
    d = pd.read_csv(f'{DATA}/feature_dictionary.csv').set_index('feature_id')
    if core_only:
        keep = d.index[d['core'] == True]
        p = p[[c for c in p.columns if c in keep]]
        d = d.loc[p.columns]
    return p, d


def align(F, D, mode='realtime', h=0):
    """Shift features so that row t holds the value usable for target quarter t (see module doc)."""
    if mode == 'coincident':
        return F.copy()
    if mode != 'realtime':
        raise ValueError(mode)
    out = {}
    for c in F.columns:
        lag = int(D.loc[c, 'realtime_min_lag_q']) if c in D.index else 1
        out[c] = F[c].shift(h + lag)
    return pd.DataFrame(out, index=F.index)


def nw_ols(y, X, lags=4, weights=None):
    """OLS (or WLS) with Newey-West HAC standard errors. Returns statsmodels results (rows with NaN dropped)."""
    import statsmodels.api as sm
    df = pd.concat([y.rename('_y'), X], axis=1).dropna()
    if weights is not None:
        w = weights.reindex(df.index).fillna(0)
        df = df[w > 0]
        w = w[w > 0]
    Xc = sm.add_constant(df.drop(columns=['_y']), has_constant='add')
    if weights is None:
        m = sm.OLS(df['_y'], Xc)
    else:
        m = sm.WLS(df['_y'], Xc, weights=w)
    return m.fit(cov_type='HAC', cov_kwds={'maxlags': lags})


def clark_west(y, f_bench, f_model):
    """Clark-West (2007) MSPE-adjusted test for nested models. Returns (stat, one-sided p-value)."""
    from scipy import stats
    df = pd.concat([y, f_bench, f_model], axis=1).dropna()
    yy, fb, fm = df.iloc[:, 0], df.iloc[:, 1], df.iloc[:, 2]
    adj = (yy - fb) ** 2 - ((yy - fm) ** 2 - (fb - fm) ** 2)
    n = len(adj)
    if n < 8:
        return np.nan, np.nan
    import statsmodels.api as sm
    r = sm.OLS(adj.values, np.ones(n)).fit(cov_type='HAC', cov_kwds={'maxlags': 4})
    stat = r.tvalues[0]
    return stat, 1 - stats.norm.cdf(stat)


def oos_r2(y, f_bench, f_model):
    df = pd.concat([y, f_bench, f_model], axis=1).dropna()
    yy, fb, fm = df.iloc[:, 0], df.iloc[:, 1], df.iloc[:, 2]
    return 1 - ((yy - fm) ** 2).sum() / ((yy - fb) ** 2).sum()


if __name__ == '__main__':
    T = load_targets()
    F, D = load_features()
    print('targets', T.shape, T.index.min(), T.index.max())
    print(T[['d_margin', 'og', 'd_og', 'd_margin_r4', 'og_r4']].describe().round(2))
    print('core features', F.shape)
    X = align(F, D, 'realtime', 1)
    print('aligned', X.shape, X.index.min(), X.index.max())
