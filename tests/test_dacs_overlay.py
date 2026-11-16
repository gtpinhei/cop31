import sys,gzip,json,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dacs_overlay as o

class Overlay(unittest.TestCase):
    def test_gzip(self):
        obj={'documents':[{'id':'1'}]}
        self.assertEqual(o.decode_payload(gzip.compress(json.dumps(obj).encode())),obj)
    def test_plain(self):
        self.assertEqual(o.decode_payload('{"documents":[]}'),{'documents':[]})
    def test_reject_unrecognized_wire_schema(self):
        with self.assertRaises(ValueError):o.decode_payload('[]')
    def test_overlay_wins_over_lagging_full_snapshot(self):
        full={'snapshot_complete':True,'documents':[{'id':'1','title':'v1'},{'id':'2','title':'keep'}]}
        delta={'delta_complete':True,'documents':[{'id':'1','title':'v2'},{'id':'3','withdrawn':True}]}
        got=o.combine(full,[delta],'2026-11-16T09:00:00Z')
        self.assertEqual({x['id']:x for x in got['documents']},{'1':{'id':'1','title':'v2'},'2':{'id':'2','title':'keep'},'3':{'id':'3','withdrawn':True}})
    def test_missing_delta_is_failure_not_all_clear(self):
        with self.assertRaises(ValueError):o.combine({'snapshot_complete':True,'documents':[{'id':'1'}]},[{'documents':[]}],'2026-11-16T09:00:00Z')
    def test_rollover(self):
        self.assertEqual(o.rollover_days('2026-11-16T00:05:00Z','2026-11-15T23:55:00Z'),['2026-11-15','2026-11-16'])
    def test_old_checkpoint(self):
        with self.assertRaises(ValueError):o.rollover_days('2026-11-16T00:05:00Z','2026-11-01T00:05:00Z')
if __name__=='__main__': unittest.main()
