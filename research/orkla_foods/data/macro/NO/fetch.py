#!/usr/bin/env python3
"""
Fetch Norwegian macro / market time series for the Orkla Foods predictor analysis.

Output: one CSV per series (columns date,value) in the directory of this script,
plus catalog.csv describing every series.

Conventions
-----------
* date = first day of the period (monthly YYYY-MM-01, quarterly first month of the
  quarter, annual YYYY-01-01).
* Daily data (policy rate, Nord Pool spot prices) are aggregated to monthly means.
* Native frequency is otherwise kept.

Sources (all public, no API key needed)
---------------------------------------
* Statistics Norway (SSB) PxWebApi v0:  https://data.ssb.no/api/v0/en/table/<id>
* Norges Bank SDMX API:                https://data.norges-bank.no/api/data/<flow>/<key>
* OECD SDMX (MEI financial market):    https://sdmx.oecd.org/public/rest/data/...
  (3-month NIBOR = OECD IR3TIB for Norway; 10y government bond = OECD IRLT,
   both sourced by OECD from Norges Bank; used because Norges Bank's own
   generic-yield flow only starts in 2019 and NIBOR is not in Norges Bank's API).
* NAV (Norwegian Labour and Welfare Administration) seasonally adjusted
  registered unemployment files from nav.no (see NAV_* constants below; the
  attachment URLs change every month -> the script scrapes the statistics page
  for the current file names).
* Energinet "Energi Data Service" API (Nord Pool day-ahead prices, NO2 and
  system price): datasets Elspotprices (to 2025-09-30, hourly) and
  DayAheadPrices (from 2025-10-01, 15-minute).
* NIBIO "Jordbrukets prisindeks" (agricultural output price index incl.
  subsidies, annual) scraped from https://www.nibio.no/tjenester/jordbrukets-prisindeks
* Hand-compiled tables (in this file): food VAT rate history and the annual
  agricultural settlement (jordbruksoppgjoret) frameworks / target price
  changes, with the documents used listed next to the data.

Usage:  python3 fetch.py [--only series_prefix]
"""
import io
import json
import re
import sys
import time
import html as htmlmod
from pathlib import Path

import numpy as np
import pandas as pd
import requests

OUT = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SSB = "https://data.ssb.no/api/v0/en/table/"
NB = "https://data.norges-bank.no/api/data/"

CATALOG = []


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def http_get(url, **kw):
    for i in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=kw.pop("timeout", 120), **kw)
            if r.status_code == 429:
                time.sleep(60 * (i + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == 3:
                raise
            time.sleep(5 * (i + 1))


def parse_period(p):
    """SSB / SDMX period strings -> Timestamp (first day of period)."""
    p = str(p).strip()
    m = re.fullmatch(r"(\d{4})M(\d{2})", p)
    if m:
        return pd.Timestamp(int(m.group(1)), int(m.group(2)), 1)
    m = re.fullmatch(r"(\d{4})K(\d)", p)
    if m:
        return pd.Timestamp(int(m.group(1)), 3 * int(m.group(2)) - 2, 1)
    m = re.fullmatch(r"(\d{4})-Q(\d)", p)
    if m:
        return pd.Timestamp(int(m.group(1)), 3 * int(m.group(2)) - 2, 1)
    m = re.fullmatch(r"(\d{4})-(\d{2})", p)
    if m:
        return pd.Timestamp(int(m.group(1)), int(m.group(2)), 1)
    m = re.fullmatch(r"(\d{4})", p)
    if m:
        return pd.Timestamp(int(m.group(1)), 1, 1)
    return pd.Timestamp(p)


def ssb(table, selection):
    """POST a PxWeb v0 query. selection: {var_code: [values]}; Tid -> all periods.
    Returns long DataFrame with one column per dimension (codes) + 'value'."""
    q = [{"code": k, "selection": {"filter": "item", "values": v}} for k, v in selection.items()]
    body = {"query": q, "response": {"format": "json-stat2"}}
    for i in range(4):
        r = requests.post(SSB + table, json=body, headers=UA, timeout=180)
        if r.status_code == 429:
            time.sleep(15 * (i + 1))
            continue
        r.raise_for_status()
        break
    d = r.json()
    ids, sizes = d["id"], d["size"]
    cats = []
    for dim in ids:
        idx = d["dimension"][dim]["category"]["index"]
        if isinstance(idx, dict):
            codes = sorted(idx, key=lambda c: idx[c])
        else:
            codes = list(idx)
        cats.append(codes)
    grid = pd.MultiIndex.from_product(cats, names=ids).to_frame(index=False)
    vals = d["value"]
    if isinstance(vals, dict):  # sparse
        full = [None] * int(np.prod(sizes))
        for k, v in vals.items():
            full[int(k)] = v
        vals = full
    grid["value"] = pd.to_numeric(pd.Series(vals), errors="coerce")
    time.sleep(1.0)  # be nice to the API (rate limit ~30 req / 60 s)
    return grid


def ssb_series(table, selection, time_dim="Tid"):
    df = ssb(table, selection)
    s = pd.Series(df["value"].values, index=df[time_dim].map(parse_period)).sort_index()
    return s.dropna()


def nb_series(key, start="1950"):
    url = f"{NB}{key}?format=csv&locale=en&startPeriod={start}"
    df = pd.read_csv(io.StringIO(http_get(url).text), sep=";")
    s = pd.Series(pd.to_numeric(df["OBS_VALUE"], errors="coerce").values,
                  index=pd.to_datetime(df["TIME_PERIOD"].astype(str).map(
                      lambda x: x if len(x) > 7 else x + "-01")))
    return s.sort_index().dropna()


def ratio_splice(new, old):
    """Extend `new` backwards with growth rates of `old` (ratio at first new obs)."""
    first = new.index.min()
    if first not in old.index:
        raise ValueError("no overlap for splice")
    k = new.loc[first] / old.loc[first]
    back = old[old.index < first] * k
    return pd.concat([back, new]).sort_index()


def save(series_id, s, description, frequency, unit, sa, source, query,
         lag, notes="", country="NO", decimals=6):
    s = s.dropna().sort_index()
    if s.empty:
        print(f"  !! {series_id}: empty series, not saved")
        return
    s = s[~s.index.duplicated(keep="last")]
    df = pd.DataFrame({"date": s.index.strftime("%Y-%m-%d"), "value": np.round(s.values.astype(float), decimals)})
    fn = f"{series_id}.csv"
    df.to_csv(OUT / fn, index=False)
    CATALOG.append(dict(series_id=series_id, file=fn, description=description, country=country,
                        frequency=frequency, unit=unit, seasonal_adjustment=sa,
                        start=df["date"].iloc[0], end=df["date"].iloc[-1], n_obs=len(df),
                        source=source, source_query=query, approx_release_lag_days=lag, notes=notes))
    print(f"  saved {series_id:40s} {df['date'].iloc[0]} .. {df['date'].iloc[-1]}  n={len(df)}")


def step(name):
    print(f"[{time.strftime('%H:%M:%S')}] {name}", flush=True)


# ----------------------------------------------------------------------------
# 1. Consumer prices (SSB)
# ----------------------------------------------------------------------------
def cpi():
    step("CPI")
    # CPI total, monthly since 1920 (2025=100)
    s = ssb_series("14710", {"ContentsCode": ["KpiIndMnd"]})
    save("no_cpi_total_idx", s, "Consumer price index (CPI), all items", "M", "index 2025=100", "NSA",
         "SSB table 14710", "14710 ContentsCode=KpiIndMnd", 10,
         "Official CPI since 1920 (rebased by SSB to 2025=100 in 2026).")

    # CPI-ATE (core) and CPI-AT, monthly since 1995
    df = ssb("14706", {"KPIavledetSerie": ["KPI-JAE", "KPI-JA"], "ContentsCode": ["KPIJustIndMnd"]})
    for code, sid, desc in [("KPI-JAE", "no_cpi_ate_idx", "CPI adjusted for tax changes and excluding energy products (CPI-ATE, core)"),
                            ("KPI-JA", "no_cpi_at_idx", "CPI adjusted for tax changes (CPI-AT)")]:
        x = df[df.KPIavledetSerie == code]
        s = pd.Series(x.value.values, index=x.Tid.map(parse_period)).sort_index()
        save(sid, s, desc, "M", "index 2025=100", "NSA", "SSB table 14706",
             f"14706 KPIavledetSerie={code} ContentsCode=KPIJustIndMnd", 10)
    s = ssb_series("14708", {"KPIavledetSerie": ["KPI-JAE"], "ContentsCode": ["KPIsesong"]})
    save("no_cpi_ate_sa_idx", s, "CPI-ATE, seasonally adjusted", "M", "index 2025=100", "SA",
         "SSB table 14708", "14708 KPIavledetSerie=KPI-JAE ContentsCode=KPIsesong", 10,
         "SSB backcast to 1985 for the seasonally adjusted CPI-ATE.")

    # Food groups, COICOP 2018 (table 14700, from 2000M01), 2025=100
    groups = [
        ("01", "no_cpi_food_bev_idx", "CPI food and non-alcoholic beverages (COICOP 01)"),
        ("01.1", "no_cpi_food_idx", "CPI food (COICOP 01.1)"),
        ("01.2", "no_cpi_nonalc_bev_idx", "CPI non-alcoholic beverages (COICOP 01.2)"),
        ("01.1.1", "no_cpi_food_cereals_idx", "CPI cereals and cereal products incl. bread (COICOP 2018 01.1.1)"),
        ("01.1.2", "no_cpi_food_meat_idx", "CPI meat (COICOP 2018 01.1.2)"),
        ("01.1.3", "no_cpi_food_fish_idx", "CPI fish and other seafood (COICOP 2018 01.1.3)"),
        ("01.1.4", "no_cpi_food_dairy_eggs_idx", "CPI milk, other dairy products and eggs (COICOP 2018 01.1.4)"),
        ("01.1.5", "no_cpi_food_oils_fats_idx", "CPI oils and fats (COICOP 2018 01.1.5)"),
        ("01.1.6", "no_cpi_food_fruit_idx", "CPI fruits and nuts (COICOP 2018 01.1.6)"),
        ("01.1.7", "no_cpi_food_vegetables_idx", "CPI vegetables, tubers and pulses incl. potatoes (COICOP 2018 01.1.7)"),
        ("01.1.8", "no_cpi_food_sugar_confect_idx", "CPI sugar, confectionery and desserts incl. chocolate and ice cream (COICOP 2018 01.1.8)"),
        ("01.1.9", "no_cpi_food_other_idx", "CPI ready-made food and other food products (COICOP 2018 01.1.9)"),
    ]
    df = ssb("14700", {"VareTjenesteGrp": [g[0] for g in groups], "ContentsCode": ["KpiIndMnd"]})
    # old table 03013 (COICOP 1999, 2015=100, 1979M01-2025M12) to extend the groups before mid-2000
    old = ssb("03013", {"Konsumgrp": [g[0] for g in groups], "ContentsCode": ["KpiIndMnd"]})
    for code, sid, desc in groups:
        x = df[df.VareTjenesteGrp == code]
        s = pd.Series(x.value.values, index=x.Tid.map(parse_period)).sort_index().dropna()
        first = s.index.min().strftime("%Y-%m")
        notes = (f"SSB COICOP 2018 classification (introduced Jan 2026, back-calculated by SSB to {first}). "
                 f"Before {first} extended with growth rates of the closed COICOP-1999 series of the same code "
                 f"(SSB table 03013, 2015=100), ratio-spliced at {first}.")
        if code.count(".") == 2:
            notes += (" Note: COICOP 1999 vs 2018 sub-group definitions differ slightly (e.g. pizza/quiche was in "
                      "old 01.1.1, ready meals in 01.1.9; ice cream in 01.1.8 in both).")
        query = f"14700 VareTjenesteGrp={code} ContentsCode=KpiIndMnd; 03013 Konsumgrp={code} ContentsCode=KpiIndMnd (before {first})"
        o = old[old.Konsumgrp == code]
        os_ = pd.Series(o.value.values, index=o.Tid.map(parse_period)).sort_index().dropna()
        s = ratio_splice(s, os_)
        save(sid, s, desc, "M", "index 2025=100", "NSA", "SSB tables 14700 + 03013", query, 10, notes)

    # CPI-AT food (adjusted for tax changes, i.e. VAT changes on food removed)
    s = ssb_series("14704", {"KPIavledetSerie": ["KPI-JA"], "VareTjenesteGrp": ["01"],
                             "ContentsCode": ["KPIJustIndMnd"]})
    save("no_cpi_at_food_bev_idx", s, "CPI-AT (adjusted for tax changes) food and non-alcoholic beverages",
         "M", "index 2025=100", "NSA", "SSB table 14704",
         "14704 KPIavledetSerie=KPI-JA VareTjenesteGrp=01 ContentsCode=KPIJustIndMnd", 10,
         "Removes the direct effect of VAT/excise changes (e.g. food VAT changes 2005-2012).")


# ----------------------------------------------------------------------------
# 2. Producer & import prices (SSB)
# ----------------------------------------------------------------------------
def producer_import_prices():
    step("PPI / first-hand / import prices")
    df = ssb("12462", {"Marked": ["01"], "NaringUtenriks": ["SNN10", "SNN101", "SNN108"],
                       "ContentsCode": ["Indeksnivo"]})
    for code, sid, desc in [("SNN10", "no_ppi_food_dom_idx", "Producer price index, manufacture of food products (NACE 10), domestic market"),
                            ("SNN101", "no_ppi_meat_dom_idx", "Producer price index, processing of meat and meat products (NACE 10.1), domestic market"),
                            ("SNN108", "no_ppi_otherfood_dom_idx", "Producer price index, manufacture of other food products (NACE 10.8: bakery excl., sugar, cocoa/chocolate, coffee, condiments, ready meals...), domestic market")]:
        x = df[df.NaringUtenriks == code]
        s = pd.Series(x.value.values, index=x.Tid.map(parse_period)).sort_index()
        save(sid, s, desc, "M", "index 2021=100", "NSA", "SSB table 12462",
             f"12462 Marked=01 NaringUtenriks={code} ContentsCode=Indeksnivo", 10)

    # Price index of first-hand domestic sales (PIF): import market = import prices of goods sold first-hand in Norway
    df = ssb("03675", {"Marked": ["4", "2"], "SITC": ["SITC0", "SITC04", "SITC07", "SITCT"],
                       "ContentsCode": ["Indeksniva"]})
    spec = [("4", "SITC0", "no_imp_price_food_idx", "Import price index for food (SITC 0, food and live animals): price index of first-hand domestic sales, import market"),
            ("4", "SITC04", "no_imp_price_cereals_idx", "Import price index, cereals and cereal preparations (SITC 04), first-hand domestic sales, import market"),
            ("4", "SITC07", "no_imp_price_coffee_cocoa_idx", "Import price index, coffee, tea, cocoa, spices (SITC 07), first-hand domestic sales, import market"),
            ("4", "SITCT", "no_imp_price_total_idx", "Import price index, all goods (all SITC groups), first-hand domestic sales, import market"),
            ("2", "SITC0", "no_dom_price_food_pif_idx", "Price index of first-hand domestic sales, domestically produced food (SITC 0), domestic market")]
    for mk, code, sid, desc in spec:
        x = df[(df.Marked == mk) & (df.SITC == code)]
        s = pd.Series(x.value.values, index=x.Tid.map(parse_period)).sort_index().dropna()
        s = s[s.index >= "1990-01-01"]
        save(sid, s, desc, "M", "index 2021=100", "NSA", "SSB table 03675",
             f"03675 Marked={mk} SITC={code} ContentsCode=Indeksniva", 10,
             "PIF = 'Prisindeks for forstehandsomsetning'; import market measures prices of imported goods at first-hand sale in Norway (NOK, incl. FX effects).")

    # External trade price index (unit-value based), quarterly, imports SITC 0
    s = ssb_series("08241", {"ImpEks": ["1"], "ImpEkspGr": ["0"], "ContentsCode": ["Prisindeks"]})
    save("no_trade_imp_price_food_q_idx", s, "External trade price index, imports of food and live animals (SITC 0)",
         "Q", "index 2000=100", "NSA", "SSB table 08241",
         "08241 ImpEks=1 ImpEkspGr=0 ContentsCode=Prisindeks", 24,
         "Unit-value based external trade price index (chain-linked, 2000=100).")


# ----------------------------------------------------------------------------
# 3. Retail trade, consumption, national accounts (SSB)
# ----------------------------------------------------------------------------
def activity():
    step("Retail / consumption / national accounts")
    df = ssb("07129", {"NACE": ["47", "47.11"], "ContentsCode": ["VolumSesong", "VerdiinSesong"]})
    spec = [("47", "VolumSesong", "no_retail_vol_sa_idx", "Retail trade volume index, retail trade except motor vehicles (NACE 47)", "volume index 2021=100"),
            ("47.11", "VolumSesong", "no_retail_foodstores_vol_sa_idx", "Retail trade volume index, non-specialised stores with food predominating (NACE 47.11, grocery stores)", "volume index 2021=100"),
            ("47.11", "VerdiinSesong", "no_retail_foodstores_val_sa_idx", "Retail trade value (sales) index, non-specialised stores with food predominating (NACE 47.11, grocery stores)", "value index 2021=100")]
    for nace, cc, sid, desc, unit in spec:
        x = df[(df.NACE == nace) & (df.ContentsCode == cc)]
        s = pd.Series(x.value.values, index=x.Tid.map(parse_period)).sort_index()
        save(sid, s, desc, "M", unit, "SA", "SSB table 07129", f"07129 NACE={nace} ContentsCode={cc}", 28,
             "SIC2007; SSB moves to SIC2025 from 2026 reference periods in some statistics - check for breaks when updating.")

    df = ssb("05333", {"Varer": ["VAREKONSUM", "MAT"], "ContentsCode": ["Sesongjustert"]})
    for code, sid, desc in [("VAREKONSUM", "no_hh_goods_cons_vol_sa_idx", "Index of household consumption of goods (varekonsumindeks), total, volume"),
                            ("MAT", "no_hh_food_cons_vol_sa_idx", "Index of household consumption of goods: food, beverages and tobacco, volume")]:
        x = df[df.Varer == code]
        s = pd.Series(x.value.values, index=x.Tid.map(parse_period)).sort_index()
        save(sid, s, desc, "M", "volume index 2005=100", "SA", "SSB table 05333",
             f"05333 Varer={code} ContentsCode=Sesongjustert", 40,
             "DISCONTINUED by SSB after 2025-06 (replaced by monthly national accounts; see no_mna_hh_goods_cons_sa_mnok for total goods).")

    s = ssb_series("11721", {"Makrost": ["koh.nr61vare"], "ContentsCode": ["FastePriserSesJust"]})
    save("no_mna_hh_goods_cons_sa_mnok", s, "Monthly national accounts: household final consumption expenditure on goods, constant 2023 prices",
         "M", "NOK million, constant 2023 prices", "SA", "SSB table 11721",
         "11721 Makrost=koh.nr61vare ContentsCode=FastePriserSesJust", 58,
         "Successor of the household goods consumption index; starts 2016-01.")

    df = ssb("09190", {"Makrost": ["koh.nr61_", "koh.nr61vare", "bnpb.nr23_9fn"], "ContentsCode": ["FastePriserSesJust"]})
    for code, sid, desc in [("koh.nr61_", "no_qna_hh_cons_sa_mnok", "Quarterly national accounts: household final consumption expenditure, constant 2023 prices"),
                            ("koh.nr61vare", "no_qna_hh_goods_cons_sa_mnok", "Quarterly national accounts: household consumption of goods, constant 2023 prices"),
                            ("bnpb.nr23_9fn", "no_gdp_mainland_sa_mnok", "GDP Mainland Norway (market values), constant 2023 prices")]:
        x = df[df.Makrost == code]
        s = pd.Series(x.value.values, index=x.Tid.map(parse_period)).sort_index()
        save(sid, s, desc, "Q", "NOK million, constant 2023 prices", "SA", "SSB table 09190",
             f"09190 Makrost={code} ContentsCode=FastePriserSesJust", 50)
    s = ssb_series("14658", {"UtgifterHushold": ["pub61A"], "ContentsCode": ["FastePriserSesJust"]})
    save("no_qna_hh_food_cons_sa_mnok", s, "Quarterly national accounts: household consumption of food and non-alcoholic beverages, constant 2023 prices",
         "Q", "NOK million, constant 2023 prices", "SA", "SSB table 14658",
         "14658 UtgifterHushold=pub61A ContentsCode=FastePriserSesJust", 50)

    # cross-border shopping (two surveys; break in 2023 -> stored separately)
    df = ssb("08460", {"ContentsCode": ["Grenseh", "Turer"]})
    for cc, sid, desc, unit in [("Grenseh", "no_border_trade_exp_mnok_s1", "Cross-border shopping by Norwegians on same-day trips abroad, expenditure (old survey 2004-2022)", "NOK million"),
                                ("Turer", "no_border_trade_trips_s1", "Cross-border shopping same-day trips abroad, number of trips (old survey 2004-2022)", "1000 trips")]:
        x = df[df.ContentsCode == cc]
        s = pd.Series(x.value.values, index=x.Tid.map(parse_period)).sort_index()
        save(sid, s, desc, "Q", unit, "NSA", "SSB table 08460 (closed)", f"08460 ContentsCode={cc}", 42,
             "Closed series; new survey from 2023 in *_s2 (not directly comparable).")
    df = ssb("14044", {"ContentsCode": ["Grenseh", "Dagsturer"]})
    for cc, sid, desc, unit in [("Grenseh", "no_border_trade_exp_mnok_s2", "Cross-border shopping by Norwegians on same-day trips abroad, expenditure (new survey from 2023)", "NOK million"),
                                ("Dagsturer", "no_border_trade_trips_s2", "Cross-border shopping same-day trips abroad, number of trips (new survey from 2023)", "1000 trips")]:
        x = df[df.ContentsCode == cc]
        s = pd.Series(x.value.values, index=x.Tid.map(parse_period)).sort_index()
        save(sid, s, desc, "Q", unit, "NSA", "SSB table 14044", f"14044 ContentsCode={cc}", 42,
             "New survey design from 2023Q1; break vs *_s1.")


# ----------------------------------------------------------------------------
# 4. Labour market
# ----------------------------------------------------------------------------
def labour():
    step("Labour market")
    s = ssb_series("13760", {"Kjonn": ["0"], "Alder": ["15-74"], "Justering": ["S"], "ContentsCode": ["ArbledProsArbstyrk"]})
    save("no_lfs_unemp_rate_sa", s, "LFS (AKU) unemployment rate, 15-74 years", "M", "percent of labour force", "SA",
         "SSB table 13760", "13760 Kjonn=0 Alder=15-74 Justering=S ContentsCode=ArbledProsArbstyrk", 23,
         "Break-adjusted (2021 LFS redesign) monthly SA series from SSB; starts 2006-01.")
    s = ssb_series("05110", {"ArbStyrkStatus": ["2"], "Kjonn": ["0"], "Alder": ["15-74"], "ContentsCode": ["Prosent"]})
    save("no_lfs_unemp_rate_q_nsa", s, "LFS (AKU) unemployment rate, 15-74 years, quarterly", "Q", "percent of labour force", "NSA",
         "SSB table 05110", "05110 ArbStyrkStatus=2 Kjonn=0 Alder=15-74 ContentsCode=Prosent", 44,
         "Longer history (1988Q2-) but NSA and with methodological breaks (2006, 2021).")

    # NAV registered unemployment (helt ledige), seasonally adjusted
    navbase = "https://www.nav.no/no/nav-og-samfunn/statistikk/arbeidssokere-og-stillinger-statistikk/"
    hp = "".join(http_get(navbase + p).text for p in ["helt-ledige", "historisk-statistikk", "hovedtall-om-arbeidsmarkedet"])
    links = sorted(set(l.replace("\\u0026", "&") for l in re.findall(r'/_/attachment/download/[^"\\]+', hp)))
    find = lambda pat: next(("https://www.nav.no" + l for l in links if re.search(pat, requests.utils.unquote(l))), None)
    url_hist = find(r"Helt_ledige_Sesong_justert_1951_\d{4}\.csv")
    url_sa = find(r"NAV_Sesongjusterte_landet_.*\.csv")
    url_x = find(r"HARB100 Sesongjusterte hovedtall.*\.xlsx")
    hist = pd.read_csv(io.StringIO(http_get(url_hist).content.decode("utf-8-sig")), sep=";")
    hist.index = pd.to_datetime(hist.iloc[:, 0].astype(str) + "01", format="%Y%m%d")
    hist = pd.to_numeric(hist.iloc[:, 1], errors="coerce")
    cur = pd.read_csv(io.StringIO(http_get(url_sa).content.decode("utf-8-sig")), sep=";")
    cur.index = pd.to_datetime(cur["Aar_maaned"].astype(str) + "01", format="%Y%m%d")
    cur = pd.to_numeric(cur["Helt_ledige_sesjust"], errors="coerce").dropna()
    lvl = ratio_splice(cur, hist)
    save("no_nav_unemp_level_sa", lvl, "NAV registered fully unemployed persons (helt ledige)", "M", "persons", "SA",
         "NAV (nav.no) seasonally adjusted series", f"{url_hist.split('/')[-1]} (1951-) + {url_sa.split('/')[-1]} (2011-)", 3,
         "NAV latest SA vintage from 2011-01, earlier months from NAV's 1951- SA file ratio-spliced at 2011-01. "
         "NAV notes a break in April 2025 (modernisation of registers).")
    xl = pd.read_excel(io.BytesIO(http_get(url_x).content), sheet_name="Helt ledige pst", header=None)
    rows = []
    for _, r in xl.iterrows():
        if isinstance(r.iloc[1], (int, float, np.integer)) and not pd.isna(r.iloc[1]) and 1900 < r.iloc[1] < 2100:
            for m in range(12):
                v = r.iloc[2 + m]
                if v is not None and not pd.isna(v):
                    rows.append((pd.Timestamp(int(r.iloc[1]), m + 1, 1), float(v)))
    rate = pd.Series(dict(rows)).sort_index()
    save("no_nav_unemp_rate_sa", rate, "NAV registered unemployment rate (helt ledige in percent of labour force)", "M",
         "percent of labour force", "SA", "NAV (nav.no) HARB100 'Sesongjusterte hovedtall'",
         f"{url_x.split('/')[-1]} sheet 'Helt ledige pst'", 3,
         "Published with one decimal; labour force base from LFS until 2021, register-based from 2022.")


# ----------------------------------------------------------------------------
# 5. Interest rates and credit
# ----------------------------------------------------------------------------
def rates():
    step("Rates / credit / housing")
    d = nb_series("IR/B.KPRA.SD.R", start="1991-01-01")
    m = d.groupby(d.index.to_period("M")).mean()
    m.index = m.index.to_timestamp()
    m = m[m.index < pd.Timestamp.today().normalize().replace(day=1)]  # complete months only
    save("no_policy_rate", m, "Norges Bank key policy rate (sight deposit rate), monthly average of daily observations",
         "M", "percent p.a.", "NSA", "Norges Bank SDMX", "IR/B.KPRA.SD.R (daily business-day values averaged per month)", 0,
         "Daily business-day observations averaged to calendar months; current incomplete month dropped.")

    url = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/NOR.M.IR3TIB+IRLT.PA.....?"
           "startPeriod=1979-01&dimensionAtObservation=AllDimensions&format=csvfilewithlabels")
    df = pd.read_csv(io.StringIO(http_get(url).text))
    for meas, sid, desc in [("IR3TIB", "no_nibor_3m", "3-month NIBOR (OECD short-term interest rate for Norway), monthly average"),
                            ("IRLT", "no_govbond_10y", "10-year Norwegian government bond yield (OECD long-term interest rate), monthly average")]:
        x = df[df.MEASURE == meas]
        s = pd.Series(x.OBS_VALUE.values, index=x.TIME_PERIOD.map(parse_period)).sort_index()
        save(sid, s, desc, "M", "percent p.a.", "NSA", "OECD MEI financial market (DF_FINMARK), data from Norges Bank",
             f"OECD.SDD.STES,DSD_STES@DF_FINMARK NOR.M.{meas}.PA", 5,
             "OECD monthly averages of daily data. Norges Bank's own generic-yield flow (GOVT_GENERIC_RATES) starts only in 2019.")

    s = ssb_series("07200", {"Laangiver960": ["02"], "Utlanstype": ["00b"], "Sektor": ["04b"], "ContentsCode": ["Utlaan"]})
    save("no_hh_loan_rate_q", s, "Average interest rate on outstanding loans to households, banks and mortgage companies (all loans)",
         "Q", "percent p.a.", "NSA", "SSB table 07200",
         "07200 Laangiver960=02 Utlanstype=00b Sektor=04b ContentsCode=Utlaan", 38,
         "End-of-quarter interest rate on outstanding loans; complete census.")
    s = ssb_series("10745", {"Utlanstype": ["04"], "Sektor": ["04b"], "ContentsCode": ["RenterUtestaende"]})
    save("no_hh_mortgage_rate", s, "Average interest rate on outstanding loans secured on dwellings, households (sample of banks and mortgage companies)",
         "M", "percent p.a.", "NSA", "SSB table 10745",
         "10745 Utlanstype=04 Sektor=04b ContentsCode=RenterUtestaende", 25, "Monthly series starts 2013-12.")

    s = ssb_series("11599", {"Valuta": ["00"], "Lantaker2": ["Kred04"], "ContentsCode": ["AarsTrans2"]})
    save("no_credit_hh_c2_yoy", s, "Credit indicator C2, households: 12-month growth in domestic loan debt", "M",
         "percent (12-month growth, transactions based)", "NSA", "SSB table 11599",
         "11599 Valuta=00 Lantaker2=Kred04 ContentsCode=AarsTrans2", 30, "Growth rate only (transactions based, excludes breaks in stock).")
    s = ssb_series("07221", {"Region": ["TOTAL"], "Boligtype": ["00"], "ContentsCode": ["Boligindeks"]})
    save("no_house_price_idx", s, "Price index for existing dwellings, whole country, all dwelling types", "Q",
         "index 2015=100", "NSA", "SSB table 07221",
         "07221 Region=TOTAL Boligtype=00 ContentsCode=Boligindeks", 25,
         "Unadjusted index used because it starts 1992Q1 (the SA variant in the same table starts only 2005Q1).")


# ----------------------------------------------------------------------------
# 6. Exchange rates (Norges Bank monthly averages)
# ----------------------------------------------------------------------------
def fx():
    step("FX")
    spec = [("I44", "no_fx_i44", "Import-weighted krone exchange rate index I-44 (higher = weaker NOK)", "index (1990=100)"),
            ("EUR", "no_fx_eurnok", "EURNOK exchange rate", "NOK per EUR"),
            ("SEK", "no_fx_seknok", "SEKNOK exchange rate", "NOK per 100 SEK"),
            ("DKK", "no_fx_dkknok", "DKKNOK exchange rate", "NOK per 100 DKK"),
            ("USD", "no_fx_usdnok", "USDNOK exchange rate", "NOK per USD"),
            ("CZK", "no_fx_czknok", "CZKNOK exchange rate", "NOK per 100 CZK")]
    for cur, sid, desc, unit in spec:
        s = nb_series(f"EXR/M.{cur}.NOK.SP", start="1960-01")
        save(sid, s, desc + ", monthly average", "M", unit, "NSA", "Norges Bank SDMX",
             f"EXR/M.{cur}.NOK.SP", 1, "Norges Bank monthly average of daily fixing rates.")


# ----------------------------------------------------------------------------
# 7. Electricity
# ----------------------------------------------------------------------------
def electricity():
    step("Electricity (SSB end-user prices)")
    a = ssb_series("08448", {"ContentsCode": ["KraftOgNettIA"]})
    b = ssb_series("09387", {"ContentsCode": ["KraftOgNettIA"]})
    s = pd.concat([a[a.index < b.index.min()], b])
    save("no_elec_hh_total_price", s, "Household electricity price incl. grid rent and taxes (before government electricity support)",
         "Q", "ore per kWh", "NSA", "SSB tables 08448 (2003-2011) + 09387 (2012-)", "ContentsCode=KraftOgNettIA in both tables", 48,
         "Concatenated (same definition) closed table 08448 and current 09387. Excludes the electricity support scheme (stromstotte) deduction from 2021Q4 - see SSB 09387 KraftOgNettIUStrSt.")
    a = ssb_series("05103", {"Kraftpriser": ["01"], "ContentsCode": ["KraftprisEA"]})
    b = ssb_series("14491", {"Kraftpriser": ["1"], "ContentsCode": ["KraftprisEA"]})
    s = pd.concat([a[a.index < b.index.min()], b])
    save("no_elec_hh_energy_price", s, "Household electricity price (energy component), excl. taxes and grid rent, all contract types",
         "Q", "ore per kWh", "NSA", "SSB tables 05103 (1998-2011) + 14491 (2012-)",
         "05103 Kraftpriser=01 KraftprisEA; 14491 Kraftpriser=1 KraftprisEA", 48,
         "Concatenated; survey redesign 2012 (possible level break).")

    step("Electricity (Nord Pool spot via Energi Data Service)")
    base = "https://api.energidataservice.dk/dataset/"
    r = http_get(base + 'Elspotprices?start=1999-01-01T00:00&end=2025-10-01T00:00&filter={"PriceArea":["NO2","SYSTEM"]}'
                 '&columns=HourDK,PriceArea,SpotPriceEUR&limit=0', timeout=600)
    old = pd.DataFrame(r.json()["records"])
    old["t"] = pd.to_datetime(old["HourDK"])
    time.sleep(10)
    r = http_get(base + 'DayAheadPrices?start=2025-10-01T00:00&filter={"PriceArea":["NO2"]}'
                 '&columns=TimeDK,PriceArea,DayAheadPriceEUR&limit=0', timeout=600)
    new = pd.DataFrame(r.json()["records"])
    new["t"] = pd.to_datetime(new["TimeDK"])
    new = new.rename(columns={"DayAheadPriceEUR": "SpotPriceEUR"})
    allp = pd.concat([old[["t", "PriceArea", "SpotPriceEUR"]], new[["t", "PriceArea", "SpotPriceEUR"]]])
    allp = allp.dropna(subset=["SpotPriceEUR"])
    cutoff = pd.Timestamp.today().normalize().replace(day=1)
    for area, sid in [("NO2", "no_elspot_no2_eur"), ("SYSTEM", "no_elspot_system_eur")]:
        x = allp[allp.PriceArea == area]
        m = x.groupby(x.t.dt.to_period("M"))["SpotPriceEUR"].mean()
        m.index = m.index.to_timestamp()
        m = m[m.index < cutoff]
        desc = {"NO2": "Nord Pool day-ahead spot price, bidding zone NO2 (Southern Norway), monthly average",
                "SYSTEM": "Nord Pool system price (Nordic), monthly average"}[area]
        note = ("Hourly prices (Elspotprices, to 2025-09) and 15-minute prices (DayAheadPrices, from 2025-10, "
                "after the switch to 15-min MTU) averaged per calendar month (CET/CEST). Current incomplete month dropped.")
        if area == "SYSTEM":
            note = (f"Hourly prices from Energi Data Service dataset Elspotprices averaged per month; the dataset only holds the system price "
                    f"for {m.index.min():%Y-%m}..{m.index.max():%Y-%m} (and the system price is not in DayAheadPrices) - use NO2 for current data.")
        save(sid, m, desc, "M", "EUR per MWh", "NSA", "Energinet Energi Data Service (Nord Pool data)",
             f"Elspotprices PriceArea={area}" + ("; DayAheadPrices PriceArea=NO2" if area == "NO2" else ""), 1, note)


# ----------------------------------------------------------------------------
# 8. Agriculture: NIBIO price index + agricultural settlements (hand compiled)
# ----------------------------------------------------------------------------
def agriculture():
    step("Agriculture")
    t = http_get("https://www.nibio.no/tjenester/jordbrukets-prisindeks").text
    tab = pd.read_html(io.StringIO(t))[0]
    tab.columns = ["year", "value"]
    tab["year"] = tab["year"].astype(str).str.extract(r"(\d{4})")[0].astype(int)
    s = pd.Series(pd.to_numeric(tab["value"]).values, index=[pd.Timestamp(y, 1, 1) for y in tab["year"]]).sort_index()
    save("no_agri_price_idx", s, "Agricultural output price index incl. subsidies (Jordbrukets prisindeks / volume and price index of BFJ)",
         "A", "index 2015=100", "NSA", "NIBIO / Budsjettnemnda for jordbruket",
         "https://www.nibio.no/tjenester/jordbrukets-prisindeks (HTML table)", -120,
         "Latest year is a budget estimate including the agreed target price increases (published ~Aug/Sep of the same year), "
         "previous year preliminary accounts. Annual, calendar year.")

    from_table = pd.DataFrame(JORDBRUK, columns=["year", "ramme_mnok", "malpris_mnok", "source"])
    for col, sid, desc, unit, note in [
        ("ramme_mnok", "no_jordbruk_ramme_mnok", "Agricultural settlement (jordbruksoppgjoret): total economic framework (ramme) of the agreement",
         "NOK million (agreed frame, full-year effect)",
         "Agreed (or Storting-decided after breakdown) frame; target price part effective 1 July of the year, budget part next calendar year. "
         "Definitions vary somewhat between years (e.g. 2002/2006 include the value of tax-deduction changes, 2020 implied from components, "
         "2022 is the extraordinary two-year total of 10.9 bn incl. cost compensation; 2000 missing - breakdown with target price cut)."),
        ("malpris_mnok", "no_jordbruk_malpris_mnok", "Agricultural settlement: agreed change in target prices (malpriser), full-year effect",
         "NOK million (full-year effect)",
         "Target prices effective 1 July of the year until 30 June next year. From 2025 milk is no longer target-priced (only cereals, potatoes, vegetables, fruit), so the series shrinks structurally."),
    ]:
        x = from_table.dropna(subset=[col])
        if x.empty:
            continue
        s = pd.Series(x[col].values.astype(float), index=[pd.Timestamp(int(y), 1, 1) for y in x["year"]])
        save(sid, s, desc, "A", unit, "NSA", "Hand-compiled from Stortinget innstillinger / jordbruksavtaler (see fetch.py JORDBRUK)",
             "see JORDBRUK table in fetch.py", -200,
             note + " Dated YYYY-01-01 per convention but agreed mid-May (or June after breakdown) and effective 1 July of year YYYY.")


# Agricultural settlement table (hand compiled; numbers as stated in the Storting committee
# recommendation for each year's settlement, PDFs at
# https://www.stortinget.no/globalassets/pdf/innstillinger/stortinget/<session>/inns-<id>.pdf ,
# 2025 from the signed final protocol reproduced in Norges Bondelag's "Avtaleguide 2025-2026").
# Columns: year, total frame (MNOK), change in target prices (MNOK, full-year effect), source/notes.
JORDBRUK = [
    (2000, None, -900, "Innst. S. nr. 219 (1999-2000); breakdown, Storting adopted govt proposal: target prices on milk/meat/eggs cut 900 MNOK, compensated by new tax deduction (est. actual price fall ~300 MNOK); no ordinary frame"),
    (2001, 425, 300, "Innst. S. nr. 345 (2000-2001); frame 425 MNOK on annual basis (+148 MNOK released funds)"),
    (2002, 750, 475, "Innst. S. nr. 250 (2001-2002); agreement with Bondelaget only; frame 450 MNOK excl. / 750 incl. tax deduction and one-off funds; target prices +~3% on average"),
    (2003, 100, 200, "Innst. S. nr. 288 (2002-2003)"),
    (2004, -170, 40, "Innst. S. nr. 260 (2003-2004)"),
    (2005, 450, 260, "Innst. S. nr. 263 (2004-2005)"),
    (2006, 850, 40, "Innst. S. nr. 236 (2005-2006); frame incl. 425 MNOK value of increased tax deduction"),
    (2007, 975, 545, "Innst. S. nr. 285 (2006-2007); target prices +3 1/4%; est. effect on Norwegian-produced food 1.5%"),
    (2008, 1900, 870, "Innst. S. nr. 320 (2007-2008)"),
    (2009, 1000, 290, "Innst. S. nr. 375 (2008-2009); frame excl. 200 MNOK extraordinary investment package (1200 incl.)"),
    (2010, 950, 420, "Innst. 364 S (2009-2010)"),
    (2011, 1420, 860, "Innst. 444 S (2010-2011); agreement with Bondelaget; target prices +580 MNOK from 1 Jul 2011 plus +280 MNOK price increases from 1 Jan 2012 (abolished food-safety fees)"),
    (2012, 625, 330, "Innst. 392 S (2011-2012); breakdown, Storting adopted govt proposal; frame 625 MNOK with income effect (900 incl. LUF top-up)"),
    (2013, 1270, 580, "Innst. 508 S (2012-2013)"),
    (2014, 400, 340, "Innst. 285 S (2013-2014); breakdown; govt proposal frame 150 MNOK, raised by 250 MNOK in Storting compromise with KrF/V"),
    (2015, 400, 315, "Innst. 385 S (2014-2015); agreement with Bondelaget"),
    (2016, 350, 190, "Innst. 412 S (2015-2016)"),
    (2017, 410, 150, "Innst. 445 S (2016-2017); breakdown, Storting adopted govt proposal with modifications to budget posts"),
    (2018, 1100, 198, "Innst. 404 S (2017-2018)"),
    (2019, 1240, 249, "Innst. 414 S (2018-2019); est. effect on CPI food +0.15 pp"),
    (2020, 655, 305, "Innst. 380 S (2019-2020); simplified COVID negotiations, no formal frame: target prices +1 3/4% (~300-310 MNOK) + budget +350 MNOK"),
    (2021, 962, 400, "Innst. 657 S (2020-2021); breakdown, Storting majority voted for the state's offer"),
    (2022, 10900, 1488, "Innst. 462 S (2021-2022); extraordinary: total increase in income possibilities 2022-2023 of 10.9 bn incl. cost compensation; est. effect on CPI food +1.8%"),
    (2023, 4150, 864, "Innst. 487 S (2022-2023)"),
    (2024, 3015, 627, "Innst. 448 S (2023-2024)"),
    (2025, 1107, 288, "Final protocol 30 Jun 2025 (Bondelaget Avtaleguide 2025-2026; Innst. 534 S states 1070); milk no longer target priced; est. effect on CPI food +0.6 pp"),
    (2026, 3660, 233, "Innst. 452 S (2025-2026)"),
]


# ----------------------------------------------------------------------------
# 9. Food VAT (hand compiled)
# ----------------------------------------------------------------------------
VAT_CHANGES = [  # (effective date, VAT rate on food in percent)
    ("1990-01-01", 20.0),  # general rate 20% (since 1970) applied to food
    ("1993-01-01", 22.0),  # general rate raised to 22%
    ("1995-01-01", 23.0),  # general rate raised to 23%
    ("2001-01-01", 24.0),  # general rate raised to 24% (Stortingets vedtak for budsjetterminen 2001)
    ("2001-07-01", 12.0),  # VAT reform: reduced rate 12% for food (naeringsmidler)
    ("2005-01-01", 11.0),  # reduced from 12% to 11% (FOR-2004-11-26-1524 transitional rules)
    ("2006-01-01", 13.0),  # raised from 11% to 13% (St.prp. nr. 1 (2005-2006) Skatte-, avgifts- og tollvedtak)
    ("2007-01-01", 14.0),  # raised from 13% to 14% (Innst. S. nr. 1 (2006-2007))
    ("2012-01-01", 15.0),  # raised from 14% to 15%; unchanged through 2026 (Stortingsvedtak om merverdiavgift 2026, FOR-2025-12-18-2752)
]


def food_vat():
    step("Food VAT")
    idx = pd.date_range("1990-01-01", "2026-12-01", freq="MS")
    s = pd.Series(np.nan, index=idx)
    for d, v in VAT_CHANGES:
        s[s.index >= pd.Timestamp(d)] = v
    save("no_vat_food_rate", s, "VAT rate on food (naeringsmidler) in Norway", "M", "percent", "NSA",
         "Hand-compiled: Skatteetaten, Lovdata, Stortinget documents", "see VAT_CHANGES in fetch.py", -31,
         "Before 1 Jul 2001 food carried the general VAT rate. Changes: 2001-01 24% (general), 2001-07 12%, 2005-01 11%, "
         "2006-01 13%, 2007-01 14%, 2012-01 15% (unchanged to 2026; proposals to cut to 10% in 2025 were postponed). "
         "Rates are legislated in advance (December budget) -> known before the period.")


# ----------------------------------------------------------------------------
def main():
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    jobs = [("cpi", cpi), ("prices", producer_import_prices), ("activity", activity), ("labour", labour),
            ("rates", rates), ("fx", fx), ("electricity", electricity), ("agriculture", agriculture),
            ("vat", food_vat)]
    failures = []
    for name, fn in jobs:
        if only and name != only:
            continue
        try:
            fn()
        except Exception as e:  # keep going; report at end
            failures.append((name, repr(e)))
            print(f"  !! {name} failed: {e!r}")
    cat = pd.DataFrame(CATALOG)
    catfile = OUT / "catalog.csv"
    if only and catfile.exists():  # merge with existing catalog
        prev = pd.read_csv(catfile)
        prev = prev[~prev.series_id.isin(cat.series_id)] if not cat.empty else prev
        cat = pd.concat([prev, cat], ignore_index=True)
    cat = cat.sort_values("series_id").reset_index(drop=True)
    cat.to_csv(catfile, index=False)
    print(f"catalog: {len(cat)} series -> {catfile}")
    if failures:
        print("FAILURES:", failures)


if __name__ == "__main__":
    main()
