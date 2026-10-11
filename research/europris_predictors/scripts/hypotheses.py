"""Pre-registered hypotheses, written from notes/drivers_and_hypotheses.md
(management statements, hedging policy, freight contracts) BEFORE looking at
their screen results. Each hypothesis fixes the feature, the target, a primary
horizon (tested with multiplicity control) and a horizon range (reported as a
profile), plus the expected sign of the coefficient.

Horizon classes requested: short = 1-4 quarters, long = 4+ quarters.
"""

HYPOTHESES = [
    # id, feature, target, primary h, range, sign, rationale
    dict(id="H1", feature="usdnok__g4", target="gm_d4", h=3, hs=[2, 3, 4], sign="-",
         why="USD ~30% of purchases, hedged up to 6 months, ~5 months of inventory: a weaker NOK reaches COGS after 2-4 quarters (centre ~3)."),
    dict(id="H1b", feature="i44__g4", target="gm_d4", h=3, hs=[2, 3, 4], sign="-",
         why="Same mechanism with the import-weighted krone (USD + EUR + CNY exposure)."),
    dict(id="H2", feature="freight_ppi__g4", target="gm_d4", h=4, hs=[3, 4, 6], sign="-",
         why="Inbound freight bought on fixed annual/2-year contracts, capitalised in inventory: spot freight reaches GM after 3-6 quarters."),
    dict(id="H2b", feature="gscpi__lvl", target="gm_d4", h=4, hs=[3, 4, 6], sign="-",
         why="Global supply-chain pressure as an alternative freight/input-cost gauge."),
    dict(id="H3", feature="policy_rate__d4", target="gm_d4", h=4, hs=[2, 4, 6], sign="-",
         why="Rate hikes squeeze floating-rate mortgage households (2-6q lag); mix shifts to low-margin consumables and campaigns."),
    dict(id="H3b", feature="policy_rate__d4", target="lfl", h=4, hs=[2, 4, 6], sign="-",
         why="Rate hikes reduce discretionary spending (offset partly by trade-down to discounters)."),
    dict(id="H4", feature="real_wage_bill__g4", target="lfl", h=2, hs=[1, 2, 4], sign="+",
         why="Management: 'interest rates, inflation and real wages remaining key for consumers' ability and willingness to spend'."),
    dict(id="H5", feature="cci__lvl", target="lfl", h=1, hs=[1, 2], sign="+",
         why="Consumer confidence drives willingness to buy higher-ticket seasonal goods (1-2q)."),
    dict(id="H5b", feature="cci__lvl", target="gm_d4", h=2, hs=[1, 2], sign="+",
         why="Confident consumers buy more non-food/seasonal (higher margin) vs consumables."),
    dict(id="H6", feature="cpi_food__g4", target="rev_yoy", h=1, hs=[1, 2], sign="+",
         why="Food/grocery inflation lifts nominal sales and trade-down to discounters (0-2q)."),
    dict(id="H6b", feature="cpi_food__g4", target="gm_d4", h=1, hs=[1, 2], sign="-",
         why="Inflation intensifies grocery price competition on consumables; mix shifts to low-margin consumables."),
    dict(id="H7", feature="seknok__g4", target="lfl", h=1, hs=[1, 2], sign="+",
         why="A weaker NOK vs SEK makes cross-border shopping in Sweden less attractive (0-1q)."),
    dict(id="H8", feature="eu_store_growth__g4", target="rev_yoy", h=2, hs=[1, 2, 4], sign="+",
         why="Net new stores (pre-approved pipeline) add to total, not like-for-like, sales."),
    dict(id="H9", feature="rti_4719_value__g4", target="lfl", h=1, hs=[1, 2], sign="+",
         why="SSB retail sales in Europris's own category (NACE 47.19), quoted by management as the market benchmark."),
    dict(id="H10", feature="cpi_electricity__g4", target="ebitm_d4", h=6, hs=[4, 6, 8], sign="-",
         why="Store/warehouse electricity hedged 12-21 months ahead: price shocks reach opex/EBIT after 4-7 quarters."),
    dict(id="H11", feature="house_prices__g4", target="lfl", h=2, hs=[1, 2, 4], sign="+",
         why="Housing-related categories and wealth effect (weak prior)."),
    dict(id="H12", feature="unemployment__d4", target="lfl", h=2, hs=[1, 2, 4], sign="?",
         why="Income channel (-) vs trade-down (+); weak prior."),
]
