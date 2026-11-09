// Headless checks for Social Pulse (Bluesky states), "Hoje na COP31" gating and feed reliability.
// node tests/test_v1.mjs   (needs jsdom: NODE_PATH=... or `cd tools && npm install`)
// Bluesky responses are SAVED fixtures (tests/fixtures): one captured live on 8 Nov 2026 and synthetic
// ones built on the same lexicon shapes. Live API behaviour is not exercised here.
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
const res = (status, body) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

const PULSE = { schema: 1, bluesky_list: null, x_list: null, hidden: [], accounts: [
  { platform: "bluesky", handle: "enb.iisd.org", institution: "IISD / ENB", priority: "A", verified: true },
  { platform: "bluesky", handle: "fixture-alpha.test", institution: "Fixture A (teste)", priority: "A", verified: true },
  { platform: "bluesky", handle: "gone.bsky.social", institution: "Conta removida", priority: "B", verified: false },
  { platform: "x", handle: "turkiyecop31", institution: "Presidência da COP31 (Türkiye)", priority: "A", verified: true },
  { platform: "instagram", handle: "turkiyecop31", institution: "Presidência da COP31 (Türkiye)", priority: "A", verified: true },
  { platform: "youtube", handle: "@UNClimateChangeEvents", institution: "UNFCCC", priority: "A", verified: true, channel_id: "UCJlvsGJAR8NsiyLzuBf_cQg" },
  { platform: "youtube", handle: "@Turkiyecop31", institution: "Presidência da COP31 (Türkiye)", priority: "B", verified: true, channel_id: null } ] };

function boot({ bsky, today, drafts, feedResp, lang, host, query, pulse } = {}) {
  const calls = [];
  const qs = [lang ? "lang=" + lang : "", query || ""].filter(Boolean).join("&");
  const dom = new JSDOM(html, { runScripts: "outside-only", url: (host || "https://cop31.grupotrie.com.br") + "/" + (qs ? "?" + qs : ""), pretendToBeVisual: true,
    beforeParse(w) {
      w.fetch = (u) => {
        u = String(u); calls.push(u);
        if (u.includes("data/feed.json")) return feedResp ? feedResp() : res(200, feed);
        if (u.includes("data/pulse.json")) return res(200, pulse || PULSE);
        if (u.includes("data/today.json")) return res(200, today || read("data/today.json"));
        if (u.includes("__private__/drafts.json")) return drafts ? res(200, drafts) : res(404, {});
        if (u.includes("i18n/")) return res(200, read("i18n/" + u.split("i18n/")[1].split("?")[0]));
        if (u.startsWith("https://public.api.bsky.app/")) return bsky(u);
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
const go = async (w, h) => { w.location.hash = "#" + h; w.dispatchEvent(new w.Event("hashchange")); await sleep(60); };
const txt = (d, s) => (d.querySelector(s)?.textContent || "").trim();

// ---------- 1. sections preserved
{
  const { d } = boot({ bsky: () => res(200, { feed: [] }) });
  const views = [...d.querySelectorAll("section.view")].map(v => v.getAttribute("data-view"));
  const original = ["panorama", "atualizacoes", "belem", "testes", "mapa", "radar", "thinktanks", "agenda", "posicoes", "brasil", "quem", "calendario", "terreno", "glossario", "fontes"];
  assert(original.every(v => views.includes(v)), "all 15 original sections present");
  assert(views.includes("pulso") && views.includes("hoje"), "new sections: hoje, pulso");
  assert(d.querySelectorAll(".nav-item").length === 17, "17 navigation items");
}

// ---------- 2. Bluesky happy path, ordering, safety, repost context
{
  const { w, d, calls } = boot({ bsky: (u) => {
    if (u.includes("actor=enb.iisd.org")) return res(200, u.includes("cursor=") ? fx("bsky_enb_p2.json") : fx("bsky_enb_p1.json"));
    if (u.includes("actor=fixture-alpha.test")) return res(200, fx("bsky_fixture_alpha.json"));
    return res(400, fx("bsky_notfound.json"));
  } });
  await sleep(30);
  assert(!calls.some(u => u.includes("bsky.app")), "Bluesky not contacted before Pulso is opened (lazy)");
  await go(w, "pulso"); await sleep(150);
  const posts = [...d.querySelectorAll("#pList .bp")];
  assert(posts.length === 6, "6 posts shown (1 hidden by label, 1 repost merged): " + posts.length);
  assert(posts[0].textContent.includes("escaping check"), "newest first");
  assert(!d.querySelector("#pList script") && posts[0].innerHTML.includes("&lt;script&gt;"), "post text is escaped");
  assert(!d.body.textContent.includes("Hidden by label"), "post with 'porn' label is not rendered");
  assert(txt(d, "#pStatus").includes("1 posts ocultados") || /ocultad/.test(txt(d, "#pStatus")), "hidden count disclosed: " + txt(d, "#pStatus"));
  assert(posts.some(p => p.querySelector("details summary.bp-warn") && p.textContent.includes("warned post")), "!warn post is collapsed behind a warning");
  const enb = posts.find(p => p.textContent.includes("Montreal Protocol"));
  assert(enb && /repostado por Fixture account/.test(enb.textContent), "repost context shown on the original post");
  assert(enb && /IISD \/ ENB/.test(enb.textContent), "institution taken from the post author, not the reposter");
  assert(enb && enb.querySelector('a[href="https://bsky.app/profile/enb.iisd.org/post/3mzopsjeufk2o"]'), "canonical post URL built from at:// uri");
  assert(enb && enb.querySelector('a[href^="https://bsky.app/hashtag/Ozone"]') && enb.querySelector('a[href^="https://enb.iisd.org/montreal"]'), "facets: hashtag and link resolved by UTF-8 byte offsets");
  const anchors = enb ? [...enb.querySelectorAll(".bp-text a")].map(x => x.textContent) : [];
  assert(anchors.join("|") === "#Ozone|#MOP38|@unepozone.bsky.social|enb.iisd.org/montreal-pro...", "facet spans exact after multibyte emoji: " + anchors.join("|"));
  assert(enb && enb.querySelector(".bp-imgs img[loading=lazy]"), "images lazy-loaded");
  assert(posts.some(p => p.textContent.includes("post citado indisponível")), "unavailable quoted post handled");
  assert(posts.some(p => p.querySelector(".bp-card") && p.textContent.includes("link card")), "external link card");
  const vid = posts.find(p => p.textContent.includes("video without thumbnail"));
  assert(vid && vid.querySelector("a.bp-mfail") && !vid.querySelector(".bp-imgs"), "video without thumbnail: text link, no empty box");
  const imgPost = posts.find(p => p.textContent.includes("image with thumbnail"));
  const img = imgPost.querySelector(".bp-imgs img");
  img.dispatchEvent(new w.Event("error"));
  assert(!imgPost.querySelector(".bp-imgs") && imgPost.querySelector("a.bp-mfail[href*='/post/fx006']"), "broken image replaced by 'open on Bluesky' link");
  const av = d.querySelector("#pList img.bp-av");
  av.dispatchEvent(new w.Event("error"));
  assert(!d.querySelector("#pList img.bp-av") && d.querySelector("#pList span.bp-av.fail")?.textContent === "E", "broken avatar replaced by initial");
  assert(!calls.some(u => u.includes("gone.bsky.social")), "priority B not fetched by default");
  d.getElementById("pAll").checked = true; d.getElementById("pAll").dispatchEvent(new w.Event("change")); await sleep(150);
  assert(/não responderam: gone\.bsky\.social \(conta não encontrada\)/.test(txt(d, "#pStatus")), "partial failure named, not-found explained: " + txt(d, "#pStatus"));
  assert(d.querySelectorAll("#pList .bp").length === 6, "other accounts still shown on partial failure");
  // institution filter
  const sel = d.getElementById("pInst"); sel.value = "Fixture A (teste)"; sel.dispatchEvent(new w.Event("change")); await sleep(150);
  assert([...d.querySelectorAll("#pList .bp")].every(p => /fixture-alpha\.test|repostado por Fixture account/.test(p.textContent)), "institution filter narrows the stream");
}

// ---------- 3. empty, rate-limited, network error
{
  const { w, d } = boot({ bsky: () => res(200, { feed: [] }) });
  await go(w, "pulso"); await sleep(120);
  assert(txt(d, "#pStatus") === "Nenhum post recente destas contas.", "empty state: " + txt(d, "#pStatus"));
  assert(d.getElementById("pMore").hidden, "no 'load more' when nothing left");
}
{
  const { w, d } = boot({ bsky: () => res(429, fx("bsky_ratelimit.json")) });
  await go(w, "pulso"); await sleep(120);
  assert(/limitou as consultas/.test(txt(d, "#pStatus")) && d.getElementById("pStatus").className.includes("err"), "rate-limit state");
  assert(d.querySelector('#pList .pc a[href="https://bsky.app/profile/enb.iisd.org"]'), "rate-limit fallback: profile cards with direct links");
}
{
  const { w, d } = boot({ bsky: () => Promise.reject(new TypeError("Failed to fetch")) });
  await go(w, "pulso"); await sleep(120);
  assert(/Não foi possível falar com o Bluesky/.test(txt(d, "#pStatus")) && d.querySelector("#pList .pc"), "network error state with profile-card fallback");
}

// ---------- 4. X / Instagram / YouTube fallbacks load no third-party script by default
{
  const { w, d } = boot({ bsky: () => res(200, { feed: [] }) });
  await go(w, "pulso"); await sleep(60);
  d.querySelector('#pTabs [data-p="x"]').click(); await sleep(30);
  assert(!d.querySelector('script[src*="platform.twitter.com"]'), "X script not loaded until requested");
  assert(d.querySelector('#xCards a[href="https://x.com/turkiyecop31"]'), "X account card with profile link");
  assert(/link do perfil/.test(txt(d, "#xCards")), "monitored X posts with profile-only URL are labelled as such");
  d.querySelector('#pTabs [data-p="youtube"]').click(); await sleep(30);
  const yt = d.querySelector('#ytCards button[data-yt]');
  assert(yt && !d.querySelector("#ytCards iframe"), "YouTube: button, no player until requested");
  yt.click(); await sleep(10);
  const fr = d.querySelector("#ytCards iframe");
  assert(fr && fr.src.startsWith("https://www.youtube-nocookie.com/embed/videoseries?list=UUJlvsGJAR8NsiyLzuBf_cQg"), "privacy-enhanced uploads playlist");
  assert(d.querySelectorAll("#ytCards button[data-yt]").length === 1, "channel without id gets only a link, no fabricated embed");
  d.querySelector('#pTabs [data-p="instagram"]').click(); await sleep(30);
  assert(d.querySelector('#igCards a[href="https://www.instagram.com/turkiyecop31/"]') && !d.querySelector('script[src*="instagram.com"]'), "Instagram: profile card, no script by default");
}

// ---------- 5. Today: editorial gate, drafts never public, seven languages
{
  const LG = ["en", "es", "fr", "ru", "zh", "ar"];
  const full = (txt) => Object.fromEntries(LG.map(l => [l, { headline: txt + " " + l.toUpperCase(), what_happened: "W " + l, what_changed: "C " + l, why_it_matters: "Y " + l, watch_next: "Z " + l, method: l === "ar" ? "machine-reviewed" : "human" }]));
  const pub = { id: "p1", status: "published", headline: "Publicada", what_happened: "W", what_changed: "C", why_it_matters: "Y", watch_next: "Z", verification: "confirmado", classification: "decisão",
    sources: [{ url: "https://unfccc.int/a", verified: true, publisher: "UNFCCC" }], approved_by: "Gustavo", approved_at: "2026-11-09T10:00:00+03:00", assessed_at: "2026-11-09T10:00:00+03:00", i18n: full("Published") };
  const pend = Object.assign({}, pub, { id: "p4", headline: "Pendente em russo", assessed_at: "2026-11-09T09:00:00+03:00", i18n: Object.fromEntries(Object.entries(full("Pend")).filter(([l]) => l !== "ru")), i18n_pending: ["ru"] });
  const noAppr = Object.assign({}, pub, { id: "p2", headline: "Sem aprovação", approved_by: null });
  const noVer = Object.assign({}, pub, { id: "p3", headline: "Fonte não verificada", sources: [{ url: "https://x.org", verified: false }] });
  const strayDraft = Object.assign({}, pub, { id: "d0", status: "draft", headline: "Rascunho perdido", approved_by: null, approved_at: null });
  const doc = { schema: 1, entries: [pub, pend, noAppr, noVer, strayDraft] };
  const drafts = { schema: 1, entries: [{ id: "d1", status: "draft", headline: "Rascunho local", what_happened: "W", verification: "fonte única", classification: "anúncio", sources: [{ url: "https://a.org" }] }] };
  let b = boot({ today: doc, drafts, bsky: () => res(200, { feed: [] }) }); await sleep(60);
  await go(b.w, "hoje");
  const heads = [...b.d.querySelectorAll("#todayList h4")].map(h => h.textContent);
  assert(heads.join("|") === "Publicada|Pendente em russo", "only approved entries with a verified source are public: " + heads.join(" | "));
  assert(!b.calls.some(u => u.includes("editorial/")), "production never requests editorial drafts");
  b = boot({ today: doc, drafts, query: "preview=1", bsky: () => res(200, { feed: [] }) }); await sleep(60); await go(b.w, "hoje");
  assert(!b.calls.some(u => u.includes("editorial/") || u.includes("__private__")) && b.d.getElementById("todayPreviewFlag").hidden && ![...b.d.querySelectorAll("#todayList h4")].some(h => /Rascunho/.test(h.textContent)), "?preview=1 on the public host does nothing");
  b = boot({ today: doc, drafts, query: "preview=1", host: "http://127.0.0.1:8765", bsky: () => res(200, { feed: [] }) }); await sleep(60); await go(b.w, "hoje");
  assert([...b.d.querySelectorAll("#todayList h4")].some(h => h.textContent === "Rascunho local") && !b.d.getElementById("todayPreviewFlag").hidden, "local preview reads the private store (via tools/preview.py), marked");
  assert(!b.d.body.textContent.includes("Rascunho perdido"), "a draft inside data/today.json is never shown, even in preview");
  b = boot({ bsky: () => res(200, { feed: [] }) }); await sleep(60); await go(b.w, "hoje");
  assert(b.d.querySelectorAll("#todayList .ti").length === 0 && !b.d.getElementById("todayEmpty").hidden && b.d.getElementById("todayTeaser").hidden, "shipped today.json is empty; honest empty state");
  for (const l of LG) {
    b = boot({ today: doc, bsky: () => res(200, { feed: [] }), lang: l }); await sleep(160); await go(b.w, "hoje");
    const cards = [...b.d.querySelectorAll("#todayList .ti")];
    const c0 = cards.find(c => c.querySelector("h4").textContent.startsWith("Published"));
    const okFull = c0 && c0.querySelector("h4").textContent === "Published " + l.toUpperCase() && [...c0.querySelectorAll("dd")].map(x => x.textContent).join("|") === ["W", "C", "Y", "Z"].map(x => x + " " + l).join("|");
    assert(okFull, `[${l}] all substantive fields shown in ${l}`);
    if (l === "ar") assert(c0 && c0.querySelector(".ti-note") && b.d.documentElement.dir === "rtl", "[ar] machine-reviewed note and RTL");
    const p4 = cards.find(c => /Pend|Pendente/.test(c.querySelector("h4").textContent));
    if (l === "ru") assert(p4 && p4.getAttribute("lang") === "pt-BR" && p4.querySelector("h4").textContent === "Pendente em russo" && p4.querySelector(".ti-note"), "[ru] pending translation: Portuguese original, lang=pt-BR, disclosed");
    else assert(p4 && p4.querySelector("h4").textContent === "Pend " + l.toUpperCase(), `[${l}] translated entry with another language pending`);
  }
}

// ---------- 5b. Bluesky request limits
{
  const many = { schema: 1, hidden: [], accounts: Array.from({ length: 14 }, (_, i) => ({ platform: "bluesky", handle: `acct${i}.fixture.test`, institution: `Fixture ${i}`, priority: "A", verified: true })) };
  let inflight = 0, peak = 0, n = 0;
  let b = boot({ pulse: many, bsky: () => { n++; inflight++; peak = Math.max(peak, inflight); return new Promise(r => setTimeout(() => { inflight--; r(res(200, { feed: [] })); }, 15)); } });
  await go(b.w, "pulso"); await sleep(400);
  assert(peak <= 3 && n === 14, `at most 3 concurrent Bluesky requests (peak ${peak}, total ${n})`);
  assert(b.d.getElementById("pRefresh").disabled, "refresh button cools down after a load");
  n = 0;
  b = boot({ pulse: many, bsky: () => { n++; return new Promise(r => setTimeout(() => r(res(429, fx("bsky_ratelimit.json"))), 10)); } });
  await go(b.w, "pulso"); await sleep(300);
  assert(n <= 3, `after a 429 no further requests are sent (sent ${n})`);
  assert(b.d.querySelectorAll("#pList .pc").length === 14, "rate-limit fallback lists every account with a Bluesky link");
}

// ---------- 5c. fixtures can never become site content
{
  assert(!/tests\//.test(html), "index.html never references tests/");
  const pub = ["data/feed.json", "data/today.json", "data/pulse.json"].map(f => fs.readFileSync(path.join(ROOT, f), "utf8")).join("\n") + fs.readdirSync(path.join(ROOT, "i18n")).filter(f => f.endsWith(".json")).map(f => fs.readFileSync(path.join(ROOT, "i18n", f), "utf8")).join("");
  assert(!/TEST FIXTURE|fixture-alpha|example\.test|<script/i.test(pub), "no fixture text or script tags in any deployed data file");
  const syn = fx("bsky_fixture_alpha.json");
  assert(syn.feed.filter(x => x.post.author.handle !== "enb.iisd.org").every(x => /\.test$/.test(x.post.author.handle) && x.post.record.text.startsWith("[TEST FIXTURE]")), "synthetic fixtures use only .test accounts and labelled text");
}

// ---------- 6. feed reliability: slow, failure + retry, freshness, profile links
{
  let n = 0;
  const b = boot({ bsky: () => res(200, { feed: [] }), feedResp: () => (++n === 1 ? Promise.reject(new Error("offline")) : res(200, feed)) });
  await sleep(60);
  assert(b.d.getElementById("feedStatus").className.includes("err") && !b.d.getElementById("feedRetry").hidden, "feed failure shows error and retry");
  b.d.getElementById("feedRetry").click(); await sleep(80);
  assert(b.d.getElementById("feedStatus").className.match(/ok|warn/) && b.d.querySelectorAll("#feedList .fi").length > 0, "retry recovers");
  const st = txt(b.d, "#feedStatusText");
  assert(/Coleta web:.*há/.test(st) && /Coleta redes:/.test(st) && /Página carregada às/.test(st), "status separates collection time from page load time");
  const bl = (feed.round && feed.round.blocked_sites) || [];
  assert(bl.length ? st.includes(bl[0]) : !/Bloqueadas nesta rodada/.test(st), "blocked sources listed when the round reports any (" + (bl[0] || "none") + ")");
  const prof = [...b.d.querySelectorAll("#feedList .fi.post")].find(p => p.querySelector(".fi-plink"));
  assert(prof && /Ver perfil @/.test(prof.textContent) && !/Ver no X$/.test(prof.querySelector(".fi-link").textContent), "profile-only posts labelled, not presented as the post");
}
{
  const b = boot({ bsky: () => res(200, { feed: [] }), feedResp: () => new Promise(() => {}) });
  await sleep(4300);
  assert(b.d.getElementById("feedStatus").className.includes("slow") && /lenta/.test(txt(b.d, "#feedStatusText")), "slow-connection state after 4 s");
}

console.log(failed ? `${failed} CHECK(S) FAILED` : "ALL OK");
process.exit(failed ? 1 : 0);
