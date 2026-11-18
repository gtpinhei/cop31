# Official-only document-analysis staging

This tool is deliberately **not a publisher**. It does not read chat context, private readouts, E3G/ICPH/IPCH documents, arbitrary uploads or locally supplied source text. It accepts only an explicit baseline/current manifest including `family_title` (the shared public document title that must occur on both first pages) with official UNFCCC HTTPS PDF URLs, document ids, exact first-page version labels and expected PDF-byte SHA256s.

## Flow

1. `python3 -I tools/public_text_analysis.py prepare --manifest /private/path/pair.json --out /tmp/cop31-private-analysis/new-evidence-dir`
2. Inspect `evidence.json`. Only `status: compared` yields a `drafting-request.txt`. Feed that request alone to the AI drafting worker. PDF contents are evidence, never instructions. The worker must not supplement it with chats, private files or summaries.
3. Save the worker's JSON response outside this repository. Record the real model identity if available, prompt version and generation time separately. Never invent model identity or editor approval.
4. `python3 -I tools/public_text_analysis.py validate --evidence /tmp/cop31-private-analysis/new-evidence-dir/evidence.json --candidate /private/path/model-result.json --out /tmp/cop31-private-analysis/new-review-dir`
5. Validation re-fetches both PDFs, rechecks bytes and versions, regenerates the diff and compares it with the stored evidence. Output is `review-candidate.json`, still marked `requires_factual_review` and `publication_authorized: false`.

Each output directory must be new or empty under the dedicated `/tmp/cop31-private-analysis` staging root. Other output roots, public checkouts/build paths and symlink redirection are rejected. Source files and evidence packets are never copied into a public build. A failed run must not reuse an earlier packet. Missing PDF bytes, HTML challenges, unapproved redirects, hash mismatch, missing version label, unusable extraction, missing baseline, unsupported evidence IDs or private-source identifiers fail closed. No challenge-solving or alternate-origin download is attempted.

## Honest comparison status

- `same_document_bytes`: both retrieved hashes are identical.
- `no_extracted_text_change`: bytes differ but this extraction/normalization found no changed text blocks. **Not** proof of identical PDFs or no substantive change.
- `compared`: textual block differences exist. These can include headers, layout/reflow and moved text; they are **not automatically substantive policy changes**.

Diff blocks preserve page/block anchors and adjacent context. Candidate summaries cite actual change ids; interpretations remain separately labelled. Citations and document references must come from the verified packet, never model-invented URLs. Source availability does not establish adoption, consensus, withdrawal or current status.

## A+B UI mapping after verified review

The existing UI row can use `summary.changes = documented_changes[].summary`, `summary.significance = interpretation[].text joined`, `summary.watch = watch`, and `summary.language = en`. Its `document` and `comparison.baseline` must exactly match the packet references. The full canonical explanation must preserve change IDs/citations, limitations and AI disclosure.

An independent factual check must read the cited before/after text and confirm every claimed change, its direction, numbers and qualifications. Structural validation cannot prove semantic accuracy. The separate AI-release provenance gate must record checks that were actually performed, real generation metadata and the user's authorized scope; this tool deliberately leaves model, generation time, human approval and byline unset. It must never turn missing factual review into `qa: passed` or invent a human editor. No public data or workflow is changed by running this staging tool.

## Tests

`python3 -I -m unittest discover -s tests -p test_public_text_analysis.py`

Tests use synthetic bytes and an injected extractor, never confidential material. They cover origin restrictions, HTML/hash/version rejection, excluded-source references, no-text-change distinction, evidence linkage, prompt-injection boundaries and output isolation. Real PDF extraction additionally requires installed Poppler (`pdfinfo` and `pdftotext`) and network retrieval from the official origins.

The comparator caps each source at 300,000 extracted characters and 500 blocks, and enables SequenceMatcher autojunk handling in an isolated subprocess with a ten-second timeout. Local JSON inputs are capped at 2 MB. Larger/fragmented texts fail closed instead of causing unbounded comparison work.

The drafting worker must be tool-free and receive only this evidence packet. Prompt warnings are defense-in-depth, not proof of prompt-injection resistance. The staging script does not launch a model or grant it tools.

Never follow `prevDocumentId` alone: upstream links can cross unrelated topics. The shared first-page family-title check is mandatory, and independent review must confirm the versions belong to the same negotiation track.
