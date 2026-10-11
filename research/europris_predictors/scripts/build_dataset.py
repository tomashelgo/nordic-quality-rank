"""Build the quarterly modelling dataset.

Outputs (in ../data):
  europris_norway_quarterly.csv  merged + checked company panel
  targets_quarterly.csv          target variables per quarter
  predictors_quarterly.csv       candidate predictors per forecast origin quarter,
                                 aligned to what was published 45 days after the
                                 quarter closed (pseudo real time)
  predictor_catalog.csv          one row per candidate predictor (transform, lag, source)

Real-time alignment: a forecast made at origin t is dated 45 days after the end
of quarter t (Europris has reported quarter t by then). A monthly series with a
publication lag of L days contributes the 3-month window ending at the latest
month m <= last month of quarter t with month_end(m) + L <= origin. Quarterly
series use the latest quarter q <= t with quarter_end(q) + L <= origin. Data are
latest vintages (revisions are not reversed out); see the report's limitations.
"""
from __future__ import annotations

from pathlib import Path

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidates import CANDIDATES, DERIVED  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ORIGIN_DAYS = 45

def load_europris() -> pd.DataFrame:
    parts = [pd.read_csv(DATA / f) for f in ("europris_part1.csv", "europris_part2.csv") if (DATA / f).exists()]
    df = pd.concat(parts, ignore_index=True)
    df["quarter"] = df["quarter"].astype(str).str.strip()
    df = df.drop_duplicates("quarter", keep="last")
    df["q"] = pd.PeriodIndex(df["quarter"], freq="Q")
    df = df.sort_values("q").set_index("q")
    num = [c for c in df.columns if c.endswith(("_nok_m", "_pct", "_pp")) or c.startswith("stores_")]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def build_targets(eu: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    idx = pd.period_range(eu.index.min(), eu.index.max(), freq="Q")
    eu = eu.reindex(idx)
    t = pd.DataFrame(index=idx)
    rev = eu["norway_revenue_nok_m"]
    gp = eu["gross_profit_nok_m"]
    gm = eu["gross_margin_pct"].where(eu["gross_margin_pct"].notna(), 100 * gp / rev)
    ebit = eu["ebit_nok_m"]
    fx = eu.get("unrealised_fx_gain_nok_m")
    t["rev"] = rev
    t["gm"] = gm
    t["ebitm"] = 100 * ebit / rev
    # quarterly y/y targets
    t["rev_yoy"] = 100 * np.log(rev / rev.shift(4))
    t["lfl"] = eu["lfl_growth_pct"]
    t["gm_d4"] = gm - gm.shift(4)
    if fx is not None and fx.notna().sum() > 8:
        gm_x = 100 * (gp - fx.fillna(0)) / rev
        t["gm_exfx"] = gm_x
        t["gm_exfx_d4"] = gm_x - gm_x.shift(4)
    t["ebitm_d4"] = t["ebitm"] - t["ebitm"].shift(4)
    # last-twelve-month (annual window) targets
    rev_ltm = rev.rolling(4).sum()
    gp_ltm = gp.rolling(4).sum()
    ebit_ltm = ebit.rolling(4).sum()
    t["rev_ltm_yoy"] = 100 * np.log(rev_ltm / rev_ltm.shift(4))
    t["gm_ltm"] = 100 * gp_ltm / rev_ltm
    t["gm_ltm_d4"] = t["gm_ltm"] - t["gm_ltm"].shift(4)
    t["ebit_ltm_yoy"] = 100 * np.log(ebit_ltm / ebit_ltm.shift(4))
    t["ebitm_ltm"] = 100 * ebit_ltm / rev_ltm
    t["ebitm_ltm_d4"] = t["ebitm_ltm"] - t["ebitm_ltm"].shift(4)
    # stores
    t["stores_total"] = eu["stores_total"]
    t["store_growth"] = 100 * np.log(eu["stores_total"] / eu["stores_total"].shift(4))
    ev = events.reindex(idx)
    for c in ev.columns:
        t["ev_" + c] = ev[c]
    return t


def load_events() -> pd.DataFrame:
    ev = pd.read_csv(DATA / "events_quarterly.csv")
    ev["q"] = pd.PeriodIndex(ev["quarter"].astype(str), freq="Q")
    ev = ev.set_index("q")
    keep = {}
    for c in ("easter_in_q1", "easter_week_split_q1_share", "easter_shift_q1", "covid_border_restrictions",
              "covid_domestic_lockdown", "ifrs16", "oob_consolidated"):
        if c in ev.columns:
            keep[c] = pd.to_numeric(ev[c], errors="coerce")
    out = pd.DataFrame(keep)
    # Easter controls usable for quarterly y/y targets: share of the Easter week in
    # the quarter minus the same share a year earlier (Q1 vs Q2 matters, Q3/Q4 = 0).
    if "easter_week_split_q1_share" in out:
        s = out["easter_week_split_q1_share"]
        qn = out.index.quarter
        in_q = np.where(qn == 1, s, np.where(qn == 2, 1 - s, 0.0))
        out["easter_share_in_q"] = in_q
        out["easter_share_d4"] = out["easter_share_in_q"] - out["easter_share_in_q"].shift(4)
    if "covid_border_restrictions" in out:
        out["covid_d4"] = out["covid_border_restrictions"] - out["covid_border_restrictions"].shift(4)
    if "ifrs16" in out:
        out["ifrs16_d4"] = out["ifrs16"] - out["ifrs16"].shift(4)
    return out


def load_long() -> tuple[pd.DataFrame, pd.DataFrame]:
    longs, cats = [], []
    for lf, cf in (("macro_ssb_long.csv", "catalog_ssb.csv"), ("macro_markets_long.csv", "catalog_markets.csv")):
        if (DATA / lf).exists():
            longs.append(pd.read_csv(DATA / lf, dtype={"period": str}))
            cats.append(pd.read_csv(DATA / cf))
    return pd.concat(longs, ignore_index=True), pd.concat(cats, ignore_index=True).drop_duplicates("series_id").set_index("series_id")


def series_from_long(long: pd.DataFrame, sid: str) -> tuple[pd.Series, str]:
    g = long[long["series_id"] == sid]
    if g.empty:
        raise KeyError(sid)
    freq = str(g["freq"].iloc[0]).upper()[0]
    idx = pd.PeriodIndex(g["period"].astype(str), freq=freq)
    s = pd.Series(pd.to_numeric(g["value"], errors="coerce").to_numpy(), index=idx).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index(), freq


def to_quarterly(s: pd.Series) -> pd.Series:
    q = s.groupby(s.index.asfreq("Q")).agg(["mean", "count"])
    return q["mean"][q["count"] == 3]


def month_end(p: pd.Period) -> pd.Timestamp:
    return p.to_timestamp(how="end").normalize()


def realtime_quarterly(series: pd.Series, freq: str, lag_days: float, quarters: pd.PeriodIndex):
    """Return (window mean, same window one year earlier) per origin quarter."""
    cur, prev = [], []
    s = series.sort_index()
    for q in quarters:
        origin = q.to_timestamp(how="end").normalize() + pd.Timedelta(days=ORIGIN_DAYS)
        if freq == "M":
            last_m = pd.Period(q.end_time, freq="M")
            avail = [m for m in s.index if m <= last_m and month_end(m) + pd.Timedelta(days=lag_days) <= origin]
            if not avail:
                cur.append(np.nan); prev.append(np.nan); continue
            m = max(avail)
            v = s.reindex(pd.period_range(m - 2, m, freq="M"))
            vp = s.reindex(pd.period_range(m - 14, m - 12, freq="M"))
            cur.append(v.mean() if v.notna().sum() >= 2 else np.nan)
            prev.append(vp.mean() if vp.notna().sum() >= 2 else np.nan)
        else:
            avail = [p for p in s.index if p <= q and p.to_timestamp(how="end").normalize() + pd.Timedelta(days=lag_days) <= origin]
            if not avail:
                cur.append(np.nan); prev.append(np.nan); continue
            p = max(avail)
            cur.append(s.get(p, np.nan))
            prev.append(s.get(p - 4, np.nan))
    return pd.Series(cur, index=quarters), pd.Series(prev, index=quarters)


def candidate_series(c: dict, long: pd.DataFrame, cat: pd.DataFrame):
    """Return (series, freq, lag_days, source description) for a candidate."""
    def lag_of(sid):
        v = pd.to_numeric(cat.loc[sid].get("typical_release_lag_days", np.nan), errors="coerce") if sid in cat.index else np.nan
        return 0.0 if pd.isna(v) else float(v)

    if "series" in c:
        s, f = series_from_long(long, c["series"])
        return s, f, lag_of(c["series"]), c["series"]
    comps, fn = DERIVED[c["derived"]]
    parts = {sid: series_from_long(long, sid) for sid in comps}
    freqs = {f for _, f in parts.values()}
    if len(freqs) > 1:  # mixed frequencies -> quarterly
        aligned = {sid: (to_quarterly(s) if f == "M" else s) for sid, (s, f) in parts.items()}
        freq = "Q"
    else:
        aligned = {sid: s for sid, (s, _) in parts.items()}
        freq = freqs.pop()
    df = pd.DataFrame(aligned).dropna()
    s = fn({k: df[k] for k in df.columns}).dropna()
    return s, freq, max(lag_of(sid) for sid in comps), " / ".join(comps)


def build_predictors(quarters: pd.PeriodIndex):
    long, cat = load_long()
    feats, rows = {}, []
    for c in CANDIDATES:
        try:
            s, freq, lag, src = candidate_series(c, long, cat)
        except KeyError as e:
            print(f"skip {c['key']}: missing {e}")
            continue
        cur, prev = realtime_quarterly(s, freq, lag, quarters)
        for tf in c["tf"]:
            name = f"{c['key']}__{tf}"
            if tf == "g4":
                feats[name] = 100 * np.log(cur / prev)
                desc = "y/y log growth (%)"
            elif tf == "lvl":
                feats[name] = cur
                desc = "level (quarterly mean)"
            else:
                feats[name] = cur - prev
                desc = "y/y change (pp)"
            rows.append({"feature": name, "concept": c["key"], "label": c["label"], "group": c["group"],
                         "transform": desc, "prior_sales": c["prior"][0], "prior_margin": c["prior"][1],
                         "source_series": src, "freq": freq, "lag_days": lag,
                         "first_obs": str(feats[name].first_valid_index())})
    X = pd.DataFrame(feats, index=quarters)
    return X, pd.DataFrame(rows)


def build_proxy(events: pd.DataFrame) -> pd.DataFrame:
    """25-year proxy target: SSB retail sales in Europris's own category (NACE 47.19)."""
    long, _ = load_long()
    out = {}
    for name, sid in (("px", "ssb_rti_4719_nonspec_nonfood_value_ca"), ("pxvol", "ssb_rti_4719_nonspec_nonfood_volume_ca")):
        s, _ = series_from_long(long, sid)
        qsum = s.groupby(s.index.asfreq("Q")).agg(["sum", "count"])
        qsum = qsum["sum"][qsum["count"] == 3]
        out[f"{name}_yoy"] = 100 * np.log(qsum / qsum.shift(4))
        ltm = qsum.rolling(4).sum()
        out[f"{name}_ltm_yoy"] = 100 * np.log(ltm / ltm.shift(4))
    px = pd.DataFrame(out)
    px.index = pd.PeriodIndex(px.index, freq="Q")
    ev = events.reindex(px.index)
    for c in ev.columns:
        px["ev_" + c] = ev[c]
    return px


def main():
    eu = load_europris()
    eu.reset_index(drop=True).to_csv(DATA / "europris_norway_quarterly.csv", index=False)
    ev = load_events()
    tg = build_targets(eu, ev)
    tg.index.name = "quarter"
    tg.to_csv(DATA / "targets_quarterly.csv")
    quarters = pd.period_range("2000Q1", tg.index.max(), freq="Q")
    X, cat = build_predictors(quarters)
    px = build_proxy(ev)
    px.index.name = "quarter"
    px.to_csv(DATA / "proxy_quarterly.csv")
    X.index.name = "quarter"
    X.to_csv(DATA / "predictors_quarterly.csv")
    cat.to_csv(DATA / "predictor_catalog.csv", index=False)
    print(f"targets: {tg.shape}, predictors: {X.shape}")


if __name__ == "__main__":
    main()
