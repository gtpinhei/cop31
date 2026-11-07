#!/usr/bin/env python3
"""Merge one or more feed sources into data/feed.json.

usage: python3 -I tools/merge_feed.py SOURCE [SOURCE ...]

Each SOURCE is either a full feed (object with "items") or a bare list of items.
Items are keyed by url for publications and by id for posts (posts often share a
profile url). Newer `round` / `social_round` blocks win. Output is sorted by date
then first_seen, newest first, and written with 1-space indentation.
"""
import json, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FEED = ROOT / "data" / "feed.json"


def key(it):
    return ("post", it.get("id")) if it.get("kind") == "post" else ("pub", it.get("url") or it.get("id"))


def newer(a, b):
    """Return the round block with the later timestamp."""
    if not a:
        return b
    if not b:
        return a
    return b if (b.get("timestamp") or "") > (a.get("timestamp") or "") else a


def main(paths):
    feed = json.loads(FEED.read_text(encoding="utf-8"))
    items = {key(it): it for it in feed.get("items", [])}
    for p in paths:
        src = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
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
        for it in new:
            k = key(it)
            if k not in items or (it.get("first_seen") or "") >= (items[k].get("first_seen") or ""):
                # keep translations already on file when the incoming copy lacks them
                if k in items and items[k].get("summary_i18n") and not it.get("summary_i18n"):
                    it["summary_i18n"] = items[k]["summary_i18n"]
                items[k] = it
            elif not items[k].get("summary_i18n") and it.get("summary_i18n"):
                items[k]["summary_i18n"] = it["summary_i18n"]
    if not feed.get("social_round"):
        feed.pop("social_round", None)
    out = sorted(items.values(), key=lambda it: ((it.get("date") or ""), (it.get("first_seen") or "")), reverse=True)
    feed["items"] = out
    FEED.write_text(json.dumps(feed, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    pubs = sum(1 for it in out if it.get("kind") != "post")
    print(f"{len(out)} items ({pubs} publications, {len(out) - pubs} posts); web round: {feed.get('round', {}).get('label')}; social round: {(feed.get('social_round') or {}).get('label')}")


if __name__ == "__main__":
    main(sys.argv[1:])
