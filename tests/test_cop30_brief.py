"""COP30 Presidency Daily Brief collector: discovery, 2025 exclusion, EN/PT pairing, revisions, malformed and
placeholder responses, idempotent re-runs, and the hourly sync's other steps left alone.
Synthetic Plone/Volto documents only (no text from the real briefs); runs against a throwaway private store.

  python3 -I -m unittest discover -s tests -k Cop30
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
EN = "https://cop30.br/en/news-about-cop30/daily-brief"
PT = "https://cop30.br/pt-br/noticias-da-cop30/boletim-diario"
SID = "cop30-presidency-daily-brief"
LANGS = ("en", "es", "fr", "ru", "zh", "ar")


def slate(text, strong=None, link=None):
    kids = [{"text": ""}]
    if strong:
        kids.append({"type": "strong", "children": [{"text": strong}]})
    kids.append({"text": text})
    if link:
        kids.append({"type": "link", "data": {"url": link}, "children": [{"text": link}]})
    return {"@type": "slate", "plaintext": (strong + " " if strong else "") + text + (" " + link if link else ""),
            "value": [{"type": "p", "children": kids}]}


def edition(url, effective, title="Synthetic Presidency Brief", desc="November 10", lang="en", headline="Alpha headline",
            body_extra="", n_events=2, modified="2026-11-10T00:00:00+00:00", uid=None):
    pt = lang == "pt"
    blocks = [slate(headline), slate(("TEMA DO DIA: " if pt else "THEMATIC FOCUS: ") + "Synthetic Theme"),
              slate("The synthetic presidency presents its synthetic roadmap on example transitions to example parties, "
                    "with a synthetic launch of an example yearbook and other placeholder activities for testing. " + body_extra,
                    link="https://unfccc.int/example"),
              slate("Momentos-chave" if pt else "Key Moments"),
              slate("Destaques" if pt else "Highlights")]
    for i in range(n_events):
        blocks.append(slate(f"\nPlaceholder event description number {i}.\nRoom: Example Hall {i}\n", strong=f"{9 + i}:00AM–{10 + i}:00AM | Example Event {i}"))
    blocks += [slate("Retrospectiva do Dia 1" if pt else "Day 1 in Review"),
               slate("Example review sentence describing a previous synthetic day of testing activity for the collector."),
               {"@type": "columnsBlock", "data": {"blocks_layout": {"items": ["c"]}, "blocks": {"c": {
                   "blocks_layout": {"items": ["b"]}, "blocks": {"b": {"@type": "buttonBlock", "label": "x",
                                                                         "href": [{"@id": "https://cop31.tr/"}]}}}}}}]
    ids = [f"b{i}" for i in range(len(blocks))]
    return {"@id": url, "@type": "News Item", "UID": uid or ("u" + str(abs(hash(url)))[:10]), "title": title, "description": desc,
            "effective": effective, "modified": modified, "created": effective, "language": {"token": lang},
            "blocks": dict(zip(ids, blocks)), "blocks_layout": {"items": ids}}


def search(index, rows):
    return {"@id": index + "/@search?portal_type=News+Item", "items_total": len(rows),
            "items": [{"@id": u, "@type": "News Item", "UID": "x" + str(abs(hash(u)))[:8], "title": t, "description": "",
                       "effective": e, "modified": m, "created": e, "image_scales": {"image": []}} for u, t, e, m in rows]}


class Cop30(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="cop31-c30-"))
        self.env = dict(os.environ, COP31_PRIVATE=str(self.tmp / "private"))
        self.n = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def put(self, doc, wrap=None):
        self.n += 1
        p = self.tmp / f"r{self.n}.json"
        txt = json.dumps(doc)
        if wrap == "nimble":       # a saved Nimble tool result
            txt = json.dumps([{"type": "text", "text": json.dumps({"content": txt, "url": "x"}) + '{"conversation_id": "c"}'}])
        p.write_text(txt if isinstance(doc, (dict, list)) else doc)
        return p

    def put_raw(self, text):
        self.n += 1
        p = self.tmp / f"r{self.n}.txt"
        p.write_text(text)
        return p

    def tool(self, *args, script="cop30_brief.py", ok=True):
        r = subprocess.run([sys.executable, "-I", str(REPO / "tools" / script), *map(str, args)], capture_output=True,
                           text=True, env=self.env, timeout=60, cwd=self.tmp)
        if ok and r.returncode != 0:
            self.fail(f"{args}: {r.stdout}\n{r.stderr}")
        return r.stdout

    def j(self, *args, **kw):
        return json.loads(self.tool(*args, **kw))

    def state(self):
        return json.loads((self.tmp / "private" / "cop30brief" / "state.json").read_text())

    def indexes(self, extra_en=(), extra_pt=()):
        en = search(EN, [(f"{EN}/nov10_x", "Synthetic Presidency Brief", "2026-11-10T05:00:00+00:00", "2026-11-10T00:00:00+00:00"),
                         *extra_en,
                         (f"{EN}/cop30-morning-brief-november-11", "Old Morning Brief", "2025-11-11T12:00:00+00:00", "2026-11-09T18:00:00+00:00")])
        pt = search(PT, [(f"{PT}/nov10_y", "Boletim Sintético", "2026-11-10T05:00:00+00:00", "2026-11-10T00:10:00+00:00"),
                         *extra_pt,
                         (f"{PT}/boletim-da-manha-da-cop30-11-de-novembro", "Boletim antigo", "2025-11-11T12:00:00+00:00", "2026-11-09T01:00:00+00:00")])
        return self.put(en, "nimble"), self.put(pt)

    def collect_day10(self, **kw):
        files = [self.put({"@id": f"{EN}/nov10_x/@translations", "items": [{"@id": f"{PT}/nov10_y", "language": "pt-br"}]}),
                 self.put(edition(f"{PT}/nov10_y", "2026-11-10T05:00:00+00:00", title="Boletim Sintético", desc="10 de novembro",
                                  lang="pt", headline="Manchete alfa", modified="2026-11-10T00:10:00+00:00")),
                 self.put(edition(f"{EN}/nov10_x", "2026-11-10T05:00:00+00:00", **kw), "nimble")]
        return self.j("collect", *files, "--out", self.tmp / "out")

    # --- tests ---
    def test_discovery_new_edition_excludes_2025(self):
        en, pt = self.indexes()
        d = self.j("discover", en, pt)
        self.assertEqual(d["outcome"], "success")
        self.assertEqual(sorted(d["series_editions"]), [f"{EN}/nov10_x", f"{PT}/nov10_y"])
        self.assertEqual(d["excluded_2025"], 2)          # 2025 briefs excluded although modified in 2026
        urls = [f["url"] for f in d["fetch"]]
        self.assertIn("https://cop30.br/++api++/en/news-about-cop30/daily-brief/nov10_x", urls)
        self.assertIn("https://cop30.br/++api++/en/news-about-cop30/daily-brief/nov10_x/@translations", urls)
        self.assertFalse(any("morning-brief" in u or "boletim-da-manha" in u for u in urls))

    def test_index_with_multiple_editions(self):
        en, pt = self.indexes(extra_en=[(f"{EN}/nov9_x", "Synthetic Presidency Brief", "2026-11-09T05:00:00+00:00", "2026-11-09T12:00:00+00:00")],
                              extra_pt=[(f"{PT}/nov9_y", "Boletim Sintético", "2026-11-09T05:00:00+00:00", "2026-11-09T13:00:00+00:00")])
        d = self.j("discover", en, pt)
        self.assertEqual(len(d["series_editions"]), 4)
        self.assertEqual(sum(1 for f in d["fetch"] if f["kind"] == "edition"), 4)

    def test_en_pt_pair_one_canonical_entry(self):
        self.j("discover", *self.indexes())
        c = self.collect_day10()
        self.assertEqual(c["new"], [f"{SID}-2026-11-10"])
        st = self.state()
        self.assertEqual(list(st["editions"]), [f"{SID}-2026-11-10"])
        e = st["editions"][f"{SID}-2026-11-10"]
        self.assertEqual(set(e["langs"]), {"en", "pt"})
        self.assertTrue(e["complete"])
        self.assertEqual(e["published"], "2026-11-10T05:00:00+00:00")
        self.assertEqual(len(e["langs"]["en"]["events"]), 2)
        self.assertEqual(e["langs"]["en"]["events"][0]["room"], "Example Hall 0")
        self.assertIn("https://unfccc.int/example", e["langs"]["en"]["official_links"])
        self.assertEqual(e["langs"]["en"]["focus"], "Synthetic Theme")
        self.assertIn("Presidência e anfitrião", e["tracks"])
        self.assertEqual(e["review"]["status"], "pending")      # roadmap / launch: flagged for an editor
        self.assertIn("roadmap", e["review"]["reasons"])
        out = self.j("emit", "--out", self.tmp / "items.json", "--feed", self.tmp / "nofeed.json")
        it = json.loads((self.tmp / "items.json").read_text())["items"][0]
        self.assertEqual(it["url"], f"{EN}/nov10_x")
        self.assertEqual(it["url_i18n"], {"en": f"{EN}/nov10_x", "pt": f"{PT}/nov10_y"})
        self.assertTrue(it["title_i18n"]["pt"].startswith("Boletim Sintético – 10 de novembro"))
        self.assertEqual(it["date"], "2026-11-10")
        self.assertEqual(out["without_summary"], [it["id"]])
        for banned in ("lead", "events", "review", "_body", "hash"):
            self.assertNotIn(banned, it)                        # never the brief's own text in public output

    def test_2025_edition_document_is_excluded_even_if_fetched(self):
        f = self.put(edition(f"{EN}/nov10_old", "2025-11-10T12:00:00+00:00", modified="2026-11-09T18:00:00+00:00"))
        c = self.j("collect", f, "--out", self.tmp / "out")
        self.assertEqual(c["new"], [])
        self.assertEqual(self.state()["editions"], {})

    def test_year_from_effective_date_not_slug(self):
        f = self.put(edition(f"{EN}/cop30-daily-brief-november-10-2025", "2026-11-10T05:00:00+00:00"))
        c = self.j("collect", f, "--out", self.tmp / "out")
        self.assertEqual(c["new"], [f"{SID}-2026-11-10"])

    def test_revision_updates_same_record_and_respects_editor(self):
        self.j("discover", *self.indexes())
        self.collect_day10()
        summ = self.tmp / "s.json"
        summ.write_text(json.dumps({f"{SID}-2026-11-10": {"summary": "Resumo do monitor.", "summary_i18n": {l: "x" for l in LANGS}}}))
        feed = self.tmp / "feed.json"
        feed.write_text(json.dumps({"schema": 1, "tracks": [], "items": []}))
        self.j("emit", "--summaries", summ, "--out", self.tmp / "i1.json", "--feed", feed)
        self.merge(feed, self.tmp / "i1.json")
        # the source revises the EN edition
        c = self.j("collect", self.put(edition(f"{EN}/nov10_x", "2026-11-10T05:00:00+00:00", headline="Alpha headline revised",
                                                body_extra="An added synthetic paragraph.", n_events=3,
                                                modified="2026-11-10T09:00:00+00:00")), "--out", self.tmp / "out")
        self.assertEqual(c["revised"], [f"{SID}-2026-11-10"])
        e = self.state()["editions"][f"{SID}-2026-11-10"]
        self.assertEqual(e["revision"], 1)
        self.assertEqual(e["revisions"][0]["events"], [2, 3])
        self.assertTrue(e["revisions"][0]["headline_changed"])
        self.assertEqual(e["published"], "2026-11-10T05:00:00+00:00")         # publication and modification kept apart
        self.assertEqual(e["last_modified"], "2026-11-10T09:00:00+00:00")
        self.j("emit", "--out", self.tmp / "i2.json", "--feed", feed)
        self.merge(feed, self.tmp / "i2.json")
        items = json.loads(feed.read_text())["items"]
        self.assertEqual(len(items), 1)
        self.assertIn("revised", items[0]["title"])
        self.assertEqual(items[0]["revision"], 1)
        self.assertTrue(items[0]["updated_at"])
        # an editor then corrects the published item; a further source revision must not overwrite it
        items[0]["summary"] = "Avaliação do editor."; items[0]["updated_at"] = "2026-11-10T12:00-03:00"
        feed.write_text(json.dumps({"schema": 1, "tracks": [], "items": items}))
        self.j("collect", self.put(edition(f"{EN}/nov10_x", "2026-11-10T05:00:00+00:00", headline="Alpha headline third",
                                           modified="2026-11-10T15:00:00+00:00")), "--out", self.tmp / "out")
        out = self.j("emit", "--out", self.tmp / "i3.json", "--feed", feed)
        self.assertEqual(out["held_for_editor"], [f"{SID}-2026-11-10"])
        self.merge(feed, self.tmp / "i3.json")
        self.assertEqual(json.loads(feed.read_text())["items"][0]["summary"], "Avaliação do editor.")
        self.assertIn("source revised after an editor's change", self.state()["editions"][f"{SID}-2026-11-10"]["review"]["reasons"])

    def merge(self, feed, items):
        r = subprocess.run([sys.executable, "-I", "-c",
                            "import sys,json,pathlib,importlib.util;"
                            f"s=importlib.util.spec_from_file_location('m', {str(REPO / 'tools' / 'merge_feed.py')!r});"
                            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                            "f=json.loads(pathlib.Path(sys.argv[1]).read_text());"
                            "out=m.merge(f,[json.loads(pathlib.Path(sys.argv[2]).read_text())],log=lambda *a:None);"
                            "pathlib.Path(sys.argv[1]).write_text(json.dumps(out))", str(feed), str(items)],
                           capture_output=True, text=True, timeout=60)
        if r.returncode:
            self.fail(r.stderr)

    def test_missing_date_or_malformed(self):
        no_date = edition(f"{EN}/nov11_x", None)
        thin = edition(f"{EN}/nov12_x", "2026-11-12T05:00:00+00:00", n_events=0)
        thin["blocks"] = {"b0": slate("Short.")}; thin["blocks_layout"] = {"items": ["b0"]}
        c = self.j("collect", self.put(no_date), self.put(thin), self.put_raw("<html><body>oops</body></html>"), "--out", self.tmp / "out")
        self.assertEqual(c["new"], [])
        probs = " ".join(p["problem"] for p in c["problems"])
        self.assertIn("no effective date", probs)
        self.assertIn("malformed: body", probs)
        self.assertIn("not an API JSON document", probs)
        self.assertEqual(self.state()["editions"], {})
        # a listing row without a date is not guessed: the edition itself is fetched to read its date
        en = search(EN, [(f"{EN}/nodate", "Synthetic Presidency Brief", None, None)])
        d = self.j("discover", self.put(en), self.put(search(PT, [(f"{PT}/x", "B", "2026-11-10T05:00:00+00:00", "2026-11-10T01:00:00+00:00")])))
        self.assertTrue(any(f["url"].endswith("/nodate") for f in d["fetch"]))

    def test_api_unavailable_or_loading_is_not_empty(self):
        self.j("discover", *self.indexes())
        before = self.state()["listing"]
        d = self.j("discover", self.put_raw("<div id='main'>Loading...</div>"),
                   self.put({"@id": PT + "/@search?x", "items": [], "items_total": 0}))
        self.assertEqual(d["outcome"], "error")
        self.assertEqual(d["series_editions"], [])
        notes = json.dumps(d["per_lang"])
        self.assertIn("placeholder", notes)
        self.assertIn("not treated as 'no editions'", notes)
        st = self.state()
        self.assertEqual(st["listing"], before)                 # the last good listing is kept
        self.assertEqual(st["discovery"]["last_outcome"], "error")
        self.assertTrue(st["discovery"]["last_success"])

    def test_no_duplicates_after_repeated_runs(self):
        feed = self.tmp / "feed.json"
        feed.write_text(json.dumps({"schema": 1, "tracks": [], "items": [
            {"id": "other", "institution": "UNFCCC", "title": "Other", "date": "2026-11-10", "url": "https://unfccc.int/o"}]}))
        for i in range(3):
            d = self.j("discover", *self.indexes())
            if d["fetch"]:
                self.collect_day10()
            self.j("emit", "--out", self.tmp / f"i{i}.json", "--feed", feed)
            self.merge(feed, self.tmp / f"i{i}.json")
        ids = [x["id"] for x in json.loads(feed.read_text())["items"]]
        self.assertEqual(sorted(ids), sorted({f"{SID}-2026-11-10", "other"}))
        self.assertEqual(self.j("discover", *self.indexes())["fetch"], [])   # nothing new: nothing re-fetched
        self.assertEqual(len(self.state()["editions"]), 1)

    def test_url_change_does_not_duplicate(self):
        feed = self.tmp / "feed.json"
        base = {"id": f"{SID}-2026-11-10", "institution": "Presidência da COP30", "title": "A", "date": "2026-11-10",
                "first_seen": "2026-11-10T03:00-03:00"}
        feed.write_text(json.dumps({"schema": 1, "tracks": [], "items": [dict(base, url=f"{EN}/old-slug")]}))
        (self.tmp / "n.json").write_text(json.dumps({"items": [dict(base, url=f"{EN}/new-slug", updated_at="2026-11-10T05:00-03:00")]}))
        self.merge(feed, self.tmp / "n.json")
        items = json.loads(feed.read_text())["items"]
        self.assertEqual([x["url"] for x in items], [f"{EN}/new-slug"])

    def test_hourly_sync_unaffected(self):
        # due only every ~3 h; the web agent's view never lists the source; feed validation accepts the item
        self.assertTrue(self.j("plan", "--now", "2026-11-10T06:00:00+00:00")["due"])
        self.j("discover", *self.indexes(), "--now", "2026-11-10T06:00:00+00:00")
        self.assertFalse(self.j("plan", "--now", "2026-11-10T07:00:00+00:00")["due"])
        self.assertEqual(self.j("plan", "--now", "2026-11-10T07:00:00+00:00")["fetch"], [])
        self.assertTrue(self.j("plan", "--now", "2026-11-10T09:00:00+00:00")["due"])
        self.tool("register", "--by", "Test", ok=True)
        out = self.tmp / "views"
        self.tool("export", out, script="sources.py")
        web = json.loads((out / "web.json").read_text())
        self.assertNotIn(SID, [s["id"] for s in web["sites"]])
        reg = json.loads((self.tmp / "private" / "sources" / "registry.json").read_text())
        s = next(x for x in reg["sources"] if x["id"] == SID)
        self.assertEqual((s["priority"], s["category"], s["collection"]["cadence"], s["languages"]), ("A", "presidency", "every_3h", ["en", "pt"]))
        self.assertEqual(s["series"]["parent_indexes"], {"en": EN, "pt": PT})
        self.collect_day10()
        reg = json.loads((self.tmp / "private" / "sources" / "registry.json").read_text())
        s = next(x for x in reg["sources"] if x["id"] == SID)
        self.assertTrue(s["series"]["last_discovery_success"] and s["series"]["last_collection_success"])
        self.assertEqual(s["series"]["editions"][0]["urls"]["pt"], f"{PT}/nov10_y")
        self.assertEqual(s["health"]["last_outcome"], "success")
        self.j("emit", "--out", self.tmp / "i.json", "--feed", self.tmp / "nofeed.json")
        feed = {"schema": 1, "tracks": ["Presidência e anfitrião", "Eletrificação", "TAFF e fósseis", "Agenda de Ação", "Finanças"],
                "items": json.loads((self.tmp / "i.json").read_text())["items"]}
        (self.tmp / "f.json").write_text(json.dumps(feed))
        r = subprocess.run([sys.executable, "-I", str(REPO / "tools" / "validate_feed.py"), str(self.tmp / "f.json")],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = subprocess.run([sys.executable, "-I", str(REPO / "tools" / "briefing.py"), "--feed", str(self.tmp / "f.json"),
                            "--out", str(self.tmp / "b.json"), "--now", "2026-11-10T12:00:00+03:00", "--no-registry"],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
