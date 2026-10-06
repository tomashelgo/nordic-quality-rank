"""OOS re-checks with real-time fixes: M4 yields, M5 EUR/SEK, O2 surveys, O3 Nordic nowcast, O4 unemployment."""
import numpy as np, pandas as pd
import vr_lib as V, oos_engine as E
pd.set_option('display.width', 250)
T, F, D = V.load(); idx = T.index
CV = pd.read_csv(f'{V.OUT}/composites_weight_variants.csv', index_col=0); CV.index = pd.PeriodIndex(CV.index, freq='Q')
MK = E.masks(idx)
rows = []

def ar(tgt, h, src=None):
    yy = T[src or tgt]
    lags = [h + 1] + ([4] if h + 1 < 4 else [])
    return pd.DataFrame({f'{src or tgt}_ar{l}': yy.shift(l) for l in lags}, index=idx)

def run(claim, label, tgt, h, feats, base, w=None, extra_ctrl=None, masks=('all', 'ex_infl', 'ex_infl_covid'), store=None):
    y = T[tgt]
    B = base.copy()
    if extra_ctrl is not None: B = pd.concat([B, extra_ctrl], axis=1)
    fb = E.expanding(y, B, h, w)
    fm = E.expanding(y, pd.concat([B, feats], axis=1), h, w)
    for mn in masks:
        r = E.evaluate(y, fb, fm, MK[mn])
        rows.append(dict(claim=claim, model=label, target=tgt, h=h, eval=mn, **r))
    if store is not None: store[label] = (fb, fm)
    return fb, fm

def al(x, lag, h):
    return x.reindex(idx).shift(h + lag)

# ---------------- M4: 10y yield changes (lag 0)
for h in (0, 1):
    for nm, x in [('no_govbond_10y__d4', F['no_govbond_10y__d4']), ('w_gov10y_d4 orig', CV['orig|w_gov10y_d4']),
                  ('w_gov10y_d4 lag4w', CV['lag4|w_gov10y_d4'])]:
        run('M4', nm, 'd_margin', h, al(x, 0, h).rename('x').to_frame(), ar('d_margin', h))

# ---------------- M5: EUR/SEK PDL L0-6 at h=0, mechanism-style base (AR t-1 + Easter window) and alternatives
eur = F['se_eursek__yoy']
store5 = {}
for h in (0, 1):
    Xp = E.pdl(al(eur, 0, h), 6, 2, 'sek')
    mech_base = pd.DataFrame({'ar': T['d_margin'].shift(h + 1), 'ew': T['d_easter_window_q1']})
    # mechanism lens: no training exclusion of covid quarters; replicate both
    for exc_lab, exc in [('train incl covid', pd.PeriodIndex([], freq='Q')), ('train excl 2020Q1-21Q2', E.TRAIN_EXCL)]:
        y = T['d_margin']
        fb = E.expanding(y, mech_base, h, excl=exc, min_train=28)
        fm = E.expanding(y, pd.concat([mech_base, Xp], axis=1), h, excl=exc, min_train=28)
        for mn in ('all', 'ex_infl', 'ex_infl_covid', '2015+'):
            rows.append(dict(claim='M5', model=f'EURSEK PDL0-6 | base AR1+Easter | {exc_lab}', target='d_margin', h=h, eval=mn,
                             **E.evaluate(y, fb, fm, MK[mn])))
    run('M5', 'EURSEK PDL0-6 | base AR(t-h-1,t-4)', 'd_margin', h, Xp, ar('d_margin', h), masks=('all', 'ex_infl', 'ex_infl_covid', '2015+'))
    run('M5', 'EURSEK L0 only | base AR(t-h-1,t-4)', 'd_margin', h, al(eur, 0, h).rename('x').to_frame(), ar('d_margin', h))
    run('M5', 'EURSEK avg L0-1 | base AR(t-h-1,t-4)', 'd_margin', h, al(eur, 0, h).rolling(2).mean().rename('x').to_frame(), ar('d_margin', h))

# ---------------- O3: Nordic og nowcast (food CPI ex VAT + real wage + confidence) at h=0
w_og = T['w_og'].fillna(0)
for h in (0, 1):
    base = ar('og', h)
    variants = {
        'panel (orig weights, full-sample z, lags 0/1/0)': [al(F['nw_food_cpi_xvat_yoy'], 0, h), al(F['nw_real_wage_yoy'], 1, h), al(F['nw_cons_conf_z'], 0, h)],
        'lag4 weights + real-time expanding z': [al(CV['lag4|nw_food_cpi_xvat_yoy'], 0, h), al(CV['lag4|nw_real_wage_yoy'], 1, h), al(CV['lag4|nw_cons_conf_zrt'], 0, h)],
        'strict timing: CPI & conf lag+1': [al(F['nw_food_cpi_xvat_yoy'], 1, h), al(F['nw_real_wage_yoy'], 1, h), al(F['nw_cons_conf_z'], 1, h)],
        'drop real wage (revision-prone SE MI wages)': [al(F['nw_food_cpi_xvat_yoy'], 0, h), al(F['nw_cons_conf_z'], 0, h)],
        'food CPI ex VAT only': [al(F['nw_food_cpi_xvat_yoy'], 0, h)],
        'real wage lagged 2 (SE prelim wages ~60d + revisions)': [al(F['nw_food_cpi_xvat_yoy'], 0, h), al(F['nw_real_wage_yoy'], 2, h), al(F['nw_cons_conf_z'], 0, h)],
    }
    for lab, cols in variants.items():
        run('O3', lab, 'og', h, pd.concat(cols, axis=1, keys=[f'f{i}' for i in range(len(cols))]), base, w=w_og,
            masks=('all', 'ex_infl', 'ex_infl_covid', '2015+'))

# ---------------- O4: w_unemp_d4 for og at h=2 (lag 1 -> x_{t-3})
store4 = {}
for h in (1, 2):
    for lab, x in [('w_unemp_d4 orig', F['w_unemp_d4']), ('w_unemp_d4 lag4 weights', CV['lag4|w_unemp_d4']),
                   ('w_unemp_d4 fixed weights', CV['fixed|w_unemp_d4']), ('nw_unemp_d4 (NO+SE)', CV['orig|nw_unemp_d4']),
                   ('w_unemp_d4 strict lag 2', F['w_unemp_d4'].shift(1))]:
        run('O4', lab, 'og', h, al(x, 1, h).rename('x').to_frame(), ar('og', h), w=w_og,
            masks=('all', 'ex_infl', 'ex_infl_covid', '2015+'), store=store4 if h == 2 else None)
# quarter-level contributions to the MSE gain for h=2 orig (ex_infl evaluation)
fb, fm = store4['w_unemp_d4 orig']
y = T['og']
dd = pd.concat([y.rename('y'), fb.rename('b'), fm.rename('m'), al(F['w_unemp_d4'], 1, 2).rename('x_t-3')], axis=1).dropna()
dd['gain'] = (dd.y - dd.b) ** 2 - (dd.y - dd.m) ** 2
dd = dd[~dd.index.isin(E.INFL)]
print('O4 top quarters by MSE gain (ex_infl eval):'); print(dd.sort_values('gain', ascending=False).head(10).round(2).to_string())
print('share of total gain from 2020Q1-2021Q4:', round(dd.loc[dd.index.isin(E.COVID), 'gain'].sum() / dd['gain'].sum(), 2),
      ' total gain', round(dd['gain'].sum(), 2))
dd.index = dd.index.astype(str); dd.to_csv(f'{V.OUT}/o4_unemp_h2_contrib.csv', float_format='%.4g')

# ---------------- O2: selling-price expectations for og (level) at h=0,1,2
for h in (0, 1, 2):
    for lab, x, lag in [('w_ec_food_ind_sell_price_exp_lvl orig', F['w_ec_food_ind_sell_price_exp_lvl'], 1),
                        ('w_ec_food_ind_sell_price_exp_lvl lag4w', CV['lag4|w_ec_food_ind_sell_price_exp_lvl'], 1),
                        ('ea_ec_food_ind_sell_price_exp__lvl', F['ea_ec_food_ind_sell_price_exp__lvl'], 0),
                        ('ea_ec_food_ind_sell_price_exp__d4', F['ea_ec_food_ind_sell_price_exp__d4'], 0),
                        ('se_nier_grocery_sell_price_exp__lvl', F['se_nier_grocery_sell_price_exp__lvl'], 0),
                        ('no_ssb_bts_consgoods_home_price_exp__lvl', F['no_ssb_bts_consgoods_home_price_exp__lvl'], 1)]:
        run('O2', lab, 'og', h, al(x, lag, h).rename('x').to_frame(), ar('og', h), w=w_og,
            masks=('all', 'ex_infl', 'ex_infl_covid'))

R = pd.DataFrame(rows)
print(R.to_string(float_format=lambda v: f'{v:.3f}'))
R.to_csv(f'{V.OUT}/oos_checks.csv', index=False, float_format='%.4g')
