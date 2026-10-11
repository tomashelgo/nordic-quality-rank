"""Test the predictors that are known in advance and therefore sit in the
benchmark (calendar, base effect, store pipeline, margin mean reversion) with
the same calibrated inference as the macro screen: drop the component from the
benchmark and test it as the candidate.

The calendar variables are deterministic, so the AR-sieve null (draws with the
series' own persistence) is a conservative way to ask whether their apparent
effect could arise by chance. Output: results/benchmark_components.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcast  # noqa: E402
import inference  # noqa: E402
import screen_predictors as sp  # noqa: E402

RES = Path(__file__).resolve().parents[1] / "results"

COMPONENTS = {
    "rev_yoy": ["c_tdays_d4", "c_easter_share_d4", "c_base", "o_store_growth"],
    "lfl": ["c_tdays_d4", "c_easter_share_d4", "c_base"],
    "gm_d4": ["c_easter_share_d4", "c_stocktaking_d4", "c_base", "o_gm_ltm"],
    "ebitm_d4": ["c_easter_share_d4", "c_ifrs16_d4", "c_base", "o_ebitm_ltm"],
}


def main():
    panel, pxp, X = sp.prepare()
    sp._init(X.index)
    frames, _ = sp.build_frames(panel, pxp)
    rows = []
    for (y, h), fr in frames.items():
        fam, kind = sp.TARGETS[y][0], sp.TARGETS[y][1]
        for comp in COMPONENTS[y]:
            for mode in ("exclude", "control"):
                f, cols = fr[mode]
                if comp not in cols:
                    continue
                base = [c for c in cols if c != comp]
                # the component, re-indexed on the X calendar so the null draws line up
                xc = f[comp].reindex(X.index)
                if xc.notna().sum() < 12:
                    continue
                sim = inference.simulate(xc, 5000, f"{comp}_{y}_{h}")
                t, p, n, bstd = sp.boot_stats(f.drop(columns=[comp]), base, xc, sim)
                cv, _ = sp.run_cv(f.drop(columns=[comp]), base, xc, h, kind)
                rt, _ = sp.run_rt(f.drop(columns=[comp]), base, xc, h, kind)
                rows.append({"target": y, "h": h, "component": comp, "spec": mode, "t": t, "p_boot": p, "n": n,
                             "beta_std": bstd, "cv_r2": cv["cv_oos_r2"] if cv else np.nan,
                             "sel_r2": rt["sel_oos_r2"] if rt else np.nan, "hold_r2": rt["hold_oos_r2"] if rt else np.nan})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "benchmark_components.csv", index=False)
    pd.set_option("display.width", 200)
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
