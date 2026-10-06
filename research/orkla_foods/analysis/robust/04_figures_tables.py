"""Step 4: figures and summary tables for the robustness lens.

Figures
  fig_rolling_<target>.png   rolling 32-quarter correlation (target residualised on controls vs x)
                             for the leading candidates of each target; 2021Q3-2023Q4 shaded.
  fig_subsamples_<target>.png sub-sample betas (+/- 1.96 HAC s.e.) for the same candidates.
  fig_placebo_size.png       how often a nominal 5% HAC(4) test rejects with an independent persistent
                             regressor, against the feature's AR(1) (size distortion).
Tables
  episode_dependence.csv     per target: how much the 2021Q3-2023Q4 episode drives significant rows.
  persistence_vs_class.csv   classification by feature persistence.
  plot_candidates.csv        the candidates shown in the figures.
  fig_apriori_class_grid.png classification of every a-priori hypothesis x target x alignment.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import robust_lib as R

INK, INK2, GRID = '#0b0b0b', '#52514e', '#e5e4e0'
BLUE, ORANGE, AQUA, VIOLET, RED = '#2a78d6', '#eb6834', '#1baf7a', '#4a3aa7', '#e34948'
CLS_COL = {'ROBUST': AQUA, 'FRAGILE': ORANGE, 'SPURIOUS': RED, 'NO_EFFECT': INK2}

B = pd.read_csv(f'{R.OUT}/robust_summary.csv', keep_default_na=False, na_values=[''])
P = pd.read_csv(f'{R.OUT}/robust_summary_by_pair.csv', keep_default_na=False, na_values=[''])
RO = pd.read_csv(f'{R.OUT}/rolling_32q.csv')
RO['end'] = pd.PeriodIndex(RO['window_end'], freq='Q').to_timestamp(how='end')

FIXED = {  # a-priori hypotheses always shown (best alignment of the pair)
    'd_margin': ['w_real_wage_yoy', 'price_cost_gap_ppi', 'w_food_ppi_yoy'],
    'og': ['w_real_wage_yoy', 'w_cons_conf_z', 'w_policy_rate_lvl'],
    'd_og': ['w_real_wage_dyoy', 'price_cost_gap_ppi', 'w_cons_conf_z_d4'],
    'vol_proxy': ['w_real_wage_yoy', 'w_cons_conf_z_d4', 'w_unemp_lvl'],
}


def style(ax):
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    for sp in ['left', 'bottom']:
        ax.spines[sp].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8)


plot_rows = []
for tgt in R.TARGETS:
    p = P[(P.target == tgt) & (P.best_class == 'ROBUST')].sort_values('p_cal')
    chosen = list(p['candidate'].head(5))
    for f in FIXED[tgt]:
        if f not in chosen:
            chosen.append(f)
    for f in chosen:
        r = P[(P.target == tgt) & (P.candidate == f)].iloc[0]
        plot_rows.append(dict(target=tgt, candidate=f, alignment=r['best_alignment'], best_class=r['best_class']))
PC = pd.DataFrame(plot_rows)
PC.to_csv(f'{R.OUT}/plot_candidates.csv', index=False)

for tgt in R.TARGETS:
    pc = PC[PC.target == tgt]
    n = len(pc)
    ncol = 4
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(15, 3.1 * nrow), sharex=True, sharey=True)
    axes = np.atleast_1d(axes).ravel()
    for ax, (_, r) in zip(axes, pc.iterrows()):
        d = RO[(RO.target == tgt) & (RO.candidate == r['candidate']) & (RO.alignment == r['alignment'])]
        ax.axvspan(pd.Timestamp('2021-07-01'), pd.Timestamp('2023-12-31'), color=GRID, alpha=0.9, lw=0)
        ax.axhline(0, color=INK2, lw=0.8)
        ax.plot(d['end'], d['corr'], color=BLUE, lw=2)
        row = B[(B.target == tgt) & (B.candidate == r['candidate']) & (B.alignment == r['alignment'])].iloc[0]
        ax.set_title(f"{r['candidate']} [{r['alignment']}]", fontsize=8.5, color=INK, loc='left')
        ax.text(0.02, 0.04, f"{row['classification']}  full t={row['t']:.1f}, ex-21Q3-23Q4 t={row['t_ex_infl']:.1f}",
                transform=ax.transAxes, fontsize=7.5, color=INK2)
        ax.set_ylim(-1, 1)
        style(ax)
    for ax in axes[n:]:
        ax.set_visible(False)
    fig.suptitle(f'{tgt}: rolling 32-quarter correlation with candidate (target residualised on definition, '
                 f'COVID and Easter controls; grey = 2021Q3-2023Q4)', fontsize=10, color=INK, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(f'{R.OUT}/fig_rolling_{tgt}.png', dpi=130)
    plt.close(fig)

# sub-sample forest plots
SUBS = [('full', 'beta_sd', 't'), ('A 2001-07', 'b_A_2001_07', 't_A_2001_07'),
        ('B/C 2008-14Q3', 'b_BC_2008_14', 't_BC_2008_14'), ('D 2014Q4-22Q2', 'b_D_2014Q4_22Q2', 't_D_2014Q4_22Q2'),
        ('E 2022Q3-26', 'b_E_2022Q3_26', 't_E_2022Q3_26'), ('pre-2013', 'b_pre2013', 't_pre2013'),
        ('post-2013', 'b_post2013', 't_post2013'), ('ex COVID', 'b_ex_covid', 't_ex_covid'),
        ('ex 21Q3-23Q4', 'b_ex_infl', 't_ex_infl'), ('ex both', 'b_ex_covid_infl', 't_ex_covid_infl'),
        ('Q4 only', 'b_q4', 't_q4'), ('annual avg', 'b_ann', 't_ann')]
for tgt in R.TARGETS:
    pc = PC[PC.target == tgt]
    n = len(pc)
    ncol = 4
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(15, 3.6 * nrow), sharey=True)
    axes = np.atleast_1d(axes).ravel()
    for ax, (_, r) in zip(axes, pc.iterrows()):
        row = B[(B.target == tgt) & (B.candidate == r['candidate']) & (B.alignment == r['alignment'])].iloc[0]
        ys = np.arange(len(SUBS))[::-1]
        for yv, (lab, bc, tc) in zip(ys, SUBS):
            b, t = row.get(bc), row.get(tc)
            if pd.isna(b) or pd.isna(t) or t == 0:
                continue
            se = abs(b / t)
            col = BLUE if lab == 'full' else (VIOLET if lab in ('Q4 only', 'annual avg') else INK2)
            ax.plot([b - 1.96 * se, b + 1.96 * se], [yv, yv], color=col, lw=1.5, alpha=0.8)
            ax.plot(b, yv, 'o', color=col, ms=5, mec='white', mew=1)
        ax.axvline(0, color=INK2, lw=0.8)
        ax.set_yticks(ys)
        ax.set_yticklabels([s[0] for s in SUBS], fontsize=7.5)
        ax.set_title(f"{r['candidate']} [{r['alignment']}]\n{row['classification']}", fontsize=8.5, color=INK, loc='left')
        ax.set_xlabel('beta per full-sample SD of x', fontsize=7.5, color=INK2)
        style(ax)
    for ax in axes[n:]:
        ax.set_visible(False)
    fig.suptitle(f'{tgt}: sub-sample estimates (bars: +/-1.96 HAC s.e.; annual/Q4: HAC 1 lag)', fontsize=10,
                 color=INK, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(f'{R.OUT}/fig_subsamples_{tgt}.png', dpi=130)
    plt.close(fig)

# placebo size distortion
fig, ax = plt.subplots(figsize=(7, 4))
ax.scatter(B['ar1_feature'], B['placebo_size_5pct'], s=10, color=BLUE, alpha=0.5, linewidths=0)
ax.axhline(0.05, color=INK2, lw=1, ls='--')
ax.text(B['ar1_feature'].min(), 0.057, 'nominal 5%', fontsize=8, color=INK2)
ax.set_xlabel('feature AR(1) coefficient')
ax.set_ylabel('rejection rate of nominal 5% HAC(4) t-test\nwith an independent AR(2) placebo regressor')
ax.set_title(f"Size distortion: median rejection rate {B['placebo_size_5pct'].median():.0%} (1,046 rows x 400 placebos)",
             fontsize=9.5, loc='left')
style(ax)
fig.tight_layout()
fig.savefig(f'{R.OUT}/fig_placebo_size.png', dpi=130)
plt.close(fig)

# episode dependence table
sig = B[B['p'] < 0.05]
ep = sig.groupby('target').apply(lambda d: pd.Series(dict(
    n_hac_significant=len(d),
    share_ex_infl_same_sign_p10=((np.sign(d['b_ex_infl']) == np.sign(d['beta_sd'])) & (d['p_ex_infl'] < 0.10)).mean(),
    share_ex_infl_sign_flip=(np.sign(d['b_ex_infl']) != np.sign(d['beta_sd'])).mean(),
    median_ratio_beta_ex_infl_to_full=(d['b_ex_infl'] / d['beta_sd']).median(),
    median_infl_cov_share=d['infl_cov_share'].median(),
    share_ex_covid_same_sign_p10=((np.sign(d['b_ex_covid']) == np.sign(d['beta_sd'])) & (d['p_ex_covid'] < 0.10)).mean(),
    share_trend_survives=((np.sign(d['beta_trend']) == np.sign(d['beta_sd'])) & (d['p_trend'] < 0.05)).mean(),
    share_annual_same_sign=(np.sign(d['b_ann']) == np.sign(d['beta_sd'])).mean(),
    share_annual_same_sign_p10=((np.sign(d['b_ann']) == np.sign(d['beta_sd'])) & (d['p_ann'] < 0.10)).mean(),
    share_survive_calibration=(d['p_cal'] < 0.05).mean(),
    share_loyo_ok=((d['loyo_n_sign_flip'] == 0) & (d['loyo_max_p'] < 0.10)).mean(),
    share_sign_flip_break=d['break_sign_flip'].astype(bool).mean(),
)), include_groups=False)
ep.to_csv(f'{R.OUT}/episode_dependence.csv')
print(ep.round(2).T.to_string())

B['ar1_bin'] = pd.cut(B['ar1_feature'], [-1, 0.5, 0.8, 0.9, 1.0], labels=['<0.5', '0.5-0.8', '0.8-0.9', '>0.9'])
pv = pd.crosstab(B['ar1_bin'], B['classification'], normalize='index').round(3)
pv['n'] = B['ar1_bin'].value_counts()
hs = B[B.p < 0.05]
pv['share_hac_sig_rows_failing_or_borderline_calibration'] = hs.groupby('ar1_bin', observed=False).apply(
    lambda d: d['reasons'].str.contains('persistence').mean(), include_groups=False).round(3)
pv.to_csv(f'{R.OUT}/persistence_vs_class.csv')
print(pv.to_string())

# classification grid for the a-priori hypotheses (all targets x alignments)
src = open(f'{R.OUT}/02_battery.py').read()  # read the APRIORI dict from the battery script
apr_block = src[src.index('APRIORI = {'):src.index('APRIORI_GROUP')]
ns = {}
exec(apr_block, ns)
apr_feats = [f for fs in ns['APRIORI'].values() for f in fs]
groups = [g for g, fs in ns['APRIORI'].items() for f in fs]
aligns = ['coincident', 'rt_h0', 'rt_h1', 'rt_h2', 'rt_h4']
GRID_COL = {'ROBUST': AQUA, 'FRAGILE': ORANGE, 'SPURIOUS': RED, 'NO_EFFECT': '#ecebe7'}
fig, axes = plt.subplots(1, 4, figsize=(17, 13), sharey=True)
for ax, tgt in zip(axes, R.TARGETS):
    for i, f in enumerate(apr_feats):
        for j, a in enumerate(aligns):
            r = B[(B.target == tgt) & (B.candidate == f) & (B.alignment == a)]
            if r.empty:
                if a == 'rt_h0':
                    ax.text(j, i, '=co', ha='center', va='center', fontsize=6, color=INK2)
                continue
            r = r.iloc[0]
            ax.add_patch(plt.Rectangle((j - 0.46, i - 0.42), 0.92, 0.84, color=GRID_COL[r['classification']], lw=0))
            txt = r['sign'] if r['classification'] != 'NO_EFFECT' else ''
            if r['classification'] == 'FRAGILE' and r['fragile_type'] == 'fdr_only':
                txt += '*'
            ax.text(j, i, txt, ha='center', va='center', fontsize=7, color=INK)
    ax.set_xlim(-0.5, len(aligns) - 0.5)
    ax.set_ylim(len(apr_feats) - 0.5, -0.5)
    ax.set_xticks(range(len(aligns)))
    ax.set_xticklabels(['co', 'h0', 'h1', 'h2', 'h4'], fontsize=8)
    ax.xaxis.tick_top()
    ax.set_title(tgt, fontsize=10, color=INK, pad=18)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
axes[0].set_yticks(range(len(apr_feats)))
axes[0].set_yticklabels([f'{f}  ({g})' for f, g in zip(apr_feats, groups)], fontsize=7)
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in GRID_COL.values()]
fig.legend(handles, list(GRID_COL), loc='lower center', ncol=4, frameon=False, fontsize=9)
fig.suptitle('A-priori hypotheses: classification by target and alignment (sign shown; * = FRAGILE only because it '
             'fails FDR; "=co" = lag-0 feature, h0 identical to coincident)', fontsize=10, x=0.01, ha='left')
fig.tight_layout(rect=(0, 0.03, 1, 0.97))
fig.savefig(f'{R.OUT}/fig_apriori_class_grid.png', dpi=120)
plt.close(fig)

# break-test summary (HAC-significant rows)
bt = []
for tgt in R.TARGETS:
    for cls in ['ALL_SIG', 'ROBUST', 'FRAGILE']:
        d = B[(B.target == tgt) & (B.p < 0.05)]
        if cls != 'ALL_SIG':
            d = d[d.classification == cls]
        if d.empty:
            continue
        yr = pd.PeriodIndex(d['supW_date'], freq='Q').year
        bt.append(dict(target=tgt, rows=cls, n=len(d),
                       share_chow_eras_p05=(d['chow_eras_p'] < 0.05).mean(),
                       share_chow_2008Q1_p05=(d['chow_p_2008Q1'] < 0.05).mean(),
                       share_chow_2013Q1_p05=(d['chow_p_2013Q1'] < 0.05).mean(),
                       share_chow_2014Q4_p05=(d['chow_p_2014Q4'] < 0.05).mean(),
                       share_chow_2022Q3_p05=(d['chow_p_2022Q3'] < 0.05).mean(),
                       share_supW_sig5=d['supW_sig5'].astype(bool).mean(),
                       share_supW_sign_flip=d['break_sign_flip'].astype(bool).mean(),
                       supW_date_2004_07=((yr >= 2004) & (yr <= 2007)).mean(),
                       supW_date_2020_23=((yr >= 2020) & (yr <= 2023)).mean()))
BT = pd.DataFrame(bt)
BT.to_csv(f'{R.OUT}/break_tests_summary.csv', index=False)
print(BT.round(2).to_string())
