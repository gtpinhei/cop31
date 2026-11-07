You are translating UI strings and briefing text for the "Navegador COP31" website from Brazilian Portuguese into {LANGUAGE}.

Files (absolute paths):
- Input chunk: {IN}
- Glossary (read it first, follow it strictly): /home/claude/cop31/i18n/glossary.md
- Output: {OUT}

Steps:
1. Read the glossary, then read the input chunk. It is a JSON object: keys → Portuguese source strings (string or array of strings). Keys starting with "d:" are English data strings from a positions table (party/bloc names, topics, position wordings); translate those into {LANGUAGE} too, tersely, keeping acronyms. Keys starting with "j:" are interface strings used by scripts.
2. Write the output file with the Write tool: a JSON object with EXACTLY the same keys, each value translated into {LANGUAGE}. Arrays stay arrays of the same length and order.
3. Rules:
   - Keep every HTML tag, attribute (href, class, target, rel, etc.), URL and `{placeholder}` exactly as in the source. Translate only human-readable text.
   - Keep acronyms, institution names, publication titles and personal names as in the source (see glossary).
   - Translate country and group names into the UN standard form in {LANGUAGE}. "Türkiye" is the official UN name; use {LANGUAGE}'s UN form.
   - Register: concise, professional briefing for climate negotiators and journalists. Keep short UI strings short.
   - Do not add notes, alternatives, comments or extra keys. Do not drop keys. Escape quotes properly so the file is valid JSON (UTF-8, not ASCII-escaped).
4. After writing, re-read your output file once to confirm it is valid JSON with the same number of keys as the input; fix if not.
5. Reply with one line: the number of keys written. Nothing else.
