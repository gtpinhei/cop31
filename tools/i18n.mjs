#!/usr/bin/env node
// Navegador COP31 — i18n tool.
//   node tools/i18n.mjs extract          → rebuilds i18n/pt.json from index.html and writes i18n/todo.<lang>.json for every target language
//   node tools/i18n.mjs merge <lang> <file...> → validates translated entries and merges them into i18n/<lang>.json (prunes keys no longer in pt.json)
//   node tools/i18n.mjs status           → coverage per language
//   node tools/i18n.mjs split <lang> <maxChars> → splits todo.<lang>.json into i18n/work/<lang>.<n>.json chunks for translation agents
// Requires jsdom (npm i in tools/ or NODE_PATH pointing at a node_modules that has it).
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { JSDOM } = require("jsdom");

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const HTML = path.join(ROOT, "index.html");
const DIR = path.join(ROOT, "i18n");
const LANGS = ["en", "es", "fr", "ru", "zh", "ar"];
fs.mkdirSync(DIR, { recursive: true });

function readJSON(p, dflt) { try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return dflt; } }
function writeJSON(p, o) { fs.writeFileSync(p, JSON.stringify(o, null, 1) + "\n"); }
function between(s, a, b) { const i = s.indexOf(a), j = s.indexOf(b, i); if (i < 0 || j < 0) throw new Error("marker missing: " + a); return s.slice(i + a.length, j); }

function extract() {
  const html = fs.readFileSync(HTML, "utf8");
  const dom = new JSDOM(html); // scripts are not executed: the static DOM is what the browser hashes too
  const doc = dom.window.document;
  const script = [...doc.querySelectorAll("script")].map(s => s.textContent).find(t => t.includes("i18n-core-begin"));
  const core = between(script, "/*i18n-core-begin*/", "/*i18n-core-end*/");
  const jsBlock = between(script, "/*i18n-js-begin*/", "/*i18n-js-end*/");
  const I18N = new Function(core + "; return I18N;")();
  const J0 = new Function(jsBlock + "; return J0;")();
  const dataSrc = script.match(/var DATA = (\[[\s\S]*?\]);\s*\n/)[1];
  const DATA = JSON.parse(dataSrc);

  const units = I18N.collect(doc.documentElement);
  const src = {};
  const seen = {};
  for (const u of units) { if (seen[u.key] && seen[u.key] !== u.src) throw new Error("hash collision " + u.key); seen[u.key] = u.src; src[u.key] = u.src; }
  for (const k of Object.keys(J0)) src["j:" + k] = J0[k];
  const dataStrings = new Set();
  for (const r of DATA) { dataStrings.add(r[0]); dataStrings.add(r[1]); dataStrings.add(r[2]); }
  const feed = readJSON(path.join(ROOT, "data", "feed.json"), {});
  for (const t of feed.tracks || []) dataStrings.add(t);
  for (const s of [...dataStrings].sort()) src["d:" + s] = s;

  writeJSON(path.join(DIR, "pt.json"), src);
  const n = Object.keys(src).length;
  console.log(`pt.json: ${n} entries (${units.length} page units, ${Object.keys(J0).length} script strings, ${dataStrings.size} data strings)`);
  for (const lang of LANGS) {
    const cur = readJSON(path.join(DIR, lang + ".json"), {});
    const todo = {};
    for (const k of Object.keys(src)) if (cur[k] == null) todo[k] = src[k];
    const p = path.join(DIR, `todo.${lang}.json`);
    if (Object.keys(todo).length) writeJSON(p, todo); else if (fs.existsSync(p)) fs.unlinkSync(p);
    console.log(`${lang}: ${n - Object.keys(todo).length}/${n} translated, ${Object.keys(todo).length} to do`);
  }
}

// --- validation of one translated entry against its source
const TAG_RE = /<\/?([a-z][a-z0-9]*)\b([^>]*)>/gi;
function sig(s) {
  // ordered list of tags with their non-text attributes (href, src, class, id, target, rel, datetime, data-*)
  const out = [];
  for (const m of s.matchAll(TAG_RE)) {
    const closing = m[0].startsWith("</");
    const attrs = [...m[2].matchAll(/([a-z][\w-]*)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi)]
      .filter(a => /^(href|src|class|id|target|rel|datetime|data-[\w-]+|style)$/i.test(a[1]))
      .map(a => a[1].toLowerCase() + "=" + a[2].replace(/^['"]|['"]$/g, ""))
      .sort();
    out.push((closing ? "/" : "") + m[1].toLowerCase() + (attrs.length ? "[" + attrs.join(" ") + "]" : ""));
  }
  return out.join(" ");
}
function placeholders(s) { return [...String(s).matchAll(/\{(\w+)\}/g)].map(m => m[1]).sort().join(","); }
export function check(key, srcV, v) {
  if (Array.isArray(srcV)) {
    if (!Array.isArray(v) || v.length !== srcV.length || v.some(x => typeof x !== "string" || !x.trim())) return "array shape";
    return null;
  }
  if (typeof v !== "string" || !v.trim()) return "empty";
  if (sig(srcV) !== sig(v)) return "markup differs";
  if (placeholders(srcV) !== placeholders(v)) return "placeholders differ";
  if (key.startsWith("h") && v.length > srcV.length * 3 + 40) return "suspiciously long";
  return null;
}

function merge(lang, files) {
  const src = readJSON(path.join(DIR, "pt.json"), null);
  if (!src) throw new Error("run extract first");
  const target = path.join(DIR, lang + ".json");
  const cur = readJSON(target, {});
  let ok = 0, bad = 0, unknown = 0;
  const rejected = {};
  for (const f of files) {
    const t = readJSON(f, null);
    if (!t) { console.error("cannot read", f); continue; }
    for (const [k, v] of Object.entries(t)) {
      if (!(k in src)) { unknown++; continue; }
      const err = check(k, src[k], v);
      if (err) { bad++; rejected[k] = { error: err, src: src[k], got: v }; continue; }
      cur[k] = v; ok++;
    }
  }
  for (const k of Object.keys(cur)) if (!(k in src)) delete cur[k]; // prune stale keys
  writeJSON(target, cur);
  const rej = path.join(DIR, `rejected.${lang}.json`);
  if (bad) writeJSON(rej, rejected); else if (fs.existsSync(rej)) fs.unlinkSync(rej);
  const n = Object.keys(src).length, have = Object.keys(cur).filter(k => k in src).length;
  console.log(`${lang}: merged ${ok}, rejected ${bad}, unknown keys ${unknown} → ${have}/${n} translated` + (bad ? ` (see ${path.relative(ROOT, rej)})` : ""));
  // refresh todo file
  const todo = {}; for (const k of Object.keys(src)) if (cur[k] == null) todo[k] = src[k];
  const p = path.join(DIR, `todo.${lang}.json`);
  if (Object.keys(todo).length) writeJSON(p, todo); else if (fs.existsSync(p)) fs.unlinkSync(p);
}

function status() {
  const src = readJSON(path.join(DIR, "pt.json"), {});
  const n = Object.keys(src).length;
  for (const lang of LANGS) {
    const cur = readJSON(path.join(DIR, lang + ".json"), {});
    const have = Object.keys(src).filter(k => cur[k] != null).length;
    console.log(`${lang}: ${have}/${n} (${(100 * have / n).toFixed(1)}%)`);
  }
}

function split(lang, maxChars) {
  const todo = readJSON(path.join(DIR, `todo.${lang}.json`), null);
  if (!todo) { console.log("nothing to do for", lang); return; }
  const wdir = path.join(DIR, "work"); fs.mkdirSync(wdir, { recursive: true });
  for (const f of fs.readdirSync(wdir)) if (f.startsWith(lang + ".")) fs.unlinkSync(path.join(wdir, f));
  let chunk = {}, size = 0, i = 0;
  const flush = () => { if (Object.keys(chunk).length) { writeJSON(path.join(wdir, `${lang}.${++i}.json`), chunk); chunk = {}; size = 0; } };
  for (const [k, v] of Object.entries(todo)) {
    const len = JSON.stringify(v).length;
    if (size + len > maxChars && size > 0) flush();
    chunk[k] = v; size += len;
  }
  flush();
  console.log(`${lang}: ${i} chunk(s) in i18n/work/`);
}

const [cmd, ...args] = process.argv.slice(2);
if (cmd === "extract") extract();
else if (cmd === "merge") merge(args[0], args.slice(1));
else if (cmd === "status") status();
else if (cmd === "split") split(args[0], +args[1] || 18000);
else { console.log("usage: i18n.mjs extract | merge <lang> <file...> | status | split <lang> [maxChars]"); process.exit(1); }
