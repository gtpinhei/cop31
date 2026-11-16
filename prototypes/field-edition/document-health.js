/* One centrally collected public feed; visitors never poll UNFCCC. */
const DH={
en:['Last successful check','Last attempt','Updates delayed; showing the last available catalog.','Document feed unavailable.','Withdrawn records','Refresh documents','Checks for updates every ten minutes while this page is visible.'],
pt:['Última consulta bem-sucedida','Última tentativa','Atualizações atrasadas; exibindo o último catálogo disponível.','Feed de documentos indisponível.','Registros retirados','Atualizar documentos','Verifica atualizações a cada dez minutos enquanto a página está visível.'],
es:['Última consulta correcta','Último intento','Actualizaciones retrasadas; se muestra el último catálogo disponible.','Feed de documentos no disponible.','Registros retirados','Actualizar documentos','Busca actualizaciones cada diez minutos mientras la página está visible.'],
fr:['Dernière vérification réussie','Dernière tentative','Mises à jour retardées ; dernier catalogue disponible affiché.','Flux documentaire indisponible.','Entrées retirées','Actualiser les documents','Recherche des mises à jour toutes les dix minutes lorsque cette page est visible.'],
ru:['Последняя успешная проверка','Последняя попытка','Обновления задерживаются; показан последний доступный каталог.','Лента документов недоступна.','Отозванные записи','Обновить документы','Проверка обновлений каждые десять минут, пока страница видна.'],
zh:['上次成功检查','上次尝试','更新延迟；显示最近可用的目录。','文件信息流不可用。','已撤回记录','刷新文件','页面可见时，每十分钟检查一次更新。'],
ar:['آخر فحص ناجح','آخر محاولة','تأخرت التحديثات؛ يُعرض آخر دليل متاح.','موجز الوثائق غير متاح.','السجلات المسحوبة','تحديث الوثائق','يتحقق من التحديثات كل عشر دقائق أثناء ظهور الصفحة.']};
const COVERAGE={en:'DACS catalog only. Presidency consultations may publish additional texts.',pt:'Somente o catálogo DACS. As consultas da Presidência podem publicar textos adicionais.',es:'Solo el catálogo DACS. Las consultas de la Presidencia pueden publicar textos adicionales.',fr:'Catalogue DACS uniquement. Les consultations de la Présidence peuvent publier d’autres textes.',ru:'Только каталог DACS. На странице консультаций председательства могут появляться другие тексты.',zh:'仅涵盖 DACS 目录。主席国磋商页面可能发布其他文本。',ar:'دليل DACS فقط. قد تنشر مشاورات الرئاسة نصوصاً إضافية.'};
const VERIFY={en:['Metadata monitoring; text revisions are not verified.','PDF fingerprints checked; political significance is not automatically assessed.'],pt:['Monitoramento de metadados; revisões do texto não verificadas.','Impressões digitais dos PDFs verificadas; significado político não avaliado automaticamente.'],es:['Seguimiento de metadatos; revisiones del texto no verificadas.','Huellas digitales PDF verificadas; significado político no evaluado automáticamente.'],fr:['Suivi des métadonnées ; révisions du texte non vérifiées.','Empreintes PDF vérifiées ; portée politique non évaluée automatiquement.'],ru:['Мониторинг метаданных; изменения текста не проверены.','Контрольные суммы PDF проверены; политическое значение автоматически не оценивается.'],zh:['监测元数据；尚未核实文本修订。','已核对 PDF 指纹；不会自动评估政治意义。'],ar:['رصد البيانات الوصفية؛ لم تُتحقق تعديلات النص.','فُحصت بصمات ملفات PDF؛ لا يُقيّم المعنى السياسي تلقائياً.']};
function documentHealth(){if(!data)return;const d=data.documents,h=DH[lang],live=!!window.COP31_DATA?.documents;let msg;
if(d.load_failed)msg=h[3];else if(live){const count=d.documents.filter(x=>x.withdrawn||x.withdrawn_at||x.status==='withdrawn').length;msg=[h[0]+': '+date(d.last_success),h[1]+': '+date(d.last_attempt),(d.degraded||!Number.isFinite(Date.parse(d.last_success))||Date.now()-Date.parse(d.last_success)>30*60*1000)?h[2]:'',count?h[4]+': '+count:'',VERIFY[lang][d.verification_mode==='pdf-hashes'?1:0],h[6]].filter(Boolean).join(' · ')}
if(msg){text('doc-status',msg);text('texts-status',msg)}
let coverage=$('document-coverage');if(!coverage){coverage=document.createElement('p');coverage.id='document-coverage';coverage.className='freshness';$('texts-status').after(coverage)}coverage.innerHTML=`<a href="https://unfccc.int/process-and-meetings/conferences/un-climate-change-conference-antalya-november-2026/cop-31/cmp-21/cma-8-presidency-consultations">${esc(COVERAGE[lang])}</a>`;
let b=$('refresh-documents');if(live&&!b){b=document.createElement('button');b.id='refresh-documents';b.type='button';$('texts-status').after(b);b.onclick=()=>checkDocumentUpdates(true)}if(b){b.textContent=h[5];b.disabled=!!documentRequest}showDocumentUpdates();startDocumentUpdates();
}
const beforeDocumentHealthRender=render;render=function(){beforeDocumentHealthRender();documentHealth()};

/* Check only our cacheable central projection, never a visitor-side UNFCCC collector.
   A changed catalog is staged until the reader chooses to apply it. */
const DOCUMENT_CHECK_MS=10*60*1000;
const UPDATE_LABEL={en:'New document updates available · Show updates',pt:'Novas atualizações de documentos · Mostrar atualizações',es:'Hay actualizaciones de documentos · Mostrar actualizaciones',fr:'Nouvelles mises à jour des documents · Afficher',ru:'Доступны обновления документов · Показать',zh:'有新的文件更新 · 显示更新',ar:'تتوفر تحديثات جديدة للوثائق · عرض التحديثات'};
let documentRequest=null,pendingDocuments=null,documentTimer=null,lastDocumentCheck=Date.now(),documentUpdatesStarted=false;
function documentSignature(v){return JSON.stringify(v.documents)}
function showDocumentUpdates(){
 for(const status of ['doc-status','texts-status']){
  let notice=$(status+'-updates');
  if(!notice){notice=document.createElement('div');notice.id=status+'-updates';notice.setAttribute('role','status');const button=document.createElement('button');button.type='button';button.onclick=applyDocumentUpdates;notice.appendChild(button);$(status).after(notice)}
  notice.hidden=!pendingDocuments;notice.firstChild.textContent=UPDATE_LABEL[lang];
 }
}
function applyDocumentUpdates(){
 if(!pendingDocuments)return;
 const x=window.scrollX,y=window.scrollY;data.documents=pendingDocuments;pendingDocuments=null;
 render();window.scrollTo(x,y);
}
async function checkDocumentUpdates(apply=false){
 if(!data||!window.COP31_DATA?.documents)return;
 if(!documentRequest){
  lastDocumentCheck=Date.now();
  documentRequest=(async()=>{
   const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);
   try{const response=await fetch(dataURL('documents'),{cache:'no-cache',signal:controller.signal});if(!response.ok)throw Error('documents');return normalizeDocuments(await response.json())}finally{clearTimeout(timeout)}
  })();
 }
 const request=documentRequest;const b=$('refresh-documents');if(b)b.disabled=true;
 try{
  const fresh=await request;
  if(documentSignature(fresh)!==documentSignature(data.documents)||data.documents.load_failed){pendingDocuments=fresh;if(apply)applyDocumentUpdates()}
  else {data.documents={...fresh,documents:data.documents.documents};pendingDocuments=null}
 }catch{data.documents={...data.documents,degraded:true}}finally{
  if(documentRequest===request)documentRequest=null;
  documentHealth();scheduleDocumentUpdate();
 }
}
function scheduleDocumentUpdate(){
 clearTimeout(documentTimer);documentTimer=null;
 if(document.visibilityState==='hidden'||!window.COP31_DATA?.documents)return;
 documentTimer=setTimeout(()=>{documentTimer=null;if(document.visibilityState!=='hidden')checkDocumentUpdates()},Math.max(0,DOCUMENT_CHECK_MS-(Date.now()-lastDocumentCheck)));
}
function startDocumentUpdates(){
 if(documentUpdatesStarted||!window.COP31_DATA?.documents)return;
 documentUpdatesStarted=true;lastDocumentCheck=Date.now();
 document.addEventListener('visibilitychange',scheduleDocumentUpdate);scheduleDocumentUpdate();
}

/* This browser only: compare catalog records with the previous page visit.
   These labels never imply substantive PDF changes or editorial verification. */
const VISIT_KEY='cop31.documents.visit.v1';
const VISIT_LABEL={
 en:['Since your previous visit','New records','Updated records','Catalog records only; not a comparison of negotiating text. Saved only in this browser.','Reset comparison'],
 pt:['Desde sua visita anterior','Novos registros','Registros atualizados','Somente registros do catálogo; não é uma comparação dos textos de negociação. Salvo apenas neste navegador.','Reiniciar comparação'],
 es:['Desde su visita anterior','Registros nuevos','Registros actualizados','Solo registros del catálogo; no es una comparación de textos de negociación. Guardado solo en este navegador.','Reiniciar comparación'],
 fr:['Depuis votre visite précédente','Nouvelles entrées','Entrées mises à jour','Entrées du catalogue uniquement ; pas une comparaison des textes de négociation. Enregistré dans ce navigateur uniquement.','Réinitialiser la comparaison'],
 ru:['С предыдущего посещения','Новые записи','Обновлённые записи','Только записи каталога, не сравнение переговорных текстов. Сохранено только в этом браузере.','Сбросить сравнение'],
 zh:['自上次访问以来','新记录','已更新记录','仅比较目录记录，并非谈判文本比较。仅保存在此浏览器中。','重置比较'],
 ar:['منذ زيارتك السابقة','سجلات جديدة','سجلات محدّثة','سجلات الدليل فقط، وليست مقارنة لنصوص التفاوض. تُحفظ في هذا المتصفح فقط.','إعادة ضبط المقارنة']};
let visitBaseline,visitStorageOK=true,visitSavedSignature='';
function catalogVisitRecords(){return Object.fromEntries(data.documents.documents.filter(d=>d.id!=null).slice(0,5000).map(d=>[String(d.id),JSON.stringify([d.title,d.symbol,d.body,d.agenda,d.version,d.status,d.withdrawn, d.url,d.attachments?.map(a=>[a.url,a.sha256])])]))}
function documentVisitSummary(){
 if($('document-visit'))$('document-visit').hidden=true;
 if(!data||!window.COP31_DATA?.documents||data.documents.load_failed||!data.documents.documents.length)return;
 const records=catalogVisitRecords(),signature=JSON.stringify(records);
 if(visitBaseline===undefined){try{const raw=localStorage.getItem(VISIT_KEY);let old;try{old=JSON.parse(raw)}catch{old=null}visitBaseline=old&&old.schema===1&&old.records&&typeof old.records==='object'&&!Array.isArray(old.records)?old:null}catch{visitBaseline=null;visitStorageOK=false}}
 // Do not overwrite a good comparison with a failed, partial or older snapshot.
 const check=data.documents.last_success||data.documents.checked_at;
 if(!Number.isFinite(Date.parse(check))||data.documents.degraded)return;
 if(visitBaseline&&Date.parse(check)<Date.parse(visitBaseline.checked))return;
 if(visitStorageOK&&signature!==visitSavedSignature){try{localStorage.setItem(VISIT_KEY,JSON.stringify({schema:1,checked:check,records}));visitSavedSignature=signature}catch{visitStorageOK=false}}
 let box=$('document-visit');if(!box){box=document.createElement('section');box.id='document-visit';box.className='freshness';$('texts-status').after(box)}
 box.hidden=!visitBaseline||!visitStorageOK;
 if(box.hidden)return;
 let added=0,changed=0;for(const [id,value] of Object.entries(records)){if(!Object.hasOwn(visitBaseline.records,id))added++;else if(visitBaseline.records[id]!==value)changed++}
 const labels=VISIT_LABEL[lang];box.innerHTML=`<strong>${esc(labels[0])}</strong><p>${esc(labels[1])}: ${added} · ${esc(labels[2])}: ${changed}</p><p>${esc(labels[3])}</p><button type="button">${esc(labels[4])}</button>`;
 box.querySelector('button').onclick=()=>{visitBaseline={schema:1,checked:check,records};documentVisitSummary()};
}
const beforeVisitHealth=documentHealth;documentHealth=function(){beforeVisitHealth();documentVisitSummary()};
