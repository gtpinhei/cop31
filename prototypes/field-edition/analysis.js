/* Approved-only Field Edition teasers. Shared gates in analysis-core.js. */
const al=i=>(ANALYSIS_LABELS[lang]||ANALYSIS_LABELS.en)[i];
const detailLabels={
 en:['What changed','Why it matters','What to watch','Read full analysis','Back to document feed','Analysis of this version only. A draft is not an adopted outcome.','Withdrawn','Replaced','Current status unverified','Reviewed document version no longer matches the catalogue','Open exact document version','Original-language summary','Version history'],
 pt:['O que mudou','Por que importa','O que observar','Ler análise completa','Voltar aos textos','Análise apenas desta versão. Uma minuta não é um resultado adotado.','Retirado','Substituído','Status atual não verificado','A versão analisada não corresponde mais ao catálogo','Abrir a versão exata','Resumo no idioma original','Histórico de versões'],
 es:['Qué cambió','Por qué importa','Qué observar','Leer análisis completo','Volver a los textos','Análisis solo de esta versión. Un borrador no es un resultado adoptado.','Retirado','Sustituido','Estado actual no verificado','La versión analizada ya no coincide con el catálogo','Abrir la versión exacta','Resumen en idioma original','Historial de versiones'],
 fr:['Ce qui a changé','Pourquoi cela compte','À surveiller','Lire l’analyse complète','Retour aux textes','Analyse de cette version uniquement. Un projet n’est pas un résultat adopté.','Retiré','Remplacé','Statut actuel non vérifié','La version analysée ne correspond plus au catalogue','Ouvrir la version exacte','Résumé dans la langue originale','Historique des versions'],
 ru:['Что изменилось','Почему это важно','За чем следить','Читать полный анализ','К списку документов','Анализ только этой версии. Проект не является принятым решением.','Отозван','Заменён','Текущий статус не проверен','Рассмотренная версия больше не совпадает с каталогом','Открыть точную версию','Резюме на языке оригинала','История версий'],
 zh:['有哪些变化','为何重要','关注下一步','阅读全文分析','返回文件列表','仅分析此版本。草案不等于已通过的成果。','已撤回','已替换','当前状态未核实','分析版本与目录不再匹配','打开确切版本','原文语言摘要','版本历史'],
 ar:['ما الذي تغير','لماذا يهم','ما الذي نترقبه','قراءة التحليل الكامل','العودة إلى قائمة الوثائق','تحليل لهذه النسخة فقط. المسودة ليست نتيجة معتمدة.','سُحبت','استُبدلت','الحالة الحالية غير متحقق منها','النسخة التي حُللت لم تعد مطابقة للفهرس','فتح النسخة المحددة','ملخص باللغة الأصلية','سجل النسخ']};
const aiLabels={en:'AI-generated',pt:'Gerado por IA',es:'Generado por IA',fr:'Généré par IA',ru:'Создано ИИ',zh:'AI 生成',ar:'مولّد بالذكاء الاصطناعي'};
let approvedAnalyses=[];
function analysisLink(row){return classicURL('hoje/leitura/'+row.article)}
function analysisTitle(a){const tr=a.i18n?.[lang],complete=!!(tr?.title&&(!a.standfirst||tr.standfirst));return {title:complete?tr.title:a.title,summary:complete?(tr.standfirst||''):(a.standfirst||''),language:complete?lang:(a.language||'pt-BR'),pending:lang!==(a.language||'pt')&&!complete}}
function analysisTeaser(row,compact=false){
 const a=row.content,v=analysisTitle(a),kind=al(row.format==='daily-diplomacy-brief'?1:2);
 const next=approvedAnalyses.find(r=>r.article===row.superseded_by);
 const labels=detailLabels[lang]||detailLabels.en,state=row.document?analysisDocumentState(row,data.documents):null,warning=state?({withdrawn:6,replaced:7,unknown:8,version_mismatch:9}[state.status]):null;
 return `<article class="post">${a.ai_provenance?`<p class="badge">${esc(aiLabels[lang]||aiLabels.en)}</p>`:''}${warning!=null?`<p class="analysis-warning">${esc(labels[warning])}</p>`:''}<p class="meta">${esc(kind)}${row.reporting_date?' · '+esc(row.reporting_date):''}</p><h3 lang="${esc(v.language)}" dir="auto"><a href="${esc(analysisLink(row))}">${esc(v.title)}</a></h3>${!compact&&v.summary?`<p lang="${esc(v.language)}" dir="auto">${esc(v.summary)}</p>`:''}${v.pending?`<p class="subtle">${esc(al(8))}</p>`:''}${row.document?`<p class="meta">${esc(al(4))}: <a href="${safeURL(row.document.url)}"><bdi>${esc(row.document.version_label)}</bdi></a> · <bdi>${esc(date(row.document.reviewed_at))}</bdi></p><p class="meta">${row.comparison.status==='not_assessed'?esc(al(6)):`${esc(al(7))}: <a href="${safeURL(row.comparison.baseline.url)}"><bdi>${esc(row.comparison.baseline.version_label)}</bdi></a>`}</p>`:''}${next?`<p class="badge">${esc(al(5))}: <a href="${esc(analysisLink(next))}" dir="auto">${esc(analysisTitle(next.content).title)}</a></p>`:''}</article>`;
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
 const labels=detailLabels[lang]||detailLabels.en;
 for(const card of document.querySelectorAll('#documents .document')){
  const genericStatus=card.querySelector('.document-comparison-status'),genericNote=card.querySelector('.document-comparison-note');if(genericStatus)genericStatus.textContent=t(19);if(genericNote)genericNote.hidden=false;
  const doc=data.documents?.documents?.find(d=>String(d.id)===card.dataset.documentId);
  if(!doc)continue;
  for(const row of approvedAnalyses.filter(r=>analysisMatchesDocument(r,doc))){
   if(row.comparison.status==='compared'){const status=card.querySelector('.document-comparison-status'),note=card.querySelector('.document-comparison-note');if(status)status.textContent=al(7)+' · '+row.comparison.baseline.version_label;if(note)note.hidden=true;}
   const panel=document.createElement('section');panel.className='analysis-document-link analysis-inline';
   panel.setAttribute('aria-label',al(2)+' · '+row.document.version_label);
   if(row.content.ai_provenance){const badge=document.createElement('p');badge.className='badge';badge.textContent=aiLabels[lang]||aiLabels.en;panel.append(badge)}
   const status=analysisDocumentState(row,data.documents);
   const warning={withdrawn:6,replaced:7,unknown:8,version_mismatch:9}[status.status];
   if(warning!=null){const p=document.createElement('p');p.className='analysis-warning';p.textContent=labels[warning];panel.append(p)}
   const summary=row.summary;
   if(summary){
    const body=document.createElement('div');body.lang=summary.language;body.dir='auto';
    const heading=document.createElement('h3');heading.textContent=labels[0];body.append(heading);
    const ul=document.createElement('ul');summary.changes.forEach(change=>{const li=document.createElement('li');li.textContent=change;li.dir='auto';ul.append(li)});body.append(ul);
    const significance=document.createElement('div');significance.className='analysis-significance';
    const title=document.createElement('h3');title.textContent=labels[1];const text=document.createElement('p');text.textContent=summary.significance;text.dir='auto';significance.append(title,text);body.append(significance);panel.append(body);
    if(summary.language!==lang){const note=document.createElement('p');note.className='meta';note.textContent=labels[11]+' · '+summary.language;panel.append(note)}
   }
   const context=document.createElement('p');context.className='meta';context.textContent=labels[5];panel.append(context);
   const a=document.createElement('a');a.className='analysis-read';a.href=analysisLink(row);a.textContent=labels[3]+' · '+row.document.version_label;
   panel.append(a);card.append(panel);
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
  approvedAnalyses=rows.filter(valid).sort((a,b)=>Date.parse(b.content.approved_at||b.content.ai_provenance?.generated_at)-Date.parse(a.content.approved_at||a.content.ai_provenance?.generated_at));
  renderAnalysis();
 }catch{/* Fail closed; no empty or misleading public section. */}
}
loadAnalysis();
