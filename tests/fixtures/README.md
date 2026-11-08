# Test fixtures (not site content)

These files exist only for `tests/test_v1.mjs`. The site never fetches anything from `tests/`
(enforced by a test), and GitHub Pages serves them only if someone types their address.

- `bsky_enb_p1.json`: AUTHENTIC public post by @enb.iisd.org, captured 8 Nov 2026.
- `bsky_fixture_alpha.json`: SYNTHETIC. Fictional account `fixture-alpha.test` (reserved `.test` domain);
  every invented text starts with `[TEST FIXTURE]`. It includes a `<script>` string to prove escaping.
- `bsky_enb_p2.json`, `bsky_notfound.json`, `bsky_ratelimit.json`: SYNTHETIC minimal responses.

Do not attribute invented text to real accounts in fixtures.
