#!/usr/bin/env python3
"""Fail if anything unpublished is tracked (CI) or staged (pre-commit hook) in this public repository.

  python3 -I tools/check_public.py            # every tracked file (CI)
  python3 -I tools/check_public.py --staged   # files staged for the next commit (tools/hooks/pre-commit)

Blocked: the legacy editorial/ folder, original documents (.docx, .pdf, .doc, .odt, .rtf, .pages), private-store
file names (drafts.json, paragraphs.json, proposal.json, prompt.md, meta.json, published.json, original.*), and any
public data file that fails validation (drafts, review markers, private fields). Test fixtures under
tests/fixtures/ are allowed only if marked synthetic.
"""
import pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC_EXT = {".docx", ".pdf", ".doc", ".odt", ".rtf", ".pages"}
PRIVATE_NAMES = {"drafts.json", "paragraphs.json", "proposal.json", "prompt.md", "published.json"}


def files(staged):
    cmd = ["git", "-C", str(ROOT), "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if staged else ["git", "-C", str(ROOT), "ls-files"]
    return [l for l in subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines() if l]


def main(argv):
    staged = "--staged" in argv
    bad = []
    for f in files(staged):
        p = pathlib.PurePosixPath(f)
        if p.parts[0] == "editorial":
            bad.append(f"{f}: editorial working files must stay in the private store")
        elif p.suffix.lower() in DOC_EXT:
            bad.append(f"{f}: original documents are never committed")
        elif p.name in PRIVATE_NAMES or re.match(r"original\.", p.name) or (p.name == "meta.json" and "intake" in p.parts):
            bad.append(f"{f}: looks like a private-store file")
        elif p.parts[0] == "tests" and "fixtures" in p.parts and "intake" in p.parts:
            text = (ROOT / f).read_text(encoding="utf-8", errors="replace") if (ROOT / f).exists() else ""
            if "SYNTHETIC" not in text and "[TESTE]" not in text:
                bad.append(f"{f}: intake fixtures must be visibly synthetic")
    r = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "validate_feed.py"), "-q"], capture_output=True, text=True)
    if r.returncode != 0:
        bad.append("public data does not validate:\n" + r.stdout)
    for b in bad:
        print("BLOCKED:", b)
    print("OK" if not bad else f"{len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
