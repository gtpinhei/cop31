#!/usr/bin/env python3
"""Validate data/feed.json (schema 1) and data/today.json.

usage: python3 -I tools/validate_feed.py [FEED.json] [--today TODAY.json]

Exit status 1 if any item has a fatal error. Warnings are printed but do not fail.
merge_feed.py loads this module by path and drops items that fail validation,
so one malformed item from an agent can never break the public page.
"""
import json, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LANGS = ("en", "es", "fr", "ru", "zh", "ar")
TYPES = {"release", "blog", "relatório", "briefing", "notícia", "opinião", "comunicado",
         "análise", "boletim", "ferramenta", "evento", "explicador"}
PLATFORMS = {"bluesky", "x", "instagram", "youtube", "linkedin", "whatsapp", "tiktok"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")
TIME = re.compile(r"^\d{2}:\d{2}$")


def link_kind(url, platform=None):
    """'post' when the URL points at one post, 'profile' when only at an account page."""
    u = (url or "").split("?")[0].rstrip("/")
    if re.search(r"(x|twitter)\.com/[^/]+/status/\d+", u): return "post"
    if re.search(r"bsky\.app/profile/[^/]+/post/[a-z0-9]+", u): return "post"
    if re.search(r"instagram\.com/(p|reel|tv)/[\w-]+", u): return "post"
    if re.search(r"youtube\.com/(watch\?v=|shorts/|live/)|youtu\.be/", url or ""): return "post"
    if re.search(r"(x|twitter)\.com/[^/]+$|bsky\.app/profile/[^/]+$|instagram\.com/[^/]+$|youtube\.com/(@[^/]+|channel/[^/]+)$", u):
        return "profile"
    return "unknown"


def _str(v):
    return isinstance(v, str) and v.strip() != ""


def check_item(it, tracks=()):
    """Return (errors, warnings) for one feed item."""
    e, w = [], []
    if not isinstance(it, dict):
        return ["item is not an object"], w
    if not _str(it.get("id")): e.append("missing id")
    post = it.get("kind") == "post"
    if it.get("kind") not in (None, "post"): e.append(f"unknown kind {it.get('kind')!r}")
    if not (isinstance(it.get("date"), str) and DATE.match(it["date"])): e.append(f"bad date {it.get('date')!r}")
    if it.get("first_seen") is not None and not (isinstance(it["first_seen"], str) and ISO.match(it["first_seen"])):
        e.append(f"bad first_seen {it.get('first_seen')!r}")
    if it.get("updated_at") is not None and not (isinstance(it["updated_at"], str) and ISO.match(it["updated_at"])):
        e.append(f"bad updated_at {it.get('updated_at')!r}")
    url = it.get("url")
    if url is not None and not (isinstance(url, str) and url.startswith("https://")):
        e.append(f"url must be https: {url!r}")
    if it.get("summary") is not None:
        if not isinstance(it["summary"], str): e.append("summary not a string")
        elif "<" in it["summary"]: w.append("summary contains '<' (rendered as text)")
    si = it.get("summary_i18n")
    if si is not None:
        if not isinstance(si, dict): e.append("summary_i18n not an object")
        else:
            for k, v in si.items():
                if k not in LANGS: w.append(f"summary_i18n has unknown language {k!r}")
                if not isinstance(v, str): e.append(f"summary_i18n[{k}] not a string")
            missing = [l for l in LANGS if l not in si]
            if missing: w.append("summary_i18n missing " + ",".join(missing))
    elif it.get("summary"):
        w.append("no summary_i18n (shown in Portuguese in every language)")
    tr = it.get("tracks", [])
    if not isinstance(tr, list) or not all(isinstance(t, str) for t in tr): e.append("tracks must be a list of strings")
    elif tracks:
        extra = [t for t in tr if t not in tracks]
        if extra: w.append("tracks not in top-level list: " + ", ".join(extra))
    if post:
        if it.get("platform") not in PLATFORMS: e.append(f"unknown platform {it.get('platform')!r}")
        if not _str(it.get("account")): e.append("post without account")
        if not _str(url): e.append("post without url")
        if it.get("time") not in (None, "") and not (isinstance(it["time"], str) and TIME.match(it["time"])):
            e.append(f"bad time {it.get('time')!r}")
        if not isinstance(it.get("text", ""), str): e.append("text not a string")
        if _str(url) and link_kind(url) == "profile":
            w.append("url is the account profile, not the post")
    else:
        if not _str(it.get("institution")): e.append("publication without institution")
        if not _str(it.get("title")): e.append("publication without title")
        if it.get("type") is not None and it["type"] not in TYPES: w.append(f"unlisted type {it['type']!r}")
        q = it.get("quotes", [])
        if not isinstance(q, list) or not all(isinstance(x, str) for x in q): e.append("quotes must be a list of strings")
    return e, w


def check_round(r, name):
    e = []
    if r is None: return e
    if not isinstance(r, dict): return [f"{name} not an object"]
    if r.get("timestamp") is not None and not (isinstance(r["timestamp"], str) and ISO.match(r["timestamp"])):
        e.append(f"{name}.timestamp bad {r.get('timestamp')!r}")
    for k in ("configured", "attempted", "sites_checked", "accounts_checked", "blocked", "new_items"):
        if r.get(k) is not None and not (isinstance(r[k], int) and r[k] >= 0):
            e.append(f"{name}.{k} must be a non-negative integer")
    return e


def check_feed(feed):
    """Return (fatal_errors, per_item {id: (errors, warnings)})."""
    fatal, per = [], {}
    if not isinstance(feed, dict): return ["feed is not an object"], per
    if feed.get("schema", 1) != 1: fatal.append(f"unknown schema {feed.get('schema')!r}")
    if not isinstance(feed.get("items"), list): fatal.append("items must be a list")
    fatal += check_round(feed.get("round"), "round") + check_round(feed.get("social_round"), "social_round")
    tracks = feed.get("tracks") or []
    seen = set()
    for i, it in enumerate(feed.get("items") or []):
        e, w = check_item(it, tracks)
        k = (it.get("id") if isinstance(it, dict) else None) or f"#{i}"
        if k in seen: e.append("duplicate id")
        seen.add(k)
        if e or w: per[k] = (e, w)
    return fatal, per


# ---- today.json (editor-curated "Hoje na COP31") and data/articles/*.json (full readouts)
# Both are public: they may hold ONLY published, human-approved content. Drafts, submissions, original
# documents, evidence quotes, flags and contributor permissions live in the private store (tools/private.py),
# outside the repository. Public files are checked against a whitelist of keys so a private field can
# never ride along into a commit.
STATUS = {"draft", "published", "retracted"}
VERIF = {"confirmado", "fonte única", "não confirmado"}
CLASS = {"decisão", "sinal político", "anúncio", "disputa", "processo", "análise"}
TEXT_FIELDS = ("headline", "summary", "what_happened", "what_changed", "why_it_matters", "watch_next", "open_questions")
METHODS = {"human", "machine-reviewed", "machine"}
MARKERS = ("[preencher]", "[revisar]", "[todo]", "TODO")
# evidence categories (brief §3): what a sentence rests on
BASIS = {"verified", "attributed", "analysis", "unverified"}
BASIS_FIELDS = ("summary", "what_happened", "what_changed", "why_it_matters", "watch_next")
SOURCE_KINDS = {"official", "media", "analysis", "contributor"}
ROLES = {"author", "observer", "analyst", "organization"}
PUBLIC_ENTRY_KEYS = {"id", "status", "headline", "summary", "theme", "areas", "classification", "verification",
                     "event_at", "assessed_at", "what_happened", "what_changed", "why_it_matters", "watch_next",
                     "open_questions", "basis", "actors", "sources", "promoted_from", "related", "contributor",
                     "article", "i18n", "i18n_pending", "approved_by", "approved_at", "corrections"}
PUBLIC_SOURCE_KEYS = {"title", "publisher", "url", "verified", "kind", "note", "date"}
PUBLIC_CONTRIB_KEYS = {"display", "name", "affiliation", "role"}
ARTICLE_KEYS = {"schema", "id", "entries", "status", "title", "standfirst", "reporting_note", "blocks", "contributor", "sources",
                "event_at", "assessed_at", "approved_by", "approved_at", "i18n", "i18n_pending", "corrections"}
ARTICLE_TEXT = ("title", "standfirst", "reporting_note")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
PRIVATE_HINTS = ("cop31-private", "/intake/", "drafts.json", "sha256:")


def _markers(v):
    return isinstance(v, str) and any(m in v for m in MARKERS)


def _private_leak(obj):
    """Strings that only make sense in the private store (paths, fingerprints)."""
    s = json.dumps(obj, ensure_ascii=False)
    return [h for h in PRIVATE_HINTS if h in s]


def check_sources(src, e, public):
    if not isinstance(src, list) or not src:
        e.append("at least one source required"); return
    for s in src:
        if not isinstance(s, dict):
            e.append(f"source must be an object: {s!r}"); continue
        kind = s.get("kind", "official" if s.get("url") else None)
        if kind is not None and kind not in SOURCE_KINDS:
            e.append(f"source kind must be one of {sorted(SOURCE_KINDS)}")
        url = s.get("url")
        if url is None and kind == "contributor":
            pass   # first-hand account by the named contributor: no public URL exists
        elif not (isinstance(url, str) and url.startswith("https://")):
            e.append(f"source needs an https url (or kind 'contributor' for a first-hand account): {s.get('title') or s!r}")
        if public:
            extra = set(s) - PUBLIC_SOURCE_KEYS
            if extra: e.append(f"source has non-public fields {sorted(extra)}")


def check_contributor(c, e):
    if c is None: return
    if not isinstance(c, dict): e.append("contributor must be an object"); return
    extra = set(c) - PUBLIC_CONTRIB_KEYS
    if extra: e.append(f"contributor has non-public fields {sorted(extra)}")
    if c.get("display") not in ("named", "anonymous"): e.append("contributor.display must be 'named' or 'anonymous'")
    if c.get("role") not in ROLES: e.append(f"contributor.role must be one of {sorted(ROLES)}")
    if c.get("display") == "named" and not _str(c.get("name")): e.append("named contributor needs a name")
    if c.get("display") == "anonymous" and (c.get("name") or c.get("affiliation")):
        e.append("anonymous contributor must not carry name or affiliation")


def check_corrections(cs, e):
    if cs is None: return
    if not isinstance(cs, list): e.append("corrections must be a list"); return
    for c in cs:
        if not (isinstance(c, dict) and _str(c.get("note")) and isinstance(c.get("at"), str) and ISO.match(c["at"])):
            e.append(f"correction needs at (ISO time) and note: {c!r}")
        elif set(c) - {"at", "note", "by", "i18n"}:
            e.append(f"correction has unknown fields {sorted(set(c) - {'at', 'note', 'by', 'i18n'})}")


def _check_i18n(tr, fields, e, extra_ok=()):
    if not isinstance(tr, dict): e.append("i18n must be an object"); return {}
    for l, d in tr.items():
        if l not in LANGS: e.append(f"i18n has unknown language {l!r}"); continue
        if not isinstance(d, dict): e.append(f"i18n[{l}] must be an object"); continue
        for k, v in d.items():
            if k in fields:
                if not isinstance(v, str): e.append(f"i18n[{l}].{k} must be a string")
            elif k == "method":
                if v not in METHODS: e.append(f"i18n[{l}].method must be one of {sorted(METHODS)}")
            elif k == "by":
                if not isinstance(v, str): e.append(f"i18n[{l}].by must be a string")
            elif k in extra_ok: pass
            else: e.append(f"i18n[{l}] has unknown field {k!r}")
    return tr


def check_entry(en, public=True):
    """public=True: rules for data/today.json. public=False: a draft in the private store."""
    e, w = [], []
    if not _str(en.get("id")): e.append("missing id")
    st = en.get("status")
    if st not in STATUS: e.append(f"status must be one of {sorted(STATUS)}")
    if public and st != "published":
        e.append(f"status {st!r} not allowed in data/today.json (drafts stay in the private store)")
    if public:
        extra = set(en) - PUBLIC_ENTRY_KEYS
        if extra: e.append(f"non-public fields in a public entry: {sorted(extra)}")
        leak = _private_leak(en)
        if leak: e.append(f"public entry mentions private-store material: {leak}")
    for f in ("headline", "what_happened"):
        if not _str(en.get(f)): e.append(f"missing {f}")
    for f in ("event_at", "assessed_at", "approved_at"):
        v = en.get(f)
        if v is not None and not (isinstance(v, str) and (ISO.match(v) or DATE.match(v))): e.append(f"bad {f} {v!r}")
    if en.get("verification") not in VERIF: e.append(f"verification must be one of {sorted(VERIF)}")
    if en.get("classification") not in CLASS: e.append(f"classification must be one of {sorted(CLASS)}")
    src = en.get("sources")
    check_sources(src, e, public)
    basis = en.get("basis") or {}
    if not isinstance(basis, dict): e.append("basis must be an object"); basis = {}
    for k, v in basis.items():
        if k not in BASIS_FIELDS: e.append(f"basis has unknown field {k!r}")
        elif v not in BASIS: e.append(f"basis.{k} must be one of {sorted(BASIS)}")
    # an interpretation must never be presented as the factual core of the card
    if basis.get("what_happened") == "analysis":
        e.append("what_happened cannot rest on analysis: report what happened, and put interpretation in why_it_matters")
    if "verified" in basis.values() and isinstance(src, list):
        if not any(isinstance(s, dict) and s.get("kind", "official") == "official" and s.get("verified") is True for s in src):
            e.append("a field marked 'verified' needs an official source marked verified: true")
    check_contributor(en.get("contributor"), e)
    if en.get("contributor") and not basis:
        e.append("an entry from a contributor must label each field's basis (verified/attributed/analysis/unverified)")
    check_corrections(en.get("corrections"), e)
    for k in ("areas", "actors", "related"):
        v = en.get(k)
        if v is not None and not (isinstance(v, list) and all(_str(x) for x in v)): e.append(f"{k} must be a list of strings")
    if en.get("article") is not None and not (isinstance(en["article"], str) and SLUG.match(en["article"])):
        e.append("article must be an article id")
    for f in TEXT_FIELDS:
        v = en.get(f)
        if isinstance(v, str) and "<" in v: w.append(f"{f} contains '<' (rendered as text)")
    tr = _check_i18n(en.get("i18n") or {}, TEXT_FIELDS, e)
    pending = en.get("i18n_pending", [])
    if not isinstance(pending, list) or any(l not in LANGS for l in pending): e.append("i18n_pending must list language codes")
    if st == "published":
        if not _str(en.get("approved_by")): e.append("published entry needs approved_by (human approval)")
        if not en.get("approved_at"): e.append("published entry needs approved_at")
        if isinstance(src, list) and not any(isinstance(s, dict) and s.get("verified") is True for s in src):
            e.append("published entry needs at least one source with verified: true")
        texts = [en.get(f) for f in TEXT_FIELDS] + [v for d in tr.values() if isinstance(d, dict) for k, v in d.items() if k in TEXT_FIELDS]
        if any(_markers(v) for v in texts): e.append("published entry still contains review markers ([preencher]/[revisar])")
        for l in LANGS:
            if l in (pending if isinstance(pending, list) else []): continue
            d = tr.get(l) if isinstance(tr.get(l), dict) else {}
            miss = [f for f in TEXT_FIELDS if _str(en.get(f)) and not _str(d.get(f))]
            if miss: e.append(f"translation {l} missing {', '.join(miss)} (translate, or list {l} in i18n_pending)")
    return e, w


def check_article(a, public=True):
    """A full readout (data/articles/<id>.json when published)."""
    e, w = [], []
    if not isinstance(a, dict): return ["article is not an object"], w
    if a.get("schema") != 1: e.append("article schema must be 1")
    if not (isinstance(a.get("id"), str) and SLUG.match(a["id"])): e.append("article id must be a lowercase slug")
    st = a.get("status")
    if st not in STATUS: e.append(f"status must be one of {sorted(STATUS)}")
    if public:
        if st != "published": e.append("only published articles may be public")
        extra = set(a) - ARTICLE_KEYS
        if extra: e.append(f"non-public fields in a public article: {sorted(extra)}")
        leak = _private_leak(a)
        if leak: e.append(f"public article mentions private-store material: {leak}")
    if not _str(a.get("title")): e.append("missing title")
    if not (isinstance(a.get("entries"), list) and a["entries"] and all(_str(x) for x in a["entries"])):
        e.append("article needs entries: the ids of the Today cards it expands")
    blocks = a.get("blocks")
    if not isinstance(blocks, list) or not blocks: e.append("article needs blocks"); blocks = []
    for i, b in enumerate(blocks):
        if not (isinstance(b, dict) and _str(b.get("md"))): e.append(f"block {i} needs md"); continue
        if b.get("basis") not in BASIS: e.append(f"block {i} basis must be one of {sorted(BASIS)}")
        if set(b) - {"basis", "heading", "md"}: e.append(f"block {i} has unknown fields")
        if "<" in b["md"]: e.append(f"block {i}: raw HTML is not allowed in md")
        for u in re.findall(r"\]\(([^)]*)\)", b["md"]):
            if not u.startswith("https://"): e.append(f"block {i}: links must be https ({u})")
    check_sources(a.get("sources"), e, public)
    check_contributor(a.get("contributor"), e)
    check_corrections(a.get("corrections"), e)
    tr = _check_i18n(a.get("i18n") or {}, ARTICLE_TEXT, e, extra_ok=("blocks",))
    for l, d in tr.items():
        if isinstance(d, dict) and "blocks" in d:
            bl = d["blocks"]
            if not (isinstance(bl, list) and len(bl) == len(blocks) and all(isinstance(x, dict) and _str(x.get("md")) for x in bl)):
                e.append(f"i18n[{l}].blocks must translate every block (same count, each with md)")
    pending = a.get("i18n_pending", [])
    if not isinstance(pending, list) or any(l not in LANGS for l in pending): e.append("i18n_pending must list language codes")
    if st == "published":
        if not _str(a.get("approved_by")) or not a.get("approved_at"): e.append("published article needs approved_by and approved_at")
        texts = [a.get(f) for f in ARTICLE_TEXT] + [b.get("md") for b in blocks if isinstance(b, dict)]
        if any(_markers(v) for v in texts): e.append("published article still contains review markers")
        for l in LANGS:
            if l in (pending if isinstance(pending, list) else []): continue
            d = tr.get(l) if isinstance(tr.get(l), dict) else {}
            if not (_str(d.get("title")) and isinstance(d.get("blocks"), list)):
                e.append(f"article translation {l} missing (translate, or list {l} in i18n_pending)")
    return e, w


def check_today(doc, public=True, articles=None, feed_ids=None):
    fatal, per = [], {}
    if not isinstance(doc, dict) or doc.get("schema") != 1: return ["today file must be an object with schema 1"], per
    if not isinstance(doc.get("entries"), list): return ["entries must be a list"], per
    if public and set(doc) - {"schema", "updated_at", "entries", "retractions"}:
        fatal.append(f"today file has unknown top-level fields {sorted(set(doc) - {'schema', 'updated_at', 'entries', 'retractions'})}")
    for r in doc.get("retractions") or []:
        if not (isinstance(r, dict) and _str(r.get("id")) and _str(r.get("reason")) and isinstance(r.get("retracted_at"), str)):
            fatal.append(f"retraction needs id, retracted_at and reason: {r!r}")
    seen = set()
    for i, en in enumerate(doc["entries"]):
        e, w = check_entry(en, public) if isinstance(en, dict) else (["entry is not an object"], [])
        if isinstance(en, dict):
            if articles is not None and en.get("article") and en["article"] not in articles:
                e.append(f"article {en['article']!r} is not published in data/articles/")
            if feed_ids is not None:
                for r in en.get("related") or []:
                    if r not in feed_ids: w.append(f"related feed item {r!r} not found in data/feed.json")
        k = (en.get("id") if isinstance(en, dict) else None) or f"#{i}"
        if k in seen: e.append("duplicate id")
        seen.add(k)
        if e or w: per[k] = (e, w)
    return fatal, per


def report(name, fatal, per, quiet_warnings=False):
    bad = 0
    for f in fatal: print(f"{name}: FATAL {f}")
    for k, (e, w) in per.items():
        for x in e: print(f"{name}: {k}: ERROR {x}")
        if not quiet_warnings:
            for x in w: print(f"{name}: {k}: warn {x}")
        bad += bool(e)
    return bool(fatal) or bad > 0


def main(argv):
    quiet = "-q" in argv
    argv = [a for a in argv if a != "-q"]
    today = None
    if "--today" in argv:
        i = argv.index("--today"); today = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    feed_path = argv[0] if argv else ROOT / "data" / "feed.json"
    feed = json.loads(pathlib.Path(feed_path).read_text(encoding="utf-8"))
    failed = report("feed", *check_feed(feed), quiet_warnings=quiet)
    tp = pathlib.Path(today) if today else ROOT / "data" / "today.json"
    adir = tp.parent / "articles"
    articles = {}
    for ap in sorted(adir.glob("*.json")) if adir.is_dir() else []:
        a = json.loads(ap.read_text(encoding="utf-8"))
        e, w = check_article(a, public=True)
        if isinstance(a, dict) and a.get("id") != ap.stem: e.append(f"file name must be the article id ({a.get('id')!r})")
        failed |= report("article", [], {ap.name: (e, w)} if e or w else {}, quiet_warnings=quiet)
        if isinstance(a, dict) and a.get("id"): articles[a["id"]] = a
    if tp.exists():
        ids = {it.get("id") for it in feed.get("items") or [] if isinstance(it, dict)}
        failed |= report("today", *check_today(json.loads(tp.read_text(encoding="utf-8")), articles=articles, feed_ids=ids), quiet_warnings=quiet)
    print("FAILED" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
