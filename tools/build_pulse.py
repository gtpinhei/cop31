#!/usr/bin/env python3
"""Build data/pulse.json (public Social Pulse config) from the monitoring watchlist.

usage: python3 -I tools/build_pulse.py WATCHLIST.json

Only public-safe fields are exported: platform, handle, institution, priority,
verified (bool) and, for YouTube, channel_id. Inactive accounts and internal
notes are dropped. Existing `bluesky_list`, `x_list`, `hidden` and `instagram_posts`
settings in data/pulse.json are kept.
"""
import json, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "pulse.json"
PLATFORMS = ("bluesky", "x", "instagram", "youtube")


def main(path):
    wl = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    accounts = []
    for a in wl.get("accounts", []):
        if a.get("inactive") or a.get("platform") not in PLATFORMS:
            continue
        e = {
            "platform": a["platform"],
            "handle": a["handle"].lstrip("@") if a["platform"] in ("x", "instagram") else a["handle"],
            "institution": a["institution"],
            "priority": a.get("priority", "B"),
            "verified": str(a.get("verified", "")).startswith(("página", "reportado")),
        }
        if a["platform"] == "youtube":
            e["channel_id"] = a.get("channel_id")
        accounts.append(e)
    out = {
        "schema": 1,
        "updated": wl.get("updated"),
        "bluesky_list": old.get("bluesky_list"),
        "x_list": old.get("x_list"),
        "hidden": old.get("hidden", []),
        "accounts": accounts,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    by = {}
    for a in accounts:
        by[a["platform"]] = by.get(a["platform"], 0) + 1
    print(f"{len(accounts)} accounts: {by}")


if __name__ == "__main__":
    main(sys.argv[1])
