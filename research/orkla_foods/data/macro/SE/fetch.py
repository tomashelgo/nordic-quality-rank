#!/usr/bin/env python3
"""
Fetch Swedish macro / market time series for the Orkla Foods predictor analysis.

Output: one CSV per series (columns date,value) in the directory of this script,
plus catalog.csv describing every series.

Sources (all public, no API key needed):
  * SCB PxWeb API v1  https://api.scb.se/OV0104/v1/doris/en/ssd/   (GET metadata, POST query)
  * Riksbank SWEA API https://api.riksbank.se/swea/v1/              (ObservationAggregates, monthly avg)
  * Energi Data Service (Energinet, DK) https://api.energidataservice.dk/  (Nord Pool day-ahead prices
    for Swedish bidding areas: 'SE' = whole-Sweden area until 2011-10, 'SE3' from 2011-11;
    dataset Elspotprices (hourly, until 2025-09-30) and DayAheadPrices (15-min MTU, from 2025-10-01))
  * Food VAT rate: hard-coded from legislation (no API). Sources:
      - Skatteverket, "Skatter i Sverige 2004", table 6.3 (VAT rates 1991-2004: food 25/18/21/21/21/12...)
      - Riksdagen bet. 2025/26:SkU9 "Tillfälligt sänkt mervärdesskatt på livsmedel"
        (food VAT 12% -> 6% from 2026-04-01 through 2027-12-31)

Usage:  python3 -I fetch.py [raw_download_dir]
  raw_download_dir (optional) is where raw JSON responses are cached; default = a fresh temp dir.

Manual steps: none.  The SCB v1 API is rate limited (~30 calls / 10 s); the script sleeps between calls.
Riksbank SWEA anonymous access is rate limited too (script sleeps ~3 s between calls).
"""
import csv
import datetime as dt
import json
import os
import sys
import tempfile
import time

import pandas as pd
import requests

OUT = os.path.dirname(os.path.abspath(__file__))
RAW = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="se_macro_raw_")
os.makedirs(RAW, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
SCB = "https://api.scb.se/OV0104/v1/doris/en/ssd/"
SWEA = "https://api.riksbank.se/swea/v1/"
EDS = "https://api.energidataservice.dk/dataset/"
SESSION = requests.Session()
SESSION.headers.update(UA)
TODAY = dt.date.today()


def http(method, url, **kw):
    last = None
    for i in range(10):
        try:
            r = SESSION.request(method, url, timeout=120, **kw)
            if r.status_code in (429, 503):
                time.sleep(15 + 10 * i)
                continue
            r.raise_for_status()
            return r
        except Exception as e:  # proxy disconnects happen under load: back off and retry
            last = e
            time.sleep(4 + 3 * i)
    raise RuntimeError(f"failed {method} {url}: {last}")


# ----------------------------------------------------------------------------------------------
# SCB
# ----------------------------------------------------------------------------------------------
def scb_period_to_date(p):
    p = str(p)
    if "M" in p:
        y, m = p.split("M")
        return f"{int(y):04d}-{int(m):02d}-01"
    if "K" in p:
        y, q = p.split("K")
        return f"{int(y):04d}-{3 * (int(q) - 1) + 1:02d}-01"
    if len(p) == 4:
        return f"{p}-01-01"
    raise ValueError(p)


def scb_fetch(table, selection):
    """selection: {variable_code: value} -- one value per non-time variable; all periods returned."""
    q = {"query": [{"code": k, "selection": {"filter": "item", "values": [v]}} for k, v in selection.items()],
         "response": {"format": "json"}}
    r = http("POST", SCB + table, json=q)
    time.sleep(0.8)
    raw = r.json()
    fn = os.path.join(RAW, "scb_" + table.replace("/", "_") + "_" + "_".join(str(v) for v in selection.values()).replace("/", "-").replace(" ", "")[:80] + ".json")
    with open(fn, "w") as f:
        json.dump(raw, f)
    tcol = [i for i, c in enumerate(raw["columns"]) if c["type"] == "t"][0]
    rows = []
    for d in raw["data"]:
        v = d["values"][0]
        try:
            val = float(v)
        except ValueError:
            continue  # '..' / '-' = missing
        rows.append((scb_period_to_date(d["key"][tcol]), val))
    s = pd.Series(dict(rows)).sort_index()
    return s


# ----------------------------------------------------------------------------------------------
# Riksbank SWEA (daily -> monthly average via ObservationAggregates/M)
# ----------------------------------------------------------------------------------------------
def swea_monthly(series_id, start="1980-01-01"):
    url = f"{SWEA}ObservationAggregates/{series_id}/M/{start}/{TODAY.isoformat()}"
    r = http("GET", url)
    time.sleep(3)
    raw = r.json()
    with open(os.path.join(RAW, f"swea_{series_id}.json"), "w") as f:
        json.dump(raw, f)
    out = {}
    cur = (TODAY.year, TODAY.month)
    for o in raw:
        if (o["year"], o["seqNr"]) >= cur:
            continue  # drop incomplete current month
        out[f"{o['year']:04d}-{o['seqNr']:02d}-01"] = float(o["average"])
    return pd.Series(out).sort_index()


# ----------------------------------------------------------------------------------------------
# Electricity day-ahead price, Swedish bidding area SE3 (Stockholm), spliced with 'SE' before 2011-11
# ----------------------------------------------------------------------------------------------
def eds_fetch(dataset, area, tcol, pcol, start, end):
    # One request per area/range (EDS rate-limits many consecutive requests with HTTP 429).
    url = (f"{EDS}{dataset}?start={start}T00:00&end={end}T00:00&limit=0&timezone=UTC"
           f"&columns={tcol},{pcol}&filter=" + requests.utils.quote(json.dumps({"PriceArea": [area]})))
    r = http("GET", url)
    time.sleep(20)
    df = pd.DataFrame(r.json().get("records", []))
    df.to_csv(os.path.join(RAW, f"eds_{dataset}_{area}.csv"), index=False)
    df[tcol] = pd.to_datetime(df[tcol])
    df = df.dropna(subset=[pcol])
    # Monthly mean of all (hourly / 15-min) observations; months defined on CET (UTC+1) clock.
    local = df[tcol] + pd.Timedelta(hours=1)
    m = df.groupby(local.dt.to_period("M"))[pcol].mean()
    m.index = [p.start_time.strftime("%Y-%m-01") for p in m.index]
    return m


def electricity_se3():
    a = eds_fetch("Elspotprices", "SE", "HourUTC", "SpotPriceEUR", "1999-07-01", "2011-11-01")
    b = eds_fetch("Elspotprices", "SE3", "HourUTC", "SpotPriceEUR", "2011-10-31", "2025-10-01")
    c = eds_fetch("DayAheadPrices", "SE3", "TimeUTC", "DayAheadPriceEUR", "2025-09-30", (TODAY + dt.timedelta(days=2)).isoformat())
    # EDS has no Swedish area price for 2011-01..2011-10 (area 'SE' ends 2010-12, SE3 starts late 2011-10):
    # fill those months with the Nord Pool system price (area 'SYSTEM'), flagged in the catalog notes.
    g = eds_fetch("Elspotprices", "SYSTEM", "HourUTC", "SpotPriceEUR", "2010-12-31", "2011-11-01")
    a = a[a.index < "2011-01-01"]
    g = g[(g.index >= "2011-01-01") & (g.index < "2011-11-01")]
    b = b[(b.index >= "2011-11-01") & (b.index < "2025-10-01")]
    c = c[c.index >= "2025-10-01"]
    s = pd.concat([a, g, b, c]).sort_index()
    cur = f"{TODAY.year:04d}-{TODAY.month:02d}-01"
    return s[s.index < cur]


# ----------------------------------------------------------------------------------------------
# Food VAT (livsmedelsmoms), monthly step series
# ----------------------------------------------------------------------------------------------
FOOD_VAT_CHANGES = [  # (effective date, rate in %)
    ("1991-01-01", 25.0),  # general rate 25% applied to food (general rate raised 23.46% -> 25% in the 1990-91 tax reform)
    ("1992-01-01", 18.0),  # reduced food rate introduced
    ("1993-01-01", 21.0),  # raised
    ("1996-01-01", 12.0),  # lowered to 12%
    ("2026-04-01", 6.0),   # temporary halving 2026-04-01 .. 2027-12-31 (bet. 2025/26:SkU9); 12% again from 2028-01-01
]


def food_vat():
    idx = pd.date_range("1991-01-01", f"{TODAY.year}-{TODAY.month:02d}-01", freq="MS")
    s = pd.Series(index=idx, dtype=float)
    for d, r in FOOD_VAT_CHANGES:
        s[s.index >= d] = r
    s.index = s.index.strftime("%Y-%m-%d")
    return s


# ----------------------------------------------------------------------------------------------
# Series specification
# ----------------------------------------------------------------------------------------------
M, Q = "monthly", "quarterly"
CPI_COICOP = "PR/PR0101/PR0101A/KPI2020COICOPM"
PPI = "PR/PR0301/PR0301G/PPI2020M"
HMPI, IMPI, ITPI = "000001I3", "000001I0", "000004XU"
RETAIL = "HA/HA0101/HA0101B/DetOms07N"


def cpi_sub(sid, code, desc):
    return dict(id=sid, src="scb", table=CPI_COICOP, sel={"VaruTjanstegrupp": code, "ContentsCode": "0000080H"},
                desc=f"CPI {desc} (COICOP 2018 {code}), index 2020=100", freq=M, unit="index 2020=100", sa="NSA", lag=13,
                notes="SCB COICOP 2018 classification (introduced 2026, back-cast by SCB). Prices incl. VAT, so food VAT changes (1992,1993,1996, Apr-2026) show up as level shifts.")


def ppi(sid, spin, cc, desc, notes=""):
    nm = {HMPI: "home market price index (HMPI)", IMPI: "import price index (IMPI)", ITPI: "price index for domestic supply (ITPI = home market + imports)", "000000SA": "producer price index (PPI = home market + export)"}[cc]
    return dict(id=sid, src="scb", table=PPI, sel={"SPIN2015": spin, "ContentsCode": cc},
                desc=f"{desc} (SPIN 2015 {spin}), {nm}, 2020=100", freq=M, unit="index 2020=100", sa="NSA", lag=25,
                notes=("Prices excl. VAT. " + notes).strip())


SERIES = [
    # --- consumer prices --------------------------------------------------------------------
    dict(id="se_cpi_idx", src="scb", table="PR/PR0101/PR0101A/KPI2020COICOP2M", sel={"VaruTjanstegrupp": "00", "ContentsCode": "0000080C"},
         desc="CPI total (KPI), 2020=100", freq=M, unit="index 2020=100", sa="NSA", lag=13,
         notes="Headline CPI incl. mortgage interest costs. Taken from the COICOP division table (total '00'), which carries full history 1980-; table KPI2020M has 2020=100 fixed numbers only from 2026. A flash estimate is published ~5-7 days after month end."),
    dict(id="se_cpif_idx", src="scb", table="PR/PR0101/PR0101G/KPIF2020", sel={"ContentsCode": "000007ZN"},
         desc="CPIF (CPI with fixed interest rate; Riksbank target variable), 2020=100", freq=M, unit="index 2020=100", sa="NSA", lag=13, notes=""),
    dict(id="se_cpifxe_idx", src="scb", table="PR/PR0101/PR0101J/KPIFXE2020", sel={"ContentsCode": "000007ZW"},
         desc="CPIF excluding energy (CPIF-XE), 2020=100", freq=M, unit="index 2020=100", sa="NSA", lag=13, notes=""),
    dict(id="se_cpif_ct_idx", src="scb", table="PR/PR0101/PR0101I/KPIFKS2020", sel={"ContentsCode": "000007ZT"},
         desc="CPIF at constant taxes (CPIF-CT), 2020=100", freq=M, unit="index 2020=100", sa="NSA", lag=13,
         notes="Removes effects of changed indirect taxes/subsidies (e.g. food VAT cut Apr-2026)."),
    dict(id="se_cpi_food_nab_idx", src="scb", table="PR/PR0101/PR0101A/KPI2020COICOP2M", sel={"VaruTjanstegrupp": "01", "ContentsCode": "0000080C"},
         desc="CPI food and non-alcoholic beverages (COICOP 01), 2020=100", freq=M, unit="index 2020=100", sa="NSA", lag=13,
         notes="Prices incl. VAT: food VAT changes (1992,1993,1996, Apr-2026 12%->6%) appear as level shifts."),
    cpi_sub("se_cpi_food_idx", "01.1", "food"),
    cpi_sub("se_cpi_food_cereals_bread_idx", "01.1.1", "cereals and cereal products (bread, bakery, pasta)"),
    cpi_sub("se_cpi_food_meat_idx", "01.1.2", "meat"),
    cpi_sub("se_cpi_food_fish_idx", "01.1.3", "fish and seafood"),
    cpi_sub("se_cpi_food_dairy_eggs_idx", "01.1.4", "milk, other dairy products and eggs"),
    cpi_sub("se_cpi_food_oils_fats_idx", "01.1.5", "oils and fats"),
    cpi_sub("se_cpi_food_fruit_nuts_idx", "01.1.6", "fruits and nuts"),
    cpi_sub("se_cpi_food_vegetables_idx", "01.1.7", "vegetables, tubers and pulses"),
    cpi_sub("se_cpi_food_sugar_confect_idx", "01.1.8", "sugar, confectionery and desserts"),
    cpi_sub("se_cpi_food_ready_other_idx", "01.1.9", "ready-made food and other food products (incl. condiments, sauces)"),
    cpi_sub("se_cpi_nonalc_bev_idx", "01.2", "non-alcoholic beverages"),
    # --- producer / import prices -----------------------------------------------------------
    ppi("se_ppi_food_hmpi_idx", "10", HMPI, "Food products"),
    ppi("se_ppi_food_impi_idx", "10", IMPI, "Food products"),
    ppi("se_ppi_food_itpi_idx", "10", ITPI, "Food products"),
    ppi("se_ppi_agri_hmpi_idx", "01", HMPI, "Products of agriculture and hunting", "Farm-gate prices of Swedish agricultural products (raw material cost proxy)."),
    ppi("se_ppi_agri_impi_idx", "01", IMPI, "Products of agriculture and hunting"),
    ppi("se_ppi_paper_packaging_itpi_idx", "17.21", ITPI, "Corrugated paper/paperboard and containers", "Packaging input cost proxy."),
    ppi("se_ppi_plastic_packaging_itpi_idx", "22.22", ITPI, "Plastic packing goods", "Packaging input cost proxy."),
    ppi("se_ppi_total_itpi_idx", "B-E", ITPI, "Total (sections B-E)"),
    ppi("se_ppi_electricity_hmpi_idx", "35.1", HMPI, "Electricity, transmission and distribution services",
        "Official continuous electricity price index (incl. network services); complements the spot price series."),
    # --- retail trade -----------------------------------------------------------------------
    dict(id="se_retail_vol_sa_idx", src="scb", table=RETAIL, sel={"SNI2007": "47exkl47.3", "ContentsCode": "000006VX"},
         desc="Retail trade excl. fuel (NACE 47 excl. 47.3), sales volume, seasonally and working-day adjusted, 2021=100", freq=M, unit="index 2021=100 (constant prices)", sa="SA+WDA", lag=30,
         notes="SCB Detaljhandelns forsaljningsvolym (headline 'total retail excl. fuel')."),
    dict(id="se_retail_grocery_vol_sa_idx", src="scb", table=RETAIL, sel={"SNI2007": "47.11+.21-24+.26+.29", "ContentsCode": "000006VX"},
         desc="Retail sale with mostly food excl. Systembolaget = dagligvaruhandel (NACE 47.11+47.21-24+47.26+47.29), sales volume, SA+WDA, 2021=100", freq=M, unit="index 2021=100 (constant prices)", sa="SA+WDA", lag=30,
         notes="SCB headline 'dagligvaruhandeln' (excludes Systembolaget, 47.25). Code 47.11+47.2 (incl. Systembolaget) only exists from 2023. Volume = value deflated by SCB retail deflator."),
    dict(id="se_retail_grocery_value_idx", src="scb", table=RETAIL, sel={"SNI2007": "47.11+.21-24+.26+.29", "ContentsCode": "000006VV"},
         desc="Retail sale with mostly food excl. Systembolaget = dagligvaruhandel, sales value at current prices, 2021=100", freq=M, unit="index 2021=100 (current prices)", sa="NSA", lag=30,
         notes="Not seasonally adjusted; use y/y changes. Value incl. VAT (so affected by food VAT changes)."),
    # --- household consumption --------------------------------------------------------------
    dict(id="se_hhcons_ind_total_sa", src="scb", table="HE/HE0203/HE0203HK/HE0203KIndCoicopM", sel={"AndamalCOICOP": "TOTex1012", "ContentsCode": "000008R7"},
         desc="Household consumption indicator (new, COICOP 2018), total excl. COICOP 10 and 12, SA constant prices ref. year 2025", freq=M, unit="SEK million, constant prices (ref. 2025)", sa="SA", lag=30,
         notes="New SCB indicator (card-transaction based) starting 2019M01; for history use se_hhcons_ind_old_total_sa (2000M01-2026M03)."),
    dict(id="se_hhcons_ind_food_sa", src="scb", table="HE/HE0203/HE0203HK/HE0203KIndCoicopM", sel={"AndamalCOICOP": "CP01", "ContentsCode": "000008R7"},
         desc="Household consumption indicator (new), COICOP 01 food and non-alcoholic beverages, SA constant prices ref. year 2025", freq=M, unit="SEK million, constant prices (ref. 2025)", sa="SA", lag=30,
         notes="Starts 2019M01. Older proxy: se_hhcons_ind_old_grocery_sa."),
    dict(id="se_hhcons_ind_old_total_sa", src="scb", table="HE/HE0203/HE0203UE/HushKonIndN", sel={"Andamal": "HTK", "ContentsCode": "000008T5"},
         desc="Monthly indicator for household consumption (old series, discontinued after 2026M03), total, SA+WDA fixed prices, 2021=100", freq=M, unit="index 2021=100 (fixed prices)", sa="SA+WDA", lag=40,
         notes="Discontinued: last observation 2026M03; superseded by se_hhcons_ind_total_sa. Overlap 2019-2026M03 allows splicing by growth rates."),
    dict(id="se_hhcons_ind_old_grocery_sa", src="scb", table="HE/HE0203/HE0203UE/HushKonIndN", sel={"Andamal": "DBS", "ContentsCode": "000008T5"},
         desc="Monthly indicator for household consumption (old series), retail trade mostly food and beverages, SA+WDA fixed prices, 2021=100", freq=M, unit="index 2021=100 (fixed prices)", sa="SA+WDA", lag=40,
         notes="Discontinued after 2026M03. Based on dagligvaruhandel retail data."),
    dict(id="se_na_hhcons_total_sa", src="scb", table="NR/NR0103/NR0103B/NR0103ENS2010T14KvN", sel={"Andamal": "S14", "ContentsCode": "0000079L"},
         desc="National accounts: household final consumption expenditure (total, S14), SA, constant prices ref. year 2025", freq=Q, unit="SEK million, constant prices (ref. 2025, chained)", sa="SA", lag=59, notes=""),
    dict(id="se_na_hhcons_food_sa", src="scb", table="NR/NR0103/NR0103B/NR0103ENS2010T14KvN", sel={"Andamal": "CP01", "ContentsCode": "0000079L"},
         desc="National accounts: household consumption of food and non-alcoholic beverages (COICOP 01), SA, constant prices ref. year 2025", freq=Q, unit="SEK million, constant prices (ref. 2025, chained)", sa="SA", lag=59, notes=""),
    dict(id="se_na_hhcons_food_cp_sa", src="scb", table="NR/NR0103/NR0103B/NR0103ENS2010T14KvN", sel={"Andamal": "CP01", "ContentsCode": "0000079O"},
         desc="National accounts: household consumption of food and non-alcoholic beverages (COICOP 01), SA, current prices", freq=Q, unit="SEK million, current prices", sa="SA", lag=59,
         notes="Nominal food spending (value = price x volume)."),
    # --- activity -------------------------------------------------------------------------------
    dict(id="se_gdp_sa", src="scb", table="NR/NR0103/NR0103B/NR0103ENS2010T10SKv", sel={"Anvandningstyp": "BNPM", "ContentsCode": "NR0103CE"},
         desc="GDP at market prices, seasonally adjusted, constant prices ref. year 2025", freq=Q, unit="SEK million, constant prices (ref. 2025, chained)", sa="SA", lag=59,
         notes="A GDP indicator flash is published ~30 days after quarter end; full NA ~58-60 days."),
    dict(id="se_gdp_indicator_sa_idx", src="scb", table="NR/NR9999/NR9999A/NR9999ENS2010BNPIndN", sel={"BNPMarknadspris": "BNPM", "ContentsCode": "000000X3"},
         desc="Monthly GDP indicator, seasonally adjusted, constant prices 2011=100", freq=M, unit="index 2011=100", sa="SA", lag=40, notes=""),
    dict(id="se_unemp_rate_sa", src="scb", table="AM/AM0401/AM0401A/AKURLBefM", sel={"Arbetskraftstillh": "ALÖSP", "TypData": "SR_DATA", "Kon": "1+2", "Alder": "tot15-74"},
         desc="Unemployment rate, LFS (AKU), age 15-74, seasonally adjusted", freq=M, unit="percent of labour force", sa="SA", lag=17,
         notes="SCB LFS monthly from 2001M01 (current definitions; LFS redesign 2021 linked back by SCB). Seasonally adjusted (not smoothed); TC_DATA (smoothed trend) also available."),
    # --- interest rates (SCB financial market statistics) ---------------------------------------
    dict(id="se_mortgage_rate_new", src="scb", table="FM/FM5001/FM5001C/RantaT04N", sel={"Referenssektor": "1", "Motpartssektor": "2c", "Avtal": "0100", "Rantebindningstid": "1"},
         desc="Average lending rate to households for housing loans, new and renegotiated agreements, all fixation periods (MFI + mortgage credit cos. + AIF)", freq=M, unit="percent p.a.", sa="NSA", lag=26, notes=""),
    dict(id="se_mortgage_rate_outstanding", src="scb", table="FM/FM5001/FM5001C/RantaT04N", sel={"Referenssektor": "1", "Motpartssektor": "2c", "Avtal": "0200", "Rantebindningstid": "1"},
         desc="Average lending rate to households for housing loans, outstanding agreements, all fixation periods", freq=M, unit="percent p.a.", sa="NSA", lag=26,
         notes="Drives household interest burden / disposable income."),
    # --- Riksbank (daily -> monthly averages) ----------------------------------------------------
    dict(id="se_policy_rate", src="swea", sid="SECBREPOEFF", desc="Riksbank policy rate (repo rate), monthly average of daily values", freq=M, unit="percent", sa="NSA", lag=1,
         notes="Daily data aggregated to calendar-month average (Riksbank SWEA ObservationAggregates). Policy rate series starts 1994-06."),
    dict(id="se_tbill_3m", src="swea", sid="SETB3MBENCH", desc="Swedish treasury bill (SSVX) 3-month benchmark yield, monthly average of daily values", freq=M, unit="percent", sa="NSA", lag=1,
         notes="Daily -> monthly average. Used instead of STIBOR 3m, which is only available in SWEA until 2020-07 (licensing)."),
    dict(id="se_gov_bond_10y", src="swea", sid="SEGVB10YC", desc="Swedish government bond 10-year benchmark yield, monthly average of daily values", freq=M, unit="percent", sa="NSA", lag=1,
         notes="Daily -> monthly average."),
    dict(id="se_kix_idx", src="swea", sid="SEKKIX92", desc="KIX krona index (trade-weighted SEK, 1992-11-18=100), monthly average", freq=M, unit="index 18 Nov 1992=100 (higher = weaker SEK)", sa="NSA", lag=1,
         notes="Daily -> monthly average. Higher value = weaker krona."),
    dict(id="se_eursek", src="swea", sid="SEKEURPMI", desc="EUR/SEK exchange rate (SEK per EUR), monthly average", freq=M, unit="SEK per EUR", sa="NSA", lag=1,
         notes="Daily -> monthly average. Before 1999 the series refers to the ECU."),
    dict(id="se_usdsek", src="swea", sid="SEKUSDPMI", desc="USD/SEK exchange rate (SEK per USD), monthly average", freq=M, unit="SEK per USD", sa="NSA", lag=1, notes="Daily -> monthly average."),
    dict(id="se_noksek", src="swea", sid="SEKNOKPMI", desc="NOK/SEK exchange rate (SEK per NOK), monthly average", freq=M, unit="SEK per NOK", sa="NSA", lag=1, notes="Daily -> monthly average."),
    # --- electricity ---------------------------------------------------------------------------
    dict(id="se_elspot_se3_eur_mwh", src="elec", desc="Nord Pool day-ahead electricity price, Sweden bidding area SE3 (Stockholm), monthly average", freq=M, unit="EUR/MWh", sa="NSA", lag=1,
         notes="Monthly mean of hourly (15-min from 2025-10) prices. Spliced (levels, no rescaling): price area 'SE' (all of Sweden) 1999-07..2010-12; 2011-01..2011-10 = Nord Pool SYSTEM price (Swedish area price missing in source; SE-vs-SYS gap was small in summer but up to +10-35% in winters 2009-10); SE3 from 2011-11 (bidding zones introduced 2011-11-01). Source dataset: Energinet Energi Data Service (Elspotprices, DayAheadPrices)."),
    dict(id="se_elspot_se3_sek_mwh", src="derived", desc="Day-ahead electricity price SE3 converted to SEK (monthly EUR price x monthly average EUR/SEK)", freq=M, unit="SEK/MWh", sa="NSA", lag=1,
         notes="Derived = se_elspot_se3_eur_mwh * se_eursek (monthly averages; approximation to the true SEK monthly mean)."),
    # --- tax -------------------------------------------------------------------------------------
    dict(id="se_food_vat_rate", src="vat", desc="Swedish VAT rate on food (livsmedelsmoms), rate in force during the month", freq=M, unit="percent", sa="NSA", lag=0,
         notes="Step series from legislation: 25% (general rate) in 1991; 18% from 1992-01-01; 21% from 1993-01-01; 12% from 1996-01-01; 6% from 2026-04-01 (temporary, legislated to end 2027-12-31, 12% again from 2028-01-01). Before 1990-07 the general rate was 23.46%. Restaurant VAT differs (25% 1995-2011, 12% from 2012). Known in advance (lag 0 / negative)."),
]

SRC_TEXT = {
    "scb": "SCB (Statistics Sweden) PxWeb API v1",
    "swea": "Sveriges Riksbank SWEA API",
    "elec": "Nord Pool via Energinet Energi Data Service API",
    "derived": "Derived (Nord Pool via Energi Data Service; Riksbank SWEA)",
    "vat": "Legislation: Skatteverket 'Skatter i Sverige 2004' table 6.3; Riksdagen bet. 2025/26:SkU9",
}


def main():
    results, catalog, failures = {}, [], []
    for spec in SERIES:
        sid = spec["id"]
        try:
            if spec["src"] == "scb":
                s = scb_fetch(spec["table"], spec["sel"])
                query = f"POST {SCB}{spec['table']} selection={json.dumps(spec['sel'], ensure_ascii=False)}"
            elif spec["src"] == "swea":
                s = swea_monthly(spec["sid"])
                query = f"GET {SWEA}ObservationAggregates/{spec['sid']}/M/1980-01-01/<today>"
            elif spec["src"] == "elec":
                s = electricity_se3()
                query = f"GET {EDS}Elspotprices (PriceArea SE <2011-11, SE3 2011-11..2025-09) + {EDS}DayAheadPrices (SE3, 2025-10->)"
            elif spec["src"] == "derived":
                s = (results["se_elspot_se3_eur_mwh"] * results["se_eursek"]).dropna()
                query = "se_elspot_se3_eur_mwh * se_eursek"
            elif spec["src"] == "vat":
                s = food_vat()
                query = "hard-coded FOOD_VAT_CHANGES in fetch.py"
            else:
                raise ValueError(spec["src"])
            s = s.dropna().sort_index()
            if s.empty:
                raise RuntimeError("empty series")
            results[sid] = s
            fn = f"{sid}.csv"
            with open(os.path.join(OUT, fn), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["date", "value"])
                for d, v in s.items():
                    w.writerow([d, f"{v:.6g}" if abs(v) < 1e6 else f"{v:.10g}"])
            catalog.append(dict(series_id=sid, file=fn, description=spec["desc"], country="SE", frequency=spec["freq"],
                                unit=spec["unit"], seasonal_adjustment=spec["sa"], start=s.index[0], end=s.index[-1],
                                n_obs=len(s), source=SRC_TEXT[spec["src"]], source_query=query,
                                approx_release_lag_days=spec["lag"], notes=spec.get("notes", "")))
            print(f"OK  {sid:38s} {s.index[0]} -> {s.index[-1]}  n={len(s)}  last={s.iloc[-1]:.4g}", flush=True)
        except Exception as e:
            failures.append((sid, str(e)))
            print(f"ERR {sid}: {e}", flush=True)
    cols = ["series_id", "file", "description", "country", "frequency", "unit", "seasonal_adjustment", "start", "end",
            "n_obs", "source", "source_query", "approx_release_lag_days", "notes"]
    pd.DataFrame(catalog, columns=cols).to_csv(os.path.join(OUT, "catalog.csv"), index=False)
    print(f"\n{len(catalog)} series written to {OUT}; raw responses in {RAW}")
    if failures:
        print("FAILURES:", failures)


if __name__ == "__main__":
    main()
