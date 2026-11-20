const fs=require('fs'),assert=require('assert/strict'),{JSDOM}=require('../../tools/node_modules/jsdom');
const code=['app.js','document-health.js'].map(f=>fs.readFileSync(__dirname+'/'+f,'utf8')).join('\n')+';window.setCatalog=x=>{data.documents=normalizeDocuments(x);documentHealth()};';
const key='cop31.documents.visit.v1', stamp='2026-11-17T00:00:00Z',nextStamp='2026-11-17T00:10:00Z';
const pdf=(language,digest='a',suffix='')=>({language,url:'https://docs.unfccc.int/file/'+language+suffix+'.pdf',sha256:digest?digest.repeat(64):null});
const row=(id,attachments=[pdf('en')],fields={})=>({id,title:'Text '+id,body:'CMA',metadata_version:'1.0',attachments,...fields});
const catalog=(documents,opts={})=>({last_success:stamp,verification_mode:'pdf-hashes',documents,...opts});
const old=catalog([row(1),row(2),row(3),row(4,[],{withdrawn:true}),row(5),row(6),row(7,[pdf('en'),pdf('en','b','-2')]),row(8),row(9)]);
const updated=catalog([
 row(9,[pdf('en','b')],{status:'withdrawn'}), // PDF also changed: withdrawal alone takes precedence
 row(1,[pdf('en','b')],{metadata_version:'2.0'}), // verified byte change alone
 row(2,[pdf('en')],{metadata_version:'2.0'}), // metadata only
 row(3,[pdf('en','a'),pdf('ar','d')]), // translation, not revised
 row(4), // reinstated
 row(5,[pdf('en',null,'-changed')]), // unverified link update
 row(7,[pdf('en','c'),pdf('en','b','-2')],{metadata_version:'2.0'}), // ambiguous language
 row(8,[pdf('en')],{published_at:nextStamp}), // corrected publication date, not revised
 row(10), // first-seen active record
 row(11,[],{withdrawn_at:nextStamp}) // first-seen withdrawn: no transition known
],{last_success:nextStamp}); // ID 6 missing: no inferred withdrawal
async function page(saved,initial=old,{blocked=false,route='texts'}={}){
 const w=new JSDOM(fs.readFileSync(__dirname+'/index.html','utf8'),{
  url:'https://review.test/#'+route,runScripts:'outside-only',pretendToBeVisual:true
 }).window;
 w.COP31_DATA={documents:'central.json'};
 let calls=0;
 if(saved)w.localStorage.setItem(key,saved);
 if(blocked)Object.defineProperty(w,'localStorage',{get(){throw Error('disabled')}});
 w.fetch=async u=>{calls++;return {ok:true,json:async()=>u==='central.json'?initial:JSON.parse(fs.readFileSync(__dirname+'/'+u))}};
 w.eval(code);await new Promise(r=>setImmediate(r));
 return {w,calls:()=>calls,summary:()=>w.document.getElementById('document-visit')};
}
const counts=w=>[...w.document.querySelectorAll('#document-visit bdi')].map(x=>+x.textContent);
(async()=>{
 let {w,calls,summary}=await page();
 assert.equal(calls(),3);
 assert(summary().hidden,'first visit has no fabricated history');
 const saved=w.localStorage.getItem(key);
 assert.equal(JSON.parse(saved).schema,2);
 w.close();

 ({w,calls,summary}=await page(saved));
 assert.deepEqual(counts(w),[]);
 assert(summary().textContent.includes('No changes to show.'));
 assert(!summary().textContent.includes('New records'));
 w.setCatalog(updated);
 assert.deepEqual(counts(w),[1,1,1,1,5],'classify by verified semantics and lifecycle precedence');
 assert.equal(calls(),3,'no extra network calls');
 assert(summary().textContent.includes('PDF file changed'));
 assert(!summary().textContent.includes('bytes'));
 const after=w.localStorage.getItem(key);
 for(const lang of ['pt','es','fr','ru','zh','ar','en']){
  w.document.getElementById('language').value=lang;
  w.document.getElementById('language').dispatchEvent(new w.Event('change'));
  assert.equal(w.document.documentElement.dir,lang==='ar'?'rtl':'ltr');
  assert(!summary().textContent.includes('undefined'));
  assert.equal(summary().querySelectorAll('bdi').length,5);
 }
 assert.deepEqual(counts(w),[1,1,1,1,5],'repeated render keeps page-open comparison');
 summary().querySelector('button').click();
 assert.deepEqual(counts(w),[]);
 for(const [lang,expected] of Object.entries({pt:'Nenhuma alteração a mostrar.',es:'No hay cambios que mostrar.',fr:'Aucun changement à afficher.',ru:'Нет изменений для отображения.',zh:'没有可显示的变更。',ar:'لا توجد تغييرات لعرضها.',en:'No changes to show.'})){
  w.document.getElementById('language').value=lang;
  w.document.getElementById('language').dispatchEvent(new w.Event('change'));
  assert(summary().textContent.includes(expected));
  assert.deepEqual(counts(w),[]);
  assert.equal(w.document.documentElement.dir,lang==='ar'?'rtl':'ltr');
 }
 summary().querySelector('button').click();
 assert.equal(w.document.activeElement,summary().querySelector('button'));
 for(const bad of [
  {...old,degraded:true},
  {...old,last_success:'2026-11-15T00:00:00Z'},
  {...old,documents:[]},
  {...old,documents:[row(1),row(1)]}
 ]){
  w.setCatalog(bad);
  assert(summary().hidden);
  assert.equal(w.localStorage.getItem(key),after,'bad input preserves the healthy checkpoint');
 }
 w.setCatalog(updated);
 assert(!summary().hidden);
 w.close();

 ({w,summary}=await page(after,updated));
 assert.deepEqual(counts(w),[],'fresh return after applied changes');
 w.close();

 ({w,summary}=await page(saved,catalog([row(1,[pdf('en','b')])],{last_success:nextStamp})));
 assert.deepEqual(counts(w),[1],'only nonzero category renders');
 assert(summary().textContent.includes('PDF file changed'));
 assert(!summary().textContent.includes('New records'));
 assert(!summary().textContent.includes('No changes to show.'));
 w.close();

 ({w,summary}=await page(saved,catalog([row(1,[pdf('en','c')])],{last_success:nextStamp,verification_mode:'metadata-only'})));
 assert.deepEqual(counts(w),[],'unverified catalog cannot assert a PDF byte change');
 w.close();

 for(const legacy of ['{corrupt',JSON.stringify({schema:1,checked:stamp,records:{1:'old'}})]){
  ({w,summary}=await page(legacy));
  assert(summary().hidden,'re-seed old or corrupt formats without suggesting updates');
  assert.equal(JSON.parse(w.localStorage.getItem(key)).schema,2);
  w.close();
 }
 ({w,summary}=await page(null,old,{blocked:true}));
 assert(summary().hidden);
 assert(w.document.getElementById('documents').textContent.includes('Text 1'));
 w.close();

 ({w,summary}=await page(null,old,{route:'today'}));
 assert.equal(w.localStorage.getItem(key),null,'no baseline until Texts is viewed');
 w.location.hash='#texts';await new Promise(r=>setTimeout(r,10));
 assert.equal(JSON.parse(w.localStorage.getItem(key)).schema,2);
 assert(summary().hidden);
 w.close();

 console.log('PASS: visit scope, first/empty/old/disabled storage, new and lifecycle states, verified byte vs metadata/translation/ambiguity, reset/focus, recurrence, seven locales/RTL, no extra requests');
})().catch(e=>{console.error(e);process.exit(1)});
