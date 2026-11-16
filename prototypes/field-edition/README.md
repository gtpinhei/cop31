# Field Edition review prototype

**Not production-ready. Not deployed.** Standalone implementation of the approved design direction. Run `python3 -m http.server 8765 --directory prototypes/field-edition` and open `http://localhost:8765`.

## Scope
- Plain typographic COP31 Monitor wordmark, no C31 box, logo mark or replacement image. Bidi isolation preserves brand order in RTL.
- Field Edition editorial identity, compact mobile cards and a document-first Texts workspace.
- Today, Texts, Pulse, Explore navigation; optional light/dark; seven interface languages; RTL direction and logical CSS.
- Real public source snapshots, with saved-check timestamps and explicit non-live banner. No simulated continuously updated data, invented comparisons, adoption claims or private intelligence.
- Search/body filters, progressive 20-document pagination, official PDF links. Standing, change and metadata-version fields separate. No previous PDF exists in this snapshot, so version comparison is explicitly unavailable.
- Static system fonts, no images/embeds, no tracking, timers, background polling, animation or automatic PDF downloads. Three JSON reads on load; no further requests for navigation, filtering or theme/language changes.

## Data and integration boundary
`briefing.json` and `pulse.json` are reduced public live-site snapshots retrieved 16 November 2026; `documents.json` is derived from the official UNFCCC DACS baseline checked 16 November 09:13 UTC, retaining English attachments only. Titles remain in official source language. Interface translations are provisional and require fluent review.

This does **not** implement the collector. Integrate a validated, centrally published document feed after the PM's ingestion work is ready. Do not make every visitor query UNFCCC. Preserve independent per-source freshness and failure states. Never infer substantive revisions from metadata versions alone.

## Verification
`node --check prototypes/field-edition/app.js` passed.
`node prototypes/field-edition/test.cjs` uses repository tools/jsdom: seven-language rerenders, RTL flag, filters, reset, pagination, theme repeat toggles, navigation, official links and exactly three initial fetches passed.
Repository public-safety and feed validators passed (existing unrelated feed warnings).

Headless Chromium could not start in this executor: `socket() failed: Operation not permitted`, including one allowed elevated attempt. Thus responsive pixels, focus visibility, contrast, screen-reader semantics, real Arabic typography and CPU/device energy are **not verified**. There are no screenshots or claimed battery savings. The Playwright test in `browser-test.cjs` is ready for an environment with a functional browser. Production replacement must wait for these checks.

## Next checks
- Verify 390px/768px/1280px and long official titles in all languages; keyboard and screen reader.
- Test actual source-fetch failure, no-data, stale data and newly revised/withdrawn document states using the PM's schema.
- Native review of Arabic, Chinese and other interface translations; preserve source-language labels.
- Compare network and CPU activity against current production under identical tasks. File bytes are not power measurements.
- Keep existing PR11/26 holds and editorial governance; no deployment authorization inferred.

## IA migration review (16 November 2026)

This is a separate implementation checkpoint, **not deployed**. Open `index.html` through a static HTTP server. Current branch `prototype/ia-migration`. See `MIGRATION.md` for exact coverage and known gaps. `node migration-test.cjs` runs the DOM integration suite using the repository's development jsdom installation.

The prototype fetches full Pulse data only when Pulse is opened, and reference translations/positions only when needed. No polling, embeds, private briefings, subscriptions or analytics are enabled. The 10-minute collector belongs to the independent backend integration work, not this preview.

## Additive live-data integration candidate (not deployed)

`live-preview.html` uses `live-config.js` to read the repository's canonical public
`data/briefing.json` and `data/feed.json`. Serve the **repository root**, then open
`/prototypes/field-edition/live-preview.html`. Routine collector commits therefore
appear on page reload without copying fixtures, rebuilding the design or querying
UNFCCC from visitors' devices. `index.html` remains a self-contained frozen review.
Documents remain explicitly saved/uncompared, not a working ten-minute feed.

This entry is additive: it does not replace the production root or modify public data.
No changes to collectors, GitHub workflows, publication permissions or held PRs.
Latest-main comparison at 1786fdd found only feed and briefing data changed from local
base dc52cb7. Exact connector blobs were used for the integration run: 823 records,
16 November briefing. Those verification copies are not committed or shipped.

Run `node prototypes/field-edition/integration-test.cjs` against repository data.
For separately fetched exact-main fixtures named `data/*.json.latest`, run with
`COP31_DATA_FIXTURE_SUFFIX=.latest`. Existing five prototype suites also remain valid.

### Release gates still open
- Corrected real-browser mobile/RTL test (grid min-content, scrollable tables, dates).
- DACS collector deployment, actual schema/withdrawal/error handling and freshness.
- Preserve or explicitly replace global search, community-approved entries and
  live/on-demand social functionality before replacing production root.
- Full existing repository CI (known unrelated QA fixture failure is not waived).
- Production swap must refresh current remote and preserve concurrent collector data.

Mobile containment fixes avoid hiding document overflow at body level: tables scroll
locally; grid children may shrink; undated/invalid dates sort after dated documents.
Pulse provenance dates are localized and explicitly bidi-isolated.

## Functional retention stage

The shell now includes native submit-triggered global search across public feed,
document metadata, reference sections and approved community entries. Public community
cards use the original published + approval + verified-source gate; corrections remain
visible and the full context opens in the preserved classic application. Private draft
routes are never fetched by the new shell, even on localhost. Search does not poll.

Pulse includes a clearly labelled link to the existing live Bluesky/on-demand platform
tools. Those tools are not iframed or preloaded. Their existing controls and safeguards
remain in the unchanged classic application, including full readouts and newsletter
behaviour. This is intentional transitional access, not a claim of native feature parity.

`node tools/build-field.cjs /absolute/new/staging-directory` makes an isolated candidate:
new shell at index.html, byte-identical old index at classic.html, current canonical
public data and seven-language resources. It refuses to overwrite an existing output,
runs public/feed validators, and records hashes. It does not publish, modify root,
change a collector, or install a deployment workflow. Existing data updates must trigger
this build in the final publishing pipeline; do not deploy a one-off snapshot and claim
it stays current. Saved document catalog remains explicitly non-live.

`retention-test.cjs` covers all seven interface locales, global search, Close, approved
versus draft/unapproved content, correction visibility and absence of private fetches
or embedded platforms. Real-browser checks must be repeated on this changed shell.

## Document-feed adapter stage

`document-health.js` and the loader accept the normalized collector contract:
`last_success`, `last_attempt`, `degraded`, `documents`, `changes`. Metadata fields
`document_code`, `published_at`, `metadata_version`, attachment language/URL and
`source_url` map to the shell without inventing political status or comparisons.
Withdrawn records do not appear as active documents; withdrawal totals remain visible.
PDF links are distinguished from source-record links. Last-success/attempt and degraded
states are translated in seven languages. Visitors only fetch the site's public JSON,
once on opening or by explicit Refresh; they never call UNFCCC or start background polls.

No `documents` override is enabled by default: the catalog remains explicitly saved
until the validated producer and deployment configuration are connected. Initial feed
failure no longer blanks Today, and manual refresh failure keeps the last valid catalog.
`document-health-test.cjs` covers schema mapping, withdrawals, seven locales, failure,
recovery and the no-visitor-polling boundary. Scheduler/production remain separate gates.
