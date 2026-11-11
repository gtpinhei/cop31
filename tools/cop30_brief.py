#!/usr/bin/env python3
"""COP30 Presidency Daily Brief: discovery and collection of the 2026 COP31-period series (EN + PT).

The COP30 Presidency publishes one brief per COP31 day at
  EN https://cop30.br/en/news-about-cop30/daily-brief      PT https://cop30.br/pt-br/noticias-da-cop30/boletim-diario
Both index pages are Plone 6 (Volto) documents whose listing is rendered by JavaScript (the HTML shows only
"Loading"/"Carregando"). The site's own REST API (the same path prefixed with ++api++) serves the content as JSON and
robots.txt allows every agent, so the collector reads the API and never scrapes the rendered page:

  discovery   ++api++<index>/@search?portal_type=News Item&sort_on=effective (dated, newest first)
  edition     ++api++<edition>                (title, description, effective/modified dates, Volto blocks)
  pairing     ++api++<EN edition>/@translations   (the PT version's URL)

The same folders also hold the 2025 COP30 Morning Briefs / Evening Summaries / Belém Summit briefs (moved there, so
their `modified` date is 2026). The series is recognised by each edition's own `effective` date, never by its slug or
its modified date: only News Items effective on or after SERIES_START belong to it.

This module does no network access. The hourly sync (or an editor) fetches the URLs it lists with the agents' own
method (Nimble extract, driver vx6) and passes the saved responses back. Raw JSON, a Nimble result object
({"content": "<json>"}) and a saved Nimble tool result ([{"type": "text", "text": ...}]) are all accepted.

  python3 -I tools/cop30_brief.py plan [--force]                     # is a run due? which index URLs to fetch
  python3 -I tools/cop30_brief.py discover FILE [FILE ...]           # index responses -> editions to fetch
  python3 -I tools/cop30_brief.py collect FILE [FILE ...] [--out DIR] # edition + @translations responses
  python3 -I tools/cop30_brief.py emit [--summaries FILE] --out ITEMS.json [--feed data/feed.json]
  python3 -I tools/cop30_brief.py review EDITION_ID --by NAME [--note TEXT]
  python3 -I tools/cop30_brief.py status
  python3 -I tools/cop30_brief.py register --by NAME                # the parent source in the registry (idempotent)

State (listing, editions, hashes, revisions, review flags, extracted event details) lives in the private store under
cop30brief/state.json, never in the repository. The public feed gets one item per edition: title, links to both
language versions, an attributed summary written by the monitor and tracks; never the brief's own text.
"""
import datetime, hashlib, json, pathlib, re, sys, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools"))
import private as P  # noqa: E402

SOURCE_ID = "cop30-presidency-daily-brief"
AGENT = "cop30brief"
INDEX = {"en": "https://cop30.br/en/news-about-cop30/daily-brief",
         "pt": "https://cop30.br/pt-br/noticias-da-cop30/boletim-diario"}
API = "https://cop30.br/++api++/"
SEARCH = ("@search?portal_type=News%20Item&sort_on=effective&sort_order=descending&b_size=30"
          "&metadata_fields=effective&metadata_fields=modified&metadata_fields=created&metadata_fields=UID")
SERIES_START = "2026-11-01"           # the 2026 COP31-period series; COP31 runs 9-20 Nov 2026
EVERY_H = 3                           # run cadence during COP31
DUE_AFTER_H = 2.75                    # hourly sync: run when the last attempt is at least this old
VENUE_TZ = datetime.timezone(datetime.timedelta(hours=3))      # Antalya: the edition's day
LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=-3))     # Brasília: feed timestamps
INSTITUTION = "Presidência da COP30"
LANGS = ("en", "es", "fr", "ru", "zh", "ar")
MIN_BODY = 200                        # characters of body text below which an edition is treated as malformed
OFFICIAL_HOSTS = ("cop30.br", "unfccc.int", "cop31.tr", "gov.br", "climatechampions.unfccc.int", "un.org")

SECTIONS = {   # Volto slate headings that split a brief into parts (EN / PT)
    "moments": re.compile(r"^(key moments|momentos[- ]chave)$", re.I),
    "highlights": re.compile(r"^(highlights|destaques)$", re.I),
    "also": re.compile(r"^(also on the agenda|tamb[eé]m na agenda)$", re.I),
    "review": re.compile(r"^(day \d+ in review|retrospectiva do dia \d+|.*\bin review$)", re.I),
    "more": re.compile(r"^(for more information|mais informa[cç][oõ]es)\b", re.I),
}
FOCUS = re.compile(r"^(THEMATIC FOCUS|TEMA DO DIA|TEMAS? DO DIA|FOCO TEM[AÁ]TICO)\s*:\s*(.+)$", re.I)
DISCLAIMER = re.compile(r"^(the events are run and owned|os eventos s[aã]o de responsabilidade|more details on|mais (detalhes|informa[cç][oõ]es) no)", re.I)

TRACK_RULES = [   # (track, pattern) — matched on the monitor's extraction, English and Portuguese
    ("TAFF e fósseis", r"fossil|f[oó]sse|taff|transition(ing)? away|transi[cç][aã]o para longe"),
    ("Eletrificação", r"electri|eletri|renewabl|renov[aá]ve|\bgrids?\b|\brede el[eé]trica|energy|energia"),
    ("Finanças", r"financ|\bfunds?\b|\bfundo|billion|bilh|trillion|trilh|invest"),
    ("Adaptação", r"adapta|resilien|\bgga\b"),
    ("Transição justa", r"just transition|transi[cç][aã]o justa|jtwp"),
    ("Mitigação e MWP", r"mitiga|\bndcs?\b|\bmwp\b"),
    ("GST2 e IPCC", r"stocktake|balan[cç]o global|\bipcc\b|\bgst\b"),
    ("Perdas e danos", r"loss and damage|perdas e danos|frld"),
    ("Florestas", r"forest|floresta|tfff|deforest|desmat"),
    ("Comércio", r"\btrade\b|com[eé]rcio|cbam"),
    ("Agenda de Ação", r"action agenda|agenda de a[cç][aã]o|gcaa|high-level champion|campe[aã]o|campe[oõ]es|yearbook|anu[aá]rio|marrakech partnership"),
    ("Decisão de cobertura", r"cover decision|decis[aã]o de cobertura"),
    ("Espaço cívico", r"civil society|sociedade civil|civic space|espa[cç]o c[ií]vico|indigenous|ind[ií]gena"),
    ("Oceanos", r"\bocean|oceano|maritime|mar[ií]tim"),
]
CONSEQUENTIAL = [   # signals that an edition may announce something an editor should look at
    ("roadmap", r"\broadmap\b|mapa do caminho"),
    ("launch", r"\blaunch|\blan[cç]a(mento|r|do|da)\b"),
    ("pledge or commitment", r"\bpledge|\bcommitment|compromisso"),
    ("declaration", r"declaration|declara[cç][aã]o"),
    ("money figure", r"(us)?\$\s?\d|\bbillion\b|\btrillion\b|\bbilh[oõ]es\b|\btrilh[oõ]es\b"),
    ("decision or agreement", r"\bdecision\b|\bagreement\b|\bdecis[aã]o\b|\bacordo\b"),
    ("new fund or initiative", r"new (fund|initiative|coalition|facility)|novo fundo|nova (iniciativa|coaliz[aã]o)"),
]


# ---------- helpers ----------
def opt(a, k, d=None):
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d


def args(a, flags=("--now", "--out", "--summaries", "--feed", "--by", "--note")):
    """Positional arguments after the command (flag values excluded)."""
    return [x for i, x in enumerate(a[1:], 1) if not x.startswith("--") and a[i - 1] not in flags]


def now(a=None):
    t = opt(a or [], "--now")
    if t:
        x = datetime.datetime.fromisoformat(t)
        return x if x.tzinfo else x.replace(tzinfo=datetime.timezone.utc)
    return datetime.datetime.now(datetime.timezone.utc)


def iso_local(t):
    return t.astimezone(LOCAL_TZ).isoformat(timespec="minutes")


def ts(x):
    try:
        t = datetime.datetime.fromisoformat(str(x))
        return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return None


def state_path():
    return P.ensure() / "cop30brief" / "state.json"


def load_state():
    return P.load_json(state_path(), {"schema": 1, "source_id": SOURCE_ID, "discovery": {}, "collection": {},
                                       "listing": {}, "uids": {}, "editions": {}, "excluded": {}, "runs": []})


def save_state(st):
    P.save_json(state_path(), st)


def api_url(public):
    return API + public.split("https://cop30.br/", 1)[1] if public.startswith("https://cop30.br/") else public


def public_url(u):
    return (u or "").replace("https://cop30.br/++api++/", "https://cop30.br/", 1)


def lang_of(u):
    p = urllib.parse.urlparse(public_url(u)).path
    return "pt" if p.startswith("/pt-br/") else "en" if p.startswith("/en/") else None


def norm(t):
    return re.sub(r"\s+", " ", (t or "").replace(" ", " ")).strip()


class Bad(Exception):
    """A response that is not the API JSON we asked for (a placeholder page, an error, truncated output)."""


def unwrap(path):
    """Return the API JSON document held in a saved response, or raise Bad."""
    raw = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    doc = None
    for _ in range(4):                       # peel saved-tool-result and Nimble wrappers
        try:
            doc = json.loads(raw)
        except ValueError:
            break
        if isinstance(doc, list) and doc and isinstance(doc[0], dict) and isinstance(doc[0].get("text"), str):
            raw = doc[0]["text"]
            # a Nimble result may be followed by a second JSON object (conversation id): keep the first
            try:
                doc = json.loads(raw)
            except ValueError:
                dec = json.JSONDecoder()
                doc, _end = dec.raw_decode(raw)
            if isinstance(doc, dict) and isinstance(doc.get("content"), str):
                raw = doc["content"]; continue
            break
        if isinstance(doc, dict) and isinstance(doc.get("content"), str) and "@id" not in doc:
            raw = doc["content"]; continue
        break
    if not isinstance(doc, dict) or "@id" not in doc:
        text = raw if isinstance(raw, str) else ""
        if re.search(r"\b(Loading|Carregando)\b", text):
            raise Bad("placeholder page (Loading/Carregando), not the API listing")
        raise Bad("not an API JSON document")
    return doc


# ---------- plan / discovery ----------
def search_urls():
    return {lang: api_url(u) + "/" + SEARCH for lang, u in INDEX.items()}


def plan(a):
    st = load_state()
    t = now(a)
    last = ts((st.get("discovery") or {}).get("last_attempt"))
    due = "--force" in a or not last or (t - last).total_seconds() >= DUE_AFTER_H * 3600
    print(json.dumps({"due": due, "last_attempt": (st.get("discovery") or {}).get("last_attempt"),
                      "fetch": [{"lang": k, "url": v, "driver": "vx6", "output_format": "plain_text"} for k, v in search_urls().items()] if due else []},
                     ensure_ascii=False, indent=1))


def in_series(effective):
    e = ts(effective)
    return bool(e) and e.date().isoformat() >= SERIES_START


def discover(a):
    st = load_state()
    t = now(a)
    files = args(a)
    st["discovery"]["last_attempt"] = iso_local(t)
    per, fetch, found, excluded = {}, [], [], 0
    for f in files:
        try:
            doc = unwrap(f)
        except (Bad, OSError, ValueError) as e:
            per[f"file:{pathlib.Path(f).name}"] = {"outcome": "error", "note": str(e)[:160]}
            continue
        lang = lang_of(doc.get("@id"))
        if "@search" not in (doc.get("@id") or "") or lang not in INDEX:
            per[f"file:{pathlib.Path(f).name}"] = {"outcome": "error", "note": "not a daily-brief @search response"}
            continue
        items = doc.get("items")
        prev_n = len((st["listing"].get(lang) or {}).get("items") or [])
        if not isinstance(items, list):
            per[lang] = {"outcome": "error", "note": "listing has no items array"}
            continue
        if not items and (prev_n or doc.get("items_total")):
            per[lang] = {"outcome": "error", "note": f"empty listing (previously {prev_n} entries): not treated as 'no editions'"}
            continue
        rows = []
        for it in items:
            u = public_url(it.get("@id"))
            row = {"url": u, "uid": it.get("UID"), "type": it.get("@type"), "title": it.get("title"),
                   "description": it.get("description"), "effective": it.get("effective"), "modified": it.get("modified"),
                   "created": it.get("created")}
            rows.append(row)
            if row["type"] != "News Item" or not u.startswith(INDEX[lang] + "/"):
                continue
            if not row["effective"] or not ts(row["effective"]) or ts(row["effective"]).year < 2000:
                st["excluded"][u] = "no effective date in the listing"
                fetch.append({"lang": lang, "kind": "edition", "url": api_url(u), "reason": "listing has no date: read the edition itself"})
                continue
            if not in_series(row["effective"]):
                st["excluded"][u] = f"effective {row['effective'][:10]}: 2025 COP30 series, not the 2026 brief"
                excluded += 1
                continue
            found.append(u)
            known = next((e for e in st["editions"].values() if (e["langs"].get(lang) or {}).get("url") == u), None)
            kl = (known or {}).get("langs", {}).get(lang) or {}
            if not known or kl.get("modified") != row["modified"] or kl.get("status") != "ok":
                fetch.append({"lang": lang, "kind": "edition", "url": api_url(u),
                              "reason": "new" if not known else "modified" if kl.get("modified") != row["modified"] else "retry"})
                if lang == "en":
                    fetch.append({"lang": lang, "kind": "translations", "url": api_url(u) + "/@translations", "reason": "EN/PT pairing"})
        st["listing"][lang] = {"at": iso_local(t), "items_total": doc.get("items_total"), "items": rows}
        per[lang] = {"outcome": "success", "editions": sum(1 for r in rows if r["url"] in found)}
    ok = [k for k, v in per.items() if k in INDEX and v["outcome"] == "success"]
    outcome = "success" if len(ok) == len(INDEX) else "partial" if ok else "error"
    st["discovery"].update(last_outcome=outcome, per_lang=per)
    if ok:
        st["discovery"]["last_success"] = iso_local(t)
    st["runs"] = (st.get("runs") or [])[-60:] + [{"at": iso_local(t), "step": "discover", "outcome": outcome,
                                                   "fetch": len(fetch), "excluded_2025": excluded}]
    save_state(st)
    if outcome != "success":
        registry_record(t, "error" if outcome == "error" else "success", 0,
                        "discovery: " + "; ".join(f"{k} {v['outcome']} {v.get('note', '')}".strip() for k, v in per.items()))
    elif not fetch:
        registry_record(t, "success", 0, f"discovery: {len(found)} series edition(s) listed, none new or revised")
    print(json.dumps({"outcome": outcome, "per_lang": per, "series_editions": found, "excluded_2025": excluded,
                      "fetch": fetch}, ensure_ascii=False, indent=1))


# ---------- extraction ----------
def walk(blocks, layout):
    for k in layout or []:
        b = (blocks or {}).get(k)
        if not isinstance(b, dict):
            continue
        if b.get("@type") == "columnsBlock":
            data = b.get("data") or {}
            for ck in (data.get("blocks_layout") or {}).get("items") or []:
                col = (data.get("blocks") or {}).get(ck) or {}
                yield from walk(col.get("blocks"), (col.get("blocks_layout") or {}).get("items"))
        else:
            yield b


def slate_links(node, out):
    if isinstance(node, dict):
        if node.get("type") == "link":
            u = (node.get("data") or {}).get("url")
            if u:
                out.append(u)
        for v in node.values():
            slate_links(v, out)
    elif isinstance(node, list):
        for v in node:
            slate_links(v, out)


def first_strong(node):
    if isinstance(node, dict):
        if node.get("type") == "strong":
            return norm("".join(c.get("text", "") for c in node.get("children") or [] if isinstance(c, dict)))
        for v in node.get("children") or []:
            r = first_strong(v)
            if r:
                return r
    elif isinstance(node, list):
        for v in node:
            r = first_strong(v)
            if r:
                return r
    return ""


def labelled(text, *labels):
    for lab in labels:
        m = re.search(rf"(?:^|\n)\s*{lab}\s*:?\s*(.+)", text, re.I)
        if m:
            return norm(m.group(1))[:160]
    return None


def extract(doc):
    """Structured facts from one edition (never the full text in public output)."""
    blocks, layout = doc.get("blocks") or {}, (doc.get("blocks_layout") or {}).get("items") or []
    paras, links, events, section, sections = [], [], [], "lead", {}
    headline = focus = group = None
    for b in walk(blocks, layout):
        typ = b.get("@type")
        if typ == "buttonBlock":
            for h in b.get("href") or []:
                if isinstance(h, dict) and h.get("@id"):
                    links.append(h["@id"])
            continue
        if typ != "slate":
            continue
        raw = b.get("plaintext") or ""
        txt = norm(raw)
        slate_links(b.get("value"), links)
        if not txt:
            continue
        hit = next((k for k, rx in SECTIONS.items() if rx.match(txt)), None)
        if hit:
            section = "moments" if hit in ("moments", "highlights", "also") else hit
            group = "also" if hit == "also" else "highlight" if hit in ("moments", "highlights") else None
            sections.setdefault(section, 0)
            continue
        if DISCLAIMER.match(txt):
            continue
        m = FOCUS.match(txt)
        if m and focus is None:
            focus = norm(m.group(2)); continue
        strong = first_strong(b.get("value"))
        first_line = norm(raw.strip().split("\n")[0])
        if section == "moments" and ("|" in strong or "|" in first_line[:80] or "|" in txt[:60]):
            # the time and title are bold, but the bold run is sometimes split ("9" + " :00AM–… | Title")
            head = strong if "|" in strong else first_line if "|" in first_line else txt[:200]
            when, _, title = head.partition("|")
            full = "".join(_texts(b.get("value")))
            ev_links = []
            slate_links(b.get("value"), ev_links)
            events.append({"time": re.sub(r"\s+:", ":", norm(when)), "title": norm(title)[:200], "group": group,
                           "room": labelled(full, "Room", "Sala", "Local", "Venue"),
                           "livestream": next((u for u in ev_links if u.startswith("https://")), None)})
            paras.append(txt); continue
        if headline is None and section == "lead" and focus is None and len(txt) <= 140 and not txt.endswith("."):
            headline = txt                      # a short title line before the thematic focus (absent in some editions)
            paras.append(txt); continue
        if section == "lead":
            headline = headline or ""           # no title line in this edition: the lead starts here
        sections[section] = sections.get(section, 0) + 1
        paras.append(txt)
    body = "\n".join(paras)
    seen, clean = set(), []
    for u in links:
        u = u.strip()
        if u.startswith("https://") and u not in seen:
            seen.add(u); clean.append(u)
    host = lambda u: urllib.parse.urlparse(u).hostname or ""  # noqa: E731
    return {"headline": headline or None, "focus": focus, "body_chars": len(body),
            "hash": hashlib.sha256(body.encode("utf-8")).hexdigest(), "paragraphs": len(paras),
            "lead": [p for p in paras if p != headline and not FOCUS.match(p)][:2],     # private: material for the monitor's summary
            "review": _section_text(blocks, layout, "review"),
            "events": events, "links": clean,
            "official_links": [u for u in clean if any(host(u) == h or host(u).endswith("." + h) for h in OFFICIAL_HOSTS)],
            "_body": body}


def _texts(node):
    if isinstance(node, dict):
        if "text" in node and isinstance(node["text"], str):
            yield node["text"]
        for v in node.get("children") or []:
            yield from _texts(v)
    elif isinstance(node, list):
        for v in node:
            yield from _texts(v)


def _section_text(blocks, layout, want):
    out, cur = [], None
    for b in walk(blocks, layout):
        if b.get("@type") != "slate":
            continue
        txt = norm(b.get("plaintext"))
        if not txt:
            continue
        hit = next((k for k, rx in SECTIONS.items() if rx.match(txt)), None)
        if hit:
            cur = hit; continue
        if cur == want and not DISCLAIMER.match(txt):
            out.append(txt)
    return out[:3]


def edition_day(doc):
    """The edition's day in Antalya, from its own effective date; cross-checked with its description."""
    e = ts(doc.get("effective"))
    if not e or e.year < 2000:
        return None, "no effective date"
    day = e.astimezone(VENUE_TZ).date()
    desc = norm(doc.get("description"))
    months = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                          "september", "october", "november", "december"], 1)}
    months.update({m: i for i, m in enumerate(["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                                               "setembro", "outubro", "novembro", "dezembro"], 1)})
    m = re.search(r"(\d{1,2})\s+de\s+([a-zç]+)|([a-z]+)\s+(\d{1,2})", desc.lower())
    note = None
    if m:
        d, mon = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        if mon in months and (int(d), months[mon]) != (day.day, day.month):
            note = f"description says {desc!r} but effective date is {day.isoformat()}"
    return day.isoformat(), note


def classify(ex):
    head = " ".join(filter(None, [ex.get("headline"), ex.get("focus"), *ex.get("lead", [])])).lower()
    rest = ex.get("_body", "").lower()
    scored = []
    for track, rx in TRACK_RULES:
        s = 3 * len(re.findall(rx, head)) + min(len(re.findall(rx, rest)), 3)
        if s >= 3:
            scored.append((s, track))
    return ["Presidência e anfitrião"] + [t for _s, t in sorted(scored, key=lambda x: -x[0])[:3]]


def consequential(ex):
    text = " ".join(filter(None, [ex.get("headline"), ex.get("focus"), *ex.get("lead", []), *ex.get("review", [])])).lower()
    return [label for label, rx in CONSEQUENTIAL if re.search(rx, text)]


def collect(a):
    st = load_state()
    t = now(a)
    files = args(a)
    out_dir = pathlib.Path(opt(a, "--out") or (P.ensure() / "cop30brief" / "out"))
    st["collection"]["last_attempt"] = iso_local(t)
    docs, trans, problems = [], {}, []
    for f in files:
        try:
            d = unwrap(f)
        except (Bad, OSError, ValueError) as e:
            problems.append({"file": pathlib.Path(f).name, "problem": str(e)[:160]}); continue
        if (d.get("@id") or "").endswith("/@translations"):
            src = public_url(d["@id"][: -len("/@translations")])
            trans[src] = {x.get("language"): public_url(x.get("@id")) for x in d.get("items") or [] if x.get("@id")}
        elif d.get("@type") == "News Item":
            docs.append(d)
        else:
            problems.append({"file": pathlib.Path(f).name, "problem": f"unexpected document type {d.get('@type')!r}"})
    for src, m in trans.items():
        st.setdefault("pairs", {})[src] = m
    changed, new, revised = [], [], []
    for d in docs:
        url = public_url(d["@id"])
        lang = lang_of(url)
        uid = d.get("UID")
        if lang not in INDEX or not url.startswith(INDEX[lang] + "/"):
            problems.append({"url": url, "problem": "not in a daily-brief index"}); continue
        day, note = edition_day(d)
        if not day:
            problems.append({"url": url, "problem": "malformed: " + note})
            st["excluded"][url] = "malformed: " + note; continue
        if not in_series(d.get("effective")):
            st["excluded"][url] = f"effective {day}: 2025 COP30 series, not the 2026 brief"; continue
        ex = extract(d)
        if ex["body_chars"] < MIN_BODY:
            problems.append({"url": url, "problem": f"malformed: body has {ex['body_chars']} characters"})
            continue
        eid = st["uids"].get(uid) if uid else None
        if not eid:                                    # pair with the other language: @translations first, then same day
            partner = counterpart(st, url)
            if partner:
                eid = next((k for k, x in st["editions"].items() if any(v.get("url") == partner for v in x["langs"].values())), None)
            if not eid:
                base = f"{SOURCE_ID}-{day}"
                cand = st["editions"].get(base)
                if cand is None or (lang not in cand["langs"] and (partner is None or
                                    any(v.get("url") == partner for v in cand["langs"].values()))):
                    eid = base
                else:
                    eid = f"{base}-{(uid or hashlib.sha1(url.encode()).hexdigest())[:6]}"
            if uid:
                st["uids"][uid] = eid
        e = st["editions"].setdefault(eid, {"id": eid, "date": day, "langs": {}, "revision": 0, "revisions": [],
                                            "first_seen": iso_local(t), "review": {"status": "none", "reasons": []}})
        prev = e["langs"].get(lang)
        rec = {"url": url, "uid": uid, "title": norm(d.get("title")), "description": norm(d.get("description")),
               "effective": d.get("effective"), "modified": d.get("modified"), "created": d.get("created"),
               "status": "ok", "extracted_at": iso_local(t), "date_note": note,
               **{k: v for k, v in ex.items() if k != "_body"}}
        if prev and prev.get("hash") == rec["hash"]:
            if prev.get("modified") != rec["modified"]:
                prev.update(modified=rec["modified"], extracted_at=rec["extracted_at"])   # metadata-only edit
            continue
        if prev:
            e["revision"] += 1
            e["revisions"].append({"at": iso_local(t), "lang": lang, "modified": rec["modified"], "old_hash": prev["hash"][:12],
                                   "new_hash": rec["hash"][:12], "title_changed": prev.get("title") != rec["title"],
                                   "headline_changed": prev.get("headline") != rec["headline"],
                                   "events": [len(prev.get("events") or []), len(rec["events"])],
                                   "chars": [prev.get("body_chars"), rec["body_chars"]]})
            e["needs_summary"] = True
            revised.append(eid)
        else:
            e["needs_summary"] = True
            new.append(eid)
        e["langs"][lang] = rec
        if prev:   # seconds: a revision must sort after the first version even within the same minute
            e["revised_at"] = t.astimezone(LOCAL_TZ).isoformat(timespec="seconds")
        e["date"] = edition_day({"effective": (e["langs"].get("en") or rec)["effective"]})[0] or day
        e["published"] = min(x["effective"] for x in e["langs"].values())
        e["last_modified"] = max(x["modified"] or "" for x in e["langs"].values())
        e["tracks"] = classify(dict(ex, _body=ex["_body"]))
        reasons = sorted(set(consequential(ex)) | set(e["review"].get("reasons") or []))
        if reasons and e["review"]["status"] in ("none",) or (prev and reasons and e["review"]["status"] == "reviewed"):
            e["review"] = {"status": "pending", "reasons": reasons, "flagged_at": iso_local(t),
                           **({"previous": e["review"]} if e["review"].get("status") == "reviewed" else {})}
        changed.append(eid)
    for e in st["editions"].values():
        e["complete"] = all(l in e["langs"] for l in INDEX)
    outcome = "error" if problems and not docs else "success" if docs else "success_empty"
    if docs:
        st["collection"]["last_success"] = iso_local(t)
    st["collection"].update(last_outcome=outcome, problems=problems[-10:])
    st["runs"] = (st.get("runs") or [])[-60:] + [{"at": iso_local(t), "step": "collect", "outcome": outcome,
                                                   "new": new, "revised": revised, "problems": len(problems)}]
    save_state(st)
    latest = max((e["date"] for e in st["editions"].values()), default=None)
    registry_record(t, outcome, len(set(new)), (
        f"{len(set(new))} new, {len(set(revised))} revised edition(s)" + (f"; {len(problems)} problem(s): " + problems[0]["problem"] if problems else "")),
        latest)
    out_dir.mkdir(parents=True, exist_ok=True)
    need = [_summary_material(e) for e in st["editions"].values() if e.get("needs_summary")]
    (out_dir / "needs_summary.json").write_text(json.dumps(need, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"outcome": outcome, "new": sorted(set(new)), "revised": sorted(set(revised)), "problems": problems,
                      "flagged": [e["id"] for e in st["editions"].values() if e["review"]["status"] == "pending"],
                      "needs_summary": str(out_dir / "needs_summary.json") if need else None}, ensure_ascii=False, indent=1))


def counterpart(st, url):
    """The other language version's URL, from the @translations responses seen so far."""
    pairs = st.get("pairs") or {}
    if url in pairs:
        return pairs[url].get("pt-br")
    return next((src for src, m in pairs.items() if m.get("pt-br") == url), None)


def _summary_material(e):
    """What the monitor summarises from (private): extracted facts, never to be published as such."""
    return {"id": e["id"], "date": e["date"], "revised": bool(e["revisions"]),
            "langs": {l: {"url": x["url"], "title": x["title"], "description": x["description"], "headline": x.get("headline"),
                          "focus": x.get("focus"), "lead": x.get("lead"), "review": x.get("review"),
                          "events": [{"time": v["time"], "title": v["title"]} for v in x.get("events") or []]}
                      for l, x in e["langs"].items()},
            "write": {"summary": "Portuguese, 2-3 sentences in the monitor's own words, attributed ('A Presidência da COP30 ...'); "
                                 "no copying of the brief's sentences; end with the tracks note like other items",
                      "summary_i18n": list(LANGS)}}


# ---------- registry ----------
def registry_record(t, outcome, new_items, note, latest=None):
    """Fold this run into the source registry's health (best effort: the collector works without a registry)."""
    try:
        import sources as S
        reg = S.load()
    except SystemExit:
        return
    except Exception:  # noqa: BLE001
        return
    s = next((x for x in reg["sources"] if x["id"] == SOURCE_ID), None)
    if not s:
        return
    st = load_state()
    S.record(s, {"at": iso_local(t), "agent": AGENT, "outcome": "success_empty" if outcome == "success" and not new_items else outcome,
                 "new_items": new_items, "latest_item_date": latest, "note": (note or "")[:200] or None})
    ser = s.setdefault("series", {})
    ser.update(last_discovery_attempt=st["discovery"].get("last_attempt"), last_discovery_success=st["discovery"].get("last_success"),
               last_collection_attempt=st["collection"].get("last_attempt"), last_collection_success=st["collection"].get("last_success"),
               editions=[{"id": e["id"], "date": e["date"], "published": e.get("published"), "last_modified": e.get("last_modified"),
                          "revision": e["revision"], "urls": {l: x["url"] for l, x in e["langs"].items()},
                          "hash": {l: x["hash"][:12] for l, x in e["langs"].items()}}
                         for e in sorted(st["editions"].values(), key=lambda x: x["date"])])
    try:
        S.save(reg, f"{AGENT}: {outcome} ({note[:80] if note else ''})")
    except SystemExit:
        pass


def register(a):
    """Create (or refresh the static fields of) the parent source in the registry. Idempotent."""
    import sources as S
    by = opt(a, "--by") or sys.exit("--by NAME is required")
    reg = S.load()
    s = next((x for x in reg["sources"] if x["id"] == SOURCE_ID), None)
    fresh = s is None
    if fresh:
        s = S.blank("web", INDEX["en"], INSTITUTION, "presidency", "A", by, "editor-request")
        s["id"] = SOURCE_ID
        reg["sources"].append(s)
    s.update(urls=[INDEX["en"], INDEX["pt"]], language="en", languages=["en", "pt"], priority="A", status="active",
             rights="link_and_summary", category="presidency", category_label="official institutional briefing",
             themes=["Presidência e anfitrião"],
             notes="Daily Brief of the COP30 Presidency during COP31 (2026 series only; the 2025 Morning Briefs / Evening "
                   "Summaries in the same folders are excluded by their own effective date).")
    s["collection"] = {"agent": AGENT, "method": "Plone REST API (++api++): @search on each index, edition JSON, "
                       "@translations for EN/PT pairing; Nimble extract vx6; robots.txt allows all agents",
                       "cadence": "every_3h", "collector": "tools/cop30_brief.py"}
    if s["identity"].get("status") != "checked":
        s["identity"] = {"status": "checked", "basis": "institution's own domain (cop30.br, the COP30 Presidency site)",
                         "evidence_url": INDEX["en"], "checked_at": S.now(), "checked_by": by}
    s.setdefault("series", {}).update(parent_indexes=INDEX, discovery="api_search", search=search_urls(),
                                      series_start=SERIES_START, cadence_hours=EVERY_H)
    s.setdefault("decision", {"at": S.now(), "by": by, "reason": "editor request (COP30 Presidency Daily Brief integration)"})
    other = next((x for x in reg["sources"] if x["id"] != SOURCE_ID and x.get("platform") in ("web", "rss")
                  and S.domain(x) == S.domain(s) and x.get("status") not in ("rejected", "retired")), None)
    for x in [o for o in reg["sources"] if o["id"] != SOURCE_ID and o.get("platform") in ("web", "rss")
              and S.domain(o) == S.domain(s)]:
        x["distinct_from"] = sorted(set(x.get("distinct_from") or []) | {SOURCE_ID})
        s["distinct_from"] = sorted(set(s.get("distinct_from") or []) | {x["id"]})
    S.save(reg, f"{'registered' if fresh else 'refreshed'} {SOURCE_ID} by {by}")
    print(f"{SOURCE_ID}: {'registered' if fresh else 'refreshed'}" + (f" (distinct from {other['id']})" if other else ""))


# ---------- feed items ----------
def item_for(e, summ, t):
    en, pt = e["langs"].get("en"), e["langs"].get("pt")
    main = en or pt
    def title(x, lang):
        if not x:
            return None
        parts = [x["title"]]
        if x.get("description"):
            parts[0] += " – " + x["description"]
        sub = x.get("headline") or x.get("focus")          # the day's title line, else its thematic focus
        return parts[0] + (": " + sub if sub else "")
    it = {"id": e["id"], "institution": INSTITUTION, "type": "boletim", "title": title(main, "en" if en else "pt"),
          "date": e["date"], "url": main["url"], "lang": "en" if en else "pt", "tracks": e.get("tracks") or ["Presidência e anfitrião"],
          "source_id": SOURCE_ID, "series": "COP30 Presidency Daily Brief",
          "first_seen": e.get("first_seen"), "published_at": e.get("published"), "source_modified_at": e.get("last_modified")}
    if en and pt:
        it["url_i18n"] = {"en": en["url"], "pt": pt["url"]}
        it["title_i18n"] = {"pt": title(pt, "pt")}
    if e["revision"]:
        it["updated_at"] = e.get("revised_at") or iso_local(t)   # the collector's version of this revision: stable across runs
        it["revision"] = e["revision"]
    if summ:
        if isinstance(summ.get("summary"), str) and summ["summary"].strip():
            it["summary"] = summ["summary"].strip()
        si = summ.get("summary_i18n") or {}
        si = {k: v.strip() for k, v in si.items() if k in LANGS and isinstance(v, str) and v.strip()}
        if si:
            it["summary_i18n"] = si
    return it


def emit(a):
    st = load_state()
    t = now(a)
    out = pathlib.Path(opt(a, "--out") or sys.exit("--out ITEMS.json is required"))
    feed_p = pathlib.Path(opt(a, "--feed") or (ROOT / "data" / "feed.json"))
    feed = json.loads(feed_p.read_text(encoding="utf-8")) if feed_p.exists() else {"items": []}
    on_file = {x.get("id"): x for x in feed.get("items") or []}
    sp = opt(a, "--summaries")
    summaries = json.loads(pathlib.Path(sp).read_text(encoding="utf-8")) if sp else {}
    if isinstance(summaries, list):
        summaries = {x.get("id"): x for x in summaries if isinstance(x, dict)}
    items, held = [], []
    for e in sorted(st["editions"].values(), key=lambda x: x["date"]):
        cur = on_file.get(e["id"])
        fd = e.setdefault("feed", {})
        summ = summaries.get(e["id"])
        cur_v = (cur or {}).get("updated_at") or (cur or {}).get("first_seen")
        if cur and fd.get("version") and cur_v != fd["version"] and e["revision"] and e.get("needs_summary"):
            # someone edited the published item after the collector last wrote it: never overwrite that assessment
            e["review"] = {**e["review"], "status": "pending",
                           "reasons": sorted(set(e["review"].get("reasons") or []) | {"source revised after an editor's change"}),
                           "flagged_at": iso_local(t)}
            held.append(e["id"]); continue
        if cur and not e.get("needs_summary") and not summ:
            continue                                            # already on file and unchanged
        it = item_for(e, summ, t)
        items.append(it)
        fd.update(version=it.get("updated_at") or it.get("first_seen"), emitted_at=iso_local(t), with_summary=bool(it.get("summary")))
        if it.get("summary") and it.get("summary_i18n"):
            e["needs_summary"] = False
    save_state(st)
    out.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"items": [x["id"] for x in items], "without_summary": [x["id"] for x in items if not x.get("summary")],
                      "held_for_editor": held}, ensure_ascii=False, indent=1))


def review(a):
    st = load_state()
    e = st["editions"].get(a[1]) or sys.exit(f"no edition {a[1]}")
    by = opt(a, "--by") or sys.exit("--by NAME is required")
    e["review"] = {**e["review"], "status": "reviewed", "by": by, "at": P.now(), "note": opt(a, "--note")}
    save_state(st)
    print(f"{a[1]}: reviewed by {by}")


def status(a):
    st = load_state()
    print(json.dumps({"discovery": st["discovery"], "collection": st["collection"],
                      "editions": [{"id": e["id"], "date": e["date"], "published": e.get("published"), "revision": e["revision"],
                                    "complete": e.get("complete"), "review": e["review"].get("status"),
                                    "needs_summary": e.get("needs_summary"),
                                    "urls": {l: x["url"] for l, x in e["langs"].items()},
                                    "events": {l: len(x.get("events") or []) for l, x in e["langs"].items()}}
                                   for e in sorted(st["editions"].values(), key=lambda x: x["date"])],
                      "excluded": len(st["excluded"])}, ensure_ascii=False, indent=1))


def main(a):
    cmd = a[0] if a else "help"
    if cmd == "plan": plan(a)
    elif cmd == "discover": discover(a)
    elif cmd == "collect": collect(a)
    elif cmd == "emit": emit(a)
    elif cmd == "review": review(a)
    elif cmd == "status": status(a)
    elif cmd == "register": register(a)
    else:
        print(__doc__); sys.exit(0 if cmd == "help" else 2)


if __name__ == "__main__":
    main(sys.argv[1:])
