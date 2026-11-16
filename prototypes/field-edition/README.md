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
