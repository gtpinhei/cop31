const assert=require('assert'),{canonicalPulseItems}=require('./canonical.js'),feed=require('./feed.json');
const post={id:'post-a',kind:'post',platform:'x',source_id:'source',account:'author',url:'https://x.com/author',date:'2026-11-16',text:'First post',tracks:['Finance']};
// Profile links, similar content, missing IDs, reused IDs and differing platforms must not imply sameness.
for(const other of [
 {...post,id:'post-b',text:'Another post'},
 {...post,id:'post-b'},
 {...post,text:'Edited/reused ID, distinct content'},
 {...post,platform:'bluesky'},
 {...post,date:'2026-11-15'}
]) assert.equal(canonicalPulseItems([post,other]).length,2);
assert.equal(canonicalPulseItems([{...post,id:undefined},{...post,id:undefined}]).length,2);
const dup=canonicalPulseItems([post,{...post,first_seen:'later',tracks:['Adaptation']}]);
assert.equal(dup.length,1);assert.equal(dup[0].variants.length,2);assert.deepEqual(dup[0].tracks,['Finance','Adaptation']);
const rows=canonicalPulseItems(feed.items);
assert.equal(rows.length,810);assert.equal(rows.flatMap(x=>x.variants).length,810);
for(const url of ['https://x.com/turkiyecop31','https://x.com/murat_kurum','https://x.com/MuratKurum']){
 const input=feed.items.filter(x=>x.url===url),output=rows.filter(x=>x.url===url);
 assert.equal(output.length,input.length);console.log(url,input.length,'preserved');
}
for(const x of feed.items)assert(rows.some(y=>y.variants.includes(x)));
console.log('PASS: all 810 records preserved; profile URLs, source IDs, reused IDs, platforms, missing IDs, duplicate provenance and track union');
