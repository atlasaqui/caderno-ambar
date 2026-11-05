'use strict';
let rotinaPagina = 1, rotinaAberta = false, rotinaAdmin = false, minhaConta = null;
let rotinaOrg = null;
const csvUpload=document.createElement('input');csvUpload.type='file';csvUpload.accept='.csv,text/csv';
const csvLabel=text('label','Selecionar arquivo CSV','csv-upload');csvLabel.append(csvUpload);
el('csv-input').parentElement.before(csvLabel);
csvUpload.onchange=()=>run(async()=>{
  const file=csvUpload.files[0];if(!file){status(null);return;}
  if(file.size>100000)throw new Error('Selecione um CSV de até 100 KB.');
  el('csv-input').value=await file.text();el('csv-input').dispatchEvent(new Event('input'));el('import-result').hidden=true;
  status('Arquivo carregado. Valide a prévia antes de confirmar a importação.');
});
const rotulosEstado = {a_fazer:'A fazer',em_andamento:'Em andamento',aguardando:'Aguardando informação',em_revisao:'Aguardando revisão',concluida:'Concluída'};
const destinos = {a_fazer:['em_andamento','aguardando'],em_andamento:['aguardando','em_revisao'],aguardando:['a_fazer','em_andamento'],em_revisao:['em_andamento','concluida'],concluida:['a_fazer']};

async function atualizarRotinaContexto(contexto) {
  rotinaAdmin = contexto.papel === 'admin';
  el('operation-panel').hidden = !rotinaAdmin;
  el('action-panel').hidden = true;
  minhaConta = null;
  el('operation-list').replaceChildren();
  if(rotinaOrg!==contexto.id){
    rotinaPagina=1;el('routine-filter').value='minhas';el('routine-search').value='';
    el('routine-list').replaceChildren();el('routine-summary').textContent='';csvUpload.value='';
  }
  rotinaOrg=contexto.id;
  if (rotinaAberta) await carregarRotina();
}

function trocarArea(rotina) {
  rotinaAberta = rotina;
  el('routine-view').hidden = !rotina;
  el('cases-view').hidden = rotina;
  el('show-cases').setAttribute('aria-pressed', String(!rotina));
  el('show-routine').setAttribute('aria-pressed', String(rotina));
  el('action-panel').hidden = true;
}

function abrirProvidencia(caso, versao, nome) {
  const form = el('action-form'); form.reset();
  form.elements.caso.value = caso; form.elements.versao.value = versao || '';
  for (const campo of ['responsavel','revisor']) {
    form.elements[campo].replaceChildren(...membros.map(m => { const o=text('option',m.email);o.value=m.usuario;return o; }));
  }
  const c = lista.find(c => c.id === caso);
  if (c) form.elements.responsavel.value = c.responsavel;
  const admin = membros.find(m => m.papel === 'admin');
  if (admin) form.elements.revisor.value = admin.usuario;
  el('action-source').textContent = `${nome}${versao ? ' · referência: versão ' + versao : ' · providência geral do processo'}`;
  el('action-panel').hidden = false;el('action-panel').scrollIntoView({behavior:'smooth',block:'start'});
  focusAfterAction = el('action-title'); status(null);
}

submit('action-form',async(data,event)=>{
  const resposta = await api('providencias',{
    ...data,caso:Number(data.caso),versao:data.versao ? Number(data.versao) : null,
    responsavel:Number(data.responsavel),revisor:Number(data.revisor)
  });
  event.target.reset();el('action-panel').hidden=true;trocarArea(true);await carregarRotina();status(resposta.status);
});

async function carregarRotina() {
  if (!minhaConta) minhaConta=await api('me?org='+org);
  const resposta=await api('rotina?'+new URLSearchParams({org,filtro:el('routine-filter').value,pagina:rotinaPagina,busca:el('routine-search').value}));
  el('routine-summary').textContent=`${resposta.resumo.minhas} comigo · ${resposta.resumo.atrasadas} com data interna vencida · ${resposta.resumo.revisar} para minha revisão`;
  el('routine-list').replaceChildren(...resposta.itens.map(providenciaCard));
  if (!resposta.itens.length) {
    const vazio=text('div','','empty-card');vazio.append(text('h3','Nenhuma providência nesta seleção.'),text('p','Abra um processo ou uma versão na linha do tempo e escolha Criar providência.'));
    el('routine-list').append(vazio);
  }
  const anterior=button('← Anterior',async()=>{rotinaPagina--;await carregarRotina();status(null);});anterior.disabled=rotinaPagina===1;
  const proxima=button('Próxima →',async()=>{rotinaPagina++;await carregarRotina();status(null);});proxima.disabled=rotinaPagina*25>=resposta.total;
  el('routine-pagination').replaceChildren(anterior,text('span',`${resposta.total} providências · página ${rotinaPagina}`),proxima);
  el('routine-pagination').hidden=resposta.total<=25;
}

function providenciaCard(p) {
  const card=text('article','','real-panel action-card');
  const cabecalho=text('div','','case-top'),titulo=text('div','');
  titulo.append(text('small',`${p.apelido || p.numero} · ${p.versao ? 'versão '+p.versao : 'processo'}`,'source-label'),text('h3',p.titulo));
  cabecalho.append(titulo,text('span',rotulosEstado[p.estado],'badge '+(p.estado==='concluida'?'':'pending')));card.append(cabecalho);
  const dataInterna=p.data_interna || '';
  const vencida=Boolean(dataInterna)&&p.estado!=='concluida'&&dataInterna<new Date().toLocaleDateString('sv-SE');
  card.append(text('p',`Data interna: ${dataInterna ? dataInterna.split('-').reverse().join('/') : 'não definida'} ${vencida?'· vencida':''} · Prioridade ${p.prioridade}`,vencida?'error-note':'muted'),
    text('p',`Responsável: ${p.responsavel_email} · Revisor: ${p.revisor_email}`,'action-people'));
  if(p.descricao)card.append(text('p',p.descricao));
  if(p.evidencia)card.append(text('p','Resultado registrado: '+p.evidencia,'movement-preview'));
  if(rotinaAdmin||[p.responsavel,p.revisor].includes(minhaConta.id)){
    const details=text('details','','case-editor');details.append(text('summary','Atualizar providência ou comentar'));
    const form=text('form',''),selecao=field(form,'Próxima etapa','','select');
    for(const estado of [p.estado,...destinos[p.estado]]){
      if(estado==='concluida'&&!rotinaAdmin&&minhaConta.id!==p.revisor)continue;
      const o=text('option',rotulosEstado[estado]);o.value=estado;selecao.append(o);
    }
    const evidencia=field(form,'Resultado / evidência de execução',p.evidencia,'textarea');evidencia.maxLength=4000;
    const comentario=field(form,'Comentário para a equipe','','textarea');comentario.maxLength=2000;
    const save=text('button','Salvar atualização','button dark');form.append(save);
    form.onsubmit=e=>{e.preventDefault();run(async()=>{const r=await api(`providencias/${p.id}/alterar`,{estado:selecao.value,evidencia:evidencia.value,comentario:comentario.value,revisao:p.revisao});await carregarRotina();status(r.status);});};
    details.append(form);card.append(details);
  }
  const historico=text('div','');
  card.append(button('Ver histórico da providência',async()=>{
    const eventos=await api(`providencias/${p.id}/historico`);historico.replaceChildren(...eventos.map(e=>{
      const detalhes=JSON.parse(e.detalhes);const linha=text('p',`${date(e.instante)} · ${e.email} · ${e.acao}`);
      if(detalhes.depois)linha.append(text('small',`${rotulosEstado[detalhes.antes]} → ${rotulosEstado[detalhes.depois]}`));
      if(detalhes.comentario)linha.append(text('p',detalhes.comentario));return linha;
    }));status(null);
  }),historico);
  return card;
}

async function carregarOperacao(){
  const d=await api('operacao?org='+org);el('operation-list').replaceChildren();
  for(const t of d.consultas){
    const p=text('div','','operation-row');p.append(text('p',`${t.apelido || t.numero} · ${t.tentativas>=5?'Intervenção necessária':t.lease>Date.now()/1000?'Em execução':'Agendado'} · próxima tentativa: ${date(t.proxima)}`));
    if(t.erro)p.append(text('p',t.erro,'error-note'));
    if(t.erro&&t.lease<=Date.now()/1000)p.append(button('Reprocessar consulta',async()=>{const r=await api('operacao/reprocessar',{org,tipo:'consulta',id:t.caso});await carregarOperacao();status(r.status);}));
    el('operation-list').append(p);
  }
  for(const e of d.emails){
    const p=text('div','','operation-row');p.append(text('p',`Mensagem ${e.id} · ${e.estado} · ${e.tentativas} tentativa(s)`));
    if(e.erro)p.append(text('p',e.erro,'error-note'));
    if(e.estado==='pendente'&&e.tentativas>=5)p.append(button('Reprocessar e-mail',async()=>{const r=await api('operacao/reprocessar',{org,tipo:'email',id:e.id});await carregarOperacao();status(r.status);}));
    el('operation-list').append(p);
  }
  if(!d.consultas.length&&!d.emails.length)el('operation-list').append(text('p','Nenhuma tarefa automática ou mensagem nesta fila.','muted'));
}

el('show-routine').onclick=()=>run(async()=>{trocarArea(true);rotinaPagina=1;await carregarRotina();status(null);});
el('show-cases').onclick=()=>{if(busy)return;trocarArea(false);status(null);};
el('refresh-routine').onclick=()=>run(async()=>{await carregarRotina();status('Rotina atualizada.');});
el('routine-filter').onchange=()=>run(async()=>{rotinaPagina=1;await carregarRotina();status(null);});
el('search-routine').onclick=()=>run(async()=>{rotinaPagina=1;await carregarRotina();status(null);});
el('routine-search').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();el('search-routine').click();}};
el('close-action').onclick=()=>{el('action-panel').hidden=true;};
el('refresh-operation').onclick=()=>run(async()=>{await carregarOperacao();status(null);});
