"""Final tests for the selected top-5 predictors (+ runner-up).

1. Evidence card per pick: in-sample HAC t (both COVID specs), CV R^2, placebo
   p, 25-year proxy, incremental-value test — all pre-holdout.
2. HOLDOUT (2024Q3-2026Q2, 8 quarters, never used for selection): pseudo
   real-time forecasts from the expanding-window model vs the AR+controls
   benchmark, both COVID specs.
3. Forecast combination per target: equal-weight average of the picks' single-
   predictor forecasts vs the benchmark, selection window and holdout.
4. Figures in ../results/figures.
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
from screen_predictors import HOLD_END, SEL_END, TARGETS, add_event_controls, frame, load, run_rt  # noqa: E402
from top5 import PICKS, RUNNER_UP  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)

INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e4e3dd", "#fcfcfb"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
TNAME = {"rev_yoy": "Norway sales growth y/y", "lfl": "Like-for-like growth", "gm_d4": "Gross margin, y/y change (pp)",
         "ebitm_d4": "EBIT margin, y/y change (pp)"}


def style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def main():
    tg, X, _ = load()
    panel = add_event_controls(tg)
    X = X.join(panel[["store_growth"]].rename(columns={"store_growth": "eu_store_growth__g4"}), how="left")
    scr = pd.read_csv(RES / "screen_all.csv")
    inc = pd.read_csv(RES / "incremental_tests.csv")
    picks = PICKS + RUNNER_UP

    cards, hold_rows, preds = [], [], {}
    for p in picks:
        for y in p["targets"]:
            fam, kind, controls = TARGETS[y]
            for h in range(1, 9):
                s = scr[(scr.feature == p["feature"]) & (scr.target == y) & (scr.h == h)]
                if s.empty:
                    continue
                s = s.iloc[0]
                cards.append({"rank": p["rank"], "key": p["key"], "feature": p["feature"], "target": y, "h": h,
                              "selected_h": h in p["hs"], "is_t": s.is_t_hac, "isc_t": s.isc_t_hac,
                              "beta_std": s.is_beta_std, "cv_r2": s.cv_oos_r2, "cvc_r2": s.cvc_r2,
                              "placebo_p": s.placebo_p, "placebo_c_p": s.get("placebo_c_p"),
                              "proxy_r2": s.get("proxy_r2"), "proxy_p": s.get("proxy_cw_p"), "proxy_t": s.get("proxy_t_hac"),
                              "proxyltm_r2": s.get("proxyltm_r2"), "proxyltm_p": s.get("proxyltm_cw_p"),
                              "proxyltm_t": s.get("proxyltm_t_hac")})
            for h in p["hs"]:
                for mode in ("exclude", "control"):
                    f, cols = frame(panel, y, h, controls, kind, mode)
                    out, res = run_rt(f, cols, X[p["feature"]], h, kind)
                    if out is None:
                        continue
                    hold = res[(res.tdate > SEL_END) & (res.tdate <= HOLD_END)]
                    hold_rows.append({"rank": p["rank"], "key": p["key"], "target": y, "h": h, "spec": mode,
                                      "hold_n": out["hold_n_oos"], "hold_r2": out["hold_oos_r2"], "hold_cw_p": out["hold_cw_p"],
                                      "hold_rmse_bench": out["hold_rmse_bench"], "hold_rmse_model": out["hold_rmse_model"],
                                      "hold_dir_hit": float(np.mean(np.sign(hold.f_model - hold.f_bench) == np.sign(hold.y - hold.f_bench)))
                                      if len(hold) else np.nan})
                    preds[(p["key"], y, h, mode)] = res
    cards = pd.DataFrame(cards)
    cards.to_csv(RES / "top5_evidence_cards.csv", index=False)
    hold = pd.DataFrame(hold_rows)
    hold.to_csv(RES / "top5_holdout.csv", index=False)

    # forecast combination per target/horizon over the top-5 picks that target it
    comb_rows = []
    for y in TARGETS:
        for h in range(1, 9):
            for mode in ("exclude", "control"):
                rs = [preds[k] for k in preds if k[1] == y and k[2] == h and k[3] == mode and
                      any(p["key"] == k[0] for p in PICKS)]
                if not rs:
                    continue
                idx = sorted(set.intersection(*[set(r.index) for r in rs]))
                base = rs[0].loc[idx]
                comb = pd.DataFrame({"y": base.y, "f_bench": base.f_bench, "tdate": base.tdate,
                                     "covid_target": base.covid_target,
                                     "f_model": np.mean([r.loc[idx, "f_model"] for r in rs], axis=0)})
                comb = comb[~comb.covid_target.astype(bool)]
                lag = h
                sel = fcast.evaluate(comb[comb.tdate <= SEL_END], lag)
                ho = fcast.evaluate(comb[(comb.tdate > SEL_END) & (comb.tdate <= HOLD_END)], lag)
                comb_rows.append({"target": y, "h": h, "spec": mode, "n_models": len(rs),
                                  "sel_n": sel["n_oos"], "sel_r2": sel["oos_r2"], "hold_n": ho["n_oos"],
                                  "hold_r2": ho["oos_r2"], "hold_cw_p": ho["cw_p"],
                                  "hold_rmse_bench": ho["rmse_bench"], "hold_rmse_comb": ho["rmse_model"]})
    comb = pd.DataFrame(comb_rows)
    comb.to_csv(RES / "top5_combination.csv", index=False)

    pd.set_option("display.width", 230)
    print(hold.round(3).to_string(index=False))
    print()
    print(comb.round(3).to_string(index=False))

    figures(cards, preds, panel, X)


def figures(cards, preds, panel, X):
    picks = PICKS + RUNNER_UP
    # 1. horizon profile: CV R^2 (COVID-control spec, all horizons) per pick on its first target
    fig, axes = plt.subplots(1, len(picks), figsize=(2.6 * len(picks), 2.8), sharey=True, facecolor=SURF)
    for ax, p in zip(axes, picks):
        c = cards[(cards.key == p["key"]) & (cards.target == p["targets"][0])].sort_values("h")
        cols = [S1 if s else "#b7d3f6" for s in c.selected_h]
        ax.bar(c.h, (100 * c.cvc_r2).clip(-60, None), color=cols, width=0.7)
        ax.axhline(0, color=INK2, lw=0.8)
        style(ax)
        ax.set_title(f"#{p['rank']} {p['key']}\n→ {p['targets'][0]}", fontsize=8.5, color=INK)
        ax.set_xticks(range(1, 9))
        ax.set_xlabel("quarters ahead", fontsize=8, color=INK2)
    axes[0].set_ylabel("cross-validated R² vs benchmark (%)", fontsize=8, color=INK2)
    fig.suptitle("Out-of-sample gain by forecast horizon (dark = selected horizons; floored at -60%)",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(FIG / "horizon_profiles.png", dpi=150, facecolor=SURF)
    plt.close(fig)

    # 2. holdout only (8 quarters): actual vs benchmark vs model, COVID-excluded spec
    sel = [(p, p["targets"][0], p["hs"][-1] if p["key"] in ("cnynok",) else p["hs"][0]) for p in picks]
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.4), facecolor=SURF)
    for ax, (p, y, h) in zip(axes.ravel(), sel):
        r = preds.get((p["key"], y, h, "exclude"))
        style(ax)
        if r is None:
            ax.set_visible(False)
            continue
        r = r[(r.tdate > SEL_END) & (r.tdate <= HOLD_END)]
        xs = np.arange(len(r))
        labels = [f"{q.year % 100}Q{q.quarter}" for q in r.tdate]
        ax.plot(xs, r.y, color=INK, lw=2, marker="o", ms=4, label="actual")
        ax.plot(xs, r.f_bench, color=MUTED, lw=1.5, ls="--", marker="o", ms=3, label="benchmark (AR + calendar)")
        ax.plot(xs, r.f_model, color=S1, lw=2, marker="o", ms=4, label=f"+ {p['key']}")
        ax.set_xticks(xs, labels)
        ax.set_title(f"#{p['rank']} {p['key']} → {TNAME[y]}, {h}q ahead", fontsize=8.5, color=INK)
        ax.legend(fontsize=6.5, frameon=False, loc="best")
    fig.suptitle("Holdout 2024Q3-2026Q2 (never used for selection): pseudo real-time forecasts vs actual",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(FIG / "holdout_forecasts.png", dpi=150, facecolor=SURF)
    plt.close(fig)

    # 3. FX vs gross margin: two stacked panels, shared time axis (no dual axis)
    gm = panel["gm_d4"]
    fx = X["cnynok__g4"].reindex(pd.period_range("2014Q1", "2026Q2", freq="Q"))
    fx_shift = fx.shift(4)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 4.6), sharex=True, facecolor=SURF)
    t = [q.to_timestamp(how="end") for q in fx_shift.index]
    a1.bar(t, fx_shift.values, width=60, color=S2)
    a1.set_ylabel("CNY/NOK y/y %\n(4 quarters earlier)", fontsize=8, color=INK2)
    g = gm.reindex(fx_shift.index)
    a2.bar(t, g.values, width=60, color=S1)
    a2.set_ylabel("gross margin\ny/y change, pp", fontsize=8, color=INK2)
    cov = panel["covid_win_q"].reindex(fx_shift.index).fillna(False).astype(bool)
    for a in (a1, a2):
        style(a)
        a.axhline(0, color=INK2, lw=0.8)
        for q, c in zip(fx_shift.index, cov):
            if c:
                a.axvspan(q.to_timestamp(how="start"), q.to_timestamp(how="end"), color="#f1f0ec", zorder=0)
    a1.set_title("A weaker krone (top) is followed by a lower gross margin 4 quarters later (bottom); shaded = COVID-distorted",
                 fontsize=9, color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "fx_vs_gross_margin.png", dpi=150, facecolor=SURF)
    plt.close(fig)


if __name__ == "__main__":
    main()
