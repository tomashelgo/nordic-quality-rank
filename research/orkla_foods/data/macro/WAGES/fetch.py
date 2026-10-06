#!/usr/bin/env python3
"""
Wages, household income and real-wage series for the Orkla Foods predictor analysis
(label macro-WAGES).  Countries: NO, SE (priority), DK, FI, CZ, euro area.

Writes one CSV per series (columns date,value) next to this script plus catalog.csv.
Dates are the first day of the period (monthly YYYY-MM-01, quarterly first month of the
quarter, annual YYYY-01-01).  Native frequency is kept (monthly is NOT aggregated to quarterly
for stored source series); derived real-wage series are quarterly (or annual where only
annual data exist).

Sources / APIs (all public, no key):
  * Statistics Norway (SSB) PxWebApi v0      https://data.ssb.no/api/v0/en/table/<id>
  * Norges Bank SDMX (Regional Network)       https://data.norges-bank.no/api/data/REGNET
  * Norges Bank Expectations Survey xlsx      linked from https://www.norges-bank.no/en/topics/Monetary-policy/expectations-survey/
  * Statistics Sweden (SCB) PxWeb API v1      https://api.scb.se/OV0104/v1/doris/en/ssd/
  * Medlingsinstitutet (MI) PxWeb API         https://www.mi.se/PXWeb/api/v1/sv/Konjunkturlönestatistik/
  * Riksbank inflation & wage expectations survey (Kantar Sifo Prospera to 2024, Origo Group from
    2025) quarterly xls/xlsx tables linked from https://www.origogroup.com/riksbanken/
  * Statistics Denmark                        https://api.statbank.dk/v1/
  * Statistics Finland PxWeb                  https://pxdata.stat.fi/PXWeb/api/v1/en/StatFin/
  * Czech Statistical Office DataStat API     https://data.csu.gov.cz/api/dotaz/v1/data/vybery/<code>
    (fallback: CZSO open-data CSV 110079)
  * ECB Data Portal                           https://data-api.ecb.europa.eu/service/data/
  * Eurostat dissemination API                https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/

Manual / hard-coded input (documented in catalog notes):
  * Norwegian frontfag wage norm ("frontfagsrammen") and outcome: TBU tables (NOU / TBU reports,
    table "Frontfagsrammen") 2014-2023 + press releases (NHO, Norsk Industri, TBU) for 2024-2026.
    regjeringen.no sits behind a Cloudflare challenge (HTTP 403 for scripts), so the values are typed in
    below; update FRONTFAG_* each spring (frame: April of the year; outcome: TBU preliminary report in Feb
    of the following year).

Formulas:
  * quarterly average of a monthly index: mean of the 3 months (quarter kept only if all 3 present)
  * y/y growth (%): 100*(x_t / x_{t-4q} - 1)
  * real wage growth (%): real_yoy = 100*((1+w/100)/(1+p/100)-1), w = nominal wage y/y, p = CPI/HICP y/y
    computed on quarterly averages of the monthly price index (annual: annual-average CPI)
  * expected real wage growth (%): 100*((1+E[w]/100)/(1+E[pi]/100)-1) from the same respondent group

Usage:  python3 fetch.py            (downloads to a temp dir, writes CSVs next to this file)
"""
import datetime as dt
import io
import json
import os
import re
import sys
import tempfile
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import requests

OUT = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="wages_dl_"))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SSB = "https://data.ssb.no/api/v0/en/table/"
SCB = "https://api.scb.se/OV0104/v1/doris/en/ssd/"
MI = "https://www.mi.se/PXWeb/api/v1/sv/Konjunkturlönestatistik/"
DST = "https://api.statbank.dk/v1/"
STATFIN = "https://pxdata.stat.fi/PXWeb/api/v1/en/StatFin/"
ECB = "https://data-api.ecb.europa.eu/service/data/"
ESTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
NB = "https://data.norges-bank.no/api/data/"

SESSION = requests.Session()
SESSION.headers.update(UA)
CATALOG = []
FAILURES = []
STORE = {}          # series_id -> pd.Series (kept for derived calculations)


# =============================================================================================
# helpers
# =============================================================================================
def http(method, url, tries=6, **kw):
    last = None
    for i in range(tries):
        try:
            r = SESSION.request(method, url, timeout=180, **kw)
            if r.status_code in (429, 503):
                time.sleep(15 * (i + 1))
                continue
            if 400 <= r.status_code < 500:   # client error / policy block: do not retry
                raise RuntimeError(f"HTTP {r.status_code} for {url}: {r.text[:200]}")
            r.raise_for_status()
            return r
        except RuntimeError:
            raise
        except Exception as e:  # transient proxy resets
            last = e
            time.sleep(4 * (i + 1))
    raise RuntimeError(f"failed {method} {url}: {last}")


def step(name):
    print(f"[{time.strftime('%H:%M:%S')}] {name}", flush=True)


def parse_period(p):
    """Period strings from SSB/SCB/DST/StatFin/SDMX -> Timestamp (first day of period)."""
    p = str(p).strip()
    for pat, f in [(r"(\d{4})M(\d{2})", lambda y, m: (y, m)),
                   (r"(\d{4})-(\d{2})", lambda y, m: (y, m)),
                   (r"(\d{4})[KQ](\d)", lambda y, q: (y, 3 * q - 2)),
                   (r"(\d{4})-Q(\d)", lambda y, q: (y, 3 * q - 2))]:
        m = re.fullmatch(pat, p)
        if m:
            y, mo = f(int(m.group(1)), int(m.group(2)))
            return pd.Timestamp(y, mo, 1)
    m = re.fullmatch(r"(\d{4})", p)
    if m:
        return pd.Timestamp(int(p), 1, 1)
    raise ValueError(p)


def jsonstat2_long(d):
    """json-stat 2.0 dataset -> long DataFrame with one column per dimension (codes) + value."""
    ids, sizes = d["id"], d["size"]
    cats = []
    for dim in ids:
        idx = d["dimension"][dim]["category"]["index"]
        cats.append(sorted(idx, key=lambda c: idx[c]) if isinstance(idx, dict) else list(idx))
    grid = pd.MultiIndex.from_product(cats, names=ids).to_frame(index=False)
    vals = d["value"]
    if isinstance(vals, dict):
        full = [None] * int(np.prod(sizes))
        for k, v in vals.items():
            full[int(k)] = v
        vals = full
    grid["value"] = pd.to_numeric(pd.Series(vals, dtype="object"), errors="coerce")
    return grid


def ssb(table, selection):
    q = [{"code": k, "selection": {"filter": "item", "values": v}} for k, v in selection.items()]
    r = http("POST", SSB + table, json={"query": q, "response": {"format": "json-stat2"}})
    time.sleep(1.2)  # SSB rate limit ~30 requests/min
    return jsonstat2_long(r.json())


def ssb_series(table, selection, **filt):
    df = ssb(table, selection)
    for k, v in filt.items():
        df = df[df[k] == v]
    return pd.Series(df["value"].values, index=df["Tid"].map(parse_period)).sort_index().dropna()


def scb(table, selection):
    q = {"query": [{"code": k, "selection": {"filter": "item", "values": [v]}} for k, v in selection.items()],
         "response": {"format": "json"}}
    raw = http("POST", SCB + table, json=q).json()
    time.sleep(1.0)
    tcol = [i for i, c in enumerate(raw["columns"]) if c["type"] == "t"][0]
    out = {}
    for d in raw["data"]:
        try:
            out[parse_period(d["key"][tcol])] = float(d["values"][0])
        except ValueError:
            continue
    return pd.Series(out).sort_index()


def pxweb_codes(base, path, selection):
    """Generic PxWeb (v1) query; selection values are codes. Returns long df with value texts."""
    meta = http("GET", base + path).json()
    texts = {v["code"]: dict(zip(v["values"], v["valueTexts"])) for v in meta["variables"]}
    q = [{"code": k, "selection": {"filter": "item", "values": v}} for k, v in selection.items()]
    raw = http("POST", base + path, json={"query": q, "response": {"format": "json"}}).json()
    time.sleep(0.5)
    cols = [c["code"] for c in raw["columns"] if c["type"] != "c"]
    rows = []
    for d in raw["data"]:
        rec = {c: texts.get(c, {}).get(k, k) for c, k in zip(cols, d["key"])}
        try:
            rec["value"] = float(d["values"][0])
        except ValueError:
            rec["value"] = np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def dst(table, variables):
    """Statistics Denmark API: variables {code: [values]} -> long df (codes), BULK csv."""
    body = {"table": table, "format": "BULK", "lang": "en", "valuePresentation": "Code",
            "variables": [{"code": k, "values": v} for k, v in variables.items()]}
    r = http("POST", DST + "data", json=body)
    time.sleep(0.5)
    df = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")), sep=";")
    df["value"] = pd.to_numeric(df["INDHOLD"].astype(str).str.replace(",", "."), errors="coerce")
    return df


def ecb(key):
    r = http("GET", f"{ECB}{key}?format=csvdata&detail=dataonly")
    df = pd.read_csv(io.StringIO(r.text))
    return pd.Series(pd.to_numeric(df["OBS_VALUE"], errors="coerce").values,
                     index=df["TIME_PERIOD"].map(parse_period)).sort_index().dropna()


def estat(dataset, **filters):
    params = [("format", "JSON"), ("lang", "EN")]
    for k, v in filters.items():
        for x in (v if isinstance(v, (list, tuple)) else [v]):
            params.append((k, x))
    r = http("GET", ESTAT + dataset, params=params)
    df = jsonstat2_long(r.json())
    return pd.Series(df["value"].values, index=df["time"].map(parse_period)).sort_index().dropna()


def yoy_splice(new, old, switch="first"):
    """Chain two quarterly NSA indices so that y/y growth is preserved within each source.
    Levels of `old` are kept up to the switch quarter; from then on I_t = I_{t-4} * new_t / new_{t-4}.
    switch='first': first quarter where `new` has a y/y rate (new.start + 1 year);
    switch='last' : quarter after the last observation of `old` (use old as long as it exists).
    This avoids the spurious y/y jumps a single-quarter level splice creates when the two sources have
    different seasonal patterns."""
    new, old = new.dropna().sort_index(), old.dropna().sort_index()
    switch = (new.index.min() + pd.DateOffset(years=1)) if switch == "first" else \
        max(new.index.min() + pd.DateOffset(years=1), old.index.max() + pd.DateOffset(months=3))
    out = old[old.index < switch].to_dict()
    for t in new.index[new.index >= switch]:
        t4 = t - pd.DateOffset(years=1)
        if t4 not in out or t4 not in new.index:
            raise ValueError(f"yoy_splice: missing {t4.date()}")
        out[t] = out[t4] * new[t] / new[t4]
    return pd.Series(out).sort_index()


def rebase(s, year):
    return s / s[s.index.year == year].mean() * 100


def q_avg(m):
    """Monthly -> quarterly average (first month of quarter as date); full quarters only."""
    m = m.dropna()
    qs = m.index.to_period("Q")
    g = m.groupby(qs)
    out = g.mean()[g.count() == 3]
    out.index = out.index.to_timestamp(how="start")
    return out


def a_avg(m, n):
    m = m.dropna()
    g = m.groupby(m.index.year)
    out = g.mean()[g.count() == n]
    out.index = pd.to_datetime([f"{y}-01-01" for y in out.index])
    return out


def yoy(s, periods_per_year):
    """y/y % change using date alignment (robust to gaps)."""
    s = s.dropna()
    prev = s.copy()
    prev.index = prev.index + pd.DateOffset(years=1)
    return (100 * (s / prev.reindex(s.index) - 1)).dropna()


def real_growth(w_yoy, p_yoy):
    j = pd.concat([w_yoy, p_yoy], axis=1, join="inner").dropna()
    return 100 * ((1 + j.iloc[:, 0] / 100) / (1 + j.iloc[:, 1] / 100) - 1)


def save(series_id, s, description, country, frequency, unit, sa, source, query, lag, notes="",
         decimals=6):
    s = pd.Series(s).dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if s.empty:
        FAILURES.append((series_id, "empty series"))
        print(f"  !! {series_id}: empty, not saved")
        return
    STORE[series_id] = s
    df = pd.DataFrame({"date": pd.DatetimeIndex(s.index).strftime("%Y-%m-%d"),
                       "value": np.round(s.values.astype(float), decimals)})
    fn = f"{series_id}.csv"
    df.to_csv(OUT / fn, index=False)
    CATALOG.append(dict(series_id=series_id, file=fn, description=description, country=country,
                        frequency=frequency, unit=unit, seasonal_adjustment=sa,
                        start=df["date"].iloc[0], end=df["date"].iloc[-1], n_obs=len(df),
                        source=source, source_query=query, approx_release_lag_days=lag, notes=notes))
    print(f"  saved {series_id:42s} {df['date'].iloc[0]} .. {df['date'].iloc[-1]}  n={len(df)}")


def section(fn):
    def run():
        try:
            fn()
        except Exception as e:
            traceback.print_exc()
            FAILURES.append((fn.__name__, repr(e)[:300]))
    return run


# =============================================================================================
# 1. Consumer prices used as deflators
# =============================================================================================
@section
def prices():
    step("CPI / HICP deflators")
    s = ssb_series("14710", {"ContentsCode": ["KpiIndMnd"]})
    save("no_cpi_idx", s, "Norway CPI all items, monthly index", "NO", "M", "index 2025=100", "NSA",
         "SSB table 14710", "14710 ContentsCode=KpiIndMnd", 10,
         "Deflator for Norwegian real wages (quarterly average of monthly index). Same as NO/no_cpi_total_idx.")
    sa = a_avg(s, 12)
    save("no_cpi_annual_idx", sa, "Norway CPI all items, annual average", "NO", "A", "index 2025=100", "NSA",
         "SSB table 14710 (annual mean of monthly index, computed)", "14710 KpiIndMnd, mean of 12 months", 10,
         "Annual-average CPI used to deflate the TBU annual wage growth.")

    s = scb("PR/PR0101/PR0101A/KPI2020COICOP2M", {"VaruTjanstegrupp": "00", "ContentsCode": "0000080C"})
    save("se_cpi_idx", s, "Sweden CPI (KPI) all items, monthly index", "SE", "M", "index 2020=100", "NSA",
         "SCB PR0101A", "PR/PR0101/PR0101A/KPI2020COICOP2M VaruTjanstegrupp=00 ContentsCode=0000080C", 13,
         "Headline CPI incl. mortgage interest costs; deflator for Swedish real wages (MI also reports KPIF-based real wages).")
    s = scb("PR/PR0101/PR0101G/KPIF2020", {"ContentsCode": "000007ZN"})
    save("se_cpif_idx", s, "Sweden CPIF (CPI with fixed interest rate), monthly index", "SE", "M", "index 2020=100",
         "NSA", "SCB PR0101G", "PR/PR0101/PR0101G/KPIF2020 ContentsCode=000007ZN", 13,
         "Alternative deflator (Riksbank target variable).")

    for geo, sid, name in [("DK", "dk_hicp_idx", "Denmark"), ("FI", "fi_hicp_idx", "Finland"),
                           ("CZ", "cz_hicp_idx", "Czechia"), ("EA", "ea_hicp_idx", "Euro area (changing composition)")]:
        s = estat("prc_hicp_minr", geo=geo, coicop18="TOTAL", unit="I25", freq="M")
        save(sid, s, f"{name} HICP all items, monthly index", geo if geo != "EA" else "EA", "M", "index 2025=100",
             "NSA", "Eurostat prc_hicp_minr", f"prc_hicp_minr M.I25.TOTAL.{geo}", 17,
             "HICP on ECOICOP ver.2 (back-calculated by Eurostat); deflator for real wages. "
             + ("Euro area changing composition (matches ECB negotiated-wage aggregate U2)." if geo == "EA" else ""))


# =============================================================================================
# 2. Norway: wages
# =============================================================================================
FRONTFAG_FRAME = {  # NHO estimate (in agreement with LO) of annual wage growth in NHO manufacturing
    2014: 3.3, 2015: 2.7, 2016: 2.4, 2017: 2.4, 2018: 2.8, 2019: 3.2, 2020: 1.7, 2021: 2.7, 2022: 3.7,
    2023: 5.2, 2024: 5.2, 2025: 4.4, 2026: 4.4}
FRONTFAG_OUTCOME = {  # TBU: annual wage growth, NHO manufacturing in total (latest two years preliminary)
    2014: 3.3, 2015: 2.5, 2016: 1.9, 2017: 2.4, 2018: 2.6, 2019: 3.1, 2020: 2.2, 2021: 3.1, 2022: 4.0,
    2023: 4.8, 2024: 5.3, 2025: 5.1}


@section
def norway_wages():
    step("Norway wages")
    # --- quarterly national accounts: wages and salaries per FTE employee
    df = ssb("09175", {"NACE": ["nr23_6", "nr23_6fn", "pub2X10_12"],
                       "ContentsCode": ["Lonn", "SysselsatteNormL"]})
    df["date"] = df["Tid"].map(parse_period)
    p = df.pivot_table(index=["NACE", "date"], columns="ContentsCode", values="value")
    for nace, sid, desc in [("nr23_6", "no_qna_wage_per_fte_q", "total economy"),
                            ("pub2X10_12", "no_qna_wage_per_fte_food_q", "manufacture of food products, beverages and tobacco")]:
        x = p.loc[nace]
        s = x["Lonn"] / x["SysselsatteNormL"]   # NOK million / 1000 FTE = NOK thousand per FTE per quarter
        save(sid, s, f"Norway QNA wages and salaries per full-time equivalent employee, {desc}", "NO", "Q",
             "NOK thousand per FTE per quarter", "NSA", "SSB table 09175 (computed ratio)",
             f"09175 NACE={nace}: Lonn / SysselsatteNormL", 55,
             "Computed: wages and salaries (NOK mn, unadjusted) / full-time-equivalent employees (1000). "
             "Strong seasonality (holiday pay in Q2) -> use y/y changes. Longest quarterly total-economy wage "
             "measure for Norway (1995-). Revised with each QNA release.")

    # --- a-ordningen based quarterly earnings (2016-)
    df = ssb("11654", {"Region": ["Ialt"], "NACE2007": ["00-99"], "ContentsCode": ["GjMdTotal"]})
    s = pd.Series(df["value"].values, index=df["Tid"].map(parse_period)).dropna()
    save("no_avg_monthly_earnings_q", s, "Norway average monthly earnings, all employees, all industries (a-ordningen)",
         "NO", "Q", "NOK per month", "NSA", "SSB table 11654",
         "11654 Region=Ialt NACE2007=00-99 ContentsCode=GjMdTotal", 45,
         "Average monthly earnings (agreed pay + irregular supplements + bonuses) per FTE, quarterly from the "
         "a-ordningen register (2016Q1-). SSB's 'Index of average monthly earnings' (GjMdTotalIndeks) is the same "
         "data indexed. No official all-industry quarterly series before 2016 (use no_qna_wage_per_fte_q). "
         "Annual monthly-earnings statistics (table 11418, Sept/Oct) not stored separately.")

    # --- manufacturing and food manufacturing quarterly earnings index, spliced 1998-
    new = ssb("11654", {"Region": ["Ialt"], "NACE2007": ["10-33"], "ContentsCode": ["GjMdTotal"]})
    new = pd.Series(new["value"].values, index=new["Tid"].map(parse_period)).dropna()
    mid = ssb_series("07235", {"NACE2007": ["10-33"], "ContentsCode": ["Indeks"]})
    old = ssb_series("06787", {"Naring": ["nr23ind"], "ContentsCode": ["Indeks"]})
    s = rebase(yoy_splice(new, yoy_splice(mid, old)), 2015)
    save("no_earn_idx_manuf_q", s, "Norway index of average monthly earnings, manufacturing (spliced)", "NO", "Q",
         "index 2015=100", "NSA", "SSB tables 11654 (y/y from 2017Q1), 07235 (2006Q1-2016Q4), 06787 (1998Q1-2005Q4)",
         "11654 NACE2007=10-33 GjMdTotal; 07235 NACE2007=10-33 Indeks; 06787 Naring=nr23ind Indeks", 45,
         "y/y-preserving chain (see yoy_splice in fetch.py): y/y growth equals 06787 (SIC2002) through 2005, "
         "07235 (survey-based quarterly wage statistics, SIC2007) 2006-2016, a-ordningen register (11654) from 2017. "
         "Levels before the switch keep the old seasonal pattern; use y/y changes.")

    f = ssb("12314", {"NACE2007": ["10", "11"], "ContentsCode": ["GjMdTotal", "HeltidsEkvMnd"]})
    f["date"] = f["Tid"].map(parse_period)
    pv = f.pivot_table(index="date", columns=["NACE2007", "ContentsCode"], values="value")
    w = (pv[("10", "GjMdTotal")] * pv[("10", "HeltidsEkvMnd")] + pv[("11", "GjMdTotal")] * pv[("11", "HeltidsEkvMnd")]) \
        / (pv[("10", "HeltidsEkvMnd")] + pv[("11", "HeltidsEkvMnd")])
    w = w.dropna()
    mid = ssb_series("07235", {"NACE2007": ["10-12"], "ContentsCode": ["Indeks"]})
    old = ssb_series("06787", {"Naring": ["nr23naerm"], "ContentsCode": ["Indeks"]})
    s = rebase(yoy_splice(w, yoy_splice(mid, old)), 2015)
    save("no_earn_idx_food_manuf_q", s, "Norway index of average monthly earnings, manufacture of food products and beverages (spliced)",
         "NO", "Q", "index 2015=100", "NSA", "SSB tables 12314 (y/y from 2017Q1), 07235 (2006Q1-2016Q4), 06787 (1998Q1-2005Q4)",
         "12314 NACE2007=10,11 GjMdTotal weighted by HeltidsEkvMnd; 07235 NACE2007=10-12 Indeks; 06787 Naring=nr23naerm Indeks", 45,
         "From 2016: FTE-weighted average monthly earnings of SIC 10 (food) and 11 (beverages) from a-ordningen; before: "
         "survey-based index for food, beverages and tobacco (10-12). y/y-preserving chain (switches 2006Q1 and 2017Q1). "
         "Direct labour-cost proxy for Orkla's Norwegian operations.")

    # --- TBU annual wage growth (all employees) and annual earnings
    df = ssb("14858", {"ContentsCode": ["Arslonn", "ArslonnEndring", "ReallonnEndring"]})
    df["date"] = df["Tid"].map(parse_period)
    p = df.pivot_table(index="date", columns="ContentsCode", values="value")
    save("no_tbu_wage_growth_a", p["ArslonnEndring"], "Norway annual wage growth, average for all employees (TBU årslønnsvekst)",
         "NO", "A", "% change y/y", "NSA", "SSB table 14858 (TBU figures)", "14858 ContentsCode=ArslonnEndring", 45,
         "Growth rate as published (årslønnsvekst, the TBU measure used in wage settlements). Preliminary figure "
         "for year t appears in TBU's February report of year t+1; SSB table updated later. 1971-.")
    save("no_annual_earnings_a", p["Arslonn"], "Norway average annual earnings, all employees (TBU basis)", "NO", "A",
         "NOK per year", "NSA", "SSB table 14858", "14858 ContentsCode=Arslonn", 45,
         "Level series underlying no_tbu_wage_growth_a (1970-).")
    STORE["_no_ssb_real_official"] = p["ReallonnEndring"].dropna()

    # --- frontfag norm (manual)
    fr = pd.Series({pd.Timestamp(y, 1, 1): v for y, v in FRONTFAG_FRAME.items()})
    save("no_frontfag_frame_a", fr, "Norway frontfag wage norm: estimated annual wage growth in NHO manufacturing agreed at the settlement (frontfagsrammen)",
         "NO", "A", "% change y/y (frame)", "NSA",
         "TBU (NOU 2023:12 / TBU Feb-2024 report, table 1.3 'Frontfagsrammen'); NHO / Norsk Industri press releases 2024-2026",
         "manual (hard-coded in fetch.py FRONTFAG_FRAME)", -260,
         "Known in March/April of the year it applies to (forward-looking wage norm; hence negative lag vs year end). "
         "Explicit frame published since Holden III (NOU 2013:13); 2014-2023 from TBU table, 2024 5.2 (hovedoppgjør), "
         "2025 4.4 (mellomoppgjør), 2026 4.4 (hovedoppgjør, agreed 12 Apr 2026).")
    oc = pd.Series({pd.Timestamp(y, 1, 1): v for y, v in FRONTFAG_OUTCOME.items()})
    save("no_frontfag_outcome_a", oc, "Norway frontfag outcome: annual wage growth in NHO manufacturing in total (TBU)",
         "NO", "A", "% change y/y", "NSA",
         "TBU (table 'Frontfagsrammen', Resultat) 2014-2023; TBU press releases Feb-2025 (2024: 5.3) and Feb-2026 (2025: 5.1)",
         "manual (hard-coded in fetch.py FRONTFAG_OUTCOME)", 45,
         "2024 and 2025 are TBU preliminary figures. Outcome minus frame = wage drift surprise.")


# =============================================================================================
# 3. Norway: expectations (Norges Bank Expectations Survey, Regional Network)
# =============================================================================================
def nb_expectations_xlsx():
    page = http("GET", "https://www.norges-bank.no/en/topics/Monetary-policy/expectations-survey/").text
    m = re.search(r'href="(/contentassets/[^"]+?expectations_survey_[^"]+?\.xlsx[^"]*)"', page)
    if not m:
        raise RuntimeError("expectations survey xlsx link not found")
    url = "https://www.norges-bank.no" + m.group(1).replace("&amp;", "&")
    fn = TMP / "nb_expectations.xlsx"
    fn.write_bytes(http("GET", url).content)
    return fn, url


def nb_sheet_series(fn, sheet, col_matcher):
    """Return series from Norges Bank expectations workbook: column found by header predicate."""
    raw = pd.read_excel(fn, sheet_name=sheet, header=None)
    hdr = raw.iloc[:5].ffill(axis=1)  # forward fill group labels across merged cells
    col = None
    for j in range(1, raw.shape[1]):
        h = [str(hdr.iat[k, j]) if pd.notna(hdr.iat[k, j]) else "" for k in range(5)]
        h = [re.sub(r"\s+", " ", x).strip() for x in h]
        if col_matcher(h, raw.iloc[:5, j].tolist()):
            col = j
            break
    if col is None:
        raise RuntimeError(f"column not found in {sheet}")
    out = {}
    for _, r in raw.iloc[5:].iterrows():
        lab = r.iloc[0]
        if not isinstance(lab, str):
            continue
        mm = re.match(r"\s*(\d)\.\s*q\.\s*(\d{4})", lab)
        if mm and pd.notna(r.iloc[col]):
            out[pd.Timestamp(int(mm.group(2)), 3 * int(mm.group(1)) - 2, 1)] = float(r.iloc[col])
    return pd.Series(out).sort_index()


def _avg_col(block, group, question_kw=None):
    """predicate factory: header row 0 block title, row1 respondent group, avg column."""
    def f(h, rawcol):
        if block.lower() not in h[0].lower():
            return False
        # group label is in row 1 (HOUSEHOLDS / SOCIAL PARTNERS / ECONOMISTS / BUSINESS LEADERS) and
        # the subgroup (e.g. 'Social partners', 'Economists', 'Business leaders') in row 3; 'Average' in row 4
        if group[0].lower() not in h[1].lower():
            return False
        sub = str(rawcol[3]) if pd.notna(rawcol[3]) else ""
        sub = re.sub(r"\s+", " ", sub).strip()
        if group[1] and sub.lower() != group[1].lower():
            return False
        avg = str(rawcol[4]) if pd.notna(rawcol[4]) else ""
        return "average" in avg.lower()
    return f


@section
def norway_expectations():
    step("Norway expectations (Norges Bank)")
    fn, url = nb_expectations_xlsx()
    src = "Norges Bank Expectations Survey (conducted by Ipsos, earlier Epinion/Opinion/TNS Gallup)"
    specs = [
        ("no_exp_wage_cy_econ", "ANNUAL WAGE GROWTH", "ANNUAL WAGE GROWTH THIS YEAR", ("ECONOMISTS", "Economists"),
         "Norway expected annual wage growth this year, economists (financial industry + academia), mean"),
        ("no_exp_wage_cy_social", "ANNUAL WAGE GROWTH", "ANNUAL WAGE GROWTH THIS YEAR", ("SOCIAL PARTNERS", "Social partners"),
         "Norway expected annual wage growth this year, social partners (employer + employee organisations), mean"),
        ("no_exp_wage_cy_business", "ANNUAL WAGE GROWTH", "ANNUAL WAGE GROWTH THIS YEAR", ("BUSINESS LEADERS", "Business leaders"),
         "Norway expected annual wage growth this year, business leaders, mean"),
        ("no_exp_infl_12m_econ", "INFLATION", "INFLATION NEXT 12 MONTHS", ("ECONOMISTS", "Economists"),
         "Norway expected CPI inflation 12 months ahead, economists, mean"),
        ("no_exp_infl_12m_social", "INFLATION", "INFLATION NEXT 12 MONTHS", ("SOCIAL PARTNERS", "Social partners"),
         "Norway expected CPI inflation 12 months ahead, social partners, mean"),
        ("no_exp_infl_12m_business", "INFLATION", "INFLATION NEXT 12 MONTHS", ("BUSINESS LEADERS", "Business leaders"),
         "Norway expected CPI inflation 12 months ahead, business leaders, mean"),
        ("no_exp_real_wage_cy_econ", "INFLATION TARGET AND REAL WAGES", "REAL WAGE INCREASE THIS YEAR", ("ECONOMISTS", "Economists"),
         "Norway expected real wage growth this year, economists, mean (direct question)"),
    ]
    for sid, sheet, block, group, desc in specs:
        s = nb_sheet_series(fn, sheet, _avg_col(block, group))
        note = ("Quarterly survey, fieldwork in the first half of the 2nd month of the quarter, published mid-quarter "
                "(before quarter end). Date = survey quarter. ")
        if "infl_12m_business" in sid:
            note += "Same data as SURVEYS/no_nbes_bl_infl_exp_12m. "
        if "real_wage" in sid:
            note += "Question asked since 2023Q1 only."
        save(sid, s, desc, "NO", "Q", "% (expected growth)", "NSA", src,
             f"{url.split('?')[0]} sheet '{sheet}', block '{block}', group '{group[1]}', Average", -45, note)

    # Regional Network: expected annual wage growth, all sectors (current year), 2005-
    r = http("GET", NB + "REGNET/Q.ARSLONN.AGG._X.CURRY?format=csv&locale=en")
    d = pd.read_csv(io.StringIO(r.text), sep=";")
    s = pd.Series(pd.to_numeric(d["OBS_VALUE"]).values, index=d["TIME_PERIOD"].map(parse_period)).sort_index()
    save("no_regnet_exp_wage_cy", s, "Norway Regional Network: contacts' expected annual wage growth this year, all sectors",
         "NO", "Q", "% (expected growth)", "NSA", "Norges Bank Regional Network (SDMX flow REGNET)",
         "data.norges-bank.no/api/data/REGNET/Q.ARSLONN.AGG._X.CURRY", -20,
         "Survey round = quarter (published in the last month of the quarter, before quarter end). Next-year "
         "expectation (HORIZON=N1Y) available only from 2022Q4, not stored.")


# =============================================================================================
# 4. Norway: household real disposable income
# =============================================================================================
@section
def norway_hh_income():
    step("Norway household disposable income")
    df = ssb("11020", {"Sektor": ["h140000"], "Transaksjoner": ["I3491FP_H", "I3491_H", "I3491UAB_H"],
                       "ContentsCode": ["LPriserS", "LPriser"]})
    df["date"] = df["Tid"].map(parse_period)
    p = df.pivot_table(index="date", columns=["Transaksjoner", "ContentsCode"], values="value")
    s = p[("I3491FP_H", "LPriserS")]
    save("no_hh_real_disp_inc_sa_q", s, "Norway households' disposable income in constant 2015 prices, seasonally adjusted",
         "NO", "Q", "NOK million, 2015 prices", "SA", "SSB table 11020 (quarterly non-financial sector accounts)",
         "11020 Sektor=h140000 Transaksjoner=I3491FP_H ContentsCode=LPriserS", 70,
         "Sector h140000 = households (excl. NPISH). Includes dividend income, which is very volatile "
         "around tax changes (2005-06, 2016) - see no_hh_real_disp_inc_xdiv_sa_q. 1999Q1-.")
    defl = p[("I3491_H", "LPriserS")] / p[("I3491FP_H", "LPriserS")]
    s2 = (p[("I3491UAB_H", "LPriserS")] / defl).dropna()
    save("no_hh_real_disp_inc_xdiv_sa_q", s2, "Norway households' real disposable income excluding dividends, seasonally adjusted (computed)",
         "NO", "Q", "NOK million, 2015 prices", "SA", "SSB table 11020 (computed)",
         "11020 h140000: I3491UAB_H(LPriserS) / [I3491_H(LPriserS)/I3491FP_H(LPriserS)]", 70,
         "Nominal disposable income excl. dividends deflated with the implicit deflator of total disposable income "
         "(= household consumption deflator used by SSB). Preferred real income measure for Norway.")


# =============================================================================================
# 5. Sweden: wages (MI / SCB) and household income
# =============================================================================================
@section
def sweden():
    step("Sweden wages (Medlingsinstitutet) and household income (SCB)")
    path = "Löneutveckling efter sektor/Loner_efter_sektor_manadsdata.px"
    meta = http("GET", MI + path).json()
    per_codes = [v for v in meta["variables"] if v["code"] == "Period"][0]["values"]
    df = pxweb_codes(MI, path, {"Sektor": ["0"], "Variabel": ["1", "2"], "Period": per_codes})
    for var, sid, desc, note in [
        ("Utgående lön, definitiva och preliminära värden", "se_wage_yoy_m",
         "Sweden wage growth, whole economy (short-term wage statistics / Konjunkturlönestatistik), outcome incl. preliminary values",
         "Annual % change of average monthly wage (utgående lön), whole economy. Latest ~12 months are preliminary and "
         "are typically revised UP as retroactive pay is booked after new agreements (MI also publishes 'skattade' "
         "estimates of final values, not stored). Published ~2 months after the reference month."),
        ("Centralt avtalad lön", "se_wage_central_agreed_yoy_m",
         "Sweden centrally agreed wage increases, whole economy (Medlingsinstitutet)",
         "Annual % change of centrally agreed wages (the 'märket'-driven component); Swedish analogue of a wage norm.")]:
        x = df[(df["Sektor"] == "Hela ekonomin") & (df["Variabel"] == var)]
        s = pd.Series(x["value"].values, index=x["Period"].map(parse_period)).sort_index().dropna()
        save(sid, s, desc, "SE", "M", "% change y/y", "NSA", "Medlingsinstitutet PxWeb (Konjunkturlönestatistik)",
             f"{path} Sektor=Hela ekonomin Variabel={var}", 60, note)

    path = "Reallöneutveckling/Realloner_manadsdata.px"
    meta = http("GET", MI + path).json()
    per_codes = [v for v in meta["variables"] if v["code"] == "Period"][0]["values"]
    df = pxweb_codes(MI, path, {"Variabel": ["0"], "Typ av data": ["1"], "Period": per_codes})
    s = pd.Series(df["value"].values, index=df["Period"].map(parse_period)).sort_index().dropna()
    save("se_wage_idx_m", s, "Sweden nominal wage index, whole economy (Konjunkturlönestatistik), monthly", "SE", "M",
         "index 1995=100", "NSA", "Medlingsinstitutet PxWeb (Reallöneutveckling)",
         f"{path} Variabel=Nominell lön, Typ av data=Index(1995=100), ej säsongrensad", 60,
         "Chain index of average wages incl. preliminary months (revised up later). Basis for se_real_wage_yoy_q.")

    path = "Reallöneutveckling/Realloner_arsdata.px"
    meta = http("GET", MI + path).json()
    per_codes = [v for v in meta["variables"] if v["code"] == "Period"][0]["values"]
    df = pxweb_codes(MI, path, {"Variabel": ["0", "3"], "Typ av data": ["0"], "Period": per_codes})
    for var, sid, desc in [("Nominell lön", "se_wage_growth_a", "Sweden annual nominal wage growth, whole economy (MI, 1960-)"),
                           ("Reallön (KPI)", "se_real_wage_growth_a", "Sweden annual real wage growth deflated by CPI (KPI), whole economy (MI, 1960-)")]:
        x = df[df["Variabel"] == var]
        s = pd.Series(x["value"].values, index=x["Period"].map(parse_period)).sort_index().dropna()
        save(sid, s, desc, "SE", "A", "% change y/y", "NSA", "Medlingsinstitutet PxWeb (Reallöneutveckling, årsdata)",
             f"{path} Variabel={var} Typ av data=Årlig procentuell förändring", 60,
             "Long annual history (Konjunkturlönestatistik from 1992, earlier years from MI/SCB historical series). "
             + ("Official MI real wage = (1+w)/(1+KPI)-1." if "real" in sid else ""))

    # household real disposable income (S14+S15), quarterly 1980-
    s = scb("NR/NR0103/NR0103C/HusDispInkENS2010Kv", {"Transaktionspost": "B6real", "ContentsCode": "NR0103DQ"})
    save("se_hh_real_disp_inc_q", s, "Sweden households' (incl. NPISH) net disposable income, real values", "SE", "Q",
         "SEK million, real (fixed prices, SCB reference year)", "NSA", "SCB NR0103C (sector accounts, quarterly)",
         "NR/NR0103/NR0103C/HusDispInkENS2010Kv Transaktionspost=B6real ContentsCode=NR0103DQ", 85,
         "Unadjusted -> use y/y. SCB key indicator table SektorENS2010KvKeyIn also publishes the real growth rate "
         "(B6nRealGrowth).")


# =============================================================================================
# 6. Sweden: Prospera / Origo expectations survey (quarterly labour-market-party wage expectations)
# =============================================================================================
def _first_text(row):
    for c in row:
        if isinstance(c, str) and c.strip():
            return c.strip()
    return None


def _first_num(row):
    seen_label = False
    for c in row:
        if isinstance(c, str) and c.strip():
            seen_label = True
            continue
        if seen_label and isinstance(c, (int, float)) and not isinstance(c, bool) and not pd.isna(c):
            return float(c)
    return None


MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul",
                                      "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_prospera(path):
    """Return (quarter_start Timestamp, survey label, {(measure, group, horizon): mean}) or None."""
    try:
        xl = pd.read_excel(path, sheet_name=None, header=None,
                           engine="xlrd" if str(path).endswith(".xls") else "openpyxl")
    except Exception:
        return None
    rows = []
    for _, df in xl.items():
        for r in df.itertuples(index=False):
            rows.append(list(r))
    if not rows:
        return None
    title = None
    for r in rows[:6]:
        t = _first_text(r)
        if t and re.search(r"\d{4}|/\d{2}", t):
            title = t
            break
    if title is None:
        return None
    # survey quarter: 'n/YY' round number (2005-2009) or month name (2009-)
    m = re.match(r"\s*(\d)/(\d{2})", title)
    if m:
        q, y = int(m.group(1)), 2000 + int(m.group(2))
    else:
        m = re.match(r"\s*([A-Za-z]+)\s+(\d{4})", title)
        if not m or m.group(1).lower()[:3] not in MONTHS:
            return None
        y, q = int(m.group(2)), (MONTHS[m.group(1).lower()[:3]] - 1) // 3 + 1
    date = pd.Timestamp(y, 3 * q - 2, 1)
    measure, group, vals = None, None, {}
    for r in rows:
        t = _first_text(r)
        if not t:
            continue
        tl = t.lower()
        if tl.startswith("table") or tl.startswith("expected"):
            if "wage" in tl:
                measure = "wage"
            elif "interval" in tl or "probability" in tl:
                measure = None
            elif "cpif" in tl:
                measure = "cpif"
            elif "cpi" in tl or "inflation" in tl:
                measure = "cpi" if (tl.startswith("expected") or measure not in ("cpi", "cpif")) else measure
            elif "gdp" in tl or "repo" in tl or "policy" in tl or "bond" in tl or "confidence" in tl:
                measure = None
            continue
        if re.fullmatch(r"(?i)all( interviewees)?", t):
            group = "all"
            continue
        if re.match(r"(?i)employee", t):
            group = "employees"
            continue
        if re.match(r"(?i)employer", t):
            group = "employers"
            continue
        if re.match(r"(?i)purchas", t) or re.match(r"(?i)money market", t):
            group = "other"
            continue
        mm = re.fullmatch(r"(?i)(inflation |wage increase )?year (\d)", t)
        if mm and measure is not None and group is not None:
            meas = measure
            if mm.group(1):
                meas = "cpi" if mm.group(1).lower().startswith("inflation") else "wage"
            v = _first_num(r)
            if v is not None:
                vals.setdefault((meas, group, int(mm.group(2))), v)
    if not any(k[0] == "wage" for k in vals):
        return None
    return date, title, vals


@section
def sweden_expectations():
    step("Sweden Prospera/Origo expectations (quarterly survey)")
    page = http("GET", "https://www.origogroup.com/riksbanken/").text
    links = sorted(set(re.findall(r'href="(https://www\.origogroup\.com/wp-content/uploads/[^"]+?\.xlsx?)"', page)))
    # optional cache of previously downloaded spreadsheets (env WAGES_PROSPERA_CACHE), else temp dir
    ddir = Path(os.environ.get("WAGES_PROSPERA_CACHE", TMP / "prospera"))
    ddir.mkdir(parents=True, exist_ok=True)
    recs = {}
    for u in links:
        fn = ddir / re.sub(r"[^A-Za-z0-9._-]", "_", u.split("/uploads/")[1])
        if not fn.exists():
            try:
                fn.write_bytes(http("GET", u, tries=3).content)
            except Exception as e:
                print("   skip", u, e)
                continue
        res = parse_prospera(fn)
        if res:
            date, title, vals = res
            recs[date] = vals  # later file for the same quarter overwrites (should not happen)
    print(f"   parsed {len(recs)} quarterly surveys with wage expectations")
    df = pd.DataFrame(recs).T.sort_index()

    def col(meas, grp, h):
        return df[(meas, grp, h)] if (meas, grp, h) in df.columns else pd.Series(dtype=float)

    lmp_w = (col("wage", "employees", 1) + col("wage", "employers", 1)) / 2
    lmp_p = (col("cpi", "employees", 1) + col("cpi", "employers", 1)) / 2
    src = "Riksbank survey of inflation & wage expectations (Kantar Sifo Prospera to 2024, Origo Group from 2025)"
    q = "origogroup.com/riksbanken quarterly tables: 'Wage Increase Expectations' / 'Inflation Expectations' (CPI), Year 1 mean"
    note0 = ("Quarterly survey (Mar/Jun/Sep/Dec; 2005-2009 rounds 1-4 dated by round number), published before quarter "
             "end. Parsed from the per-survey spreadsheets (2005Q4-). ")
    save("se_exp_wage_1y_lmp", lmp_w.dropna(), "Sweden expected wage increase coming 12 months, labour market parties (avg of employee and employer organisations), mean",
         "SE", "Q", "% (expected growth)", "NSA", src, q, -15, note0 + "Simple average of the two organisation-group means.")
    save("se_exp_wage_1y_all", col("wage", "all", 1).dropna(), "Sweden expected wage increase coming 12 months, all interviewees (labour market parties + purchasing managers), mean",
         "SE", "Q", "% (expected growth)", "NSA", src, q, -15, note0 + "Money market players are not asked about wages.")
    save("se_exp_cpi_1y_lmp", lmp_p.dropna(), "Sweden expected CPI inflation coming 12 months, labour market parties (avg of employee and employer organisations), mean",
         "SE", "Q", "% (expected inflation)", "NSA", src, q, -15, note0)
    save("se_exp_cpi_1y_all", col("cpi", "all", 1).dropna(), "Sweden expected CPI inflation coming 12 months, all interviewees, mean (quarterly survey)",
         "SE", "Q", "% (expected inflation)", "NSA", src, q, -15,
         note0 + "Monthly money-market-player surveys are not included here (quarterly rounds only).")


# =============================================================================================
# 7. Denmark
# =============================================================================================
@section
def denmark():
    step("Denmark wages and household income")
    d = dst("SBLON1", {"BRANCHE07": ["TOT", "CA"], "SEKTOR": ["1000", "1046"], "VARIA1": ["100"], "Tid": ["*"]})
    d["date"] = d["TID"].map(parse_period)
    tot = d[(d.BRANCHE07 == "TOT") & (d.SEKTOR == 1000)].set_index("date")["value"].sort_index().dropna()
    save("dk_wage_idx_total_q", tot, "Denmark standardised index of average earnings, all sectors, all industries", "DK", "Q",
         "index (DST base)", "NSA", "Statistics Denmark SBLON1", "SBLON1 BRANCHE07=TOT SEKTOR=1000 VARIA1=100", 75,
         "Standardised (composition-adjusted) earnings index incl. irregular payments, 2016Q1-. For longer history see "
         "dk_wage_idx_private_q.")

    def private_chain(branch_new, branch_ilon12, branch_old):
        new = d[(d.BRANCHE07 == branch_new) & (d.SEKTOR == 1046)].set_index("date")["value"].sort_index().dropna()
        m = dst("ILON12", {"ERHVERV": [branch_ilon12], "SÆSON": ["EJSÆSON"], "Tid": ["*"]})
        mid = pd.Series(m["value"].values, index=m["TID"].map(parse_period)).sort_index().dropna()
        o = dst("ILON2X", {"ERHVERV": [branch_old], "Tid": ["*"]})
        old = pd.Series(o["value"].values, index=o["TID"].map(parse_period)).sort_index().dropna()
        return rebase(yoy_splice(new, yoy_splice(mid, old), switch="last"), 2015)

    s = private_chain("TOT", "TOT", "TOT")
    save("dk_wage_idx_private_q", s, "Denmark index of average earnings, corporations and organisations (private sector), spliced",
         "DK", "Q", "index 2015=100", "NSA", "Statistics Denmark ILON12 (2006Q1 to its last quarter, 2025Q4), SBLON1 (after), ILON2X (1994Q1-2005Q4)",
         "SBLON1 BRANCHE07=TOT SEKTOR=1046; ILON12 ERHVERV=TOT EJSÆSON; ILON2X ERHVERV=TOT", 75,
         "y/y-preserving chain: implicit wage index ILON2X to 2005, ILON12 from 2006Q1 as long as it is published "
         "(currently to 2025Q4), then y/y of the standardised earnings index SBLON1 (the new headline, 2016Q1-). ILON is "
         "preferred while available because SBLON y/y is noisier at industry level. Private sector only.")
    s = private_chain("CA", "CA", "1509")
    save("dk_wage_idx_food_manuf_q", s, "Denmark index of average earnings, manufacture of food, beverages and tobacco (private), spliced",
         "DK", "Q", "index 2015=100", "NSA", "Statistics Denmark ILON12 (2006Q1-last), SBLON1 (after), ILON2X (1996Q1-2005Q4)",
         "SBLON1 BRANCHE07=CA SEKTOR=1046; ILON12 ERHVERV=CA EJSÆSON; ILON2X ERHVERV=1509", 75,
         "y/y-preserving chain as dk_wage_idx_private_q (ILON2X 1509 to 2005, ILON12 CA 2006Q1-2025Q4, SBLON1 CA after); "
         "DB07 CA = food, beverages, tobacco; DB03 1509 before 2005. SBLON1 CA y/y is volatile (e.g. 7.1% in 2017Q1).")

    n = dst("NKN3", {"TRANSAKT": ["B6G"], "PRISENHED": ["RKV_M"], "Tid": ["*"]})
    s = pd.Series(n["value"].values, index=n["TID"].map(parse_period)).sort_index().dropna()
    save("dk_hh_real_disp_inc_sa_q", s, "Denmark households' and NPISH gross disposable income, real (2020 chained prices), seasonally adjusted",
         "DK", "Q", "DKK billion, 2020 chained prices", "SA", "Statistics Denmark NKN3", "NKN3 TRANSAKT=B6G PRISENHED=RKV_M", 85,
         "Deflated by DST with the household consumption deflator.")


# =============================================================================================
# 8. Finland, Czechia
# =============================================================================================
@section
def finland():
    step("Finland index of wage and salary earnings")
    q = {"query": [{"code": "contentscode", "selection": {"filter": "item", "values": ["ati_1964_100"]}}],
         "response": {"format": "json-stat2"}}
    r = http("POST", STATFIN + "ati/14ut.px", json=q)
    df = jsonstat2_long(r.json())
    s = pd.Series(df["value"].values, index=df["timeperiod_q"].map(parse_period)).sort_index().dropna()
    save("fi_wage_idx_q", s, "Finland index of wage and salary earnings, total economy", "FI", "Q", "index 1964=100", "NSA",
         "Statistics Finland (StatFin ati, table 14ut)", "StatFin/ati/14ut.px contentscode=ati_1964_100", 50,
         "Long chain index (1964-); latest quarters preliminary (*). Includes regular earnings, overtime and irregular "
         "supplements; excludes performance bonuses.")


@section
def czechia():
    step("Czechia average gross monthly wage")
    try:
        r = http("GET", "https://data.csu.gov.cz/api/dotaz/v1/data/vybery/WPRACECRQT1")
        df = jsonstat2_long(r.json())
        df = df[df["IndicatorType"] == "5958P"]
        tcol = [c for c in df.columns if c.lower().startswith("cas")][0]
        df["date"] = df[tcol].astype(str).map(parse_period)   # codes like '2026-Q2'
        s = df.set_index("date")["value"].sort_index().dropna()
        query = "data.csu.gov.cz/api/dotaz/v1/data/vybery/WPRACECRQT1 IndicatorType=5958P"
    except Exception as e:
        print("   DataStat failed, using open-data CSV 110079:", e)
        meta = http("GET", "https://vdb.czso.cz/pll/eweb/package_show?id=110079").json()
        url = meta["result"]["resources"][0]["url"]
        d = pd.read_csv(io.StringIO(http("GET", url).content.decode("utf-8")))
        d = d[(d["stapro_kod"] == 5958) & (d["typosoby_kod"] == 200) & (d["odvetvi_kod"].isna())]
        s = pd.Series(d["hodnota"].values, index=[pd.Timestamp(int(y), 3 * int(q) - 2, 1) for y, q in zip(d["rok"], d["ctvrtleti"])]).sort_index()
        query = "CZSO open data 110079: stapro_kod=5958, typosoby_kod=200 (FTE), all industries"
    save("cz_avg_gross_wage_q", s, "Czechia average gross monthly wage per full-time equivalent employee, whole economy", "CZ", "Q",
         "CZK per month", "NSA", "Czech Statistical Office (CZSO)", query, 65,
         "Quarterly from 2000Q1; latest quarters preliminary. Strong Q4 seasonality (bonuses) -> use y/y.")


# =============================================================================================
# 9. Euro area
# =============================================================================================
@section
def euro_area():
    step("Euro area wages and household income")
    s = ecb("INW/Q.U2.N.INWR.000000.4F0.GY.IX")
    save("ea_negotiated_wages_yoy_q", s, "Euro area indicator of negotiated wage rates, annual growth rate", "EA", "Q",
         "% change y/y", "NSA", "ECB Data Portal (INW)", "INW/Q.U2.N.INWR.000000.4F0.GY.IX", 50,
         "Euro area changing composition; only growth rates published. Same series as legacy STS.Q.U2.N.INWR.000000.3.ANR "
         "(which stops 2025Q3). Includes one-off payments (volatile 2024).")
    s = ecb("EWT/Q.U2.N.WT.INWS._T.4F0.GY")
    save("ea_wage_tracker_yoy_q", s, "Euro area ECB wage tracker (negotiated wages incl. smoothed one-off payments), annual growth",
         "EA", "Q", "% change y/y", "NSA", "ECB Data Portal (EWT, ECB wage tracker)", "EWT/Q.U2.N.WT.INWS._T.4F0.GY", -180,
         "Forward-looking: built from signed collective agreements, so it extends ~4 quarters beyond the latest "
         "official data (values beyond the current quarter are mechanical projections of already-agreed pay and are "
         "revised as new agreements arrive). Use as expectation of near-term wage growth. 2013Q1-.")
    d1 = estat("namq_10_a10", geo="EA20", na_item="D1", nace_r2="TOTAL", unit="CP_MEUR", s_adj="SCA")
    emp = estat("namq_10_a10_e", geo="EA20", na_item="SAL_DC", nace_r2="TOTAL", unit="THS_PER", s_adj="SCA")
    s = (d1 / emp * 1000).dropna()   # EUR million / thousand persons *1000 = EUR per employee per quarter
    save("ea_comp_per_employee_q", s, "Euro area (EA20) compensation per employee (QNA), seasonally adjusted (computed)", "EA", "Q",
         "EUR per employee per quarter", "SCA", "Eurostat namq_10_a10 / namq_10_a10_e (computed ratio)",
         "namq_10_a10 Q.CP_MEUR.SCA.TOTAL.D1.EA20 / namq_10_a10_e Q.THS_PER.SCA.TOTAL.SAL_DC.EA20", 65,
         "Compensation of employees (incl. employer social contributions) divided by employees (domestic concept); "
         "fixed EA20 composition back to 1995.")
    s = estat("nasq_10_ki", geo="EA21", na_item="B6G_R_HAB_2010", s_adj="SCA", sector="S14_S15")
    save("ea_hh_real_disp_inc_pc_idx", s, "Euro area gross disposable income of households (incl. NPISH) in real terms per capita",
         "EA", "Q", "index 2010=100", "SCA", "Eurostat nasq_10_ki", "nasq_10_ki Q.PC.SCA.B6G_R_HAB_2010.S14_S15.EA21", 95,
         "Euro area aggregate EA21 (only composition published; incl. Bulgaria from 2026). Deflated with the household "
         "final consumption deflator. Same concept as EU/ea_hh_real_gdi_pc_idx.")


# =============================================================================================
# 10. Derived: real wage growth (quarterly) and expected real wages
# =============================================================================================
@section
def derived():
    step("Derived real wage series")
    S = STORE
    note_f = "real_yoy = 100*((1+w/100)/(1+p/100)-1); "

    def qcpi(sid):
        return yoy(q_avg(S[sid]), 4)

    specs = [
        ("no_real_wage_qna_yoy_q", "no_qna_wage_per_fte_q", "no_cpi_idx", "NO",
         "Norway real wage growth: QNA wages per FTE employee deflated by CPI", 55,
         "w = y/y of no_qna_wage_per_fte_q (NSA level, same quarter previous year), p = y/y of quarterly-average CPI (no_cpi_idx). Longest quarterly NO real wage series (1996-)."),
        ("no_real_earnings_yoy_q", "no_avg_monthly_earnings_q", "no_cpi_idx", "NO",
         "Norway real earnings growth: average monthly earnings (a-ordningen) deflated by CPI", 45,
         "w = y/y of no_avg_monthly_earnings_q, p = y/y of quarterly-average CPI (2017-)."),
        ("dk_real_wage_yoy_q", "dk_wage_idx_private_q", "dk_hicp_idx", "DK",
         "Denmark real wage growth: private-sector earnings index deflated by HICP", 75,
         "w = y/y of dk_wage_idx_private_q (spliced), p = y/y of quarterly-average HICP DK."),
        ("fi_real_wage_yoy_q", "fi_wage_idx_q", "fi_hicp_idx", "FI",
         "Finland real wage growth: index of wage and salary earnings deflated by HICP", 50,
         "w = y/y of fi_wage_idx_q, p = y/y of quarterly-average HICP FI (Statistics Finland's own real index uses national CPI)."),
        ("cz_real_wage_yoy_q", "cz_avg_gross_wage_q", "cz_hicp_idx", "CZ",
         "Czechia real wage growth: average gross monthly wage deflated by HICP", 65,
         "w = y/y of cz_avg_gross_wage_q, p = y/y of quarterly-average HICP CZ (CZSO's official real wage uses national CPI)."),
        ("ea_real_comp_per_employee_yoy_q", "ea_comp_per_employee_q", "ea_hicp_idx", "EA",
         "Euro area real compensation per employee growth (deflated by HICP)", 65,
         "w = y/y of ea_comp_per_employee_q (EA20), p = y/y of quarterly-average HICP (EA changing composition)."),
    ]
    for sid, wid, pid, c, desc, lag, extra in specs:
        if wid not in S or pid not in S:
            FAILURES.append((sid, f"missing input {wid} or {pid}"))
            continue
        r = real_growth(yoy(S[wid], 4), qcpi(pid))
        save(sid, r, desc, c, "Q", "% change y/y (real)", "NSA (y/y)", "computed (see notes)", f"{wid} & {pid}", lag,
             note_f + extra)

    # Sweden: monthly wage index -> quarterly average
    if "se_wage_idx_m" in S:
        w = yoy(q_avg(S["se_wage_idx_m"]), 4)
        save("se_real_wage_yoy_q", real_growth(w, qcpi("se_cpi_idx")),
             "Sweden real wage growth: whole-economy wage index (Konjunkturlönestatistik) deflated by CPI (KPI)", "SE", "Q",
             "% change y/y (real)", "NSA (y/y)", "computed (see notes)", "se_wage_idx_m & se_cpi_idx", 60,
             note_f + "w = y/y of quarterly average of se_wage_idx_m (latest quarters based on preliminary wage data, "
             "biased down until revised), p = y/y of quarterly-average KPI. KPIF-based variant = same formula with se_cpif_idx.")
        save("se_real_wage_kpif_yoy_q", real_growth(w, qcpi("se_cpif_idx")),
             "Sweden real wage growth deflated by CPIF (KPIF)", "SE", "Q", "% change y/y (real)", "NSA (y/y)",
             "computed (see notes)", "se_wage_idx_m & se_cpif_idx", 60,
             note_f + "As se_real_wage_yoy_q but p = y/y of quarterly-average KPIF (removes mortgage-rate effects, which "
             "dominated KPI in 2022-2024). MI's headline real wage measure uses KPIF.")

    # euro area negotiated wages (growth only)
    if "ea_negotiated_wages_yoy_q" in S:
        save("ea_real_negotiated_wages_yoy_q", real_growth(S["ea_negotiated_wages_yoy_q"], qcpi("ea_hicp_idx")),
             "Euro area real negotiated wage growth (deflated by HICP)", "EA", "Q", "% change y/y (real)", "NSA (y/y)",
             "computed (see notes)", "ea_negotiated_wages_yoy_q & ea_hicp_idx", 50,
             note_f + "w = ECB negotiated wage indicator y/y (published as growth rate), p = y/y of quarterly-average HICP EA.")

    # Norway annual TBU real wage
    if "no_tbu_wage_growth_a" in S:
        p = yoy(S["no_cpi_annual_idx"], 1)
        r = real_growth(S["no_tbu_wage_growth_a"], p)
        off = S.get("_no_ssb_real_official")
        diff = (r.round(1) - off.reindex(r.index)).abs().max() if off is not None else np.nan
        save("no_real_wage_tbu_yoy_a", r, "Norway annual real wage growth, all employees (TBU wage growth deflated by annual-average CPI)",
             "NO", "A", "% change y/y (real)", "NSA", "computed (see notes)", "no_tbu_wage_growth_a & no_cpi_annual_idx", 45,
             note_f + f"Annual: w = TBU årslønnsvekst, p = growth of annual-average CPI. Matches SSB's official real "
             f"earnings change (table 14858 ReallonnEndring) to within {diff:.1f} pp after rounding.")

    # Expected real wage growth
    for grp, wid, pid in [("econ", "no_exp_wage_cy_econ", "no_exp_infl_12m_econ"),
                          ("social", "no_exp_wage_cy_social", "no_exp_infl_12m_social"),
                          ("business", "no_exp_wage_cy_business", "no_exp_infl_12m_business")]:
        if wid in S and pid in S:
            name = {"econ": "economists", "social": "social partners", "business": "business leaders"}[grp]
            save(f"no_exp_real_wage_{grp}_q", real_growth(S[wid], S[pid]),
                 f"Norway expected real wage growth, {name} (expected wage growth this year vs expected CPI inflation next 12 months)",
                 "NO", "Q", "% (expected real growth)", "NSA", "computed from Norges Bank Expectations Survey",
                 f"{wid} & {pid}", -45,
                 "E[real] = 100*((1+E[w]/100)/(1+E[pi]/100)-1), same respondent group and survey round. Horizon mismatch: "
                 "wage question refers to the current calendar year, inflation to the next 12 months (no current-year "
                 "CPI question). From 2023 economists also answer a direct real-wage question (no_exp_real_wage_cy_econ).")
    if "se_exp_wage_1y_lmp" in S and "se_exp_cpi_1y_lmp" in S:
        save("se_exp_real_wage_1y_lmp", real_growth(S["se_exp_wage_1y_lmp"], S["se_exp_cpi_1y_lmp"]),
             "Sweden expected real wage growth next 12 months, labour market parties (Prospera/Origo)", "SE", "Q",
             "% (expected real growth)", "NSA", "computed from Riksbank expectations survey", "se_exp_wage_1y_lmp & se_exp_cpi_1y_lmp", -15,
             "E[real] = 100*((1+E[w]/100)/(1+E[pi]/100)-1); both 1-year-ahead means of the same respondents (avg of "
             "employee and employer organisations). CPI (KPI) expectations; KPIF expectations only from 2017.")


# =============================================================================================
def main():
    prices()
    norway_wages()
    norway_expectations()
    norway_hh_income()
    sweden()
    sweden_expectations()
    denmark()
    finland()
    czechia()
    euro_area()
    derived()
    cat = pd.DataFrame(CATALOG)
    cols = ["series_id", "file", "description", "country", "frequency", "unit", "seasonal_adjustment", "start", "end",
            "n_obs", "source", "source_query", "approx_release_lag_days", "notes"]
    cat = cat[cols].sort_values("series_id")
    cat.to_csv(OUT / "catalog.csv", index=False)
    print(f"\n{len(cat)} series written to {OUT}")
    if FAILURES:
        print("FAILURES:")
        for f in FAILURES:
            print("  ", f)


if __name__ == "__main__":
    main()
