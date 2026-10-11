"""Test the pre-registered hypotheses (scripts/hypotheses.py) with calibrated
inference (v3; results/evidence_all.csv from rank_evidence.py).

Primary test per hypothesis: Europris bootstrap p-value at the primary horizon
(p_eu: the larger of the COVID-excluded / COVID-control p-values when both
exist and agree in sign), sign as expected (or prior "?"), Benjamini-Hochberg
across the hypotheses.

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
            t = r.t_isc if np.isfinite(r.t_isc) else r.t_is
            ok = sign_ok(t, hy["sign"])
            proxy_ok = bool(np.isfinite(r.get("p_proxy", np.nan)) and r.p_proxy <= 0.05 and ok)
            rec = {"id": hy["id"], "feature": hy["feature"], "target": hy["target"], "h": h, "primary": h == hy["h"],
                   "sign": hy["sign"], "t_is": r.t_is, "p_is": r.p_is, "t_isc": r.t_isc, "p_isc": r.p_isc,
                   "p_eu": r.p_eu if ok else 1.0, "sign_ok": ok, "t_no16": r.t_no16, "tc_no16": r.tc_no16,
                   "p_proxy": r.get("p_proxy"), "proxy_ok": proxy_ok, "hold_r2": r.hold_r2, "holdc_r2": r.holdc_r2,
                   "partial": bool(ok and (r.p_eu <= 0.05 or proxy_ok))}
            prof.append(rec)
            if h == hy["h"]:
                prim.append(rec)
    P = pd.DataFrame(prim)
    P["q_bh"] = fcast.bh_fdr(P["p_eu"])
    prof = pd.DataFrame(prof)
    part = prof.groupby("id")["partial"].any()
    P["verdict"] = np.where(P.sign_ok & (P.q_bh <= 0.10), "SUPPORTED",
                            np.where(P["id"].map(part).fillna(False), "PARTIAL", "NOT SUPPORTED"))
    missing = [hy["id"] for hy in HYPOTHESES if hy["id"] not in set(P["id"])]
    P.to_csv(RES / "hypotheses_primary.csv", index=False)
    prof.to_csv(RES / "hypotheses_profile.csv", index=False)
    pd.set_option("display.width", 240)
    print(P[["id", "feature", "target", "h", "verdict", "t_is", "p_is", "t_isc", "p_isc", "q_bh", "t_no16", "tc_no16",
             "p_proxy", "hold_r2", "holdc_r2"]].round(3).to_string(index=False))
    if missing:
        print("not computable at the primary horizon:", missing)


if __name__ == "__main__":
    main()
