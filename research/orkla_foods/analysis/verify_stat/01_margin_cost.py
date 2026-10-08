"""M1/M2: same-quarter input-cost effects on d_margin; raw-material DL response; asymmetry."""
import warnings
import numpy as np
import pandas as pd
import vlib as V

warnings.filterwarnings('ignore')
T, F, D = V.load()
idx = T.index
Xc = V.X_at(F, D, 'coincident', idx=idx)
X0 = V.X_at(F, D, 'realtime', 0, idx=idx)
rows = []


def rec(claim, test, **kw):
    d = dict(claim=claim, test=test)
    d.update(kw)
    rows.append(d)
    print(claim, test, {k: (round(v, 4) if isinstance(v, (float, np.floating)) else v) for k, v in kw.items()})


SAMPLES = ['full', 'exepi', 'excovid', 'exbreak', 'exepi+excovid', 'exepi+excovid+exbreak', 'pre2020']
for feat, X, al in [('packaging_eu_yoy', Xc, 'coin'), ('packaging_eu_yoy', X0, 'rt0'),
                    ('eu_ppi_plastic_products_idx__yoy', Xc, 'coin'), ('eu_ppi_plastic_products_idx__yoy', X0, 'rt0')]:
    x = X[feat]
    for s in SAMPLES:
        for L in (4, 8):
            r = V.fit_one(T, 'd_margin', x, L=L, sample=s)
            rec('M1', f'{feat}|{al}|{s}|HAC{L}', b=r['b']['x'], t=r['t']['x'], n=r['n'])
    for s in ['full', 'exepi']:
        pl = V.placebo_t(T, 'd_margin', x, nsim=2000, sample=s, F_source=F[feat])
        rec('M1', f'{feat}|{al}|{s}|placebo', t=pl['t_obs'], q95=pl['q95'], size5=pl['size5'], p_emp=pl['p_emp'],
            p_cal=pl['p_cal'])
        t0, ts = V.circ_shift_t(T, 'd_margin', x, sample=s)
        rec('M1', f'{feat}|{al}|{s}|circshift', t=t0, q95=np.nanquantile(np.abs(ts), 0.95),
            p_circ=(np.sum(np.abs(ts) >= abs(t0)) + 1) / (len(ts) + 1), nshift=len(ts))
        y, Xd, w = V.design(T, 'd_margin', x, sample=s)
        bb = V.mbb_coef(y, Xd, w, nboot=2000, block=8)
        rec('M1', f'{feat}|{al}|{s}|mbb8', b=bb['b'], se=bb['se_boot'], t=bb['t_boot'], ci_lo=bb['ci'][0],
            ci_hi=bb['ci'][1], p_boot=bb['p_boot'])

# Family-wise: is "single strongest of 200 core features" significant against the max-|t| circular-shift null?
core = [c for c in D.index[D['core'] == True] if c in F.columns]
for al, X in [('coin', Xc), ('rt0', X0)]:
    for s in ['full', 'exepi']:
        tobs, tmax = {}, None
        allshift = []
        for f in core:
            x = X[f]
            if x.notna().sum() < 40 or x.std() == 0:
                continue
            try:
                t0, ts = V.circ_shift_t(T, 'd_margin', x, sample=s)
            except Exception:
                continue
            tobs[f] = t0
            allshift.append(np.abs(ts))
        M = np.vstack([a[:min(map(len, allshift))] for a in allshift])
        maxnull = np.nanmax(M, axis=0)
        obs = pd.Series(tobs)
        top = obs.abs().sort_values(ascending=False).head(5)
        for f in top.index:
            rec('M1', f'familywise_max|{al}|{s}|{f}', t=obs[f], maxnull_q95=np.quantile(maxnull, 0.95),
                p_fwer=(np.sum(maxnull >= abs(obs[f])) + 1) / (len(maxnull) + 1), rank=int(list(top.index).index(f) + 1))
        pd.DataFrame({'feature': obs.index, 't': obs.values}).to_csv(f'{V.OUT}/m1_core_t_{al}_{s}.csv', index=False)


# ----------------------------------------------------------------- raw-material distributed lags
def lagmat(x, K):
    return pd.DataFrame({f'L{k}': x.shift(k) for k in range(K + 1)})


def pdl(x, K, P):
    Lm = lagmat(x, K)
    ks = np.arange(K + 1)
    H = np.vstack([(ks / K) ** p for p in range(P + 1)]).T
    Z = pd.DataFrame(Lm.values @ H, index=Lm.index, columns=[f'p{p}' for p in range(P + 1)])
    Z[Lm.isna().any(axis=1)] = np.nan
    return Z, H


def dl_profile(y, x, K, P=None, sample_mask=None, L=4, nboot=1000, block=8, seed=1):
    yy = y.where(sample_mask) if sample_mask is not None else y
    if P is None:
        Z = lagmat(x, K)
        H = np.eye(K + 1)
    else:
        Z, H = pdl(x, K, P)
    r = V.hac_fit(yy, Z, None, L)
    a = r['b'][Z.columns].values
    Va = r['V'].loc[Z.columns, Z.columns].values
    beta = H @ a
    cum = np.cumsum(beta) * 10  # level response to permanent +10% cost-level shock
    Lc = np.tril(np.ones((K + 1, K + 1)))
    se_cum = np.sqrt(np.diag(Lc @ H @ Va @ H.T @ Lc.T)) * 10
    # block bootstrap of trough, trough lag and recovery lag
    df = pd.concat([yy.rename('_y'), Z], axis=1).dropna()
    n = len(df)
    A = np.column_stack([np.ones(n), df[Z.columns].values])
    yv = df['_y'].values
    rng = np.random.default_rng(seed)
    tr, trl, recl = [], [], []
    for _ in range(nboot):
        nb = int(np.ceil(n / block))
        ii = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, n - block + 1, nb)])[:n]
        bb = np.linalg.lstsq(A[ii], yv[ii], rcond=None)[0][1:]
        c = np.cumsum(H @ bb) * 10
        i0 = int(np.argmin(c))
        tr.append(c[i0])
        trl.append(i0)
        after = np.where(c[i0:] > 0.5 * c[i0])[0] if c[i0] < 0 else []
        recl.append(i0 + after[0] if len(after) else np.nan)
    i0 = int(np.argmin(cum))
    after = np.where(cum[i0:] > 0.5 * cum[i0])[0]
    zero = np.where(cum[i0:] >= 0)[0]
    return dict(n=n, cum=cum, se_cum=se_cum, trough=cum[i0], trough_lag=i0,
                half_rec=(i0 + after[0]) if len(after) else np.nan,
                zero_rec=(i0 + zero[0]) if len(zero) else np.nan,
                trough_ci=(np.quantile(tr, 0.05), np.quantile(tr, 0.95)),
                trough_lag_ci=(np.quantile(trl, 0.05), np.quantile(trl, 0.95)),
                half_rec_na=np.mean(np.isnan(recl)),
                half_rec_ci=(np.nanquantile(recl, 0.05), np.nanquantile(recl, 0.95)) if np.isfinite(recl).any() else (np.nan, np.nan))


y = T['d_margin']
prof_rows = []
for feat in ['raw_mat_wloc_yoy', 'eu_agri_basket_wloc_yoy', 'fao_ffpi_wloc_yoy', 'cost_idx_calib_yoy', 'packaging_eu_yoy']:
    x = Xc[feat]
    for s in ['full', 'exepi', 'exepi+excovid', 'exepi+execho']:
        m = pd.Series(V.sample_mask(T, s), idx)
        for K, P in [(6, None), (6, 2), (12, 3)]:
            for L in (4, 8):
                pr = V.dl_profile(y, x, K, P, m, L) if hasattr(V, 'dl_profile') else dl_profile(y, x, K, P, m, L,
                                                                                            nboot=500 if L == 8 else 1000)
                tag = f'{feat}|{s}|K{K}P{P}|HAC{L}'
                rec('M1dl', tag, n=pr['n'], trough=pr['trough'], trough_lag=pr['trough_lag'],
                    trough_t=pr['trough'] / pr['se_cum'][pr['trough_lag']], half_rec=pr['half_rec'],
                    zero_rec=pr['zero_rec'], trough_ci_lo=pr['trough_ci'][0], trough_ci_hi=pr['trough_ci'][1],
                    half_rec_na=pr['half_rec_na'], half_rec_ci_lo=pr['half_rec_ci'][0], half_rec_ci_hi=pr['half_rec_ci'][1])
                for k in range(len(pr['cum'])):
                    prof_rows.append(dict(tag=tag, lag=k, cum=pr['cum'][k], se=pr['se_cum'][k]))
pd.DataFrame(prof_rows).to_csv(f'{V.OUT}/m1_dl_profiles.csv', index=False)

# ----------------------------------------------------------------- M2 asymmetry
x = Xc['raw_mat_wloc_yoy']
xp, xn = x.clip(lower=0), x.clip(upper=0)
print('share of quarters with raw_mat inflation <0:', (x.reindex(idx[V.mask_period(idx, '2001Q1', '2026Q2')]) < 0).mean())
for s in ['full', 'exepi', 'exepi+excovid', 'exepi+execho']:
    m = pd.Series(V.sample_mask(T, s), idx)
    yy = y.where(m)
    for K, P in [(6, 2), (6, None)]:
        if P is None:
            Zp, Hp = lagmat(xp, K), np.eye(K + 1)
            Zn, Hn = lagmat(xn, K), np.eye(K + 1)
        else:
            Zp, Hp = pdl(xp, K, P)
            Zn, Hn = pdl(xn, K, P)
        Zp.columns = ['pos_' + c for c in Zp.columns]
        Zn.columns = ['neg_' + c for c in Zn.columns]
        Z = pd.concat([Zp, Zn], axis=1)
        for L in (4, 8):
            r = V.hac_fit(yy, Z, None, L)
            bp = Hp @ r['b'][Zp.columns].values
            bn = Hn @ r['b'][Zn.columns].values
            Vp = Hp @ r['V'].loc[Zp.columns, Zp.columns].values @ Hp.T
            Vn = Hn @ r['V'].loc[Zn.columns, Zn.columns].values @ Hn.T
            Vpn = Hp @ r['V'].loc[Zp.columns, Zn.columns].values @ Hn.T
            Lc = np.tril(np.ones((K + 1, K + 1)))
            cp, cn = Lc @ bp * 10, Lc @ bn * -10  # +10pp increase; -10pp decrease
            se_p = np.sqrt(np.diag(Lc @ Vp @ Lc.T)) * 10
            se_n = np.sqrt(np.diag(Lc @ Vn @ Lc.T)) * 10
            # difference in cumulative response per 1pp (symmetry: cum_pos == cum_neg coefficient)
            dV = Lc @ (Vp + Vn - Vpn - Vpn.T) @ Lc.T
            dcum = Lc @ (bp - bn)
            tdiff = dcum / np.sqrt(np.diag(dV))
            # count quarters with any negative raw-material inflation in the lag window used
            df = pd.concat([yy.rename('y'), Z], axis=1).dropna()
            nneg = int((xn.reindex(df.index) < 0).sum())
            rec('M2', f'asym|{s}|K{K}P{P}|HAC{L}', n=r['n'], n_neg_quarters=nneg,
                inc_cum_l1=cp[1], inc_cum_l2=cp[2], inc_t_l2=cp[2] / se_p[2],
                dec_cum_l2=cn[2], dec_cum_l3=cn[3], dec_cum_l6=cn[6], dec_t_l6=cn[6] / se_n[6],
                tdiff_l2=tdiff[2], tdiff_l6=tdiff[6])
pd.DataFrame(rows).to_csv(f'{V.OUT}/m1_m2_results.csv', index=False)
