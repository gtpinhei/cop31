// V1.1: evidence labels, contributor attribution, full readout (article) view, cross-references,
// corrections, retractions and seven languages. Synthetic content only.
// node tests/test_v11.mjs   (needs jsdom: NODE_PATH=... or `cd tools && npm install`)
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { JSDOM } = require("jsdom");
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const read = n => JSON.parse(fs.readFileSync(path.join(ROOT, n), "utf8"));
const feed = read("data/feed.json");
let failed = 0;
const assert = (c, m) => { if (!c) { failed++; console.error("FAIL:", m); } else console.log("ok:", m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const res = (status, body) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });
const LANGS = ["en", "es", "fr", "ru", "zh", "ar"];
const FIELDS = ["headline", "summary", "what_happened", "what_changed", "why_it_matters", "watch_next", "open_questions"];
const FID = feed.items[0].id;

function entry(over = {}) {
  const e = {
    id: "2099-01-01-test-grid", status: "published", headline: "[TESTE] Grade voluntária", summary: "[TESTE] Resumo executivo.",
    theme: "Finanças", classification: "processo", verification: "fonte única", event_at: "2099-01-01",
    assessed_at: "2099-01-01T12:00+03:00", what_happened: "[TESTE] A presidência propôs a grade.", what_changed: "[TESTE] Mudou.",
    why_it_matters: "[TESTE] O autor avalia que importa.", watch_next: "[TESTE] Observar doadores.", open_questions: "[TESTE] Quem paga?",
    basis: { summary: "attributed", what_happened: "attributed", what_changed: "attributed", why_it_matters: "analysis", watch_next: "unverified" },
    actors: ["Presidência fictícia"], related: [FID],
    contributor: { display: "named", name: "Test Author", affiliation: "Example Institute", role: "observer" },
    sources: [{ title: "Readout", publisher: "Test Author", url: null, kind: "contributor", verified: true },
              { title: "Doc", publisher: "Example", url: "https://example.org/doc", kind: "official", verified: false }],
    approved_by: "Editor", approved_at: "2099-01-01T12:00+03:00", article: "2099-01-01-test-readout", i18n: {} };
  for (const l of LANGS) { e.i18n[l] = { method: l === "ru" ? "machine" : "human" }; for (const f of FIELDS) e.i18n[l][f] = `[${l}] ${e[f]}`; }
  return Object.assign(e, over);
}
function article(over = {}) {
  const a = { schema: 1, id: "2099-01-01-test-readout", entries: ["2099-01-01-test-grid"], status: "published",
    title: "[TESTE] Readout completo", standfirst: "[TESTE] Linha fina.", reporting_note: "[TESTE] Presença direta na coletiva.", event_at: "2099-01-01",
    blocks: [{ basis: "attributed", heading: "Relato", md: "[TESTE] A presidência disse **três** cenários.\n\n- item um\n- item dois" },
             { basis: "analysis", heading: "Avaliação", md: "[TESTE] Ver [documento](https://example.org/doc) e [mau](javascript:alert(1)) <img src=x onerror=alert(1)>" }],
    contributor: { display: "named", name: "Test Author", affiliation: "Example Institute", role: "observer" },
    sources: [{ title: "Readout", publisher: "Test Author", url: null, kind: "contributor", verified: false }],
    approved_by: "Editor", approved_at: "2099-01-01T12:00+03:00", i18n: {} };
  for (const l of LANGS) a.i18n[l] = { title: `[${l}] ${a.title}`, standfirst: `[${l}] ${a.standfirst}`, reporting_note: `[${l}] ${a.reporting_note}`, method: "machine-reviewed",
    blocks: a.blocks.map(b => ({ heading: `[${l}] ${b.heading}`, md: `[${l}] ${b.md}` })) };
  return Object.assign(a, over);
}

function boot({ today, articles = {}, privateDrafts, privateArticles = {}, lang, host, query } = {}) {
  const calls = [];
  const qs = [lang ? "lang=" + lang : "", query || ""].filter(Boolean).join("&");
  const dom = new JSDOM(html, { runScripts: "outside-only", url: (host || "https://cop31.grupotrie.com.br") + "/" + (qs ? "?" + qs : ""), pretendToBeVisual: true,
    beforeParse(w) {
      w.fetch = (u) => {
        u = String(u); calls.push(u);
        if (u.includes("data/feed.json")) return res(200, feed);
        if (u.includes("data/pulse.json")) return res(200, { schema: 1, accounts: [] });
        if (u.includes("data/today.json")) return res(200, today);
        const m = /data\/articles\/([a-z0-9-]+)\.json/.exec(u);
        if (m) return articles[m[1]] ? res(200, articles[m[1]]) : res(404, {});
        if (u.includes("__private__/drafts.json")) return privateDrafts ? res(200, privateDrafts) : res(404, {});
        const pm = /__private__\/articles\/([a-z0-9-]+)\.json/.exec(u);
        if (pm) return privateArticles[pm[1]] ? res(200, privateArticles[pm[1]]) : res(404, {});
        if (u.includes("i18n/")) return res(200, read("i18n/" + u.split("i18n/")[1].split("?")[0]));
        if (u.startsWith("https://public.api.bsky.app/")) return res(200, { feed: [] });
        return Promise.reject(new Error("unexpected fetch " + u));
      };
      w.scrollTo = () => {};
      Object.defineProperty(w.navigator, "language", { value: "pt-BR", configurable: true });
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {} });
    } });
  const w = dom.window;
  const script = [...w.document.querySelectorAll("script")].map(s => s.textContent).find(t => t.includes("i18n-core-begin"));
  w.eval(script);
  return { w, d: w.document, calls };
}
const go = async (w, h) => { w.location.hash = "#" + h; w.dispatchEvent(new w.Event("hashchange")); await sleep(80); };
const setLang = async (b, l) => { const s = b.d.getElementById("langSel"); s.value = l; s.dispatchEvent(new b.w.Event("change")); await sleep(120); };

// ---------- 1. card: evidence labels, attribution, cross-reference, sources without link
{
  const b = boot({ today: { schema: 1, entries: [entry()] }, articles: { "2099-01-01-test-readout": article() } });
  await sleep(80); await go(b.w, "hoje");
  const c = b.d.querySelector("#todayList article.ti");
  assert(c && c.querySelector("h4").textContent === "[TESTE] Grade voluntária", "published card renders");
  const badges = [...c.querySelectorAll(".ti-b")].map(x => x.className.split(" ")[1]);
  assert(["b-attributed", "b-analysis", "b-unverified"].every(k => badges.includes(k)), "each field shows its evidence label: " + badges.join(","));
  const why = [...c.querySelectorAll("dt")].find(dt => dt.textContent.startsWith("Por que importa"));
  assert(why && why.querySelector(".b-analysis") && why.querySelector(".b-analysis").textContent === "análise", "interpretation is labelled analysis, never fact");
  assert(!b.d.getElementById("todayLegend").hidden, "legend explains the four evidence categories");
  assert(/Test Author, Example Institute \(observador\)/.test(c.querySelector(".ti-contrib").textContent) && /não implica endosso/.test(c.querySelector(".ti-contrib").textContent), "named contributor with no-endorsement note");
  assert(c.querySelector(".ti-rel a") && c.querySelector(".ti-rel a").getAttribute("href") === feed.items[0].url, "cross-reference links the monitoring item");
  assert(/relato do colaborador, sem link público/.test(c.querySelector(".ti-src").textContent), "first-hand source shown without a fake link");
  assert(c.querySelector(".ti-art a").getAttribute("href") === "#hoje/leitura/2099-01-01-test-readout", "card links to the full readout");
  assert(/Perguntas em aberto/.test(c.textContent), "open questions shown");
}
// ---------- 2. anonymous contributor, corrections, retractions
{
  const e = entry({ contributor: { display: "anonymous", role: "analyst" }, sources: [{ title: "Readout", publisher: "Contribuição à curadoria (anônima)", url: null, kind: "contributor", verified: true }], corrections: [{ at: "2099-01-02T09:00+03:00", by: "Editor", note: "Valor corrigido." }], article: undefined });
  const b = boot({ today: { schema: 1, entries: [e], retractions: [{ id: "x", retracted_at: "2099-01-02T10:00+03:00", reason: "Fonte retirou a declaração." }] } });
  await sleep(80); await go(b.w, "hoje");
  const c = b.d.querySelector("#todayList article.ti");
  assert(/identificado pela editoria/.test(c.querySelector(".ti-contrib").textContent) && !/Test Author/.test(c.textContent), "anonymous attribution reveals no identity");
  assert(/Correção em 2 jan.*Valor corrigido/.test(c.querySelector(".ti-corr").textContent), "correction history is public");
  assert(!b.d.getElementById("todayRetr").hidden && /Fonte retirou/.test(b.d.getElementById("todayRetr").textContent), "retraction notice stays visible");
  assert(!c.querySelector(".ti-art"), "no readout link without a published article");
}
// ---------- 3. article view: blocks, labels, safe markdown, back link
{
  const b = boot({ today: { schema: 1, entries: [entry()] }, articles: { "2099-01-01-test-readout": article() } });
  await sleep(80); await go(b.w, "hoje/leitura/2099-01-01-test-readout"); await sleep(80);
  const a = b.d.getElementById("todayArticle");
  assert(!a.hidden && b.d.getElementById("todayList").hidden, "readout route shows the article in place of the list");
  assert(a.querySelector(".art-title").textContent === "[TESTE] Readout completo", "article title");
  const blocks = [...a.querySelectorAll(".art-block")];
  assert(blocks.length === 2 && blocks[0].classList.contains("b-attributed") && blocks[1].classList.contains("b-analysis"), "blocks keep reported vs analysis labels");
  assert(blocks[0].querySelector("strong") && blocks[0].querySelectorAll("li").length === 2, "markdown: bold and list");
  const links = [...blocks[1].querySelectorAll("a")].map(x => x.getAttribute("href"));
  assert(links.length === 1 && links[0] === "https://example.org/doc", "only https links become links");
  assert(!blocks[1].querySelector("img") && /&lt;img|<img/.test(blocks[1].innerHTML) && blocks[1].innerHTML.includes("&lt;img"), "raw HTML is escaped, never executed");
  assert(a.querySelector(".art-back a").getAttribute("href") === "#hoje", "back to Today");
  assert(/Nota de apuração: \[TESTE\] Presença direta na coletiva\./.test(a.querySelector(".art-rn").textContent), "contributor's reporting note shown with the readout");
  await go(b.w, "hoje");
  assert(b.d.getElementById("todayArticle").hidden && !b.d.getElementById("todayList").hidden, "leaving the readout restores the list");
  await go(b.w, "hoje/leitura/2099-01-01-missing");
  await sleep(80);
  assert(/não está disponível/.test(b.d.getElementById("todayArticle").textContent), "unknown readout shows a clear message");
}
// ---------- 4. seven languages: card and article
{
  const b = boot({ today: { schema: 1, entries: [entry()] }, articles: { "2099-01-01-test-readout": article() } });
  await sleep(80); await go(b.w, "hoje");
  for (const l of LANGS) {
    await setLang(b, l); await go(b.w, "hoje");
    const c = b.d.querySelector("#todayList article.ti");
    const lab = c.querySelector(".ti-b.b-analysis").textContent;
    assert(c.querySelector("h4").textContent === `[${l}] [TESTE] Grade voluntária` && lab && lab !== "análise" || (l === "es" && lab === "análisis"), `${l}: card translated, evidence label localized (${lab})`);
    assert(l !== "ru" || /машин/i.test(c.querySelector(".ti-note").textContent), `${l}: machine translation disclosed`);
    await go(b.w, "hoje/leitura/2099-01-01-test-readout"); await sleep(60);
    const a = b.d.getElementById("todayArticle");
    assert(a.querySelector(".art-title").textContent === `[${l}] [TESTE] Readout completo` && a.querySelectorAll(".art-block").length === 2 && a.querySelector(".art-rn").textContent.includes(`[${l}]`), `${l}: article and reporting note translated`);
    if (l === "ar") assert(b.d.documentElement.dir === "rtl", "ar: right-to-left");
  }
  await setLang(b, "pt");
}
// ---------- 5. missing translation is disclosed, not hidden
{
  const e = entry(); delete e.i18n.fr; e.i18n_pending = ["fr"];
  const b = boot({ today: { schema: 1, entries: [e] } });
  await sleep(80); await setLang(b, "fr"); await go(b.w, "hoje");
  const c = b.d.querySelector("#todayList article.ti");
  assert(c.getAttribute("lang") === "pt-BR" && c.querySelector(".ti-note") && c.querySelector("h4").textContent === "[TESTE] Grade voluntária", "fr pending: Portuguese original shown with a notice");
}
// ---------- 6. drafts and private readouts: never on the public host
{
  const drafts = { schema: 1, entries: [entry({ id: "d1", status: "draft", headline: "Rascunho privado" })] };
  const priv = { "2099-01-01-test-readout": article({ status: "draft", title: "Readout privado" }) };
  let b = boot({ today: { schema: 1, entries: [] }, privateDrafts: drafts, privateArticles: priv, query: "preview=1" });
  await sleep(80); await go(b.w, "hoje"); await go(b.w, "hoje/leitura/2099-01-01-test-readout"); await sleep(80);
  assert(!b.calls.some(u => u.includes("__private__")) && !b.d.body.textContent.includes("Rascunho privado") && !b.d.body.textContent.includes("Readout privado"),
    "public host with ?preview=1 never requests or shows private material");
  b = boot({ today: { schema: 1, entries: [] }, privateDrafts: drafts, privateArticles: priv, query: "preview=1", host: "http://127.0.0.1:8000" });
  await sleep(80); await go(b.w, "hoje");
  assert([...b.d.querySelectorAll("#todayList h4")].some(h => h.textContent === "Rascunho privado"), "local preview shows private drafts");
  await go(b.w, "hoje/leitura/2099-01-01-test-readout"); await sleep(80);
  assert(/Readout privado/.test(b.d.getElementById("todayArticle").textContent) && b.d.querySelector("#todayArticle .ti-tag.draft"), "local preview shows a private readout, marked as draft");
}
// ---------- 7. unapproved content in the public file is still filtered
{
  const b = boot({ today: { schema: 1, entries: [entry({ approved_by: "" }), entry({ id: "x2", status: "draft", headline: "Vazou" })] } });
  await sleep(80); await go(b.w, "hoje");
  assert(b.d.querySelectorAll("#todayList article.ti").length === 0 && !b.d.body.textContent.includes("Vazou"), "unapproved or draft entries in today.json are not rendered");
}
// ---------- 8. mobile-first CSS rules exist for the new components
{
  const css = [...new JSDOM(html).window.document.querySelectorAll("style")].map(s => s.textContent).join("\n");
  assert(/\.art\{max-width:44em\}/.test(css) && /\.art-block p,\.art-block li\{[^}]*overflow-wrap:anywhere/.test(css), "readout text wraps on narrow screens");
  assert(/\.ti\{[^}]*min-width:0/.test(css), "cards shrink on narrow screens");
}

console.log(failed ? `${failed} CHECK(S) FAILED` : "ALL OK");
process.exit(failed ? 1 : 0);
