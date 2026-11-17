const fs=require('fs'),assert=require('assert'),{JSDOM}=require('../../tools/node_modules/jsdom');
const w=new JSDOM(fs.readFileSync(__dirname+'/index.html','utf8'),{url:'https://review.test/#texts',runScripts:'outside-only'}).window;
const records=[{id:1,title:'Financement et résilience',symbol:'FCCC/PA/CMA/2026/L.1',body:'CMA',agenda:'11(a)'},{id:2,title:'Adaptation finance',symbol:'FCCC/CP/2026/L.2',body:'COP'},{id:3,title:'تمويل المناخ',symbol:'AR',body:'CMA'},{id:4,title:'气候资金',symbol:'ZH',body:'CMA'},{id:5,title:'Withdrawn finance',body:'CMA',withdrawn:true}];
let calls=0;w.fetch=async u=>{calls++;return {ok:true,json:async()=>u==='documents.json'?{documents:records}:JSON.parse(fs.readFileSync(__dirname+'/'+u))}};
w.eval(fs.readFileSync(__dirname+'/app.js','utf8'));
(async()=>{await new Promise(r=>setImmediate(r));const d=w.document,q=d.getElementById('search');const search=v=>{q.value=v;q.dispatchEvent(new w.Event('input'));return [...d.querySelectorAll('.document h2')].map(x=>x.textContent)};
assert.deepEqual(search(' RESILIENCE   financement '),['Financement et résilience']);
assert.deepEqual(search('re\u0301silience'),['Financement et résilience']);
assert.deepEqual(search('CMA 11(a)'),['Financement et résilience']);
assert.deepEqual(search('2026/L.2 finance'),['Adaptation finance']);
assert.deepEqual(search('تمويل'),['تمويل المناخ']);assert.deepEqual(search('资金'),['气候资金']);
assert.equal(search('finance impossible').length,0);assert.equal(search('<script>').length,0);
assert.equal(search('   ').length,4);assert.equal(search('withdrawn').length,0);
search('finance');d.getElementById('body').value='COP';d.getElementById('body').dispatchEvent(new w.Event('change'));assert.equal(d.querySelectorAll('.document').length,1);
for(const l of ['en','pt','es','fr','ru','zh','ar']){d.getElementById('language').value=l;d.getElementById('language').dispatchEvent(new w.Event('change'));assert.equal(d.querySelectorAll('.document').length,1)}
d.getElementById('reset').click();assert.equal(q.value,'');assert.equal(d.querySelectorAll('.document').length,4);assert.equal(calls,3);w.close();console.log('PASS: document multi-term/accent search, official symbol/body/agenda, scripts, language persistence, reset, no new fetches');})().catch(e=>{console.error(e);process.exit(1)});
