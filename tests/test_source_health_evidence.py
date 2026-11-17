"""Private health calculations use synthetic evidence; no actual registry loaded."""
import copy
import datetime as dt
import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location('source_health_tool', pathlib.Path(__file__).resolve().parents[1] / 'tools/sources.py')
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)
NOW = dt.datetime(2026, 11, 17, 12, tzinfo=dt.timezone.utc)


def source(history):
    return {'id': 'synthetic', 'status': 'active', 'platform': 'web', 'priority': 'A',
            'provenance': {'origin': 'test'}, 'collection': {'cadence': 'daily', 'agent': 'web'},
            'health': {'history': history, 'last_collected': '2099-01-01T00:00:00Z'}}


def run(hour, outcome='success_empty', **kw):
    return {'at': f'2026-11-17T{hour:02d}:00:00Z', 'agent': 'web', 'outcome': outcome, **kw}


class SourceHealthEvidence(unittest.TestCase):
    def row(self, history):
        return sources.coverage({'sources': [source(history)]}, NOW)['sources'][0]

    def test_late_old_report_cannot_replace_newer_failure(self):
        history = [run(11, 'blocked'), run(9, 'success', new_items=2)]
        for ordered in (history, list(reversed(history))):
            r = self.row(ordered)
            self.assertEqual(r['state'], 'blocked')
            self.assertEqual(r['last_success'], run(9)['at'])
            self.assertEqual(r['new_items_24h'], 2)
            d = sources.due_view(source(ordered), NOW)
            self.assertEqual(d['last_outcome'], 'blocked')
            self.assertEqual(d['last_attempt'], run(11)['at'])

    def test_future_invalid_unknown_reports_do_not_create_health(self):
        history = [run(13), dict(run(10), at='not-a-date'), run(11, 'mystery')]
        r = self.row(history)
        self.assertEqual(r['state'], 'unknown')
        self.assertEqual(r['invalid_runs'], 3)
        self.assertEqual(r['checks_24h'], 0)
        self.assertFalse(r['covered_24h'])
        d = sources.due_view(source(history), NOW)
        self.assertTrue(d['due'])
        self.assertIsNone(d['last_attempt'])
        self.assertIsNone(d['last_success'])

    def test_timezone_chronology_not_lexical_order(self):
        history = [dict(run(11, 'blocked'), at='2026-11-17T11:00:00+01:00'), run(9)]
        self.assertEqual(self.row(history)['state'], 'blocked')
        self.assertEqual(sources.due_view(source(history), NOW)['last_outcome'], 'blocked')

    def test_same_time_failure_wins_either_order(self):
        history = [run(10, 'blocked'), run(10)]
        for ordered in (history, list(reversed(history))):
            self.assertEqual(self.row(ordered)['state'], 'blocked')

    def test_probe_and_skipped_never_count_as_collection(self):
        history = [dict(run(11), agent='probe'), run(11, 'skipped')]
        r = self.row(history)
        self.assertEqual(r['state'], 'never')
        self.assertEqual(r['invalid_runs'], 0)
        self.assertTrue(sources.due_view(source(history), NOW)['due'])

    def test_invalid_counts_diagnosed_not_crash_or_inflate(self):
        history = [run(8, new_items=-1), run(9, new_items='several'), run(10, new_items=True), run(11, new_items=3)]
        original = copy.deepcopy(history)
        r = self.row(history)
        self.assertEqual(r['new_items_24h'], 3)
        self.assertEqual(r['invalid_item_counts'], 3)
        self.assertEqual(history, original)
        cv = sources.coverage({'sources': [source(history)]}, NOW)
        self.assertEqual(cv['totals']['all']['invalid_item_counts'], 3)

    def test_stale_success_remains_overdue(self):
        history = [dict(run(10), at='2026-11-14T10:00:00Z'), run(13)]
        r = self.row(history)
        self.assertEqual(r['state'], 'overdue')
        self.assertFalse(r['covered_24h'])
        self.assertTrue(sources.due_view(source(history), NOW)['due'])
