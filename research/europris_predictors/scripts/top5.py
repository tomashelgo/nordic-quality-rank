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
  WEAK         below the fragile bar (p < 0.05 in only one spec or 0.05-0.10 in
               both) but consistently signed across independent checks; the best
               of the non-calendar candidates tested in round 4 (new variables).
"""

# Easter timing and shop trading days are not listed: they are obvious calendar
# effects (established, see results/benchmark_components.csv and
# calendar_joint.csv) and stay in every benchmark as controls.
CALENDAR_CONTROLS = ["c_easter_share_d4", "c_tdays_d4"]

PICKS = [
    dict(rank=1, key="house_prices", short="house prices", kind="macro", feature="house_prices__g4",
         label="House prices, y/y % (SSB house price index)",
         targets=["lfl", "rev_yoy"], hs=[1, 2], horizon_class="short (next 1-2 quarters)", sign="+", grade="MODERATE",
         mechanism="Housing wealth and home-related purchases; positive slope in every sub-period of 25 years of "
                   "category sales (NACE 47.19), including the pre-2015 period independent of the Europris sample."),
    dict(rank=2, key="store_pace", short="store openings", kind="macro", feature="eu_store_growth__g4",
         label="Europris chain store count, y/y growth (pre-approved store pipeline)",
         targets=["ebitm_d4"], hs=[2], horizon_class="short (2 quarters)", sign="-", grade="FRAGILE",
         mechanism="Faster store expansion is followed by a lower EBIT margin two quarters later; the significance "
                   "leans on 2019 (central-warehouse cost overruns coincided)."),
    dict(rank=3, key="krone", short="krone (CNY/NOK)", kind="macro", feature="cnynok__g4",
         label="Krone vs Chinese yuan (CNY/NOK y/y %; USD/NOK similar)",
         targets=["gm_d4"], hs=[4], horizon_class="long (4 quarters)", sign="-", grade="FRAGILE",
         mechanism="Purchases are paid in USD, hedged up to 6 months, and inventory turns in ~5 months, so a weaker "
                   "krone reaches cost of goods ~4 quarters later. Rests on the 2015-16 krone shock; not confirmed "
                   "at Clas Ohlson or Kid; mixed in the 2024-26 holdout when the stronger krone was passed on."),
    dict(rank=4, key="int_burden", short="interest burden", kind="macro", feature="new_hhf_int_burden__d4",
         label="Household interest burden (interest expenses / disposable income excl. dividends, SSB 11020), y/y change in pp",
         targets=["rev_yoy"], hs=[3, 4], horizon_class="long (3-4 quarters)", sign="-", grade="WEAK",
         mechanism="Norwegian mortgages are mostly floating-rate, so rate changes hit household cash flow with a lag; "
                   "a rising burden is followed by weaker sales 3-4 quarters later. Same sign at h=1-5, in the 2008-09 "
                   "cycle, in the 25-year category data and in 11 of 12 holdout cells, but significant only when "
                   "COVID-era quarters are kept (p 0.03 vs 0.19), not visible in like-for-like, and largely the same "
                   "information as the policy-rate change."),
    dict(rank=5, key="employment", short="employment growth", kind="macro", feature="employment__g4",
         label="Employed persons, register (SA), y/y %",
         targets=["lfl"], hs=[8], horizon_class="long (~8 quarters)", sign="+", grade="WEAK",
         mechanism="Job growth lifts household income and spending with a long lag; the best-scoring candidate on a "
                   "uniform robustness battery (10/15), robust to dropping 2016, positive at neighbouring horizons, "
                   "but p 0.06-0.08, rests on 2016-19 targets, opposite sign in pre-2015 category data, and absorbed "
                   "by the krone in the COVID-excluded spec."),
]

RUNNERS_UP = [
    dict(rank=8, key="spend_abroad", short="spending abroad", kind="macro", feature="hh_cons_abroad__g4",
         label="Household purchases abroad (QNA), y/y", targets=["lfl"], hs=[4], horizon_class="long (4 quarters)",
         sign="-", grade="REJECTED", mechanism="Formally p<0.05 in both specs but spurious: ~87% holiday travel, "
         "isolated h=4 spike, opposite sign in 25-year category data, holdout relation reversed."),
    dict(rank=6, key="cci_country_next", short="consumer expectations", kind="macro",
         feature="cci_country_next__lvl", label="Finans Norge: households' view of Norway's economy next year",
         targets=["gm_d4"], hs=[2, 4], horizon_class="medium (2-4 quarters)", sign="+", grade="FRAGILE",
         mechanism="Only significant in the COVID-control spec; moves with the krone."),
    dict(rank=7, key="saving_ratio", short="saving ratio", kind="macro", feature="saving_ratio__d4",
         label="Household saving ratio, y/y change", targets=["lfl"], hs=[6], horizon_class="long (6 quarters)",
         sign="+", grade="FRAGILE", mechanism="Single-horizon spike; dividend-tax artefacts in the SSB series."),
]
