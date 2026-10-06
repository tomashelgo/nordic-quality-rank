"""Step 1: quick univariate screen of the 200 core features for d_margin, og, d_og.

For every target x feature x alignment (coincident; realtime h=0; realtime h=1):
    y_t = a + b * z(x_t) + controls + e_t,  HAC (Newey-West, 4 lags) s.e.
Controls (robust_lib.controls_for): definition dummies (B..E; India absorbed by def_D), COVID
2020-21 dummy, Easter (d_easter_window_q1 for d_margin; calendar-adjustment-aware Easter term for
og; its y/y change plus the definition-break flag for d_og). og and d_og use the quality weights.
x is standardised over the regression sample, so b is in target units per 1 SD of x.

For lag-0 features realtime h=0 is identical to coincident; the duplicate is not re-tested
(it is flagged in the output) so that the multiple-testing family is not inflated.

Multiple testing: Benjamini-Yekutieli q-values within each target family and across all tests.

Outputs: screen_all.csv, screen_selected.csv, screen_trend_check.csv, fig_screen_persistence.png
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import robust_lib as R
C = R.C

T = R.load_T()
F, D = C.load_features(core_only=True)

# Validate the implied volume/mix proxy (og - w_food_cpi_xvat_yoy) on the reported 2022Q2+ split.
v = T[['vol_proxy', 'volume_mix', 'price']].dropna()
v['food_cpi_xvat'] = F['w_food_cpi_xvat_yoy'].reindex(v.index)
val = pd.DataFrame([dict(n=len(v), corr_proxy_vs_reported_volmix=v['vol_proxy'].corr(v['volume_mix']),
                         corr_foodcpi_vs_reported_price=v['food_cpi_xvat'].corr(v['price']),
                         mean_proxy_minus_reported=(v['vol_proxy'] - v['volume_mix']).mean(),
                         mae=(v['vol_proxy'] - v['volume_mix']).abs().mean())])
val.to_csv(f'{R.OUT}/vol_proxy_validation.csv', index=False)
print(val.round(3).to_string())
ALIGN = {'coincident': ('coincident', 0), 'rt_h0': ('realtime', 0), 'rt_h1': ('realtime', 1)}
XA = {a: C.align(F, D, m, h) for a, (m, h) in ALIGN.items()}

# Feature persistence / trendiness over the Orkla sample period (2001Q1-2026Q2).
samp = F.loc[pd.Period('2001Q1', 'Q'):pd.Period('2026Q2', 'Q')]
pers = {}
for c in F.columns:
    s = samp[c].dropna()
    if len(s) < 20:
        pers[c] = (np.nan, np.nan)
        continue
    rho = np.corrcoef(s.values[1:], s.values[:-1])[0, 1]
    tt = np.array([p.ordinal for p in s.index], float)
    r2 = np.corrcoef(tt, s.values)[0, 1] ** 2
    pers[c] = (rho, r2)
pers = pd.DataFrame(pers, index=['ar1', 'trend_r2']).T

rows = []
for tgt in R.TARGETS:
    y = T[tgt]
    Ctrl = R.controls_for(tgt, T)
    w = R.weights_for(tgt, T)
    for a in ALIGN:
        for f in F.columns:
            lag = int(D.loc[f, 'realtime_min_lag_q'])
            if a == 'rt_h0' and lag == 0:
                continue  # identical to coincident
            x = XA[a][f]
            yv, Xv, wv, idx = R.frame(y, x, Ctrl, w)
            if len(yv) < 40:
                continue
            sd = Xv[:, 0].std()
            if sd == 0:
                continue
            Xv = Xv.copy()
            Xv[:, 0] = (Xv[:, 0] - Xv[:, 0].mean()) / sd
            r = R.hac_ols(yv, Xv, wv)
            rows.append(dict(target=tgt, feature=f, alignment=a, lag_q=lag,
                             category=D.loc[f, 'category'], n=r['n'],
                             beta_sd=r['beta'][0], t=r['t'][0], p=r['p'][0],
                             corr=np.corrcoef(yv, Xv[:, 0])[0, 1],
                             same_as_coincident=(a == 'coincident' and lag == 0)))
S = pd.DataFrame(rows)
S['q_by_target'] = np.nan
for tgt in R.TARGETS:
    m = S['target'] == tgt
    S.loc[m, 'q_by_target'] = R.by_qvalues(S.loc[m, 'p'].values)
S['q_by_all'] = R.by_qvalues(S['p'].values)
S = S.join(pers, on='feature')
S.to_csv(f'{R.OUT}/screen_all.csv', index=False)

print('screen tests per target:', S.groupby('target').size().to_dict(), 'total', len(S))
for tgt in R.TARGETS:
    s = S[S.target == tgt]
    print(f'{tgt}: p<0.05 {int((s.p < 0.05).sum())} (expected by chance {0.05 * len(s):.0f}); '
          f'BY q<0.10 {int((s.q_by_target < 0.10).sum())}; BY q<0.05 {int((s.q_by_target < 0.05).sum())}')

# ---------------------------------------------------------------- candidate selection
corrF = samp.corr(min_periods=40)
sel_rows = []
for tgt in R.TARGETS:
    s = S[S.target == tgt].copy()
    best = s.loc[s.groupby('feature')['p'].idxmin()].sort_values('p')
    chosen = []
    for _, r in best.iterrows():
        f = r['feature']
        if any(abs(corrF.loc[f, g]) > 0.9 for g in chosen if not np.isnan(corrF.loc[f, g])):
            continue
        chosen.append(f)
        sel_rows.append(dict(target=tgt, feature=f, best_alignment=r['alignment'], beta_sd=r['beta_sd'],
                             t=r['t'], p=r['p'], q_by_target=r['q_by_target'], rank=len(chosen)))
        if len(chosen) == 15:
            break
Sel = pd.DataFrame(sel_rows)
Sel.to_csv(f'{R.OUT}/screen_selected.csv', index=False)
pd.set_option('display.width', 200)
print(Sel.round(4).to_string())

# ---------------------------------------------------------------- do trending features dominate?
tc = []
for tgt in R.TARGETS:
    s = S[S.target == tgt]
    best = s.loc[s.groupby('feature')['p'].idxmin()].copy()
    best['abs_t'] = best['t'].abs()
    from scipy.stats import spearmanr
    rho_ar, p_ar = spearmanr(best['abs_t'], best['ar1'], nan_policy='omit')
    rho_tr, p_tr = spearmanr(best['abs_t'], best['trend_r2'], nan_policy='omit')
    top = best.nsmallest(20, 'p')
    tc.append(dict(target=tgt, n_features=len(best),
                   spearman_abs_t_vs_ar1=rho_ar, p_ar1=p_ar,
                   spearman_abs_t_vs_trend_r2=rho_tr, p_trend=p_tr,
                   share_ar1_gt_0p9_all=(best['ar1'] > 0.9).mean(),
                   share_ar1_gt_0p9_top20=(top['ar1'] > 0.9).mean(),
                   median_trend_r2_all=best['trend_r2'].median(),
                   median_trend_r2_top20=top['trend_r2'].median()))
TC = pd.DataFrame(tc)
TC.to_csv(f'{R.OUT}/screen_trend_check.csv', index=False)
print(TC.round(3).to_string())

# figure: |t| vs persistence
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
fig, axes = plt.subplots(1, 4, figsize=(16, 4), sharey=True)
for ax, tgt, col in zip(axes, R.TARGETS, [BLUE, ORANGE, AQUA, '#4a3aa7']):
    s = S[S.target == tgt]
    best = s.loc[s.groupby('feature')['p'].idxmin()]
    ax.scatter(best['ar1'], best['t'].abs(), s=14, color=col, alpha=0.75, linewidths=0)
    thr = s.loc[s.q_by_target < 0.10, 't'].abs().min()
    if not np.isnan(thr):
        ax.axhline(thr, color='#52514e', lw=1, ls='--')
        ax.text(0.02, thr + 0.1, 'BY q<0.10', color='#52514e', fontsize=8)
    ax.set_title(f'{tgt}: best |t| per feature vs AR(1)', fontsize=10)
    ax.set_xlabel('feature AR(1) coefficient, 2001-26')
    ax.grid(color='#e5e4e0', lw=0.6)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
axes[0].set_ylabel('|HAC t| (best of coincident / rt h0 / rt h1)')
fig.tight_layout()
fig.savefig(f'{R.OUT}/fig_screen_persistence.png', dpi=130)
