// Headless check of the language layer: node tools/test_i18n.mjs
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { JSDOM } = require("jsdom");
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const pt = JSON.parse(fs.readFileSync(path.join(ROOT, "i18n", "pt.json"), "utf8"));
const feed = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "feed.json"), "utf8"));

// fake dictionary: every string prefixed with [en], arrays mapped, markup preserved
const fake = {};
for (const [k, v] of Object.entries(pt)) {
  if (Array.isArray(v)) fake[k] = v.map(x => "[en]" + x);
  else if (/^<[a-z]/i.test(v) && /^<([a-z0-9]+)[^>]*>.*<\/\1>$/is.test(v)) fake[k] = v.replace(/>([^<]*[A-Za-zÀ-ÿ][^<]*)</g, (m, t) => ">[en]" + t + "<");
  else fake[k] = "[en]" + v;
}
const realLang = process.argv[2]; // optional: test a real i18n/<lang>.json
const LANGCODE = realLang || "en";
const dict = realLang ? JSON.parse(fs.readFileSync(path.join(ROOT, "i18n", realLang + ".json"), "utf8")) : fake;

const dom = new JSDOM(html, { runScripts: "outside-only", url: "https://cop31.grupotrie.com.br/", pretendToBeVisual: true,
  beforeParse(w) {
    w.fetch = (u) => Promise.resolve({ ok: true, json: () => Promise.resolve(String(u).includes("feed.json") ? feed : dict) });
    w.scrollTo = () => {};
    Object.defineProperty(w.navigator, "language", { value: "pt-BR", configurable: true });
    w.matchMedia = () => ({ matches: false, addListener(){}, removeListener(){} });
  } });
const w = dom.window, d = w.document;
const script = [...d.querySelectorAll("script")].map(s => s.textContent).find(t => t.includes("i18n-core-begin"));
w.eval(script);
const sleep = ms => new Promise(r => setTimeout(r, ms));
await sleep(50);
const txt = sel => (d.querySelector(sel)?.textContent || "").trim();
const assert = (c, m) => { if (!c) { console.error("FAIL:", m); process.exitCode = 1; } else console.log("ok:", m); };

assert(d.documentElement.lang === "pt-BR", "starts in Portuguese");
const ptNav = txt(".nav-item[data-view=posicoes] .nav-label");
const ptStatus = txt("#feedStatusText");
assert(/fontes checadas/.test(ptStatus), "feed status rendered in Portuguese: " + ptStatus.slice(0, 60));

d.getElementById("langSel").value = realLang || "en";
d.getElementById("langSel").dispatchEvent(new w.Event("change"));
await sleep(80);
assert(d.documentElement.lang !== "pt-BR", "lang attribute switched: " + d.documentElement.lang);
const enNav = txt(".nav-item[data-view=posicoes] .nav-label");
assert(enNav !== ptNav, "nav label translated: " + enNav);
assert(txt("#feedStatusText") !== ptStatus && txt("#feedStatusText").length > 10, "feed status re-rendered: " + txt("#feedStatusText").slice(0, 70));
const firstCell = txt("#posBody tr td");
assert(firstCell.length > 0, "positions table rendered: " + firstCell);
const optText = d.querySelector("#fTema option:nth-child(2)")?.textContent;
assert(!!optText, "topic filter option: " + optText);
assert(d.getElementById("q").placeholder !== "Buscar no guia", "placeholder translated: " + d.getElementById("q").placeholder);
assert(txt("#countdown").length > 0, "countdown: " + txt("#countdown"));
assert(!!d.getElementById("navFeedCount") && d.getElementById("navFeedCount").textContent !== "", "feed badge kept alive: " + d.getElementById("navFeedCount").textContent);
const dayHeader = txt("#feedList .feed-day");
assert(dayHeader.length > 0, "feed day header: " + dayHeader);
{ // feed summaries follow the viewed language
  const sums = [...d.querySelectorAll("#feedList .fi-sum")].map(e => e.textContent);
  const withI18n = feed.items.filter(i => i.summary_i18n && i.summary_i18n[LANGCODE]).map(i => i.summary_i18n[LANGCODE]);
  assert(sums.length > 0 && sums.every(t => withI18n.includes(t)), "feed summaries in " + LANGCODE + ": " + (sums[0] || "").slice(0, 50));
}
// search still works (positions view)
w.location.hash = "#posicoes"; w.dispatchEvent(new w.Event("hashchange")); await sleep(10);
d.getElementById("q").value = "adapt"; d.getElementById("q").dispatchEvent(new w.Event("input"));
await sleep(10);
assert(d.querySelectorAll("#posBody tr").length < 341 && d.querySelectorAll("#posBody tr").length > 0, "search filters table: " + d.querySelectorAll("#posBody tr").length + " rows");
d.getElementById("q").value = ""; d.getElementById("q").dispatchEvent(new w.Event("input"));

if (realLang) {
  // coverage: how many static units still show their Portuguese source
  const missing = Object.keys(pt).filter(k => dict[k] == null).length;
  assert(missing === 0, `all ${Object.keys(pt).length} keys translated (missing ${missing})`);
  assert(d.documentElement.dir === (realLang === "ar" ? "rtl" : "ltr"), "text direction " + d.documentElement.dir);
}
// back to Portuguese
d.getElementById("langSel").value = "pt"; d.getElementById("langSel").dispatchEvent(new w.Event("change"));
await sleep(30);
assert(txt(".nav-item[data-view=posicoes] .nav-label") === ptNav, "back to Portuguese nav: " + txt(".nav-item[data-view=posicoes] .nav-label"));
assert(d.documentElement.dir === "ltr" && d.documentElement.lang === "pt-BR", "dir/lang restored");
assert(JSON.parse(w.localStorage.getItem("cop31nav")).lang === "pt", "choice persisted");
console.log(process.exitCode ? "SOME CHECKS FAILED" : "ALL OK");
