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

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ORIGIN_DAYS = 45

RATE_HINTS = ("percent", "%", "rate", "per cent", "balance", "net ", "points", "pp", "yield")


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
    return pd.concat(longs, ignore_index=True), pd.concat(cats, ignore_index=True)


def is_rate(row: pd.Series, values: pd.Series) -> bool:
    unit = str(row.get("unit", "")).lower()
    sid = str(row.get("series_id", "")).lower()
    if any(k in unit for k in ("index", "nok", "usd", "eur", "sek", "level", "persons", "number", "million", "price")) \
            and "points" not in unit and "balance" not in unit and "percent" not in unit:
        return False
    if any(k in unit for k in RATE_HINTS) or any(k in sid for k in ("rate", "yield", "nibor", "unemp", "conf", "gscpi", "growth", "saving")):
        return True
    return bool((values <= 0).any())


def month_end(p: pd.Period) -> pd.Timestamp:
    return p.to_timestamp(how="end").normalize()


def realtime_quarterly(series: pd.Series, freq: str, lag_days: float, quarters: pd.PeriodIndex):
    """Return (window_mean, window_mean_one_year_earlier) per origin quarter."""
    cur, prev = [], []
    if freq == "M":
        s = series.sort_index()
        for q in quarters:
            origin = q.to_timestamp(how="end").normalize() + pd.Timedelta(days=ORIGIN_DAYS)
            last_m = pd.Period(q.end_time, freq="M")
            cand = s.index[(s.index <= last_m)]
            avail = [m for m in cand if month_end(m) + pd.Timedelta(days=lag_days) <= origin]
            if not avail:
                cur.append(np.nan); prev.append(np.nan); continue
            m = max(avail)
            win = pd.period_range(m - 2, m, freq="M")
            win_prev = pd.period_range(m - 14, m - 12, freq="M")
            v = s.reindex(win)
            vp = s.reindex(win_prev)
            cur.append(v.mean() if v.notna().sum() >= 2 else np.nan)
            prev.append(vp.mean() if vp.notna().sum() >= 2 else np.nan)
    else:
        s = series.sort_index()
        for q in quarters:
            origin = q.to_timestamp(how="end").normalize() + pd.Timedelta(days=ORIGIN_DAYS)
            avail = [p for p in s.index if p <= q and p.to_timestamp(how="end").normalize() + pd.Timedelta(days=lag_days) <= origin]
            if not avail:
                cur.append(np.nan); prev.append(np.nan); continue
            p = max(avail)
            cur.append(s.get(p, np.nan))
            prev.append(s.get(p - 4, np.nan))
    return pd.Series(cur, index=quarters), pd.Series(prev, index=quarters)


def build_predictors(quarters: pd.PeriodIndex):
    long, cat = load_long()
    cat = cat.drop_duplicates("series_id").set_index("series_id")
    feats, rows = {}, []
    for sid, g in long.groupby("series_id"):
        if sid not in cat.index:
            continue
        info = cat.loc[sid]
        freq = str(g["freq"].iloc[0]).upper()[0]
        vals = pd.to_numeric(g["value"], errors="coerce")
        try:
            if freq == "M":
                idx = pd.PeriodIndex(g["period"].astype(str), freq="M")
            elif freq == "Q":
                idx = pd.PeriodIndex(g["period"].astype(str).str.replace("-Q", "Q"), freq="Q")
            else:
                continue
        except Exception:
            continue
        s = pd.Series(vals.to_numpy(), index=idx).dropna()
        s = s[~s.index.duplicated(keep="last")]
        if len(s) < 12:
            continue
        lag = pd.to_numeric(info.get("typical_release_lag_days", np.nan), errors="coerce")
        lag = 0.0 if pd.isna(lag) else float(lag)
        cur, prev = realtime_quarterly(s, freq, lag, quarters)
        rate = is_rate(info.to_dict() | {"series_id": sid}, s)
        base = {"series_id": sid, "description": info.get("description", ""), "source": info.get("source", ""),
                "freq": freq, "lag_days": lag, "unit": info.get("unit", ""), "sa": info.get("seasonal_adjustment", "")}
        if rate:
            feats[f"{sid}__lvl"] = cur
            rows.append(base | {"feature": f"{sid}__lvl", "transform": "level (3m/qtr mean)"})
            feats[f"{sid}__d4"] = cur - prev
            rows.append(base | {"feature": f"{sid}__d4", "transform": "y/y change (pp)"})
        else:
            if (s <= 0).any():
                continue
            feats[f"{sid}__g4"] = 100 * np.log(cur / prev)
            rows.append(base | {"feature": f"{sid}__g4", "transform": "y/y log growth (%)"})
    X = pd.DataFrame(feats, index=quarters)
    return X, pd.DataFrame(rows)


def main():
    eu = load_europris()
    eu.reset_index(drop=True).to_csv(DATA / "europris_norway_quarterly.csv", index=False)
    ev = load_events()
    tg = build_targets(eu, ev)
    tg.index.name = "quarter"
    tg.to_csv(DATA / "targets_quarterly.csv")
    quarters = pd.period_range("2000Q1", tg.index.max(), freq="Q")
    X, cat = build_predictors(quarters)
    X.index.name = "quarter"
    X.to_csv(DATA / "predictors_quarterly.csv")
    cat.to_csv(DATA / "predictor_catalog.csv", index=False)
    print(f"targets: {tg.shape}, predictors: {X.shape}")


if __name__ == "__main__":
    main()
