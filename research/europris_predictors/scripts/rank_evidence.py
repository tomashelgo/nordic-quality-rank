"""Evidence synthesis (v3, calibrated inference). Holdout results are NOT used.

For each (feature, target, h), from results/screen_all.csv:
  p_eu    Europris evidence: the larger of the two specs' bootstrap p-values
          (COVID-excluded and COVID-control) when both exist and the signs
          agree; 1.0 when the signs disagree; else the one available.
  q_eu    Benjamini-Hochberg q of p_eu within each target (all features x
          horizons, ~570 tests per target).
  p_proxy 25-year category proxy (sales targets only): bootstrap p of the
          quarterly proxy (h <= 3) or the better of quarterly / annual-window
          proxy (h >= 4), same sign as Europris required.

Tiers:
  ESTABLISHED  q_eu <= 0.10.
  SUPPORTED    p_eu <= 0.05 with same-sign |t| >= 1.5 without 2016 (in either
               spec), and, for sales targets, the proxy agrees (p_proxy <= 0.10)
               — or, failing the proxy, both specs individually <= 0.05.
  WEAK         min(p_is, p_isc) <= 0.05 with sign agreement, or proxy-only
               (p_proxy <= 0.01 and same Europris sign).
  none         otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcast  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
DATA = ROOT / "data"


def main():
    df = pd.read_csv(RES / "screen_all.csv")
    cat = pd.read_csv(DATA / "predictor_catalog.csv")
    company = pd.DataFrame([{"feature": "eu_store_growth__g4", "concept": "store_growth", "label": "Europris store count growth",
                             "group": "company", "prior_sales": "+", "prior_margin": "?"}])
    cat = pd.concat([cat, company], ignore_index=True)
    df = df.merge(cat[["feature", "concept", "label", "group", "prior_sales", "prior_margin"]], on="feature", how="left")

    both = df.p_is.notna() & df.p_isc.notna()
    agree = np.sign(df.t_is) == np.sign(df.t_isc)
    df["sign"] = np.sign(df.t_isc.fillna(df.t_is))
    df["p_eu"] = np.where(both, np.where(agree, np.maximum(df.p_is, df.p_isc), 1.0), df[["p_is", "p_isc"]].max(axis=1))
    for y, g in df.groupby("target"):
        df.loc[g.index, "q_eu"] = fcast.bh_fdr(g["p_eu"])
    no16 = ((np.sign(df.t_no16) == df.sign) & (df.t_no16.abs() >= 1.5)) | ((np.sign(df.tc_no16) == df.sign) & (df.tc_no16.abs() >= 1.5))
    df["robust_no16"] = no16
    # proxy p with sign agreement
    pq = np.where(np.sign(df.get("t_px")) == df.sign, df.get("p_px"), 1.0)
    pl = np.where(np.sign(df.get("t_pxl")) == df.sign, df.get("p_pxl"), 1.0)
    pq = pd.Series(pq, index=df.index).where(df.get("p_px").notna())
    pl = pd.Series(pl, index=df.index).where(df.get("p_pxl").notna())
    df["p_proxy"] = np.where(df.h >= 4, pd.concat([pq, pl], axis=1).min(axis=1), pq)
    sales = df.family == "revenue"
    est = df.q_eu <= 0.10
    sup_core = (df.p_eu <= 0.05) & df.robust_no16
    sup = sup_core & np.where(sales, (df.p_proxy <= 0.10) | (both & agree & (df.p_is <= 0.05) & (df.p_isc <= 0.05)),
                              both & agree & (df.p_is <= 0.05) & (df.p_isc <= 0.05) | (df.p_eu <= 0.05))
    weak = ((df[["p_is", "p_isc"]].min(axis=1) <= 0.05) & (agree | ~both)) | (sales & (df.p_proxy <= 0.01))
    df["tier"] = np.select([est, sup, weak], ["ESTABLISHED", "SUPPORTED", "WEAK"], "none")
    df.to_csv(RES / "evidence_all.csv", index=False)
    pd.set_option("display.width", 260)
    show = ["tier", "concept", "feature", "target", "h", "sign", "t_is", "p_is", "t_isc", "p_isc", "q_eu", "t_no16", "tc_no16",
            "t_px", "p_px", "t_pxl", "p_pxl", "cvc_r2"]
    top = df[df.tier.isin(["ESTABLISHED", "SUPPORTED"])].sort_values(["tier", "p_eu"])
    print(top[show].round(3).to_string(index=False))
    print()
    print(df.groupby(["target", "tier"]).size().unstack(fill_value=0))
    summ = (df[df.tier != "none"].groupby(["concept", "tier"])
              .agg(targets=("target", lambda s: ",".join(sorted(set(s)))),
                   horizons=("h", lambda s: ",".join(str(int(x)) for x in sorted(set(s)))),
                   best_p=("p_eu", "min"))
              .reset_index().sort_values(["tier", "best_p"]))
    summ.to_csv(RES / "evidence_concepts.csv", index=False)


if __name__ == "__main__":
    main()
