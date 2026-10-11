"""Test the predictors that are known in advance and therefore sit in the
benchmark: calendar (Easter window, shop trading days), base effect, store
pipeline and margin mean reversion. Each component is dropped from the
benchmark and tested as the candidate.

Inference:
  calendar terms  exact placebo-calendar randomisation: the same quarter's
                  calendar from year Y+k (k = -399..399, k != 0; weekday
                  patterns repeat every 400 years) replaces the real one; p =
                  share of placebo |t| >= observed |t|. Also a joint F-test of
                  both calendar terms against joint placebo calendars.
  other terms     AR-sieve conditional-randomisation bootstrap (inference.py).
Output: results/benchmark_components.csv, results/calendar_joint.csv.
"""
from __future__ import annotations

import datetime as dt
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcast  # noqa: E402
import inference  # noqa: E402
import screen_predictors as sp  # noqa: E402

RES = Path(__file__).resolve().parents[1] / "results"
SHIFTS = [k for k in range(-399, 400) if k != 0]
CALENDAR = {"c_tdays_d4", "c_easter_share_d4"}
COMPONENTS = {
    "rev_yoy": ["c_tdays_d4", "c_easter_share_d4", "c_base", "o_store_growth"],
    "lfl": ["c_tdays_d4", "c_easter_share_d4", "c_base"],
    "gm_d4": ["c_easter_share_d4", "c_stocktaking_d4", "c_base", "o_gm_ltm"],
    "ebitm_d4": ["c_easter_share_d4", "c_ifrs16_d4", "c_base", "o_ebitm_ltm"],
}


@lru_cache(maxsize=None)
def tdays(year: int, quarter: int) -> int:
    e = easter(year)
    hol = {dt.date(year, 1, 1), e - dt.timedelta(3), e - dt.timedelta(2), e + dt.timedelta(1), dt.date(year, 5, 1),
           dt.date(year, 5, 17), e + dt.timedelta(39), e + dt.timedelta(50), dt.date(year, 12, 25), dt.date(year, 12, 26)}
    d = dt.date(year, 3 * quarter - 2, 1)
    end = dt.date(year + 1, 1, 1) if quarter == 4 else dt.date(year, 3 * quarter + 1, 1)
    n = 0
    while d < end:
        n += d.weekday() < 6 and d not in hol
        d += dt.timedelta(1)
    return n


@lru_cache(maxsize=None)
def easter_q1_share(year: int, days: int = 14) -> float:
    e = easter(year)
    return sum((e - dt.timedelta(k)).month <= 3 for k in range(1, days + 1)) / days


def cal_d4(year: int, quarter: int, comp: str) -> float:
    if comp == "c_tdays_d4":
        return float(tdays(year, quarter) - tdays(year - 1, quarter))
    d = easter_q1_share(year) - easter_q1_share(year - 1)
    return d if quarter == 1 else -d if quarter == 2 else 0.0


def placebo_t(d, base, comp):
    """Observed t of `comp` and its placebo-calendar p-value (rows d, controls base)."""
    Z = fcast.design(d, ["ar"] + base)
    Z = Z[:, fcast._varying(Z)]
    yv = d["target"].to_numpy(float)
    x = d[comp].to_numpy(float)
    tq = list(d["tdate"])
    # sanity: the stored control equals the recomputed calendar
    assert np.allclose(x, [cal_d4(q.year, q.quarter, comp) for q in tq], atol=1e-6), comp
    Xp = np.array([[cal_d4(q.year + k, q.quarter, comp) for k in SHIFTS] for q in tq])
    t = inference.ols_t_many(yv, Z, x[:, None])[0]
    tk = inference.ols_t_many(yv, Z, Xp)
    tk = tk[np.isfinite(tk)]
    return t, (1 + np.sum(np.abs(tk) >= abs(t))) / (1 + len(tk))


def fstat(y, Z, W):
    r0 = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    ZW = np.column_stack([Z, W])
    r1 = y - ZW @ np.linalg.lstsq(ZW, y, rcond=None)[0]
    dof = len(y) - ZW.shape[1]
    return ((r0 @ r0 - r1 @ r1) / W.shape[1]) / (r1 @ r1 / dof)


def main():
    panel, pxp, X = sp.prepare()
    sp._init(X.index)
    frames, _ = sp.build_frames(panel, pxp)
    rows, joint = [], []
    for (y, h), fr in frames.items():
        kind = sp.TARGETS[y][1]
        for mode in ("exclude", "control"):
            f, cols = fr[mode]
            d_all = f[f["tdate"] <= sp.SEL_END].dropna(subset=["ar"] + cols + ["target"])
            for comp in COMPONENTS[y]:
                if comp not in cols:
                    continue
                base = [c for c in cols if c != comp]
                rec = {"target": y, "h": h, "component": comp, "spec": mode, "n": len(d_all)}
                if len(d_all) >= sp.MIN_IS:
                    if comp in CALENDAR:
                        rec["t"], rec["p"] = placebo_t(d_all, base, comp)
                        rec["test"] = "placebo calendar"
                    else:
                        xc = f[comp].reindex(X.index)
                        sim = inference.simulate(xc, 5000, f"{comp}_{y}_{h}")
                        rec["t"], rec["p"], _, _ = sp.boot_stats(f.drop(columns=[comp]), base, xc, sim)
                        rec["test"] = "AR-sieve bootstrap"
                    xs = d_all[comp]
                    b = np.linalg.lstsq(np.column_stack([fcast.design(d_all, ["ar"] + base), xs]), d_all["target"],
                                        rcond=None)[0][-1]
                    rec["beta"] = b
                    rec["beta_std"] = b * xs.std() / d_all["target"].std()
                xc = f[comp].reindex(X.index)
                cv, _ = sp.run_cv(f.drop(columns=[comp]), base, xc, h, kind)
                rt, _ = sp.run_rt(f.drop(columns=[comp]), base, xc, h, kind)
                rec |= {"cv_r2": cv["cv_oos_r2"] if cv else np.nan, "sel_r2": rt["sel_oos_r2"] if rt else np.nan,
                        "hold_r2": rt["hold_oos_r2"] if rt else np.nan}
                rows.append(rec)
            comps = [c for c in ("c_tdays_d4", "c_easter_share_d4") if c in cols]
            if len(comps) == 2 and len(d_all) >= sp.MIN_IS:
                base = [c for c in cols if c not in comps]
                Z = fcast.design(d_all, ["ar"] + base)
                Z = Z[:, fcast._varying(Z)]
                yv = d_all["target"].to_numpy(float)
                F0 = fstat(yv, Z, d_all[comps].to_numpy(float))
                tq = list(d_all["tdate"])
                Fk = np.array([fstat(yv, Z, np.array([[cal_d4(q.year + k, q.quarter, c) for c in comps] for q in tq]))
                               for k in SHIFTS[::3]])
                joint.append({"target": y, "h": h, "spec": mode, "n": len(d_all), "F": F0,
                              "p_placebo": (1 + np.sum(Fk >= F0)) / (1 + len(Fk)), "n_placebo": len(Fk)})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "benchmark_components.csv", index=False)
    jt = pd.DataFrame(joint)
    jt.to_csv(RES / "calendar_joint.csv", index=False)
    pd.set_option("display.width", 200)
    print(df[df.h.isin([1, 2, 4, 6])].round(3).to_string(index=False))
    print(jt.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
