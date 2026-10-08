"""Which M&A / event quarters drive the ex-episode margin results (M1 packaging, raw materials, M2 asymmetry, M3)?"""
import numpy as np, pandas as pd
import vr_lib as V
pd.set_option('display.width', 250)
T, F, D = V.load(); idx = T.index; y = T['d_margin']
CV = pd.read_csv(f'{V.OUT}/composites_weight_variants.csv', index_col=0); CV.index = pd.PeriodIndex(CV.index, freq='Q')
EX = V.ex_mask(idx, 'infl')
ev = pd.DataFrame({
    'ev_bakers': V.win(idx, '2012Q1', '2012Q4'), 'ev_rieber': V.win(idx, '2013Q2', '2014Q1'),
    'ev_hame': V.win(idx, '2016Q2', '2017Q1'), 'ev_eastern': V.win(idx, '2021Q2', '2022Q1'),
    'ev_2007': V.win(idx, '2007Q2', '2007Q4'), 'ev_ifrs16': T['ifrs16'], 'covid': T['covid'],
    'ev_sladco': V.win(idx, '2005Q1', '2005Q4'), 'ev_krup': V.win(idx, '2006Q3', '2007Q2')})
pk = F['packaging_eu_yoy'].reindex(idx).rename('x')
rm = CV['orig|raw_mat_wloc_yoy'].reindex(idx)
dairy6 = F['eu_ppi_dom_c105_idx__yoy'].reindex(idx).shift(6).rename('x')
sefood6 = F['se_ppi_food_hmpi_idx__yoy'].reindex(idx).shift(6).rename('x')

def asym(evs, sample):
    pos, neg = rm.clip(lower=0), rm.clip(upper=0)
    Z = pd.concat({**{f'P{k}': pos.shift(k) for k in range(7)}, **{f'N{k}': neg.shift(k) for k in range(7)}}, axis=1)
    if evs is not None and evs.shape[1]: Z = pd.concat([Z, evs], axis=1)
    r = V.ols(y, Z, sample=sample)
    return (np.cumsum([r.params[f'P{k}'] for k in range(7)]) * 10)[2], (np.cumsum([r.params[f'N{k}'] for k in range(7)]) * -10)[6]

rows = []
sets = {'none': []}
sets.update({f'only {c}': [c] for c in ev.columns})
sets.update({f'all but {c}': [d for d in ev.columns if d != c] for c in ev.columns})
sets['all'] = list(ev.columns)
sets['pure M&A (bakers,rieber,hame,eastern,sladco,krup)'] = ['ev_bakers', 'ev_rieber', 'ev_hame', 'ev_eastern', 'ev_sladco', 'ev_krup']
for lab, cols in sets.items():
    E = ev[cols] if cols else None
    r = {}
    for nm, x in [('pack', pk), ('rm_avg03', rm.rolling(4).mean().rename('x')), ('dairy_k6', dairy6), ('sefood_k6', sefood6)]:
        for s, m in [('full', None), ('ex', EX)]:
            Z = x if E is None else pd.concat([x, E], axis=1)
            c = V.coef(V.ols(y, Z, sample=m), 'x')
            r[f'{nm}_{s}_b'] = c['b']; r[f'{nm}_{s}_t'] = c['t']
    for s, m in [('full', None), ('ex', EX)]:
        p2, n6 = asym(E, m)
        r[f'asym_pos10_L2_{s}'] = p2; r[f'asym_neg10_L6_{s}'] = n6
    rows.append(dict(events=lab, **r))
R = pd.DataFrame(rows)
print(R.to_string(float_format=lambda v: f'{v:.2f}'))
R.to_csv(f'{V.OUT}/margin_event_decomposition.csv', index=False, float_format='%.4g')
# list the event quarters with key data
cols = ['d_margin', 'og']
X = pd.concat([T[cols], pk.rename('pack'), rm.rename('rawmat')], axis=1)
print(X.loc['2006Q1':'2008Q4'].round(2).to_string())
print(X.loc['2011Q1':'2014Q2'].round(2).to_string())
