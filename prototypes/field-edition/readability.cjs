// Editorial boundaries, not sentence splitting: preserve every character and inline link.
const plans={
en:['The first is whether','The second is whether','The third is whether','The real disagreements','The starkest numbers','IDDRI, Carbon Brief and Germanwatch treat','The largest analytical gap'],
pt:['se a meta de eletrificação','se surge um caminho','e se o Mecanismo','As divergências reais','O quadro numérico','Os mapas do caminho brasileiros','A maior lacuna'],
es:['si la meta de electrificación','si surge una vía','y si el Mecanismo','Las divergencias reales','El cuadro numérico','Los mapas de ruta brasileños','La mayor laguna'],
fr:["si l'objectif d'électrification",'si une voie de mise','et si le Mécanisme','Les divergences réelles','Le tableau chiffré','Les feuilles de route brésiliennes',"La plus grande lacune"],
ru:['превратится ли цель','появится ли путь','и получит ли Механизм','Реальных расхождений','Самые жёсткие цифры','Бразильские дорожные карты','Самый большой пробел'],
zh:['“35 by 35”电气化目标','能否为NCQG','以及公正转型机制','真正的分歧','最严峻的数字','巴西关于TAFF','最大的分析空白'],
ar:['هل يتحول هدف','وهل يظهر مسار','وهل تكتسب آلية','والخلافات الحقيقية','أقسى الأرقام','وتعامل IDDRI','وأكبر فجوة']
};
function improve(document,lang){
 const root=document;document=root.ownerDocument||root;
 const p=root.querySelector('.report-lede > p');
 if(!p||root.querySelector('.report-tests'))return;
 const text=p.textContent, markers=plans[lang];
 if(!markers)throw Error('Missing readability locale '+lang);
 const cuts=[0,...markers.map(m=>text.indexOf(m)),text.length];
 if(cuts.some((v,i)=>v<0||(i&&v<=cuts[i-1])))throw Error('Editorial boundaries changed for '+lang);
 // DOM ranges retain inline emphasis and citations rather than converting HTML to text.
 const walker=document.createTreeWalker(p,4),nodes=[];let n,offset=0;
 while(n=walker.nextNode()){nodes.push({node:n,start:offset,end:offset+n.length});offset+=n.length;}
 function point(pos){const n=nodes.find(n=>pos<=n.end);return[n.node,pos-n.start];}
 function part(start,end,tag){const el=document.createElement(tag),r=document.createRange();r.setStart(...point(start));r.setEnd(...point(end));el.append(r.cloneContents());return el;}
 const out=document.createDocumentFragment(),list=document.createElement('ul');list.className='report-tests';
 out.append(part(cuts[0],cuts[1],'p'));
 for(let i=1;i<=3;i++)list.append(part(cuts[i],cuts[i+1],'li'));
 out.append(list);
 for(let i=4;i<cuts.length-1;i++)out.append(part(cuts[i],cuts[i+1],'p'));
 p.replaceWith(out);
}
module.exports={improve};
