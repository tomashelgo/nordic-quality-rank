"""Data for the one-page house-price slide (slides/house_prices_indicator.pptx).

Writes slides/house_prices_slide_data.json:
  series   quarterly category sales growth (SSB NACE 47.19, calendar adjusted, y/y %)
           and house-price growth (SSB, y/y %) as known one quarter earlier, 2001-2026
  periods  next-quarter slope of sales growth on house-price growth by sub-period,
           with the same benchmark controls as the screen (own lag, base effect,
           Easter, trading days), COVID-distorted quarters excluded
  evidence calibrated p-values / holdout R^2 from results/
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fcast  # noqa: E402
import screen_predictors as sp  # noqa: E402

panel, pxp, X = sp.prepare()
sp._init(X.index)
hp = X["house_prices__g4"]

# time series on the target quarter: sales growth at q, house-price growth known at q-1
q = pd.period_range("2001Q2", "2026Q2", freq="Q")
sales = pxp["px_yoy"].reindex(q)
hp_lead = hp.shift(1).reindex(q)
covid = pxp["covid_win_q"].reindex(q).fillna(False).astype(bool)
series = [{"q": f"{p.year}Q{p.quarter}", "sales": None if np.isnan(s) else round(float(s), 2),
           "hp": None if np.isnan(h) else round(float(h), 2), "covid": bool(c)}
          for p, s, h, c in zip(q, sales, hp_lead, covid)]
ok = (~covid) & sales.notna() & hp_lead.notna()
corr = float(np.corrcoef(sales[ok], hp_lead[ok])[0, 1])


def slope(frame, cols, x, lo, hi):
    d, _ = sp._with_x(frame, cols, x, sel_only=False)
    d = d[(d.tdate >= pd.Period(lo, "Q")) & (d.tdate <= pd.Period(hi, "Q"))]
    Z = fcast.design(d, ["ar"] + cols)
    Z = Z[:, fcast._varying(Z)]
    Xm = np.column_stack([Z, d["x"].to_numpy(float)])
    yv = d["target"].to_numpy(float)
    b = np.linalg.lstsq(Xm, yv, rcond=None)[0]
    r = yv - Xm @ b
    s2 = r @ r / max(len(yv) - Xm.shape[1], 1)
    se = np.sqrt(s2 * np.linalg.pinv(Xm.T @ Xm)[-1, -1])
    return {"slope": round(float(b[-1]), 3), "t": round(float(b[-1] / se), 2), "n": int(len(d))}


fpx, cpx = sp.frame(pxp, "px_yoy", 1, ["easter_share_d4", "tdays_d4"], "q", "exclude")
feu, ceu = sp.frame(panel, "lfl", 1, ["easter_share_d4", "tdays_d4", "covid_d4"], "q", "exclude")
periods = [
    {"label": "2001-07", "who": "category"} | slope(fpx, cpx, hp, "2001Q1", "2007Q4"),
    {"label": "2008-14", "who": "category"} | slope(fpx, cpx, hp, "2008Q1", "2014Q4"),
    {"label": "2015-24", "who": "category"} | slope(fpx, cpx, hp, "2015Q1", "2024Q2"),
    {"label": "Europris LFL 2015-24", "who": "europris"} | slope(feu, ceu, hp, "2015Q1", "2024Q2"),
]
full = slope(fpx, cpx, hp, "2001Q1", "2024Q2")

ev = pd.read_csv(ROOT / "results" / "evidence_all.csv")
r = ev[(ev.feature == "house_prices__g4") & (ev.target == "lfl") & (ev.h == 1)].iloc[0]
r2 = ev[(ev.feature == "house_prices__g4") & (ev.target == "lfl") & (ev.h == 2)].iloc[0]
hold = pd.read_csv(ROOT / "results" / "top5_holdout.csv")
hh = hold[(hold.key == "house_prices") & (hold.target == "lfl")]
evidence = {
    "proxy_p": float(r.p_px), "proxy_slope": full["slope"], "proxy_n": full["n"],
    "pxpre_p": float(r.p_pxpre), "eu_p_h1": float(r.p_is), "eu_p_h1_control": float(r.p_isc),
    "eu_p_h2": float(r2.p_is), "corr_category": round(corr, 2),
    "hold_lfl": {f"h{int(x.h)}_{x.spec}": round(float(x.hold_r2), 3) for x in hh.itertuples()},
    "hold_rmse": {f"h{int(x.h)}_{x.spec}": [round(float(x.rmse_bench), 2), round(float(x.rmse_model), 2)] for x in hh.itertuples()},
    "latest_hp": round(float(hp.dropna().iloc[-1]), 2), "latest_q": str(hp.dropna().index[-1]),
}
out = {"series": series, "periods": periods, "full": full, "evidence": evidence}
(Path(__file__).parent / "house_prices_slide_data.json").write_text(json.dumps(out, indent=1))
print(json.dumps({"periods": periods, "full": full, "evidence": evidence}, indent=1))
