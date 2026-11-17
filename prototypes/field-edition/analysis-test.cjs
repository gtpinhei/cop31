/* SYNTHETIC approved-content rendering tests; nothing here is real editorial approval. */
const fs=require('fs'),assert=require('assert'),{JSDOM}=require('../../tools/node_modules/jsdom');
const tick=()=>new Promise(r=>setTimeout(r,40));
const doc={url:'https://unfccc.int/test.pdf',version_label:'SYNTHETIC v1',reviewed_at:'2026-11-17T00:00:00Z',sha256:'a'.repeat(64)};
const row={article:'synthetic-text',format:'text-explained',document:doc,comparison:{status:'not_assessed'}};
const article={schema:1,id:row.article,status:'published',approved_by:'SYNTHETIC editor',approved_at:'2026-11-17T01:00:00Z',title:'SYNTHETIC analysis <unsafe>',standfirst:'SYNTHETIC summary',sources:[{verified:true,url:doc.url}],contributor:{display:'named',name:'SYNTHETIC author'}};
async function boot(entries=[],articles={}){
 const w=new JSDOM(fs.readFileSync(__dirname+'/live-preview.html','utf8'),{url:'https://review.test/',runScripts:'outside-only'}).window,calls=[];
 w.COP31_DATA={analysis:'data/analysis.json',today:'data/today.json'};
 w.fetch=async u=>{calls.push(u);if(u==='data/analysis.json')return {ok:true,json:async()=>({schema:1,entries})};
 if(u==='data/today.json')return {ok:true,json:async()=>({entries:[{status:'published',approved_by:'SYNTHETIC',approved_at:'2026-11-17',headline:'DUPLICATE CARD',article:row.article,sources:[{verified:true}]}]})};
 if(u.includes('/articles/')){const a=articles[u.split('/').pop().replace('.json','')];return {ok:!!a,json:async()=>a}}
 return {ok:true,json:async()=>JSON.parse(fs.readFileSync(__dirname+'/'+u))}};
 w.eval(['app.js','canonical.js','migration.js','retention.js','analysis-core.js','analysis.js'].map(f=>fs.readFileSync(__dirname+'/'+f,'utf8')).join('\n')+';window.gate=analysisAllowed;window.docGate=analysisDocument;window.translationView=analysisTitle;window.refreshAnalysis=renderAnalysis;');
 await tick();return {w,calls};
}
(async()=>{
 let {w,calls}=await boot();assert(w.document.getElementById('original-analysis').hidden);assert(w.document.getElementById('explore-analysis').hidden);assert.equal(calls.filter(u=>u.includes('/articles/')).length,0);w.close();
 ({w,calls}=await boot([row],{[row.article]:article}));
 assert(w.translationView({...article,i18n:{en:{title:'ONLY TITLE'}}}).pending);assert.equal(w.translationView({...article,i18n:{en:{title:'ONLY TITLE'}}}).language,'pt-BR');
 let box=w.document.getElementById('original-analysis');assert(!box.hidden);assert(box.textContent.includes('SYNTHETIC analysis <unsafe>'));assert(!box.querySelector('unsafe'));
 assert(!w.document.getElementById('community').textContent.includes('DUPLICATE CARD'));assert.equal(box.querySelector('h3 a').hash,'#hoje/leitura/synthetic-text');assert(box.querySelector('a[href="'+doc.url+'"]'));assert(box.textContent.includes('Comparison not assessed'));
 for(const code of ['en','pt','es','fr','ru','zh','ar']){w.document.getElementById('language').value=code;w.document.getElementById('language').dispatchEvent(new w.Event('change'));await tick();assert(box.querySelector('h3 a').search.includes('lang='+code));assert(box.querySelector('h2').textContent)}
 assert.equal(w.document.documentElement.dir,'rtl');assert.equal(calls.filter(u=>u.includes('/articles/')).length,1);assert(!w.document.querySelector('iframe'));assert(!calls.some(u=>/private|draft/.test(u)));
 const cards=w.document.getElementById('documents');cards.innerHTML='<article class="document"><a href="'+doc.url+'">PDF</a></article><article class="document"><a href="https://unfccc.int/other.pdf">Other</a></article>';w.refreshAnalysis();assert.equal(cards.querySelectorAll('.analysis-document-link').length,1);w.refreshAnalysis();assert.equal(cards.querySelectorAll('.analysis-document-link').length,1);
 for(const change of [{status:'draft'},{approved_by:''},{approved_at:'bad'},{contributor:null},{sources:[]},{id:'other'}])assert(!w.gate(row,{...article,...change}),JSON.stringify(change));
 assert(!w.gate({...row,document:{...doc,url:'https://evil.test'}},article));assert(!w.gate({...row,comparison:{status:'compared'}},article));assert(!w.docGate({...doc,url:'https://localhost/a'}));w.close();
 ({w}=await boot([{...row,superseded_by:'missing-new'}],{[row.article]:article}));assert(w.document.getElementById('original-analysis').hidden);w.close();
 ({w}=await boot([row,row],{[row.article]:article}));assert(w.document.getElementById('original-analysis').hidden);w.close();
 const next={...row,article:'synthetic-new',document:{...doc,version_label:'SYNTHETIC v2'}};
 ({w}=await boot([{...row,superseded_by:next.article},next],{[row.article]:article,[next.article]:{...article,id:next.article,title:'SYNTHETIC replacement'}}));assert(w.document.getElementById('original-analysis').textContent.includes('Superseded by'));w.close();
 console.log('PASS: empty hidden; approved-only teasers; canonical article routes; exact source versions; seven locales/RTL; one fetch; no duplicate community card; supersession; no private requests');
})().catch(e=>{console.error(e);process.exit(1)});
