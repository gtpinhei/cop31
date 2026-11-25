'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {JSDOM,VirtualConsole}=require('../../tools/node_modules/jsdom');
const built=process.argv[2], files=built?path.resolve(built):__dirname;
const html=fs.readFileSync(path.join(files,built?'index.html':'live-preview.html'),'utf8');
const scripts=[...html.matchAll(/<script(?: defer)? src="([^"?]+)(?:\?[^"]*)?"/g)].map(m=>m[1]);
const w=new JSDOM(html,{url:'https://monitor.example/?lang=en#today',runScripts:'outside-only',virtualConsole:new VirtualConsole()}).window;
const d=w.document,q=s=>d.querySelector(s),all=s=>[...d.querySelectorAll(s)];
const errors=[];
w.addEventListener('error',e=>errors.push(e.error));
w.fetch=async input=>{
  const url=new URL(input,w.location.href);
  assert.equal(url.origin,w.location.origin);
  const file=path.join(files,String(input).split('?')[0]);
  if(!fs.existsSync(file))return {ok:false,status:404};
  return {ok:true,json:async()=>JSON.parse(fs.readFileSync(file,'utf8')),text:async()=>fs.readFileSync(file,'utf8')};
};
const tick=()=>new Promise(r=>setTimeout(r,25));
const navigate=async hash=>{w.location.hash=hash;await tick()};
const approved=id=>'https://unfccc.int/documents/'+id;
const published={
  'gcf-cop':['COP 31 · 8(c)',665896],
  'gcf-cma':['CMA 8 · 11(b)',665901],
  'loss-and-damage-fund-cma':['CMA 8 · 11(d)',665892],
  'adaptation-fund-cmp':['CMP 21 · 6',665890],
  'adaptation-fund-cma':['CMA 8 · 11(e)',665893],
  'adaptation-fund-board-cmp':['CMP 21 · 6',665891],
  'adaptation-fund-board-cma':['CMA 8 · 11(e)',665902],
  'article-6-2':['CMA 8 · 16(a)',665848],
  'article-6-2-funding':['CMA 8 · 18',665849],
  'article-6-8':['CMA 8 · 16(c)',665845]
};
const unresolved={
  'antalya-pact':['COP 31 · 2(f)','FCCC/CP/2026/L.14'],
  'antalya-pact-cma':['CMA 8 · 2(c)','FCCC/PA/CMA/2026/L.25'],
  'gef-cop':['COP 31 · 8(d)','FCCC/CP/2026/L.11'],
  'gef-cma':['CMA 8 · 11(c)','FCCC/PA/CMA/2026/L.20'],
  'response-measures':['COP 31 · 12 / CMP 21 · 7 / CMA 8 · 15','FCCC/CP/2026/L.12','FCCC/KP/CMP/2026/L.5','FCCC/PA/CMA/2026/L.21']
};
(async()=>{
  w.eval(scripts.map(f=>fs.readFileSync(path.join(files,f),'utf8')).join('\n'));
  await tick();
  const base=q('[data-tab="results"]')?'#results':'#texts/results';
  assert(q('#results').hidden&&q('#error').hidden);
  await navigate(base);
  assert(!q('#results').hidden);
  assert.equal(all('.result-card').length,22);
  assert.equal(all('.result-card .result-status.adopted').length,16);
  assert.equal(all('.result-card .result-status.notAdopted').length,6);
  const {outcomes,milestones}=w.COP31_RESULTS_DATA;
  const keys=new Set(outcomes.map(o=>o.id));
  assert.equal(keys.size,outcomes.length);
  assert(milestones.every(m=>keys.has(m.id)&&m.en&&m.pt&&(m.date||m.session)));
  assert.equal(outcomes.find(o=>o.id==='mitigation').body,'CMA 8 · 6');
  const cards=new Map(all('.result-card').map(c=>[c.querySelector('h3 a').hash.split('/').pop(),c]));
  assert.equal(cards.size,outcomes.length);
  for(const [id,[body,doc]] of Object.entries(published)){
    assert(cards.get(id).textContent.includes(body));
    assert(cards.get(id).querySelector('.adopted'));
    const href=cards.get(id).querySelector('h3 a').hash;
    await navigate(href);
    assert.equal(q('.result-provenance a').href,approved(doc));
    assert(q('.result-stage').textContent.includes('Advance unedited version'));
  }
  for(const [id,[body,...symbols]] of Object.entries(unresolved)){
    assert(cards.get(id).textContent.includes(body));
    await navigate(cards.get(id).querySelector('h3 a').hash);
    assert.equal(q('.result-provenance a').hostname,'enb.iisd.org');
    assert(q('.result-status.notAdopted'));
    assert(q('.result-stage').textContent.includes('No adopted text'));
    assert(symbols.every(s=>q('#results').textContent.includes(s)));
  }
  await navigate('#texts/results/decision/antalya-pact');
  assert(q('#results-heading').textContent.includes('Convention cover text'));
  await navigate(base+'/decision/article-6-8');
  assert(q('.result-status.adopted'));
  assert(q('.result-steps').textContent.includes('SBSTA 66'));
  assert.deepEqual(all('.result-steps time').map(n=>n.dateTime),['2027-03-31','2027-08-31']);
  await navigate(base+'/decision/article-6-2-funding');
  assert(q('.result-status.adopted')&&q('#results').textContent.includes('did not select a funding model'));
  assert(q('.result-steps').textContent.includes('SBI 66'));
  await navigate(base+'/decision/adaptation-fund-cmp');
  assert.equal(q('.result-steps time').dateTime,'2027-01-01');
  assert(q('.result-steps').textContent.includes('separate trigger'));
  await navigate(base+'/decision/response-measures');
  assert(q('.result-steps').textContent.includes('SB 66'));
  q('#language').value='pt';
  q('#language').dispatchEvent(new w.Event('change'));
  await tick();
  assert.equal(q('#results-heading').lang,'pt');
  assert(q('#results').textContent.includes('não obteve consenso'));
  assert.deepEqual(errors,[]);
  console.log('PASS: 22 outcomes including 6 not adopted, 15 new/updated provenance checks, old Antalya link, AUV vs procedural carryover, dates and Portuguese details');
})().catch(e=>{console.error(e);process.exitCode=1}).finally(()=>w.close());
