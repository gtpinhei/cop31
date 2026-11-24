/* Public, curated from the UNFCCC AUVs and IISD Earth Negotiations Bulletin. */
window.COP31_RESULTS_DATA=(()=>{
  const enb='https://enb.iisd.org/antalya-un-climate-change-conference-cop31-summary';
  const u=id=>'https://unfccc.int/documents/'+id;
  // Copy fields: title, what happened, why it matters. The ruling is not a publication status.
  return {
    outcomes:[
      {id:'antalya-pact',topic:'package',body:'COP 31 · CMA 8',status:'notAdopted',stage:'draft',source:enb,
       en:['Antalya Pact cover texts','Neither the Convention nor the Paris Agreement cover text secured consensus.','The proposed overarching political package did not become a negotiated decision. Separate agenda items could still be adopted.'],
       pt:['Textos de capa do Pacto de Antália','Nem o texto de capa da Convenção nem o do Acordo de Paris obteve consenso.','O pacote político proposto não se tornou uma decisão negociada. Outros itens da agenda puderam ser adotados separadamente.']},
      {id:'adaptation',topic:'adaptation',body:'CMA 8 · 9(a)',status:'adopted',stage:'auv',source:u(665895),
       en:['Global goal on adaptation','Parties agreed on voluntary testing of the adaptation indicators and work to improve their methods.','Testing will show how useful the indicators are for tracking adaptation progress. The decision does not itself provide funding.'],
       pt:['Meta global de adaptação','As Partes concordaram em testar voluntariamente os indicadores de adaptação e aprimorar suas metodologias.','Os testes ajudarão a avaliar se os indicadores servem para acompanhar o progresso em adaptação. A decisão, por si só, não destina recursos.']},
      {id:'just-transition',topic:'justice',body:'CMA 8 · 5',status:'adopted',stage:'auv',source:u(665900),
       en:['Just transition work programme','Parties extended the programme for three years and agreed to put the just transition mechanism into operation in phases.','The programme continues while Parties work out how the mechanism will function.'],
       pt:['Programa de trabalho sobre transição justa','As Partes prorrogaram o programa por três anos e decidiram operacionalizar o mecanismo de transição justa em etapas.','O programa segue enquanto as Partes definem como o mecanismo funcionará.']},
      {id:'climate-finance',topic:'finance',body:'CMA 8 · 11(g)',status:'adopted',stage:'auv',source:u(665903),
       en:['Climate finance work programme','Parties agreed how to run the programme on climate finance under Article 9, including workshops, submissions and reports.','The decision sets a process for discussing delivery of climate finance; it does not itself commit new money.'],
       pt:['Programa de trabalho sobre financiamento climático','As Partes definiram como funcionará o programa sobre financiamento climático no âmbito do Artigo 9, com oficinas, contribuições escritas e relatórios.','A decisão estabelece um processo para discutir a entrega de financiamento climático, mas não compromete novos recursos.']},
      {id:'finance-flows',topic:'finance',body:'CMA 8 · 11(f)',status:'adopted',stage:'auv',source:u(665898),
       en:['Alignment of financial flows','Parties adopted a decision on Article 2.1(c) and its relationship to Article 9.','Aligning financial flows with climate goals and providing climate finance are distinct parts of the Paris Agreement. The adopted text addresses how they complement each other.'],
       pt:['Alinhamento dos fluxos financeiros','As Partes adotaram uma decisão sobre o Artigo 2.1(c) e sua relação com o Artigo 9.','Alinhar os fluxos financeiros às metas climáticas e prover financiamento climático são frentes distintas do Acordo de Paris. O texto adotado trata de como elas se complementam.']},
      {id:'mitigation',topic:'mitigation',body:'CMA 8 · 10(c)',status:'notAdopted',stage:'draft',source:enb,
       en:['Mitigation work programme','Parties did not agree to the draft; the item goes to CMA 9 under the draft rules of procedure.','Carrying the agenda item forward did not extend the existing work programme.'],
       pt:['Programa de trabalho sobre mitigação','As Partes não chegaram a acordo sobre o texto. O item volta à CMA 9 pelas regras de procedimento em aplicação.','O adiamento do item não prorrogou o programa de trabalho vigente.']},
      {id:'loss-and-damage-fund',topic:'loss',body:'COP 31 · 8(e)',status:'adopted',stage:'auv',source:u(665889),
       en:['Fund for responding to loss and damage','The COP adopted guidance to the Fund and considered the Fund’s report.','This is guidance to the Fund, not a record of contributions pledged or paid.'],
       pt:['Fundo de resposta a perdas e danos','A COP adotou orientações ao Fundo e examinou seu relatório.','A decisão orienta o Fundo; não é um registro de contribuições prometidas ou pagas.']},
      {id:'article-6-4',topic:'mitigation',body:'CMA 8 · 16(b)',status:'adopted',stage:'auv',source:u(665844),
       en:['Paris Agreement Article 6.4','Parties adopted further guidance for the UN crediting mechanism.','The guidance applies to the mechanism as a whole; it does not approve any individual project.'],
       pt:['Artigo 6.4 do Acordo de Paris','As Partes adotaram novas orientações para o mecanismo de créditos da ONU.','As orientações se aplicam ao mecanismo e não aprovam projetos individuais.']}
    ],
    milestones:[
      {id:'adaptation',date:'2027-02-28',precision:'byDay',en:'Deadline for nominations to the adaptation indicators task force.',pt:'Prazo para indicações à força-tarefa sobre indicadores de adaptação.'},
      {id:'just-transition',session:'SB 66',en:'Develop the functions and operating arrangements of the just transition mechanism.',pt:'Desenvolver as funções e as regras de funcionamento do mecanismo de transição justa.'},
      {id:'adaptation',date:'2027-08-01',precision:'byMonth',en:'Virtual technical dialogue, open to Parties and observers, on lessons from testing the indicators.',pt:'Diálogo técnico virtual, aberto a Partes e observadores, sobre aprendizados dos testes dos indicadores.'},
      {id:'adaptation',date:'2027-08-31',precision:'byDay',en:'Deadline for Parties to submit experience and lessons from testing the indicators.',pt:'Prazo para as Partes enviarem experiências e aprendizados sobre os testes dos indicadores.'},
      {id:'mitigation',session:'CMA 9',en:'The mitigation item returns for consideration; no extension was agreed at CMA 8.',pt:'O tema volta à pauta. A CMA 8 não aprovou a prorrogação do programa.'},
      {id:'climate-finance',session:'CMA 9',en:'Consider the work programme and its annual report, and provide guidance for the work in 2028.',pt:'Examinar o programa de trabalho e seu relatório anual e orientar as atividades para 2028.'}
    ]
  };
})();
