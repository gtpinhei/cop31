# COP30 Presidency Daily Brief

Registry source `cop30-presidency-daily-brief` (COP30 Presidency, official institutional briefing, priority A, EN + PT,
every 3 hours during COP31). It is collected by `tools/cop30_brief.py`, run from the hourly sync, and never by the web or
social agents (the web agent's view does not list it).

## Where it comes from

| | English | Portuguese |
|---|---|---|
| Index | https://cop30.br/en/news-about-cop30/daily-brief | https://cop30.br/pt-br/noticias-da-cop30/boletim-diario |

Both pages are Plone 6 (Volto). Their HTML only shows "Loading" / "Carregando"; the listing is drawn by JavaScript. The
site's own REST API serves the same content as JSON when the path is prefixed with `++api++`, and
https://cop30.br/robots.txt allows every agent. Discovery therefore uses the API, never the rendered page:

- **Discovery**: `++api++<index>/@search?portal_type=News Item&sort_on=effective&sort_order=descending&b_size=30` with the
  `effective`, `modified`, `created` and `UID` metadata, one call per language.
- **Edition**: `++api++<edition URL>`: title, description, `effective` (publication) and `modified` dates and the page's
  blocks (headline, thematic focus, lead, key moments with time, room and livestream, day-in-review, official links).
- **Pairing**: `++api++<EN edition>/@translations` gives the PT version's URL; same-day matching is only a fallback.

Fetch with the agents' method (Nimble extract, driver vx6, plain text). The script itself makes no network calls.

The same folders also hold the 2025 COP30 Morning Briefs, Evening Summaries and Belém Summit briefs. Their `modified`
date is in 2026 (they were moved), so the series is recognised by each document's own **effective** date: only News
Items effective on or after 2026-11-01 belong to it. Slugs are never used to tell the year.

## One run (hourly sync, step 3b)

```
python3 -I tools/cop30_brief.py plan                 # due? (every ~3 h) and the two discovery URLs
python3 -I tools/cop30_brief.py discover EN.json PT.json
python3 -I tools/cop30_brief.py collect <edition and @translations responses>
python3 -I tools/cop30_brief.py emit --summaries S.json --out /tmp/cop30/items.json
python3 -I tools/merge_feed.py /tmp/cop30/items.json
```

`collect` writes `needs_summary.json` (private) with the extracted facts of new or revised editions. The monitor writes the
Portuguese summary and its six translations in its own words, attributed to the Presidency, as for every other item.
`emit` without summaries still produces link-only items; summaries added later fill them in.

## What is published

One feed item per edition (`id` = `cop30-presidency-daily-brief-YYYY-MM-DD`, from the effective date in Antalya time):
title with the brief's own headline, the date, `url` (English) and `url_i18n` (EN + PT; the page links the reader's
language), `title_i18n.pt`, tracks, the monitor's summary and translations, `published_at`, `source_modified_at` and
`revision`. Never the brief's own paragraphs, event descriptions or images.

## Revisions and human assessments

Each language version keeps a SHA-256 of its body. A metadata-only change (new `modified`, same text) is recorded
without a revision. A text change increments `revision`, records what changed (headline, events, length) and sets
`updated_at` so the feed item is replaced in place (merge_feed keys on URL and, for a changed slug, on id). If an editor
changed the published item after the collector last wrote it, the collector does not overwrite it: the edition is held
and flagged "source revised after an editor's change". Human-approved Today cards and readouts are never touched.

## Review flags

Editions whose headline, focus, lead or day-in-review mention a roadmap, launch, pledge or commitment, declaration,
money figure, decision or agreement, or a new fund or initiative are flagged `pending` in the private state. The sync
tells the editor in one line. `python3 -I tools/cop30_brief.py review ID --by NAME [--note ...]` clears a flag; a later
text revision raises it again.

## Status and failure handling

`status` prints discovery and collection status separately, with each edition's URLs, dates, revision and flag. The
registry entry keeps `series.last_discovery_success` and `series.last_collection_success` apart, plus each edition's
canonical URLs, dates, revision and hash. A placeholder page, a non-JSON answer or an empty listing (when editions were
listed before) is an **error**, never "no editions": the last good listing is kept. An edition without an effective date
or with almost no body is reported as malformed and not published.
