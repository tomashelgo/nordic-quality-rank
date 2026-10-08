"""Section 3: text evidence from management's quarterly driver commentary (lens-mechanism).

1. Classify each quarter's `drivers_note` into themes with transparent regex rules (text_rules.THEMES),
   then apply the documented manual review (text_rules.MANUAL_OVERRIDES).
2. Event study: average macro series in quarters where management cites a theme vs. not
   (HAC regression on the theme dummy + circular-shift permutation p-value + AUC), with and
   without 2021Q3-2023Q4. BY correction across the family.
3. Timing: at which lag does macro input-cost inflation best line up with management citing cost pressure?
4. Margin/organic-growth outcomes by theme (descriptive; text is published with the results, so coincident).

Outputs: text_themes.csv, text_rule_review.csv, text_event_study.csv, text_timing.csv, text_outcomes.csv,
mt_tests_text.csv, fig_text_timeline.png, fig_text_event_study.png
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import mech_utils as M
import text_rules as R

T, F, D, X = M.load_all()
XT = X.reindex(T.index)
q = M.C.load_orkla()
notes = q['drivers_note']

# ============================================================================ 1 classification
auto, final, review = {}, {}, []
for p, txt in notes.items():
    if not isinstance(txt, str):
        continue
    a = R.classify(txt)
    f = dict(a)
    ov = R.MANUAL_OVERRIDES.get(str(p))
    if ov:
        for k, v in ov[0].items():
            if f[k] != v:
                review.append(dict(period=str(p), theme=k, rule=a[k], final=v, reason=ov[1]))
            f[k] = v
    auto[p], final[p] = a, f
A = pd.DataFrame(auto).T.sort_index()
TH = pd.DataFrame(final).T.sort_index()
TH.index = pd.PeriodIndex(TH.index, freq='Q'); A.index = TH.index
rev = pd.DataFrame(review)
rev.to_csv(f'{M.OUTDIR}/text_rule_review.csv', index=False)
agree = []
for th in TH.columns:
    a, f = A[th], TH[th]
    po = (a == f).mean()
    pe = a.mean() * f.mean() + (1 - a.mean()) * (1 - f.mean())
    agree.append(dict(theme=th, n_final=int(f.sum()), n_rule=int(a.sum()), changed=int((a != f).sum()),
                      agreement=po, kappa=(po - pe) / (1 - pe) if pe < 1 else np.nan))
agree = pd.DataFrame(agree)
print(agree.to_string(float_format=lambda v: f'{v:.2f}'))
out = TH.copy()
out.insert(0, 'drivers_note', notes.reindex(TH.index))
out.insert(0, 'og', T['og'].reindex(TH.index))
out.insert(0, 'd_margin', T['d_margin'].reindex(TH.index))
out.insert(0, 'def_id', T['def_id'].reindex(TH.index))
out.to_csv(f'{M.OUTDIR}/text_themes.csv', index_label='period')
agree.to_csv(f'{M.OUTDIR}/text_rule_agreement.csv', index=False, float_format='%.3f')

# ============================================================================ 2 event study
TE = TH.reindex(T.index)
EVENTS = {
    'cost_up': ['raw_mat_wloc_yoy', 'eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy', 'w_food_ppi_yoy', 'packaging_eu_yoy',
                'cost_idx_calib_yoy', 'se_ppi_food_impi_idx__yoy', 'glob_fao_ffpi__yoy'],
    'cost_relief': ['raw_mat_wloc_yoy', 'eu_agri_basket_wloc_yoy', 'cost_idx_calib_yoy', 'packaging_eu_yoy'],
    'price_lag': ['raw_mat_wloc_yoy', 'cost_idx_calib_yoy', 'gap_raw_xvat_wloc'],
    'fx_weak': ['w_fx_vs_eur_yoy', 'w_fx_vs_usd_yoy', 'se_eursek__yoy', 'no_fx_eurnok__yoy'],
    'fx_strong': ['w_fx_vs_eur_yoy', 'no_fx_eurnok__yoy'],
    'energy': ['elec_nordic_loc_yoy', 'natgas_eu_eur_yoy', 'brent_nok_yoy'],
    'price_up': ['w_food_cpi_xvat_yoy', 'w_food_ppi_yoy', 'w_ec_food_ind_sell_price_exp_lvl'],
    'volume_weak': ['w_retail_food_vol_yoy', 'nw_retail_food_vol_yoy', 'w_real_wage_yoy', 'w_cons_conf_z', 'w_food_rel_xvat_yoy'],
    'buying_power': ['w_real_wage_yoy', 'w_cons_conf_z', 'w_food_rel_xvat_yoy'],
}
OUTCOMES = {'d_margin': T['d_margin'], 'og': T['og'], 'vol_proxy_in': T['vol_proxy_in']}
rng = np.random.default_rng(7)


def event_test(theme, series, smp, avg_lags=(0, 1)):
    """macro averaged over lags avg_lags (t and t-1: input costs reach P&L with a lag) vs theme dummy."""
    z = pd.concat([series.shift(k) for k in avg_lags], axis=1).mean(axis=1, skipna=False).reindex(T.index)
    dd = pd.concat([TE[theme].rename('d'), z.rename('z')], axis=1)
    dd = dd[smp & dd['d'].notna() & dd['z'].notna()]
    if dd['d'].sum() < 3 or (1 - dd['d']).sum() < 3:
        return None
    r = M.C.nw_ols(dd['z'], dd[['d']], lags=4)
    obs = dd.loc[dd.d == 1, 'z'].mean() - dd.loc[dd.d == 0, 'z'].mean()
    # circular-shift permutation (keeps the autocorrelation of both series)
    n = len(dd)
    dv, zv = dd['d'].values, dd['z'].values
    diffs = []
    for s in range(4, n - 3):
        ds = np.roll(dv, s)
        if ds.sum() == 0 or ds.sum() == n:
            continue
        diffs.append(zv[ds == 1].mean() - zv[ds == 0].mean())
    diffs = np.array(diffs)
    p_perm = (np.sum(np.abs(diffs) >= abs(obs)) + 1) / (len(diffs) + 1)
    # AUC (Mann-Whitney): P(z in theme quarter > z in other quarter)
    from scipy.stats import mannwhitneyu
    u = mannwhitneyu(dd.loc[dd.d == 1, 'z'], dd.loc[dd.d == 0, 'z']).statistic
    auc = u / (dd.d.sum() * (1 - dd.d).sum())
    return dict(n=n, n_theme=int(dd.d.sum()), mean_theme=dd.loc[dd.d == 1, 'z'].mean(), mean_other=dd.loc[dd.d == 0, 'z'].mean(),
                diff=obs, se_hac=r.bse['d'], p_hac=r.pvalues['d'], p_perm=p_perm, auc=auc)


ev_rows, tests = [], []
for s in ['full', 'ex_infl']:
    smp = M.mask(T, s) & (T.index >= pd.Period('2001Q1', 'Q'))
    for th, feats in EVENTS.items():
        for c in feats:
            res = event_test(th, X[c], smp, avg_lags=(0, 1) if th in ('cost_up', 'cost_relief', 'price_lag', 'fx_weak', 'fx_strong', 'energy') else (0,))
            if res is None:
                continue
            ev_rows.append(dict(theme=th, macro=c, sample=s, kind='macro', **res))
            tests.append(('text_event_study', f'{th}|{c}', s, np.nan, 1, max(res['p_hac'], res['p_perm']), res['n']))
        for oc, ser in OUTCOMES.items():
            res = event_test(th, ser, smp, avg_lags=(0,))
            if res is not None:
                ev_rows.append(dict(theme=th, macro=oc, sample=s, kind='outcome', **res))
ev = pd.DataFrame(ev_rows)
m = ev.kind == 'macro'
ev['p_conservative'] = ev[['p_hac', 'p_perm']].max(axis=1)
ev.loc[m, 'p_BY_family'] = M.mt_adjust(ev.loc[m, 'p_conservative'], 'fdr_by')
# the circular-shift permutation p has a floor of ~1/(n_shifts+1) ~ 0.01, which caps BY-adjusted values;
# report BY on the HAC p-values as well
ev.loc[m, 'p_BY_family_hac'] = M.mt_adjust(ev.loc[m, 'p_hac'], 'fdr_by')
ev.loc[m, 'n_tests_family'] = int(m.sum())
ev.to_csv(f'{M.OUTDIR}/text_event_study.csv', index=False, float_format='%.4g')
print(ev.to_string(float_format=lambda v: f'{v:.3g}'))

# ============================================================================ 3 timing
tm_rows = []
for c in ['raw_mat_wloc_yoy', 'eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy', 'cost_idx_calib_yoy', 'packaging_eu_yoy',
          'w_food_ppi_yoy', 'se_eursek__yoy', 'w_fx_vs_eur_yoy']:
    th = 'fx_weak' if c in ('se_eursek__yoy', 'w_fx_vs_eur_yoy') else 'cost_up'
    for s in ['full', 'ex_infl']:
        smp = M.mask(T, s) & (T.index >= pd.Period('2001Q1', 'Q'))
        for k in range(-3, 7):
            z = X[c].shift(k).reindex(T.index)
            dd = pd.concat([TE[th], z], axis=1)[smp].dropna()
            from scipy.stats import mannwhitneyu, pointbiserialr
            u = mannwhitneyu(dd.iloc[:, 1][dd.iloc[:, 0] == 1], dd.iloc[:, 1][dd.iloc[:, 0] == 0]).statistic
            auc = u / ((dd.iloc[:, 0] == 1).sum() * (dd.iloc[:, 0] == 0).sum())
            tm_rows.append(dict(macro=c, theme=th, sample=s, k=k, n=len(dd), corr=dd.corr().iloc[0, 1], auc=auc))
tm = pd.DataFrame(tm_rows)
tm.to_csv(f'{M.OUTDIR}/text_timing.csv', index=False, float_format='%.4g')
print(tm.pivot_table(index=['macro', 'sample'], columns='k', values='auc').round(2).to_string())

# ============================================================================ 4 outcomes by theme (multivariate, descriptive)
oc_rows = []
TH_REG = ['cost_up', 'price_lag', 'price_offset', 'cost_relief', 'fx_weak', 'volume_weak', 'volume_strong', 'ma_distribution',
          'cost_programme', 'one_off', 'easter_timing', 'campaign', 'covid']
for target in ['d_margin', 'og']:
    for s in ['full', 'ex_infl']:
        yv = T[target].where(M.mask(T, s))
        r = M.C.nw_ols(yv, TE[TH_REG].astype(float), lags=4)
        for th in TH_REG:
            oc_rows.append(dict(target=target, sample=s, theme=th, n_theme=int(TE[th][M.mask(T, s) & yv.notna()].sum()),
                                coef=r.params[th], se=r.bse[th], p=r.pvalues[th], r2=r.rsquared, n=int(r.nobs)))
oc = pd.DataFrame(oc_rows)
oc.to_csv(f'{M.OUTDIR}/text_outcomes.csv', index=False, float_format='%.4g')
print(oc.to_string(float_format=lambda v: f'{v:.3g}'))
pd.DataFrame(tests, columns=['family', 'test', 'sample', 'stat', 'df', 'p', 'n']).to_csv(
    f'{M.OUTDIR}/mt_tests_text.csv', index=False, float_format='%.4g')

# ============================================================================ figures
BLUE, ORANGE, AQUA, GRAY, INK, INK2 = '#2a78d6', '#eb6834', '#1baf7a', '#8a8984', '#0b0b0b', '#52514e'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': '#c9c8c3', 'axes.labelcolor': INK2, 'xtick.color': INK2,
                     'ytick.color': INK2, 'axes.titlesize': 9.5, 'axes.titlecolor': INK, 'axes.spines.top': False,
                     'axes.spines.right': False, 'legend.frameon': False})
SHOW = [('cost_up', 'input costs up / high'), ('price_lag', 'price increases lag costs'), ('price_offset', 'costs offset by pricing'),
        ('cost_relief', 'input costs stable / lower'), ('price_up', 'price increases'), ('fx_weak', 'weak NOK/SEK raises costs'),
        ('fx_strong', 'strong NOK'), ('energy', 'energy costs'), ('volume_weak', 'volume weakness'), ('volume_strong', 'volume strength'),
        ('buying_power', 'buying power / discounters / PL'), ('easter_timing', 'Easter / calendar timing'), ('campaign', 'campaigns'),
        ('ma_distribution', 'M&A / distribution / dilution'), ('cost_programme', 'cost programmes / synergies'),
        ('covid', 'COVID'), ('out_of_home', 'out-of-home'), ('one_off', 'one-offs (recall, ERP, strike)')]
fig = plt.figure(figsize=(14, 8.2))
gs = fig.add_gridspec(2, 1, height_ratios=[1.1, 2.4], hspace=0.08)
ax0 = fig.add_subplot(gs[0])
idx = TH.index
xs = np.arange(len(idx))
ax0.bar(xs, T['d_margin'].reindex(idx), color=[ORANGE if v < 0 else BLUE for v in T['d_margin'].reindex(idx)], width=0.7)
ax0.set_ylabel('d_margin, pp', color=INK2)
ax0b = ax0.twinx()
ax0b.plot(xs, XT['raw_mat_wloc_yoy'].reindex(idx), color=INK, lw=1.6, label='raw-material inflation, local ccy (% y/y, right)')
ax0b.spines['top'].set_visible(False)
ax0b.set_ylabel('% y/y', color=INK2)
ax0b.legend(loc='upper left', fontsize=8)
ax0.axhline(0, color=INK2, lw=0.8)
ax0.set_xlim(-0.6, len(idx) - 0.4); ax0.set_xticks([])
ax0.set_title('Management-cited drivers by quarter (rule-based classification of drivers_note, manually reviewed); bars = y/y EBIT-margin change',
              fontsize=10, loc='left')
ax = fig.add_subplot(gs[1], sharex=ax0)
mat = np.array([TH[k].values for k, _ in SHOW], dtype=float)
from matplotlib.colors import ListedColormap
ax.imshow(mat, aspect='auto', cmap=ListedColormap(['#f4f3f0', BLUE]), interpolation='nearest')
ax0.tick_params(labelbottom=False)
ax.set_yticks(range(len(SHOW))); ax.set_yticklabels([lab for _, lab in SHOW], fontsize=8)
ax.set_xticks(xs[::4]); ax.set_xticklabels([str(p) for p in idx[::4]], rotation=60, fontsize=8)
for y in np.arange(-0.5, len(SHOW), 1):
    ax.axhline(y, color='white', lw=1)
fig.savefig(f'{M.OUTDIR}/fig_text_timeline.png', dpi=130, bbox_inches='tight')
plt.close(fig)

# event-study figure: macro averages theme vs other
sel = [('cost_up', 'raw_mat_wloc_yoy'), ('cost_up', 'cost_idx_calib_yoy'), ('cost_up', 'packaging_eu_yoy'), ('cost_up', 'w_food_ppi_yoy'),
       ('cost_relief', 'raw_mat_wloc_yoy'), ('fx_weak', 'w_fx_vs_eur_yoy'), ('fx_weak', 'se_eursek__yoy'),
       ('price_up', 'w_food_cpi_xvat_yoy'), ('volume_weak', 'w_food_rel_xvat_yoy')]
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
for j, s in enumerate(['full', 'ex_infl']):
    ax = axes[j]
    d = ev[(ev['sample'] == s) & (ev.kind == 'macro')].set_index(['theme', 'macro'])
    ys = np.arange(len(sel))
    for i, key in enumerate(sel):
        if key not in d.index:
            continue
        r = d.loc[key]
        ax.plot([r['mean_other'], r['mean_theme']], [i, i], color=GRAY, lw=1.2)
        ax.scatter(r['mean_other'], i, color=GRAY, s=30, zorder=3, label='quarters without theme' if i == 0 else None)
        ax.scatter(r['mean_theme'], i, color=ORANGE, s=36, zorder=3, label='quarters where management cites theme' if i == 0 else None)
        ax.annotate(f"p={r['p_conservative']:.3f}", (max(r['mean_other'], r['mean_theme']), i), xytext=(6, -3),
                    textcoords='offset points', fontsize=7.5, color=INK2)
    ax.set_yticks(ys); ax.set_yticklabels([f'{a}: {b}' for a, b in sel], fontsize=8)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_title({'full': 'full sample 2001-2026', 'ex_infl': 'excl. 2021Q3-2023Q4'}[s], fontsize=9.5)
    ax.set_xlabel('macro series, % y/y (avg of t and t-1 for cost/FX/energy themes)')
    ax.grid(axis='x', color='#ebeae6', lw=0.6)
axes[0].legend(fontsize=8, loc='lower right')
fig.suptitle('Event study: macro series in quarters where management cites a driver vs. other quarters (p = max of HAC and circular-shift permutation)',
             fontsize=10.5, color=INK, x=0.01, ha='left')
fig.tight_layout()
M.savefig(fig, 'fig_text_event_study.png'); plt.close(fig)
print('done')
