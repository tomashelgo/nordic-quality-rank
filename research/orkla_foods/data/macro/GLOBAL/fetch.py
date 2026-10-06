#!/usr/bin/env python3
"""
Fetch global input-cost / market driver series for the Orkla Foods predictor analysis
(label: macro-GLOBAL).

Output: one CSV per series (columns date,value; date = first day of period, YYYY-MM-01)
in the directory of this script, plus catalog.csv.

Usage:
    python3 -I fetch.py [--dl DOWNLOAD_DIR]
DOWNLOAD_DIR defaults to a fresh temporary directory. Raw downloads are written there and
parsed from there (downloaded content is treated as data only).

Sources (all public, no API keys, no manual steps):
  * FAO Food Price Index  - https://www.fao.org/worldfoodsituation/foodpricesindex/en/
      The xlsx link changes name every month (ffpi-data-YYYY-MM.xlsx?sfvrsn=...), so it is
      scraped from the page; sheets Indices_Monthly (nominal) and Indices_Monthly_Real.
  * World Bank Pink Sheet - CMO-Historical-Data-Monthly.xlsx; the link (thedocs.worldbank.org
      .../related/CMO-Historical-Data-Monthly.xlsx) is scraped from
      https://www.worldbank.org/en/research/commodity-markets
  * FRED (St. Louis Fed)  - https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>
      NB: through the sandbox proxy FRED rejects browser-like user agents; a plain
      "curl/8" UA works.
  * Eurostat dissemination API (JSON-stat) - sts_inppd_m (industrial producer prices).
  * NY Fed GSCPI          - https://www.newyorkfed.org/medialibrary/research/interactives/gscpi/downloads/gscpi_data.xlsx
      (despite the extension it is a legacy .xls / BIFF file -> read with xlrd).
  * EC Agri-food data portal API - https://api.tech.ec.europa.eu/agrifood/api/...
      (OpenAPI spec: https://api.tech.ec.europa.eu/agrifood/v3/api-docs). The endpoint is
      occasionally "SUSPENDED" (HTTP 500) for a few seconds -> retried.
  * Energi Data Service (Energinet) - https://api.energidataservice.dk/dataset/Elspotprices
      (hourly, 2000-01..2025-09-30, areas SYS/SYSTEM, NO2, SE3, DK1, ...) and
      dataset DayAheadPrices (15-min resolution from 2025-10-01; areas DK1, DK2, NO2, SE3, SE4, DE;
      no SYSTEM price). Rate limited (HTTP 429 "Try again in N seconds") -> retried.
  * Ember European wholesale electricity prices (ENTSO-E day-ahead, cleaned):
      https://files.ember-energy.org/public-downloads/price/outputs/european_wholesale_electricity_price_data_monthly.csv
      Used for Finland (single bidding zone) and Norway country average (load-weighted
      across NO1-NO5; substitute for NO1, which has no free long history).

Daily/hourly/weekly data are aggregated to calendar-month arithmetic means.
Incomplete current months are dropped (only months strictly before the current month are kept
for sources that publish partial months).
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import re
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

OUT = Path(__file__).resolve().parent
UA_BROWSER = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/126.0 Safari/537.36"}
UA_PLAIN = {"User-Agent": "curl/8"}
TODAY = dt.date.today()
CUR_MONTH = pd.Timestamp(TODAY.year, TODAY.month, 1)

CATALOG: list[dict] = []
FAILURES: list[dict] = []
DL: Path = Path(".")


# ----------------------------------------------------------------------------- helpers
def http_get(url, fname=None, headers=None, params=None, tries=6, timeout=300, binary=True):
    """GET with retries; optionally save the body to DL/fname. Returns requests.Response."""
    headers = headers or UA_BROWSER
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
        except requests.RequestException as e:  # noqa: PERF203
            last = e
            time.sleep(3 * (i + 1))
            continue
        if r.status_code == 429:
            m = re.search(r"(\d+)\s*second", r.text)
            wait = min(int(m.group(1)) + 2, 200) if m else 30
            print(f"   429 rate limited, waiting {wait}s ...")
            time.sleep(wait)
            continue
        if r.status_code == 500 and "SUSPENDED" in r.text:
            time.sleep(5)
            continue
        if r.status_code >= 500:
            last = RuntimeError(f"{r.status_code} {r.text[:200]}")
            time.sleep(3 * (i + 1))
            continue
        if fname:
            (DL / fname).write_bytes(r.content)
        return r
    raise RuntimeError(f"GET failed for {url}: {last}")


def monthly_index(s: pd.Series) -> pd.Series:
    s = s.copy()
    s.index = pd.to_datetime(s.index).to_period("M").to_timestamp()
    s = pd.to_numeric(s, errors="coerce").dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


def to_monthly_mean(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").dropna()
    m = s.groupby(pd.to_datetime(s.index).to_period("M")).mean()
    m.index = m.index.to_timestamp()
    return m


def drop_incomplete(s: pd.Series) -> pd.Series:
    return s[s.index < CUR_MONTH]


def add(series_id, s: pd.Series, *, description, country, frequency="M", unit, sa="NSA",
        source, source_query, lag, notes=""):
    s = monthly_index(s) if frequency == "M" else s.dropna().sort_index()
    if s.empty:
        FAILURES.append(dict(wanted=series_id, reason="empty after parsing"))
        print(f"!! {series_id}: empty")
        return
    df = pd.DataFrame({"date": s.index.strftime("%Y-%m-%d"), "value": s.values})
    df["value"] = df["value"].map(lambda v: float(f"{v:.10g}"))
    df.to_csv(OUT / f"{series_id}.csv", index=False)
    CATALOG.append(dict(series_id=series_id, file=f"{series_id}.csv", description=description,
                        country=country, frequency=frequency, unit=unit, seasonal_adjustment=sa,
                        start=df["date"].iloc[0], end=df["date"].iloc[-1], n_obs=len(df),
                        source=source, source_query=source_query, approx_release_lag_days=lag,
                        notes=notes))
    print(f"ok {series_id:40s} {df['date'].iloc[0]} .. {df['date'].iloc[-1]}  n={len(df)}")


def safe(fn):
    def wrap(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            FAILURES.append(dict(wanted=fn.__name__, reason=f"{type(e).__name__}: {e}"[:300]))
            return None
    return wrap


STORE: dict[str, pd.Series] = {}  # series kept for derived calculations


# ----------------------------------------------------------------------------- FAO
@safe
def block_fao():
    print("== FAO Food Price Index")
    page = "https://www.fao.org/worldfoodsituation/foodpricesindex/en/"
    html = http_get(page, "fao_page.html").text
    m = re.search(r'href="([^"]+ffpi-data-[^"]+\.xlsx[^"]*)"', html)
    if not m:
        raise RuntimeError("FAO ffpi-data xlsx link not found on page")
    url = m.group(1).replace("&amp;", "&")
    http_get(url, "fao_ffpi_data.xlsx")
    nom = pd.read_excel(DL / "fao_ffpi_data.xlsx", sheet_name="Indices_Monthly", header=None)
    real = pd.read_excel(DL / "fao_ffpi_data.xlsx", sheet_name="Indices_Monthly_Real", header=None)

    def parse(df, date_col, first_val_col):
        df = df[pd.to_datetime(df[date_col], errors="coerce", format="mixed").notna()].copy()
        df.index = pd.to_datetime(df[date_col])
        cols = list(range(first_val_col, first_val_col + 6))
        out = df[cols].apply(pd.to_numeric, errors="coerce")
        out.columns = ["ffpi", "meat", "dairy", "cereals", "oils", "sugar"]
        return out

    n = parse(nom, 0, 1)
    r = parse(real, 1, 2)
    common = dict(country="GLOBAL", unit="Index 2014-2016=100", source="FAO",
                  lag=6, sa="NSA")
    q = f"{url.split('?')[0]} sheet Indices_Monthly"
    rel = ("Released ~first Friday of following month; FAO revises the last few months "
           "(esp. dairy/meat) in later releases.")
    add("glob_fao_ffpi", n["ffpi"], description="FAO Food Price Index (nominal, USD-based, "
        "trade-weighted average of 5 commodity group indices)", source_query=q,
        notes=rel, **common)
    add("glob_fao_ffpi_real", r["ffpi"], description="FAO Food Price Index, real (deflated by "
        "World Bank Manufactures Unit Value index, MUV)",
        source_query=f"{url.split('?')[0]} sheet Indices_Monthly_Real",
        notes=rel + " Real index is revised when MUV is revised.", **common)
    names = dict(meat="Meat Price Index", dairy="Dairy Price Index", cereals="Cereals Price Index",
                 oils="Vegetable Oil Price Index", sugar="Sugar Price Index")
    ids = dict(meat="glob_fao_meat_idx", dairy="glob_fao_dairy_idx", cereals="glob_fao_cereals_idx",
               oils="glob_fao_vegoils_idx", sugar="glob_fao_sugar_idx")
    for k, nm in names.items():
        add(ids[k], n[k], description=f"FAO {nm} (nominal)", source_query=q, notes=rel, **common)
    STORE["fao_ffpi"] = monthly_index(n["ffpi"])


# ----------------------------------------------------------------------------- World Bank
WB_INDEX_COLS = {  # column position in 'Monthly Indices' sheet -> (id, description)
    2: ("glob_wb_energy_idx", "Energy"),
    3: ("glob_wb_nonenergy_idx", "Non-energy"),
    4: ("glob_wb_agri_idx", "Agriculture"),
    5: ("glob_wb_beverages_idx", "Beverages"),
    6: ("glob_wb_food_idx", "Food"),
    7: ("glob_wb_oilsmeals_idx", "Oils & Meals"),
    8: ("glob_wb_grains_idx", "Grains"),
    9: ("glob_wb_otherfood_idx", "Other Food"),
    10: ("glob_wb_rawmat_idx", "Raw Materials"),
    13: ("glob_wb_fertilizers_idx", "Fertilizers"),
    14: ("glob_wb_metals_idx", "Metals & Minerals"),
}
WB_PRICES = [  # (header in 'Monthly Prices', id, description, extra note)
    ("Wheat, US HRW", "glob_wb_wheat_us_hrw", "Wheat, US No.2 Hard Red Winter, export price US Gulf", ""),
    ("Wheat, US SRW", "glob_wb_wheat_us_srw", "Wheat, US No.2 Soft Red Winter, export price US Gulf", ""),
    ("Maize", "glob_wb_maize", "Maize, US No.2 yellow, FOB US Gulf", ""),
    ("Rice, Thai 5% ", "glob_wb_rice_thai5", "Rice, Thai 5% broken white, FOB Bangkok", ""),
    ("Barley", "glob_wb_barley", "Barley (US feed No.2 Minneapolis from 2012-05; Canadian feed before)",
     "Discontinued by the World Bank after 2020-08; see eu_agri_barley_feed for EU barley from 2015."),
    ("Soybeans", "glob_wb_soybeans", "Soybeans (US origin; delivery basis changed 2021, 2025)", ""),
    ("Soybean oil", "glob_wb_soybean_oil", "Soybean oil (Dutch crude degummed FOB NW Europe to 2024; US Gulf from 2025-01)",
     "Basis change Jan-2025 (Dutch -> US Gulf) causes a level break."),
    ("Palm oil", "glob_wb_palm_oil", "Palm oil, Malaysia (RBD/crude; basis changed several times)",
     "Several basis changes (2001, 2021, 2024-11, 2025-02, 2026-01 replacement series)."),
    ("Sunflower oil", "glob_wb_sunflower_oil", "Sunflower oil, EU/NW Europe FOB Rotterdam", "Starts 2002."),
    ("Rapeseed oil", "glob_wb_rapeseed_oil", "Rapeseed oil, Dutch, FOB Rotterdam", "Starts 2002."),
    ("Sugar, world", "glob_wb_sugar_world", "Sugar, ISA daily price raw, FOB Caribbean", ""),
    ("Sugar, EU", "glob_wb_sugar_eu", "Sugar, EU negotiated import price for raw ACP sugar, CIF European ports",
     "Administered/sticky price; see eu_agri_sugar_white for EU white sugar market price."),
    ("Cocoa", "glob_wb_cocoa", "Cocoa, ICCO daily price (NY/London futures avg)", ""),
    ("Coffee, Arabica", "glob_wb_coffee_arabica", "Coffee, Arabica, ICO other mild Arabicas, ex-dock", ""),
    ("Coffee, Robusta", "glob_wb_coffee_robusta", "Coffee, Robusta, ICO indicator, ex-dock", ""),
    ("Tea, avg 3 auctions", "glob_wb_tea", "Tea, average of Kolkata, Colombo and Mombasa auctions", ""),
    ("Beef **", "glob_wb_beef", "Beef (NZ 90% lean CIF US from 2024; Australian/NZ before)",
     "Replacement series Jan-2024 and Sep-2021."),
    ("Chicken **", "glob_wb_chicken", "Chicken (Brazil wholesale frozen from 2021-09; US broiler before)",
     "Source switched from USA to Brazil in Sep-2021 (level break)."),
    ("Orange", "glob_wb_orange", "Oranges, Mediterranean navel, EU indicative import price CIF Paris", ""),
    ("Banana, Europe", "glob_wb_banana_eu", "Bananas, EU import price", ""),
    ("Natural gas, Europe", "glob_wb_natgas_eu", "Natural gas Europe (Netherlands TTF from 2015-04; avg import border price before)",
     "TTF since Apr-2015; Jun-2000..Mar-2010 import border price excl UK; Apr-2010..Mar-2015 incl. spot component. "
     "Use as EU TTF gas proxy (daily TTF settlement data is not freely downloadable)."),
    ("Crude oil, Brent", "glob_wb_brent", "Crude oil, UK Brent 38 API, spot", ""),
    ("Coal, Australian", "glob_wb_coal_aus", "Coal, Australia thermal FOB Newcastle 6000 kcal/kg", ""),
    ("Urea ", "glob_wb_urea", "Urea, prill FOB Middle East (Black Sea before 2022-03)", ""),
    ("DAP", "glob_wb_dap", "DAP (diammonium phosphate), spot FOB US Gulf", ""),
    ("Aluminum", "glob_wb_aluminum", "Aluminum, LME primary ingots 99.7% (packaging cans/foil proxy)", ""),
    ("Tin", "glob_wb_tin", "Tin, LME refined 99.85% (tinplate/food can proxy)", ""),
]


@safe
def block_worldbank():
    print("== World Bank Pink Sheet")
    page = "https://www.worldbank.org/en/research/commodity-markets"
    html = http_get(page, "wb_page.html").text
    m = re.search(r'href="([^"]+CMO-Historical-Data-Monthly\.xlsx)"', html)
    url = m.group(1) if m else "https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx"
    http_get(url, "CMO-Historical-Data-Monthly.xlsx")
    path = DL / "CMO-Historical-Data-Monthly.xlsx"
    rel = "Pink Sheet published ~2nd business day of the following month; recent months may be revised."

    def ym(x):
        return pd.Timestamp(int(x[:4]), int(x[5:7]), 1)

    pr = pd.read_excel(path, sheet_name="Monthly Prices", header=None)
    hdr = pr.iloc[4].tolist()
    units = pr.iloc[5].tolist()
    data = pr[pr[0].astype(str).str.match(r"^\d{4}M\d{2}$")]
    idx = data[0].map(ym)
    for col, sid, desc, note in WB_PRICES:
        j = hdr.index(col)
        s = pd.Series(pd.to_numeric(data[j].replace({"…": np.nan, "...": np.nan}), errors="coerce").values, index=idx)
        unit = str(units[j]).strip("()").replace("$", "USD ")
        add(sid, s, description=f"World Bank: {desc}", country="GLOBAL", unit=f"{unit} (nominal)",
            source="World Bank Commodity Price Data (Pink Sheet)",
            source_query=f"{url} sheet 'Monthly Prices' column '{col.strip()}'", lag=3,
            notes=(rel + " " + note).strip())
        STORE[sid] = monthly_index(s)

    ix = pd.read_excel(path, sheet_name="Monthly Indices", header=None)
    data = ix[ix[0].astype(str).str.match(r"^\d{4}M\d{2}$")]
    idx = data[0].map(ym)
    # sanity-check the header layout (rows 5-8 hold the multi-level names)
    labels = ix.iloc[5:9].fillna("").astype(str).agg(" ".join).str.replace(r"\s+", " ", regex=True)
    for c, (sid, nm) in WB_INDEX_COLS.items():
        lab = labels[c]
        key = nm.split()[0].replace("-energy", "")
        if key.lower()[:5] not in lab.lower().replace("-", "").replace("  ", " ") and key[:5] not in lab:
            print(f"   WARNING: WB index column {c} label '{lab.strip()}' vs expected '{nm}'")
        s = pd.Series(pd.to_numeric(data[c], errors="coerce").values, index=idx)
        add(sid, s, description=f"World Bank commodity price index: {nm} (nominal USD)",
            country="GLOBAL", unit="Index 2010=100 (nominal USD)",
            source="World Bank Commodity Price Data (Pink Sheet)",
            source_query=f"{url} sheet 'Monthly Indices' column '{lab.strip()}'", lag=3,
            notes=rel + " Laspeyres index, weights based on 2002-2004 export values.")
        STORE[sid] = monthly_index(s)


# ----------------------------------------------------------------------------- FRED
def fred(series_id) -> pd.Series:
    r = http_get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
                 f"fred_{series_id}.csv", headers=UA_PLAIN)
    d = pd.read_csv(io.BytesIO(r.content))
    s = pd.Series(pd.to_numeric(d.iloc[:, 1], errors="coerce").values, index=pd.to_datetime(d.iloc[:, 0]))
    return s.dropna()


@safe
def block_fred():
    print("== FRED (IMF commodity indices, US PPIs, FX, US rates)")
    fq = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
    imf = [("PFOODINDEXM", "glob_imf_food_idx", "IMF Global price of Food index"),
           ("PFANDBINDEXM", "glob_imf_foodbev_idx", "IMF Global price of Food and Beverage index"),
           ("PALLFNFINDEXM", "glob_imf_allcomm_idx", "IMF Global price of All Commodities index")]
    for fid, sid, desc in imf:
        add(sid, fred(fid), description=desc + " (IMF Primary Commodity Prices, via FRED)",
            country="GLOBAL", unit="Index 2016=100 (nominal USD)", source="IMF PCPS via FRED",
            source_query=fq + fid, lag=60,
            notes="Cross-check for FAO/World Bank indices. IMF PCPS is updated monthly but FRED lags "
                  "~2 months (as of 2026-10 latest obs is 2026-07).")
    ppi = [("PCU325211325211", "us_ppi_plastic_resins_idx", "US PPI: Plastics material and resins manufacturing",
            "Index Jun 1976=100"),
           ("PCU327213327213", "us_ppi_glass_containers_idx", "US PPI: Glass container manufacturing",
            "Index Jun 1983=100 (FRED native base)"),
           ("PCU332431332431", "us_ppi_metal_cans_idx", "US PPI: Metal can manufacturing",
            "Index Jun 1983=100 (FRED native base)"),
           ("PCU322211322211", "us_ppi_corrugated_boxes_idx", "US PPI: Corrugated and solid fiber box manufacturing",
            "Index Mar 1980=100"),
           ("WPU0911", "us_ppi_wood_pulp_idx", "US PPI commodity: Wood pulp", "Index 1982=100"),
           ("PCU483111483111", "us_ppi_deep_sea_freight_idx",
            "US PPI: Deep sea freight transportation (ocean freight cost proxy)", "Index Jun 1988=100")]
    for fid, sid, desc, unit in ppi:
        add(sid, fred(fid), description=desc + " (packaging/freight cost proxy)", country="US",
            unit=unit, source="US BLS via FRED", source_query=fq + fid, lag=15,
            notes="BLS PPI released ~mid following month; last 4 months preliminary (revised).")

    # Broad USD index: monthly TWEXBGSMTH (2006-01=100) back-spliced with discontinued TWEXBMTH by growth rates
    new = monthly_index(fred("TWEXBGSMTH"))
    old = monthly_index(fred("TWEXBMTH"))
    base = new.index[0]
    ratio = new.loc[base] / old.loc[base]
    spliced = pd.concat([old[old.index < base] * ratio, new])
    add("glob_fx_usd_broad_idx", spliced, description="Nominal broad US dollar index (trade-weighted, "
        "goods and services), monthly average; higher = stronger USD", country="US",
        unit="Index Jan 2006=100", source="Federal Reserve Board H.10 via FRED",
        source_query=fq + "TWEXBGSMTH (2006-01 onward) + " + fq + "TWEXBMTH (1973-01..2005-12, rescaled)",
        lag=1, notes="Pre-2006 values = old broad index (TWEXBMTH, goods only, discontinued) rescaled to "
                     "match TWEXBGSMTH at 2006-01 (growth-rate splice).")
    fx = [("EXUSEU", "glob_fx_eurusd", "EUR/USD exchange rate, monthly average", "USD per EUR"),
          ("EXNOUS", "glob_fx_usdnok", "USD/NOK exchange rate, monthly average", "NOK per USD"),
          ("EXSDUS", "glob_fx_usdsek", "USD/SEK exchange rate, monthly average", "SEK per USD")]
    for fid, sid, desc, unit in fx:
        s = monthly_index(fred(fid))
        add(sid, s, description=desc + " (noon buying rates NY)", country="GLOBAL", unit=unit,
            source="Federal Reserve Board H.10 via FRED", source_query=fq + fid, lag=1,
            notes="Monthly average of daily rates; known in real time (H.10 monthly release first business day).")
        STORE[sid] = s
    add("us_fed_funds_rate", fred("FEDFUNDS"), description="US effective federal funds rate, monthly average",
        country="US", unit="% p.a.", source="Federal Reserve Board H.15 via FRED", source_query=fq + "FEDFUNDS",
        lag=1, notes="Known in real time.")
    add("us_treasury_10y", fred("GS10"), description="US 10-year Treasury constant maturity yield, monthly average",
        country="US", unit="% p.a.", source="Federal Reserve Board H.15 via FRED", source_query=fq + "GS10",
        lag=1, notes="Known in real time.")


# ----------------------------------------------------------------------------- Eurostat
def estat_series(dataset, **flt) -> pd.Series:
    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}"
    params = {"format": "JSON", **flt}
    r = http_get(url, f"estat_{dataset}_{flt.get('geo')}_{flt.get('nace_r2')}.json", params=params)
    d = r.json()
    t = d["dimension"]["time"]["category"]["index"]
    inv = {v: k for k, v in t.items()}
    vals = {inv[int(k)]: v for k, v in d["value"].items()}
    s = pd.Series(vals)
    s.index = pd.to_datetime(s.index, format="%Y-%m")
    return s.sort_index()


@safe
def block_eurostat():
    print("== Eurostat PPI paper / packaging")
    specs = [("EA20", "C17", "ea_ppi_paper_idx", "Euro area (EA20): domestic producer prices, manufacture of paper "
              "and paper products (NACE C17)"),
             ("EU27_2020", "C172", "eu_ppi_paper_packaging_idx", "EU27: domestic producer prices, articles of paper "
              "and paperboard incl. corrugated packaging (NACE C172)"),
             ("EU27_2020", "C222", "eu_ppi_plastic_products_idx", "EU27: domestic producer prices, plastic products "
              "incl. plastic packaging (NACE C222)")]
    for geo, nace, sid, desc in specs:
        s = estat_series("sts_inppd_m", freq="M", indic_bt="PRC_PRR_DOM", nace_r2=nace, s_adj="NSA",
                         unit="I21", geo=geo)
        add(sid, s, description=desc, country=geo, unit="Index 2021=100", source="Eurostat",
            source_query=f"sts_inppd_m M.PRC_PRR_DOM.{nace}.NSA.I21.{geo}", lag=35,
            notes="Eurostat STS release ~t+33-35d; packaging cost proxy for European food manufacturers.")


# ----------------------------------------------------------------------------- NY Fed GSCPI
@safe
def block_gscpi():
    print("== NY Fed GSCPI")
    url = "https://www.newyorkfed.org/medialibrary/research/interactives/gscpi/downloads/gscpi_data.xlsx"
    http_get(url, "gscpi_data.xls")
    df = pd.read_excel(DL / "gscpi_data.xls", sheet_name="GSCPI Monthly Data", header=None, engine="xlrd")
    d = pd.to_datetime(df[0], format="%d-%b-%Y", errors="coerce")
    s = pd.Series(pd.to_numeric(df[1], errors="coerce").values, index=d)
    s = s[s.index.notna()].dropna()
    add("glob_gscpi", s, description="NY Fed Global Supply Chain Pressure Index (freight costs, delivery "
        "times, backlogs, inventories from PMIs + BDI/Harpex/airfreight)", country="GLOBAL",
        unit="Standard deviations from average", source="Federal Reserve Bank of New York",
        source_query=url + " sheet 'GSCPI Monthly Data'", lag=5,
        notes="Published ~4th business day of following month; whole history re-estimated each month "
              "(small revisions). Starts 1998-01 in current vintage.")


# ----------------------------------------------------------------------------- EC agri-food portal
AGRI = "https://api.tech.ec.europa.eu/agrifood/api"


def agri_get(ep, fname, **params):
    r = http_get(f"{AGRI}/{ep}", fname, headers={**UA_BROWSER, "Accept": "application/json"}, params=params)
    if r.status_code != 200:
        raise RuntimeError(f"agri {ep} {r.status_code}: {r.text[:200]}")
    return r.json()


def parse_price(p) -> float:
    if p is None:
        return np.nan
    if isinstance(p, (int, float)):
        return float(p)
    s = re.sub(r"[^\d,.\-]", "", str(p))
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def weekly_to_monthly(recs) -> pd.Series:
    """Weekly records -> monthly mean; each week is assigned to the month containing its Thursday."""
    d = pd.to_datetime([r["beginDate"] for r in recs], format="%d/%m/%Y") + pd.Timedelta(days=3)
    v = [parse_price(r["price"]) for r in recs]
    s = pd.Series(v, index=d)
    s = s[~s.index.duplicated()]
    return to_monthly_mean(s)


@safe
def block_agri():
    print("== EC agri-food data portal")
    yrs = ",".join(str(y) for y in range(1990, TODAY.year + 1))
    end = TODAY.strftime("%d/%m/%Y")
    src = "European Commission, Agri-food data portal (DG AGRI)"
    wk_note = ("Weekly EU-average prices (member-state reports weighted by DG AGRI); aggregated to "
               "calendar-month mean of weekly quotes (week assigned to month containing its Thursday). "
               "Published ~1 week after the reference week. ")

    # raw milk (monthly)
    j = agri_get("rawMilk/prices", "agri_rawmilk.json", memberStateCodes="EU", products="Raw milk", years=yrs)
    s = pd.Series([parse_price(r["price"]) for r in j],
                  index=pd.to_datetime([r["beginDate"] for r in j], format="%d/%m/%Y"))
    add("eu_agri_raw_milk_price", s, description="EU average farm-gate raw cow milk price (real fat & protein)",
        country="EU", unit="EUR per 100 kg", source=src,
        source_query=f"{AGRI}/rawMilk/prices?memberStateCodes=EU&products=Raw milk&years=1990..",
        lag=40, notes="Monthly; API code 'EU-UK' = EU excl. UK (composition of EU aggregate changes over time).")

    # dairy commodities (weekly)
    j = agri_get("dairy/prices", "agri_dairy.json", memberStateCodes="EU", products="BUTTER,SMP,WMP", years=yrs)
    for prod, sid, desc in [("BUTTER", "eu_agri_butter_price", "EU average butter wholesale price"),
                            ("SMP", "eu_agri_smp_price", "EU average skimmed milk powder (SMP) price"),
                            ("WMP", "eu_agri_wmp_price", "EU average whole milk powder (WMP) price")]:
        recs = [r for r in j if r["product"] == prod]
        add(sid, weekly_to_monthly(recs), description=desc, country="EU", unit="EUR per 100 kg", source=src,
            source_query=f"{AGRI}/dairy/prices?memberStateCodes=EU&products={prod}&years=1990..",
            lag=7, notes=wk_note)

    # pigmeat (weekly) class E carcass
    j = agri_get("pigmeat/prices", "agri_pig.json", memberStateCodes="EU", pigClasses="E",
                 beginDate="01/01/1990", endDate=end)
    add("eu_agri_pig_carcass_e_price", weekly_to_monthly(j), description="EU average pig carcass price, class E",
        country="EU", unit="EUR per 100 kg carcass weight", source=src,
        source_query=f"{AGRI}/pigmeat/prices?memberStateCodes=EU&pigClasses=E", lag=7, notes=wk_note)

    # beef (weekly) young bulls R3
    j = agri_get("beef/prices", "agri_beef.json", memberStateCodes="EU", productCodes="AR3",
                 beginDate="01/01/1990", endDate=end)
    add("eu_agri_beef_young_bulls_r3_price", weekly_to_monthly(j),
        description="EU average beef carcass price, young bulls class R3 (reference grade)", country="EU",
        unit="EUR per 100 kg carcass weight", source=src,
        source_query=f"{AGRI}/beef/prices?memberStateCodes=EU&productCodes=AR3", lag=7, notes=wk_note)

    # poultry (monthly) whole broiler 65% selling price; products filter rejected by API -> filter locally
    j = agri_get("poultry/prices/month", "agri_poultry.json", memberStateCodes="EU", years=yrs)
    recs = [r for r in j if r.get("productName") == "Whole broiler (65%)" and r.get("priceType") == "Selling price"]
    s = pd.Series([parse_price(r["price"]) for r in recs],
                  index=pd.to_datetime([r["beginDate"] for r in recs], format="%d/%m/%Y"))
    add("eu_agri_broiler_price", s, description="EU average whole broiler (65% carcass) selling price",
        country="EU", unit="EUR per 100 kg", source=src,
        source_query=f"{AGRI}/poultry/prices/month?memberStateCodes=EU (productName='Whole broiler (65%)', priceType='Selling price')",
        lag=40, notes="Monthly EU average.")

    # cereals (weekly) - EU national-average series exist only from 2015-11 in the API
    j = agri_get("cereal/prices", "agri_cereal.json", memberStateCodes="EU",
                 productCodes="BLTPAN,ORGFOUR,ORGBRAS,MAI", beginDate="01/01/2010", endDate=end)
    # From marketing year 2026/27 (weeks from 2026-08-03) the EU average is reported with stage
    # 'Deliver to first customer ...' and wheat is labelled 'Milling wheat' instead of
    # 'Breadmaking common wheat'/'National Average - Not Specified' -> concatenated (no overlap).
    for pnames, sid, desc in [(("Breadmaking common wheat", "Milling wheat"), "eu_agri_wheat_bread_price",
                               "EU average breadmaking/milling common wheat price"),
                              (("Feed barley",), "eu_agri_barley_feed_price", "EU average feed barley price"),
                              (("Malting barley",), "eu_agri_barley_malting_price", "EU average malting barley price"),
                              (("Feed maize",), "eu_agri_maize_feed_price", "EU average feed maize price")]:
        old = [r for r in j if r["productName"] == pnames[0] and r["stageName"].startswith("National Average")]
        new = [r for r in j if r["productName"] in pnames and r["stageName"].startswith("Deliver to first customer")]
        so, sn = weekly_to_monthly(old), weekly_to_monthly(new)
        s = pd.concat([so, sn[sn.index > so.index.max()]]) if len(so) else sn
        add(sid, s, description=desc, country="EU", unit="EUR per tonne", source=src,
            source_query=f"{AGRI}/cereal/prices?memberStateCodes=EU&productCodes=BLTPAN,ORGFOUR,ORGBRAS,MAI "
                         f"(productName in {list(pnames)}; stage 'National Average' to 2026-07, "
                         f"'Deliver to first customer' from 2026-08)",
            lag=10, notes=wk_note + "EU average cereal series start 2015-11 in the API (older data only "
                                    "per market in archived Excel files). Reporting stage changed with marketing "
                                    "year 2026/27 (from 2026-08, 'Deliver to first customer'); pieces concatenated "
                                    "without overlap (possible small level break). Long history: glob_wb_wheat_us_hrw/srw.")

    # sugar (monthly) EU average white sugar ex-works price
    j = agri_get("sugar/prices", "agri_sugar.json", regions="EU Average")
    recs = [r for r in j if r.get("contractType") == "Monthly data"]
    s = pd.Series([parse_price(r["price"]) for r in recs],
                  index=pd.to_datetime([r["ym"].replace("/", "-") + "-01" for r in recs]))
    add("eu_agri_sugar_white_price", s, description="EU average white sugar market price (ex-works, sugar price "
        "reporting system)", country="EU", unit="EUR per tonne", source=src,
        source_query=f"{AGRI}/sugar/prices?regions=EU Average (contractType='Monthly data')", lag=95,
        notes="Monthly; published with ~3 month lag (contract prices reported by sugar producers).")


# ----------------------------------------------------------------------------- electricity
EDS = "https://api.energidataservice.dk/dataset/"


def eds_monthly(area_codes, dataset="Elspotprices", start="2000-01-01", end="2025-10-01"):
    if dataset == "Elspotprices":
        cols, tcol, pcol = "HourDK,PriceArea,SpotPriceEUR", "HourDK", "SpotPriceEUR"
    else:
        cols, tcol, pcol = "TimeDK,PriceArea,DayAheadPriceEUR", "TimeDK", "DayAheadPriceEUR"
    params = {"start": start, "end": end, "columns": cols, "limit": 0,
              "filter": json.dumps({"PriceArea": area_codes})}
    fn = f"eds_{dataset}_{'_'.join(area_codes)}_{start[:4]}.json"
    r = http_get(EDS + dataset, fn, params=params, timeout=600)
    rec = r.json()["records"]
    df = pd.DataFrame(rec)
    if df.empty:
        return pd.Series(dtype=float)
    s = pd.Series(pd.to_numeric(df[pcol], errors="coerce").values, index=pd.to_datetime(df[tcol])).dropna()
    m = to_monthly_mean(s)
    # keep only months with >= 90% of the expected number of price intervals (drops partial months,
    # e.g. the system price, which stops on 2025-02-06 in this dataset)
    per_day = 24 if dataset == "Elspotprices" else 96
    cnt = s.groupby(s.index.to_period("M")).size()
    cnt.index = cnt.index.to_timestamp()
    expected = pd.Series(cnt.index.days_in_month * per_day, index=cnt.index)
    full = cnt[cnt >= 0.9 * expected].index
    return m[m.index.isin(full)]


@safe
def block_electricity():
    print("== Nordic electricity (Energi Data Service, Ember)")
    switch = "2025-10-01"
    cur = CUR_MONTH.strftime("%Y-%m-%d")
    note_eds = ("Monthly arithmetic mean of hourly day-ahead (Elspot) prices (Danish local time); from 2025-10 "
                "mean of 15-minute day-ahead prices (dataset DayAheadPrices, after Nord Pool's 15-min MTU go-live). ")
    sys_m = eds_monthly(["SYS", "SYSTEM"], end=switch)
    add("nordic_elspot_system_price", sys_m, description="Nord Pool Nordic system price (unconstrained reference "
        "price), monthly average", country="NORDIC", unit="EUR per MWh", source="Energinet Energi Data Service (Nord Pool data)",
        source_query=EDS + 'Elspotprices?filter={"PriceArea":["SYS","SYSTEM"]}&columns=HourDK,PriceArea,SpotPriceEUR',
        lag=1, notes="Monthly mean of hourly prices ('SYS' to 2010, 'SYSTEM' from 2011). Series ends 2025-01: the "
                     "Elspotprices dataset stops carrying the system price on 2025-02-06 (partial month dropped), the "
                     "successor dataset DayAheadPrices has no system price, and Nord Pool's own history requires login.")
    for area, sid, ctry, desc in [("NO2", "no_elspot_no2_price", "NO", "Norway NO2 (Southwest, Kristiansand) bidding-zone day-ahead price"),
                                  ("SE3", "se_elspot_se3_price", "SE", "Sweden SE3 (Stockholm) bidding-zone day-ahead price"),
                                  ("DK1", "dk_elspot_dk1_price", "DK", "Denmark DK1 (West) bidding-zone day-ahead price")]:
        a = eds_monthly([area], end=switch)
        b = eds_monthly([area], dataset="DayAheadPrices", start=switch, end=cur)
        s = pd.concat([a[a.index < switch], b[b.index >= switch]])
        extra = ""
        if area == "SE3":
            # SE3 exists from 2011-11 (split of Sweden into SE1-SE4); before that use the single Swedish area 'SE'
            se = eds_monthly(["SE"], end="2011-11-01")
            s = pd.concat([se[se.index < s.index.min()], s])
            extra = ("Before 2011-11 (split of Sweden into SE1-SE4) the single Swedish area price ('SE' in the "
                     "dataset) is used.")
        if area == "NO2":
            extra = ("Norwegian bidding-zone definitions were reorganised several times before 2010; early values "
                     "are the dataset's NO2 mapping (southern Norway).")
        add(sid, drop_incomplete(s), description=desc + ", monthly average", country=ctry, unit="EUR per MWh",
            source="Energinet Energi Data Service (Nord Pool data)",
            source_query=EDS + f'Elspotprices?filter={{"PriceArea":["{area}"]}} (to 2025-09) + '
                         + EDS + f'DayAheadPrices?filter={{"PriceArea":["{area}"]}} (2025-10 onward)',
            lag=1, notes=note_eds + extra)

    url = "https://files.ember-energy.org/public-downloads/price/outputs/european_wholesale_electricity_price_data_monthly.csv"
    r = http_get(url, "ember_monthly.csv")
    em = pd.read_csv(io.BytesIO(r.content))
    for ctry, sid, cc, desc, note in [
            ("Finland", "fi_elspot_price", "FI", "Finland (FI bidding zone) day-ahead electricity price, monthly average",
             "Finland is a single bidding zone, so this equals the FI area price."),
            ("Norway", "no_elspot_country_avg_price", "NO", "Norway day-ahead electricity price, load-weighted average of "
             "bidding zones NO1-NO5, monthly average",
             "Substitute for NO1 (Oslo), for which no free long history was found; NO1 and NO2 dominate load. "
             "Long-history southern Norway price: no_elspot_no2_price.")]:
        sub = em[em["Country"] == ctry]
        s = pd.Series(pd.to_numeric(sub["Price (EUR/MWhe)"], errors="coerce").values, index=pd.to_datetime(sub["Date"]))
        add(sid, drop_incomplete(monthly_index(s)), description=desc, country=cc, unit="EUR per MWh",
            source="Ember (European wholesale electricity price data, from ENTSO-E day-ahead)",
            source_query=url + f" Country=={ctry}", lag=2,
            notes="Hourly ENTSO-E day-ahead prices aggregated by Ember (load-weighted monthly). Starts 2015-01. "
                  "Current partial month dropped. " + note)


# ----------------------------------------------------------------------------- derived
@safe
def block_derived():
    print("== Derived local-currency series")
    usdnok, eurusd = STORE["glob_fx_usdnok"], STORE["glob_fx_eurusd"]
    eurnok = (usdnok * eurusd).dropna()
    add("glob_fx_eurnok", eurnok, description="EUR/NOK cross rate derived from FRED monthly averages",
        country="GLOBAL", unit="NOK per EUR", source="Derived from Federal Reserve H.10 via FRED",
        source_query="EXNOUS * EXUSEU", lag=1,
        notes="eurnok_t = usdnok_t * eurusd_t (product of monthly averages; differs marginally from the "
              "monthly average of daily EURNOK). Starts 1999-01.")
    eurperusd = 1.0 / eurusd
    for base_id, sid_base, base_years, base_lbl in [
            ("fao_ffpi", "glob_fao_ffpi", ("2014", "2016"), "2014-2016"),
            ("glob_wb_food_idx", "glob_wb_food_idx", ("2010", "2010"), "2010")]:
        x = STORE[base_id]
        for cur, fxs, cname in [("nok", usdnok, "NOK"), ("eur", eurperusd, "EUR")]:
            fx = fxs.dropna()
            fbase = fx.loc[base_years[0]:base_years[1]].mean()
            y = (x * fx / fbase).dropna()
            add(f"{sid_base}_{cur}", y,
                description=f"{'FAO Food Price Index' if base_id == 'fao_ffpi' else 'World Bank food price index'} "
                            f"converted to {cname} (local-currency import-cost pressure)",
                country="GLOBAL", unit=f"Index {base_lbl}=100 approx. ({cname} terms)",
                source="Derived (FAO / World Bank and FRED FX)",
                source_query=f"{sid_base} * {'EXNOUS' if cur == 'nok' else '1/EXUSEU'} / mean({base_lbl})",
                lag=6 if base_id == "fao_ffpi" else 3,
                notes=f"Formula: idx_{cname}_t = idx_USD_t * FX_t / mean(FX over {base_lbl}), FX = {cname} per USD "
                      f"monthly average ({'FRED EXNOUS' if cur == 'nok' else '1/FRED EXUSEU'}). Same base period as "
                      f"the USD index so the base-period average is ~100.")


# ----------------------------------------------------------------------------- main
def main():
    global DL
    ap = argparse.ArgumentParser()
    ap.add_argument("--dl", default=None)
    a = ap.parse_args()
    DL = Path(a.dl) if a.dl else Path(tempfile.mkdtemp(prefix="macro_global_"))
    DL.mkdir(parents=True, exist_ok=True)
    print("download dir:", DL)
    for blk in (block_fao, block_worldbank, block_fred, block_eurostat, block_gscpi, block_agri,
                block_electricity, block_derived):
        blk()
    cat = pd.DataFrame(CATALOG)
    cols = ["series_id", "file", "description", "country", "frequency", "unit", "seasonal_adjustment", "start",
            "end", "n_obs", "source", "source_query", "approx_release_lag_days", "notes"]
    cat = cat[cols].sort_values("series_id")
    cat.to_csv(OUT / "catalog.csv", index=False)
    print(f"\n{len(cat)} series written; failures: {FAILURES}")
    (DL / "failures.json").write_text(json.dumps(FAILURES, indent=1))


if __name__ == "__main__":
    main()
