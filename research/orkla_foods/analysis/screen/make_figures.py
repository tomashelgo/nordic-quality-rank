"""Figures for the univariate screen (run after run_screen.py).

For each target:
  figures/top10_<target>_coincident.png  top 10 distinct core features, coincident alignment
  figures/top10_<target>_realtime.png    top 10 distinct core features, best real-time alignment
                                          (rt0, rt1, rt2 or rt4; never uses future data)
  figures/lagprofile_<target>.png        HAC t-stat by real-time lag k=0..6 for the top 15 features
Each top-10 row: left = scatter (2021Q3-2023Q4 highlighted, full and ex-episode OLS lines);
right = target vs the univariate fitted value from the feature (one axis, target units).
'Distinct' = a feature is skipped if |corr| > 0.9 with an already selected feature.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import screen_lib as S
from screen_lib import C

OUT = S.OUTDIR
FIG = f'{OUT}/figures'

INK, INK2, MUTED, GRID, AXIS, SURF = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7', '#fcfcfb'
BLUE, ORANGE, GRAYLINE = '#2a78d6', '#eb6834', '#52514e'
DIVERGING = LinearSegmentedColormap.from_list('bdr', ['#104281', '#3987e5', '#f0efec', '#e66767', '#a32a2a'])

TARGET_LABEL = {
    'd_margin': 'EBIT-margin change y/y (pp)',
    'og': 'Organic growth (%)',
    'd_og': 'Organic-growth change y/y (pp)',
    'd_margin_r4': 'Rolling-4Q EBIT-margin change y/y (pp)',
    'd_og_r4': 'Rolling-4Q organic-growth change y/y (pp)',
    'vol_proxy': 'Implied volume/mix: og - food CPI ex VAT (pp)',
}

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.edgecolor': AXIS, 'axes.labelcolor': INK2,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.titlecolor': INK, 'axes.titlesize': 8.5,
    'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'grid.linestyle': '-',
    'figure.facecolor': SURF, 'axes.facecolor': SURF, 'axes.spines.top': False, 'axes.spines.right': False,
    'legend.frameon': False, 'legend.fontsize': 7.5,
})


def aligned_series(F, D, feature, alignment, index):
    m, h = S.ALIGNMENTS[alignment]
    return C.align(F[[feature]], D, mode=m, h=h)[feature].reindex(index)


def pick_distinct(cands, F, D, T, n=10, thr=0.9):
    chosen, series = [], []
    for r in cands.itertuples():
        x = aligned_series(F, D, r.feature, r.alignment, T.index)
        if any(abs(x.corr(s)) > thr for s in series):
            continue
        chosen.append(r)
        series.append(x)
        if len(chosen) == n:
            break
    return chosen


def ols_line(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 10:
        return None
    b, a = np.polyfit(x[ok], y[ok], 1)
    return a, b


def top10_figure(target, rows, F, D, T, title, path):
    infl = (T.index >= S.INFL[0]) & (T.index <= S.INFL[1])
    fig, axes = plt.subplots(len(rows), 2, figsize=(12.5, 2.45 * len(rows)),
                             gridspec_kw=dict(width_ratios=[1, 2.6]))
    if len(rows) == 1:
        axes = axes[None, :]
    y = T[target]
    for i, r in enumerate(rows):
        x = aligned_series(F, D, r.feature, r.alignment, T.index)
        ok = x.notna() & y.notna()
        ax = axes[i, 0]
        ax.scatter(x[ok & ~infl], y[ok & ~infl], s=16, color=BLUE, edgecolor=SURF, linewidth=0.8,
                   label='other quarters', zorder=3)
        ax.scatter(x[ok & infl], y[ok & infl], s=16, color=ORANGE, edgecolor=SURF, linewidth=0.8,
                   label='2021Q3-2023Q4', zorder=4)
        xs = np.linspace(x[ok].min(), x[ok].max(), 50)
        f_all = ols_line(x[ok].values, y[ok].values)
        f_ex = ols_line(x[ok & ~infl].values, y[ok & ~infl].values)
        if f_all:
            ax.plot(xs, f_all[0] + f_all[1] * xs, color=GRAYLINE, lw=1.5, label='OLS all')
        if f_ex:
            ax.plot(xs, f_ex[0] + f_ex[1] * xs, color=BLUE, lw=1.5, label='OLS ex 21Q3-23Q4')
        ax.set_xlabel(f'{r.feature} [{r.alignment}]', fontsize=7)
        ax.set_ylabel(target, fontsize=7)
        if i == 0:
            ax.legend(loc='best', fontsize=6.5)
        # time series: target vs fitted value from the feature
        ax2 = axes[i, 1]
        ax2.plot(y.index.to_timestamp(), y.values, color=BLUE, lw=1.6, label=target)
        if f_all:
            fit = f_all[0] + f_all[1] * x
            ax2.plot(x.index.to_timestamp(), fit.values, color=ORANGE, lw=1.6,
                     label=f'fitted from {r.feature} [{r.alignment}]')
        ax2.axvspan(S.INFL[0].start_time, S.INFL[1].end_time, color='#f0efec', zorder=0)
        ax2.axhline(0, color=AXIS, lw=0.8)
        ax2.set_xlim(pd.Timestamp('2000-07-01'), pd.Timestamp('2026-10-01'))
        q = r.q_by
        ax2.set_title(f'#{i+1} {r.feature} ({r.category})  [{r.alignment}]  n={r.n}  r={r.pearson:+.2f}\n'
                      f'HAC t={r.t:+.1f} (leverage-adj. {r.t_lev:+.1f}), BY q={q:.3f};  '
                      f't excl. 2021Q3-23Q4 = {r.t_exinfl:+.1f};  t 2001-12 / 2013-26 = '
                      f'{r.t_early:+.1f} / {r.t_late:+.1f}',
                      loc='left', fontsize=7.3)
        ax2.legend(loc='upper left', fontsize=6.5, ncol=2)
    fig.suptitle(title, x=0.01, ha='left', fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    fig.savefig(path, dpi=110)
    plt.close(fig)


def lag_heatmap(target, L, B, path, n=15):
    top = B[(B.target == target)].sort_values('p_best').head(n)
    M = L[(L.target == target) & L.feature.isin(top.feature)].pivot(index='feature', columns='k', values='t')
    M = M.loc[top.feature]
    fig, ax = plt.subplots(figsize=(8.5, 0.36 * len(M) + 1.4))
    v = 8
    im = ax.imshow(M.values, cmap=DIVERGING, vmin=-v, vmax=v, aspect='auto')
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            val = M.values[i, j]
            if np.isfinite(val):
                ax.text(j, i, f'{val:+.1f}', ha='center', va='center', fontsize=7,
                        color='white' if abs(val) > 5 else INK)
    ax.set_xticks(range(M.shape[1]))
    ax.set_xticklabels([f'k={k}' for k in M.columns])
    ax.set_yticks(range(M.shape[0]))
    ax.set_yticklabels(M.index, fontsize=7)
    ax.grid(False)
    ax.set_title(f'{TARGET_LABEL[target]}: HAC t-stat by real-time lag\n'
                 f'(X_t = feature at t - publication lag - k; top {n} core features by best |t|)',
                 loc='left', fontsize=8.5)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.ax.tick_params(labelsize=7)
    cb.outline.set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    T = S.build_targets()
    F, D = C.load_features(core_only=True)
    R = pd.read_csv(f'{OUT}/screen_results_core.csv')
    L = pd.read_csv(f'{OUT}/lag_profiles.csv')
    B = pd.read_csv(f'{OUT}/lag_best.csv')
    sel = []
    for target in S.TARGETS:
        g = R[(R.target == target) & (R.n >= 60) & R.p.notna()]
        coin = g[g.alignment == 'coin'].sort_values('p')
        rows = pick_distinct(coin, F, D, T)
        top10_figure(target, rows, F, D, T,
                     f'{TARGET_LABEL[target]}: top 10 distinct core features, COINCIDENT (explanatory, not real-time)',
                     f'{FIG}/top10_{target}_coincident.png')
        sel += [dict(target=target, set='coincident', rank=i + 1, feature=r.feature, alignment=r.alignment)
                for i, r in enumerate(rows)]
        rt = g[g.alignment != 'coin'].sort_values('p').drop_duplicates('feature')
        rows = pick_distinct(rt, F, D, T)
        top10_figure(target, rows, F, D, T,
                     f'{TARGET_LABEL[target]}: top 10 distinct core features, REAL-TIME (best of h=0,1,2,4; '
                     f'feature shifted by its publication lag + h)',
                     f'{FIG}/top10_{target}_realtime.png')
        sel += [dict(target=target, set='realtime', rank=i + 1, feature=r.feature, alignment=r.alignment)
                for i, r in enumerate(rows)]
        lag_heatmap(target, L, B, f'{FIG}/lagprofile_{target}.png')
        print('figures done', target, flush=True)
    pd.DataFrame(sel).to_csv(f'{OUT}/figure_selection.csv', index=False)


if __name__ == '__main__':
    main()
