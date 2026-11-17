/* Version context on the existing canonical article page, never a second article body. */
(()=>{
 let current=null,indexPromise=null;
 const safeText=(tag,value)=>{const e=document.createElement(tag);e.textContent=value;return e};
 function index(){if(!indexPromise)indexPromise=fetch('data/analysis.json').then(r=>r.ok?r.json():null).catch(()=>null);return indexPromise}
 async function update(detail){
  current=detail;const token=detail;
  document.getElementById('analysis-version-context')?.remove();
  if(detail.preview)return;
  const data=await index();if(current!==token||!data||data.schema!==1||!Array.isArray(data.entries)||Object.keys(data).some(k=>!['schema','entries'].includes(k)))return;
  const matching=data.entries.filter(r=>r?.article===detail.article.id);
  if(matching.length!==1||!analysisAllowed(matching[0],detail.article))return;
  const row=matching[0],l=ANALYSIS_LABELS[detail.language]||ANALYSIS_LABELS.en;
  const box=document.getElementById('todayArticle');if(!box||box.hidden)return;
  const section=document.createElement('aside');section.id='analysis-version-context';section.className='ti-note';
  section.append(safeText('strong',l[row.format==='daily-diplomacy-brief'?1:2]));
  function source(d,label){const p=safeText('p',label+': '),a=safeText('a',d.version_label);a.href=d.url;a.dir='auto';p.append(a,safeText('span',' · '+d.reviewed_at));section.append(p)}
  if(row.document){source(row.document,l[4]);if(row.comparison.status==='compared')source(row.comparison.baseline,l[7]);else section.append(safeText('p',l[6]))}
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
  if(current===token&&!box.hidden)box.prepend(section);
 }
 document.addEventListener('cop31:article',e=>update(e.detail));
 window.addEventListener('hashchange',()=>{current=null;document.getElementById('analysis-version-context')?.remove()});
})();
