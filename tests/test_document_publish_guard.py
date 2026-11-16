import copy,datetime as dt,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import document_publish_guard as g

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.base={'schema':1,'last_attempt':'2026-11-16T20:00:00Z','last_success':'2026-11-16T20:00:00Z','checked_at':'2026-11-16T20:00:00Z','degraded':False,'verification_mode':'pdf-hashes','sources':sorted(g.SOURCES),'documents':[{'id':'1','title':'Public draft','status':'draft','withdrawn':False,'attachments':[],'source_url':'https://docs.unfccc.int/documents/1/metadata'},{'id':'2','title':'Other draft','status':'draft','withdrawn':False,'attachments':[],'source_url':'https://docs.unfccc.int/documents/2/metadata'}],'changes':[{'event_id':'a'*24,'document_id':'1','change':'new','at':'2026-11-16T20:00:00Z'}]}
        self.new=copy.deepcopy(self.base);self.new.update(last_attempt='2026-11-16T23:00:00Z',last_success='2026-11-16T23:00:00Z',checked_at='2026-11-16T23:00:00Z')
        self.now=dt.datetime(2026,11,16,23,1,tzinfo=dt.timezone.utc)
    def run_guard(self):
        old=json.dumps(self.base).encode();return g.prepare(old,g.blob_sha(old),json.dumps(self.new).encode(),self.now)
    def test_healthy(self): self.assertFalse(self.run_guard()['degraded'])
    def test_blob_lease(self):
        with self.assertRaisesRegex(ValueError,'baseline bytes'):g.prepare(b'{}','wrong',b'{}',self.now)
    def test_degraded_preserves_catalog(self):
        self.new=copy.deepcopy(self.base);self.new.update(last_attempt='2026-11-16T23:00:00Z',degraded=True)
        self.assertTrue(self.run_guard()['degraded'])
        self.new['documents'][0]['title']='wrong'
        with self.assertRaisesRegex(ValueError,'preserve'):self.run_guard()
    def test_no_disappearance(self):
        self.new['documents'].pop()
        with self.assertRaisesRegex(ValueError,'disappearance'):self.run_guard()
    def test_explicit_withdrawal_retains_record(self):
        self.new['documents'][0].update(withdrawn=True,status='withdrawn')
        self.new['changes'].append({'event_id':'b'*24,'document_id':'1','change':'withdrawn','at':'2026-11-16T23:00:00Z'})
        self.run_guard()
    def test_private_fields(self):
        self.new['private_checkpoint']={}
        with self.assertRaises(ValueError):self.run_guard()
    def test_unknown_doc_fields(self):
        self.new['documents'][0]['raw_metadata']={}
        with self.assertRaises(ValueError):self.run_guard()
    def test_stale_candidate(self):
        self.now+=dt.timedelta(minutes=10)
        with self.assertRaisesRegex(ValueError,'stale'):self.run_guard()
    def test_clock_ahead(self):
        self.now-=dt.timedelta(minutes=2)
        with self.assertRaisesRegex(ValueError,'clock'):self.run_guard()
    def test_success_regression(self):
        self.new.update(last_success='2026-11-15T00:00:00Z',checked_at='2026-11-15T00:00:00Z')
        with self.assertRaisesRegex(ValueError,'regression'):self.run_guard()
    def test_nonofficial_attachment(self):
        self.new['documents'][0]['attachments']=[{'url':'https://example.org/a.pdf'}]
        with self.assertRaises(ValueError):self.run_guard()
    def test_event_reference(self):
        self.new['changes'][0]['document_id']='9999999'
        with self.assertRaises(ValueError):self.run_guard()

    def test_hash_mode_needs_hashes(self):
        self.new['documents'][0]['attachments']=[{'url':'https://docs.unfccc.int/a.pdf','sha256':None}]
        with self.assertRaisesRegex(ValueError,'requires hashes'):self.run_guard()
    def test_record_timestamp_regression(self):
        self.base['documents'][0]['modified_at']='2026-11-16T18:00:00Z'
        self.new['documents'][0]['modified_at']='2026-11-16T17:00:00Z'
        with self.assertRaisesRegex(ValueError,'document timestamp'):self.run_guard()
    def test_metadata_version_regression(self):
        self.base['documents'][0]['metadata_version']='2.0';self.new['documents'][0]['metadata_version']='1.0'
        with self.assertRaisesRegex(ValueError,'version regression'):self.run_guard()
    def test_degraded_no_new_event(self):
        self.new=copy.deepcopy(self.base);self.new.update(last_attempt='2026-11-16T23:00:00Z',degraded=True)
        self.new['changes'].append({'event_id':'b'*24,'document_id':'1','change':'revised','at':'2026-11-16T23:00:00Z'})
        with self.assertRaisesRegex(ValueError,'invent events'):self.run_guard()
    def test_withdrawal_requires_current_event(self):
        self.new['documents'][0].update(withdrawn=True,status='withdrawn')
        with self.assertRaisesRegex(ValueError,'current event'):self.run_guard()
