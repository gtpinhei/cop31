# Standing contributor authorizations

Trusted contributors are onboarded once. Their standing profile records who they are, how they want to
be credited and what they allow by default. New submissions reuse it with `intake.py add --profile SLUG`,
so attribution does not have to be negotiated again for every readout.

Profiles live in the private store (`contributors.json`), never in the repository.

## What a profile settles once

| Decision | In the profile | Notes |
|---|---|---|
| Identity and provenance | name, role, how consent was given (`--consent`), who recorded it | Recorded with the editor's name and date |
| Byline | `named` or `anonymous` (with an internal reason) | `ask` is not allowed: a profile is a decision |
| Affiliation | shown or hidden (`--show-affiliation`, default hidden) | Avoids implying institutional endorsement |
| Routine analysis | standing consent (`--routine-analysis yes`) | Applies only to submissions the editor marks `--sensitivity routine` |

## What stays a per-item decision

- **Publication:** every card and readout is still approved by a named editor (`today.py publish --by`).
- **Politically sensitive analysis:** every submission is `sensitive` by default. Publishing its analysis
  needs `intake.py permissions SID --publish-analysis yes --by EDITOR` for that item.
- **Original documents:** never published from a profile.
- **Confidentiality and Chatham House:** set per submission, never by the profile.
- **Changes for one item:** `intake.py permissions` (for example, anonymity for one sensitive readout).

## Lifecycle

```
python3 -I tools/contributors.py register gustavo-pinheiro --name "Gustavo Pinheiro" --role author \
    --attribute named --consent "confirmed in writing on DATE" --by EDITOR
python3 -I tools/intake.py add readout.docx --title "..." --profile gustavo-pinheiro          # sensitive by default
python3 -I tools/today.py check CARD_ID ARTICLE_ID                                             # dry run of every gate
python3 -I tools/contributors.py update gustavo-pinheiro --show-affiliation yes --by EDITOR
python3 -I tools/contributors.py revoke gustavo-pinheiro --by EDITOR --reason "..."
```

Revoking a profile blocks publication of every unpublished draft that relied on it. Each blocked item
must be re-confirmed with `intake.py permissions` before it can be published.

Each submission keeps its own audit trail: the standing profile used, its grant date and every
per-item change (`permissions_history`).
