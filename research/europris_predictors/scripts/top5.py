"""The final top-5 predictors (+ runners-up), v3.

Chosen from pre-holdout evidence (results/benchmark_components.csv,
calendar_joint.csv, evidence_all.csv, exploratory_shortlist.csv) and three
rounds of independent verification (replication, adversarial robustness,
cross-company tests on Clas Ohlson and Kid ASA, code audits). The holdout
(2024Q3-2026Q2) is reported by evaluate_top.py as the final test.

Grades
  ESTABLISHED  survives exact randomisation tests at every horizon and the holdout.
  MODERATE     consistent across two independent samples, but thin on Europris alone.
  FRAGILE      significant on Europris (calibrated p < 0.05 in both COVID specs)
               but driven by one episode or not confirmed out of sample.
"""

PICKS = [
    dict(rank=1, key="easter", short="Easter timing", kind="calendar", component="c_easter_share_d4",
         label="Easter timing: share of the 14-day pre-Easter shopping window falling in the quarter (y/y change)",
         targets=["lfl", "rev_yoy"], hs=[1, 2, 4, 6], horizon_class="short and long (known years ahead)",
         sign="+", grade="ESTABLISHED",
         mechanism="Easter is Europris's biggest seasonal event after Christmas; when the pre-Easter weeks move "
                   "between Q1 and Q2, sales move with them (management quantifies -5 to +7 pp)."),
    dict(rank=2, key="tdays", short="trading days", kind="calendar", component="c_tdays_d4",
         label="Shop trading days in the quarter (Mon-Sat excl. public holidays), y/y difference",
         targets=["lfl", "rev_yoy"], hs=[1, 2, 4, 6], horizon_class="short and long (known years ahead)",
         sign="+", grade="ESTABLISHED",
         mechanism="Stores are closed on Sundays and public holidays; one extra trading day adds roughly 2-3 pp to "
                   "quarterly like-for-like growth (overlapping with the Easter effect)."),
    dict(rank=3, key="house_prices", short="house prices", kind="macro", feature="house_prices__g4",
         label="House prices, y/y % (SSB house price index)",
         targets=["lfl", "rev_yoy"], hs=[1, 2], horizon_class="short (next 1-2 quarters)", sign="+", grade="MODERATE",
         mechanism="Housing wealth and home-related purchases; positive slope in every sub-period of 25 years of "
                   "category sales (NACE 47.19), including the pre-2015 period independent of the Europris sample."),
    dict(rank=4, key="store_pace", short="store openings", kind="macro", feature="eu_store_growth__g4",
         label="Europris chain store count, y/y growth (pre-approved store pipeline)",
         targets=["ebitm_d4"], hs=[2], horizon_class="short (2 quarters)", sign="-", grade="FRAGILE",
         mechanism="Faster store expansion is followed by a lower EBIT margin two quarters later; the significance "
                   "leans on 2019 (central-warehouse cost overruns coincided)."),
    dict(rank=5, key="krone", short="krone (CNY/NOK)", kind="macro", feature="cnynok__g4",
         label="Krone vs Chinese yuan (CNY/NOK y/y %; USD/NOK similar)",
         targets=["gm_d4"], hs=[4], horizon_class="long (4 quarters)", sign="-", grade="FRAGILE",
         mechanism="Purchases are paid in USD, hedged up to 6 months, and inventory turns in ~5 months, so a weaker "
                   "krone reaches cost of goods ~4 quarters later. Rests on the 2015-16 krone shock; not confirmed "
                   "at Clas Ohlson or Kid; negative in the 2024-26 holdout when the stronger krone was passed on."),
]

RUNNERS_UP = [
    dict(rank=6, key="cci_country_next", short="consumer expectations", kind="macro",
         feature="cci_country_next__lvl", label="Finans Norge: households' view of Norway's economy next year",
         targets=["gm_d4"], hs=[2, 4], horizon_class="medium (2-4 quarters)", sign="+", grade="FRAGILE",
         mechanism="Only significant in the COVID-control spec; moves with the krone."),
    dict(rank=7, key="saving_ratio", short="saving ratio", kind="macro", feature="saving_ratio__d4",
         label="Household saving ratio, y/y change", targets=["lfl"], hs=[6], horizon_class="long (6 quarters)",
         sign="+", grade="FRAGILE", mechanism="Single-horizon spike; dividend-tax artefacts in the SSB series."),
]
