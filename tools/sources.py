#!/usr/bin/env python3
"""Source registry for the COP31 monitoring agents.

The registry is the single list of everything the agents monitor: websites, RSS feeds and social
accounts, with stable ids, priority, collection method, cadence, status, identity, provenance and
health. It lives in the private store (tools/private.py), never in the repository, and never inside
data/feed.json (which holds collected outputs only). The agents read generated views; they never
edit the registry. They report what happened to each source in a status file and may propose new
sources there; the hourly sync folds those reports back in (`ingest`).

  python3 -I tools/sources.py import-legacy SOCIAL_WATCHLIST.json WEB_WATCHLIST.json [FEED.json]
  python3 -I tools/sources.py plan BATCH.txt --by EDITOR > plan.json   # parse + dedupe + what to probe
  python3 -I tools/sources.py apply plan.json probes.json --by EDITOR  # identity + activation rules
  python3 -I tools/sources.py ingest STATUS.json [...]                 # agents' run reports + proposals
  python3 -I tools/sources.py set ID FIELD VALUE --by EDITOR           # priority|status|category|themes|...
  python3 -I tools/sources.py approve ID --by EDITOR | reject ID --reason "..." --by EDITOR | retire ID --reason "..." --by EDITOR
  python3 -I tools/sources.py export OUT_DIR [--pulse data/pulse.json] # agent views, dashboard, report
  python3 -I tools/sources.py validate | report | show ID

Batch lines: a URL, a handle (@x_handle with --platform or "x:handle", "bsky:handle", "ig:handle",
"yt:@handle") and optional "| key=value" pairs: institution, category, priority, themes (a,b),
language, rights, note. Lines starting with # are ignored.

Statuses: proposed (by an agent) → pending_review → active | rejected; active → paused | retired.
Health outcomes per attempt: success, success_empty (read fine, nothing new), blocked (refused,
login wall, client_error), unavailable (does not exist / 404), error. A blocked or unavailable source
is never counted as "nothing new".
"""
import datetime, hashlib, json, pathlib, re, sys, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools"))
import private as P  # noqa: E402

TRACKS = ["Finanças", "Adaptação", "Transição justa", "Mitigação e MWP", "TAFF e fósseis", "Eletrificação",
          "GST2 e IPCC", "Perdas e danos", "Florestas", "Comércio", "Agenda de Ação", "Decisão de cobertura",
          "Presidência e anfitrião", "Espaço cívico", "Oceanos"]
CATEGORIES = {"presidency", "unfccc", "government", "multilateral", "negotiating_group",       # official
              "research", "civil_society", "media", "journalist", "business", "individual", "other"}
OFFICIAL = {"presidency", "unfccc", "government", "multilateral", "negotiating_group"}
SOCIAL = {"bluesky", "x", "instagram", "youtube"}
COLLECTABLE = SOCIAL | {"web", "rss"}
MANUAL = {"linkedin", "whatsapp", "tiktok", "facebook", "telegram", "threads"}
STATUSES = {"proposed", "pending_review", "active", "paused", "rejected", "retired"}
OUTCOMES = {"success", "success_empty", "blocked", "unavailable", "error", "skipped"}
RIGHTS = {"link_and_summary", "link_only"}   # neither allows republishing full content
METHOD = {"bluesky": "nimble vx6: public.api.bsky.app getAuthorFeed (JSON)",
          "x": "nimble vx10 x.com/<handle>, wait 4000–6000",
          "instagram": "nimble vx10 instagram.com/<handle>/ (embedded JSON)",
          "youtube": "nimble vx6 youtube.com/feeds/videos.xml?channel_id=<id>",
          "web": "WebFetch; Nimble extract when blocked", "rss": "WebFetch of the feed"}
AGENT = {**{p: "social" for p in SOCIAL}, "web": "web", "rss": "web"}
RULES = {
    "auto_activate": "official category (presidency, unfccc, government, multilateral, negotiating_group) "
                     "+ identity checked + a successful probe with the collector's own method",
    "review": "everything else that is collectable and reachable (unverified or third-party-reported identity, "
              "non-official categories, blocked probes)",
    "reject": "invalid input, duplicate of a registered source, platform not collectable by the agents, "
              "source that does not exist (probe: unavailable)",
    "identity_checked": "Bluesky domain handle that resolves; or an official page (evidence_url) that links the "
                        "account; or, for websites, the institution's own domain",
    "never": "an inaccessible source is never reported as having published nothing; content is linked and "
             "summarised, never republished (rights: link_and_summary or link_only)",
}


def now():
    return P.now()


def reg_path():
    return P.ensure() / "sources" / "registry.json"


def load():
    p = reg_path()
    return P.load_json(p, {"schema": 1, "updated_at": None, "rules": RULES, "sources": []})


def save(reg, why):
    reg["updated_at"] = now()
    reg["rules"] = RULES
    errs, _ = validate(reg)
    if errs:
        sys.exit("registry would be invalid:\n- " + "\n- ".join(errs[:20]))
    (P.ensure() / "sources").mkdir(exist_ok=True)
    P.save_json(reg_path(), reg)
    with open(P.ensure() / "sources" / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": now(), "event": why}, ensure_ascii=False) + "\n")


def opt(a, k, d=None):
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d


def slug(s, n=48):
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return s[:n].strip("-")


# ---------- parsing and identity of an input line ----------
def norm_url(u):
    p = urllib.parse.urlsplit(u.strip())
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+$", "", p.path or "")
    return f"{host}{path}" + (f"?{p.query}" if p.query else "")


def parse_target(t, platform=None):
    """→ (platform, handle_or_url, error). Handles are returned without @ except YouTube's @name."""
    t = t.strip()
    m = re.match(r"^(x|twitter|bsky|bluesky|ig|instagram|yt|youtube):(.+)$", t, re.I)
    if m:
        platform = {"twitter": "x", "bsky": "bluesky", "ig": "instagram", "yt": "youtube"}.get(m[1].lower(), m[1].lower())
        t = m[2].strip()
    if re.match(r"^https?://", t, re.I):
        p = urllib.parse.urlsplit(t)
        host = (p.hostname or "").lower().removeprefix("www.").removeprefix("m.")
        seg = [s for s in p.path.split("/") if s]
        if host in ("x.com", "twitter.com"):
            return ("x", seg[0], None) if seg and seg[0] not in ("i", "home", "search", "intent") else (None, t, "not a profile URL")
        if host == "bsky.app":
            return ("bluesky", seg[1], None) if len(seg) >= 2 and seg[0] == "profile" else (None, t, "not a profile URL")
        if host == "instagram.com":
            return ("instagram", seg[0], None) if seg and seg[0] not in ("p", "reel", "explore") else (None, t, "not a profile URL")
        if host == "youtube.com":
            if seg and seg[0].startswith("@"):
                return "youtube", seg[0], None
            if len(seg) >= 2 and seg[0] == "channel":
                return "youtube", seg[1], None
            return None, t, "not a channel URL"
        for mp in MANUAL:
            if host == f"{mp}.com" or host.endswith(f".{mp}.com") or (mp == "whatsapp" and host == "chat.whatsapp.com"):
                return mp, t, None
        if host in ("t.me",):
            return "telegram", t, None
        if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", host):
            return None, t, "invalid host"
        is_feed = bool(re.search(r"(/feed/?$|/rss|\.xml$|\.rss$|atom)", p.path, re.I))
        return ("rss" if is_feed else "web"), t, None
    h = t.lstrip("@")
    if not platform:
        if re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", h, re.I):
            return "bluesky", h.lower(), None
        return None, t, "handle without platform (use x:, ig:, bsky: or yt:)"
    if platform == "youtube":
        return "youtube", (t if t.startswith("@") or t.startswith("UC") else "@" + h), None
    if platform == "bluesky":
        return ("bluesky", h.lower(), None) if "." in h else ("bluesky", h.lower() + ".bsky.social", None)
    if not re.match(r"^[A-Za-z0-9_.]{1,30}$", h):
        return None, t, "invalid handle"
    return platform, h, None


def key_of(s):
    pl = s["platform"]
    if pl in SOCIAL:
        h = (s.get("channel_id") if pl == "youtube" and s.get("channel_id") else s["handle"]).lower()
        return f"{pl}:{h.lstrip('@')}"
    if pl in ("web", "rss"):
        return f"{pl}:{norm_url(s['urls'][0])}"
    return f"{pl}:{(s.get('urls') or [s.get('handle', '')])[0].lower()}"


def all_keys(s):
    ks = {key_of(s)}
    for u in (s.get("urls") or [])[1:]:
        ks.add(f"{s['platform']}:{norm_url(u)}")
    if s.get("platform") == "youtube" and s.get("handle"):
        ks.add(f"youtube:{s['handle'].lower().lstrip('@')}")
    for a in s.get("aliases") or []:
        ks.add(f"{s['platform']}:{a.lower().lstrip('@')}")
    return ks


def domain(s):
    if s.get("urls"):
        return norm_url(s["urls"][0]).split("/")[0]
    h = s.get("handle") or ""
    return h.lower() if s.get("platform") == "bluesky" and not h.endswith(".bsky.social") else None


def new_id(s, taken):
    base = {"bluesky": "bsky", "instagram": "ig", "youtube": "yt"}.get(s["platform"], s["platform"])
    tail = s.get("handle") if s["platform"] in SOCIAL else norm_url(s["urls"][0]) if s.get("urls") else s.get("handle")
    i = f"{base}-{slug(tail)}"
    if i in taken:
        i = f"{i}-{hashlib.sha1(json.dumps(s, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:4]}"
    return i


def cadence_for(platform, priority):
    if platform in SOCIAL:
        return {"A": "every_run", "B": "daily", "C": "weekly"}[priority]
    return {"A": "every_run", "B": "every_run", "C": "daily"}[priority]


def blank(platform, target, institution, category, priority, by, origin, **kw):
    s = {"platform": platform, "institution": institution or "", "category": category or "other",
         "themes": kw.get("themes") or [], "priority": priority or "B", "language": kw.get("language"),
         "status": "pending_review", "rights": kw.get("rights") or "link_and_summary",
         "collection": {"agent": AGENT.get(platform, "none"), "method": METHOD.get(platform, "manual (not accessible to agents)"),
                        "cadence": cadence_for(platform, priority or "B") if platform in COLLECTABLE else "manual"},
         "identity": {"status": "unverified", "basis": None, "evidence_url": None, "checked_at": None, "checked_by": None},
         "provenance": {"added_at": now(), "added_by": by, "origin": origin, "note": kw.get("note")},
         "health": {"last_attempt": None, "last_success": None, "last_outcome": None, "consecutive_failures": 0,
                    "latest_item_date": None, "history": []},
         "notes": kw.get("notes")}
    if platform in SOCIAL:
        s["handle"] = target
        if platform == "youtube":
            s["channel_id"] = target if target.startswith("UC") else None
    else:
        s["urls"] = [target]
    return s


# ---------- validation and duplicate detection ----------
def validate(reg):
    errs, warns = [], []
    ids, keys = set(), {}
    for s in reg["sources"]:
        i = s.get("id")
        if not i or not re.match(r"^[a-z0-9][a-z0-9-]{2,80}$", i):
            errs.append(f"bad id {i!r}"); continue
        if i in ids:
            errs.append(f"duplicate id {i}")
        ids.add(i)
        if s.get("platform") not in COLLECTABLE | MANUAL:
            errs.append(f"{i}: unknown platform {s.get('platform')!r}")
        if s.get("status") not in STATUSES:
            errs.append(f"{i}: bad status {s.get('status')!r}")
        if s.get("priority") not in ("A", "B", "C"):
            errs.append(f"{i}: priority must be A, B or C")
        if s.get("category") not in CATEGORIES:
            errs.append(f"{i}: bad category {s.get('category')!r}")
        if s.get("rights") not in RIGHTS:
            errs.append(f"{i}: rights must be one of {sorted(RIGHTS)}")
        bad = [t for t in s.get("themes") or [] if t not in TRACKS]
        if bad:
            errs.append(f"{i}: unknown themes {bad}")
        if s.get("status") == "active" and s.get("platform") not in COLLECTABLE:
            errs.append(f"{i}: only collectable platforms can be active")
        if s.get("status") == "rejected" and not (s.get("decision") or {}).get("reason"):
            errs.append(f"{i}: rejected without a documented reason")
        if s.get("platform") in SOCIAL and not s.get("handle"):
            errs.append(f"{i}: social source without handle")
        if s.get("platform") in ("web", "rss") and not s.get("urls"):
            errs.append(f"{i}: web source without urls")
        if s.get("status") in ("rejected", "retired"):
            continue
        for k in all_keys(s):
            if k in keys and keys[k] != i:
                errs.append(f"{i}: same target as {keys[k]} ({k})")
            keys.setdefault(k, i)
    # near duplicates: same institution and platform, or same web domain, among live sources
    live = [s for s in reg["sources"] if s.get("status") not in ("rejected", "retired")]
    seen = {}
    for s in live:
        if s.get("platform") in ("web", "rss"):
            k = ("domain", domain(s))
        else:
            k = (s.get("platform"), slug(s.get("institution", "")))
        if k in seen:
            warns.append(f"possible duplicate: {s['id']} and {seen[k]} ({k[0]} {k[1]})")
        else:
            seen[k] = s["id"]
    return errs, warns


def find_dup(reg, cand):
    ks = all_keys(cand)
    for s in reg["sources"]:
        if s.get("status") in ("rejected",):
            continue
        if ks & all_keys(s):
            return s["id"]
    return None


# ---------- legacy import ----------
VER = {"página": ("checked", "official-page"), "reportado": ("reported", "third-party report")}


def guess_category(inst):
    i = inst.lower()
    table = [("presidency", ["presidência da cop", "cop31 presidency", "murat kurum", "fatma varank", "samed ağırbaş",
                             "chris bowen", "high-level champion", "circle of finance"]),
             ("unfccc", ["unfccc", "simon stiell", "baku to belém"]),
             ("negotiating_group", ["aosis", "ldc group", "coalition for rainforest", "caricom", "v20", "arab group"]),
             ("government", ["ministério", "itamaraty", "mma (brasil)", "lula", "dcceew", "moefcc", "bhupender", "bayraktar",
                             "comissão europeia", "conselho da ue", "presidência irlandesa", "hoekstra", "fahnbulleh", "desnz"]),
             ("multilateral", ["unep", "ipcc", "iea ", "iea world", "ihleg"]),
             ("media", ["carbon brief", "climate home", "carbon pulse", "iisd / enb", "bianet", "turkey recap", "medyascope"]),
             ("journalist", ["(reuters)", "(the guardian)", "(ap)", "(le monde)", "(carbon brief)", "(climate home)"]),
             ("business", ["we mean business", "icc", "wbcsd"]),
             ("civil_society", ["can ", "greenpeace", "350.org", "oil change", "power shift", "halkların", "loss and damage",
                                "amnesty", "wwf", "oxfam", "christian aid", "actionaid", "friends of the earth", "demand climate",
                                "ituc", "observatório", "global witness", "eurodad", "bretton woods", "third world network", "nrdc"])]
    for cat, words in table:
        if any(w in i for w in words):
            return cat
    return "research"


def import_legacy(a):
    social = json.loads(pathlib.Path(a[1]).read_text(encoding="utf-8"))
    web = json.loads(pathlib.Path(a[2]).read_text(encoding="utf-8"))
    feed = json.loads(pathlib.Path(a[3]).read_text(encoding="utf-8")) if len(a) > 3 and not a[3].startswith("--") else {}
    by = opt(a, "--by", "legacy import")
    reg = load()
    if reg["sources"]:
        sys.exit("registry already has sources: import-legacy only seeds an empty registry")
    taken, dups = set(), []
    seen_items = {}
    for it in feed.get("items") or []:
        k = (it.get("platform"), str(it.get("account") or "").lstrip("@").lower()) if it.get("kind") == "post" else ("web", it.get("institution"))
        if it.get("date") and it["date"] > seen_items.get(k, ""):
            seen_items[k] = it["date"]
    for acc in social.get("accounts") or []:
        pl, h = acc["platform"], acc["handle"].lstrip("@") if acc["platform"] in ("x", "instagram") else acc["handle"]
        s = blank(pl, h, acc["institution"], guess_category(acc["institution"]), acc.get("priority", "B"), by,
                  "legacy-watchlist-social", note=acc.get("note"))
        if pl == "youtube":
            s["channel_id"] = acc.get("channel_id")
        if acc.get("alt_handle"):
            s["aliases"] = [acc["alt_handle"]]
        st, basis = VER.get(str(acc.get("verified") or "").split(" ")[0], ("unverified", acc.get("verified") or "prior knowledge"))
        if "resolver" in str(acc.get("verified")):
            st = "unverified"
        s["identity"].update(status=st, basis=acc.get("verified") or basis, checked_at="2026-11-07" if st == "checked" else None)
        s["status"] = "paused" if acc.get("inactive") else "active"
        if acc.get("inactive"):
            s["decision"] = {"at": now(), "by": by, "reason": acc.get("note") or "marked inactive in the legacy watchlist"}
        s["health"]["latest_item_date"] = seen_items.get((pl, h.lower()))
        s["id"] = new_id(s, taken); taken.add(s["id"])
        if find_dup(reg, s):
            dups.append((s["id"], find_dup(reg, s))); continue
        reg["sources"].append(s)
    for m in social.get("manual_only") or []:
        urls = list((m.get("channels") or {}).values()) or [f"https://{m['platform']}.com/"]
        s = blank(m["platform"], urls[0], m["institution"], guess_category(m["institution"]), "C", by, "legacy-watchlist-social",
                  note=m.get("note"))
        s["urls"] = urls
        s["status"] = "rejected"
        s["decision"] = {"at": now(), "by": by, "reason": "not_collectable: platform not accessible to the agents; follow manually"}
        s["id"] = new_id(s, taken); taken.add(s["id"])
        reg["sources"].append(s)
    for w in web:
        urls = list(dict.fromkeys(w["urls"]))
        s = blank("web", urls[0], w["institution"], guess_category(w["institution"]), "B", by, "legacy-watchlist-web",
                  notes=w.get("notes"), language=w.get("language"))
        s["urls"] = urls
        if w.get("rss"):
            s["rss"] = w["rss"]
        s["identity"].update(status="checked", basis="institution's own domain (legacy watchlist)")
        if any(d in norm_url(urls[0]) for d in ("unfccc.int", "cop31.tr", "consilium.europa.eu", "cop30.br", "unep.org", "ipcc.ch", "iea.org")):
            s["priority"] = "A"
            s["collection"]["cadence"] = "every_run"
        s["status"] = "active"
        s["health"]["latest_item_date"] = seen_items.get(("web", w["institution"]))
        s["id"] = new_id(s, taken); taken.add(s["id"])
        d = find_dup(reg, s)
        if d:
            # legacy web lists repeat institutions with overlapping URLs: merge the extra URLs instead of duplicating
            tgt = next(x for x in reg["sources"] if x["id"] == d)
            extra = [u for u in urls if f"web:{norm_url(u)}" not in all_keys(tgt)]
            tgt["urls"] += extra
            tgt.setdefault("aliases_institution", []).append(w["institution"])
            dups.append((s["id"], d)); continue
        reg["sources"].append(s)
    save(reg, f"import-legacy by {by}")
    print(f"imported {len(reg['sources'])} sources; merged {len(dups)} duplicates: {dups}")


# ---------- batch: plan → probe → apply ----------
def plan(a):
    lines = pathlib.Path(a[1]).read_text(encoding="utf-8").splitlines() if a[1] != "-" else sys.stdin.read().splitlines()
    by = opt(a, "--by") or sys.exit("--by EDITOR is required")
    reg = load()
    out, taken = [], {s["id"] for s in reg["sources"]}
    batch_keys = {}
    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        meta = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
        meta = {k.strip().lower(): v.strip() for k, v in meta.items()}
        c = {"line": n, "input": parts[0], "meta": meta}
        pl, tgt, err = parse_target(parts[0], meta.get("platform"))
        if err:
            c.update(decision="reject", reason=f"invalid: {err}"); out.append(c); continue
        pri = meta.get("priority", "B").upper()
        cat = meta.get("category", "other")
        themes = [t.strip() for t in meta.get("themes", "").split(",") if t.strip()]
        problems = []
        if pri not in ("A", "B", "C"): problems.append("priority must be A, B or C")
        if cat not in CATEGORIES: problems.append(f"category must be one of {sorted(CATEGORIES)}")
        if [t for t in themes if t not in TRACKS]: problems.append(f"unknown themes {[t for t in themes if t not in TRACKS]}")
        if meta.get("rights", "link_and_summary") not in RIGHTS: problems.append("rights must be link_and_summary or link_only")
        if problems:
            c.update(decision="reject", reason="invalid: " + "; ".join(problems)); out.append(c); continue
        s = blank(pl, tgt, meta.get("institution"), cat, pri, by, "batch", themes=themes, language=meta.get("language"),
                  rights=meta.get("rights"), note=meta.get("note"))
        s["id"] = new_id(s, taken); taken.add(s["id"])
        d = find_dup(reg, s)
        k = key_of(s)
        if d:
            c.update(decision="reject", reason=f"duplicate of {d}", source=s)
        elif k in batch_keys:
            c.update(decision="reject", reason=f"duplicate of line {batch_keys[k]} in this batch", source=s)
        elif pl not in COLLECTABLE:
            c.update(decision="reject", reason="not_collectable: platform not accessible to the agents; follow manually", source=s)
        else:
            batch_keys[k] = n
            c.update(decision="probe", source=s, probe=probe_spec(s))
        out.append(c)
    print(json.dumps({"plan_at": now(), "by": by, "candidates": out}, ensure_ascii=False, indent=1))


def probe_spec(s):
    pl = s["platform"]
    if pl == "bluesky":
        return {"tool": "nimble_extract", "driver": "vx6",
                "url": f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={s['handle']}&limit=3&filter=posts_no_replies",
                "identity": "custom-domain handles resolve only if the domain owner set them up" if not s["handle"].endswith(".bsky.social") else "needs an official page linking the handle"}
    if pl == "x":
        return {"tool": "nimble_extract", "driver": "vx10", "wait": 5000, "url": f"https://x.com/{s['handle']}",
                "identity": "find an official page linking the account (evidence_url)"}
    if pl == "instagram":
        return {"tool": "nimble_extract", "driver": "vx10", "url": f"https://www.instagram.com/{s['handle']}/",
                "identity": "find an official page linking the account (evidence_url)"}
    if pl == "youtube":
        return {"tool": "nimble_extract", "driver": "vx6", "url": f"https://www.youtube.com/{s['handle']}" if not s.get("channel_id") else
                f"https://www.youtube.com/feeds/videos.xml?channel_id={s['channel_id']}", "identity": "official page linking the channel"}
    return {"tool": "WebFetch", "url": s["urls"][0], "fallback": "nimble_extract vx10",
            "discover": "title, site name, publisher, language, RSS link, latest dated item, links to social accounts"}


def apply(a):
    plan_doc = json.loads(pathlib.Path(a[1]).read_text(encoding="utf-8"))
    probes = json.loads(pathlib.Path(a[2]).read_text(encoding="utf-8"))
    by = opt(a, "--by") or sys.exit("--by EDITOR is required")
    reg = load()
    res = []
    for c in plan_doc["candidates"]:
        s = c.get("source")
        if c["decision"] == "reject":
            if s:
                s.update(status="rejected", decision={"at": now(), "by": by, "reason": c["reason"]})
                if not c["reason"].startswith("duplicate"):
                    reg["sources"].append(s)
            res.append({"line": c["line"], "input": c["input"], "id": (s or {}).get("id"), "result": "rejected", "reason": c["reason"]})
            continue
        pr = probes.get(str(c["line"])) or probes.get(s["id"]) or {}
        out = pr.get("outcome")
        if out not in OUTCOMES - {"skipped"}:
            s["status"] = "pending_review"
            s["decision"] = {"at": now(), "by": by, "reason": "not probed yet"}
            reg["sources"].append(s)
            res.append({"line": c["line"], "input": c["input"], "id": s["id"], "result": "awaiting_activation", "reason": "not probed yet"})
            continue
        md = pr.get("metadata") or {}
        if not s["institution"]:
            s["institution"] = md.get("institution") or md.get("site_name") or md.get("display_name") or s.get("handle") or domain(s)
        if md.get("language") and not s.get("language"):
            s["language"] = md["language"]
        if md.get("rss") and s["platform"] == "web":
            s["rss"] = md["rss"]
        if md.get("channel_id") and s["platform"] == "youtube":
            s["channel_id"] = md["channel_id"]
        if md.get("paywall"):
            s["rights"] = "link_only"
        s["probe"] = {"at": pr.get("at") or now(), "by": pr.get("by") or by, "method": pr.get("method"), "outcome": out,
                      "evidence": pr.get("evidence"), "metadata": md}
        record(s, {"at": s["probe"]["at"], "agent": "probe", "outcome": out, "latest_item_date": md.get("latest_item_date"),
                   "note": pr.get("note")})
        idn = identity_from_probe(s, pr)
        s["identity"].update(idn, checked_at=s["probe"]["at"] if idn["status"] == "checked" else None, checked_by=by)
        if out == "unavailable":
            s.update(status="rejected", decision={"at": now(), "by": by, "reason": f"unavailable: {pr.get('note') or 'source does not exist'}"})
            result, why = "rejected", s["decision"]["reason"]
        elif out in ("success", "success_empty") and s["identity"]["status"] == "checked" and s["category"] in OFFICIAL:
            s.update(status="active", decision={"at": now(), "by": "rule: auto_activate", "reason": RULES["auto_activate"]})
            result, why = "active", "official source, identity checked, probe succeeded"
        else:
            why = []
            if out not in ("success", "success_empty"):
                why.append(f"probe {out}: {pr.get('note') or ''}".strip())
            if s["identity"]["status"] != "checked":
                why.append(f"identity {s['identity']['status']}")
            if s["category"] not in OFFICIAL:
                why.append(f"category {s['category']} needs editor approval")
            why = "; ".join(why)
            s.update(status="pending_review", decision={"at": now(), "by": "rule: review", "reason": why})
            result = "awaiting_activation"
        reg["sources"].append(s)
        res.append({"line": c["line"], "input": c["input"], "id": s["id"], "result": result, "reason": why,
                    "probe": out, "identity": s["identity"]["status"], "evidence": pr.get("evidence")})
    save(reg, f"batch apply by {by}: {len(res)} lines")
    print(json.dumps(res, ensure_ascii=False, indent=1))


def identity_from_probe(s, pr):
    md = pr.get("metadata") or {}
    ev = pr.get("identity_evidence_url")
    if s["platform"] == "bluesky" and not s["handle"].endswith(".bsky.social") and pr.get("outcome") in ("success", "success_empty"):
        return {"status": "checked", "basis": f"domain handle: {s['handle']} resolves, so the domain owner controls it", "evidence_url": f"https://{s['handle']}"}
    if ev and pr.get("identity_link_found"):
        return {"status": "checked", "basis": "official page links the account", "evidence_url": ev}
    if s["platform"] in ("web", "rss") and pr.get("outcome") in ("success", "success_empty") and md.get("official_domain"):
        return {"status": "checked", "basis": "institution's own domain", "evidence_url": s["urls"][0]}
    if pr.get("reported_by"):
        return {"status": "reported", "basis": f"reported by {pr['reported_by']}", "evidence_url": ev}
    return {"status": "unverified", "basis": md.get("identity_note") or "no official page linking it was found", "evidence_url": ev}


# ---------- health from agent run reports ----------
def record(s, h):
    hl = s["health"]
    if any(x.get("at") == h["at"] and x.get("agent") == h.get("agent") for x in hl["history"]):
        return False
    hl["history"] = (hl["history"] + [{k: v for k, v in h.items() if v is not None}])[-12:]
    out = h["outcome"]
    if out == "skipped":
        return True
    hl["last_attempt"] = max(hl["last_attempt"] or "", h["at"])
    if h.get("agent") != "probe":   # a probe at registration does not count as the agent having collected it
        hl["last_collected"] = max(hl.get("last_collected") or "", h["at"])
    hl["last_outcome"] = out
    if out in ("success", "success_empty"):
        hl["last_success"] = max(hl["last_success"] or "", h["at"])
        hl["consecutive_failures"] = 0
    else:
        hl["consecutive_failures"] = hl.get("consecutive_failures", 0) + 1
    if h.get("latest_item_date") and h["latest_item_date"] > (hl.get("latest_item_date") or ""):
        hl["latest_item_date"] = h["latest_item_date"]
    return True


def ingest(a):
    reg = load()
    byid = {s["id"]: s for s in reg["sources"]}
    n_res = n_prop = n_unknown = 0
    for path in a[1:]:
        st = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        agent, at = st.get("agent", "?"), st.get("run_at")
        if not at:
            continue
        for r in st.get("results") or []:
            s = byid.get(r.get("source_id"))
            if not s or r.get("outcome") not in OUTCOMES:
                n_unknown += 1; continue
            if record(s, {"at": at, "agent": agent, "outcome": r["outcome"], "new_items": r.get("new_items"),
                          "latest_item_date": r.get("latest_item_date"), "note": (r.get("note") or "")[:200] or None}):
                n_res += 1
            disc = r.get("discovered") or {}
            if disc.get("channel_id") and s["platform"] == "youtube" and not s.get("channel_id"):
                s["channel_id"] = disc["channel_id"]
            if r.get("outcome") == "unavailable" and s["health"]["consecutive_failures"] >= 3 and s["status"] == "active":
                s.update(status="paused", decision={"at": now(), "by": "rule: health",
                                                    "reason": f"unavailable in 3 consecutive runs ({r.get('note') or ''})"})
        for p in st.get("proposals") or []:
            pl, tgt, err = parse_target(p.get("target", ""), p.get("platform"))
            if err:
                continue
            s = blank(pl, tgt, p.get("institution"), p.get("category") if p.get("category") in CATEGORIES else "other",
                      p.get("priority") if p.get("priority") in ("A", "B", "C") else "C", f"agent {agent}", "agent-proposal",
                      themes=[t for t in p.get("themes") or [] if t in TRACKS])
            s["status"] = "proposed"
            s["proposal"] = {"at": at, "agent": agent, "relevance": (p.get("relevance") or "")[:500],
                             "evidence_url": p.get("evidence_url"), "identity_evidence_url": p.get("identity_evidence_url")}
            s["id"] = new_id(s, set(byid))
            if find_dup(reg, s):
                continue
            reg["sources"].append(s); byid[s["id"]] = s; n_prop += 1
    save(reg, f"ingest {len(a) - 1} status file(s): {n_res} results, {n_prop} proposals")
    print(f"ingested {n_res} results, {n_prop} new proposals, {n_unknown} unknown results")


# ---------- editor decisions ----------
def decide(a, status):
    reg = load()
    s = next((x for x in reg["sources"] if x["id"] == a[1]), None) or sys.exit(f"no source {a[1]}")
    by = opt(a, "--by") or sys.exit("--by EDITOR is required")
    reason = opt(a, "--reason")
    if status in ("rejected", "retired", "paused") and not reason:
        sys.exit("--reason is required")
    if status == "active" and s["platform"] not in COLLECTABLE:
        sys.exit("only collectable platforms can be activated")
    if status == "active" and s["status"] in ("proposed", "pending_review") and not s.get("probe") and not opt(a, "--without-probe"):
        print("note: activated without a probe; the first agent run will show whether it can be collected")
    s.update(status=status, decision={"at": now(), "by": by, "reason": reason or "editor approval"})
    save(reg, f"{status} {s['id']} by {by}")
    print(f"{s['id']}: {status}")


def set_field(a):
    reg = load()
    s = next((x for x in reg["sources"] if x["id"] == a[1]), None) or sys.exit(f"no source {a[1]}")
    field, val = a[2], a[3]
    by = opt(a, "--by") or sys.exit("--by EDITOR is required")
    if field == "priority":
        s["priority"] = val.upper()
        s["collection"]["cadence"] = cadence_for(s["platform"], s["priority"]) if s["platform"] in COLLECTABLE else "manual"
    elif field == "themes":
        s["themes"] = [t.strip() for t in val.split(",") if t.strip()]
    elif field in ("institution", "category", "language", "rights", "notes", "channel_id"):
        s[field] = val
    elif field == "cadence":
        s["collection"]["cadence"] = val
    elif field == "urls":
        s["urls"] = [u.strip() for u in val.split(",") if u.strip()]
    elif field == "identity":
        st, _, ev = val.partition(" ")
        s["identity"].update(status=st, basis=f"editor: {ev or 'confirmed'}", evidence_url=ev or None, checked_at=now(), checked_by=by)
    else:
        sys.exit("field: priority|themes|institution|category|language|rights|notes|channel_id|cadence|urls|identity")
    s.setdefault("edits", []).append({"at": now(), "by": by, "field": field})
    save(reg, f"set {s['id']} {field} by {by}")
    print(f"{s['id']}: {field} updated")


# ---------- views, dashboard and report ----------
LEGACY_VER = {"checked": "página", "reported": "reportado"}


def legacy_basis(s):
    """The agents' and the Social Pulse's identity wording: legacy text kept verbatim, else mapped."""
    b = s["identity"].get("basis") or ""
    if s["provenance"].get("origin") == "legacy-watchlist-social" and not b.startswith("editor"):
        return b or "não"
    return LEGACY_VER.get(s["identity"]["status"], "não")


def due_view(s):
    h = s["health"]
    agent_runs = [x for x in h["history"] if x.get("agent") != "probe" and x.get("outcome") != "skipped"]
    last = agent_runs[-1] if agent_runs else {}
    ok = [x for x in agent_runs if x.get("outcome") in ("success", "success_empty")]
    return {"last_attempt": h.get("last_collected"), "last_success": ok[-1]["at"] if ok else None, "last_outcome": last.get("outcome")}


def views(reg):
    act = [s for s in reg["sources"] if s["status"] == "active"]
    social = {"schema": 2, "generated_at": now(), "generated_from": "source registry (do not edit; propose changes in the status file)",
              "rules": {"cadence": "every_run = each run; daily = once a day (06:42 Brasília run or not read in 24 h); weekly = once a week",
                        "rights": "link_and_summary: summary, short quotes and link; link_only: summary of the public teaser and link, no quotes; never republish full content",
                        "report": "report every configured source of this view in the status file: success, success_empty, blocked, unavailable, error or skipped (not due). Blocked or unavailable is never 'nothing new'."},
              "methods": METHOD, "notes": (reg.get("agent_notes") or {}).get("social"),
              "accounts": [{"id": s["id"], "institution": s["institution"], "platform": s["platform"], "handle": s["handle"],
                            **({"channel_id": s.get("channel_id")} if s["platform"] == "youtube" else {}),
                            "priority": s["priority"], "cadence": s["collection"]["cadence"],
                            "verified": legacy_basis(s), "rights": s["rights"],
                            **({"note": s["provenance"].get("note")} if s["provenance"].get("note") else {}), **due_view(s)}
                           for s in act if s["platform"] in SOCIAL],
              "manual_only": [{"id": s["id"], "institution": s["institution"], "platform": s["platform"], "urls": s.get("urls")}
                              for s in reg["sources"] if s["platform"] in MANUAL and s["status"] != "retired"]}
    web = {"schema": 2, "generated_at": now(), "generated_from": "source registry (do not edit; propose changes in the status file)",
           "rules": social["rules"], "notes": (reg.get("agent_notes") or {}).get("web"),
           "sites": [{"id": s["id"], "institution": s["institution"], "urls": s["urls"], "rss": s.get("rss"),
                      "language": s.get("language"), "priority": s["priority"], "cadence": s["collection"]["cadence"],
                      "rights": s["rights"], "notes": s.get("notes"), **due_view(s)}
                     for s in sorted(act, key=lambda x: x["priority"]) if s["platform"] in ("web", "rss")]}
    return social, web


def counts(reg):
    from collections import Counter
    src = reg["sources"]
    c = {"total": len(src), "by_status": Counter(s["status"] for s in src),
         "by_platform": Counter(s["platform"] for s in src if s["status"] == "active"),
         "by_priority": Counter(s["priority"] for s in src if s["status"] == "active"),
         "by_category": Counter(s["category"] for s in src if s["status"] == "active")}
    h = Counter()
    for s in src:
        if s["status"] != "active":
            continue
        h["configured"] += 1
        hl = s["health"]
        if not hl["last_attempt"]:
            h["never_attempted"] += 1
        else:
            h["attempted"] += 1
            h[{"success": "successful", "success_empty": "successful", "blocked": "blocked",
               "unavailable": "unavailable"}.get(hl["last_outcome"], "error")] += 1
    c["health"] = h
    return c


def stale(s, hours=26):
    la = s["health"]["last_attempt"]
    if not la:
        return True
    try:
        t = datetime.datetime.fromisoformat(la)
        return (datetime.datetime.now(t.tzinfo) - t).total_seconds() > hours * 3600 * (7 if s["collection"]["cadence"] == "weekly" else 1)
    except ValueError:
        return True


def report_md(reg):
    c = counts(reg)
    _, warns = validate(reg)
    L = [f"# Registro de fontes COP31 — situação em {now()[:16].replace('T', ' ')}", ""]
    L.append(f"{c['total']} fontes registradas: " + ", ".join(f"{k} {v}" for k, v in sorted(c["by_status"].items())))
    L.append("")
    L.append("## Coleta das fontes ativas (última tentativa)")
    h = c["health"]
    L.append(f"- configuradas: {h['configured']}; tentadas: {h['attempted']}; nunca tentadas: {h['never_attempted']}")
    L.append(f"- com sucesso: {h['successful']}; bloqueadas: {h['blocked']}; indisponíveis: {h['unavailable']}; erro: {h['error']}")
    L.append("- por plataforma: " + ", ".join(f"{k} {v}" for k, v in sorted(c["by_platform"].items())))
    L.append("- por prioridade: " + ", ".join(f"{k} {v}" for k, v in sorted(c["by_priority"].items())))
    L.append("- por categoria: " + ", ".join(f"{k} {v}" for k, v in sorted(c["by_category"].items())))
    L.append("")
    pend = [s for s in reg["sources"] if s["status"] in ("proposed", "pending_review")]
    L.append(f"## Aguardando decisão ({len(pend)})")
    for s in pend:
        tgt = s.get("handle") or (s.get("urls") or [""])[0]
        why = (s.get("decision") or {}).get("reason") or (s.get("proposal") or {}).get("relevance") or ""
        L.append(f"- `{s['id']}` {s['platform']} {tgt} — {s['institution']} [{s['category']}, {s['priority']}] — {why}")
    bad = [s for s in reg["sources"] if s["status"] == "active" and s["health"]["last_outcome"] in ("blocked", "unavailable", "error")]
    L.append("")
    L.append(f"## Ativas com problema na última tentativa ({len(bad)})")
    for s in sorted(bad, key=lambda x: -x["health"]["consecutive_failures"]):
        note = next((x.get("note") for x in reversed(s["health"]["history"]) if x.get("note")), "")
        L.append(f"- `{s['id']}` {s['institution']}: {s['health']['last_outcome']} ×{s['health']['consecutive_failures']} {note}")
    st = [s for s in reg["sources"] if s["status"] == "active" and s["priority"] == "A" and stale(s)]
    L.append("")
    L.append(f"## Prioridade A sem tentativa recente ({len(st)})")
    L.append(", ".join(f"`{s['id']}`" for s in st) or "nenhuma")
    if warns:
        L.append("")
        L.append(f"## Possíveis duplicatas ({len(warns)})")
        L += [f"- {w}" for w in warns]
    L.append("")
    L.append("Para decidir: no chat, \"aprovar <id>\", \"rejeitar <id> — motivo\", \"prioridade <id> A\"; "
             "ou escreva linhas no doc `claude/COP31 fontes — entrada.md` (uma URL ou @conta por linha, opcional `| priority=A | category=government`).")
    return "\n".join(L) + "\n"


def export(a):
    out = pathlib.Path(a[1]); out.mkdir(parents=True, exist_ok=True)
    reg = load()
    social, web = views(reg)
    files = {"social.json": social, "web.json": web}
    changed = []
    for name, doc in files.items():
        p = out / name
        old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        if {k: v for k, v in old.items() if k != "generated_at"} != {k: v for k, v in doc.items() if k != "generated_at"}:
            p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"); changed.append(name)
    (out / "sources.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "report.md").write_text(report_md(reg), encoding="utf-8")
    pulse = opt(a, "--pulse")
    if pulse:
        legacy = {"updated": now()[:10], "accounts": [dict(x, handle=x["handle"]) for x in social["accounts"]]}
        tmp = out / "pulse_input.json"
        tmp.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
        import subprocess
        before = pathlib.Path(pulse).read_text(encoding="utf-8") if pathlib.Path(pulse).exists() else ""
        subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "build_pulse.py"), str(tmp)], check=True, capture_output=True)
        tmp.unlink()
        now_txt = pathlib.Path(pulse).read_text(encoding="utf-8")
        strip = lambda t: re.sub(r'"updated": "[^"]*",?', "", t)   # noqa: E731
        if strip(before) == strip(now_txt):
            pathlib.Path(pulse).write_text(before, encoding="utf-8")   # date-only change: keep the old file
        else:
            changed.append("pulse.json")
    print(json.dumps({"changed": changed, "counts": counts(reg)}, ensure_ascii=False, default=dict))


def main(a):
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "import-legacy": import_legacy(a)
    elif cmd == "plan": plan(a)
    elif cmd == "apply": apply(a)
    elif cmd == "ingest": ingest(a)
    elif cmd == "approve": decide(a, "active")
    elif cmd == "reject": decide(a, "rejected")
    elif cmd == "retire": decide(a, "retired")
    elif cmd == "pause": decide(a, "paused")
    elif cmd == "set": set_field(a)
    elif cmd == "export": export(a)
    elif cmd == "validate":
        e, w = validate(load())
        print("\n".join([f"error: {x}" for x in e] + [f"warning: {x}" for x in w]) or "OK")
        sys.exit(1 if e else 0)
    elif cmd == "report": print(report_md(load()))
    elif cmd == "show": print(json.dumps(next((s for s in load()["sources"] if s["id"] == a[1]), {}), ensure_ascii=False, indent=1))
    else: sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
