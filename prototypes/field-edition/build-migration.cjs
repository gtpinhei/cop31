const fs=require('fs'),path=require('path'),{JSDOM}=require('../../tools/node_modules/jsdom');
const base=__dirname,source=fs.readFileSync(path.join(base,'source-public.html'),'utf8');
const core=source.match(/\/\*i18n-core-begin\*\/([\s\S]*?)\/\*i18n-core-end\*\//)[1];
const dom=new JSDOM(source,{runScripts:'outside-only'});dom.window.eval(core);const key=Object.keys(dom.window).filter(k=>dom.window[k]?.collect&&dom.window[k]?.hash)[0];
const names=['panorama','belem','testes','mapa','radar','thinktanks','agenda','posicoes','brasil','quem','calendario','terreno','glossario','fontes','privacidade'];
const positions=JSON.parse(source.match(/var DATA = (\[.*?\]);/s)[1]);fs.writeFileSync(path.join(base,'positions.json'),JSON.stringify(positions));
for(const lang of ['en','pt','es','fr','ru','zh','ar']){
const dic=lang==='pt'?{}:JSON.parse(fs.readFileSync(path.join(base,'../../i18n',lang+'.json')));const out={language:lang,captured_at:new Date().toISOString(),sections:{},anchors:{}};
for(const name of names){const node=dom.window.document.querySelector('#view-'+name).cloneNode(true);
for(const u of dom.window[key].collect(node)){const s=dic[u.key];if(s){if(u.kind==='html')u.node.innerHTML=s;else if(u.kind==='text')u.node.nodeValue=s;else u.node.setAttribute(u.attr,s)}}
if(name==='posicoes'){node.querySelectorAll('table,.filters,[role="status"],input,select,button').forEach(n=>n.remove())}
node.querySelectorAll('script,style,iframe,img,video,audio,form,input,select,button').forEach(n=>n.remove());
for(const el of node.querySelectorAll('*')){for(const a of [...el.attributes])if(/^on/i.test(a.name)||a.name==='style')el.removeAttribute(a.name);if(el.id)out.anchors[el.id]=name;for(const attr of ['href','src'])if(el.hasAttribute(attr)&&! /^(https?:\/\/|#|mailto:)/.test(el.getAttribute(attr)))el.removeAttribute(attr);}
node.querySelectorAll('a[href^="#"]').forEach(a=>{const h=a.getAttribute('href');if(a.getAttribute('onclick'))a.removeAttribute('onclick');});if(name==='thinktanks')require('./readability.cjs').improve(node,lang);out.sections[name]=node.innerHTML;
}
fs.writeFileSync(path.join(base,'explore-'+lang+'.json'),JSON.stringify(out));}
console.log('Built 15 retained sections × 7 locales and '+positions.length+' positions.');
