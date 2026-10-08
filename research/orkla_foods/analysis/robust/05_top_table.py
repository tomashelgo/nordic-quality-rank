"""Step 5: compact table of the ROBUST relationships (one row per target x candidate), preferring the
row that is usable in real time (realtime alignment, or coincident for a lag-0 feature), then the
smallest calibrated p-value. Output: top_predictors.csv
"""
import pandas as pd
import robust_lib as R

B = pd.read_csv(f'{R.OUT}/robust_summary.csv', keep_default_na=False, na_values=[''])
r = B[B.classification == 'ROBUST'].copy()
r['rt'] = r['realtime_usable'].astype(str).str.lower().eq('true')
rows = []
for (tgt, f), g in r.groupby(['target', 'candidate']):
    g = g.sort_values(['rt', 'p_cal'], ascending=[False, True])
    best = g.iloc[0]
    rows.append(dict(
        target=tgt, candidate=f, source=best['source'], best_alignment=best['alignment'],
        realtime_usable=bool(best['rt']), robust_alignments=','.join(g['alignment']), sign=best['sign'],
        beta_sd=round(best['beta_sd'], 3), beta_per_unit=round(best['beta_per_unit'], 4), t=round(best['t'], 2),
        p_cal=best['p_cal'], q_by_target_family=round(best['q_by_target_family'], 3),
        era_signs=best['era_signs'], t_ex_infl=round(best['t_ex_infl'], 2),
        t_ex_covid_infl=round(best['t_ex_covid_infl'], 2), t_annual=round(best['t_ann'], 2),
        t_own_history=round(best['t_own'], 2) if pd.notna(best['t_own']) else None,
        t_channel=round(best['t_chan'], 2) if pd.notna(best['t_chan']) else None,
        channel_note=best['channel_note'], granger_p_x_to_y=round(best['granger_p_x_to_y'], 3),
        granger_p_y_to_x=round(best['granger_p_y_to_x'], 3), soft_fail=best['soft_fail']))
TP = pd.DataFrame(rows).sort_values(['target', 'realtime_usable', 'p_cal'], ascending=[True, False, True])
TP.to_csv(f'{R.OUT}/top_predictors.csv', index=False)
pd.set_option('display.width', 250)
print(TP[['target', 'candidate', 'best_alignment', 'robust_alignments', 'sign', 'beta_per_unit', 't',
          't_ex_infl', 't_ex_covid_infl', 't_channel']].to_string(index=False))
