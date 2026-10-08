"""Step 3: multiple-testing control and ROBUST / FRAGILE / SPURIOUS / NO_EFFECT classification.

Inputs: battery_raw.csv (02_battery.py), screen_all.csv (01_screen.py).

Persistence-calibrated p-values. The AR(2) placebo in the battery shows that a nominal 5% HAC(4)
test rejects far more often than 5% when an independent but persistent regressor replaces x
(typical rejection rate ~18%). Each row's |t| is therefore deflated by the spread of its own
placebo distribution: p_cal = 2*(1 - Phi(1.96*|t| / t95_placebo)), where t95_placebo is the 95th
percentile of the placebo |t|. p_cal is ~equal to the empirical placebo p-value but continuous,
so it can enter false-discovery control.

FDR (Benjamini-Yekutieli, valid under arbitrary dependence). The decisive family is ONE family per
target: the union of every screen test (200 core features x coincident / rt h0 / rt h1, 492 tests)
and every additional battery test (h=2 and h=4 rows, non-core a-priori features), ~600 tests per
target. Battery rows use their own placebo-calibrated p_cal; screen rows not in the battery use the
target's median placebo spread. This charges data-selected candidates for the selection step and
treats a-priori and screened variables identically.  -> q_by_target_family, fdr_pass = q < 0.10.
Also reported (information only): q_by_battery (all 1,046 battery rows pooled), q_by_apriori and
holm_apriori (the 46 pre-specified features x alignments, per target), q_by_screen_cal (screen only).

Classification of each candidate x target x alignment row:
  NO_EFFECT HAC p >= 0.05 (no evidence in the full sample).
  SPURIOUS  HAC p < 0.05 but an artefact explains it: (T1) persistence - p_cal >= 0.10;
            (T2) common trend - sign flips or p > 0.30 once a linear trend is added;
            (T3) episode artefact - the estimate excluding 2021Q3-2023Q4 has the opposite sign with
            |t| >= 1; (T4) overlap - the non-overlapping annual estimate has the opposite sign with |t| >= 1;
            (T5) mechanical - for vol_proxy (= og - food CPI) any food-CPI feature.
  ROBUST    p_cal < 0.05, fdr_pass, all core checks pass and at most one soft check fails.
            Core: (C1) same sign in >= 3 of the 4 definition eras; (C2) ex-2021Q3-2023Q4 same sign,
            p < 0.10; (C3) leave-one-year-out never flips the sign and max p < 0.10; (C4) with linear
            trend same sign, p < 0.05; (C5) no sign-reversing slope break (Quandt-Andrews 5%).
            Soft: (S1) ex-COVID same sign p < 0.10; (S2) non-overlapping annual or Q4-only estimate
            same sign p < 0.10; (S3) rolling-32Q slope same sign in >= 80% of windows; (S4) same sign
            pre and post 2013; (S5) survives the own-history control (latest known Orkla value)
            with p < 0.05; (S6) excluding both 2020-21 and 2021Q3-2023Q4 same sign, p < 0.10.
  FRAGILE   everything else that is HAC-significant and not SPURIOUS (fails FDR, borderline
            calibration 0.05 <= p_cal < 0.10, a core check or >= 2 soft checks).

Outputs: robust_summary.csv (all rows), robust_summary_by_pair.csv, fdr_counts.csv
"""
import numpy as np
import pandas as pd
from scipy import stats
import robust_lib as R

B = pd.read_csv(f"{R.OUT}/battery_raw.csv").copy()
import warnings
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
S = pd.read_csv(f'{R.OUT}/screen_all.csv')

B['placebo_scale'] = B['placebo_t95'] / 1.96
B['p_cal'] = 2 * (1 - stats.norm.cdf(B['t'].abs() / B['placebo_scale']))
B['q_by_battery'] = R.by_qvalues(B['p_cal'].values)
apr = B['source'].str.contains('a_priori')
B['q_by_apriori'] = np.nan
B['holm_apriori'] = np.nan
for tgt in B['target'].unique():  # a-priori family = pre-specified rows of one target
    m = apr & (B['target'] == tgt)
    B.loc[m, 'q_by_apriori'] = R.by_qvalues(B.loc[m, 'p_cal'].values)
    B.loc[m, 'holm_apriori'] = R.holm(B.loc[m, 'p_cal'].values)

# calibrated screen family
scale_t = B.groupby('target')['placebo_scale'].median()
S['p_cal'] = 2 * (1 - stats.norm.cdf(S['t'].abs() / S['target'].map(scale_t)))
S['q_by_screen_cal'] = np.nan
for tgt in S['target'].unique():
    m = S['target'] == tgt
    S.loc[m, 'q_by_screen_cal'] = R.by_qvalues(S.loc[m, 'p_cal'].values)
B = B.merge(S[['target', 'feature', 'alignment', 'q_by_screen_cal']].rename(columns={'feature': 'candidate'}),
            on=['target', 'candidate', 'alignment'], how='left')
# unified per-target family: screen tests + battery-only tests
fam_rows = []
for tgt in R.TARGETS:
    s_ = S[S.target == tgt][['feature', 'alignment', 'p_cal']].rename(columns={'feature': 'candidate'})
    b_ = B[B.target == tgt][['candidate', 'alignment', 'p_cal']]
    u = pd.concat([b_, s_]).drop_duplicates(['candidate', 'alignment'], keep='first')
    u['q_by_target_family'] = R.by_qvalues(u['p_cal'].values)
    u['target'] = tgt
    u['family_size'] = len(u)
    fam_rows.append(u)
FAM = pd.concat(fam_rows)
B = B.merge(FAM[['target', 'candidate', 'alignment', 'q_by_target_family', 'family_size']],
            on=['target', 'candidate', 'alignment'], how='left')
B['fdr_pass'] = B['q_by_target_family'] < 0.10

# SD of the aligned feature over each row's regression sample (beta per unit = beta_sd / x_sd)
C = R.C
T = R.load_T()
Fall, Dall = C.load_features(core_only=False)
feats = sorted(B['candidate'].unique())
AL = {a: C.align(Fall[feats], Dall.loc[feats], m, h) for a, m, h in
      [('coincident', 'coincident', 0), ('rt_h0', 'realtime', 0), ('rt_h1', 'realtime', 1),
       ('rt_h2', 'realtime', 2), ('rt_h4', 'realtime', 4)]}
xsd = []
for _, r in B.iterrows():
    yv, Xv, wv, idx = R.frame(T[r['target']], AL[r['alignment']][r['candidate']],
                              R.controls_for(r['target'], T), R.weights_for(r['target'], T))
    xsd.append(Xv[:, 0].std())
B['x_sd'] = xsd
B['beta_per_unit'] = B['beta_sd'] / B['x_sd']
sg = np.sign(B['beta_sd'])
same = lambda col: np.sign(B[col]) == sg  # noqa: E731
eras = ['A_2001_07', 'BC_2008_14', 'D_2014Q4_22Q2', 'E_2022Q3_26']
era_b = B[[f'b_{e}' for e in eras]]
B['eras_estimable'] = era_b.notna().sum(axis=1)
B['eras_same_sign'] = sum((np.sign(B[f'b_{e}']) == sg).astype(int) for e in eras)
B['era_signs'] = era_b.apply(lambda r: ''.join('+' if v > 0 else '-' if v < 0 else '.' for v in r), axis=1)

chk = pd.DataFrame(index=B.index)
chk['C1_eras'] = (B['eras_same_sign'] >= 3) | ((B['eras_estimable'] < 4) & (B['eras_same_sign'] == B['eras_estimable']))
chk['C2_ex_infl'] = same('b_ex_infl') & (B['p_ex_infl'] < 0.10)
chk['C3_loyo'] = (B['loyo_n_sign_flip'] == 0) & (B['loyo_max_p'] < 0.10)
chk['C4_trend'] = same('beta_trend') & (B['p_trend'] < 0.05)
B['break_sign_flip'] = B['supW_sig5'] & (np.sign(B['b_pre_supW']) != np.sign(B['b_post_supW']))
chk['C5_no_flip_break'] = ~B['break_sign_flip']
chk['S1_ex_covid'] = same('b_ex_covid') & (B['p_ex_covid'] < 0.10)
chk['S2_nonoverlap'] = (same('b_ann') & (B['p_ann'] < 0.10)) | (same('b_q4') & (B['p_q4'] < 0.10))
chk['S3_rolling'] = B['roll_share_same_sign'] >= 0.8
chk['S4_pre_post_2013'] = same('b_pre2013') & same('b_post2013')
chk['S5_own_history'] = same('b_own') & (B['p_own'] < 0.05)
chk['S6_ex_covid_and_infl'] = same('b_ex_covid_infl') & (B['p_ex_covid_infl'] < 0.10)
core = [c for c in chk if c.startswith('C')]
soft = [c for c in chk if c.startswith('S')]
B = pd.concat([B, chk], axis=1)
B['n_checks_passed'] = chk.sum(axis=1)
B['core_fail'] = chk[core].apply(lambda r: ','.join(c for c in core if not r[c]), axis=1)
B['soft_fail'] = chk[soft].apply(lambda r: ','.join(c for c in soft if not r[c]), axis=1)
B['n_soft_fail'] = (~chk[soft]).sum(axis=1)

# vol_proxy = og - w_food_cpi_xvat_yoy: food-CPI features are (near-)components of the target.
MECH = {'w_food_cpi_xvat_yoy', 'w_food_cpi_yoy', 'nw_food_cpi_xvat_yoy', 'nw_food_cpi_yoy',
        'w_food_cpi_xvat_dyoy', 'w_food_cpi_dyoy', 'nw_food_cpi_xvat_dyoy', 'ea_hicp_food_idx__yoy',
        'w_food_cpi_rel_yoy', 'w_food_cpi_rel_dyoy', 'w_cpi_yoy'}
B['mechanical'] = (B['target'] == 'vol_proxy') & B['candidate'].isin(MECH)
B['survives_channel'] = np.where(B['t_chan'].isna(), np.nan, (same('b_chan') & (B['p_chan'] < 0.05)).astype(float))
T1 = B['p_cal'] >= 0.10
T2 = (~same('beta_trend')) | (B['p_trend'] > 0.30)
T3 = (~same('b_ex_infl')) & (B['t_ex_infl'].abs() >= 1.0)
T4 = (~same('b_ann')) & (B['t_ann'].abs() >= 1.0)
sig = B['p'] < 0.05

cls, why = [], []
for i in B.index:
    r = B.loc[i]
    if r['mechanical'] and sig[i]:
        cls.append('SPURIOUS')
        why.append('mechanical: vol_proxy is constructed as og minus food CPI, so food-CPI features enter the target by construction')
        continue
    if not sig[i]:
        cls.append('NO_EFFECT')
        why.append(f"full-sample HAC p={r['p']:.2f}" + (' (weak, p<0.10)' if r['p'] < 0.10 else ''))
        continue
    trig = []
    if T1[i]:
        trig.append(f"persistence: calibrated p={r['p_cal']:.2f} (placebo 95% |t|={r['placebo_t95']:.2f})")
    if T2[i]:
        trig.append(f"trend: t={r['t_trend']:.1f} with linear trend")
    if T3[i]:
        trig.append(f"episode artefact: ex-2021Q3-23Q4 beta={r['b_ex_infl']:.2f} (t={r['t_ex_infl']:.1f}) opposite sign")
    if T4[i]:
        trig.append(f"overlap: annual non-overlapping beta opposite sign (t={r['t_ann']:.1f})")
    if trig:
        cls.append('SPURIOUS')
        why.append('; '.join(trig))
        continue
    reasons = []
    if r['p_cal'] >= 0.05:
        reasons.append(f"borderline after persistence calibration (p_cal={r['p_cal']:.3f})")
    if not r['fdr_pass']:
        reasons.append('fails FDR (BY q>=0.10)')
    if r['core_fail']:
        reasons.append('core fail: ' + r['core_fail'])
    if r['n_soft_fail'] > 1:
        reasons.append('soft fails: ' + r['soft_fail'])
    if reasons:
        cls.append('FRAGILE')
        why.append('; '.join(reasons))
    else:
        cls.append('ROBUST')
        why.append('passes all core checks' + (f"; soft fail: {r['soft_fail']}" if r['soft_fail'] else '; passes all soft checks'))
B['classification'] = cls
B['reasons'] = why
# FRAGILE sub-type: 'fdr_only' = stable on every core check (and <= 1 soft fail) but not FDR-significant
ft = np.where(B['classification'] != 'FRAGILE', '',
              np.where((B['core_fail'] == '') & (B['n_soft_fail'] <= 1) & (B['p_cal'] < 0.05), 'fdr_only',
                       np.where(B['p_cal'] >= 0.05, 'borderline_calibration', 'unstable')))
B['fragile_type'] = ft
# usable in real time? (realtime alignments, or coincident for features published within ~2 weeks)
B['realtime_usable'] = (B['alignment'] != 'coincident') | (B['lag_q'] == 0)
B['channel_note'] = np.where(B['survives_channel'] == 0,
                             'proxy: insignificant once the same-quarter ' +
                             B['target'].map({'d_margin': 'food PPI (cost channel)', 'og': 'food CPI ex VAT (price channel)',
                                              'd_og': 'food CPI ex VAT dyoy (price channel)'}).fillna('') + ' is added',
                             np.where(B['survives_channel'] == 1, 'adds to the same-quarter price/cost channel', ''))
B['sign'] = np.where(B['beta_sd'] > 0, '+', '-')

lead = ['target', 'candidate', 'alignment', 'horizon', 'lag_q', 'source', 'a_priori_group', 'category',
        'classification', 'fragile_type', 'reasons', 'realtime_usable', 'channel_note', 'sign', 'n', 'beta_sd', 'x_sd', 'beta_per_unit', 't', 'p', 'p_cal', 'p_placebo', 'placebo_t95',
        'placebo_size_5pct', 'q_by_target_family', 'family_size', 'q_by_battery', 'q_by_apriori', 'holm_apriori', 'q_by_screen_cal', 'fdr_pass',
        'era_signs', 'eras_same_sign', 'b_A_2001_07', 'b_BC_2008_14', 'b_D_2014Q4_22Q2', 'b_E_2022Q3_26',
        'b_pre2013', 'b_post2013', 'b_ex_covid', 't_ex_covid', 'b_ex_infl', 't_ex_infl', 'b_ex_covid_infl',
        't_ex_covid_infl', 'b_ex_india', 't_ex_india', 'b_infl_only', 'infl_cov_share',
        'chow_p_2008Q1', 'chow_p_2013Q1', 'chow_p_2014Q4', 'chow_p_2022Q3', 'chow_eras_p',
        'supW', 'supW_date', 'supW_sig5', 'b_pre_supW', 'b_post_supW', 'break_sign_flip',
        'loyo_min_abs_t_same_sign', 'loyo_max_p', 'loyo_n_sign_flip', 'loyo_most_influential_year', 'loyo_b_range',
        'b_q4', 't_q4', 'n_q4', 'b_ann', 't_ann', 'n_ann', 'roll_share_same_sign',
        'beta_trend', 't_trend', 'beta_fd', 't_fd', 'b_own', 't_own', 'b_chan', 't_chan', 'survives_channel',
        'mechanical', 't_hac8',
        'granger_p_x_to_y', 'granger_p_y_to_x', 'ar1_feature', 'partial_corr', 'n_checks_passed',
        'core_fail', 'soft_fail'] + core + soft
rest = [c for c in B.columns if c not in lead]
B = B[lead + rest].sort_values(['target', 'classification', 'p_cal'])
B.to_csv(f'{R.OUT}/robust_summary.csv', index=False)

# ------------------------------------------------------------------ by pair
order = {'ROBUST': 0, 'FRAGILE': 1, 'SPURIOUS': 2, 'NO_EFFECT': 3}
pairs = []
for (tgt, f), g in B.groupby(['target', 'candidate']):
    g = g.copy()
    g['o'] = g['classification'].map(order)
    best = g.sort_values(['o', 'p_cal']).iloc[0]
    rt = g[g['alignment'] != 'coincident']
    coin = g[g['alignment'] == 'coincident']
    pairs.append(dict(
        target=tgt, candidate=f, source=best['source'], a_priori_group=best['a_priori_group'],
        best_class=best['classification'], best_alignment=best['alignment'], sign=best['sign'],
        beta_sd=best['beta_sd'], t=best['t'], p_cal=best['p_cal'],
        per_alignment='; '.join(f"{a}:{c}" for a, c in zip(g['alignment'], g['classification'])),
        coincident_class=coin['classification'].iloc[0] if len(coin) else '',
        lag0_feature=bool(g['lag_q'].iloc[0] == 0),
        robust_realtime_horizons=','.join(str(int(h)) for h in rt.loc[rt['classification'] == 'ROBUST', 'horizon']),
        reasons_best=best['reasons']))
P = pd.DataFrame(pairs)
P['o'] = P['best_class'].map(order)
P = P.sort_values(['target', 'o', 'p_cal']).drop(columns='o')
P.to_csv(f'{R.OUT}/robust_summary_by_pair.csv', index=False)

# ------------------------------------------------------------------ counts
cnt = []
for tgt in R.TARGETS:
    s = S[S.target == tgt]
    b = B[B.target == tgt]
    cnt.append(dict(target=tgt, screen_tests=len(s), screen_p05=int((s.p < 0.05).sum()),
                    screen_by_q10_nominal=int((s.q_by_target < 0.10).sum()),
                    screen_by_q10_calibrated=int((s.q_by_screen_cal < 0.10).sum()),
                    target_family_tests=int(FAM[FAM.target == tgt].shape[0]),
                    target_family_q10=int((FAM[FAM.target == tgt].q_by_target_family < 0.10).sum()),
                    battery_rows=len(b), **{f'n_{k}': int((b.classification == k).sum()) for k in order},
                    pairs=int((P.target == tgt).sum()),
                    **{f'pairs_best_{k}': int(((P.target == tgt) & (P.best_class == k)).sum()) for k in order}))
cnt = pd.DataFrame(cnt)
cnt.loc[len(cnt)] = ['ALL'] + [cnt[c].sum() for c in cnt.columns[1:]]
cnt.to_csv(f'{R.OUT}/fdr_counts.csv', index=False)
pd.set_option('display.width', 250)
print(cnt.to_string())
print('battery rows', len(B), 'a-priori rows', int(apr.sum()))
print('median placebo rejection rate of nominal 5% HAC(4) test:', B['placebo_size_5pct'].median().round(3))
print(B.groupby('target')['placebo_t95'].median().round(2))
