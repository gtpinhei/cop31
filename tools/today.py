#!/usr/bin/env python3
"""Editorial workflow for "Hoje na COP31".

Drafts live in editorial/drafts.json, which is gitignored: they are never committed,
pushed or deployed. data/today.json (public) receives an entry only through `publish`.

  python3 -I tools/today.py list
  python3 -I tools/today.py promote FEED_ITEM_ID             # draft from a monitoring item
  python3 -I tools/today.py i18n-export ENTRY_ID             # Portuguese fields to translate
  python3 -I tools/today.py i18n-import ENTRY_ID LANG FILE --method human|machine-reviewed|machine [--by NAME]
  python3 -I tools/today.py publish ENTRY_ID --by "Name" [--verified-source N ...] [--pending-langs en,ru]
  python3 -I tools/today.py retract ENTRY_ID --by "Name" --reason "..."

promote copies only facts the feed already holds and leaves judgement fields as [preencher].
publish refuses unless: no [preencher]/[revisar] markers remain, a named human approves,
at least one source is marked verified (--verified-source, after the editor opened it), and
all six translations of the substantive fields exist (or the missing languages are listed
explicitly with --pending-langs, which the site then discloses to readers of those languages).
Nothing here calls a model or fetches the web.
"""
import json, sys, pathlib, datetime, importlib.util

ROOT = pathlib.Path(__file__).resolve().parent.parent
TODAY = ROOT / "data" / "today.json"
DRAFTS = ROOT / "editorial" / "drafts.json"
FEED = ROOT / "data" / "feed.json"
_spec = importlib.util.spec_from_file_location("validate_feed", ROOT / "tools" / "validate_feed.py")
V = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(V)
TBD = "[preencher]"


def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat(timespec="minutes")


def load(path):
    if not path.exists():
        return {"schema": 1, "entries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc["updated_at"] = now()
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def find(doc, eid, where):
    for en in doc["entries"]:
        if en["id"] == eid:
            return en
    sys.exit(f"no entry {eid!r} in {where}")


def opt(a, k):
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else None


def promote(fid):
    feed = json.loads(FEED.read_text(encoding="utf-8"))
    it = next((i for i in feed["items"] if i.get("id") == fid), None)
    if not it:
        sys.exit(f"no feed item {fid!r}")
    doc = load(DRAFTS)
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
        "classification": "anúncio", "verification": "fonte única", "event_at": it["date"], "assessed_at": now(),
        "what_happened": it.get("summary") or TBD, "what_changed": TBD, "why_it_matters": TBD, "watch_next": TBD,
        "sources": [src], "promoted_from": fid, "i18n": {}})
    save(DRAFTS, doc)
    print(f"draft {eid} created in editorial/drafts.json (not public)")


def i18n_export(eid):
    en = find(load(DRAFTS), eid, "editorial/drafts.json")
    left = [f for f in V.TEXT_FIELDS if V._markers(en.get(f))]
    if left:
        sys.exit("finish the Portuguese text first: " + ", ".join(left))
    out = ROOT / "editorial" / "i18n" / f"{eid}.pt.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({f: en[f] for f in V.TEXT_FIELDS if en.get(f)}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}; translate into en, es, fr, ru, zh, ar with the same keys (glossary: i18n/glossary.md)")


def i18n_import(eid, lang, path, method, by):
    if lang not in V.LANGS:
        sys.exit(f"language must be one of {V.LANGS}")
    if method not in V.METHODS:
        sys.exit(f"--method must be one of {sorted(V.METHODS)}")
    doc = load(DRAFTS)
    en = find(doc, eid, "editorial/drafts.json")
    tr = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
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
    save(DRAFTS, doc)
    print(f"{eid}: {lang} imported ({method})")


def publish(eid, by, verified, pending):
    drafts = load(DRAFTS)
    en = find(drafts, eid, "editorial/drafts.json")
    for n in verified:
        en["sources"][n - 1]["verified"] = True
    trial = dict(en, status="published", approved_by=by, approved_at=now(), assessed_at=now())
    if pending:
        trial["i18n_pending"] = pending
    else:
        trial.pop("i18n_pending", None)
    errs, _ = V.check_entry(trial, public=True)
    if errs:
        save(DRAFTS, drafts)  # keep the verified-source marks
        sys.exit("cannot publish:\n- " + "\n- ".join(errs))
    pub = load(TODAY)
    pub["entries"] = [e for e in pub["entries"] if e["id"] != eid] + [trial]
    fatal, per = V.check_today(pub)
    if fatal or any(e for e, _ in per.values()):
        sys.exit(f"data/today.json would be invalid: {fatal or per}")
    save(TODAY, pub)
    drafts["entries"] = [e for e in drafts["entries"] if e["id"] != eid]
    save(DRAFTS, drafts)
    print(f"published {eid} (approved by {by}); commit data/today.json to deploy")


def retract(eid, by, reason):
    pub = load(TODAY)
    en = find(pub, eid, "data/today.json")
    pub["entries"] = [e for e in pub["entries"] if e["id"] != eid]
    save(TODAY, pub)
    drafts = load(DRAFTS)
    en.update(status="retracted", retracted_by=by, retracted_at=now(), retraction_reason=reason)
    drafts["entries"].insert(0, en)
    save(DRAFTS, drafts)
    print(f"retracted {eid}: removed from data/today.json, kept in editorial/drafts.json")


def main(a):
    if not a or a[0] == "list":
        for name, doc in (("public", load(TODAY)), ("drafts", load(DRAFTS))):
            for en in doc["entries"]:
                langs = ",".join(sorted((en.get("i18n") or {}).keys())) or "-"
                print(f"{name:7} {en['status']:9} {en['id']}  [{langs}]  {en['headline'][:60]}")
        return
    cmd = a[0]
    if cmd == "promote": promote(a[1])
    elif cmd == "i18n-export": i18n_export(a[1])
    elif cmd == "i18n-import":
        i18n_import(a[1], a[2], a[3], opt(a, "--method"), opt(a, "--by"))
    elif cmd == "publish":
        if not opt(a, "--by"): sys.exit("--by NAME is required (human approval)")
        ver = [int(a[i + 1]) for i, x in enumerate(a) if x == "--verified-source"]
        pend = [l for l in (opt(a, "--pending-langs") or "").split(",") if l]
        publish(a[1], opt(a, "--by"), ver, pend)
    elif cmd == "retract":
        if not opt(a, "--by") or not opt(a, "--reason"): sys.exit("--by and --reason are required")
        retract(a[1], opt(a, "--by"), opt(a, "--reason"))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
