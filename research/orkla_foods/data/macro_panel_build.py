#!/usr/bin/env python3
"""Build the quarterly macro feature panel for the Orkla Foods predictor screen.

Reads ONLY:
  data/macro/{NO,SE,WAGES,EU,SURVEYS,GLOBAL}/catalog.csv + one CSV per series (date,value)
  data/orkla_raw/geo_weights.csv

Writes (next to this script, i.e. research/orkla_foods/data/):
  macro_panel_quarterly.csv               period (YYYYQn) x feature, 1995Q1..2026Q3
  feature_dictionary.csv                  one row per feature
  macro_panel_geo_weights_quarterly.csv   raw Orkla Foods country weights per quarter (diagnostic)
  macro_panel_notes.md                    method, weight mapping, composites, breaks, coverage

Run:  python3 -I macro_panel_build.py
Deterministic; no network access.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
MACRO = HERE / "macro"
GEO_FILE = HERE / "orkla_raw" / "geo_weights.csv"
OUT_PANEL = HERE / "macro_panel_quarterly.csv"
OUT_DICT = HERE / "feature_dictionary.csv"
OUT_W = HERE / "macro_panel_geo_weights_quarterly.csv"
OUT_NOTES = HERE / "macro_panel_notes.md"

FOLDERS = ["NO", "SE", "WAGES", "EU", "SURVEYS", "GLOBAL"]
P_START, P_END = pd.Period("1995Q1", "Q"), pd.Period("2026Q3", "Q")
CALC_START = pd.Period("1980Q1", "Q")          # history used for yoy/dyoy before the panel starts
QIDX = pd.period_range(CALC_START, P_END, freq="Q")
PIDX = pd.period_range(P_START, P_END, freq="Q")
CUTOFF_M = pd.Timestamp("2026-09-01")         # nothing dated after Sep-2026 enters
CUTOFF_Q = pd.Timestamp("2026-07-01")
CUTOFF_A = pd.Timestamp("2026-01-01")
ZSCORE_WINDOW = (pd.Period("2000Q1", "Q"), pd.Period("2025Q4", "Q"))
MIN_COVERAGE_W = 0.40      # floor: min share of Orkla Foods revenue covered by countries with data (W composites)
REL_COVERAGE_W = 0.80      # ... and at least 80% of the composite's median coverage over 2005Q1-2025Q4
                           # (avoids composition jumps, e.g. a last quarter computed from NO+SE only)
MIN_COVERAGE_NW = 0.99     # Nordic composites need both NO and SE

# ---------------------------------------------------------------------------------------------
# 1. Exclusions (identical / near-identical copies across folders) - keep one copy only
# ---------------------------------------------------------------------------------------------
EXCLUDE = {
    ("WAGES", "no_cpi_idx"): "identical to NO/no_cpi_total_idx (qa_B I11)",
    ("WAGES", "se_cpi_idx"): "identical to SE/se_cpi_idx (qa_B I11)",
    ("WAGES", "se_cpif_idx"): "identical to SE/se_cpif_idx (qa_B I11)",
    ("WAGES", "dk_hicp_idx"): "identical to EU/dk_hicp_all_idx (qa_B I11)",
    ("WAGES", "fi_hicp_idx"): "identical to EU/fi_hicp_all_idx (qa_B I11)",
    ("WAGES", "cz_hicp_idx"): "identical to EU/cz_hicp_all_idx (qa_B I11)",
    ("WAGES", "ea_hicp_idx"): "near-identical to EU/ea_hicp_all_idx (EA changing composition vs EA20; yoy corr 0.9999)",
    ("WAGES", "ea_hh_real_disp_inc_pc_idx"): "identical to EU/ea_hh_real_gdi_pc_idx (qa_B I11)",
    ("WAGES", "no_exp_infl_12m_business"): "identical to SURVEYS/no_nbes_bl_infl_exp_12m (qa_B I11)",
    ("WAGES", "no_cpi_annual_idx"): "annual average of NO/no_cpi_total_idx (redundant)",
    ("EU", "no_gov_bond_10y"): "identical to NO/no_govbond_10y (qa_B I11)",
    ("EU", "no_retail_total_vol_idx"): "identical to NO/no_retail_vol_sa_idx (qa_B I11)",
    ("SE", "se_unemp_rate_sa"): "same id and values as EU/se_unemp_rate_sa, which is longer (1983-) and is kept",
    ("EU", "se_gov_bond_10y"): "same id as SE/se_gov_bond_10y; Riksbank benchmark (SE) kept, EMU-convergence copy dropped (yoy corr 0.99)",
    ("EU", "no_ppi_dom_food_mfg_idx"): "near-identical to NO/no_ppi_food_dom_idx (SSB, 10-day lag) which is kept",
    ("EU", "se_ppi_dom_food_mfg_idx"): "near-identical to SE/se_ppi_food_hmpi_idx (SCB HMPI) which is kept (yoy corr 0.9998)",
    ("NO", "no_lfs_unemp_rate_sa"): "near-identical to EU/no_unemp_rate_sa (max diff 0.1pp), which is longer and kept",
    ("GLOBAL", "no_elspot_no2_price"): "identical to NO/no_elspot_no2_eur (qa_B I11)",
    ("GLOBAL", "nordic_elspot_system_price"): "identical to NO/no_elspot_system_eur (qa_B I11)",
    ("GLOBAL", "se_elspot_se3_price"): "near-identical to SE/se_elspot_se3_eur_mwh (kept); GLOBAL copy has 2011-01..10 gap",
    ("EU", "ea_fx_nok_per_eur"): "near-identical to NO/no_fx_eurnok (Norges Bank) which is kept",
    ("GLOBAL", "glob_fx_eurnok"): "near-identical to NO/no_fx_eurnok which is kept",
    ("EU", "ea_fx_sek_per_eur"): "near-identical to SE/se_eursek (Riksbank) which is kept",
    ("GLOBAL", "glob_fx_eurusd"): "near-identical to EU/ea_fx_usd_per_eur which is kept",
    ("GLOBAL", "glob_fx_usdnok"): "near-identical to NO/no_fx_usdnok which is kept",
    ("GLOBAL", "glob_fx_usdsek"): "near-identical to SE/se_usdsek which is kept",
    ("SE", "se_noksek"): "inverse of NO/no_fx_seknok (yoy would be exactly the negative)",
}

# ---------------------------------------------------------------------------------------------
# 2. Cleaning rules (documented breaks, outliers, unusable early data)
# ---------------------------------------------------------------------------------------------
CEE = ("cz", "ee", "hu", "lt", "lv", "pl", "ro", "sk")
# monthly / native-frequency level masks applied before quarterly aggregation: (from, to) inclusive
LEVEL_MASK = {
    "no_imp_price_coffee_cocoa_idx": [(None, None, "2003-01-01", "2003-04-01", "qa_B I3 source anomaly 2003-01..04")],
    "no_imp_price_total_idx": [(None, None, "2003-01-01", "2003-04-01", "qa_B I3 source anomaly 2003-01..04")],
    "no_imp_price_cereals_idx": [(None, None, None, "2003-12-01", "qa_B I3 carried-forward prices; start 2004")],
    "se_ppi_electricity_hmpi_idx": [(None, None, None, "1995-12-01", "qa_B I4 annual-only values 1990-95")],
    "no_hh_real_disp_inc_sa_q": [(None, None, None, "2006-10-01", "qa_B I5 volatile income components before 2007")],
    "no_hh_real_disp_inc_xdiv_sa_q": [(None, None, None, "2006-10-01", "qa_B I5 volatile income components before 2007")],
}
# level masks on quarterly values (period strings) - spurious single quarters
QUARTER_LEVEL_MASK = {
    "no_real_wage_qna_yoy_q": (["2015Q2", "2015Q3", "2016Q2", "2016Q3"],
                               "2015 a-ordningen timing break (qa_B I5): 2015Q2/Q3 spurious and 2016Q2/Q3 base-affected"),
}
# yoy-type breaks: first month of the new basis -> yoy NaN for every quarter whose 4-quarter
# comparison straddles the break (4 quarters if the break starts a quarter, else 5)
YOY_BREAK_MONTHS = {
    "lt_lci_wages_idx": (["2019-01"], "LT 2019 tax reform: +30% level jump in 2019Q1 (qa_C 8)"),
    "glob_wb_chicken": (["2021-09"], "source US->Brazil 2021-09, -26% level step (qa_C 16)"),
    "glob_wb_soybean_oil": (["2025-01"], "basis Dutch->US Gulf 2025-01 (qa_C 16)"),
    "glob_wb_palm_oil": (["2001-07", "2024-11", "2025-02", "2026-01"],
                         "several basis changes (2001-07, 2021 [month unknown], 2024-11, 2025-02, 2026-01) (qa_C 16)"),
    "glob_wb_natgas_eu": (["2000-06", "2010-04", "2015-04"],
                          "definition changes: import border price from 2000-06, incl. spot 2010-04, TTF 2015-04 (qa_C 16)"),
    "glob_wb_barley": (["2012-05"], "Canadian -> US feed barley 2012-05 (catalog)"),
    "eu_agri_wheat_bread_price": (["2026-08"], "reporting-stage change 2026-08 (qa_C 16)"),
    "eu_agri_barley_feed_price": (["2026-08"], "reporting-stage change 2026-08 (qa_C 16)"),
    "eu_agri_barley_malting_price": (["2026-08"], "reporting-stage change 2026-08 (qa_C 16)"),
    "eu_agri_maize_feed_price": (["2026-08"], "reporting-stage change 2026-08 (qa_C 16)"),
    "eu_ppi_dom_c102_idx": (["2009-01"], "-12% level jump 2009-01, composition effect (qa_C 14)"),
    "no_nav_unemp_level_sa": (["2025-04"], "NAV register modernisation break 2025-04 (qa_B I5)"),
}
YOY_BREAK_YEARS = {"glob_wb_palm_oil": [2021]}   # month unknown -> mask Q1(Y)..Q4(Y+1)
YOY_BREAK_QUARTERS = {
    "no_qna_wage_per_fte_q": (["2015Q2", "2015Q3", "2016Q2", "2016Q3"],
                              "2015 a-ordningen quarterly timing break (qa_B I5); annual sums fine"),
    "no_qna_wage_per_fte_food_q": (["2015Q2", "2015Q3", "2016Q2", "2016Q3"],
                                   "2015 a-ordningen quarterly timing break (qa_B I5); annual sums fine"),
}
D4_BREAK_MONTHS = {   # rate/level-type series: d4 NaN across documented breaks (lvl kept)
    "no_nav_unemp_rate_sa": (["2022-01", "2025-04"], "labour-force base change 2022-01; register break 2025-04"),
    "no_lfs_unemp_rate_q_nsa": (["2006-01", "2021-01"], "LFS methodological breaks 2006 and 2021 (catalog)"),
    # [QA verify-panel] scope change documented in the NO catalog: from the 2025 settlement (effective
    # 1 Jul 2025) milk is no longer target-priced, so the NOK-million amount shrinks structurally.
    # The July-effective assignment puts the 2025 settlement in 2025Q3..2026Q2, so d4 there compares
    # the new scope with the old one.
    "no_jordbruk_malpris_mnok": (["2025-07"], "scope change: milk no longer target-priced from the 2025 "
                                              "settlement (effective 1 Jul 2025); lvl from 2025Q3 covers only "
                                              "cereals, potatoes, vegetables and fruit and is not comparable with "
                                              "earlier years (catalog)"),
}
# annual policy series assigned by effective date (1 July of year Y -> Q3(Y)..Q2(Y+1))
ANNUAL_EFFECTIVE_JULY = {"no_jordbruk_ramme_mnok", "no_jordbruk_malpris_mnok"}
# annual series whose value is known before the year (or at its start) - documented only
ANNUAL_LEVEL_TYPE_OVERRIDE = {"no_jordbruk_ramme_mnok", "no_jordbruk_malpris_mnok"}   # NOK-million changes -> lvl/d4
LVL_TYPE_OVERRIDE = {"us_umich_sentiment"}   # survey index with arbitrary base -> lvl/d4
# annual policy values settled by the time of the Q1 report (frontfag frame agreed late Mar / mid Apr;
# 2026: 12 Apr) -> treated as known in advance (lag 0)
KNOWN_AT_Q1_REPORT = {"no_frontfag_frame_a"}

# series excluded from specific composites (kept as stand-alone features)
NOISY_NOTES = {
    "ro_hh_saving_rate": "very noisy quarterly SCA data (qa_C 12); excluded from w_hh_saving composite",
    "lt_gov_bond_10y": "flat carried-forward primary yield (qa_C 9); excluded from w_gov10y composite",
    "ee_gov_bond_10y": "from 2020-06 only, not comparable (catalog); excluded from w_gov10y composite",
    "lt_ec_food_retail_sell_price_exp": "extremely noisy (qa_C 11); excluded from composites",
    "dk_unemp_rate_sa": "noisy monthly LFS (qa_C 13); quarterly mean used",
    "se_elspot_se3_eur_mwh": "2011-01..10 filled with Nord Pool system price (documented splice in catalog; qa_B I5)",
    "se_elspot_se3_sek_mwh": "2011-01..10 based on Nord Pool system price (documented splice in catalog; qa_B I5)",
    "no_elec_hh_energy_price": "survey redesign 2012 (possible level break; no visible step, kept)",
    "in_cpi_food_idx": "FAOSTAT; 2025 values FAO-imputed (qa_C 3); ends 2026-03; ~120-day lag, so left out of the food-CPI composites",
    "glob_wb_beef": "replacement series Sep-2021 and Jan-2024 (no visible step; not masked)",
    "glob_wb_soybeans": "delivery-basis changes 2021/2025 (no visible step; not masked)",
    "no_border_trade_exp_mnok_s1": "old survey 2004-2022; never chained with *_s2 (design break)",
    "no_border_trade_trips_s1": "old survey 2004-2022; never chained with *_s2 (design break)",
    "no_border_trade_exp_mnok_s2": "new survey from 2023Q1; never chained with *_s1 (design break)",
    "no_border_trade_trips_s2": "new survey from 2023Q1; never chained with *_s1 (design break)",
    "se_wage_yoy_m": "latest ~12 months preliminary, usually revised up (qa_B I7)",
    "se_wage_idx_m": "latest ~12 months preliminary, usually revised up (qa_B I7)",
    "no_vat_food_rate": "legislated step series; values after 2026-09 removed",
    "se_food_vat_rate": "legislated step series; 6% from 2026-04 (temporary to 2027); values after 2026-09 removed",
    "no_agri_price_idx": "latest year is a budget estimate (published Aug/Sep of the same year)",
    "no_frontfag_outcome_a": "2024-2025 preliminary TBU figures",
    "no_frontfag_frame_a": "wage norm agreed late March/mid April (2026: 12 Apr): treated as known at the Q1 report "
                           "(lag 0). Exception: the 2020 settlement was postponed (COVID-19) and the 1.7 frame was only "
                           "agreed in late summer 2020, so the 2020Q1-Q2 values are not real-time",
    "no_hh_real_disp_inc_sa_q": "incl. dividends: 2021Q4-2022Q1 dividend spike around tax changes (qa_B I5) distorts "
                                "yoy 2021Q4-2023Q1; the composite uses the ex-dividend series",
    "no_jordbruk_ramme_mnok": "definitions vary between years (2002/2006 incl. tax-deduction changes; 2022 = "
                              "extraordinary two-year total of 10.9 bn incl. cost compensation; 2000 missing) (catalog)",
    "ea_wage_tracker_yoy_q": "forward-looking ECB tracker: projected quarters after 2026Q3 removed. The 2013- history is "
                             "a back-calculation from signed agreements, not a real-time record",
    "se_exp_wage_1y_lmp": "Prospera rounds 3/06-3/09 mis-dated by up to one quarter (qa_B I6)",
    "se_exp_wage_1y_all": "Prospera rounds 3/06-3/09 mis-dated by up to one quarter (qa_B I6)",
    "se_exp_cpi_1y_lmp": "Prospera rounds 3/06-3/09 mis-dated by up to one quarter (qa_B I6)",
    "se_exp_cpi_1y_all": "Prospera rounds 3/06-3/09 mis-dated by up to one quarter (qa_B I6)",
    "se_exp_real_wage_1y_lmp": "Prospera rounds 3/06-3/09 mis-dated by up to one quarter (qa_B I6)",
    "sk_retail_food_vol_idx": "residual December seasonality 2000-2003 in source (qa_C 15)",
    "no_elspot_system_eur": "discontinued in free source after 2025-01 (qa_B I1)",
    "glob_wb_barley": "discontinued by the World Bank after 2020-08",
    "no_hh_food_cons_vol_sa_idx": "discontinued 2025-06 (qa_B I1)",
    "no_hh_goods_cons_vol_sa_idx": "discontinued 2025-06 (qa_B I1)",
    "se_hhcons_ind_old_total_sa": "discontinued 2026-03; successor se_hhcons_ind_total_sa (2019-)",
    "se_hhcons_ind_old_grocery_sa": "discontinued 2026-03; successor se_hhcons_ind_food_sa (2019-)",
}

# ---------------------------------------------------------------------------------------------
# 3. Core feature list (base series; both of their transforms are core)
# ---------------------------------------------------------------------------------------------
CORE_BASE = {
    # Norway: food prices, input prices, grocery volume, rates, FX, surveys, wages, VAT, farm policy
    "no_cpi_food_idx", "no_cpi_total_idx",
    "no_ppi_food_dom_idx", "no_imp_price_food_idx",
    "no_retail_foodstores_vol_sa_idx", "no_qna_hh_food_cons_sa_mnok",
    "no_policy_rate", "no_govbond_10y", "no_fx_eurnok",
    "no_fn_cci_sa", "no_nbes_bl_sell_price_di", "no_ssb_bts_consgoods_home_price_exp",
    "no_earn_idx_food_manuf_q", "no_real_wage_qna_yoy_q",
    "no_vat_food_rate", "no_jordbruk_malpris_mnok",
    # Sweden
    "se_cpi_food_idx", "se_cpi_idx", "se_ppi_food_hmpi_idx",
    "se_retail_grocery_vol_sa_idx", "se_na_hhcons_food_sa", "se_policy_rate", "se_gov_bond_10y",
    "se_eursek", "se_ec_cons_conf", "se_nier_food_mfg_sell_price_exp",
    "se_wage_idx_m", "se_real_wage_yoy_q", "se_food_vat_rate",
    # global input costs (energy and FX-converted costs are covered by core composites)
    "glob_fao_ffpi", "glob_fao_ffpi_nok", "glob_fao_ffpi_eur", "glob_fao_dairy_idx", "glob_fao_meat_idx",
    "glob_fao_cereals_idx", "glob_fao_vegoils_idx", "glob_fao_sugar_idx",
    "glob_wb_food_idx", "glob_wb_food_idx_nok", "glob_wb_food_idx_eur",
    "glob_gscpi", "eu_agri_wheat_bread_price",
    "eu_ppi_paper_packaging_idx", "eu_ppi_plastic_products_idx",
    "us_ppi_plastic_resins_idx", "us_ppi_corrugated_boxes_idx",
    # EA / EU aggregates
    "ea_hicp_food_idx", "eu_ppi_dom_food_mfg_idx",
    "eu_ppi_dom_c103_idx", "eu_ppi_dom_c105_idx",
    "eu_ppi_dom_c106_idx", "eu_ppi_dom_c107_idx", "eu_ppi_dom_c108_idx",
    "ea_ec_food_ind_sell_price_exp", "ea_negotiated_wages_yoy_q",
}

COUNTRY_NAME = {"NO": "Norway", "SE": "Sweden", "DK": "Denmark", "FI": "Finland", "EE": "Estonia",
                "LV": "Latvia", "LT": "Lithuania", "CZ": "Czechia", "SK": "Slovakia", "AT": "Austria",
                "HU": "Hungary", "RO": "Romania", "PL": "Poland", "DE": "Germany", "IN": "India",
                "RU": "Russia (no data)", "UK": "United Kingdom (no data)", "DROP": "Other regions (no data)"}
DATA_COUNTRIES = ["NO", "SE", "DK", "FI", "EE", "LV", "LT", "CZ", "SK", "AT", "HU", "RO", "PL", "DE", "IN"]
ALL_COLS = DATA_COUNTRIES + ["RU", "UK", "DROP"]


# =============================================================================================
# helpers
# =============================================================================================
def realtime_lag_q(lag_days: float, freq: str, sid: str = "") -> int:
    """Quarters of delay before the value for quarter t is available at a quarterly report
    published ~14 days after quarter end. Rule: 0 if lag<=14, 1 if <=100, else 2 (non-annual).
    Annual series assigned to all 4 quarters: availability is measured from the end of the first
    assigned quarter (Q1 = 275 days before year end; Q3 = 92 days for July-effective policy values)."""
    d = float(lag_days) if pd.notna(lag_days) else 60.0
    if sid in KNOWN_AT_Q1_REPORT:
        return 0
    if freq == "A":
        d += 92.0 if sid in ANNUAL_EFFECTIVE_JULY else 275.0
        return 0 if d <= 14 else int(math.ceil((d - 14) / 91.3))
    return 0 if d <= 14 else (1 if d <= 100 else 2)


def norm_freq(f: str) -> str:
    f = str(f).strip().lower()
    if f in ("m", "monthly"):
        return "M"
    if f in ("q", "quarterly"):
        return "Q"
    if f in ("a", "annual", "yearly", "y"):
        return "A"
    raise ValueError(f"unknown frequency {f}")


def transform_type(sid: str, unit: str) -> str:
    """'yoy' -> yoy & dyoy ; 'lvl' -> lvl & d4."""
    u = str(unit).lower()
    if sid in ANNUAL_LEVEL_TYPE_OVERRIDE or sid in LVL_TYPE_OVERRIDE:
        return "lvl"
    if u.startswith("%") or u.startswith("percent") or "balance" in u or "diffusion" in u \
            or "long-term average" in u or "mean=100, sd=10" in u or "standard deviations" in u:
        return "lvl"
    return "yoy"


def lvl_subtype(sid: str, unit: str) -> str:
    u = str(unit).lower()
    if sid in ANNUAL_LEVEL_TYPE_OVERRIDE:
        return "policy change (NOK million)"
    if sid in ("no_vat_food_rate", "se_food_vat_rate"):
        return "tax rate"
    if "y/y" in u or "12-month growth" in u or "quarter-on-quarter" in u:
        return "growth rate"
    if "expected" in u:
        return "expectation (percent)"
    if "balance" in u or "diffusion" in u or "long-term average" in u or "mean=100" in u \
            or "standard deviations" in u or sid in LVL_TYPE_OVERRIDE:
        return "survey balance / confidence / diffusion index"
    if "labour force" in u or "disposable income" in u:
        return "ratio (percent)"
    if sid.startswith("no_nbrn_profit"):
        return "survey (percent change)"
    return "interest rate / yield (percent)"


def category(sid: str, folder: str) -> str:
    s = sid
    if re.search(r"(^|_)vat(_|$)", s) or "jordbruk" in s:
        return "tax_policy"
    if re.search(r"_fx_|eursek|usdsek|noksek|kix_idx", s):
        return "fx"
    if re.search(r"policy_rate|_ecb_|euribor|nibor|tbill|mm_rate|gov_bond|govbond|mortgage|loan_rate|"
                 r"fed_funds|treasury|credit_hh", s):
        return "rates"
    if re.search(r"elspot|elec_|natgas|brent|coal|_energy_idx|ppi_electricity", s):
        return "energy"
    if re.search(r"packaging|plastic|corrugated|resin|wood_pulp|glass_cont|metal_cans|freight|gscpi|"
                 r"ppi_paper|aluminum|_tin$", s):
        return "packaging_freight"
    if folder == "SURVEYS":
        if re.search(r"price_exp|infl_exp|price_di", s):
            return "price_expectations"
        if re.search(r"cons_conf|cons_macro|cons_micro|_fn_|oecd_cci|umich|cons_price_past", s):
            return "consumer_survey"
        if re.search(r"oecd_cli", s):
            return "activity_retail"
        return "business_survey"
    if re.search(r"exp_infl|exp_cpi", s):
        return "price_expectations"
    if re.search(r"wage|earn|lci_|comp_per_employee|disp_inc|real_gdi|saving|frontfag|tbu", s):
        return "wages_income"
    if "unemp" in s:
        return "labour_market"
    if re.search(r"retail|hhcons|hh_food_cons|hh_goods_cons|qna_hh|na_hhcons|mna_hh|gdp|border_trade", s):
        return "activity_retail"
    if re.search(r"cpi|hicp", s):
        return "consumer_prices"
    if folder == "GLOBAL" and (s.startswith("glob_") or s.startswith("eu_agri")):
        return "commodities"
    if re.search(r"ppi|imp_price|dom_price|agri_price|trade_imp", s):
        return "producer_prices_input_costs"
    return "other"


def country_code(c: str) -> str:
    c = str(c)
    return {"EU27_2020": "EU", "EA20": "EA", "EA21": "EA"}.get(c, c)


def months_to_quarters(month: str) -> list[pd.Period]:
    m = pd.Period(month, "M")
    qb = m.asfreq("Q")
    n = 4 if (m.month - 1) % 3 == 0 else 5
    return [qb + i for i in range(n)]


def yoy_of(q: pd.Series) -> pd.Series:
    x = q.where(q > 0)
    return 100.0 * np.log(x / x.shift(4))


# =============================================================================================
# 4. load catalogs and series -> quarterly
# =============================================================================================
def load_catalog() -> pd.DataFrame:
    cats = []
    for d in FOLDERS:
        c = pd.read_csv(MACRO / d / "catalog.csv")
        c["folder"] = d
        cats.append(c)
    cat = pd.concat(cats, ignore_index=True)
    cat["freq"] = cat["frequency"].map(norm_freq)
    cat["excluded"] = [EXCLUDE.get((f, s)) for f, s in zip(cat.folder, cat.series_id)]
    keep = cat[cat.excluded.isna()].copy()
    dup = keep.series_id[keep.series_id.duplicated()]
    if len(dup):
        raise RuntimeError(f"duplicate series ids after exclusions: {list(dup)}")
    return cat, keep.set_index("series_id")


def read_series(folder: str, fname: str) -> pd.Series:
    df = pd.read_csv(MACRO / folder / fname, parse_dates=["date"])
    s = df.set_index("date")["value"].astype(float).sort_index()
    return s[~s.index.duplicated()]


def to_quarterly(sid: str, row: pd.Series, raw: pd.Series) -> tuple[pd.Series, list[str]]:
    notes = []
    f = row.freq
    s = raw.copy()
    # truncate anything after the cut-off (projections / legislated future values / forward quarters)
    cutoff = {"M": CUTOFF_M, "Q": CUTOFF_Q, "A": CUTOFF_A}[f]
    n_future = int((s.index > cutoff).sum())
    if n_future:
        s = s[s.index <= cutoff]
        notes.append(f"{n_future} obs dated after 2026-09 removed")
    # level masks
    for (_, _, a, b, why) in LEVEL_MASK.get(sid, []):
        lo = pd.Timestamp(a) if a else s.index.min()
        hi = pd.Timestamp(b)
        s[(s.index >= lo) & (s.index <= hi)] = np.nan
        notes.append(f"masked {a or 'start'}..{b}: {why}")
    if sid.startswith(CEE) and row.folder == "SURVEYS":
        n = int((s.index < "2000-01-01").sum())
        if n:
            s[s.index < "2000-01-01"] = np.nan
            notes.append("pre-2000 values dropped (transition-era survey artefacts, qa_C 10)")
    if f == "M":
        per = s.index.to_period("Q")
        g = s.groupby(per)
        q = g.mean().where(g.count() == 3)
    elif f == "Q":
        q = pd.Series(s.values, index=s.index.to_period("Q"))
    else:  # annual
        vals = {}
        for ts, v in s.items():
            y = ts.year
            if sid in ANNUAL_EFFECTIVE_JULY:
                qs = [pd.Period(f"{y}Q3"), pd.Period(f"{y}Q4"), pd.Period(f"{y+1}Q1"), pd.Period(f"{y+1}Q2")]
            else:
                qs = [pd.Period(f"{y}Q{k}") for k in range(1, 5)]
            for p in qs:
                vals[p] = v
        q = pd.Series(vals, dtype=float)
        if sid in ANNUAL_EFFECTIVE_JULY:
            notes.append("ANNUAL policy value assigned by effective date (1 July Y -> Q3 Y..Q2 Y+1)")
        else:
            notes.append("ANNUAL value assigned to all 4 quarters of the year")
    q = q.reindex(QIDX)
    if sid in QUARTER_LEVEL_MASK:
        ps, why = QUARTER_LEVEL_MASK[sid]
        q.loc[[pd.Period(p) for p in ps]] = np.nan
        notes.append(f"levels masked {','.join(ps)}: {why}")
    return q, notes


# =============================================================================================
# 5. Orkla Foods geographic weights
# =============================================================================================
SEG = {
    "A": "Orkla Foods (2000-2007 definition)",
    "B": "Orkla Foods Nordic (2008-2012 definition)",
    "C": "Orkla Foods (2013-2014 definition)",
    "D": "Orkla Foods (2015-2022 definition)",
    "E": "Orkla Foods Europe (2022Q3-2024; renamed Orkla Foods Feb 2025)",
    "F": "Orkla Foods (label from Feb 2025; same scope as Orkla Foods Europe)",
}
MAIN_REGIONS = {"Norway", "Sweden", "Denmark", "Finland and Iceland", "Finland", "Iceland", "The Baltics",
                "Rest of Europe", "Rest of Western Europe", "Central and Eastern Europe", "Asia",
                "North America", "South and Central America", "Rest of the world"}
CZSK_SPLIT = {"CZ": 0.75, "SK": 0.25}     # assumption: Czech-based businesses (Hame, Vitana)
A_CEE_NONRU_CAP = 9.6                       # A-def CEE share before SladCo/Krupskaya (Russia) were added
A_CEE_BALTIC = 2.0                          # A-def: Baltic food cos. in OF International (~257 MNOK moved to
                                            # OF Nordic in the 2008 restatement, ~2% of OF revenue)


def era_of(p: pd.Period) -> tuple[str, int]:
    y, q = p.year, p.quarter
    if y < 2000:
        return "A", 2000
    if y <= 2006:
        return "A", y
    if y == 2007:
        return "A", 2006            # no 2007 split for the 2000-2007 definition: carry 2006
    if y <= 2011:
        return "B", y
    if y == 2012:
        return "C", 2012            # B-def 2012 not published; C-def 2012 (after Bakers sale)
    if y == 2013 or (y == 2014 and q <= 3):
        return "C", 2013            # C-def reported 2013Q1-2014Q3; no 2014 C split -> carry 2013
    if y <= 2021:
        return "D", y               # D-def from 2014Q4
    if y == 2022 and q <= 2:
        return "D", 2021            # D-def 2022H1: carry 2021
    if y <= 2023:
        return "E", y
    if y <= 2025:
        return "F", y
    return "F", 2025                # 2026: carry 2025


def build_weights(geo: pd.DataFrame):
    geo = geo.copy()
    geo["share"] = pd.to_numeric(geo["share_of_revenue_pct"], errors="coerce")

    def main_rows(defn, year):
        r = geo[(geo.segment_label == SEG[defn]) & (geo.year == year) & geo.share.notna()
                & geo.country_or_region.isin(MAIN_REGIONS)]
        if defn == "D":   # 2014 has both AR rows and rounded Investor-Day rows: keep the AR rows
            r = r[~r.source.str.contains("Investor Day", na=False)]
        if r.empty:
            raise RuntimeError(f"no geo rows for {defn} {year}")
        return dict(zip(r.country_or_region, r.share))

    def est_rows(defn, year):
        r = geo[(geo.segment_label == SEG[defn]) & (geo.year == year) & geo.share.notna()
                & geo.source.str.contains("Project estimate", na=False)]
        return dict(zip(r.country_or_region, r.share))

    # Rest-of-Europe composition (fractions of the 'Rest of Europe' share)
    roe_frac_D = {}
    ar14 = main_rows("D", 2014)["Rest of Europe"]
    idr = geo[geo.source.str.contains("Investor Day 11 Sep 2015", na=False) & (geo.year == 2014)]
    idd = dict(zip(idr.country_or_region, idr.share))
    f1415 = {"CZSK": idd["Czech Republic"] / ar14, "AT": idd["Austria"] / ar14}
    f1415["OTHER"] = 1 - f1415["CZSK"] - f1415["AT"]

    def frac_from_est(defn, year, keys):
        e = est_rows(defn, year)
        out = {}
        for k, v in e.items():
            if k.startswith("Czech Republic + Slovakia"):
                out["CZSK"] = v
            elif k == "Austria":
                out["AT"] = v
            elif k == "Hungary":
                out["HU"] = v
            elif k.startswith("Other Europe"):
                out["OTHER"] = v
        tot = sum(out.values())
        return {k: out.get(k, 0.0) / tot for k in keys}

    f17 = frac_from_est("D", 2017, ["CZSK", "AT", "OTHER"])
    f21 = frac_from_est("D", 2021, ["CZSK", "AT", "OTHER"])
    for y in (2014, 2015):
        roe_frac_D[y] = f1415
    roe_frac_D[2016] = f17
    roe_frac_D[2017] = f17
    for y in (2018, 2019, 2020):
        a = (y - 2017) / 4.0
        roe_frac_D[y] = {k: (1 - a) * f17[k] + a * f21[k] for k in f17}
    roe_frac_D[2021] = f21
    roe_frac_EF = {}
    f23 = frac_from_est("E", 2023, ["CZSK", "AT", "HU", "OTHER"])
    f25 = frac_from_est("F", 2025, ["CZSK", "AT", "HU", "OTHER"])
    roe_frac_EF[2022] = f23
    roe_frac_EF[2023] = f23
    roe_frac_EF[2024] = {k: 0.5 * (f23[k] + f25[k]) for k in f23}
    roe_frac_EF[2025] = f25

    def map_regions(defn, year, shares):
        w = dict.fromkeys(ALL_COLS, 0.0)

        def add(c, v):
            w[c] += v

        for reg, v in shares.items():
            if reg == "Norway":
                add("NO", v)
            elif reg == "Sweden":
                add("SE", v)
            elif reg == "Denmark":
                add("DK", v)
            elif reg in ("Finland and Iceland", "Finland", "Iceland"):
                add("FI", v)
            elif reg == "The Baltics":
                for c in ("EE", "LV", "LT"):
                    add(c, v / 3)
            elif reg == "Rest of Western Europe":
                if defn == "A":
                    add("AT", 0.6 * v)
                    add("DE", 0.4 * v)
                else:
                    add("DE", v)
            elif reg == "Central and Eastern Europe":
                if defn == "A":
                    nonru = min(v, A_CEE_NONRU_CAP)
                    balt = min(A_CEE_BALTIC, nonru)     # Baltic food companies booked in OF International
                    for c in ("EE", "LV", "LT"):
                        add(c, balt / 3)
                    cs = ["PL", "CZ", "HU"] + (["RO"] if year >= 2002 else [])
                    for c in cs:
                        add(c, (nonru - balt) / len(cs))
                    add("RU", v - nonru)
                else:   # B/C: Baltic food companies (+ Kalev in B) are booked as CEE
                    for c in ("EE", "LV", "LT"):
                        add(c, v / 3)
            elif reg == "Rest of Europe":
                if defn == "D":
                    fr = roe_frac_D[year]
                    for c, s_ in CZSK_SPLIT.items():
                        add(c, v * fr["CZSK"] * s_)
                    add("AT", v * fr["AT"])
                    for c in ("HU", "RO", "PL", "DE", "RU"):
                        add(c, v * fr["OTHER"] / 5)
                else:
                    fr = roe_frac_EF[year]
                    for c, s_ in CZSK_SPLIT.items():
                        add(c, v * fr["CZSK"] * s_)
                    add("AT", v * fr["AT"])
                    add("HU", v * fr["HU"])
                    for c in ("RO", "DE", "UK"):
                        add(c, v * fr["OTHER"] / 3)
            elif reg == "Rest of the world":
                add("IN" if defn == "D" else "DROP", v)
            else:   # Asia, North America, South and Central America
                add("DROP", v)
        tot = sum(w.values())
        return {k: v / tot for k, v in w.items()}

    rows, meta = [], []
    for p in PIDX:
        defn, yr = era_of(p)
        w = map_regions(defn, yr, main_rows(defn, yr))
        rows.append(w)
        meta.append((str(p), defn, yr))
    W = pd.DataFrame(rows, index=PIDX)[ALL_COLS]
    M = pd.DataFrame(meta, columns=["period", "definition", "weights_year"]).set_index(pd.Index(PIDX))
    return W, M, {"D": roe_frac_D, "EF": roe_frac_EF}


def wavg(comp: dict, W: pd.DataFrame, min_cov: float, rel_cov: float = 0.0
         ) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Weighted average over countries with data; weights renormalised to 1 each quarter.
    NaN where covered share < max(min_cov, rel_cov * median covered share 2005Q1-2025Q4)."""
    df = pd.DataFrame({c: s.reindex(PIDX) for c, s in comp.items()})
    w = W.reindex(columns=df.columns).fillna(0.0)
    avail = df.notna() & (w > 0)
    wa = w.where(avail, 0.0)
    cov = wa.sum(axis=1)
    wn = wa.div(cov.replace(0, np.nan), axis=0)
    val = (df.fillna(0.0) * wn).sum(axis=1)
    ref = cov[(cov.index >= pd.Period("2005Q1")) & (cov.index <= pd.Period("2025Q4")) & (cov > 0)]
    thr = max(min_cov, rel_cov * float(ref.median())) if len(ref) else min_cov
    ok = cov >= thr - 1e-12
    val = val.where(ok)
    wsum = wn.sum(axis=1).where(ok)
    return val, cov.where(cov > 0), wsum


# =============================================================================================
# main build
# =============================================================================================
def main() -> int:
    cat_all, cat = load_catalog()
    print(f"catalog rows: {len(cat_all)}; kept after duplicate exclusions: {len(cat)}")

    Q = {}          # sid -> cleaned quarterly level series (QIDX)
    QNOTES = {}
    for sid, row in cat.iterrows():
        raw = read_series(row.folder, row.file)
        q, notes = to_quarterly(sid, row, raw)
        Q[sid] = q
        QNOTES[sid] = notes

    # ------------------------------------------------------------------ base transforms
    feats = {}      # feature_id -> pd.Series on QIDX
    fmeta = {}      # feature_id -> dict
    YOY, DYOY = {}, {}

    def lag_of(sid):
        r = cat.loc[sid]
        return realtime_lag_q(r.approx_release_lag_days, r.freq, sid)

    for sid, row in cat.iterrows():
        q = Q[sid]
        tt = transform_type(sid, row.unit)
        notes = list(QNOTES[sid])
        if sid in NOISY_NOTES:
            notes.append(NOISY_NOTES[sid])
        base = dict(base_series=sid, folder=row.folder, country=country_code(row.country),
                    category=category(sid, row.folder), core=sid in CORE_BASE,
                    realtime_min_lag_q=lag_of(sid), freq=row.freq)
        if tt == "yoy":
            y = yoy_of(q)
            masked = []
            if sid in YOY_BREAK_MONTHS:
                ms, why = YOY_BREAK_MONTHS[sid]
                for m in ms:
                    masked += months_to_quarters(m)
                notes.append(f"yoy NaN across break(s): {why}")
            for yr in YOY_BREAK_YEARS.get(sid, []):
                masked += [pd.Period(f"{yr}Q1") + i for i in range(8)]
            if sid in YOY_BREAK_QUARTERS:
                ps, why = YOY_BREAK_QUARTERS[sid]
                masked += [pd.Period(p) for p in ps]
                notes.append(f"yoy NaN {','.join(ps)}: {why}")
            masked = [p for p in masked if p in y.index]
            y.loc[masked] = np.nan
            dy = y - y.shift(4)
            YOY[sid], DYOY[sid] = y, dy
            desc = row.description
            feats[f"{sid}__yoy"] = y
            fmeta[f"{sid}__yoy"] = dict(base, transform="yoy",
                                        description=f"{desc} | yoy: 100*ln(x_t/x_t-4)",
                                        notes="; ".join(notes))
            feats[f"{sid}__dyoy"] = dy
            fmeta[f"{sid}__dyoy"] = dict(base, transform="dyoy",
                                         description=f"{desc} | dyoy: yoy_t - yoy_t-4",
                                         notes="; ".join(notes))
        else:
            lv = q.copy()
            d4 = lv - lv.shift(4)
            if sid in D4_BREAK_MONTHS:
                ms, why = D4_BREAK_MONTHS[sid]
                masked = [p for m in ms for p in months_to_quarters(m) if p in d4.index]
                d4.loc[masked] = np.nan
                notes.append(f"d4 NaN across break(s): {why}")
            st = lvl_subtype(sid, row.unit)
            desc = row.description
            feats[f"{sid}__lvl"] = lv
            fmeta[f"{sid}__lvl"] = dict(base, transform="lvl",
                                        description=f"{desc} | lvl ({st}): quarterly value",
                                        notes="; ".join(notes))
            feats[f"{sid}__d4"] = d4
            fmeta[f"{sid}__d4"] = dict(base, transform="d4",
                                       description=f"{desc} | d4 ({st}): x_t - x_t-4",
                                       notes="; ".join(notes))

    # ------------------------------------------------------------------ weights
    geo = pd.read_csv(GEO_FILE)
    W, WMETA, ROEFRAC = build_weights(geo)
    assert np.allclose(W.sum(axis=1), 1.0), "raw geo weights do not sum to 1"
    NWW = W[["NO", "SE"]].div(W[["NO", "SE"]].sum(axis=1), axis=0)   # Nordic weights NO/(NO+SE)

    def q(sid):            # quarterly level on PIDX
        return Q[sid].reindex(PIDX)

    def y_(sid):
        return YOY[sid].reindex(PIDX)

    def dy_(sid):
        return DYOY[sid].reindex(PIDX)

    def lvl_d4(sid):
        s = Q[sid]
        return s.reindex(PIDX), (s - s.shift(4)).reindex(PIDX)

    comp_feats, comp_meta = {}, {}
    weight_checks = {}
    coverage = {}

    def add_comp(fid, series, components, desc, category_, country, notes, transform):
        comp_feats[fid] = series
        lag = max(lag_of(s) for s in components)
        comp_meta[fid] = dict(base_series=",".join(sorted(set(components))), folder="COMPOSITE",
                              country=country, category=category_, core=True, realtime_min_lag_q=lag,
                              transform=transform, description=desc, notes=notes, freq="Q")

    def w_composite(name, cmap_yoy, cmap_dyoy, comps_used, desc, cat_, kind="yoy", nordic=False,
                    extra_note=""):
        """cmap_*: country -> series. kind 'yoy' -> name_yoy & name_dyoy ; 'lvl' -> name_lvl & name_d4;
        'z' -> name_z & name_z_d4."""
        Wuse = NWW if nordic else W
        mc = MIN_COVERAGE_NW if nordic else MIN_COVERAGE_W
        rc = 0.0 if nordic else REL_COVERAGE_W
        pre = "nw_" if nordic else "w_"
        a, b = {"yoy": ("_yoy", "_dyoy"), "lvl": ("_lvl", "_d4"), "z": ("_z", "_z_d4")}[kind]
        v1, cov1, ws1 = wavg(cmap_yoy, Wuse, mc, rc)
        v2, cov2, ws2 = wavg(cmap_dyoy, Wuse, mc, rc)
        cty = "NORDIC" if nordic else "W"
        wtxt = ("Nordic weights NO/(NO+SE) from geo_weights; both countries required" if nordic else
                f"Orkla Foods time-varying country weights renormalised over countries with data; "
                f"NaN if covered revenue share < max({MIN_COVERAGE_W:.0%}, {REL_COVERAGE_W:.0%} of the "
                f"composite's 2005-2025 median coverage)")
        countries = ",".join(cmap_yoy.keys())
        t1, t2 = a.strip("_"), b.strip("_")
        add_comp(pre + name + a, v1, comps_used,
                 f"{desc} [{t1}; countries: {countries}]", cat_, cty, f"{wtxt}. {extra_note}".strip(), t1)
        add_comp(pre + name + b, v2, comps_used,
                 f"{desc} [{t2}: weighted average of country-level {t2} with weights at t; countries: {countries}]",
                 cat_, cty, f"{wtxt}. {extra_note}".strip(), t2)
        for fid, ws, cv in ((pre + name + a, ws1, cov1), (pre + name + b, ws2, cov2)):
            weight_checks[fid] = ws
            coverage[fid] = cv

    EU_CC = ["dk", "fi", "ee", "lv", "lt", "cz", "sk", "at", "hu", "ro", "pl", "de"]

    def cc(c):
        return c.upper()

    # ---- food CPI
    food_cpi = {"NO": "no_cpi_food_idx", "SE": "se_cpi_food_idx"}
    food_cpi.update({cc(c): f"{c}_hicp_food_idx" for c in EU_CC})
    # India's only food CPI (FAOSTAT) has a ~120-day lag, ends 2026-03 and is FAO-imputed for 2025:
    # it is kept as a stand-alone feature but left out of the food-CPI composites (renormalised).
    cpi = {"NO": "no_cpi_total_idx", "SE": "se_cpi_idx"}
    cpi.update({cc(c): f"{c}_hicp_all_idx" for c in EU_CC})
    cpi["IN"] = "in_cpi_all_idx"
    food_note = "India excluded (FAOSTAT food CPI: 120-day lag, 2025 FAO-imputed)."
    w_composite("food_cpi", {k: y_(v) for k, v in food_cpi.items()}, {k: dy_(v) for k, v in food_cpi.items()},
                list(food_cpi.values()), "Orkla-weighted food CPI inflation (national CPI food NO/SE, HICP CP011 "
                "EU countries)", "consumer_prices", extra_note=food_note)
    w_composite("cpi", {k: y_(v) for k, v in cpi.items()}, {k: dy_(v) for k, v in cpi.items()},
                list(cpi.values()), "Orkla-weighted headline CPI inflation (CPI NO/SE, HICP all items EU, CPI India)",
                "consumer_prices")
    rel = {k: y_(food_cpi[k]) - y_(cpi[k]) for k in food_cpi}
    rel_d = {k: dy_(food_cpi[k]) - dy_(cpi[k]) for k in food_cpi}
    w_composite("food_cpi_rel", rel, rel_d, list(food_cpi.values()) + [cpi[k] for k in food_cpi],
                "Orkla-weighted relative food inflation (country food CPI yoy minus headline CPI yoy)",
                "consumer_prices", extra_note=food_note)
    # VAT-adjusted food CPI (NO/SE only adjusted for food VAT changes; other countries unadjusted)
    vat = {"NO": "no_vat_food_rate", "SE": "se_food_vat_rate"}
    xvat, xvat_d = {}, {}
    for k, v in food_cpi.items():
        if k in vat:
            r = Q[vat[k]]
            vadj = (100.0 * np.log((1 + r / 100.0) / (1 + r.shift(4) / 100.0)))
            yy = (YOY[v] - vadj)
            xvat[k] = yy.reindex(PIDX)
            xvat_d[k] = (yy - yy.shift(4)).reindex(PIDX)
        else:
            xvat[k], xvat_d[k] = y_(v), dy_(v)
    w_composite("food_cpi_xvat", xvat, xvat_d, list(food_cpi.values()) + list(vat.values()),
                "Orkla-weighted food CPI inflation with NO and SE adjusted for food-VAT changes "
                "(yoy - 100*ln((1+vat_t)/(1+vat_t-4)))", "consumer_prices",
                extra_note="Other countries unadjusted (no VAT history in the data). " + food_note)

    # ---- wages and real wages
    wage = {"NO": "no_lci_wages_idx", "SE": "se_wage_idx_m", "DK": "dk_wage_idx_private_q", "FI": "fi_wage_idx_q"}
    wage.update({cc(c): f"{c}_lci_wages_idx" for c in ["ee", "lv", "lt", "cz", "sk", "hu", "ro", "pl", "at", "de"]})
    w_composite("wage", {k: y_(v) for k, v in wage.items()}, {k: dy_(v) for k, v in wage.items()},
                list(wage.values()), "Orkla-weighted nominal wage growth (LCI wages & salaries; national wage "
                "indices for SE (MI), DK (private earnings) and FI (wage & salary index))", "wages_income",
                extra_note="LT LCI yoy NaN 2019Q1-Q4 (tax-reform level break).")
    rw = {k: y_(wage[k]) - y_(cpi[k]) for k in wage}
    rw_d = {k: dy_(wage[k]) - dy_(cpi[k]) for k in wage}
    w_composite("real_wage", rw, rw_d, list(wage.values()) + [cpi[k] for k in wage],
                "Orkla-weighted real wage growth (country nominal wage yoy minus headline CPI yoy, log points)",
                "wages_income")

    # ---- consumer confidence (z-scores over 2000-2025)
    conf = {"NO": "no_fn_cci_sa", "SE": "se_ec_cons_conf"}
    conf.update({cc(c): f"{c}_ec_cons_conf" for c in EU_CC})
    z, zd = {}, {}
    for k, v in conf.items():
        s = Q[v]
        win = s[(s.index >= ZSCORE_WINDOW[0]) & (s.index <= ZSCORE_WINDOW[1])]
        zz = (s - win.mean()) / win.std(ddof=1)
        z[k] = zz.reindex(PIDX)
        zd[k] = (zz - zz.shift(4)).reindex(PIDX)
    w_composite("cons_conf", z, zd, list(conf.values()),
                "Orkla-weighted consumer confidence, z-scored per country over 2000Q1-2025Q4 "
                "(Norway: Finans Norge Forventningsbarometer SA; others: EC consumer confidence)",
                "consumer_survey", kind="z", extra_note="India excluded (OECD CCI only from 2012, 15-day lag).")

    # ---- activity
    rfood = {cc(c): f"{c}_retail_food_vol_idx" for c in ["no", "se"] + EU_CC}
    w_composite("retail_food_vol", {k: y_(v) for k, v in rfood.items()}, {k: dy_(v) for k, v in rfood.items()},
                list(rfood.values()), "Orkla-weighted retail sales volume growth, food, beverages & tobacco "
                "(Eurostat G47_FOOD)", "activity_retail")
    rtot = {"NO": "no_retail_vol_sa_idx"}
    rtot.update({cc(c): f"{c}_retail_total_vol_idx" for c in ["se"] + EU_CC})
    w_composite("retail_total_vol", {k: y_(v) for k, v in rtot.items()}, {k: dy_(v) for k, v in rtot.items()},
                list(rtot.values()), "Orkla-weighted total retail sales volume growth (excl. motor vehicles)",
                "activity_retail")
    gdp = {"NO": "no_gdp_mainland_sa_mnok"}
    gdp.update({cc(c): f"{c}_gdp_vol_idx" for c in ["se"] + EU_CC})
    w_composite("gdp_vol", {k: y_(v) for k, v in gdp.items()}, {k: dy_(v) for k, v in gdp.items()},
                list(gdp.values()), "Orkla-weighted real GDP growth (Mainland GDP for Norway)", "activity_retail")
    inc = {"NO": "no_hh_real_disp_inc_xdiv_sa_q"}
    inc.update({cc(c): f"{c}_hh_real_gdi_pc_idx" for c in ["se", "dk", "fi", "cz", "at", "de", "hu", "pl", "ro"]})
    w_composite("hh_real_inc", {k: y_(v) for k, v in inc.items()}, {k: dy_(v) for k, v in inc.items()},
                list(inc.values()), "Orkla-weighted household real disposable income growth (per capita where "
                "available; Norway excl. dividends, from 2007)", "wages_income")

    # ---- producer prices
    fppi = {"NO": "no_ppi_food_dom_idx", "SE": "se_ppi_food_hmpi_idx"}
    fppi.update({cc(c): f"{c}_ppi_dom_food_mfg_idx" for c in ["dk", "fi", "lt", "cz", "at", "hu", "ro", "pl", "de"]})
    w_composite("food_ppi", {k: y_(v) for k, v in fppi.items()}, {k: dy_(v) for k, v in fppi.items()},
                list(fppi.values()), "Orkla-weighted domestic producer-price inflation, manufacture of food "
                "products (NACE C10)", "producer_prices_input_costs",
                extra_note="No food PPI for EE, LV, SK, IN in the data (renormalised).")

    # ---- labour market and rates
    un = {"NO": "no_unemp_rate_sa", "SE": "se_unemp_rate_sa"}
    un.update({cc(c): f"{c}_unemp_rate_sa" for c in EU_CC})
    lv = {k: lvl_d4(v) for k, v in un.items()}
    w_composite("unemp", {k: a for k, (a, b) in lv.items()}, {k: b for k, (a, b) in lv.items()},
                list(un.values()), "Orkla-weighted unemployment rate (ILO/LFS, SA)", "labour_market", kind="lvl")
    # euro-area effective policy rate: MRO until 2008-09, deposit rate from 2008-10 (full allotment)
    mro = read_series("EU", cat.loc["ea_ecb_mro"].file)
    dfr = read_series("EU", cat.loc["ea_ecb_dfr"].file)
    eff = pd.concat([mro[mro.index < "2008-10-01"], dfr[dfr.index >= "2008-10-01"]]).sort_index()
    eff = eff[eff.index <= CUTOFF_M]
    g = eff.groupby(eff.index.to_period("Q"))
    ea_eff = g.mean().where(g.count() == 3).reindex(QIDX)
    pol = {"NO": "no_policy_rate", "SE": "se_policy_rate", "DK": "dk_policy_rate", "CZ": "cz_policy_rate",
           "HU": "hu_policy_rate", "PL": "pl_policy_rate", "RO": "ro_policy_rate", "IN": "in_policy_rate"}
    pl_lvl = {k: Q[v] for k, v in pol.items()}
    euro_from = {"FI": "1999Q1", "AT": "1999Q1", "DE": "1999Q1", "EE": "1999Q1", "LV": "1999Q1",
                 "LT": "1999Q1", "SK": "2009Q1"}
    for k, p0 in euro_from.items():
        pl_lvl[k] = ea_eff.where(ea_eff.index >= pd.Period(p0))
    w_composite("policy_rate", {k: s.reindex(PIDX) for k, s in pl_lvl.items()},
                {k: (s - s.shift(4)).reindex(PIDX) for k, s in pl_lvl.items()},
                list(pol.values()) + ["ea_ecb_mro", "ea_ecb_dfr"],
                "Orkla-weighted central-bank policy rate", "rates", kind="lvl",
                extra_note="Euro members use the ECB effective rate (MRO to 2008-09, deposit rate from 2008-10) "
                           "from 1999 (SK from 2009; Baltic pegs proxied by the ECB rate from 1999).")
    gb = {"NO": "no_govbond_10y", "SE": "se_gov_bond_10y"}
    gb.update({cc(c): f"{c}_gov_bond_10y" for c in ["dk", "fi", "cz", "at", "de", "hu", "pl", "ro", "sk", "lv"]})
    lv = {k: lvl_d4(v) for k, v in gb.items()}
    w_composite("gov10y", {k: a for k, (a, b) in lv.items()}, {k: b for k, (a, b) in lv.items()},
                list(gb.values()), "Orkla-weighted 10-year government bond yield", "rates", kind="lvl",
                extra_note="LT (flat carried-forward yield) and EE (2020- only) excluded; Baltics = LV.")

    # ---- FX: local currency per EUR / per USD / per NOK (+ = local currency weaker)
    usd_per_eur = YOY["ea_fx_usd_per_eur"]
    # before 1999 se_eursek is SEK per ECU; NOK per ECU = NOK/SEK x SEK/ECU (the same cross reproduces
    # Norges Bank EURNOK within 0.04% after 1999). DKK and CZK per ECU via their NOK crosses.
    no_eur = YOY["no_fx_eurnok"].combine_first(YOY["no_fx_seknok"] + YOY["se_eursek"])
    dk_eur = YOY["ea_fx_dkk_per_eur"].combine_first(no_eur - YOY["no_fx_dkknok"])
    cz_eur = YOY["ea_fx_czk_per_eur"].combine_first(no_eur - YOY["no_fx_czknok"])
    fx_eur = {"NO": no_eur, "SE": YOY["se_eursek"], "DK": dk_eur,
              "CZ": cz_eur, "HU": YOY["ea_fx_huf_per_eur"], "PL": YOY["ea_fx_pln_per_eur"],
              "RO": YOY["ea_fx_ron_per_eur"], "IN": YOY["ea_fx_inr_per_eur"]}
    zero_from = {"FI": "1999Q1", "AT": "1999Q1", "DE": "1999Q1", "EE": "1995Q1", "LT": "2003Q1",
                 "LV": "2006Q1", "SK": "2010Q1"}
    for k, p0 in zero_from.items():
        s = pd.Series(0.0, index=QIDX)
        fx_eur[k] = s.where(s.index >= pd.Period(p0))
    fx_usd = {}
    for k, s in fx_eur.items():
        fx_usd[k] = s - usd_per_eur
    fx_usd["NO"] = YOY["no_fx_usdnok"]
    fx_usd["SE"] = YOY["se_usdsek"]
    fx_nok = {k: s - fx_eur["NO"] for k, s in fx_eur.items()}
    fx_nok["NO"] = pd.Series(0.0, index=QIDX)
    fx_nok["SE"] = -YOY["no_fx_seknok"]
    fx_nok["DK"] = -YOY["no_fx_dkknok"]
    fx_nok["CZ"] = -YOY["no_fx_czknok"]
    for k in ("DK", "CZ"):   # pre-1999 local per USD via the NOK cross
        fx_usd[k] = fx_usd[k].combine_first(fx_nok[k] + YOY["no_fx_usdnok"])
    fx_comp = ["no_fx_eurnok", "se_eursek", "ea_fx_dkk_per_eur", "ea_fx_czk_per_eur", "ea_fx_huf_per_eur",
               "ea_fx_pln_per_eur", "ea_fx_ron_per_eur", "ea_fx_inr_per_eur", "no_fx_seknok", "no_fx_dkknok",
               "no_fx_czknok"]
    fxnote = ("Euro members (and EUR-pegged EE from 1995, LT from 2003, LV from 2006) have zero yoy vs EUR; "
              "SK from 2010 (NaN before, SKK not in data). Before 1999 EUR = ECU: NO via NOK/SEK x SEK/ECU, "
              "DK and CZ via their NOK crosses; FI/AT/DE legacy currencies not in data (NaN before 1999).")
    for nm, d, comps, desc in (
            ("fx_vs_eur", fx_eur, fx_comp, "Orkla-weighted yoy change of local currency per EUR (+ = local "
                                           "currencies weaker vs EUR)"),
            ("fx_vs_usd", fx_usd, fx_comp + ["ea_fx_usd_per_eur", "no_fx_usdnok", "se_usdsek"],
             "Orkla-weighted yoy change of local currency per USD (+ = local currencies weaker vs USD; "
             "cross rates via EUR)"),
            ("fx_vs_nok", fx_nok, fx_comp + ["no_fx_seknok", "no_fx_dkknok", "no_fx_czknok"],
             "Orkla-weighted yoy change of local currency per NOK (+ = local currencies weaker vs NOK, i.e. "
             "negative translation effect for NOK reporting)")):
        w_composite(nm, {k: s.reindex(PIDX) for k, s in d.items()},
                    {k: (s - s.shift(4)).reindex(PIDX) for k, s in d.items()}, comps, desc, "fx",
                    extra_note=fxnote)

    # ---- surveys: selling-price expectations, consumer price expectations, household saving
    fsp = {"NO": "no_ssb_bts_consgoods_home_price_exp", "SE": "se_ec_food_ind_sell_price_exp"}
    fsp.update({cc(c): f"{c}_ec_food_ind_sell_price_exp" for c in EU_CC})
    lv = {k: lvl_d4(v) for k, v in fsp.items()}
    w_composite("ec_food_ind_sell_price_exp", {k: a for k, (a, b) in lv.items()}, {k: b for k, (a, b) in lv.items()},
                list(fsp.values()), "Orkla-weighted selling-price expectations of food manufacturers (EC BCS NACE "
                "C10 balance; Norway: SSB BTS consumer-goods home-market price expectations)", "price_expectations",
                kind="lvl")
    frp = {cc(c): f"{c}_ec_food_retail_sell_price_exp" for c in ["se"] + [c for c in EU_CC if c != "lt"]}
    lv = {k: lvl_d4(v) for k, v in frp.items()}
    w_composite("ec_food_retail_sell_price_exp", {k: a for k, (a, b) in lv.items()},
                {k: b for k, (a, b) in lv.items()}, list(frp.values()),
                "Orkla-weighted selling-price expectations of food retailers (EC retail FBT balance)",
                "price_expectations", kind="lvl", extra_note="No Norway data; LT excluded (noise).")
    cpe = {cc(c): f"{c}_ec_cons_price_exp_12m" for c in ["se"] + EU_CC}
    lv = {k: lvl_d4(v) for k, v in cpe.items()}
    w_composite("ec_cons_price_exp", {k: a for k, (a, b) in lv.items()}, {k: b for k, (a, b) in lv.items()},
                list(cpe.values()), "Orkla-weighted consumers' price expectations next 12 months (EC balance)",
                "price_expectations", kind="lvl", extra_note="No Norway data (renormalised).")
    sav = {cc(c): f"{c}_hh_saving_rate" for c in ["se", "dk", "fi", "cz", "at", "de", "hu", "pl"]}
    lv = {k: lvl_d4(v) for k, v in sav.items()}
    w_composite("hh_saving", {k: a for k, (a, b) in lv.items()}, {k: b for k, (a, b) in lv.items()},
                list(sav.values()), "Orkla-weighted gross household saving rate", "wages_income", kind="lvl",
                extra_note="No Norway/Baltic/SK data; RO excluded (noisy).")

    # ---- Nordic (NO+SE) composites
    def nw(name, m, desc, cat_, kind="yoy", comps=None, yo=None, dyo=None):
        if yo is None:
            yo = {k: y_(v) for k, v in m.items()}
            dyo = {k: dy_(v) for k, v in m.items()}
        w_composite(name, yo, dyo, comps or list(m.values()), desc, cat_, kind=kind, nordic=True)

    nw("food_cpi", {"NO": "no_cpi_food_idx", "SE": "se_cpi_food_idx"},
       "Nordic (NO+SE) food CPI inflation", "consumer_prices")
    nw("food_cpi_xvat", None, "Nordic (NO+SE) food CPI inflation adjusted for food-VAT changes",
       "consumer_prices", comps=["no_cpi_food_idx", "se_cpi_food_idx", "no_vat_food_rate", "se_food_vat_rate"],
       yo={k: xvat[k] for k in ("NO", "SE")}, dyo={k: xvat_d[k] for k in ("NO", "SE")})
    nw("real_wage", None, "Nordic (NO+SE) real wage growth (NO LCI, SE MI wage index, minus CPI)", "wages_income",
       comps=[wage["NO"], wage["SE"], cpi["NO"], cpi["SE"]],
       yo={k: rw[k] for k in ("NO", "SE")}, dyo={k: rw_d[k] for k in ("NO", "SE")})
    nw("cons_conf", None, "Nordic (NO+SE) consumer confidence z-score (Finans Norge; EC Sweden)",
       "consumer_survey", kind="z", comps=[conf["NO"], conf["SE"]],
       yo={k: z[k] for k in ("NO", "SE")}, dyo={k: zd[k] for k in ("NO", "SE")})
    nw("retail_food_vol", {"NO": "no_retail_foodstores_vol_sa_idx", "SE": "se_retail_grocery_vol_sa_idx"},
       "Nordic (NO+SE) grocery retail volume growth (SSB non-specialised food stores; SCB dagligvaruhandel)",
       "activity_retail")
    nw("food_ppi", {"NO": "no_ppi_food_dom_idx", "SE": "se_ppi_food_hmpi_idx"},
       "Nordic (NO+SE) domestic food-manufacturing PPI inflation", "producer_prices_input_costs")

    # ---- input-cost composites (GLOBAL)
    def g_comp(fid, yo, comps, desc, cat_, note=""):
        add_comp(fid + "_yoy", yo.reindex(PIDX), comps, desc + " [yoy, log points]", cat_, "GLOBAL", note, "yoy")
        add_comp(fid + "_dyoy", (yo - yo.shift(4)).reindex(PIDX), comps, desc + " [dyoy: yoy_t - yoy_t-4]",
                 cat_, "GLOBAL", note, "dyoy")

    g_comp("fao_ffpi_sek", YOY["glob_fao_ffpi"] + YOY["se_usdsek"], ["glob_fao_ffpi", "se_usdsek"],
           "FAO Food Price Index in SEK (USD index yoy + SEK/USD yoy)", "commodities")
    g_comp("wb_food_sek", YOY["glob_wb_food_idx"] + YOY["se_usdsek"], ["glob_wb_food_idx", "se_usdsek"],
           "World Bank food price index in SEK (USD index yoy + SEK/USD yoy)", "commodities")
    fx_usd_w, _, _ = wavg({k: s.reindex(PIDX) for k, s in fx_usd.items()}, W, MIN_COVERAGE_W, REL_COVERAGE_W)
    fx_usd_wq = fx_usd_w.reindex(QIDX)
    fxu_comps = fx_comp + ["ea_fx_usd_per_eur", "no_fx_usdnok", "se_usdsek"]
    g_comp("fao_ffpi_wloc", YOY["glob_fao_ffpi"] + fx_usd_wq, ["glob_fao_ffpi"] + fxu_comps,
           "FAO Food Price Index in Orkla-weighted local currency (USD index yoy + w_fx_vs_usd_yoy)", "commodities")
    g_comp("wb_food_wloc", YOY["glob_wb_food_idx"] + fx_usd_wq, ["glob_wb_food_idx"] + fxu_comps,
           "World Bank food index in Orkla-weighted local currency (USD index yoy + w_fx_vs_usd_yoy)",
           "commodities")
    agri = ["eu_agri_raw_milk_price", "eu_agri_butter_price", "eu_agri_smp_price", "eu_agri_pig_carcass_e_price",
            "eu_agri_beef_young_bulls_r3_price", "eu_agri_broiler_price", "eu_agri_sugar_white_price"]
    A_ = pd.DataFrame({s: YOY[s] for s in agri})
    basket = A_.mean(axis=1).where(A_.notna().sum(axis=1) >= 6)
    g_comp("eu_agri_basket", basket, agri, "EU agri raw-material basket in EUR: equal-weight mean of yoy of raw "
           "milk, butter, SMP, pig carcass, beef, broiler, white sugar (DG AGRI)", "commodities",
           "Requires >=6 of 7 components (white sugar only from 2007Q3). Wheat kept separate (from 2015-11).")
    fx_eur_w, _, _ = wavg({k: s.reindex(PIDX) for k, s in fx_eur.items()}, W, MIN_COVERAGE_W, REL_COVERAGE_W)
    g_comp("eu_agri_basket_wloc", basket + fx_eur_w.reindex(QIDX), agri + fx_comp,
           "EU agri basket converted to Orkla-weighted local currency (basket yoy + w_fx_vs_eur_yoy)", "commodities",
           "Requires >=6 of 7 basket components.")
    el = {"NO": YOY["no_elspot_no2_eur"] + YOY["no_fx_eurnok"], "SE": YOY["se_elspot_se3_sek_mwh"]}
    el_v, _, _ = wavg({k: s.reindex(PIDX) for k, s in el.items()}, NWW, MIN_COVERAGE_NW)
    g_comp("elec_nordic_loc", el_v.reindex(QIDX), ["no_elspot_no2_eur", "no_fx_eurnok", "se_elspot_se3_sek_mwh"],
           "Nordic wholesale electricity price in local currency (NO2 in NOK, SE3 in SEK), Nordic-weighted",
           "energy", "SE3 2011-01..10 is the system price (catalog splice).")
    g_comp("natgas_eu_eur", YOY["glob_wb_natgas_eu"] - usd_per_eur, ["glob_wb_natgas_eu", "ea_fx_usd_per_eur"],
           "EU natural gas price (WB Europe/TTF) in EUR", "energy",
           "NaN across WB definition changes 2000-06, 2010-04, 2015-04.")
    g_comp("brent_nok", YOY["glob_wb_brent"] + YOY["no_fx_usdnok"], ["glob_wb_brent", "no_fx_usdnok"],
           "Brent crude oil price in NOK", "energy")
    pk = pd.concat([YOY["eu_ppi_paper_packaging_idx"], YOY["eu_ppi_plastic_products_idx"]], axis=1)
    g_comp("packaging_eu", pk.mean(axis=1).where(pk.notna().all(axis=1)),
           ["eu_ppi_paper_packaging_idx", "eu_ppi_plastic_products_idx"],
           "EU packaging cost: mean of yoy of EU PPI paper & paperboard articles and plastic products",
           "packaging_freight")
    pku = pd.concat([YOY["us_ppi_plastic_resins_idx"], YOY["us_ppi_corrugated_boxes_idx"]], axis=1)
    g_comp("packaging_us", pku.mean(axis=1).where(pku.notna().all(axis=1)),
           ["us_ppi_plastic_resins_idx", "us_ppi_corrugated_boxes_idx"],
           "US packaging inputs: mean of yoy of US PPI plastic resins and corrugated boxes", "packaging_freight")

    # ---- spreads (price-cost gaps)
    def spread(fid, a_yoy, a_dyoy, b_yoy, b_dyoy, comps, desc, cat_="other", country="W", note=""):
        add_comp(fid, a_yoy - b_yoy, comps, desc + " [yoy gap, log points]", cat_, country, note, "spread")
        add_comp(fid + "_d4", a_dyoy - b_dyoy, comps, desc + " [d4 of gap = difference of the dyoy terms]",
                 cat_, country, note, "d4")

    cf = comp_feats
    cm = comp_meta
    comps_of = lambda *fids: sum([cm[f]["base_series"].split(",") for f in fids], [])
    spread("price_cost_gap_ppi", cf["w_food_cpi_yoy"], cf["w_food_cpi_dyoy"], cf["w_food_ppi_yoy"],
           cf["w_food_ppi_dyoy"], comps_of("w_food_cpi_yoy", "w_food_ppi_yoy"),
           "Price-cost gap: w_food_cpi_yoy - w_food_ppi_yoy (consumer food prices vs food-manufacturing PPI)",
           note="Country coverage differs between the two composites (no food PPI for EE/LV/SK/IN).")
    spread("price_cost_gap_fao_nok", cf["w_food_cpi_yoy"], cf["w_food_cpi_dyoy"],
           YOY["glob_fao_ffpi_nok"].reindex(PIDX), DYOY["glob_fao_ffpi_nok"].reindex(PIDX),
           comps_of("w_food_cpi_yoy") + ["glob_fao_ffpi_nok"],
           "Price-cost gap: w_food_cpi_yoy - FAO Food Price Index in NOK yoy")
    spread("price_cost_gap_agri", cf["w_food_cpi_yoy"], cf["w_food_cpi_dyoy"], cf["eu_agri_basket_yoy"],
           cf["eu_agri_basket_dyoy"], comps_of("w_food_cpi_yoy", "eu_agri_basket_yoy"),
           "Price-cost gap: w_food_cpi_yoy - EU agri raw-material basket yoy (EUR)")
    spread("price_cost_gap_fao_wloc", cf["w_food_cpi_yoy"], cf["w_food_cpi_dyoy"], cf["fao_ffpi_wloc_yoy"],
           cf["fao_ffpi_wloc_dyoy"], comps_of("w_food_cpi_yoy", "fao_ffpi_wloc_yoy"),
           "Price-cost gap: w_food_cpi_yoy - FAO Food Price Index in Orkla-weighted local currency yoy")
    spread("nw_price_cost_gap_ppi", cf["nw_food_cpi_yoy"], cf["nw_food_cpi_dyoy"], cf["nw_food_ppi_yoy"],
           cf["nw_food_ppi_dyoy"], comps_of("nw_food_cpi_yoy", "nw_food_ppi_yoy"),
           "Nordic price-cost gap: nw_food_cpi_yoy - nw_food_ppi_yoy", country="NORDIC")
    spread("price_wage_gap", cf["w_food_cpi_yoy"], cf["w_food_cpi_dyoy"], cf["w_wage_yoy"], cf["w_wage_dyoy"],
           comps_of("w_food_cpi_yoy", "w_wage_yoy"),
           "Price-wage gap: w_food_cpi_yoy - w_wage_yoy (selling prices vs labour-cost growth)")

    # ------------------------------------------------------------------ assemble
    panel = pd.DataFrame({k: v.reindex(PIDX) for k, v in feats.items()})
    cpanel = pd.DataFrame({k: v.reindex(PIDX) for k, v in comp_feats.items()})
    overlap = set(panel.columns) & set(cpanel.columns)
    assert not overlap, f"composite ids collide with base ids: {overlap}"
    panel = pd.concat([panel, cpanel], axis=1)
    meta = {**fmeta, **comp_meta}
    panel = panel.replace([np.inf, -np.inf], np.nan)
    empty = [c for c in panel.columns if panel[c].notna().sum() == 0]
    panel = panel.drop(columns=empty)
    assert panel.columns.is_unique, "duplicate feature ids"
    panel.index = pd.Index([str(p) for p in PIDX], name="period")
    panel = panel.round(6)
    panel.to_csv(OUT_PANEL, float_format="%.6g")

    # ------------------------------------------------------------------ dictionary
    drows = []
    for fid in panel.columns:
        m = meta[fid]
        s = panel[fid]
        nn = s.dropna()
        drows.append(dict(feature_id=fid, base_series=m["base_series"], folder=m["folder"],
                          transform=m["transform"], description=m["description"], country=m["country"],
                          category=m["category"], core=bool(m["core"]),
                          realtime_min_lag_q=int(m["realtime_min_lag_q"]),
                          start=nn.index[0] if len(nn) else "", end=nn.index[-1] if len(nn) else "",
                          n_obs=int(len(nn)), notes=m["notes"]))
    D = pd.DataFrame(drows)
    D.to_csv(OUT_DICT, index=False)

    # raw weights file (diagnostic)
    Wout = W.copy()
    Wout.index = pd.Index([str(p) for p in PIDX], name="period")
    Wout.insert(0, "weights_year", WMETA["weights_year"].values)
    Wout.insert(0, "segment_definition", WMETA["definition"].values)
    Wout.round(6).to_csv(OUT_W)

    # ------------------------------------------------------------------ checks
    for fid, ws in weight_checks.items():
        ws = ws.dropna()
        if len(ws) and not np.allclose(ws.values, 1.0, atol=1e-9):
            raise AssertionError(f"weights do not sum to 1 for {fid}")
    print(f"features: {panel.shape[1]} (base {sum(1 for c in panel.columns if '__' in c)}, "
          f"composite {sum(1 for c in panel.columns if '__' not in c)}); dropped empty: {empty}")
    print(f"core: {int(D.core.sum())}")
    print(D.groupby("category").agg(n=("feature_id", "size"), core=("core", "sum")).to_string())

    write_notes(D, W, WMETA, ROEFRAC, coverage, cat_all, panel, empty)
    return 0


# =============================================================================================
# notes
# =============================================================================================
def write_notes(D, W, WMETA, ROEFRAC, coverage, cat_all, panel, empty):
    L = []
    a = L.append
    a("# Macro feature panel (quarterly) - method notes")
    a("")
    a("Built by `macro_panel_build.py` (label macro-panel) on the data as of 2026-10-06 (latest Orkla report "
      "Q2 2026). Re-run with `python3 -I macro_panel_build.py`; the script reads only `data/macro/*/` and "
      "`data/orkla_raw/geo_weights.csv` and regenerates this file. Independent verification and fixes: "
      "`macro_panel_qa.md`.")
    a("")
    a("## Outputs")
    a("")
    a("| file | content |")
    a("|---|---|")
    a(f"| `macro_panel_quarterly.csv` | index `period` (YYYYQn) {P_START}..{P_END} ({len(PIDX)} rows) x "
      f"{panel.shape[1]} features |")
    a("| `feature_dictionary.csv` | one row per feature: base series, folder, transform, description, country, "
      "category, core flag, real-time lag, start/end/n_obs, notes |")
    a("| `macro_panel_geo_weights_quarterly.csv` | raw Orkla Foods country weights per quarter (before "
      "renormalisation over countries with data), with the segment definition and source year used |")
    a("")
    a("## 1. Method")
    a("")
    a("**Quarterly aggregation.** Monthly series: mean of the three months, only when all three are present "
      "(no partial quarters, so a quarter whose last month is not yet published is NaN). Quarterly series as "
      "published (first day of quarter -> quarter). Annual series: the annual value is assigned to all four "
      "quarters of the year (flagged `ANNUAL` in the dictionary notes); the agricultural settlement series "
      "(`no_jordbruk_*`, effective 1 July) are assigned by effective date to Q3(Y)..Q2(Y+1). Food VAT rates are "
      "monthly step series and are averaged within the quarter (so a mid-quarter change gives a fractional "
      "quarterly rate).")
    a("")
    a("**Look-ahead guard.** Nothing dated after Sep-2026 enters: monthly obs > 2026-09, quarterly obs > 2026Q3. "
      "This removes the ECB wage tracker's projected quarters 2026Q4-2027Q2 and the legislated future VAT "
      "months (NO to 2026-12, SE to 2026-10). The 2026Q3 wage-tracker value (current quarter at its latest "
      "release) is kept.")
    a("")
    a("**Transforms** (feature id = `<series_id>__<transform>`):")
    a("")
    a("| series type | transforms |")
    a("|---|---|")
    a("| index, price, currency level, volume, wage index, FX rate, income level | `yoy` = 100*ln(x_t/x_t-4); "
      "`dyoy` = yoy_t - yoy_t-4 |")
    a("| interest rates, yields, unemployment and saving rates (percent) | `lvl`; `d4` = x_t - x_t-4 |")
    a("| survey balances, confidence indicators (EC, OECD, NIER, Finans Norge, UMich), diffusion indices, "
      "expectations in percent, GSCPI | `lvl`; `d4` |")
    a("| series already in y/y growth (wage growth, real wage growth, credit growth, negotiated wages, "
      "wage tracker, frontfag) | `lvl`; `d4` |")
    a("| food VAT rates, agricultural settlement (NOK million changes) | `lvl`; `d4` |")
    a("")
    a("yoy is only computed for strictly positive values. Composites use `<name>_yoy`/`_dyoy`, "
      "`_lvl`/`_d4` or `_z`/`_z_d4`.")
    a("")
    a("**Duplicates.** Identical or near-identical copies across folders are kept once "
      f"({len(EXCLUDE)} series dropped):")
    a("")
    for (f, s), why in EXCLUDE.items():
        a(f"- `{f}/{s}`: {why}")
    a("")
    a("**Real-time availability (`realtime_min_lag_q`).** From the catalog's `approx_release_lag_days` "
      "(days after the end of the reference period): 0 if <= 14 (available before a quarterly report "
      "published ~2 weeks after quarter end), 1 if <= 100, else 2. Negative lags (surveys fielded inside the "
      "quarter, legislated rates) give 0. Annual series assigned to all four quarters are measured from the end "
      "of Q1 (lag + 275 days, then ceil((d-14)/91.3)), so annual outcomes (e.g. TBU wage growth) get 4 and the "
      "agricultural price index (budget estimate published Aug/Sep) gets 2; known-in-advance policy values get 0 "
      "(July-effective agricultural settlement assigned from Q3; frontfag frame, agreed by mid-April). Composites "
      "and spreads take the maximum over all component series. Note: country HICPs have a 17-day lag, so the "
      "Orkla-weighted price composites are lag 1 while the Nordic (NO+SE, national CPI) versions are lag 0.")
    a("")
    a("## 2. Orkla Foods geographic weights")
    a("")
    a("Shares of external revenue by customer location from `geo_weights.csv`, stepped by year, using the "
      "segment definition that was the reported food segment in each quarter:")
    a("")
    a("| quarters | definition used | source year of the split |")
    a("|---|---|---|")
    a("| 1995Q1-1999Q4 | 2000-2007 Orkla Foods (proxy = 2004 split) | 2000 row |")
    a("| 2000Q1-2006Q4 | 2000-2007 Orkla Foods (2000-03 proxy; 2004-06 exact) | same year |")
    a("| 2007Q1-2007Q4 | 2000-2007 Orkla Foods | 2006 (no 2007 split for this definition) |")
    a("| 2008Q1-2011Q4 | Orkla Foods Nordic (2008-2012 def.) | same year |")
    a("| 2012Q1-2012Q4 | Orkla Foods (2013-2014 def.) | 2012 (OFN 2012 split not published; Bakers sold Q1-2012) |")
    a("| 2013Q1-2014Q3 | Orkla Foods (2013-2014 def.) | 2013 |")
    a("| 2014Q4-2021Q4 | Orkla Foods (2015-2022 def., incl. India) | same year (AR rows) |")
    a("| 2022Q1-2022Q2 | Orkla Foods (2015-2022 def.) | 2021 |")
    a("| 2022Q3-2023Q4 | Orkla Foods Europe | same year |")
    a("| 2024Q1-2025Q4 | Orkla Foods (renamed, same scope) | same year |")
    a("| 2026Q1-2026Q3 | Orkla Foods | 2025 |")
    a("")
    a("Region -> country mapping:")
    a("")
    a("- Norway -> NO, Sweden -> SE, Denmark -> DK, Finland (and Iceland) -> FI.")
    a("- The Baltics -> EE, LV, LT (one third each). In the 2008-2014 definitions the Baltic food companies "
      "(and Kalev, 2010-2012) are booked as 'Central and Eastern Europe', which is therefore mapped to the "
      "Baltics as well.")
    a("- 2000-2007 definition: 'Rest of Western Europe' -> AT 60% (Felix Austria) / DE 40% (exports); "
      f"'Central and Eastern Europe' up to {A_CEE_NONRU_CAP}%: {A_CEE_BALTIC}pp -> Baltics (Baltic food companies "
      "were in Orkla Foods International until the 2008 restatement moved ~257 MNOK to OF Nordic), the rest -> "
      "PL, CZ, HU (+RO from 2002) equally; the excess in 2005-07 (SladCo/Krupskaya) -> Russia (no data). "
      "Asia / rest of world dropped.")
    a("- 2008-2014 definitions: 'Rest of Western Europe' -> DE; Asia, North America, other -> dropped.")
    a("- 2015-2022 definition: 'Rest of Europe' split into CZ+SK / AT / other using the project estimates in "
      "geo_weights (2017 and 2021 rows; 2014-15 from the 2015 Investor Day CZ 4% / AT 3%; 2016 = 2017; "
      "2018-20 linearly interpolated). CZ+SK -> CZ 75% / SK 25% (assumption). 'Other Europe' -> HU, RO, PL, DE, "
      "RU equally (RU has no data). 'Rest of the world' -> India (MTR, Eastern).")
    a("- Orkla Foods Europe / Orkla Foods (2022Q3-): 'Rest of Europe' split CZ+SK / AT / HU / other from the "
      "2023 and 2025 estimate rows (2022 = 2023, 2024 = average). 'Other' -> RO, DE, UK equally (UK no data). "
      "'Rest of the world' (exports, <1%) dropped.")
    a("")
    a("Rest-of-Europe composition used (fractions of the 'Rest of Europe' share):")
    a("")
    a("| year | CZ+SK | AT | HU | other |")
    a("|---|---|---|---|---|")
    for y, fr in sorted(ROEFRAC["D"].items()):
        a(f"| {y} (2015-22 def.) | {fr['CZSK']:.3f} | {fr['AT']:.3f} | in other | {fr['OTHER']:.3f} |")
    for y, fr in sorted(ROEFRAC["EF"].items()):
        a(f"| {y} (Europe def.) | {fr['CZSK']:.3f} | {fr['AT']:.3f} | {fr['HU']:.3f} | {fr['OTHER']:.3f} |")
    a("")
    a("Raw country weights (% of segment revenue; before renormalisation over countries with data). One row per "
      "change point:")
    a("")
    cols = ALL_COLS
    a("| period | def. | yr | " + " | ".join(cols) + " |")
    a("|---|---|---|" + "---|" * len(cols))
    prev = None
    for p in PIDX:
        row = tuple(np.round(W.loc[p].values * 100, 2))
        key = (WMETA.loc[p, "definition"], WMETA.loc[p, "weights_year"])
        if key != prev:
            a(f"| {p} | {key[0]} | {key[1]} | " + " | ".join(f"{v:.1f}" for v in row) + " |")
            prev = key
    a("")
    a("For each composite and quarter the weights of the countries that have data are renormalised to sum to 1 "
      f"(checked in the build). Orkla-weighted composites are NaN when the covered share is below "
      f"max({MIN_COVERAGE_W:.0%}, {REL_COVERAGE_W:.0%} x the composite's median coverage over 2005Q1-2025Q4), "
      "so that a quarter is not computed from a much smaller country set than usual (typically the latest "
      "quarter, when only the fast-publishing Nordic data are out, or years before a large country's series "
      "starts). Nordic composites (prefix `nw_`) use NO/(NO+SE) and require both countries.")
    a("")
    a("## 3. Composites and spreads")
    a("")
    a("Notation: yoy_c = country yoy (log points); w_c,t = renormalised Orkla weight. "
      "`w_X_yoy` = sum_c w_c,t * yoy_c,t. The dyoy/d4 companions are computed as the weighted average of the "
      "country-level dyoy/d4 with weights at t (not as a difference of the composite), so that changes in the "
      "weights (e.g. India leaving the segment in 2022Q3) do not create spurious jumps.")
    a("")
    a("| feature(s) | formula / components | lag |")
    a("|---|---|---|")
    comp = D[D.folder == "COMPOSITE"]
    seen = set()
    for _, r in comp.iterrows():
        fid = r.feature_id
        stem = re.sub(r"_(yoy|dyoy|lvl|d4|z|z_d4)$", "", fid)
        if fid.endswith("_z_d4"):
            stem = fid[:-5]
        if stem in seen:
            continue
        seen.add(stem)
        fam = comp[comp.feature_id.str.startswith(stem) & comp.feature_id.str.len().le(len(stem) + 6)]
        fam = fam[fam.feature_id.map(lambda x: re.sub(r"_(yoy|dyoy|lvl|d4|z|z_d4)$", "", x) in (stem,)
                                     or x[:-5] == stem or x == stem)]
        ids = ", ".join(f"`{x}`" for x in fam.feature_id)
        desc = re.sub(r"\s*\[.*?\]\s*$", "", r.description)
        countries = re.search(r"countries: ([A-Z,]+)", r.description)
        ctxt = f" Countries: {countries.group(1)}." if countries else ""
        bs = r.base_series.split(",")
        btxt = ", ".join(bs) if len(bs) <= 8 else ", ".join(bs[:8]) + f", ... ({len(bs)} series)"
        a(f"| {ids} | {desc}.{ctxt} Components: {btxt}. {r.notes} | {int(fam.realtime_min_lag_q.max())} |")
    a("")
    a("## 4. Break and data-quality handling")
    a("")
    a("| series | treatment |")
    a("|---|---|")
    for sid, (ms, why) in YOY_BREAK_MONTHS.items():
        extra = " (+ all quarters 2021Q1-2022Q4 for the 2021 change of unknown month)" if sid in YOY_BREAK_YEARS else ""
        a(f"| `{sid}` | yoy (and hence dyoy) NaN for the quarters whose 4-quarter comparison straddles "
          f"{', '.join(ms)}{extra}: {why} |")
    for sid, (ps, why) in YOY_BREAK_QUARTERS.items():
        a(f"| `{sid}` | yoy NaN {', '.join(ps)}: {why} |")
    for sid, (ps, why) in QUARTER_LEVEL_MASK.items():
        a(f"| `{sid}` | level NaN {', '.join(ps)} (d4 follows): {why} |")
    for sid, (ms, why) in D4_BREAK_MONTHS.items():
        a(f"| `{sid}` | d4 NaN across {', '.join(ms)}: {why} |")
    for sid, lst in LEVEL_MASK.items():
        for (_, _, x0, x1, why) in lst:
            a(f"| `{sid}` | values {x0 or 'start'}..{x1} set NaN: {why} |")
    a("| CEE survey series (cz, ee, hu, lt, lv, pl, ro, sk in SURVEYS) | values before 2000-01 set NaN "
      "(transition-era artefacts, qa_C 10) |")
    a("| `no_border_trade_*_s1` / `_s2` | separate features, never chained (survey design break 2023) |")
    a("| `ea_wage_tracker_yoy_q` | projected quarters after 2026Q3 removed |")
    a("| `no_vat_food_rate`, `se_food_vat_rate` | months after 2026-09 removed; used for VAT-adjusted food CPI "
      "composites |")
    for sid, why in NOISY_NOTES.items():
        if sid in ("ro_hh_saving_rate", "lt_gov_bond_10y", "ee_gov_bond_10y", "lt_ec_food_retail_sell_price_exp",
                   "se_elspot_se3_eur_mwh", "glob_wb_beef", "glob_wb_soybeans", "in_cpi_food_idx",
                   "no_elec_hh_energy_price"):
            a(f"| `{sid}` | kept as is: {why} |")
    a("")
    a("## 5. Coverage summary")
    a("")
    nb = int((D.folder != "COMPOSITE").sum())
    nc = int((D.folder == "COMPOSITE").sum())
    a(f"- Features: **{len(D)}** ({nb} base-series transforms from {len(set(D[D.folder != 'COMPOSITE'].base_series))} "
      f"series, {nc} composites/spreads). Core: **{int(D.core.sum())}**.")
    if empty:
        a(f"- Dropped because empty in {P_START}..{P_END}: {', '.join(empty)}")
    a("")
    a("By category:")
    a("")
    a("| category | features | core |")
    a("|---|---|---|")
    for k, g in D.groupby("category"):
        a(f"| {k} | {len(g)} | {int(g.core.sum())} |")
    a("")
    a("By folder:")
    a("")
    a("| folder | features | core |")
    a("|---|---|---|")
    for k, g in D.groupby("folder"):
        a(f"| {k} | {len(g)} | {int(g.core.sum())} |")
    a("")
    a("Real-time lag distribution (all / core):")
    a("")
    a("| realtime_min_lag_q | all | core |")
    a("|---|---|---|")
    for k, g in D.groupby("realtime_min_lag_q"):
        a(f"| {k} | {len(g)} | {int(g.core.sum())} |")
    a("")
    a("Feature start year (non-missing), all features:")
    a("")
    sy = D.start.str[:4].value_counts().sort_index()
    bins = {"1995-1999": 0, "2000-2004": 0, "2005-2009": 0, "2010-2014": 0, "2015+": 0}
    for yv, n in sy.items():
        yv = int(yv)
        k = ("1995-1999" if yv < 2000 else "2000-2004" if yv < 2005 else "2005-2009" if yv < 2010
             else "2010-2014" if yv < 2015 else "2015+")
        bins[k] += n
    a("| start | features |")
    a("|---|---|")
    for k, v in bins.items():
        a(f"| {k} | {v} |")
    a("")
    a("Composite coverage (share of Orkla Foods revenue in countries with data; mean over quarters with a value):")
    a("")
    a("| composite | start | end | n_obs | mean coverage 2005-2026 | min coverage 2005-2026 |")
    a("|---|---|---|---|---|---|")
    for fid, cv in coverage.items():
        if fid not in D.feature_id.values or fid.startswith("nw_"):
            continue
        r = D.set_index("feature_id").loc[fid]
        c = cv[(cv.index >= pd.Period("2005Q1"))]
        c = c[panel[fid].reindex([str(p) for p in c.index]).notna().values]
        if len(c) == 0:
            continue
        a(f"| `{fid}` | {r.start} | {r.end} | {r.n_obs} | {c.mean():.2f} | {c.min():.2f} |")
    a("")
    a("## 6. Caveats")
    a("")
    a("- Geographic weights before 2004 are a proxy (2004 split); the 'Rest of Europe' country split is a "
      "project estimate (+/-2pp) and the CZ/SK split is an assumption. Weights matter mainly for the non-Nordic "
      "15-30% of revenue; NO+SE are 54-81% throughout.")
    a("- Early history: HICPs start in 1996 (yoy from 1997) and most Eurostat LCI/retail/PPI series in 2000, so "
      "Orkla-weighted composites start when enough countries are available (see the coverage table); Orkla's own "
      "quarterly segment data start in 2000, so this rarely binds. The latest quarter of a composite is NaN "
      "until most countries have published.")
    a("- Country data sources differ across composites (national CPI vs HICP, LCI vs national wage indices); "
      "the Nordic `nw_` versions use national sources only.")
    a("- Organic growth excludes FX, but reported revenue does not: `w_fx_vs_nok_yoy` captures the translation "
      "effect for NOK reporting. Food CPIs include VAT, so the Swedish food-VAT cut (12% -> 6%, 2026-04) "
      "depresses `se_cpi_food_idx__yoy`, `w_food_cpi_yoy` and the price-cost gaps from 2026Q2 although Orkla's "
      "net sales are ex VAT; use the `*_food_cpi_xvat_*` variants for that episode (and the 2001-07 Norwegian cut).")
    a("- All values are the latest vintage (revised national accounts, preliminary wage statistics, re-estimated "
      "seasonal factors). `realtime_min_lag_q` handles publication lags but not revisions.")
    a("- Other real-time caveats (QA verify-panel):")
    a("  - The geographic weights for year Y come from the annual report for Y, published in Feb-Mar of Y+1, so the "
      "weights are not strictly real-time. They are slow-moving structural shares, and the large steps "
      "(e.g. Hame in 2016, India leaving in 2022Q3) were announced in advance.")
    a("  - Consumer-confidence z-scores use each country's 2000-2025 mean and standard deviation. This scaling uses "
      "the full sample; it changes the relative country weights in `w_cons_conf_z`, not its timing.")
    a("  - `no_frontfag_frame_a` is lag 0 (frame agreed by mid-April), but the 2020 settlement was postponed "
      "(COVID-19), so its 2020Q1-Q2 values were not known in real time. The ECB wage tracker's 2013- history is a "
      "back-calculation. The latest month of euro-area countries' all-items HICP (Sep-2026) is a national flash "
      "estimate.")
    a("  - `no_jordbruk_malpris_mnok` changes scope from the 2025 settlement: milk is no longer target-priced. "
      "`d4` is masked for 2025Q3-2026Q2, and `lvl` from 2025Q3 is not comparable with earlier years.")
    a("- Quarterly means of daily/hourly prices (electricity, gas) are very volatile in log terms; electricity "
      "yoy reaches +/-150 log points in 2020-2023.")
    a("- Several series are flagged in the dictionary notes (preliminary latest values, discontinued series, "
      "documented splices). The screening stage should prefer `core` features and respect "
      "`realtime_min_lag_q` when lining features up with Orkla quarters.")
    OUT_NOTES.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
