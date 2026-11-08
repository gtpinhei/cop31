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


# ---- today.json (editor-curated "Hoje na COP31")
# data/today.json is public: it may hold ONLY published, human-approved entries, complete in all
# seven languages. Drafts live in editorial/drafts.json, which is gitignored and never deployed.
STATUS = {"draft", "published", "retracted"}
VERIF = {"confirmado", "fonte única", "não confirmado"}
CLASS = {"decisão", "sinal político", "anúncio", "disputa", "processo", "análise"}
TEXT_FIELDS = ("headline", "what_happened", "what_changed", "why_it_matters", "watch_next")
METHODS = {"human", "machine-reviewed", "machine"}
MARKERS = ("[preencher]", "[revisar]", "[todo]", "TODO")


def _markers(v):
    return isinstance(v, str) and any(m in v for m in MARKERS)


def check_entry(en, public=True):
    """public=True: rules for data/today.json. public=False: a draft in editorial/drafts.json."""
    e, w = [], []
    if not _str(en.get("id")): e.append("missing id")
    st = en.get("status")
    if st not in STATUS: e.append(f"status must be one of {sorted(STATUS)}")
    if public and st != "published":
        e.append(f"status {st!r} not allowed in data/today.json (keep drafts in editorial/drafts.json)")
    for f in ("headline", "what_happened"):
        if not _str(en.get(f)): e.append(f"missing {f}")
    for f in ("event_at", "assessed_at", "approved_at"):
        v = en.get(f)
        if v is not None and not (isinstance(v, str) and (ISO.match(v) or DATE.match(v))): e.append(f"bad {f} {v!r}")
    if en.get("verification") not in VERIF: e.append(f"verification must be one of {sorted(VERIF)}")
    if en.get("classification") not in CLASS: e.append(f"classification must be one of {sorted(CLASS)}")
    src = en.get("sources")
    if not isinstance(src, list) or not src: e.append("at least one source required")
    else:
        for s in src:
            if not (isinstance(s, dict) and isinstance(s.get("url"), str) and s["url"].startswith("https://")):
                e.append(f"source needs an https url: {s!r}")
    for f in TEXT_FIELDS:
        v = en.get(f)
        if isinstance(v, str) and "<" in v: w.append(f"{f} contains '<' (rendered as text)")
    tr = en.get("i18n") or {}
    if not isinstance(tr, dict): e.append("i18n must be an object"); tr = {}
    for l, d in tr.items():
        if l not in LANGS: e.append(f"i18n has unknown language {l!r}"); continue
        if not isinstance(d, dict): e.append(f"i18n[{l}] must be an object"); continue
        for k, v in d.items():
            if k in TEXT_FIELDS:
                if not isinstance(v, str): e.append(f"i18n[{l}].{k} must be a string")
            elif k == "method":
                if v not in METHODS: e.append(f"i18n[{l}].method must be one of {sorted(METHODS)}")
            elif k == "by":
                if not isinstance(v, str): e.append(f"i18n[{l}].by must be a string")
            else: e.append(f"i18n[{l}] has unknown field {k!r}")
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


def check_today(doc, public=True):
    fatal, per = [], {}
    if not isinstance(doc, dict) or doc.get("schema") != 1: return ["today file must be an object with schema 1"], per
    if not isinstance(doc.get("entries"), list): return ["entries must be a list"], per
    seen = set()
    for i, en in enumerate(doc["entries"]):
        e, w = check_entry(en, public) if isinstance(en, dict) else (["entry is not an object"], [])
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
    failed = report("feed", *check_feed(json.loads(pathlib.Path(feed_path).read_text(encoding="utf-8"))), quiet_warnings=quiet)
    tp = pathlib.Path(today) if today else ROOT / "data" / "today.json"
    if tp.exists():
        failed |= report("today", *check_today(json.loads(tp.read_text(encoding="utf-8"))), quiet_warnings=quiet)
    print("FAILED" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
