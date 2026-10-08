"""Builds report/chart_data.json (embedded in the report page) from the verified datasets."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, '/home/user/nordic-quality-rank/research/orkla_foods/analysis')
import common as C

q = C.load_orkla()
F, D = C.load_features(core_only=False)
F = F.reindex(q.index)

def ser(s, nd=2):
    return [None if (v is None or (isinstance(v, float) and np.isnan(v))) else round(float(v), nd) for v in s]

out = {
    'period': [str(p) for p in q.index],
    'def_id': q['def_id'].tolist(),
    'revenue': ser(q['revenue_nokm'], 0),
    'ebit': ser(q['ebit_nokm'], 0),
    'margin': ser(q['ebit_margin_pct']),
    'd_margin': ser(q['d_margin_yoy_pp']),
    'og': ser(q['og_est'], 1),
    'og_quality': q['og_quality'].fillna('').tolist(),
    'd_og': ser(q['d_og_yoy_pp'], 1),
    'price': ser(q['price_pct'], 1),
    'volume_mix': ser(q['volume_mix_pct'], 1),
    'rev_chain_idx': ser(q['rev_chain_idx'], 1),
    'ebit_chain_idx': ser(q['ebit_chain_idx'], 1),
}
macro = {
    'food_cpi_xvat': 'w_food_cpi_xvat_yoy',
    'packaging': 'packaging_eu_yoy',
    'agri_local': 'eu_agri_basket_wloc_yoy',
    'fao_local': 'fao_ffpi_wloc_yoy',
    'real_wage': 'w_real_wage_yoy',
    'cons_conf': 'nw_cons_conf_z',
    'gov10y_d4': 'w_gov10y_d4',
    'policy_d4': 'w_policy_rate_d4',
    'unemp_d4': 'w_unemp_d4',
    'food_sell_exp': 'w_ec_food_ind_sell_price_exp_lvl',
    'eursek': 'se_eursek__yoy',
}
for k, c in macro.items():
    out[k] = ser(F[c])
# Annual series.
a = pd.read_csv('data/orkla_foods_annual.csv')
out['annual'] = json.loads(a.to_json(orient='records'))
json.dump(out, open('report/chart_data.json', 'w'), separators=(',', ':'), allow_nan=False, default=str)
print('ok', len(out['period']), {k: sum(v is not None for v in out[k]) for k in macro})
