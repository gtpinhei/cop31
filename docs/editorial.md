# Hoje na COP31: editorial workflow

Nothing in `data/today.json` or `data/articles/` reaches the public page unless **all** of these hold:

- `status` is `published`;
- `approved_by` names the human who approved it, and `approved_at` is set;
- at least one source has `verified: true`, meaning the editor opened it and it supports the entry;
- every flag raised at intake is resolved by a named editor, and the contributor's permissions allow what is shown;
- all six translations (en, es, fr, ru, zh, ar) of the text fields exist, or the missing languages are listed in `i18n_pending` (readers of those languages then see the Portuguese original with a notice).

Drafts, submissions, original documents and evidence live in the **private store** (`../cop31-private`, or `$COP31_PRIVATE`), never in the repository. `data/today.json` and `data/articles/` may contain only published content with whitelisted fields (the validator, CI and the pre-commit hook enforce this). Enable the hook once per clone: `git config core.hooksPath tools/hooks`. If an old `editorial/drafts.json` exists, run `python3 -I tools/today.py migrate`.

To preview drafts: `python3 -I tools/preview.py` and open `http://127.0.0.1:8000/?preview=1#hoje`. The flag does nothing on the public site, and the public site has no drafts to show. Never put screenshots of drafts in the repository or a pull request.

## A. From a monitoring item

1. `python3 -I tools/today.py promote <feed-item-id>`: copies only what the feed holds and marks judgement fields `[preencher]`.
2. Fill the fields with `today.py set <id> <field> "<text>"` (headline, summary, what_happened, what_changed, why_it_matters, watch_next, open_questions, theme, classification, verification, event_at, basis.<field>). No JSON editing needed.
3. Translate and publish as in C.

## B. From a contribution (readout, analysis, meeting notes, field report)

Trusted contributors can be onboarded once with a standing profile (`tools/contributors.py`, see `docs/contributors.md`). Then `intake.py add FILE --title ... --profile SLUG` applies their byline choice. Publication and politically sensitive analysis are still approved per item. Run `today.py check ID` at any time to see what still blocks a card or readout; it writes nothing.

1. **Intake** (keeps a private copy, numbers the paragraphs, records permissions):
   ```sh
   python3 -I tools/intake.py add readout.docx --title "COP30 press briefing readout" --kind readout \
     --contributor "Name" --affiliation "Org" --role observer --event-date 2026-11-08 \
     --confidentiality public --attribute named|anonymous|ask --publish-analysis yes|no \
     [--anonymity-reason "..."] [--source-url https://official.document]
   ```
   Pasted text: `... add - --title ...` and paste on standard input.
2. **Extraction:** `python3 -I tools/intake.py prompt <submission-id>` writes `prompt.md` in the store. Ask the AI assistant to follow it and save its JSON answer; then `python3 -I tools/intake.py propose <submission-id> answer.json`. The importer rejects quotes that are not in the document, "verified" without an official source, and any field that claims more than its claims support. It creates one private draft card per development, a draft readout if proposed, and the flags to resolve.
3. **Review each card:** `today.py show <id>` lists fields, evidence labels, flags and cross-reference decisions. Check every field against the original. Fix with `today.py set`. Set the editorial priority with `today.py priority <id> lead|supporting`.
4. **Cross-references are manual and reasoned:** `today.py link <id> <feed-item-id> --reason "..." --by NAME` when a monitoring item describes the same development, or `today.py distinct <id> <feed-item-id> --reason "..." --by NAME` when it only shares the topic. Links proposed during extraction stay unconfirmed (flag `confirm_link`) until an editor decides; `intake.py related <id>` lists candidates, which are hints only.
5. **Attribution:** drafts can be prepared as named (`intake.py add ... --attribute ask --display-default named`), but nothing named is published until the contributor's authorization is recorded: `intake.py permissions <submission-id> --attribute named|anonymous [--publish-analysis yes|no] --by EDITOR` (logged with who and when). Anonymous needs an internal justification.
6. **First-hand accounts without a public URL** are allowed, but such a card needs its paragraph-level provenance (kept privately) and a recorded authorization, and can never carry "verified fact". Resolve each remaining flag with what you checked: `today.py resolve <id> <n> --by "Name" --note "..."`.

## C. Translate and publish

1. `today.py i18n-export <id>` (a card or a readout) writes the Portuguese fields to the store. Translate into each language with `i18n/glossary.md`, then `today.py i18n-import <id> <lang> <file> --method human|machine-reviewed|machine --by NAME`. For diplomatic analysis prefer `human` or `machine-reviewed`. If a language cannot be ready, publish with `--pending-langs ru,zh` (disclosed on the page).
2. `today.py publish <id> --by "Name" --verified-source N` (N = the source you opened). The command lists everything still blocking publication.
3. Readout (optional, after at least one of its cards is published and only with the contributor's permission): `today.py publish-article <article-id> --by "Name"`. The cards then link to it.
4. `python3 -I tools/validate_feed.py && python3 -I tools/check_public.py`, run the tests, commit `data/today.json` (and `data/articles/<id>.json`).

## D. Corrections and retractions

- `today.py correct <id> --by NAME --note "..." [--field what_happened --text "..."]`: public dated note; a changed field's translations become pending until re-imported (`i18n-import` works on published cards).
- `today.py retract <id> --by NAME --reason "..."`: removes the card (and its readout if no other card uses it) and leaves a public retraction notice; the record moves back to the private store.

Routine social posts stay in Pulso social; do not copy them here. AI-drafted text may be used as a starting point only inside a draft; the approver is responsible for every published sentence.
