// One-page slide: house prices as a leading indicator of Europris's sales.
// Input:  slides/house_prices_slide_data.json (from house_prices_slide_data.py)
// Output: slides/house_prices_indicator.pptx
// Usage:  node slides/build_house_prices_slide.js [path/to/apply_theme.js]
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const HERE = __dirname;
const D = JSON.parse(fs.readFileSync(path.join(HERE, "house_prices_slide_data.json"), "utf8"));
const OUT = path.join(HERE, "house_prices_indicator.pptx");

// Slate for sales, terracotta (roof tiles) for house prices, grey for COVID-distorted quarters.
const THEME = {
  name: "Nordic Housing",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1E2B33", lt1: "FFFFFF", dk2: "1F3A4D", lt2: "EEF2F4",
    accent1: "1F3A4D", accent2: "C8553D", accent3: "7F9BAD", accent4: "B5B5B5",
    accent5: "5E6B73", accent6: "D9A441", hlink: "1F3A4D", folHlink: "5E6B73",
  },
};
const HEX = THEME.colors;
const MUTED = "5E6B73";
const GRID = "DCE3E7";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "House prices as a leading indicator of Europris sales";
pres.author = "Europris predictors research";
const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "TITLE_ONLY",
  background: { color: C.background1 },
  margin: [0.5, 0.5, 0.5, 0.5],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.35, w: 12.33, h: 0.7,
      fontFace: THEME.headFontFace, fontSize: 36, bold: true, color: C.text2, align: "left", valign: "middle", margin: 0 },
      text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.5, y: 1.1, w: 12.33, h: 0.65,
      fontFace: THEME.bodyFontFace, fontSize: 16, color: C.text1, valign: "top", margin: 0 },
      text: "" } },
    { placeholder: { options: { name: "footer", type: "body", x: 0.5, y: 6.85, w: 12.33, h: 0.4,
      fontFace: THEME.bodyFontFace, fontSize: 10, color: C.accent5, valign: "top", margin: 0 },
      text: "" } },
  ],
});

pres.addSection({ title: "House prices" });
const s = pres.addSlide({ masterName: "TITLE_ONLY", sectionTitle: "House prices" });

const ev = D.evidence;
const f1 = (x) => x.toFixed(1);
const r2 = (x) => Math.round(x * 100 + 1e-6) / 100; // 0.345 -> 0.35 everywhere
const f2 = (x) => r2(x).toFixed(2);
const pfmt = (p) => (p < 0.01 ? p.toFixed(3) : p.toFixed(2));

s.addText("House prices lead sales by one quarter", { placeholder: "title" });
s.addText([
  { text: "For 25 years, each 1 pp of y/y house-price growth has been followed by " },
  { text: "+0.3 to +0.4 pp", options: { bold: true } },
  { text: " of sales growth in Europris's category the next quarter, on top of sales momentum and calendar effects. " },
  { text: `Latest reading: +${f1(ev.latest_hp)}% (${ev.latest_q}), a mild tailwind.` },
], { placeholder: "body" });

// ---- left: 25-year line chart -------------------------------------------------
const LX = 0.5, TOP = 1.95, CH = 3.35, LW = 8.0;
s.addText("Category sales growth vs house-price growth one quarter earlier, % y/y", {
  x: LX, y: TOP, w: LW, h: 0.3, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true,
  objectName: "line chart heading",
});

const ser = D.series;
// year labels on Q1 every fourth year only, so both PowerPoint and LibreOffice show a clean axis
const labels = ser.map((r) => (r.q.endsWith("Q1") && (+r.q.slice(0, 4) - 2002) % 4 === 0 ? r.q.slice(0, 4) : ""));
const covidIdx = ser.map((r, i) => (r.covid ? i : -1)).filter((i) => i >= 0);
const c0 = Math.max(covidIdx[0] - 1, 0), c1 = Math.min(covidIdx[covidIdx.length - 1] + 1, ser.length - 1);
const sales = ser.map((r) => (r.covid ? null : r.sales));
const covidSales = ser.map((r, i) => (i >= c0 && i <= c1 ? r.sales : null)); // joined to its neighbours
const hp = ser.map((r) => r.hp);

s.addChart(pres.charts.LINE, [
  { name: "Category sales", labels, values: sales },
  { name: "House prices (one quarter earlier)", labels, values: hp },
  { name: "COVID-distorted (excluded)", labels, values: covidSales },
], {
  x: LX - 0.1, y: TOP + 0.35, w: LW + 0.1, h: CH, objectName: "line chart 25 years",
  chartColors: [HEX.accent1, HEX.accent2, HEX.accent4],
  lineSize: 2, lineDataSymbol: "none", displayBlanksAs: "gap",
  showLegend: true, legendPos: "t", legendFontSize: 12, legendFontFace: "+mn-lt", legendColor: HEX.dk1,
  catAxisLabelFrequency: 1, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", catAxisLabelColor: MUTED,
  catAxisLineShow: false, catGridLine: { style: "none" }, catAxisOrientation: "minMax",
  catAxisLabelPos: "low",
  valAxisMinVal: -10, valAxisMaxVal: 25, valAxisMajorUnit: 5,
  valAxisLabelFontSize: 12, valAxisLabelFontFace: "+mn-lt", valAxisLabelColor: MUTED, valAxisLineShow: false,
  valAxisLabelFormatCode: "0",
  valGridLine: { color: GRID, size: 0.75 },
});

// ---- right: slope by sub-period -------------------------------------------------
const RX = 8.85, RW = 3.98;
s.addText("Same effect in every period", {
  x: RX, y: TOP, w: RW, h: 0.3, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true,
  objectName: "bar chart heading",
});
s.addText("Extra sales growth next quarter (pp) per 1 pp of house-price growth", {
  x: RX, y: TOP + 0.33, w: RW, h: 0.45, fontSize: 12, color: MUTED, margin: 0, isTextBox: true, valign: "top",
  objectName: "bar chart caption",
});
const per = D.periods;
s.addChart(pres.charts.BAR, [{
  name: "Slope",
  labels: per.map((p) => (p.who === "europris" ? "Europris LFL 2015–24" : `Category ${p.label.replace("-", "–")}`)),
  values: per.map((p) => r2(p.slope)),
}], {
  x: RX - 0.1, y: TOP + 0.75, w: RW + 0.1, h: 1.85, objectName: "bar chart slopes by period",
  barDir: "bar", catAxisOrientation: "maxMin", barGapWidthPct: 45,
  chartColors: per.map((p) => (p.who === "europris" ? HEX.accent3 : HEX.accent1)),
  showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "+0.00", dataLabelFontSize: 12,
  dataLabelFontFace: "+mn-lt", dataLabelColor: HEX.dk1,
  catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", catAxisLabelColor: HEX.dk1, catAxisLineShow: false,
  valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 0.6, valGridLine: { style: "none" },
  catGridLine: { style: "none" }, showLegend: false,
});
const eu = per.find((p) => p.who === "europris");
s.addText(`Europris's own data is shorter and noisier: significant with COVID-era quarters excluded `
  + `(p ${pfmt(ev.eu_p_h1)}), not when they are kept with controls (p ${pfmt(ev.eu_p_h1_control)}).`, {
  x: RX, y: TOP + 2.65, w: RW, h: 0.75, fontSize: 12, color: MUTED, margin: 0, isTextBox: true, valign: "top",
  objectName: "Europris caveat",
});

// ---- bottom: evidence cards ------------------------------------------------------
const rm = ev.hold_rmse.h1_exclude;
const cards = [
  [`p = ${pfmt(ev.proxy_p)}`, `25 years of category sales, 2001–24 (${ev.proxy_n} quarters)`],
  [`p = ${pfmt(ev.pxpre_p)}`, "2001–14 alone, before Europris's own data starts"],
  [`p = ${pfmt(ev.eu_p_h1)}`, `Europris like-for-like sales, next quarter, 2015–24 (n = ${eu.n})`],
  [`${f1(rm[0])} → ${f1(rm[1])} pp`, "Next-quarter LFL forecast error on unseen 2024Q3–26Q2"],
];
const CY = 5.75, CHH = 0.95, GAP = 0.25, CW = (12.33 - 3 * GAP) / 4;
cards.forEach(([big, small], i) => {
  const x = 0.5 + i * (CW + GAP);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y: CY, w: CW, h: CHH, fill: { color: C.background2 }, line: { type: "none" }, rectRadius: 0.08,
    objectName: `evidence card ${i + 1}`,
  });
  s.addText([
    { text: big, options: { fontSize: 22, bold: true, color: C.text2, breakLine: true } },
    { text: small, options: { fontSize: 12, color: C.text1 } },
  ], {
    x: x + 0.15, y: CY + 0.08, w: CW - 0.3, h: CHH - 0.16, margin: 0, valign: "middle", isTextBox: true,
    objectName: `evidence card ${i + 1} text`,
  });
});

s.addText("Sources: SSB house price index (table 07221); SSB retail trade index NACE 47.19, calendar adjusted "
  + "(table 07129; Europris is about two-thirds of the category); Europris quarterly reports. Slopes control for "
  + "last quarter's sales growth, base effect, Easter and trading days; COVID-distorted quarters 2020Q1–23Q1 excluded. "
  + "p-values from calibrated randomisation tests.", { placeholder: "footer" });

s.addNotes(
  `Category slope over 2001-24: +${f2(D.full.slope)} (t ${D.full.t}, n ${D.full.n}). Sub-periods: `
  + per.map((p) => `${p.label} +${f2(p.slope)} (t ${p.t}, n ${p.n})`).join("; ")
  + `. Correlation of category sales growth with house-price growth one quarter earlier (non-COVID quarters): ${ev.corr_category}. `
  + `Europris LFL two quarters ahead: p ${pfmt(ev.eu_p_h2)}. Holdout 2024Q3-2026Q2 out-of-sample R2 vs benchmark: `
  + `next quarter ${ev.hold_lfl.h1_exclude} (COVID excluded) / ${ev.hold_lfl.h1_control} (COVID controlled); `
  + `two quarters ${ev.hold_lfl.h2_exclude} / ${ev.hold_lfl.h2_control}. Grade: moderate (strong in 25 years of `
  + `category data, thin on Europris's own ~10 years). Source: research/europris_predictors/README.md.`
);

(async () => {
  await pres.writeFile({ fileName: OUT });
  const themeJs = process.argv[2];
  if (themeJs) {
    const { applyTheme } = require(path.resolve(themeJs));
    await applyTheme(OUT, THEME);
  }
  console.log("written", OUT);
})();
