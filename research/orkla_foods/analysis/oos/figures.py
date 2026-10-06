"""Stage 3: figures for the OOS horse race (reads oos_results.csv, forecasts_all.csv.gz, lasso_selection_raw.csv)."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

import oos_lib as L

OUT = L.OUT
# reference palette (dataviz skill): categorical slots in fixed order, ink and chrome
S1, S2, S3, S4 = '#2a78d6', '#eb6834', '#1baf7a', '#eda100'
INK, INK2, MUTED, GRID, AXIS, SURF = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7', '#fcfcfb'
SHADE = '#f0efec'
plt.rcParams.update({
    'font.family': 'sans-serif', 'font.size': 9, 'axes.edgecolor': AXIS, 'axes.labelcolor': INK2,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
    'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
    'legend.frameon': False, 'axes.titlesize': 10, 'axes.titlecolor': INK, 'lines.linewidth': 2,
})
LABEL = {'d_margin': 'EBIT-margin change y/y (pp)', 'd_og': 'Change in organic growth y/y (pp)',
         'og': 'Organic growth (%)', 'd_margin_r4': 'Rolling-4Q EBIT-margin change y/y (pp)'}
HLAB = {0: 'h=0 nowcast', 1: 'h=1 (one quarter ahead)', 2: 'h=2 (two quarters ahead)'}

R = pd.read_csv(f'{OUT}/oos_results.csv')
R = R[R.primary]                      # benchmarks + the primary base variant of each target
FC = pd.read_csv(f'{OUT}/forecasts_all.csv.gz')
FC['period'] = pd.PeriodIndex(FC['period'], freq='Q')
FC = FC[np.array([v == 'bench' or v == L.PRIMARY[t] for t, v in zip(FC.target, FC.variant)])]


def shade(ax, x_of):
    for (a, b), lab in [(('2020Q1', '2021Q2'), 'COVID'), (('2021Q3', '2023Q4'), 'inflation\n2021Q3-23Q4')]:
        ax.axvspan(x_of(pd.Period(a, 'Q')) - 0.5, x_of(pd.Period(b, 'Q')) + 0.5, color=SHADE, zorder=0, lw=0)
        ax.text((x_of(pd.Period(a, 'Q')) + x_of(pd.Period(b, 'Q'))) / 2, 1.0, lab, transform=ax.get_xaxis_transform(),
                ha='center', va='top', fontsize=7, color=MUTED)


def pick_models(tgt, h):
    """Models to display: real-time combination, LASSO, best theory (ex post), best univariate (ex post)."""
    r = R[(R.target == tgt) & (R.h == h) & (R['sample'] == 'full2010')]
    th = r[r.family == 'theory'].sort_values('rmse').iloc[0]
    un = r[(r.family == 'univariate') & (~r.short_sample)].sort_values('rmse').iloc[0]
    return [('comb_adaptive', 'Combination, top-k (k chosen in real time)', S1),
            ('lasso', 'LASSO (all core features)', S2),
            (th.model, f'Best theory model, ex post pick: {th.model}', S3),
            (un.model, f'Best single feature, ex post pick: {un.feature} (p={un.lags})', S4)]


def wide(tgt, h):
    f = FC[(FC.target == tgt) & (FC.h == h) & (FC.period >= L.EVAL_START)]
    W = f.pivot(index='period', columns='model', values='forecast')
    y = f.drop_duplicates('period').set_index('period')['actual']
    return W, y


def fig_cssed(tgt):
    base = L.BASE_NAME[tgt]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=False)
    for ax, h in zip(axes, L.HS):
        W, y = wide(tgt, h)
        per = W.index
        x = np.arange(len(per))
        pos = {p: i for i, p in enumerate(per)}
        shade(ax, lambda p: pos[p])
        eb = (y - W[base]) ** 2
        for m, lab, col in pick_models(tgt, h):
            d = (eb - (y - W[m]) ** 2)
            ok = d.notna()
            ax.plot(x[ok.values], d[ok].cumsum().values, color=col, label=lab)
        ax.axhline(0, color=AXIS, lw=1)
        ticks = [i for i, p in enumerate(per) if p.quarter == 1 and p.year % 2 == 0]
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(per[i].year) for i in ticks])
        ax.set_title(HLAB[h], loc='left')
        if h == 0:
            ax.set_ylabel(f'Cumulative SSE({base}) - SSE(model)')
    h_, l_ = axes[0].get_legend_handles_labels()
    fig.legend(h_, ['Combination, top-k (k chosen in real time)', 'LASSO (all core features)',
                    'Best theory model (ex post pick, differs by panel)',
                    'Best single feature (ex post pick, differs by panel)'], loc='lower center', ncol=4, fontsize=8)
    fig.suptitle(f'{LABEL[tgt]}: cumulative squared-error gain vs the {base.upper()} benchmark '
                 f'(rising = model beats benchmark)', x=0.01, ha='left', color=INK, fontsize=11)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(f'{OUT}/fig_cssed_{tgt}.png', dpi=150)
    plt.close(fig)


def fig_fva():
    fig, axes = plt.subplots(4, 2, figsize=(13, 13))
    for r_, tgt in enumerate(L.TARGETS):
        base = L.BASE_NAME[tgt]
        for c_, h in enumerate([0, 1]):
            ax = axes[r_, c_]
            W, y = wide(tgt, h)
            per = W.index
            x = np.arange(len(per))
            pos = {p: i for i, p in enumerate(per)}
            shade(ax, lambda p: pos[p])
            ax.plot(x, y.values, color=INK, lw=1.5, marker='o', ms=3, label='Actual')
            ax.plot(x, W[base].values, color=MUTED, lw=1.5, ls='--', label=f'{base.upper()} benchmark')
            ax.plot(x, W['comb_adaptive'].values, color=S1, label='Combination (real-time k)')
            r = R[(R.target == tgt) & (R.h == h) & (R['sample'] == 'full2010') &
                  (R.family.isin(['theory', 'penalised', 'pca', 'ml', 'combination']))].sort_values('rmse').iloc[0]
            if r.model != 'comb_adaptive':
                ax.plot(x, W[r.model].values, color=S2, label=f'Best multivariate, ex post: {r.model}')
            ax.axhline(0, color=AXIS, lw=1)
            ticks = [i for i, p in enumerate(per) if p.quarter == 1 and p.year % 2 == 0]
            ax.set_xticks(ticks)
            ax.set_xticklabels([str(per[i].year) for i in ticks])
            ax.set_title(f'{LABEL[tgt]} - {HLAB[h]}', loc='left')
            ax.legend(fontsize=7, loc='lower left', ncol=2)
    fig.tight_layout()
    fig.savefig(f'{OUT}/fig_forecast_vs_actual.png', dpi=140)
    plt.close(fig)


def fig_r2_heatmap():
    models = ['ar', 'ar_bic', 'naive', 'rw', 'theory_best_ex_post', 'uni_best_ex_post', 'comb_adaptive', 'comb_all_mean',
              'comb_dmspe', 'comb_top5', 'lasso', 'enet', 'ridge', 'pca_bic', 'pca_k3', 'rf_resid', 'gbm_resid']
    cols = [(t, h) for t in L.TARGETS for h in L.HS]
    cmap = LinearSegmentedColormap.from_list('div', ['#c23a3a', '#e34948', '#f2a8a3', SHADE, '#9ec5f4', '#3987e5',
                                                     '#1c5cab'])
    fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
    for ax, s in zip(axes, ['full2010', 'exinfl2010']):
        M = np.full((len(models), len(cols)), np.nan)
        for j, (t, h) in enumerate(cols):
            r = R[(R.target == t) & (R.h == h) & (R['sample'] == s)].set_index('model')
            rf = R[(R.target == t) & (R.h == h) & (R['sample'] == 'full2010')]
            for i, m in enumerate(models):
                if m == 'theory_best_ex_post':
                    mm = rf[rf.family == 'theory'].sort_values('rmse').model.iloc[0]
                elif m == 'uni_best_ex_post':
                    mm = rf[(rf.family == 'univariate') & (~rf.short_sample)].sort_values('rmse').model.iloc[0]
                elif m == 'naive':
                    mm = 'mean' if t == 'og' else 'zero'
                else:
                    mm = m
                if mm in r.index:
                    rr = r.loc[mm]
                    M[i, j] = 1 - rr['rmse'] ** 2 / rr['rmse_base'] ** 2
        im = ax.imshow(np.clip(M, -0.5, 0.5), cmap=cmap, vmin=-0.5, vmax=0.5, aspect='auto')
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if np.isfinite(M[i, j]):
                    ax.text(j, i, f'{M[i, j]:.2f}', ha='center', va='center', fontsize=6.5,
                            color=INK if abs(M[i, j]) < 0.35 else 'white')
        ax.set_xticks(range(len(cols)))
        ax.set_xticklabels([f'{t}\nh={h}' for t, h in cols], fontsize=7)
        ax.set_yticks(range(len(models)))
        ax.set_yticklabels(models, fontsize=8)
        ax.grid(False)
        ax.set_title({'full2010': 'OOS R2 vs nested base (AR; og-level AR for d_og), 2010Q1-2026Q2',
                      'exinfl2010': 'Same, excluding 2021Q3-2023Q4'}[s], loc='left')
    fig.colorbar(im, ax=axes, shrink=0.6, label='OOS R2 vs base (clipped at +/-0.5); blue = beats base')
    fig.savefig(f'{OUT}/fig_oos_r2_heatmap.png', dpi=140, bbox_inches='tight')
    plt.close(fig)


def fig_lasso_heat():
    import glob
    sel = pd.concat([pd.read_csv(f) for f in glob.glob(f'{OUT}/lasso_selection_raw_*.csv')])
    alog = pd.concat([pd.read_csv(f) for f in glob.glob(f'{OUT}/penalised_alpha_log_*.csv')])
    sel = sel[(sel.method == 'lasso').values & np.array([v == L.PRIMARY[t] for t, v in zip(sel.target, sel.variant)])]
    alog = alog[np.array([v == L.PRIMARY[t] for t, v in zip(alog.target, alog.variant)])]
    blue = LinearSegmentedColormap.from_list('b', [SURF, '#2a78d6'])
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, tgt in zip(axes.ravel(), L.TARGETS):
        h = 0
        s = sel[(sel.target == tgt) & (sel.h == h)]
        origins = sorted(alog[(alog.target == tgt) & (alog.h == h) & (alog.method == 'lasso')].period.unique())
        top = s.feature.value_counts().head(15).index
        M = np.zeros((len(top), len(origins)))
        o_pos = {o: i for i, o in enumerate(origins)}
        for _, r in s[s.feature.isin(top)].iterrows():
            M[list(top).index(r.feature), o_pos[r.period]] = np.sign(r.coef)
        ax.imshow(np.abs(M), cmap=blue, aspect='auto', vmin=0, vmax=1)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if M[i, j] < 0:
                    ax.plot(j, i, marker='_', color='white', ms=4)
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels([f'{f} ({(s.feature == f).sum() / len(origins):.0%})' for f in top], fontsize=7)
        tk = [i for i, o in enumerate(origins) if o.endswith('Q1') and int(o[:4]) % 2 == 0]
        ax.set_xticks(tk)
        ax.set_xticklabels([origins[i][:4] for i in tk], fontsize=7)
        ax.grid(False)
        ax.set_title(f'{tgt}, h=0: LASSO selection by forecast quarter (white dash = negative coef)', loc='left',
                     fontsize=9)
    fig.tight_layout()
    fig.savefig(f'{OUT}/fig_lasso_selection_heatmap.png', dpi=140)
    plt.close(fig)


if __name__ == '__main__':
    for t in L.TARGETS:
        fig_cssed(t)
    fig_fva()
    fig_r2_heatmap()
    fig_lasso_heat()
    print('figures done')
