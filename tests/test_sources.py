"""Source registry: parsing, dedupe, identity and activation rules, health ingestion, views.
Synthetic data only; runs against a throwaway private store.

  python3 -I -m unittest discover -s tests -k Sources
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, unittest

REPO = pathlib.Path(__file__).resolve().parent.parent


class Sources(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="cop31-src-"))
        self.env = dict(os.environ, COP31_PRIVATE=str(self.tmp / "private"))
        self.social = self.tmp / "social.json"
        self.social.write_text(json.dumps({"accounts": [
            {"institution": "UNFCCC", "platform": "x", "handle": "UNFCCC", "priority": "A", "verified": "página"},
            {"institution": "Example Lab", "platform": "bluesky", "handle": "examplelab.bsky.social", "priority": "B", "verified": "não"},
            {"institution": "Gone Org", "platform": "x", "handle": "gone", "priority": "A", "verified": "não", "inactive": True,
             "note": "does not exist"}],
            "manual_only": [{"institution": "UNFCCC", "platform": "whatsapp", "channels": {"EN": "https://whatsapp.com/channel/x"}}]}))
        self.web = self.tmp / "web.json"
        self.web.write_text(json.dumps([
            {"institution": "UNFCCC newsroom", "urls": ["https://unfccc.int/news", "https://unfccc.int/cop31"], "rss": None, "language": "en"},
            {"institution": "UNFCCC / Stiell", "urls": ["https://unfccc.int/news/", "https://unfccc.int/cop31/daily"], "rss": None, "language": "en"},
            {"institution": "Example Think Tank", "urls": ["https://example.org/news"], "rss": None, "language": "en"}]))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, *args, ok=True):
        r = subprocess.run([sys.executable, "-I", str(REPO / "tools" / "sources.py"), *map(str, args)], capture_output=True,
                           text=True, env=self.env, timeout=60)
        if ok and r.returncode != 0:
            self.fail(f"{args}: {r.stdout}\n{r.stderr}")
        if not ok and r.returncode == 0:
            self.fail(f"{args} should fail: {r.stdout}")
        return r.stdout + r.stderr

    def reg(self):
        return json.loads((self.tmp / "private" / "sources" / "registry.json").read_text())

    def seed(self):
        self.run_tool("import-legacy", self.social, self.web, "--by", "T")

    def test_legacy_import_merges_duplicates_and_keeps_states(self):
        self.seed()
        src = {s["id"]: s for s in self.reg()["sources"]}
        web = [s for s in src.values() if s["platform"] == "web" and "unfccc.int" in s["urls"][0]]
        self.assertEqual(len(web), 1)                                       # trailing slash duplicate merged
        self.assertIn("https://unfccc.int/cop31/daily", web[0]["urls"])      # extra URL kept
        self.assertEqual(src["x-gone"]["status"], "paused")
        self.assertEqual(src["x-unfccc"]["identity"]["status"], "checked")
        self.assertEqual(src["bsky-examplelab-bsky-social"]["identity"]["status"], "unverified")
        wa = next(s for s in src.values() if s["platform"] == "whatsapp")
        self.assertEqual(wa["status"], "rejected")
        self.assertIn("not_collectable", wa["decision"]["reason"])
        self.assertIn("OK", self.run_tool("validate"))

    def batch(self, text):
        b = self.tmp / "batch.txt"
        b.write_text(text)
        out = self.run_tool("plan", b, "--by", "Editor")
        p = self.tmp / "plan.json"
        p.write_text(out)
        return p, json.loads(out)["candidates"]

    def test_plan_parses_dedupes_and_rejects(self):
        self.seed()
        _, c = self.batch("\n".join([
            "https://x.com/UNFCCC",                                   # duplicate of registered
            "https://bsky.app/profile/wmo.int | category=multilateral | priority=A",
            "bsky:wmo.int",                                           # duplicate within batch
            "https://www.linkedin.com/company/e3g",                   # not collectable
            "not a url",                                              # no platform
            "https://example.net/feed/ | category=media | themes=Finanças",
            "https://example.com | priority=Z",
            "# comment"]))
        d = {x["line"]: x for x in c}
        self.assertTrue(d[1]["reason"].startswith("duplicate of x-unfccc"))
        self.assertEqual(d[2]["decision"], "probe")
        self.assertIn("duplicate of line 2", d[3]["reason"])
        self.assertIn("not_collectable", d[4]["reason"])
        self.assertIn("invalid", d[5]["reason"])
        self.assertEqual(d[6]["source"]["platform"], "rss")
        self.assertIn("priority", d[7]["reason"])
        self.assertNotIn(8, d)

    def test_activation_rules(self):
        self.seed()
        p, c = self.batch("\n".join([
            "https://bsky.app/profile/wmo.int | category=multilateral | priority=A",           # official + domain handle
            "x:cop31fanpage | category=presidency",                                           # official but unverified
            "https://bsky.app/profile/someresearch.org | category=research",                   # verified but not official
            "x:doesnotexist | category=government",                                           # unavailable
            "https://blocked.example.org/news | category=government",                         # blocked
            "x:notprobed | category=government"]))
        probes = self.tmp / "probes.json"
        probes.write_text(json.dumps({
            "1": {"outcome": "success", "metadata": {"latest_item_date": "2026-11-09", "display_name": "WMO"}},
            "2": {"outcome": "success", "metadata": {}},
            "3": {"outcome": "success_empty", "metadata": {}},
            "4": {"outcome": "unavailable", "note": "This account doesn't exist"},
            "5": {"outcome": "blocked", "note": "client_error"}}))
        res = {r["line"]: r for r in json.loads(self.run_tool("apply", p, probes, "--by", "Editor"))}
        self.assertEqual(res[1]["result"], "active")
        self.assertEqual(res[2]["result"], "awaiting_activation"); self.assertIn("identity unverified", res[2]["reason"])
        self.assertEqual(res[3]["result"], "awaiting_activation"); self.assertIn("needs editor approval", res[3]["reason"])
        self.assertEqual(res[4]["result"], "rejected"); self.assertIn("unavailable", res[4]["reason"])
        self.assertEqual(res[5]["result"], "awaiting_activation"); self.assertIn("probe blocked", res[5]["reason"])
        self.assertEqual(res[6]["result"], "awaiting_activation"); self.assertIn("not probed", res[6]["reason"])
        wmo = next(s for s in self.reg()["sources"] if s.get("handle") == "wmo.int")
        self.assertEqual(wmo["health"]["last_outcome"], "success")
        self.assertEqual(wmo["identity"]["status"], "checked")
        # editor can approve one that is awaiting; rejecting needs a reason
        rid = res[3]["id"]
        self.run_tool("approve", rid, "--by", "Editor")
        self.run_tool("reject", res[2]["id"], "--by", "Editor", ok=False)
        self.run_tool("reject", res[2]["id"], "--by", "Editor", "--reason", "fan page")
        self.assertIn("OK", self.run_tool("validate"))

    def test_ingest_health_counts_blocked_separately_and_proposals(self):
        self.seed()
        st = self.tmp / "status.json"
        st.write_text(json.dumps({"agent": "social", "run_at": "2026-11-09T10:00:00-03:00", "results": [
            {"source_id": "x-unfccc", "outcome": "success", "new_items": 2, "latest_item_date": "2026-11-09"},
            {"source_id": "bsky-examplelab-bsky-social", "outcome": "blocked", "note": "login wall"},
            {"source_id": "nope", "outcome": "success"}],
            "proposals": [{"target": "https://bsky.app/profile/newvoice.bsky.social", "institution": "New Voice",
                           "relevance": "reposted by UNFCCC about COP31 finance", "evidence_url": "https://bsky.app/x"}]}))
        out = self.run_tool("ingest", st)
        self.assertIn("ingested 2 results, 1 new proposals, 1 unknown", out)
        self.run_tool("ingest", st)                                       # idempotent
        src = {s["id"]: s for s in self.reg()["sources"]}
        self.assertEqual(len(src["x-unfccc"]["health"]["history"]), 1)
        self.assertEqual(src["bsky-examplelab-bsky-social"]["health"]["last_outcome"], "blocked")
        self.assertEqual(src["bsky-newvoice-bsky-social"]["status"], "proposed")
        rep = self.run_tool("report")
        self.assertIn("bloqueadas: 1", rep)
        self.assertIn("com sucesso: 1", rep)
        self.assertIn("nunca tentadas", rep)
        self.assertIn("bsky-newvoice-bsky-social", rep)

    def test_views_only_active_and_never_edit_hint(self):
        self.seed()
        out = self.tmp / "views"
        self.run_tool("export", out)
        social = json.loads((out / "social.json").read_text())
        self.assertNotIn("gone", [a["handle"] for a in social["accounts"]])
        self.assertTrue(all("id" in a and "cadence" in a and "rights" in a for a in social["accounts"]))
        web = json.loads((out / "web.json").read_text())
        self.assertEqual(len(web["sites"]), 2)
        self.assertIn("do not edit", web["generated_from"])
        self.assertTrue((out / "report.md").exists())

    def test_unavailable_three_times_pauses(self):
        self.seed()
        for i in range(3):
            st = self.tmp / f"s{i}.json"
            st.write_text(json.dumps({"agent": "social", "run_at": f"2026-11-09T1{i}:00:00-03:00",
                                      "results": [{"source_id": "x-unfccc", "outcome": "unavailable", "note": "gone"}]}))
            self.run_tool("ingest", st)
        s = next(x for x in self.reg()["sources"] if x["id"] == "x-unfccc")
        self.assertEqual(s["status"], "paused")


if __name__ == "__main__":
    unittest.main()
