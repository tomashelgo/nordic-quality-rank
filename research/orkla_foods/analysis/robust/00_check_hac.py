"""Check that the fast numpy HAC regression in robust_lib reproduces common.nw_ols (statsmodels)."""
import numpy as np
import pandas as pd
import robust_lib as R
C = R.C

T = R.load_T()
F, D = C.load_features(core_only=True)
X = C.align(F, D, 'realtime', 1)
for tgt, feat in [('d_margin', 'w_food_ppi_yoy'), ('og', 'w_food_cpi_xvat_yoy'), ('d_og', 'w_cons_conf_z_d4')]:
    Ctrl = R.controls_for(tgt, T)
    w = R.weights_for(tgt, T)
    x = X[feat]
    sm = C.nw_ols(T[tgt], pd.concat([x.rename('x'), Ctrl], axis=1), lags=4, weights=w)
    yv, Xv, wv, idx = R.frame(T[tgt], x, Ctrl, w)
    r = R.hac_ols(yv, Xv, wv, drop_const_cols=False)
    print(tgt, feat, 'statsmodels b/t', round(sm.params['x'], 6), round(sm.tvalues['x'], 4),
          '| fast b/t', round(r['beta'][0], 6), round(r['t'][0], 4), 'n', sm.nobs, r['n'])
    assert abs(sm.params['x'] - r['beta'][0]) < 1e-8 and abs(sm.tvalues['x'] - r['t'][0]) < 1e-6
print('fast HAC matches statsmodels HAC')
