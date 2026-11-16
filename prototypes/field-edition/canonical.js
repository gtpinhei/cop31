/* Conservative record identity. A URL may be only an account/profile landing page.
   Distinct source IDs are never collapsed based on URL or similar text. */
function canonicalPulseItems(items) {
  const records = new Map();
  items.forEach((item, index) => {
    // Stable source identity plus content evidence protects against reused IDs.
    // Missing source IDs cannot safely establish duplicate identity.
    const key = item.id ? JSON.stringify([
      item.kind || 'publication', item.platform || '', item.source_id || '',
      item.id, item.url || '', item.account || item.author || '',
      item.date || item.published || '', item.time || '',
      item.text || '', item.title || '', item.summary || '', item.description || ''
    ]) : `unidentified-observation:${index}`;
    if (!records.has(key)) records.set(key, {...item, variants: []});
    const record = records.get(key);
    record.variants.push(item);
    record.tracks = [...new Set([...(record.tracks || []), ...(item.tracks || [])])];
  });
  return [...records.values()];
}
if (typeof module !== 'undefined' && module.exports) module.exports = {canonicalPulseItems};
