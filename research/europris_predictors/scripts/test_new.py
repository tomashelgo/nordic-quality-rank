"""Test NEW candidate predictors with exactly the v3 harness (same targets,
benchmark, COVID specs, calibrated randomisation p-values, no-2016 check,
25-year proxy incl. the pre-2015-only test, CV and holdout).

Inputs (data/new/): one or more spec files *_spec.csv with columns
  key, series_id, transforms (e.g. "g4;lvl;d4"), prior_sales, prior_margin, label, group
and the series they reference in *_long.csv (series_id, period, freq, value)
with catalog rows in *_catalog.csv (series_id, ..., typical_release_lag_days).
Priors must be written before running this script.

Usage: python3 scripts/test_new.py [spec glob, default data/new/*_spec.csv]
Output: results/new_candidates_screen.csv and a printed summary with the
family calibration of the new set and the strict-shortlist rule of
rank_evidence.py (with the number of passes expected by chance).
"""
from __future__ import annotations

import glob
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dataset as bd  # noqa: E402
import fcast  # noqa: E402
import screen_predictors as sp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NEW = ROOT / "data" / "new"
RES = ROOT / "results"


def load_new(spec_glob: str):
    specs = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(spec_glob))], ignore_index=True)
    longs = [pd.read_csv(f, dtype={"period": str}) for f in sorted(glob.glob(str(NEW / "*_long.csv")))]
    cats = [pd.read_csv(f) for f in sorted(glob.glob(str(NEW / "*_catalog.csv")))]
    base_long, base_cat = bd.load_long()
    long = pd.concat([base_long] + longs, ignore_index=True)
    cat = pd.concat([base_cat.reset_index()] + cats, ignore_index=True).drop_duplicates("series_id", keep="last")
    return specs, long, cat.set_index("series_id")


def build_features(specs, long, cat, quarters):
    feats, meta = {}, []
    for _, s in specs.iterrows():
        try:
            series, freq = bd.series_from_long(long, s.series_id)
        except KeyError:
            print(f"missing series {s.series_id}")
            continue
        lag = pd.to_numeric(cat.loc[s.series_id].get("typical_release_lag_days", np.nan), errors="coerce") \
            if s.series_id in cat.index else np.nan
        lag = 0.0 if pd.isna(lag) else float(lag)
        cur, prev = bd.realtime_quarterly(series, freq, lag, quarters)
        for tf in str(s.transforms).split(";"):
            tf = tf.strip()
            name = f"new_{s.key}__{tf}"
            if tf == "g4":
                if (series <= 0).any():
                    print(f"skip {name}: non-positive values")
                    continue
                feats[name] = 100 * np.log(cur / prev)
            elif tf == "lvl":
                feats[name] = cur
            elif tf == "d4":
                feats[name] = cur - prev
            else:
                continue
            meta.append({"feature": name, "key": s.key, "series_id": s.series_id, "transform": tf,
                         "prior_sales": s.prior_sales, "prior_margin": s.prior_margin, "label": s.label,
                         "group": s.get("group", ""), "lag_days": lag, "freq": freq})
    return pd.DataFrame(feats, index=quarters), pd.DataFrame(meta)


def summarise(df: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(meta, on="feature", how="left")
    sales = df.family == "revenue"
    df["prior"] = np.where(sales, df.prior_sales, df.prior_margin)
    df["sign"] = np.sign(df.t_is)
    has16 = df.n_no16 < df.n_is
    no16_ok = ~has16 | ((np.sign(df.t_no16) == df.sign) & (df.t_no16.abs() >= 1.5))
    ctrl_ok = np.sign(df.t_isc) == df.sign
    prior_ok = ((df.prior == "+") & (df.sign > 0)) | ((df.prior == "-") & (df.sign < 0))
    pre_ok = ~sales | (np.sign(df.get("t_pxpre", pd.Series(np.nan, index=df.index))) == df.sign)
    eligible = (df.n_is >= 15) & df.p_is.notna() & df.prior.isin(["+", "-"])
    df["shortlist"] = eligible & (df.p_is <= 0.05) & prior_ok & ctrl_ok & no16_ok & pre_ok
    for y, g in df.groupby("target"):
        df.loc[g.index, "q_bh"] = fcast.bh_fdr(g["p_is"].where(g.n_is >= 15))
    el = df[eligible]
    follow = (ctrl_ok & no16_ok & pre_ok)[eligible].mean() if len(el) else np.nan
    df.attrs["expected"] = len(el) * 0.05 * 0.5 * follow if len(el) else 0.0
    df.attrs["eligible"] = len(el)
    return df


def main():
    spec_glob = sys.argv[1] if len(sys.argv) > 1 else str(NEW / "*_spec.csv")
    specs, long, cat = load_new(spec_glob)
    panel, pxp, X = sp.prepare()
    Xn, meta = build_features(specs, long, cat, X.index)
    frames, pframes = sp.build_frames(panel, pxp)
    cover = Xn.reindex(panel.index).notna().mean()
    keep = cover[cover >= 0.6].index
    dropped = sorted(set(Xn.columns) - set(keep))
    if dropped:
        print("dropped for coverage < 60% of the Europris sample:", dropped)
    jobs = [(c, Xn[c], frames, pframes) for c in keep]
    rows = []
    with ProcessPoolExecutor(max_workers=4, initializer=sp._init, initargs=(X.index,)) as ex:
        for r in ex.map(sp.task, jobs):
            rows.extend(r)
    df = summarise(pd.DataFrame(rows), meta)
    out = RES / "new_candidates_screen.csv"
    df.to_csv(out, index=False)
    pd.set_option("display.width", 250)
    cal = df[df.n_is >= 15].groupby("target").agg(tests=("p_is", "count"), share_p05=("p_is", lambda s: (s <= .05).mean()),
                                                  min_q=("q_bh", "min"))
    print(cal.round(3).to_string())
    print(f"\nstrict shortlist: {int(df.shortlist.sum())} passes vs ~{df.attrs['expected']:.1f} expected by chance "
          f"({df.attrs['eligible']} eligible tests)")
    cols = ["feature", "target", "h", "t_is", "p_is", "n_is", "t_isc", "p_isc", "t_no16", "t_pxpre", "p_pxpre",
            "p_px", "cv_r2", "cvc_r2", "hold_r2", "holdc_r2", "shortlist"]
    print(df.sort_values("p_is")[[c for c in cols if c in df]].head(40).round(3).to_string(index=False))
    print(f"\nwritten {out}")


if __name__ == "__main__":
    main()
