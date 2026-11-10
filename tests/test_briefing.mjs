// Today page, automated layer (data/briefing.json): sections, empty states, multilingual descriptions, RTL,
// stale editions, separation from human-approved contributions, and the Social Pulse still working. Synthetic data.
// node tests/test_briefing.mjs   (needs jsdom: NODE_PATH=... or `cd tools && npm install`)
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { JSDOM } = require("jsdom");
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const read = n => JSON.parse(fs.readFileSync(path.join(ROOT, n), "utf8"));
let failed = 0;
const assert = (c, m) => { if (!c) { failed++; console.error("FAIL:", m); } else console.log("ok:", m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const res = (status, body) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

const lead = (i, over = {}) => ({ id: "x-" + i, title: "[TEST] Headline " + i, url: "https://www.example.org/story-" + i, publisher: "Pub " + i,
  published: "2099-11-10", content_type: "reporting", kind: "publication", tracks: ["Finanças"], description: "[TESTE] Descrição " + i,
  description_i18n: { en: "[TEST] Description " + i, ar: "[اختبار] وصف " + i }, description_i18n_method: "machine", ...over });
const story = (i, sec, over = {}, related = []) => ({ id: "st-" + i, section: sec, score: 1, lead: lead(i, over), related, publishers: ["Pub " + i] });
function brief(over = {}) {
  return { schema: 1, edition: "2099-11-10", generated_at: "2099-11-10T09:58+03:00", window: { from: "2099-11-07", to: "2099-11-10" },
    collection: { web_round: "2099-11-10T03:00:00-03:00", social_round: "2099-11-10T03:30:00-03:00", stale: false },
    coverage: { candidates: 5, stories: 4, top: 2, publishers: ["Pub 1", "Pub 2", "Pub 3"], access_gaps: [{ publisher: "Blocked Pub", outcome: "blocked" }] },
    sections: { essential: [story(1, "negotiations", {}, [lead(9, { publisher: "Also Pub", url: "https://www.example.org/also" })]), story(2, "action")],
      negotiations: [story(3, "negotiations")], action: [], civil: [story(4, "civil", { content_type: "advocacy" })] }, ...over };
}
const human = { id: "2099-01-01-human", status: "published", headline: "[TESTE] Contribuição humana", summary: "[TESTE] Resumo.", theme: "Finanças",
  classification: "processo", verification: "fonte única", event_at: "2099-01-01", assessed_at: "2099-01-01T12:00+03:00", what_happened: "[TESTE] x",
  sources: [{ title: "Doc", publisher: "Example", url: "https://example.org/doc", kind: "official", verified: true }], approved_by: "Editor", approved_at: "2099-01-01T12:00+03:00" };

function boot({ briefing, today = { schema: 1, entries: [] }, lang } = {}) {
  const calls = [];
  const dom = new JSDOM(html, { runScripts: "outside-only", url: "https://cop31.grupotrie.com.br/" + (lang ? "?lang=" + lang : "") + "#hoje", pretendToBeVisual: true,
    beforeParse(w) {
      w.fetch = (u) => {
        u = String(u); calls.push(u);
        if (u.includes("data/briefing.json")) return briefing === undefined ? res(404, {}) : res(200, briefing);
        if (u.includes("data/today.json")) return res(200, today);
        if (u.includes("data/feed.json")) return res(200, { schema: 1, items: [], tracks: [] });
        if (u.includes("data/pulse.json")) return res(200, { schema: 1, accounts: [{ platform: "bluesky", handle: "example.org", institution: "Example", priority: "A", verified: true }] });
        if (u.includes("data/newsletter.json")) return res(200, { mode: "off" });
        if (u.includes("i18n/")) return res(200, read("i18n/" + u.split("i18n/")[1].split("?")[0]));
        if (u.startsWith("https://public.api.bsky.app/")) return res(200, { feed: [] });
        return res(404, {});
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
const sec = (d, k) => d.querySelector(`.brf-sec[data-sec="${k}"]`);

// 1. sections render, empty ones hidden, attribution and direct links, commons separate
{
  const b = boot({ briefing: brief(), today: { schema: 1, entries: [human] } }); await sleep(150);
  assert(!b.d.getElementById("brf").hidden, "briefing block shown");
  assert(!sec(b.d, "essential").hidden && sec(b.d, "essential").querySelectorAll(".brf-card").length === 2, "essential reading with two stories");
  assert(sec(b.d, "action").hidden, "empty section hidden, no filler");
  const a = sec(b.d, "essential").querySelector(".brf-card h4 a");
  assert(a.getAttribute("href") === "https://www.example.org/story-1" && a.target === "_blank" && a.rel === "noopener", "headline links straight to the source");
  assert(a.textContent === "[TEST] Headline 1", "original headline kept");
  assert(sec(b.d, "essential").querySelector(".brf-pub").textContent === "Pub 1", "publisher shown");
  assert(sec(b.d, "essential").querySelector(".brf-also a").textContent === "Also Pub", "other coverage of the same event grouped under the story");
  assert(sec(b.d, "civil").querySelector(".brf-t").textContent === "posicionamento", "advocacy labelled as a position");
  assert(!b.d.getElementById("commonsH").hidden && b.d.querySelector("#todayList article.ti h4").textContent === "[TESTE] Contribuição humana", "human-approved contributions shown separately under Da comunidade");
  assert(/Blocked Pub/.test(b.d.getElementById("brfNote").textContent), "known access gaps disclosed");
  assert(/Atualizado em/.test(b.d.getElementById("brfMeta").textContent) && /4 histórias/.test(b.d.getElementById("brfMeta").textContent), "last update and counts shown");
  assert(b.d.getElementById("todayEmpty").hidden, "no 'curation starts' placeholder when the briefing has stories");
  assert(!b.calls.some(u => u.includes("__private__")), "public page never asks for private drafts");
}

// 2. unapproved human entries stay hidden even with the automated layer on
{
  const draft = { ...human, id: "x-draft", headline: "[TESTE] Vazou", status: "draft" };
  const b = boot({ briefing: brief(), today: { schema: 1, entries: [draft] } }); await sleep(150);
  assert(!b.d.body.textContent.includes("Vazou") && b.d.getElementById("commonsH").hidden, "drafts never shown; commons heading hidden when nothing approved");
}

// 3. multilingual descriptions with machine-translation label; Arabic RTL; headline keeps its language
{
  const b = boot({ briefing: brief(), lang: "ar" }); await sleep(350);
  assert(b.d.documentElement.dir === "rtl", "Arabic page is right-to-left");
  const c = sec(b.d, "essential").querySelector(".brf-card");
  assert(c.querySelector(".brf-d").textContent === "[اختبار] وصف 1" && c.querySelector(".brf-d").getAttribute("dir") === "auto", "Arabic description, direction auto");
  assert(c.querySelector(".brf-mt") && c.querySelector("h4").getAttribute("dir") === "auto", "machine translation labelled; original headline isolated");
  assert(sec(b.d, "essential").querySelector(".brf-h").textContent === "قراءات أساسية", "section title translated");
  const e = boot({ briefing: brief(), lang: "en" }); await sleep(350);
  assert(sec(e.d, "essential").querySelector(".brf-d").textContent === "[TEST] Description 1", "English description");
  const z = boot({ briefing: brief({ sections: { essential: [story(1, "x", { description_i18n: {} })], negotiations: [], action: [], civil: [] } }), lang: "zh" }); await sleep(350);
  const zc = sec(z.d, "essential").querySelector(".brf-card");
  assert(zc.querySelector(".brf-d").getAttribute("lang") === "pt" && !zc.querySelector(".brf-mt"), "no translation: Portuguese description, honestly marked as such");
}

// 4. stale edition: banner, stories kept; empty fresh edition: honest message, sections hidden
{
  const b = boot({ briefing: brief({ collection: { stale: true, web_round: "2099-11-09T01:00:00-03:00" } }) }); await sleep(150);
  assert(!b.d.getElementById("brfStale").hidden && /12 horas/.test(b.d.getElementById("brfStale").textContent), "stale collection flagged");
  assert(sec(b.d, "essential").querySelectorAll(".brf-card").length === 2, "previous valid edition still shown");
  const e = boot({ briefing: brief({ sections: { essential: [], negotiations: [], action: [], civil: [] }, coverage: { publishers: [], access_gaps: [] } }) }); await sleep(150);
  assert([...e.d.querySelectorAll(".brf-sec")].every(s => s.hidden) && /Nenhuma reportagem/.test(e.d.getElementById("brfMeta").textContent), "empty edition says so plainly");
}

// 5. bad links filtered in the browser too; no briefing file: page falls back to the editorial view
{
  const bad = brief({ sections: { essential: [story(1, "x", { url: "javascript:alert(1)" }), story(2, "x")], negotiations: [], action: [], civil: [] } });
  const b = boot({ briefing: bad }); await sleep(150);
  assert(sec(b.d, "essential").querySelectorAll(".brf-card").length === 1 && !b.d.body.innerHTML.includes("javascript:alert"), "non-https link never rendered");
  const n = boot({}); await sleep(150);
  assert(n.d.getElementById("brf").hidden && !n.d.getElementById("todayEmpty").hidden, "without briefing.json the old empty state is unchanged");
}

// 6. Panorama teaser and Social Pulse keep working
{
  const b = boot({ briefing: brief() }); await sleep(150);
  b.w.location.hash = "#panorama"; b.w.dispatchEvent(new b.w.Event("hashchange")); await sleep(80);
  assert(!b.d.getElementById("todayTeaser").hidden && b.d.querySelectorAll("#todayTeaserList .brf-card").length === 2, "Panorama teaser shows the top stories");
  b.w.location.hash = "#pulso"; b.w.dispatchEvent(new b.w.Event("hashchange")); await sleep(250);
  assert(b.calls.some(u => u.includes("data/pulse.json")), "Social Pulse still loads its accounts");
}

// 7. hero copy: headline, subtitle, curation details collapsed, every language translated
{
  const exp = { pt: "Filtre o ruído. Acompanhe o que importa.", en: "Cut through the noise. Follow what matters.", es: "Menos ruido. Lo que de verdad importa.",
    fr: "Moins de bruit. L’essentiel, chaque jour.", ru: "Без информационного шума. Только главное.", zh: "拨开纷扰，紧盯要事。", ar: "بعيدًا عن الضجيج، تابع ما يهمّ." };
  for (const [l, h] of Object.entries(exp)) {
    const b = boot({ briefing: brief(), lang: l === "pt" ? undefined : l }); await sleep(l === "pt" ? 120 : 300);
    const hero = b.d.querySelector("#view-hoje .hoje-hero");
    assert(hero.querySelector(".hoje-h").textContent === h && hero.querySelector(".hoje-sub").textContent.length > 30, l + ": headline and subtitle");
    const how = hero.querySelector("details.hoje-how");
    assert(how && !how.open && how.querySelector("a[href='#pulso']") && how.querySelector("a[href='#atualizacoes']"), l + ": curation explanation collapsed, links to Pulso and Atualizações kept");
    if (l === "ar") assert(b.d.documentElement.dir === "rtl", "ar: right-to-left");
  }
  const b = boot({ briefing: brief() }); await sleep(120);
  assert(!b.d.querySelector("#view-hoje > p.intro"), "the long introduction is gone from the page body");
  assert(sec(b.d, "essential").querySelector(".brf-card h4 a").getAttribute("href").startsWith("https://"), "stories keep their source links");
}

if (failed) { console.error(failed + " failed"); process.exit(1); }
