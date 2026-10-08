"""Stage 4 (addendum): live forecasts with the information available today (2026-10-06).

Orkla has reported up to 2026Q2. As of today:
  h=0 -> 2026Q3 (nowcast before the Q3 report), h=1 -> 2026Q4, h=2 -> 2027Q1.
Models are estimated on all rows <= 2026Q2 with exactly the same specification as in the OOS exercise.
Features not yet published (e.g. September CPI, due ~10 Oct) are NaN, so a model needing them is skipped.
Output: live_forecasts.csv
"""
import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import warnings
import numpy as np
import pandas as pd

import oos_lib as L

warnings.filterwarnings('ignore')
C = L.C

T0 = C.load_targets()
F, D = C.load_features(core_only=True)
ext = pd.period_range('2000Q1', '2027Q1', freq='Q')
T = T0.reindex(ext)
# Calendar for the future quarters (Easter 2026 = 5 Apr, Easter 2027 = 28 Mar; window = Palm Sunday..Easter Monday)
T.loc[pd.Period('2026Q3', 'Q'), ['easter_shift', 'd_easter_window_q1']] = [0, 0.0]
T.loc[pd.Period('2026Q4', 'Q'), ['easter_shift', 'd_easter_window_q1']] = [0, 0.0]
T.loc[pd.Period('2027Q1', 'Q'), ['easter_shift', 'd_easter_window_q1']] = [1, 1.0 - 3 / 9]
for c in ['w_og', 'w_d_og']:
    T[c] = T[c].fillna(0.0)
Fx = F.reindex(ext)
X = {h: C.align(Fx, D, 'realtime', h) for h in L.HS}
TARGET_Q = {0: pd.Period('2026Q3', 'Q'), 1: pd.Period('2026Q4', 'Q'), 2: pd.Period('2027Q1', 'Q')}

res = pd.read_csv(f'{L.OUT}/oos_results.csv')
fc_all = pd.read_csv(f'{L.OUT}/forecasts_all.csv.gz')
rows = []
ok = L.train_ok_mask(ext)
for tgt in L.TARGETS:
    y = T[tgt].values.astype(float)
    w = L.target_weights(T, tgt).values
    for h in L.HS:
        tq = TARGET_Q[h]
        i = list(ext).index(tq)
        var = L.PRIMARY[tgt]
        B = L.base_frame(T, tgt, h, var)
        fv = fc_all[(fc_all.target == tgt) & (fc_all.h == h) & (fc_all.variant == var)]
        out = {}
        out['ar'] = L.ExpandingWLS(y, L.ar_frame(T, tgt, h).values, w, ok).forecast(i, h, 12)
        out['arcal'] = L.ExpandingWLS(y, pd.concat([L.ar_frame(T, tgt, h), L.calendar_frame(T, tgt)], axis=1).values,
                                      w, ok).forecast(i, h, 12)
        out['rw'] = T[tgt].shift(h + 1).iloc[i]
        out['mean'] = L.ExpandingWLS(y, np.zeros((len(y), 0)), w, ok).forecast(i, h, 8)
        if tgt == 'd_og':
            out['ar_oglev'] = L.ExpandingWLS(y, B.values, w, ok).forecast(i, h, 12)
        for name, feats in L.THEORY[tgt].items():
            Z = pd.concat([B] + [X[h][f] for f in feats], axis=1)
            out[name] = L.ExpandingWLS(y, Z.values, w, ok).forecast(i, h, 12)
        # univariate p=1 forecasts and the real-time top-k combination (ranking from past OOS errors <= 2026Q2)
        uni = {}
        for f in X[h].columns:
            Z = pd.concat([B, X[h][f]], axis=1)
            uni[f'uni_p1__{f}'] = L.ExpandingWLS(y, Z.values, w, ok).forecast(i, h, 12)
        uni = pd.Series(uni)
        past = fv[fv.model.str.startswith('uni_p1__')].copy()
        past['e2'] = (past['actual'] - past['forecast']) ** 2
        mse = past.groupby('model')['e2'].mean()
        cnt = past.groupby('model')['e2'].count()
        elig = [m for m in uni.index[uni.notna()] if cnt.get(m, 0) >= 8]
        order = mse[elig].sort_values().index
        # re-select k with the combinations' full track record up to 2026Q2
        combos = fv[fv.model.isin(
            ['comb_top1', 'comb_top3', 'comb_top5', 'comb_top10', 'comb_top20', 'comb_all_mean'])].copy()
        combos['e2'] = (combos['actual'] - combos['forecast']) ** 2
        best = combos.groupby('model')['e2'].mean().idxmin()
        out['comb_all_mean'] = uni.mean()
        for k in (1, 3, 5, 10, 20):
            out[f'comb_top{k}'] = uni[order[:k]].mean()
        out['comb_adaptive'] = out[best]
        out['comb_adaptive_k'] = best
        out['comb_top5_members'] = ';'.join(o.replace('uni_p1__', '') for o in order[:5])
        out['n_uni_available'] = int(uni.notna().sum())
        for k, v in out.items():
            rows.append({'target': tgt, 'h': h, 'target_quarter': str(tq), 'model': k, 'value': v})
L_ = pd.DataFrame(rows)
L_.to_csv(f'{L.OUT}/live_forecasts.csv', index=False)
num = L_[L_.model.isin(['ar', 'arcal', 'ar_oglev', 'rw', 'mean', 'comb_adaptive', 'comb_all_mean'] +
                        [m for t in L.THEORY for m in L.THEORY[t]])].copy()
num['value'] = pd.to_numeric(num['value'])
print(num.pivot_table(index=['target', 'model'], columns='target_quarter', values='value').round(2).to_string())
print(L_[L_.model.isin(['comb_adaptive_k', 'comb_top5_members', 'n_uni_available'])].to_string())
