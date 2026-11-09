#!/usr/bin/env python3
"""Private intake of human intelligence: readouts, analysis, meeting notes, field reports.

Everything here stays in the private store (tools/private.py), outside the repository. Nothing is
published: drafts go through tools/today.py (translation, flags, human approval) like any other card.

  python3 -I tools/intake.py add FILE|- --title "..." --contributor "Name" --role author|observer|analyst|organization
        [--affiliation "Org"] [--kind readout|analysis|meeting-note|field-report] [--event-date YYYY-MM-DD]
        [--confidentiality public|chatham|confidential] [--attribute named|anonymous|ask]
        [--anonymity-reason "..."] [--publish-analysis yes|no] [--publish-document yes|no]
        [--received-by EDITOR] [--source-url URL ...]
  python3 -I tools/intake.py prompt SID      # extraction brief for the AI assistant (numbered paragraphs + rules)
  python3 -I tools/intake.py propose SID FILE  # check the AI's structured proposal and create private drafts
  python3 -I tools/intake.py related SID|ENTRY_ID  # monitoring items that may describe the same development
  python3 -I tools/intake.py list | show SID

Supported inputs: .docx, .pdf (with a text layer), .md, .txt, or pasted text on stdin ("-").

Provenance rules enforced by `propose` (brief: "AI must not silently promote an attributed
interpretation into a verified fact"):
  - every claim is one of: verified (needs an official https source; the editor confirms it at publish),
    attributed (a named or described speaker, or the contributor's first-hand observation),
    analysis (the contributor's or editor's interpretation), unverified (needs confirmation);
  - every verified or attributed claim quotes the document word for word (<= 40 words) and names its paragraph;
  - a card field may not claim more than the claims it cites: what happened can never rest on analysis.
"""
import hashlib, json, re, shutil, subprocess, sys, pathlib, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True   # never leave files in the site tree
sys.path.insert(0, str(ROOT / "tools"))
import private as P  # noqa: E402
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("validate_feed", ROOT / "tools" / "validate_feed.py")
V = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(V)
FEED = ROOT / "data" / "feed.json"
KINDS = {"readout", "analysis", "meeting-note", "field-report"}
# public label of the contributor's own account (the submission title stays private)
KIND_LABEL = {"readout": "Readout enviado à curadoria", "analysis": "Análise enviada à curadoria",
              "meeting-note": "Notas de reunião enviadas à curadoria", "field-report": "Relato de campo enviado à curadoria"}
CONF = {"public", "chatham", "confidential"}
ATTR = {"named", "anonymous", "ask"}
STRENGTH = {"verified": 3, "attributed": 2, "unverified": 1}
FACT_FIELDS = ("summary", "what_happened", "what_changed", "why_it_matters", "watch_next")
MAX_QUOTE_WORDS = 40


def opt(a, k, default=None):
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else default


def opts(a, k):
    return [a[i + 1] for i, x in enumerate(a) if x == k and i + 1 < len(a)]


def slug(s, n=40):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:n].strip("-") or "x"


def norm(s):
    """Normalization for verbatim-quote matching: typographic quotes/dashes, spaces, case."""
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[‐-―]", "-", s)
    s = re.sub(r"[*_`]", "", s)   # markdown emphasis
    return re.sub(r"\s+", " ", s).strip().lower()


# ---------------------------------------------------------------- extraction

def extract_text(path):
    """Plain extraction, no model: returns (paragraphs, notes)."""
    ext = path.suffix.lower()
    notes = []
    if ext in (".md", ".txt", ""):
        raw = path.read_text(encoding="utf-8", errors="replace")
        paras = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", raw)]
    elif ext == ".docx":
        import docx  # python-docx
        d = docx.Document(str(path))
        paras = []
        for p in d.paragraphs:
            t = p.text.strip()
            if not t:
                continue
            style = (p.style.name or "").lower() if p.style is not None else ""
            paras.append(("## " + t) if style.startswith("heading") or style == "title" else t)
        for tb in d.tables:
            for row in tb.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    paras.append(" | ".join(dict.fromkeys(cells)))
        if d.tables:
            notes.append(f"{len(d.tables)} table(s) appended after the body text as ' | '-separated rows")
    elif ext == ".pdf":
        out = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"], capture_output=True, text=True, timeout=120)
        raw = out.stdout if out.returncode == 0 else ""
        paras = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", raw)]
        paras = [re.sub(r"(\w)- (\w)", r"\1\2", p) for p in paras]   # hyphenation at line ends
    else:
        sys.exit(f"unsupported file type {ext!r}: use .docx, .pdf, .md, .txt or paste text with '-'")
    paras = [p for p in paras if p and not re.fullmatch(r"[\d\s\-–—|]+", p)]
    if ext == ".pdf" and sum(len(p) for p in paras) < 200:
        notes.append("almost no text layer: scanned PDF? Ask for the original document or a transcript (no OCR is run)")
    return paras, notes


# ---------------------------------------------------------------- matching against the monitoring feed

STOP = set("""a o os as de do da dos das e em no na nos nas um uma para por com que se ao à às sobre entre mais como
the of and to in for on with by from at is are was were be as that this an or it its their his her new
cop31 cop30 cop clima climate climática climático""".split())


def tokens(text):
    t = norm(text)
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    out = set()
    for w in re.findall(r"[a-zà-ÿ0-9][a-zà-ÿ0-9.$%-]*", t):
        w = w.strip(".-")
        if (len(w) >= 4 or re.search(r"\d", w)) and w not in STOP:
            out.add(w)
    return out


def related_items(text, date=None, n=8):
    feed = json.loads(FEED.read_text(encoding="utf-8"))
    A = tokens(text)
    res = []
    for it in feed.get("items") or []:
        B = tokens(" ".join(str(it.get(k) or "") for k in ("title", "summary", "text")))
        if not A or not B:
            continue
        shared = A & B
        score = len(shared) / ((len(A) * len(B)) ** 0.5)
        if date and it.get("date"):
            try:
                import datetime as dt
                gap = abs((dt.date.fromisoformat(it["date"]) - dt.date.fromisoformat(date[:10])).days)
                score *= 1.0 if gap <= 3 else 0.6
            except ValueError:
                pass
        if len(shared) >= 3:
            res.append({"id": it["id"], "date": it.get("date"), "title": it.get("title") or (it.get("text") or "")[:90],
                        "url": it.get("url"), "score": round(score, 3), "shared": sorted(shared)[:12]})
    return sorted(res, key=lambda r: -r["score"])[:n]


# ---------------------------------------------------------------- commands

def sub_dir(sid):
    d = P.ensure() / "intake" / sid
    if not d.exists():
        sys.exit(f"no submission {sid!r}")
    return d


def add(a):
    src = a[1]
    title = opt(a, "--title")
    who = opt(a, "--contributor")
    role = opt(a, "--role")
    if not title or not who or role not in V.ROLES:
        sys.exit(f"--title, --contributor and --role ({'|'.join(sorted(V.ROLES))}) are required")
    kind = opt(a, "--kind", "readout")
    conf = opt(a, "--confidentiality", "public")
    attr = opt(a, "--attribute", "ask")
    if kind not in KINDS or conf not in CONF or attr not in ATTR:
        sys.exit(f"--kind {sorted(KINDS)}, --confidentiality {sorted(CONF)}, --attribute {sorted(ATTR)}")
    if attr == "anonymous" and not opt(a, "--anonymity-reason"):
        sys.exit("anonymous attribution needs --anonymity-reason (kept internal)")
    store = P.ensure()
    if src == "-":
        data = sys.stdin.read().encode("utf-8")
        ext = ".md"
    else:
        sp = pathlib.Path(src)
        if not sp.is_file():
            sys.exit(f"no file {src}")
        data = sp.read_bytes()
        ext = sp.suffix.lower()
    digest = hashlib.sha256(data).hexdigest()
    for m in (store / "intake").glob("*/meta.json"):
        if P.load_json(m, {}).get("sha256") == digest:
            sys.exit(f"this document was already submitted as {m.parent.name}")
    date = opt(a, "--event-date") or P.now()[:10]
    sid = f"{date}-{slug(title, 32)}-{digest[:6]}"
    d = store / "intake" / sid
    d.mkdir(parents=True)
    d.chmod(0o700)
    orig = d / f"original{ext or '.txt'}"
    orig.write_bytes(data)
    orig.chmod(0o600)
    paras, notes = extract_text(orig)
    if not paras:
        shutil.rmtree(d)
        sys.exit("no text could be extracted")
    P.save_json(d / "paragraphs.json", [{"n": i, "text": t} for i, t in enumerate(paras, 1)])
    (d / "text.md").write_text("\n\n".join(f"¶{i} {t}" for i, t in enumerate(paras, 1)) + "\n", encoding="utf-8")
    (d / "text.md").chmod(0o600)
    meta = {
        "id": sid, "title": title, "kind": kind, "event_date": date, "received_at": P.now(),
        "received_by": opt(a, "--received-by"), "original": orig.name, "sha256": digest, "bytes": len(data),
        "contributor": {"name": who, "affiliation": opt(a, "--affiliation"), "role": role},
        "confidentiality": conf,
        "permissions": {"attribute": attr, "publish_analysis": opt(a, "--publish-analysis", "no") == "yes",
                        "publish_document": opt(a, "--publish-document", "no") == "yes"},
        "anonymity_reason": opt(a, "--anonymity-reason"),
        "source_urls": [u for u in opts(a, "--source-url") if u.startswith("https://")],
        "extraction_notes": notes, "paragraphs": len(paras),
    }
    P.save_json(d / "meta.json", meta)
    print(f"submission {sid}: {len(paras)} paragraphs extracted ({orig.name}, {len(data)} bytes) into the private store")
    for n in notes:
        print(f"  note: {n}")
    print(f"next: python3 -I tools/intake.py prompt {sid}")


PROMPT = """# Extraction brief: {title}

You are helping an editor of COP31 Monitor turn one private submission into structured DRAFTS.
Nothing you write is published: a named editor reviews, translates and approves every field.

Submission {sid} — kind: {kind}; contributor role: {role}; confidentiality: {conf}; event date: {date}.
{conf_note}

## Rules (the importer rejects proposals that break them)
1. Write all card text in Brazilian Portuguese, concise and neutral. Keep names, numbers and dates exactly as in the document.
2. Find EVERY distinct development (a decision, proposal, figure, framework, dispute or open question that a reader
   would track separately). One development = one card. Do not merge unrelated developments; do not split one.
3. Break each development into claims. Each claim has a category:
   - "attributed": something a speaker said, or something the contributor saw or heard first-hand. Give the speaker
     as the document gives it (e.g. "Presidência da COP30", "um negociador", "o autor do readout").
   - "analysis": the contributor's interpretation, assessment or recommendation, or your own inference.
     Anything not stated in the document is analysis by the editor ("speaker": "editor (IA)").
   - "unverified": a factual assertion the document makes without a source, or that you cannot attribute.
   - "verified": ONLY when "source_url" is an official https document that the editor can open. You cannot open it
     yourself, so the editor confirms it before publication. Never infer "verified" from a speaker's authority.
4. Every attributed, unverified and verified claim carries "para" (the ¶ number) and "quote": the document's words,
   copied exactly, at most {maxq} words. Analysis taken from the document also carries para and quote; your own
   inference carries neither.
5. Card fields cite claims and declare a basis that is never stronger than the weakest claim they cite
   (verified > attributed > unverified). "what_happened" must be attributed/verified/unverified, never analysis.
   "why_it_matters" is usually analysis. Write attribution into the text ("segundo a presidência", "o autor avalia").
6. "theme" is one of: {tracks}. "classification" is one of: {classes}. "verification" is one of: {verif}.
7. List outstanding questions (what an editor must still confirm) in "open_questions".
8. If the document preserves analysis worth reading in full, propose an "article": blocks in the order of the
   document, each with basis and the ¶ numbers it comes from, keeping the contributor's reasoning and nuance.
   Mark reported material "attributed" and the contributor's interpretation "analysis".
9. "related": ids of monitoring items below that describe the SAME development (not just the same topic).

## Output: one JSON object, nothing else
{schema}

## Monitoring items that may overlap (from data/feed.json)
{related}

## Document (paragraphs numbered by the importer)
{text}
"""

SCHEMA = """{
 "developments": [
  {"key": "short-slug", "headline": "...", "summary": {"text": "...", "basis": "attributed", "claims": ["c1"]},
   "theme": "Finanças", "areas": ["..."], "classification": "processo", "verification": "fonte única",
   "event_at": "YYYY-MM-DD",
   "what_happened": {"text": "...", "basis": "attributed", "claims": ["c1", "c2"]},
   "what_changed": {"text": "...", "basis": "attributed", "claims": ["c2"]},
   "why_it_matters": {"text": "...", "basis": "analysis", "claims": ["c3"]},
   "watch_next": {"text": "...", "basis": "analysis", "claims": ["c3"]},
   "open_questions": "...", "actors": ["..."], "related": ["feed-item-id"],
   "sources": [{"title": "...", "publisher": "...", "url": "https://...", "kind": "official|media|analysis"}],
   "claims": [{"id": "c1", "text": "...", "category": "attributed", "speaker": "...", "para": 3, "quote": "exact words"},
              {"id": "c3", "text": "...", "category": "analysis", "speaker": "autor do readout", "para": 9, "quote": "..."}]}
 ],
 "article": {"title": "...", "standfirst": "...",
   "blocks": [{"basis": "attributed", "heading": "...", "md": "markdown paragraph(s)", "paras": [2, 3], "claims": ["c1"]}]}
}"""


def prompt(sid):
    d = sub_dir(sid)
    meta = P.load_json(d / "meta.json", {})
    feed = json.loads(FEED.read_text(encoding="utf-8"))
    text = (d / "text.md").read_text(encoding="utf-8")
    rel = related_items(text, meta.get("event_date"), n=10)
    conf_note = {"chatham": "CHATHAM HOUSE RULE: speakers must not be identified by name or affiliation in any card text; describe them generically.",
                 "confidential": "CONFIDENTIAL: drafts may be prepared for internal use, but nothing from this submission can be published.",
                 "public": ""}[meta["confidentiality"]]
    body = PROMPT.format(title=meta["title"], sid=sid, kind=meta["kind"], role=meta["contributor"]["role"],
                         conf=meta["confidentiality"], date=meta["event_date"], conf_note=conf_note, maxq=MAX_QUOTE_WORDS,
                         tracks=", ".join(feed.get("tracks") or []), classes=", ".join(sorted(V.CLASS)),
                         verif=", ".join(sorted(V.VERIF)), schema=SCHEMA, text=text,
                         related="\n".join(f"- {r['id']} ({r['date']}): {r['title']}" for r in rel) or "(none)")
    out = d / "prompt.md"
    out.write_text(body, encoding="utf-8")
    out.chmod(0o600)
    print(f"wrote {out}\nGive it to the AI assistant; save its JSON answer and run: python3 -I tools/intake.py propose {sid} <answer.json>")


def check_proposal(prop, paras, meta, feed):
    """Returns (errors, warnings). Errors block draft creation."""
    E, W = [], []
    ptext = {p["n"]: norm(p["text"]) for p in paras}
    alltext = " ".join(ptext.values())
    tracks = set(feed.get("tracks") or [])
    feed_ids = {i.get("id") for i in feed.get("items") or []}
    devs = prop.get("developments")
    if not isinstance(devs, list) or not devs:
        return ["proposal needs at least one development"], W
    keys = set()
    claims_all = {}
    for di, dv in enumerate(devs):
        tag = f"development {di + 1} ({dv.get('key')})"
        if not (isinstance(dv.get("key"), str) and re.fullmatch(r"[a-z0-9-]{2,30}", dv["key"])) or dv["key"] in keys:
            E.append(f"{tag}: key must be a unique short slug")
        keys.add(dv.get("key"))
        if not V._str(dv.get("headline")): E.append(f"{tag}: headline missing")
        if dv.get("theme") not in tracks: E.append(f"{tag}: theme must be one of the feed tracks")
        if dv.get("classification") not in V.CLASS: E.append(f"{tag}: classification invalid")
        if dv.get("verification") not in V.VERIF: E.append(f"{tag}: verification invalid")
        claims = {}
        for c in dv.get("claims") or []:
            cid = c.get("id")
            ctag = f"{tag} claim {cid}"
            if not cid or cid in claims_all: E.append(f"{ctag}: claim ids must be unique across the proposal"); continue
            cat = c.get("category")
            if cat not in V.BASIS: E.append(f"{ctag}: category must be one of {sorted(V.BASIS)}"); continue
            q = c.get("quote")
            if cat in ("verified", "attributed", "unverified") or q:
                if not (V._str(q) and isinstance(c.get("para"), int)):
                    E.append(f"{ctag}: {cat} claims need para and a verbatim quote"); continue
                if len(q.split()) > MAX_QUOTE_WORDS:
                    E.append(f"{ctag}: quote longer than {MAX_QUOTE_WORDS} words")
                nq = norm(q).strip(" .,;:\"'")
                if nq not in ptext.get(c["para"], ""):
                    if nq in alltext:
                        W.append(f"{ctag}: quote found, but not in ¶{c['para']}")
                    else:
                        E.append(f"{ctag}: quote not found in the document (claims must quote it word for word)")
            if cat == "verified" and not (isinstance(c.get("source_url"), str) and c["source_url"].startswith("https://")):
                E.append(f"{ctag}: 'verified' needs an official https source_url; otherwise use attributed or unverified")
            if cat == "attributed" and not V._str(c.get("speaker")):
                E.append(f"{ctag}: attributed claims need a speaker (generic under Chatham House)")
            claims[cid] = c
            claims_all[cid] = c
        if not claims: E.append(f"{tag}: no valid claims")
        for f in FACT_FIELDS:
            fv = dv.get(f)
            if fv is None:
                if f == "what_happened": E.append(f"{tag}: what_happened missing")
                continue
            if not (isinstance(fv, dict) and V._str(fv.get("text"))):
                E.append(f"{tag}: {f} must be {{text, basis, claims}}"); continue
            b = fv.get("basis")
            cited = [claims[x] for x in fv.get("claims") or [] if x in claims]
            if len(cited) != len(fv.get("claims") or []): E.append(f"{tag}: {f} cites unknown claims")
            if b not in V.BASIS: E.append(f"{tag}: {f}.basis invalid"); continue
            if f == "what_happened" and b == "analysis":
                E.append(f"{tag}: what_happened cannot rest on analysis")
            if b in STRENGTH:
                if not cited: E.append(f"{tag}: {f} is {b} but cites no claim")
                elif any(c["category"] == "analysis" for c in cited):
                    E.append(f"{tag}: {f} is {b} but cites analysis (an interpretation cannot become a fact)")
                elif STRENGTH[b] > min(STRENGTH[c["category"]] for c in cited):
                    E.append(f"{tag}: {f} claims '{b}' but its weakest claim is '{min(cited, key=lambda c: STRENGTH[c['category']])['category']}'")
        for s in dv.get("sources") or []:
            if not (isinstance(s, dict) and isinstance(s.get("url"), str) and s["url"].startswith("https://")):
                E.append(f"{tag}: sources need https urls (the contributor's own account is added automatically)")
            elif s.get("kind", "official") not in ("official", "media", "analysis"):
                E.append(f"{tag}: source kind must be official, media or analysis")
        for r in dv.get("related") or []:
            if r not in feed_ids: E.append(f"{tag}: related item {r!r} is not in the feed")
        if meta["confidentiality"] == "chatham":
            names = [c.get("speaker") for c in claims.values() if c["category"] == "attributed"]
            W.append(f"{tag}: Chatham House: check that speakers {names} are not identifiable in the text")
    art = prop.get("article")
    if art is not None:
        if not (isinstance(art, dict) and V._str(art.get("title")) and isinstance(art.get("blocks"), list) and art["blocks"]):
            E.append("article needs title and blocks")
        else:
            for i, b in enumerate(art["blocks"]):
                if b.get("basis") not in V.BASIS or not V._str(b.get("md")): E.append(f"article block {i}: basis and md required"); continue
                if not b.get("paras") or any(not isinstance(n, int) or n not in ptext for n in b["paras"]):
                    E.append(f"article block {i}: paras must name the document paragraphs it comes from")
                if "<" in b["md"]: E.append(f"article block {i}: no raw HTML")
                cited = [claims_all[x] for x in b.get("claims") or [] if x in claims_all]
                if b["basis"] in STRENGTH and any(c["category"] == "analysis" for c in cited):
                    E.append(f"article block {i}: {b['basis']} block cites analysis")
                if b["basis"] in STRENGTH and cited and STRENGTH[b["basis"]] > min(STRENGTH.get(c["category"], 0) for c in cited):
                    E.append(f"article block {i}: basis stronger than its claims")
    return E, W


def propose(sid, path):
    d = sub_dir(sid)
    meta = P.load_json(d / "meta.json", {})
    paras = P.load_json(d / "paragraphs.json", [])
    feed = json.loads(FEED.read_text(encoding="utf-8"))
    prop = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    E, W = check_proposal(prop, paras, meta, feed)
    for w in W:
        print(f"warning: {w}")
    if E:
        sys.exit("proposal rejected:\n- " + "\n- ".join(E))
    P.save_json(d / "proposal.json", prop)
    import today as T
    dp = T.drafts_path()
    drafts = T.load(dp)
    public_ids = {e["id"] for e in T.load(T.TODAY)["entries"]}
    perm = meta["permissions"]
    pc = meta["contributor"]
    if perm["attribute"] == "named":
        contrib = {"display": "named", "name": pc["name"], "affiliation": pc.get("affiliation"), "role": pc["role"]}
        contrib = {k: v for k, v in contrib.items() if v}
    else:
        contrib = {"display": "anonymous", "role": pc["role"]}
    aid = f"{meta['event_date']}-readout-{meta['sha256'][:6]}" if prop.get("article") else None
    made = []
    for dv in prop["developments"]:
        # public ids never carry the private title: date + development key + submission fingerprint
        eid = f"{meta['event_date']}-{dv['key']}-{meta['sha256'][:6]}"
        if any(e["id"] == eid for e in drafts["entries"]) or eid in public_ids:
            sys.exit(f"entry {eid} already exists (re-run after removing it, or change the development key)")
        claims = dv["claims"]
        own = {"title": KIND_LABEL[meta["kind"]], "publisher": contrib.get("name") or T.ANON,
               "url": None, "kind": "contributor", "verified": False, "date": meta["event_date"]}
        sources = [own] + [dict(s, verified=False) for s in dv.get("sources") or []]
        for u in meta.get("source_urls") or []:
            if not any(s.get("url") == u for s in sources):
                sources.append({"title": u, "url": u, "kind": "official", "verified": False})
        flags = [{"code": "ai_draft", "msg": "AI-assisted draft: check every field and claim against the original document"}]
        for c in claims:
            if c["category"] == "unverified":
                flags.append({"code": "unverified_claim", "msg": f"unverified claim ({c['id']}, ¶{c.get('para')}): {c['text']}"})
            if c["category"] == "verified":
                flags.append({"code": "verify_source", "msg": f"open {c['source_url']} and confirm claim {c['id']}: {c['text']}"})
        if not any(s.get("url") for s in sources):
            flags.append({"code": "missing_source_url", "msg": "no public source URL: only the contributor's account supports this card; look for an official document"})
        if meta["confidentiality"] == "chatham":
            flags.append({"code": "chatham", "msg": "Chatham House rule: confirm no speaker or affiliation is identifiable"})
        if meta["confidentiality"] == "confidential":
            flags.append({"code": "confidential", "msg": "confidential submission: not publishable"})
        if perm["attribute"] == "ask":
            flags.append({"code": "attribution", "msg": "contributor's attribution preference not recorded: confirm named or anonymous"})
        linked = set(dv.get("related") or [])
        card_text = " ".join([dv["headline"]] + [dv[f]["text"] for f in FACT_FIELDS if isinstance(dv.get(f), dict)])
        for r in related_items(card_text, dv.get("event_at") or meta["event_date"], n=5):
            if r["id"] not in linked and r["score"] >= 0.15:
                flags.append({"code": "possible_duplicate", "ref": r["id"],
                              "msg": f"may describe the same development as monitoring item {r['id']} ({r['title'][:80]}): "
                                     f"link it (today.py link) or resolve as distinct"})
        en = {
            "id": eid, "status": "draft", "headline": dv["headline"], "theme": dv["theme"],
            "areas": dv.get("areas") or [], "classification": dv["classification"], "verification": dv["verification"],
            "event_at": dv.get("event_at") or meta["event_date"], "assessed_at": P.now(),
            "basis": {f: dv[f]["basis"] for f in FACT_FIELDS if isinstance(dv.get(f), dict)},
            "actors": dv.get("actors") or [], "sources": sources, "related": sorted(linked),
            "contributor": contrib, "i18n": {},
            "_private": {"submission": sid, "claims": claims, "flags": flags, "permissions": perm,
                         "confidentiality": meta["confidentiality"], "anonymity_reason": meta.get("anonymity_reason"),
                         "contributor": pc, "article": aid, "ai_assisted": True, "proposal_key": dv["key"]},
        }
        for f in FACT_FIELDS:
            if isinstance(dv.get(f), dict):
                en[f] = dv[f]["text"]
        if V._str(dv.get("open_questions")):
            en["open_questions"] = dv["open_questions"]
        drafts["entries"].insert(0, en)
        made.append((eid, len(flags)))
    T.save(dp, drafts)
    if aid:
        art = prop["article"]
        a = {"schema": 1, "id": aid, "entries": [m[0] for m in made], "status": "draft", "title": art["title"],
             "standfirst": art.get("standfirst") or "", "event_at": meta["event_date"], "assessed_at": P.now(),
             "blocks": [{k: b[k] for k in ("basis", "heading", "md") if b.get(k)} for b in art["blocks"]],
             "contributor": contrib,
             "sources": [{"title": KIND_LABEL[meta["kind"]], "publisher": contrib.get("name") or T.ANON,
                          "url": None, "kind": "contributor", "verified": False, "date": meta["event_date"]}],
             "i18n": {},
             "_private": {"submission": sid, "block_paras": [b.get("paras") for b in art["blocks"]],
                          "block_claims": [b.get("claims") for b in art["blocks"]], "permissions": perm,
                          "confidentiality": meta["confidentiality"]}}
        P.save_json(P.ensure() / "articles" / f"{aid}.json", a)
    meta["drafts"] = [m[0] for m in made]
    meta["article"] = aid
    P.save_json(d / "meta.json", meta)
    print(f"{len(made)} private draft card(s) from {sid}:")
    for eid, nf in made:
        print(f"  {eid}  ({nf} flag(s) to resolve)")
    if aid:
        print(f"  article draft {aid}" + ("" if perm["publish_analysis"] else "  (contributor has NOT authorized publishing the full analysis)"))
    print("review: python3 -I tools/today.py show <id>; preview: python3 -I tools/preview.py")


def related_cmd(x):
    import today as T
    d = P.ensure() / "intake" / x
    if d.exists():
        text, date = (d / "text.md").read_text(encoding="utf-8"), P.load_json(d / "meta.json", {}).get("event_date")
    else:
        en = T.find(T.load(T.drafts_path()), x, "the private drafts")
        text = " ".join(str(en.get(f) or "") for f in ("headline",) + FACT_FIELDS)
        date = en.get("event_at")
    for r in related_items(text, date):
        print(f"{r['score']:.3f}  {r['id']}  ({r['date']})  {r['title'][:90]}\n        shared: {', '.join(r['shared'])}")


def list_cmd():
    for m in sorted((P.ensure() / "intake").glob("*/meta.json")):
        meta = P.load_json(m, {})
        print(f"{meta['id']}  {meta['kind']:12} {meta['confidentiality']:12} drafts: {len(meta.get('drafts') or [])}  {meta['title'][:60]}")


def show_cmd(sid):
    meta = P.load_json(sub_dir(sid) / "meta.json", {})
    print(json.dumps(meta, ensure_ascii=False, indent=1))


def main(a):
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "add" and len(a) > 1: add(a)
    elif cmd == "prompt": prompt(a[1])
    elif cmd == "propose": propose(a[1], a[2])
    elif cmd == "related": related_cmd(a[1])
    elif cmd == "list": list_cmd()
    elif cmd == "show": show_cmd(a[1])
    else: sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
