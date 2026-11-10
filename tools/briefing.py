#!/usr/bin/env python3
"""Today at COP31, automated layer: a daily briefing of links to already-public reporting and analysis.

  python3 -I tools/briefing.py [--feed data/feed.json] [--out data/briefing.json] [--now ISO] [--registry]

Reads only items the monitoring agents already collected into data/feed.json from registry sources. It never fetches
anything, never writes original analysis and never touches data/today.json (human-approved contributions, shown on
the page as "Da comunidade"). For each story it keeps the original headline and canonical URL, the publisher, the
original publication date, a short attributed description (the monitor's summary of the source, with its machine
translations) and the collection timestamp.

Selection: candidates from the last 72 hours (by the publisher's date), reports of the same event grouped into one
story, ranked by source quality, timeliness, type, relevance to negotiations and implementation, independent coverage
and novelty, with publisher diversity in the top stories. Sections: essential, negotiations, action, civil society.
Empty sections are left empty and the page hides them.

Safety: the new edition is validated and written atomically; on any error the previous edition stays in place.
When the agents' rounds are older than 12 hours the edition is flagged stale instead of claiming a quiet day.
"""
import datetime, json, math, os, pathlib, re, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
TZ = datetime.timezone(datetime.timedelta(hours=3))      # Antalya
WINDOW_DAYS = 3
TOP = 8
STALE_H = 12

# priority publishers named by the editor (matched on institution, case-insensitive)
PRIORITY = [r"carbon brief", r"climate home", r"\benb\b|earth negotiations", r"\becco\b", r"talanoa|pol[ií]tica por inteiro",
            r"\bcan\b|climate action network|climatenetwork", r"third world network|\btwn\b", r"\be3g\b", r"unfccc",
            r"presid[eê]ncia|presidency|cop31 presidency|kurum|bowen"]
NEGOTIATION = {"Mitigação e MWP", "Adaptação", "Finanças", "Transição justa", "GST2 e IPCC", "Perdas e danos", "Decisão de cobertura",
               "Comércio", "TAFF e fósseis"}
ACTION = {"Agenda de Ação", "Eletrificação", "Florestas", "Oceanos", "Presidência e anfitrião", "Espaço cívico"}
OFFICIAL = {"presidency", "unfccc", "government", "multilateral", "negotiating_group"}
STOP = set("""the and for with that this from into over have has had were was are will would their them they its it's
about after before between under than then also more most such only what when where which while who whom why how
cop31 cop 2026 antalya climate conference summit says said new news says will been being said cop31's
para com que uma por mais como dos das nos nas sobre entre pelo pela seus suas este esta isso ainda após
""".split())


def now_tz(arg=None):
    if arg:
        t = datetime.datetime.fromisoformat(arg)
        return t if t.tzinfo else t.replace(tzinfo=TZ)
    return datetime.datetime.now(TZ)


def ts(x):
    try:
        t = datetime.datetime.fromisoformat(x)
        return t if t.tzinfo else t.replace(tzinfo=TZ)
    except (TypeError, ValueError):
        return None


def registry_index():
    """Category and priority per source id and per institution, from the private registry when it is available."""
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import sources as S   # noqa: E402
        reg = S.load()
    except Exception:
        return {}, {}, []
    by_id, by_inst = {}, {}
    for s in reg["sources"]:
        meta = {"category": s.get("category"), "priority": s.get("priority"), "status": s.get("status")}
        by_id[s["id"]] = meta
        by_inst.setdefault(s.get("institution", "").lower(), meta)
    gaps = []
    for s in reg["sources"]:
        if s.get("status") != "active" or s.get("platform") not in ("web", "rss"):
            continue
        if not any(re.search(p, s.get("institution", ""), re.I) for p in PRIORITY):
            continue
        last = s["health"].get("last_outcome")
        if last in ("blocked", "unavailable", "error"):
            note = next((h.get("note") for h in reversed(s["health"]["history"]) if h.get("note")), "") or ""
            gaps.append({"publisher": s.get("institution"), "outcome": last, "note": note[:120]})
    return by_id, by_inst, gaps


def meta_for(it, by_id, by_inst):
    return by_id.get(it.get("source_id") or "") or by_inst.get((it.get("institution") or "").lower()) or {}


def content_type(it, cat):
    t = (it.get("type") or "").lower()
    if it.get("kind") == "post":
        return "official" if cat in OFFICIAL else "advocacy" if cat == "civil_society" else "reporting"
    if cat in OFFICIAL:
        return "document" if t in ("relatório", "ferramenta") else "official"
    if cat == "civil_society":
        return "advocacy"
    if t in ("notícia", "boletim"):
        return "reporting"
    return "analysis"


def direct_url(u, kind):
    if not isinstance(u, str) or not u.startswith("https://"):
        return False
    p = re.sub(r"^https://[^/]+", "", u).strip("/")
    if kind == "post":
        return bool(re.search(r"/post/|/status/|/p/|watch\?v=", u))   # a single post, not a profile
    return len(p) > 3


def tokens(it):
    txt = " ".join([it.get("title") or "", (it.get("summary_i18n") or {}).get("en") or "", it.get("text") or ""])
    return {w for w in re.findall(r"[a-zà-ÿ0-9]{4,}", txt.lower()) if w not in STOP and not w.isdigit()}


def candidates(feed, now, by_id, by_inst):
    out = []
    start = (now - datetime.timedelta(days=WINDOW_DAYS)).date()
    for it in feed.get("items") or []:
        kind = it.get("kind") or "publication"
        d = it.get("date")
        try:
            day = datetime.date.fromisoformat(d)
        except (TypeError, ValueError):
            continue
        if day < start or day > now.date():
            continue
        if not direct_url(it.get("url"), kind):
            continue
        m = meta_for(it, by_id, by_inst)
        if m and m.get("status") not in (None, "active"):
            continue                                      # only sources currently approved in the registry
        cat = m.get("category")
        if kind == "post" and not (cat in OFFICIAL or re.search(r"\benb\b|earth negotiations|climate action network|\bcan\b", it.get("institution") or "", re.I)):
            continue                                      # social: official voices and ENB/CAN only; the rest stays in Pulso
        if kind == "post" and (not it.get("tracks") or it.get("platform") == "youtube"):
            continue                                      # recorded side-event videos stay in Pulso
        out.append(dict(it, _kind=kind, _day=day, _cat=cat, _prio=m.get("priority"), _ctype=content_type(it, cat), _tok=tokens(it)))
    return out


def score(it, now, seen_before):
    inst = it.get("institution") or ""
    src = 1.0 if any(re.search(p, inst, re.I) for p in PRIORITY) else {"A": 0.9, "B": 0.75, "C": 0.55}.get(it["_prio"], 0.7)
    age = (now.date() - it["_day"]).days
    fresh = {0: 1.0, 1: 0.8, 2: 0.5}.get(age, 0.3)
    typ = {"reporting": 1.0, "official": 1.0, "document": 0.95, "analysis": 0.9, "advocacy": 0.75}[it["_ctype"]]
    if it["_kind"] == "post":
        typ *= 0.55                                       # a post points to a development; an article explains it
    tr = set(it.get("tracks") or [])
    rel = 0.6 + 0.25 * bool(tr & NEGOTIATION) + 0.15 * bool(tr & ACTION) if tr else 0.5
    nov = 0.6 if it.get("id") in seen_before else 1.0
    return src * fresh * typ * rel * nov


def group(items):
    """Union-find over items about the same event: shared distinctive words, published within two days."""
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if abs((a["_day"] - b["_day"]).days) > 2 or not a["_tok"] or not b["_tok"]:
                continue
            inter = len(a["_tok"] & b["_tok"])
            jac = inter / len(a["_tok"] | b["_tok"])
            if a.get("url") == b.get("url") or (jac >= 0.22 and inter >= 6):
                parent[find(i)] = find(j)
    groups = {}
    for i, it in enumerate(items):
        groups.setdefault(find(i), []).append(it)
    return list(groups.values())


def public_item(it):
    title = it.get("title")
    if not title and it["_kind"] == "post":
        txt = re.sub(r"\s+", " ", it.get("text") or "").strip()      # the post's own words, briefly, in its language
        title = (it.get("account", "") + ": " if it.get("account") else "") + (txt[:117].rsplit(" ", 1)[0] + "…" if len(txt) > 120 else txt)
        if not txt:
            title = None
    pub = {"id": it.get("id"), "title": title or short(it.get("summary") or "", 140), "title_is_post": it["_kind"] == "post" or None, "url": it["url"],
           "publisher": it.get("institution"), "author": it.get("authors") or None, "published": it["_day"].isoformat(),
           "time": it.get("time") or None, "language": it.get("lang") or None, "tracks": it.get("tracks") or [],
           "content_type": it["_ctype"], "kind": it["_kind"], "platform": it.get("platform") if it["_kind"] == "post" else None,
           "description": short(it.get("summary") or ""), "collected_at": it.get("first_seen"),
           "validation": "registry source, collected by the monitor"}
    i18n = it.get("summary_i18n") or {}
    pub["description_i18n"] = {k: short(v) for k, v in i18n.items() if isinstance(v, str) and v.strip()}
    if pub["description_i18n"]:
        pub["description_i18n_method"] = "machine"
    return {k: v for k, v in pub.items() if v not in (None, [], {})}


def short(t, n=320):
    """Concise description: the first sentences of the monitor's summary, never the source's own text."""
    t = re.sub(r"\s+", " ", t or "").strip()
    t = re.sub(r"\s*(Toca|Touches|Relevant to|Trilhas?)[^.]*\.?$", "", t).strip()   # drop the trailing track note
    if len(t) <= n:
        return t
    cut = t[:n]
    k = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[:k + 1] if k > n * 0.5 else cut.rsplit(" ", 1)[0] + "…").strip()


def section_of(lead, members):
    cats = {m["_cat"] for m in members}
    if lead["_ctype"] == "advocacy" and cats <= {"civil_society", None}:
        return "civil"
    tr = set()
    for m in members:
        tr |= set(m.get("tracks") or [])
    first = (lead.get("tracks") or [""])[0]
    if first in NEGOTIATION or (tr & NEGOTIATION and not first in ACTION):
        return "negotiations"
    if tr & ACTION:
        return "action"
    return "civil" if lead["_ctype"] == "advocacy" else "negotiations"


def voice(it):
    """Who is speaking, for diversity: the presidency's accounts and ministers count as one voice."""
    inst = it.get("institution") or ""
    if re.search(r"presid[eê]ncia|presidency|kurum|bowen", inst, re.I):
        return "presidency"
    return inst.lower()


def build(feed, now, prev=None, registry=True):
    by_id, by_inst, gaps = registry_index() if registry else ({}, {}, [])
    prev = prev or {}
    seen_before = {i for d, ids in (prev.get("featured_history") or {}).items() if d != now.date().isoformat() for i in ids}
    cands = candidates(feed, now, by_id, by_inst)
    stories = []
    for g in group(cands):
        for m in g:
            m["_score"] = score(m, now, seen_before)
        g.sort(key=lambda m: (-m["_score"], m.get("first_seen") or ""))
        lead = g[0]
        pubs = {m.get("institution") for m in g}
        s = lead["_score"] * (1 + 0.25 * math.log(len(pubs)))           # independent coverage of the same event
        stories.append({"lead": lead, "members": g, "score": s, "section": section_of(lead, g)})
    stories.sort(key=lambda s: (-s["score"], s["lead"]["_day"].isoformat()), reverse=False)
    # top stories with publisher diversity (no quota per section)
    top, used = [], {}
    pool = list(stories)
    while pool and len(top) < TOP:
        best = max(pool, key=lambda s: s["score"] * (0.6 ** used.get(voice(s["lead"]), 0)))
        if best["score"] < 0.15:
            break
        top.append(best); pool.remove(best)
        used[voice(best["lead"])] = used.get(voice(best["lead"]), 0) + 1

    def story(s):
        lead = s["lead"]
        rel = [public_item(m) for m in s["members"][1:]]
        return {"id": "st-" + (lead.get("id") or "")[:80], "section": s["section"], "score": round(s["score"], 3),
                "lead": public_item(lead), "related": rel, "publishers": sorted({m.get("institution") for m in s["members"] if m.get("institution")})}
    sections = {"essential": [story(s) for s in top], "negotiations": [], "action": [], "civil": []}
    for s in sorted(pool, key=lambda s: -s["score"]):
        sections[s["section"]].append(story(s))
    rounds = [ts((feed.get("round") or {}).get("timestamp")), ts((feed.get("social_round") or {}).get("timestamp"))]
    rounds = [r for r in rounds if r]
    newest = max(rounds) if rounds else None
    stale = not newest or (now - newest).total_seconds() > STALE_H * 3600
    shown_ids = [x["lead"]["id"] for x in sections["essential"]]
    hist = dict(prev.get("featured_history") or {})
    hist[now.date().isoformat()] = sorted(set(hist.get(now.date().isoformat(), [])) | set(shown_ids))
    hist = {d: v for d, v in hist.items() if d >= (now.date() - datetime.timedelta(days=7)).isoformat()}
    n_stories = sum(len(v) for v in sections.values())
    return {
        "schema": 1, "edition": now.date().isoformat(), "generated_at": now.isoformat(timespec="minutes"),
        "window": {"from": (now.date() - datetime.timedelta(days=WINDOW_DAYS)).isoformat(), "to": now.date().isoformat(), "basis": "publisher date"},
        "collection": {"web_round": (feed.get("round") or {}).get("timestamp"), "social_round": (feed.get("social_round") or {}).get("timestamp"),
                       "stale": stale},
        "coverage": {"candidates": len(cands), "stories": n_stories, "top": len(sections["essential"]),
                     "publishers": sorted({c.get("institution") for c in cands if c.get("institution")}),
                     "access_gaps": gaps},
        "provenance": "Links to public reporting and analysis collected by the COP31 Monitor from registry sources; "
                      "descriptions are the monitor's short summaries of each source, translations are machine translations. "
                      "Not original analysis.",
        "sections": sections,
        "featured_history": hist,
    }


def validate(b):
    assert b.get("schema") == 1 and isinstance(b.get("sections"), dict)
    for name in ("essential", "negotiations", "action", "civil"):
        for s in b["sections"].get(name, []):
            for it in [s["lead"]] + s.get("related", []):
                assert it["url"].startswith("https://") and it.get("publisher") and it.get("title"), it.get("id")
                assert re.match(r"^\d{4}-\d{2}-\d{2}$", it["published"]), it.get("id")
                assert len(it.get("description", "")) <= 400, it.get("id")
    ids = [s["lead"]["id"] for v in b["sections"].values() for s in v]
    assert len(ids) == len(set(ids)), "a story appears twice"
    return True


def main(a):
    def opt(k, d=None):
        return a[a.index(k) + 1] if k in a else d
    feed_p = pathlib.Path(opt("--feed", ROOT / "data" / "feed.json"))
    out_p = pathlib.Path(opt("--out", ROOT / "data" / "briefing.json"))
    prev = None
    if out_p.exists():
        try:
            prev = json.loads(out_p.read_text(encoding="utf-8"))
        except ValueError:
            prev = None
    try:
        feed = json.loads(feed_p.read_text(encoding="utf-8"))
        b = build(feed, now_tz(opt("--now")), prev, registry="--no-registry" not in a)
        validate(b)
    except Exception as e:                           # keep the previous valid edition
        print(f"briefing not rebuilt, previous edition kept: {e!r}", file=sys.stderr)
        return 1
    if prev and {k: v for k, v in prev.items() if k != "generated_at"} == {k: v for k, v in b.items() if k != "generated_at"}:
        print("briefing unchanged"); return 0
    fd, tmp = tempfile.mkstemp(dir=out_p.parent, prefix=".briefing-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(b, f, ensure_ascii=False, indent=1); f.write("\n")
    os.replace(tmp, out_p)
    c = b["coverage"]
    print(f"briefing {b['edition']}: {c['candidates']} candidates, {c['stories']} stories, top {c['top']}, "
          f"{len(c['publishers'])} publishers{', STALE collection' if b['collection']['stale'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
