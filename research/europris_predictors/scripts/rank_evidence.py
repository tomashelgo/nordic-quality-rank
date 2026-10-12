"""Evidence synthesis (v3, calibrated). Holdout results are NOT used here.

The COVID-excluded spec is primary; the COVID-control spec is a robustness
check only (45-70% of its rows are COVID-era, where x and y are both driven by
the pandemic and the independence null is not credible - v3 audit).

Outputs
  results/evidence_all.csv          every (feature, target, h) with its stats
  results/family_calibration.csv    per target: share of primary-spec p <= .05 / .01
                                    vs nominal, and the BH result
  results/exploratory_shortlist.csv strict shortlist, with the number of passes
                                    expected by chance

Strict shortlist rule (per test):
  primary spec computable with n >= 15 and bootstrap p <= 0.05;
  coefficient sign equal to a DIRECTIONAL prior written before the analysis
  (candidates.py; '?' priors are excluded);
  the COVID-control spec has the same sign;
  if 2016 targets are in the sample, dropping them keeps the same sign with |t| >= 1.5;
  for sales targets, the independent pre-2015 category proxy has the same sign.
Under the null each test passes with probability ~ 0.05 x 0.5 x (share of
same-sign follow-ups); the expected count is reported next to the observed one.
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
    sales = df.family == "revenue"
    df["prior"] = np.where(sales, df.prior_sales, df.prior_margin)
    df["sign"] = np.sign(df.t_is)
    for y, g in df.groupby("target"):
        df.loc[g.index, "q_bh"] = fcast.bh_fdr(g["p_is"].where(g.n_is >= 15))
    has16 = df.n_no16 < df.n_is
    no16_ok = ~has16 | ((np.sign(df.t_no16) == df.sign) & (df.t_no16.abs() >= 1.5))
    ctrl_ok = np.sign(df.t_isc) == df.sign
    prior_ok = ((df.prior == "+") & (df.sign > 0)) | ((df.prior == "-") & (df.sign < 0))
    pre_ok = ~sales | (np.sign(df.get("t_pxpre")) == df.sign)
    eligible = (df.n_is >= 15) & df.p_is.notna() & df.prior.isin(["+", "-"])
    df["shortlist"] = eligible & (df.p_is <= 0.05) & prior_ok & ctrl_ok & no16_ok & pre_ok
    df.to_csv(RES / "evidence_all.csv", index=False)

    cal = []
    for y, g in df.groupby("target"):
        gp = g[g.n_is >= 15]
        cal.append({"target": y, "tests_primary": int(gp.p_is.notna().sum()),
                    "share_p05": float((gp.p_is <= 0.05).mean()), "share_p01": float((gp.p_is <= 0.01).mean()),
                    "nominal_p05": 0.05, "min_q_bh": float(g.q_bh.min()),
                    "survive_bh_q10": int((g.q_bh <= 0.10).sum())})
    cal = pd.DataFrame(cal)
    cal.to_csv(RES / "family_calibration.csv", index=False)

    el = df[eligible]
    follow = (ctrl_ok & no16_ok & pre_ok)[eligible].mean()
    expected = len(el) * 0.05 * 0.5 * follow
    sl = df[df.shortlist].sort_values("p_is")
    sl.assign(expected_by_chance=expected).to_csv(RES / "exploratory_shortlist.csv", index=False)
    pd.set_option("display.width", 240)
    print(cal.round(3).to_string(index=False))
    print(f"\nexploratory shortlist: {len(sl)} passes vs ~{expected:.1f} expected by chance "
          f"({len(el)} eligible tests with a directional prior)")
    print(sl[["concept", "feature", "target", "h", "sign", "t_is", "p_is", "n_is", "t_isc", "p_isc", "t_no16",
              "t_pxpre", "p_pxpre", "cv_r2", "cvc_r2"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
