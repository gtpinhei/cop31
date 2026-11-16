import copy
import sys
import unittest
import tempfile
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import collect_negotiating_texts as c

STAMP='2026-11-16T12:00:00Z'
def row(id=10000328):
    return {'id':id,'schemaVersion':17,'title':'Climate finance work programme','session':{'title':'CMA 8'},'symbol':'DT.CMA8.i11g.1','documentType':{'title':'draft text'},'version':1.0,'changed':'2026-11-16T05:01:00Z','publicationDate':'2026-11-16T05:00:00Z','attachments':{'en':{'filename':'CFWP_DT_cma8.pdf'}},'agendaItems':[{'sessionId':'CMA 8','itemNo':'11(g)'}]}
def empty():
    return {'schema':1,'initialized':False,'documents':{},'events':[],'last_success':None}
class Fake:
    def __init__(self):
        self.snapshot={'dumpedAt':'2026-11-15T23:00:00Z','documentMetadataSchemaVersion':17,'documentMetadata':[row()]}
        self.delta={'changedAfter':'2026-11-15T22:00:00Z','documents':[]}
        self.details={}
        self.pdf=b'%PDF-1.7 test'
    def json(self,url):
        if url.endswith('/metadata/all'):return copy.deepcopy(self.snapshot)
        if url.endswith('/metadata/changed/today'):return copy.deepcopy(self.delta)
        return copy.deepcopy(self.details[url.split('/')[-2]])
    def get(self,url):return self.pdf
class WireTests(unittest.TestCase):
    def test_actual_schema_bootstrap_no_finance_alert(self):
        s,p=c.run(Fake(),empty(),STAMP)
        self.assertEqual(p['changes'],[])
        self.assertEqual(p['documents'][0]['document_code'],'DT.CMA8.i11g.1')
        self.assertEqual(p['documents'][0]['published_at'],'2026-11-16T05:00:00Z')
        self.assertFalse(p['degraded'])
    def test_delta_fetch_detail_new_gef(self):
        f=Fake();s,p=c.run(f,empty(),STAMP)
        f.delta['documents']=[{'id':10000330,'changed':STAMP}]
        f.details['10000330']=row(10000330)
        s,p=c.run(f,s,STAMP)
        self.assertEqual([x['document_id'] for x in p['changes']],['10000330'])
    def test_explicit_withdrawal(self):
        f=Fake();s,p=c.run(f,empty(),STAMP)
        f.delta['documents']=[{'id':10000328,'unpublished':STAMP,'changed':STAMP}]
        s,p=c.run(f,s,STAMP)
        self.assertEqual(p['changes'][0]['change'],'withdrawn')
    def test_gap_is_degraded_not_healthy(self):
        f=Fake();f.delta['changedAfter']='2026-11-16T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'coverage gap'):c.run(f,empty(),STAMP)
    def test_bad_schema(self):
        f=Fake();f.snapshot['documentMetadataSchemaVersion']=18
        with self.assertRaises(ValueError):c.run(f,empty(),STAMP)
    def test_snapshot_absence_not_withdrawal(self):
        f=Fake();s,p=c.run(f,empty(),STAMP)
        f.snapshot['documentMetadata']=[row(10000330)]
        f.details['10000328']=row()
        s,p=c.run(f,s,STAMP)
        self.assertFalse(s['documents']['10000328']['withdrawn'])
    def test_changed_pdf_revision(self):
        f=Fake();s,p=c.run(f,empty(),STAMP)
        f.snapshot['documentMetadata'][0]['changed']=STAMP
        f.pdf=b'%PDF-1.7 revised'
        s,p=c.run(f,s,STAMP)
        self.assertEqual(p['changes'][0]['change'],'revised')
    def test_public_status_not_inferred_adopted(self):
        r=row();r['documentType']['title']='Decision'
        self.assertEqual(c.normalize_wire(r)['status'],'unknown')
    def test_unsafe_attachment(self):
        r=row();r['attachments']['en']['filename']='../../x.pdf'
        with self.assertRaises(ValueError):c.normalize_wire(r)
    def test_source_failure_leaves_input_state_unchanged(self):
        f=Fake();s,p=c.run(f,empty(),STAMP);saved=copy.deepcopy(s)
        f.delta['documents']=[{'id':10000330}]
        with self.assertRaises(KeyError):c.run(f,s,STAMP)
        self.assertEqual(s,saved)
    def test_missing_timestamp_not_spcreated(self):
        r=row();del r['publicationDate'];r['spCreated']=STAMP
        self.assertIsNone(c.normalize_wire(r)['published_at'])
    def test_verification_mode_is_explicit(self):
        _,p=c.run(Fake(),empty(),STAMP,hash_files=False)
        self.assertEqual(p['verification_mode'],'metadata-only')
        state,p=c.run(Fake(),empty(),STAMP)
        self.assertEqual(p['verification_mode'],'pdf-hashes')
        retained=c.public_payload(state,p,STAMP,True)
        self.assertEqual(retained['verification_mode'],'pdf-hashes')
    def test_public_restore_no_bootstrap_events(self):
        f=Fake();_,p=c.run(f,empty(),STAMP)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'public.json';path.write_text(json.dumps(p))
            state=c.restore_public(path)
            _,again=c.run(f,state,STAMP)
            self.assertEqual(again['changes'],[])
            self.assertNotIn('source_url',state['documents']['10000328'])
    def test_repeated_withdrawal_after_reinstatement_is_distinct(self):
        f=Fake();state,_=c.run(f,empty(),STAMP)
        f.delta['documents']=[{'id':10000328,'unpublished':STAMP,'changed':STAMP}]
        state,_=c.run(f,state,STAMP)
        f.delta['documents']=[]
        state,_=c.run(f,state,'2026-11-16T12:10:00Z')
        f.delta['documents']=[{'id':10000328,'unpublished':'2026-11-16T12:20:00Z','changed':'2026-11-16T12:20:00Z'}]
        state,p=c.run(f,state,'2026-11-16T12:20:00Z')
        self.assertEqual(3,len(p['changes']))
        self.assertEqual(3,len({x['event_id'] for x in p['changes']}))
    def test_recent_change_survives_next_poll(self):
        f=Fake();state,p=c.run(f,empty(),STAMP)
        f.snapshot['documentMetadata'].append(row(10000330))
        state,p=c.run(f,state,STAMP)
        state,p2=c.run(f,state,'2026-11-16T12:10:00Z')
        self.assertEqual(p['changes'],p2['changes'])
        state,p3=c.run(f,state,'2026-11-17T12:10:00Z')
        self.assertEqual([],p3['changes'])
    def test_public_restore_rejects_duplicates(self):
        _,p=c.run(Fake(),empty(),STAMP);p['documents']*=2
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'public.json';path.write_text(json.dumps(p))
            with self.assertRaises(ValueError):c.restore_public(path)
    def test_unknown_withdrawal_not_fabricated(self):
        f=Fake();f.delta['documents']=[{'id':999,'unpublished':STAMP}]
        s,p=c.run(f,empty(),STAMP)
        self.assertNotIn('999',s['documents'])
if __name__=='__main__':unittest.main()
