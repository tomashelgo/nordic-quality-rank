"""O1-O6: organic-growth claims."""
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import vlib as V

warnings.filterwarnings('ignore')
pd.set_option('display.width', 250)
T, F, D = V.load()
idx = T.index
Fa, Da = F, D
Xc = V.X_at(F, D, 'coincident', idx=idx)
XR = {h: V.X_at(F, D, 'realtime', h, idx=idx) for h in (0, 1, 2, 3, 4)}
rows = []


def rec(claim, test, **kw):
    d = dict(claim=claim, test=test)
    d.update(kw)
    rows.append(d)


def full_battery(claim, target, x, tag, samples=('full', 'exepi', 'excovid', 'exbreak', 'exepi+excovid', 'pre2020'),
                 extra=None, placebo=True, src=None, circ=False):
    for s in samples:
        for L in (4, 8):
            for wtd in (True, False):
                if not wtd and L == 8:
                    continue
                r = V.fit_one(T, target, x, L=L, sample=s, weighted=wtd, extra_controls=extra)
                rec(claim, f'{tag}|{s}|HAC{L}|{"wls" if wtd else "ols"}', b=r['b']['x'], t=r['t']['x'], n=r['n'])
    if placebo:
        for s in ('full', 'exepi'):
            pl = V.placebo_t(T, target, x, nsim=2000, sample=s, extra_controls=extra, F_source=src)
            rec(claim, f'{tag}|{s}|placebo', t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal'], p_emp=pl['p_emp'],
                size5=pl['size5'])
    if circ:
        t0, ts = V.circ_shift_t(T, target, x)
        rec(claim, f'{tag}|full|circshift', t=t0, q95=np.quantile(np.abs(ts), .95),
            p_circ=(np.sum(np.abs(ts) >= abs(t0)) + 1) / (len(ts) + 1))


# ================================================================== O1
x = Xc['w_food_cpi_xvat_yoy']
full_battery('O1', 'og', x, 'og~w_food_cpi_xvat|coin', src=F['w_food_cpi_xvat_yoy'], circ=True)
yy, X, w = V.design(T, 'og', x)
bb = V.mbb_coef(yy, X, w, nboot=2000, block=8)
rec('O1', 'og~w_food_cpi_xvat|coin|full|mbb8', b=bb['b'], t=bb['t_boot'], ci_lo=bb['ci'][0], ci_hi=bb['ci'][1])
yy, X, w = V.design(T, 'og', x, sample='exepi')
bb = V.mbb_coef(yy, X, w, nboot=2000, block=8)
rec('O1', 'og~w_food_cpi_xvat|coin|exepi|mbb8', b=bb['b'], t=bb['t_boot'], ci_lo=bb['ci'][0], ci_hi=bb['ci'][1])
# eras
eras = {'2001-07 (A)': ('2001Q1', '2007Q4'), '2008-14Q3 (B/C)': ('2008Q1', '2014Q3'),
        '2014Q4-19 (D pre-COVID)': ('2014Q4', '2019Q4'), '2020-21 (COVID)': ('2020Q1', '2021Q4'),
        '2022-26': ('2022Q1', '2026Q2'), '2001-12': ('2001Q1', '2012Q4'), '2013-26': ('2013Q1', '2026Q2'),
        '2001-20': ('2001Q1', '2020Q4'), '2013-20': ('2013Q1', '2020Q4')}
for en, (a, b_) in eras.items():
    m = pd.Series(V.mask_period(idx, a, b_), idx)
    yy = T['og'].where(m)
    Z = pd.concat([x.rename('x'), T['easter_shift']], axis=1)
    r = V.hac_fit(yy, Z, T['w_og'], 4)
    rec('O1', f'era|{en}', b=r['b']['x'], t=r['t']['x'], n=r['n'], sd_x=float(x[m].std()))
# formal slope-equality test across 4 non-COVID eras
E = pd.DataFrame(index=idx)
for en in ['2008-14Q3 (B/C)', '2014Q4-19 (D pre-COVID)', '2022-26']:
    a, b_ = eras[en]
    d = pd.Series(V.mask_period(idx, a, b_).astype(float), idx)
    E['d_' + en[:4]] = d
    E['xd_' + en[:4]] = d * x
m = pd.Series(~V.mask_period(idx, '2020Q1', '2021Q4'), idx)
r = V.hac_fit(T['og'].where(m), pd.concat([x.rename('x'), T['easter_shift'], E], axis=1), T['w_og'], 4)
cols = [c for c in r['b'].index if c.startswith('xd_')]
bvec = r['b'][cols].values
Vm = r['V'].loc[cols, cols].values
W = float(bvec @ np.linalg.pinv(Vm) @ bvec)
rec('O1', 'era_slope_equality_wald', W=W, df=len(cols), p_chi2=1 - stats.chi2.cdf(W, len(cols)),
    p_F=1 - stats.f.cdf(W / len(cols), len(cols), r['df']))
# rolling 32Q
roll = []
for end in range(32, len(idx)):
    win = idx[end - 32:end]
    m = pd.Series(idx.isin(win), idx)
    yy = T['og'].where(m)
    try:
        r = V.hac_fit(yy, pd.concat([x.rename('x'), T['easter_shift']], axis=1), T['w_og'], 4)
        roll.append(dict(end=str(idx[end - 1]), b=r['b']['x'], t=r['t']['x'], n=r['n']))
    except Exception:
        pass
pd.DataFrame(roll).to_csv(f'{V.OUT}/o1_rolling32.csv', index=False)

# ---- price component n=17
P = T[['price', 'volume_mix', 'og']].dropna()
pi = P.index
for f in ['w_food_cpi_xvat_yoy', 'nw_food_cpi_xvat_yoy']:
    xx = Xc[f].reindex(pi)
    yv = P['price']
    A = np.column_stack([np.ones(len(pi)), xx.values])
    b, res, rk, sv = np.linalg.lstsq(A, yv.values, rcond=None)
    e = yv.values - A @ b
    s2 = (e ** 2).sum() / (len(pi) - 2)
    se = np.sqrt(s2 * np.linalg.inv(A.T @ A).diagonal())
    r2 = 1 - (e ** 2).sum() / ((yv - yv.mean()) ** 2).sum()
    rho1 = np.corrcoef(e[1:], e[:-1])[0, 1]
    dw = (np.diff(e) ** 2).sum() / (e ** 2).sum()
    # HAC
    rh2 = V.hac_fit(yv, xx.rename('x').to_frame(), None, 2)
    rh4 = V.hac_fit(yv, xx.rename('x').to_frame(), None, 4)
    # Effective-n adjusted t (Bartlett-type: n_eff = n (1 - r1 r2)/(1 + r1 r2))
    r1 = np.corrcoef(xx.values[1:], xx.values[:-1])[0, 1]
    r2y = np.corrcoef(yv.values[1:], yv.values[:-1])[0, 1]
    neff = len(pi) * (1 - r1 * r2y) / (1 + r1 * r2y)
    rr = np.corrcoef(xx.values, yv.values)[0, 1]
    t_eff = rr * np.sqrt((neff - 2) / (1 - rr ** 2))
    # first differences
    dx, dy = xx.diff().dropna(), yv.diff().dropna()
    Ad = np.column_stack([np.ones(len(dx)), dx.values])
    bd = np.linalg.lstsq(Ad, dy.values, rcond=None)[0]
    ed = dy.values - Ad @ bd
    sed = np.sqrt((ed ** 2).sum() / (len(dx) - 2) * np.linalg.inv(Ad.T @ Ad).diagonal())
    # Q2-only (non-overlapping annual observations)
    q2 = [p for p in pi if p.quarter == 2]
    # block bootstrap (block 4) and wild-cluster-by-year style: resample whole years
    rng = np.random.default_rng(3)
    bs = []
    for _ in range(5000):
        nb = int(np.ceil(len(pi) / 4))
        ii = np.concatenate([np.arange(s, s + 4) for s in rng.integers(0, len(pi) - 3, nb)])[:len(pi)]
        Ab = A[ii]
        if np.std(Ab[:, 1]) == 0:
            continue
        bs.append(np.linalg.lstsq(Ab, yv.values[ii], rcond=None)[0][1])
    bs = np.array(bs)
    # leave-one-year-out
    years = sorted(set(p.year for p in pi))
    loyo = []
    for yr in years:
        k = np.array([p.year != yr for p in pi])
        loyo.append(np.linalg.lstsq(A[k], yv.values[k], rcond=None)[0][1])
    rec('O1', f'price17~{f}', n=len(pi), a=b[0], b=b[1], se_ols=se[1], t_ols=b[1] / se[1],
        p_ols=2 * (1 - stats.t.cdf(abs(b[1] / se[1]), len(pi) - 2)), t_slope_eq1=(b[1] - 1) / se[1], r2=r2,
        resid_rho1=rho1, dw=dw, t_hac2=rh2['t']['x'], t_hac4=rh4['t']['x'], se_hac4=rh4['se']['x'],
        t_slope_eq1_hac4=(b[1] - 1) / rh4['se']['x'], neff=neff, t_eff=t_eff,
        p_eff=2 * (1 - stats.t.cdf(abs(t_eff), max(neff - 2, 1))),
        b_diff=bd[1], t_diff=bd[1] / sed[1], n_diff=len(dx),
        boot_ci_lo=np.quantile(bs, 0.025), boot_ci_hi=np.quantile(bs, 0.975), loyo_min=min(loyo), loyo_max=max(loyo),
        q2_n=len(q2), q2_b=np.polyfit(xx[q2].values, yv[q2].values, 1)[0],
        q2_r=np.corrcoef(xx[q2].values, yv[q2].values)[0, 1])
# PPI lags vs price
for f in ['w_food_ppi_yoy', 'nw_food_ppi_yoy', 'w_food_cpi_xvat_yoy', 'nw_food_cpi_xvat_yoy']:
    for k in range(0, 4):
        xx = Xc[f].shift(k).reindex(pi)
        rr = np.corrcoef(xx.values, P['price'].values)[0, 1]
        bk = np.polyfit(xx.values, P['price'].values, 1)[0]
        rec('O1', f'price17~{f}|lag{k}', r=rr, r2=rr ** 2, b=bk)
# bootstrap: is lag-1 PPI really better than lag-0 PPI? (resample quarters in blocks of 4)
for f in ['w_food_ppi_yoy', 'nw_food_ppi_yoy']:
    x0 = Xc[f].reindex(pi).values
    x1 = Xc[f].shift(1).reindex(pi).values
    yv = P['price'].values
    rng = np.random.default_rng(5)
    d = []
    for _ in range(5000):
        nb = int(np.ceil(len(pi) / 4))
        ii = np.concatenate([np.arange(s, s + 4) for s in rng.integers(0, len(pi) - 3, nb)])[:len(pi)]
        d.append(np.corrcoef(x1[ii], yv[ii])[0, 1] ** 2 - np.corrcoef(x0[ii], yv[ii])[0, 1] ** 2)
    d = np.array(d)
    rec('O1', f'price17~{f}|R2(lag1)-R2(lag0)', mean=np.nanmean(d), share_pos=np.nanmean(d > 0),
        ci_lo=np.nanquantile(d, .05), ci_hi=np.nanquantile(d, .95))

# ================================================================== O2 surveys
surveys = ['ea_ec_food_ind_sell_price_exp__d4', 'w_ec_food_ind_sell_price_exp_lvl', 'w_ec_food_ind_sell_price_exp_d4',
           'no_ssb_bts_consgoods_home_price_exp__lvl', 'no_ssb_bts_consgoods_home_price_exp__d4',
           'se_ec_retail_sell_price_exp__lvl']
for f in surveys:
    for tg in ['og', 'd_og']:
        for h in (1, 2, 4):
            xa = XR[h][f]
            extra = None
            tag = f'{tg}~{f}|rt{h}'
            for s in ['full', 'exepi', 'exepi+excovid']:
                r = V.fit_one(T, tg, xa, sample=s)
                rec('O2', f'{tag}|{s}|HAC4', b=r['b']['x'], t=r['t']['x'], n=r['n'])
            r = V.fit_one(T, tg, xa, L=8)
            rec('O2', f'{tag}|full|HAC8', b=r['b']['x'], t=r['t']['x'], n=r['n'])
            pl = V.placebo_t(T, tg, xa, nsim=1000, F_source=F[f])
            rec('O2', f'{tag}|full|placebo', t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal'])
            pl = V.placebo_t(T, tg, xa, nsim=1000, F_source=F[f], sample='exepi')
            rec('O2', f'{tag}|exepi|placebo', t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal'])
            if tg == 'd_og':
                # in-sample: control the base og_{t-4} itself (mechanical part of d_og)
                Z = pd.concat([xa.rename('x'), T['og'].shift(4).rename('og4')], axis=1)
                r = V.fit_one(T, tg, Z)
                rec('O2', f'{tag}|full|ctrl_og(t-4)', b=r['b']['x'], t=r['t']['x'], n=r['n'])
                r = V.fit_one(T, tg, Z, sample='exepi')
                rec('O2', f'{tag}|exepi|ctrl_og(t-4)', b=r['b']['x'], t=r['t']['x'], n=r['n'])
            if tg == 'og':
                Z = pd.concat([xa.rename('x'), Xc['w_food_cpi_xvat_yoy'].rename('cpi0')], axis=1)
                r = V.fit_one(T, tg, Z)
                rec('O2', f'{tag}|full|ctrl_foodcpi_t', b=r['b']['x'], t=r['t']['x'], n=r['n'])

# ---- OOS engine for og / d_og
TR_EX = ('2020Q1', '2021Q2')
evalm = {'full2010': None, 'exepi': pd.Series(V.sample_mask(T, 'exepi'), idx),
         'excovid+exepi': pd.Series(V.sample_mask(T, 'exepi+excovid'), idx),
         '2015+': pd.Series(np.asarray(idx >= pd.Period('2015Q1')), idx)}


def og_base(h, levels=True):
    lags = [h + 1] + ([4] if h + 1 < 4 else [])
    return pd.DataFrame({f'og{l}': T['og'].shift(l) for l in lags}, index=idx)


def run(claim, name, target, h, Zx, base=None):
    B = og_base(h) if base is None else base
    w = T['w_og'] if target == 'og' else T['w_d_og']
    fb, fm, yy = V.oos_forecasts(T[target], B, Zx, w.fillna(0), idx, h=h)
    for en, em in evalm.items():
        s = V.oos_summary(yy, fb, fm, em)
        rec(claim, f'OOS|{name}|{target}|h{h}|{en}', **s)
    return fb, fm, yy


for f in surveys:
    for h in (1, 2):
        run('O2', f, 'og', h, XR[h][[f]])
        run('O2', f, 'd_og', h, XR[h][[f]])   # og-level base for d_og

# ================================================================== O3 real wages / confidence
for f in ['w_real_wage_yoy', 'nw_real_wage_yoy', 'w_cons_conf_z', 'nw_cons_conf_z']:
    for al, X in [('coin', Xc), ('rt0', XR[0])]:
        xa = X[f]
        for s in ['full', 'exepi', 'exepi+excovid']:
            r = V.fit_one(T, 'og', xa, sample=s)
            rec('O3', f'og~{f}|{al}|{s}', b=r['b']['x'], t=r['t']['x'], n=r['n'])
            r = V.fit_one(T, 'og', pd.concat([xa.rename('x'), Xc['w_food_cpi_xvat_yoy'].rename('c')], axis=1), sample=s)
            rec('O3', f'og~{f}|{al}|{s}|ctrl_foodcpi', b=r['b']['x'], t=r['t']['x'], t_ctrl=r['t']['c'], n=r['n'])
            r = V.fit_one(T, 'vol_proxy', xa, sample=s)
            rec('O3', f'vol_proxy~{f}|{al}|{s}', b=r['b']['x'], t=r['t']['x'], n=r['n'])
        pl = V.placebo_t(T, 'og', xa, nsim=1000, F_source=F[f])
        rec('O3', f'og~{f}|{al}|full|placebo', t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal'])
# Granger og <-> confidence (4 lags each, HAC), 2002-2026, COVID quarters included / excluded
for f in ['nw_cons_conf_z', 'w_cons_conf_z']:
    c = Xc[f]
    og = T['og']
    for excl in (False, True):
        m = pd.Series(~V.mask_period(idx, '2020Q1', '2021Q4') if excl else np.ones(len(idx), bool), idx)
        L4 = lambda s, nm: pd.DataFrame({f'{nm}{k}': s.shift(k) for k in range(1, 5)})
        # og -> conf
        Z = pd.concat([L4(c, 'c'), L4(og, 'o')], axis=1)
        r = V.hac_fit(c.where(m & og.notna()), Z, None, 4)
        cols = [k for k in r['b'].index if k.startswith('o')]
        W = float(r['b'][cols] @ np.linalg.pinv(r['V'].loc[cols, cols]) @ r['b'][cols])
        p1 = 1 - stats.f.cdf(W / 4, 4, r['df'])
        # conf -> og (with easter control)
        Z2 = pd.concat([L4(og, 'o'), L4(c, 'c'), T['easter_shift']], axis=1)
        r2 = V.hac_fit(og.where(m), Z2, T['w_og'], 4)
        cols2 = [k for k in r2['b'].index if k.startswith('c')]
        W2 = float(r2['b'][cols2] @ np.linalg.pinv(r2['V'].loc[cols2, cols2]) @ r2['b'][cols2])
        p2 = 1 - stats.f.cdf(W2 / 4, 4, r2['df'])
        rec('O3', f'granger|{f}|exCOVID={excl}', p_og_to_conf=p1, p_conf_to_og=p2, sum_og_lags=float(r['b'][cols].sum()),
            sum_conf_lags=float(r2['b'][cols2].sum()))
# Nordic nowcast model
nord = ['nw_food_cpi_xvat_yoy', 'nw_real_wage_yoy', 'nw_cons_conf_z']
run('O3', 'nordic_nowcast', 'og', 0, XR[0][nord])
for drop in nord:
    run('O3', f'nordic_nowcast_minus_{drop}', 'og', 0, XR[0][[c for c in nord if c != drop]])
for f in nord:
    run('O3', f'single_{f}', 'og', 0, XR[0][[f]])

# ================================================================== O4 volume proxy
P2 = pd.concat([T['vol_proxy'], T['volume_mix']], axis=1).dropna()
rr = np.corrcoef(P2.iloc[:, 0], P2.iloc[:, 1])[0, 1]
rng = np.random.default_rng(7)
bs = []
for _ in range(5000):
    n = len(P2)
    ii = np.concatenate([np.arange(s, s + 4) for s in rng.integers(0, n - 3, int(np.ceil(n / 4)))])[:n]
    bs.append(np.corrcoef(P2.iloc[ii, 0], P2.iloc[ii, 1])[0, 1])
rec('O4', 'vol_proxy_vs_reported_volume', n=len(P2), r=rr, ci_lo=np.nanquantile(bs, .025), ci_hi=np.nanquantile(bs, .975),
    r_ex2025=np.corrcoef(P2[P2.index.year != 2025].iloc[:, 0], P2[P2.index.year != 2025].iloc[:, 1])[0, 1])
xr = Xc['w_food_rel_xvat_yoy']
full_battery('O4', 'vol_proxy', xr, 'vol~food_rel|coin', samples=('full', 'exepi', 'exepi+excovid', 'pre2020'),
             src=F['w_food_rel_xvat_yoy'])
# mechanical decomposition: og on food CPI and headline CPI separately
for s in ['full', 'exepi']:
    Z = pd.concat([Xc['w_food_cpi_xvat_yoy'].rename('x'), Xc['w_cpi_yoy'].rename('cpi')], axis=1)
    r = V.fit_one(T, 'og', Z, sample=s)
    rec('O4', f'og~foodcpi+cpi|{s}', b_food=r['b']['x'], t_food=r['t']['x'], b_cpi=r['b']['cpi'], t_cpi=r['t']['cpi'],
        n=r['n'])
    # vol proxy on relative food inflation controlling food CPI level itself (pass-through < 1 confound)
    Z = pd.concat([xr.rename('x'), Xc['w_food_cpi_xvat_yoy'].rename('food')], axis=1)
    r = V.fit_one(T, 'vol_proxy', Z, sample=s)
    rec('O4', f'vol~food_rel+foodcpi|{s}', b=r['b']['x'], t=r['t']['x'], b_food=r['b']['food'], t_food=r['t']['food'])
for f in ['w_hh_real_inc_yoy', 'w_gdp_vol_yoy']:
    full_battery('O4', 'vol_proxy', Xc[f], f'vol~{f}|coin', samples=('full', 'exepi', 'exepi+excovid'), src=F[f])
# real-time predictability of vol_proxy: placebo-calibrated scan of all core features at rt1 and rt2
core = [c for c in D.index[D['core'] == True] if c in F.columns]
scan = []
for h in (1, 2):
    for f in core:
        xa = XR[h][f]
        if xa.notna().sum() < 40 or f in ('w_food_cpi_xvat_yoy',):
            continue
        try:
            pl = V.placebo_t(T, 'vol_proxy', xa, nsim=500, F_source=F[f], seed=h)
        except Exception:
            continue
        scan.append(dict(h=h, feature=f, t=pl['t_obs'], p_cal=pl['p_cal']))
S = pd.DataFrame(scan)
S['by'] = S.groupby('h')['p_cal'].transform(lambda p: V.by_adjust(p))
S.to_csv(f'{V.OUT}/o4_volproxy_rt_scan.csv', index=False)
for h, g in S.groupby('h'):
    rec('O4', f'vol_proxy_rt{h}_scan', n_tests=len(g), n_by10=int((g.by < 0.10).sum()),
        best=g.loc[g.t.abs().idxmax(), 'feature'], best_t=g.t.abs().max(), best_pcal=g.p_cal.min())
# unemployment h=2 OOS for og
for h in (1, 2):
    run('O4', 'w_unemp_d4', 'og', h, XR[h][['w_unemp_d4']])
    run('O4', 'w_unemp_d4', 'd_og', h, XR[h][['w_unemp_d4']])
for s in ['full', 'exepi', 'exepi+excovid']:
    r = V.fit_one(T, 'og', XR[2]['w_unemp_d4'], sample=s)
    rec('O4', f'og~w_unemp_d4|rt2|{s}', b=r['b']['x'], t=r['t']['x'], n=r['n'])
    r = V.fit_one(T, 'vol_proxy', XR[2]['w_unemp_d4'], sample=s)
    rec('O4', f'vol_proxy~w_unemp_d4|rt2|{s}', b=r['b']['x'], t=r['t']['x'], n=r['n'])

# ================================================================== O5 d_og mechanics
d = pd.concat([T['d_og'], T['og'].shift(4), T['og']], axis=1).dropna()
rec('O5', 'corr(d_og, og_t-4)', r=np.corrcoef(d.iloc[:, 0], d.iloc[:, 1])[0, 1], n=len(d),
    acf4_og=np.corrcoef(d.iloc[:, 2], d.iloc[:, 1])[0, 1],
    iid_benchmark=-np.sqrt((1 - np.corrcoef(d.iloc[:, 2], d.iloc[:, 1])[0, 1]) / 2))
og = T['og'].dropna()
for k in (1, 2, 4):
    rec('O5', f'acf_og_lag{k}', r=og.autocorr(k))
for h in (0, 1, 2):
    fb, fm, yy = V.oos_forecasts(T['d_og'], pd.DataFrame(index=idx), og_base(h), T['w_d_og'].fillna(0), idx, h=h)
    for en, em in evalm.items():
        dfz = pd.concat([yy, fm], axis=1).dropna()
        if em is not None:
            dfz = dfz[em.reindex(dfz.index).values]
        r2z = 1 - ((dfz.iloc[:, 0] - dfz.iloc[:, 1]) ** 2).sum() / (dfz.iloc[:, 0] ** 2).sum()
        rec('O5', f'OOS|oglevelAR_for_d_og|h{h}|{en}', r2_vs_zero=r2z, n=len(dfz))
    # og-level AR vs prevailing mean for og itself
    fb, fm, yy = V.oos_forecasts(T['og'], pd.DataFrame(index=idx), og_base(h), T['w_og'].fillna(0), idx, h=h)
    s = V.oos_summary(yy, fb, fm)
    rec('O5', f'OOS|og_AR_vs_mean|h{h}', **s)
for f, al in [('w_food_cpi_xvat_dyoy', 'coin'), ('w_food_cpi_xvat_dyoy', 'rt0'), ('nw_food_cpi_xvat_dyoy', 'coin'),
              ('nw_food_ppi_dyoy', 'rt0'), ('w_food_ppi_dyoy', 'rt0'), ('nw_food_ppi_dyoy', 'coin')]:
    xa = (Xc if al == 'coin' else XR[0])[f]
    full_battery('O5', 'd_og', xa, f'd_og~{f}|{al}', samples=('full', 'exepi', 'exepi+excovid', 'exbreak'), src=F[f])
    Z = pd.concat([xa.rename('x'), T['og'].shift(4).rename('og4')], axis=1)
    for s in ('full', 'exepi'):
        r = V.fit_one(T, 'd_og', Z, sample=s)
        rec('O5', f'd_og~{f}|{al}|{s}|ctrl_og(t-4)', b=r['b']['x'], t=r['t']['x'])

# ================================================================== O6 policy rates
for h in (2, 3, 4):
    xa = XR[h]['w_policy_rate_d4']
    for s in ['full', 'exepi', 'exepi+excovid', 'pre2020']:
        r = V.fit_one(T, 'og', xa, sample=s)
        rec('O6', f'og~w_policy_rate_d4|rt{h}|{s}', b=r['b']['x'], t=r['t']['x'], n=r['n'])
    for en in ['2001-12', '2013-26', '2013-20']:
        a, b_ = eras[en]
        m = pd.Series(V.mask_period(idx, a, b_), idx)
        r = V.hac_fit(T['og'].where(m), pd.concat([xa.rename('x'), T['easter_shift']], axis=1), T['w_og'], 4)
        rec('O6', f'og~w_policy_rate_d4|rt{h}|era {en}', b=r['b']['x'], t=r['t']['x'], n=r['n'])
    r = V.fit_one(T, 'og', xa, L=8)
    rec('O6', f'og~w_policy_rate_d4|rt{h}|full|HAC8', b=r['b']['x'], t=r['t']['x'])
    pl = V.placebo_t(T, 'og', xa, nsim=2000, F_source=F['w_policy_rate_d4'])
    rec('O6', f'og~w_policy_rate_d4|rt{h}|full|placebo', t=pl['t_obs'], q95=pl['q95'], p_cal=pl['p_cal'])
    # real-time control: food CPI known at the forecast origin (not the coincident value)
    Z = pd.concat([xa.rename('x'), XR[h]['w_food_cpi_xvat_yoy'].rename('c')], axis=1)
    r = V.fit_one(T, 'og', Z)
    rec('O6', f'og~w_policy_rate_d4|rt{h}|ctrl_rt_foodcpi', b=r['b']['x'], t=r['t']['x'], t_ctrl=r['t']['c'])
    Z = pd.concat([xa.rename('x'), T['og'].shift(h + 1).rename('ogl')], axis=1)
    r = V.fit_one(T, 'og', Z)
    rec('O6', f'og~w_policy_rate_d4|rt{h}|ctrl_own_og(t-h-1)', b=r['b']['x'], t=r['t']['x'], t_ctrl=r['t']['c'] if 'c' in r['t'] else np.nan)
for h in (1, 2):
    run('O6', 'w_policy_rate_d4', 'og', h, XR[h][['w_policy_rate_d4']])

R = pd.DataFrame(rows)
R.to_csv(f'{V.OUT}/o_results.csv', index=False)
print(R.round(4).to_string())
