"""Stage 2: forecast combinations, OOS evaluation, multiple-testing control, LASSO selection frequency.

Inputs : forecasts_linear.pkl, forecasts_multi_<variant>.pkl, lasso_selection_raw_<variant>.csv,
         penalised_alpha_log_<variant>.csv (from run_forecasts.py)
Outputs: forecasts_all.csv.gz      every forecast incl. combinations (target, h, model, family, period, forecast, actual)
         oos_results.csv           one row per target x h x model x evaluation sample
         oos_summary.csv           benchmarks + multivariate/combination models, main samples side by side
         oos_top_univariate.csv    best univariate ARDL models per target x h (full 2010+ sample), with robustness
         lasso_selection_freq.csv  LASSO / elastic-net selection frequency over forecast origins
"""
import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import warnings
import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

import oos_lib as L

warnings.filterwarnings('ignore')

T = L.C.load_targets()
COMBO_KS = (1, 3, 5, 10, 20)

BENCH = {
    'd_margin': ['zero', 'mean', 'rw', 'ar', 'arcal', 'ar_bic'],
    'd_og': ['zero', 'mean', 'rw', 'rw_implied', 'ar', 'arcal', 'ar_bic', 'ar_oglev', 'ar_og_implied'],
    'og': ['mean', 'rw', 'srw', 'ar', 'arcal', 'ar_bic', 'ar_dog_implied'],
    'd_margin_r4': ['zero', 'mean', 'rw', 'ar', 'ar_bic'],
}
NAIVE = {'d_margin': 'zero', 'd_og': 'zero', 'og': 'mean', 'd_margin_r4': 'zero'}

SAMPLES = {
    'full2010': lambda p: p >= L.EVAL_START,
    'exinfl2010': lambda p: (p >= L.EVAL_START) & ~p.isin(L.INFL),
    'excovinfl2010': lambda p: (p >= L.EVAL_START) & ~p.isin(L.INFL) & ~p.isin(L.COVID_EVAL),
    'full2015': lambda p: p >= L.EVAL_START2,
    'exinfl2015': lambda p: (p >= L.EVAL_START2) & ~p.isin(L.INFL),
}


# ----------------------------------------------------------------------------------------------
def make_combos(W, y, h):
    """Forecast combinations of the univariate (p=1) ARDL forecasts using only past OOS performance."""
    uni = W[[c for c in W.columns if c.startswith('uni_p1__')]]
    per = uni.index
    pos = np.arange(len(per))
    yv = y.reindex(per)
    E2 = uni.sub(yv, axis=0) ** 2
    names = [f'comb_top{k}' for k in COMBO_KS] + ['comb_all_mean', 'comb_all_median', 'comb_dmspe']
    out = {k: np.full(len(per), np.nan) for k in names}
    for m, t in enumerate(per):
        known = pos <= m - (h + 1)
        f_t = uni.iloc[m]
        avail = f_t.notna()
        if avail.any():
            out['comb_all_mean'][m] = f_t[avail].mean()
            out['comb_all_median'][m] = f_t[avail].median()
        if known.sum() == 0:
            continue
        past = E2[known]
        cnt = past.notna().sum()
        elig = avail & (cnt >= 8)
        if elig.sum() == 0:
            continue
        mse = past.mean()[elig]
        order = mse.sort_values().index
        for k in COMBO_KS:
            out[f'comb_top{k}'][m] = f_t[order[:k]].mean()
        disc = 0.95 ** (m - pos[known])
        dm = (past[elig.index[elig]].mul(disc, axis=0)).sum() / (past[elig.index[elig]].notna().mul(disc, axis=0)).sum()
        wts = 1 / dm
        out['comb_dmspe'][m] = (f_t[wts.index] * wts).sum() / wts.sum()
    C = pd.DataFrame(out, index=per)
    # adaptive k: choose among the combinations by their own past OOS MSE (>= 4 past errors)
    cand = [f'comb_top{k}' for k in COMBO_KS] + ['comb_all_mean']
    E2c = C[cand].sub(yv, axis=0) ** 2
    ad = np.full(len(per), np.nan)
    chosen = []
    for m in range(len(per)):
        known = pos <= m - (h + 1)
        past = E2c[known]
        cnt = past.notna().sum()
        ok = cnt >= 4
        if ok.any():
            best = past.mean()[ok].idxmin()
        else:
            best = 'comb_all_mean'
        ad[m] = C[best].iloc[m]
        chosen.append(best)
    C['comb_adaptive'] = ad
    return C, pd.Series(chosen, index=per)


# ----------------------------------------------------------------------------------------------
def evaluate_one(y, f, B, tgt, h, base, ref_dir):
    """Metrics for one model on the index of y (already restricted to the sample)."""
    df = pd.concat({'y': y, 'f': f, 'base': B[base]}, axis=1).dropna()
    r = {'n': len(df)}
    if len(df) < 8:
        return r
    idx = df.index
    yy, ff, fb = df['y'].values, df['f'].values, df['base'].values
    sse = np.sum((yy - ff) ** 2)
    r['rmse'] = np.sqrt(sse / len(yy))
    r['rmse_base'] = np.sqrt(np.mean((yy - fb) ** 2))
    r['rmse_ratio_base'] = r['rmse'] / r['rmse_base']
    best_b, best_sse = None, np.inf
    for b in BENCH[tgt]:
        bb = B[b].reindex(idx)
        if bb.isna().any():
            r[f'r2_vs_{b}'] = np.nan
            continue
        sse_b = np.sum((yy - bb.values) ** 2)
        r[f'r2_vs_{b}'] = 1 - sse / sse_b if sse_b > 0 else np.nan
        if sse_b < best_sse:
            best_b, best_sse = b, sse_b
    r['best_bench'] = best_b
    r['r2_vs_best_bench'] = 1 - sse / best_sse
    r['rmse_ratio_best_bench'] = np.sqrt(sse / best_sse)
    r['rmse_ratio_ar'] = np.sqrt(sse / np.sum((yy - B['ar'].reindex(idx).values) ** 2))
    r['cw_stat_base'], r['cw_p_base'] = L.clark_west(yy, fb, ff)
    r['dm_stat_base'], r['dm_p_base'] = L.diebold_mariano(yy, fb, ff)
    bb = B[best_b].reindex(idx).values
    r['cw_p_best_bench'] = L.clark_west(yy, bb, ff)[1]
    r['dm_p_best_bench'] = L.diebold_mariano(yy, bb, ff)[1]
    for b in ('ar', NAIVE[tgt], 'rw'):
        bb = B[b].reindex(idx).values
        r[f'cw_p_{b}'] = L.clark_west(yy, bb, ff)[1] if np.isfinite(bb).all() else np.nan
    # directional accuracy (sign of the y/y change; for og: change vs the last reported og)
    if ref_dir is None:
        a, s_ = yy, ff
        r['hit_rate_base'] = np.mean((yy > 0) == (fb > 0))
    else:
        rr = ref_dir.reindex(idx).values
        a, s_ = yy - rr, ff - rr
        r['hit_rate_base'] = np.mean(((yy - rr) > 0) == ((fb - rr) > 0))
    r['hit_rate'], r['pt_p'] = L.pesaran_timmermann(a, s_)
    return r


def load_forecasts():
    import glob
    parts = [pd.read_pickle(f'{L.OUT}/forecasts_linear.pkl')]
    parts += [pd.read_pickle(f) for f in sorted(glob.glob(f'{L.OUT}/forecasts_multi_*.pkl'))]
    fc = pd.concat(parts, ignore_index=True)
    fc['period'] = pd.PeriodIndex(fc['period'], freq='Q')
    return fc[fc['family'] != 'check']


def main():
    fc = load_forecasts()
    rows, all_fc, chosen_k = [], [], []
    for tgt in L.TARGETS:
        y = T[tgt]
        for h in L.HS:
            sub_b = fc[(fc.target == tgt) & (fc.h == h) & (fc.variant == 'bench')]
            Bw = sub_b.pivot(index='period', columns='model', values='forecast')
            rd = (T['og'].shift(h + 1)) if tgt == 'og' else None
            for var in ['bench'] + L.VARIANTS[tgt]:
                if var == 'bench':
                    W = Bw.copy()
                    fam = pd.Series('benchmark', index=W.columns)
                    base = L.BASE_NAME[tgt]
                else:
                    sub = fc[(fc.target == tgt) & (fc.h == h) & (fc.variant == var)]
                    W = sub.pivot(index='period', columns='model', values='forecast')
                    fam = sub.drop_duplicates('model').set_index('model')['family']
                    Cmb, ch = make_combos(W, y, h)
                    chosen_k.append(pd.DataFrame({'target': tgt, 'h': h, 'variant': var,
                                                  'period': ch.index.astype(str), 'chosen': ch.values}))
                    W = pd.concat([W, Cmb], axis=1)
                    fam = pd.concat([fam, pd.Series('combination', index=Cmb.columns)])
                    base = L.BASE_BENCH[var]
                long = W.rename_axis(index='period', columns='model').reset_index() \
                    .melt(id_vars='period', var_name='model', value_name='forecast')
                long['target'], long['h'], long['variant'] = tgt, h, var
                long['family'] = long['model'].map(fam)
                long['actual'] = long['period'].map(y)
                all_fc.append(long)
                B = Bw.reindex(W.index)
                for sname, sel in SAMPLES.items():
                    per = W.index[sel(W.index) & (W.index <= L.LAST)]
                    per = per[per >= L.EVAL_START]
                    yy = y.reindex(per).dropna()
                    for mname in W.columns:
                        r = evaluate_one(yy, W[mname].reindex(yy.index), B, tgt, h, base, rd)
                        r.update({'target': tgt, 'h': h, 'variant': var, 'model': mname, 'family': fam[mname],
                                  'sample': sname, 'base': base})
                        rows.append(r)
            print('evaluated', tgt, h, flush=True)
    R = pd.DataFrame(rows)
    R['primary'] = [(v == L.PRIMARY[t]) or v == 'bench' for t, v in zip(R.target, R.variant)]
    R['feature'] = R['model'].str.extract(r'uni_p\d__(.*)')[0]
    R['lags'] = R['model'].str.extract(r'uni_p(\d)__')[0]
    nmax = R.groupby(['target', 'h', 'sample'])['n'].transform('max')
    R['short_sample'] = R['n'] < 0.9 * nmax

    # ---- multiple-testing control on Clark-West p-values vs the nested base
    R['test_family'] = np.where(R['family'] == 'univariate', 'univariate',
                                np.where(R['family'] == 'benchmark', 'benchmark', 'multivariate'))
    for c in ['cw_p_base_holm_fam', 'cw_p_base_by_fam', 'n_tests_fam', 'cw_p_base_holm_global',
              'cw_p_base_by_global', 'n_tests_global']:
        R[c] = np.nan
    for (tf, var_, s), g in R[R.test_family != 'benchmark'].groupby(['test_family', 'variant', 'sample']):
        gg = g[g['cw_p_base'].notna()]
        for (tg, hh), g2 in gg.groupby(['target', 'h']):
            R.loc[g2.index, 'cw_p_base_holm_fam'] = multipletests(g2['cw_p_base'], method='holm')[1]
            R.loc[g2.index, 'cw_p_base_by_fam'] = multipletests(g2['cw_p_base'], method='fdr_by')[1]
            R.loc[g2.index, 'n_tests_fam'] = len(g2)
    # global family: all primary-variant tests of the same type across the 4 targets x 3 horizons
    for (tf, s), g in R[(R.test_family != 'benchmark') & R.primary].groupby(['test_family', 'sample']):
        gg = g[g['cw_p_base'].notna()]
        R.loc[gg.index, 'cw_p_base_holm_global'] = multipletests(gg['cw_p_base'], method='holm')[1]
        R.loc[gg.index, 'cw_p_base_by_global'] = multipletests(gg['cw_p_base'], method='fdr_by')[1]
        R.loc[gg.index, 'n_tests_global'] = len(gg)

    lead = ['target', 'h', 'variant', 'primary', 'sample', 'family', 'model', 'feature', 'lags', 'base', 'n',
            'short_sample', 'rmse', 'rmse_base', 'rmse_ratio_base', 'rmse_ratio_ar', 'best_bench',
            'rmse_ratio_best_bench', 'r2_vs_best_bench']
    r2c = [c for c in R.columns if c.startswith('r2_vs_') and c not in lead]
    rest = [c for c in R.columns if c not in lead + r2c + ['test_family']]
    R = R[lead + r2c + rest + ['test_family']]
    R.to_csv(f'{L.OUT}/oos_results.csv', index=False, float_format='%.5g')

    pd.concat(all_fc, ignore_index=True).assign(period=lambda d: d['period'].astype(str)) \
        .to_csv(f'{L.OUT}/forecasts_all.csv.gz', index=False, float_format='%.5g')
    pd.concat(chosen_k).to_csv(f'{L.OUT}/combination_adaptive_choice.csv', index=False)

    # ---- summary tables
    keep_s = ['full2010', 'exinfl2010', 'excovinfl2010', 'full2015', 'exinfl2015']
    S = R[(R.family != 'univariate')].copy()
    cols = ['rmse', 'rmse_ratio_base', 'rmse_ratio_best_bench', 'r2_vs_best_bench', 'cw_p_base', 'cw_p_base_by_fam',
            'dm_p_best_bench', 'hit_rate', 'pt_p', 'n']
    piv = S.pivot_table(index=['target', 'h', 'variant', 'family', 'model'], columns='sample', values=cols)
    piv = piv.reindex(columns=keep_s, level=1)
    piv.columns = [f'{a}__{b}' for a, b in piv.columns]
    piv.reset_index().to_csv(f'{L.OUT}/oos_summary.csv', index=False, float_format='%.4g')

    U = R[(R.family == 'univariate') & (R['sample'] == 'full2010') & (~R.short_sample) & R.primary].copy()
    U = U.sort_values(['target', 'h', 'rmse_ratio_base'])
    top = U.groupby(['target', 'h']).head(15).copy()
    rob = R[(R.family == 'univariate')].set_index(['target', 'h', 'variant', 'model', 'sample'])
    for s in ['exinfl2010', 'excovinfl2010', 'full2015', 'exinfl2015']:
        key = list(zip(top.target, top.h, top.variant, top.model, [s] * len(top)))
        top[f'rmse_ratio_base__{s}'] = rob.loc[key, 'rmse_ratio_base'].values
        top[f'cw_p_base__{s}'] = rob.loc[key, 'cw_p_base'].values
    top.to_csv(f'{L.OUT}/oos_top_univariate.csv', index=False, float_format='%.4g')

    # ---- LASSO / EN selection frequency
    import glob
    sel = pd.concat([pd.read_csv(f) for f in glob.glob(f'{L.OUT}/lasso_selection_raw_*.csv')], ignore_index=True)
    alog = pd.concat([pd.read_csv(f) for f in glob.glob(f'{L.OUT}/penalised_alpha_log_*.csv')], ignore_index=True)
    sel['period'] = pd.PeriodIndex(sel['period'], freq='Q')
    alog['period'] = pd.PeriodIndex(alog['period'], freq='Q')
    blocks = {'2010_14': ('2010Q1', '2014Q4'), '2015_19': ('2015Q1', '2019Q4'), '2020_26': ('2020Q1', '2026Q2')}
    out = []
    for (tgt, h, var, meth), g in sel.groupby(['target', 'h', 'variant', 'method']):
        al = alog[(alog.target == tgt) & (alog.h == h) & (alog.variant == var) & (alog.method == meth)]
        n_or = len(al)
        for f, gf in g.groupby('feature'):
            r = {'target': tgt, 'h': h, 'variant': var, 'primary': var == L.PRIMARY[tgt], 'method': meth,
                 'feature': f, 'n_origins': n_or, 'n_selected': len(gf), 'sel_freq': len(gf) / n_or,
                 'share_positive': (gf['coef'] > 0).mean(), 'mean_coef_std': gf['coef_std'].mean(),
                 'first_selected': str(gf['period'].min()), 'last_selected': str(gf['period'].max())}
            for b, (a0, a1) in blocks.items():
                na = ((al.period >= pd.Period(a0, 'Q')) & (al.period <= pd.Period(a1, 'Q'))).sum()
                ns = ((gf.period >= pd.Period(a0, 'Q')) & (gf.period <= pd.Period(a1, 'Q'))).sum()
                r[f'sel_freq_{b}'] = ns / na if na else np.nan
            out.append(r)
    SF = pd.DataFrame(out).sort_values(['target', 'h', 'variant', 'method', 'sel_freq'],
                                       ascending=[True, True, True, True, False])
    avg_sel = alog.groupby(['target', 'h', 'variant', 'method'])['n_selected'].mean() \
        .rename('avg_n_selected_per_origin')
    SF = SF.merge(avg_sel.reset_index(), on=['target', 'h', 'variant', 'method'], how='left')
    SF.to_csv(f'{L.OUT}/lasso_selection_freq.csv', index=False, float_format='%.4g')
    print('done', R.shape)


if __name__ == '__main__':
    main()
