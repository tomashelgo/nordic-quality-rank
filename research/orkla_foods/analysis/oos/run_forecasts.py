"""Stage 1: generate all real-time out-of-sample forecasts (lens-oos).

Usage:
  python3 run_forecasts.py linear            # benchmarks + univariate ARDL + theory models, all base variants
  python3 run_forecasts.py multi <variant>   # penalised / PCA / trees for the targets that use <variant>
                                             # (variant in ar, arcal, oglev; see oos_lib.VARIANTS)

Outputs (in this directory):
  forecasts_linear.pkl                long table: target, h, variant, model, family, period, forecast
  forecasts_multi_<variant>.pkl       same layout for the penalised / PCA / ML models
  lasso_selection_raw_<variant>.csv   per origin: selected LASSO / EN features and coefficients
  penalised_alpha_log_<variant>.csv   per origin: chosen penalty, number of candidate features, n_train
"""
import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import sys
import time
import warnings
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

import oos_lib as L

warnings.filterwarnings('ignore')


def positions(index, start, end):
    return [i for i, p in enumerate(index) if start <= p <= end]


# ----------------------------------------------------------------------------------------------
# Benchmarks, univariate ARDL, theory models (all via exact expanding WLS)
# ----------------------------------------------------------------------------------------------
def run_linear(T, X):
    idx = T.index
    pos = positions(idx, L.FIRST_FC, L.LAST)
    periods = idx[pos]
    ok_all = L.train_ok_mask(idx)
    rows = []

    def add(tgt, h, variant, model, family, fc):
        rows.append(pd.DataFrame({'target': tgt, 'h': h, 'variant': variant, 'model': model, 'family': family,
                                  'period': periods, 'forecast': fc}))

    def ewls(tgt, Z, min_train=L.MIN_TRAIN_UNI, ok=ok_all, h=0):
        y = T[tgt].values.astype(float)
        w = L.target_weights(T, tgt).values
        Zv = Z.values if hasattr(Z, 'values') else Z
        return L.ExpandingWLS(y, Zv, w, ok).forecasts(pos, h, min_train)

    for tgt in L.TARGETS:
        y = T[tgt].values.astype(float)
        w = L.target_weights(T, tgt).values
        for h in L.HS:
            t0 = time.time()
            # ---------------- benchmarks
            add(tgt, h, 'bench', 'zero', 'benchmark', np.zeros(len(pos)) if tgt != 'og' else np.full(len(pos), np.nan))
            add(tgt, h, 'bench', 'mean', 'benchmark', ewls(tgt, np.zeros((len(y), 0)), 8, h=h))
            add(tgt, h, 'bench', 'rw', 'benchmark', T[tgt].shift(h + 1).values[pos])
            AR = L.ar_frame(T, tgt, h)
            add(tgt, h, 'bench', 'ar', 'benchmark', ewls(tgt, AR, h=h))
            CAL = L.calendar_frame(T, tgt)
            add(tgt, h, 'bench', 'arcal', 'benchmark', ewls(tgt, pd.concat([AR, CAL], axis=1), h=h))
            # AR with BIC-selected lag set (common estimation sample: rows where all lags h+1..4 exist)
            lagsets = [[], [h + 1], [4], [h + 1, 4], list(range(h + 1, 5))]
            allL = L.ar_frame(T, tgt, h, lags=list(range(h + 1, 5)))
            okc = ok_all & np.isfinite(allL.values).all(1)
            mods = [L.ExpandingWLS(y, L.ar_frame(T, tgt, h, lags=ls).values if ls else np.zeros((len(y), 0)),
                                   w, okc) for ls in lagsets]
            fc = []
            for i in pos:
                bics = [L.bic_at(mm, i - h - 1, L.MIN_TRAIN_UNI) for mm in mods]
                b = int(np.argmin(bics))
                fc.append(mods[b].forecast(i, h, L.MIN_TRAIN_UNI) if np.isfinite(bics[b]) else np.nan)
            add(tgt, h, 'bench', 'ar_bic', 'benchmark', np.array(fc))
            # cross-parameterisation benchmarks for organic growth (og_py ~ og_{t-4} is known in advance)
            og4 = T['og'].shift(4).values[pos]
            if tgt == 'og':
                add(tgt, h, 'bench', 'srw', 'benchmark', og4)                       # og_t = og_{t-4}  (d_og = 0)
                f_dog = ewls('d_og', L.ar_frame(T, 'd_og', h), h=h)
                add(tgt, h, 'bench', 'ar_dog_implied', 'benchmark', og4 + f_dog)
            if tgt == 'd_og':
                add(tgt, h, 'bench', 'rw_implied', 'benchmark', T['og'].shift(h + 1).values[pos] - og4)
                add(tgt, h, 'bench', 'ar_oglev', 'benchmark', ewls('d_og', L.base_frame(T, 'd_og', h, 'oglev'), h=h))
                f_og = ewls('og', L.ar_frame(T, 'og', h), h=h)
                add(tgt, h, 'bench', 'ar_og_implied', 'benchmark', f_og - og4)

            # ---------------- univariate ARDL and theory models on top of each base variant
            Xh = X[h]
            for var in L.VARIANTS[tgt]:
                B = L.base_frame(T, tgt, h, var)
                for f in Xh.columns:
                    x = Xh[f]
                    for p in (1, 2):
                        Z = pd.concat([B, x.rename('x0')] + ([x.shift(1).rename('x1')] if p == 2 else []), axis=1)
                        add(tgt, h, var, f'uni_p{p}__{f}', 'univariate', ewls(tgt, Z, h=h))
                for name, feats in L.THEORY[tgt].items():
                    Z = pd.concat([B] + [Xh[f] for f in feats], axis=1)
                    add(tgt, h, var, name, 'theory', ewls(tgt, Z, h=h))
                    Z2 = pd.concat([Z] + [Xh[f].shift(1).rename(f + '_l1') for f in feats], axis=1)
                    add(tgt, h, var, name + '_p2', 'theory', ewls(tgt, Z2, h=h))
            print(f'linear {tgt} h={h} done in {time.time() - t0:.1f}s', flush=True)
    return pd.concat(rows, ignore_index=True)


# ----------------------------------------------------------------------------------------------
# Penalised regressions, PCA factors, random forest / boosting (loop over origins)
# ----------------------------------------------------------------------------------------------
def run_multi(tgt, h, variant, T, Xh):
    warnings.filterwarnings('ignore')   # loky workers do not inherit the parent's filter
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    idx = T.index
    pos = positions(idx, L.EVAL_START, L.LAST)
    y = T[tgt].values.astype(float)
    w = L.target_weights(T, tgt).values
    B = L.base_frame(T, tgt, h, variant)
    A_all = np.column_stack([np.ones(len(idx)), B.values])
    Xv = Xh.values
    feats = np.array(Xh.columns)
    ok = L.train_ok_mask(idx, L.MULTI_TRAIN_START)
    base_valid = ok & np.isfinite(y) & np.isfinite(A_all).all(1) & (w > 0)

    out = {k: np.full(len(pos), np.nan) for k in
           ['lasso', 'ridge', 'enet', 'pca_k1', 'pca_k2', 'pca_k3', 'pca_k4', 'pca_k5', 'pca_bic',
            'rf_resid', 'gbm_resid', 'base_2003']}
    sel_rows, alpha_rows = [], []

    def complete_feats(rows_, i):
        good = np.isfinite(Xv[rows_]).all(0) & np.isfinite(Xv[i])
        if good.any():
            gi = np.where(good)[0]
            sdv = Xv[np.ix_(rows_, gi)].std(0)
            good[gi[sdv < 1e-8]] = False
        return np.where(good)[0]

    for m_, i in enumerate(pos):
        if not np.isfinite(A_all[i]).all():
            continue
        R = np.where(base_valid & (np.arange(len(idx)) <= i - h - 1))[0]
        n = len(R)
        if n < L.MIN_TRAIN_MULTI:
            continue
        cols = complete_feats(R, i)
        Xtr, Atr, ytr, wtr = Xv[np.ix_(R, cols)], A_all[R], y[R], w[R]
        xi, ai = Xv[i, cols], A_all[i]
        s = np.sqrt(wtr)
        gb = np.linalg.lstsq(Atr * s[:, None], ytr * s, rcond=None)[0]
        base_fc = ai @ gb
        out['base_2003'][m_] = base_fc   # base model on the multivariate estimation sample (2003Q1+)

        # ---- penalised with forward-chaining CV inside the training window
        V = int(min(10, max(5, n // 4)))
        val_pos = R[-V:]
        for meth in ('lasso', 'ridge', 'enet'):
            alphas = L.alpha_grid(meth, ytr, Atr, Xtr, wtr)
            errs = np.zeros(len(alphas))
            wsum = 0.0
            for v in val_pos:
                Rin = R[R <= v - h - 1]
                if len(Rin) < 15:
                    continue
                cin = np.intersect1d(complete_feats(Rin, v), cols)
                G, Bc = L.penalised_path(meth, y[Rin], A_all[Rin], Xv[np.ix_(Rin, cin)], w[Rin], alphas)
                pred = A_all[v] @ G + Xv[v, cin] @ Bc
                errs += w[v] * (y[v] - pred) ** 2
                wsum += w[v]
            k = int(np.argmin(errs)) if wsum > 0 else len(alphas) // 2
            G, Bc = L.penalised_path(meth, ytr, Atr, Xtr, wtr, alphas[k:k + 1])
            out[meth][m_] = float(ai @ G[:, 0] + xi @ Bc[:, 0])
            nz = np.where(np.abs(Bc[:, 0]) > 1e-12)[0]
            alpha_rows.append({'target': tgt, 'h': h, 'variant': variant, 'period': str(idx[i]), 'method': meth,
                               'alpha': alphas[k], 'alpha_rank': k, 'n_candidates': len(cols),
                               'n_selected': len(nz) if meth != 'ridge' else len(cols), 'n_train': n})
            if meth in ('lasso', 'enet'):
                for j in nz:
                    sel_rows.append({'target': tgt, 'h': h, 'variant': variant, 'period': str(idx[i]),
                                     'method': meth, 'feature': feats[cols[j]], 'coef': Bc[j, 0],
                                     'coef_std': Bc[j, 0] * Xtr[:, j].std()})

        # ---- PCA factors of the (training-window standardised) core features
        mu, sd = Xtr.mean(0), Xtr.std(0)
        Ztr = (Xtr - mu) / sd
        zi = (xi - mu) / sd
        U, S, Vt = np.linalg.svd(Ztr, full_matrices=False)
        Ftr = Ztr @ Vt[:5].T
        fi = zi @ Vt[:5].T
        bics, fcs = [], []
        for kf in range(0, 6):
            M = np.column_stack([Atr, Ftr[:, :kf]])
            g = np.linalg.lstsq(M * s[:, None], ytr * s, rcond=None)[0]
            res = (ytr - M @ g) * s
            ssr = res @ res
            bics.append(n * np.log(ssr / n) + M.shape[1] * np.log(n))
            fcs.append(float(np.concatenate([ai, fi[:kf]]) @ g))
            if kf >= 1:
                out[f'pca_k{kf}'][m_] = fcs[-1]
        out['pca_bic'][m_] = fcs[int(np.argmin(bics))]

        # ---- nonlinear check: trees on the base-model residuals
        resid = ytr - Atr @ gb
        rf = RandomForestRegressor(n_estimators=300, max_depth=3, min_samples_leaf=4, max_features=0.33,
                                   random_state=0, n_jobs=1)
        rf.fit(Xtr, resid, sample_weight=wtr)
        out['rf_resid'][m_] = base_fc + rf.predict(xi[None, :])[0]
        gbm = GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.7,
                                        random_state=0)
        gbm.fit(Xtr, resid, sample_weight=wtr)
        out['gbm_resid'][m_] = base_fc + gbm.predict(xi[None, :])[0]

    fam = {'lasso': 'penalised', 'ridge': 'penalised', 'enet': 'penalised', 'rf_resid': 'ml', 'gbm_resid': 'ml',
           'base_2003': 'check'}
    df = pd.concat([pd.DataFrame({'target': tgt, 'h': h, 'variant': variant, 'model': k,
                                  'family': fam.get(k, 'pca'), 'period': idx[pos], 'forecast': v})
                    for k, v in out.items()], ignore_index=True)
    print(f'multi {tgt} h={h} {variant} done', flush=True)
    return df, pd.DataFrame(sel_rows), pd.DataFrame(alpha_rows)


if __name__ == '__main__':
    T, F, D, X = L.load_all()
    mode = sys.argv[1]
    t0 = time.time()
    if mode == 'linear':
        lin = run_linear(T, X)
        lin['period'] = lin['period'].astype(str)
        lin.to_pickle(f'{L.OUT}/forecasts_linear.pkl')
        print('linear stage', round(time.time() - t0, 1), 's', lin.shape, flush=True)
    elif mode == 'multi':
        variant = sys.argv[2]
        tasks = [(tgt, h) for tgt in L.TARGETS if variant in L.VARIANTS[tgt] for h in L.HS]
        res = Parallel(n_jobs=4)(delayed(run_multi)(tgt, h, variant, T, X[h]) for tgt, h in tasks)
        multi = pd.concat([r[0] for r in res], ignore_index=True)
        multi['period'] = multi['period'].astype(str)
        multi.to_pickle(f'{L.OUT}/forecasts_multi_{variant}.pkl')
        pd.concat([r[1] for r in res], ignore_index=True).to_csv(f'{L.OUT}/lasso_selection_raw_{variant}.csv',
                                                                 index=False)
        pd.concat([r[2] for r in res], ignore_index=True).to_csv(f'{L.OUT}/penalised_alpha_log_{variant}.csv',
                                                                 index=False)
        print('multi stage', variant, round(time.time() - t0, 1), 's', multi.shape, flush=True)
    else:
        raise SystemExit(__doc__)
