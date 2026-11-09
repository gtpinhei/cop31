#!/usr/bin/env python3
"""Standing contributor authorizations (private store: contributors.json).

A trusted contributor is onboarded once: identity, how they want to be credited and what they allow
by default. Each new submission can then reuse that profile (intake.py add --profile SLUG) instead of
repeating the onboarding. A profile never replaces the decisions taken per item:

  - every publication still needs a named editor's approval (today.py publish --by);
  - politically sensitive analysis (the default for every submission) needs its own, per-item
    authorization (intake.py permissions SID --publish-analysis yes --by EDITOR);
  - only analysis the editor marks routine (intake.py add --sensitivity routine) can use the
    profile's standing consent to routine analysis;
  - original documents are never published from a profile;
  - revoking a profile blocks publication of every unpublished draft that relied on it.

  python3 -I tools/contributors.py register SLUG --name "..." --role author|observer|analyst|organization
        --attribute named|anonymous [--affiliation "..."] [--show-affiliation yes|no]
        [--routine-analysis yes|no] [--anonymity-reason "..."] --consent "how the contributor gave consent" --by EDITOR
  python3 -I tools/contributors.py update SLUG --by EDITOR [same options]
  python3 -I tools/contributors.py revoke SLUG --by EDITOR --reason "..."
  python3 -I tools/contributors.py list | show SLUG
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools"))
import private as P  # noqa: E402

ROLES = {"author", "observer", "analyst", "organization"}
FIELDS = ("name", "affiliation", "role", "attribute", "show_affiliation", "routine_analysis", "anonymity_reason", "consent")


def path():
    return P.ensure() / "contributors.json"


def load():
    return P.load_json(path(), {"schema": 1, "contributors": {}})


def get(slug):
    """The active profile, or None. A revoked profile is returned with status 'revoked'."""
    return load()["contributors"].get(slug)


def opt(a, k, default=None):
    return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else default


def _yn(v, k):
    if v is None:
        return None
    if v not in ("yes", "no"):
        sys.exit(f"{k} must be yes or no")
    return v == "yes"


def _read(a):
    vals = {"name": opt(a, "--name"), "affiliation": opt(a, "--affiliation"), "role": opt(a, "--role"),
            "attribute": opt(a, "--attribute"), "show_affiliation": _yn(opt(a, "--show-affiliation"), "--show-affiliation"),
            "routine_analysis": _yn(opt(a, "--routine-analysis"), "--routine-analysis"),
            "anonymity_reason": opt(a, "--anonymity-reason"), "consent": opt(a, "--consent")}
    return {k: v for k, v in vals.items() if v is not None}


def _check(p):
    if not p.get("name") or p.get("role") not in ROLES:
        sys.exit(f"--name and --role ({'|'.join(sorted(ROLES))}) are required")
    if p.get("attribute") not in ("named", "anonymous"):
        sys.exit("--attribute must be named or anonymous (a standing profile records a decision, not 'ask')")
    if p["attribute"] == "anonymous" and not p.get("anonymity_reason"):
        sys.exit("anonymous attribution needs --anonymity-reason (kept internal)")
    if not p.get("consent"):
        sys.exit("--consent is required: say how and when the contributor gave this standing authorization")


def register(a):
    slug, by = a[1], opt(a, "--by")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", slug):
        sys.exit("SLUG must be a short lowercase slug")
    if not by:
        sys.exit("--by EDITOR is required")
    doc = load()
    if slug in doc["contributors"]:
        sys.exit(f"{slug} already exists (use update)")
    p = dict({"show_affiliation": False, "routine_analysis": False}, **_read(a))
    _check(p)
    p.update(status="active", granted_by=by, granted_at=P.now(), publish_document=False,
             history=[{"at": P.now(), "by": by, "event": "registered"}])
    doc["contributors"][slug] = p
    P.save_json(path(), doc)
    print(f"registered {slug}: {p['attribute']}" + (" with affiliation" if p["show_affiliation"] else "")
          + ("; routine analysis allowed by default" if p["routine_analysis"] else "; every analysis needs per-item authorization"))


def update(a):
    slug, by = a[1], opt(a, "--by")
    if not by:
        sys.exit("--by EDITOR is required")
    doc = load()
    p = doc["contributors"].get(slug) or sys.exit(f"no profile {slug}")
    if p.get("status") != "active":
        sys.exit(f"{slug} is {p.get('status')}: register a new authorization instead of editing a revoked one")
    change = _read(a)
    if not change:
        sys.exit("nothing to update")
    trial = dict(p, **change)
    _check(trial)
    p.update(change)
    p["history"].append({"at": P.now(), "by": by, "event": "updated", "changes": sorted(change)})
    P.save_json(path(), doc)
    print(f"updated {slug}: {', '.join(sorted(change))}")


def revoke(a):
    slug, by, reason = a[1], opt(a, "--by"), opt(a, "--reason")
    if not by or not reason:
        sys.exit("--by and --reason are required")
    doc = load()
    p = doc["contributors"].get(slug) or sys.exit(f"no profile {slug}")
    import datetime
    p.update(status="revoked", revoked_at=P.now(), revoked_by=by,
             revoked_at_s=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds"))
    p["history"].append({"at": P.now(), "by": by, "event": "revoked", "reason": reason})
    P.save_json(path(), doc)
    print(f"revoked {slug}: unpublished drafts that relied on it are blocked until re-authorized per item")


def apply_to_submission(slug, sensitivity):
    """Contributor block, permissions and audit entry for a new submission (used by intake.py add)."""
    p = get(slug)
    if not p:
        sys.exit(f"no contributor profile {slug} (contributors.py register)")
    if p.get("status") != "active":
        sys.exit(f"contributor profile {slug} is {p.get('status')}")
    contributor = {"name": p["name"], "affiliation": p.get("affiliation") if p.get("show_affiliation") else None,
                   "role": p["role"]}
    routine = sensitivity == "routine" and p.get("routine_analysis") is True
    perm = {"attribute": p["attribute"], "publish_analysis": routine, "publish_document": False}
    standing = {"profile": slug, "granted_by": p["granted_by"], "granted_at": p["granted_at"], "sensitivity": sensitivity}
    hist = {"at": P.now(), "by": f"standing profile {slug}",
            "changes": {"attribute": p["attribute"], "publish_analysis": routine,
                        "basis": "standing authorization" + (" (routine analysis)" if routine else
                                 "; analysis needs per-item authorization")}}
    return contributor, perm, standing, hist, p.get("anonymity_reason")


def list_cmd():
    for slug, p in sorted(load()["contributors"].items()):
        print(f"{slug:24} {p.get('status'):8} {p['attribute']:9} routine-analysis:{'yes' if p.get('routine_analysis') else 'no'}  {p['name']}")


def main(a):
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "register" and len(a) > 1: register(a)
    elif cmd == "update" and len(a) > 1: update(a)
    elif cmd == "revoke" and len(a) > 1: revoke(a)
    elif cmd == "list": list_cmd()
    elif cmd == "show" and len(a) > 1:
        import json
        print(json.dumps(get(a[1]) or {}, ensure_ascii=False, indent=1))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
