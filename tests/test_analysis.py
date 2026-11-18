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

class AnalysisABGate(unittest.TestCase):
    write = AnalysisGate.write
    check = AnalysisGate.check
    def setUp(self):
        AnalysisGate.setUp(self)
        self.document['id'] = 'synthetic-350'
        self.row = {'article': 'synthetic-brief', 'format': 'text-explained', 'document': self.document,
                    'comparison': {'status': 'not_assessed'},
                    'summary': {'changes': ['SYNTHETIC example only'], 'significance': 'SYNTHETIC interpretation', 'watch': 'SYNTHETIC next step', 'language': 'en'},
                    'lifecycle': {'status': 'current', 'checked_at': '2026-11-18T00:00:00Z'}}

    # Inherited tests target the older daily format, so this subclass only adds focused AB tests.
    def test_ab_summary_required_identity(self):
        self.assertEqual(self.check(), [])
        self.document.pop('id')
        self.assertTrue(self.check())

    def test_ab_summary_limits(self):
        for bad in [None, {}, {'changes': []}, dict(self.row['summary'], language='xx'), dict(self.row['summary'], changes=['x']*6), dict(self.row['summary'], watch='')]:
            row = dict(self.row, summary=bad)
            self.assertTrue(self.check([row]), repr(bad))

    def test_ab_status_and_replacement(self):
        self.row['lifecycle']['status'] = 'withdrawn'
        self.assertEqual(self.check(), [])
        self.row['lifecycle']['status'] = 'replaced'
        self.assertTrue(self.check())
        self.row['lifecycle']['replacement'] = dict(self.document, id='synthetic-353', url='https://unfccc.int/replacement.pdf')
        self.assertEqual(self.check(), [])
        self.row['lifecycle']['replacement']['sha256'] = 'not-pdf-bytes'
        self.assertTrue(self.check())

class AIReleaseGate(unittest.TestCase):
    write = AnalysisGate.write
    check = AnalysisGate.check
    def setUp(self):
        AnalysisGate.setUp(self)
        self.document['id']='synthetic-after'
        self.baseline=dict(self.document, id='synthetic-before', url='https://unfccc.int/before.pdf',sha256='b'*64)
        self.row={'article':'synthetic-brief','format':'text-explained','document':self.document,'comparison':{'status':'compared','baseline':self.baseline}}
        self.article['language']='en'
        self.article['entries']=[]
        self.article['i18n_pending']=['pt','es','fr','ru','zh','ar']
        self.article.pop('approved_by');self.article.pop('approved_at')
        self.article['sources'].append({'url':self.baseline['url'],'verified':True})
        self.article['contributor']={'display':'named','name':'COP31 Monitor AI','role':'analyst'}
        self.article['ai_provenance']={'schema':1,'mode':'public-unfccc-diff','generated_at':'2026-11-18T00:00:00Z','model':'SYNTHETIC TEST MODEL','prompt_version':'synthetic-v1','authorization':'owner-public-unfccc-analysis-2026-11-18','source_documents':[self.baseline,self.document],'qa':{'status':'passed','checked_at':'2026-11-18T00:01:00Z','checks':['official_sources_only','pdf_bytes_verified','version_identity_verified','evidence_links_checked','confidential_inputs_excluded']}}
        self.write()
    def test_ai_article_requires_index_home(self):
        self.assertTrue(self.check([]))
        self.assertTrue(gate.problems(self.root))

    def test_explicit_ai_not_human_approval(self):
        self.assertEqual(self.check(),[])
        self.article['approved_by']='SYNTHETIC fake editor';self.write()
        self.assertTrue(self.check())
    def test_fail_closed_qa_scope_and_sources(self):
        original=copy.deepcopy(self.article)
        for key in ['qa','authorization','source_documents','model','generated_at']:
            self.article=copy.deepcopy(original);self.article['ai_provenance'].pop(key);self.write()
            self.assertTrue(self.check(),key)
        self.article=copy.deepcopy(original);self.article['sources'].append({'url':'https://example.org/intelligence','verified':True});self.write()
        self.assertTrue(self.check())
    def test_only_bound_comparison_versions(self):
        self.row['comparison']['baseline']=dict(self.baseline,sha256='c'*64)
        self.assertTrue(self.check())
        self.row['comparison']={'status':'not_assessed'}
        self.assertTrue(self.check())
