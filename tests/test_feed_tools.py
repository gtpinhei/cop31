"""Regression tests for the feed tools: python3 -I -m unittest discover -s tests (from the repo root)."""
import copy, importlib.util, json, pathlib, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


V = load("validate_feed")
M = load("merge_feed")

PUB = {"id": "e3g-2026-11-06-x", "institution": "E3G", "type": "briefing", "title": "T", "date": "2026-11-06",
       "url": "https://e3g.org/x", "summary": "Resumo.", "tracks": ["Finanças"], "quotes": [],
       "first_seen": "2026-11-06T12:00:00-03:00", "lang": "en"}
POST = {"id": "x-unfccc-20261107-a", "kind": "post", "platform": "x", "account": "@UNFCCC", "institution": "UNFCCC",
        "verified": True, "date": "2026-11-07", "time": "10:00", "text": "Hello", "summary": "Olá.",
        "url": "https://x.com/UNFCCC", "tracks": [], "first_seen": "2026-11-07T10:42:00-03:00", "lang": "en"}


class Validate(unittest.TestCase):
    def test_live_feed_is_valid(self):
        fatal, per = V.check_feed(json.loads((ROOT / "data" / "feed.json").read_text(encoding="utf-8")))
        self.assertEqual(fatal, [])
        self.assertEqual({k: e for k, (e, w) in per.items() if e}, {})

    def test_today_file_is_valid(self):
        p = ROOT / "data" / "today.json"
        fatal, per = V.check_today(json.loads(p.read_text(encoding="utf-8")))
        self.assertEqual(fatal, [])
        self.assertEqual({k: e for k, (e, w) in per.items() if e}, {})

    def test_rejects_bad_items(self):
        bad = dict(PUB, url="http://insecure", date="7 nov")
        e, _ = V.check_item(bad)
        self.assertTrue(any("https" in x for x in e) and any("date" in x for x in e))
        e, _ = V.check_item(dict(POST, url=""))
        self.assertIn("post without url", e)

    def test_link_kind(self):
        self.assertEqual(V.link_kind("https://x.com/UNFCCC"), "profile")
        self.assertEqual(V.link_kind("https://x.com/UNFCCC/status/123"), "post")
        self.assertEqual(V.link_kind("https://bsky.app/profile/enb.iisd.org/post/3mzopsjeufk2o"), "post")
        self.assertEqual(V.link_kind("https://www.instagram.com/p/DQx1/"), "post")
        self.assertEqual(V.link_kind("https://www.instagram.com/turkiyecop31/"), "profile")
        self.assertEqual(V.link_kind("https://www.youtube.com/watch?v=abc"), "post")

    def entry(self, **kw):
        en = {"id": "a", "status": "published", "headline": "H", "what_happened": "W", "what_changed": "C",
              "why_it_matters": "Y", "watch_next": "Z", "verification": "confirmado", "classification": "anúncio",
              "sources": [{"url": "https://unfccc.int/x", "verified": True}], "approved_by": "Gustavo",
              "approved_at": "2026-11-09T10:00:00+03:00",
              "i18n": {l: {f: f + l for f in V.TEXT_FIELDS} | {"method": "human"} for l in V.LANGS}}
        en.update(kw); return en

    def test_today_complete_entry_is_valid(self):
        self.assertEqual(V.check_entry(self.entry())[0], [])

    def test_today_publish_needs_human_approval_and_verified_source(self):
        e, _ = V.check_entry(self.entry(approved_by=None, sources=[{"url": "https://unfccc.int/x", "verified": False}]))
        self.assertTrue(any("approved_by" in x for x in e))
        self.assertTrue(any("verified: true" in x for x in e))

    def test_today_public_file_rejects_drafts_and_markers(self):
        e, _ = V.check_entry(self.entry(status="draft"))
        self.assertTrue(any("not allowed in data/today.json" in x for x in e))
        e, _ = V.check_entry(self.entry(why_it_matters="Talvez. [revisar]"))
        self.assertTrue(any("review markers" in x for x in e))
        self.assertEqual(V.check_entry(self.entry(status="draft", approved_by=None), public=False)[0], [])

    def test_today_requires_all_six_translations_of_substantive_fields(self):
        en = self.entry(); del en["i18n"]["ru"]; en["i18n"]["zh"].pop("why_it_matters")
        e, _ = V.check_entry(en)
        self.assertTrue(any(x.startswith("translation ru missing") for x in e))
        self.assertTrue(any(x.startswith("translation zh missing why_it_matters") for x in e))
        en["i18n_pending"] = ["ru", "zh"]
        self.assertEqual(V.check_entry(en)[0], [])
        e, _ = V.check_entry(self.entry(i18n={"en": {"headline": "H", "method": "guess"}}))
        self.assertTrue(any("method" in x for x in e))

    def test_shipped_today_has_no_drafts(self):
        doc = json.loads((ROOT / "data" / "today.json").read_text(encoding="utf-8"))
        self.assertTrue(all(en.get("status") == "published" for en in doc["entries"]))


class Merge(unittest.TestCase):
    def feed(self, *items):
        return {"schema": 1, "tracks": ["Finanças"], "items": [copy.deepcopy(i) for i in items]}

    def test_stale_copy_cannot_overwrite_newer_correction(self):
        fixed = dict(PUB, summary="Corrigido.", updated_at="2026-11-07T09:00:00-03:00")
        out = M.merge(self.feed(fixed), [self.feed(PUB)], log=lambda *_: None)
        self.assertEqual(out["items"][0]["summary"], "Corrigido.")

    def test_newer_version_wins_and_keeps_missing_fields(self):
        old = dict(PUB, summary_i18n={"en": "Summary."})
        new = dict(PUB, summary="Novo.", updated_at="2026-11-08T09:00:00-03:00")
        out = M.merge(self.feed(old), [self.feed(new)], log=lambda *_: None)
        self.assertEqual(out["items"][0]["summary"], "Novo.")
        self.assertEqual(out["items"][0]["summary_i18n"], {"en": "Summary."})

    def test_same_version_only_fills_gaps(self):
        a = dict(PUB, summary="A.")
        b = dict(PUB, summary="B.", summary_i18n={"en": "B."})
        out = M.merge(self.feed(a), [self.feed(b)], log=lambda *_: None)
        self.assertEqual(out["items"][0]["summary"], "A.")
        self.assertEqual(out["items"][0]["summary_i18n"], {"en": "B."})

    def test_invalid_incoming_items_are_dropped(self):
        msgs = []
        out = M.merge(self.feed(PUB), [self.feed(dict(POST, id="bad", url="javascript:alert(1)"))], log=msgs.append)
        self.assertEqual(len(out["items"]), 1)
        self.assertTrue(msgs and "bad" in msgs[0])

    def test_posts_keyed_by_id_and_rounds_newest_wins(self):
        src = self.feed(POST, dict(POST, id="x-unfccc-20261107-b", text="Other"))
        src["social_round"] = {"timestamp": "2026-11-08T05:45:00-03:00", "label": "new"}
        base = self.feed(); base["social_round"] = {"timestamp": "2026-11-08T06:45:00-03:00", "label": "newer"}
        out = M.merge(base, [src], log=lambda *_: None)
        self.assertEqual(len(out["items"]), 2)
        self.assertEqual(out["social_round"]["label"], "newer")


if __name__ == "__main__":
    unittest.main()
