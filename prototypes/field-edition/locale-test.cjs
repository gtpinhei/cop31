const assert=require('assert'),fs=require('fs'),{JSDOM}=require('../../tools/node_modules/jsdom');
(async()=>{
const dom=new JSDOM(fs.readFileSync(__dirname+'/index.html','utf8'),{url:'https://prototype.test/',runScripts:'outside-only'}),w=dom.window,d=w.document;
w.fetch=async u=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(__dirname+'/'+u))});
w.eval(['app.js','canonical.js','migration.js'].map(f=>fs.readFileSync(__dirname+'/'+f,'utf8')).join('\n')+'\nwindow.iaLabels=IA;');
const tick=()=>new Promise(r=>setTimeout(r,20));await tick();
const expected={en:'Civil society',pt:'Sociedade civil',es:'Sociedad civil',fr:'Société civile',ru:'Гражданское общество',zh:'公民社会',ar:'المجتمع المدني'};
for(const [lang,civil] of Object.entries(expected)){
 assert.equal(w.iaLabels[lang].length,33);assert(w.iaLabels[lang].every(s=>typeof s==='string'&&s.length));
 assert.equal(w.iaLabels[lang][32],civil);assert.notEqual(w.iaLabels[lang][11],civil);
 d.querySelector('#language').value=lang;d.querySelector('#language').dispatchEvent(new w.Event('change'));await tick();
 assert([...d.querySelectorAll('#daily-sections h2')].some(h=>h.textContent===civil));
 w.location.hash='#pulse';w.dispatchEvent(new w.Event('hashchange'));await tick();
 assert(d.querySelector('#pulse-platform').parentElement.textContent.includes(w.iaLabels[lang][15]));
 assert(d.querySelector('#pulse-from').parentElement.textContent.includes(w.iaLabels[lang][17]));
 w.location.hash='#radar';w.dispatchEvent(new w.Event('hashchange'));await tick();
 assert.equal(d.querySelector('#method .freshness').textContent,w.iaLabels[lang][26]);
 assert.equal(d.querySelector('.archive-label').textContent,w.iaLabels[lang][27]);
}
console.log('PASS: all 33 new IA labels provided in 7 locales; civil society separate from social; localized controls, reference warning and archive label');w.close();
})().catch(e=>{console.error(e);process.exit(1)});
