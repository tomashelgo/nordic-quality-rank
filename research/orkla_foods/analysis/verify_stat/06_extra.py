"""Extra: circular-shift nulls for M3 headline rows; O1 ex-episode OLS placebo; M3 joint DL sum."""
import warnings
import numpy as np
import pandas as pd
import vlib as V
warnings.filterwarnings('ignore')
T, F, D = V.load()
idx = T.index
out = []
for f, k in [('eu_ppi_dom_c105_idx__yoy', 6), ('se_ppi_food_hmpi_idx__yoy', 6), ('eu_ppi_dom_c107_idx__yoy', 5), ('se_cpi_idx__yoy', 6)]:
    x = V.X_at(F, D, 'realtime', k, idx=idx)[f]
    t0, ts = V.circ_shift_t(T, 'd_margin', x)
    out.append(dict(item='M3_circshift', feature=f, k=k, t=t0, q95=np.quantile(np.abs(ts), .95), q99=np.quantile(np.abs(ts), .99),
                    p_circ=(np.sum(np.abs(ts) >= abs(t0)) + 1) / (len(ts) + 1), n_shift=len(ts),
                    p_onesided=(np.sum(ts >= t0) + 1) / (len(ts) + 1)))
# O1 ex-episode, OLS (unweighted) placebo
x = V.X_at(F, D, 'coincident', idx=idx)['w_food_cpi_xvat_yoy']
for s in ['exepi', 'exepi+excovid']:
    pl = V.placebo_t(T, 'og', x, nsim=2000, sample=s, weighted=False, F_source=F['w_food_cpi_xvat_yoy'])
    out.append(dict(item='O1_exepi_ols_placebo', feature=s, t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal']))
# M3: joint DL lags 0..8 of the dairy PPI (coincident) -> sum of coefficients (permanent level effect) and lag 5-7 block
Xc = V.X_at(F, D, 'coincident', idx=idx)
for f in ['eu_ppi_dom_c105_idx__yoy', 'raw_mat_wloc_yoy', 'w_food_ppi_yoy']:
    Z = pd.DataFrame({f'L{j}': Xc[f].shift(j) for j in range(0, 9)})
    for s in ['full', 'exepi', 'exepi+execho']:
        r = V.hac_fit(T['d_margin'].where(V.sample_mask(T, s)), Z, None, 4)
        b = r['b'][Z.columns].values
        Vm = r['V'].loc[Z.columns, Z.columns].values
        g_s = np.r_[np.ones(4), np.zeros(5)]
        g_l = np.r_[np.zeros(5), np.ones(3), 0]
        g_all = np.ones(9)
        def lin(g):
            return float(g @ b), float(g @ b / np.sqrt(g @ Vm @ g))
        out.append(dict(item='M3_jointDL', feature=f, k=s, sum_L0_3=lin(g_s)[0], t_L0_3=lin(g_s)[1], sum_L5_7=lin(g_l)[0],
                        t_L5_7=lin(g_l)[1], sum_all=lin(g_all)[0], t_all=lin(g_all)[1], n=r['n']))
O = pd.DataFrame(out)
O.to_csv(f'{V.OUT}/extra_results.csv', index=False)
pd.set_option('display.width', 220)
print(O.round(4).to_string())
