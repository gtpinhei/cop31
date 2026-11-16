# IA migration checkpoint

16 November 2026. Isolated review branch, not a production release. No merge of PR11/26, no private E3G or ICPH material, no editorial publication, no production push.

## Navigation and migration map

| Previous destination | New home | Treatment |
|---|---|---|
| #hoje | Today | Full briefing essential, negotiations, action and civil selections; duplicate lead URLs removed across the daily view. Related-source links retained. |
| #atualizacoes, #pulso | Pulse | One canonical URL record; All/Publications/Social, search, institution, topic, platform, account and date-range filters; pagination. |
| #mapa | Explore / Topics | Negotiating track framework, preserved source links. |
| #belem | Explore / Topics | Historical mandates and unresolved questions, saved-reference label. |
| #testes | Explore / Topics | Explicit E3G assessment-framework attribution, not an official verdict. |
| #thinktanks | Explore / Topics / Analysis & evidence | Full attributed dated source evidence retained; no separate publisher-type top-level destination. |
| #posicoes | Explore / Actors & positions | All 341 Carbon Brief positions, actor/topic/position/search filters, reset; original source/context and static synthesis retained separately. |
| #quem | Explore / Actors & positions | Actor roles alongside, not conflated with policy positions. |
| #agenda | Explore / Action & implementation | Retained, not represented as negotiated outcomes. |
| #brasil | Explore / Brazil dossier | Retained dossier and original contextual links. |
| #panorama, #terreno | Explore / Guide | Reference and practical material, saved-reference label. |
| #calendario | Explore / Calendar | Full original calendar retained. |
| #glossario | Explore / Glossary | Preserved definitions and links. |
| #radar | Explore / Archive | Explicit pre-COP 5–6 November label. |
| #fontes, #privacidade | Explore / Sources & method | Full original methodology/privacy context retained. |
| #newsletter | Explore / Sources & method | No signup enabled; operational delivery remains gated. |

Original section hash aliases and nested reference IDs route to their new home. These aliases work inside the prototype; production URL paths are deliberately unchanged and need deployment-level redirects only if paths change later.

## Evidence and preservation

Public live HTML, feed and briefing fetched on 16 November, not private documents. Source snapshots remain in the bundle. The feed contains **810 input records and 632 distinct URL keys**. Pulse renders one canonical item per URL; all original input records remain in feed.json, with per-record IDs, institution, date and collection time exposed under source details. Topic labels are unioned. No distinct URL was dropped.

All **341** inline Carbon Brief rows preserved in positions.json, including original English question/topic text. All **15** reference sections preserved in seven existing locale variants using the site's own hashed translation maps. External attribution and original dates remain. Metadata versions in Texts are explicitly not substantive document diffs; document catalogue snapshot is unchanged from the prior prototype and is not a live 10-minute feed.

## Tests actually run

- Existing baseline DOM suite: plain wordmark, seven language shell renders/Arabic direction, document filters/reset/pagination/theme and official PDF links.
- New migration DOM suite: complete daily sections, 632 canonical feed items/810 source records, social filter and pagination, 341 positions/actor filter/reset, all 15 retained-section aliases, seven reference locale loads, Arabic RTL and no media embeds.
- Lazy data requests only; no timers or repeated background polling.

## Remaining release gates, not claims of completion

- Browser rendering/mobile layout, keyboard and screen-reader checks still need real-browser QA. DOM tests are not accessibility certification.
- New controls beyond main destination/search labels still fall back to English in five locales; fluent review and complete UI translation remain required. Existing reference translations are preserved, not independently verified.
- Some old contextual summaries overlap (especially Brazil/roadmap and actor synthesis). They are preserved deliberately rather than silently deleted; final editorial consolidation into canonical issue records remains pending. Top-level duplicated destinations and duplicate feed URL cards are removed now.
- Canonical feed records use the first snapshot record as display text, retaining variant provenance; editorial choice of preferred rendition and unioning all variant classifications needs review.
- Positions search/filter works, but the previous actors-by-position aggregate visual is not recreated yet. Calendar is retained as reference, not live scheduling.
- Arbitrary nested anchors belonging to generated old feed rows cannot resolve if they were never present in public HTML; original section anchors and static reference anchors are supported.
- Private original analysis has a future home under Topics / Analysis & evidence, but no new analytical content has been imported or published. Further briefs require editorial authorization.
- Backend 10-minute UNFCCC feed integration, document comparisons/withdrawals/adoption verification, health alerting and staging/production deployment remain separate work. The preview never implies live monitoring.

## Reproducibility

`build-migration.cjs` extracts public reference sections and the 341-row dataset from `source-public.html`, sanitizes executable elements/handlers and builds locale assets using the original site's translation mechanism. Requires repository development jsdom. `migration-test.cjs` verifies the isolated prototype. No production files changed.
