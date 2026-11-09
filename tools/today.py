#!/usr/bin/env python3
"""Editorial workflow for "Hoje na COP31" (Today cards) and full readouts (articles).

Drafts live in the PRIVATE STORE (tools/private.py: $COP31_PRIVATE, default ../cop31-private), outside
the repository: they are never committed, pushed or deployed. data/today.json and data/articles/ (public)
receive content only through `publish` and `publish-article`, which copy a whitelist of public fields.

  python3 -I tools/today.py list
  python3 -I tools/today.py show ID                          # one draft or published card, with its flags
  python3 -I tools/today.py promote FEED_ITEM_ID             # draft from a monitoring item
  python3 -I tools/today.py set ID FIELD TEXT                # edit a draft field (no JSON editing)
         FIELD: headline summary what_happened what_changed why_it_matters watch_next open_questions
                theme classification verification event_at basis.<field> contributor.display
  python3 -I tools/today.py link ID FEED_ITEM_ID [--unlink]  # cross-reference a monitoring item
  python3 -I tools/today.py resolve ID FLAG_NO --by NAME --note "what was checked"
  python3 -I tools/today.py i18n-export ID                   # Portuguese fields to translate (card or article)
  python3 -I tools/today.py i18n-import ID LANG FILE --method human|machine-reviewed|machine [--by NAME]
  python3 -I tools/today.py publish ID --by "Name" [--verified-source N ...] [--pending-langs en,ru]
  python3 -I tools/today.py publish-article ARTICLE_ID --by "Name" [--pending-langs ...]
  python3 -I tools/today.py correct ID --by NAME --note "..." [--field F --text "..."]
  python3 -I tools/today.py retract ID --by "Name" --reason "..."
  python3 -I tools/today.py migrate                          # move a legacy editorial/drafts.json into the store

publish refuses unless: no [preencher]/[revisar] markers remain, every flag is resolved by a named editor,
contributor permissions allow the attribution shown, the submission is not confidential, a named human
approves, at least one source is verified, and all six translations exist (or are listed as pending,
which the site discloses). Nothing here calls a model or fetches the web.
"""
import json, sys, pathlib, importlib.util

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True   # never leave files in the site tree
sys.path.insert(0, str(ROOT / "tools"))
import private as P  # noqa: E402

TODAY = ROOT / "data" / "today.json"
ARTICLES = ROOT / "data" / "articles"
FEED = ROOT / "data" / "feed.json"
LEGACY = ROOT / "editorial" / "drafts.json"
_spec = importlib.util.spec_from_file_location("validate_feed", ROOT / "tools" / "validate_feed.py")
V = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(V)
TBD = "[preencher]"
SET_TEXT = set(V.TEXT_FIELDS)
SET_ENUM = {"theme": None, "classification": V.CLASS, "verification": V.VERIF}
ANON = "Contribuição à curadoria (anônima)"


def drafts_path():
    return P.ensure() / "drafts.json"


def load(path):
    return P.load_json(path, {"schema": 1, "entries": []})


def save(path, doc, private=True):
    doc["updated_at"] = P.now()
    P.save_json(path, doc, private=private)


def find(doc, eid, where):
    for en in doc["entries"]:
        if en["id"] == eid:
            return en
    sys.exit(f"no entry {eid!r} in {where}")


def opt(a, k):
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else None


def warn_legacy():
    if LEGACY.exists():
        print(f"warning: legacy drafts file {LEGACY.relative_to(ROOT)} exists inside the repository; run `today.py migrate`", file=sys.stderr)


def public_entry(en):
    """Whitelist copy: nothing private (flags, claims, permissions, submission ids) can reach today.json."""
    out = {k: v for k, v in en.items() if k in V.PUBLIC_ENTRY_KEYS}
    out["sources"] = [{k: v for k, v in s.items() if k in V.PUBLIC_SOURCE_KEYS} for s in en.get("sources") or []]
    if en.get("contributor"):
        out["contributor"] = {k: v for k, v in en["contributor"].items() if k in V.PUBLIC_CONTRIB_KEYS}
    return out


def public_article(a):
    out = {k: v for k, v in a.items() if k in V.ARTICLE_KEYS}
    out["blocks"] = [{k: v for k, v in b.items() if k in ("basis", "heading", "md")} for b in a.get("blocks") or []]
    out["sources"] = [{k: v for k, v in s.items() if k in V.PUBLIC_SOURCE_KEYS} for s in a.get("sources") or []]
    if a.get("contributor"):
        out["contributor"] = {k: v for k, v in a["contributor"].items() if k in V.PUBLIC_CONTRIB_KEYS}
    if "i18n" in a:
        out["i18n"] = {l: {k: (v if k != "blocks" else [{kk: vv for kk, vv in b.items() if kk in ("heading", "md")} for b in v])
                           for k, v in d.items()} for l, d in a["i18n"].items()}
    return out


def permission_errors(en):
    """Contributor permissions and confidentiality, recorded privately at intake."""
    pv = en.get("_private") or {}
    perm = pv.get("permissions") or {}
    c = en.get("contributor")
    errs = []
    if pv.get("confidentiality") == "confidential":
        errs.append("the submission is confidential: nothing from it can be published")
    if c:
        if c.get("display") == "named" and perm.get("attribute") != "named":
            errs.append("the contributor has not authorized public attribution by name (contributor.display must be 'anonymous')")
        if c.get("display") == "anonymous" and not _s(pv.get("anonymity_reason")):
            errs.append("anonymous attribution needs an internal justification (intake --anonymity-reason)")
        if c.get("display") == "anonymous":
            pub = json.dumps(public_entry(en), ensure_ascii=False)
            who = (pv.get("contributor") or {})
            for k in ("name", "affiliation"):
                if _s(who.get(k)) and who[k] in pub:
                    errs.append(f"anonymous card still mentions the contributor's {k}: remove it from the text and sources")
    for i, f in enumerate(pv.get("flags") or [], 1):
        if not f.get("resolved_by"):
            errs.append(f"flag {i} unresolved: {f['msg']} (today.py resolve {en['id']} {i} --by NAME --note ...)")
    return errs


def _s(v):
    return isinstance(v, str) and v.strip() != ""


# ---------------------------------------------------------------- commands

def promote(fid):
    feed = json.loads(FEED.read_text(encoding="utf-8"))
    it = next((i for i in feed["items"] if i.get("id") == fid), None)
    if not it:
        sys.exit(f"no feed item {fid!r}")
    dp = drafts_path()
    doc = load(dp)
    eid = f"{it['date']}-{fid}"[:80]
    if any(e["id"] == eid for e in doc["entries"] + load(TODAY)["entries"]):
        sys.exit(f"entry {eid!r} already exists")
    post = it.get("kind") == "post"
    src = {"title": (it.get("text") or "")[:120] if post else it.get("title"),
           "publisher": it.get("institution") or it.get("account"), "url": it["url"], "verified": False}
    if post and V.link_kind(it["url"]) == "profile":
        src["note"] = "link do perfil, não do post: localizar o post antes de publicar"
    doc["entries"].insert(0, {
        "id": eid, "status": "draft", "headline": TBD, "theme": (it.get("tracks") or [""])[0],
        "classification": "anúncio", "verification": "fonte única", "event_at": it["date"], "assessed_at": P.now(),
        "what_happened": it.get("summary") or TBD, "what_changed": TBD, "why_it_matters": TBD, "watch_next": TBD,
        "sources": [src], "promoted_from": fid, "related": [fid], "i18n": {}})
    save(dp, doc)
    print(f"draft {eid} created in the private store (not public)")


def set_field(eid, field, text):
    dp = drafts_path()
    doc = load(dp)
    en = find(doc, eid, "the private drafts")
    if field in SET_TEXT:
        en[field] = text
        for d in (en.get("i18n") or {}).values():   # the translation of a changed field is stale
            d.pop(field, None)
    elif field in SET_ENUM:
        allowed = SET_ENUM[field]
        if field == "theme":
            allowed = set(json.loads(FEED.read_text(encoding="utf-8")).get("tracks") or [])
        if text not in allowed:
            sys.exit(f"{field} must be one of {sorted(allowed)}")
        en[field] = text
    elif field == "event_at":
        en[field] = text
    elif field.startswith("basis."):
        f = field.split(".", 1)[1]
        if f not in V.BASIS_FIELDS or text not in V.BASIS:
            sys.exit(f"basis.<{'|'.join(V.BASIS_FIELDS)}> must be one of {sorted(V.BASIS)}")
        en.setdefault("basis", {})[f] = text
    elif field == "contributor.display":
        if text not in ("named", "anonymous") or not en.get("contributor"):
            sys.exit("contributor.display must be named or anonymous (entry must come from a contributor)")
        c = en["contributor"]
        pc = (en.get("_private") or {}).get("contributor") or {}
        if text == "anonymous":
            c.pop("name", None); c.pop("affiliation", None)
        else:
            c["name"] = pc.get("name"); c["affiliation"] = pc.get("affiliation")
            c = {k: v for k, v in c.items() if v}
        for s in en.get("sources") or []:   # the contributor's own account must follow the same choice
            if s.get("kind") == "contributor":
                s["publisher"] = pc.get("name") if text == "named" else ANON
        c["display"] = text
        en["contributor"] = c
    else:
        sys.exit(f"cannot set {field!r}")
    errs, _ = V.check_entry(en, public=False)
    save(dp, doc)
    print(f"{eid}: {field} updated" + (f" (draft still has {len(errs)} issue(s) before publication)" if errs else ""))


def link(eid, fid, unlink=False):
    feed_ids = {i.get("id") for i in json.loads(FEED.read_text(encoding="utf-8"))["items"]}
    if fid not in feed_ids:
        sys.exit(f"no feed item {fid!r}")
    dp = drafts_path()
    doc = load(dp)
    en = find(doc, eid, "the private drafts")
    rel = [r for r in en.get("related") or [] if r != fid]
    if not unlink:
        rel.append(fid)
    en["related"] = rel
    # linking settles a possible-duplicate flag for that item
    for f in (en.get("_private") or {}).get("flags") or []:
        if f.get("code") == "possible_duplicate" and f.get("ref") == fid and not f.get("resolved_by"):
            f.update(resolved_by="(linked)", note=f"cross-referenced to {fid}", resolved_at=P.now())
    save(dp, doc)
    print(f"{eid}: {'unlinked' if unlink else 'linked'} {fid}")


def resolve(eid, n, by, note):
    dp = drafts_path()
    doc = load(dp)
    en = find(doc, eid, "the private drafts")
    flags = (en.get("_private") or {}).get("flags") or []
    if not 1 <= n <= len(flags):
        sys.exit(f"{eid} has {len(flags)} flag(s)")
    flags[n - 1].update(resolved_by=by, note=note, resolved_at=P.now())
    save(dp, doc)
    print(f"{eid}: flag {n} resolved by {by}")


def show(eid):
    for name, doc in (("draft", load(drafts_path())), ("public", load(TODAY))):
        for en in doc["entries"]:
            if en["id"] == eid:
                print(json.dumps({k: v for k, v in en.items() if k != "_private"}, ensure_ascii=False, indent=1))
                pv = en.get("_private") or {}
                for i, f in enumerate(pv.get("flags") or [], 1):
                    st = f"resolved by {f['resolved_by']}: {f.get('note', '')}" if f.get("resolved_by") else "OPEN"
                    print(f"flag {i} [{f['code']}] {f['msg']} -> {st}")
                errs, _ = V.check_entry(dict(en, status="published", approved_by="x", approved_at=P.now()), public=False)
                errs += permission_errors(en) if name == "draft" else []
                print(f"[{name}] before publication: " + ("ready" if not errs else "; ".join(errs)))
                return
    sys.exit(f"no entry {eid!r}")


def _article_path(aid):
    return P.ensure() / "articles" / f"{aid}.json"


def i18n_export(eid):
    ap = _article_path(eid)
    if ap.exists():
        a = P.load_json(ap, {})
        left = [f for f in V.ARTICLE_TEXT if V._markers(a.get(f))] + [f"block {i}" for i, b in enumerate(a.get("blocks") or []) if V._markers(b.get("md"))]
        if left:
            sys.exit("finish the Portuguese text first: " + ", ".join(left))
        payload = {f: a[f] for f in V.ARTICLE_TEXT if a.get(f)}
        payload["blocks"] = [{k: b[k] for k in ("heading", "md") if b.get(k)} for b in a["blocks"]]
    else:
        en = find(load(drafts_path()), eid, "the private drafts")
        left = [f for f in V.TEXT_FIELDS if V._markers(en.get(f))]
        if left:
            sys.exit("finish the Portuguese text first: " + ", ".join(left))
        payload = {f: en[f] for f in V.TEXT_FIELDS if en.get(f)}
    out = P.ensure() / "i18n" / f"{eid}.pt.json"
    P.save_json(out, payload)
    print(f"wrote {out}; translate into en, es, fr, ru, zh, ar with the same keys (glossary: i18n/glossary.md); "
          "for diplomatic analysis prefer --method human or machine-reviewed")


def i18n_import(eid, lang, path, method, by):
    if lang not in V.LANGS:
        sys.exit(f"language must be one of {V.LANGS}")
    if method not in V.METHODS:
        sys.exit(f"--method must be one of {sorted(V.METHODS)}")
    tr = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    ap = _article_path(eid)
    if ap.exists():
        a = P.load_json(ap, {})
        need = [f for f in V.ARTICLE_TEXT if a.get(f)]
        bad = [f for f in need if not V._str(tr.get(f)) or V._markers(tr.get(f))]
        bl = tr.get("blocks")
        if not (isinstance(bl, list) and len(bl) == len(a["blocks"]) and all(V._str(b.get("md")) and not V._markers(b.get("md")) for b in bl)):
            bad.append("blocks (same number as the original, each with md)")
        if bad:
            sys.exit(f"translation incomplete or invalid: {bad}")
        d = {f: tr[f] for f in need}
        d["blocks"] = [{k: b[k] for k in ("heading", "md") if b.get(k)} for b in bl]
        d["method"] = method
        if by:
            d["by"] = by
        a.setdefault("i18n", {})[lang] = d
        P.save_json(ap, a)
        print(f"{eid}: article {lang} imported ({method})")
        return
    # a draft, or a published card whose translation was invalidated by a correction
    dp = drafts_path()
    doc, where = load(dp), "drafts"
    en = next((e for e in doc["entries"] if e["id"] == eid), None)
    if en is None:
        doc, where = load(TODAY), "public"
        en = find(doc, eid, "drafts or data/today.json")
    need = [f for f in V.TEXT_FIELDS if en.get(f)]
    bad = [f for f in need if not V._str(tr.get(f)) or V._markers(tr.get(f))]
    extra = [k for k in tr if k not in V.TEXT_FIELDS]
    if bad or extra:
        sys.exit(f"translation incomplete or invalid: missing {bad}, unknown {extra}")
    d = {f: tr[f] for f in need}
    d["method"] = method
    if by:
        d["by"] = by
    en.setdefault("i18n", {})[lang] = d
    if where == "public":
        en["i18n_pending"] = [l for l in en.get("i18n_pending") or [] if l != lang]
        if not en["i18n_pending"]:
            en.pop("i18n_pending")
        fatal, per = V.check_today(doc)
        if fatal or any(e for e, _ in per.values()):
            sys.exit(f"data/today.json would be invalid: {fatal or per}")
        save(TODAY, doc, private=False)
    else:
        save(dp, doc)
    print(f"{eid}: {lang} imported ({method}) [{where}]")


def publish(eid, by, verified, pending):
    dp = drafts_path()
    drafts = load(dp)
    en = find(drafts, eid, "the private drafts")
    for n in verified:
        en["sources"][n - 1]["verified"] = True
    perr = permission_errors(en)
    trial = dict(en, status="published", approved_by=by, approved_at=P.now(), assessed_at=P.now())
    if pending:
        trial["i18n_pending"] = pending
    else:
        trial.pop("i18n_pending", None)
    art = (en.get("_private") or {}).get("article")
    if art and (ARTICLES / f"{art}.json").exists():
        trial["article"] = art
    pub_en = public_entry(trial)
    errs, _ = V.check_entry(pub_en, public=True)
    if perr or errs:
        save(dp, drafts)  # keep the verified-source marks
        sys.exit("cannot publish:\n- " + "\n- ".join(perr + errs))
    pub = load(TODAY)
    pub["entries"] = [e for e in pub["entries"] if e["id"] != eid] + [pub_en]
    fatal, per = V.check_today(pub)
    if fatal or any(e for e, _ in per.values()):
        sys.exit(f"data/today.json would be invalid: {fatal or per}")
    save(TODAY, pub, private=False)
    # the private record (flags, claims, permissions) stays in the store as the audit trail
    en.update(status="published", approved_by=by, approved_at=trial["approved_at"])
    log = P.ensure() / "published.json"
    hist = P.load_json(log, {"entries": {}})
    hist["entries"][eid] = en
    P.save_json(log, hist)
    drafts["entries"] = [e for e in drafts["entries"] if e["id"] != eid]
    save(dp, drafts)
    print(f"published {eid} (approved by {by}); commit data/today.json to deploy")


def publish_article(aid, by, pending):
    ap = _article_path(aid)
    if not ap.exists():
        sys.exit(f"no article draft {aid!r} in the private store")
    a = P.load_json(ap, {})
    pv = a.get("_private") or {}
    perm = pv.get("permissions") or {}
    errs = []
    if pv.get("confidentiality") == "confidential":
        errs.append("the submission is confidential")
    if perm.get("publish_analysis") is not True:
        errs.append("the contributor has not authorized publication of the full analysis")
    c = a.get("contributor")
    if c and c.get("display") == "named" and perm.get("attribute") != "named":
        errs.append("the contributor has not authorized public attribution by name")
    pub = load(TODAY)
    live = {e["id"] for e in pub["entries"]}
    if not any(x in live for x in a.get("entries") or []):
        errs.append("publish at least one of its Today cards first: " + ", ".join(a.get("entries") or []))
    trial = dict(a, status="published", approved_by=by, approved_at=P.now(), assessed_at=P.now())
    if pending:
        trial["i18n_pending"] = pending
    else:
        trial.pop("i18n_pending", None)
    pa = public_article(trial)
    e2, _ = V.check_article(pa, public=True)
    if errs or e2:
        sys.exit("cannot publish article:\n- " + "\n- ".join(errs + e2))
    ARTICLES.mkdir(parents=True, exist_ok=True)
    P.save_json(ARTICLES / f"{aid}.json", pa, private=False)
    for en in pub["entries"]:
        if en["id"] in (a.get("entries") or []):
            en["article"] = aid
    save(TODAY, pub, private=False)
    a.update(status="published", approved_by=by, approved_at=trial["approved_at"])
    P.save_json(ap, a)
    print(f"published article {aid} (approved by {by}); commit data/articles/{aid}.json and data/today.json")


def correct(eid, by, note, field=None, text=None):
    pub = load(TODAY)
    en = find(pub, eid, "data/today.json")
    if field:
        if field not in V.TEXT_FIELDS:
            sys.exit(f"--field must be one of {V.TEXT_FIELDS}")
        en[field] = text
        stale = []
        for l, d in (en.get("i18n") or {}).items():
            if field in d:
                d.pop(field)
                stale.append(l)
        if stale:   # disclosed on the page until the corrected translations are imported
            en["i18n_pending"] = sorted(set((en.get("i18n_pending") or []) + stale))
    en.setdefault("corrections", []).append({"at": P.now(), "by": by, "note": note})
    en["assessed_at"] = P.now()
    fatal, per = V.check_today(pub)
    if fatal or any(e for e, _ in per.values()):
        sys.exit(f"data/today.json would be invalid: {fatal or per}")
    save(TODAY, pub, private=False)
    print(f"{eid}: correction recorded" + (f"; translations now pending: {en.get('i18n_pending')}" if field else ""))


def retract(eid, by, reason):
    pub = load(TODAY)
    en = find(pub, eid, "data/today.json")
    pub["entries"] = [e for e in pub["entries"] if e["id"] != eid]
    pub.setdefault("retractions", []).append({"id": eid, "retracted_at": P.now(), "reason": reason})
    art = en.get("article")
    if art and not any(e.get("article") == art for e in pub["entries"]):
        (ARTICLES / f"{art}.json").unlink(missing_ok=True)   # an article never outlives all its cards
    save(TODAY, pub, private=False)
    dp = drafts_path()
    drafts = load(dp)
    en.update(status="retracted", retracted_by=by, retracted_at=P.now(), retraction_reason=reason)
    drafts["entries"].insert(0, en)
    save(dp, drafts)
    print(f"retracted {eid}: removed from data/today.json (public notice kept), record kept in the private store")


def migrate():
    if not LEGACY.exists():
        print("nothing to migrate"); return
    dp = drafts_path()
    doc = load(dp)
    old = json.loads(LEGACY.read_text(encoding="utf-8"))
    have = {e["id"] for e in doc["entries"]}
    moved = [e for e in old.get("entries") or [] if e["id"] not in have]
    doc["entries"] = moved + doc["entries"]
    save(dp, doc)
    LEGACY.unlink()
    print(f"moved {len(moved)} draft(s) into {dp}; removed {LEGACY.relative_to(ROOT)}")


def main(a):
    warn_legacy()
    if not a or a[0] == "list":
        for name, doc in (("public", load(TODAY)), ("drafts", load(drafts_path()))):
            for en in doc["entries"]:
                langs = ",".join(sorted((en.get("i18n") or {}).keys())) or "-"
                nf = sum(1 for f in (en.get("_private") or {}).get("flags") or [] if not f.get("resolved_by"))
                print(f"{name:7} {en['status']:9} {en['id']}  [{langs}] flags:{nf}  {en['headline'][:60]}")
        for ap in sorted((P.ensure() / "articles").glob("*.json")):
            ar = P.load_json(ap, {})
            print(f"article {ar.get('status', '?'):9} {ar.get('id')}  cards: {', '.join(ar.get('entries') or [])}")
        return
    cmd = a[0]
    if cmd == "promote": promote(a[1])
    elif cmd == "show": show(a[1])
    elif cmd == "set": set_field(a[1], a[2], a[3])
    elif cmd == "link": link(a[1], a[2], "--unlink" in a)
    elif cmd == "resolve":
        if not opt(a, "--by") or not opt(a, "--note"): sys.exit("--by and --note are required")
        resolve(a[1], int(a[2]), opt(a, "--by"), opt(a, "--note"))
    elif cmd == "i18n-export": i18n_export(a[1])
    elif cmd == "i18n-import":
        i18n_import(a[1], a[2], a[3], opt(a, "--method"), opt(a, "--by"))
    elif cmd == "publish":
        if not opt(a, "--by"): sys.exit("--by NAME is required (human approval)")
        ver = [int(a[i + 1]) for i, x in enumerate(a) if x == "--verified-source"]
        pend = [l for l in (opt(a, "--pending-langs") or "").split(",") if l]
        publish(a[1], opt(a, "--by"), ver, pend)
    elif cmd == "publish-article":
        if not opt(a, "--by"): sys.exit("--by NAME is required (human approval)")
        publish_article(a[1], opt(a, "--by"), [l for l in (opt(a, "--pending-langs") or "").split(",") if l])
    elif cmd == "correct":
        if not opt(a, "--by") or not opt(a, "--note"): sys.exit("--by and --note are required")
        correct(a[1], opt(a, "--by"), opt(a, "--note"), opt(a, "--field"), opt(a, "--text"))
    elif cmd == "retract":
        if not opt(a, "--by") or not opt(a, "--reason"): sys.exit("--by and --reason are required")
        retract(a[1], opt(a, "--by"), opt(a, "--reason"))
    elif cmd == "migrate": migrate()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
