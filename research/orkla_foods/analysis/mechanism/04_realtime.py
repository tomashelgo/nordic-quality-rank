"""Section 4: real-time predictive value of the mechanism models (lens-mechanism).

All features are aligned with C.align(mode='realtime', h): row t holds information available at the
end of quarter t-h (h=0: nowcast after quarter end, before Orkla's report). Extra distributed lags are
added on top of the aligned feature (.shift(k)). Targets known at forecast time: up to t-h-1.

Pseudo out-of-sample, expanding window, first forecast 2010Q1 (training from 2002/2003). Benchmarks:
prevailing mean and an AR model on the last reported value (y_{t-h-1}). Statistics: OOS R^2 vs each
benchmark (C.oos_r2) and the Clark-West test vs the AR benchmark (nested), on all OOS quarters and
excluding the 2021Q3-2023Q4 episode. Easter calendar control is included (known in advance); the
COVID dummy is not (not known in real time).

Outputs: rt_oos.csv, rt_insample.csv, fig_rt_oos.png
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import mech_utils as M

C = M.C
T, F, D, X = M.load_all()
START = pd.Period('2010Q1', 'Q')
EPI = M.mask(T, 'ex_infl')


def design(spec, h):
    """Return DataFrame of regressors (index = T.index) for a model spec at horizon h."""
    cols = {}
    for kind, feat, arg in spec:
        Xa = C.align(F[[feat]], D.loc[[feat]], mode='realtime', h=h)[feat]
        if kind == 'pdl':                     # Almon PDL quadratic over lags 0..arg of the aligned feature
            Z, _ = M.pdl_regressors(Xa, arg, 2, feat)
            for c in Z:
                cols[c] = Z[c]
        elif kind == 'avg':                   # moving average over aligned lags arg=(a,b)
            a, b = arg
            cols[f'{feat}_avg{a}_{b}'] = Xa.shift(a).rolling(b - a + 1).mean()
        elif kind == 'accel':                 # avg of aligned lags 0-3 minus avg of lags 4-7
            cols[f'{feat}_accel'] = Xa.rolling(4).mean() - Xa.shift(4).rolling(4).mean()
        elif kind == 'lvl':
            cols[f'{feat}_L{arg}'] = Xa.shift(arg)
    return pd.DataFrame(cols).reindex(T.index)


def oos_run(target, spec, h, ar=True, ctrl=('d_easter_window_q1',), min_train=28):
    y = T[target]
    Xm = design(spec, h) if spec else pd.DataFrame(index=T.index)
    if ar:
        Xm['ar'] = y.shift(h + 1)
    for c in ctrl:
        Xm[c] = T[c]
    preds = {}
    for t in T.index[T.index >= START]:
        if pd.isna(y.get(t)):
            continue
        tr = T.index[T.index <= t - h - 1]
        dtr = pd.concat([y.reindex(tr).rename('_y'), Xm.reindex(tr)], axis=1).dropna()
        if len(dtr) < min_train or Xm.loc[t].isna().any():
            continue
        keep = [c for c in Xm.columns if dtr[c].std() > 1e-12]
        A = np.column_stack([np.ones(len(dtr)), dtr[keep].values])
        b = np.linalg.lstsq(A, dtr['_y'].values, rcond=None)[0]
        preds[t] = float(np.r_[1, Xm.loc[t, keep].values] @ b)
    return pd.Series(preds)


def prevailing_mean(target, h):
    y = T[target]
    out = {}
    for t in T.index[T.index >= START]:
        tr = y.reindex(T.index[T.index <= t - h - 1]).dropna()
        if len(tr) >= 8 and not pd.isna(y.get(t)):
            out[t] = tr.mean()
    return pd.Series(out)


MODELS = {
    'd_margin': {
        'AR + Easter (benchmark)': [],
        'raw materials local ccy, PDL L0-6': [('pdl', 'raw_mat_wloc_yoy', 6)],
        'FAO food index local ccy, PDL L0-6': [('pdl', 'fao_ffpi_wloc_yoy', 6)],
        'calibrated cost index, PDL L0-6': [('pdl', 'cost_idx_calib_yoy', 6)],
        'packaging EU, PDL L0-6': [('pdl', 'packaging_eu_yoy', 6)],
        'cost index + food CPI ex VAT, PDL': [('pdl', 'cost_idx_calib_yoy', 6), ('pdl', 'w_food_cpi_xvat_yoy', 6)],
        'gap: CPI ex VAT - cost index, PDL': [('pdl', 'gap_calib', 6)],
        'gap: CPI - agri basket (panel), avg L0-2': [('avg', 'price_cost_gap_agri', (0, 2))],
        'cost-index acceleration (avg L0-3 - L4-7)': [('accel', 'cost_idx_calib_yoy', None)],
        'packaging acceleration': [('accel', 'packaging_eu_yoy', None)],
        'EUR/SEK, PDL L0-6': [('pdl', 'se_eursek__yoy', 6)],
        'raw materials + packaging + EUR/SEK, PDL': [('pdl', 'raw_mat_wloc_yoy', 6), ('pdl', 'packaging_eu_yoy', 6),
                                                    ('pdl', 'se_eursek__yoy', 6)],
    },
    'og': {
        'AR + Easter (benchmark)': [],
        'food CPI ex VAT NO+SE (lag-0 data)': [('lvl', 'nw_food_cpi_xvat_yoy', 0)],
        'food CPI ex VAT Orkla-wtd': [('lvl', 'w_food_cpi_xvat_yoy', 0)],
        'food PPI Orkla-wtd': [('lvl', 'w_food_ppi_yoy', 0)],
        'food CPI NO+SE + relative food price': [('lvl', 'nw_food_cpi_xvat_yoy', 0), ('lvl', 'w_food_rel_xvat_yoy', 0)],
        'food CPI NO+SE + confidence d4': [('lvl', 'nw_food_cpi_xvat_yoy', 0), ('lvl', 'w_cons_conf_z_d4', 0)],
        'food CPI NO+SE + real wage': [('lvl', 'nw_food_cpi_xvat_yoy', 0), ('lvl', 'w_real_wage_yoy', 0)],
        'food mfr selling-price expectations (EC)': [('lvl', 'w_ec_food_ind_sell_price_exp_lvl', 0)],
    },
    'd_og': {
        'AR + Easter (benchmark)': [],
        'd food CPI ex VAT NO+SE (dyoy)': [('lvl', 'nw_food_cpi_xvat_dyoy', 0)],
        'd food CPI ex VAT Orkla-wtd (dyoy)': [('lvl', 'w_food_cpi_xvat_dyoy', 0)],
        'd food PPI (dyoy)': [('lvl', 'w_food_ppi_dyoy', 0)],
    },
}

rows, PRED = [], {}
for target, models in MODELS.items():
    for h in (0, 1, 2, 4):
        pm = prevailing_mean(target, h)
        bench = oos_run(target, [], h)
        PRED[(target, h, 'prevailing mean')] = pm
        for name, spec in models.items():
            pr = bench if not spec else oos_run(target, spec, h)
            PRED[(target, h, name)] = pr
            y = T[target]
            for ev_name, emask in [('all OOS quarters', pd.Series(True, index=T.index)), ('excl. 2021Q3-2023Q4', EPI)]:
                idx = pr.index[emask.reindex(pr.index).fillna(False).values]
                idx = idx.intersection(bench.index).intersection(pm.index)
                if len(idx) < 12:
                    continue
                r2_pm = C.oos_r2(y[idx], pm[idx], pr[idx])
                r2_ar = C.oos_r2(y[idx], bench[idx], pr[idx]) if spec else 0.0
                cw = C.clark_west(y[idx], bench[idx], pr[idx]) if spec else (np.nan, np.nan)
                rows.append(dict(target=target, h=h, model=name, evaluation=ev_name, n_oos=len(idx),
                                 rmse=np.sqrt(((y[idx] - pr[idx]) ** 2).mean()),
                                 oos_r2_vs_mean=r2_pm, oos_r2_vs_ar=r2_ar, cw_stat=cw[0], cw_p=cw[1]))
rt = pd.DataFrame(rows)
m = rt['cw_p'].notna()
rt.loc[m, 'cw_p_BY_family'] = M.mt_adjust(rt.loc[m, 'cw_p'], 'fdr_by')
rt['n_tests_family'] = int(m.sum())
rt.to_csv(f'{M.OUTDIR}/rt_oos.csv', index=False, float_format='%.4g')
pd.set_option('display.width', 250)
print(rt.to_string(float_format=lambda v: f'{v:.3g}'))
pd.DataFrame([(a, b, c, *rr) for (a, b, c), s in PRED.items() for rr in s.items()],
             columns=['target', 'h', 'model', 'period', 'pred']).assign(period=lambda d: d['period'].astype(str)).to_csv(
    f'{M.OUTDIR}/rt_predictions.csv', index=False, float_format='%.4g')

# In-sample real-time-aligned fit (whole sample) for the headline models: coefficients and HAC tests
ins = []
for h in (0, 1, 2, 4):
    for name, spec in [('calibrated cost index, PDL L0-6', [('pdl', 'cost_idx_calib_yoy', 6)]),
                       ('raw materials local ccy, PDL L0-6', [('pdl', 'raw_mat_wloc_yoy', 6)]),
                       ('packaging EU, PDL L0-6', [('pdl', 'packaging_eu_yoy', 6)]),
                       ('EUR/SEK, PDL L0-6', [('pdl', 'se_eursek__yoy', 6)])]:
        feat = spec[0][1]
        Xa = C.align(F[[feat]], D.loc[[feat]], mode='realtime', h=h)[feat]
        for s in ['full', 'ex_infl']:
            f = M.fit_dl(T['d_margin'], {feat: Xa}, T[['d_easter_window_q1']], M.mask(T, s), K=6, kind='pdl', P=2)
            cu = f['cum'].set_index('lag')
            ins.append(dict(model=name, h=h, sample=s, n=f['n'], r2=f['r2'], p=f['wald'][feat][2],
                            eff10_L0=10 * cu.loc[0, 'cum'], eff10_L2=10 * cu.loc[2, 'cum'], eff10_L6=10 * cu.loc[6, 'cum'],
                            first_lag_used=f'feature at t-{h}-{int(D.loc[feat, "realtime_min_lag_q"])}'))
ins = pd.DataFrame(ins)
ins.to_csv(f'{M.OUTDIR}/rt_insample.csv', index=False, float_format='%.4g')
print(ins.to_string(float_format=lambda v: f'{v:.3g}'))

# Figure: OOS R^2 vs AR benchmark by horizon for d_margin models
BLUE, ORANGE, AQUA, GRAY, INK, INK2 = '#2a78d6', '#eb6834', '#1baf7a', '#8a8984', '#0b0b0b', '#52514e'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': '#c9c8c3', 'axes.labelcolor': INK2, 'xtick.color': INK2,
                     'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False, 'legend.frameon': False})
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
mods = [k for k in MODELS['d_margin'] if not k.startswith('AR')]
for j, ev_name in enumerate(['all OOS quarters', 'excl. 2021Q3-2023Q4']):
    ax = axes[j]
    d = rt[(rt.target == 'd_margin') & (rt.evaluation == ev_name) & rt.model.isin(mods)]
    for k, (h, col) in enumerate(zip((0, 1, 2, 4), (BLUE, ORANGE, AQUA, GRAY))):
        dd = d[d.h == h].set_index('model').reindex(mods)
        ys = np.arange(len(mods)) + (k - 1.5) * 0.19
        ax.barh(ys, dd['oos_r2_vs_ar'].clip(-0.6, None), height=0.17, color=col, label=f'h={h}')
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(np.arange(len(mods))); ax.set_yticklabels(mods, fontsize=8)
    ax.set_title(f'd_margin, evaluation: {ev_name} (OOS from 2010Q1)', fontsize=9.5, loc='left')
    ax.set_xlabel('OOS R² vs AR(last reported)+Easter benchmark (clipped at -0.6)')
    ax.grid(axis='x', color='#ebeae6', lw=0.6)
axes[0].legend(fontsize=8, loc='lower right', title='horizon')
fig.tight_layout()
M.savefig(fig, 'fig_rt_oos.png'); plt.close(fig)
print('done')
