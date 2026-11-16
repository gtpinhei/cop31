"""Identity classification must not depend on mutable production accounts."""
import runpy
import unittest
from pathlib import Path

identity = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'tools/build_pulse.py'))['identity']


class IdentityContractTests(unittest.TestCase):
    def test_reported_is_not_checked(self):
        self.assertEqual(identity('reportado'), 'reported')
        self.assertEqual(identity('reportado por terceiros'), 'reported')

    def test_official_page_is_checked(self):
        self.assertEqual(identity('página oficial'), 'checked')

    def test_unresolved_and_missing_remain_unverified(self):
        for value in ('página: resolver', 'a resolver', None, '', 'conhecimento prévio'):
            with self.subTest(value=value):
                self.assertEqual(identity(value), 'unverified')
