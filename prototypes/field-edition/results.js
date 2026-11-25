'use strict';
/* Results is a read-only top-level view, independent of the document collector. */
window.COP31_RESULTS=(()=>{
  const root=document.getElementById('results');
  const base='#results';
  const langs={
    en:['COP31 Results','What countries decided, where talks fell short, and what to follow next.','What was decided','What happens next','Key outcomes','Why it matters','Sources and details','Official text','Plenary reporting','Adopted','Not adopted','Text available','Advance unedited version','No adopted text','All workstreams','No confirmed milestones for this selection.','English summaries shown.','Political package','Adaptation','Just transition','Finance','Mitigation','Loss and damage','Back to results','By','A selection, not a complete record.'],
    pt:['Resultados da COP31','O que os países decidiram, onde não houve acordo e o que acompanhar a seguir.','O que foi decidido','Próximos passos','Principais resultados','Por que importa','Fontes e detalhes','Texto oficial','Relato da plenária','Adotado','Não adotado','Texto disponível','Versão preliminar não editada','Sem texto adotado','Todos os temas','Não há marcos confirmados nesta seleção.','','Pacote político','Adaptação','Transição justa','Financiamento','Mitigação','Perdas e danos','Voltar aos resultados','Até','Seleção de resultados, não um registro completo.'],
    es:['Resultados de la COP31','Qué decidieron los países, dónde faltó acuerdo y qué sigue.','Decisiones','Próximos pasos','Principales resultados','Por qué importa','Fuentes y detalles','Texto oficial','Crónica del plenario','Adoptado','No adoptado','Texto disponible','Versión preliminar sin editar','Sin texto adoptado','Todos los temas','No hay hitos confirmados para esta selección.','Resúmenes en inglés.','Paquete político','Adaptación','Transición justa','Financiación','Mitigación','Pérdidas y daños','Volver a los resultados','Hasta','Selección de resultados; no es un registro completo.'],
    fr:['Résultats de la COP31','Les décisions, les points de désaccord et les prochaines étapes.','Décisions','Prochaines étapes','Principaux résultats','Pourquoi c’est important','Sources et détails','Texte officiel','Compte rendu de la plénière','Adopté','Non adopté','Texte disponible','Version préliminaire non éditée','Aucun texte adopté','Tous les thèmes','Aucun jalon confirmé pour cette sélection.','Résumés en anglais.','Ensemble politique','Adaptation','Transition juste','Financement','Atténuation','Pertes et préjudices','Retour aux résultats','D’ici','Sélection de résultats, non exhaustive.'],
    ru:['Итоги КС-31','Что решили страны, по чему не договорились и за чем следить дальше.','Решения','Следующие шаги','Ключевые итоги','Почему это важно','Источники и подробности','Официальный текст','Отчёт о пленарном заседании','Принято','Не принято','Доступный текст','Предварительная неотредактированная версия','Принятого текста нет','Все темы','Для выбранной темы нет подтверждённых этапов.','Резюме на английском.','Политический пакет','Адаптация','Справедливый переход','Финансирование','Смягчение последствий','Потери и ущерб','К итогам','К','Избранные итоги, а не полный перечень.'],
    zh:['COP31 成果','各国达成了什么决定、哪些议题未达成共识，以及后续关注点。','通过情况','后续进展','主要成果','为何重要','来源及详情','官方文本','全体会议报道','已通过','未通过','文本状态','未经编辑的预发版本','无通过文本','全部议题','所选议题暂无已确认的后续节点。','摘要以英文显示。','政治方案','适应','公正转型','资金','减缓','损失与损害','返回成果页','截至','仅列出部分成果，并非完整记录。'],
    ar:['نتائج مؤتمر الأطراف 31','ما قررته الدول، وما لم تتفق عليه، وما ينبغي متابعته لاحقًا.','ما تم البت فيه','الخطوات التالية','النتائج الرئيسية','لماذا يهم ذلك','المصادر والتفاصيل','النص الرسمي','تقرير الجلسة العامة','اعتُمد','لم يُعتمد','النص المتاح','نسخة مسبقة غير محررة','لا يوجد نص معتمد','جميع المواضيع','لا توجد محطات مؤكدة ضمن هذا الاختيار.','تُعرض الملخصات باللغة الإنجليزية.','الحزمة السياسية','التكيف','الانتقال العادل','التمويل','التخفيف','الخسائر والأضرار','العودة إلى النتائج','بحلول','نتائج مختارة وليست سجلاً كاملاً.']
  };
  const navLabels={en:'Results',pt:'Resultados',es:'Resultados',fr:'Résultats',ru:'Итоги',zh:'成果',ar:'النتائج'};
  const todaySummary={
    en:'COP31 ended without an overarching agreement. Countries adopted decisions on adaptation, just transition and climate finance.',
    pt:'A COP31 terminou sem um acordo geral. Os países adotaram decisões sobre adaptação, transição justa e financiamento climático.',
    es:'La COP31 terminó sin un acuerdo general. Los países adoptaron decisiones sobre adaptación, transición justa y financiación climática.',
    fr:'La COP31 s’est achevée sans accord global. Les pays ont adopté des décisions sur l’adaptation, la transition juste et le financement climatique.',
    ru:'КС-31 завершилась без общего соглашения. Страны приняли решения по адаптации, справедливому переходу и климатическому финансированию.',
    zh:'COP31未能达成总体协议。各国通过了关于适应、公正转型和气候融资的决定。',
    ar:'انتهى مؤتمر الأطراف 31 دون اتفاق شامل. واعتمدت الدول قرارات بشأن التكيف والانتقال العادل وتمويل المناخ.'
  };
  const topics=['package','adaptation','justice','finance','mitigation','loss'];
  const {outcomes,milestones}=window.COP31_RESULTS_DATA;
  const records=new Map(outcomes.map(o=>[o.id,o]));
  const el=(tag,value,cls)=>{const n=document.createElement(tag);if(value!=null)n.textContent=value;if(cls)n.className=cls;return n};
  const add=(parent,...children)=>{parent.append(...children);return parent};
  const link=(label,url,cls)=>{const a=el('a',label,cls);a.href=url;return a};
  const copy=n=>{n.lang=copyLang();n.dir='ltr';return n};
  const copyLang=()=>lang==='pt'?'pt':'en';
  const L=i=>(langs[lang]||langs.en)[i];
  const topic=t=>L(17+topics.indexOf(t));
  const mid=id=>base+'/decision/'+id;
  const tag=o=>el('span',L(o.status==='adopted'?9:10),'result-status '+o.status);
  const source=o=>link(L(o.stage==='auv'?7:8)+' ↗',o.source,'result-source');
  const body=o=>{const b=el('bdi',o.body);b.dir='ltr';return b};
  function metadata(o){return add(el('div',null,'result-row'),add(el('p',null,'result-topic'),el('span',topic(o.topic)+' · '),body(o)),tag(o))}
  function timestamp(m){
    if(!m.date)return m.session;
    const options=m.precision==='byMonth'?{month:'long',year:'numeric'}:{day:'numeric',month:'long',year:'numeric'};
    const str=new Intl.DateTimeFormat(lang,{...options,timeZone:'UTC'}).format(new Date(m.date+'T00:00:00Z'));
    return m.precision==='byMonth'?L(24)+' '+str:str;
  }
  function steps(list,links){
    const ol=el('ol',null,'result-steps');
    for(const m of list){
      const o=records.get(m.id);
      const label=m.date?el('time',timestamp(m)):el('bdi',m.session);
      if(m.date)label.dateTime=m.precision==='byMonth'?m.date.slice(0,7):m.date;
      const li=add(el('li'),label,copy(el('p',m[copyLang()])));
      if(links)add(li,link(o[copyLang()][0],mid(o.id),'result-source'));
      add(ol,li);
    }
    return ol;
  }
  function tabs(next){
    const nav=el('nav',null,'result-tabs');nav.setAttribute('aria-label',L(0));
    for(const [active,i,hash] of [[!next,2,base],[next,3,base+'/next']]){
      const a=link(L(i),hash);
      if(active)a.setAttribute('aria-current','page');
      add(nav,a);
    }
    return nav;
  }
  function listing(next){
    const hero=add(el('div',null,'result-hero'),el('p','ANTALYA · COP 31','result-topic'),el('h1',L(0)),el('p',L(1)));
    hero.querySelector('h1').id='results-heading';
    add(root,hero,tabs(next));
    if(L(16)&&lang!=='en')add(root,el('p',L(16),'result-muted'));
    if(next){
      const section=add(el('section',null,'result-box'),el('h2',L(3)));
      const select=el('select');const label=add(el('label',null,'result-filter'),el('span',L(14)),select);
      const used=topics.filter(t=>milestones.some(m=>records.get(m.id).topic===t));
      for(const t of ['',...used]){const op=el('option',t?topic(t):L(14));op.value=t;add(select,op)}
      const items=el('div');
      const update=()=>{const matches=milestones.filter(m=>!select.value||records.get(m.id).topic===select.value);items.replaceChildren(matches.length?steps(matches,true):el('p',L(15)))};
      select.addEventListener('change',update);update();add(section,label,items);add(root,section);
    }else{
      const grid=el('div',null,'result-grid');
      const group=add(el('section'),el('h2',L(4)));
      for(const o of outcomes){
        const h=add(el('h3'),copy(link(o[copyLang()][0],mid(o.id))));
        add(group,add(el('article',null,'result-box result-card'),metadata(o),h,copy(el('p',o[copyLang()][1])),source(o)));
      }
      const sidebar=add(el('aside',null,'result-box result-side'),el('h2',L(3)),steps(milestones.slice(0,3),true),link(L(3)+' ↗',base+'/next','result-source'));
      add(root,add(grid,group,sidebar));
    }
    add(root,el('p',L(25),'result-muted'));
  }
  function details(o){
    const [title,decision,impact]=o[copyLang()];
    const heading=copy(el('h1',title));heading.id='results-heading';
    const wrap=el('article',null,'result-detail');
    add(root,wrap);
    add(wrap,link(L(23),base,'result-back'),metadata(o),heading,el('p',L(11)+': '+L(o.stage==='auv'?12:13),'result-stage'));
    if(L(16)&&lang!=='en')add(wrap,el('p',L(16),'result-muted'));
    for(const [i,content] of [[2,decision],[5,impact]])add(wrap,add(el('section',null,'result-box'),el('h2',L(i)),copy(el('p',content))));
    const next=milestones.filter(m=>m.id===o.id);
    add(wrap,add(el('section',null,'result-box'),el('h2',L(3)),next.length?steps(next,false):el('p',L(15))));
    const more=add(el('details'),el('summary',L(6)),add(el('p'),body(o)));
    add(wrap,add(el('div',null,'result-box result-provenance'),source(o),more));
  }
  let previous='',previousLang='';
  function route(parts){
    const o=parts.length===2&&parts[0]==='decision'?records.get(parts[1]):null;
    const next=parts.length===1&&parts[0]==='next';
    const page=o?.id||(next?'next':'list');
    const wasHidden=root.hidden;
    document.querySelectorAll('.view').forEach(s=>s.hidden=s!==root);
    document.querySelectorAll('[data-tab]').forEach(a=>a.setAttribute('aria-current',a.dataset.tab==='results'?'page':'false'));
    const changed=previous!==page;
    if(changed||previousLang!==lang){
      root.replaceChildren();
      if(o)details(o);else listing(next);
      previous=page;previousLang=lang;
    }
    if(changed||wasHidden){
      const heading=root.querySelector('h1');
      heading.tabIndex=-1;heading.focus();
    }
  }
  function entries(){
    const nav=document.querySelector('[data-tab="results"]');
    if(nav)nav.textContent=navLabels[lang]||navLabels.en;
    for(const id of ['results-today','results-texts']){
      const holder=document.getElementById(id);if(!holder)continue;
      let a=holder.querySelector('a');
      if(!a){
        a=link('',base,'result-entry');
        if(id==='results-today'){
          const section=el('section',null,'result-today-lead');
          const heading=el('h2');heading.id='results-today-heading';
          section.setAttribute('aria-labelledby',heading.id);
          add(holder,add(section,heading,el('p'),a));
        }else add(holder,a);
      }
      a.textContent=L(0)+' ↗';
      if(id==='results-today'){
        holder.querySelector('h2').textContent=L(0);
        holder.querySelector('p').textContent=todaySummary[lang]||todaySummary.en;
        a.textContent=L(2)+' ↗';
      }
    }
  }
  const priorRender=render;render=function(){priorRender();entries()};
  entries();
  return {route};
})();
