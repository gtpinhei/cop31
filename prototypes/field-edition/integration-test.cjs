const fs=require('fs'),assert=require('assert'),{JSDOM}=require('../../tools/node_modules/jsdom');
(async()=>{
const w=new JSDOM(fs.readFileSync(__dirname+'/live-preview.html','utf8'),{url:'https://test.test/prototypes/field-edition/live-preview.html',runScripts:'outside-only'}).window;
const calls=[], suffix=process.env.COP31_DATA_FIXTURE_SUFFIX||'';
w.fetch=async u=>{calls.push(u);const file=u.startsWith('../../data/')?__dirname+'/'+u+suffix:__dirname+'/'+u;return {ok:true,json:async()=>JSON.parse(fs.readFileSync(file,'utf8'))}};
w.eval(['live-config.js','app.js','canonical.js','migration.js'].map(f=>fs.readFileSync(__dirname+'/'+f,'utf8')).join('\n'));
const tick=()=>new Promise(r=>setTimeout(r,25));await tick();
assert(!w.document.getElementById('error').hidden===false);
assert(w.document.getElementById('edition').textContent.includes(JSON.parse(fs.readFileSync(__dirname+'/../../data/briefing.json'+suffix)).edition));
assert(calls.includes('../../data/briefing.json'));assert(!calls.includes('briefing.json'));
w.location.hash='#pulse';w.dispatchEvent(new w.Event('hashchange'));await tick();
const feed=JSON.parse(fs.readFileSync(__dirname+'/../../data/feed.json'+suffix));
assert(w.document.getElementById('pulse-count').textContent.includes('/ '+feed.items.length));
assert(!calls.includes('feed.json'));assert(w.document.querySelector('#feed-list details bdi'));
for(const language of ['en','pt','es','fr','ru','zh','ar']){
w.document.getElementById('language').value=language;w.document.getElementById('language').dispatchEvent(new w.Event('change'));await tick();assert(!w.document.body.textContent.includes('Invalid Date'));
}
w.eval(`{
const test=[{published:null},{published:'2026-11-15T12:00:00Z'},{published:undefined},{published:'2026-11-16T12:00:00Z'},{published:'invalid'}].sort(newestDocument);
if(test[0].published!=='2026-11-16T12:00:00Z'||test[1].published!=='2026-11-15T12:00:00Z')throw Error('undated sort');
if(date('bad')!=='—')throw Error('invalid date');
}`);
assert(!w.document.querySelector('iframe,img,video'));
assert(!fs.readFileSync(__dirname+'/live-config.js','utf8').includes('unfccc.int'));
console.log('PASS: canonical briefing + '+feed.items.length+' feed records, canonical data paths, all 7 languages, invalid/undated dates last, bidi provenance, no embeds/source polling');w.close();
})().catch(e=>{console.error(e);process.exit(1)});
