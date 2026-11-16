#!/usr/bin/env python3
"""DACS schema-17 wire adapter. Private state must remain outside the public tree.
Full dump + explicit changed/today detail overlay, no disappearance withdrawals.
HTTP failures never advance last_success. Bootstrap creates no historical alerts.
"""
import argparse
import copy
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
# Support isolated Python execution while importing only this checked-in directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dacs_texts import apply, atomic, iso, load, official, normalize

BASE = 'https://docs.unfccc.int/documents'
SESSIONS = {'COP 31', 'CMA 8', 'CMP 21', 'SBI 65', 'SBSTA 65'}
MAX_BYTES = 40 * 1024 * 1024

class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not official(newurl) or urlsplit(newurl).port not in (None, 443):
            raise ValueError('nonofficial redirect rejected')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class Transport:
    def __init__(self):
        self.opener = build_opener(SafeRedirect())
    def get(self, url):
        if not official(url) or urlsplit(url).port not in (None, 443):
            raise ValueError('nonofficial request rejected')
        request = Request(url, headers={'User-Agent':'COP31-Monitor/1.0 (public negotiating-text monitor)', 'Accept-Encoding':'gzip'})
        with self.opener.open(request, timeout=25) as response:
            blob = response.read(MAX_BYTES + 1)
        if len(blob) > MAX_BYTES:
            raise ValueError('response too large')
        if blob.startswith(b'\x1f\x8b'):
            # Bounded decompression prevents compressed payload memory exhaustion.
            import io
            with gzip.GzipFile(fileobj=io.BytesIO(blob)) as stream:
                blob = stream.read(MAX_BYTES + 1)
            if len(blob) > MAX_BYTES:
                raise ValueError('expanded response too large')
        return blob
    def json(self, url):
        value = json.loads(self.get(url))
        if not isinstance(value, dict):
            raise ValueError('DACS object expected')
        return value

def did(value):
    if isinstance(value, bool) or not re.fullmatch(r'[1-9][0-9]{0,11}', str(value)):
        raise ValueError('invalid DACS id')
    return str(value)

def title(value):
    return value.get('title', '') if isinstance(value, dict) else ''

def relevant(row):
    return title(row.get('session')) in SESSIONS or any(x.get('sessionId') in SESSIONS for x in row.get('agendaItems', []))

def normalize_wire(row):
    if row.get('schemaVersion') != 17:
        raise ValueError('unsupported DACS metadata schema')
    id_ = did(row.get('id'))
    if not isinstance(row.get('title'), str) or not row['title'].strip():
        raise ValueError('missing title')
    attachments = row.get('attachments', {})
    if not isinstance(attachments, dict):
        raise ValueError('invalid attachment map')
    files = []
    for lang, item in attachments.items():
        if not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]+)?', lang) or not isinstance(item, dict):
            raise ValueError('invalid language attachment')
        filename = item.get('filename')
        if not isinstance(filename, str) or not filename or '/' in filename or '\\' in filename or filename in ('.','..'):
            raise ValueError('invalid filename')
        files.append({'language':lang,'url':f'{BASE}/{id_}/files/{lang}/{quote(filename, safe="")}','sha256':None})
    kind = title(row.get('documentType')).lower()
    status = {'draft text':'draft','informal note':'informal'}.get(kind, 'unknown')
    withdrawn = bool(row.get('unpublished'))
    return {'id':id_, 'title':row['title'], 'body':'; '.join(title(b) for b in row.get('bodies', [])),
            'session':title(row.get('session')), 'agenda':'; '.join(f"{a.get('sessionId','')} {a.get('itemNo','')}".strip() for a in row.get('agendaItems', [])),
            'document_code':row.get('symbol',''), 'published_at':row.get('publicationDate'),
            'modified_at':row.get('changed'), 'metadata_version':str(row.get('version','')),
            'status':'withdrawn' if withdrawn else status, 'withdrawn':withdrawn, 'attachments':files}

def collect(transport, state, stamp, hash_files=True):
    snapshot = transport.json(BASE + '/metadata/all')
    delta = transport.json(BASE + '/metadata/changed/today')
    if snapshot.get('documentMetadataSchemaVersion') != 17 or not isinstance(snapshot.get('documentMetadata'), list):
        raise ValueError('unrecognized snapshot schema')
    dumped = iso(snapshot.get('dumpedAt'))
    since = iso(delta.get('changedAfter'))
    if not dumped or not since or not isinstance(delta.get('documents'), list):
        raise ValueError('missing coverage timestamps')
    if dumped < since:
        raise ValueError('snapshot/delta coverage gap; refusing incomplete reconciliation')
    if dumped > stamp or since > stamp:
        raise ValueError('future source timestamp')
    rows = {}
    for row in snapshot['documentMetadata']:
        if relevant(row):
            key = did(row.get('id'))
            if key in rows:
                raise ValueError('duplicate snapshot id')
            rows[key] = normalize_wire(row)
    for change in delta['documents']:
        key = did(change.get('id'))
        if change.get('unpublished'):
            old = rows.get(key) or state.get('documents', {}).get(key)
            if old:
                rows[key] = dict(old, withdrawn=True, status='withdrawn', modified_at=change.get('changed'))
            # Unknown withdrawn items have no safe title/session; never invent them.
            continue
        detail = transport.json(f'{BASE}/{key}/metadata')
        if did(detail.get('id')) != key:
            raise ValueError('detail id mismatch')
        if relevant(detail):
            rows[key] = normalize_wire(detail)
    if not rows:
        raise ValueError('empty session snapshot')
    # If dump loses a known row, check its current detail rather than treating absence as withdrawal.
    for key, old in state.get('documents', {}).items():
        if key not in rows and not old.get('withdrawn'):
            detail = transport.json(f'{BASE}/{key}/metadata')
            if did(detail.get('id')) != key:
                raise ValueError('detail id mismatch')
            rows[key] = normalize_wire(detail)
    for key, row in rows.items():
        if row.get('withdrawn'):
            continue
        old = state.get('documents', {}).get(key, {})
        previous = {a['url']:a for a in old.get('attachments', [])}
        same_metadata = old.get('modified_at') == iso(row.get('modified_at'))
        for attachment in row['attachments']:
            prior = previous.get(attachment['url'], {})
            if same_metadata and prior.get('sha256'):
                attachment['sha256'] = prior['sha256']
            elif hash_files:
                blob = transport.get(attachment['url'])
                if not blob.startswith(b'%PDF-'):
                    raise ValueError('attachment is not a PDF')
                attachment['sha256'] = hashlib.sha256(blob).hexdigest()
    return {'snapshot_complete':True, 'checked_at':stamp, 'documents':list(rows.values())}

def public_payload(state, payload, stamp, degraded=False):
    payload.update(last_attempt=stamp, degraded=degraded, verification_mode=state.get('verification_mode', 'metadata-only'))
    cutoff = (dt.datetime.fromisoformat(stamp.replace('Z','+00:00')) - dt.timedelta(hours=24)).isoformat().replace('+00:00','Z')
    # Public change history is bounded; private delivered-alert state is never exported.
    payload['changes'] = [copy.deepcopy(e) for e in state.get('events', []) if cutoff <= e['at'] <= stamp][-500:]
    payload['documents'] = copy.deepcopy(payload['documents'])
    for row in payload['documents']:
        row['source_url'] = f"{BASE}/{row['id']}/metadata"
    return payload

def run(transport, state, stamp, hash_files=True):
    candidate = copy.deepcopy(state)
    data = collect(transport, candidate, stamp, hash_files)
    updated, payload = apply(data, candidate)
    updated['verification_mode'] = 'pdf-hashes' if hash_files else 'metadata-only'
    return updated, public_payload(updated, payload, stamp)

def restore_public(path):
    """Recover only published state, never private event history. Fails closed."""
    obj = json.loads(Path(path).read_text(encoding='utf-8'))
    stamp = iso(obj.get('last_success'))
    if obj.get('schema') != 1 or not stamp or not isinstance(obj.get('documents'), list) or not obj['documents']:
        raise ValueError('public payload cannot seed state')
    docs = {}
    for raw in obj['documents']:
        key = did(raw.get('id'))
        if key in docs:
            raise ValueError('duplicate public id')
        docs[key] = normalize(raw)
    events=[]
    for event in obj.get('changes', []):
        if not isinstance(event,dict) or not re.fullmatch(r'[a-f0-9]{24}',str(event.get('event_id',''))) or str(event.get('document_id')) not in docs or event.get('change') not in {'new','revised','withdrawn','reinstated'} or not iso(event.get('at')):
            raise ValueError('invalid public change')
        events.append({k:event[k] for k in ('event_id','document_id','change','at')})
    return {'schema':1,'initialized':True,'documents':docs,'events':events[-500:],'last_success':stamp,'verification_mode':obj.get('verification_mode') if obj.get('verification_mode') in ('metadata-only','pdf-hashes') else 'metadata-only'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', required=True, help='Private checkpoint outside served repository')
    p.add_argument('--out', required=True)
    p.add_argument('--restore-public', help='If private state missing, recover comparison baseline from verified public JSON; historical event ledger is not restored')
    p.add_argument('--metadata-only', action='store_true', help='Do not hash PDFs; revisions remain unverified')
    args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    state_path=Path(args.state).resolve()
    if state_path == root or root in state_path.parents:
        p.error('--state must be outside repository to prevent public checkpoint disclosure')
    stamp=dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z')
    state=load(state_path)
    if not state.get("initialized") and args.restore_public:
        state=restore_public(args.restore_public)
    try:
        updated,payload=run(Transport(),state,stamp,not args.metadata_only)
        # Public payload is derived, not a copy of the private checkpoint.
        atomic(args.out,payload)
        atomic(state_path,updated)
        print(json.dumps({'documents':len(payload['documents']), 'changes':len(payload['changes']), 'last_success':payload['last_success']}))
    except Exception as exc:
        payload={'schema':1,'checked_at':state.get('last_success'),'last_success':state.get('last_success'),
                 'documents':list(copy.deepcopy(state.get('documents',{})).values()), 'changes':[],
                 'sources':[BASE+'/metadata/all',BASE+'/metadata/changed/today'], 'error':'Official document check failed; last successful data retained.'}
        atomic(args.out,public_payload(state,payload,stamp,True))
        print(f'Collection failed: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
