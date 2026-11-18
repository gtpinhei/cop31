/* SYNTHETIC explicit AI release mode. No real model output or editorial clearance. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx={URL,console};vm.createContext(ctx);vm.runInContext(fs.readFileSync(__dirname+'/analysis-core.js','utf8')+';this.allowed=analysisAllowed;this.release=analysisReleaseAllowed;',ctx);
const before={id:'synthetic-before',url:'https://unfccc.int/before.pdf',version_label:'SYNTHETIC v1',reviewed_at:'2026-11-18T00:00:00Z',sha256:'a'.repeat(64)},after={...before,id:'synthetic-after',url:'https://unfccc.int/after.pdf',version_label:'SYNTHETIC v2',sha256:'b'.repeat(64)};
const row={article:'synthetic-ai',format:'text-explained',document:after,comparison:{status:'compared',baseline:before}};
const a={language:'en',schema:1,id:row.article,status:'published',title:'SYNTHETIC only',contributor:{display:'named',name:'COP31 Monitor AI',role:'analyst'},sources:[before,after].map(d=>({url:d.url,verified:true})),ai_provenance:{schema:1,mode:'public-unfccc-diff',generated_at:'2026-11-18T00:01:00Z',model:'SYNTHETIC',prompt_version:'synthetic-v1',authorization:'owner-public-unfccc-analysis-2026-11-18',source_documents:[before,after],qa:{status:'passed',checked_at:'2026-11-18T00:02:00Z',checks:['official_sources_only','pdf_bytes_verified','version_identity_verified','evidence_links_checked','confidential_inputs_excluded']}}};
assert(ctx.allowed(row,a));
for(const field of ['qa','authorization','source_documents','model']){const b=structuredClone(a);delete b.ai_provenance[field];assert(!ctx.allowed(row,b),field)}
assert(!ctx.allowed(row,{...a,approved_by:'fake',approved_at:'2026-11-18T00:00:00Z'}));
assert(!ctx.allowed(row,{...a,sources:[...a.sources,{verified:true,url:'https://example.org/private'}]}));
assert(!ctx.allowed({...row,document:{...after,sha256:'c'.repeat(64)}},a));
assert(!ctx.allowed({...row,comparison:{status:'not_assessed'}},a));
assert(!ctx.allowed({...row,comparison:{status:'compared',baseline:after}},a));
assert(!ctx.allowed({...row,format:'daily-diplomacy-brief',reporting_date:'2026-11-18',document:undefined,comparison:undefined},a));
const relabel=structuredClone(a);relabel.ai_provenance.source_documents[1]={...before,version_label:'SYNTHETIC relabel',reviewed_at:'2026-11-18T01:00:00Z'};assert(!ctx.release(relabel));
assert(!ctx.release({...a,status:'draft'}));
console.log('PASS AI: scoped official-only provenance; no fake human approval; QA required; exact input binding; fail closed');

// Exercise the actual canonical loader, not only isolated helpers.
const {JSDOM}=require('../../tools/node_modules/jsdom');
const html=fs.readFileSync(__dirname+'/../../index.html','utf8');
const aiArticle={...a,entries:['synthetic-card'],blocks:[{basis:'analysis',heading:'SYNTHETIC only',md:'SYNTHETIC AI BODY SENTINEL'}]};
const pause=()=>new Promise(r=>setTimeout(r,90));
async function direct(index){
 const w=new JSDOM(html,{url:'https://review.test/classic.html?lang=en#hoje/leitura/synthetic-ai',runScripts:'outside-only',pretendToBeVisual:true}).window;
 w.scrollTo=()=>{};w.matchMedia=()=>({matches:false,addListener(){},removeListener(){}});
 w.fetch=async url=>{const u=String(url);if(u.includes('data/analysis.json'))return {ok:index!==null,json:async()=>index};
  if(u.includes('data/articles/'))return {ok:true,json:async()=>aiArticle};
  if(u.includes('i18n/'))return {ok:true,json:async()=>JSON.parse(fs.readFileSync(__dirname+'/../../i18n/en.json','utf8'))};
  if(u.includes('data/today.json'))return {ok:true,json:async()=>({schema:1,entries:[]})};
  if(u.includes('negotiating-texts'))return new Promise(()=>{});
  return {ok:false,json:async()=>({})};};
 const script=[...w.document.querySelectorAll('script')].map(s=>s.textContent).find(s=>s.includes('i18n-core-begin'));w.eval(fs.readFileSync(__dirname+'/analysis-core.js','utf8')+'\n'+script+'\n'+fs.readFileSync(__dirname+'/analysis-classic.js','utf8'));
 await pause();w.dispatchEvent(new w.Event('hashchange'));await pause();return w;
}
(async()=>{
 for(const bad of [null,{schema:1,entries:[]},{schema:1,entries:[row,row]},{schema:1,entries:[{...row,document:before}]}]){
  const w=await direct(bad);assert(!w.document.getElementById('todayArticle').textContent.includes('SYNTHETIC AI BODY SENTINEL'),'invalid index must block direct body');w.close();
 }
 const w=await direct({schema:1,entries:[row]});const body=w.document.getElementById('todayArticle');
 assert(body.textContent.includes('SYNTHETIC AI BODY SENTINEL'));assert(body.textContent.includes('AI-generated analysis'));assert(body.textContent.includes('not human editorial approval'));assert(body.textContent.includes('not an adopted outcome'));assert.equal(body.lang,'en');w.close();
 console.log('PASS AI canonical route: absent/duplicate/mismatched index blocks body; valid route has synchronous AI/draft warning even while status stalls');
})().catch(e=>{console.error(e);process.exitCode=1});
