#!/usr/bin/env python3
"""Public analysis index gate. Article bodies/approval stay in the existing workflow.

This is metadata validation, not proof of human approval or source immutability.
Never place private drafts in the index, even when an entry is disabled.
"""
import datetime as dt
import importlib.util
import json
import pathlib
import re
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent.parent
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{2,79}\Z")
KEYS = {"article", "format", "reporting_date", "document", "comparison", "superseded_by"}
DOC_KEYS = {"url", "version_label", "reviewed_at", "sha256"}


def timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def document_errors(doc):
    if not isinstance(doc, dict):
        return ["document must be an object"]
    errors = []
    if set(doc) - DOC_KEYS:
        errors.append("document has unexpected fields")
    try:
        url = urlsplit(doc.get("url", ""))
        if url.scheme != "https" or url.hostname not in {"unfccc.int", "www.unfccc.int", "docs.unfccc.int"} or url.username or url.password or url.port not in (None, 443):
            errors.append("document requires an official UNFCCC HTTPS URL without credentials")
    except (TypeError, ValueError):
        errors.append("invalid document URL")
    if not isinstance(doc.get("version_label"), str) or not doc["version_label"].strip():
        errors.append("document needs the exact reviewed version label")
    if not timestamp(doc.get("reviewed_at")):
        errors.append("document needs a timezone-aware review timestamp")
    if not isinstance(doc.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", doc["sha256"]):
        errors.append("document needs a verified PDF-byte SHA256, never a challenge-page hash")
    return errors


def validate(doc, root=ROOT):
    if not isinstance(doc, dict) or set(doc) != {"schema", "entries"} or doc.get("schema") != 1 or not isinstance(doc.get("entries"), list):
        return ["analysis index must contain only schema=1 and entries array"]
    spec = importlib.util.spec_from_file_location("analysis_feed_validator", pathlib.Path(__file__).with_name("validate_feed.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    errors, seen = [], set()
    if module._private_leak(doc):
        errors.append("analysis index mentions private-store material")
    for row in doc["entries"]:
        if not isinstance(row, dict):
            errors.append("analysis entry must be an object")
            continue
        if set(row) - KEYS:
            errors.append("analysis entry has unexpected fields; no bodies, private notes or drafts allowed")
        aid = row.get("article")
        if not isinstance(aid, str) or not SLUG.fullmatch(aid):
            errors.append("analysis entry requires a safe canonical article id")
            continue
        if aid in seen:
            errors.append(f"duplicate canonical article: {aid}")
        seen.add(aid)
        article = {}
        try:
            article = json.loads((root / "data" / "articles" / (aid + ".json")).read_text())
            article_errors, _ = module.check_article(article, public=True)
            errors.extend(f"{aid}: {e}" for e in article_errors)
            if article.get("id") != aid:
                errors.append(f"{aid}: article id does not match")
            if not timestamp(article.get("approved_at")):
                errors.append(f"{aid}: valid timestamp of explicit editorial approval required")
            if not article.get("contributor"):
                errors.append(f"{aid}: explicitly cleared attribution required")
            if not any(s.get("verified") is True and s.get("url", "").startswith("https://") for s in article.get("sources", []) if isinstance(s, dict)):
                errors.append(f"{aid}: verified public source required")
        except (OSError, ValueError, TypeError, AttributeError):
            errors.append(f"{aid}: valid published canonical article required")
            article = {}
        if row.get("format") == "daily-diplomacy-brief":
            try:
                dt.date.fromisoformat(row.get("reporting_date", ""))
            except (TypeError, ValueError):
                errors.append(f"{aid}: daily brief requires reporting_date")
            if "document" in row or "comparison" in row:
                errors.append(f"{aid}: document metadata belongs to text-explained")
        elif row.get("format") == "text-explained":
            errors.extend(f"{aid}: {e}" for e in document_errors(row.get("document")))
            ref = row.get("document")
            public_sources = article.get("sources", [])
            public_sources = public_sources if isinstance(public_sources, list) else []
            if isinstance(ref, dict) and not any(isinstance(s, dict) and s.get("verified") is True and s.get("url") == ref.get("url") for s in public_sources):
                errors.append(f"{aid}: reviewed document must be a verified article source")
            comparison = row.get("comparison")
            if comparison != {"status": "not_assessed"}:
                if not isinstance(comparison, dict) or set(comparison) != {"status", "baseline"} or comparison.get("status") != "compared":
                    errors.append(f"{aid}: comparison must be explicitly not_assessed or compared with baseline")
                else:
                    errors.extend(f"{aid} baseline: {e}" for e in document_errors(comparison["baseline"]))
                    baseline = comparison["baseline"]
                    if isinstance(baseline, dict) and not any(isinstance(s, dict) and s.get("verified") is True and s.get("url") == baseline.get("url") for s in public_sources):
                        errors.append(f"{aid}: comparison baseline must be a verified article source")
            if "reporting_date" in row:
                errors.append(f"{aid}: reporting_date belongs to daily-diplomacy-brief")
        else:
            errors.append(f"{aid}: unsupported analysis format")
    links = {r.get("article"): r.get("superseded_by") for r in doc["entries"] if isinstance(r, dict) and isinstance(r.get("article"), str)}
    for aid, target in links.items():
        if target is not None and (not isinstance(target, str) or target not in seen):
            errors.append(f"{aid}: superseded_by must identify an indexed approved article")
            continue
        chain, current = set(), aid
        while current in links:
            if current in chain:
                errors.append(f"{aid}: supersession cycle")
                break
            chain.add(current)
            current = links[current]
            if not isinstance(current, str):
                break
    return errors


def problems(root=ROOT):
    path = root / "data" / "analysis.json"
    if not path.exists():
        return []  # Backward-compatible for older snapshots and private tooling tests.
    try:
        return validate(json.loads(path.read_text()), root)
    except (ValueError, OSError):
        return ["analysis index unreadable"]


if __name__ == "__main__":
    errors = problems()
    print("\n".join(errors) if errors else "Analysis index OK")
    raise SystemExit(bool(errors))
