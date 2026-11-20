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

/* Device-local only: classify changes without claiming a substantive text comparison. */
const VISIT_KEY='cop31.documents.visit.v1'; // Keep the storage key; schema v1 safely re-seeds once.
const VISIT_LABEL={
 en:['Since your previous visit','New records','PDF file changed','Withdrawn','Reinstated','Other record updates','Compared with the last catalog you viewed. A changed PDF file may still have the same wording. Saved only in this browser.','Reset comparison','No changes to show.'],
 pt:['Desde sua visita anterior','Novos registros','Arquivo PDF alterado','Retirados','Restabelecidos','Outras atualizações de registros','Comparação com o último catálogo que você viu. Alterações no arquivo PDF não comprovam mudanças no texto. Salvo apenas neste navegador.','Reiniciar comparação','Nenhuma alteração a mostrar.'],
 es:['Desde su visita anterior','Registros nuevos','PDF con cambios en el archivo','Retirados','Restablecidos','Otras actualizaciones de registros','Comparación con el último catálogo que consultó. Un cambio en el archivo PDF no equivale a una comparación del texto. Guardado solo en este navegador.','Reiniciar comparación','No hay cambios que mostrar.'],
 fr:['Depuis votre visite précédente','Nouvelles entrées','Fichiers PDF modifiés','Retirés','Rétablis','Autres mises à jour','Comparaison avec le dernier catalogue consulté. La modification d’un fichier PDF ne prouve pas un changement de texte. Enregistré dans ce navigateur uniquement.','Réinitialiser la comparaison','Aucun changement à afficher.'],
 ru:['С предыдущего посещения','Новые записи','Изменённые файлы PDF','Отозваны','Восстановлены','Другие обновления записей','Сравнение с последним просмотренным каталогом. Изменение файла PDF не означает изменения текста. Хранится только в этом браузере.','Сбросить сравнение','Нет изменений для отображения.'],
 zh:['自上次访问以来','新记录','PDF 文件有变动','已撤回','已恢复','其他记录更新','与上次查看的目录比较。PDF 文件变动不代表文本内容发生变化。仅保存在此浏览器中。','重置比较','没有可显示的变更。'],
 ar:['منذ زيارتك السابقة','سجلات جديدة','ملفات PDF تغيّرت','مسحوبة','أُعيد إدراجها','تحديثات أخرى للسجلات','مقارنة بآخر دليل اطّلعت عليه. تغيّر ملف PDF لا يثبت تغيّر النص. تُحفظ في هذا المتصفح فقط.','إعادة ضبط المقارنة','لا توجد تغييرات لعرضها.']};
let visitBaseline,visitStorageOK=true,visitSavedSignature='';
const visitHash=h=>typeof h==='string'&&/^[a-f0-9]{64}$/.test(h);
function catalogVisitRecords(catalog){
 const rows=catalog.documents, records=Object.create(null);
 if(rows.length>5000)return null;
 for(const d of rows){
  const id=String(d?.id??'');
  if(!/^[A-Za-z0-9_-]{1,80}$/.test(id)||Object.hasOwn(records,id))return null;
  const attachments=Array.isArray(d.attachments)?d.attachments:[];
  const links=attachments.map(a=>JSON.stringify([a?.language||'',a?.url||''])).sort();
  const hashes=Object.create(null);
  if(catalog.verification_mode==='pdf-hashes')for(const a of attachments){
   if(typeof a?.language!=='string'||!a.language)continue;
   const language=a.language.toLowerCase();
   if(!Object.hasOwn(hashes,language))hashes[language]=[];
   hashes[language].push(visitHash(a.sha256)?a.sha256:'');
  }
  for(const values of Object.values(hashes))values.sort();
  records[id]={
   withdrawn:!!(d.withdrawn||d.withdrawn_at||d.status==='withdrawn'),
   meta:JSON.stringify([d.title,d.symbol,d.body,d.agenda,d.version,d.status,d.url,d.published,links]),
   hashes
  };
 }
 return records;
}
function catalogVisitCounts(previous,records){
 const counts=[0,0,0,0,0];
 for(const [id,next] of Object.entries(records)){
  if(!Object.hasOwn(previous,id)){if(!next.withdrawn)counts[0]++;continue}
  const old=previous[id];
  if(!old||typeof old.withdrawn!=='boolean'||typeof old.meta!=='string'||!old.hashes||typeof old.hashes!=='object')continue;
  if(old.withdrawn!==next.withdrawn){counts[next.withdrawn?2:3]++;continue}
  if(next.withdrawn)continue;
  // Only a one-to-one fingerprint change in the same recorded language is conclusive.
  // New translations, unverified links and ambiguous multiple files are not called revisions.
  const revised=Object.entries(next.hashes).some(([language,current])=>{
   if(!Object.hasOwn(old.hashes,language))return false;
   const prior=old.hashes[language];
   return Array.isArray(prior)&&prior.length===1&&visitHash(prior[0])&&current.length===1&&visitHash(current[0])&&prior[0]!==current[0]
  });
  if(revised)counts[1]++;
  else if(old.meta!==next.meta)counts[4]++;
 }
 return counts;
}
function readCatalogVisit(){
 let old;try{old=JSON.parse(localStorage.getItem(VISIT_KEY))}catch(e){
  if(!(e instanceof SyntaxError))throw e;
 }
 return old&&old.schema===2&&Number.isFinite(Date.parse(old.checked))&&old.records&&typeof old.records==='object'&&!Array.isArray(old.records)?old:null;
}
function documentVisitSummary(){
 let box=$('document-visit');if(box)box.hidden=true;
 if(!data||!window.COP31_DATA?.documents||data.documents.load_failed||!data.documents.documents.length||$('texts').hidden||document.visibilityState==='hidden')return;
 const check=data.documents.last_success||data.documents.checked_at;
 if(!Number.isFinite(Date.parse(check))||data.documents.degraded)return;
 const records=catalogVisitRecords(data.documents);
 if(!records)return;
 const signature=JSON.stringify(records);
 if(visitBaseline===undefined){try{visitBaseline=readCatalogVisit()}catch{visitBaseline=null;visitStorageOK=false}}
 if(visitBaseline&&Date.parse(check)<Date.parse(visitBaseline.checked))return;
 if(visitStorageOK&&signature!==visitSavedSignature){try{
  const latest=readCatalogVisit();
  if(!latest||Date.parse(check)>=Date.parse(latest.checked)){
   localStorage.setItem(VISIT_KEY,JSON.stringify({schema:2,checked:check,records}));visitSavedSignature=signature;
  }
 }catch{visitStorageOK=false}}
 if(!box){box=document.createElement('section');box.id='document-visit';box.className='freshness';$('texts-status').after(box)}
 box.hidden=!visitBaseline||!visitStorageOK;
 if(box.hidden)return;
 const counts=catalogVisitCounts(visitBaseline.records,records),labels=VISIT_LABEL[lang]||VISIT_LABEL.en;
 const format=new Intl.NumberFormat(lang);
 const changes=counts.flatMap((n,i)=>n?[esc(labels[i+1])+': <bdi>'+esc(format.format(n))+'</bdi>']:[]);
 const markup=`<strong>${esc(labels[0])}</strong><p>${changes.length?changes.join(' · '):esc(labels[8])}</p><p>${esc(labels[6])}</p><button type="button">${esc(labels[7])}</button>`;
 if(box._visitMarkup!==markup){box.innerHTML=markup;box._visitMarkup=markup}
 box.querySelector('button').onclick=()=>{visitBaseline={schema:2,checked:check,records};documentVisitSummary();box.querySelector('button')?.focus()};
}
const beforeVisitHealth=documentHealth;documentHealth=function(){beforeVisitHealth();documentVisitSummary()};
window.addEventListener('hashchange',documentVisitSummary);
document.addEventListener('visibilitychange',documentVisitSummary);

/* Public, bounded change log. Events record detection, not negotiation outcomes.
   No previous PDFs are fabricated and no metadata version is called a revision. */
const HISTORY_LABEL={
 en:['Recent catalog changes','New record','PDF changed','Withdrawn','Reinstated','Latest 20 retained events. Times show detection, not publication. This is not a complete text-version history.','View official record'],
 pt:['Alterações recentes no catálogo','Novo registro','PDF alterado','Retirado','Restabelecido','Últimos 20 eventos retidos. Os horários indicam detecção, não publicação. Não é um histórico completo das versões dos textos.','Ver registro oficial'],
 es:['Cambios recientes del catálogo','Registro nuevo','PDF modificado','Retirado','Restablecido','Últimos 20 eventos conservados. Las horas indican detección, no publicación. No es un historial completo de versiones de textos.','Ver registro oficial'],
 fr:['Changements récents du catalogue','Nouvelle entrée','PDF modifié','Retiré','Rétabli','Les 20 derniers événements conservés. Les heures indiquent la détection, pas la publication. Ce n’est pas un historique complet des versions des textes.','Voir la fiche officielle'],
 ru:['Последние изменения каталога','Новая запись','PDF изменён','Отозвано','Восстановлено','Последние 20 сохранённых событий. Указано время обнаружения, не публикации. Это не полная история версий текстов.','Открыть официальную запись'],
 zh:['最近的目录变更','新记录','PDF 已更改','已撤回','已恢复','最近保留的 20 条事件。时间表示检测时间，而非发布时间。这不是完整的文本版本历史。','查看官方记录'],
 ar:['أحدث تغييرات الدليل','سجل جديد','تغيّر ملف PDF','سُحب','أُعيد إدراجه','آخر 20 حدثاً محفوظاً. الأوقات هي أوقات الرصد وليست النشر. هذا ليس سجلاً كاملاً لإصدارات النصوص.','عرض السجل الرسمي']};
function documentHistory(){
 if(!data||!window.COP31_DATA?.documents)return;
 let box=$('document-history');
 if(!box){box=document.createElement('details');box.id='document-history';box.className='freshness';$('document-coverage').after(box)}
 const records=new Map(data.documents.documents.map(d=>[String(d.id),d]));
 const kinds={new:1,revised:2,withdrawn:3,reinstated:4},seen=new Set();
 const events=(Array.isArray(data.documents.changes)?data.documents.changes:[]).filter(e=>{
  if(!e||!Object.hasOwn(kinds,e.change)||!records.has(String(e.document_id))||!Number.isFinite(Date.parse(e.at))||!e.event_id||seen.has(e.event_id))return false;
  seen.add(e.event_id);return true;
 }).sort((a,b)=>Date.parse(b.at)-Date.parse(a.at)).slice(0,20);
 box.hidden=!events.length;if(box.hidden)return;
 const h=HISTORY_LABEL[lang];const markup=`<summary>${esc(h[0])} · ${events.length}</summary><p>${esc(h[5])}</p><ol>`+events.map(e=>{
  const row=records.get(String(e.document_id));
  return `<li><p><strong>${esc(h[kinds[e.change]])}</strong> · <bdi>${esc(date(e.at))}</bdi></p><p lang="en" dir="auto">${esc(row.title)}</p><a href="${safeURL(row.source_url)}">${esc(h[6])} ↗</a></li>`;
 }).join('')+'</ol>';
 if(box._historyMarkup!==markup){box.innerHTML=markup;box._historyMarkup=markup}
}
const beforeHistoryHealth=documentHealth;documentHealth=function(){beforeHistoryHealth();documentHistory()};
