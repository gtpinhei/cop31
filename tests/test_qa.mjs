// Regression tests for QA issues #2–#9 (independent browser QA of v1-launch, 8 Nov 2026).
// node tests/test_qa.mjs   (needs jsdom). Bluesky responses are saved fixtures; see tests/fixtures/README.md.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { JSDOM } = require("jsdom");
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const fx = n => JSON.parse(fs.readFileSync(path.join(ROOT, "tests", "fixtures", n), "utf8"));
const read = n => JSON.parse(fs.readFileSync(path.join(ROOT, n), "utf8"));
const feed = read("data/feed.json");
let failed = 0;
const assert = (c, m) => { if (!c) { failed++; console.error("FAIL:", m); } else console.log("ok:", m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const res = (status, body) => ({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

const PULSE = { schema: 2, bluesky_list: null, x_list: null, hidden: [], accounts: [
  { platform: "bluesky", handle: "enb.iisd.org", institution: "IISD / ENB", priority: "A", identity: "checked", verified: true },
  { platform: "bluesky", handle: "fixture-alpha.test", institution: "Fixture A", priority: "A", identity: "unverified", verified: false },
  { platform: "bluesky", handle: "fixture-beta.test", institution: "Fixture B", priority: "B", identity: "reported", verified: false },
  { platform: "bluesky", handle: "gone.fixture.test", institution: "Fixture gone", priority: "B", identity: "unverified", verified: false, health: "not_found", health_checked_at: "2026-11-08" },
  { platform: "x", handle: "AOSISChair", institution: "AOSIS", priority: "A", identity: "checked", verified: true },
  { platform: "x", handle: "UNFCCC", institution: "UNFCCC", priority: "A", identity: "checked", verified: true },
  { platform: "x", handle: "hiz_2026", institution: "Fixture B", priority: "A", identity: "reported", verified: false },
  { platform: "youtube", handle: "@UNClimateChangeEvents", institution: "UNFCCC", priority: "A", identity: "checked", verified: true, channel_id: "UCJlvsGJAR8NsiyLzuBf_cQg" } ] };

function boot({ bsky, lang, timeouts } = {}) {
  const calls = [];
  const dom = new JSDOM(html, { runScripts: "outside-only", url: "https://cop31.grupotrie.com.br/" + (lang ? "?lang=" + lang : ""), pretendToBeVisual: true,
    beforeParse(w) {
      w.fetch = (u, opt) => {
        u = String(u); calls.push(u);
        if (u.includes("data/feed.json")) return Promise.resolve(res(200, feed));
        if (u.includes("data/pulse.json")) return Promise.resolve(res(200, PULSE));
        if (u.includes("data/today.json")) return Promise.resolve(res(200, { schema: 1, entries: [] }));
        if (u.includes("i18n/")) return Promise.resolve(res(200, read("i18n/" + u.split("i18n/")[1].split("?")[0])));
        if (u.startsWith("https://public.api.bsky.app/")) return bsky(u, opt);
        return Promise.reject(new Error("unexpected fetch " + u));
      };
      w.scrollTo = () => {};
      Object.defineProperty(w.navigator, "language", { value: "pt-BR", configurable: true });
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {} });
      w.COP31_TEST_TIMEOUTS = timeouts || { bsky: 300, yt: 300 };
    } });
  const w = dom.window;
  w.eval([...w.document.querySelectorAll("script")].map(s => s.textContent).find(t => t.includes("i18n-core-begin")));
  return { w, d: w.document, calls };
}
const go = async (w, h) => { w.location.hash = "#" + h; w.dispatchEvent(new w.Event("hashchange")); await sleep(40); };
const txt = (d, s) => (d.querySelector(s)?.textContent || "").trim();
const choose = (w, el, v) => { el.value = v; el.dispatchEvent(new w.Event("change")); };
const actor = u => decodeURIComponent((/actor=([^&]+)/.exec(u) || [])[1] || "");
const FX = { "enb.iisd.org": "bsky_enb_p1.json", "fixture-alpha.test": "bsky_fixture_alpha.json", "fixture-beta.test": "bsky_fixture_beta.json" };
const page1 = u => (u.includes("cursor=") ? fx("bsky_enb_p2.json") : fx(FX[actor(u)]));
// synthetic long page for fixture-alpha.test (fictional .test account), 20 posts plus a cursor
const bigPage = (tag, cursor) => ({ cursor, feed: Array.from({ length: 20 }, (_, i) => ({ post: { uri: `at://did:plc:fixture-alpha/app.bsky.feed.post/${tag}${i}`, cid: "c" + i,
  author: { did: "did:plc:fixture-alpha", handle: "fixture-alpha.test", displayName: "Fixture account (test)" },
  record: { text: `[TEST FIXTURE] ${tag} ${i}`, createdAt: new Date(Date.UTC(2026, 10, 8, 9, 59 - i)).toISOString() }, indexedAt: new Date(Date.UTC(2026, 10, 8, 9, 59 - i)).toISOString() } })) });
// controllable Bluesky: every request waits until released, so tests decide the order
function gated() {
  const pending = [];
  const fn = (u) => new Promise(r => pending.push({ u, a: actor(u), r }));
  fn.release = (a, body) => { const i = pending.findIndex(p => p.a === a); if (i < 0) return false; const p = pending.splice(i, 1)[0]; p.r(res(200, body || page1(p.u))); return true; };
  fn.drain = async (a) => { for (let k = 0; k < 10; k++) { await sleep(10); if (!fn.release(a)) { await sleep(10); if (!pending.some(p => p.a === a)) return; } } };
  fn.pending = pending;
  return fn;
}
const authors = d => [...d.querySelectorAll("#pList .bp .bp-who span")].map(s => s.textContent.split(" ")[0].replace("@", ""));

// ---------- #2 rapid filter changes must end with the last selection only
{
  const g = gated(); const { w, d } = boot({ bsky: g });
  await go(w, "pulso"); await sleep(20);
  while (g.pending.length) { g.release(g.pending[0].a); await sleep(5); }
  await sleep(40);
  const sel = d.getElementById("pInst");
  choose(w, sel, "Fixture A"); await sleep(5);
  choose(w, sel, "IISD / ENB"); await sleep(5);
  await g.drain("enb.iisd.org");
  await g.drain("fixture-alpha.test"); await sleep(30);
  const au = authors(d);
  assert(sel.value === "IISD / ENB" && au.length > 0 && au.every(a => a === "enb.iisd.org"), "#2 A -> ENB with A answering last: only ENB posts (" + au.join(",") + ")");
  assert(/de 1 contas/.test(txt(d, "#pStatus")), "#2 status describes the final selection: " + txt(d, "#pStatus"));
  // A -> B -> C, out of order
  choose(w, sel, "Fixture A"); await sleep(5); choose(w, sel, "Fixture B"); await sleep(5); choose(w, sel, "IISD / ENB"); await sleep(5);
  await g.drain("enb.iisd.org"); await g.drain("fixture-beta.test"); await g.drain("fixture-alpha.test"); await sleep(30);
  assert(authors(d).every(a => a === "enb.iisd.org"), "#2 A -> B -> C out of order: only C's posts");
  // load more pending, then change institution
  choose(w, sel, "Fixture A"); await sleep(10);
  g.release("fixture-alpha.test", bigPage("p1-", "c1")); await sleep(40);
  const more = d.getElementById("pMore");
  assert(!more.hidden && d.querySelectorAll("#pList .bp").length === 15, "#2 Fixture A has more to show");
  more.click(); await sleep(10);                       // asks for page 2, held pending
  choose(w, sel, "IISD / ENB"); await sleep(10);
  await g.drain("enb.iisd.org");
  g.release("fixture-alpha.test", bigPage("p2-", null)); await sleep(40);   // stale 'load more' answer arrives last
  const au2 = authors(d);
  assert(au2.length > 0 && au2.every(a => a === "enb.iisd.org") && /de 1 contas/.test(txt(d, "#pStatus")) && !more.disabled,
    "#2 stale 'load more' answer does not replace the new selection (" + [...new Set(au2)].join(",") + ")");
  // priority-B checkbox flipped mid-flight
  choose(w, sel, ""); await sleep(5);
  const all = d.getElementById("pAll"); all.checked = true; all.dispatchEvent(new w.Event("change")); await sleep(10);
  for (let k = 0; k < 30 && g.pending.length; k++) { g.release(g.pending[g.pending.length - 1].a); await sleep(10); }
  await sleep(60);
  assert(/de 3 contas/.test(txt(d, "#pStatus")), "#2 priority-B change applies to the final load: " + txt(d, "#pStatus"));
}

// ---------- #3 bounded, distinguishable failure states
async function stateFor(resp, wait = 450) {
  const { w, d, calls } = boot({ bsky: () => resp() });
  await go(w, "pulso"); await sleep(wait);
  return { d, w, calls, status: txt(d, "#pStatus"), err: d.getElementById("pStatus").className.includes("err"), retry: !d.getElementById("pRetry").hidden, cards: d.querySelectorAll("#pList .pc").length };
}
{
  let s = await stateFor(() => Promise.resolve({ ok: true, status: 200, json: () => new Promise(() => {}) }));
  assert(s.err && /demorou demais/.test(s.status) && s.retry && s.cards === 2, "#3 stalled body ends in timeout with retry and profile links: " + s.status);
  s = await stateFor(() => new Promise(() => {}));
  assert(s.err && /demorou demais/.test(s.status) && s.retry, "#3 delayed headers end in timeout");
  s = await stateFor(() => Promise.resolve({ ok: true, status: 200, json: () => Promise.reject(new SyntaxError("Unexpected token")) }));
  assert(s.err && /resposta inválida/.test(s.status) && s.retry && s.cards === 2, "#3 malformed JSON is an error, not an empty feed: " + s.status);
  s = await stateFor(() => Promise.resolve(res(200, {})));
  assert(s.err && /resposta inválida/.test(s.status), "#3 HTTP 200 {} is an invalid response");
  s = await stateFor(() => Promise.resolve(res(429, fx("bsky_ratelimit.json"))));
  assert(s.err && /limitou as consultas/.test(s.status) && !s.retry && s.cards === 2, "#3 429: rate-limit state, profile links, no immediate retry");
  s = await stateFor(() => Promise.resolve(res(200, { feed: [] })));
  assert(!s.err && s.status === "Nenhum post recente destas contas." && !s.retry && s.cards === 0, "#3 genuine empty feed stays an empty success");
  // partial failure keeps successful streams and names the reason
  s = await stateFor(u => (actor(u) === "enb.iisd.org" ? Promise.resolve(res(200, page1(u))) : Promise.resolve({ ok: true, status: 200, json: () => Promise.reject(new SyntaxError("x")) })));
  const s2 = await (async () => { const { w, d } = boot({ bsky: u => (actor(u) === "enb.iisd.org" ? Promise.resolve(res(200, page1(u))) : Promise.resolve({ ok: true, status: 200, json: () => Promise.reject(new SyntaxError("x")) })) });
    await go(w, "pulso"); await sleep(200); return { st: txt(d, "#pStatus"), n: d.querySelectorAll("#pList .bp").length, retry: !d.getElementById("pRetry").hidden }; })();
  assert(s2.n === 1 && /fixture-alpha\.test \(resposta inválida\)/.test(s2.st) && s2.retry, "#3 partial failure keeps good posts and names the bad source: " + s2.st);
  // retry recovers
  let n = 0;
  const { w, d } = boot({ bsky: u => (++n <= 2 ? Promise.resolve(res(200, {})) : Promise.resolve(res(200, fx(FX[actor(u)])))) });
  await go(w, "pulso"); await sleep(200);
  d.getElementById("pRetry").click(); await sleep(200);
  assert(d.querySelectorAll("#pList .bp").length > 0 && !d.getElementById("pStatus").className.includes("err"), "#3 retry after an invalid response recovers");
}

// ---------- #4 identity status on native Bluesky cards
{
  const { w, d } = boot({ bsky: u => Promise.resolve(res(200, page1(u))) });
  await go(w, "pulso"); await sleep(60);
  const all = d.getElementById("pAll"); all.checked = true; all.dispatchEvent(new w.Event("change")); await sleep(150);
  const card = t => [...d.querySelectorAll("#pList .bp")].find(b => b.textContent.includes(t));
  const alpha = card("escaping check");
  assert(alpha && /não verificado/.test(alpha.querySelector(".bp-who").textContent), "#4 unverified watchlist author shows a warning");
  const enb = card("Montreal Protocol");
  assert(enb && !enb.querySelector(".bp-who .badge") && /repostado por Fixture account \(test\)\s*não verificado/.test(enb.querySelector(".bp-ctx").textContent),
    "#4 checked author keeps no badge while the unverified reposter is flagged (no inheritance)");
  const outsider = card("outside the watchlist");
  assert(outsider && /conta fora da lista monitorada/.test(outsider.querySelector(".bp-who").textContent) && /identidade citada por terceiros/.test(outsider.querySelector(".bp-ctx").textContent),
    "#4 author outside the watchlist is 'unknown'; reported reposter keeps its own status");
  const quote = card("quoting an outsider");
  assert(quote && /conta fora da lista monitorada/.test(quote.querySelector(".bp-quote").textContent), "#4 quoted outsider is marked unknown");
  assert(card("beta newest post")?.querySelector(".badge.id-reported"), "#4 reported identity is distinct from unverified");
  d.querySelector('#pTabs [data-p="x"]').click(); await sleep(20);
  assert(/identidade citada por terceiros/.test(txt(d, "#xCards")), "#4 same identity wording on X cards");
  const out = read("data/pulse.json");
  const ch = out.accounts.find(a => a.handle === "chesc.bsky.social"), ca = out.accounts.find(a => a.handle === "climateanalytics.bsky.social"), rk = out.accounts.find(a => a.handle === "rkyte365.bsky.social");
  assert(ch.identity === "reported" && ch.verified === false && ch.identity_basis === "reportado", "#4 export keeps 'reported' distinct from checked");
  assert(ca.identity === "unverified" && /resolver/.test(ca.identity_basis), "#4 unresolved handle is not treated as checked");
  assert(rk.identity === "unverified", "#4 Rachel Kyte's handle stays unverified");
}

// ---------- #5 X selector stays valid and Load never silently no-ops
{
  const { w, d } = boot({ bsky: () => Promise.resolve(res(200, { feed: [] })) });
  await go(w, "pulso"); await sleep(40);
  d.querySelector('#pTabs [data-p="x"]').click(); await sleep(20);
  const xs = d.getElementById("xSel"), sel = d.getElementById("pInst");
  xs.value = "https://x.com/AOSISChair";
  d.getElementById("xStatus").textContent = "stale status";
  choose(w, sel, "UNFCCC"); await sleep(20);
  assert(xs.value === "https://x.com/UNFCCC" && xs.selectedIndex === 0 && !d.getElementById("xLoad").disabled, "#5 AOSIS -> UNFCCC selects @UNFCCC (value " + xs.value + ", index " + xs.selectedIndex + ")");
  assert(txt(d, "#xStatus") === "" && d.getElementById("xFrame").innerHTML === "", "#5 old embed/status cleared on institution change");
  d.getElementById("xLoad").click(); await sleep(10);
  assert(d.querySelector('#xFrame a.twitter-timeline[href="https://x.com/UNFCCC"]') && /Carregando timeline/.test(txt(d, "#xStatus")), "#5 Load makes an attempt for the selected account");
  choose(w, sel, "IISD / ENB"); await sleep(20);
  assert(xs.disabled && d.getElementById("xLoad").disabled && /Nenhuma conta desta plataforma/.test(txt(d, "#xCards")), "#5 institution without X account: explicit empty state, Load disabled");
  assert(!/os posts existem|é restrição do X/.test(d.getElementById("pPanelX").textContent), "#5 no categorical claims about why a timeline is empty");
}

// ---------- #6 search reads the displayed language and loaded content; explicit no-results
{
  const LANGS = ["pt", "en", "es", "fr", "ru", "zh", "ar"];
  for (const l of LANGS) {
    const { w, d } = boot({ bsky: () => Promise.resolve(res(200, { feed: [] })), lang: l === "pt" ? undefined : l });
    await sleep(200);
    const title = txt(d, "#view-panorama h2.view-title");
    const words = title.split(/[\s:：，,،()«»"“”]+/).filter(x => x.length >= (l === "zh" ? 2 : 5));
    const term = l === "zh" ? title.replace(/[^一-鿿]/g, "").slice(0, 2) : words.sort((a, b) => b.length - a.length)[0];
    const q = d.getElementById("q"); q.value = term; q.dispatchEvent(new w.Event("input"));
    const nav = d.querySelector('.nav-item[data-view="panorama"]');
    assert(!nav.classList.contains("dim") && +nav.querySelector(".nav-hits").textContent > 0 && !d.getElementById("qStatus").hidden, `#6 [${l}] term from the translated Overview ("${term}") finds Overview`);
    q.value = "zzqqxxnotaword"; q.dispatchEvent(new w.Event("input"));
    assert(!d.getElementById("qStatus").hidden && txt(d, "#qStatus").includes("zzqqxxnotaword") && [...d.querySelectorAll(".nav-item")].every(a => a.classList.contains("dim")), `#6 [${l}] explicit no-results message`);
  }
  // language switch invalidates; loaded feed text is searchable
  const { w, d } = boot({ bsky: () => Promise.resolve(res(200, { feed: [] })) });
  await sleep(150);
  const q = d.getElementById("q"); q.value = "diferente"; q.dispatchEvent(new w.Event("input"));
  const pan = () => +d.querySelector('.nav-item[data-view="panorama"] .nav-hits').textContent;
  const before = pan();
  d.getElementById("langSel").value = "en"; d.getElementById("langSel").dispatchEvent(new w.Event("change")); await sleep(150);
  assert(before > 0 && pan() < before, `#6 switching language re-counts hits (pt ${before} -> en ${pan()})`);
  const title = feed.items.find(i => i.kind !== "post").title.split(/\s+/).filter(x => x.length > 6)[0];
  q.value = title; q.dispatchEvent(new w.Event("input"));
  assert(+d.querySelector('.nav-item[data-view="atualizacoes"] .nav-hits').textContent > 0, `#6 loaded monitoring items are searchable ("${title}")`);
}

// ---------- #7 English topic labels and localized search name
{
  const { w, d } = boot({ bsky: () => Promise.resolve(res(200, { feed: [] })), lang: "en" });
  await sleep(200); await go(w, "atualizacoes");
  const chips = [...d.querySelectorAll("#ffTracks .chip")].map(c => c.textContent);
  assert(chips.some(c => /^Finance/.test(c)) && !chips.some(c => /^Finanças/.test(c)), "#7 English track filters are English: " + chips.slice(0, 3).join(" | "));
  const al = d.getElementById("q").getAttribute("aria-label");
  assert(al && al !== "Buscar no guia" && /Search/.test(al), "#7 search accessible name follows the language: " + al);
}

// ---------- #8 old posts show the year; unavailable accounts are coverage gaps; empty platform states
{
  const { w, d, calls } = boot({ bsky: u => Promise.resolve(res(200, page1(u))) });
  await go(w, "pulso"); await sleep(40);
  const all = d.getElementById("pAll"); all.checked = true; all.dispatchEvent(new w.Event("change")); await sleep(150);
  const old = [...d.querySelectorAll("#pList .bp")].find(b => b.textContent.includes("from last year"));
  const yr = new Date().getFullYear() !== 2025;
  assert(old && (!yr || /2025/.test(old.querySelector("time").textContent)), "#8 a post from a previous year shows the year: " + (old && old.querySelector("time").textContent));
  assert(!calls.some(u => u.includes("gone.fixture.test")) && /contas indisponíveis.*gone\.fixture\.test/.test(txt(d, "#pStatus")), "#8 account not found at last check is listed as a gap, not requested");
  choose(w, d.getElementById("pInst"), "AOSIS"); await sleep(40);
  assert(/Nenhuma conta desta plataforma/.test(txt(d, "#pStatus")), "#8 institution without a Bluesky account: explicit state");
  d.querySelector('#pTabs [data-p="instagram"]').click(); await sleep(20);
  assert(/Nenhuma conta desta plataforma/.test(txt(d, "#igCards")), "#8 Instagram empty state");
}

// ---------- #9 YouTube loading message clears on load; bounded fallback with retry
{
  const { w, d } = boot({ bsky: () => Promise.resolve(res(200, { feed: [] })) });
  await go(w, "pulso"); await sleep(30);
  d.querySelector('#pTabs [data-p="youtube"]').click(); await sleep(10);
  d.querySelector("#ytCards button[data-yt]").click(); await sleep(5);
  const wrap = d.querySelector("#ytCards .yt-wrap"), msg = d.querySelector("#ytCards .yt-load");
  assert(wrap.getAttribute("aria-busy") === "true" && !msg.hidden, "#9 loading state while the player frame loads");
  d.querySelector("#ytCards iframe").dispatchEvent(new w.Event("load")); await sleep(5);
  assert(msg.hidden && !wrap.hasAttribute("aria-busy") && d.querySelector("#ytCards .yt-fb a"), "#9 loading text removed on load; channel link kept");
  const b2 = boot({ bsky: () => Promise.resolve(res(200, { feed: [] })) });
  await go(b2.w, "pulso"); await sleep(30);
  b2.d.querySelector('#pTabs [data-p="youtube"]').click(); await sleep(10);
  b2.d.querySelector("#ytCards button[data-yt]").click(); await sleep(400);
  const m2 = b2.d.querySelector("#ytCards .yt-load");
  assert(!m2.hidden && /não respondeu/.test(m2.textContent) && m2.querySelector("button"), "#9 no load event: bounded 'did not respond' state with retry");
  m2.querySelector("button").click(); await sleep(5);
  assert(b2.d.querySelectorAll("#ytCards iframe").length === 1, "#9 retry keeps one player per card");
}

// ---------- Release blocker A: language switch with a nonempty feed and an active pagination cursor
{
  const dict = l => read("i18n/" + l + ".json");
  const PT = { "j:pOpen": "Abrir no Bluesky", "j:unv": "não verificado" };
  const want = (l, k) => (l === "pt" ? PT[k] : dict(l)[k]);
  const setLang = async (w, d, l) => { d.getElementById("langSel").value = l; d.getElementById("langSel").dispatchEvent(new w.Event("change")); await sleep(120); };
  const { w, d, calls } = boot({ lang: "en", bsky: u => Promise.resolve(res(200, u.includes("cursor=") ? bigPage("p2-", null) : bigPage("p1-", "c1"))) });
  await sleep(150); await go(w, "pulso"); await sleep(20);
  choose(w, d.getElementById("pInst"), "Fixture A"); await sleep(120);
  const n0 = calls.filter(u => u.includes("bsky.app")).length;
  assert(d.querySelectorAll("#pList .bp").length === 15 && !d.getElementById("pMore").hidden, "A: 15 posts shown with a next-page cursor pending");
  const check = l => {
    const cards = [...d.querySelectorAll("#pList .bp")];
    const opens = cards.map(c => c.querySelector(".bp-foot a").textContent);
    const badges = cards.map(c => (c.querySelector(".bp-who .badge") || {}).textContent);
    return cards.length === 15 && opens.every(t => t === want(l, "j:pOpen")) && badges.every(t => t === want(l, "j:unv"));
  };
  assert(check("en"), "A: cards and identity warnings in English");
  for (const l of ["ar", "en", "es", "fr", "ru", "zh", "ar", "pt"]) {
    await setLang(w, d, l);
    assert(check(l) && (l !== "ar" || d.documentElement.dir === "rtl"), `A: switch to ${l}: 15 cards, link and warning re-rendered in ${l}`);
  }
  assert(calls.filter(u => u.includes("bsky.app")).length === n0, "A: language switches made no new Bluesky requests");
  assert(!d.getElementById("pMore").hidden, "A: pagination still available after switching");
  // switching while the first page is still loading: status relabelled, posts drawn in the new language
  const g = gated(); const b2 = boot({ lang: "en", bsky: g });
  await sleep(150); await go(b2.w, "pulso"); await sleep(20);
  await setLang(b2.w, b2.d, "ar");
  const loadingAr = dict("ar")["j:pLoading"].split("{n}")[0].trim();
  assert(txt(b2.d, "#pStatus").startsWith(loadingAr.slice(0, 6)), "A: loading status relabelled while loading: " + txt(b2.d, "#pStatus"));
  for (let k = 0; k < 20 && g.pending.length; k++) { g.release(g.pending[0].a); await sleep(10); }
  await sleep(60);
  const first = b2.d.querySelector("#pList .bp .bp-foot a");
  assert(first && first.textContent === dict("ar")["j:pOpen"], "A: posts drawn after loading use the new language");
}

// ---------- Release blocker B: a failed 'load more' keeps the posts already shown
{
  let fail503 = true; const seen = [];
  const bsky = u => { seen.push(u);
    if (!u.includes("cursor=")) return Promise.resolve(res(200, bigPage("p1-", "c1")));
    if (fail503) return Promise.resolve({ ok: false, status: 503, json: () => Promise.reject(new SyntaxError("html")) });
    return Promise.resolve(res(200, bigPage("p2-", null))); };
  const { w, d } = boot({ bsky });
  await go(w, "pulso"); await sleep(20);
  choose(w, d.getElementById("pInst"), "Fixture A"); await sleep(120);
  assert(d.querySelectorAll("#pList .bp").length === 15, "B: 15 cards before load more");
  d.getElementById("pMore").click(); await sleep(120);
  const cards = d.querySelectorAll("#pList .bp").length, fallbacks = d.querySelectorAll("#pList .pc").length;
  const err = d.getElementById("pMoreErr"), retry = d.getElementById("pMoreRetry");
  assert(cards === 15 && fallbacks === 0, `B: HTTP 503 on load more keeps the 15 cards (cards ${cards}, fallback cards ${fallbacks})`);
  assert(!err.hidden && /Não foi possível carregar mais posts \(erro de rede\)/.test(err.textContent) && !retry.hidden && d.getElementById("pMore").hidden,
    "B: localized pagination error with a retry action: " + err.textContent);
  assert(!d.getElementById("pStatus").className.includes("err") && /15 posts/.test(txt(d, "#pStatus")), "B: main status still reports the loaded posts");
  fail503 = false;
  const before = seen.length;
  retry.click(); await sleep(150);
  const retried = seen.slice(before);
  assert(retried.length >= 1 && retried.every(u => /cursor=c1/.test(u)), "B: retry asks for the same failed cursor");
  assert(d.querySelectorAll("#pList .bp").length === 30 && err.hidden && retry.hidden, "B: successful continuation shows 30 cards and clears the error");
  // language switch while the pagination error is showing keeps the cards too
  fail503 = true;
  const b3 = boot({ bsky });
  await go(b3.w, "pulso"); await sleep(20);
  choose(b3.w, b3.d.getElementById("pInst"), "Fixture A"); await sleep(120);
  b3.d.getElementById("pMore").click(); await sleep(120);
  b3.d.getElementById("langSel").value = "ar"; b3.d.getElementById("langSel").dispatchEvent(new b3.w.Event("change")); await sleep(150);
  assert(b3.d.querySelectorAll("#pList .bp").length === 15 && b3.d.getElementById("pMoreErr").textContent === read("i18n/ar.json")["j:pMoreErr"].replace("{r}", read("i18n/ar.json")["j:pReasonNet"]),
    "B: pagination error survives a language switch, localized");
}

console.log(failed ? `${failed} CHECK(S) FAILED` : "ALL OK");
process.exit(failed ? 1 : 0);
