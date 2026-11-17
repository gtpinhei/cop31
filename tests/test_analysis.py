"""Synthetic tests only: no private readouts, people or release approvals."""
import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('analysis_gate', ROOT / 'tools/validate_analysis.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class AnalysisGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        (self.root / 'data/articles').mkdir(parents=True)
        self.article = {
            'schema': 1, 'id': 'synthetic-brief', 'entries': ['synthetic-card'],
            'status': 'published', 'title': 'SYNTHETIC test',
            'blocks': [{'basis': 'analysis', 'md': 'SYNTHETIC test only.'}],
            'sources': [{'url': 'https://unfccc.int/example.pdf', 'verified': True}],
            'contributor': {'display': 'named', 'name': 'SYNTHETIC author', 'role': 'observer'},
            'approved_by': 'SYNTHETIC editor', 'approved_at': '2026-11-17T00:00:00Z',
            'i18n_pending': ['en', 'es', 'fr', 'ru', 'zh', 'ar']}
        self.row = {'article': 'synthetic-brief', 'format': 'daily-diplomacy-brief', 'reporting_date': '2026-11-16'}
        self.document = {'url': 'https://unfccc.int/example.pdf', 'version_label': 'SYNTHETIC v1', 'reviewed_at': '2026-11-17T00:00:00Z', 'sha256': 'a'*64}
        self.write()

    def write(self):
        (self.root / 'data/articles/synthetic-brief.json').write_text(json.dumps(self.article))

    def check(self, rows=None):
        return gate.validate({'schema': 1, 'entries': [self.row] if rows is None else rows}, self.root)

    def test_empty_and_approved_index(self):
        self.assertEqual(self.check([]), [])
        self.assertEqual(self.check(), [])

    def test_drafts_rejected(self):
        self.article['status'] = 'draft'; self.write()
        self.assertTrue(self.check())

    def test_approval_attribution_source_required(self):
        original = copy.deepcopy(self.article)
        for key in ['approved_by', 'approved_at', 'contributor', 'sources']:
            self.article = copy.deepcopy(original); self.article.pop(key); self.write()
            self.assertTrue(self.check(), key)

    def test_missing_and_path_traversal(self):
        for value in ['missing-article', '../../private', None, []]:
            self.row['article'] = value
            self.assertTrue(self.check())

    def test_private_fields_and_duplicate(self):
        self.row['draft_body'] = 'SYNTHETIC'
        self.assertTrue(self.check())
        self.row.pop('draft_body')
        self.assertTrue(self.check([self.row, self.row]))

    def test_version_required(self):
        self.row = {'article': 'synthetic-brief', 'format': 'text-explained', 'document': self.document, 'comparison': {'status': 'not_assessed'}}
        self.assertEqual(self.check(), [])
        for key in ['version_label', 'reviewed_at', 'sha256', 'url']:
            d = self.document.pop(key)
            self.assertTrue(self.check(), key)
            self.document[key] = d
        self.row['comparison'] = {'status': 'compared'}
        self.assertTrue(self.check())
        self.row['comparison']['baseline'] = copy.deepcopy(self.document)
        self.assertEqual(self.check(), [])

    def test_supersession_and_bad_shape(self):
        self.row['superseded_by'] = 'synthetic-brief'
        self.assertTrue(self.check())
        self.row['superseded_by'] = 'not-published'
        self.assertTrue(self.check())
        for bad in [None, [], {'schema': 1, 'entries': 'bad'}, {'schema': 1, 'entries': [], 'drafts': []}]:
            self.assertTrue(gate.validate(bad, self.root))

    def test_official_urls_only(self):
        for url in ['https://localhost/test', 'https://127.0.0.1/a', 'https://evil.test/a', 'https://unfccc.int:8080/a', 'https://user:pass@unfccc.int/a']:
            doc = dict(self.document, url=url)
            self.assertTrue(gate.document_errors(doc), url)

    def test_baseline_must_be_verified_source(self):
        self.row = {'article': 'synthetic-brief', 'format': 'text-explained', 'document': self.document, 'comparison': {'status': 'compared', 'baseline': dict(self.document, url='https://unfccc.int/other.pdf')}}
        self.assertTrue(self.check())

    def test_private_marker_in_metadata_rejected(self):
        self.row = {'article': 'synthetic-brief', 'format': 'text-explained', 'document': dict(self.document, version_label='cop31-private/intake/secret'), 'comparison': {'status': 'not_assessed'}}
        self.assertTrue(self.check())
