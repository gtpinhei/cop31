# Hoje na COP31: editorial workflow

Nothing in `data/today.json` reaches the public page unless **all** of these hold:

- `status` is `published`;
- `approved_by` names the human who approved it, and `approved_at` is set;
- at least one source has `verified: true`, meaning the editor opened it and it supports the entry.

- all six translations (en, es, fr, ru, zh, ar) of headline, what happened, what changed, why it matters and what to watch exist, or the missing languages are listed in `i18n_pending` (readers of those languages then see the Portuguese original with a notice).

Drafts live in `editorial/drafts.json`, which is gitignored: they are never committed or deployed, and `data/today.json` may contain only published entries (the validator and CI enforce this). To preview drafts, serve the folder locally (`python3 -m http.server 8000`) and open `http://localhost:8000/?preview=1#hoje`; the flag does nothing on the public site. Keep a backup of drafts in the private Project doc "COP31 Hoje — rascunhos editoriais".

## Steps

1. Pick a monitoring item (Atualizações or the agent's push message) and promote it:
   `python3 -I tools/today.py promote <feed-item-id>`
   This copies only what the feed already holds (date, source, summary) and marks the judgement fields `[preencher]`.
2. Edit `data/today.json`: headline, theme (one of the 15 tracks), classification (`decisão`, `sinal político`, `anúncio`, `disputa`, `processo`, `análise`), verification (`confirmado`, `fonte única`, `não confirmado`), what changed, why it matters, what to watch. Add sources; open each one. If a social post only has a profile link, find the post URL first.
3. (see 4 for translations) Publish: `python3 -I tools/today.py publish <entry-id> --by "Gustavo Pinheiro" --verified-source 1`
   The command refuses while any field still says `[preencher]`/`[revisar]`, a translation is missing, or the validator fails. It moves the entry from the drafts file into `data/today.json`; commit that file to deploy.
4. Translations, before publishing: `tools/today.py i18n-export <entry-id>` writes the Portuguese fields to `editorial/i18n/<id>.pt.json`. Translate into each language (person, or a model followed by review, using `i18n/glossary.md`), then `tools/today.py i18n-import <entry-id> <lang> <file> --method human|machine-reviewed|machine --by NAME`. The page labels machine translations; `machine` (unreviewed) is allowed but disclosed, and for diplomatic analysis `human` or `machine-reviewed` is recommended. If a language cannot be ready in time, publish with `--pending-langs ru,zh`.
5. Corrections: edit the entry in `data/today.json` (all languages) and update `assessed_at`. To withdraw: `tools/today.py retract <entry-id> --by NAME --reason "..."` (removed from the public file, kept in the drafts file with the reason).
6. Run `python3 -I tools/validate_feed.py` and the tests, then commit.

Routine social posts stay in Pulso social; do not copy them here. AI-drafted analysis may be used as a starting point only inside a draft; the approver is responsible for every published sentence.
