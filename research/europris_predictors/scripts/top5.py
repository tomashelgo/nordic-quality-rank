"""The selected top-5 predictors (+ runner-up), chosen from results/evidence_*.csv
and results/incremental_tests.csv WITHOUT using holdout (2024Q3-2026Q2) results.

Selection: concepts passing the confirmation rule in rank_evidence.py, ranked by
evidence score, after removing concepts that do not add information beyond a
stronger correlated one (incremental.py): USD/NOK, I-44 and Chinese export
prices in NOK collapse into the CNY/NOK currency concept; population, business
confidence, retail volume and employment growth are absorbed by FX, FCI or
unemployment. Saving-ratio change passes the two-sample evidence but its sign is
opposite to the (naive) prior written beforehand, so it is reported as the
runner-up rather than in the top 5.
"""

PICKS = [
    dict(rank=1, key="cnynok", feature="cnynok__g4", label="Krone vs Chinese yuan (CNY/NOK, y/y %)",
         targets=["gm_d4"], hs=[3, 4], horizon_class="long (4 quarters; already visible at 3)",
         sign="-", alt="usdnok__g4",
         mechanism="Most goods are sourced from China and paid in USD; purchase orders are hedged up to 6 "
                   "months and inventory turns in ~5 months, so a weaker krone reaches cost of goods 3-4 "
                   "quarters later before retail prices catch up."),
    dict(rank=2, key="unemployment", feature="unemployment__d4", label="Unemployment rate, y/y change (LFS, pp)",
         targets=["gm_d4"], hs=[4, 6], horizon_class="long (4-6 quarters)", sign="-", alt="employment__g4",
         mechanism="A softening labour market pushes the basket toward low-margin consumables and campaign "
                   "items over the following year (management: mix shifts when budgets are squeezed)."),
    dict(rank=3, key="fci", feature="fci__lvl", label="Norges Bank financial conditions index (higher = tighter)",
         targets=["gm_d4"], hs=[1, 2, 3], horizon_class="short (1-3 quarters)", sign="-", alt="fci__d4",
         mechanism="Tighter credit, lending rates and housing conditions squeeze household budgets quickly "
                   "(floating-rate mortgages), shifting demand to consumables and promotions."),
    dict(rank=4, key="real_disp_income", feature="real_disp_income__g4", label="Household real disposable income, y/y %",
         targets=["ebitm_d4"], hs=[1], horizon_class="short (next quarter)", sign="+", alt=None,
         mechanism="Purchasing power lifts volumes and non-food mix; with a largely fixed store cost base the "
                   "operating leverage shows up in EBIT margin. Published ~70 days after the quarter, so the "
                   "usable reading is one quarter old."),
    dict(rank=5, key="house_prices", feature="house_prices__g4", label="House prices, y/y % (SSB)",
         targets=["rev_yoy", "lfl"], hs=[1], horizon_class="short (next quarter)", sign="+", alt=None,
         mechanism="Housing wealth and home-related purchases (home, interior, garden); confirmed on 25 years "
                   "of category sales (NACE 47.19) and adds information beyond Norges Bank's Regional Network."),
]

RUNNER_UP = [
    dict(rank=6, key="saving_ratio", feature="saving_ratio__d4", label="Household saving ratio, y/y change (pp)",
         targets=["lfl", "rev_yoy"], hs=[6], horizon_class="long (6 quarters)", sign="+", alt="real_disp_income__g4",
         mechanism="Income gains are first saved and spent later ('it will take time until higher purchasing "
                   "power translates into higher sales volumes', Q3 2024). Sign opposite to the prior written "
                   "beforehand."),
]
