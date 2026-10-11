"""Incremental-value tests: does a candidate add information beyond another
predictor already in the benchmark?

benchmark: y_{t+h} = a + b*y_t + controls + c*z_t
candidate: y_{t+h} = a + b*y_t + controls + c*z_t + g*x_t

Same estimation specs as the screen (primary COVID-excluded and COVID-control),
reporting in-sample HAC t of g and the CV R^2 / Clark-West p of the nested
comparison (control spec, where enough rows exist).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from screen_predictors import TARGETS, add_event_controls, frame, insample, load, run_cv  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"

TESTS = [
    # (target, h list, base feature z, candidate x)
    ("gm_d4", [3, 4, 6], "usdnok__g4", "unemployment__d4"),
    ("gm_d4", [3, 4, 6], "usdnok__g4", "fci__lvl"),
    ("gm_d4", [3, 4], "usdnok__g4", "population__g4"),
    ("gm_d4", [3, 4], "usdnok__g4", "cnynok__g4"),
    ("gm_d4", [3, 4], "cnynok__g4", "usdnok__g4"),
    ("gm_d4", [1, 2, 3], "fci__lvl", "rti_retail_exfuel_volume__g4"),
    ("gm_d4", [1, 2], "usdnok__g4", "fci__lvl"),
    ("gm_d4", [4, 6], "unemployment__d4", "usdnok__g4"),
    ("ebitm_d4", [3, 4], "usdnok__g4", "business_conf__lvl"),
    ("ebitm_d4", [3, 4], "unemployment__d4", "business_conf__lvl"),
    ("ebitm_d4", [1, 2], "usdnok__g4", "real_disp_income__g4"),
    ("ebitm_d4", [3, 4, 6], "business_conf__lvl", "usdnok__g4"),
    ("rev_yoy", [1, 2], "regnet_retail_next__lvl", "house_prices__g4"),
    ("lfl", [1, 2], "regnet_retail_next__lvl", "house_prices__g4"),
    ("lfl", [4, 6], "house_prices__g4", "saving_ratio__d4"),
    ("rev_yoy", [4, 6], "house_prices__g4", "saving_ratio__d4"),
    ("lfl", [6], "real_disp_income__g4", "saving_ratio__d4"),
]


def main():
    tg, X, _ = load()
    panel = add_event_controls(tg)
    rows = []
    for y, hs, z, xname in TESTS:
        fam, kind, controls = TARGETS[y]
        for h in hs:
            rec = {"target": y, "h": h, "base": z, "candidate": xname}
            for mode, tag in (("exclude", ""), ("control", "c")):
                f, cols = frame(panel, y, h, controls, kind, mode)
                f = f.copy()
                f["z"] = X[z].reindex(f.index)
                cols2 = cols + ["z"]
                ins = insample(f, cols2, X[xname], h, kind)
                rec[f"is{tag}_t"] = ins.get("is_t_hac")
                rec[f"is{tag}_beta_std"] = ins.get("is_beta_std")
                cv, _ = run_cv(f, cols2, X[xname], h, kind)
                if cv:
                    rec[f"cv{tag}_r2"] = cv["cv_oos_r2"]
                    rec[f"cv{tag}_p"] = cv["cv_cw_p"]
                    rec[f"cv{tag}_n"] = cv["cv_n_oos"]
            rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "incremental_tests.csv", index=False)
    pd.set_option("display.width", 220)
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
