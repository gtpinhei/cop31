import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import dacs_texts as d

H1='a'*64
H2='b'*64

def doc(id='10000328', sha=H1, **kwargs):
    x=dict(id=id,title='Climate finance work programme',body='CMA',session='CMA-8',agenda='11(g)',
           document_code='DT.CMA8.i11g.1', status='draft', published_at='2026-11-16T05:00:00Z',
           modified_at='2026-11-16T05:00:00Z', attachments=[dict(url=f'https://docs.unfccc.int/documents/{id}/files/en/test.pdf', sha256=sha, language='en')])
    return {**x,**kwargs}

def snap(*items,when='2026-11-16T08:25:00Z'):
    return dict(snapshot_complete=True,checked_at=when,documents=list(items))

def empty():
    return dict(schema=1,initialized=False,documents={},events=[],last_success=None)

class TestDacs(unittest.TestCase):
    def setUp(self):
        self.x=doc()
        self.s,self.o=d.apply(snap(self.x),empty())
    def updated(self,**kwargs):
        x=copy.deepcopy(self.x);x.update(kwargs)
        return d.apply(snap(x,when='2026-11-16T08:35:00Z'),copy.deepcopy(self.s))[1]
    def test_first_run_no_retroactive_event(self):
        self.assertEqual(self.o['changes'],[])
    def test_known_release_idempotent(self):
        self.assertEqual(self.updated()['changes'],[])
    def test_new_document_event(self):
        x=doc('10000329');o=d.apply(snap(self.x,x,when='2026-11-16T08:35:00Z'),self.s)[1]
        self.assertEqual([(c['document_id'],c['change']) for c in o['changes']],[('10000329','new')])
    def test_metadata_only_not_text(self):
        self.assertEqual(self.updated(modified_at='2026-11-16T08:30:00Z')['changes'],[])
    def test_actual_file_change(self):
        self.assertEqual(self.updated(attachments=[dict(url=self.x['attachments'][0]['url'],sha256=H2,language='en')])['changes'][0]['change'],'revised')
    def test_unhashed_attachment_not_fake_revision(self):
        self.assertEqual(self.updated(attachments=[dict(url='https://docs.unfccc.int/documents/10000328/files/en/v2.pdf',sha256=None)])['changes'],[])
    def test_withdrawal(self):
        self.assertEqual(self.updated(withdrawn=True)['changes'][0]['change'],'withdrawn')
    def test_absence_is_not_withdrawal(self):
        y=doc('10000001');s,_=d.apply(snap(self.x,y,when='2026-11-16T08:26:00Z'),self.s)
        _,o=d.apply(snap(self.x,when='2026-11-16T08:35:00Z'),s)
        self.assertIn('10000001',[r['id'] for r in o['documents']]);self.assertEqual(o['changes'],[])
    def test_reinstatement(self):
        y=dict(self.x, withdrawn=True);s,_=d.apply(snap(y,when='2026-11-16T08:30:00Z'),self.s)
        _,o=d.apply(snap(self.x,when='2026-11-16T08:35:00Z'),s)
        self.assertEqual(o['changes'][0]['change'],'reinstated')
    def test_new_translation_not_text_revision(self):
        fr=dict(url='https://docs.unfccc.int/documents/10000328/files/fr/test.pdf',sha256=H2,language='fr')
        self.assertEqual(self.updated(attachments=self.x['attachments']+[fr])['changes'],[])
    def test_translations_same_id(self):
        fr=doc(language='fr',attachments=[dict(url='https://docs.unfccc.int/documents/10000328/files/fr/test.pdf',sha256=H2,language='fr')])
        s,o=d.apply(snap(self.x,fr),empty());self.assertEqual(len(o['documents']),1);self.assertEqual(o['changes'],[])
    def test_partial_snapshot_rejected(self):
        with self.assertRaises(ValueError):d.apply({'checked_at':'2026-11-16T09:00:00Z','documents':[self.x]},self.s)
    def test_empty_snapshot_rejected(self):
        with self.assertRaises(ValueError):d.apply(snap(),self.s)
    def test_stale_snapshot_rejected(self):
        with self.assertRaises(ValueError):d.apply(snap(self.x,when='2026-11-16T08:20:00Z'),self.s)
    def test_unofficial_pdf_rejected(self):
        with self.assertRaises(ValueError):d.normalize(doc(attachments=[dict(url='https://example.org/file.pdf',sha256=H1)]))
    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):d.normalize(doc(status='agreed'))
    def test_priority(self):
        self.assertEqual(d.normalize(self.x)['topic'],'Finance')

if __name__=='__main__':unittest.main()
