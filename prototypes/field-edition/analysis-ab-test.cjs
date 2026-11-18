/* A+B acceptance fixtures are wholly synthetic. Equal extracted text is not equal PDF bytes. */
const fs=require('fs'),assert=require('assert'),{JSDOM}=require('../../tools/node_modules/jsdom');
const tick=()=>new Promise(r=>setTimeout(r,30));
const checked_at=new Date().toISOString(),base={url:'https://unfccc.int/synthetic-352.pdf',id:'synthetic352',version_label:'SYNTHETIC v352',reviewed_at:checked_at,sha256:'a'.repeat(64)};
const replacement={...base,id:'synthetic353',url:'https://unfccc.int/synthetic-353.pdf',version_label:'SYNTHETIC corrected v353',sha256:'b'.repeat(64)};
const row={article:'synthetic-analysis-352',format:'text-explained',document:base,comparison:{status:'compared',baseline:replacement},summary:{changes:['SYNTHETIC metadata correction, no textual change established beyond extracted-text equality.'],significance:'SYNTHETIC files retain separate identities.',watch:'SYNTHETIC next revision.',language:'en'},lifecycle:{status:'replaced',checked_at,replacement}};
const article={schema:1,id:row.article,status:'published',approved_by:'SYNTHETIC editor',approved_at:checked_at,title:'SYNTHETIC analysis',sources:[{verified:true,url:base.url},{verified:true,url:replacement.url,note:'SYNTHETIC reviewed original bytes; current URL differs.'}],contributor:{display:'named',name:'SYNTHETIC author'}};
(async()=>{
 const w=new JSDOM('<head></head><div id="todayArticle"></div>',{url:'https://review.test/classic.html#hoje/leitura/'+row.article,runScripts:'outside-only'}).window;
 let catalog={checked_at,documents:[{id:base.id,attachments:[{url:base.url,sha256:base.sha256}],extracted_text_sha256:'c'.repeat(64)},{id:replacement.id,attachments:[{url:replacement.url,sha256:replacement.sha256}],extracted_text_sha256:'c'.repeat(64)}]};
 w.fetch=async u=>({ok:true,json:async()=>u==='data/analysis.json'?{schema:1,entries:[row]}:catalog});
 w.eval(fs.readFileSync(__dirname+'/analysis-core.js','utf8')+'\n'+fs.readFileSync(__dirname+'/analysis-classic.js','utf8')+'\nwindow.matches=analysisMatchesDocument;window.state=analysisDocumentState;');
 const live={...row,lifecycle:undefined};delete live.lifecycle;
 assert(w.matches(row,catalog.documents[0]));assert(!w.matches(row,catalog.documents[1]),'same extracted text must not join different IDs/PDFs');
 assert.equal(w.state(row,catalog).status,'replaced');assert.equal(w.state(row,catalog).replacement.sha256,'b'.repeat(64));
 const combined=w.state(row,{checked_at,documents:[{...catalog.documents[0],withdrawn:true}]});assert.equal(combined.status,'withdrawn');assert.equal(combined.replacement.sha256,replacement.sha256);
 const ldc={...live,document:{...base,id:'synthetic350'}};
 assert.equal(w.state(ldc,{checked_at,documents:[{id:'synthetic350',withdrawn:true,attachments:[]}]}).status,'withdrawn');
 assert.equal(w.state(live,catalog).status,'current');
 assert.equal(w.state(live,{...catalog,checked_at:'2020-01-01T00:00:00Z'}).status,'unknown');
 assert.equal(w.state(live,{...catalog,degraded:true}).status,'unknown');assert.equal(w.state(live,null).status,'unknown');
 assert.equal(w.state(live,{checked_at,documents:[{...catalog.documents[0],attachments:[{url:base.url,sha256:'d'.repeat(64)}]}]}).status,'version_mismatch');
 const dispatch=()=>w.document.dispatchEvent(new w.CustomEvent('cop31:article',{detail:{article,language:'en',preview:false}}));
 dispatch();await tick();let box=w.document.getElementById('analysis-version-context');
 assert(box.textContent.includes('Replaced'));assert(box.querySelector('details').textContent.includes('SYNTHETIC reviewed original bytes; current URL differs.'));assert(box.querySelector('details').textContent.includes(replacement.sha256));assert(box.querySelector('a[href="'+replacement.url+'"]'));assert(box.textContent.includes('What changed'));assert(box.textContent.includes('What to watch'));assert(box.querySelector('.analysis-back').hash==='#texts');
 dispatch();await tick();assert.equal(w.document.querySelectorAll('#analysis-version-context').length,1);assert.equal(w.document.querySelectorAll('#analysis-detail-style').length,1);
 dispatch();w.dispatchEvent(new w.Event('hashchange'));await tick();assert(!w.document.getElementById('analysis-version-context'),'late result must not restore dismissed context');
 w.close();console.log('PASS A+B: withdrawal, replacement lineage, distinct PDF hashes, freshness, mismatch, repeated render and navigation cancellation');
})().catch(e=>{console.error(e);process.exit(1)});
