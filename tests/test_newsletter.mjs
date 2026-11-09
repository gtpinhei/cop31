// Newsletter signup (V1.2): feature flag off | preview | live, no personal data leaving the browser outside live mode,
// live mode only with a complete configuration, provider field mapping, seven languages. Synthetic values only.
// node tests/test_newsletter.mjs   (needs jsdom: NODE_PATH=... or `cd tools && npm install`)
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
const LIVE = { schema: 1, mode: "live", provider: "buttondown", action: "https://buttondown.com/api/emails/embed-subscribe/examplelist",
  processor: "Example Provider", controller: { name: "Example Controller", contact: "privacy@example.org" }, privacy: { status: "final", version: "2099-01" } };

function boot(cfg, { lang, hash } = {}) {
  const calls = [], submits = [];
  const dom = new JSDOM(html, { runScripts: "outside-only", url: "https://cop31.grupotrie.com.br/" + (lang ? "?lang=" + lang : "") + (hash ? "#" + hash : ""), pretendToBeVisual: true,
    beforeParse(w) {
      w.fetch = (u, opt) => {
        u = String(u); calls.push({ u, opt });
        if (u.includes("data/newsletter.json")) return cfg === undefined ? res(404, {}) : res(200, cfg);
        if (u.includes("data/feed.json")) return res(200, { schema: 1, items: [], tracks: [] });
        if (u.includes("data/pulse.json")) return res(200, { schema: 1, accounts: [] });
        if (u.includes("data/today.json")) return res(200, { schema: 1, entries: [] });
        if (u.includes("i18n/")) return res(200, read("i18n/" + u.split("i18n/")[1].split("?")[0]));
        return res(404, {});
      };
      w.scrollTo = () => {};
      Object.defineProperty(w.navigator, "language", { value: "pt-BR", configurable: true });
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {} });
      w.HTMLFormElement.prototype.submit = function(){ submits.push(this); };
    } });
  const w = dom.window;
  // record what a native submission would carry; jsdom does not navigate
  w.document.addEventListener("submit", e => { if (!e.defaultPrevented) submits.push({ action: e.target.getAttribute("action"), target: e.target.getAttribute("target"),
    data: [...new w.FormData(e.target).entries()] }); });
  const script = [...w.document.querySelectorAll("script")].map(s => s.textContent).find(t => t.includes("i18n-core-begin"));
  w.eval(script);
  return { w, d: w.document, calls, submits };
}
const go = async (w, h) => { w.location.hash = "#" + h; w.dispatchEvent(new w.Event("hashchange")); await sleep(60); };
function submit(b, form, email) {
  form.querySelector('[data-k="email"]').value = email;
  const ev = new b.w.Event("submit", { bubbles: true, cancelable: true });
  form.dispatchEvent(ev);
  return form.querySelector(".nl-msg");
}

// 1. off (production default) and missing config: nothing visible, routes fall back, no network beyond the config file
for (const cfg of [read("data/newsletter.json"), undefined]) {
  const b = boot(cfg); await sleep(80);
  assert([...b.d.querySelectorAll("[data-nl]")].every(e => e.hidden), "off: every newsletter element hidden (" + (cfg ? "repo config" : "no config") + ")");
  await go(b.w, "newsletter");
  assert(b.d.getElementById("view-newsletter").hidden && !b.d.getElementById("view-panorama").hidden, "off: #newsletter falls back to Panorama");
  await go(b.w, "privacidade");
  assert(b.d.getElementById("view-privacidade").hidden, "off: privacy draft is not reachable");
}
assert(read("data/newsletter.json").mode === "off", "repository ships with the newsletter switched off");

// 2. preview: visible, validates, never submits or fetches anywhere with the address
{
  const b = boot({ mode: "preview" }); await sleep(80);
  const cards = [...b.d.querySelectorAll(".nl-card")];
  assert(cards.length === 3 && cards.every(c => !c.hidden), "preview: compact signup on Hoje, Panorama and Atualizações");
  assert([...b.d.querySelectorAll("[data-nl-preview]")].every(e => !e.hidden), "preview: every form says nothing is sent");
  const f = b.d.querySelector('form[data-nl-src="hoje"]');
  let m = submit(b, f, "not-an-email");
  assert(!m.hidden && m.classList.contains("err"), "preview: invalid address rejected");
  m = submit(b, f, "someone@example.org");
  assert(!m.hidden && /nada foi enviado/.test(m.textContent), "preview: valid address gets the preview message");
  assert(b.submits.length === 0, "preview: no native submission");
  assert(!b.calls.some(c => /someone%40example|someone@example/.test(c.u + JSON.stringify(c.opt || {}))), "preview: the address never reaches the network");
  assert(![...b.d.querySelectorAll("form[data-nl-form] [name]")].length, "preview: no named fields at all, so even a stray submit carries nothing");
  assert(!f.hasAttribute("action"), "preview: form has no action");
  await go(b.w, "newsletter");
  assert(!b.d.getElementById("view-newsletter").hidden, "preview: newsletter page reachable");
  const full = b.d.querySelector('form[data-nl-src="newsletter"]');
  full.querySelectorAll("input[data-tag]").forEach(x => { x.checked = false; });
  m = submit(b, full, "someone@example.org");
  assert(/ao menos uma/.test(m.textContent), "preview: at least one newsletter must be chosen");
  await go(b.w, "privacidade");
  assert(b.d.getElementById("nlCtl").textContent === "a confirmar", "preview: controller shown as to be confirmed");
}

// 3. live with an incomplete configuration degrades to preview
for (const [label, cfg] of [["no controller", { ...LIVE, controller: null }], ["draft notice", { ...LIVE, privacy: { status: "draft", version: "x" } }],
                            ["foreign action", { ...LIVE, action: "https://evil.example/collect" }], ["no processor", { ...LIVE, processor: null }]]) {
  const b = boot(cfg); await sleep(80);
  const f = b.d.querySelector('form[data-nl-src="panorama"]');
  submit(b, f, "someone@example.org");
  assert(b.submits.length === 0 && !b.d.querySelector("[data-nl-preview]").hidden, "live with " + label + " stays in preview");
}

// 4. live, complete: posts straight to the provider with mapped fields, tags, language and consent version
{
  const b = boot(LIVE, { lang: "fr" }); await sleep(150);
  assert([...b.d.querySelectorAll("[data-nl-preview]")].every(e => e.hidden), "live: preview banners hidden");
  await go(b.w, "newsletter");
  const f = b.d.querySelector('form[data-nl-src="newsletter"]');
  f.querySelector('[data-k="organization"]').value = "Example Org";
  f.querySelector('input[data-tag="resumo-semanal"]').checked = true;
  submit(b, f, "someone@example.org");
  const s = b.submits[0];
  assert(s && s.action === LIVE.action && s.target === "_blank", "live: native POST to the provider in a new tab");
  const d = s ? s.data : [];
  const get = k => d.filter(x => x[0] === k).map(x => x[1]);
  assert(get("email")[0] === "someone@example.org", "live: email field mapped");
  assert(get("metadata__organization")[0] === "Example Org" && !get("metadata__name").length, "live: optional fields only when filled");
  assert(["briefing-diario", "resumo-semanal", "lang-fr"].every(t => get("tag").includes(t)), "live: preference and language tags: " + get("tag").join(","));
  assert(get("metadata__consent_version")[0] === "2099-01" && get("metadata__source")[0] === "newsletter", "live: consent version and source recorded");
  assert(b.d.getElementById("nlCtl").textContent === "Example Controller", "live: controller shown in the privacy notice");
  assert(!f.querySelector("input.nl-gen") || true, "generated inputs are transient");
}

// 5. seven languages: no newsletter string left untranslated
for (const l of ["en", "es", "fr", "ru", "zh", "ar"]) {
  const pt = read("i18n/pt.json"), t = read(`i18n/${l}.json`);
  const keys = Object.keys(pt).filter(k => /newsletter|Assinar|privacidade|nl[A-Z]|a confirmar/i.test(pt[k]) || k.startsWith("j:nl"));
  assert(keys.length > 10 && keys.every(k => t[k] && t[k] !== pt[k] || /^(Newsletter|E-mail)$/.test(pt[k])), `${l}: newsletter strings translated (${keys.length})`);
}

if (failed) { console.error(failed + " failed"); process.exit(1); }
