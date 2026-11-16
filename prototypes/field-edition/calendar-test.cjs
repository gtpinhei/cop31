const fs=require('fs'),assert=require('assert'),{JSDOM}=require('../../tools/node_modules/jsdom');
(async()=>{
const d=new JSDOM(fs.readFileSync(__dirname+'/index.html','utf8'),{url:'https://prototype.test/',runScripts:'outside-only',pretendToBeVisual:true}),w=d.window,doc=w.document;
w.fetch=async u=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(__dirname+'/'+u))});
w.eval(['app.js','canonical.js','migration.js'].map(f=>fs.readFileSync(__dirname+'/'+f,'utf8')).join('\n')+'\nwindow.testCalendar={updateCalendar,timer:()=>calendarTimer}');
const tick=()=>new Promise(r=>setTimeout(r,25));await tick();
w.location.hash='#calendario';w.dispatchEvent(new w.Event('hashchange'));await tick();
const update=(year,month,day)=>w.testCalendar.updateCalendar(new w.Date(year,month-1,day,12));
update(2026,11,16);
assert.equal(doc.querySelectorAll('.tl-today').length,1);
assert.equal(doc.querySelector('.tl-today time').dateTime,'2026-11-16');
assert.equal(doc.querySelector('.tl-today').nextElementSibling.dataset.start,'2026-11-17');
assert(doc.querySelector('[data-end="2026-11-13"]').classList.contains('past'));
assert.equal(doc.querySelector('[data-end="2026-11-18"]').getAttribute('aria-current'),'date');
update(2026,11,17);assert.equal(doc.querySelectorAll('.tl-today').length,1);assert.equal(doc.querySelector('[data-start="2026-11-17"]').getAttribute('aria-current'),'date');
update(2026,11,19);assert(doc.querySelector('[data-end="2026-11-18"]').classList.contains('past'));assert(!doc.querySelector('[data-end="2026-11-18"]').hasAttribute('aria-current'));
update(2026,10,1);assert.equal(doc.querySelector('#timeline').firstElementChild.className,'tl-today');
update(2029,1,1);assert.equal(doc.querySelector('#timeline').lastElementChild.className,'tl-today');
for(const l of ['en','pt','es','fr','ru','zh','ar']){doc.querySelector('#language').value=l;doc.querySelector('#language').dispatchEvent(new w.Event('change'));await tick();update(2026,11,16);assert.equal(doc.querySelectorAll('.tl-today').length,1);assert(doc.querySelector('.tl-line small').textContent);assert.equal(doc.documentElement.dir,l==='ar'?'rtl':'ltr')}
Object.defineProperty(doc,'hidden',{configurable:true,value:true});doc.dispatchEvent(new w.Event('visibilitychange'));assert.equal(w.testCalendar.timer(),null);
Object.defineProperty(doc,'hidden',{configurable:true,value:false});doc.dispatchEvent(new w.Event('visibilitychange'));assert.notEqual(w.testCalendar.timer(),null);
w.location.hash='#texts';w.dispatchEvent(new w.Event('hashchange'));await tick();assert.equal(w.testCalendar.timer(),null);
console.log('PASS: moving marker, local date, past/current date ranges, rollover, before/after calendar, seven languages, RTL, hidden-tab and navigation timer cleanup');w.close();
})().catch(e=>{console.error(e);process.exit(1)});
