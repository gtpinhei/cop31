"""Today aggregator (tools/briefing.py): grouping, attribution, link rules, freshness, empty states, safety.
Synthetic data only.

  python3 -I -m unittest discover -s tests -k Briefing
"""
import json, pathlib, subprocess, sys, tempfile, unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import briefing as B  # noqa: E402

NOW = B.now_tz("2099-11-10T10:00:00+03:00")


def item(i, **kw):
    it = {"id": f"x-{i}", "institution": "Carbon Brief", "type": "análise", "title": f"[TESTE] Story {i}",
          "date": "2099-11-10", "url": f"https://www.example.org/2099/11/story-{i}", "summary": f"[TESTE] Resumo {i}. Toca a trilha de Finanças.",
          "summary_i18n": {"en": f"[TEST] Summary {i} about adaptation finance pledges", "ar": f"[اختبار] ملخص {i}"},
          "tracks": ["Finanças"], "first_seen": "2099-11-10T08:00:00-03:00", "lang": "en"}
    it.update(kw)
    return it


def feed(items, web="2099-11-10T03:00:00-03:00", social="2099-11-10T03:30:00-03:00"):
    return {"schema": 1, "round": {"timestamp": web}, "social_round": {"timestamp": social}, "items": items}


class Briefing(unittest.TestCase):
    def build(self, items, **kw):
        b = B.build(feed(items, **kw), NOW, registry=False)
        B.validate(b)
        return b

    def all_leads(self, b):
        return [s["lead"] for v in b["sections"].values() for s in v]

    def test_same_event_grouped_into_one_story(self):
        en = "[TEST] Loss and damage fund board approves first disbursement window replenishment Barbados implementation modalities"
        items = [item(1, institution="Carbon Brief", summary_i18n={"en": en}),
                 item(2, institution="Climate Home News", type="notícia", url="https://www.example.org/chn/l-and-d", summary_i18n={"en": en + " countries"}),
                 item(3, institution="IISD / ENB", type="boletim", url="https://www.example.org/enb/day2", summary_i18n={"en": en + " observers"}),
                 item(4, title="[TESTE] Unrelated electrification pledge", summary_i18n={"en": "[TEST] Electrification pledge signatories grid storage"},
                      tracks=["Eletrificação"], url="https://www.example.org/other")]
        b = self.build(items)
        leads = self.all_leads(b)
        self.assertEqual(len(leads), 2)                                   # three reports of one event = one story
        big = next(s for v in b["sections"].values() for s in v if s["related"])
        self.assertEqual(len(big["related"]), 2)
        self.assertEqual(set(big["publishers"]), {"Carbon Brief", "Climate Home News", "IISD / ENB"})

    def test_attribution_original_headline_url_and_publisher_date(self):
        b = self.build([item(1, authors="A. Writer", date="2099-11-09")])
        lead = self.all_leads(b)[0]
        self.assertEqual(lead["title"], "[TESTE] Story 1")
        self.assertEqual(lead["url"], "https://www.example.org/2099/11/story-1")
        self.assertEqual((lead["publisher"], lead["author"], lead["published"]), ("Carbon Brief", "A. Writer", "2099-11-09"))
        self.assertEqual(lead["collected_at"], "2099-11-10T08:00:00-03:00")           # discovery time kept apart
        self.assertNotIn("Toca a trilha", lead["description"])                       # monitor's track note dropped
        self.assertEqual(lead["description_i18n_method"], "machine")
        self.assertIn("ar", lead["description_i18n"])

    def test_links_must_be_direct_and_https(self):
        items = [item(1, url="http://insecure.example.org/a"), item(2, url="https://www.example.org/"),
                 item(3, kind="post", platform="x", account="@acc", institution="UNFCCC", url="https://x.com/acc", text="[TESTE] post"),
                 item(4, kind="post", platform="bluesky", account="unfccc.int", institution="IISD / ENB", url="https://bsky.app/profile/enb.iisd.org/post/3abc", text="[TESTE] ENB daily report out", title=None)]
        b = self.build(items)
        urls = [l["url"] for l in self.all_leads(b)]
        self.assertEqual(urls, ["https://bsky.app/profile/enb.iisd.org/post/3abc"])   # profile links and http dropped
        self.assertTrue(self.all_leads(b)[0]["title"].startswith("unfccc.int: [TESTE]"))

    def test_window_uses_publisher_date_not_discovery(self):
        b = self.build([item(1, date="2099-11-01", first_seen="2099-11-10T09:00:00-03:00"), item(2)])
        self.assertEqual([l["id"] for l in self.all_leads(b)], ["x-2"])

    def test_top_stories_diverse_and_at_most_eight(self):
        items = [item(i, institution="Carbon Brief" if i < 10 else f"Pub {i}", summary_i18n={"en": f"[TEST] distinct topic {i} " + "word%d " % i * 3})
                 for i in range(14)]
        b = self.build(items)
        top = b["sections"]["essential"]
        self.assertLessEqual(len(top), 8)
        self.assertLess(sum(1 for s in top if s["lead"]["publisher"] == "Carbon Brief"), len(top))
        ids = [s["lead"]["id"] for v in b["sections"].values() for s in v]
        self.assertEqual(len(ids), len(set(ids)))                                    # nothing shown twice

    def test_stale_collection_is_flagged_not_reported_as_quiet_day(self):
        b = self.build([], web="2099-11-09T01:00:00-03:00", social="2099-11-09T02:00:00-03:00")
        self.assertTrue(b["collection"]["stale"])
        b = self.build([])
        self.assertFalse(b["collection"]["stale"])
        self.assertEqual(b["coverage"]["stories"], 0)

    def test_empty_sections_stay_empty(self):
        b = self.build([item(1)])
        self.assertEqual(sum(len(v) for v in b["sections"].values()), 1)
        self.assertEqual(b["sections"]["civil"], [])

    def test_previous_edition_kept_when_build_fails_and_today_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            out = d / "briefing.json"; good = {"schema": 1, "sections": {}, "edition": "keep"}
            out.write_text(json.dumps(good))
            (d / "feed.json").write_text("{not json")
            today = REPO / "data" / "today.json"; before = today.read_bytes()
            r = subprocess.run([sys.executable, "-I", str(REPO / "tools/briefing.py"), "--feed", str(d / "feed.json"), "--out", str(out), "--no-registry"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertEqual(json.loads(out.read_text())["edition"], "keep")
            self.assertEqual(today.read_bytes(), before)
            (d / "feed.json").write_text(json.dumps(feed([item(1)])))
            r = subprocess.run([sys.executable, "-I", str(REPO / "tools/briefing.py"), "--feed", str(d / "feed.json"), "--out", str(out), "--no-registry",
                                "--now", "2099-11-10T10:00:00+03:00"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(out.read_text())["coverage"]["stories"], 1)

    def test_novelty_previously_featured_ranks_lower(self):
        a, b_ = item(1), item(2, institution="Climate Home News", type="notícia", summary_i18n={"en": "[TEST] other topic entirely glaciers"})
        prev = {"featured_history": {"2099-11-09": ["x-1"]}}
        b = B.build(feed([a, b_]), NOW, prev, registry=False)
        self.assertEqual(b["sections"]["essential"][0]["lead"]["id"], "x-2")

    def test_shipped_briefing_validates(self):
        p = REPO / "data" / "briefing.json"
        if p.exists():
            self.assertTrue(B.validate(json.loads(p.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    unittest.main()
