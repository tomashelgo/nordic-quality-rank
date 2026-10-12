"""Rank concepts from the screen and pick the top 5 (>=2 short-term, >=2 long-term).

Only SELECTION-window statistics (targets dated <= 2024Q2) and robustness checks
that do not touch the holdout are used here; holdout columns are reported later
by evaluate_top.py.

A (feature, target, h) result "passes" when
  * sel_oos_r2 > 0 and Clark-West p < 0.10 (beats the AR benchmark out of sample)
  * placebo_p <= 0.10 (beats >= 90% of time-shifted placebo versions of itself)
  * the full-sample coefficient sign matches the prior (ambiguous priors pass)
and it is "robust" when additionally the COVID-excluded OOS R^2 > 0 or, for the
sales family, the 25-year proxy-target OOS R^2 > 0.

A concept qualifies for a horizon bucket (short: h=1-4 on quarterly targets;
long: h=4-8 on quarterly or annual-window targets) when one target has >= 2
passing horizons in that bucket, at least one of them robust. Its score is the
mean selection OOS R^2 over the passing horizons, ranked within bucket.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
DATA = ROOT / "data"

SHORT = {1, 2, 3, 4}
LONG = {4, 6, 8}


def sign_ok(row) -> bool:
    prior = row["prior_sales"] if row["family"] == "revenue" else row["prior_margin"]
    if row["family"] == "profit":
        ps, pm = row["prior_sales"], row["prior_margin"]
        prior = ps if pm == "?" else pm if ps == "?" else (ps if ps == pm else "?")
    b = row.get("is_beta", np.nan)
    if prior == "?" or not np.isfinite(b):
        return True
    return (b > 0) == (prior == "+")


def main():
    df = pd.read_csv(RES / "screen_all.csv")
    cat = pd.read_csv(DATA / "predictor_catalog.csv")
    company = pd.DataFrame([{"feature": "eu_store_growth__g4", "concept": "store_growth", "label": "Europris store count growth",
                             "group": "company", "prior_sales": "+", "prior_margin": "?"}])
    cat = pd.concat([cat, company], ignore_index=True)
    df = df.merge(cat[["feature", "concept", "label", "group", "prior_sales", "prior_margin"]], on="feature", how="left")
    df["sign_ok"] = df.apply(sign_ok, axis=1)
    df["pass"] = (df["sel_oos_r2"] > 0) & (df["sel_cw_p"] < 0.10) & (df["placebo_p"] <= 0.10) & df["sign_ok"]
    robust_proxy = (df["family"] == "revenue") & (df.get("proxy_oos_r2", np.nan) > 0)
    df["robust"] = df["pass"] & ((df.get("nocovid_oos_r2", np.nan) > 0) | robust_proxy)
    df.to_csv(RES / "screen_scored.csv", index=False)

    quals = []
    for (concept, feature, target), g in df.groupby(["concept", "feature", "target"]):
        kind = g["kind"].iloc[0]
        for bucket, hs in (("short", SHORT), ("long", LONG)):
            if bucket == "short" and kind != "q":
                continue
            gb = g[g["h"].isin(hs)]
            p = gb[gb["pass"]]
            if len(p) >= 2 and p["robust"].any():
                quals.append({"bucket": bucket, "concept": concept, "feature": feature, "target": target,
                              "family": g["family"].iloc[0], "group": g["group"].iloc[0], "label": g["label"].iloc[0],
                              "pass_h": ",".join(str(int(h)) for h in sorted(p["h"])),
                              "n_pass": len(p), "n_robust": int(p["robust"].sum()),
                              "score": p["sel_oos_r2"].mean(),
                              "mean_cw_p": p["sel_cw_p"].mean(), "mean_placebo_p": p["placebo_p"].mean(),
                              "beta_std": p["is_beta_std"].mean()})
    q = pd.DataFrame(quals)
    if q.empty:
        print("no concept qualified")
        q.to_csv(RES / "qualified.csv", index=False)
        return
    q = q.sort_values(["bucket", "score"], ascending=[True, False])
    q.to_csv(RES / "qualified.csv", index=False)

    # best entry per concept & bucket
    best = q.sort_values("score", ascending=False).drop_duplicates(["bucket", "concept"])

    picks, used_groups, used_concepts = [], set(), set()

    def take(bucket, n):
        for _, r in best[best["bucket"] == bucket].iterrows():
            if len([p for p in picks if p["bucket"] == bucket]) >= n:
                break
            if r["concept"] in used_concepts or r["group"] in used_groups:
                continue
            picks.append(r.to_dict()); used_concepts.add(r["concept"]); used_groups.add(r["group"])

    take("short", 2)
    take("long", 2)
    # fifth slot: best remaining in either bucket
    rest = best[~best["concept"].isin(used_concepts) & ~best["group"].isin(used_groups)]
    if len(rest):
        picks.append(rest.iloc[0].to_dict())
    out = pd.DataFrame(picks)
    out.to_csv(RES / "top5.csv", index=False)
    pd.set_option("display.width", 220)
    print(best.groupby("bucket").head(12)[["bucket", "concept", "feature", "target", "pass_h", "n_robust", "score", "mean_cw_p", "mean_placebo_p", "beta_std"]].to_string())
    print("\nTOP 5:\n", out[["bucket", "concept", "feature", "target", "pass_h", "score"]].to_string())


if __name__ == "__main__":
    main()
