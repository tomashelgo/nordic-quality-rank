"""M5 text check (weak-SEK mentions vs EUR/SEK, and whether mentions predate or follow the margin outcome);
G1 placebo size of nominal HAC(4) tests and episode share of covariance for key relations."""
import numpy as np, pandas as pd
import vr_lib as V
pd.set_option('display.width', 250)
T, F, D = V.load(); idx = T.index
t = pd.read_csv('/home/user/nordic-quality-rank/research/orkla_foods/analysis/mechanism/text_themes.csv')
t.index = pd.PeriodIndex(t['period'], freq='Q')
sek = F['se_eursek__yoy'].reindex(t.index)
fw = t['fx_weak'].astype(bool)
print('fx_weak quarters', fw.sum(), 'EURSEK yoy mean in/out', round(sek[fw].mean(), 2), round(sek[~fw].mean(), 2))
print('d_margin in/out', round(t.loc[fw, 'd_margin'].mean(), 2), round(t.loc[~fw, 'd_margin'].mean(), 2))
# real-time aspect: the text is in the same report as d_margin (ex post explanation), so it cannot be a predictor
EX = V.ex_mask(t.index, 'infl')
print('ex-episode fx_weak n', (fw & EX).sum(), 'EURSEK in/out', round(sek[fw & EX].mean(), 2), round(sek[~fw & EX].mean(), 2))

# ---- G1 placebo: persistent AR(2) placebo regressors (independent of y), nominal 5% HAC(4) rejection rate
rng = np.random.default_rng(20261006)
res = []
for tgt, w in [('d_margin', None), ('og', T['w_og'])]:
    y = T[tgt]
    for phi in [(0.5, 0.0), (0.9, 0.0), (1.2, -0.3), (0.97, 0.0)]:
        rej = []; tt = []
        for r in range(400):
            e = rng.standard_normal(len(idx) + 50)
            x = np.zeros_like(e)
            for i in range(2, len(e)):
                x[i] = phi[0] * x[i - 1] + phi[1] * x[i - 2] + e[i]
            xs = pd.Series(x[50:], index=idx, name='x')
            Z = xs.to_frame() if tgt == 'd_margin' else pd.concat([xs, T['easter_shift']], axis=1)
            rr = V.ols(y, Z, w=w)
            tt.append(abs(rr.tvalues['x'])); rej.append(abs(rr.tvalues['x']) > 1.96)
        res.append(dict(target=tgt, ar=str(phi), size_5pct=np.mean(rej), t95=np.quantile(tt, 0.95)))
P = pd.DataFrame(res); print(P.to_string(float_format=lambda v: f'{v:.3f}'))
P.to_csv(f'{V.OUT}/g1_placebo.csv', index=False, float_format='%.4g')

# ---- episode share of the covariance for key relations
EPI = pd.Series((idx >= V.EPI[0]) & (idx <= V.EPI[1]), index=idx)
rel = [('d_margin', 'packaging_eu_yoy', 0), ('d_margin', 'no_govbond_10y__d4', 0), ('d_margin', 'eu_ppi_dom_c105_idx__yoy', 6),
       ('d_margin', 'se_ppi_food_hmpi_idx__yoy', 6), ('og', 'w_food_cpi_xvat_yoy', 0), ('og', 'w_policy_rate_d4', 3),
       ('d_og', 'ea_ec_food_ind_sell_price_exp__d4', 4), ('og', 'w_unemp_d4', 3), ('d_og', 'w_food_cpi_xvat_dyoy', 0)]
out = []
for tgt, f, k in rel:
    d = pd.concat([T[tgt].rename('y'), F[f].reindex(idx).shift(k).rename('x'), EPI.rename('e')], axis=1).dropna()
    cp = (d.x - d.x.mean()) * (d.y - d.y.mean())
    out.append(dict(target=tgt, feature=f, k=k, n=len(d), n_epi=int(d.e.sum()), share_cov_epi=cp[d.e.astype(bool)].sum() / cp.sum(),
                    corr_full=np.corrcoef(d.x, d.y)[0, 1], corr_ex=np.corrcoef(d.x[~d.e.astype(bool)], d.y[~d.e.astype(bool)])[0, 1]))
O = pd.DataFrame(out); print(O.to_string(float_format=lambda v: f'{v:.3f}'))
O.to_csv(f'{V.OUT}/g1_episode_share.csv', index=False, float_format='%.4g')
