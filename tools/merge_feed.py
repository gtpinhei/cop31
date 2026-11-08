#!/usr/bin/env python3
"""Merge one or more feed sources into data/feed.json.

usage: python3 -I tools/merge_feed.py SOURCE [SOURCE ...]

Each SOURCE is either a full feed (object with "items") or a bare list of items.
Items are keyed by url for publications and by id for posts (posts often share a
profile url).

Precedence (so a stale copy can never overwrite a newer verified version):
- an item's version is its `updated_at`, or `first_seen` when there is none;
- an incoming item replaces the stored one only if its version is strictly newer;
- otherwise (same or older version) it can only fill fields the stored item lacks,
  such as `summary_i18n`; it never changes a value already on file.
Editors who correct an item by hand set `updated_at` so the correction wins.

Items that fail tools/validate_feed.py are dropped with a message; newer `round` /
`social_round` blocks win. Output is sorted by date then first_seen, newest first,
and written with 1-space indentation.
"""
import json, sys, pathlib, importlib.util

ROOT = pathlib.Path(__file__).resolve().parent.parent
FEED = ROOT / "data" / "feed.json"

_spec = importlib.util.spec_from_file_location("validate_feed", ROOT / "tools" / "validate_feed.py")
validate = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(validate)


def key(it):
    return ("post", it.get("id")) if it.get("kind") == "post" else ("pub", it.get("url") or it.get("id"))


def version(it):
    return it.get("updated_at") or it.get("first_seen") or ""


def newer(a, b):
    """Return the round block with the later timestamp."""
    if not a:
        return b
    if not b:
        return a
    return b if (b.get("timestamp") or "") > (a.get("timestamp") or "") else a


def fill(base, extra):
    """Copy into base the fields it lacks (or holds empty) from extra; never overwrite."""
    for k, v in extra.items():
        if k not in base or base[k] in (None, "", [], {}):
            base[k] = v
    return base


def merge_items(items, new, tracks=(), log=print):
    for it in new:
        errs, _ = validate.check_item(it, tracks)
        if errs:
            log(f"dropped {it.get('id') if isinstance(it, dict) else it!r}: {'; '.join(errs)}")
            continue
        k = key(it)
        cur = items.get(k)
        if cur is None:
            items[k] = it
        elif version(it) > version(cur):
            items[k] = fill(dict(it), cur)
        else:
            fill(cur, it)
    return items


def merge(feed, sources, log=print):
    items = {key(it): it for it in feed.get("items", [])}
    for src in sources:
        if isinstance(src, dict):
            feed["round"] = newer(feed.get("round"), src.get("round"))
            feed["social_round"] = newer(feed.get("social_round"), src.get("social_round"))
            if (src.get("generated_at") or "") > (feed.get("generated_at") or ""):
                feed["generated_at"] = src["generated_at"]
            for t in src.get("tracks", []):
                if t not in feed.setdefault("tracks", []):
                    feed["tracks"].append(t)
            new = src.get("items", [])
        else:
            new = src
        merge_items(items, new, feed.get("tracks") or (), log)
    if not feed.get("social_round"):
        feed.pop("social_round", None)
    feed["items"] = sorted(items.values(), key=lambda it: ((it.get("date") or ""), (it.get("first_seen") or "")), reverse=True)
    return feed


def main(paths):
    feed = json.loads(FEED.read_text(encoding="utf-8"))
    sources = [json.loads(pathlib.Path(p).read_text(encoding="utf-8")) for p in paths]
    feed = merge(feed, sources)
    fatal, per = validate.check_feed(feed)
    bad = [k for k, (e, _) in per.items() if e]
    if fatal or bad:
        print("refusing to write an invalid feed:", fatal, bad[:5]); sys.exit(1)
    FEED.write_text(json.dumps(feed, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    out = feed["items"]
    pubs = sum(1 for it in out if it.get("kind") != "post")
    print(f"{len(out)} items ({pubs} publications, {len(out) - pubs} posts); web round: {feed.get('round', {}).get('label')}; social round: {(feed.get('social_round') or {}).get('label')}")


if __name__ == "__main__":
    main(sys.argv[1:])
