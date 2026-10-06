"""M4 (10y yields), M5 (EUR/SEK), M6 (OOS: no macro model robustly beats AR; null variables)."""
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import vlib as V

warnings.filterwarnings('ignore')
pd.set_option('display.width', 250)
T, F, D = V.load()
idx = T.index
Xc = V.X_at(F, D, 'coincident', idx=idx)
XR = {h: V.X_at(F, D, 'realtime', h, idx=idx) for h in (0, 1, 2)}
y = T['d_margin']
rows = []


def rec(claim, test, **kw):
    d = dict(claim=claim, test=test)
    d.update(kw)
    rows.append(d)


# ------------------------------------------------------------------ M4 in-sample
for f in ['w_gov10y_d4', 'no_govbond_10y__d4', 'se_gov_bond_10y__d4']:
    x = Xc[f]
    for s in ['full', 'exepi', 'excovid', 'exbreak', 'exepi+excovid', 'pre2020', 'exepi+excovid+exbreak']:
        for L in (4, 8):
            r = V.fit_one(T, 'd_margin', x, L=L, sample=s)
            rec('M4', f'{f}|coin|{s}|HAC{L}', b=r['b']['x'], t=r['t']['x'], n=r['n'])
        if s in ('full', 'exepi', 'exepi+excovid'):
            pl = V.placebo_t(T, 'd_margin', x, nsim=2000, sample=s, F_source=F[f])
            rec('M4', f'{f}|coin|{s}|placebo', t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal'], p_emp=pl['p_emp'])
            yy, X, w = V.design(T, 'd_margin', x, sample=s)
            bb = V.mbb_coef(yy, X, w, nboot=2000, block=8)
            rec('M4', f'{f}|coin|{s}|mbb8', b=bb['b'], t=bb['t_boot'], p_boot=bb['p_boot'], ci_lo=bb['ci'][0],
                ci_hi=bb['ci'][1])
    t0, ts = V.circ_shift_t(T, 'd_margin', x)
    rec('M4', f'{f}|coin|full|circshift', t=t0, q95=np.quantile(np.abs(ts), .95),
        p_circ=(np.sum(np.abs(ts) >= abs(t0)) + 1) / (len(ts) + 1))
    # cost controls
    for ctrl in ['packaging_eu_yoy', 'w_food_ppi_yoy', 'eu_ppi_plastic_products_idx__yoy', 'raw_mat_wloc_yoy',
                 'w_food_cpi_xvat_yoy']:
        for s in ['full', 'exepi']:
            r = V.fit_one(T, 'd_margin', pd.concat([x.rename('x'), Xc[ctrl].rename('c')], axis=1), sample=s)
            rec('M4', f'{f}|coin|{s}|ctrl={ctrl}', b=r['b']['x'], t=r['t']['x'], t_ctrl=r['t']['c'], n=r['n'])

# ------------------------------------------------------------------ OOS engine helpers
TR_EX = ('2020Q1', '2021Q2')
evalm = {'full2010': None, 'exepi': pd.Series(V.sample_mask(T, 'exepi'), idx),
         'excovid+exepi': pd.Series(V.sample_mask(T, 'exepi+excovid'), idx),
         '2015+': pd.Series(np.asarray(idx >= pd.Period('2015Q1')), idx)}


def ar_base(h, target='d_margin', lags=None):
    yy = T[target]
    lags = lags or ([h + 1] + ([4] if h + 1 < 4 else []))
    return pd.DataFrame({f'ar{l}': yy.shift(l) for l in lags}, index=idx)


def run(name, h, Zx, base=None, target='d_margin', w=None, claim='M6', train_excl=TR_EX, min_train=12):
    B = ar_base(h, target) if base is None else base
    fb, fm, yy = V.oos_forecasts(T[target], B, Zx, w, idx, h=h, train_excl=train_excl, min_train=min_train)
    out = {}
    for en, em in evalm.items():
        s = V.oos_summary(yy, fb, fm, em)
        rec(claim, f'OOS|{name}|h{h}|{en}', **s)
        out[en] = s
    return out, (fb, fm, yy)


# M4 OOS
for f in ['w_gov10y_d4', 'no_govbond_10y__d4']:
    for h in (0, 1, 2):
        run(f, h, XR[h][[f]], claim='M4')

# ------------------------------------------------------------------ M5 EUR/SEK
f = 'se_eursek__yoy'
x = Xc[f]
for k in (0, 1, 2):
    for s in ['full', 'exepi']:
        r = V.fit_one(T, 'd_margin', x.shift(k), sample=s)
        rec('M5', f'{f}|lag{k}|{s}|per10pct', b=10 * r['b']['x'], t=r['t']['x'], n=r['n'])
    pl = V.placebo_t(T, 'd_margin', x.shift(k), nsim=2000, F_source=F[f])
    rec('M5', f'{f}|lag{k}|full|placebo', t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal'])
r = V.fit_one(T, 'd_margin', pd.concat([x.rename('x'), x.shift(1).rename('x1')], axis=1))
rec('M5', f'{f}|lag0+1|full|sum_per10pct', b=10 * (r['b']['x'] + r['b']['x1']), t=r['t']['x'], n=r['n'])


def pdl_cols(xa, K=6, P=2):
    Lm = pd.concat([xa.shift(k) for k in range(K + 1)], axis=1)
    ks = np.arange(K + 1)
    H = np.vstack([(ks / K) ** p for p in range(P + 1)]).T
    Z = pd.DataFrame(Lm.values @ H, index=xa.index, columns=[f'p{p}' for p in range(P + 1)])
    Z[Lm.isna().any(axis=1)] = np.nan
    return Z


xa0 = XR[0][f]
# (a) the mechanism lens' set-up: AR(y_{t-1}) + Easter window, COVID quarters used in training, min_train 28
mechB = pd.DataFrame({'ar1': y.shift(1), 'ew': T['d_easter_window_q1']}, index=idx)
run('EURSEK_PDL06|mech_bench(AR1+Easter)', 0, pdl_cols(xa0), base=mechB, claim='M5', train_excl=('1900Q1', '1900Q1'),
    min_train=28)
# (b) pure AR(1)+no Easter, same training rule
run('EURSEK_PDL06|bench AR1', 0, pdl_cols(xa0), base=pd.DataFrame({'ar1': y.shift(1)}, index=idx), claim='M5',
    train_excl=('1900Q1', '1900Q1'), min_train=28)
# The Easter term alone vs AR1 (does the benchmark choice matter?)
run('Easter_only|bench AR1', 0, T[['d_easter_window_q1']], base=pd.DataFrame({'ar1': y.shift(1)}, index=idx),
    claim='M5', train_excl=('1900Q1', '1900Q1'), min_train=28)
# (c) OOS-lens primary AR(y_{t-1}, y_{t-4}), COVID excluded from training
run('EURSEK_PDL06|bench AR(1,4)', 0, pdl_cols(xa0), claim='M5')
run('EURSEK_lvl0|bench AR(1,4)', 0, xa0.to_frame(), claim='M5')
run('EURSEK_lvl0+1|bench AR(1,4)', 0, pd.concat([xa0, xa0.shift(1).rename('l1')], axis=1), claim='M5')

# management-cited weak SEK
try:
    th = pd.read_csv('/home/user/nordic-quality-rank/research/orkla_foods/analysis/mechanism/text_themes.csv')
    th.index = pd.PeriodIndex(th['period'].astype(str), freq='Q')
    col = [c for c in th.columns if 'sek' in c.lower() or 'fx' in c.lower()]
    print('text theme columns with fx/sek:', col)
    for c in col:
        if th[c].dropna().isin([0, 1, True, False]).all():
            fl = th[c].astype(float).reindex(idx)
            eur = Xc[f]
            a, b = eur[fl == 1].mean(), eur[fl == 0].mean()
            rec('M5', f'text|{c}', n_flag=int((fl == 1).sum()), eursek_flag=a, eursek_noflag=b)
except Exception as e:
    print('text check failed', e)

# ------------------------------------------------------------------ M6: univariate OOS for all core features
core = [c for c in D.index[D['core'] == True] if c in F.columns]
uni = []
for h in (0, 1, 2):
    for fct in core:
        xa = XR[h][fct]
        if xa.notna().sum() < 40:
            continue
        B = ar_base(h)
        fb, fm, yy = V.oos_forecasts(y, B, xa.to_frame(), None, idx, h=h)
        for en, em in evalm.items():
            s = V.oos_summary(yy, fb, fm, em)
            uni.append(dict(feature=fct, h=h, eval=en, **s))
U = pd.DataFrame(uni)
U['by_fam'] = U.groupby(['h', 'eval'])['cw_p'].transform(lambda p: V.by_adjust(p))
U['holm_fam'] = U.groupby(['h', 'eval'])['cw_p'].transform(
    lambda p: __import__('statsmodels.stats.multitest', fromlist=['x']).multipletests(p.fillna(1), method='holm')[1])
U.to_csv(f'{V.OUT}/m6_univariate_oos.csv', index=False)
for (h, en), g in U.groupby(['h', 'eval']):
    g2 = g.sort_values('ratio')
    print(f'h={h} {en}: best', g2.head(3)[['feature', 'ratio', 'cw_p', 'by_fam']].round(3).values.tolist(),
          ' share ratio<1:', round((g.ratio < 1).mean(), 2), ' n BY<0.1:', int((g.by_fam < 0.1).sum()))

# theory input-cost model (pre-specified by OOS lens), h=0,1,2
for h in (0, 1, 2):
    run('th_input_costs', h, XR[h][['fao_ffpi_wloc_yoy', 'w_wage_yoy', 'packaging_eu_yoy']])
    run('packaging_eu_yoy', h, XR[h][['packaging_eu_yoy']])
    run('eu_ppi_plastic', h, XR[h][['eu_ppi_plastic_products_idx__yoy']])

# PCA1 (expanding standardisation, complete-case features from 2003; refit each origin)
from numpy.linalg import svd
for h in (0, 1, 2):
    Xh = XR[h][core]
    pos = [i for i, p in enumerate(idx) if p >= pd.Period('2010Q1') and np.isfinite(y.values[i])]
    yv = y.values
    B = ar_base(h).values
    excl = V.mask_period(idx, '2020Q1', '2021Q2') | np.asarray(idx < pd.Period('2003Q1'))
    fb_, fm_ = [], []
    for i in pos:
        tr = np.isfinite(yv) & np.isfinite(B).all(1) & ~excl
        tr[i - h:] = False
        # aligned features in rows <= i are all known at the forecast origin
        rows_ = np.where(np.asarray(idx >= pd.Period('2003Q1')) & (np.arange(len(idx)) <= i))[0]
        Xs = Xh.values[rows_]
        good = np.isfinite(Xs).all(0)
        Xg = Xh.values[:, good]
        mu, sd = Xg[rows_].mean(0), Xg[rows_].std(0)
        sd[sd == 0] = 1
        Zs = (Xg[rows_] - mu) / sd
        U_, S_, Vt = svd(Zs, full_matrices=False)
        pc = ((Xg - mu) / sd) @ Vt[0]
        A0 = np.column_stack([np.ones(len(yv)), B])
        A1 = np.column_stack([A0, pc])
        m = tr & np.isfinite(pc)
        b0 = np.linalg.lstsq(A0[m], yv[m], rcond=None)[0]
        b1 = np.linalg.lstsq(A1[m], yv[m], rcond=None)[0]
        fb_.append(A0[i] @ b0)
        fm_.append(A1[i] @ b1)
    ix = idx[pos]
    for en, em in evalm.items():
        s = V.oos_summary(pd.Series(yv[pos], ix), pd.Series(fb_, ix), pd.Series(fm_, ix), em)
        rec('M6', f'OOS|pca1|h{h}|{en}', **s)

# ------------------------------------------------------------------ M6: null variables in sample (placebo-calibrated)
nulls = ['w_real_wage_yoy', 'nw_real_wage_yoy', 'w_cons_conf_z', 'nw_cons_conf_z', 'w_policy_rate_lvl',
         'w_gov10y_lvl', 'elec_nordic_loc_yoy', 'natgas_eu_eur_yoy', 'brent_nok_yoy', 'w_wage_yoy', 'w_wage_dyoy', 'w_cons_conf_z_d4']
nulls = [c for c in nulls if c in F.columns]
missing = [c for c in ['natgas_eu_eur_yoy', 'w_gov10y_lvl'] if c not in F.columns]
print('missing null candidates:', missing, [c for c in F.columns if 'gas' in c][:10])
for fct in nulls:
    for al, X in [('coin', Xc), ('rt0', XR[0]), ('rt1', XR[1])]:
        for s in ['full', 'exepi']:
            pl = V.placebo_t(T, 'd_margin', X[fct], nsim=1000, sample=s, F_source=F[fct])
            rec('M6null', f'{fct}|{al}|{s}', b=pl['b'], t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal'],
                sd_x=float(X[fct].std()), b_1sd=pl['b'] * float(X[fct].std()))
R = pd.DataFrame(rows)
R.to_csv(f'{V.OUT}/m4_m5_m6_results.csv', index=False)
print(R.round(4).to_string())
