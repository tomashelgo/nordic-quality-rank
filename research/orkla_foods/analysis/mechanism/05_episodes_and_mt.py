"""Section 5: episode anatomy of cost shocks and the multiple-testing summary (lens-mechanism).

(a) Episodes: runs of quarters with raw-material inflation in local currency >= 10% y/y (one-quarter
    gaps bridged). For each: cost peak, margin trough, first non-negative y/y margin change after the
    trough, and the peaks of manufacturer (PPI) and retail (CPI ex VAT) food-price inflation and
    Orkla's own price component (2022Q2+), with lags measured from the cost peak.
(b) Multiple testing: all p-values written by 01-04 (mt_tests_*.csv and the Clark-West tests in
    rt_oos.csv), Benjamini-Yekutieli and Holm within each family and across everything.

Outputs: episodes.csv, mt_summary_by_family.csv, mt_all_tests.csv
"""
import numpy as np
import pandas as pd

import mech_utils as M

T, F, D, X = M.load_all()
XT = X.reindex(T.index)
idx = T.index[T.index >= pd.Period('2001Q1', 'Q')]
raw = XT.loc[idx, 'raw_mat_wloc_yoy']
hot = (raw >= 10).astype(int)
# bridge single-quarter gaps
hot = ((hot == 1) | ((hot.shift(1) == 1) & (hot.shift(-1) == 1))).astype(int)
runs, cur = [], []
for p, v in hot.items():
    if v:
        cur.append(p)
    elif cur:
        runs.append(cur); cur = []
if cur:
    runs.append(cur)


def argmax_in(s, a, b):
    w = s[(s.index >= a) & (s.index <= b)].dropna()
    return (w.idxmax(), w.max()) if len(w) else (None, np.nan)


def argmin_in(s, a, b):
    w = s[(s.index >= a) & (s.index <= b)].dropna()
    return (w.idxmin(), w.min()) if len(w) else (None, np.nan)


rows = []
for r in runs:
    a, b = r[0], r[-1]
    pk, pv = argmax_in(raw, a, b)
    tr, tv = argmin_in(T['d_margin'], a - 1, b + 4)
    rec = None
    if tv is not None and not np.isnan(tv) and tv >= 0:     # no margin decline in this episode
        tr, tv = None, np.nan
    if tr is not None:
        after = T['d_margin'][(T.index > tr)].dropna()
        nonneg = after[after >= 0]
        rec = nonneg.index[0] if len(nonneg) else None
    ppk, ppv = argmax_in(XT['w_food_ppi_yoy'], a, b + 6)
    cpk, cpv = argmax_in(XT['w_food_cpi_xvat_yoy'], a, b + 6)
    opk, opv = argmax_in(T['price'], a, b + 6)
    ogk, ogv = argmax_in(T['og'], a, b + 6)
    lagq = lambda p: (p - pk).n if (p is not None and pk is not None) else np.nan
    rows.append(dict(episode=f'{a}-{b}', n_quarters=len(r), raw_peak_q=str(pk), raw_peak_yoy=pv,
                     cost_idx_peak=XT.loc[a:b, 'cost_idx_calib_yoy'].max(),
                     margin_trough_q=str(tr), margin_trough_pp=tv, lag_trough_vs_cost_peak=lagq(tr),
                     first_nonneg_dmargin_q=str(rec), lag_recovery_vs_cost_peak=lagq(rec),
                     sum_dmargin_episode_plus4=T['d_margin'][(T.index >= a) & (T.index <= b + 4)].sum(),
                     ppi_peak_q=str(ppk), ppi_peak=ppv, lag_ppi_peak=lagq(ppk),
                     cpi_xvat_peak_q=str(cpk), cpi_xvat_peak=cpv, lag_cpi_peak=lagq(cpk),
                     orkla_price_peak_q=str(opk) if opk is not None else '', orkla_price_peak=opv, lag_orkla_price_peak=lagq(opk),
                     og_peak_q=str(ogk), og_peak=ogv, lag_og_peak=lagq(ogk),
                     drivers_note_at_trough=M.C.load_orkla()['drivers_note'].get(tr, '') if tr is not None else ''))
ep = pd.DataFrame(rows)
ep.to_csv(f'{M.OUTDIR}/episodes.csv', index=False, float_format='%.3g')
pd.set_option('display.width', 250)
print(ep.drop(columns=['drivers_note_at_trough']).to_string(float_format=lambda v: f'{v:.3g}'))

# ----------------------------------------------------------------------------- multiple testing
parts = []
for f in ['mt_tests_passthrough.csv', 'mt_tests_organic.csv', 'mt_tests_text.csv']:
    d = pd.read_csv(f'{M.OUTDIR}/{f}')
    d['source'] = f
    parts.append(d)
rt = pd.read_csv(f'{M.OUTDIR}/rt_oos.csv')
rt = rt[rt['cw_p'].notna()]
parts.append(pd.DataFrame({'family': 'rt_clark_west_' + rt['target'], 'test': rt['model'] + '|h' + rt['h'].astype(str),
                           'sample': rt['evaluation'], 'stat': rt['cw_stat'], 'df': 1, 'p': rt['cw_p'], 'n': rt['n_oos'],
                           'source': 'rt_oos.csv'}))
A = pd.concat(parts, ignore_index=True)
A = A[A['p'].notna()]
A['p_BY_family'] = np.nan
A['p_Holm_family'] = np.nan
for fam, g in A.groupby('family'):
    A.loc[g.index, 'p_BY_family'] = M.mt_adjust(g['p'], 'fdr_by')
    A.loc[g.index, 'p_Holm_family'] = M.mt_adjust(g['p'], 'holm')
A['p_BY_global'] = M.mt_adjust(A['p'], 'fdr_by')
A['p_Holm_global'] = M.mt_adjust(A['p'], 'holm')
A.to_csv(f'{M.OUTDIR}/mt_all_tests.csv', index=False, float_format='%.4g')
S = A.groupby('family').agg(n_tests=('p', 'size'), n_p05=('p', lambda v: int((v < 0.05).sum())),
                            n_BY05_family=('p_BY_family', lambda v: int((v < 0.05).sum())),
                            n_Holm05_family=('p_Holm_family', lambda v: int((v < 0.05).sum())),
                            n_BY05_global=('p_BY_global', lambda v: int((v < 0.05).sum()))).reset_index()
tot = pd.DataFrame([dict(family='TOTAL', n_tests=len(A), n_p05=int((A.p < 0.05).sum()),
                         n_BY05_family=int((A.p_BY_family < 0.05).sum()), n_Holm05_family=int((A.p_Holm_family < 0.05).sum()),
                         n_BY05_global=int((A.p_BY_global < 0.05).sum()))])
S = pd.concat([S, tot], ignore_index=True)
S.to_csv(f'{M.OUTDIR}/mt_summary_by_family.csv', index=False)
print(S.to_string())
print(A.sort_values('p').head(40)[['family', 'test', 'sample', 'p', 'p_BY_family', 'p_BY_global']].to_string())
