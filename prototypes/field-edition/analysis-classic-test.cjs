/* SYNTHETIC canonical-route context, races and exact version links. */
const fs=require('fs'),assert=require('assert'),{JSDOM}=require('../../tools/node_modules/jsdom');
(async()=>{
 const w=new JSDOM('<div id="todayArticle"></div>',{url:'https://review.test/classic.html#hoje/leitura/synthetic-old',runScripts:'outside-only'}).window;
 const doc={id:'synthetic-document',url:'https://unfccc.int/test.pdf',version_label:'SYNTHETIC exact v1',reviewed_at:'2026-11-17T00:00:00Z',sha256:'a'.repeat(64)};
 const old={article:'synthetic-old',format:'text-explained',document:doc,comparison:{status:'not_assessed'},summary:{changes:['SYNTHETIC change'],significance:'SYNTHETIC significance',watch:'SYNTHETIC watch',language:'en'},superseded_by:'synthetic-new'},next={...old,article:'synthetic-new',superseded_by:null};
 const article={schema:1,id:'synthetic-old',status:'published',approved_by:'SYNTHETIC editor',approved_at:'2026-11-17T01:00:00Z',title:'SYNTHETIC old',sources:[{verified:true,url:doc.url}],contributor:{display:'named',name:'SYNTHETIC author'}};
 let catalog={documents:[{id:doc.id,withdrawn:true,attachments:[{url:doc.url,sha256:doc.sha256}]}]},calls=[];w.fetch=async u=>{calls.push(u);return {ok:true,json:async()=>u==='data/analysis.json'?{schema:1,entries:[old,next]}:u==='data/negotiating-texts.json'?catalog:{...article,id:'synthetic-new',title:'SYNTHETIC new'}}};
 w.eval(['analysis-core.js','analysis-classic.js'].map(f=>fs.readFileSync(__dirname+'/'+f,'utf8')).join('\n'));
 const tick=()=>new Promise(r=>setTimeout(r,25)),dispatch=(a=article,language='en')=>w.document.dispatchEvent(new w.CustomEvent('cop31:article',{detail:{article:a,language,preview:false}}));
 dispatch();await tick();let box=w.document.getElementById('analysis-version-context');assert(box.textContent.includes('SYNTHETIC exact v1'));assert(box.textContent.includes('Superseded by'));assert.equal(box.querySelector('a').href,doc.url);assert(box.querySelector('a[href="#hoje/leitura/synthetic-new"]'));
 assert(box.textContent.includes('Withdrawn'));assert(box.textContent.includes('What to watch'));assert(box.querySelector('.analysis-back').href==='https://review.test/index.html?lang=en#texts');assert(box.querySelector('details summary'));
 dispatch();await tick();assert.equal(w.document.querySelectorAll('#analysis-version-context').length,1);assert.equal(calls.filter(u=>u==='data/analysis.json').length,1);
 dispatch({...article,status:'draft'});await tick();assert(!w.document.getElementById('analysis-version-context'));
 dispatch(article,'ar');await tick();assert(w.document.getElementById('analysis-version-context').textContent.includes('حل محله'));
 w.fetch=async()=>({ok:false});dispatch();await tick();assert(w.document.getElementById('analysis-version-context').textContent.includes('Superseded by'));assert(w.document.getElementById('analysis-version-context').textContent.includes('SYNTHETIC exact v1'));
 // Reading order and exact-token disclosure, without deleting scope prose or citations.
 const host=w.document.getElementById('todayArticle');host.innerHTML='<h3 class="art-title">Title</h3><p class="art-sf">Standfirst</p><p class="art-rn">Reporting method</p><section class="art-block"><p>Withdrawn baseline; mutable URL. '+doc.sha256+'</p><a href="https://unfccc.int/citation">Claim citation</a></section>';
 dispatch({...article,blocks:[{md:'scope'}]});await tick();box=w.document.getElementById('analysis-version-context');
 assert.equal(host.querySelector('.art-sf').nextElementSibling,box);assert(!box.querySelector('.analysis-summary'),'real article body is not duplicated');
 assert(!box.querySelector('details').open);assert(box.querySelector('details').textContent.includes(doc.sha256));assert(!host.querySelector('.art-block').textContent.includes(doc.sha256));assert(host.querySelector('.art-block').textContent.includes('Withdrawn baseline; mutable URL.'));assert(host.querySelector('a[href="https://unfccc.int/citation"]'));
 assert(host.querySelector(':scope > .art-rn').hidden);assert(box.querySelector('details .art-rn')&&!box.querySelector('details .art-rn').hidden);
 dispatch({...article,blocks:[{md:'scope'}]});await tick();assert.equal(w.document.querySelectorAll('#analysis-verification').length,1);const disclosure=w.document.getElementById('analysis-verification');w.dispatchEvent(new w.Event('beforeprint'));assert(disclosure.open);w.dispatchEvent(new w.Event('afterprint'));assert(!disclosure.open);disclosure.open=true;w.dispatchEvent(new w.Event('beforeprint'));w.dispatchEvent(new w.Event('afterprint'));assert(disclosure.open);
 dispatch();w.dispatchEvent(new w.Event('hashchange'));await tick();assert(!w.document.getElementById('analysis-version-context'));
 w.close();console.log('PASS: canonical version/source links and supersession, no duplicate context, invalid approval hidden, Arabic, navigation race');
})().catch(e=>{console.error(e);process.exit(1)});
