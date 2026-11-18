/* Approved original analysis only. No draft routes, polling, embeds or article bodies. */
const ANALYSIS_LABELS={
 en:['Original analysis','Daily Diplomacy Brief','Text Explained','Read analysis','Reviewed text','Superseded by','Comparison not assessed','Compared with','Original language; translation pending'],
 pt:['Análise original','Boletim diplomático diário','Texto explicado','Ler análise','Texto analisado','Substituída por','Comparação não realizada','Comparado com','Idioma original; tradução pendente'],
 es:['Análisis original','Informe diplomático diario','Texto explicado','Leer análisis','Texto analizado','Sustituido por','Comparación no realizada','Comparado con','Idioma original; traducción pendiente'],
 fr:['Analyse originale','Bulletin diplomatique quotidien','Texte expliqué','Lire l’analyse','Texte analysé','Remplacé par','Comparaison non effectuée','Comparé à','Langue originale ; traduction en attente'],
 ru:['Авторская аналитика','Ежедневный дипломатический обзор','Разбор текста','Читать анализ','Рассмотренный текст','Заменён на','Сравнение не проводилось','Сравнение с','Язык оригинала; перевод ожидается'],
 zh:['原创分析','每日外交简报','文本解读','阅读分析','已审阅文本','已被取代','尚未比较','比较基准','原文语言；翻译待完成'],
 ar:['تحليل أصلي','موجز دبلوماسي يومي','شرح النص','قراءة التحليل','النص الذي جرت مراجعته','حل محله','لم تُجرَ مقارنة','مقارنة مع','اللغة الأصلية؛ الترجمة قيد الانتظار']};
const analysisSlug=v=>typeof v==='string'&&/^[a-z0-9][a-z0-9-]{2,79}$/.test(v);
const analysisTime=v=>typeof v==='string'&&/(Z|[+-]\d\d:\d\d)$/.test(v)&&Number.isFinite(Date.parse(v));
function analysisDocument(d){try{const u=new URL(d.url);return d&&Object.keys(d).every(k=>['url','version_label','reviewed_at','sha256','id'].includes(k))&&(!('id' in d)||(typeof d.id==='string'&&/^[A-Za-z0-9_-]{1,80}$/.test(d.id)))&&u.protocol==='https:'&&['unfccc.int','www.unfccc.int','docs.unfccc.int'].includes(u.hostname)&&!u.username&&!u.password&&!u.port&&typeof d.version_label==='string'&&d.version_label.trim()&&analysisTime(d.reviewed_at)&&/^[a-f0-9]{64}$/.test(d.sha256)}catch{return false}}
function analysisAllowed(row,a){
 if(!row||!a||!analysisSlug(row.article)||a.id!==row.article||a.schema!==1||a.status!=='published'||!analysisReleaseAllowed(a))return false;
 if(!a.contributor||!['named','anonymous'].includes(a.contributor.display)||(a.contributor.display==='named'&&!a.contributor.name)||(a.contributor.display==='anonymous'&&(a.contributor.name||a.contributor.affiliation)))return false;
 if(typeof a.title!=='string'||!a.title.trim()||!Array.isArray(a.sources)||!a.sources.some(s=>s?.verified===true&&typeof s.url==='string'&&s.url.startsWith('https://')))return false;
 if(Object.keys(row).some(k=>!['article','format','reporting_date','document','comparison','superseded_by','summary','lifecycle'].includes(k)))return false;
 if(!analysisSummaryValid(row)||!analysisLifecycleValid(row))return false;
 if(row.superseded_by!=null&&!analysisSlug(row.superseded_by))return false;
 if(a.ai_provenance&&(row.format!=='text-explained'||row.comparison?.status!=='compared'||!analysisSameVersion(row.comparison.baseline,a.ai_provenance.source_documents[0])||!analysisSameVersion(row.document,a.ai_provenance.source_documents[1])))return false;
 if(row.format==='daily-diplomacy-brief')return /^\d{4}-\d{2}-\d{2}$/.test(row.reporting_date)&&!row.document&&!row.comparison;
 if(row.format!=='text-explained'||row.reporting_date||!analysisDocument(row.document))return false;

 const verified=d=>a.sources.some(s=>s?.verified===true&&s.url===d.url),c=row.comparison;
 return verified(row.document)&&c&&(c.status==='not_assessed'&&Object.keys(c).length===1||c.status==='compared'&&Object.keys(c).every(k=>['status','baseline'].includes(k))&&analysisDocument(c.baseline)&&verified(c.baseline));
}

// Summary/lifecycle are public, explicitly released editorial metadata, never draft containers.
function analysisSummaryValid(row){
 if(!('summary' in row))return true;
 const s=row.summary,short=(v,n)=>typeof v==='string'&&v.trim()&&v.length<=n;
 return row.format==='text-explained'&&!!row.document?.id&&s&&Object.keys(s).length===4&&Object.keys(s).every(k=>['changes','significance','watch','language'].includes(k))&&['pt','en','es','fr','ru','zh','ar'].includes(s.language)&&Array.isArray(s.changes)&&s.changes.length>=1&&s.changes.length<=5&&s.changes.every(v=>short(v,500))&&short(s.significance,1000)&&short(s.watch,1000);
}
function analysisLifecycleValid(row){
 if(!('lifecycle' in row))return true;
 const l=row.lifecycle;
 if(row.format!=='text-explained'||!l||Object.keys(l).some(k=>!['status','checked_at','replacement'].includes(k))||!['unknown','current','withdrawn','replaced'].includes(l.status)||!analysisTime(l.checked_at))return false;
 return l.status==='replaced'?analysisDocument(l.replacement)&&JSON.stringify(l.replacement)!==JSON.stringify(row.document):!('replacement' in l);
}
function analysisMatchesDocument(row,d){
 const r=row?.document;
 return !!(r?.id&&d&&String(d.id)===r.id&&!d.withdrawn&&!d.withdrawn_at&&d.status!=='withdrawn'&&Array.isArray(d.attachments)&&d.attachments.some(a=>a.url===r.url&&a.sha256===r.sha256));
}
function analysisDocumentState(row,catalog){
 const stored=row.lifecycle;
 const docs=Array.isArray(catalog?.documents)?catalog.documents:[];
 const matches=row.document?.id?docs.filter(d=>String(d.id)===row.document.id):[];
 if(matches.some(d=>d.withdrawn||d.withdrawn_at||d.status==='withdrawn'))return {status:'withdrawn',checked_at:catalog.checked_at||catalog.last_success,...(stored?.replacement?{replacement:stored.replacement}:{})};
 if(stored?.status==='withdrawn'||stored?.status==='replaced')return {...stored};
 const checked=catalog?.last_success||catalog?.checked_at,age=Date.now()-Date.parse(checked);
 if(matches.length!==1||catalog?.degraded||catalog?.load_failed||!Number.isFinite(age)||age< -60000||age>20*60*1000)return {status:'unknown'};
 if(!analysisMatchesDocument(row,matches[0]))return {status:'version_mismatch'};
 // This status concerns the catalog record, never adoption or agreement.
 return {status:'current',checked_at:catalog.checked_at||catalog.last_success};
}

function analysisSameVersion(a,b){return !!(a&&b&&['id','url','version_label','reviewed_at','sha256'].every(k=>a[k]===b[k]));}
function analysisReleaseAllowed(a){
 if(!a||a.status!=='published')return false;
 if(!('ai_provenance' in a))return typeof a.approved_by==='string'&&!!a.approved_by.trim()&&analysisTime(a.approved_at);
 const p=a.ai_provenance,q=p?.qa,keys=['schema','mode','generated_at','model','prompt_version','authorization','source_documents','qa'],checks=['official_sources_only','pdf_bytes_verified','version_identity_verified','evidence_links_checked','confidential_inputs_excluded'];
 const official=v=>{try{const u=new URL(v);return u.protocol==='https:'&&['unfccc.int','www.unfccc.int','docs.unfccc.int'].includes(u.hostname)&&!u.username&&!u.password&&!u.port}catch{return false}};
 return !!(['pt','en','es','fr','ru','zh','ar'].includes(a.language)&&p&&Object.keys(p).length===keys.length&&Object.keys(p).every(k=>keys.includes(k))&&p.schema===1&&p.mode==='public-unfccc-diff'&&p.authorization==='owner-public-unfccc-analysis-2026-11-18'&&analysisTime(p.generated_at)&&typeof p.model==='string'&&p.model.trim()&&typeof p.prompt_version==='string'&&p.prompt_version.trim()&&!('approved_by' in a)&&!('approved_at' in a)&&a.contributor?.display==='named'&&a.contributor.name==='COP31 Monitor AI'&&a.contributor.role==='analyst'&&Object.keys(a.contributor).length===3&&Array.isArray(a.sources)&&a.sources.length&&a.sources.every(s=>s?.verified===true&&official(s.url))&&Array.isArray(p.source_documents)&&p.source_documents.length===2&&p.source_documents.every(d=>analysisDocument(d)&&!!d.id&&a.sources.some(s=>s.url===d.url))&&!['id','url','sha256'].every(k=>p.source_documents[0][k]===p.source_documents[1][k])&&q&&Object.keys(q).length===3&&q.status==='passed'&&analysisTime(q.checked_at)&&Array.isArray(q.checks)&&q.checks.length===checks.length&&checks.every(c=>q.checks.includes(c)));
}
