"""Schema compatibility and fail-closed regression fixtures; no live requests."""
import copy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dacs_wire import c, Fake, empty, row, STAMP

FIXTURES = Path(__file__).parent / 'fixtures'

class Schema18Tests(unittest.TestCase):
    def test_mixed_snapshot17_detail18(self):
        f = Fake()
        f.snapshot = json.loads((FIXTURES / 'dacs-snapshot17.json').read_text())
        f.delta = json.loads((FIXTURES / 'dacs-delta.json').read_text())
        f.details['10000325'] = json.loads((FIXTURES / 'dacs-detail18.json').read_text())
        state, payload = c.run(f, empty(), STAMP, hash_files=False)
        self.assertEqual(set(state['documents']), {'10000325', '10000328'})
        doc = state['documents']['10000325']
        self.assertEqual(doc['document_code'], 'FCCC/SB/2026/L.9')
        self.assertEqual(doc['status'], 'unknown')
        self.assertEqual(len(doc['attachments']), 6)
        self.assertEqual(payload['changes'], [])
        self.assertNotIn('nextDocumentId', doc)
        self.assertNotIn('conclusionLabel', json.dumps(doc))

    def test_schema18_same_projection_as17(self):
        detail = json.loads((FIXTURES / 'dacs-detail18.json').read_text())
        equivalent = copy.deepcopy(detail)
        equivalent['schemaVersion'] = 17
        for key in ['nextDocumentId', 'prevDocumentId']:
            equivalent.pop(key, None)
        for agenda in equivalent['agendaItems']:
            for key in ['conclusions', 'conclusionLabel']:
                agenda.pop(key, None)
        self.assertEqual(c.normalize_wire(detail), c.normalize_wire(equivalent))

    def test_snapshot18_and_mixed_row_versions(self):
        f = Fake(); f.snapshot['documentMetadataSchemaVersion'] = 18
        other = row(10000330); other['schemaVersion'] = 18
        f.snapshot['documentMetadata'].append(other)
        state, _ = c.run(f, empty(), STAMP)
        self.assertEqual(len(state['documents']), 2)

    def test_unknown_and_wrong_type_versions_rejected(self):
        for version in [19, 16, None, '18', 18.0, True]:
            with self.subTest(version=version):
                f = Fake(); f.snapshot['documentMetadataSchemaVersion'] = version
                with self.assertRaisesRegex(ValueError, 'snapshot schema'):
                    c.run(f, empty(), STAMP)
                r = row(); r['schemaVersion'] = version
                with self.assertRaisesRegex(ValueError, 'metadata schema'):
                    c.normalize_wire(r)

    def test_future_detail_leaves_state_unchanged(self):
        f = Fake(); state, _ = c.run(f, empty(), STAMP)
        saved = copy.deepcopy(state)
        f.delta['documents'] = [{'id':10000330}]
        f.details['10000330'] = dict(row(10000330), schemaVersion=19)
        with self.assertRaisesRegex(ValueError, 'metadata schema'):
            c.run(f, state, STAMP)
        self.assertEqual(state, saved)

    def test_malformed18_attachments_rejected(self):
        cases = [[], {'en': 'bad'}, {'en': {'filename':'../bad.pdf'}}, {'en': {'filename':None}}]
        for attachments in cases:
            with self.subTest(attachments=attachments):
                with self.assertRaises(ValueError):
                    c.normalize_wire(dict(row(), schemaVersion=18, attachments=attachments))

    def test_schema18_does_not_bypass_coverage_or_detail_id(self):
        f = Fake(); f.snapshot['documentMetadataSchemaVersion'] = 18
        f.delta['changedAfter'] = STAMP
        with self.assertRaisesRegex(ValueError, 'coverage gap'):
            c.run(f, empty(), STAMP)
        f = Fake(); f.delta['documents'] = [{'id':10000330}]
        f.details['10000330'] = dict(row(), schemaVersion=18)
        with self.assertRaisesRegex(ValueError, 'detail id mismatch'):
            c.run(f, empty(), STAMP)

    def test_schema18_revision_and_repeat_no_duplicate_events(self):
        f = Fake(); state, _ = c.run(f, empty(), STAMP)
        detail = dict(row(), schemaVersion=18, changed=STAMP)
        f.delta['documents'] = [{'id':10000328}]; f.details['10000328'] = detail
        f.pdf = b'%PDF-1.7 changed'
        state, payload = c.run(f, state, STAMP)
        self.assertEqual([x['change'] for x in payload['changes']], ['revised'])
        state, repeated = c.run(f, state, '2026-11-16T12:10:00Z')
        self.assertEqual(payload['changes'], repeated['changes'])

    def test_cli_failed_check_retains_public_and_checkpoint(self):
        f = Fake(); state, _ = c.run(f, empty(), STAMP)
        f.delta['documents'] = [{'id':10000330}]
        f.details['10000330'] = dict(row(10000330), schemaVersion=19)
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory)/'private.json'; out = Path(directory)/'public.json'
            checkpoint.write_text(json.dumps(state)); before = checkpoint.read_bytes()
            with patch.object(c, 'Transport', return_value=f), patch.object(sys, 'argv', ['collector','--state',str(checkpoint),'--out',str(out)]), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(c.main(), 1)
            self.assertEqual(checkpoint.read_bytes(), before)
            payload = json.loads(out.read_text())
            self.assertTrue(payload['degraded'])
            self.assertEqual(payload['last_success'], state['last_success'])
            self.assertEqual([r['id'] for r in payload['documents']], ['10000328'])

    def test_unknown_irrelevant_snapshot_and_detail_fail_closed(self):
        for location in ['snapshot', 'detail']:
            f = Fake(); state, _ = c.run(f, empty(), STAMP); saved = copy.deepcopy(state)
            bad = dict(row(10000330), schemaVersion=19, session={'title':'COP 1'}, agendaItems=[])
            if location == 'snapshot':
                f.snapshot['documentMetadata'].append(bad)
            else:
                f.delta['documents'] = [{'id':10000330}]; f.details['10000330'] = bad
            with self.subTest(location=location), self.assertRaisesRegex(ValueError, 'metadata schema'):
                c.run(f, state, STAMP)
            self.assertEqual(state, saved)

    def test_withdrawal_accepts_only_explicit_boolean_or_timestamp(self):
        for value, expected in [(None,False),(False,False),(True,True),(STAMP,True)]:
            self.assertEqual(c.normalize_wire(dict(row(), unpublished=value))['withdrawn'], expected)
        for value in ['false','true','',0,1,[],{},'2026-11-16']:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'unpublished'):
                c.normalize_wire(dict(row(), unpublished=value))
            f = Fake(); state, _ = c.run(f, empty(), STAMP); saved = copy.deepcopy(state)
            f.delta['documents'] = [{'id':10000328, 'unpublished':value}]
            with self.assertRaisesRegex(ValueError, 'unpublished'):
                c.run(f, state, STAMP)
            self.assertEqual(state, saved)

    def test_malformed_projected_timestamps_rejected_before_filtering(self):
        for key in ['changed','publicationDate']:
            for value in ['', 'bad', '2026-11-16', 123, True, {}]:
                with self.subTest(key=key,value=value), self.assertRaisesRegex(ValueError,key):
                    c.normalize_wire(dict(row(), **{key:value}))
                f = Fake(); bad = dict(row(10000330), session={'title':'COP 1'}, agendaItems=[], **{key:value})
                f.snapshot['documentMetadata'].append(bad)
                with self.assertRaisesRegex(ValueError,key): c.run(f,empty(),STAMP)
        f=Fake(); f.delta['documents']=[{'id':10000328,'unpublished':STAMP,'changed':'bad'}]
        with self.assertRaisesRegex(ValueError,'changed'): c.run(f,empty(),STAMP)

    def test_optional_missing_dates_and_null_withdrawal_remain_supported(self):
        r=row(); r.pop('publicationDate'); r.pop('changed'); r['unpublished']=None
        doc=c.normalize_wire(r)
        self.assertIsNone(doc['published_at']); self.assertIsNone(doc['modified_at'])
        self.assertFalse(doc['withdrawn'])

if __name__ == '__main__': unittest.main()
