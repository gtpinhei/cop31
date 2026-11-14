"""Identity export regressions use synthetic input, never the live account registry."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("build_pulse", Path(__file__).resolve().parents[1] / "tools" / "build_pulse.py")
build_pulse = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_pulse)


class PulseIdentityExportTests(unittest.TestCase):
    def test_export_preserves_identity_provenance(self):
        cases = [
            ("checked.fixture.test", "página oficial", "checked"),
            ("reported.fixture.test", "reportado", "reported"),
            ("unresolved.fixture.test", "página oficial; resolver handle", "unverified"),
            ("unknown.fixture.test", None, "unverified"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            watchlist = root / "watchlist.json"
            output = root / "pulse.json"
            watchlist.write_text(json.dumps({"accounts": [
                {"platform": "bluesky", "handle": handle, "institution": "Synthetic fixture", "verified": basis}
                for handle, basis, _ in cases
            ]}), encoding="utf-8")
            with patch.object(build_pulse, "OUT", output), contextlib.redirect_stdout(io.StringIO()):
                build_pulse.main(watchlist)
            accounts = json.loads(output.read_text(encoding="utf-8"))["accounts"]
            self.assertEqual(len(accounts), len(cases))
            for account, (handle, basis, expected) in zip(accounts, cases):
                with self.subTest(handle=handle):
                    self.assertEqual(account["identity"], expected)
                    self.assertEqual(account["identity_basis"], basis)
                    self.assertEqual(account["verified"], expected == "checked")


if __name__ == "__main__":
    unittest.main()
