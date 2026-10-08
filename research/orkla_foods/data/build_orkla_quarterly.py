#!/usr/bin/env python3
"""
build_orkla_quarterly.py - build the definitive quarterly Orkla Foods dataset.

Inputs (data/orkla_raw/):
    era_E1_verified.csv ... era_E6_verified.csv   verified quarterly extractions (2001Q1-2026Q2 reports)
    restatements.csv                              separately published restated histories
    segment_history.json                          pre-2001 annual figures
Outputs (data/):
    orkla_foods_quarterly.csv        headline "as originally reported" series, 2000Q1..2026Q2
    orkla_foods_alt_definitions.csv  restated / alternative definitions (never mixed into the headline)
    orkla_foods_annual.csv           annual figures 1992-2025 by definition
    orkla_foods_methodology.md       only the auto-generated block between the AUTO markers is refreshed

Run from anywhere:  python3 -I build_orkla_quarterly.py

Every manual override or estimate is an explicit dictionary below, with a comment citing its source.
All amounts are NOK million.
"""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "orkla_raw")
OUT_Q = os.path.join(HERE, "orkla_foods_quarterly.csv")
OUT_ALT = os.path.join(HERE, "orkla_foods_alt_definitions.csv")
OUT_A = os.path.join(HERE, "orkla_foods_annual.csv")
OUT_MD = os.path.join(HERE, "orkla_foods_methodology.md")

FIRST_YEAR, LAST_YEAR, LAST_Q = 2000, 2026, 2

# ----------------------------------------------------------------------------------------------
# Definitions (see orkla_raw/segment_history.md section 1; E and the 2025 rename "F" share one id)
# ----------------------------------------------------------------------------------------------
DEF_INFO = {
    "PRE": "Orkla Foods business area 1992-1999 (NGAAP; annual only; Procordia/Abba acquired 1995)",
    "A": "Orkla Foods (2000-2007 def.): Nordic food incl. Bakers + Orkla Food Ingredients + Orkla Foods International "
         "(CEE; SladCo RU 2005-, Krupskaya 2006Q3-, MTR India 2007Q2-)",
    "A_NORDIC": "Orkla Foods Nordic, 2005-07 sub-segment of A (incl. Bakers, Panda; excl. Baltics)",
    "A_OFI": "Orkla Food Ingredients, sub-segment of A",
    "A_INTL": "Orkla Foods International, sub-segment of A (CEE, Baltics, Russia 2005-, MTR India 2007Q2-)",
    "A_ELIM": "Eliminations within Orkla Foods (A); revenue only",
    "B": "Orkla Foods Nordic (2008-12 def.): Nordic + Baltic food incl. Bakers (to Jan-2012), Panda, Kalev (2010Q2-)",
    "C": "Orkla Foods (2013-14 def.): Nordic + Baltic food excl. Panda/Kalev confectionery; Rieber Nordic from 1 May 2013",
    "D": "Orkla Foods (2015-22 def.): C + MTR India, Vitana CZ, Felix Austria; Hame 2016Q2-, Eastern India 2021Q2-",
    "D_DERIVED": "Orkla Foods (2015-22 def.) DERIVED after 2022Q2 as Orkla Foods Europe + Orkla India (both printed)",
    "E": "Orkla Foods Europe (2022Q3-2024Q3), renamed Orkla Foods (Q4 2024 report / Feb 2025): D excl. Orkla India",
    "IND": "Orkla India (MTR + Eastern Condiments); separate segment from 2022Q3, comparatives from 2021Q3",
}


def pstr(y, q):
    return f"{y}Q{q}"


def pparse(p):
    return int(p[:4]), int(p[5])


def shift_years(p, n):
    y, q = pparse(p)
    return pstr(y + n, q)


def all_periods():
    out = []
    for y in range(FIRST_YEAR, LAST_YEAR + 1):
        for q in range(1, 5):
            if (y, q) <= (LAST_YEAR, LAST_Q):
                out.append(pstr(y, q))
    return out


def headline_def(p):
    """Food-segment definition in force when quarter p was first reported."""
    y, q = pparse(p)
    if y <= 2007:
        return "A"
    if y <= 2012:
        return "B"
    if y == 2013 or (y == 2014 and q <= 3):
        return "C"
    if (y, q) <= (2022, 2):
        return "D"
    return "E"


def assign_def(label, report_period):
    """Map a raw row (printed label + report it was printed in) to a definition id."""
    ry, rq = pparse(report_period)
    if label == "Orkla Foods":
        if ry <= 2007:
            return "A"
        if ry == 2013 or (ry == 2014 and rq <= 3):
            return "C"
        if (ry, rq) >= (2014, 4) and (ry, rq) <= (2022, 2):
            return "D"
        if (ry, rq) >= (2024, 4):
            return "E"  # renamed Orkla Foods Europe; scope unchanged (Q4 2024 report footnote)
    if label == "Orkla Foods Europe":
        return "E"
    if label == "Orkla Foods Nordic":
        return "A_NORDIC" if ry <= 2007 else ("B" if ry <= 2012 else None)
    if label == "Orkla India":
        return "IND"
    if ry <= 2007:
        if label == "Orkla Foods International":
            return "A_INTL"
        if label in ("Orkla Food Ingredients", "Orkla Foods Ingredients"):
            return "A_OFI"
        if label == "Eliminations Orkla Foods":
            return "A_ELIM"
    return None  # context rows (BCG, Orkla Brands, OFI after 2007, ...)


def metric_class(m):
    m = str(m)
    if re.search(r"EBIT \(adj", m):
        return "EBIT (adj.)"
    if "goodwill" in m.lower():
        return "NGAAP EBITA (before goodwill amortisation)"
    if m.strip() == "Operating profit":
        return "NGAAP operating profit after goodwill amortisation"
    return "EBITA (IFRS)"


def easter_date(y):
    """Anonymous Gregorian (Meeus/Jones/Butcher) algorithm."""
    a = y % 19
    b, c = divmod(y, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = ((h + l_ - 7 * m + 114) % 31) + 1
    return pd.Timestamp(year=y, month=month, day=day)


def easter_quarter(y):
    return (easter_date(y).month - 1) // 3 + 1


def nz(x):
    return x is not None and not (isinstance(x, float) and np.isnan(x)) and not pd.isna(x)


# ----------------------------------------------------------------------------------------------
# MANUAL INPUTS (explicit, with sources)
# ----------------------------------------------------------------------------------------------

# Calendar-adjusted organic growth (og_easter_adjusted = True). Sources: og_metric/verify notes.
CALENDAR_ADJ = {
    "2010Q1": "Easter-adjusted (Q1 2010 report p.5; only basis given)",
    "2011Q1": "Easter-adjusted (Q1 2011 report p.5)",
    "2011Q2": "Easter-adjusted (Q2 2011 report p.5; H1 -0.5)",
    "2014Q1": "Easter- and selling-day-adjusted (Q1 2014 report p.5; pres p.19 'adj. organic growth')",
    "2014Q2": "Easter- and selling-day-adjusted (Q2 2014 pres p.5/p.18)",
    "2014Q3": "selling-day-adjusted (Q3 2014 pres p.4/p.19 footnote; verify-E4 #1)",
    "2014Q4": "selling-day-adjusted (Q4 2014 pres p.4/p.18 footnote; verify-E4 #1)",
}

# Quality overrides for stated values that are doubtful per the verification logs (quality B).
OG_QUALITY_OVERRIDES = {
    "2001Q1": ("B", "'for continuing business', FX adjustment not stated; probably NOT FX-adjusted "
                    "(verify-E1 D4: FX-adjusted Q1 likely ~+7-8%)"),
    "2008Q1": ("B", "'around 6%' adj. for acquisitions/disposals, no explicit FX exclusion (verify-E2)"),
    "2013Q3": ("B", "Rieber treatment not stated (verify-E3). Printed FY2013 -4.2 does not reconcile exactly with the "
                    "quarters (Q1-Q4 weighted by 2012 C revenue = -3.5; -3.7 with Rieber pro forma in the base), "
                    "and the Q3-13 'YTD -3.3' slide does not reconcile either, so the basis is uncertain (splice QA)"),
    "2013Q4": ("B", "Rieber treatment not stated (verify-E3). Printed FY2013 -4.2 does not reconcile exactly with the "
                    "quarters (Q1-Q4 weighted by 2012 C revenue = -3.5; -3.7 with Rieber pro forma in the base), "
                    "so the basis is uncertain (splice QA)"),
}

# 2005Q1-Q3 carry one 9M average, not a quarterly YTD difference (label only; quality C via og_source=derived)
NINE_MONTH_AVG = ("2005Q1", "2005Q2", "2005Q3")

# Caveat notes attached to og_est where a (derived or doubtful) value IS present.
OG_PRESENT_NOTES = {
    "2001Q2": "Derived from H1 +1.6 (FX-adj.) minus Q1 +5 (probably not FX-adj.); basis-consistent "
              "estimate ~-3.4 (range -4.5 to -1.4); treat -1.4 as an upper bound (verify-E1 D4).",
    "2001Q3": "Derived from 9M 'just under 2%' (1.9) and H1 1.6; range +2.2 to +2.6 (verify-E1 D5).",
    "2001Q4": "Derived from FY 'approximately 2.5%' and 9M ~1.9; range +3.4 to +5.1 (verify-E1 D5).",
    "2002Q1": "'Approximately 4%' with currency rates unchanged (Q1 2002 report p.2); whole-percent rounding.",
    "2002Q2": "'Approximately 1%' measured in local currency (Q2 2002 report p.2); whole-percent rounding.",
    "2002Q3": "Derived from 9M 2% minus Q1 ~4% and Q2 ~1%; +/-0.5pp on 9M moves Q3 +/-1.5pp (verify-E1 D5).",
    "2004Q2": "Derived from H1 1% minus Q1 4%; range -2.7 to -0.8 (verify-E1 D5).",
    "2004Q3": "Derived from 9M 'on a par' minus H1 1%; range -4.2 to +0.5 (verify-E1 D5).",
    "2005Q1": "9M-2005 AVERAGE (-2.4) implied by FY -2% and Q4 -1% (Q4 2005 report p.3); same value in Q1-Q3; "
              "range -3.3 to -1.5; Q1 text 'slightly lower' (verify-E1 D3).",
    "2005Q2": "9M-2005 AVERAGE implied by FY -2% and Q4 -1%; quarterly split unknown (verify-E1 D3).",
    "2005Q3": "9M-2005 AVERAGE implied by FY -2% and Q4 -1%; quarterly split unknown (verify-E1 D3).",
    "2008Q2": "Derived from H1 5% and Q1 ~6% with 2007 restated weights: (5 x 4,629 - 6 x 2,207) / 2,422 = 4.09; "
              "the verified extraction keeps the rounded 'about 4'; range 2.7 to 5.5 (verify-E2 #2).",
    "2009Q1": "'Decline of about 2%' (Q1 2009 report p.5). The 'doubtful' item in verify-E2 #3 concerns the parent "
              "Orkla Brands figure (0), not this Orkla Foods Nordic value.",
    "2012Q1": "'About 5%', unadjusted; about half due to Easter timing (Q1 2012 report p.5).",
    "2012Q3": "+4.0 'boosted slightly by timing effects reversing in Q4' (Q3 2012 report p.5).",
    "2013Q2": "Incl. Rieber pro forma (-4.2); ex Rieber -2.3 (Q2 2013 pres p.24).",
}

# Inputs for the two 2012 organic-growth estimates (Orkla Foods Nordic, definition B).
EST_2012 = {
    "q1": 5.0,   # Q1 2012 report p.5: underlying growth 'about 5%'
    "h1": 0.8,   # Q2 2012 presentation p.11: H1-12 +0.8 (report p.4 rounds to +1%)
    "q3": 4.0,   # Q3 2012 report p.5 / presentation p.25: +4.0
    "fy": 1.0,   # Q4 2012 presentation p.23 bar chart: FY2012 +1% (+3% adj. for lost contract production)
    # weights = 2011 revenue as printed in the 2012 reports (B definition, incl. Bakers)
}

# For 2008 (first B quarter) the prior-year OG is taken from the 2005-07 Orkla Foods Nordic sub-segment
# (closest to B: B = that sub-segment + Baltic food cos), not from the A total.
OG_PY_FROM_ALT = {"2008Q1": "A_NORDIC", "2008Q2": "A_NORDIC", "2008Q3": "A_NORDIC", "2008Q4": "A_NORDIC"}

# Price / volume-mix for 2022Q2: headline 2022Q2 is definition D (no split printed); the only split is the
# Orkla Foods Europe (E) comparative printed in the Q2 2023 report (7.4 / 3.0; sums to E organic 10.4, not
# to the headline D organic 11.6). Used because the specification asks for 2022Q2; flagged in kpi_source.
PRICE_VOL_CROSS_DEF = {"2022Q2": "E"}

# Restated FY2006 for Orkla Foods Nordic on the 2008 definition (Annual Report 2007; verify-E2 #4).
ANNUAL_EXTRA = [
    dict(year=2006, def_id="B", revenue_nokm=9483, ebit_nokm=1074, ebit_metric="EBITA (IFRS)",
         source="Annual Report 2007 (FY2006 restated to 2008 definition incl. Baltics); verify-E2 item 4"),
]

# Reported full-year organic growth (annual file). Anything else is computed (weighted quarters).
FY_OG_REPORTED = {
    ("A", 2001): (2.5, "Q4 2001 report p.2: 'approximately 2.5%' (continuing business, FX-adj.)"),
    ("A", 2002): (2.0, "Q4 2002 report p.2 / AR2002"),
    ("A", 2003): (1.0, "AR2003 / Q4 2003 report"),
    ("A", 2004): (0.0, "Q4 2004 report p.2 / AR2004: 'on a par'"),
    ("A", 2005): (-2.0, "Q4 2005 report p.3"),
    ("A", 2006): (0.0, "Q4 2006 report: FY underlying sales 'on a par'"),
    ("A", 2007): (-1.1, "Q4 2007 report / AR2007"),
    ("B", 2008): (4.0, "Q4 2012 presentation p.23 bar chart (bars matched to years by order; approximate)"),
    ("B", 2009): (-1.0, "Q4 2012 presentation p.23 bar chart (approximate)"),
    ("B", 2010): (-4.0, "Q4 2012 presentation p.23 bar chart (approximate)"),
    ("B", 2011): (-1.0, "Q4 2012 presentation p.23 bar chart (approximate)"),
    ("B", 2012): (1.0, "Q4 2012 presentation p.23 (+3% adj. for lost Procordia contract production)"),
    ("C", 2013): (-4.2, "Q4 2013 presentation p.21"),
    ("D", 2014): (-1.1, "Q4 2014 presentation p.18 (selling-day adjusted)"),
    ("D", 2015): (3.9, "Q4 2015 presentation p.19"),
    ("D", 2016): (2.3, "Q4 2016 presentation p.14; Q4 2017 report table"),
    ("D", 2017): (1.4, "Q4 2017 report table"),
    ("D", 2018): (1.5, "Q4 2018 report (verify-E5 section 5)"),
    ("D", 2019): (1.8, "Q4 2019 report; Feb-2020 restated segment file"),
    ("D", 2020): (3.7, "Q4 2020 report (verify-E5 section 5)"),
    ("D", 2021): (1.8, "Q4 2021 report (verify-E5 section 5)"),
    ("E", 2021): (1.4, "Q4 2022 report Note 2 / APM (restatements.csv)"),
    ("E", 2022): (7.2, "Q4 2022 report (restatements.csv)"),
}

# Printed full-year totals used to check that four quarters sum to the annual figure.
PRINTED_FY = {
    ("A", 2000, "NGAAP operating profit after goodwill amortisation"): (11039, 787),
    ("A", 2001, "NGAAP operating profit after goodwill amortisation"): (11133, 791),
    ("A", 2001, "NGAAP EBITA (before goodwill amortisation)"): (11133, 952),   # restated in 2002 reports
    ("A", 2004, "EBITA (IFRS)"): (12711, 1164),                                # restated in 2005 reports
    ("A", 2002, "NGAAP EBITA (before goodwill amortisation)"): (11062, 902),
    ("A", 2003, "NGAAP EBITA (before goodwill amortisation)"): (11913, 1030),
    ("A", 2004, "NGAAP EBITA (before goodwill amortisation)"): (12711, 1178),
    ("A", 2005, "EBITA (IFRS)"): (13650, 1213),
    ("A", 2006, "EBITA (IFRS)"): (14266, 1278),
    ("A", 2007, "EBITA (IFRS)"): (14725, 1000),
    ("A_NORDIC", 2006, "EBITA (IFRS)"): (9283, 1057),
    ("A_NORDIC", 2007, "EBITA (IFRS)"): (9291, 873),
    ("B", 2007, "EBITA (IFRS)"): (9548, 893),
    ("B", 2008, "EBITA (IFRS)"): (9913, 1050),
    ("B", 2009, "EBITA (IFRS)"): (9754, 1088),
    ("B", 2010, "EBITA (IFRS)"): (9438, 1115),
    ("B", 2011, "EBITA (IFRS)"): (9496, 1082),
    ("B", 2012, "EBITA (IFRS)"): (8569, 1161),
    ("C", 2012, "EBITA (IFRS)"): (7972, 1144),
    ("C", 2013, "EBITA (IFRS)"): (9797, 1275),
    ("D", 2013, "EBITA (IFRS)"): (11110, 1312),
    ("D", 2014, "EBITA (IFRS)"): (12232, 1495),
    ("D", 2014, "EBIT (adj.)"): (12232, 1488),
    ("D", 2015, "EBIT (adj.)"): (13250, 1701),
    ("D", 2016, "EBIT (adj.)"): (15476, 1968),
    ("D", 2017, "EBIT (adj.)"): (16126, 2055),
    ("D", 2018, "EBIT (adj.)"): (16000, 2048),
    ("D", 2019, "EBIT (adj.)"): (16776, 2276),
    ("D", 2020, "EBIT (adj.)"): (18301, 2641),
    ("D", 2021, "EBIT (adj.)"): (18760, 2471),
    ("E", 2022, "EBIT (adj.)"): (17820, 1973),
    ("E", 2023, "EBIT (adj.)"): (20319, 2259),
    ("E", 2024, "EBIT (adj.)"): (20594, 2532),
    ("E", 2025, "EBIT (adj.)"): (20864, 2621),
    ("IND", 2022, "EBIT (adj.)"): (2542, 303),
    ("IND", 2023, "EBIT (adj.)"): (2947, 386),
    ("IND", 2024, "EBIT (adj.)"): (3106, 463),
    ("IND", 2025, "EBIT (adj.)"): (2981, 486),
}

# Structural / definition / distribution-agreement events (segment_history.md, ma_events.csv, era notes).
EVENT_NOTES = {
    "2000Q1": "2000 quarters = comparatives printed in the 2001 reports (Orkla reported four-monthly until 2000)",
    "2000Q2": "2000 quarters = comparatives printed in the 2001 reports",
    "2000Q3": "2000 quarters = comparatives in 2001 reports; Superfish (PL, 51%, ~NOK 650m/yr) acquired Sep-2000",
    "2000Q4": "2000 quarters = comparatives printed in the 2001 reports",
    "2001Q1": "First quarterly report; 2001 EBIT is after goodwill amortisation (2002 reports restate 2001 to EBITA, ~+40m/qtr)",
    "2002Q1": "Metric: NGAAP EBITA (before goodwill amortisation) from 2002; comparatives restated",
    "2002Q2": "Topway Foods (Orkla Foods Romania) acquired 31 May 2002",
    "2003Q1": "Credin group (DK/PL/PT, ~NOK 330m/yr) consolidated from 1 Jan 2003; Superfish moved to Orkla Foods International (internal)",
    "2004Q1": "Bakehuset Norge (~NOK 517m/yr) consolidated Jan-2004 (acquisition costs -35m below EBITA)",
    "2004Q3": "Spilva (LV) consolidated from Jul-2004",
    "2005Q1": "IFRS adopted (2004 comparatives restated); SladCo (RU, ~NOK 1,075m/yr) consolidated 1 Jan 2005; Hallofisk, Ardealul, Baechs acquired",
    "2005Q2": "Panda (FI confectionery, ~NOK 370m/yr) acquired May-2005",
    "2005Q4": "Sub-segments Nordic / Ingredients / International first reported",
    "2006Q1": "Martin Nordby (Bakers, ~NOK 126m/yr) acquired Jan-2006",
    "2006Q2": "Royal Brinkers (RO) from 1 Jun 2006",
    "2006Q3": "Krupskaya (RU, ~NOK 330m/yr) consolidated from 1 Jul 2006",
    "2007Q2": "MTR Foods (India, ~NOK 230m/yr) consolidated from 1 Apr 2007 (inside Orkla Foods International); Pastella (DK) Apr-2007",
    "2007Q3": "Bakehuset Kafe sold Aug-2007; NOK -324m charge below EBITA (Romania goodwill, Superfish sale, Poland)",
    "2007Q4": "Superfish (PL, ~NOK 250m/yr) sold Nov-2007; last quarter of definition A",
    "2008Q1": "DEFINITION BREAK A->B: Orkla Foods merged into Orkla Brands (18 Feb 2008); headline = Orkla Foods Nordic incl. Baltic food cos; y/y vs 2007 restated to the 2008 definition",
    "2010Q2": "Kalev (EE chocolate, ~NOK 225m/yr) acquired May-2010",
    "2010Q4": "Bakers goodwill write-down NOK -276m below EBITA; Hovenaset closure write-down inside EBITA",
    "2011Q2": "Dagens AS (Stabburet) from 9 Jun 2011",
    "2012Q1": "Bakers (~NOK 1,200m/yr) deconsolidated 1 Feb 2012; 2011 comparatives NOT restated (reported y/y revenue -6 to -14% in 2012)",
    "2012Q2": "Bakers out (comparative still incl. Bakers)",
    "2012Q3": "Bakers out (comparative incl. Bakers); Jokk brand acquired; EBITA incl. NOK 11m property gain (Abba)",
    "2012Q4": "Bakers out (comparative incl. Bakers); fewer selling days",
    "2013Q1": "DEFINITION BREAK B->C: Panda/Kalev confectionery moved out; 2012 comparatives restated incl. IAS 19R (raises EBITA) and IFRS 11; restated 2012 still incl. Bakers to Jan-2012",
    "2013Q2": "Rieber & Son Nordic food (~NOK 2.7bn/yr est.) consolidated 1 May 2013 (OG incl. Rieber pro forma); Procordia + Abba merged",
    "2013Q3": "Rieber in current quarter, not in comparative",
    "2013Q4": "Rieber in current quarter, not in comparative",
    "2014Q1": "Rieber in current quarter, not in comparative",
    "2014Q2": "Rieber anniversary 1 May 2014",
    "2014Q3": "Delecta (PL) sold - it sat in Orkla International, i.e. outside headline C (inside restated D)",
    "2014Q4": "DEFINITION BREAK C->D: MTR India, Vitana CZ, Felix Austria added (comparative 2013Q4 restated); Krogarklass from 1 Oct 2014; OG selling-day adjusted",
    "2015Q1": "METRIC EBITA->EBIT (adj.) (2014 comparatives restated, ~-7m/yr); Tropicana distribution (SE/DK) from 1 Jan 2015 counted as ORGANIC; Delecta in comparative",
    "2015Q2": "Anamma (SE) acquired; Tropicana distribution counted as organic",
    "2015Q3": "Bioquelle (AT) acquired; Tropicana distribution counted as organic; Delecta in comparative until sale",
    "2015Q4": "NP Foods drinks (Gutta) moved into Orkla Foods Latvija 1 Oct 2015 (not restated); Tropicana counted as organic",
    "2016Q1": "O. Kavli DK (~NOK 210m/yr) from 1 Mar 2016; expanded PepsiCo distribution (Tropicana NO, Quaker Nordics) counted as ORGANIC",
    "2016Q2": "Hame CZ/SK (~NOK 1,700m/yr) consolidated 1 Apr 2016; ESMA APM organic definition; PepsiCo distribution counted as organic",
    "2016Q3": "Hame in current, not comparative; PepsiCo distribution counted as organic",
    "2016Q4": "Hame in current, not comparative; PepsiCo distribution counted as organic; Nordic delivery problems",
    "2017Q1": "Hame in current, not comparative (anniversary 1 Apr 2017); Kavli anniversary 1 Mar",
    "2017Q4": "K-Salat (DK) sold Dec-2017; Agrimex (CZ) acquired; organic-growth row in segment table from this report",
    "2018Q1": "Scoop and Pastella transferred internally to Orkla Food Ingredients (Jan-2018); IFRS 15 (no material effect)",
    "2018Q4": "Mrs Cheng's (SE) sold Dec-2018; underlying EBIT (adj.) growth APM introduced",
    "2019Q1": "IFRS 16 from 1 Jan 2019, 2018 NOT restated (negligible EBIT effect; EBITDA up); Pama brand acquired",
    "2019Q2": "Easyfood (DK, 90%, ~NOK 415m/yr) from 1 May 2019; IFRS 16 vs IAS 17 comparative",
    "2019Q3": "Glyngore brand sold Jul-2019; IFRS 16 vs IAS 17 comparative",
    "2019Q4": "IFRS 16 vs IAS 17 comparative",
    "2020Q1": "Covid-19 stockpiling; Panzani distribution (CZ/SK/HU, NOK 111m/yr) ended 1 Mar 2020 (structure); SaritaS sold",
    "2020Q2": "Havrefras brand bought from PepsiCo Jun-2020 (previously distributed); Vestlandslefsa sold; Covid reversal",
    "2020Q4": "Frodinge cakes moved to Orkla Food Ingredients (not restated; structure)",
    "2021Q1": "Seagood Fort Deli (FI, 80%) from 1 Mar 2021; Panzani/OTA Solgryn distribution losses treated as structure; Sweden ERP roll-out",
    "2021Q2": "Eastern Condiments (India, 67.8%, ~NOK 1.1-1.2bn/yr) consolidated 1 Apr 2021 (structure +5.9pp)",
    "2021Q3": "Eastern in current, not comparative",
    "2021Q4": "Eastern in current, not comparative; Orkla Latvija divestment(s)",
    "2022Q1": "Exit from Russia (Hame Foods ZAO, ~NOK 184m/yr) Mar-2022 (structure); Eastern in current, not comparative",
    "2022Q2": "Last quarter of definition D (incl. India)",
    "2022Q3": "DEFINITION BREAK D->E: Orkla India carved out (Orkla Foods Europe); 2021 comparatives restated; loss of PepsiCo/Tropicana and Alpro distribution (2022-24) treated as structure; Struer, Everest water, Orkla Latvija convenience sold (2022)",
    "2023Q1": "Khell-Food (HU, ~NOK 85m/yr) from 1 Mar 2023",
    "2023Q2": "New operating model (portfolio companies) from 1 Mar 2023, scope unchanged; price vs volume/mix split begins; distribution agreements and intra-group transfers formally structure",
    "2024Q2": "Blomberg's Glogg and Fruta Podivin (CZ) sold May-2024; Tropicana/Alpro distribution loss in structure",
    "2024Q4": "Renamed Orkla Foods (Feb 2025); scope unchanged",
    "2026Q1": "Quaker (PepsiCo) distribution ended; small DK distribution agreement moved to Orkla Food Ingredients (structure)",
    "2026Q2": "Poltsamaa factory and brands (EE) sold; Quaker distribution end (structure)",
}

# ----------------------------------------------------------------------------------------------
# Load
# ----------------------------------------------------------------------------------------------


def load_raw():
    frames = []
    for e in range(1, 7):
        d = pd.read_csv(os.path.join(RAW, f"era_E{e}_verified.csv"))
        d["era"] = f"E{e}"
        frames.append(d)
    raw = pd.concat(frames, ignore_index=True)
    m = raw["report"].str.extract(r"Q(\d)\s+(\d{4})")
    raw["report_period"] = m[1] + "Q" + m[0]
    raw["def_id"] = [assign_def(lab, rp) for lab, rp in zip(raw["segment_label"], raw["report_period"])]
    raw["metric_class"] = [metric_class(x) for x in raw["ebit_metric"]]
    return raw


def load_restatements():
    r = pd.read_csv(os.path.join(RAW, "restatements.csv"))
    lab_map = {
        "Orkla Foods Nordic": "A_NORDIC",
        "Orkla Food Ingredients": "A_OFI",
        "Orkla Foods International": "A_INTL",
        "Orkla Foods (2000-2007 definition)": "A",
        "Orkla Foods Nordic (2008-2012 definition)": "B",
        "Orkla Foods (2013-2014 definition)": "C",
        "Orkla Foods (2015-2022 definition)": "D",
        "Orkla Foods Europe (2022Q3- ; renamed Orkla Foods Feb 2025)": "E",
        "Orkla India (carved out of Orkla Foods from Q3 2022)": "IND",
    }
    r["def_id"] = r["segment_label"].map(lab_map)
    r["metric_class"] = [metric_class(x) for x in r["ebit_metric"]]
    r["is_quarter"] = r["period"].str.fullmatch(r"\d{4}Q[1-4]")
    return r


# ----------------------------------------------------------------------------------------------
# Quarterly headline
# ----------------------------------------------------------------------------------------------


def og_label_for(p, row):
    y, q = pparse(p)
    if (y, q) <= (2003, 1):
        base = "growth for continuing business (FX-adj.)"
        if p == "2001Q1":
            base = "growth for continuing business (FX adj. not stated)"
    elif p == "2008Q1":
        base = "growth adj. for acquisitions/disposals (FX excl. not stated)"
    elif y <= 2014:
        base = "underlying growth (excl. M&A and FX)"
    elif (y, q) <= (2016, 1):
        base = "organic growth (excl. M&A and FX)"
    elif (y, q) <= (2023, 1):
        base = "organic growth (ESMA APM: M&A 12m rule, FX at prior-year rates)"
    else:
        base = "organic growth (APM; distribution agreements & intra-group transfers = structure)"
    if p in CALENDAR_ADJ:
        base += "; " + CALENDAR_ADJ[p].split(" (")[0]
    if p == "2013Q2":
        base += "; incl. Rieber pro forma"
    elif p in ("2013Q3", "2013Q4"):
        # verify-E3 residual concern 2: only Q2 states the Rieber basis (QA fix: label no longer claims pro forma)
        base += "; Rieber treatment not stated (Q2 2013 was incl. Rieber pro forma)"
    if p in NINE_MONTH_AVG:
        base += "; 9M-2005 average implied by FY and Q4 (not quarter-specific)"
    elif row is not None and nz(row.get("og_source")) and row.get("og_source") == "derived":
        base += "; derived from YTD"
    return base


def og_quality_for(p, row):
    """A = quarterly figure stated on the standard unadjusted basis; B = stated but calendar-adjusted,
    'about/approx/on a par' verbal, incl. pro-forma acquisitions or doubtful; C = derived/averaged/estimated."""
    if p in OG_QUALITY_OVERRIDES:
        return OG_QUALITY_OVERRIDES[p][0]
    if row.get("og_source") == "derived" or bool(row.get("derived_from_ytd")):
        return "C"
    if p in CALENDAR_ADJ:
        return "B"
    if re.search(r"approx|about|around|some |roughly|on a par|pro forma", str(row.get("og_metric")), re.I):
        return "B"
    return "A"


QRANK = {"A": 0, "B": 1, "C": 2}


def worst(*qs):
    qs = [q for q in qs if nz(q)]
    return max(qs, key=lambda x: QRANK[x]) if qs else np.nan


def parse_kpis(note):
    out = {}
    note = str(note)
    m = re.search(r"Contribution ratio (-?\d+(?:\.\d+)?)%", note)
    if m:
        out["contribution_ratio_pct"] = float(m.group(1))
    m = re.search(r"underlying EBIT \(adj\.\) growth (-?\d+(?:\.\d+)?)%", note)
    if m:
        out["underlying_ebit_growth_pct"] = float(m.group(1))
    m = re.search(r"reported EBIT (-?\d+)", note)
    if m:
        out["reported_ebit_nokm"] = float(m.group(1))
    return out


def build_quarterly(raw):
    periods = all_periods()
    food = raw[raw["def_id"].notna()].copy()
    rows = []
    for p in periods:
        y, q = pparse(p)
        hd = headline_def(p)
        py = shift_years(p, -1)
        # ---- current-vintage row of the definition in force
        if y == 2000:
            cur = food[(food.period == p) & (food.def_id == "A") & (food.vintage == "comparative")
                       & (food.report_period == shift_years(p, 1))]
        else:
            cur = food[(food.period == p) & (food.def_id == hd) & (food.vintage == "current")
                       & (food.report_period == p)]
        assert len(cur) == 1, (p, len(cur))
        c = cur.iloc[0].to_dict()
        rep_p = c["report_period"]
        rec = dict(period=p, year=y, q=q, def_id=hd, segment_label=c["segment_label"],
                   revenue_nokm=float(c["revenue_nokm"]), ebit_nokm=float(c["ebit_nokm"]),
                   ebit_metric=c["metric_class"], ebit_metric_printed=c["ebit_metric"],
                   ebit_margin_printed=c["ebit_margin_pct"] if not bool(c["margin_computed"]) else np.nan)
        src = [f"{c['report']} report ({'comparative' if y == 2000 else 'current'}): {c['report_url']}"]
        # ---- prior-year same-definition comparative
        comp = food[(food.period == py) & (food.def_id == hd) & (food.vintage == "comparative")
                    & (food.report_period == rep_p)]
        if y == 2000:
            comp = comp.iloc[0:0]
        if len(comp) == 1:
            cp = comp.iloc[0].to_dict()
            rec.update(revenue_py_samedef=float(cp["revenue_nokm"]), ebit_py_samedef=float(cp["ebit_nokm"]),
                       dm_source="same_report")
            comp_row = cp
        else:
            # fallback: any other same-definition, same-metric source for the prior-year quarter
            alt = food[(food.period == py) & (food.def_id == hd) & (food.metric_class == c["metric_class"])]
            if len(alt) and y > 2000:
                a0 = alt.sort_values("report_period").iloc[-1].to_dict()
                rec.update(revenue_py_samedef=float(a0["revenue_nokm"]), ebit_py_samedef=float(a0["ebit_nokm"]),
                           dm_source="other_same_def")
                src.append(f"py from {a0['report']} ({a0['vintage']})")
                comp_row = a0
            else:
                rec.update(revenue_py_samedef=np.nan, ebit_py_samedef=np.nan, dm_source="none")
                comp_row = None
        # ---- organic growth and decomposition; fill gaps from later comparatives of the same definition
        later = food[(food.period == p) & (food.def_id == hd) & (food.report_period > rep_p)
                     & (food.revenue_nokm == c["revenue_nokm"])].sort_values("report_period")
        fill_src = {}
        vals = {}
        for f in ["organic_growth_pct", "price_mix_pct", "volume_pct", "fx_effect_pct", "structural_effect_pct"]:
            v = c.get(f)
            if not nz(v):
                for _, lr in later.iterrows():
                    if nz(lr[f]):
                        v = lr[f]
                        fill_src[f] = f"{lr['report']} report comparative"
                        break
            vals[f] = v if nz(v) else np.nan
        # E-basis KPIs (contribution ratio etc.) from notes, with the same fill rule
        kpis = parse_kpis(c.get("notes"))
        for _, lr in later.iterrows():
            for k, v in parse_kpis(lr["notes"]).items():
                kpis.setdefault(k, v)
        kpi_src = []
        if p in PRICE_VOL_CROSS_DEF:
            xdef = PRICE_VOL_CROSS_DEF[p]
            xr = food[(food.period == p) & (food.def_id == xdef) & food.price_mix_pct.notna()]
            assert len(xr) >= 1, p
            xr0 = xr.sort_values("report_period").iloc[0]
            vals["price_mix_pct"], vals["volume_pct"] = xr0["price_mix_pct"], xr0["volume_pct"]
            for k, v in parse_kpis(xr0["notes"]).items():
                kpis.setdefault(k, v)
            # Splice QA fix: keep only RATES from the other definition. A NOK level (reported EBIT) of definition E
            # must not sit next to this row's definition-D EBIT (480 vs E-basis reported EBIT 389 would imply a
            # spurious -91m of other income/expenses), so reported_ebit_nokm is left blank and quoted in kpi_source.
            rep_x = kpis.pop("reported_ebit_nokm", None)
            kpi_src.append(f"price/vol and KPIs are DEFINITION {xdef} (Orkla Foods Europe) from the {xr0['report']} "
                           f"report comparative; they sum to E organic {xr0['organic_growth_pct']}, not to the headline D organic"
                           + (f"; reported_ebit_nokm left blank: the E-basis reported EBIT {rep_x:.0f} (E EBIT (adj.) "
                              f"{xr0['ebit_nokm']:.0f}) is not comparable with this row's D EBIT" if rep_x is not None else ""))
            src.append(f"price/volume and contribution ratio from {xr0['report']} report comparative (definition {xdef})")
        for f in ("price_mix_pct", "volume_pct"):
            if f in fill_src:
                kpi_src.append(f"price/vol and KPIs from {fill_src[f]}")
                break
        og = vals["organic_growth_pct"]
        rec["organic_growth_pct"] = og
        if nz(og):
            q_ = og_quality_for(p, c)
            rec["og_quality"] = q_
            rec["og_label"] = og_label_for(p, c)
            rec["og_source"] = (f"{c['og_source']} [{c['report']} report]" if "organic_growth_pct" not in fill_src
                                else f"table [{fill_src['organic_growth_pct']}]")
        else:
            rec["og_quality"] = np.nan
            rec["og_label"] = og_label_for(p, None) if y > 2000 else "none (no quarterly organic growth for 2000)"
            rec["og_source"] = "none"
        rec["og_easter_adjusted"] = p in CALENDAR_ADJ
        rec["price_pct"] = vals["price_mix_pct"]
        rec["volume_mix_pct"] = vals["volume_pct"]
        rec["fx_effect_pct"] = vals["fx_effect_pct"]
        rec["structural_effect_pct"] = vals["structural_effect_pct"]
        for k in ("contribution_ratio_pct", "underlying_ebit_growth_pct", "reported_ebit_nokm"):
            rec[k] = kpis.get(k, np.nan)
        rec["kpi_source"] = "; ".join(kpi_src) if kpi_src else ("current report" if kpis else "")
        for f, s in fill_src.items():
            src.append(f"{f} from {s}")
        rec["drivers_note"] = c.get("drivers_note") if nz(c.get("drivers_note")) else ""
        rec["report"] = c["report"]
        rec["source_reports"] = "; ".join(src)
        rec["_comp_og"] = comp_row.get("organic_growth_pct") if comp_row else np.nan
        rec["_comp_og_src"] = comp_row.get("og_source") if comp_row else np.nan
        rows.append(rec)
    Q = pd.DataFrame(rows)

    # ---- organic-growth estimates where nothing quarterly was published (2012Q2, 2012Q4; quality C)
    r11 = {qq: float(food[(food.period == f"2011Q{qq}") & (food.def_id == "B") & (food.vintage == "comparative")
                          & (food.report_period == f"2012Q{qq}")]["revenue_nokm"].iloc[0]) for qq in range(1, 5)}
    q2 = (EST_2012["h1"] * (r11[1] + r11[2]) - EST_2012["q1"] * r11[1]) / r11[2]
    q4 = (EST_2012["fy"] * sum(r11.values()) - EST_2012["q1"] * r11[1] - q2 * r11[2] - EST_2012["q3"] * r11[3]) / r11[4]
    OG_ESTIMATES = {
        "2012Q2": (round(q2, 1), f"ESTIMATE: (H1 {EST_2012['h1']} x H1-11 rev - Q1 {EST_2012['q1']} x Q1-11 rev) / Q2-11 rev "
                                 f"= {q2:.2f}; H1 +0.8 from Q2 2012 pres p.11 (report +1%), Q1 'about 5%' (Q1 2012 report p.5); "
                                 f"weights = 2011 revenue as printed (incl. Bakers; ex-Bakers weights give ~-3.0); "
                                 f"Q1 read as 4.5-5.5 gives -2.6 to -3.6; Q1+Q2 together (H1) are well determined"),
        "2012Q4": (round(q4, 1), f"ESTIMATE: FY2012 +1% (Q4 2012 pres p.23) less Q1 5.0, Q2 est. {q2:.1f}, Q3 4.0, weighted by "
                                 f"2011 revenue = {q4:.2f} (equivalently FY less H1 0.8 and Q3; the Q1 split cancels); "
                                 f"consistent with report text 'small underlying decline' (fewer selling days); "
                                 f"FY read as 0.5-1.5 gives -3.0 to +0.6"),
    }
    est, est_note = [], []
    for _, r in Q.iterrows():
        if nz(r.organic_growth_pct):
            est.append(r.organic_growth_pct)
            est_note.append(OG_PRESENT_NOTES.get(r.period, ""))
        elif r.period in OG_ESTIMATES:
            est.append(OG_ESTIMATES[r.period][0])
            est_note.append(OG_ESTIMATES[r.period][1])
        else:
            est.append(np.nan)
            est_note.append("no quarterly organic growth available (2000 quarters exist only as 2001 comparatives)"
                            if r.year == 2000 else "")
    Q["og_est"] = est
    Q["og_est_note"] = est_note
    for p, (v, n) in OG_ESTIMATES.items():
        i = Q.index[Q.period == p][0]
        Q.loc[i, "og_quality"] = "C"
        Q.loc[i, "og_source"] = "estimate (see og_est_note)"
        Q.loc[i, "og_label"] += "; ESTIMATE (no quarterly figure published; og_est only)"  # splice QA fix
    Q.loc[Q.period.isin(OG_QUALITY_OVERRIDES.keys()), "og_est_note"] = [
        (n + " " if n else "") + "QUALITY NOTE: " + OG_QUALITY_OVERRIDES[p][1]
        for p, n in zip(Q.loc[Q.period.isin(OG_QUALITY_OVERRIDES.keys()), "period"],
                        Q.loc[Q.period.isin(OG_QUALITY_OVERRIDES.keys()), "og_est_note"])]

    # ---- prior-year organic growth on the most comparable basis
    by_p = Q.set_index("period")
    alt_og = {}
    for p, d in OG_PY_FROM_ALT.items():
        py = shift_years(p, -1)
        a = food[(food.period == py) & (food.def_id == d) & (food.vintage == "current")]
        alt_og[p] = (float(a["organic_growth_pct"].iloc[0]),
                     og_quality_for(py, a.iloc[0].to_dict()) if nz(a["organic_growth_pct"].iloc[0]) else np.nan)
    og_py, og_py_src, og_py_q = [], [], []
    for _, r in Q.iterrows():
        py = shift_years(r.period, -1)
        if py not in by_p.index:
            og_py.append(np.nan); og_py_src.append("none"); og_py_q.append(np.nan)
            continue
        prow = by_p.loc[py]
        if nz(r._comp_og):
            og_py.append(float(r._comp_og))
            og_py_src.append("same_report_comparative")
            og_py_q.append("A" if r._comp_og_src == "table" else prow.og_quality)
        elif r.period in alt_og:
            og_py.append(alt_og[r.period][0])
            og_py_src.append(f"alt_def_proxy ({OG_PY_FROM_ALT[r.period]} 2005-07 sub-segment)")
            og_py_q.append(alt_og[r.period][1])
        elif nz(prow.og_est):
            og_py.append(prow.og_est)
            og_py_src.append("prior_headline_same_def" if prow.def_id == r.def_id else
                             f"prior_headline_other_def ({prow.def_id})")
            og_py_q.append(prow.og_quality)
        else:
            og_py.append(np.nan); og_py_src.append("none"); og_py_q.append(np.nan)
    Q["og_py"] = og_py
    Q["og_py_source"] = og_py_src
    Q["d_og_yoy_pp"] = (Q["og_est"] - Q["og_py"]).round(2)
    Q["d_og_quality"] = [worst(a, b) if nz(d) else np.nan for a, b, d in zip(Q.og_quality, og_py_q, Q.d_og_yoy_pp)]
    Q["d_og_def_break"] = [s.startswith("prior_headline_other_def") or s.startswith("alt_def") for s in og_py_src]

    # ---- same-definition growth and margin change (from NOK figures)
    Q["ebit_margin_pct"] = (100 * Q.ebit_nokm / Q.revenue_nokm).round(2)
    Q["margin_py_samedef"] = (100 * Q.ebit_py_samedef / Q.revenue_py_samedef).round(2)
    Q["rev_growth_samedef_pct"] = (100 * (Q.revenue_nokm / Q.revenue_py_samedef - 1)).round(2)
    Q["ebit_growth_samedef_pct"] = (100 * (Q.ebit_nokm / Q.ebit_py_samedef - 1)).round(2)
    Q["d_margin_yoy_pp"] = (100 * (Q.ebit_nokm / Q.revenue_nokm - Q.ebit_py_samedef / Q.revenue_py_samedef)).round(3)

    # ---- calendar / flags
    Q["easter_date"] = [easter_date(y).strftime("%Y-%m-%d") for y in Q.year]
    Q["easter_q"] = [easter_quarter(y) for y in Q.year]
    sh = []
    for y, q in zip(Q.year, Q.q):
        e0, e1 = easter_quarter(y), easter_quarter(y - 1)
        if q in (1, 2) and e0 != e1:
            sh.append(1 if e0 == q else -1)
        else:
            sh.append(0)
    Q["easter_shift"] = sh
    # share of the 9-day Easter shopping/holiday window (Palm Sunday .. Easter Monday) falling in Q1;
    # for Q1 rows: share this year minus share last year (positive = more Easter trade in Q1 than a year ago)
    def q1_share(y):
        e = easter_date(y)
        days = pd.date_range(e - pd.Timedelta(days=7), e + pd.Timedelta(days=1))
        return float((days.month <= 3).mean())
    Q["easter_window_q1_share"] = [round(q1_share(y), 3) for y in Q.year]
    Q["d_easter_window_q1"] = [round(q1_share(y) - q1_share(y - 1), 3) + 0.0 if q == 1 else
                               (round(q1_share(y - 1) - q1_share(y), 3) + 0.0 if q == 2 else 0.0)
                               for y, q in zip(Q.year, Q.q)]
    Q["india_included"] = [(pparse(p) >= (2007, 2) and pparse(p) <= (2007, 4)) or
                           (pparse(p) >= (2014, 4) and pparse(p) <= (2022, 2)) for p in Q.period]
    Q["ifrs16_transition"] = Q.year == 2019
    Q["covid"] = Q.year.isin([2020, 2021])
    Q["event_note"] = [EVENT_NOTES.get(p, "") for p in Q.period]

    # ---- chain-linked indices (2015 average = 100), quarter-specific chaining
    for col, num, den in (("rev_chain_idx", "revenue_nokm", "revenue_py_samedef"),
                          ("ebit_chain_idx", "ebit_nokm", "ebit_py_samedef")):
        idx = {}
        base15 = Q[Q.year == 2015]
        avg15 = base15[num].mean()
        for _, r in base15.iterrows():
            idx[r.period] = 100.0 * r[num] / avg15
        P = Q.set_index("period")
        for p in Q.period[Q.year > 2015]:  # forward
            pp = shift_years(p, -1)
            idx[p] = idx[pp] * P.loc[p, num] / P.loc[p, den]
        for p in reversed(list(Q.period[Q.year < 2015])):  # backward: idx(t) = idx(t+4) * py(t+4)/cur(t+4)
            nx = shift_years(p, 1)
            idx[p] = idx[nx] * P.loc[nx, den] / P.loc[nx, num]
        Q[col] = [round(idx[p], 3) for p in Q.period]

    cols = ["period", "year", "q", "def_id", "segment_label", "revenue_nokm", "ebit_nokm", "ebit_metric",
            "ebit_margin_pct", "ebit_margin_printed",
            "revenue_py_samedef", "ebit_py_samedef", "margin_py_samedef",
            "rev_growth_samedef_pct", "ebit_growth_samedef_pct", "d_margin_yoy_pp", "dm_source",
            "organic_growth_pct", "og_label", "og_quality", "og_easter_adjusted", "og_source",
            "og_est", "og_est_note", "og_py", "og_py_source", "d_og_yoy_pp", "d_og_quality", "d_og_def_break",
            "price_pct", "volume_mix_pct", "fx_effect_pct", "structural_effect_pct",
            "contribution_ratio_pct", "underlying_ebit_growth_pct", "reported_ebit_nokm", "kpi_source",
            "easter_date", "easter_q", "easter_shift", "easter_window_q1_share", "d_easter_window_q1", "india_included", "ifrs16_transition", "covid",
            "rev_chain_idx", "ebit_chain_idx",
            "event_note", "drivers_note", "ebit_metric_printed", "report", "source_reports"]
    return Q[cols]


# ----------------------------------------------------------------------------------------------
# Alternative definitions
# ----------------------------------------------------------------------------------------------


def build_alt(raw, rst, Q):
    head_keys = set(zip(Q.period, Q.def_id, Q.ebit_metric))
    recs = []
    food = raw[raw.def_id.notna()]
    for _, r in food.sort_values(["period", "report_period"]).iterrows():
        key = (r.period, r.def_id, r.metric_class)
        if key in head_keys:
            continue  # identical definition and metric as the headline -> not an alternative
        recs.append(dict(period=r.period, def_id=r.def_id, segment_label=r.segment_label,
                         revenue_nokm=r.revenue_nokm, ebit_nokm=r.ebit_nokm, ebit_metric=r.metric_class,
                         organic_growth_pct=r.organic_growth_pct,
                         source=f"{r.report} report ({r.vintage}): {r.report_url}", derived=False,
                         _prio=0 if r.vintage == "current" else 1, _rp=r.report_period))
    for _, r in rst[rst.is_quarter & rst.def_id.notna()].iterrows():
        key = (r.period, r.def_id, r.metric_class)
        if key in head_keys:
            continue
        recs.append(dict(period=r.period, def_id=r.def_id, segment_label=r.segment_label,
                         revenue_nokm=r.revenue_nokm, ebit_nokm=r.ebit_nokm, ebit_metric=r.metric_class,
                         organic_growth_pct=r.organic_growth_pct,
                         source=f"restatements.csv: {r.source_doc} ({r.source_url})", derived=False,
                         _prio=2, _rp="9999"))
    A = pd.DataFrame(recs)
    # de-duplicate (period, def, metric): keep earliest current / comparative print, merge OG and sources
    out = []
    for key, g in A.groupby(["period", "def_id", "ebit_metric"], sort=True):
        g = g.sort_values(["_prio", "_rp"])
        first = g.iloc[0].to_dict()
        if g.revenue_nokm.nunique() > 1 or g.ebit_nokm.dropna().nunique() > 1:
            first["notes"] = "vintages differ: " + "; ".join(f"{a}/{b}" for a, b in zip(g.revenue_nokm, g.ebit_nokm))
        else:
            first["notes"] = ""
        ogs = g.organic_growth_pct.dropna()
        first["organic_growth_pct"] = ogs.iloc[0] if len(ogs) else np.nan
        first["source"] = " | ".join(dict.fromkeys(g.source))
        out.append(first)
    A = pd.DataFrame(out)

    # Eliminations within A (2004Q1-2007Q4) derived as residual: A total - (Nordic + Ingredients + International)
    H = Q.set_index("period")
    elim = []
    for p in sorted(A.loc[A.def_id == "A_NORDIC", "period"].unique()):
        if ((A.period == p) & (A.def_id == "A_ELIM")).any():
            continue
        subs = A[(A.period == p) & A.def_id.isin(["A_NORDIC", "A_OFI", "A_INTL"]) & (A.ebit_metric == "EBITA (IFRS)")]
        if subs.def_id.nunique() != 3 or p not in H.index:
            continue
        a_rev, a_eb = H.loc[p, "revenue_nokm"], H.loc[p, "ebit_nokm"]
        if H.loc[p, "ebit_metric"] != "EBITA (IFRS)":  # 2004: headline is NGAAP; use IFRS comparative of 2005 reports
            a_rev, a_eb = H.loc[shift_years(p, 1), "revenue_py_samedef"], H.loc[shift_years(p, 1), "ebit_py_samedef"]
        r_res, e_res = a_rev - subs.revenue_nokm.sum(), a_eb - subs.ebit_nokm.sum()
        elim.append(dict(period=p, def_id="A_ELIM", segment_label="Eliminations Orkla Foods (derived)",
                         revenue_nokm=r_res, ebit_nokm=e_res if abs(e_res) > 0.5 else np.nan, ebit_metric="EBITA (IFRS)",
                         organic_growth_pct=np.nan, derived=True,
                         source="derived: Orkla Foods (A, IFRS) minus Nordic + Ingredients + International",
                         notes="residual; EBIT residual blank when zero"))
    A = pd.concat([A, pd.DataFrame(elim)], ignore_index=True)

    # D derived after 2022Q2 = E (headline) + India; OG weighted by prior-year revenue of each part
    E = Q[Q.def_id == "E"].set_index("period")
    IND = A[A.def_id == "IND"].set_index("period")
    ind_py = IND.revenue_nokm
    drv = []
    for p in E.index:
        if p not in IND.index:
            continue
        py = shift_years(p, -1)
        e_py, i_py = E.loc[p, "revenue_py_samedef"], ind_py.get(py, np.nan)
        og = np.nan
        if nz(e_py) and nz(i_py) and nz(E.loc[p, "organic_growth_pct"]) and nz(IND.loc[p, "organic_growth_pct"]):
            og = round((E.loc[p, "organic_growth_pct"] * e_py + IND.loc[p, "organic_growth_pct"] * i_py) / (e_py + i_py), 2)
        drv.append(dict(period=p, def_id="D_DERIVED", segment_label="Orkla Foods (2015-22 def.) derived = E + Orkla India",
                        revenue_nokm=E.loc[p, "revenue_nokm"] + IND.loc[p, "revenue_nokm"],
                        ebit_nokm=E.loc[p, "ebit_nokm"] + IND.loc[p, "ebit_nokm"], ebit_metric="EBIT (adj.)",
                        organic_growth_pct=og, derived=True,
                        source="derived: Orkla Foods Europe/Orkla Foods (headline) + Orkla India, same report",
                        notes="sum of printed segments (eliminations negligible: Q1 2022 4,239+550=4,789 vs 4,788 printed); "
                              "OG = prior-year-revenue-weighted average of E and India organic growth (approximation)"))
    A = pd.concat([A, pd.DataFrame(drv)], ignore_index=True)
    A["ebit_margin_pct"] = (100 * A.ebit_nokm / A.revenue_nokm).round(2)
    A.loc[A.def_id == "A_ELIM", "ebit_margin_pct"] = np.nan
    A["def_desc"] = A.def_id.map(DEF_INFO)
    A["derived"] = A["derived"].astype(bool)
    A = A.sort_values(["def_id", "period", "ebit_metric"]).reset_index(drop=True)
    return A[["period", "def_id", "segment_label", "revenue_nokm", "ebit_nokm", "ebit_margin_pct",
              "organic_growth_pct", "source", "ebit_metric", "derived", "def_desc", "notes"]]


# ----------------------------------------------------------------------------------------------
# Annual
# ----------------------------------------------------------------------------------------------

HEADLINE_ANNUAL_DEF = {**{y: "A" for y in range(2000, 2008)}, **{y: "B" for y in range(2008, 2013)},
                       2013: "C", 2014: "D", **{y: "D" for y in range(2015, 2022)},
                       **{y: "E" for y in range(2022, 2026)}}


def build_annual(Q, ALT, rst):
    seghist = json.load(open(os.path.join(RAW, "segment_history.json")))
    rows = []
    for it in seghist["pre_2000"]["annual_orkla_foods"]:
        rows.append(dict(year=it["year"], def_id="PRE", segment_label=DEF_INFO["PRE"],
                         revenue_nokm=it["revenue"], ebit_nokm=it["op_profit"],
                         ebit_metric="NGAAP operating profit after goodwill amortisation",
                         ebit_alt_nokm=it.get("op_profit_before_goodwill", np.nan),
                         ebit_alt_metric="NGAAP operating profit before goodwill amortisation"
                         if it.get("op_profit_before_goodwill") else "",
                         n_quarters=0, source="segment_history.json pre_2000 (annual reports on Hugin)",
                         is_headline=True))
    # quarterly pool: headline + alternative definitions
    hcols = ["period", "def_id", "revenue_nokm", "ebit_nokm", "ebit_metric", "organic_growth_pct", "og_est",
             "revenue_py_samedef"]
    pool = pd.concat([
        Q[hcols].assign(origin="headline"),
        # D_DERIVED annual 2022 = printed D 2022Q1-Q2 (headline) + derived 2022Q3-Q4
        Q.loc[(Q.def_id == "D") & (Q.year == 2022), hcols].assign(def_id="D_DERIVED", origin="headline"),
        ALT[["period", "def_id", "revenue_nokm", "ebit_nokm", "ebit_metric", "organic_growth_pct"]]
        .assign(og_est=ALT.organic_growth_pct, revenue_py_samedef=np.nan, origin="alt"),
    ], ignore_index=True)
    pool["year"] = pool.period.str[:4].astype(int)
    checks = []
    for (d, y, m), g in pool.groupby(["def_id", "year", "ebit_metric"]):
        if d in ("A_ELIM", "A_OFI", "A_INTL") or len(g) != 4 or g.period.nunique() != 4:
            continue
        if d == "D_DERIVED" and y == 2022:
            g = g.assign(revenue_py_samedef=np.nan)
        rev, eb = g.revenue_nokm.sum(), g.ebit_nokm.sum()
        if (d, y, m) in PRINTED_FY:
            pr = PRINTED_FY[(d, y, m)]
            checks.append((d, y, m, rev, eb, pr[0], pr[1], abs(rev - pr[0]) < 0.5 and abs(eb - pr[1]) < 0.5))
        # same-definition prior-year quarterly revenue for weighting OG (headline: printed comparatives)
        og_fy, og_src = np.nan, ""
        if (d, y) in FY_OG_REPORTED:
            og_fy, og_src = FY_OG_REPORTED[(d, y)][0], "reported FY: " + FY_OG_REPORTED[(d, y)][1]
        else:
            w = g.revenue_py_samedef
            if w.isna().any():
                dprev = "D" if (d == "D_DERIVED" and y == 2022) else d  # D_DERIVED continues D
                prev = (pool[(pool.def_id == dprev) & (pool.year == y - 1)].drop_duplicates("period")
                        .assign(qq=lambda x: x.period.str[4:]).set_index("qq").revenue_nokm)
                w = pd.Series([prev.get(p[4:], np.nan) for p in g.period], index=g.index)
            if g.og_est.notna().all() and w.notna().all():
                og_fy = round(float((g.og_est * w).sum() / w.sum()), 2)
                og_src = "computed: quarterly OG weighted by prior-year same-definition revenue"
        rows.append(dict(year=y, def_id=d, segment_label=DEF_INFO[d], revenue_nokm=rev, ebit_nokm=eb, ebit_metric=m,
                         organic_growth_pct=og_fy, og_source=og_src, n_quarters=4,
                         source="sum of 4 quarters (" + ", ".join(sorted(set(g.origin))) + ")",
                         is_headline=False))
    # annual-only restatements
    for _, r in rst[~rst.is_quarter & rst.def_id.notna() & rst.period.str.endswith("FY")].iterrows():
        y = int(r.period[:4])
        rows.append(dict(year=y, def_id=r.def_id, segment_label=DEF_INFO[r.def_id], revenue_nokm=r.revenue_nokm,
                         ebit_nokm=r.ebit_nokm, ebit_metric=r.metric_class + (" pre-IAS 19R" if "before IAS 19R" in str(r.ebit_metric) else ""),
                         organic_growth_pct=r.organic_growth_pct if nz(r.organic_growth_pct) else
                         (FY_OG_REPORTED.get((r.def_id, y), (np.nan,))[0]),
                         og_source="restatements.csv" if nz(r.organic_growth_pct) else
                         ("reported FY: " + FY_OG_REPORTED[(r.def_id, y)][1] if (r.def_id, y) in FY_OG_REPORTED else ""),
                         n_quarters=0, source=f"restatements.csv: {r.source_doc}", is_headline=False))
    for x in ANNUAL_EXTRA:
        rows.append(dict(**x, segment_label=DEF_INFO[x["def_id"]], n_quarters=0, is_headline=False,
                         organic_growth_pct=np.nan, og_source=""))
    A = pd.DataFrame(rows)
    # drop annual-only rows that duplicate a 4-quarter sum (same def/year/metric and same values)
    A["_k"] = list(zip(A.def_id, A.year, A.ebit_metric))
    dup = A.duplicated(subset=["def_id", "year", "ebit_metric", "revenue_nokm", "ebit_nokm"], keep="first")
    A = A[~dup].copy()
    # mark headline rows: def in force (year-end) and preferred metric
    pref_metric = {}
    for y, d in HEADLINE_ANNUAL_DEF.items():
        cand = A[(A.year == y) & (A.def_id == d) & (A.n_quarters == 4)]
        hm = Q[(Q.year == y) & (Q.def_id == d)].ebit_metric.mode()
        cand = cand[cand.ebit_metric == hm.iloc[0]]  # metric as reported that year (2014: EBITA, Q4 2014 report)
        if len(cand) == 0:
            cand = A[(A.year == y) & (A.def_id == d)]
        if len(cand):
            A.loc[cand.index[0], "is_headline"] = True
            pref_metric[(d, y)] = cand.iloc[0].ebit_metric
    # restated basis for the next year's y/y (sum of next year's same-report comparatives when same def)
    Qy = Q.copy()
    for (d, y), m in pref_metric.items():
        nxt = Qy[(Qy.year == y + 1) & (Qy.def_id == d)]
        if len(nxt) == 4:
            i = A.index[(A.year == y) & (A.def_id == d) & (A.is_headline)][0]
            rv, eb = nxt.revenue_py_samedef.sum(), nxt.ebit_py_samedef.sum()
            if abs(eb - A.loc[i, "ebit_nokm"]) > 0.5 or abs(rv - A.loc[i, "revenue_nokm"]) > 0.5:
                A.loc[i, "ebit_alt_nokm"] = eb
                A.loc[i, "ebit_alt_metric"] = f"restated in {y + 1} reports ({nxt.ebit_metric.iloc[0]}; revenue {rv:.0f})"
    # same-definition annual y/y for headline rows
    for i in A.index[A.is_headline & (A.year >= 2001)]:
        y, d = A.loc[i, "year"], A.loc[i, "def_id"]
        qy = Q[(Q.year == y) & (Q.def_id == d)]
        if len(qy) == 4:
            rv_py, eb_py, s = qy.revenue_py_samedef.sum(), qy.ebit_py_samedef.sum(), "sum of same-report comparatives"
        else:
            prev = A[(A.year == y - 1) & (A.def_id == d) & (A.ebit_metric == A.loc[i, "ebit_metric"])]
            if len(prev) == 0:
                continue
            rv_py, eb_py, s = prev.revenue_nokm.iloc[0], prev.ebit_nokm.iloc[0], f"{d} {y - 1} restated annual ({prev.source.iloc[0]})"
        A.loc[i, "revenue_py_samedef"] = rv_py
        A.loc[i, "ebit_py_samedef"] = eb_py
        A.loc[i, "py_source"] = s
    # other rows (pre-2000, non-headline definitions): prior year of the same definition and metric
    for c_ in ("revenue_py_samedef", "ebit_py_samedef", "py_source"):
        if c_ not in A.columns:
            A[c_] = np.nan
    for i in A.index[A.revenue_py_samedef.isna()]:
        y, d, m = A.loc[i, "year"], A.loc[i, "def_id"], A.loc[i, "ebit_metric"]
        prev = A[(A.year == y - 1) & (A.def_id == d) & (A.ebit_metric == m)]
        s = f"{d} {y - 1} ({m})"
        if d == "D_DERIVED" and len(prev) == 0:  # D_DERIVED continues the printed D series
            prev = A[(A.year == y - 1) & (A.def_id == "D") & (A.ebit_metric == m)]
            s = f"D {y - 1} ({m}, printed)"
        if d == "A" and y == 2000:  # 2000 (first A year) vs 1999 business-area annual, same NGAAP after-goodwill basis
            prev = A[(A.year == 1999) & (A.def_id == "PRE")]
            s = "1999 annual report (pre-2001 business area; same NGAAP after-goodwill basis; scope assumed comparable)"
        if len(prev):
            A.loc[i, "revenue_py_samedef"] = prev.revenue_nokm.iloc[0]
            A.loc[i, "ebit_py_samedef"] = prev.ebit_nokm.iloc[0]
            A.loc[i, "py_source"] = s
    A["ebit_margin_pct"] = (100 * A.ebit_nokm / A.revenue_nokm).round(2)
    A["rev_growth_samedef_pct"] = (100 * (A.revenue_nokm / A.revenue_py_samedef - 1)).round(2)
    A["ebit_growth_samedef_pct"] = (100 * (A.ebit_nokm / A.ebit_py_samedef - 1)).round(2)
    A["d_margin_yoy_pp"] = (100 * (A.ebit_nokm / A.revenue_nokm - A.ebit_py_samedef / A.revenue_py_samedef)).round(3)
    A["is_headline"] = A.is_headline.astype(bool)
    notes = {
        (2014, "D"): "Headline annual = D (year-end definition); headline quarters 2014Q1-Q3 are definition C "
                     "(C 9M 2014: 7,707/971; no C full year exists)",
        (2022, "E"): "Headline annual = E (year-end definition); headline quarters 2022Q1-Q2 are definition D",
        (2000, "A"): "2000 from comparatives in the 2001 reports; no organic growth",
        (2001, "A"): "EBIT after goodwill amortisation; EBITA basis (restated in 2002) = 952",
        (2004, "A"): "NGAAP; IFRS basis (restated in 2005) = 1,164",
        # splice QA: printed FY organic growth vs revenue-weighted headline quarters
        (2008, "B"): "FY organic growth 4 is read from a bar chart (Q4 2012 pres p.23); the reported quarters "
                     "(6 / ~4 derived / 5 / 4) weighted by 2007 B revenue give 4.7",
        (2013, "C"): "Printed FY organic growth -4.2 (Q4 2013 pres p.21); the quarters (0 / -4.2 / -3.5 / -6.0) weighted "
                     "by 2012 C revenue give -3.5 (-3.7 with Rieber pro forma in the base): mixed Rieber bases",
    }
    A["notes"] = [notes.get((y, d), "") for y, d in zip(A.year, A.def_id)]
    order = {"PRE": 0, "A": 1, "A_NORDIC": 2, "B": 3, "C": 4, "D": 5, "D_DERIVED": 6, "E": 7, "IND": 8}
    A["_o"] = A.def_id.map(order).fillna(9)
    A = A.sort_values(["year", "is_headline", "_o"], ascending=[True, False, True]).reset_index(drop=True)
    cols = ["year", "def_id", "segment_label", "is_headline", "revenue_nokm", "ebit_nokm", "ebit_metric",
            "ebit_margin_pct", "organic_growth_pct", "og_source", "revenue_py_samedef", "ebit_py_samedef",
            "rev_growth_samedef_pct", "ebit_growth_samedef_pct", "d_margin_yoy_pp", "py_source",
            "ebit_alt_nokm", "ebit_alt_metric", "n_quarters", "source", "notes"]
    for c in cols:
        if c not in A.columns:
            A[c] = np.nan
    return A[cols], checks


# ----------------------------------------------------------------------------------------------
# Methodology auto block
# ----------------------------------------------------------------------------------------------


def fmt(x, nd=1):
    if not nz(x):
        return ""
    return f"{x:,.{nd}f}" if nd else f"{x:,.0f}"


def auto_block(Q, A):
    lines = ["| period | def | revenue | EBIT | margin % | d margin pp | OG est % | OG q | d OG pp | price % | vol/mix % | Easter shift |",
             "|---|---|---:|---:|---:|---:|---:|:-:|---:|---:|---:|---:|"]
    for _, r in Q.iterrows():
        lines.append(f"| {r.period} | {r.def_id} | {fmt(r.revenue_nokm, 0)} | {fmt(r.ebit_nokm, 0)} | {fmt(r.ebit_margin_pct, 2)} | "
                     f"{fmt(r.d_margin_yoy_pp, 2)} | {fmt(r.og_est)} | {r.og_quality if nz(r.og_quality) else ''} | "
                     f"{fmt(r.d_og_yoy_pp)} | {fmt(r.price_pct)} | {fmt(r.volume_mix_pct)} | {r.easter_shift:+d} |")
    lines += ["", "**Annual headline series** (year-end definition):", "",
              "| year | def | revenue | EBIT | metric | margin % | organic % | rev growth (same def) % | d margin pp |",
              "|---|---|---:|---:|---|---:|---:|---:|---:|"]
    for _, r in A[A.is_headline].iterrows():
        lines.append(f"| {r.year} | {r.def_id} | {fmt(r.revenue_nokm, 0)} | {fmt(r.ebit_nokm, 0)} | {r.ebit_metric} | "
                     f"{fmt(r.ebit_margin_pct, 2)} | {fmt(r.organic_growth_pct)} | {fmt(r.rev_growth_samedef_pct)} | "
                     f"{fmt(r.d_margin_yoy_pp, 2)} |")
    miss = Q[Q.og_quality.isna() | (Q.og_quality == "C")]
    lines += ["", "**Quarters where organic growth is missing, derived or estimated (quality C or blank):**", ""]
    for _, r in miss.iterrows():
        lines.append(f"- {r.period}: og_est = {fmt(r.og_est) or 'blank'} "
                     f"({'missing' if not nz(r.og_quality) else 'quality C'}). {r.og_est_note}")
    return "\n".join(lines)


def refresh_md(Q, A):
    if not os.path.exists(OUT_MD):
        return False
    txt = open(OUT_MD, encoding="utf-8").read()
    b, e = "<!-- BEGIN AUTO (build_orkla_quarterly.py) -->", "<!-- END AUTO -->"
    if b not in txt or e not in txt:
        return False
    new = txt.split(b)[0] + b + "\n" + auto_block(Q, A) + "\n" + e + txt.split(e)[1]
    open(OUT_MD, "w", encoding="utf-8").write(new)
    return True


# ----------------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------------


def main():
    raw = load_raw()
    rst = load_restatements()
    Q = build_quarterly(raw)
    ALT = build_alt(raw, rst, Q)
    A, checks = build_annual(Q, ALT, rst)

    # ---------------- checks ----------------
    ok = True
    exp = all_periods()
    if list(Q.period) != exp:
        print("FAIL: quarter coverage"); ok = False
    print(f"Quarters: {len(Q)} ({Q.period.iloc[0]}..{Q.period.iloc[-1]}), all present: {list(Q.period) == exp}")
    dm_ok = Q[Q.year >= 2001].d_margin_yoy_pp.notna().all()
    print(f"d_margin_yoy_pp available for all quarters from 2001Q1: {dm_ok} "
          f"({Q.d_margin_yoy_pp.notna().sum()} of {len(Q)} quarters)")
    ok &= bool(dm_ok)
    mdiff = (Q.ebit_margin_printed - 100 * Q.ebit_nokm / Q.revenue_nokm).abs()
    print(f"Margin = EBIT/revenue: ebit_margin_pct computed from NOK for all rows; printed margins available for "
          f"{Q.ebit_margin_printed.notna().sum()} rows, max |printed - computed| = {mdiff.max():.3f}pp "
          f"(rows > 0.05pp, print-rounding quirks: {', '.join(Q.period[mdiff > 0.0501]) or 'none'})")
    ok &= bool((mdiff.dropna() < 0.1).all())
    print("Four-quarter sums vs printed full-year totals:")
    for d, y, m, rev, eb, pr_r, pr_e, good in checks:
        print(f"  {d:9s} {y} {m[:28]:28s} sum {rev:8.0f}/{eb:6.0f}  printed {pr_r:8.0f}/{pr_e:6.0f}  {'OK' if good else 'MISMATCH'}")
        ok &= good
    missing_checks = [k for k in PRINTED_FY if (k[0], k[1], k[2]) not in {(c[0], c[1], c[2]) for c in checks}]
    if missing_checks:
        print("  printed FY with no 4-quarter set:", missing_checks)
    pv = Q[(Q.period >= "2022Q2")]
    print(f"price/volume available 2022Q2+: {pv.price_pct.notna().sum()} of {len(pv)}")
    print("\nOrganic growth (og_est) by quality:")
    print(Q.og_quality.fillna("missing").value_counts().reindex(["A", "B", "C", "missing"]).fillna(0).astype(int).to_string())
    print(f"  og_est present: {Q.og_est.notna().sum()} of {len(Q)}; organic_growth_pct (published/derived) present: "
          f"{Q.organic_growth_pct.notna().sum()}")
    print(f"  calendar-adjusted (og_easter_adjusted): {int(Q.og_easter_adjusted.sum())}")
    print("d_og_yoy_pp by quality:")
    print(Q.d_og_quality.fillna("missing").value_counts().reindex(["A", "B", "C", "missing"]).fillna(0).astype(int).to_string())
    print(f"  d_og across a definition break: {int(Q.d_og_def_break.sum())}")
    print("og_py source:")
    print(Q.og_py_source.value_counts().to_string())
    print("d_margin source (dm_source):")
    print(Q.dm_source.value_counts().to_string())
    print("Definition counts:", Q.def_id.value_counts().sort_index().to_dict())
    print(f"Alt-definition rows: {len(ALT)} by def {ALT.def_id.value_counts().sort_index().to_dict()}")
    print(f"Annual rows: {len(A)} (headline {int(A.is_headline.sum())}, years {A.year.min()}-{A.year.max()})")

    Q.to_csv(OUT_Q, index=False)
    ALT.to_csv(OUT_ALT, index=False)
    A.to_csv(OUT_A, index=False)
    md = refresh_md(Q, A)
    print(f"\nWrote {OUT_Q}\n      {OUT_ALT}\n      {OUT_A}" + (f"\n      {OUT_MD} (auto block refreshed)" if md else ""))
    if not ok:
        print("SOME CHECKS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
