"""Test the pre-registered hypotheses (scripts/hypotheses.py) with calibrated
inference (v3; results/evidence_all.csv from rank_evidence.py).

Primary test per hypothesis: Europris bootstrap p-value at the primary horizon
in the primary (COVID-excluded) spec, requiring n >= 15 (p_eu); sign as
expected (or prior "?"); Benjamini-Hochberg across the hypotheses. The
COVID-control spec p-value is reported as a robustness check.

Verdicts:
  SUPPORTED   sign as expected and BH q <= 0.10 at the primary horizon.
  PARTIAL     sign as expected and raw p_eu <= 0.05 at the primary or another
              pre-registered horizon, or (sales) 25-year proxy p <= 0.05 with
              the expected sign.
  NOT SUPPORTED otherwise.
Holdout (2024Q3-2026Q2) R^2 is reported, never used.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcast  # noqa: E402
from hypotheses import HYPOTHESES  # noqa: E402

RES = Path(__file__).resolve().parents[1] / "results"


def sign_ok(t, sign):
    return sign == "?" or (np.isfinite(t) and (t > 0) == (sign == "+"))


def main():
    ev = pd.read_csv(RES / "evidence_all.csv")
    prim, prof = [], []
    for hy in HYPOTHESES:
        g = ev[(ev.feature == hy["feature"]) & (ev.target == hy["target"])]
        for h in sorted(set(hy["hs"]) | {hy["h"]}):
            r = g[g.h == h]
            if r.empty:
                prof.append({"id": hy["id"], "h": h, "primary": h == hy["h"], "note": "not computable"})
                continue
            r = r.iloc[0]
            t = r.t_is
            ok = sign_ok(t, hy["sign"])
            p_eu = r.p_is if (np.isfinite(r.p_is) and r.n_is >= 15) else np.nan
            pp = r.get("p_pxpre", np.nan) if np.sign(r.get("t_pxpre", np.nan)) == np.sign(t) else 1.0
            proxy_ok = bool(np.isfinite(pp) and pp <= 0.05 and ok)
            rec = {"id": hy["id"], "feature": hy["feature"], "target": hy["target"], "h": h, "primary": h == hy["h"],
                   "sign": hy["sign"], "t_is": r.t_is, "p_is": r.p_is, "t_isc": r.t_isc, "p_isc": r.p_isc,
                   "n_is": r.n_is, "p_eu": (p_eu if ok else 1.0) if np.isfinite(p_eu) else np.nan, "sign_ok": ok, "t_no16": r.t_no16, "tc_no16": r.tc_no16,
                   "p_proxy_pre2015": pp if np.isfinite(pp) else np.nan, "proxy_ok": proxy_ok, "hold_r2": r.hold_r2, "holdc_r2": r.holdc_r2,
                   "partial": bool(ok and ((np.isfinite(p_eu) and p_eu <= 0.05) or proxy_ok))}
            prof.append(rec)
            if h == hy["h"]:
                prim.append(rec)
    P = pd.DataFrame(prim)
    P["q_bh"] = fcast.bh_fdr(P["p_eu"])
    prof = pd.DataFrame(prof)
    part = prof.groupby("id")["partial"].any()
    P["verdict"] = np.where(P.sign_ok & (P.q_bh <= 0.10), "SUPPORTED",
                            np.where(P["id"].map(part).fillna(False), "PARTIAL",
                                     np.where(P.p_eu.isna(), "UNTESTABLE (n < 15)", "NOT SUPPORTED")))
    missing = [hy["id"] for hy in HYPOTHESES if hy["id"] not in set(P["id"])]
    P.to_csv(RES / "hypotheses_primary.csv", index=False)
    prof.to_csv(RES / "hypotheses_profile.csv", index=False)
    pd.set_option("display.width", 240)
    print(P[["id", "feature", "target", "h", "verdict", "n_is", "t_is", "p_is", "t_isc", "p_isc", "q_bh", "t_no16",
             "hold_r2", "holdc_r2"]].round(3).to_string(index=False))
    if missing:
        print("not computable at the primary horizon:", missing)


if __name__ == "__main__":
    main()
