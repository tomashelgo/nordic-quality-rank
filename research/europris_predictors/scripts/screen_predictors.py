"""Screen candidate predictors of Europris Norway financials.

For every candidate feature x, target y and horizon h we compare two direct
forecasting models:

  benchmark: y_{t+h} = a + b*y_t + controls
  candidate: y_{t+h} = a + b*y_t + controls + g*x_t

Controls: Easter-timing shift at t+h (quarterly targets; the calendar is known in
advance), annual-stocktaking timing (quarterly gross margin), IFRS 16 break
(EBIT), and COVID border-restriction changes at t+h and t. Controls are identical
in both models, so only x's incremental content is measured.

COVID: 2020-22 swings (border closure) are an order of magnitude larger than
normal quarters and would dominate any squared-error metric. Target quarters
whose y/y (or LTM) comparison touches a COVID quarter are excluded from SCORING
everywhere. Two estimation specs are run:
  primary ("exclude"): rows whose target or origin y/y window touches COVID are
            also dropped from estimation;
  "control" (columns cvc_*, rtc_*, isc_*): COVID-era rows kept in training with
            COVID-intensity controls.

Evidence per (x, y, h):
  cv_*      hv-block cross-validation (blocks = calendar years of target date;
            training rows must lie > 4 quarters before / > h+4 after the block,
            7 / h+7 for annual windows), targets <= 2024Q2.
  sel_*     pseudo real-time expanding-window OOS, targets <= 2024Q2.
  hold_*    pseudo real-time OOS on the HOLDOUT 2024Q3-2026Q2 (never used for
            selection; reported by evaluate_top.py).
  cvc_/rtc_/isc_  the same CV / real-time / in-sample statistics in the "control" spec.
  proxy_*   real-time OOS on a 25-year proxy target (SSB retail sales in
            Europris's category, NACE 47.19), targets <= 2024Q2.
  placebo_p / placebo_c_p (control spec): share of 49 time-shifted placebo versions x_{t-k} (k = 12..60) whose
            CV R^2 >= the actual one; familywise_placebo.csv does the same for
            the maximum over all candidates.
  is_*      OLS on non-COVID targets <= 2024Q2 with Newey-West HAC t-stat.
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
MIN_TRAIN_CV = 12
PLACEBO_SHIFTS = list(range(12, 61))

# target -> (family, kind, controls)
# Annual-window (LTM) Europris targets are not screened: once LTM comparisons
# touching 2020-22 are excluded only ~20 usable quarters remain. Long horizons
# use the quarterly targets at h = 4, 6, 8 plus the 25-year proxy (incl. LTM).
TARGETS = {
    "rev_yoy":      ("revenue", "q",   ["easter_share_d4", "covid_d4"]),
    "lfl":          ("revenue", "q",   ["easter_share_d4", "covid_d4"]),
    "gm_d4":        ("margin",  "q",   ["easter_share_d4", "covid_d4", "stocktaking_d4"]),
    "ebitm_d4":     ("profit",  "q",   ["easter_share_d4", "covid_d4", "ifrs16_d4"]),
}
H_SHORT = [1, 2, 3, 4]
H_LONG = [4, 6, 8]
PROXY = {"rev_yoy": "px_yoy", "lfl": "px_yoy"}
PROXY_LTM = "px_ltm_yoy"  # annual-window proxy, used for revenue targets at h >= 4


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
    cov = df.get("ev_covid_border_restrictions", pd.Series(0.0, index=df.index)).fillna(0)
    df["covid"] = cov
    df["covid_d4"] = cov - cov.shift(4)
    ltm = cov.rolling(4, min_periods=1).mean()
    df["covid_ltm_d4"] = ltm - ltm.shift(4)
    # quarters whose y/y (5-quarter) or LTM y/y (8-quarter) window touches COVID
    df["covid_win_q"] = cov.rolling(5, min_periods=1).max() > 0
    df["covid_win_ltm"] = cov.rolling(8, min_periods=1).max() > 0
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
    """Rows = origin t. Columns: target y_{t+h}, ar = y_t, controls at t+h (and COVID at t)."""
    full = pd.period_range(panel.index.min(), HOLD_END, freq="Q")
    p = panel.reindex(full)
    f = pd.DataFrame(index=full)
    f["target"] = p[y].shift(-h)
    f["ar"] = p[y]
    f["tdate"] = [q + h for q in full]
    f["pos"] = np.arange(len(full))
    win = p["covid_win_q" if kind == "q" else "covid_win_ltm"].astype(float).fillna(0) > 0
    f["covid_target"] = win.shift(-h).fillna(False).astype(bool)
    cols = []
    for c in controls:
        if c not in p or (covid_mode == "exclude" and c.startswith("covid")):
            continue
        f["c_" + c] = p[c].shift(-h)
        cols.append("c_" + c)
    if covid_mode == "control":
        cov_now = "covid_d4" if kind == "q" else "covid_ltm_d4"
        f["c0_covid"] = p[cov_now]
        cols.append("c0_covid")
    else:
        f = f[~(f["covid_target"] | win)]
    return f, cols


def _scores(res: pd.DataFrame, lag: int, prefix: str, drop_covid: bool = True) -> dict:
    ok = res[~res["covid_target"].astype(bool)] if drop_covid else res
    return {f"{prefix}_{k}": v for k, v in fcast.evaluate(ok, lag).items()}


def _with_x(f, cols, x, sel_only):
    d = f[f["tdate"] <= SEL_END].copy() if sel_only else f.copy()
    extra = []
    if x is not None:
        d["x"] = x.reindex(d.index)
        extra = ["x"]
    return d.dropna(subset=["ar"] + cols + extra + ["target"]), extra


def run_rt(f, cols, x, h, kind):
    """Pseudo real-time expanding window -> selection and holdout scores."""
    d, extra = _with_x(f, cols, x, sel_only=False)
    if len(d) < MIN_TRAIN + 4:
        return None, None
    res = fcast.oos_forecasts(d, "target", ["ar"] + cols, extra, h, MIN_TRAIN, d["pos"].to_numpy())
    res["tdate"] = d.loc[res.index, "tdate"]
    res["covid_target"] = d.loc[res.index, "covid_target"]
    lag = h + (3 if kind == "ltm" else 0)
    sel = res[res["tdate"] <= SEL_END]
    hold = res[(res["tdate"] > SEL_END) & (res["tdate"] <= HOLD_END)]
    out = _scores(sel, lag, "sel") | _scores(hold, lag, "hold") | _scores(sel, lag, "sel_inclcovid", drop_covid=False)
    return out, res


def run_cv(f, cols, x, h, kind):
    """hv-block CV on targets <= SEL_END; scores exclude COVID-distorted targets."""
    d, extra = _with_x(f, cols, x, sel_only=True)
    if len(d) < MIN_TRAIN_CV + 2:
        return None, None
    w = 7 if kind == "ltm" else 4  # y/y window overlap (8-quarter for LTM)
    block = np.array([q.year for q in d["tdate"]])
    res = fcast.cv_forecasts(d, "target", ["ar"] + cols, extra, w, block, d["pos"].to_numpy(),
                             min_train=MIN_TRAIN_CV, gap_future=h + w)
    res["covid_target"] = d.loc[res.index, "covid_target"]
    lag = h + (3 if kind == "ltm" else 0)
    return _scores(res, lag, "cv"), res


def insample(f, cols, x, h, kind):
    d, _ = _with_x(f, cols, x, sel_only=True)
    d = d[~d["covid_target"]]
    lag = h + (3 if kind == "ltm" else 0)
    return {f"is_{k}": v for k, v in fcast.insample(d, "target", ["ar"] + cols, "x", lag).items()}


def task(args):
    """Evaluate one (target, h) for all candidates (+ placebo and robustness)."""
    y, h, panel, X, px = args
    fam, kind, controls = TARGETS[y]
    rows = []
    # primary: COVID-distorted rows dropped from estimation and scoring;
    # robustness ("cvc_"): COVID-era rows kept in training with COVID controls
    f, cols = frame(panel, y, h, controls, kind, "exclude")
    fc, colsc = frame(panel, y, h, controls, kind, "control")
    pyn = PROXY.get(y)
    if pyn:
        fp, colsp = frame(px, pyn, h, controls, kind, "exclude")
        if h >= 4:
            fpl, colspl = frame(px, PROXY_LTM, h, [], "ltm", "exclude")
    placebo_r2 = {k: {} for k in PLACEBO_SHIFTS}
    for feat in X.columns:
        x = X[feat]
        cv, _ = run_cv(f, cols, x, h, kind)
        rt, _ = run_rt(f, cols, x, h, kind)
        if cv is None or rt is None:
            continue
        row = {"target": y, "family": fam, "kind": kind, "h": h, "feature": feat} | cv | rt
        row |= insample(f, cols, x, h, kind)
        nx, _ = run_cv(fc, colsc, x, h, kind)
        if nx:
            row |= {"cvc_r2": nx["cv_oos_r2"], "cvc_cw_p": nx["cv_cw_p"], "cvc_n": nx["cv_n_oos"]}
        rc, _ = run_rt(fc, colsc, x, h, kind)
        if rc:
            row |= {"rtc_sel_r2": rc["sel_oos_r2"], "rtc_hold_r2": rc["hold_oos_r2"]}
        ic = insample(fc, colsc, x, h, kind)
        row |= {"isc_beta_std": ic.get("is_beta_std"), "isc_t_hac": ic.get("is_t_hac"), "isc_n": ic.get("is_n_is")}
        if pyn:
            op, _ = run_rt(fp, colsp, x, h, kind)
            if op:
                row |= {"proxy_r2": op["sel_oos_r2"], "proxy_cw_p": op["sel_cw_p"], "proxy_n": op["sel_n_oos"]}
                pis = insample(fp, colsp, x, h, kind)
                row |= {"proxy_t_hac": pis.get("is_t_hac"), "proxy_beta_std": pis.get("is_beta_std")}
            if h >= 4:
                ol, _ = run_rt(fpl, colspl, x, h, "ltm")
                if ol:
                    row |= {"proxyltm_r2": ol["sel_oos_r2"], "proxyltm_cw_p": ol["sel_cw_p"], "proxyltm_n": ol["sel_n_oos"]}
                    pil = insample(fpl, colspl, x, h, "ltm")
                    row |= {"proxyltm_t_hac": pil.get("is_t_hac"), "proxyltm_beta_std": pil.get("is_beta_std")}
        # placebo: misaligned history of the same series, scored on CV R^2
        pl = []
        base_n = x.reindex(f.index).notna().sum()
        for k in PLACEBO_SHIFTS:
            xs = x.shift(k)
            if xs.reindex(f.index).notna().sum() < base_n - 2:
                continue
            op, _ = run_cv(f, cols, xs, h, kind)
            if op is None or not np.isfinite(op["cv_oos_r2"]):
                continue
            pl.append(op["cv_oos_r2"])
            placebo_r2[k][feat] = op["cv_oos_r2"]
        if len(pl) >= 10 and np.isfinite(row.get("cv_oos_r2", np.nan)):
            pl = np.array(pl)
            row["placebo_n"] = len(pl)
            row["placebo_p"] = (1 + (pl >= row["cv_oos_r2"]).sum()) / (1 + len(pl))
            row["placebo_q90"] = float(np.quantile(pl, 0.9))
        # same placebo on the COVID-control spec (available at all horizons)
        plc = []
        for k in PLACEBO_SHIFTS:
            xs = x.shift(k)
            if xs.reindex(fc.index).notna().sum() < x.reindex(fc.index).notna().sum() - 2:
                continue
            op, _ = run_cv(fc, colsc, xs, h, kind)
            if op is not None and np.isfinite(op["cv_oos_r2"]):
                plc.append(op["cv_oos_r2"])
        if len(plc) >= 10 and np.isfinite(row.get("cvc_r2", np.nan)):
            plc = np.array(plc)
            row["placebo_c_n"] = len(plc)
            row["placebo_c_p"] = (1 + (plc >= row["cvc_r2"]).sum()) / (1 + len(plc))
        rows.append(row)
    bench_cv, _ = run_cv(f, cols, None, h, kind)
    bench_rt, _ = run_rt(f, cols, None, h, kind)
    return rows, placebo_r2, {"target": y, "h": h, "bench_cv": bench_cv, "bench_rt": bench_rt}


def main():
    tg, X, px = load()
    panel = add_event_controls(tg)
    pxp = add_event_controls(px)
    cover = X.reindex(panel.index).notna().mean()
    X = X.loc[:, cover >= 0.8]
    store = panel[["store_growth"]].rename(columns={"store_growth": "eu_store_growth__g4"})
    X = X.join(store, how="left")
    jobs = []
    for y, (fam, kind, _) in TARGETS.items():
        if y not in panel:
            continue
        for h in horizons(kind):
            jobs.append((y, h, panel, X, pxp))
    all_rows, fw, benches = [], [], []
    with ProcessPoolExecutor(max_workers=4) as ex:
        for rows, placebo, bench in ex.map(task, jobs):
            all_rows.extend(rows)
            benches.append(bench)
            finite = [r["cv_oos_r2"] for r in rows if np.isfinite(r.get("cv_oos_r2", np.nan))]
            if finite:
                actual_max = max(finite)
                maxes = [max(v.values()) for v in placebo.values() if len(v) >= 0.8 * len(rows)]
                fw.append({"target": bench["target"], "h": bench["h"], "actual_max_cv_r2": actual_max,
                           "best_feature": max((r for r in rows if np.isfinite(r.get("cv_oos_r2", np.nan))),
                                               key=lambda r: r["cv_oos_r2"])["feature"],
                           "placebo_max_median": float(np.median(maxes)) if maxes else np.nan,
                           "familywise_p": (1 + sum(m >= actual_max for m in maxes)) / (1 + len(maxes)) if maxes else np.nan,
                           "n_shifts": len(maxes)})
            print(f"done {bench['target']} h={bench['h']}: {len(rows)} candidates", flush=True)
    df = pd.DataFrame(all_rows)
    for (y, h), g in df.groupby(["target", "h"]):
        df.loc[g.index, "cv_q_bh"] = fcast.bh_fdr(g["cv_cw_p"])
    df.to_csv(RES / "screen_all.csv", index=False)
    pd.DataFrame(fw).to_csv(RES / "familywise_placebo.csv", index=False)
    with open(RES / "benchmarks.json", "w") as fh:
        json.dump(benches, fh, indent=1, default=float)
    print(df.shape)


if __name__ == "__main__":
    main()
