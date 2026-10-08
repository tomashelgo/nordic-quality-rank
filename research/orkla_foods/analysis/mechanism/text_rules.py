"""Transparent keyword/regex rules for classifying Orkla Foods `drivers_note` texts into themes.

Each theme is a list of case-insensitive regular expressions; a quarter gets theme=1 if any pattern
matches. MANUAL_OVERRIDES (applied after the rules) record the manual review, with a reason each.
"""
import re

W = r"[\w\s/,&'\-\.]"   # filler characters allowed between keyword parts

THEMES = {
    # management cites rising / high input costs as a headwind
    'cost_up': [
        rf"(raw material|raw-material|input|factor input|purchasing|packaging|transport|energy|production|import|"
        rf"meat|dairy|sugar|glass|metal|marine|berry|mackerel|herring|seafood|fish|agri)\w*{W}{{0,45}}"
        rf"(cost|price)s?{W}{{0,30}}(up\b|rose|rising|rise|rises|higher|increase|inflation|soaring|outpaced|kept rising|still)",
        rf"(higher|rising|soaring|high|increased|increasing){W}{{0,35}}(raw material|input|purchasing|packaging|energy|transport|"
        rf"meat|dairy|mackerel|marine|berry|herring|seafood|import|production|factor input)\w*{W}{{0,30}}(cost|price)",
        r"input cost inflation", r"cost inflation", r"raised (swedish )?(purchasing|raw material|input|import|swedish raw material) costs",
        r"weak-(sek|nok) input costs", r"(meat|dairy|sugar|glass|metal)/[\w/]*inflation", r"general inflation",
        r"wage (growth|inflation)", r"raw material[\w\s&]* cost rises", r"cost (rises|increases) (only partly|triggered)",
        r"higher prices for key raw materials", r"raw material prices rose", r"raw material costs (up|higher|still higher)",
        r"factor input price increases", r"labour costs rising", r"price rises triggered by cost increases",
        r"purchasing costs", r"seafood raw material costs", r"raw material prices (kept rising|rose|up)",
    ],
    # management cites stable / falling input costs
    'cost_relief': [
        r"stable raw material costs", r"stabilis", r"stabiliz", r"lower net input costs", r"input costs more stable",
        r"(higher|costs?)[\w\s]{0,20}but declining", r"input cost rises largely offset",
    ],
    'price_up': [
        r"price increase", r"prices raised", r"price rise", r"price hike", r"price-driven", r"price-led", r"price \+",
        r"\bpricing\b", r"revenue management", r"price and volume", r"priced through", r"higher prices", r"price contribution",
        r"from prices", r"on prices", r"slightly higher prices", r"\(price \+", r"mostly price", r"price increases",
    ],
    # price increases lag cost increases (squeeze)
    'price_lag': [
        r"not sufficiently compensated", r"not yet offset", r"\blag", r"outpaced", r"only partly offset", r"partly priced through",
        r"took effect late", r"price rises from 1 july", r"not yet", r"lagging",
    ],
    # costs compensated / offset by pricing
    'price_offset': [
        r"offset by price", r"compensated", r"largely offset", r"offset with lag", r"prices offset", r"price increases offset",
        r"offset by prices", r"compensated weak", r"offset weak", r"price increases/portfolio mgmt offset",
        r"offset by price increases", r"raw material costs[\w\s]*offset",
    ],
    'fx_weak': [
        r"weak(er)?[\s-](sek|nok|currenc|fx|nok/sek)", r"sek[\s~\d%]*weaker", r"weak sek", r"weak nok",
    ],
    'fx_strong': [r"strong(er)? nok", r"strong(er)? sek"],
    'fx_translation': [r"translation", r"\bfx\b", r"currenc"],
    'volume_weak': [
        r"volume decline", r"weak(er)? volume", r"volumes? (down|declin|hit|loss)", r"volume loss", r"weak grocery volumes",
        r"destocking", r"slower volume", r"(reduced|weak|lower) (buying|purchasing) power", r"volume/mix -", r"lower activity",
        r"weak sales", r"sales down", r"underlying sales -", r"share losses", r"market shares? (lower|down|reduced|somewhat|slightly down)",
        r"share (down|somewhat lower)", r"weak (june|december)", r"volume-driven: customer destocking", r"less negative volumes",
        r"volume decline in", r"decline in (norway|scandinavia)", r"lower market shares", r"weak nordic sales", r"weaker sales",
        r"volumes down", r"volume decline", r"weak .*volume", r"organic -", r"underlying -",
    ],
    'volume_strong': [
        r"volume growth", r"volume/mix \+", r"volume/mix-driven", r"volumes up", r"grocery growth", r"grocery up",
        r"stockpiling", r"share gains", r"reopening", r"recovered", r"from volumes", r"volume growth in",
        r"price and volume", r"broad-based organic growth", r"positive\)", r"slight volume growth", r"\(no positive",
    ],
    'easter_timing': [r"easter", r"selling days", r"sales days", r"timing", r"phasing", r"pulled forward", r"shifted",
                      r"pre-xmas", r"pre-buying"],
    'campaign': [r"campaign"],
    'ma_distribution': [
        r"acqui", r"consolidat", r"divest", r"\bsold\b", r"structural", r"distribution", r"pepsico", r"tropicana",
        r"rieber", r"ham[eé]", r"dilut", r"low-margin (exit|categories)", r"contract production", r"\bstructure\b",
        r"inclusion", r"bakers sale", r"non-core",
    ],
    'energy': [r"energy", r"electricity"],
    'covid': [r"covid", r"stockpiling", r"lockdown", r"reopening"],
    'out_of_home': [r"out-of-home", r"food service", r"convenience"],
    'cost_programme': [
        r"cost cut", r"cost reduction", r"cost improvement", r"cost programme", r"synerg", r"saving", r"lyftet",
        r"improvement programme", r"efficiency", r"fixed-cost", r"restructuring", r"cost control", r"lower sg&a",
        r"fixed costs", r"cost focus", r"man-years", r"cost base", r"cost goal", r"lower fixed production costs",
        r"reorganisation", r"cost programmes", r"cost-reduction",
    ],
    'buying_power': [r"buying power", r"purchasing power", r"discounter", r"private label", r"low-price", r"hard-discount",
                     r"shelf prices"],
    'one_off': [r"recall", r"\berp\b", r"strike", r"delivery (problems|issues)", r"start-up", r"write-down", r"one-off",
                r"property gain", r"periodisation", r"factory project", r"fmd/bse", r"accruals"],
    'advertising': [r"advertising", r"\ba&p\b", r"marketing"],
    'launches': [r"launch", r"innovation"],
    'mix': [r"\bmix\b", r"category profitability", r"contribution ratio"],
}

# Manual review (period -> {theme: value, ...}, reason). Applied after the regex rules.
MANUAL_OVERRIDES = {
    '2001Q2': ({'cost_up': 1, 'fx_weak': 1, 'price_up': 1}, 'weak SEK raised Swedish raw-material costs; raw material prices up; prices raised in Q2'),
    '2001Q3': ({'cost_up': 1, 'fx_weak': 1, 'price_offset': 1}, 'SEK weaker hit import costs; fish raw material prices up, partly priced through'),
    '2001Q4': ({'cost_up': 0, 'price_offset': 1, 'price_up': 1}, 'early-2001 raw material rises largely offset by price increases (backward-looking: no current pressure)'),
    '2002Q2': ({'cost_up': 1, 'fx_strong': 1, 'volume_weak': 1}, 'seafood raw material costs drove prices above substitutes, volumes fell; strong NOK'),
    '2002Q3': ({'cost_up': 1, 'fx_strong': 1, 'volume_weak': 1}, 'seafood prices up on raw materials, demand down; stronger NOK'),
    '2002Q4': ({'fx_strong': 1}, 'strong NOK translation drag'),
    '2004Q2': ({'cost_up': 1, 'one_off': 1}, 'EU enlargement raised CEE purchasing costs; transport strike'),
    '2006Q1': ({'cost_up': 1, 'buying_power': 1}, 'higher herring prices; falling Swedish grocery prices'),
    '2006Q2': ({'cost_up': 1}, 'OFI up despite higher prices for key raw materials'),
    '2006Q3': ({'cost_up': 1}, 'Nordic raw material prices rose, some significantly'),
    '2006Q4': ({'cost_up': 1, 'energy': 1, 'price_lag': 1}, 'raw material & energy cost rises only partly offset by price rises'),
    '2007Q2': ({'cost_up': 1, 'price_lag': 1}, 'factor input price increases not sufficiently compensated (price rises from 1 July)'),
    '2007Q3': ({'cost_up': 1, 'price_lag': 1}, 'raw material prices kept rising; finished-goods price rises lag (contracts)'),
    '2007Q4': ({'cost_up': 1, 'price_lag': 1}, 'raw material prices rose all quarter; price increases only late Q4/early 2008'),
    '2008Q1': ({'cost_up': 1, 'price_up': 1}, 'growing effect of price increases; raw material & labour costs rising'),
    '2008Q2': ({'price_up': 1}, 'price increases implemented'),
    '2008Q3': ({'cost_up': 1, 'price_up': 1}, 'price increases implemented; Norwegian agri raw material prices up'),
    '2008Q4': ({'cost_up': 1, 'fx_weak': 1, 'price_up': 1, 'volume_weak': 1}, 'price rises triggered by cost increases; weak NOK/SEK raised purchasing costs; volume decline'),
    '2009Q1': ({'cost_up': 1, 'fx_weak': 1, 'volume_weak': 1}, 'weak SEK raised Swedish purchasing costs; weak volume'),
    '2009Q2': ({'cost_up': 1, 'fx_weak': 1}, 'weak SEK raised Swedish purchasing costs'),
    '2009Q4': ({'price_up': 0, 'fx_translation': 1}, '"much lower price contribution" = price growth fading, not a price increase'),
    '2010Q3': ({'cost_up': 1}, 'raw material prices slightly higher y/y'),
    '2010Q4': ({'cost_up': 1}, 'raw material prices rising'),
    '2011Q1': ({'cost_up': 1, 'price_offset': 1, 'price_lag': 1}, 'raw material price rises offset with lag'),
    '2011Q2': ({'cost_up': 1, 'price_lag': 1}, 'raw material costs not yet offset by price increases'),
    '2011Q3': ({'cost_up': 1, 'price_offset': 1, 'price_up': 1}, 'BCG-level price increases compensated raw material costs'),
    '2012Q1': ({'cost_up': 1, 'price_offset': 1}, 'raw material costs up but offset by prices'),
    '2012Q2': ({'cost_up': 1, 'cost_relief': 1}, 'raw material costs higher but declining'),
    '2012Q3': ({'cost_up': 1, 'price_offset': 1}, 'raw material costs up y/y via carry-over, offset by price increases'),
    '2012Q4': ({'cost_up': 1, 'price_offset': 1}, 'raw material costs still higher but offset by price increases'),
    '2013Q1': ({'cost_relief': 1, 'cost_up': 0}, 'stable raw material costs'),
    '2014Q3': ({'fx_weak': 1, 'cost_up': 1}, 'weaker SEK/FX costs'),
    '2015Q3': ({'cost_up': 1, 'fx_weak': 1, 'volume_weak': 0}, 'weaker NOK raising purchasing costs; "weak Q3-14" is the base, not weak volume (regex false positive)'),
    '2015Q4': ({'cost_up': 1, 'fx_weak': 1}, 'weaker NOK and higher raw material prices raised costs'),
    '2016Q1': ({'cost_up': 1, 'fx_weak': 1}, 'weak-NOK input costs'),
    '2016Q2': ({'cost_up': 1, 'fx_weak': 1}, 'higher raw material costs (weak NOK)'),
    '2016Q4': ({'cost_up': 1, 'fx_translation': 1}, 'higher raw material prices, negative FX'),
    '2017Q1': ({'cost_up': 1}, 'higher input costs'),
    '2017Q2': ({'cost_up': 1}, 'higher raw material costs (SE, CZ)'),
    '2017Q3': ({'cost_up': 1}, 'despite high raw material costs'),
    '2017Q4': ({'cost_up': 1, 'price_up': 1, 'price_offset': 1}, 'mainly price increases offsetting higher raw material costs'),
    '2018Q1': ({'cost_up': 1, 'fx_weak': 1, 'price_up': 1}, 'weaker SEK raised input costs; price increases'),
    '2018Q2': ({'cost_up': 1, 'fx_weak': 1}, 'weak-SEK input costs'),
    '2018Q3': ({'cost_up': 1, 'fx_weak': 1}, 'weak SEK raised raw material costs in Sweden'),
    '2018Q4': ({'cost_up': 1, 'fx_weak': 1}, 'weak-SEK input costs'),
    '2019Q1': ({'cost_up': 1, 'fx_weak': 1, 'price_offset': 1, 'price_up': 1}, 'price increases compensated weak SEK and higher raw material prices'),
    '2019Q2': ({'cost_up': 1, 'fx_weak': 1, 'price_offset': 1, 'price_up': 1}, 'price increases offset weak SEK and higher raw material costs'),
    '2019Q3': ({'cost_up': 1, 'fx_weak': 1, 'price_offset': 1, 'price_up': 1}, 'prices offset weak SEK/NOK and raw materials'),
    '2019Q4': ({'cost_up': 1, 'fx_weak': 1, 'price_offset': 1, 'price_up': 1}, 'price increases offset weak SEK/NOK and higher raw material prices'),
    '2020Q1': ({'cost_up': 1, 'fx_weak': 1, 'price_offset': 1, 'price_up': 1}, 'weaker NOK/SEK and higher raw material prices largely offset by price increases'),
    '2020Q2': ({'cost_up': 1, 'fx_weak': 1}, 'weak-NOK input costs'),
    '2020Q3': ({'cost_up': 1}, 'higher input costs'),
    '2020Q4': ({'cost_up': 1, 'price_up': 1, 'price_lag': 1}, 'lagged price increases for earlier cost rises; raw materials still rising'),
    '2021Q1': ({'cost_up': 1, 'price_offset': 1, 'price_up': 1}, 'input cost rises offset by price increases and FX'),
    '2021Q2': ({'cost_up': 1, 'price_offset': 1, 'cost_programme': 0}, 'input cost inflation offset by pricing so far; "lapping 2020 Covid cost savings" is a headwind, not a cost programme'),
    '2021Q3': ({'cost_up': 1, 'energy': 1}, 'higher raw material, packaging, transport and energy costs'),
    '2021Q4': ({'cost_up': 1, 'energy': 1, 'price_lag': 1}, 'higher purchasing, transport and energy costs with price increases lagging'),
    '2022Q1': ({'cost_up': 1, 'energy': 1, 'price_lag': 1}, 'raw material, packaging, energy, transport costs rose; price hikes lag'),
    '2022Q2': ({'cost_up': 1, 'energy': 1, 'price_lag': 1, 'price_up': 1}, 'costs and wage growth outpaced substantial price increases'),
    '2022Q3': ({'cost_up': 1, 'energy': 1, 'price_up': 1, 'volume_weak': 1}, 'soaring raw material/packaging/energy costs; price-driven growth; weak volumes'),
    '2022Q4': ({'cost_up': 1, 'energy': 1, 'price_up': 1, 'volume_weak': 1}, 'raw material/energy cost and wage inflation; price-led; volumes down'),
    '2023Q1': ({'cost_up': 1, 'fx_weak': 1, 'price_up': 1, 'volume_weak': 1}, 'meat/dairy/sugar/glass/metal inflation; weak NOK/SEK; price-driven; weak volumes'),
    '2023Q2': ({'cost_up': 1, 'fx_weak': 1, 'price_up': 1, 'volume_weak': 1}, 'high input costs and weak NOK/SEK; price +16.3%, volume/mix -9.3%'),
    '2023Q3': ({'cost_up': 1, 'cost_relief': 1, 'fx_weak': 1, 'price_up': 1, 'volume_weak': 1}, 'raw material prices stabilising but high; weak NOK/SEK'),
    '2023Q4': ({'cost_up': 0, 'fx_weak': 1, 'price_up': 1, 'volume_weak': 1}, 'price-led, less negative volumes; weak FX; no current cost-rise statement'),
    '2024Q1': ({'cost_up': 0, 'cost_relief': 1, 'fx_weak': 1, 'price_up': 1}, 'input costs stabilising; weak currencies'),
    '2024Q2': ({'cost_up': 0, 'cost_relief': 1, 'volume_weak': 1}, 'lower net input costs; volumes down'),
    '2024Q3': ({'cost_up': 0, 'cost_relief': 1, 'price_up': 1, 'volume_strong': 1}, 'input costs stabilising; price and volume growth'),
    '2025Q1': ({'cost_up': 0, 'cost_relief': 1, 'volume_weak': 1}, 'input costs more stable; volume-driven decline'),
    '2025Q2': ({'cost_up': 1, 'price_offset': 1, 'cost_relief': 0}, 'input cost rises largely offset'),
    '2025Q3': ({'cost_up': 1, 'volume_weak': 1}, 'meat/dairy/marine/berry costs up; volumes hit'),
    '2025Q4': ({'cost_up': 1, 'price_lag': 1}, 'rising meat/marine/berry costs only partly offset'),
    '2026Q1': ({'cost_up': 1, 'volume_strong': 1}, 'high mackerel/meat/dairy costs; volume/mix +2.3%'),
    '2026Q2': ({'cost_up': 1, 'fx_strong': 1, 'volume_weak': 1}, 'high mackerel/meat/dairy costs; strong NOK; volume/mix -2.3%'),
}


def classify(text):
    t = (text or '').lower()
    out = {}
    for th, pats in THEMES.items():
        out[th] = int(any(re.search(p, t) for p in pats))
    return out
