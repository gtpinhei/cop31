"""Private editorial store: drafts, submissions, original documents, evidence and permissions.

Everything unpublished lives here, OUTSIDE the repository and outside anything GitHub Pages serves.
Location: $COP31_PRIVATE, or a sibling folder of the repository named cop31-private.

The store refuses to live inside this repository, or inside any git working tree whose remote is the
public repository, so an unpublished document can never be committed by accident.
"""
import json, os, pathlib, subprocess, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUBLIC_REMOTE = "gtpinhei/cop31"


class StoreError(SystemExit):
    pass


def _inside(child, parent):
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _git_remote(path):
    try:
        top = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
        if top.returncode != 0:
            return None
        r = subprocess.run(["git", "-C", str(path), "remote", "-v"], capture_output=True, text=True, timeout=10)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return None


def store_path():
    p = pathlib.Path(os.environ.get("COP31_PRIVATE") or (ROOT.parent / "cop31-private")).expanduser().resolve()
    if _inside(p, ROOT.resolve()):
        raise StoreError(f"refusing private store inside the repository: {p}")
    probe = p if p.exists() else p.parent
    remotes = _git_remote(probe)
    if remotes is not None and PUBLIC_REMOTE in remotes:
        raise StoreError(f"refusing private store inside a clone of the public repository: {p}")
    return p


def ensure():
    p = store_path()
    for sub in ("", "intake", "articles", "i18n"):
        d = p / sub
        d.mkdir(parents=True, exist_ok=True)
        try:
            d.chmod(0o700)
        except OSError:
            pass
    return p


def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat(timespec="minutes")


def load_json(path, default):
    path = pathlib.Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, doc, private=True):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if private:
        try:
            tmp.chmod(0o600)
        except OSError:
            pass
    tmp.replace(path)
