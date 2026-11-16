# Dormant publishing examples, not deployed

These files do nothing until reviewed and moved under `.github/workflows`.
The ten-minute cron is best effort: GitHub may delay or skip scheduled jobs. UI exposes
last-success/attempt/degraded instead of implying exact timing. Keep the root watcher
until production is smoke-tested; then have it read the site's public feed/health, not
poll UNFCCC again. Its private delivered-alert ledger stays separate.

## Activation gates
- Merge/review wire adapter, public schema, actual-wire tests and restored-public tests.
- Bootstrap validated public feed once, suppress bootstrap changes and review all URLs.
- Wire builder to copy/use the dedicated public feed; no saved catalog labelled live.
- Re-run all UI/browser/mobile/RTL and existing CI; resolve held QA failure via authorized process.
- Activate both workflows together, verify Pages source is GitHub Actions and retire old
  branch-based Pages publishing to avoid competing deployments. Keep original root app
  as build source for classic.html; deployment artifact uses the new shell.
- Verify `gh workflow run field-pages.yml` is permitted by repo settings and a real run
  publishes the exact candidate commit. Bot commits alone will not trigger Pages.
- Smoke-test new canonical data on a later collector run, stale/failure health and rollback.

The producer restores only already-public sanitized document metadata when its ephemeral
checkpoint is absent. It does NOT persist or publish the private checkpoint or historical
internal event ledger. No private state is cached/uploaded; no personal tokens are used.
Only the dedicated public JSON is staged, never the whole working tree. Concurrent
reporting/social commits are rebased, not overwritten or force-pushed. Failed collection
should retain last-success/public data, publish degraded health, and fail the run.
The examples depend on collector exit0/1 and atomic-output guarantees; verify them first.

Root monitor reconciliation and repository activation are release actions, not performed
by creating these examples. New external runner/provider accounts are not required.
