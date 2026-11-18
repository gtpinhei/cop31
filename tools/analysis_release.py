"""Explicit machine-analysis release mode; never masquerades as human clearance.
Structural validation does not replace the producer's evidence checks or independent review.
"""
import datetime as dt
import re
from urllib.parse import urlsplit
AUTHORIZATION = 'owner-public-unfccc-analysis-2026-11-18'
CHECKS = {'official_sources_only', 'pdf_bytes_verified', 'version_identity_verified', 'evidence_links_checked', 'confidential_inputs_excluded'}
def timestamp(v):
    try:
        return isinstance(v,str) and dt.datetime.fromisoformat(v.replace('Z','+00:00')).utcoffset() is not None
    except ValueError:
        return False

def official(v):
    try:
        u=urlsplit(v)
        return u.scheme=='https' and u.hostname in {'unfccc.int','www.unfccc.int','docs.unfccc.int'} and not u.username and not u.password and u.port in (None,443)
    except (TypeError,ValueError):
        return False

def ai_errors(a):
    p=a.get('ai_provenance')
    if not isinstance(p,dict) or set(p)!={'schema','mode','generated_at','model','prompt_version','authorization','source_documents','qa'}:
        return ['invalid AI provenance shape']
    e=[]
    if a.get('language') not in {'pt','en','es','fr','ru','zh','ar'}: e.append('AI original language required')
    if p.get('schema')!=1 or p.get('mode')!='public-unfccc-diff' or p.get('authorization')!=AUTHORIZATION:
        e.append('unsupported AI release scope')
    if not timestamp(p.get('generated_at')) or any(not isinstance(p.get(k),str) or not p[k].strip() for k in ('model','prompt_version')):
        e.append('AI generation identity required')
    if 'approved_by' in a or 'approved_at' in a:
        e.append('AI mode must not claim human editorial approval')
    if a.get('contributor')!={'display':'named','name':'COP31 Monitor AI','role':'analyst'}:
        e.append('AI authorship must be explicit')
    sources=a.get('sources')
    if not isinstance(sources,list) or not sources or any(not isinstance(s,dict) or s.get('verified') is not True or not official(s.get('url')) for s in sources):
        e.append('AI analysis accepts only verified official UNFCCC sources')
    docs=p.get('source_documents')
    if not isinstance(docs,list) or len(docs)!=2:
        e.append('AI changes need exactly two verified document versions')
    else:
        for d in docs:
            if not isinstance(d,dict) or set(d)!={'id','url','version_label','reviewed_at','sha256'} or not official(d.get('url')) or not isinstance(d.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',d['id']) or not isinstance(d.get('version_label'),str) or not d['version_label'].strip() or not timestamp(d.get('reviewed_at')) or not isinstance(d.get('sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',d['sha256']):
                e.append('invalid verified AI document identity')
            elif not any(isinstance(s,dict) and s.get('url')==d['url'] for s in sources or []):
                e.append('AI document missing from cited sources')
        if all(isinstance(d,dict) for d in docs) and all(docs[0].get(k)==docs[1].get(k) for k in ('id','url','sha256')): e.append('AI baseline and current document must differ')
    q=p.get('qa')
    if not isinstance(q,dict) or set(q)!={'status','checked_at','checks'} or q.get('status')!='passed' or not timestamp(q.get('checked_at')) or not isinstance(q.get('checks'),list) or set(q['checks'])!=CHECKS or len(q['checks'])!=len(CHECKS):
        e.append('AI automated evidence checks required')
    return e
