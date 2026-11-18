/* Version context on the existing canonical article page, never a second article body. */
(()=>{
const detailLabels={
 en:['What changed','Why it matters','What to watch','Read full analysis','Back to document feed','Analysis of this version only. A draft is not an adopted outcome.','Withdrawn','Replaced','Current status unverified','Reviewed document version no longer matches the catalogue','Open exact document version','Original-language summary','Version history'],
 pt:['O que mudou','Por que importa','O que observar','Ler análise completa','Voltar aos textos','Análise apenas desta versão. Uma minuta não é um resultado adotado.','Retirado','Substituído','Status atual não verificado','A versão analisada não corresponde mais ao catálogo','Abrir a versão exata','Resumo no idioma original','Histórico de versões'],
 es:['Qué cambió','Por qué importa','Qué observar','Leer análisis completo','Volver a los textos','Análisis solo de esta versión. Un borrador no es un resultado adoptado.','Retirado','Sustituido','Estado actual no verificado','La versión analizada ya no coincide con el catálogo','Abrir la versión exacta','Resumen en idioma original','Historial de versiones'],
 fr:['Ce qui a changé','Pourquoi cela compte','À surveiller','Lire l’analyse complète','Retour aux textes','Analyse de cette version uniquement. Un projet n’est pas un résultat adopté.','Retiré','Remplacé','Statut actuel non vérifié','La version analysée ne correspond plus au catalogue','Ouvrir la version exacte','Résumé dans la langue originale','Historique des versions'],
 ru:['Что изменилось','Почему это важно','За чем следить','Читать полный анализ','К списку документов','Анализ только этой версии. Проект не является принятым решением.','Отозван','Заменён','Текущий статус не проверен','Рассмотренная версия больше не совпадает с каталогом','Открыть точную версию','Резюме на языке оригинала','История версий'],
 zh:['有哪些变化','为何重要','关注下一步','阅读全文分析','返回文件列表','仅分析此版本。草案不等于已通过的成果。','已撤回','已替换','当前状态未核实','分析版本与目录不再匹配','打开确切版本','原文语言摘要','版本历史'],
 ar:['ما الذي تغير','لماذا يهم','ما الذي نترقبه','قراءة التحليل الكامل','العودة إلى قائمة الوثائق','تحليل لهذه النسخة فقط. المسودة ليست نتيجة معتمدة.','سُحبت','استُبدلت','الحالة الحالية غير متحقق منها','النسخة التي حُللت لم تعد مطابقة للفهرس','فتح النسخة المحددة','ملخص باللغة الأصلية','سجل النسخ']};
const aiLabels={en:'AI-generated analysis · Automated evidence checks; not human editorial approval',pt:'Análise gerada por IA · Verificações automatizadas de evidências; sem aprovação editorial humana',es:'Análisis generado por IA · Verificaciones automatizadas de pruebas; sin aprobación editorial humana',fr:'Analyse générée par IA · Vérification automatisée des sources ; sans validation éditoriale humaine',ru:'Анализ ИИ · Автоматическая проверка доказательств; без редакционного одобрения человеком',zh:'AI 生成分析 · 自动证据核查；未经人工编辑批准',ar:'تحليل مولّد بالذكاء الاصطناعي · تحقق آلي من الأدلة؛ دون موافقة تحريرية بشرية'};
 let current=null,indexPromise=null,catalogPromise=null;
 function catalog(){if(!catalogPromise)catalogPromise=fetch('data/negotiating-texts.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null);return catalogPromise}

 const safeText=(tag,value)=>{const e=document.createElement(tag);e.textContent=value;return e};
 function index(){if(!indexPromise)indexPromise=fetch('data/analysis.json').then(r=>r.ok?r.json():null).catch(()=>null);return indexPromise}
 async function update(detail){
  current=detail;const token=detail;
  document.getElementById('analysis-version-context')?.remove();
  if(detail.preview)return;
  const data=await index();if(current!==token||!data||data.schema!==1||!Array.isArray(data.entries)||Object.keys(data).some(k=>!['schema','entries'].includes(k)))return;
  const matching=data.entries.filter(r=>r?.article===detail.article.id);
  if(matching.length!==1||!analysisAllowed(matching[0],detail.article))return;
  const row=matching[0],l=ANALYSIS_LABELS[detail.language]||ANALYSIS_LABELS.en,labels=detailLabels[detail.language]||detailLabels.en;
  const documents=row.document?await catalog():null;if(current!==token)return;
  const box=document.getElementById('todayArticle');if(!box||box.hidden)return;
  const section=document.createElement('aside');section.id='analysis-version-context';section.className='analysis-detail';
  section.append(safeText('strong',l[row.format==='daily-diplomacy-brief'?1:2]));
  if(detail.article.ai_provenance){const ai=detail.article.ai_provenance;section.append(safeText('p',aiLabels[detail.language]||aiLabels.en),safeText('p','AI · '+ai.model+' · '+ai.generated_at),safeText('p','QA · '+ai.qa.checked_at))}
  function source(d,label){const p=safeText('p',label+': '),a=safeText('a',d.version_label);a.href=d.url;a.dir='auto';p.append(a,safeText('span',' · '+d.reviewed_at));section.append(p)}
  if(row.document){
   source(row.document,l[4]);
   section.append(safeText('p','PDF SHA-256 · '+row.document.sha256));
   section.append(safeText('p',({en:'Official source link; its content may change. The hash identifies the reviewed bytes.',pt:'Link da fonte oficial; o conteúdo pode mudar. O hash identifica os bytes analisados.',es:'Enlace oficial; el contenido puede cambiar. El hash identifica los bytes analizados.',fr:'Lien officiel ; son contenu peut changer. Le hash identifie les octets analysés.',ru:'Официальная ссылка; содержимое может измениться. Хеш идентифицирует рассмотренные байты.',zh:'官方来源链接的内容可能变化。哈希标识所审阅的文件字节。',ar:'قد يتغير محتوى الرابط الرسمي. تحدد البصمة الرقمية البايتات التي تمت مراجعتها.'})[detail.language]));
   const back=safeText('a',labels[4]);back.href='index.html?lang='+encodeURIComponent(detail.language)+'#texts';back.className='analysis-back';section.append(back);
   section.append(safeText('p',labels[5]));
   const status=analysisDocumentState(row,documents),warning={withdrawn:6,replaced:7,unknown:8,version_mismatch:9}[status.status];
   if(warning!=null){const p=safeText('p',labels[warning]);p.className='analysis-warning';section.append(p)}
   if(status.replacement)source(status.replacement,labels[7]);
   const history=document.createElement('details'),heading=safeText('summary',labels[12]);history.append(heading);
   if(row.comparison.status==='compared'){const baseline=row.comparison.baseline,sourceNote=detail.article.sources.find(s=>s.url===baseline.url)?.note;if(typeof sourceNote==='string'&&sourceNote.trim()){const note=safeText('p',sourceNote);note.lang=detail.article.language||'pt';note.dir='auto';note.className='analysis-warning';history.append(note)}history.append(safeText('p','PDF SHA-256 · '+baseline.sha256));const p=safeText('p',l[7]+': '),a=safeText('a',baseline.version_label);a.href=row.comparison.baseline.url;p.append(a);history.append(p)}else history.append(safeText('p',l[6]));section.append(history);
   if(row.summary){
    const summary=row.summary,body=document.createElement('div');body.className='analysis-summary';body.lang=summary.language;body.dir='auto';
    body.append(safeText('h3',labels[0]));const ul=document.createElement('ul');summary.changes.forEach(change=>{const li=safeText('li',change);li.dir='auto';ul.append(li)});body.append(ul);
    body.append(safeText('h3',labels[1]),safeText('p',summary.significance),safeText('h3',labels[2]),safeText('p',summary.watch));body.querySelectorAll('p').forEach(p=>p.dir='auto');section.append(body);
    if(summary.language!==detail.language)section.append(safeText('p',labels[11]+' · '+summary.language));
   }
  }
  if(row.reporting_date)section.append(safeText('p',row.reporting_date));
  if(row.superseded_by){
   const p=safeText('p',l[5]+': '+row.superseded_by);section.append(p);
   const next=data.entries.filter(r=>r?.article===row.superseded_by);
   if(next.length===1&&analysisSlug(row.superseded_by)&&next[0].superseded_by!==row.article){
    try{const r=await fetch('data/articles/'+row.superseded_by+'.json');const a=r.ok?await r.json():null;
     if(current!==token)return;
     if(analysisAllowed(next[0],a)){const link=safeText('a',a.i18n?.[detail.language]?.title||a.title);link.href='#hoje/leitura/'+row.superseded_by;p.textContent=l[5]+': ';p.append(link)}
    }catch{/* Keep reviewed-version context and the supersession warning, without an unverified link. */}
   }
  }
  if(current===token&&!box.hidden){
   if(!document.getElementById('analysis-detail-style')){const style=document.createElement('style');style.id='analysis-detail-style';style.textContent='.analysis-detail{font-family:var(--font-ui,system-ui);font-size:16px;font-style:normal;color:var(--fg);max-width:72ch;overflow-wrap:anywhere;padding:1.25rem;border:1px solid currentColor;border-radius:12px;margin-block:1rem 2rem}.analysis-detail h3{margin-block:1.4rem .5rem}.analysis-detail li{margin-block:.5rem;line-height:1.65}.analysis-detail p{line-height:1.65}.analysis-detail a,.analysis-detail summary{display:inline-block;padding-block:.5rem;min-height:44px}.analysis-detail .analysis-warning{font-weight:700;border-inline-start:4px solid currentColor;padding-inline-start:1rem}.analysis-detail .analysis-back{display:block}.analysis-detail details{margin-block:1rem}';document.head.append(style)}
   box.prepend(section);
  }
 }
 document.addEventListener('cop31:article',e=>update(e.detail));
 window.addEventListener('hashchange',()=>{current=null;document.getElementById('analysis-version-context')?.remove()});
})();
