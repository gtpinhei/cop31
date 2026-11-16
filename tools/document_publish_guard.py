#!/usr/bin/env python3
"""Offline, fail-closed prepublication guard. Never writes GitHub or schedules work.

A caller must fetch the baseline and expected blob before collection and supply
that same blob to GitHub update_file. A newer blob requires a fresh collection,
not substitution of the new SHA. See docs/workflows/document-automation.md.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

TOP = {'schema','documents','changes','checked_at','last_success','last_attempt','degraded','sources','history_count','error','verification_mode'}
FIELDS = {'id','title','body','session','agenda','document_code','published_at','modified_at','metadata_version','status','withdrawn','attachments','topic','source_url'}
SOURCES = {'https://docs.unfccc.int/documents/metadata/all','https://docs.unfccc.int/documents/metadata/changed/today'}

def require(ok, message):
    if not ok: raise ValueError(message)

def timestamp(value):
    require(isinstance(value,str), 'timestamp missing')
    try: value=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError: raise ValueError('invalid timestamp')
    require(value.tzinfo is not None, 'timezone missing')
    return value.astimezone(dt.timezone.utc)

def blob_sha(content):
    return hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()

def official(url):
    try:
        u=urlsplit(url)
        return u.scheme=='https' and u.hostname in {'docs.unfccc.int','unfccc.int'} and not u.username and not u.password and u.port in (None,443)
    except (ValueError,TypeError): return False

def validate(data):
    require(isinstance(data,dict) and not set(data)-TOP and data.get('schema')==1, 'invalid public shape')
    require(data.get('verification_mode') in {'pdf-hashes','metadata-only'}, 'invalid verification mode')
    require(isinstance(data.get('degraded'),bool), 'missing health status')
    require('error' not in data or data['error']=='Official document check failed; last successful data retained.', 'unsanitized error')
    require(isinstance(data.get('sources'),list) and set(data['sources'])==SOURCES, 'unexpected sources')
    attempt=timestamp(data.get('last_attempt'));success=timestamp(data.get('last_success'))
    require(timestamp(data.get('checked_at'))==success and success<=attempt, 'inconsistent check timestamps')
    require(isinstance(data.get('documents'),list) and data['documents'], 'empty catalog')
    docs={}
    for row in data['documents']:
        require(isinstance(row,dict) and not set(row)-FIELDS, 'private/unknown document fields')
        key=str(row.get('id'))
        require(re.fullmatch(r'[1-9][0-9]{0,11}',key) and key not in docs, 'bad/duplicate id')
        require(isinstance(row.get('title'),str) and row['title'].strip(), 'missing title')
        require(row.get('status') in {'draft','informal','proposed','adopted','unknown','withdrawn'} and isinstance(row.get('withdrawn'),bool), 'bad status')
        require(row['withdrawn']==(row['status']=='withdrawn'), 'inconsistent withdrawal')
        require(official(row.get('source_url')), 'bad source URL')
        require(isinstance(row.get('attachments'),list), 'bad attachments')
        for a in row['attachments']:
            require(isinstance(a,dict) and not set(a)-{'url','language','sha256'} and official(a.get('url')), 'bad attachment')
            require(a.get('sha256') is None or re.fullmatch(r'[a-f0-9]{64}',str(a['sha256'])), 'bad PDF hash')
            if data['verification_mode']=='pdf-hashes' and not data['degraded'] and not row['withdrawn']:
                require(a.get('sha256') is not None, 'healthy hash mode requires hashes')
        docs[key]=row
    require(isinstance(data.get('changes'),list) and len(data['changes'])<=500, 'bad change history')
    seen=set()
    for event in data['changes']:
        require(isinstance(event,dict) and set(event)=={'event_id','document_id','change','at'}, 'unknown event fields')
        require(re.fullmatch(r'[a-f0-9]{24}',str(event['event_id'])) and event['event_id'] not in seen, 'bad/duplicate event')
        require(str(event['document_id']) in docs and event['change'] in {'new','revised','withdrawn','reinstated'}, 'bad event reference')
        require(timestamp(event['at'])<=attempt, 'future event')
        seen.add(event['event_id'])
    return docs

def prepare(baseline_bytes, expected_blob, candidate_bytes, now):
    require(blob_sha(baseline_bytes)==expected_blob, 'baseline bytes do not match fetched blob')
    old=json.loads(baseline_bytes);new=json.loads(candidate_bytes)
    old_docs=validate(old);new_docs=validate(new)
    attempt=timestamp(new['last_attempt']);success=timestamp(new['last_success'])
    require(dt.timedelta(0)<=now-attempt<=dt.timedelta(minutes=10), 'candidate stale or clock ahead')
    require(attempt>=timestamp(old['last_attempt']) and success>=timestamp(old['last_success']), 'timestamp regression')
    require(set(old_docs)<=set(new_docs), 'record disappearance is not withdrawal')
    if new['degraded']:
        require(old_docs==new_docs and new['last_success']==old['last_success'], 'failure must preserve last-good catalog')
        require(new['verification_mode']==old['verification_mode'], 'failure cannot change verification mode')
        require(all(e in old['changes'] for e in new['changes']), 'failure cannot invent events')
    else:
        require(success==attempt, 'healthy run must record successful current attempt')
        for key,previous in old_docs.items():
            current=new_docs[key]
            if previous.get('modified_at'):
                require(current.get('modified_at') and timestamp(current['modified_at'])>=timestamp(previous['modified_at']), 'document timestamp regression')
            # Numeric metadata revisions may detect rollback, never political significance.
            ov=str(previous.get('metadata_version',''));nv=str(current.get('metadata_version',''))
            if re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',ov) and re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',nv):
                from decimal import Decimal
                require(Decimal(nv)>=Decimal(ov), 'metadata version regression')
            if previous['withdrawn']!=current['withdrawn']:
                kind='withdrawn' if current['withdrawn'] else 'reinstated'
                require(any(str(e['document_id'])==key and e['change']==kind and timestamp(e['at'])==attempt for e in new['changes']), 'withdrawal transition lacks current event')
    return {'expected_blob':expected_blob,'candidate_blob':blob_sha(candidate_bytes),'candidate_sha256':hashlib.sha256(candidate_bytes).hexdigest(),'last_attempt':new['last_attempt'],'last_success':new['last_success'],'degraded':new['degraded'],'documents':len(new_docs),'changes':len(new['changes'])}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',required=True);p.add_argument('--expected-blob',required=True);p.add_argument('--candidate',required=True)
    a=p.parse_args();receipt=prepare(Path(a.baseline).read_bytes(),a.expected_blob,Path(a.candidate).read_bytes(),dt.datetime.now(dt.timezone.utc))
    print(json.dumps(receipt,sort_keys=True))
if __name__=='__main__':
    try: main()
    except (ValueError,TypeError,KeyError) as exc:
        print('Refusing publication: '+str(exc),file=sys.stderr);sys.exit(1)
