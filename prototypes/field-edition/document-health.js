/* One centrally collected public feed; visitors never poll UNFCCC. */
const DH={
en:['Last successful check','Last attempt','Updates delayed; showing the last available catalog.','Document feed unavailable.','Withdrawn records','Refresh documents','Updated centrally; refresh to see new documents.'],
pt:['Última consulta bem-sucedida','Última tentativa','Atualizações atrasadas; exibindo o último catálogo disponível.','Feed de documentos indisponível.','Registros retirados','Atualizar documentos','Atualizado centralmente; atualize a página para ver novos documentos.'],
es:['Última consulta correcta','Último intento','Actualizaciones retrasadas; se muestra el último catálogo disponible.','Feed de documentos no disponible.','Registros retirados','Actualizar documentos','Actualización centralizada; actualice para ver nuevos documentos.'],
fr:['Dernière vérification réussie','Dernière tentative','Mises à jour retardées ; dernier catalogue disponible affiché.','Flux documentaire indisponible.','Entrées retirées','Actualiser les documents','Mise à jour centralisée ; actualisez pour voir les nouveaux documents.'],
ru:['Последняя успешная проверка','Последняя попытка','Обновления задерживаются; показан последний доступный каталог.','Лента документов недоступна.','Отозванные записи','Обновить документы','Централизованное обновление; обновите страницу для новых документов.'],
zh:['上次成功检查','上次尝试','更新延迟；显示最近可用的目录。','文件信息流不可用。','已撤回记录','刷新文件','由中央系统更新；刷新以查看新文件。'],
ar:['آخر فحص ناجح','آخر محاولة','تأخرت التحديثات؛ يُعرض آخر دليل متاح.','موجز الوثائق غير متاح.','السجلات المسحوبة','تحديث الوثائق','تحديث مركزي؛ حدّث لعرض الوثائق الجديدة.']};
function documentHealth(){if(!data)return;const d=data.documents,h=DH[lang],live=!!window.COP31_DATA?.documents;let msg;
if(d.load_failed)msg=h[3];else if(live){const count=d.documents.filter(x=>x.withdrawn||x.withdrawn_at||x.status==='withdrawn').length;msg=[h[0]+': '+date(d.last_success),h[1]+': '+date(d.last_attempt),d.degraded?h[2]:'',count?h[4]+': '+count:'',h[6]].filter(Boolean).join(' · ')}
if(msg){text('doc-status',msg);text('texts-status',msg)}
let b=$('refresh-documents');if(live&&!b){b=document.createElement('button');b.id='refresh-documents';b.type='button';$('texts-status').after(b);b.onclick=async()=>{b.disabled=true;try{const r=await fetch(dataURL('documents'),{cache:'no-store'});if(!r.ok)throw Error('documents');const v=await r.json();data.documents=normalizeDocuments(v);render()}catch{data.documents={...data.documents,degraded:true};text('texts-status',h[2])}finally{b.disabled=false}}}if(b)b.textContent=h[5];
}
const beforeDocumentHealthRender=render;render=function(){beforeDocumentHealthRender();documentHealth()};
