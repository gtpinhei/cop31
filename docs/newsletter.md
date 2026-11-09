# Newsletter, subscriptions and distribution (V1.2)

Status: **phase 1 built behind a switch, collection not active.** The repository ships with
`data/newsletter.json` set to `"mode": "off"`, so nothing appears on the public site. No personal
data is collected until the open decisions at the end of this document have been made.

## What is built

- A compact signup on Hoje na COP31, Panorama and Atualizações, a full page (`#newsletter`) and a privacy notice
  (`#privacidade`), in the seven languages of the site.
- Email is the only required field. Name, organization, country, role and the edition language are optional.
  The edition language follows the site language until the reader changes it.
- Preferences: daily COP briefing (`briefing-diario`), weekly implementation digest (`resumo-semanal`) and
  major-development alerts (shown, disabled, "em breve").
- Three modes, set in `data/newsletter.json` (public configuration, never subscriber data):
  - `off`: nothing is shown and `#newsletter` and `#privacidade` fall back to Panorama.
  - `preview`: the forms validate and answer, but nothing leaves the browser. The form controls have no `name`
    attributes and the form has no `action`, so even a stray submit carries nothing.
  - `live`: only when `action` is a Buttondown embed endpoint, `processor`, `controller.name` and `controller.contact`
    are set and `privacy.status` is `final`. Anything less falls back to preview.
- In live mode the browser posts straight to the provider's public embed endpoint (no API key involved) and opens the
  provider's confirmation page. Double opt-in, unsubscribe and the subscriber portal are the provider's. Each signup
  carries tags (preferences and `lang-xx`), the optional fields as metadata, `metadata__source` (which section) and
  `metadata__consent_version` (the version of the privacy notice), which together with the provider's
  subscription and confirmation timestamps form the consent record.
- `tools/check_public.py` (CI) rejects any unexpected key in `data/newsletter.json` and blocks live mode while the
  privacy notice still says "a confirmar" or the controller, processor or final notice are missing.
- Tests: `tests/test_newsletter.mjs`.

Nothing about subscribers is stored on GitHub Pages, in the repository, in public JSON or in agent artifacts.
API credentials (needed only for phase 2) live in protected configuration outside the repository.

## Provider evaluation

Prices from published pricing pages as reported in November 2026; confirm on the provider's own page before
committing.

| | Buttondown | Brevo | beehiiv | listmonk + Amazon SES |
|---|---|---|---|---|
| Model | Indie, writer-first newsletter service (US) | EU email marketing platform (France) | Creator growth platform (US) | Self-hosted open source |
| Cost | Free ≤100 subscribers; $9/mo ≤1,000; $29 ≤5,000; $79 ≤10,000; some features are add-ons (tagging and segmentation reported at $29/mo) | Free 300 emails/day; Starter priced by monthly email volume (about $9 for 5,000, about $32 for 20,000) | Free ≤2,500 (API read only); Lite from $49/mo (1,000) after the October 2026 price change | Server plus about $0.10 per 1,000 emails |
| Static-site form without credentials | Yes: plain HTML form to `embed-subscribe` | Yes: hosted form endpoint | Embed widget | Yes, but needs our server |
| Double opt-in, unsubscribe, self-service preferences | Yes; Portal lets subscribers change metadata, tags, unsubscribe | Yes, on all plans | Yes | Yes |
| API and data portability | Full REST API, webhooks, CSV export | Full API, export | Write API gated to paid plans | Full control |
| Multilingual delivery | By tag segment (one send per language) | Native: one campaign, versions per language attribute | By segment | By list |
| Privacy | DPA with SCCs; data in the US; no ad networks | DPA; EU hosting | Ad network and recommendation network built in | Data where we host it |
| Fit for COP31 launch | Best | Good alternative | Poor fit for public infrastructure | Later, not during COP31 |

**Recommendation: Buttondown for launch during COP31**. It needs no backend: the static site posts to a public
endpoint, so nothing about subscribers or credentials touches our infrastructure. It handles double opt-in, the
subscriber portal (preferences, unsubscribe), CSV export and deletion, and has a full API for phase 2. Its business
model has no advertising or list-sharing component, and open and click tracking can be switched off. Expected cost
during COP31: $9/mo up to 1,000 subscribers, $29/mo up to 5,000, plus the segmentation add-on if per-language sends
require it (verify), so roughly **$9–58/mo**, about $0 if the list stays under 100.

**Alternative: Brevo**, if the data controller prefers EU hosting or one multilingual campaign over per-language
sends. It costs about the same at COP31 volume (daily sends to 1,000 subscribers over the conference are about 15,000
emails a month), but the free plan's 300 emails/day caps a daily briefing at 300 subscribers.

Not recommended: beehiiv (growth and advertising features we would have to switch off, write API on paid plans), and
self-hosting for now (deliverability and operations work during the conference). Self-hosting can be revisited after
COP31 if the list grows large.

## Phase 2 — editorial distribution (design)

1. `tools/newsletter.py draft DATE` builds the issue from what is already public: entries in `data/today.json` with
   `status: published` (approved by a person, verified source), plus a short "also in the feed" list from
   `data/feed.json`. Each block keeps its evidence label from the site (published fact, attributed reporting, analysis,
   unverified), so the distinction is never lost in email.
2. One draft per language from the entries' existing `i18n` fields; machine translations keep the "tradução
   automática" label. Drafts are written to the private store (`newsletter/drafts/DATE/<lang>.md`), never to the
   repository.
3. Editorial approval: `tools/newsletter.py approve DATE --by EDITOR` records who approved what. An issue with any
   block labelled analysis is never sent without it. Unapproved drafts are never sent.
4. Distribution: once approved, the tool creates one email per language through the provider API, addressed to the
   `briefing-diario` + `lang-xx` segment, scheduled for the agreed time. The API key is read from protected
   configuration (private store, mode 600, or the scheduled task's secret), never committed or placed in an artifact.
   This step can then run automatically for approved issues only.
5. Measurement, aggregated only: subscribers by status (unconfirmed, active, unsubscribed), confirmation rate,
   bounces and complaints, issues sent, per language and preference. Individual open and click tracking stays off.
   The figures go to a private dashboard, never to public JSON.

## Phase 3 — member space (design only, no login yet)

Public intelligence stays fully accessible without registration. A member space only makes sense once it offers
something the public site cannot:

- Saved topics and personal watchlists (tracks, actors, countries), first by email magic link, without passwords.
- Custom alerts built on the same tags (a track or actor of interest triggers an alert edition).
- Contributor profiles and authentication, extending the contributor model held in PR #11, with editor-assigned roles.
- Secure submission of original intelligence: authenticated upload to the private intake (`tools/intake.py`),
  provenance recorded, nothing published without editorial review.
- Institution workspaces: shared watchlists and notes for a team, with the institution as its own controller of what it
  adds.

Technical direction: a small backend (serverless functions plus a managed database in a jurisdiction chosen with the
controller), passwordless email login, provider subscribers linked by email only with the member's consent, and data
export and deletion from day one. Not to be built during COP31.

## Operating costs

| Item | During COP31 | After COP31 |
|---|---|---|
| Email provider | $0–58/mo depending on list size and add-ons | Same tiers; reassess at 5,000+ |
| Custom sending domain (optional, e.g. news.cop31.grupotrie.com.br) | DNS records only, no cost | — |
| Hosting | GitHub Pages, no change | — |
| Phase 2 tooling | Runs in the existing sessions | — |

No paid service has been contracted.

## Launch checklist

Decisions for the editor (blocking):

- [ ] Data controller: who is legally responsible (person or organization, address, privacy contact). This also
      decides whether the brand on emails is "Navegador COP31" alone.
- [ ] Provider approved (recommendation: Buttondown), and whether paid tiers may be used.
- [ ] International transfer basis for Brazilian subscribers if the provider is in the US: confirm the provider accepts
      the ANPD standard contractual clauses, or another LGPD art. 33 mechanism (legal review).
- [ ] Retention periods (unconfirmed, after unsubscribe), then remove every "a confirmar" from the privacy notice.
- [ ] Sending cadence and time for the daily briefing during COP31, and who approves each issue.

Technical, once those are settled:

- [ ] Create the provider account under the controller; switch on double opt-in; switch off open and click tracking;
      set the confirmation and welcome emails in the seven languages; create the tags `briefing-diario`,
      `resumo-semanal`, `lang-pt` … `lang-ar`; sign the DPA.
- [ ] Sending domain: SPF, DKIM and DMARC records for the sending address.
- [ ] Fill `data/newsletter.json` (`action`, `processor`, `controller`, `privacy.status: final`, `privacy.version`) and
      finalise the privacy notice; `tools/check_public.py` must pass.
- [ ] Test with a real address end to end: signup, confirmation email, portal (change language, unsubscribe), export
      and deletion request.
- [ ] Switch `mode` to `live`. Rollback: set `mode` back to `off` (one-line commit; the site hides everything).
