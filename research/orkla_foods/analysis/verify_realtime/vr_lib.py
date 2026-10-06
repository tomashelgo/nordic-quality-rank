"""Helpers for the sceptic-realtime verification lens (look-ahead, timing, data artefacts).

Independent re-implementation: only common.py (targets/features/align) is reused.
"""
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, '/home/user/nordic-quality-rank/research/orkla_foods/analysis')
import common as C  # noqa: E402

OUT = '/home/user/nordic-quality-rank/research/orkla_foods/analysis/verify_realtime'
DATA = C.DATA
EPI = (pd.Period('2021Q3', 'Q'), pd.Period('2023Q4', 'Q'))
COVID = (pd.Period('2020Q1', 'Q'), pd.Period('2021Q4', 'Q'))

DATA_COUNTRIES = ["NO", "SE", "DK", "FI", "EE", "LV", "LT", "CZ", "SK", "AT", "HU", "RO", "PL", "DE", "IN"]
EU_CC = ["dk", "fi", "ee", "lv", "lt", "cz", "sk", "at", "hu", "ro", "pl", "de"]


def load():
    T = C.load_targets()
    F, D = C.load_features(core_only=False)
    return T, F, D


def win(idx, a, b):
    return pd.Series(((idx >= pd.Period(a, 'Q')) & (idx <= pd.Period(b, 'Q'))).astype(float), index=idx)


def ex_mask(idx, which):
    m = pd.Series(True, index=idx)
    if 'infl' in which:
        m &= ~((idx >= EPI[0]) & (idx <= EPI[1]))
    if 'covid' in which:
        m &= ~((idx >= COVID[0]) & (idx <= COVID[1]))
    return m


def ols(y, X, w=None, hac=4, sample=None):
    """HAC OLS/WLS; drops NaN rows and regressors constant in the estimation sample.
    Returns statsmodels results (or None)."""
    if isinstance(X, pd.Series):
        X = X.to_frame()
    df = pd.concat([y.rename('_y'), X], axis=1)
    if sample is not None:
        df = df[sample.reindex(df.index).fillna(False).astype(bool)]
    if w is not None:
        df['_w'] = w.reindex(df.index)
    df = df.dropna()
    if w is not None:
        df = df[df['_w'] > 0]
        ww = df.pop('_w')
    keep = [c for c in df.columns if c != '_y' and df[c].std() > 1e-12]
    if len(df) < 15:
        return None
    Xc = sm.add_constant(df[keep], has_constant='add')
    m = sm.WLS(df['_y'], Xc, weights=ww) if w is not None else sm.OLS(df['_y'], Xc)
    return m.fit(cov_type='HAC', cov_kwds={'maxlags': hac})


def coef(res, name):
    if res is None or name not in res.params.index:
        return dict(b=np.nan, t=np.nan, p=np.nan, n=np.nan)
    return dict(b=res.params[name], t=res.tvalues[name], p=res.pvalues[name], n=int(res.nobs))


# ----------------------------------------------------------------------------------- weights
def load_weights():
    g = pd.read_csv(f'{DATA}/macro_panel_geo_weights_quarterly.csv')
    g.index = pd.PeriodIndex(g['period'], freq='Q')
    return g


def wavg(comp, W, min_cov=0.40, rel_cov=0.80):
    """Re-implementation of the panel's renormalised weighted average with coverage floor."""
    idx = W.index
    df = pd.DataFrame({c: s.reindex(idx) for c, s in comp.items()})
    w = W.reindex(columns=df.columns).fillna(0.0)
    avail = df.notna() & (w > 0)
    wa = w.where(avail, 0.0)
    cov = wa.sum(axis=1)
    wn = wa.div(cov.replace(0, np.nan), axis=0)
    val = (df.fillna(0.0) * wn).sum(axis=1)
    ref = cov[(cov.index >= pd.Period('2005Q1')) & (cov.index <= pd.Period('2025Q4')) & (cov > 0)]
    thr = max(min_cov, rel_cov * float(ref.median())) if len(ref) else min_cov
    return val.where(cov >= thr - 1e-12)


def weight_variants(g):
    """Return dict name -> W (country columns) for: orig, lag4 (prior-year annual-report shares,
    i.e. what was published before the quarter), fixed (constant 2001-2025 mean)."""
    cols = [c for c in DATA_COUNTRIES + ['RU', 'UK', 'DROP'] if c in g.columns]
    W = g[cols].astype(float)
    Wl = W.shift(4)
    Wl.iloc[:4] = W.iloc[:4].values
    fixed = W.loc[(W.index >= pd.Period('2001Q1')) & (W.index <= pd.Period('2025Q4'))].mean()
    Wf = pd.DataFrame([fixed.values] * len(W), index=W.index, columns=cols)
    return {'orig': W, 'lag4': Wl, 'fixed': Wf}


def country_maps(F):
    """Country-level component series (yoy / lvl / d4) from the full panel, mirroring macro_panel_build."""
    def y(s):
        return F.get(f'{s}__yoy')

    def dy(s):
        return F.get(f'{s}__dyoy')

    def lv(s):
        return F.get(f'{s}__lvl')

    m = {}
    food = {"NO": "no_cpi_food_idx", "SE": "se_cpi_food_idx"}
    food.update({c.upper(): f"{c}_hicp_food_idx" for c in EU_CC})
    cpi = {"NO": "no_cpi_total_idx", "SE": "se_cpi_idx"}
    cpi.update({c.upper(): f"{c}_hicp_all_idx" for c in EU_CC})
    cpi["IN"] = "in_cpi_all_idx"
    vat = {"NO": "no_vat_food_rate", "SE": "se_food_vat_rate"}
    xvat = {}
    for k, s in food.items():
        if k in vat:
            r = lv(vat[k])
            vadj = 100.0 * np.log((1 + r / 100.0) / (1 + r.shift(4) / 100.0))
            xvat[k] = y(s) - vadj
        else:
            xvat[k] = y(s)
    m['food_cpi_xvat_yoy'] = xvat
    m['food_cpi_xvat_dyoy'] = {k: v - v.shift(4) for k, v in xvat.items()}
    m['food_cpi_yoy'] = {k: y(s) for k, s in food.items()}
    m['cpi_yoy'] = {k: y(s) for k, s in cpi.items()}
    m['cpi_exIN_yoy'] = {k: y(s) for k, s in cpi.items() if k != 'IN'}
    m['food_cpi_rel_yoy'] = {k: y(food[k]) - y(cpi[k]) for k in food}
    m['food_rel_xvat_cc_yoy'] = {k: xvat[k] - y(cpi[k]) for k in food}   # country-consistent ex-VAT relative
    wage = {"NO": "no_lci_wages_idx", "SE": "se_wage_idx_m", "DK": "dk_wage_idx_private_q", "FI": "fi_wage_idx_q"}
    wage.update({c.upper(): f"{c}_lci_wages_idx" for c in ["ee", "lv", "lt", "cz", "sk", "hu", "ro", "pl", "at", "de"]})
    m['real_wage_yoy'] = {k: y(wage[k]) - y(cpi[k]) for k in wage}
    m['wage_yoy'] = {k: y(s) for k, s in wage.items()}
    un = {"NO": "no_unemp_rate_sa", "SE": "se_unemp_rate_sa"}
    un.update({c.upper(): f"{c}_unemp_rate_sa" for c in EU_CC})
    m['unemp_lvl'] = {k: lv(s) for k, s in un.items()}
    m['unemp_d4'] = {k: lv(s) - lv(s).shift(4) for k, s in un.items()}
    gb = {"NO": "no_govbond_10y", "SE": "se_gov_bond_10y"}
    gb.update({c.upper(): f"{c}_gov_bond_10y" for c in ["dk", "fi", "cz", "at", "de", "hu", "pl", "ro", "sk", "lv"]})
    m['gov10y_d4'] = {k: lv(s) - lv(s).shift(4) for k, s in gb.items()}
    pol = {"NO": "no_policy_rate", "SE": "se_policy_rate", "DK": "dk_policy_rate", "CZ": "cz_policy_rate",
           "HU": "hu_policy_rate", "PL": "pl_policy_rate", "RO": "ro_policy_rate", "IN": "in_policy_rate"}
    plv = {k: lv(s) for k, s in pol.items()}
    mro, dfr = lv('ea_ecb_mro'), lv('ea_ecb_dfr')
    eff = mro.where(mro.index <= pd.Period('2008Q3'), dfr)
    for k, p0 in {"FI": "1999Q1", "AT": "1999Q1", "DE": "1999Q1", "EE": "1999Q1", "LV": "1999Q1",
                  "LT": "1999Q1", "SK": "2009Q1"}.items():
        plv[k] = eff.where(eff.index >= pd.Period(p0))
    m['policy_rate_d4'] = {k: s - s.shift(4) for k, s in plv.items()}
    fsp = {"NO": "no_ssb_bts_consgoods_home_price_exp", "SE": "se_ec_food_ind_sell_price_exp"}
    fsp.update({c.upper(): f"{c}_ec_food_ind_sell_price_exp" for c in EU_CC})
    m['ec_food_ind_sell_price_exp_lvl'] = {k: lv(s) for k, s in fsp.items()}
    m['ec_food_ind_sell_price_exp_d4'] = {k: lv(s) - lv(s).shift(4) for k, s in fsp.items()}
    conf = {"NO": "no_fn_cci_sa", "SE": "se_ec_cons_conf"}
    conf.update({c.upper(): f"{c}_ec_cons_conf" for c in EU_CC})
    zfull, zrt = {}, {}
    for k, s in conf.items():
        s = lv(s)
        win_ = s[(s.index >= pd.Period('2000Q1')) & (s.index <= pd.Period('2025Q4'))]
        zfull[k] = (s - win_.mean()) / win_.std(ddof=1)
        # real-time z: expanding mean/sd up to t (min 16 quarters)
        mu = s.expanding(16).mean()
        sd = s.expanding(16).std()
        zrt[k] = (s - mu) / sd
    m['cons_conf_z'] = zfull
    m['cons_conf_zrt'] = zrt
    fx = {"NO": y('no_fx_eurnok'), "SE": y('se_eursek'), "DK": y('ea_fx_dkk_per_eur'), "CZ": y('ea_fx_czk_per_eur'),
          "HU": y('ea_fx_huf_per_eur'), "PL": y('ea_fx_pln_per_eur'), "RO": y('ea_fx_ron_per_eur'),
          "IN": y('ea_fx_inr_per_eur')}
    idx = F.index
    for k, p0 in {"FI": "1999Q1", "AT": "1999Q1", "DE": "1999Q1", "EE": "1995Q1", "LT": "2003Q1",
                  "LV": "2006Q1", "SK": "2010Q1"}.items():
        s = pd.Series(0.0, index=idx)
        fx[k] = s.where(s.index >= pd.Period(p0))
    m['fx_vs_eur_yoy'] = fx
    usd = y('ea_fx_usd_per_eur')
    fxu = {k: s - usd for k, s in fx.items()}
    fxu['NO'] = y('no_fx_usdnok')
    fxu['SE'] = y('se_usdsek')
    m['fx_vs_usd_yoy'] = fxu
    fppi = {"NO": "no_ppi_food_dom_idx", "SE": "se_ppi_food_hmpi_idx"}
    fppi.update({c.upper(): f"{c}_ppi_dom_food_mfg_idx" for c in ["dk", "fi", "lt", "cz", "at", "hu", "ro", "pl", "de"]})
    m['food_ppi_yoy'] = {k: y(s) for k, s in fppi.items()}
    m['food_ppi_dyoy'] = {k: dy(s) for k, s in fppi.items()}
    return m


def build_composites(F, W, nordic=False):
    m = country_maps(F)
    out = {}
    for name, comp in m.items():
        if nordic:
            comp = {k: v for k, v in comp.items() if k in ('NO', 'SE')}
            if len(comp) < 2:
                continue
            Wn = W[['NO', 'SE']].div(W[['NO', 'SE']].sum(axis=1), axis=0)
            out['nw_' + name] = wavg(comp, Wn, 0.99, 0.0)
        else:
            out['w_' + name] = wavg(comp, W)
    out = pd.DataFrame(out).reindex(F.index)
    # derived local-currency raw materials (as in the mechanism lens)
    if not nordic:
        basket = F['eu_agri_basket_yoy']
        fao = F['glob_fao_ffpi__yoy']
        out['eu_agri_basket_wloc_yoy'] = basket + out['w_fx_vs_eur_yoy']
        out['fao_ffpi_wloc_yoy'] = fao + out['w_fx_vs_usd_yoy']
        out['raw_mat_wloc_yoy'] = 0.5 * out['eu_agri_basket_wloc_yoy'] + 0.5 * out['fao_ffpi_wloc_yoy']
        out['w_food_rel_xvat_yoy'] = out['w_food_cpi_xvat_yoy'] - out['w_cpi_yoy']   # mechanism-lens definition
        out['w_food_rel_xvat_exIN_yoy'] = out['w_food_cpi_xvat_yoy'] - out['w_cpi_exIN_yoy']
    return out


def realtime(x, lag, h):
    return x.shift(h + lag)
