"""V1.1 human-intelligence workflow: ingestion, provenance, draft isolation, publication gates,
corrections and retractions. Runs on a throwaway copy of the repository and a throwaway private store;
every document used here is synthetic (tests/fixtures/intake), nothing real or sensitive.

  python3 -m unittest tests.test_intake
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
FIX = REPO / "tests" / "fixtures" / "intake"
LANGS = ("en", "es", "fr", "ru", "zh", "ar")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="cop31-v11-"))
        self.root = self.tmp / "site"
        shutil.copytree(REPO, self.root, ignore=shutil.ignore_patterns(".git", "node_modules", "editorial", "__pycache__", "i18n"))
        (self.root / "data" / "today.json").write_text(json.dumps({"schema": 1, "entries": []}), encoding="utf-8")
        shutil.rmtree(self.root / "data" / "articles", ignore_errors=True)
        self.store = self.tmp / "private"
        self.env = dict(os.environ, COP31_PRIVATE=str(self.store))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, tool, *args, ok=True, stdin=None, env=None):
        r = subprocess.run([sys.executable, "-I", str(self.root / "tools" / tool), *map(str, args)], capture_output=True,
                           text=True, env=env or self.env, input=stdin, cwd=self.root, timeout=120)
        if ok and r.returncode != 0:
            self.fail(f"{tool} {args} failed:\n{r.stdout}\n{r.stderr}")
        if not ok and r.returncode == 0:
            self.fail(f"{tool} {args} should have failed:\n{r.stdout}")
        return r.stdout + r.stderr

    def add(self, path=FIX / "synthetic_readout.md", *extra):
        out = self.run_tool("intake.py", "add", path, "--title", "Synthetic briefing readout", "--contributor", "Test Author",
                            "--affiliation", "Example Institute", "--role", "observer", "--event-date", "2099-01-01", *extra)
        return out.split("submission ")[1].split(":")[0]

    def drafts(self):
        return json.loads((self.store / "drafts.json").read_text(encoding="utf-8"))["entries"]

    def proposal(self, mutate=None):
        p = json.loads((FIX / "synthetic_proposal.json").read_text(encoding="utf-8"))
        if mutate:
            mutate(p)
        f = self.tmp / "prop.json"
        f.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
        return f

    def ready(self, attribute="named", publish_analysis="yes", **kw):
        sid = self.add(FIX / "synthetic_readout.md", "--attribute", attribute, "--publish-analysis", publish_analysis,
                       *(["--anonymity-reason", "source at risk"] if attribute == "anonymous" else []))
        self.run_tool("intake.py", "propose", sid, self.proposal())
        return sid

    def translate_all(self, eid):
        self.run_tool("today.py", "i18n-export", eid)
        pt = json.loads((self.store / "i18n" / f"{eid}.pt.json").read_text(encoding="utf-8"))
        for l in LANGS:
            if "blocks" in pt:
                tr = {k: f"[{l}] {v}" for k, v in pt.items() if k != "blocks"}
                tr["blocks"] = [{k: f"[{l}] {v}" for k, v in b.items()} for b in pt["blocks"]]
            else:
                tr = {k: f"[{l}] {v}" for k, v in pt.items()}
            f = self.tmp / f"{eid}.{l}.json"
            f.write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
            self.run_tool("today.py", "i18n-import", eid, l, f, "--method", "machine-reviewed", "--by", "Reviewer")

    def resolve_all(self, eid):
        en = next(e for e in self.drafts() if e["id"] == eid)
        for i, _ in enumerate(en["_private"]["flags"], 1):
            self.run_tool("today.py", "resolve", eid, i, "--by", "Editor", "--note", "checked against the original")


class Ingestion(Base):
    def test_markdown_numbered_paragraphs_and_private_copy(self):
        sid = self.add()
        d = self.store / "intake" / sid
        self.assertEqual((d / "original.md").read_bytes(), (FIX / "synthetic_readout.md").read_bytes())
        paras = json.loads((d / "paragraphs.json").read_text())
        self.assertTrue(any("three scenarios" in p["text"] for p in paras))
        self.assertEqual(oct((d / "original.md").stat().st_mode)[-3:], "600")
        meta = json.loads((d / "meta.json").read_text())
        self.assertEqual(len(meta["sha256"]), 64)
        self.assertEqual(meta["permissions"], {"attribute": "ask", "publish_analysis": False, "publish_document": False})

    def test_docx_and_pdf_and_paste(self):
        import docx
        doc = docx.Document()
        doc.add_heading("[SYNTHETIC] Heading", 1)
        doc.add_paragraph("The presidency said the grid is voluntary.")
        doc.add_table(rows=1, cols=2).rows[0].cells[0].text = "Low scenario"
        p = self.tmp / "in.docx"; doc.save(p)
        sid = self.add(p)
        paras = [x["text"] for x in json.loads((self.store / "intake" / sid / "paragraphs.json").read_text())]
        self.assertIn("## [SYNTHETIC] Heading", paras)
        self.assertIn("Low scenario", paras[-1])
        # PDF made with pandoc is not available everywhere; build one from text with a tiny writer
        pdf = self.tmp / "in.pdf"
        _write_pdf(pdf, ["[SYNTHETIC] PDF readout", "", "The presidency said the low scenario reaches 320 credits."])
        out = self.run_tool("intake.py", "add", pdf, "--title", "pdf test", "--contributor", "X", "--role", "author")
        sid2 = out.split("submission ")[1].split(":")[0]
        text = (self.store / "intake" / sid2 / "text.md").read_text()
        self.assertIn("320 credits", text)
        self.assertIn("scanned PDF", out)   # very short text layer is flagged, not OCR'd
        out = self.run_tool("intake.py", "add", "-", "--title", "pasted", "--contributor", "Y", "--role", "analyst",
                            stdin="First paragraph.\n\nSecond paragraph with a figure of 12.")
        self.assertIn("2 paragraphs", out)

    def test_same_document_twice_is_refused(self):
        self.add()
        out = self.run_tool("intake.py", "add", FIX / "synthetic_readout.md", "--title", "again", "--contributor", "Z",
                            "--role", "author", ok=False)
        self.assertIn("already submitted", out)

    def test_multiple_developments_and_article_from_one_document(self):
        sid = self.ready()
        ids = [e["id"] for e in self.drafts()]
        self.assertEqual(len(ids), 2)
        self.assertTrue(any("-scenarios-" in i for i in ids) and any("-grid-" in i for i in ids))
        self.assertTrue(all("synthetic" not in i for i in ids), "public ids never carry the private title")
        art = json.loads(next((self.store / "articles").glob("*.json")).read_text())
        self.assertEqual(sorted(art["entries"]), sorted(ids))
        self.assertEqual([b["basis"] for b in art["blocks"]], ["attributed", "analysis"])


class Provenance(Base):
    def reject(self, mutate, needle):
        sid = self.add()
        out = self.run_tool("intake.py", "propose", sid, self.proposal(mutate), ok=False)
        self.assertIn(needle, out)
        self.assertFalse((self.store / "drafts.json").exists() and self.drafts())

    def test_quote_must_be_in_the_document(self):
        self.reject(lambda p: p["developments"][0]["claims"][0].update(quote="the fund was approved unanimously"),
                    "quote not found in the document")

    def test_verified_needs_official_source(self):
        self.reject(lambda p: p["developments"][0]["claims"][0].update(category="verified"), "needs an official https source_url")

    def test_analysis_cannot_become_fact(self):
        def m(p):
            p["developments"][0]["what_changed"] = {"text": "x", "basis": "attributed", "claims": ["c4"]}
        self.reject(m, "cites analysis")

    def test_what_happened_never_analysis(self):
        def m(p):
            p["developments"][0]["what_happened"]["basis"] = "analysis"
        self.reject(m, "what_happened cannot rest on analysis")

    def test_field_not_stronger_than_its_claims(self):
        def m(p):
            p["developments"][0]["watch_next"]["basis"] = "attributed"   # cites c5, unverified
        self.reject(m, "weakest claim is 'unverified'")

    def test_attributed_needs_speaker(self):
        self.reject(lambda p: p["developments"][1]["claims"][0].pop("speaker"), "need a speaker")

    def test_claims_and_flags_are_kept_privately(self):
        self.ready()
        en = next(e for e in self.drafts() if "-scenarios-" in e["id"])
        codes = [f["code"] for f in en["_private"]["flags"]]
        self.assertIn("ai_draft", codes)
        self.assertIn("unverified_claim", codes)
        self.assertIn("contributor_only", codes)
        self.assertEqual(en["basis"]["why_it_matters"], "analysis")
        self.assertEqual(en["basis"]["watch_next"], "unverified")
        self.assertEqual(en["sources"][0]["kind"], "contributor")
        self.assertIsNone(en["sources"][0]["url"])


class Isolation(Base):
    def test_store_refused_inside_repository(self):
        env = dict(self.env, COP31_PRIVATE=str(self.root / "editorial"))
        out = self.run_tool("intake.py", "list", ok=False, env=env)
        self.assertIn("refusing private store inside the repository", out)

    def test_store_refused_inside_public_clone(self):
        clone = self.tmp / "clone"
        clone.mkdir()
        subprocess.run(["git", "init", "-q", str(clone)], check=True)
        subprocess.run(["git", "-C", str(clone), "remote", "add", "origin", "https://github.com/gtpinhei/cop31.git"], check=True)
        env = dict(self.env, COP31_PRIVATE=str(clone / "private"))
        out = self.run_tool("intake.py", "list", ok=False, env=env)
        self.assertIn("clone of the public repository", out)

    def test_nothing_written_inside_the_site_before_publication(self):
        before = {p: p.stat().st_mtime for p in self.root.rglob("*") if p.is_file()}
        self.ready()
        after = {p: p.stat().st_mtime for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after, "intake and propose must not touch the site tree")

    def test_validator_rejects_private_fields_and_drafts_in_public_file(self):
        self.ready()
        en = self.drafts()[0]
        doc = {"schema": 1, "entries": [dict(en, status="published", approved_by="X", approved_at="2099-01-01T10:00+03:00")]}
        p = self.root / "data" / "today.json"
        p.write_text(json.dumps(doc, ensure_ascii=False))
        out = subprocess.run([sys.executable, "-I", str(self.root / "tools" / "validate_feed.py")], capture_output=True, text=True, cwd=self.root)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("non-public fields", out.stdout)


class Publication(Base):
    def card(self, key):
        return next(e["id"] for e in self.drafts() if key + "-" in e["id"])

    def test_gates_then_publish_strips_private_material(self):
        self.ready()
        eid = self.card("-grid")
        out = self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1, ok=False)
        self.assertIn("flag 1 unresolved", out)
        self.assertIn("translation en missing", out)
        self.resolve_all(eid)
        self.translate_all(eid)
        self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1)
        pub = json.loads((self.root / "data" / "today.json").read_text())["entries"][0]
        self.assertNotIn("_private", pub)
        self.assertEqual(pub["contributor"], {"display": "named", "name": "Test Author", "affiliation": "Example Institute", "role": "observer"})
        blob = json.dumps(pub, ensure_ascii=False)
        sid = next((self.store / "intake").iterdir()).name
        for secret in ("sha256", "claims", "quote", "flags", "permissions", "intake", sid, "Synthetic briefing readout"):
            self.assertNotIn(secret, blob)   # private title and submission id never reach the public file
        audit = json.loads((self.store / "published.json").read_text())["entries"][eid]
        self.assertTrue(all(f["resolved_by"] == "Editor" for f in audit["_private"]["flags"]))
        r = subprocess.run([sys.executable, "-I", str(self.root / "tools" / "validate_feed.py"), "-q"], capture_output=True, text=True, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_named_attribution_needs_permission(self):
        self.ready(attribute="ask")
        eid = self.card("-grid")
        self.resolve_all(eid); self.translate_all(eid)
        self.run_tool("today.py", "set", eid, "contributor.display", "named")
        out = self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1, ok=False)
        self.assertIn("not authorized public attribution", out)

    def test_anonymous_publication_hides_identity(self):
        self.ready(attribute="anonymous")
        eid = self.card("-grid")
        self.resolve_all(eid); self.translate_all(eid)
        self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1)
        pub = (self.root / "data" / "today.json").read_text()
        self.assertNotIn("Test Author", pub)
        self.assertNotIn("Example Institute", pub)
        self.assertIn('"display": "anonymous"', pub)

    def test_anonymous_card_cannot_leak_the_name(self):
        self.ready(attribute="anonymous")
        eid = self.card("-grid")
        self.resolve_all(eid)
        self.run_tool("today.py", "set", eid, "why_it_matters", "Test Author avalia que a grade importa.")
        self.translate_all(eid)
        out = self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1, ok=False)
        self.assertIn("still mentions the contributor's name", out)

    def test_switching_to_anonymous_renames_own_source(self):
        self.ready(attribute="named")
        eid = self.card("-grid")
        self.run_tool("today.py", "set", eid, "contributor.display", "anonymous")
        en = next(e for e in self.drafts() if e["id"] == eid)
        self.assertNotIn("Test Author", json.dumps({k: v for k, v in en.items() if k != "_private"}, ensure_ascii=False))

    def test_confidential_never_publishes(self):
        sid = self.add(FIX / "synthetic_readout.md", "--confidentiality", "confidential", "--attribute", "named")
        self.run_tool("intake.py", "propose", sid, self.proposal())
        eid = self.card("-grid")
        self.resolve_all(eid); self.translate_all(eid)
        out = self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1, ok=False)
        self.assertIn("confidential", out)
        self.assertEqual(json.loads((self.root / "data" / "today.json").read_text())["entries"], [])

    def test_article_needs_permission_and_a_published_card(self):
        self.ready(publish_analysis="no")
        aid = next((self.store / "articles").glob("*.json")).stem
        self.translate_all(aid)
        out = self.run_tool("today.py", "publish-article", aid, "--by", "Editor", ok=False)
        self.assertIn("not authorized publication of the full analysis", out)
        self.assertIn("publish at least one of its Today cards first", out)

    def test_reporting_note_reaches_the_readout(self):
        sid = self.ready()
        self.run_tool("intake.py", "note", sid, "--reporting-note", "Presença direta na coletiva.", ok=False)   # --by required
        self.run_tool("intake.py", "note", sid, "--reporting-note", "Presença direta na coletiva.", "--by", "Editor")
        art = json.loads(next((self.store / "articles").glob("*.json")).read_text())
        self.assertEqual(art["reporting_note"], "Presença direta na coletiva.")

    def test_article_publication_links_card(self):
        self.ready()
        eid = self.card("-grid")
        self.resolve_all(eid); self.translate_all(eid)
        self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1)
        aid = next((self.store / "articles").glob("*.json")).stem
        self.translate_all(aid)
        self.run_tool("today.py", "publish-article", aid, "--by", "Editor")
        art = json.loads((self.root / "data" / "articles" / f"{aid}.json").read_text())
        self.assertEqual(art["status"], "published")
        self.assertNotIn("_private", art)
        self.assertNotIn("paras", json.dumps(art))
        pub = json.loads((self.root / "data" / "today.json").read_text())["entries"][0]
        self.assertEqual(pub["article"], aid)
        r = subprocess.run([sys.executable, "-I", str(self.root / "tools" / "validate_feed.py"), "-q"], capture_output=True, text=True, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_cross_reference_resolves_duplicate_flag(self):
        self.ready()
        eid = self.card("-scenarios")
        feed = json.loads((self.root / "data" / "feed.json").read_text())
        fid = feed["items"][0]["id"]
        out = self.run_tool("today.py", "link", eid, fid, ok=False)
        self.assertIn("--reason and --by are required", out)
        self.run_tool("today.py", "link", eid, fid, "--reason", "same report", "--by", "Editor")
        en = next(e for e in self.drafts() if e["id"] == eid)
        self.assertIn(fid, en["related"])
        self.assertEqual(en["_private"]["matches"][-1]["decision"], "linked")
        self.assertEqual(en["_private"]["matches"][-1]["reason"], "same report")
        self.run_tool("today.py", "link", eid, "no-such-item", "--reason", "x", "--by", "E", ok=False)
        fid2 = feed["items"][1]["id"]
        self.run_tool("today.py", "distinct", eid, fid2, "--reason", "same topic, different event", "--by", "Editor")
        en = next(e for e in self.drafts() if e["id"] == eid)
        self.assertNotIn(fid2, en["related"])
        self.assertEqual(en["_private"]["matches"][-1]["decision"], "distinct")

    def test_correction_marks_translations_pending_and_retraction_leaves_notice(self):
        self.ready()
        eid = self.card("-grid")
        self.resolve_all(eid); self.translate_all(eid)
        self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1)
        self.run_tool("today.py", "correct", eid, "--by", "Editor", "--note", "Nome do mecanismo corrigido.",
                      "--field", "what_happened", "--text", "[TESTE] Texto corrigido.")
        pub = json.loads((self.root / "data" / "today.json").read_text())["entries"][0]
        self.assertEqual(pub["corrections"][0]["note"], "Nome do mecanismo corrigido.")
        self.assertEqual(sorted(pub["i18n_pending"]), sorted(LANGS))   # disclosed, not silently stale
        self.assertNotIn("what_happened", pub["i18n"]["en"])
        self.run_tool("today.py", "retract", eid, "--by", "Editor", "--reason", "Fonte retirou a declaração.")
        doc = json.loads((self.root / "data" / "today.json").read_text())
        self.assertEqual(doc["entries"], [])
        self.assertEqual(doc["retractions"][0]["id"], eid)
        self.assertEqual(self.drafts()[0]["status"], "retracted")


class EditorialDecisions(Base):
    def card(self, key):
        return next(e["id"] for e in self.drafts() if key + "-" in e["id"])

    def test_named_by_default_but_unauthorized_until_recorded(self):
        sid = self.add(FIX / "synthetic_readout.md", "--attribute", "ask", "--display-default", "named", "--publish-analysis", "no")
        self.run_tool("intake.py", "propose", sid, self.proposal())
        eid = self.card("-grid")
        en = next(e for e in self.drafts() if e["id"] == eid)
        self.assertEqual(en["contributor"]["display"], "named")          # prepared as named
        self.assertEqual(en["_private"]["permissions"]["attribute"], "ask")  # but not authorized
        self.assertTrue(any(f["code"] == "attribution" and "NOT authorized" in f["msg"] for f in en["_private"]["flags"]))
        others = [i for i, f in enumerate(en["_private"]["flags"], 1) if f["code"] != "attribution"]
        for i in others:
            self.run_tool("today.py", "resolve", eid, i, "--by", "Editor", "--note", "checked")
        self.translate_all(eid)
        out = self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1, ok=False)
        self.assertIn("not authorized public attribution", out)
        self.run_tool("intake.py", "permissions", sid, "--attribute", "named", ok=False)   # --by required
        self.run_tool("intake.py", "permissions", sid, "--attribute", "named", "--by", "Editor")
        meta = json.loads((self.store / "intake" / sid / "meta.json").read_text())
        self.assertEqual(meta["permissions_history"][0]["by"], "Editor")
        self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1)

    def test_contributor_only_card_needs_authorized_attribution_and_never_verified(self):
        sid = self.add(FIX / "synthetic_readout.md", "--attribute", "ask")
        self.run_tool("intake.py", "propose", sid, self.proposal())
        eid = self.card("-grid")
        self.resolve_all(eid)
        self.translate_all(eid)
        out = self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1, ok=False)
        self.assertIn("record the contributor's authorized attribution first", out)
        self.run_tool("today.py", "set", eid, "basis.what_happened", "verified")
        self.run_tool("intake.py", "permissions", sid, "--attribute", "anonymous", "--anonymity-reason", "safety", "--by", "Editor")
        out = self.run_tool("today.py", "publish", eid, "--by", "Editor", "--verified-source", 1, ok=False)
        self.assertIn("cannot carry 'verified'", out)

    def test_priority_and_proposed_links_need_confirmation(self):
        sid = self.add()
        feed = json.loads((self.root / "data" / "feed.json").read_text())
        fid = feed["items"][0]["id"]
        def m(p):
            p["developments"][1]["related"] = [fid]
            p["developments"][1]["related_reasons"] = {fid: "test reason"}
        self.run_tool("intake.py", "propose", sid, self.proposal(m))
        eid = self.card("-grid")
        en = next(e for e in self.drafts() if e["id"] == eid)
        self.assertEqual(en["_private"]["matches"][0], {**en["_private"]["matches"][0], "decision": "proposed", "reason": "test reason"})
        self.assertTrue(any(f["code"] == "confirm_link" and f["ref"] == fid for f in en["_private"]["flags"]))
        self.run_tool("today.py", "priority", eid, "lead")
        self.run_tool("today.py", "priority", eid, "urgent", ok=False)
        self.assertIn("priority:lead", self.run_tool("today.py", "list"))


class Compatibility(Base):
    def test_feed_merge_unaffected(self):
        feed = self.root / "data" / "feed.json"
        before = feed.read_text()
        r = subprocess.run([sys.executable, "-I", str(self.root / "tools" / "merge_feed.py"), str(feed)], capture_output=True, text=True, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(feed.read_text())["items"], json.loads(before)["items"])

    def test_legacy_drafts_migrate_out_of_the_repository(self):
        legacy = self.root / "editorial" / "drafts.json"
        legacy.parent.mkdir()
        legacy.write_text(json.dumps({"schema": 1, "entries": [{"id": "old-1", "status": "draft", "headline": "x"}]}))
        out = self.run_tool("today.py", "list")
        self.assertIn("legacy drafts file", out)
        self.run_tool("today.py", "migrate")
        self.assertFalse(legacy.exists())
        self.assertEqual(self.drafts()[0]["id"], "old-1")


def _write_pdf(path, lines):
    """Minimal one-page PDF with a text layer (Helvetica), enough for pdftotext."""
    text = "BT /F1 12 Tf 72 720 Td 14 TL " + " ".join("(" + l.replace("(", "").replace(")", "") + ") '" for l in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(text)} >>\nstream\n{text}\nendstream", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(out)


if __name__ == "__main__":
    unittest.main()
