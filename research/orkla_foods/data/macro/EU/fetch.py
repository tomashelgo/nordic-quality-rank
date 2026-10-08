#!/usr/bin/env python3
"""
Fetch harmonised macro/market panel for Orkla Foods' European markets (label: macro-EU).

Countries: NO SE DK FI EE LV LT CZ SK AT PL HU RO DE + EA20 (prefix "ea") + EU27_2020 (prefix "eu").

Sources (all public, no API keys, no manual steps):
  * Eurostat dissemination API (JSON-stat 2.0):
      https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset>?<filters>&format=JSON
  * ECB Data Portal API (CSV):  https://data-api.ecb.europa.eu/service/data/<flow>/<key>?format=csvdata
  * BIS SDMX API (central bank policy rates, CSV): https://stats.bis.org/api/v1/data/WS_CBPOL/<key>?format=csv
  * OECD SDMX API (Norway 10y yield, CSV): https://sdmx.oecd.org/public/rest/data/...
  * IMF SDMX API (India CPI all items): https://api.imf.org/external/sdmx/2.1/data/IMF.STA,CPI/...
  * FAOSTAT bulk download (India food CPI): https://bulks-faostat.fao.org/production/...

Output: one CSV per series (date,value) in the directory of this script, plus catalog.csv.
Dates: first day of the period (monthly YYYY-MM-01, quarterly first month of quarter).
Daily series (ECB key rates, BIS policy rates) are converted to monthly averages of calendar
days (step function forward-filled across weekends/holidays); the current incomplete month is dropped.

Conventions / caveats:
  * Euro area: EA20 is used where Eurostat publishes it; where only EA21 (Bulgaria joined the euro
    on 2026-01-01) or the evolving-composition 'EA' is available (une_rt_m, nasq_10_ki,
    irt_lt_mcby_m) that code is used under the same 'ea_' prefix (see catalog 'country'/'notes').
  * HICP comes from prc_hicp_minr (ECOICOP ver.2 / COICOP 2018, 2025=100). The legacy
    prc_hicp_midx (COICOP 1999) is frozen at 2025-12 and is NOT used.
  * Retail volumes and food PPI: 2021=100 series ratio-spliced backwards with the 2015=100 and
    2010=100 vintages where those start earlier (e.g. Sweden retail, I21 only from 2023).
  * Missing series are printed as MISSING at the end of the run.

Usage:  python3 fetch.py [output_dir]
"""
import io
import json
import os
import sys
import time
import zipfile

import numpy as np
import pandas as pd
import requests

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"}
ESTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
ECB = "https://data-api.ecb.europa.eu/service/data/"
BIS = "https://stats.bis.org/api/v1/data/"
OECD = "https://sdmx.oecd.org/public/rest/data/"

GEOS = ["NO", "SE", "DK", "FI", "EE", "LV", "LT", "CZ", "SK", "AT", "PL", "HU", "RO", "DE",
        "EA20", "EU27_2020"]
CNAME = {"NO": "Norway", "SE": "Sweden", "DK": "Denmark", "FI": "Finland", "EE": "Estonia",
         "LV": "Latvia", "LT": "Lithuania", "CZ": "Czechia", "SK": "Slovakia", "AT": "Austria",
         "PL": "Poland", "HU": "Hungary", "RO": "Romania", "DE": "Germany",
         "EA20": "Euro area (20)", "EU27_2020": "European Union (27, 2020)",
         "EA21": "Euro area (21)", "EA": "Euro area", "IN": "India"}


def prefix(geo):
    return {"EA20": "ea", "EA21": "ea", "EA": "ea", "EU27_2020": "eu"}.get(geo, geo.lower())


CATALOG = []
FAILURES = []


# ----------------------------------------------------------------------------- helpers
def get(url, params=None, tries=4, timeout=180):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code in (400, 403, 404, 407):
                break
        except Exception as e:  # network hiccup
            last = repr(e)
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"{url} {params} -> {last}")


def jsonstat_to_long(d):
    """Eurostat JSON-stat 2.0 -> long DataFrame with one column per dimension + value + flag."""
    ids, sizes = d["id"], d["size"]
    cats = []
    for k in ids:
        idx = d["dimension"][k]["category"]["index"]
        keys = sorted(idx, key=lambda x: idx[x]) if isinstance(idx, dict) else list(idx)
        cats.append(keys)
    vals = d.get("value", {})
    flags = d.get("status", {})
    if isinstance(vals, list):
        vals = {str(i): v for i, v in enumerate(vals) if v is not None}
    strides = np.cumprod([1] + sizes[::-1])[:-1][::-1]
    rows = []
    for pos, v in vals.items():
        pos = int(pos)
        rec = {}
        for k, keys, st, sz in zip(ids, cats, strides, sizes):
            rec[k] = keys[(pos // st) % sz]
        rec["value"] = v
        rec["flag"] = flags.get(str(pos), "") if isinstance(flags, dict) else ""
        rows.append(rec)
    return pd.DataFrame(rows)


def estat(dataset, **filters):
    """Query Eurostat statistics API. Filters: dim=value or dim=[values]."""
    params = [("format", "JSON"), ("lang", "EN")]
    for k, v in filters.items():
        for x in (v if isinstance(v, (list, tuple)) else [v]):
            params.append((k, x))
    r = get(ESTAT + dataset, params=params)
    d = r.json()
    df = jsonstat_to_long(d)
    df.attrs["updated"] = d.get("updated", "")
    df.attrs["query"] = r.url
    return df


EA_FALLBACK = ["EA21", "EA"]  # used only when EA20 is not published in a dataset
EA_NOTE = {"EA20": "", "EA21": " Euro-area aggregate is EA21 (incl. Bulgaria, euro member from "
                                "2026-01) because EA20 is not published in this dataset.",
           "EA": " Euro-area aggregate is 'EA' (evolving composition) because EA20 is not "
                 "published in this dataset."}


def resolve_ea(df, keys):
    """Keep one euro-area aggregate per series: EA20 if present, else EA21, else EA."""
    if df.empty:
        return df
    keep = []
    for _, g in df.groupby(keys) if keys else [(None, df)]:
        geos = set(g.geo)
        for cand in ["EA20", "EA21", "EA"]:
            if cand in geos:
                drop = {"EA20", "EA21", "EA"} - {cand}
                break
        else:
            drop = set()
        keep.append(g[~g.geo.isin(drop)])
    return pd.concat(keep)


def estat_geo(dataset, keys, **filters):
    """estat() over GEOS plus euro-area fallbacks, resolved to one EA aggregate."""
    df = estat(dataset, geo=GEOS + EA_FALLBACK, **filters)
    q = df.attrs.get("query", "")
    df = resolve_ea(df, keys)
    df.attrs["query"] = q
    return df


def splice_back(new, old):
    """Extend `new` backwards with the growth rates of `old` (ratio-splice at the first common
    period). Returns (series, spliced_flag)."""
    new, old = new.dropna().sort_index(), old.dropna().sort_index()
    if old.empty or new.empty or old.index.min() >= new.index.min():
        return new, False
    common = new.index.intersection(old.index)
    if len(common) == 0:
        return new, False
    t0 = common.min()
    back = old[old.index < t0] * (new[t0] / old[t0])
    return pd.concat([back, new]).sort_index(), True


def missing(sids_written, expected, reason):
    for sid in expected:
        if sid not in sids_written:
            FAILURES.append({"wanted": sid, "reason": reason})


def period_to_date(p):
    p = str(p)
    if "-Q" in p:
        y, q = p.split("-Q")
        return pd.Timestamp(int(y), 3 * (int(q) - 1) + 1, 1)
    if len(p) == 7:  # YYYY-MM
        return pd.Timestamp(p + "-01")
    if len(p) == 4:
        return pd.Timestamp(p + "-01-01")
    return pd.Timestamp(p)


def write_series(sid, s, meta):
    """s: pandas Series indexed by Timestamp. meta: dict for catalog."""
    s = s.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if len(s) == 0:
        FAILURES.append({"wanted": sid, "reason": "no observations returned"})
        return
    fn = f"{sid}.csv"
    out = pd.DataFrame({"date": s.index.strftime("%Y-%m-%d"), "value": s.values})
    out.to_csv(os.path.join(OUT, fn), index=False)
    row = {"series_id": sid, "file": fn, "start": out.date.iloc[0], "end": out.date.iloc[-1],
           "n_obs": len(out)}
    row.update(meta)
    CATALOG.append(row)
    print(f"  {sid:38s} {row['start']} .. {row['end']}  n={len(out)}")


def daily_to_monthly(s, complete_tol_days=7):
    """Daily step series -> calendar-day monthly average. Forward-fill across non-business days.
    Last month kept only if last observation falls within `complete_tol_days` of its end (and the
    month is not the current, still-running month)."""
    s = s.dropna().sort_index()
    last = s.index.max()
    month_end = last + pd.offsets.MonthEnd(0)
    today = pd.Timestamp.today().normalize()
    keep_last = (month_end - last).days <= complete_tol_days and month_end < today
    end = month_end if keep_last else (last.replace(day=1) - pd.Timedelta(days=1))
    idx = pd.date_range(s.index.min(), end, freq="D")
    s = s.reindex(idx.union(s.index)).ffill().reindex(idx)
    m = s.resample("MS").mean()
    # first month may be partial; keep only if series starts on day 1
    if s.index.min().day != 1:
        m = m.iloc[1:]
    return m


def ecb(flow, key):
    r = get(f"{ECB}{flow}/{key}", params={"format": "csvdata"})
    d = pd.read_csv(io.StringIO(r.text))
    d.attrs["query"] = r.url
    return d


# ----------------------------------------------------------------------------- Eurostat blocks
def ser(g):
    return pd.Series(g.value.values, index=g.time.map(period_to_date))


def written():
    return {r["series_id"] for r in CATALOG}


def block_hicp():
    print("HICP (prc_hicp_minr, ECOICOP ver.2, 2025=100)")
    names = {"TOTAL": ("hicp_all_idx", "HICP all items"),
             "CP01": ("hicp_food_bev_idx", "HICP food and non-alcoholic beverages (CP01)"),
             "CP011": ("hicp_food_idx", "HICP food (CP011)")}
    df = estat_geo("prc_hicp_minr", ["coicop18"], freq="M", unit="I25", coicop18=list(names))
    for (geo, c), g in df.groupby(["geo", "coicop18"]):
        suf, desc = names[c]
        flash = geo == "EA20" and c == "TOTAL"
        write_series(f"{prefix(geo)}_{suf}", ser(g), dict(
            description=f"{CNAME[geo]}: {desc}, monthly index",
            country=geo, frequency="M", unit="Index 2025=100", seasonal_adjustment="NSA",
            source="Eurostat", source_query=f"prc_hicp_minr M.I25.{c}.{geo}",
            approx_release_lag_days=1 if flash else 17,
            notes=("HICP on ECOICOP ver.2 (COICOP 2018), back-calculated by Eurostat; replaces "
                   "prc_hicp_midx (COICOP 1999), frozen at 2025-12. Full release ~t+17d; euro-area "
                   "all-items flash ~t+1d and some euro countries' national flashes are included "
                   "for the latest month (provisional)." + EA_NOTE.get(geo, ""))))
    missing(written(), [f"{prefix(g)}_{v[0]}" for g in GEOS for v in names.values()],
            "not returned by prc_hicp_minr")


def block_lci():
    print("LCI wages & salaries (lc_lci_r2_q)")
    df = estat_geo("lc_lci_r2_q", ["s_adj"], freq="Q", unit="I20", nace_r2="B-S", lcstruct="D11",
                   s_adj=["SCA", "CA"])
    for geo, g in df.groupby("geo"):
        gs, sa = g[g.s_adj == "SCA"], "SCA"
        if gs.empty:
            gs, sa = g[g.s_adj == "CA"], "CA"
        write_series(f"{prefix(geo)}_lci_wages_idx", ser(gs), dict(
            description=f"{CNAME[geo]}: labour cost index, wages and salaries (D11), NACE B-S, "
                        f"nominal, per hour worked",
            country=geo, frequency="Q", unit="Index 2020=100", seasonal_adjustment=sa,
            source="Eurostat", source_query=f"lc_lci_r2_q Q.{sa}.I20.B-S.D11.{geo}",
            approx_release_lag_days=77,
            notes="Nominal hourly wages & salaries; deflate with HICP for real wages. Eurostat "
                  "release ~mid third month after quarter. AT, EA and EU aggregates start 2009, "
                  "SE 2008 (NACE Rev.2 series)." + EA_NOTE.get(geo, "")))
    missing(written(), [f"{prefix(g)}_lci_wages_idx" for g in GEOS], "not in lc_lci_r2_q")


def _spliced_panel(dataset, item_dim, items, filters, base_units=("I21", "I15", "I10")):
    """Fetch several index bases; return dict (geo,item)->(series, spliced_from list)."""
    df = estat(dataset, geo=GEOS + EA_FALLBACK, unit=list(base_units), **{item_dim: list(items)},
               **filters)
    main = resolve_ea(df[df.unit == base_units[0]], [item_dim])
    out = {}
    for (geo, it), g in main.groupby(["geo", item_dim]):
        s, used = ser(g), []
        for u in base_units[1:]:
            o = ser(df[(df.geo == geo) & (df[item_dim] == it) & (df.unit == u)])
            # break check: if the new base's m/m growth deviates >15 log-pts from the older
            # base in some overlapping month, the new base is inconsistent before that month
            # (e.g. SK food retail I21 jumps +54% in 2016-01 while I15 is smooth) -> truncate.
            common = s.index.intersection(o.index)
            if len(common) > 2:
                dn, do = np.log(s[common]).diff(), np.log(o[common]).diff()
                dev = (dn - do).abs()
                # a deviating month is a break in the NEW base if the new base moves more
                bad = [t for t in dev[dev > 0.15].index if abs(dn[t]) > abs(do[t])]
                if bad:
                    tb = max(bad)
                    print(f"    break in {dataset} {it} {geo} I21 at {tb:%Y-%m} (vs {u})")
                    s = s[s.index >= tb]
                    used.append(f"{u} (break in I21 at {tb:%Y-%m}: I21 values before it "
                                f"replaced by {u} growth rates)")
                    s, _ = splice_back(s, o)
                    continue
            s, ok = splice_back(s, o)
            if ok:
                used.append(u)
        out[(geo, it)] = (s, used)
    return out


def block_retail():
    print("Retail trade volume (sts_trtu_m)")
    names = {"G47_FOOD": ("retail_food_vol_idx",
                          "retail trade volume, food, beverages and tobacco (G47_FOOD)"),
             "G47": ("retail_total_vol_idx",
                     "retail trade volume, total retail trade except motor vehicles (G47)")}
    panel = _spliced_panel("sts_trtu_m", "nace_r2", names,
                           dict(freq="M", indic_bt="VOL_SLS", s_adj="SCA"))
    for (geo, n), (s, used) in panel.items():
        suf, desc = names[n]
        sp = (f" Ratio-spliced backwards with older base(s) {'; '.join(used)} "
              f"(growth rates of older base preserved before the splice point)." if used else "")
        write_series(f"{prefix(geo)}_{suf}", s, dict(
            description=f"{CNAME[geo]}: {desc}",
            country=geo, frequency="M", unit="Index 2021=100 (volume of sales)",
            seasonal_adjustment="SCA", source="Eurostat",
            source_query=f"sts_trtu_m M.VOL_SLS.{n}.SCA.I21.{geo}"
                         + (f" (+{'/'.join(u[:3] for u in used)} back-splice)" if used else ""),
            approx_release_lag_days=35,
            notes="Deflated turnover. Eurostat release ~t+35d (national releases often ~t+28d)."
                  + sp + EA_NOTE.get(geo, "")))
    missing(written(), [f"{prefix(g)}_{v[0]}" for g in GEOS for v in names.values()],
            "sts_trtu_m SCA volume not published for this country")


def block_ppi():
    print("Domestic producer prices, food manufacturing (sts_inppd_m)")
    panel = _spliced_panel("sts_inppd_m", "nace_r2", ["C10"],
                           dict(freq="M", indic_bt="PRC_PRR_DOM", s_adj="NSA"))
    for (geo, n), (s, used) in panel.items():
        sp = (f" Ratio-spliced backwards with older base(s) {'; '.join(used)}." if used else "")
        write_series(f"{prefix(geo)}_ppi_dom_food_mfg_idx", s, dict(
            description=f"{CNAME[geo]}: producer prices in industry, domestic market, "
                        f"manufacture of food products (NACE C10)",
            country=geo, frequency="M", unit="Index 2021=100", seasonal_adjustment="NSA",
            source="Eurostat", source_query=f"sts_inppd_m M.PRC_PRR_DOM.C10.NSA.I21.{geo}"
            + (f" (+{'/'.join(u[:3] for u in used)} back-splice)" if used else ""),
            approx_release_lag_days=35,
            notes="Output (selling) prices of food manufacturers on the domestic market. "
                  "Eurostat release ~t+33-35d." + sp + EA_NOTE.get(geo, "")))
    missing(written(), [f"{prefix(g)}_ppi_dom_food_mfg_idx" for g in GEOS],
            "sts_inppd_m C10 not published for this country (confidential / not transmitted; "
            "SK only I10 2010-2015)")
    subs = {"C101": "meat", "C102": "fish", "C103": "fruit & vegetables",
            "C104": "vegetable & animal oils and fats", "C105": "dairy",
            "C106": "grain mill & starch", "C107": "bakery & farinaceous",
            "C108": "other food products"}
    df = estat("sts_inppd_m", freq="M", indic_bt="PRC_PRR_DOM", nace_r2=list(subs), s_adj="NSA",
               unit="I21", geo="EU27_2020")
    for n, g in df.groupby("nace_r2"):
        write_series(f"eu_ppi_dom_{n.lower()}_idx", ser(g), dict(
            description=f"EU27: domestic producer prices, NACE {n} ({subs[n]})",
            country="EU27_2020", frequency="M", unit="Index 2021=100", seasonal_adjustment="NSA",
            source="Eurostat", source_query=f"sts_inppd_m M.PRC_PRR_DOM.{n}.NSA.I21.EU27_2020",
            approx_release_lag_days=35, notes="NACE Rev.2 group-level food manufacturing PPI."))


def block_unemp():
    print("Unemployment rate SA (une_rt_m)")
    df = estat_geo("une_rt_m", [], freq="M", s_adj="SA", age="TOTAL", unit="PC_ACT", sex="T")
    for geo, g in df.groupby("geo"):
        write_series(f"{prefix(geo)}_unemp_rate_sa", ser(g), dict(
            description=f"{CNAME[geo]}: unemployment rate, total (15-74), ILO definition",
            country=geo, frequency="M", unit="% of labour force", seasonal_adjustment="SA",
            source="Eurostat", source_query=f"une_rt_m M.SA.TOTAL.PC_ACT.T.{geo}",
            approx_release_lag_days=31,
            notes="Monthly LFS-based estimates (some countries interpolate quarterly LFS; latest "
                  "months may be provisional)." + EA_NOTE.get(geo, "")))
    missing(written(), [f"{prefix(g)}_unemp_rate_sa" for g in GEOS], "not in une_rt_m")


def block_gdp():
    print("GDP volume (namq_10_gdp)")
    df = estat_geo("namq_10_gdp", [], freq="Q", unit="CLV_I20", s_adj="SCA", na_item="B1GQ")
    for geo, g in df.groupby("geo"):
        agg = geo in ("EA20", "EA21", "EU27_2020")
        write_series(f"{prefix(geo)}_gdp_vol_idx", ser(g), dict(
            description=f"{CNAME[geo]}: GDP at market prices, chain-linked volume index",
            country=geo, frequency="Q", unit="Index 2020=100 (chain-linked volumes)",
            seasonal_adjustment="SCA", source="Eurostat",
            source_query=f"namq_10_gdp Q.CLV_I20.SCA.B1GQ.{geo}",
            approx_release_lag_days=30 if agg else 45,
            notes="EA/EU preliminary flash ~t+30d; national first estimates ~t+30..60d."
                  + EA_NOTE.get(geo, "")))
    missing(written(), [f"{prefix(g)}_gdp_vol_idx" for g in GEOS], "not in namq_10_gdp")


def block_households():
    print("Household sector key indicators (nasq_10_ki)")
    items = {"SRG_S14_S15": ("hh_saving_rate", "gross household saving rate B8G/(B6G+D8net)",
                             "% of gross disposable income (+D8net)"),
             "B6G_R_HAB_2010": ("hh_real_gdi_pc_idx",
                                "real gross disposable income of households per capita",
                                "Index 2010=100")}
    df = estat_geo("nasq_10_ki", ["na_item"], freq="Q", unit="PC", s_adj="SCA",
                   na_item=list(items), sector="S14_S15")
    df = df[df.value != 0]  # Eurostat stores 0 placeholders before series start (e.g. DK GDI)
    for (geo, it), g in df.groupby(["geo", "na_item"]):
        suf, desc, unit = items[it]
        write_series(f"{prefix(geo)}_{suf}", ser(g), dict(
            description=f"{CNAME[geo]}: {desc} (households incl. NPISH, S14_S15)",
            country=geo, frequency="Q", unit=unit, seasonal_adjustment="SCA",
            source="Eurostat", source_query=f"nasq_10_ki Q.PC.SCA.{it}.S14_S15.{geo}",
            approx_release_lag_days=97,
            notes="Quarterly sector accounts; Eurostat release ~early 4th month after quarter. "
                  "Real GDI deflated with household final consumption deflator."
                  + EA_NOTE.get(geo, "")))
    missing(written(), [f"{prefix(g)}_{v[0]}" for g in GEOS for v in items.values()],
            "nasq_10_ki SCA not published for this country (NO: only NSA saving rate to "
            "2023-Q2; EE/LV/LT/SK: not transmitted)")


def block_bonds():
    print("10y government bond yields (irt_lt_mcby_m)")
    df = estat_geo("irt_lt_mcby_m", [], freq="M", int_rt="MCBY")
    for geo, g in df.groupby("geo"):
        note = ""
        if geo == "EE":
            note = (" Estonia has no benchmark 10y government bond; Eurostat series exists only "
                    "from 2020-06 (based on new issuance); not comparable to other countries.")
        write_series(f"{prefix(geo)}_gov_bond_10y", ser(g), dict(
            description=f"{CNAME[geo]}: EMU convergence criterion long-term (~10y) government "
                        f"bond yield, monthly average",
            country=geo, frequency="M", unit="% p.a.", seasonal_adjustment="NSA",
            source="Eurostat", source_query=f"irt_lt_mcby_m M.MCBY.{geo}",
            approx_release_lag_days=1,
            notes="Market data known in real time; Eurostat monthly publication ~t+10d."
                  + note + EA_NOTE.get(geo, "")))
    missing(written(), [f"{prefix(g)}_gov_bond_10y" for g in GEOS if g != "NO"],
            "not in irt_lt_mcby_m")


def block_st_rates():
    print("3-month money market rates, non-euro countries (irt_st_m)")
    # HU (BUBOR) excluded: 19 missing months 2004-2013 and a spurious 0 in 2021-07 in Eurostat;
    # use hu_policy_rate instead. SE/NO short rates are covered by the national (macro-SE/NO) sets.
    geos = ["DK", "CZ", "PL", "RO"]
    df = estat("irt_st_m", freq="M", int_rt="IRT_M3", geo=geos)
    for geo, g in df.groupby("geo"):
        s = ser(g)
        note = ""
        if s.index.max() < pd.Timestamp("2026-06-01"):
            note = (f" Eurostat updates stop at {s.index.max():%Y-%m} (stale; use "
                    f"{prefix(geo)}_policy_rate / EUR rates for recent months).")
        write_series(f"{prefix(geo)}_mm_rate_3m", s, dict(
            description=f"{CNAME[geo]}: 3-month interbank money market rate, monthly average",
            country=geo, frequency="M", unit="% p.a.", seasonal_adjustment="NSA",
            source="Eurostat", source_query=f"irt_st_m M.IRT_M3.{geo}",
            approx_release_lag_days=1,
            notes="CIBOR/PRIBOR/WIBOR/ROBOR 3m. Market data known in real time; Eurostat "
                  "publication ~t+10d." + note))

# ----------------------------------------------------------------------------- ECB blocks
def block_ecb_rates():
    print("ECB key rates and Euribor")
    d = ecb("FM", "D.U2.EUR.4F.KR.DFR.LEV")
    s = pd.Series(d.OBS_VALUE.values, index=pd.to_datetime(d.TIME_PERIOD))
    write_series("ea_ecb_dfr", daily_to_monthly(s), dict(
        description="ECB deposit facility rate, monthly average of calendar days",
        country="EA", frequency="M", unit="% p.a.", seasonal_adjustment="NSA",
        source="ECB Data Portal", source_query="FM.D.U2.EUR.4F.KR.DFR.LEV",
        approx_release_lag_days=0,
        notes="Daily (calendar-day) series averaged to months; current incomplete month dropped."))
    fr = ecb("FM", "D.U2.EUR.4F.KR.MRR_FR.LEV")
    mbr = ecb("FM", "D.U2.EUR.4F.KR.MRR_MBR.LEV")
    s_fr = pd.Series(fr.OBS_VALUE.values, index=pd.to_datetime(fr.TIME_PERIOD))
    s_mbr = pd.Series(mbr.OBS_VALUE.values, index=pd.to_datetime(mbr.TIME_PERIOD))
    s = pd.concat([s_fr, s_mbr[~s_mbr.index.isin(s_fr.index)]]).sort_index()
    write_series("ea_ecb_mro", daily_to_monthly(s), dict(
        description="ECB main refinancing operations rate, monthly average of calendar days",
        country="EA", frequency="M", unit="% p.a.", seasonal_adjustment="NSA",
        source="ECB Data Portal",
        source_query="FM.D.U2.EUR.4F.KR.MRR_FR.LEV spliced with FM.D.U2.EUR.4F.KR.MRR_MBR.LEV",
        approx_release_lag_days=0,
        notes="Fixed rate (1999-01..2000-06-27 and 2008-10-15..) and minimum bid rate of "
              "variable-rate tenders (2000-06-28..2008-10-14). Daily averaged to months; "
              "current incomplete month dropped."))
    d = ecb("FM", "M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA")
    s = pd.Series(d.OBS_VALUE.values, index=d.TIME_PERIOD.map(period_to_date))
    write_series("ea_euribor_3m", s, dict(
        description="3-month Euribor, monthly average",
        country="EA", frequency="M", unit="% p.a.", seasonal_adjustment="NSA",
        source="ECB Data Portal", source_query="FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA",
        approx_release_lag_days=1, notes="Historical close, average of observations through "
                                         "period (pre-1999 synthetic/national rates)."))


def block_fx():
    print("ECB reference rates, monthly averages")
    ccys = ["NOK", "SEK", "DKK", "CZK", "PLN", "HUF", "RON", "INR", "USD"]
    d = ecb("EXR", f"M.{'+'.join(ccys)}.EUR.SP00.A")
    for c, g in d.groupby("CURRENCY"):
        s = pd.Series(g.OBS_VALUE.values, index=g.TIME_PERIOD.map(period_to_date))
        write_series(f"ea_fx_{c.lower()}_per_eur", s, dict(
            description=f"ECB euro foreign exchange reference rate, {c} per EUR, monthly average",
            country="EA", frequency="M", unit=f"{c} per 1 EUR", seasonal_adjustment="NSA",
            source="ECB Data Portal", source_query=f"EXR.M.{c}.EUR.SP00.A",
            approx_release_lag_days=1,
            notes="Higher value = weaker local currency vs EUR. Monthly average of daily "
                  "reference rates (ECB-computed)."))


# ----------------------------------------------------------------------------- BIS policy rates
def block_policy_rates():
    print("Central bank policy rates (BIS WS_CBPOL, daily -> monthly avg)")
    geos = {"CZ": "CNB 2-week repo rate", "PL": "NBP reference rate",
            "HU": "MNB base rate", "RO": "NBR monetary policy rate",
            "DK": "Danmarks Nationalbank policy rate", "IN": "RBI policy repo rate"}
    r = get(f"{BIS}WS_CBPOL/D.{'+'.join(geos)}", params={"format": "csv"})
    d = pd.read_csv(io.StringIO(r.text))
    for geo, g in d.groupby("REF_AREA"):
        s = pd.Series(pd.to_numeric(g.OBS_VALUE, errors="coerce").values,
                      index=pd.to_datetime(g.TIME_PERIOD))
        s = s[s.index >= "1990-01-01"]
        comp = str(g.COMPILATION.dropna().iloc[0]) if g.COMPILATION.notna().any() else ""
        write_series(f"{prefix(geo)}_policy_rate", daily_to_monthly(s), dict(
            description=f"{CNAME[geo]}: central bank policy rate ({geos[geo]}), monthly average "
                        f"of calendar days",
            country=geo, frequency="M", unit="% p.a.", seasonal_adjustment="NSA",
            source="BIS (central bank policy rates)", source_query=f"WS_CBPOL D.{geo}",
            approx_release_lag_days=0,
            notes=f"Daily step series forward-filled over non-business days and averaged to "
                  f"months; truncated at 1990. BIS compilation note: {comp[:160]}"))


# ----------------------------------------------------------------------------- OECD extras
def oecd_csv(path):
    r = get(OECD + path, params={"format": "csvfile"})
    return pd.read_csv(io.StringIO(r.text))


def block_india_cpi():
    print("India CPI all items (IMF CPI dataset, SDMX)")
    url = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,CPI/IND.CPI._T.IX.M"
    r = requests.get(url, headers={**UA, "Accept": "application/vnd.sdmx.data+csv;version=1.0.0"},
                     timeout=180)
    r.raise_for_status()
    g = pd.read_csv(io.StringIO(r.text))
    g = g[g.TIME_PERIOD.str.contains("-M")]
    idx = g.TIME_PERIOD.map(lambda p: pd.Timestamp(p.replace("-M", "-") + "-01"))
    s = pd.Series(pd.to_numeric(g.OBS_VALUE, errors="coerce").values, index=idx)
    write_series("in_cpi_all_idx", s[s.index >= "1990-01-01"], dict(
        description="India: consumer price index, all items (national CPI)", country="IN",
        frequency="M", unit="Index 2024=100 (IMF overlap-linked)", seasonal_adjustment="NSA",
        source="IMF CPI dataset (from MoSPI)", source_query="api.imf.org IMF.STA,CPI IND.CPI._T.IX.M",
        approx_release_lag_days=12,
        notes="IMF links older bases (CPI-IW pre-2011, CPI 2012=100, CPI 2024=100 from 2026) by "
              "overlap; truncated at 1990. MoSPI release ~12th of following month. Relevant for "
              "Orkla's Indian businesses (MTR, Eastern). IMF/OECD food sub-index is empty or ends "
              "2019, hence in_cpi_food_idx from FAOSTAT."))

    print("India CPI food (FAOSTAT consumer price indices, bulk download)")
    url = ("https://bulks-faostat.fao.org/production/"
           "ConsumerPriceIndices_E_All_Data_(Normalized).zip")
    r = get(url, timeout=300)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    d = pd.read_csv(z.open("ConsumerPriceIndices_E_All_Data_(Normalized).csv"),
                    encoding="latin-1", low_memory=False)
    d = d[(d["Area"] == "India") & (d["Item"] == "Consumer Prices, Food Indices (2015 = 100)")]
    months = {m: k + 1 for k, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July", "August",
         "September", "October", "November", "December"])}
    idx = pd.to_datetime(dict(year=d.Year, month=d.Months.map(months), day=1))
    s = pd.Series(d.Value.values, index=idx.values)
    write_series("in_cpi_food_idx", s, dict(
        description="India: consumer price index, food", country="IN", frequency="M",
        unit="Index 2015=100", seasonal_adjustment="NSA",
        source="FAOSTAT Consumer Price Indices (from ILO/MoSPI)",
        source_query="FAOSTAT bulk ConsumerPriceIndices_E_All_Data_(Normalized).zip, Area=India, "
                     "Item=Consumer Prices, Food Indices (2015 = 100)",
        approx_release_lag_days=120,
        notes="FAO compiles from ILO/national sources (flags A=official, X=international org, "
              "I=imputed); updated with a lag of several months. Official source = MoSPI "
              "CFPI/CPI food (api.mospi.gov.in refused TLS: legacy renegotiation)."))


def block_no_bond():
    print("Norway 10y government bond yield (OECD MEI/KEI)")
    d = oecd_csv("OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/NOR.M.IRLT.PA._Z._Z._Z._Z.N")
    s = pd.Series(d.OBS_VALUE.values, index=d.TIME_PERIOD.map(period_to_date))
    write_series("no_gov_bond_10y", s, dict(
        description="Norway: long-term (10y) government bond yield, monthly average",
        country="NO", frequency="M", unit="% p.a.", seasonal_adjustment="NSA",
        source="OECD financial market statistics (from Norges Bank)",
        source_query="OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/NOR.M.IRLT.PA._Z._Z._Z._Z.N",
        approx_release_lag_days=1,
        notes="Norway is not in Eurostat irt_lt_mcby_m (EU-only convergence series)."))


# ----------------------------------------------------------------------------- main
BLOCKS = [block_hicp, block_lci, block_retail, block_ppi, block_unemp, block_gdp,
          block_households, block_bonds, block_st_rates, block_ecb_rates, block_fx,
          block_policy_rates, block_india_cpi, block_no_bond]

if __name__ == "__main__":
    for b in BLOCKS:
        try:
            b()
        except Exception as e:
            print("FAILED", b.__name__, e)
            FAILURES.append({"wanted": b.__name__, "reason": str(e)[:300]})
    cols = ["series_id", "file", "description", "country", "frequency", "unit",
            "seasonal_adjustment", "start", "end", "n_obs", "source", "source_query",
            "approx_release_lag_days", "notes"]
    cat = pd.DataFrame(CATALOG)[cols].sort_values("series_id")
    cat.to_csv(os.path.join(OUT, "catalog.csv"), index=False)
    print(f"\n{len(cat)} series written to {OUT}")
    for x in FAILURES:
        print("MISSING:", x)
