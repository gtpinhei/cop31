# IA migration checkpoint

16 November 2026. Isolated review branch, not a production release. No merge of PR11/26, no private E3G or ICPH material, no editorial publication, no production push.

## Navigation and migration map

| Previous destination | New home | Treatment |
|---|---|---|
| #hoje | Today | Full briefing essential, negotiations, action and civil selections; duplicate lead URLs removed across the daily view. Related-source links retained. |
| #atualizacoes, #pulso | Pulse | Conservative source-record identity; All/Publications/Social, search, institution, topic, platform, account and date-range filters; pagination. |
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

Public live HTML, feed and briefing fetched on 16 November, not private documents. Source snapshots remain in the bundle. The feed contains **810 input records and 810 displayed records**. The initial URL-only grouping was rejected in independent review because profile fallback links are shared by distinct posts. Identity now requires the same source ID, record ID, platform, URL, author/account, publication date/time and content evidence. Distinct IDs and unidentified records are not collapsed. Exact repeated observations can share a display record while retaining every provenance observation and unioned topic labels. All 55 records linking to the Türkiye COP31 X profile and all 28 linking to Murat Kurum’s X profile remain independently visible.

All **341** inline Carbon Brief rows preserved in positions.json, including original English question/topic text. All **15** reference sections preserved in seven existing locale variants using the site's own hashed translation maps. External attribution and original dates remain. Metadata versions in Texts are explicitly not substantive document diffs; document catalogue snapshot is unchanged from the prior prototype and is not a live 10-minute feed.

## Tests actually run

- Existing baseline DOM suite: plain wordmark, seven language shell renders/Arabic direction, document filters/reset/pagination/theme and official PDF links.
- New migration DOM suite: complete daily sections, 810 preserved feed items/810 source records, social filter and pagination, 341 positions/actor filter/reset, all 15 retained-section aliases, seven reference locale loads, Arabic RTL and no media embeds.
- Adversarial canonicalization tests: shared profile URLs, distinct IDs with identical text, reused IDs with changed content, different platforms/dates, missing IDs, true repeated observations and provenance preservation. All 810 input records are represented.
- Locale regression suite: all 33 IA labels exist in all seven locales; Civil society differs from Social; rendered controls, reference warnings and archive labels use the selected locale.
- Lazy data requests only; no timers or repeated background polling.

## Remaining release gates, not claims of completion

- Browser rendering/mobile layout, keyboard and screen-reader checks still need real-browser QA. DOM tests are not accessibility certification.
- All 33 newly introduced IA labels now have explicit translations in all seven locales, with no English fallback. Civil society is correctly distinguished from social-media posts. Reference warnings, Pulse controls/eyebrow and archive labels are localized. Fluent linguistic review remains required; existing reference translations are preserved, not independently verified.
- Some old contextual summaries overlap (especially Brazil/roadmap and actor synthesis). They are preserved deliberately rather than silently deleted; final editorial consolidation into canonical issue records remains pending. Top-level duplicated destinations are removed now. Shared profile links are correctly retained as distinct posts.
- Canonical feed records merge only repeated observations with matching stable identity and content evidence, retaining variant provenance. Distinct record IDs remain separate even when URLs coincide.
- Positions search/filter works, but the previous actors-by-position aggregate visual is not recreated yet. Calendar is retained as reference, not live scheduling.
- Arbitrary nested anchors belonging to generated old feed rows cannot resolve if they were never present in public HTML; original section anchors and static reference anchors are supported.
- Private original analysis has a future home under Topics / Analysis & evidence, but no new analytical content has been imported or published. Further briefs require editorial authorization.
- Backend 10-minute UNFCCC feed integration, document comparisons/withdrawals/adoption verification, health alerting and staging/production deployment remain separate work. The preview never implies live monitoring.

## Reproducibility

`build-migration.cjs` extracts public reference sections and the 341-row dataset from `source-public.html`, sanitizes executable elements/handlers and builds locale assets using the original site's translation mechanism. Requires repository development jsdom. `migration-test.cjs` verifies the isolated prototype. No production files changed.

### Explore readability pass (16 November)
- Prose is limited to 68 characters of approximate measure, with increased leading and explicit heading/list spacing. Tables retain their comparisons and scroll within their own container; cards become one column on small screens.
- The especially dense think-tank report introduction has three semantic bullets for its three tests, followed by separate thematic paragraphs. Editorial boundary phrases are specified for all seven languages; no automatic sentence splitting or new claims are used.
- `readability.cjs` is included in asset generation. `node prototypes/field-edition/readability-test.cjs` verifies exact character preservation, links/anchors, reproducibility and idempotence against the pre-readability commit across 105 sections.
- Existing functional, migration, canonical-record and locale suites pass. This is structural/CSS QA, not a claim of completed real-browser visual or assistive-technology testing. No live-site deployment is included.
