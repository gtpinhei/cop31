#!/usr/bin/env python3
"""Build data/pulse.json (public Social Pulse config) from the monitoring watchlist.

usage: python3 -I tools/build_pulse.py WATCHLIST.json

Only public-safe fields are exported. Identity provenance is kept, not collapsed:

  identity           "checked"    handle read on the institution's/person's own official page ("página")
                     "reported"   handle cited by a third-party source ("reportado"), not checked
                     "unverified" anything else (prior knowledge, unresolved handle, ...)
  identity_basis     the watchlist's own wording, verbatim
  identity_evidence  URL of the page that confirms the handle, when recorded (else null)
  identity_checked_at  date of that check, when recorded (else null)
  verified           kept for older readers: true only for "checked"

Account health (does the handle currently resolve?) is a separate question from identity:
health / health_checked_at / health_source are copied from the existing data/pulse.json and never
inferred here. Inactive accounts and internal notes are dropped. Existing `bluesky_list`, `x_list`
and `hidden` settings are kept.
"""
import json, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "pulse.json"
PLATFORMS = ("bluesky", "x", "instagram", "youtube")
KEEP = ("health", "health_checked_at", "health_source", "identity_evidence", "identity_checked_at")


def identity(raw):
    s = str(raw or "").strip().lower()
    if s.startswith("página") and "resolver" not in s:
        return "checked"
    if s.startswith("reportado"):
        return "reported"
    return "unverified"


def main(path):
    wl = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    prev = {(a["platform"], a["handle"].lower()): a for a in old.get("accounts", [])}
    accounts = []
    for a in wl.get("accounts", []):
        if a.get("inactive") or a.get("platform") not in PLATFORMS:
            continue
        handle = a["handle"].lstrip("@") if a["platform"] in ("x", "instagram") else a["handle"]
        idn = identity(a.get("verified"))
        e = {
            "platform": a["platform"],
            "handle": handle,
            "institution": a["institution"],
            "priority": a.get("priority", "B"),
            "identity": idn,
            "identity_basis": a.get("verified"),
            "identity_evidence": a.get("evidence_url"),
            "identity_checked_at": a.get("checked_at"),
            "verified": idn == "checked",
        }
        if a["platform"] == "youtube":
            e["channel_id"] = a.get("channel_id")
        p = prev.get((a["platform"], handle.lower()), {})
        for k in KEEP:
            if p.get(k) is not None and e.get(k) is None:
                e[k] = p[k]
        accounts.append(e)
    out = {
        "schema": 2,
        "updated": wl.get("updated"),
        "bluesky_list": old.get("bluesky_list"),
        "x_list": old.get("x_list"),
        "hidden": old.get("hidden", []),
        "accounts": accounts,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    by, ids = {}, {}
    for a in accounts:
        by[a["platform"]] = by.get(a["platform"], 0) + 1
        ids[a["identity"]] = ids.get(a["identity"], 0) + 1
    print(f"{len(accounts)} accounts: {by}; identity: {ids}")


if __name__ == "__main__":
    main(sys.argv[1])
