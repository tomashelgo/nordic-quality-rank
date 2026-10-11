"""Evidence synthesis: which (variable, target, horizon) relationships are confirmed.

Europris alone has ~20 usable quarterly observations once COVID-distorted y/y
comparisons are removed, too few to separate 74 candidates from luck (see
familywise_placebo.csv). Confirmation therefore needs two independent pieces of
evidence. Holdout results (2024Q3-2026Q2) are NOT used here.

Sales family (targets lfl, rev_yoy) - two-sample rule:
  P  25-year proxy (SSB NACE 47.19, Europris's own category): out-of-sample
     R^2 > 0 with Clark-West p < 0.05 and HAC |t| >= 2, on the quarterly
     proxy (h <= 3) or the quarterly / annual-window proxy (h >= 4).
  E  Europris: same coefficient sign with HAC |t| >= 2 in the primary
     (COVID-excluded) spec and the same sign in the COVID-control spec.
  S  sign not contradicting the prior.

Margin / profit family (gm_d4, ebitm_d4) - no long-history proxy exists, so:
  E  same sign in both COVID specs with HAC |t| >= 2.5 in both;
  O  out-of-sample: CV R^2 > 0 (COVID-control spec, ~20 obs) with placebo
     p <= 0.10 (beats >= 90% of time-shifted placebo versions of itself);
  S  sign not contradicting the prior.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
DATA = ROOT / "data"


def prior_ok(sign: float, prior: str) -> bool:
    return prior == "?" or (sign > 0) == (prior == "+")


def main():
    df = pd.read_csv(RES / "screen_all.csv")
    cat = pd.read_csv(DATA / "predictor_catalog.csv")
    company = pd.DataFrame([{"feature": "eu_store_growth__g4", "concept": "store_growth", "label": "Europris store count growth",
                             "group": "company", "prior_sales": "+", "prior_margin": "?"}])
    cat = pd.concat([cat, company], ignore_index=True)
    df = df.merge(cat[["feature", "concept", "label", "group", "prior_sales", "prior_margin"]], on="feature", how="left")
    out = []
    for _, r in df.iterrows():
        rec = r.to_dict()
        if r.family == "revenue":
            q_ok = (r.proxy_r2 > 0) & (r.proxy_cw_p < 0.05) & (abs(r.proxy_t_hac) >= 2)
            l_ok = (r.h >= 4) & (r.get("proxyltm_r2", np.nan) > 0) & (r.get("proxyltm_cw_p", np.nan) < 0.05) & (abs(r.get("proxyltm_t_hac", np.nan)) >= 2)
            if l_ok and (not q_ok or r.proxyltm_r2 > r.proxy_r2):
                psign, pr2, pp, pt, pkind = np.sign(r.proxyltm_t_hac), r.proxyltm_r2, r.proxyltm_cw_p, r.proxyltm_t_hac, "annual"
            elif q_ok:
                psign, pr2, pp, pt, pkind = np.sign(r.proxy_t_hac), r.proxy_r2, r.proxy_cw_p, r.proxy_t_hac, "quarterly"
            else:
                psign, pr2, pp, pt, pkind = np.nan, np.nan, np.nan, np.nan, ""
            P = bool(q_ok or l_ok)
            E = bool(P and np.sign(r.is_t_hac) == psign and abs(r.is_t_hac) >= 2 and np.sign(r.isc_t_hac) == psign)
            S = bool(P and prior_ok(psign, r.prior_sales))
            rec |= {"P": P, "E": E, "S": S, "confirmed": P and E and S, "proxy_kind": pkind, "proxy_r2_used": pr2,
                    "proxy_p_used": pp, "proxy_t_used": pt, "sign": psign,
                    "score": (pr2 if P else 0) + 0.02 * min(abs(r.is_t_hac), 6) if P and E else np.nan}
        else:
            prior = r.prior_margin if r.family == "margin" else (r.prior_margin if r.prior_margin != "?" else r.prior_sales)
            s1, s2 = np.sign(r.is_t_hac), np.sign(r.isc_t_hac)
            E = bool(s1 == s2 and abs(r.is_t_hac) >= 2.5 and abs(r.isc_t_hac) >= 2.5)
            O = bool(r.cvc_r2 > 0 and r.get("placebo_c_p", np.nan) <= 0.10)
            S = bool(E and prior_ok(s1, prior))
            rec |= {"E": E, "O": O, "S": S, "confirmed": E and O and S, "sign": s1,
                    "score": r.cvc_r2 + 0.02 * min(abs(r.is_t_hac), 6) if E and O else np.nan}
        out.append(rec)
    ev = pd.DataFrame(out)
    ev["bucket"] = np.where(ev.h <= 3, "short", np.where(ev.h == 4, "both", "long"))
    ev.to_csv(RES / "evidence_all.csv", index=False)
    conf = ev[ev.confirmed].sort_values("score", ascending=False)
    conf.to_csv(RES / "evidence_confirmed.csv", index=False)
    pd.set_option("display.width", 260)
    show = ["concept", "feature", "target", "h", "sign", "score", "is_t_hac", "isc_t_hac", "cv_oos_r2", "cvc_r2",
            "placebo_p", "placebo_c_p", "proxy_kind", "proxy_r2_used", "proxy_p_used", "proxy_t_used", "prior_sales", "prior_margin"]
    print(conf[show].round(3).to_string(index=False))
    # concept-level summary: best confirmed entry per concept, with its horizon set
    summ = (conf.groupby("concept")
                .agg(n=("h", "size"), targets=("target", lambda s: ",".join(sorted(set(s)))),
                     horizons=("h", lambda s: ",".join(str(int(x)) for x in sorted(set(s)))),
                     best_score=("score", "max"))
                .sort_values("best_score", ascending=False))
    summ.to_csv(RES / "evidence_concepts.csv")
    print()
    print(summ.to_string())


if __name__ == "__main__":
    main()
