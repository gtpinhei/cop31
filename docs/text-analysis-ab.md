# Version-specific text analysis (A+B)

A concise **What changed / Why it matters** card links to the existing canonical article route for the same reviewed version. The full article has **What to watch**, exact reviewed PDF, comparison baseline, status, version history and a return link. There is no second article body or duplicate collection pipeline.

## Identity and lifecycle

Inline summaries require a stable document `id`, exact attachment URL and matching **PDF-byte** SHA256. Extracted-text fingerprints are not interchangeable with byte hashes. A URL alone never attaches an analysis to a current card. Missing or changed hashes suppress inline summaries.

The public catalog supplies current withdrawal status. A stored withdrawal or replacement warning is never erased by an unavailable catalog. Current status requires a successful catalog check within 20 minutes; a failed/degraded/stale catalog means **current status unverified**. This is catalog status, not adoption or legal effect. The canonical page remains a historical explanation, not an assertion that its version remains current.

`summary` contains 1–5 `changes` strings, `significance`, `watch` and an explicit original `language`. These are public release metadata, not a draft container. `lifecycle` contains `status`, `checked_at` and a verified exact `replacement` only when replaced. Original-language summaries are visibly labeled when the UI language differs.

## Separate release modes

1. Existing human-reviewed articles retain their named/anonymous contributor rules and explicit `approved_by` / `approved_at` gate.
2. AI document comparisons use `ai_provenance` with `mode: public-unfccc-diff`, exact before/after input identities, model and prompt version, generation timestamp and recorded automated evidence checks. Authorship is **COP31 Monitor AI**, role `analyst`. They cannot contain `approved_by` or `approved_at`, because automated checks are not human editorial approval. The authorization identifier records the owner's 18 November 2026 instruction allowing AI analysis of public UNFCCC document changes; it is not a credential.

AI release is limited to comparisons of two verified official public UNFCCC PDFs. All source URLs must be official HTTPS, all versions require verified byte hashes, and the index must bind to those exact input versions. E3G and ICPH documents and private chat/readout material are not input sources. No private drafts belong in this repository, build output, previews or generation pipeline.

The schema gates are **structural checks, not proof that evidence was reviewed**. The producer must genuinely execute the checks it reports. Independent implementation/pipeline review is required before deployment. Real content must not be fabricated to populate an empty page.

## Acceptance cases (synthetic fixtures only)

- A previously alerted document later withdrawn must show a withdrawal warning on its historical explanation and must not remain in the active feed.
- A replacement record with the same extracted text but different PDF bytes retains both identities and replacement lineage. It must not generate invented substantive changes or claim identical files.
- Same URL with new bytes must not inherit the old inline summary.
- Empty/unapproved/malformed content fails closed; broken navigation, repeated rendering, locales/RTL and slow navigation cancellation are tested.

## Checks

Run `python3 -I -m unittest discover -s tests`, public-data gates, and the Field Edition tests in `.github/workflows/field-pages.yml`. The A+B and AI mode tests also run in main PR CI. Public `data/analysis.json` remains empty until a genuinely verified release packet is available. No scheduler or negotiating-feed data is changed by this feature.
