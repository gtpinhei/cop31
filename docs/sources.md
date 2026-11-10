# Source registry (V1.2)

One list of everything the monitoring agents watch: websites, RSS feeds and social accounts. Adding,
re-prioritising, pausing or retiring a source never requires editing an agent prompt or the site.

## Where things live

| What | Where | Who writes it |
|---|---|---|
| Canonical registry (`registry.json`, `history.jsonl`, batches, probes) | private store `sources/` (never in this repository) | `tools/sources.py` only |
| Durable mirror + agent views: `registry/sources.json`, `registry/social.json`, `registry/web.json` | private artifact "Navegador COP31" | the hourly sync |
| Agent run reports: `registry/status-social.json`, `registry/status-web.json` | same private artifact | each agent, in the same publish as `data/feed.json` |
| Editor dashboard | Project doc `claude/COP31 fontes — painel.md` | the hourly sync |
| Editor inbox | Project doc `claude/COP31 fontes — entrada.md` | the editor (one URL or handle per line) |
| Public Social Pulse list `data/pulse.json` | this repository | generated from the registry (active social accounts only, public fields only) |

`data/feed.json` holds collected outputs only and never carries registry data.

## Source record

Stable `id` (never reused), `platform` (web, rss, bluesky, x, instagram, youtube; linkedin, whatsapp and
other manual-only platforms are recorded but never collected), `handle` or `urls`, `institution`,
`category` (presidency, unfccc, government, multilateral, negotiating_group are official; research,
civil_society, media, journalist, business, individual, other), `themes` (the feed's tracks),
`priority` A/B/C, `collection` (agent, method, cadence), `status`, `rights`, `identity`
(status checked/reported/unverified, basis, evidence URL, when, by whom), `provenance`
(added when, by whom, from where), `decision` (last status change with its reason) and `health`.

Priority sets cadence: social A every run (hourly), B daily, C weekly; web A and B every run (6-hourly),
C daily. An editor can override the cadence per source.

## Lifecycle and rules

`proposed` (by an agent) → `pending_review` → `active` | `rejected`; `active` → `paused` | `retired`.

- **Activated automatically:** official category, identity checked, and a successful probe with the collector's own method.
- **Identity counts as checked when:**
  - a Bluesky domain handle resolves;
  - an official page links the account (the evidence URL is stored);
  - a website is on the institution's own domain.
- **Rejected with a documented reason:** invalid input, a duplicate (same handle or URL, including URL variants), a platform the agents cannot read, a source that does not exist (404, "profile not found"), or one that could only be read by circumventing a site's policy.
- **Everything else waits for the editor:**
  - unverified or third-party-reported identity;
  - non-official categories;
  - blocked or failed probes;
  - agent proposals.
- **Pausing:** a source unavailable in three consecutive agent runs is paused automatically.
- **Never:**
  - registration is never presented as monitoring; a source counts as collected only after an agent run reports `success` or `success_empty` for it;
  - a blocked or unavailable source is never reported as "nothing new";
  - content is never republished: `rights` is `link_and_summary` (summary, short quotes, link) or `link_only` (no quotes or post text, e.g. paywalls).

## Health

Every agent run reports one outcome per source in its view:

- `success`
- `success_empty` (read fine, nothing new)
- `blocked` (refusal, login wall, client_error)
- `unavailable` (does not exist)
- `error`
- `skipped` (not due, or over the run's budget)

The hourly sync folds the reports into each source's `health` (last attempt, last success, last outcome,
consecutive failures, newest item seen, last 36 runs). The dashboard counts active sources as
configured, attempted, never attempted, successful, blocked, unavailable and error. These are
separate numbers, never merged.

Each view entry carries `due`, computed at export from the source's cadence and the last agent read
(never-read sources are due; daily = not read in 23 h, weekly = 167 h). The agents follow `due` and do
not interpret cadence themselves. When a run's budget is short they read newly activated sources first,
then priority A, then the due sources read longest ago, so priority-B accounts rotate across runs.

### Coverage (`coverage`, `out/coverage.json`, dashboard section "Cobertura nas últimas 24 h")

Computed from agent runs only, never from registration probes, for active sources:

- state: `on_time` (last agent success within the cadence window: every run = 5 h social, 7 h web;
  daily = 26 h; weekly = 170 h), `overdue`, `never` (no agent attempt), or the failed outcome of the
  latest attempt (`blocked`, `unavailable`, `error`);
- `covered_24h`: a successful agent read within max(24 h, window); `coverage_24h` is the share of
  active sources covered, overall and per priority;
- operational success (`checks_24h`, `ok_checks_24h`) is kept apart from intelligence produced
  (`new_items_24h`, `sources_with_new_items_24h`): a source read fine with nothing relevant is
  healthy but produced nothing;
- per source: `last_success`, `last_item_date`.

`set A distinct_from B` records that an editor confirmed two similar sources (same institution and
platform, or same domain) are separate identities, which clears the near-duplicate warning.

## Workflows

**Batch add** (from chat, or lines written into the inbox doc):

```
https://bsky.app/profile/example.org | category=multilateral | priority=B | themes=Finanças
x:SomeMinister | institution=Ministry of X | category=government | priority=A
https://example.org/feed/ | category=media | rights=link_only
```

```
python3 -I tools/sources.py plan batch.txt --by EDITOR > plan.json     # parse, dedupe, what to probe
# probe each "probe" line with its probe spec (Nimble/WebFetch, the agents' own method) → probes.json
python3 -I tools/sources.py apply plan.json probes.json --by EDITOR    # identity + activation rules
python3 -I tools/sources.py export OUT --pulse data/pulse.json         # views, report, Social Pulse
```

**Decisions:**

```
python3 -I tools/sources.py approve ID --by EDITOR
python3 -I tools/sources.py reject ID --reason "..." --by EDITOR
python3 -I tools/sources.py pause|retire ID --reason "..." --by EDITOR
python3 -I tools/sources.py set ID priority|themes|category|rights|cadence|urls|identity|distinct_from VALUE --by EDITOR
```

**Hourly sync:** read both status files from the artifact, `sources.py ingest` them, process the inbox,
`sources.py export`, then republish the changed views, commit `data/pulse.json` if it changed, and
refresh the dashboard doc.

## Rollback

The legacy watchlists (`claude/COP31 watchlist.json`, `claude/COP31 social watchlist.json`) are left
untouched in the Project. To roll back, point step 1 of each agent prompt back at its watchlist and drop
the status-file step (4d/5d); the feed format is unchanged.

## Sources with their own collector

Some series need a collector of their own instead of the generic web agent. They keep `collection.agent` set to that
collector, are left out of the web agent's view, and report their health to the registry directly. Cadence `every_3h`
(due after 2 h 45 min, on time within 4 h) is available for them.

- `cop30-presidency-daily-brief` — `tools/cop30_brief.py`, see [cop30-brief.md](cop30-brief.md).
