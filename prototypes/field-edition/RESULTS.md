# COP31 Results

The Field Edition entry points are Today and Texts. The result links are stable fragments:
- `#texts/results`: selected outcomes.
- `#texts/results/next`: verified follow-up, filterable by workstream.
- `#texts/results/decision/<id>`: one outcome and its source.

The result cards are an editorial selection, not a projection of the negotiating-text feed. No new collector, schedule, or background requests are used. The data file contains public-source summaries and no excerpts from working registers or private briefings.

An outcome (adopted or not adopted) is different from the availability of an advance unedited or edited text. Do not infer non-adoption from an absent document: check a public record of the ruling. Do not interpret a carried-forward item as an extension of an existing mandate. Dates must come from the linked decision, not its draft or a calendar inference. In particular, the adaptation deadline dates and the “by August” dialogue are from paragraphs 4, 6, and 13 of the official advance unedited text linked in the card.

English and Brazilian Portuguese summaries are provided. In other Monitor languages the controls are localized and the English fallback is labelled and marked as English, including in the RTL layout.

From the repository root, after installing the existing tools package dependencies:
```sh
node prototypes/field-edition/results-test.cjs
node tools/build-field.cjs /tmp/cop31-results-review --release
node prototypes/field-edition/results-test.cjs /tmp/cop31-results-review
```
