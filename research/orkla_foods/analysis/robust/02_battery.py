"""Step 2: robustness / stability battery for each candidate x target x alignment.

Candidates per target = 15 de-duplicated screen leaders (screen_selected.csv) + the a-priori
hypothesis list below (tested for every target regardless of rank).
Alignments: coincident; realtime h=0 (skipped when identical to coincident, i.e. lag-0 features);
realtime h=1, h=2, h=4 (C.align). All regressions use the target's control set and weights from
robust_lib (definition dummies, COVID, Easter, d_og definition-break flag) and Newey-West HAC
(4 lags unless stated). x is standardised once over the full regression sample, so every
sub-sample beta is in the same units (target units per full-sample SD of x).

Checks per row:
  full sample (HAC4, HAC8), linear-trend control, first differences, AR(2) placebo (Granger-Newbold
  spurious-regression check: 400 independent persistent series with x's own AR(2) dynamics replace x;
  empirical p-value of |t|), sub-samples (4 definition eras, pre/post 2013, ex COVID 2020-21,
  ex 2021Q3-2023Q4, ex India periods, inflation episode only), definition-break Chow tests (slope
  interaction at each break and joint equal-slopes-across-eras Wald test), Quandt-Andrews sup-Wald
  for a slope break (15% trimming), leave-one-year-out, non-overlapping samples (Q4 observations
  only; calendar-year averages, HAC 1 lag), rolling 32-quarter slope and correlation, the share of
  the full-sample covariance contributed by 2021Q3-2023Q4, and Granger-style tests in both
  directions (4 lags of y and x, raw feature timing).

Outputs: battery_raw.csv (one row per candidate x target x alignment), rolling_32q.csv (long),
loyo_detail.csv (long).
"""
import time
import numpy as np
import pandas as pd
import robust_lib as R
C = R.C

APRIORI = {
    'real_wage': ['w_real_wage_yoy', 'w_real_wage_dyoy', 'nw_real_wage_yoy', 'nw_real_wage_dyoy'],
    'cons_conf': ['w_cons_conf_z', 'w_cons_conf_z_d4', 'nw_cons_conf_z', 'nw_cons_conf_z_d4',
                  'no_fn_cci_sa__lvl', 'no_fn_cci_sa__d4', 'se_nier_cons_conf__lvl', 'se_nier_cons_conf__d4'],
    'sell_price_exp': ['w_ec_food_ind_sell_price_exp_lvl', 'w_ec_food_ind_sell_price_exp_d4',
                       'se_nier_food_mfg_sell_price_exp__lvl', 'se_nier_food_mfg_sell_price_exp__d4'],
    'rates': ['w_policy_rate_lvl', 'w_policy_rate_d4', 'w_gov10y_lvl', 'w_gov10y_d4'],
    'fx': ['w_fx_vs_eur_yoy', 'no_fx_eurnok__yoy', 'se_eursek__yoy'],
    'food_cpi_xvat': ['w_food_cpi_xvat_yoy', 'w_food_cpi_xvat_dyoy', 'nw_food_cpi_xvat_yoy', 'nw_food_cpi_xvat_dyoy'],
    'food_ppi': ['w_food_ppi_yoy', 'w_food_ppi_dyoy', 'nw_food_ppi_yoy'],
    'price_cost_gap': ['price_cost_gap_ppi', 'price_cost_gap_ppi_d4', 'nw_price_cost_gap_ppi',
                       'price_cost_gap_fao_wloc', 'price_cost_gap_agri', 'price_wage_gap'],
    'fao_food': ['glob_fao_ffpi_nok__yoy', 'glob_fao_ffpi_eur__yoy', 'fao_ffpi_wloc_yoy'],
    'eu_agri': ['eu_agri_basket_yoy', 'eu_agri_basket_wloc_yoy'],
    'energy': ['elec_nordic_loc_yoy', 'natgas_eu_eur_yoy', 'brent_nok_yoy'],
    'unemployment': ['w_unemp_lvl', 'w_unemp_d4'],
}
APRIORI_GROUP = {f: g for g, fs in APRIORI.items() for f in fs}
ALIGNS = [('coincident', 'coincident', 0), ('rt_h0', 'realtime', 0), ('rt_h1', 'realtime', 1),
          ('rt_h2', 'realtime', 2), ('rt_h4', 'realtime', 4)]
N_PLACEBO = 400
CHANNEL = {'d_margin': 'w_food_ppi_yoy', 'og': 'w_food_cpi_xvat_yoy', 'd_og': 'w_food_cpi_xvat_dyoy'}
rng = np.random.default_rng(20261006)

T = R.load_T()
Fall, Dall = C.load_features(core_only=False)
Sel = pd.read_csv(f'{R.OUT}/screen_selected.csv')
feats = sorted(set(Sel['feature']) | set(APRIORI_GROUP))
F, D = Fall[feats], Dall.loc[feats]
XA = {a: C.align(F, D, m, h) for a, m, h in ALIGNS}
idx_all = F.index
pos = {p: i for i, p in enumerate(idx_all)}

# AR(2) fits for the placebo (on the raw feature over its available contiguous sample)
ar2 = {}
for f in feats:
    s = F[f].dropna()
    s = s.loc[s.index >= pd.Period('1997Q1', 'Q')]
    y_, X_ = s.values[2:], np.column_stack([np.ones(len(s) - 2), s.values[1:-1], s.values[:-2]])
    b, *_ = np.linalg.lstsq(X_, y_, rcond=None)
    e = y_ - X_ @ b
    # enforce stationarity (shrink if needed)
    phi = b[1:].copy()
    for _ in range(50):
        roots = np.roots([1, -phi[0], -phi[1]])
        if np.all(np.abs(roots) < 0.995):
            break
        phi *= 0.98
    ar2[f] = (phi, e.std(ddof=3))


def sim_ar2(phi, sd, n, nsim, burn=100):
    e = rng.standard_normal((nsim, n + burn)) * sd
    x = np.zeros((nsim, n + burn))
    for t in range(2, n + burn):
        x[:, t] = phi[0] * x[:, t - 1] + phi[1] * x[:, t - 2] + e[:, t]
    return x[:, burn:]


def sub(idx, name):
    """Boolean mask for a named sub-sample over a PeriodIndex."""
    if name in R.ERAS:
        return R.in_range(idx, *R.ERAS[name])
    if name == 'pre2013':
        return idx < pd.Period('2013Q1', 'Q')
    if name == 'post2013':
        return idx >= pd.Period('2013Q1', 'Q')
    if name == 'ex_covid':
        return ~R.in_range(idx, *R.COVID)
    if name == 'ex_infl':
        return ~R.in_range(idx, *R.INFL)
    if name == 'infl_only':
        return R.in_range(idx, *R.INFL)
    if name == 'ex_india':
        return ~(R.in_range(idx, '2014Q4', '2022Q2') | R.in_range(idx, '2007Q2', '2007Q4'))
    if name == 'ex_covid_infl':
        return ~(R.in_range(idx, *R.COVID) | R.in_range(idx, *R.INFL))
    raise ValueError(name)


SUBS = list(R.ERAS) + ['pre2013', 'post2013', 'ex_covid', 'ex_infl', 'ex_covid_infl', 'ex_india', 'infl_only']


def reg(yv, Xv, wv, mask=None, lags=R.HAC_LAGS, min_n=10):
    if mask is not None:
        yv, Xv = yv[mask], Xv[mask]
        wv = wv[mask] if wv is not None else None
    if len(yv) < min_n or Xv[:, 0].std() < 1e-12:
        return None
    return R.hac_ols(yv, Xv, wv, lags=lags)


rows, roll_rows, loyo_rows = [], [], []
t0 = time.time()
for tgt in R.TARGETS:
    y = T[tgt]
    Ctrl = R.controls_for(tgt, T)
    w = R.weights_for(tgt, T)
    screened = set(Sel.loc[Sel.target == tgt, 'feature'])
    cands = sorted(screened | set(APRIORI_GROUP))
    # residualised target for rolling correlations (controls only, full sample)
    yc, Cc, wc, ic = R.frame(y, Ctrl.iloc[:, 0], Ctrl.iloc[:, 1:], w)
    Zc = np.column_stack([Cc, np.ones(len(yc))])
    yres_full = pd.Series(yc - Zc @ np.linalg.lstsq(Zc, yc, rcond=None)[0], index=ic)

    # Granger-style tests (raw timing, independent of alignment)
    granger = {}
    for f in cands:
        x = F[f]
        lagsY = pd.concat({f'y_l{j}': y.shift(j) for j in range(1, 5)}, axis=1)
        lagsX = pd.concat({f'x_l{j}': x.shift(j) for j in range(1, 5)}, axis=1)
        # x -> y
        df = pd.concat([y.rename('_y'), lagsX, lagsY, Ctrl], axis=1)
        if w is not None:
            df['_w'] = w
        df = df.dropna()
        if w is not None:
            df = df[df['_w'] > 0]
        p_xy = np.nan
        if len(df) >= 40:
            Xg = df.drop(columns=['_y'] + (['_w'] if w is not None else [])).values
            r = R.hac_ols(df['_y'].values, Xg, df['_w'].values if w is not None else None, drop_const_cols=False)
            _, p_xy = R.wald(r, [0, 1, 2, 3])
            sum_x = r['beta'][:4].sum() * x.std()
        # y -> x
        df2 = pd.concat([x.rename('_x'), lagsY, lagsX, Ctrl[['def_B', 'def_C', 'def_D', 'def_E', 'covid']]], axis=1).dropna()
        p_yx = np.nan
        if len(df2) >= 40:
            r2 = R.hac_ols(df2['_x'].values, df2.drop(columns=['_x']).values, None, drop_const_cols=False)
            _, p_yx = R.wald(r2, [0, 1, 2, 3])
        granger[f] = (p_xy, p_yx, sum_x if len(df) >= 40 else np.nan)

    for f in cands:
        lag = int(D.loc[f, 'realtime_min_lag_q'])
        src = ('screen+a_priori' if f in screened and f in APRIORI_GROUP else
               'screen' if f in screened else 'a_priori')
        for a, mode, h in ALIGNS:
            if a == 'rt_h0' and lag == 0:
                continue
            x = XA[a][f]
            yv, Xv, wv, idx = R.frame(y, x, Ctrl, w)
            if len(yv) < 40:
                continue
            mu, sd = Xv[:, 0].mean(), Xv[:, 0].std()
            if sd < 1e-12:
                continue
            Xv = Xv.copy()
            Xv[:, 0] = (Xv[:, 0] - mu) / sd
            out = dict(target=tgt, candidate=f, alignment=a, source=src,
                       a_priori_group=APRIORI_GROUP.get(f, ''), category=D.loc[f, 'category'],
                       lag_q=lag, horizon=h if mode == 'realtime' else np.nan,
                       same_as_coincident=(a == 'coincident' and lag == 0),
                       sample=f'{idx.min()}-{idx.max()}')
            full = R.hac_ols(yv, Xv, wv)
            b0, t0_, p0 = full['beta'][0], full['t'][0], full['p'][0]
            out.update(n=full['n'], beta_sd=b0, t=t0_, p=p0)
            r8 = R.hac_ols(yv, Xv, wv, lags=8)
            out.update(t_hac8=r8['t'][0], p_hac8=r8['p'][0])
            # partial correlation (y and x residualised on controls)
            Z = np.column_stack([Xv[:, 1:], np.ones(len(yv))])
            ry = yv - Z @ np.linalg.lstsq(Z, yv, rcond=None)[0]
            rx = Xv[:, 0] - Z @ np.linalg.lstsq(Z, Xv[:, 0], rcond=None)[0]
            out['partial_corr'] = np.corrcoef(ry, rx)[0, 1]
            # own-history control: the latest Orkla figure known at the forecast origin (y_{t-h-1});
            # for d_og also the base og_{t-4} when it is already published (h <= 3).
            hh = 0 if mode == 'coincident' else h
            own = pd.concat([y.shift(hh + 1).rename('own1')] +
                            ([T['og'].shift(4).rename('og_base')] if tgt == 'd_og' and hh <= 3 else []), axis=1)
            yo, Xo, wo, io = R.frame(y, x, Ctrl, w, extra=own)
            if len(yo) >= 40:
                Xo = Xo.copy()
                Xo[:, 0] = (Xo[:, 0] - mu) / sd
                ro = R.hac_ols(yo, Xo, wo)
                out.update(b_own=ro['beta'][0], t_own=ro['t'][0], p_own=ro['p'][0])
            # dominant-channel horse race (explanatory, not a gate): add the same-quarter price channel
            # (og: food CPI ex VAT yoy; d_og: its dyoy) or cost channel (d_margin: food PPI yoy).
            ch = CHANNEL.get(tgt)
            if ch is not None and f != ch:
                chs = F[ch].rename('chan')
                cc = pd.concat([x, chs], axis=1).dropna().corr().iloc[0, 1]
                if abs(cc) < 0.9:
                    yh, Xh, wh, ih = R.frame(y, x, Ctrl, w, extra=chs.to_frame())
                    if len(yh) >= 40:
                        Xh = Xh.copy()
                        Xh[:, 0] = (Xh[:, 0] - mu) / sd
                        rh = R.hac_ols(yh, Xh, wh)
                        out.update(b_chan=rh['beta'][0], t_chan=rh['t'][0], p_chan=rh['p'][0], corr_chan=cc)
            # trend control
            tr = T['trend'].reindex(idx).values
            rt_ = R.hac_ols(yv, np.column_stack([Xv, tr]), wv)
            out.update(beta_trend=rt_['beta'][0], t_trend=rt_['t'][0], p_trend=rt_['p'][0])
            # first differences of y and x (consecutive quarters only)
            per = np.array([p.ordinal for p in idx])
            consec = np.diff(per) == 1
            dy = np.diff(yv)[consec]
            dX = np.diff(Xv, axis=0)[consec]
            dw = wv[1:][consec] * wv[:-1][consec] if wv is not None else None
            if dw is not None:
                dw = np.sqrt(dw)
            if len(dy) >= 30:
                rfd = R.hac_ols(dy, dX, dw)
                out.update(beta_fd=rfd['beta'][0], t_fd=rfd['t'][0], p_fd=rfd['p'][0], n_fd=len(dy))
            # AR(2) placebo
            phi, sde = ar2[f]
            positions = np.array([pos[p] for p in idx])
            sims = sim_ar2(phi, sde, positions.max() + 1, N_PLACEBO)[:, positions]
            tabs = np.empty(N_PLACEBO)
            for s_ in range(N_PLACEBO):
                Xs = Xv.copy()
                xs = sims[s_]
                Xs[:, 0] = (xs - xs.mean()) / xs.std()
                tabs[s_] = abs(R.hac_ols(yv, Xs, wv, drop_const_cols=False)['t'][0])
            out['p_placebo'] = (1 + np.sum(tabs >= abs(t0_))) / (1 + N_PLACEBO)
            out['placebo_t95'] = np.quantile(tabs, 0.95)
            out['placebo_size_5pct'] = np.mean(tabs > 1.96)  # rejection rate of nominal 5% HAC test
            # sub-samples
            for sname in SUBS:
                m = sub(idx, sname)
                r = reg(yv, Xv, wv, m, min_n=8 if sname == 'infl_only' else 10)
                if r is None:
                    out.update({f'b_{sname}': np.nan, f't_{sname}': np.nan, f'p_{sname}': np.nan, f'n_{sname}': int(m.sum())})
                else:
                    out.update({f'b_{sname}': r['beta'][0], f't_{sname}': r['t'][0], f'p_{sname}': r['p'][0], f'n_{sname}': r['n']})
            # covariance share of the inflation episode
            m_inf = sub(idx, 'infl_only')
            cov_all = np.sum(ry * rx)
            out['infl_cov_share'] = np.sum(ry[m_inf] * rx[m_inf]) / cov_all if abs(cov_all) > 1e-12 else np.nan
            # Chow-type slope-break tests at definition breaks (x * post interaction; level shifts are
            # already in the definition dummies)
            for br in R.DEF_BREAKS:
                post = (idx >= pd.Period(br, 'Q')).astype(float)
                if post.sum() < 8 or (1 - post).sum() < 8:
                    out[f'chow_p_{br}'] = np.nan
                    continue
                Xb = np.column_stack([Xv[:, 0], Xv[:, 0] * post, post, Xv[:, 1:]])
                rb = R.hac_ols(yv, Xb, wv)
                out[f'chow_p_{br}'] = rb['p'][1]
            # joint: era-specific slopes equal?
            eras = [sub(idx, e).astype(float) for e in R.ERAS]
            ok = [e for e in eras if e.sum() >= 8]
            if len(ok) >= 2:
                inter = [Xv[:, 0] * e for e in ok[1:]]
                Xe = np.column_stack([Xv[:, 0]] + inter + [Xv[:, 1:]])
                re_ = R.hac_ols(yv, Xe, wv)
                W, pW = R.wald(re_, list(range(1, len(ok))))
                out.update(chow_eras_W=W, chow_eras_p=pW, chow_eras_df=len(ok) - 1)
            # Quandt-Andrews sup-Wald (slope break, intercept shift allowed), 15% trimming
            n = len(yv)
            lo, hi = int(np.floor(0.15 * n)), int(np.ceil(0.85 * n))
            best_W, best_i = -1, None
            for i in range(lo, hi):
                post = (np.arange(n) >= i).astype(float)
                Xb = np.column_stack([Xv[:, 0], Xv[:, 0] * post, post, Xv[:, 1:]])
                rb = R.hac_ols(yv, Xb, wv)
                Wb = rb['t'][1] ** 2
                if Wb > best_W:
                    best_W, best_i = Wb, i
            out.update(supW=best_W, supW_date=str(idx[best_i]),
                       supW_sig5=best_W > R.QLR_CV[0.05], supW_sig1=best_W > R.QLR_CV[0.01])
            if best_i is not None:
                pre_m = np.arange(n) < best_i
                rpre, rpost = reg(yv, Xv, wv, pre_m), reg(yv, Xv, wv, ~pre_m)
                out['b_pre_supW'] = rpre['beta'][0] if rpre else np.nan
                out['b_post_supW'] = rpost['beta'][0] if rpost else np.nan
            # leave-one-year-out
            years = idx.year
            lt = []
            for yr in np.unique(years):
                m = years != yr
                r = R.hac_ols(yv[m], Xv[m], wv[m] if wv is not None else None)
                lt.append((yr, r['beta'][0], r['t'][0], r['p'][0]))
                loyo_rows.append(dict(target=tgt, candidate=f, alignment=a, year_dropped=yr,
                                      beta_sd=r['beta'][0], t=r['t'][0], p=r['p'][0]))
            lt = pd.DataFrame(lt, columns=['yr', 'b', 't', 'p'])
            same = np.sign(lt['b']) == np.sign(b0)
            out.update(loyo_min_abs_t_same_sign=lt.loc[same, 't'].abs().min() if same.any() else 0.0,
                       loyo_max_p=lt['p'].max(), loyo_n_sign_flip=int((~same).sum()),
                       loyo_n_p_gt_010=int((lt['p'] > 0.10).sum()),
                       loyo_most_influential_year=int(lt.loc[(lt['b'] - b0).abs().idxmax(), 'yr']),
                       loyo_b_range=f"{lt['b'].min():.3f}..{lt['b'].max():.3f}")
            # non-overlapping samples
            q4 = idx.quarter == 4
            r = reg(yv, Xv, wv, q4, lags=1, min_n=12)
            out.update(b_q4=r['beta'][0] if r else np.nan, t_q4=r['t'][0] if r else np.nan,
                       p_q4=r['p'][0] if r else np.nan, n_q4=r['n'] if r else int(q4.sum()))
            dfa = pd.DataFrame(np.column_stack([yv, Xv]), index=idx)
            dfa['year'] = years
            cnt = dfa.groupby('year').size()
            full_years = cnt[cnt == 4].index
            ann = dfa[dfa['year'].isin(full_years)].groupby('year').mean()
            if len(ann) >= 12:
                Xa = ann.iloc[:, 1:].values
                ra = R.hac_ols(ann.iloc[:, 0].values, Xa, None, lags=1)
                out.update(b_ann=ra['beta'][0], t_ann=ra['t'][0], p_ann=ra['p'][0], n_ann=ra['n'])
            # rolling 32-quarter slope / correlation (target residualised on controls, full sample)
            yr_ = yres_full.reindex(idx).values
            xr_ = Xv[:, 0]
            per_idx = np.array([p.ordinal for p in idx])
            signs = []
            for j in range(len(idx)):
                end = per_idx[j]
                m = (per_idx > end - 32) & (per_idx <= end)
                if m.sum() < 24:
                    continue
                xx, yy = xr_[m], yr_[m]
                if xx.std() < 1e-12:
                    continue
                slope = np.cov(xx, yy, ddof=1)[0, 1] / xx.var(ddof=1)
                corr = np.corrcoef(xx, yy)[0, 1]
                signs.append(np.sign(slope))
                roll_rows.append(dict(target=tgt, candidate=f, alignment=a, window_end=str(idx[j]),
                                      n_window=int(m.sum()), slope=slope, corr=corr))
            signs = np.array(signs)
            out['roll_share_same_sign'] = np.mean(signs == np.sign(b0)) if len(signs) else np.nan
            out['roll_n_windows'] = len(signs)
            # Granger
            out['granger_p_x_to_y'], out['granger_p_y_to_x'], out['granger_sum_xlags_sd'] = granger[f]
            out['ar1_feature'] = np.corrcoef(F[f].dropna().values[1:], F[f].dropna().values[:-1])[0, 1]
            rows.append(out)
    print(tgt, 'done', len(rows), 'rows', round(time.time() - t0), 's', flush=True)

B = pd.DataFrame(rows)
B.to_csv(f'{R.OUT}/battery_raw.csv', index=False)
pd.DataFrame(roll_rows).to_csv(f'{R.OUT}/rolling_32q.csv', index=False)
pd.DataFrame(loyo_rows).to_csv(f'{R.OUT}/loyo_detail.csv', index=False)
print('rows', len(B))
