const fs=require('fs'),assert=require('assert'),{JSDOM}=require('../../tools/node_modules/jsdom');
(async()=>{
const w=new JSDOM(fs.readFileSync(__dirname+'/index.html','utf8'),{url:'https://review.test/#texts',runScripts:'outside-only',pretendToBeVisual:true}).window;
let now=0,calls=0,hold=null,version=1,timers=new Map(),nextId=0,hidden=false;
w.Date.now=()=>now;w.scrollTo=(x,y)=>{w.savedScroll=[x,y]};
w.setTimeout=(fn,ms)=>{timers.set(++nextId,{fn,ms});return nextId};w.clearTimeout=id=>timers.delete(id);
Object.defineProperty(w.document,'visibilityState',{get:()=>hidden?'hidden':'visible'});
w.COP31_DATA={documents:'central.json'};
const feed=()=>({last_success:'2026-11-17T00:00:00Z',documents:[{id:1,title:'Finance '+version,body:'CMA',metadata_version:version,attachments:[]}]});
w.fetch=async u=>{if(u==='central.json'){calls++;if(hold)await hold;return {ok:true,json:async()=>feed()}}return {ok:true,json:async()=>JSON.parse(fs.readFileSync(__dirname+'/'+u))}};
w.eval(['app.js','document-health.js'].map(f=>fs.readFileSync(__dirname+'/'+f,'utf8')).join('\n')+';window.checkDocumentUpdates=checkDocumentUpdates;');
const tick=()=>new Promise(r=>setImmediate(r));await tick();assert.equal(calls,1);
const poll=()=>[...timers.values()].find(t=>t.ms===600000);assert(poll(),'ten-minute timer');
w.document.getElementById('search').value='Finance';w.document.getElementById('body').value='CMA';
hidden=true;w.document.dispatchEvent(new w.Event('visibilitychange'));assert.equal(timers.size,0,'hidden cancels timer');
now=600000;hidden=false;w.document.dispatchEvent(new w.Event('visibilitychange'));assert([...timers.values()].some(t=>t.ms===0));
version=2;let release;hold=new Promise(r=>release=r);
const auto=w.checkDocumentUpdates(),manual=w.checkDocumentUpdates();assert.equal(calls,2,'concurrent checks share request');release();await Promise.all([auto,manual]);hold=null;
assert(w.document.getElementById('documents').textContent.includes('Finance 1'),'no content replacement while reading');
assert(!w.document.getElementById('texts-status-updates').hidden,'update notice visible');
w.document.getElementById('texts-status-updates').firstChild.click();assert(w.document.getElementById('documents').textContent.includes('Finance 2'));assert.equal(calls,2,'apply reuses staged response');assert.equal(w.document.getElementById('search').value,'Finance');assert.equal(w.document.getElementById('body').value,'CMA');assert.deepEqual(w.savedScroll,[0,0]);
await w.checkDocumentUpdates();assert(w.document.getElementById('texts-status-updates').hidden,'unchanged feed no notice');
for(const lang of ['pt','es','fr','ru','zh','ar']){w.document.getElementById('language').value=lang;w.document.getElementById('language').dispatchEvent(new w.Event('change'));assert(!w.document.getElementById('texts-status-updates').textContent.includes('undefined'))}
w.close();console.log('PASS:10min central polling, hidden-tab pause/resume, request deduplication, staged update, reader filters/scroll,7locales');
})().catch(e=>{console.error(e);process.exit(1)});
