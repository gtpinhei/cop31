# Official negotiating-text collection

`documents-producer.yml` remains the only DACS collector/publisher. It runs on
best-effort ten-minute GitHub schedules, explicit manual dispatch, and changes
to the broader public feed or briefing on main. The latter is a recovery path
when schedule delivery is delayed, not a substitute for a ten-minute service.
Changes to `data/negotiating-texts.json` do not trigger the producer, avoiding a
self-triggering loop. Collector concurrency remains serialized and the Pages
workflow remains the sole deployment owner.

## Certification

A workflow file or successful manual run is not evidence of an autonomous
schedule. Certify only after observing at least two unattended `schedule` runs,
then their successful Pages deployments and fresh public `last_success` values.
If the cron has not fired, report it as unverified even when push recovery works.
The build manifest explicitly makes no runtime scheduler/deployment assertion.

The UI's stale warning is based on collection success, not page-load time.
DACS coverage excludes Presidency pages that publish outside the catalog.
Do not describe a failed/challenged PDF fetch as an unchanged document.

## Further recovery

If scheduled events remain absent, use a separately approved durable timer to
**dispatch this workflow**, not a second collector or Pages publisher. Verify
an existing cloud project and scoped secret store first. Do not introduce broad
credentials, paid resources, or recurring heartbeat commits as a workaround.
At cutover remove the duplicate native schedule and verify slot deduplication.
