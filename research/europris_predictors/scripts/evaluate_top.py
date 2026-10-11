"""Final evidence cards, holdout tests and figures for the selected predictors (v3).

Macro / company picks: statistics from results/evidence_all.csv (calibrated
bootstrap p-values, both COVID specs, no-2016 check, 25-year proxy) plus
pseudo real-time holdout forecasts (2024Q3-2026Q2, never used for selection).
Calendar picks (part of the benchmark because they are known in advance):
statistics from results/benchmark_components.csv, i.e. the benchmark with vs
without the calendar term.
Outputs: results/top5_evidence_cards.csv, results/top5_holdout.csv,
results/figures/*.png.
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
import screen_predictors as sp  # noqa: E402
from top5 import PICKS, RUNNERS_UP  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)

INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e4e3dd", "#fcfcfb"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
TNAME = {"rev_yoy": "Norway sales growth y/y (%)", "lfl": "Like-for-like growth (%)",
         "gm_d4": "Gross margin y/y change (pp)", "ebitm_d4": "EBIT margin y/y change (pp)"}


def style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def forecasts(frames, X, p, y, h):
    out = {}
    for mode in ("exclude", "control"):
        f, cols = frames[(y, h)][mode]
        if p["kind"] == "calendar":
            comp = p["component"]
            base = [c for c in cols if c != comp]
            out[mode] = sp.run_rt(f.drop(columns=[comp]), base, f[comp].reindex(X.index), h, "q")
        else:
            out[mode] = sp.run_rt(f, cols, X[p["feature"]], h, "q")
    return out


def main():
    panel, pxp, X = sp.prepare()
    sp._init(X.index)
    frames, _ = sp.build_frames(panel, pxp)
    ev = pd.read_csv(RES / "evidence_all.csv")
    bc = pd.read_csv(RES / "benchmark_components.csv")
    cards, hold, preds = [], [], {}
    for p in PICKS + RUNNERS_UP:
        for y in p["targets"]:
            for h in sp.HORIZONS:
                if p["kind"] == "calendar":
                    r = bc[(bc.component == p["component"]) & (bc.target == y) & (bc.h == h)]
                    if r.empty:
                        continue
                    e, c = r[r.spec == "exclude"], r[r.spec == "control"]

                    def g(d, k):
                        return d[k].iloc[0] if len(d) else np.nan
                    cards.append({"rank": p["rank"], "key": p["key"], "target": y, "h": h, "selected_h": h in p["hs"],
                                  "t_is": g(e, "t"), "p_is": g(e, "p_boot"), "t_isc": g(c, "t"), "p_isc": g(c, "p_boot"),
                                  "beta_std": g(c, "beta_std"), "cv_r2": g(e, "cv_r2"), "cvc_r2": g(c, "cv_r2"),
                                  "hold_r2": g(e, "hold_r2"), "holdc_r2": g(c, "hold_r2")})
                else:
                    r = ev[(ev.feature == p["feature"]) & (ev.target == y) & (ev.h == h)]
                    if r.empty:
                        continue
                    r = r.iloc[0]
                    cards.append({"rank": p["rank"], "key": p["key"], "target": y, "h": h, "selected_h": h in p["hs"],
                                  "t_is": r.t_is, "p_is": r.p_is, "t_isc": r.t_isc, "p_isc": r.p_isc, "q_eu": r.q_eu,
                                  "beta_std": r.beta_std_c, "t_no16": r.t_no16, "tc_no16": r.tc_no16,
                                  "t_px": r.get("t_px"), "p_px": r.get("p_px"), "t_pxl": r.get("t_pxl"), "p_pxl": r.get("p_pxl"),
                                  "cv_r2": r.get("cv_r2"), "cvc_r2": r.get("cvc_r2"),
                                  "hold_r2": r.get("hold_r2"), "holdc_r2": r.get("holdc_r2")})
            for h in p["hs"]:
                for mode, (o, res) in forecasts(frames, X, p, y, h).items():
                    if o is None:
                        continue
                    hres = res[(res.tdate > sp.SEL_END) & (res.tdate <= sp.HOLD_END)]
                    hold.append({"rank": p["rank"], "key": p["key"], "target": y, "h": h, "spec": mode,
                                 "hold_n": o["hold_n_oos"], "hold_r2": o["hold_oos_r2"],
                                 "rmse_bench": o["hold_rmse_bench"], "rmse_model": o["hold_rmse_model"],
                                 "dir_hit": float(np.mean(np.sign(hres.f_model - hres.f_bench) == np.sign(hres.y - hres.f_bench)))
                                 if len(hres) else np.nan})
                    preds[(p["key"], y, h, mode)] = res
    cards = pd.DataFrame(cards)
    cards.to_csv(RES / "top5_evidence_cards.csv", index=False)
    hold = pd.DataFrame(hold)
    hold.to_csv(RES / "top5_holdout.csv", index=False)
    pd.set_option("display.width", 230)
    print(cards[cards.selected_h].round(3).to_string(index=False))
    print()
    print(hold.round(3).to_string(index=False))
    figures(cards, preds, panel, pxp, X)


def figures(cards, preds, panel, pxp, X):
    picks = PICKS
    # 1. holdout forecasts (primary horizon, COVID-excluded spec)
    shown = picks + RUNNERS_UP[:1]
    fig, axes = plt.subplots(2, 3, figsize=(11.5, 5.8), facecolor=SURF)
    for ax, p in zip(axes.ravel(), shown):
        y, h = p["targets"][0], p["hs"][0]
        r = preds.get((p["key"], y, h, "exclude"))
        style(ax)
        if r is None:
            ax.set_visible(False)
            continue
        r = r[(r.tdate > sp.SEL_END) & (r.tdate <= sp.HOLD_END)]
        xs = np.arange(len(r))
        ax.plot(xs, r.y, color=INK, lw=2, marker="o", ms=4, label="actual")
        ax.plot(xs, r.f_bench, color=MUTED, lw=1.5, ls="--", marker="o", ms=3,
                label="benchmark without it" if p["kind"] == "calendar" else "benchmark")
        ax.plot(xs, r.f_model, color=S1, lw=2, marker="o", ms=4, label=f"+ {p['short']}")
        ax.set_xticks(xs, [f"{q.year % 100}Q{q.quarter}" for q in r.tdate])
        ax.set_title(f"#{p['rank']} {p['short']} → {TNAME[y]}, {h}q ahead", fontsize=8.3, color=INK)
        ax.legend(fontsize=6.5, frameon=False, loc="best")
    for ax in axes.ravel()[len(shown):]:
        ax.set_visible(False)
    fig.suptitle("Holdout 2024Q3-2026Q2 (never used for selection): pseudo real-time forecasts vs actual",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(FIG / "holdout_forecasts.png", dpi=150, facecolor=SURF)
    plt.close(fig)

    # 2. evidence by horizon: -log10 bootstrap p (COVID-control spec)
    fig, axes = plt.subplots(1, len(picks), figsize=(2.5 * len(picks), 2.9), sharey=True, facecolor=SURF)
    for ax, p in zip(np.atleast_1d(axes), picks):
        c = cards[(cards.key == p["key"]) & (cards.target == p["targets"][0])].sort_values("h")
        val = -np.log10(c.p_isc.clip(lower=1e-4))
        cols = [S1 if s else "#b7d3f6" for s in c.selected_h]
        ax.bar(c.h, val, color=cols, width=0.7)
        ax.axhline(-np.log10(0.05), color=S2, lw=1, ls="--")
        style(ax)
        ax.set_xticks(sp.HORIZONS)
        ax.set_title(f"#{p['rank']} {p['short']}\n→ {p['targets'][0]}", fontsize=8.3, color=INK)
        ax.set_xlabel("quarters ahead", fontsize=8, color=INK2)
    np.atleast_1d(axes)[0].set_ylabel("-log10 bootstrap p (higher = stronger)", fontsize=8, color=INK2)
    fig.suptitle("Calibrated evidence by horizon (dark = selected horizons; dashed line = p 0.05)",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(FIG / "evidence_by_horizon.png", dpi=150, facecolor=SURF)
    plt.close(fig)

    # 3. FX vs gross margin: two stacked panels (no dual axis)
    idx = pd.period_range("2014Q1", "2026Q2", freq="Q")
    fx_shift = X["cnynok__g4"].reindex(idx).shift(4)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 4.6), sharex=True, facecolor=SURF)
    t = [q.to_timestamp(how="end") for q in idx]
    a1.bar(t, fx_shift.values, width=60, color=S2)
    a1.set_ylabel("CNY/NOK y/y %\n(4 quarters earlier)", fontsize=8, color=INK2)
    a2.bar(t, panel["gm_d4"].reindex(idx).values, width=60, color=S1)
    a2.set_ylabel("gross margin\ny/y change, pp", fontsize=8, color=INK2)
    cov = panel["covid_win_q"].reindex(idx).fillna(False).astype(bool)
    for a in (a1, a2):
        style(a)
        a.axhline(0, color=INK2, lw=0.8)
        for q, c in zip(idx, cov):
            if c:
                a.axvspan(q.to_timestamp(how="start"), q.to_timestamp(how="end"), color="#f1f0ec", zorder=0)
    a1.set_title("A weaker krone (top) and gross margin 4 quarters later (bottom); shaded = COVID-distorted",
                 fontsize=8.5, color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "fx_vs_gross_margin.png", dpi=150, facecolor=SURF)
    plt.close(fig)

    # 4. house prices vs next-quarter sales: 25-year category proxy and Europris
    hp = X["house_prices__g4"]
    q = pd.period_range("2001Q1", "2024Q2", freq="Q")
    d = pd.DataFrame({"x": hp.reindex(q), "y": pxp["px_yoy"].shift(-1).reindex(q),
                      "cov": pxp["covid_win_q"].shift(-1).reindex(q).fillna(False).astype(bool)}).dropna()
    d = d[~d["cov"]]
    qe = pd.period_range("2014Q1", "2024Q2", freq="Q")
    eu = pd.DataFrame({"x": hp.reindex(qe), "y": panel["lfl"].shift(-1).reindex(qe),
                       "cov": panel["covid_win_q"].shift(-1).reindex(qe).fillna(False).astype(bool)}).dropna()
    eu = eu[~eu["cov"]]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.6), facecolor=SURF)
    for a, dd, col, ttl in ((a1, d, S1, "Category sales (NACE 47.19), 2001-2024"),
                            (a2, eu, S2, "Europris like-for-like, 2014-2024")):
        style(a)
        a.scatter(dd.x, dd.y, s=16, color=col, alpha=0.85, edgecolor=SURF, lw=0.5)
        b = np.polyfit(dd.x.astype(float), dd.y.astype(float), 1)
        xx = np.linspace(dd.x.min(), dd.x.max(), 20)
        a.plot(xx, np.polyval(b, xx), color=INK, lw=1.5)
        a.set_xlabel("house prices y/y % (quarter t)", fontsize=8, color=INK2)
        a.set_ylabel("sales growth y/y % (quarter t+1)", fontsize=8, color=INK2)
        a.set_title(ttl, fontsize=8.5, color=INK, loc="left")
    fig.suptitle("House-price growth and next-quarter sales (COVID-distorted quarters removed; raw, before controls)",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(FIG / "house_prices_next_quarter.png", dpi=150, facecolor=SURF)
    plt.close(fig)


if __name__ == "__main__":
    main()
