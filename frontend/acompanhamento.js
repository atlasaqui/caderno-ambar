'use strict';

const el = id => document.getElementById(id);
const text = (tag, value, className) => {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
};
let org = null, lista = [], membros = [], pagina = 0, busy = false;
let importedPreview = null;
let carteiraAtual = null;
let buscaTimer;
let focusAfterAction = null;
let eventosDaAcao = [];
let atualizacaoTimer;

function acompanharAtualizacoes() {
  clearTimeout(atualizacaoTimer);
  if (!lista.some(c => c.atualizacao_pendente || c.consulta_reservada_ate > Date.now()/1000)) return;
  atualizacaoTimer=setTimeout(async()=>{
    const editando=document.activeElement?.matches('input,textarea,select') || document.querySelector('.case-editor[open]');
    if (busy || document.hidden || el('cases-view').hidden || !el('history-panel').hidden || editando) { acompanharAtualizacoes(); return; }
    try { await load(); } catch { status('Não foi possível verificar a atualização. Seus dados salvos continuam disponíveis.','error'); }
  },15000);
}

function status(message, kind = 'success') {
  el('status').textContent = message || '';
  el('status').dataset.kind = kind;
  el('status').hidden = !message;
}

function signedIn(value) {
  if (!value) clearTimeout(atualizacaoTimer);
  document.body.classList.toggle('signed-in', value);
  el('auth').hidden = value;
  el('workspace').hidden = !value;
  document.querySelector('.page-intro h1').textContent = value ? 'Carteira de processos.' : 'Seu trabalho, em perspectiva.';
  document.querySelector('.page-intro .eyebrow').textContent = value ? 'CADERNO ÂMBAR / ÁREA DE TRABALHO' : 'DA CONSULTA À CONFERÊNCIA';
}

async function api(path, data) {
  const response = await fetch('/api/' + path, {
    method: data === undefined ? 'GET' : 'POST',
    headers: data === undefined ? {} : { 'Content-Type': 'application/json' },
    body: data === undefined ? undefined : JSON.stringify(data),
    signal: AbortSignal.timeout(120000)
  });
  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('Não foi possível comunicar com a aplicação. Abra a versão local na porta 8093.');
  }
  const dataOut = await response.json();
  if (!response.ok) {
    if (response.status === 401) signedIn(false);
    const error = new Error(dataOut.error || 'Não foi possível concluir a solicitação.');
    error.status = response.status;
    error.code = dataOut.code;
    error.retryAfter = dataOut.retry_after;
    throw error;
  }
  eventosDaAcao.push(path.split('?')[0]);
  return dataOut;
}

async function run(action, loading = 'Processando sua solicitação…') {
  if (busy) return;
  busy = true;
  eventosDaAcao = [];
  el('workspace').inert = true;
  el('auth').inert = true;
  el('workspace').setAttribute('aria-busy', 'true');
  status(loading, 'loading');
  try { await action(); }
  catch (error) {
    status(error.name === 'TimeoutError' ? 'A consulta demorou mais que o esperado. Sua referência anterior foi preservada. Tente novamente.' : error.message, 'error');
  } finally {
    busy = false;
    el('workspace').inert = false;
    el('auth').inert = false;
    el('workspace').removeAttribute('aria-busy');
    focusAfterAction?.focus({ preventScroll: true });
    focusAfterAction = null;
    window.dispatchEvent(new CustomEvent('ambar:acao', {detail: {paths: [...eventosDaAcao]}}));
  }
}

function button(label, action, primary = false) {
  const node = text('button', label, 'button ' + (primary ? 'dark' : 'outline'));
  node.type = 'button';
  node.onclick = () => run(action);
  return node;
}

function field(form, label, value = '', type = 'input') {
  const node = document.createElement(type);
  node.value = value ?? '';
  const wrapper = text('label', label);
  wrapper.append(node);
  form.append(wrapper);
  return node;
}

const date = value => value ? new Date(value * 1000).toLocaleString('pt-BR') : 'Ainda não consultado';
const movementDate = value => {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString('pt-BR');
};

async function load() {
  const context = await api('contexto');
  if (!context.some(item => item.id === Number(org))) org = context[0].id;
  el('organization').replaceChildren(...context.map(item => {
    const option = text('option', `${item.nome} · ${item.papel === 'admin' ? 'Administrador' : 'Membro'}`);
    option.value = item.id;
    return option;
  }));
  el('organization').value = org;
  const current = context.find(item => item.id === Number(org));
  [carteiraAtual, membros] = await Promise.all([api('carteira?' + new URLSearchParams({org,pagina:pagina+1,busca:el('search').value,filtro:el('filter').value})), api('membros?org=' + org)]);
  lista = carteiraAtual.itens; pagina = carteiraAtual.pagina - 1;
  signedIn(true);
  el('history-panel').hidden = true;
  render();
  el('invite-form').hidden = current.papel !== 'admin';
  el('office-form').hidden = current.papel !== 'admin';
  el('office-form').elements.nome.value = current.nome;
  renderTeam(current.papel === 'admin');
  if (typeof carregarPainelPiloto === 'function') await carregarPainelPiloto(current);
  if (typeof atualizarRotinaContexto === 'function') await atualizarRotinaContexto(current);
  const notices = await api('notificacoes?org=' + org);
  el('notifications').replaceChildren(...notices.slice(0, 20).map(item => {
    const c = lista.find(caso => caso.id === item.caso);
    return text('p', `${date(item.instante)} · ${c?.apelido || 'Acompanhamento'}: ${item.texto}`);
  }));
  if (!notices.length) el('notifications').append(text('p', 'As novidades identificadas nas consultas aparecerão aqui.', 'muted'));
}

function renderTeam(admin) {
  el('team-list').replaceChildren(...membros.map(member => {
    const row = text('div', '', 'member-row');
    const info = text('p', member.email);
    info.append(text('small', member.papel === 'admin' ? 'Administrador' : 'Membro'));
    row.append(info);
    if (admin && member.papel !== 'admin') {
      row.append(button('Revogar acesso', async () => {
        if (!window.confirm(`Revogar o acesso de ${member.email} a este escritório?`)) { status(null); return; }
        await api('membros/revogar', { org, usuario: member.usuario });
        await load(); status('Acesso revogado. Os acompanhamentos foram preservados.');
      }));
    }
    return row;
  }));
}

function renderMetrics() {
  const resumo = carteiraAtual.resumo;
  const metrics = [
    [resumo.ativos, 'Acompanhamentos ativos'],
    [resumo.conferir, 'Versões a conferir'],
    [resumo.falhas, 'Atualizações com pendência'],
    [resumo.atrasadas, 'Consultas programadas atrasadas']
  ];
  el('metrics').replaceChildren(...metrics.map(([number, label]) => {
    const item = text('div', '', 'metric');
    item.append(text('strong', number), text('span', label));
    return item;
  }));
  const demo = carteiraAtual.demonstracao;
  el('demo').textContent = demo ? 'Ver demonstração' : 'Carregar demonstração';
  el('demo-help').textContent = !demo ? 'Use um exemplo fictício para conhecer a consulta, a comparação e a conferência.'
    : !demo.versao_id ? 'Passo 1 de 3 · O exemplo está na lista. Clique em Consultar referência.'
    : !demo.etapa ? 'Passo 2 de 3 · Referência salva. Simule uma nova movimentação e consulte outra vez.'
    : !demo.snapshot?.includes('123') ? 'Passo 2 de 3 · A fonte fictícia mudou. Clique em Consultar novidade.'
    : !demo.conferido ? 'Passo 3 de 3 · Abra a linha do tempo, leia a novidade e confira esta versão.'
    : 'Percurso concluído · Você consultou, comparou e registrou a leitura de uma versão. Explore o histórico.';
}

function render() {
  renderMetrics();
  const shown = lista;
  el('cases').replaceChildren(...shown.map(caseCard));
  if (!shown.length) {
    const empty = text('div', '', 'empty-card');
    empty.append(text('h3', lista.length ? 'Nenhum resultado nesta seleção.' : 'Seu primeiro acompanhamento começa aqui.'),
      text('p', lista.length ? 'Experimente outra busca ou situação para encontrar seus processos.' : 'Carregue a demonstração acima ou adicione um processo público pelo formulário de cadastro.'));
    el('cases').append(empty);
  }
  const prev = button('← Anterior', async () => { pagina--; await load(); status(null); });
  const next = button('Próxima →', async () => { pagina++; await load(); status(null); });
  prev.disabled = pagina === 0;
  next.disabled = (pagina + 1) * 20 >= carteiraAtual.total;
  el('pagination').replaceChildren(prev, text('span', `Página ${pagina + 1} de ${Math.max(1, Math.ceil(carteiraAtual.total / 20))} · ${carteiraAtual.total} resultados`), next);
  el('pagination').hidden = carteiraAtual.total <= 20;
  exportButton.disabled = carteiraAtual.resumo.total === 0;
}

function caseCard(c) {
  const card = text('article', '', 'real-panel case-card');
  card.dataset.caseId = c.id;
  const top = text('div', '', 'case-top'), heading = text('div', '');
  heading.append(text('span', c.fonte === 'demo' ? 'EXEMPLO FICTÍCIO · SEM CONSULTA AO TRIBUNAL' : 'CNJ / DATAJUD', 'source-label'),
    text('h3', c.apelido || 'Processo acompanhado'), text('div', `${c.numero} · ${c.tribunal.toUpperCase()}`, 'case-number'));
  const emConsulta=c.consulta_reservada_ate>Date.now()/1000;
  const pendente=Boolean(c.atualizacao_pendente || emConsulta);
  const label = c.arquivado ? 'Arquivado' : emConsulta ? 'Consultando fonte' : pendente ? 'Atualização na fila' : c.erro ? (c.versao_id ? 'Dados salvos disponíveis' : 'Aguardando primeira consulta') : !c.versao_id ? 'Não consultado' : c.conferido ? 'Versão conferida' : 'A conferir';
  top.append(heading, text('span', label, 'badge ' + (c.erro || pendente || !c.conferido ? 'pending' : '')));
  card.append(top);
  const meta = text('dl', '', 'case-meta');
  for (const [name, value] of [['Responsável', c.responsavel_email || 'Não atribuído'], ['Última consulta válida', date(c.ultima_ok)]]) {
    const pair = text('div', ''); pair.append(text('dt', name), text('dd', value)); meta.append(pair);
  }
  card.append(meta);
  if (c.erro || pendente) {
    const notice=text('div','','source-notice');notice.setAttribute('role','status');
    notice.append(text('strong',emConsulta ? 'Consultando o DataJud em segundo plano.' : c.codigo_falha==='fonte_sobrecarregada' ? 'O serviço de buscas do CNJ está sobrecarregado.' : c.erro ? 'A atualização ainda não foi concluída.' : 'Sua solicitação está na fila.'));
    notice.append(text('p',c.snapshot ? 'Você pode continuar usando os últimos dados recebidos. Uma falha de atualização não apaga o histórico.' : 'Ainda não recebemos os dados deste processo. Você pode organizar a carteira enquanto aguarda.'));
    if(pendente)notice.append(text('small',emConsulta ? 'Pode continuar trabalhando nesta página.' : 'Tentativa automática prevista a partir de '+date(c.proxima_tentativa)+'. O servidor precisa permanecer ligado.'));
    else if(c.erro)notice.append(text('small',(c.tentativas_atualizacao>=5 ? 'As tentativas automáticas foram pausadas. ' : '')+'Solicite uma nova atualização quando desejar.'));
    if(c.erro){const details=text('details','','source-diagnostic');details.append(text('summary','Detalhes da última tentativa'),text('p',c.erro));notice.append(details);}
    card.append(notice);
  }
  if (c.snapshot) for (const record of JSON.parse(c.snapshot).registros) {
    const latest = [...record.movimentos].sort((a, b) => a.dataHora.localeCompare(b.dataHora)).at(-1);
    const preview = text('div', '', 'movement-preview');
    preview.append(text('small', `${record.grau || 'Grau não informado'} · ${record.classe?.nome || 'Classe não informada'}`),
      text('p', latest ? latest.nome || String(latest.codigo) : 'A fonte não disponibilizou movimentações.'));
    if (latest) preview.append(text('small', movementDate(latest.dataHora)));
    card.append(preview);
  }
  const actions = text('div', '', 'real-actions');
  if (!c.arquivado) {
    const consulta = button(c.fonte !== 'demo' ? 'Solicitar atualização' : !c.versao_id ? 'Consultar referência' : c.etapa && !c.snapshot?.includes('123') ? 'Consultar novidade' : 'Consultar novamente', async () => {
    let result;
    try { result = await api(`casos/${c.id}/${c.fonte === 'demo' ? 'consultar' : 'agendar'}`, {}); }
    catch(error) { await load(); throw error; }
    await load(); status(result.status || `${c.apelido || c.numero}: ${result.estado}.`);
    }, true);
    if(pendente){consulta.disabled=true;consulta.textContent=emConsulta ? 'Consulta em andamento' : 'Atualização solicitada';}
    const espera = c.fonte !== 'demo' && c.erro && c.proxima_tentativa ? Math.ceil(c.proxima_tentativa-Date.now()/1000) : 0;
    if(espera>0 && !pendente){
      consulta.disabled=true;consulta.textContent='Aguardando nova tentativa';
      card.append(text('p','Nova tentativa disponível após '+date(c.proxima_tentativa)+'.','helper'));
      setTimeout(()=>{consulta.disabled=false;consulta.textContent='Solicitar atualização';},Math.min(espera*1000,2147483647));
    }
    actions.append(consulta);
    if(c.fonte!=='demo' && pendente)actions.append(button('Verificar atualização',async()=>{await load();status('Situação da fila atualizada. Esta ação não consulta o CNJ.');}));
  }
  if (c.versao_id || c.erro) actions.append(button(c.versao_id ? 'Linha do tempo' : 'Histórico de consultas', () => history(c.id, c.apelido || c.numero)));
  if (c.versao_id) {
    if (!c.conferido) actions.append(button('Conferir esta versão', () => review(c.id, c.versao_id)));
  }
  if (!c.arquivado) actions.append(button('Criar providência', () => abrirProvidencia(c.id, c.versao_id, c.apelido || c.numero)));
  if (c.fonte === 'demo' && c.versao_id && !c.etapa && !c.arquivado) actions.append(button('Simular nova movimentação', async () => {
    await api(`casos/${c.id}/avancar-demo`, {}); await load();
    status('A fonte fictícia recebeu uma novidade. Clique em Consultar novidade para comparar.');
  }));
  card.append(actions, editor(c));
  acompanharAtualizacoes();
  return card;
}

async function review(id, version) {
  await api(`casos/${id}/revisar`, { versao_id: version });
  await load(); status('Leitura registrada para a versão apresentada.');
}

function editor(c) {
  const details = text('details', '', 'case-editor');
  details.append(text('summary', 'Editar organização e periodicidade'));
  const form = text('form', ''), grid = text('div', '', 'editor-grid');
  const name = field(grid, 'Apelido', c.apelido), tags = field(grid, 'Etiquetas', c.etiquetas);
  const owner = field(grid, 'Responsável', '', 'select'), interval = field(grid, 'Periodicidade', '', 'select');
  name.maxLength = 120; tags.maxLength = 200;
  for (const member of membros) { const option = text('option', member.email); option.value = member.usuario; owner.append(option); }
  owner.value = c.responsavel;
  for (const [value, label] of [[0, 'Somente manual'], [900, 'A cada 15 minutos'], [3600, 'A cada hora'], [86400, 'Diariamente']]) {
    const option = text('option', label); option.value = value; interval.append(option);
  }
  interval.value = c.intervalo;
  const observations = field(form, 'Observações internas', c.observacoes, 'textarea'); observations.maxLength = 2000;
  form.prepend(grid);
  const save = text('button', 'Salvar alterações', 'button dark'); form.append(save);
  form.onsubmit = event => {
    event.preventDefault();
    run(async () => {
      await api(`casos/${c.id}/alterar`, { apelido: name.value, etiquetas: tags.value, observacoes: observations.value, responsavel: Number(owner.value), intervalo: Number(interval.value) });
      await load(); status('Organização atualizada. A periodicidade depende de manter o servidor em execução.');
    });
  };
  details.append(form, button(c.arquivado ? 'Reativar acompanhamento' : 'Arquivar acompanhamento', async () => {
    await api(`casos/${c.id}/alterar`, { arquivado: !c.arquivado });
    await load(); status(c.arquivado ? 'Acompanhamento reativado.' : 'Acompanhamento arquivado. Você pode reativá-lo pelo filtro Arquivados.');
  }));
  return details;
}

async function history(id, name) {
  const [entries, details] = await Promise.all([api(`casos/${id}/historico`), api(`casos/${id}/detalhe`)]);
  el('history').replaceChildren(); el('history-panel').hidden = false;
  el('history-title').textContent = 'Linha do tempo · ' + name;
  if(entries.length){
    const consultas=text('section','','query-history');consultas.append(text('h3','Tentativas de consulta'));
    for(const entry of entries){
      const row=text('article','','timeline-entry');
      row.append(text('time',date(entry.instante)),text('strong',entry.estado));
      if(entry.erro)row.append(text('p',entry.erro,'error-note'));
      consultas.append(row);
    }
    el('history').append(consultas);
  }
  for (const version of details.versoes) {
    const block = text('article', '', 'timeline-entry'), diff = JSON.parse(version.diferenca);
    block.append(text('time', date(version.instante)), text('h3', diff.tipo));
    if (diff.tipo === 'primeiro registro') block.append(text('p', 'Esta é a referência inicial usada nas próximas comparações.', 'muted'));
    for (const movement of diff.novos) block.append(text('p', `Novo · ${movement.nome || movement.codigo} · ${movementDate(movement.dataHora)}`, 'new-movement'));
    for (const movement of diff.removidos) block.append(text('p', `Alterado ou removido na fonte · ${movement.nome || movement.codigo}`, 'error-note'));
    if (diff.cadastro) block.append(text('p', 'A fonte apresentou uma alteração cadastral.'));
    const source = text('details', ''); source.append(text('summary', 'Ver os movimentos desta versão'));
    for (const record of JSON.parse(version.dados).registros) for (const movement of record.movimentos) {
      source.append(text('p', `${movementDate(movement.dataHora)} · ${movement.nome || movement.codigo}`));
    }
    block.append(source);
    const reviews = details.conferencias.filter(item => item.versao === version.id);
    for (const item of reviews) block.append(text('span', `Conferido por ${item.email} em ${date(item.instante)}`, 'review-proof'));
    if (!reviews.length) block.append(button('Registrar leitura desta versão', () => review(id, version.id)));
    block.append(button('Criar providência desta versão', () => abrirProvidencia(id, version.id, name)));
    el('history').append(block);
  }
  if (!details.versoes.length) el('history').append(text('p', 'Ainda não há uma versão recebida da fonte. As tentativas com falha não criam informações de processo.', 'muted'));
  const technical = text('details', ''); technical.append(text('summary', 'Diagnóstico técnico das consultas'), text('pre', JSON.stringify(entries, null, 2)));
  el('history').append(technical);
  el('history-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  focusAfterAction = el('history-title'); status(null);
}

function submit(id, action) {
  el(id).onsubmit = event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    run(() => action(data, event));
  };
}

submit('auth-form', async (data, event) => {
  await api('conta/' + (event.submitter?.value || 'login'), data);
  event.target.reset(); await load(); status('Seu caderno está pronto. Selecione o escritório e comece pela demonstração.');
});
submit('case-form', async (data, event) => {
  await api('casos', { ...data, org }); event.target.reset();
  el('search').value = ''; el('filter').value = 'all'; pagina = 0;
  await load(); status('Acompanhamento adicionado. Consulte a fonte para obter a primeira referência.');
});
submit('recover-form', async data => status((await api('conta/recuperar', data)).status));
submit('reset-form', async (data, event) => { status((await api('conta/redefinir', data)).status); event.target.reset(); });
submit('office-form', async data => { await api('organizacao/nome', { ...data, org }); await load(); status('Nome do escritório atualizado.'); });
submit('invite-form', async data => {
  const result = await api('convites/criar', { ...data, org });
  el('invite-token').value = result.token; el('invite-token').parentElement.hidden = false;
  status('Convite criado por 24 horas. Copie o token e entregue-o ao destinatário por um canal privado.');
});
submit('accept-form', async (data, event) => {
  await api('convites/aceitar', data); event.target.reset();
  await load(); status('Convite aceito. O escritório compartilhado já está disponível no seletor.');
});
el('invite-token').parentElement.hidden = true;
el('close-history').onclick = () => { el('history-panel').hidden = true; };
document.querySelector('a[href="#team-panel"]').onclick = () => { el('team-panel').open = true; };
el('logout').onclick = () => run(async () => {
  await api('conta/sair', {}); lista = []; org = null;
  if(typeof pausarGuia==='function')pausarGuia();
  signedIn(false); el('history').replaceChildren(); el('invite-token').value = '';
  status('Sessão encerrada.');
});
el('demo').onclick = () => run(async () => {
  const result = await api('demonstracao', { org });
  if (lista.find(c => c.id === result.id)?.arquivado) await api(`casos/${result.id}/alterar`, { arquivado: false });
  el('search').value = ''; el('filter').value = 'all'; pagina = 0;
  await load();
  status('Demonstração disponível. Siga as instruções acima da lista.');
  document.querySelector(`[data-case-id="${result.id}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
});
el('organization').onchange = event => run(async () => {
  org = Number(event.target.value); pagina = 0; importedPreview = null;
  el('confirm-import').disabled = true;
  el('search').value = ''; el('filter').value = 'all'; el('csv-input').value = ''; el('import-result').textContent = '';
  el('invite-token').value = ''; el('invite-token').parentElement.hidden = true;
  await load(); status('Escritório selecionado. A lista mostra somente os acompanhamentos deste espaço.');
});
el('search').oninput = () => { clearTimeout(buscaTimer); buscaTimer=setTimeout(()=>run(async()=>{ pagina=0; await load(); status(null); }),350); };
el('filter').onchange = () => run(async()=>{ pagina=0; await load(); status(null); });
el('csv-input').oninput = () => { importedPreview = null; el('confirm-import').disabled = true; };
el('confirm-import').disabled = true;
for (const [id, confirm] of [['preview-import', false], ['confirm-import', true]]) el(id).onclick = () => run(async () => {
  const csv = el('csv-input').value;
  if (!csv.trim()) throw new Error('Cole o conteúdo CSV, incluindo o cabeçalho numero;tribunal;apelido.');
  if (confirm && importedPreview !== csv) throw new Error('Valide a prévia deste arquivo antes de importar.');
  const result = await api('importar', { org, csv, confirmar: confirm });
  el('import-result').textContent = result.linhas.map(item => `Linha ${item.linha}: ${item.status}${item.erro ? ' — ' + item.erro : ''}`).join('\n') || 'Nenhuma linha encontrada. Confira o cabeçalho e o separador ponto e vírgula.';
  el('import-result').hidden = false;
  importedPreview = confirm ? null : csv;
  el('confirm-import').disabled = confirm || !result.linhas.some(item => item.status === 'válido');
  if (confirm) await load();
  status(confirm ? 'Importação processada. Confira o resultado de cada linha.' : 'Prévia validada. Revise o relatório e confirme a importação.');
});

const exportButton = button('Exportar carteira CSV', async () => {
  const response = await fetch('/api/exportar?org=' + org);
  if (!response.ok) throw new Error('Não foi possível exportar. Verifique sua sessão.');
  const url = URL.createObjectURL(await response.blob()), link = document.createElement('a');
  link.href = url; link.download = 'caderno-ambar.csv'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000); status('CSV preparado com a carteira do escritório selecionado.');
});
document.querySelector('.search-bar').append(exportButton);
const preferenceActions = text('div', '', 'preference-actions');
preferenceActions.append(button('Ativar avisos por e-mail', async () => status((await api('preferencias', { email: true })).status)),
  button('Desativar avisos por e-mail', async () => status((await api('preferencias', { email: false })).status)));
el('notifications').after(preferenceActions);

let aplicacaoIniciada = false;
function iniciarAplicacao() {
  if (aplicacaoIniciada) return;
  aplicacaoIniciada = true;
  run(async () => {
    try { await load(); status(null); }
    catch (error) { if (error.status === 401) { signedIn(false); status(null); } else throw error; }
  }, 'Abrindo seu caderno…');
}
document.addEventListener('DOMContentLoaded', iniciarAplicacao, { once: true });
