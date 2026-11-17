# Original analysis: empty, gated infrastructure

The public `data/analysis.json` index starts empty. It contains no articles, private drafts, assumed bylines or editorial approvals. Existing third-party reporting/analysis in the monitoring feed is separate from this original-analysis product.

## Reuse, do not duplicate

Use the existing private intake, card and full-article workflow in `docs/editorial.md`. Keep complete working readouts, confidential strategy, permissions and provenance outside this public repository and its previews. A published article has one home at the classic route `#hoje/leitura/<article-id>`. This index references that id instead of copying its body. Future Today, Texts and topic teasers should link to the same home.

The Field Edition already displays approved community-card teasers and links them to the classic article renderer. This sprint does **not** add a second renderer or expose this new index in the interface. Wiring the two formats into the interface remains a separate tested step once an editor clears an initial public entry. No automated collector should write this index.

## Index contract

Top-level fields: `schema: 1`, `entries: []`.

Each entry has `article` (existing canonical article id) and `format`:

- `daily-diplomacy-brief`: also requires `reporting_date` (YYYY-MM-DD).
- `text-explained`: also requires `document` and `comparison`.

A document reference contains the official UNFCCC HTTPS `url` (unfccc.int, www.unfccc.int or docs.unfccc.int), exact `version_label`, timezone-aware `reviewed_at`, and `sha256` of the verified document bytes. A challenge page returned with HTTP 200 is not document verification. Mutable URLs without a successfully retrieved and verified document fingerprint must remain private draft work.

`comparison` is either `{"status":"not_assessed"}` or has `status: "compared"` plus a `baseline` with the same document-reference fields. Both reviewed and baseline URLs must appear among the article’s verified public sources. Do not call a provision new, removed or changed without comparing the identified baseline.

Optional `superseded_by` references another approved indexed article. Unknown targets, self-links and cycles are rejected. Do not point readers to an unpublished replacement. An editor must recheck the source before release and mark an analysis superseded when its reviewed text is replaced; the ten-minute collector does not make that editorial determination automatically.

## Release gate

`tools/validate_analysis.py`, called by the existing CI/pre-commit public-content gate, requires:

- A valid published canonical article passing the existing article validator.
- Explicit editor approval with a timezone-aware timestamp.
- Explicit cleared attribution and a verified public source.
- Format-specific date/version metadata and valid supersession references.
- No body, draft, unknown or private fields in the index.

These checks validate the recorded state; they cannot supply actual consent or prove an editor reviewed a source. Never invent approval, a byline or institutional endorsement. An editor must separately clear confidentiality, attribution, factual support, translations and publication. Passing a test is not release authorization.

Run `python3 -I tools/validate_analysis.py`, `python3 -I tools/check_public.py` and `python3 -I -m unittest discover -s tests`. Synthetic tests do not represent approved real articles.
