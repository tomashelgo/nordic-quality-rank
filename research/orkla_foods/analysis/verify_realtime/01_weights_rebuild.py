"""(c) Geographic weights from annual reports published after the year: rebuild the Orkla-weighted
composites with (i) original weights (validation), (ii) prior-year weights (lag4 = what was published
before the quarter), (iii) fixed 2001-25 mean weights; plus real-time expanding z-scores for confidence."""
import numpy as np, pandas as pd
import vr_lib as V

T, F, D = V.load()
g = V.load_weights()
WV = V.weight_variants(g)
comps = {}
for k, W in WV.items():
    a = V.build_composites(F, W)
    b = V.build_composites(F, W, nordic=True)
    comps[k] = pd.concat([a, b], axis=1)

# validation vs panel
chk = []
for c in comps['orig'].columns:
    if c in F.columns:
        d = (comps['orig'][c] - F[c]).abs()
        both = comps['orig'][c].notna() & F[c].notna()
        chk.append(dict(feature=c, max_abs_diff=d.max(), n_both=int(both.sum()),
                        n_orig=int(F[c].notna().sum()), n_rebuilt=int(comps['orig'][c].notna().sum())))
chk = pd.DataFrame(chk)
print(chk.to_string())

# how much do the variants differ from the published composite?
rows = []
for c in comps['orig'].columns:
    for k in ('lag4', 'fixed'):
        a, b = comps['orig'][c], comps[k][c]
        ok = a.notna() & b.notna() & (a.index >= pd.Period('2001Q1'))
        if ok.sum() < 20: continue
        rows.append(dict(feature=c, variant=k, corr=np.corrcoef(a[ok], b[ok])[0, 1],
                         rmse_diff=np.sqrt(((a[ok] - b[ok]) ** 2).mean()), sd_orig=a[ok].std(),
                         max_abs_diff=(a[ok] - b[ok]).abs().max(),
                         when_max=str((a[ok] - b[ok]).abs().idxmax())))
dv = pd.DataFrame(rows)
print(dv.to_string(float_format=lambda v: f'{v:.3f}'))
dv.to_csv(f'{V.OUT}/weights_variant_diff.csv', index=False, float_format='%.4g')
chk.to_csv(f'{V.OUT}/weights_rebuild_validation.csv', index=False, float_format='%.4g')
allc = pd.concat({k: v for k, v in comps.items()}, axis=1)
allc.columns = [f'{a}|{b}' for a, b in allc.columns]
allc.index = allc.index.astype(str)
allc.to_csv(f'{V.OUT}/composites_weight_variants.csv', float_format='%.6g')
