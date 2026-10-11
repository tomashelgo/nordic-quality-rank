"""Final tests for the selected top-5 predictors.

* Horizon profile: selection-window and holdout OOS R^2 for h = 1..8 on every
  target in the predictor's family.
* Holdout (2024Q3-2026Q2, never used for selection): each predictor's own
  target/horizons.
* Forecast combination: equal-weight average of the single-predictor models
  (Stock & Watson style) vs the AR benchmark, per target and horizon.
* Charts in ../results/figures.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcast  # noqa: E402
from screen_predictors import (HOLD_END, SEL_END, TARGETS, add_event_controls, frame,  # noqa: E402
                               horizons, load, run_one)

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def main():
    tg, X, px = load()
    panel = add_event_controls(tg)
    X = X.join(panel[["store_growth"]].rename(columns={"store_growth": "eu_store_growth__g4"}), how="left")
    top = pd.read_csv(RES / "top5.csv")
    feats = top["feature"].tolist()

    prof_rows, comb_rows = [], []
    for y, (fam, kind, controls) in TARGETS.items():
        if y not in panel:
            continue
        for h in horizons(kind):
            f, cols = frame(panel, y, h, controls, kind, "control")
            preds = {}
            for feat in feats:
                out, res = run_one(f, cols, X[feat], h, kind)
                if out is None:
                    continue
                prof_rows.append({"feature": feat, "target": y, "family": fam, "kind": kind, "h": h,
                                  "sel_oos_r2": out["sel_oos_r2"], "sel_cw_p": out["sel_cw_p"],
                                  "hold_oos_r2": out["hold_oos_r2"], "hold_cw_p": out["hold_cw_p"],
                                  "hold_n": out["hold_n_oos"], "is_beta_std": out.get("is_beta_std"),
                                  "is_t_hac": out.get("is_t_hac")})
                preds[feat] = res
            if not preds:
                continue
            # combination on the common evaluation rows
            idx = sorted(set.intersection(*[set(r.index) for r in preds.values()]))
            if len(idx) < 6:
                continue
            base = next(iter(preds.values())).loc[idx]
            comb = pd.DataFrame({"y": base["y"], "f_bench": base["f_bench"],
                                 "f_model": np.mean([r.loc[idx, "f_model"] for r in preds.values()], axis=0),
                                 "tdate": base["tdate"]})
            lag = h + (3 if kind == "ltm" else 0)
            sel = fcast.evaluate(comb[comb["tdate"] <= SEL_END], lag)
            hold = fcast.evaluate(comb[(comb["tdate"] > SEL_END) & (comb["tdate"] <= HOLD_END)], lag)
            comb_rows.append({"target": y, "h": h, "sel_oos_r2": sel["oos_r2"], "sel_cw_p": sel["cw_p"],
                              "sel_n": sel["n_oos"], "hold_oos_r2": hold["oos_r2"], "hold_cw_p": hold["cw_p"],
                              "hold_n": hold["n_oos"], "rmse_bench_all": np.sqrt(((comb.y - comb.f_bench) ** 2).mean()),
                              "rmse_comb_all": np.sqrt(((comb.y - comb.f_model) ** 2).mean())})
            comb.to_csv(RES / f"combination_{y}_h{h}.csv")
    prof = pd.DataFrame(prof_rows)
    prof.to_csv(RES / "top5_horizon_profile.csv", index=False)
    combdf = pd.DataFrame(comb_rows)
    combdf.to_csv(RES / "top5_combination.csv", index=False)
    pd.set_option("display.width", 220)
    print(combdf.round(3).to_string())

    # figure: OOS R^2 by horizon for each pick on its own target
    fig, axes = plt.subplots(1, len(top), figsize=(4 * len(top), 3.4), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, (_, r) in zip(axes, top.iterrows()):
        p = prof[(prof.feature == r.feature) & (prof.target == r.target)].sort_values("h")
        ax.bar(p.h - 0.2, 100 * p.sel_oos_r2, width=0.4, label="selection (to 2024Q2)", color="#2a78d6")
        ax.bar(p.h + 0.2, 100 * p.hold_oos_r2.clip(-100, None), width=0.4, label="holdout (2024Q3-26Q2)", color="#e08a2c")
        ax.axhline(0, color="#888", lw=0.8)
        ax.set_title(f"{r.concept}\n→ {r.target}", fontsize=9)
        ax.set_xlabel("horizon (quarters)")
    axes[0].set_ylabel("OOS R² vs AR benchmark (%)")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "top5_oos_r2_by_horizon.png", dpi=130)


if __name__ == "__main__":
    main()
