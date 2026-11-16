#!/usr/bin/env python3
"""Pure I/O boundary for DACS snapshot and changed/today normalized adapters.

Actual DACS wire schema MUST be investigated before mapping responses here.
This boundary accepts already normalized {documents: [...]} envelopes, with
complete snapshot + same-day changes and optional previous-day rollover changes.
Neither the URL nor the route name proves a successful, complete read.
"""
import gzip
import json
from datetime import datetime, timedelta, timezone


def decode_payload(blob):
    if isinstance(blob, str):
        blob = blob.encode('utf-8')
    if blob[:2] == b'\x1f\x8b':
        blob = gzip.decompress(blob)
    obj = json.loads(blob)
    if not isinstance(obj, dict) or not isinstance(obj.get('documents'), list):
        raise ValueError('unrecognized normalized payload schema')
    return obj


def rollover_days(checked_at, previous_success=None):
    """Days whose changed deltas must be reconciled; no unsupported URL guessed."""
    now = datetime.fromisoformat(checked_at.replace('Z','+00:00')).astimezone(timezone.utc)
    since = (datetime.fromisoformat(previous_success.replace('Z','+00:00')).astimezone(timezone.utc)
             if previous_success else now - timedelta(days=1))
    if since > now:
        raise ValueError('out-of-order check')
    start = since.date()
    out=[]
    while start <= now.date():
        out.append(start.isoformat())
        start += timedelta(days=1)
        if len(out) > 8:
            raise ValueError('more than 7 days of delta history needs full reconciliation')
    return out


def combine(snapshot, deltas, checked_at):
    """Overlay changed/today onto full snapshot without treating missing ids as deletions.

    Requires snapshots to be validated upstream as complete. Changed items
    can represent explicit withdrawals but absent items never do.
    """
    if snapshot.get('snapshot_complete') is not True:
        raise ValueError('full snapshot not confirmed')
    if not isinstance(snapshot.get('documents'), list):
        raise ValueError('missing snapshot documents')
    merged = {str(item['id']): item for item in snapshot['documents']}
    for delta in deltas:
        if not delta.get('delta_complete') or not isinstance(delta.get('documents'), list):
            raise ValueError('changed endpoint failed; cannot advance checkpoint')
        for item in delta['documents']:
            key = str(item['id'])
            merged[key] = item
    return dict(snapshot_complete=True, checked_at=checked_at, documents=list(merged.values()))
