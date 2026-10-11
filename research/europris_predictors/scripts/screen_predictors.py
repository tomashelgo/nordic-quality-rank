"""Screen candidate predictors of Europris Norway financials (v3).

For every candidate feature x, target y and horizon h we compare two direct
forecasting models:

  benchmark: y_{t+h} = a + b*y_t + known controls
  candidate: benchmark + g*x_t

Known controls (all known at the forecast origin t):
  sales (rev_yoy, lfl): Easter-window shift and shop trading-day difference at
      t+h (calendar), base effect y_{t+h-4} for h < 4, and for rev_yoy the
      store-count growth at t (pre-approved store pipeline);
  gross margin (gm_d4): Easter shift and stocktaking timing at t+h, base effect,
      LTM margin level at t (mean reversion);
  EBIT margin (ebitm_d4): Easter shift and IFRS 16 break at t+h, base effect,
      LTM EBIT-margin level at t.

COVID: target quarters whose y/y window touches 2020Q1-2022Q1 (2020Q1-2023Q1)
are excluded from scoring everywhere. Two estimation specs:
  primary ("exclude"): COVID-distorted targets and origins also dropped from
      estimation;
  "control" (suffix c): COVID-era rows kept in estimation with COVID-intensity
      controls (in-sample statistics included).

Inference (the code audit showed Newey-West t-stats are 2-15x oversized here):
  p_is / p_isc   conditional-randomisation bootstrap p-value of the OLS t of x
                 (20,000 AR-sieve draws of x under H0, same y/controls/rows), on
                 targets <= 2024Q2 (selection window), primary / control spec;
  p_px / p_pxl   the same on the 25-year proxy target (SSB NACE 47.19 sales,
                 2001-2024; Europris is ~2/3 of this category, so this is
                 largely Europris's own pre-2014 history), quarterly / annual;
  t_no16 / tc_no16  OLS t without 2016 targets (single-episode check);
  cv_* / cvc_*   hv-block CV R^2 (descriptive);
  sel_* / hold_* pseudo real-time expanding-window OOS R^2 on targets <= 2024Q2
                 and on the HOLDOUT 2024Q3-2026Q2 (never used for selection).
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
import inference  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES = ROOT / "results"
RES.mkdir(exist_ok=True)

SEL_END = pd.Period("2024Q2", "Q")
HOLD_END = pd.Period("2026Q2", "Q")
MIN_TRAIN = 14
MIN_TRAIN_CV = 12
MIN_IS = 12
B_BOOT = 20000

# target -> (family, kind, controls at t+h, controls at t)
TARGETS = {
    "rev_yoy":  ("revenue", "q", ["easter_share_d4", "tdays_d4", "covid_d4"], ["store_growth"]),
    "lfl":      ("revenue", "q", ["easter_share_d4", "tdays_d4", "covid_d4"], []),
    "gm_d4":    ("margin",  "q", ["easter_share_d4", "stocktaking_d4", "covid_d4"], ["gm_ltm"]),
    "ebitm_d4": ("profit",  "q", ["easter_share_d4", "ifrs16_d4", "covid_d4"], ["ebitm_ltm"]),
}
HORIZONS = [1, 2, 3, 4, 6, 8]
PROXY = {"rev_yoy": "px_yoy", "lfl": "px_yoy"}
PROXY_LTM = "px_ltm_yoy"


def horizons(kind: str = "q"):
    return HORIZONS


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
    df["covid_d4"] = df["ev_covid_d4"] if "ev_covid_d4" in df else cov - cov.shift(4)
    ltm = cov.rolling(4, min_periods=1).mean()
    df["covid_ltm_d4"] = ltm - ltm.shift(4)
    df["covid_win_q"] = cov.rolling(5, min_periods=1).max() > 0
    df["covid_win_ltm"] = cov.rolling(8, min_periods=1).max() > 0
    for c in ("stocktaking_d4", "easter_share_d4", "tdays_d4", "ifrs16_d4"):
        if "ev_" + c in df:
            df[c] = df["ev_" + c]
    if "ifrs16_d4" not in df and "ev_ifrs16" in df:
        ifrs = df["ev_ifrs16"].fillna(0)
        df["ifrs16_d4"] = ifrs - ifrs.shift(4)
    return df


def frame(panel: pd.DataFrame, y: str, h: int, controls: list[str], kind: str, covid_mode: str,
          origin_controls: list[str] | None = None):
    """Rows = origin t: target y_{t+h}, ar = y_t, base = y_{t+h-4} (h<4), controls."""
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
    if kind == "q" and h < 4:
        f["c_base"] = p[y].shift(4 - h)
        cols.append("c_base")
    for c in controls:
        if c not in p or (covid_mode == "exclude" and c.startswith("covid")):
            continue
        f["c_" + c] = p[c].shift(-h)
        cols.append("c_" + c)
    for c in origin_controls or []:
        if c in p:
            f["o_" + c] = p[c]
            cols.append("o_" + c)
    if covid_mode == "control":
        f["c0_covid"] = p["covid_d4" if kind == "q" else "covid_ltm_d4"]
        cols.append("c0_covid")
    else:
        f = f[~(f["covid_target"] | win)]
    return f, cols


def _with_x(f, cols, x, sel_only):
    d = f[f["tdate"] <= SEL_END].copy() if sel_only else f.copy()
    extra = []
    if x is not None:
        d["x"] = x.reindex(d.index)
        extra = ["x"]
    return d.dropna(subset=["ar"] + cols + extra + ["target"]), extra


def _scores(res: pd.DataFrame, lag: int, prefix: str) -> dict:
    ok = res[~res["covid_target"].astype(bool)]
    return {f"{prefix}_{k}": v for k, v in fcast.evaluate(ok, lag).items()}


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
    return _scores(sel, lag, "sel") | _scores(hold, lag, "hold"), res


def run_cv(f, cols, x, h, kind):
    """hv-block CV on targets <= SEL_END; scores exclude COVID-distorted targets."""
    d, extra = _with_x(f, cols, x, sel_only=True)
    if len(d) < MIN_TRAIN_CV + 2:
        return None, None
    w = 7 if kind == "ltm" else 4
    block = np.array([q.year for q in d["tdate"]])
    res = fcast.cv_forecasts(d, "target", ["ar"] + cols, extra, w, block, d["pos"].to_numpy(),
                             min_train=MIN_TRAIN_CV, gap_future=h + w)
    res["covid_target"] = d.loc[res.index, "covid_target"]
    lag = h + (3 if kind == "ltm" else 0)
    return _scores(res, lag, "cv"), res


def insample(f, cols, x, h, kind, drop_covid=True):
    """HAC in-sample statistics (descriptive; not used for inference)."""
    d, _ = _with_x(f, cols, x, sel_only=True)
    if drop_covid:
        d = d[~d["covid_target"]]
    lag = h + (3 if kind == "ltm" else 0)
    return {f"is_{k}": v for k, v in fcast.insample(d, "target", ["ar"] + cols, "x", lag).items()}


X_INDEX = None


def _init(xindex):
    global X_INDEX
    X_INDEX = xindex


def boot_stats(f, cols, x, Xsim, drop_years=()):
    """OLS t of x, its bootstrap p-value and std. beta on targets <= SEL_END."""
    d, _ = _with_x(f, cols, x, sel_only=True)
    if drop_years:
        d = d[[q.year not in drop_years for q in d["tdate"]]]
    if len(d) < MIN_IS:
        return np.nan, np.nan, len(d), np.nan
    Z = fcast.design(d, ["ar"] + cols)
    Z = Z[:, fcast._varying(Z)]
    yv, xv = d["target"].to_numpy(float), d["x"].to_numpy(float)
    pos = np.array([X_INDEX.get_loc(q) for q in d.index])
    xs = Xsim[pos]
    xs = xs[:, np.isfinite(xs).all(axis=0)]
    p, t = inference.boot_pvalue(yv, Z, xv, xs)
    beta = np.linalg.lstsq(np.column_stack([Z, xv]), yv, rcond=None)[0][-1]
    return t, p, len(d), beta * xv.std() / yv.std()


def task(args):
    """All targets / horizons / specs for one candidate feature."""
    feat, x, frames, pframes = args
    Xsim = inference.simulate(x, B_BOOT, feat)
    rows = []
    for (y, h), fr in frames.items():
        fam, kind = TARGETS[y][0], TARGETS[y][1]
        (f, cols), (fc, colsc) = fr["exclude"], fr["control"]
        t, p, n, bstd = boot_stats(f, cols, x, Xsim)
        tc, pc, nc, bstdc = boot_stats(fc, colsc, x, Xsim)
        if not (np.isfinite(t) or np.isfinite(tc)):
            continue
        row = {"target": y, "family": fam, "kind": kind, "h": h, "feature": feat,
               "t_is": t, "p_is": p, "n_is": n, "beta_std": bstd,
               "t_isc": tc, "p_isc": pc, "n_isc": nc, "beta_std_c": bstdc}
        row["t_no16"], _, row["n_no16"], _ = boot_stats(f, cols, x, Xsim[:, :2], drop_years=(2016,))
        row["tc_no16"], _, _, _ = boot_stats(fc, colsc, x, Xsim[:, :2], drop_years=(2016,))
        for prefix, (ff, cc) in (("", (f, cols)), ("c", (fc, colsc))):
            r, _ = run_cv(ff, cc, x, h, kind)
            if r:
                row[f"cv{prefix}_r2"], row[f"cv{prefix}_n"] = r["cv_oos_r2"], r["cv_n_oos"]
            r, _ = run_rt(ff, cc, x, h, kind)
            if r:
                row[f"sel{prefix}_r2"], row[f"sel{prefix}_n"] = r["sel_oos_r2"], r["sel_n_oos"]
                row[f"hold{prefix}_r2"], row[f"hold{prefix}_n"] = r["hold_oos_r2"], r["hold_n_oos"]
                row[f"hold{prefix}_rmse_b"], row[f"hold{prefix}_rmse_m"] = r["hold_rmse_bench"], r["hold_rmse_model"]
        row["t_hac_c"] = insample(fc, colsc, x, h, kind, drop_covid=False).get("is_t_hac")
        for tag, (fp, colsp) in pframes.get((y, h), {}).items():
            tp, pp, npx, bp = boot_stats(fp, colsp, x, Xsim)
            op, _ = run_rt(fp, colsp, x, h, "ltm" if tag == "pxl" else "q")
            row |= {f"t_{tag}": tp, f"p_{tag}": pp, f"n_{tag}": npx, f"beta_std_{tag}": bp,
                    f"oos_{tag}": op["sel_oos_r2"] if op else np.nan}
        rows.append(row)
    return rows


def build_frames(panel, pxp):
    frames, pframes = {}, {}
    for y, (fam, kind, controls, ocontrols) in TARGETS.items():
        if y not in panel:
            continue
        for h in HORIZONS:
            frames[(y, h)] = {m: frame(panel, y, h, controls, kind, m, ocontrols) for m in ("exclude", "control")}
            if y in PROXY:
                pctl = [c for c in controls if not c.startswith("covid")]
                pf = {"px": frame(pxp, PROXY[y], h, pctl, "q", "exclude")}
                if h >= 4:
                    pf["pxl"] = frame(pxp, PROXY_LTM, h, [], "ltm", "exclude")
                pframes[(y, h)] = pf
    return frames, pframes


def prepare():
    tg, X, px = load()
    panel = add_event_controls(tg)
    pxp = add_event_controls(px)
    cover = X.reindex(panel.index).notna().mean()
    X = X.loc[:, cover >= 0.8]
    X = X.join(panel[["store_growth"]].rename(columns={"store_growth": "eu_store_growth__g4"}), how="left")
    X = X.reindex(pd.period_range(min(X.index.min(), pxp.index.min()), HOLD_END, freq="Q"))
    return panel, pxp, X


def main():
    panel, pxp, X = prepare()
    frames, pframes = build_frames(panel, pxp)
    jobs = [(c, X[c], frames, pframes) for c in X.columns]
    rows = []
    with ProcessPoolExecutor(max_workers=4, initializer=_init, initargs=(X.index,)) as ex:
        for r in ex.map(task, jobs):
            rows.extend(r)
            if r:
                print(f"done {r[0]['feature']}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "screen_all.csv", index=False)
    bench = {}
    for (y, h), fr in frames.items():
        for m in ("exclude", "control"):
            o, _ = run_rt(*fr[m], None, h, "q")
            bench[f"{y}_h{h}_{m}"] = o
    with open(RES / "benchmarks.json", "w") as fh:
        json.dump(bench, fh, indent=1, default=float)
    print(df.shape)


if __name__ == "__main__":
    main()
