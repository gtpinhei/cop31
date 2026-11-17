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
function analysisDocument(d){try{const u=new URL(d.url);return d&&Object.keys(d).every(k=>['url','version_label','reviewed_at','sha256'].includes(k))&&u.protocol==='https:'&&['unfccc.int','www.unfccc.int','docs.unfccc.int'].includes(u.hostname)&&!u.username&&!u.password&&!u.port&&typeof d.version_label==='string'&&d.version_label.trim()&&analysisTime(d.reviewed_at)&&/^[a-f0-9]{64}$/.test(d.sha256)}catch{return false}}
function analysisAllowed(row,a){
 if(!row||!a||!analysisSlug(row.article)||a.id!==row.article||a.schema!==1||a.status!=='published'||typeof a.approved_by!=='string'||!a.approved_by.trim()||!analysisTime(a.approved_at))return false;
 if(!a.contributor||!['named','anonymous'].includes(a.contributor.display)||(a.contributor.display==='named'&&!a.contributor.name)||(a.contributor.display==='anonymous'&&(a.contributor.name||a.contributor.affiliation)))return false;
 if(typeof a.title!=='string'||!a.title.trim()||!Array.isArray(a.sources)||!a.sources.some(s=>s?.verified===true&&typeof s.url==='string'&&s.url.startsWith('https://')))return false;
 if(Object.keys(row).some(k=>!['article','format','reporting_date','document','comparison','superseded_by'].includes(k)))return false;
 if(row.superseded_by!=null&&!analysisSlug(row.superseded_by))return false;
 if(row.format==='daily-diplomacy-brief')return /^\d{4}-\d{2}-\d{2}$/.test(row.reporting_date)&&!row.document&&!row.comparison;
 if(row.format!=='text-explained'||row.reporting_date||!analysisDocument(row.document))return false;
 const verified=d=>a.sources.some(s=>s?.verified===true&&s.url===d.url),c=row.comparison;
 return verified(row.document)&&c&&(c.status==='not_assessed'&&Object.keys(c).length===1||c.status==='compared'&&Object.keys(c).every(k=>['status','baseline'].includes(k))&&analysisDocument(c.baseline)&&verified(c.baseline));
}
