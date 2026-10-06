"""Sign and stability of the feature coefficient in the real-time univariate ARDL(p=1) models.

For the best univariate models (oos_top_univariate.csv) plus any feature named in the findings, re-run the
expanding-window fits and record the feature coefficient at every forecast origin 2010Q1-2026Q2:
share of origins with a positive coefficient, the coefficient (per 1 s.d. of the feature) at the last
origin and its HAC t-stat in the full-sample fit (through 2026Q2, in-sample, for orientation only).
Output: coef_signs.csv
"""
import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import numpy as np
import pandas as pd

import oos_lib as L

EXTRA = {('og', 2): ['w_unemp_d4'], ('d_og', 2): ['w_unemp_d4', 'no_earn_idx_food_manuf_q__yoy'],
         ('og', 0): ['nw_food_cpi_xvat_yoy', 'w_food_cpi_xvat_yoy'], ('d_og', 0): ['nw_food_cpi_xvat_dyoy'],
         ('d_margin', 0): ['price_cost_gap_ppi', 'w_food_ppi_dyoy', 'w_wage_yoy', 'fao_ffpi_wloc_yoy'],
         ('d_margin', 1): ['price_cost_gap_ppi', 'fao_ffpi_wloc_yoy'], ('d_og', 1): ['se_eursek__yoy'],
         ('d_og', 0): ['se_eursek__yoy']}

if __name__ == '__main__':
    T, F, D, X = L.load_all()
    top = pd.read_csv(f'{L.OUT}/oos_top_univariate.csv')
    idx = T.index
    pos = [i for i, p in enumerate(idx) if L.EVAL_START <= p <= L.LAST]
    ok = L.train_ok_mask(idx)
    rows = []
    for (tgt, h), g in top.groupby(['target', 'h']):
        feats = list(dict.fromkeys(list(g.feature) + EXTRA.get((tgt, h), [])))
        y = T[tgt].values.astype(float)
        w = L.target_weights(T, tgt).values
        B = L.base_frame(T, tgt, h, L.PRIMARY[tgt])
        for f in feats:
            x = X[h][f]
            Z = pd.concat([B, x.rename('x')], axis=1)
            m = L.ExpandingWLS(y, Z.values, w, ok)
            sdx = np.nanstd(Z['x'].values)
            coefs = []
            for i in pos:
                fit = m.fit_at(i - h - 1, L.MIN_TRAIN_UNI)
                if fit is None:
                    continue
                keep, beta, _, _ = fit
                k = Z.shape[1]   # feature is the last column (index k in the constant-augmented design)
                coefs.append(beta[list(keep).index(k)] if k in keep else 0.0)   # per 1 s.d. of x (full-sample sd)
            coefs = np.array(coefs)
            wfs = L.target_weights(T, tgt) * (~T.index.isin(L.TRAIN_EXCL)).astype(float)   # pandemic quarters out
            fs = L.C.nw_ols(T[tgt], Z, lags=4, weights=wfs)
            rows.append({'target': tgt, 'h': h, 'feature': f, 'n_origins': len(coefs),
                         'share_origins_positive': np.mean(coefs > 0) if len(coefs) else np.nan,
                         'coef_per_sd_last_origin': coefs[-1] if len(coefs) else np.nan,
                         'coef_per_sd_first_origin': coefs[0] if len(coefs) else np.nan,
                         'insample_coef_per_sd': fs.params['x'] * sdx, 'insample_hac_t': fs.tvalues['x'],
                         'insample_n': int(fs.nobs)})
    out = pd.DataFrame(rows)
    out.to_csv(f'{L.OUT}/coef_signs.csv', index=False, float_format='%.4g')
    pd.set_option('display.width', 220)
    print(out.round(3).to_string())
