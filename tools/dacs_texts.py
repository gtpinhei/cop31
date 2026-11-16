#!/usr/bin/env python3
"""Conservative DACS document delta tracker (offline-first integration scaffold).

Only verified *document-level* identifiers and attachment evidence create text events.
No live endpoint schema is assumed. The --input format is a normalized adapter
contract, NOT a claim that DACS returns these keys. A schema-specific adapter must
be validated against actual official endpoint responses before live deployment.

Usage:
  python tools/dacs_texts.py apply --input normalized.json --state private/state.json --out out/texts.json
  python tools/dacs_texts.py status --state private/state.json

Input: {"checked_at": ISO8601 UTC, "snapshot_complete": true|false,
        "documents": [{"id":"...", "title":"...", "body":"CMA", "session":"CMA-8",
          "agenda":"...", "published_at":ISO, "modified_at":ISO, "status":"draft|informal|proposed|adopted|unknown|withdrawn",
          "withdrawn":false, "language":"en", "document_code":"...",
          "metadata_version":"...", "attachments":[{"url":"https://...", "sha256":"...", "language":"en"}]}]}

Input is a complete snapshot or already reconciled full-snapshot + changes overlay.
A changed/today partial feed alone must never be labeled snapshot_complete.
First successful run stores baseline without retroactive notifications.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

ALLOWED_HOSTS = {"docs.unfccc.int", "unfccc.int"}
STATUSES = {"draft", "informal", "proposed", "adopted", "unknown", "withdrawn"}
PRIORITY = (
    ("TAFF / mitigation", ("taff", "fossil", "mitigation", "mwp", "transition away")),
    ("Finance", ("finance", "article 9", "ncqg", "climate finance")),
    ("Adaptation", ("adaptation", "gga", "nap")),
    ("Just transition", ("just transition", "jtwp")),
    ("GST / IPCC", ("stocktake", "gst", "ipcc")),
    ("Cover decision", ("cover decision", "mutirão", "mutirao")),
)


def iso(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return None
        return stamp.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def official(url):
    try:
        u = urlsplit(url)
        return u.scheme == "https" and u.hostname in ALLOWED_HOSTS and not u.username and not u.password
    except (ValueError, TypeError):
        return False


def topic(row):
    t = " ".join(str(row.get(k) or "") for k in ("title", "agenda", "document_code")).lower()
    return next((label for label, words in PRIORITY if any(word in t for word in words)), "Other negotiations")


def normalize(row):
    if not isinstance(row, dict) or not isinstance(row.get("id"), (str, int)):
        raise ValueError("document id missing")
    did = str(row["id"]).strip()
    if not did or len(did) > 100:
        raise ValueError("invalid document id")
    title = row.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("document title missing")
    if row.get("status", "unknown") not in STATUSES:
        raise ValueError("unknown status: do not infer adopted/draft")
    attachments = []
    for a in row.get("attachments", []):
        if not isinstance(a, dict) or not official(a.get("url")):
            raise ValueError("nonofficial or invalid attachment URL")
        sha = a.get("sha256")
        if sha is not None and (not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdefABCDEF" for c in sha)):
            raise ValueError("invalid attachment sha256")
        attachments.append({"url": a["url"], "sha256": sha.lower() if sha else None,
                            "language": a.get("language") or row.get("language") or "und"})
    withdrawn = bool(row.get("withdrawn", False)) or row.get("status") == "withdrawn"
    # An actual attachment hash or a verified new attachment version is needed to flag a text revision.
    # URL changes without hashes require review; metadata edits must not become 'new text'.
    return {"id": did, "title": title.strip(), "body": str(row.get("body") or ""),
            "session": str(row.get("session") or ""), "agenda": str(row.get("agenda") or ""),
            "document_code": str(row.get("document_code") or ""),
            "published_at": iso(row.get("published_at")), "modified_at": iso(row.get("modified_at")),
            "metadata_version": str(row.get("metadata_version") or ""),
            "status": "withdrawn" if withdrawn else row.get("status", "unknown"),
            "withdrawn": withdrawn, "attachments": sorted(attachments, key=lambda a: (a["language"], a["url"])),
            "topic": topic(row)}


def signatures(row):
    hashed = sorted((a["language"], a["sha256"]) for a in row["attachments"] if a["sha256"])
    urls = sorted((a["language"], a["url"]) for a in row["attachments"])
    return hashed, urls


def compare(old, new):
    if not old:
        return "new"
    if old["withdrawn"] != new["withdrawn"]:
        return "withdrawn" if new["withdrawn"] else "reinstated"
    old_hash, old_urls = signatures(old)
    new_hash, new_urls = signatures(new)
    if old_hash and new_hash:
        old_by_lang = {}
        new_by_lang = {}
        for lang, value in old_hash:
            old_by_lang.setdefault(lang, set()).add(value)
        for lang, value in new_hash:
            new_by_lang.setdefault(lang, set()).add(value)
        # A newly indexed translation is not a new substantive source-text revision.
        # Only changed hashes for a language present in both versions qualify.
        if any(old_by_lang[lang] != new_by_lang[lang] for lang in old_by_lang.keys() & new_by_lang.keys()):
            return "revised"
        if old_by_lang.keys() <= new_by_lang.keys() and all(old_by_lang[k] == new_by_lang[k] for k in old_by_lang):
            return "metadata_only" if old != new else "unchanged"
    if old_urls != new_urls and not (old_hash and new_hash and old_hash == new_hash):
        return "attachment_unverified"  # evidence insufficient to claim a revised text
    if old != new:
        return "metadata_only"
    return "unchanged"


def load(path):
    p = Path(path)
    if not p.exists():
        return {"schema": 1, "initialized": False, "documents": {}, "events": [], "last_success": None}
    result = json.loads(p.read_text(encoding="utf-8"))
    if result.get("schema") != 1 or not isinstance(result.get("documents"), dict):
        raise ValueError("unsupported state")
    return result


def atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)
        tmp = f.name
    os.replace(tmp, path)


def apply(data, state):
    if not isinstance(data, dict) or not data.get("snapshot_complete"):
        raise ValueError("full snapshot plus changes overlay must be reconciled first")
    stamp = iso(data.get("checked_at"))
    if not stamp:
        raise ValueError("checked_at must be timezone-aware")
    if state.get("last_success") and stamp < state["last_success"]:
        raise ValueError("out-of-order snapshot: refusing state rollback")
    raw = data.get("documents")
    if not isinstance(raw, list) or not raw:
        raise ValueError("empty snapshot cannot establish healthy coverage")
    incoming = {}
    for raw_item in raw:
        row = normalize(raw_item)
        did = row["id"]
        if did in incoming:
            prev = incoming[did]
            # Multiple languages for one DACS ID are merged. The canonical record's
            # title can be localized by a future display adapter, never a new event.
            if (prev["status"], prev["withdrawn"]) != (row["status"], row["withdrawn"]):
                raise ValueError("conflicting statuses for document " + did)
            merged = {**prev}
            merged["attachments"] = sorted({(a["language"], a["url"]): a for a in prev["attachments"] + row["attachments"]}.values(), key=lambda a: (a["language"], a["url"]))
            if not merged["published_at"]:
                merged["published_at"] = row["published_at"]
            incoming[did] = merged
        else:
            incoming[did] = row
    existing = state["documents"]
    first = not state.get("initialized")
    events = []
    for did, row in incoming.items():
        change = compare(existing.get(did), row)
        if not first and change in {"new", "revised", "withdrawn", "reinstated"}:
            # Stable event key keeps retry / repeated snapshots idempotent.
            hashes, urls = signatures(row)
            proof = json.dumps([did, change, hashes if hashes else urls, row["withdrawn"]], sort_keys=True)
            event_id = hashlib.sha256(proof.encode()).hexdigest()[:24]
            events.append({"event_id": event_id, "document_id": did, "change": change, "at": stamp})
    # Disappearing records stay visible; absence from full snapshot alone is not withdrawal.
    state["documents"] = {**existing, **incoming}
    old_event_ids = {e["event_id"] for e in state.get("events", [])}
    state["events"] = state.get("events", []) + [e for e in events if e["event_id"] not in old_event_ids]
    state.update({"schema": 1, "initialized": True, "last_success": stamp})
    payload = {"schema": 1, "checked_at": stamp, "last_success": stamp,
               "sources": ["https://docs.unfccc.int/documents/metadata/all", "https://docs.unfccc.int/documents/metadata/changed/today"],
               "documents": sorted(state["documents"].values(), key=lambda d: (d["topic"], d["id"])),
               "changes": [e for e in events if e["event_id"] not in old_event_ids],
               "history_count": len(state["events"])}
    return state, payload


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("apply")
    a.add_argument("--input", required=True)
    a.add_argument("--state", required=True)
    a.add_argument("--out", required=True)
    b = sp.add_parser("status")
    b.add_argument("--state", required=True)
    args = p.parse_args()
    if args.cmd == "status":
        s = load(args.state)
        print(json.dumps({"initialized": s.get("initialized"), "last_success": s.get("last_success"),
                          "documents": len(s["documents"]), "events": len(s.get("events", []))}))
        return
    s, output = apply(json.loads(Path(args.input).read_text(encoding="utf-8")), load(args.state))
    atomic(args.state, s)
    atomic(args.out, output)
    print(json.dumps({"documents": len(output["documents"]), "new_events": len(output["changes"]), "last_success": output["last_success"]}))

if __name__ == "__main__":
    main()
