/* Approved-only Field Edition teasers. Shared gates in analysis-core.js. */
const al=i=>(ANALYSIS_LABELS[lang]||ANALYSIS_LABELS.en)[i];
let approvedAnalyses=[];
function analysisLink(row){return classicURL('hoje/leitura/'+row.article)}
function analysisTitle(a){const tr=a.i18n?.[lang],complete=!!(tr?.title&&(!a.standfirst||tr.standfirst));return {title:complete?tr.title:a.title,summary:complete?(tr.standfirst||''):(a.standfirst||''),language:complete?lang:'pt-BR',pending:lang!=='pt'&&!complete}}
function analysisTeaser(row,compact=false){
 const a=row.content,v=analysisTitle(a),kind=al(row.format==='daily-diplomacy-brief'?1:2);
 const next=approvedAnalyses.find(r=>r.article===row.superseded_by);
 return `<article class="post"><p class="meta">${esc(kind)}${row.reporting_date?' · '+esc(row.reporting_date):''}</p><h3 lang="${esc(v.language)}" dir="auto"><a href="${esc(analysisLink(row))}">${esc(v.title)}</a></h3>${!compact&&v.summary?`<p lang="${esc(v.language)}" dir="auto">${esc(v.summary)}</p>`:''}${v.pending?`<p class="subtle">${esc(al(8))}</p>`:''}${row.document?`<p class="meta">${esc(al(4))}: <a href="${safeURL(row.document.url)}"><bdi>${esc(row.document.version_label)}</bdi></a> · <bdi>${esc(date(row.document.reviewed_at))}</bdi></p><p class="meta">${row.comparison.status==='not_assessed'?esc(al(6)):`${esc(al(7))}: <a href="${safeURL(row.comparison.baseline.url)}"><bdi>${esc(row.comparison.baseline.version_label)}</bdi></a>`}</p>`:''}${next?`<p class="badge">${esc(al(5))}: <a href="${esc(analysisLink(next))}" dir="auto">${esc(analysisTitle(next.content).title)}</a></p>`:''}</article>`;
}
function renderAnalysis(){
 for(const [host,id,compact] of [['today','original-analysis',false],['explore','explore-analysis',true]]){
  let el=$(id);if(!el){el=document.createElement('section');el.id=id;$(host).appendChild(el)}
  el.hidden=!approvedAnalyses.length;el.innerHTML=approvedAnalyses.length?`<h2>${esc(al(0))}</h2>`+approvedAnalyses.map(r=>analysisTeaser(r,compact)).join(''):'';
 }
 analysisDocumentLinks();communityRows();
}
function analysisDocumentLinks(){
 document.querySelectorAll('#documents .analysis-document-link').forEach(n=>n.remove());
 for(const card of document.querySelectorAll('#documents .document')){
  const urls=[...card.querySelectorAll('a')].map(a=>a.href);
  for(const row of approvedAnalyses.filter(r=>r.document&&urls.includes(r.document.url))){
   const p=document.createElement('p');p.className='analysis-document-link';
   const a=document.createElement('a');a.href=analysisLink(row);a.textContent=al(3)+' · '+row.document.version_label;
   p.append(a);card.append(p);
  }
 }
}
const analysisOldCommunity=communityRows;
communityRows=function(){const saved=publicCommunity;if(saved)publicCommunity={...saved,entries:saved.entries.filter(e=>!approvedAnalyses.some(r=>r.article===e.article))};try{analysisOldCommunity()}finally{publicCommunity=saved}};
const analysisOldRender=render;render=function(){analysisOldRender();renderAnalysis()};
const analysisOldDocs=docs;docs=function(){analysisOldDocs();analysisDocumentLinks()};
async function loadAnalysis(){
 if(!window.COP31_DATA?.analysis)return;
 try{
  const response=await fetch(dataURL('analysis'));if(!response.ok)return;
  const index=await response.json();if(index?.schema!==1||!Array.isArray(index.entries)||Object.keys(index).some(k=>!['schema','entries'].includes(k)))return;
  const ids=new Set();if(index.entries.some(r=>!r||!analysisSlug(r.article)||ids.has(r.article)||!ids.add(r.article)))return;
  const rows=[];
  // Sequential and once per page load: avoids a burst of requests on low-power devices.
  for(const row of index.entries){try{
   const base=new URL(dataURL('analysis'),location.href);const u=new URL('articles/'+row.article+'.json',base);
   if(u.origin!==location.origin)continue;
   const r=await fetch(u.href);if(!r.ok)continue;const a=await r.json();
   if(analysisAllowed(row,a))rows.push({...row,content:a});
  }catch{}}
  // Broken supersession and cycles must never appear as a current analysis.
  const valid=row=>{const seen=new Set();let cur=row;while(cur?.superseded_by){if(seen.has(cur.article))return false;seen.add(cur.article);cur=rows.find(r=>r.article===cur.superseded_by);if(!cur)return false}return true};
  approvedAnalyses=rows.filter(valid).sort((a,b)=>Date.parse(b.content.approved_at)-Date.parse(a.content.approved_at));
  renderAnalysis();
 }catch{/* Fail closed; no empty or misleading public section. */}
}
loadAnalysis();
