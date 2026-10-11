"""Test the pre-registered hypotheses (scripts/hypotheses.py) on the screen output.

Decision rule (fixed before looking at hypothesis results):
  SUPPORTED   at the primary horizon: coefficient sign as expected (or prior "?"),
              CV R^2 > 0, Benjamini-Hochberg adjusted Clark-West p <= 0.10
              across all primary tests, and shifted-placebo p <= 0.10.
  PARTIAL     at the primary or another pre-registered horizon: sign as expected,
              CV R^2 > 0, raw Clark-West p <= 0.10 and placebo p <= 0.20.
  otherwise   NOT SUPPORTED.
Robustness columns (reported, not part of the rule): COVID-excluded CV R^2,
real-time selection-window R^2, 25-year proxy R^2 (sales family), and the
holdout 2024Q3-2026Q2 R^2 (never used for any selection).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcast  # noqa: E402
from hypotheses import HYPOTHESES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"

COLS = ["cv_oos_r2", "cv_cw_p", "cv_n_oos", "placebo_p", "is_beta_std", "is_t_hac", "cvc_r2", "rtc_sel_r2", "rtc_hold_r2",
        "sel_oos_r2", "sel_n_oos", "proxy_r2", "proxy_cw_p", "proxyltm_r2", "proxyltm_cw_p", "hold_oos_r2", "hold_cw_p"]


def sign_ok(beta, sign):
    if sign == "?" or not np.isfinite(beta):
        return True
    return (beta > 0) == (sign == "+")


def main():
    df = pd.read_csv(RES / "screen_all.csv")
    prim, prof = [], []
    for hy in HYPOTHESES:
        g = df[(df.feature == hy["feature"]) & (df.target == hy["target"])]
        for h in sorted(set(hy["hs"]) | {hy["h"]}):
            r = g[g.h == h]
            if r.empty:
                continue
            r = r.iloc[0]
            rec = {"id": hy["id"], "feature": hy["feature"], "target": hy["target"], "h": h,
                   "primary": h == hy["h"], "sign": hy["sign"], **{c: r.get(c, np.nan) for c in COLS}}
            rec["sign_ok"] = sign_ok(rec["is_beta_std"], hy["sign"])
            rec["partial"] = bool(rec["sign_ok"] and rec["cv_oos_r2"] > 0 and rec["cv_cw_p"] <= 0.10
                                  and rec["placebo_p"] <= 0.20)
            prof.append(rec)
            if h == hy["h"]:
                prim.append(rec)
    P = pd.DataFrame(prim)
    P["cv_cw_p_bh"] = fcast.bh_fdr(P["cv_cw_p"])
    P["supported"] = P["sign_ok"] & (P["cv_oos_r2"] > 0) & (P["cv_cw_p_bh"] <= 0.10) & (P["placebo_p"] <= 0.10)
    prof = pd.DataFrame(prof)
    part = prof.groupby("id")["partial"].any()
    P["any_partial"] = P["id"].map(part)
    P["verdict"] = np.where(P["supported"], "SUPPORTED", np.where(P["any_partial"], "PARTIAL", "not supported"))
    P.to_csv(RES / "hypotheses_primary.csv", index=False)
    prof.to_csv(RES / "hypotheses_profile.csv", index=False)
    pd.set_option("display.width", 250)
    show = ["id", "feature", "target", "h", "verdict", "is_beta_std", "is_t_hac", "cv_oos_r2", "cv_cw_p", "cv_cw_p_bh",
            "placebo_p", "cvc_r2", "rtc_sel_r2", "rtc_hold_r2", "sel_oos_r2", "proxy_r2", "hold_oos_r2"]
    print(P[show].round(3).to_string())
    print()
    print(prof[["id", "h", "primary", "sign_ok", "partial", "is_beta_std", "cv_oos_r2", "cv_cw_p", "placebo_p",
                "cvc_r2", "rtc_sel_r2", "rtc_hold_r2", "proxy_r2", "proxyltm_r2", "hold_oos_r2"]].round(3).to_string())


if __name__ == "__main__":
    main()
