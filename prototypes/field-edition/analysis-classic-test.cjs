/* SYNTHETIC canonical-route context, races and exact version links. */
const fs=require('fs'),assert=require('assert'),{JSDOM}=require('../../tools/node_modules/jsdom');
(async()=>{
 const w=new JSDOM('<div id="todayArticle"></div>',{url:'https://review.test/classic.html#hoje/leitura/synthetic-old',runScripts:'outside-only'}).window;
 const doc={url:'https://unfccc.int/test.pdf',version_label:'SYNTHETIC exact v1',reviewed_at:'2026-11-17T00:00:00Z',sha256:'a'.repeat(64)};
 const old={article:'synthetic-old',format:'text-explained',document:doc,comparison:{status:'not_assessed'},superseded_by:'synthetic-new'},next={...old,article:'synthetic-new',superseded_by:null};
 const article={schema:1,id:'synthetic-old',status:'published',approved_by:'SYNTHETIC editor',approved_at:'2026-11-17T01:00:00Z',title:'SYNTHETIC old',sources:[{verified:true,url:doc.url}],contributor:{display:'named',name:'SYNTHETIC author'}};
 let calls=[];w.fetch=async u=>{calls.push(u);return {ok:true,json:async()=>u==='data/analysis.json'?{schema:1,entries:[old,next]}:{...article,id:'synthetic-new',title:'SYNTHETIC new'}}};
 w.eval(['analysis-core.js','analysis-classic.js'].map(f=>fs.readFileSync(__dirname+'/'+f,'utf8')).join('\n'));
 const tick=()=>new Promise(r=>setTimeout(r,25)),dispatch=(a=article,language='en')=>w.document.dispatchEvent(new w.CustomEvent('cop31:article',{detail:{article:a,language,preview:false}}));
 dispatch();await tick();let box=w.document.getElementById('analysis-version-context');assert(box.textContent.includes('SYNTHETIC exact v1'));assert(box.textContent.includes('Superseded by'));assert.equal(box.querySelector('a').href,doc.url);assert(box.querySelector('a[href="#hoje/leitura/synthetic-new"]'));
 dispatch();await tick();assert.equal(w.document.querySelectorAll('#analysis-version-context').length,1);assert.equal(calls.filter(u=>u==='data/analysis.json').length,1);
 dispatch({...article,status:'draft'});await tick();assert(!w.document.getElementById('analysis-version-context'));
 dispatch(article,'ar');await tick();assert(w.document.getElementById('analysis-version-context').textContent.includes('حل محله'));
 w.fetch=async()=>({ok:false});dispatch();await tick();assert(w.document.getElementById('analysis-version-context').textContent.includes('Superseded by'));assert(w.document.getElementById('analysis-version-context').textContent.includes('SYNTHETIC exact v1'));
 dispatch();w.dispatchEvent(new w.Event('hashchange'));await tick();assert(!w.document.getElementById('analysis-version-context'));
 w.close();console.log('PASS: canonical version/source links and supersession, no duplicate context, invalid approval hidden, Arabic, navigation race');
})().catch(e=>{console.error(e);process.exit(1)});
