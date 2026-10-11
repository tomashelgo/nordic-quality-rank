"""Screen candidate predictors of Europris Norway financials.

For every candidate feature x, target y and horizon h we compare two direct
forecasting models estimated on an expanding window:

  benchmark: y_{t+h} = a + b*y_t + controls
  candidate: y_{t+h} = a + b*y_t + controls + g*x_t

Controls: Easter-timing shift at t+h (quarterly targets; the calendar is known in
advance), COVID border-restriction change at t+h and t (applied identically to
both models), IFRS 16 break for EBIT targets.

Evidence recorded per (x, y, h):
  * OOS R^2 vs benchmark and Clark-West p-value in the SELECTION window
    (targets dated <= 2024Q2) and in the HOLDOUT window (2024Q3-2026Q2)
  * full-sample HAC t-stat, standardised beta
  * COVID-excluded OOS R^2 (rows touching COVID dropped, no COVID controls)
  * same test on a 25-year proxy target (SSB retail sales, NACE 47.19) for the
    revenue family
  * shifted-placebo p-value: share of placebo versions x_{t-k} (k = 12..44
    quarters) whose selection-window OOS R^2 >= the actual one, plus a
    family-wise "max over all candidates" version.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcast  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES = ROOT / "results"
RES.mkdir(exist_ok=True)

SEL_END = pd.Period("2024Q2", "Q")
HOLD_END = pd.Period("2026Q2", "Q")
MIN_TRAIN = 14
PLACEBO_SHIFTS = list(range(12, 45, 2))

# target -> (family, kind, controls)
TARGETS = {
    "rev_yoy":      ("revenue", "q",   ["easter_share_d4", "covid_d4"]),
    "lfl":          ("revenue", "q",   ["easter_share_d4", "covid_d4"]),
    "rev_ltm_yoy":  ("revenue", "ltm", ["covid_ltm_d4"]),
    "gm_d4":        ("margin",  "q",   ["easter_share_d4", "covid_d4", "stocktaking_d4"]),
    "gm_ltm_d4":    ("margin",  "ltm", ["covid_ltm_d4"]),
    "ebitm_d4":     ("profit",  "q",   ["easter_share_d4", "covid_d4", "ifrs16_d4"]),
    "ebitm_ltm_d4": ("profit",  "ltm", ["covid_ltm_d4", "ifrs16_ltm_d4"]),
}
H_SHORT = [1, 2, 3, 4]
H_LONG = [4, 6, 8]
PROXY = {"rev_yoy": "px_yoy", "lfl": "px_yoy", "rev_ltm_yoy": "px_ltm_yoy"}


def horizons(kind: str):
    return H_SHORT + [6, 8] if kind == "q" else H_LONG


def load():
    tg = pd.read_csv(DATA / "targets_quarterly.csv")
    tg.index = pd.PeriodIndex(tg.pop("quarter"), freq="Q")
    X = pd.read_csv(DATA / "predictors_quarterly.csv")
    X.index = pd.PeriodIndex(X.pop("quarter"), freq="Q")
    px = pd.read_csv(DATA / "proxy_quarterly.csv")
    px.index = pd.PeriodIndex(px.pop("quarter"), freq="Q")
    return tg, X, px


def add_event_controls(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cov = df.get("ev_covid_border_restrictions")
    if cov is not None:
        cov = cov.fillna(0)
        df["covid"] = cov
        df["covid_d4"] = cov - cov.shift(4)
        ltm = cov.rolling(4, min_periods=1).mean()
        df["covid_ltm_d4"] = ltm - ltm.shift(4)
    if "ev_stocktaking_d4" in df:
        df["stocktaking_d4"] = df["ev_stocktaking_d4"]
    if "ev_easter_share_d4" in df:
        df["easter_share_d4"] = df["ev_easter_share_d4"]
    ifrs = df.get("ev_ifrs16")
    if ifrs is not None:
        ifrs = ifrs.fillna(0)
        df["ifrs16_d4"] = ifrs - ifrs.shift(4)
        ltm = ifrs.rolling(4, min_periods=1).mean()
        df["ifrs16_ltm_d4"] = ltm - ltm.shift(4)
    return df


def frame(panel: pd.DataFrame, y: str, h: int, controls: list[str], kind: str, covid_mode: str):
    """Rows = origin t. Columns: target (y_{t+h}), ar (y_t), controls at t+h and covid at t."""
    full = pd.period_range(panel.index.min(), HOLD_END, freq="Q")
    p = panel.reindex(full)
    f = pd.DataFrame(index=full)
    f["target"] = p[y].shift(-h)
    f["ar"] = p[y]
    f["tdate"] = [q + h for q in full]
    cols = []
    if covid_mode == "control":
        for c in controls:
            if c in p:
                f["c_" + c] = p[c].shift(-h)
                cols.append("c_" + c)
        cov_now = "covid_d4" if kind == "q" else "covid_ltm_d4"
        if cov_now in p:
            f["c0_covid"] = p[cov_now]
            cols.append("c0_covid")
    else:  # exclude rows whose information set or target touches COVID
        for c in controls:
            if c in p and not c.startswith("covid"):
                f["c_" + c] = p[c].shift(-h)
                cols.append("c_" + c)
        cov = p.get("covid", pd.Series(0, index=full)).fillna(0)
        win = cov.rolling(8, min_periods=1).max()  # covid anywhere in the y/y or LTM window
        bad = (win.shift(-h).fillna(0) > 0) | (win.fillna(0) > 0)
        f = f[~bad]
    f["pos"] = np.arange(len(f)) if covid_mode == "control" else [full.get_loc(q) for q in f.index]
    return f, cols


def run_one(f: pd.DataFrame, cols: list[str], x: pd.Series | None, h: int, kind: str):
    d = f.copy()
    extra = []
    if x is not None:
        d["x"] = x.reindex(d.index)
        extra = ["x"]
    need = ["ar"] + cols + extra
    d = d.dropna(subset=need)
    d_fit = d.dropna(subset=["target"])
    if len(d_fit) < MIN_TRAIN + 4:
        return None, None
    res = fcast.oos_forecasts(d_fit, "target", ["ar"] + cols, extra, h, MIN_TRAIN, d_fit["pos"].to_numpy())
    res["tdate"] = d_fit.loc[res.index, "tdate"]
    lag = h + (3 if kind == "ltm" else 0)
    sel = fcast.evaluate(res[res["tdate"] <= SEL_END], lag)
    hold = fcast.evaluate(res[(res["tdate"] > SEL_END) & (res["tdate"] <= HOLD_END)], lag)
    full = fcast.evaluate(res, lag)
    out = {f"sel_{k}": v for k, v in sel.items()} | {f"hold_{k}": v for k, v in hold.items()} | {f"all_{k}": v for k, v in full.items()}
    if x is not None:
        d_is = d_fit[d_fit["tdate"] <= HOLD_END]
        out |= {f"is_{k}": v for k, v in fcast.insample(d_is, "target", ["ar"] + cols, "x", lag).items()}
    return out, res


def task(args):
    """Evaluate one (target, h) for all candidates (+ placebo and robustness)."""
    y, h, panel_json, X_json, px_json = args
    panel = pd.read_json(panel_json, orient="split")
    panel.index = pd.PeriodIndex(panel.index.astype(str), freq="Q")
    X = pd.read_json(X_json, orient="split")
    X.index = pd.PeriodIndex(X.index.astype(str), freq="Q")
    px = pd.read_json(px_json, orient="split")
    px.index = pd.PeriodIndex(px.index.astype(str), freq="Q")
    fam, kind, controls = TARGETS[y]
    rows = []
    f, cols = frame(panel, y, h, controls, kind, "control")
    fx, colsx = frame(panel, y, h, controls, kind, "exclude")
    pyn = PROXY.get(y)
    if pyn:
        fp, colsp = frame(px, pyn, h, controls, kind, "control")
    placebo_r2 = {k: {} for k in PLACEBO_SHIFTS}
    for feat in X.columns:
        x = X[feat]
        out, _ = run_one(f, cols, x, h, kind)
        if out is None:
            continue
        row = {"target": y, "family": fam, "kind": kind, "h": h, "feature": feat} | out
        ox, _ = run_one(fx, colsx, x, h, kind)
        if ox:
            row |= {"nocovid_oos_r2": ox["all_oos_r2"], "nocovid_cw_p": ox["all_cw_p"], "nocovid_n": ox["all_n_oos"]}
        if pyn:
            op, _ = run_one(fp, colsp, x, h, kind)
            if op:
                row |= {"proxy_oos_r2": op["all_oos_r2"], "proxy_cw_p": op["all_cw_p"], "proxy_n": op["all_n_oos"],
                        "proxy_sel_oos_r2": op["sel_oos_r2"], "proxy_t_hac": op.get("is_t_hac"), "proxy_beta_std": op.get("is_beta_std")}
        # placebo: misaligned history of the same series
        pl = []
        for k in PLACEBO_SHIFTS:
            xs = x.shift(k)
            if xs.reindex(f.index).notna().sum() < x.reindex(f.index).notna().sum() - 2:
                continue  # not enough history for this shift
            op, _ = run_one(f, cols, xs, h, kind)
            if op is None or not np.isfinite(op["sel_oos_r2"]):
                continue
            pl.append(op["sel_oos_r2"])
            placebo_r2[k][feat] = op["sel_oos_r2"]
        if pl and np.isfinite(row.get("sel_oos_r2", np.nan)):
            pl = np.array(pl)
            row["placebo_n"] = len(pl)
            row["placebo_p"] = (1 + (pl >= row["sel_oos_r2"]).sum()) / (1 + len(pl))
        rows.append(row)
    bench_out, bench_res = run_one(f, cols, None, h, kind)
    return rows, placebo_r2, {"target": y, "h": h, "bench": bench_out}


def main():
    tg, X, px = load()
    panel = add_event_controls(tg)
    pxp = add_event_controls(px)
    # only candidates with enough history over the Europris sample
    cover = X.reindex(panel.index).notna().mean()
    X = X.loc[:, cover >= 0.8]
    store = panel[["store_growth"]].rename(columns={"store_growth": "eu_store_growth__g4"})
    X = X.join(store, how="left")
    jobs = []
    for y, (fam, kind, _) in TARGETS.items():
        if y not in panel:
            continue
        for h in horizons(kind):
            jobs.append((y, h, panel.to_json(orient="split"), X.to_json(orient="split"), pxp.to_json(orient="split")))
    all_rows, fw, benches = [], [], []
    with ProcessPoolExecutor(max_workers=4) as ex:
        for rows, placebo, bench in ex.map(task, jobs):
            all_rows.extend(rows)
            benches.append(bench)
            if rows:
                actual_max = max(r.get("sel_oos_r2", -np.inf) for r in rows if np.isfinite(r.get("sel_oos_r2", np.nan)))
                maxes = [max(v.values()) for v in placebo.values() if v]
                fw.append({"target": rows[0]["target"], "h": rows[0]["h"], "actual_max_oos_r2": actual_max,
                           "placebo_max_mean": float(np.mean(maxes)) if maxes else np.nan,
                           "familywise_p": (1 + sum(m >= actual_max for m in maxes)) / (1 + len(maxes)) if maxes else np.nan,
                           "n_shifts": len(maxes)})
            print(f"done {bench['target']} h={bench['h']}: {len(rows)} candidates", flush=True)
    df = pd.DataFrame(all_rows)
    for (y, h), g in df.groupby(["target", "h"]):
        df.loc[g.index, "sel_cw_q_bh"] = fcast.bh_fdr(g["sel_cw_p"])
    df.to_csv(RES / "screen_all.csv", index=False)
    pd.DataFrame(fw).to_csv(RES / "familywise_placebo.csv", index=False)
    with open(RES / "benchmarks.json", "w") as fh:
        json.dump(benches, fh, indent=1, default=float)
    print(df.shape)


if __name__ == "__main__":
    main()
