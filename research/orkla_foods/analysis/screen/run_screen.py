"""Run the univariate predictor screen (lens-screen).

Outputs (in this directory):
  hac_validation.csv        numpy HAC vs common.nw_ols (statsmodels) check
  vol_proxy_validation.csv  implied volume/mix proxy vs reported price/volume split (2022Q2+)
  screen_results_core.csv   200 core features x 6 targets x 5 alignments
  screen_results_all.csv    1,420 features x 6 targets x 5 alignments
  lag_profiles.csv          core features x 6 targets x lags k=0..6 (real-time shifted)
  lag_best.csv              best lag per (target, core feature) + BY q over the 200x7 family

Run: python3 run_screen.py   (about 1-2 minutes)
"""
import time
import numpy as np
import pandas as pd
import screen_lib as S
from screen_lib import C

OUT = S.OUTDIR


def vol_proxy_validation(T):
    Fa, _ = C.load_features(core_only=False)
    d = T[['og', 'price', 'volume_mix', 'food_cpi_xvat', 'vol_proxy']].copy()
    d['nw_food_cpi_xvat'] = Fa['nw_food_cpi_xvat_yoy'].reindex(T.index)
    d = d.loc['2022Q2':'2026Q2']
    d.index = d.index.astype(str)
    rows = []
    for start in ['2022Q2', '2022Q3']:
        e = d.loc[start:]
        rows.append(dict(sample=f'{start}-2026Q2', n=len(e),
                         corr_price_vs_w_food_cpi_xvat=e['price'].corr(e['food_cpi_xvat']),
                         corr_price_vs_nw_food_cpi_xvat=e['price'].corr(e['nw_food_cpi_xvat']),
                         corr_volmix_vs_proxy=e['volume_mix'].corr(e['vol_proxy']),
                         mae_volmix_vs_proxy=(e['volume_mix'] - e['vol_proxy']).abs().mean(),
                         mean_bias_proxy_minus_volmix=(e['vol_proxy'] - e['volume_mix']).mean()))
    return d, pd.DataFrame(rows)


def main():
    t0 = time.time()
    T = S.build_targets()

    V = S.validate_hac()
    V.to_csv(f'{OUT}/hac_validation.csv', index=False)
    print(f'HAC validation: max |t_numpy - t_statsmodels| = {V.abs_diff_t.max():.2e}')

    d, vs = vol_proxy_validation(T)
    d.to_csv(f'{OUT}/vol_proxy_series_2022on.csv')
    vs.to_csv(f'{OUT}/vol_proxy_validation.csv', index=False)
    print(vs.round(3).to_string())

    # Core family
    F, D = C.load_features(core_only=True)
    Rc = S.screen(F, D, T, family='core')
    Rc = S.add_adjustments(Rc)
    # Global BY across all core tests of all targets x alignments (more conservative family).
    Rc = S.adjust(Rc, 'p', by=('family',), method='fdr_by', out='q_by_global_core')
    prim = Rc['target'].isin([k for k, v in S.TARGET_SPEC.items() if v['primary']])
    Rc['q_by_global_primary'] = np.nan
    from statsmodels.stats.multitest import multipletests
    pp = Rc.loc[prim, 'p'].dropna()
    Rc.loc[pp.index, 'q_by_global_primary'] = multipletests(pp.values, method='fdr_by')[1]
    Rc = Rc.merge(D[['category', 'description', 'realtime_min_lag_q']], left_on='feature', right_index=True, how='left')
    Rc.to_csv(f'{OUT}/screen_results_core.csv', index=False, float_format='%.6g')
    print(f'core screen done: {len(Rc)} rows, {Rc.p.notna().sum()} tests, {time.time()-t0:.0f}s')

    # All-feature family
    Fa, Da = C.load_features(core_only=False)
    Ra = S.screen(Fa, Da, T, family='all', verbose=False)
    Ra = S.add_adjustments(Ra)
    Ra = Ra.merge(Da[['category', 'core', 'description', 'realtime_min_lag_q']], left_on='feature', right_index=True, how='left')
    Ra.to_csv(f'{OUT}/screen_results_all.csv', index=False, float_format='%.6g')
    print(f'all screen done: {len(Ra)} rows, {Ra.p.notna().sum()} tests, {time.time()-t0:.0f}s')

    # Distributed-lag scan (core)
    L = S.lag_scan(F, D, T)
    L = L.merge(D[['category']], left_on='feature', right_index=True, how='left')
    L.to_csv(f'{OUT}/lag_profiles.csv', index=False, float_format='%.6g')
    best = []
    for (tg, f), g in L.dropna(subset=['t']).groupby(['target', 'feature']):
        i = g['t'].abs().idxmax()
        prof = g.set_index('k')['t'].reindex(range(7))
        prof_ex = g.set_index('k')['t_exinfl'].reindex(range(7))
        prof_in = g.set_index('k')['t_incr'].reindex(range(7)) if 't_incr' in g else pd.Series(np.nan, index=range(7))
        best.append(dict(target=tg, feature=f, category=g['category'].iloc[0], best_k=int(g.loc[i, 'k']),
                         t_best=g.loc[i, 't'], p_best=g.loc[i, 'p'], r_best=g.loc[i, 'r'],
                         b_1sd_best=g.loc[i, 'b_1sd'], n_best=int(g.loc[i, 'n']),
                         t_lev_at_best=g.loc[i, 't_lev'], t_exinfl_at_best=g.loc[i, 't_exinfl'],
                         t_incr_at_best=g.loc[i, 't_incr'] if 't_incr' in g else np.nan,
                         t_incr_base_at_best=g.loc[i, 't_incr_base'] if 't_incr_base' in g else np.nan,
                         best_k_exinfl=int(prof_ex.abs().idxmax()) if prof_ex.notna().any() else np.nan,
                         **{f't_k{k}': prof[k] for k in range(7)},
                         **{f't_ex_k{k}': prof_ex[k] for k in range(7)},
                         **{f't_incr_k{k}': prof_in[k] for k in range(7)}))
    B = pd.DataFrame(best)
    # BY over the full family of 200 features x 7 lags per target (selection over lags is a search).
    L2 = S.adjust(L.copy(), 'p', by=('target',), method='fdr_by', out='q_by_lagfamily')
    qmap = L2.set_index(['target', 'feature', 'k'])['q_by_lagfamily']
    B['q_by_lagfamily'] = [qmap.get((r.target, r.feature, r.best_k), np.nan) for r in B.itertuples()]
    B['n_tests_lagfamily'] = B['target'].map(L2.dropna(subset=['p']).groupby('target').size())
    B = B.sort_values(['target', 'p_best'])
    B.to_csv(f'{OUT}/lag_best.csv', index=False, float_format='%.6g')
    print(f'lag scan done: {len(L)} rows, {time.time()-t0:.0f}s')


if __name__ == '__main__':
    main()
