"""Curated candidate predictors: one representative series per economic concept.

Each entry: concept key, human label, source series (or a derived recipe), the
transforms to test and the prior sign for (sales growth, gross-margin change).
Priors: "+", "-" or "?" (ambiguous / competing mechanisms). Transforms:
  g4  = y/y log growth of the quarterly (3-month) mean, %
  lvl = level of the quarterly mean (rates, balances, survey scores)
  d4  = y/y change of the quarterly mean (pp)

Calendar-adjusted (_ca) retail indices are used so y/y growth is not driven by
Easter / trading-day shifts. Spliced / long-history variants are preferred so
that the placebo test and the 25-year proxy target can use them.
"""

CANDIDATES = [
    # --- Demand: retail sales & household consumption ---------------------
    dict(key="rti_4719_value", label="Retail sales, non-specialised non-food stores (NACE 47.19), value",
         series="ssb_rti_4719_nonspec_nonfood_value_ca", tf=["g4"], prior=("+", "?"), group="demand"),
    dict(key="rti_4719_value_nsa", label="Retail sales NACE 47.19, value, unadjusted",
         series="ssb_rti_4719_nonspec_nonfood_value_nsa", tf=["g4"], prior=("+", "?"), group="demand"),
    dict(key="rti_4719_volume", label="Retail sales NACE 47.19, volume",
         series="ssb_rti_4719_nonspec_nonfood_volume_ca", tf=["g4"], prior=("+", "?"), group="demand"),
    dict(key="rti_retail_exfuel_value", label="Retail sales excl. fuel (NACE 47 ex 47.3), value",
         series="ssb_rti_47x473_retail_ex_fuel_value_ca", tf=["g4"], prior=("+", "?"), group="demand"),
    dict(key="rti_retail_exfuel_volume", label="Retail sales excl. fuel, volume",
         series="ssb_rti_47x473_retail_ex_fuel_volume_ca", tf=["g4"], prior=("+", "?"), group="demand"),
    dict(key="rti_grocery_value", label="Grocery retail sales (NACE 47.11), value",
         series="ssb_rti_4711_grocery_value_ca", tf=["g4"], prior=("+", "?"), group="demand"),
    dict(key="rti_hh_equip_value", label="Household-equipment retail sales (NACE 47.5), value",
         series="ssb_rti_475_household_equip_value_ca", tf=["g4"], prior=("+", "?"), group="demand"),
    dict(key="rti_online_value", label="Mail-order/internet retail sales (NACE 47.91), value",
         series="ssb_rti_4791_mail_order_internet_value_ca", tf=["g4"], prior=("-", "?"), group="demand"),
    dict(key="hh_cons_goods", label="Household consumption of goods, constant prices (QNA)",
         series="ssb_qna_hh_cons_goods_const_nsa", tf=["g4"], prior=("+", "?"), group="demand"),
    dict(key="hh_cons_total", label="Household consumption total, constant prices (QNA)",
         series="ssb_qna_hh_cons_total_const_nsa", tf=["g4"], prior=("+", "?"), group="demand"),
    dict(key="hh_cons_semidurable", label="Household consumption semi-durable goods (QNA)",
         series="ssb_qna_hh_cons_semidurable_goods_const_nsa", tf=["g4"], prior=("+", "?"), group="demand"),
    dict(key="hh_cons_abroad", label="Household direct purchases abroad incl. cross-border, constant prices (QNA)",
         series="ssb_qna_hh_cons_direct_purch_abroad_const_nsa", tf=["g4"], prior=("-", "?"), group="crossborder"),
    dict(key="imports_consumer_volume", label="Import volume, consumer goods (BEC)",
         series="ssb_imports_bec_consumer_goods_volume_idx", tf=["g4"], prior=("+", "?"), group="demand"),
    # --- Income, labour ------------------------------------------------------
    dict(key="real_disp_income", label="Household real disposable income (QNA)",
         series="ssb_hh_real_disp_income_2015p_nsa", tf=["g4"], prior=("+", "?"), group="income"),
    dict(key="saving_ratio", label="Household saving ratio (SA)",
         series="ssb_hh_saving_ratio_sa", tf=["lvl", "d4"], prior=("-", "?"), group="income"),
    dict(key="saving_ratio_exdiv", label="Household saving ratio excl. dividends (SA)",
         series="ssb_hh_saving_ratio_ex_div_sa", tf=["lvl", "d4"], prior=("?", "?"), group="income"),
    dict(key="real_disp_income_exdiv", label="Household real disposable income excl. dividends (QNA / CPI)",
         derived="real_disp_income_exdiv", tf=["g4"], prior=("+", "?"), group="income"),
    dict(key="unemployment", label="LFS unemployment rate (SA)",
         series="ssb_lfs_unemp_rate_sa", tf=["lvl", "d4"], prior=("?", "?"), group="labour"),
    dict(key="employment", label="Employed persons, register (SA)",
         series="ssb_employees_register_all_sa_final", tf=["g4"], prior=("+", "?"), group="labour"),
    dict(key="employment_rate", label="LFS employment rate (SA)",
         series="ssb_lfs_employment_rate_sa", tf=["lvl", "d4"], prior=("+", "?"), group="labour"),
    dict(key="wage_bill", label="Total wages paid, nominal (QNA)",
         series="ssb_qna_total_wages_nsa", tf=["g4"], prior=("+", "-"), group="income"),
    dict(key="real_wage_bill", label="Real wage bill (QNA wages deflated by CPI)",
         derived="real_wage_bill", tf=["g4"], prior=("+", "?"), group="income"),
    dict(key="labour_cost_trade", label="Labour cost index, wholesale & retail trade",
         series="ssb_labour_cost_idx_trade", tf=["g4"], prior=("?", "-"), group="costs"),
    # --- Prices --------------------------------------------------------------
    dict(key="cpi_total", label="CPI, total", series="ssb_cpi_total", tf=["g4"], prior=("+", "?"), group="prices"),
    dict(key="cpi_ate", label="CPI-ATE (core)", series="ssb_cpi_ate", tf=["g4"], prior=("+", "?"), group="prices"),
    dict(key="cpi_imported", label="CPI, imported consumer goods (spliced)",
         series="ssb_cpi_dsec_imported_goods_spliced", tf=["g4"], prior=("+", "?"), group="prices"),
    dict(key="cpi_food", label="CPI, food & non-alcoholic beverages",
         series="ssb_cpi_coicop_01_food_nonalc_bev", tf=["g4"], prior=("+", "?"), group="prices"),
    dict(key="cpi_furnishings", label="CPI, furnishings & household equipment",
         series="ssb_cpi_coicop_05_furnishings_hh_equip", tf=["g4"], prior=("+", "+"), group="prices"),
    dict(key="cpi_nondurable_hh", label="CPI, non-durable household goods",
         series="ssb_cpi_coicop_0561_nondurable_hh_goods", tf=["g4"], prior=("+", "+"), group="prices"),
    dict(key="cpi_electricity", label="CPI, electricity", series="ssb_cpi_coicop_0451_electricity",
         tf=["g4"], prior=("-", "?"), group="prices"),
    dict(key="elec_price_hh", label="Household electricity price incl. grid and taxes, net of support",
         series="ssb_elec_hh_total_price_net_support", tf=["g4"], prior=("-", "?"), group="prices"),
    dict(key="import_price_misc_manuf", label="Import price index, misc. manufactured goods (SITC 8), NOK",
         series="ssb_import_price_idx_sitc8_misc_manufactured", tf=["g4"], prior=("+", "-"), group="costs"),
    dict(key="import_price_consumer", label="Import price index, consumer goods (BEC), NOK",
         series="ssb_imports_bec_consumer_goods_price_idx", tf=["g4"], prior=("+", "-"), group="costs"),
    dict(key="ppi_consumer", label="PPI, domestic consumer goods", series="ssb_ppi_domestic_consumer_goods",
         tf=["g4"], prior=("+", "-"), group="costs"),
    # --- Housing, credit, population ----------------------------------------
    dict(key="house_prices", label="House price index, Norway", series="ssb_house_price_idx_total_nsa",
         tf=["g4"], prior=("+", "?"), group="housing"),
    dict(key="dwelling_starts", label="Dwelling starts (SA)", series="ssb_dwelling_starts_sa",
         tf=["g4"], prior=("+", "?"), group="housing"),
    dict(key="k2_households", label="Household credit growth (K2, 12-month)", series="ssb_k2_households_yoy",
         tf=["lvl", "d4"], prior=("+", "?"), group="credit"),
    dict(key="population", label="Population", series="ssb_population_end_q", tf=["g4"], prior=("+", "?"), group="population"),
    # --- Rates & financial conditions ---------------------------------------
    dict(key="policy_rate", label="Norges Bank policy rate", series="mkt_no_policy_rate_avg",
         tf=["lvl", "d4"], prior=("?", "?"), group="rates"),
    dict(key="nibor_3m", label="3-month NIBOR", series="mkt_no_interbank_3m_rate_oecd",
         tf=["lvl", "d4"], prior=("?", "?"), group="rates"),
    dict(key="govt_10y", label="10-year government bond yield", series="mkt_no_govt_10y_yield_oecd",
         tf=["lvl", "d4"], prior=("?", "?"), group="rates"),
    # --- Currency ------------------------------------------------------------
    dict(key="usdnok", label="USD/NOK (NOK per USD; up = weaker krone)", series="mkt_nok_per_usd_avg",
         tf=["g4"], prior=("+", "-"), group="fx"),
    dict(key="eurnok", label="EUR/NOK", series="mkt_nok_per_eur_avg", tf=["g4"], prior=("+", "-"), group="fx"),
    dict(key="cnynok", label="CNY/NOK", series="mkt_nok_per_100cny_avg", tf=["g4"], prior=("+", "-"), group="fx"),
    dict(key="i44", label="Import-weighted krone index I-44 (up = weaker)", series="mkt_nok_i44_import_weighted_avg",
         tf=["g4"], prior=("+", "-"), group="fx"),
    dict(key="seknok", label="SEK/NOK (NOK per 100 SEK; up = Sweden dearer)", series="mkt_nok_per_100sek_avg",
         tf=["g4"], prior=("+", "?"), group="crossborder"),
    dict(key="real_seknok", label="Real SEK/NOK (Swedish vs Norwegian price level, HICP)",
         derived="real_seknok", tf=["g4"], prior=("+", "?"), group="crossborder"),
    dict(key="real_seknok_food", label="Real SEK/NOK on food prices (HICP food)",
         derived="real_seknok_food", tf=["g4"], prior=("+", "?"), group="crossborder"),
    # --- Sentiment & surveys -------------------------------------------------
    dict(key="cci", label="Consumer confidence (Finans Norge, SA)", series="mkt_no_finansnorge_cci_sa",
         tf=["lvl", "d4"], prior=("+", "?"), group="sentiment"),
    dict(key="cci_own_fin_next", label="Consumer confidence: own finances next year",
         series="mkt_no_finansnorge_cci_own_finances_next_year", tf=["lvl", "d4"], prior=("+", "?"), group="sentiment"),
    dict(key="cci_major_purchases", label="Consumer confidence: good time for major purchases",
         series="mkt_no_finansnorge_cci_major_purchases", tf=["lvl", "d4"], prior=("+", "?"), group="sentiment"),
    dict(key="business_conf", label="OECD business confidence, Norway", series="mkt_no_oecd_business_confidence",
         tf=["lvl", "d4"], prior=("+", "?"), group="sentiment"),
    dict(key="regnet_retail_now", label="Regional Network: retail output growth, current quarter",
         series="mkt_no_regnet_output_retail_curr_q", tf=["lvl", "d4"], prior=("+", "?"), group="sentiment"),
    dict(key="regnet_retail_next", label="Regional Network: retail expected output growth, next quarter",
         series="mkt_no_regnet_output_retail_next_q", tf=["lvl", "d4"], prior=("+", "?"), group="sentiment"),
    dict(key="regnet_retail_profit", label="Regional Network: retail profitability",
         series="mkt_no_regnet_profitability_retail", tf=["lvl", "d4"], prior=("+", "+"), group="sentiment"),
    dict(key="cci_country_next", label="Consumer confidence: Norway's economy next year (Finans Norge)",
         series="mkt_no_finansnorge_cci_country_next_year", tf=["lvl", "d4"], prior=("+", "+"), group="sentiment"),
    dict(key="cci_country_past", label="Consumer confidence: Norway's economy vs a year ago (Finans Norge)",
         series="mkt_no_finansnorge_cci_country_past_year", tf=["lvl", "d4"], prior=("+", "+"), group="sentiment"),
    dict(key="cci_own_fin_past", label="Consumer confidence: own finances vs a year ago (Finans Norge)",
         series="mkt_no_finansnorge_cci_own_finances_past_year", tf=["lvl", "d4"], prior=("+", "+"), group="sentiment"),
    dict(key="extra_save", label="Finans Norge: share who would save extra money",
         series="mkt_no_finansnorge_extra_money_save", tf=["lvl", "d4"], prior=("-", "?"), group="sentiment"),
    dict(key="extra_paydown", label="Finans Norge: share who would pay down debt with extra money",
         series="mkt_no_finansnorge_extra_money_pay_down_debt", tf=["lvl", "d4"], prior=("-", "?"), group="sentiment"),
    dict(key="extra_brown", label="Finans Norge: share who would buy consumer electronics",
         series="mkt_no_finansnorge_extra_money_brown_goods", tf=["lvl", "d4"], prior=("+", "?"), group="sentiment"),
    dict(key="extra_white", label="Finans Norge: share who would buy household appliances",
         series="mkt_no_finansnorge_extra_money_white_goods", tf=["lvl", "d4"], prior=("+", "?"), group="sentiment"),
    dict(key="regnet_total_next", label="Regional Network: expected output growth, all sectors",
         series="mkt_no_regnet_output_total_next_q", tf=["lvl", "d4"], prior=("+", "?"), group="sentiment"),
    # --- Global cost shocks --------------------------------------------------
    dict(key="gscpi", label="NY Fed Global Supply Chain Pressure Index", series="mkt_gscpi",
         tf=["lvl", "d4"], prior=("?", "-"), group="global_costs"),
    dict(key="freight_ppi", label="US PPI deep-sea freight", series="mkt_us_ppi_deep_sea_freight",
         tf=["g4"], prior=("?", "-"), group="global_costs"),
    dict(key="brent_nok", label="Brent crude in NOK", derived="brent_nok", tf=["g4"], prior=("-", "-"), group="global_costs"),
    dict(key="cotton", label="Cotton price (USD)", series="mkt_cotton_price_usc_lb", tf=["g4"], prior=("?", "-"), group="global_costs"),
    dict(key="china_export_prices", label="US import prices from China (USD)", series="mkt_us_import_price_from_china",
         tf=["g4"], prior=("?", "-"), group="global_costs"),
    dict(key="china_prices_nok", label="Chinese export prices in NOK (US import prices from China x USD/NOK)",
         derived="china_prices_nok", tf=["g4"], prior=("+", "-"), group="global_costs"),
    # --- Weather ---------------------------------------------------------------
    dict(key="temp_oslo", label="Mean temperature, Oslo-Blindern", series="mkt_oslo_blindern_temp_mean_c",
         tf=["d4"], prior=("?", "?"), group="weather"),
]

# Europris's own store-count growth is added by the screen (company variable).
COMPANY = [dict(key="store_growth", label="Europris chain store count, y/y growth", tf=["g4"],
                prior=("+", "?"), group="company")]


# Derived series: name -> (component series, function of a dict of aligned series).
# All components share one frequency; the derived publication lag is the max of
# the components' lags.
# Series whose catalog lag is the preliminary release but the final series is used.
LAG_OVERRIDE = {"ssb_employees_register_all_sa_final": 54.0}

# Excluded after the code audit: re-estimated over the full history each vintage,
# so the downloaded history is not what was known in real time.
EXCLUDED = {"fci": "Norges Bank FCI (mkt_no_fci_*) is model-based and re-estimated each vintage - not real-time."}

DERIVED = {
    "real_disp_income_exdiv": (["ssb_hh_disp_income_ex_div_nsa", "ssb_cpi_total"],
                               lambda d: d["ssb_hh_disp_income_ex_div_nsa"] / d["ssb_cpi_total"]),
    "real_wage_bill": (["ssb_qna_total_wages_nsa", "ssb_cpi_total"],
                       lambda d: d["ssb_qna_total_wages_nsa"] / d["ssb_cpi_total"]),
    "real_seknok": (["mkt_nok_per_100sek_avg", "mkt_hicp_se_all_items_2015", "mkt_hicp_no_all_items_2015"],
                    lambda d: d["mkt_nok_per_100sek_avg"] * d["mkt_hicp_se_all_items_2015"] / d["mkt_hicp_no_all_items_2015"]),
    "real_seknok_food": (["mkt_nok_per_100sek_avg", "mkt_hicp_se_food_2015", "mkt_hicp_no_food_2015"],
                         lambda d: d["mkt_nok_per_100sek_avg"] * d["mkt_hicp_se_food_2015"] / d["mkt_hicp_no_food_2015"]),
    "brent_nok": (["mkt_brent_usd_avg", "mkt_nok_per_usd_avg"],
                  lambda d: d["mkt_brent_usd_avg"] * d["mkt_nok_per_usd_avg"]),
    "china_prices_nok": (["mkt_us_import_price_from_china", "mkt_nok_per_usd_avg"],
                         lambda d: d["mkt_us_import_price_from_china"] * d["mkt_nok_per_usd_avg"]),
}
