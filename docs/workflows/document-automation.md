# Controlled automation publisher rollout (NOT ENABLED)

This runbook and offline guard do not change any schedule or publish data. The
current GitHub producer remains authoritative until the controlled handover.

## What is proven

- At 16 Nov 2026, native workflow was active on default `main`, but only manual
  runs were observed. Do not claim the reason is diagnosed.
- Existing collector completed a read-only cloud dry run in 91.15 seconds and
  restored all 100 public records without persistent private state.
- Connector git commit/ref publication of `0fce3b0` generated a push-triggered
  `Publish Field Edition` run 43976918831, successfully deployed the exact commit.
- The Pages workflow matches `data/**`. Thus a connector contents update to
  `data/negotiating-texts.json` should trigger it, but this exact contents-API path
  must be verified by the first controlled publication. Do not assume success.
- No new GitHub credentials are needed: fetch_file returns the blob SHA;
  update_file accepts that exact SHA. Tool availability must be checked per run.

## Durable preparation (root coordinates)

1. Publish this guard, tests and runbook only after independent review, using the
   existing publishing authorization. This alone changes no producer schedule.
2. Save the complete runtime instructions below in the existing ten-minute
   automation. Preserve its alerts, expiry, confidentiality rules and coverage
   limits. Start in `shadow` mode: collection/validation only, no public writes.
3. A future automation wake (not just the current conversation) must reconstruct
   code and baseline, complete a candidate and report its receipt. Confirm root
   can retrieve definition and status. No dependency on this temporary folder,
   a long-running shell, a Mac, a remembered tool handle or a private checkpoint.
4. Set a second existing health watcher to flag two missed attempts (>25 min),
   failed publication/deployment or a cover/DACS health regression. Avoid duplicate
   alerts. Root must arrange it; this script cannot schedule anything.

## Handover sequence

1. Freeze new automatic publisher starts (`shadow`). Obtain latest repository
   head and native workflow run list, including queued, waiting and in-progress.
2. Commit removal of native `schedule` and feed/briefing `push` triggers, leaving
   `workflow_dispatch` as a documented **manual recovery only** route. Do not
   change collector logic, sanitization or Pages publishing. Save exact previous
   workflow blob and commit for rollback, not the whole repository snapshot.
3. Read back workflow and confirm auto triggers removed. Drain ALL existing native
   runs; a queued run can contain the old workflow definition. Do not publish until
   none remain. Do not cancel a running publication blindly.
4. Activate automation publishing immediately and run its first collection from a
   fresh repository baseline. Bound collection at 240 seconds. If startup or
   collection cannot begin, restore native triggers without waiting for next tick
   and report failure; do not describe handover as completed.
5. Verify repository publication, Pages run and live content for this first write.
   Require a second independently scheduled successful publication before declaring
   operational. Record both attempt and deployment timestamps. Ten-minute checks
   are best-effort, not a service-level guarantee.
6. Keep manual recovery available, but pause automation before dispatching it,
   drain any automation candidate, then resume from a fresh baseline afterward.

## Instructions to save in the ten-minute automation

- Preserve existing document alerts and current expiry. Public output is only the
  sanitized official DACS projection. Do not publish alert ledgers, raw metadata,
  private E3G/ICPH material, tokens or internal notes. Cover consultations remain
  separately degraded unless independently verified; do not imply DACS covers them.
- On each wake read the saved definition/version as required. Check enabled mode
  (`shadow` vs `publish`). Read current native workflow and active native runs.
  In `publish`, abort and report if native auto triggers are present or any native
  job is queued/running/waiting. Never have two intended automated writers.
- Fetch `data/negotiating-texts.json` from **repository main**, not the website, using
  the connector and retain its blob SHA. Materialize complete exact bytes; verify
  `git hash-object` matches the fetched SHA. A truncated tool excerpt is not a
  baseline. Public clone/raw data pinned to the verified commit is an alternative.
- Skip collection when canonical last_attempt is less than 8 minutes old; do not
  skip merely because last_success is old. Never advance a timestamp by hand.
- Load collector and guard from reviewed canonical repository code. Execute the
  collector with a fresh temporary private checkpoint, `--restore-public` pointing
  to those exact baseline bytes, and output in a nonserved temporary directory.
  Enforce 240-second process limit; do not overlap or leave it running. If the cap
  kills the process, do not manufacture success or publish a partial file.
- Run `document_publish_guard.py --baseline BASE --expected-blob SHA --candidate OUT`.
  A source failure may publish `degraded:true` only while preserving the entire
  last-good catalog and last_success. An invalid schema, coverage gap, clock issue
  or invalid PDF must never produce healthy output. Never infer withdrawal from
  absence; explicit DACS unpublished events remain required.
- In `shadow`, stop after recording the validation receipt privately.
- In `publish`, recheck native jobs, workflow mode and repository file blob after
  collection. If changed, discard candidate and retry from fresh data next wake;
  never substitute a newer SHA for an older candidate. This closes ordinary races;
  the final atomic expected-SHA write handles a race after the last read.
- Call GitHub update_file exactly once for `data/negotiating-texts.json`, branch
  `main`, complete candidate text, SHA captured before collection. Do not use force,
  unrelated tree replacement, whole-repository reset or broad staging. No private
  checkpoint is a tool argument. If lease fails, discard and defer, not blind retry.
- Verify returned commit and remote file blob equal the guard's candidate_blob.
  If result is uncertain, read the file once and compare. Matching candidate means
  accepted; original blob means not confirmed; other blob means concurrent change.
  Do not resend uncertain writes automatically.
- Verify `Publish Field Edition` run for resulting commit and live
  build-manifest/source_commit plus exact public JSON. A later legitimate data
  commit is acceptable only after verifying it contains this candidate or a newer
  successful catalog. Keep latest verified baseline. Do not say live on API receipt
  alone. If no Pages run appears or it fails, flag deployment health separately;
  the repository can be fresh while the website is stale.
- Update user only for genuine new/revised documents, material health problems,
  confirmed recovery, or necessary action. Do not send routine no-change checks.
- Stop at the saved COP monitoring expiry unless user extends it.

## Failure and race reasoning

An in-flight native worker could start after a preflight check. Disable automatic
triggers and drain queued native work first. A human manual dispatch after that
cannot be prohibited by the script; coordination plus double preflight reduces
risk. GitHub blob compare-and-swap rejects concurrent modifications. Native git
rebase cannot silently replace a same-file concurrent change without conflict;
never modify that behavior to favor a writer. Any observed manual run pauses the
automation until it completes. CAS is not a global distributed mutex.

## Rollback

1. Pause publishing mode, wait for any candidate/write to finish or confirm no write.
2. Re-read main and restore **only the previous workflow trigger configuration**
   with expected blob/lease. Preserve newer code/data and manual dispatch. Do not
   reset main, restore old data, or revert unrelated commits.
3. Verify trigger restoration, then use an available authenticated manual dispatch
   if immediate recovery is required. If unavailable, report it: restoring an
   already-unreliable native cron is not proof of freshness.
4. Keep health watcher active until a new successful collection and live deployment
   are verified. Do not claim rollback healthy merely because YAML was restored.
