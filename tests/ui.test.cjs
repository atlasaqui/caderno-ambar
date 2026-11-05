// Testes de comportamento em DOM simulado. Não substituem inspeção visual.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { JSDOM } = require('jsdom');
const html = fs.readFileSync('frontend/acompanhamento.html', 'utf8');
const code = fs.readFileSync('frontend/acompanhamento.js', 'utf8');
const routineCode = fs.readFileSync('frontend/rotina.js', 'utf8');
const pilotCode = fs.readFileSync('frontend/piloto.js', 'utf8');
const guideCode = fs.readFileSync('frontend/guia.js', 'utf8');

async function waitFor(check) {
  for (let i = 0; i < 100; i++) { if (check()) return; await new Promise(r => setTimeout(r, 5)); }
  throw new Error('Estado esperado não apareceu.');
}

function fixture(scenario = {}) {
  const dom = new JSDOM(html, { url: 'http://127.0.0.1:8093/acompanhamento.html', runScripts: 'outside-only' });
  const w = dom.window;
  w.HTMLElement.prototype.scrollIntoView = function () {};
  w.confirm = () => true;
  let authenticated = false, cases = [], queries = 0, actions = [];
  const events = [];
  const contexts = [{ id: 1, nome: 'Escritório A', papel: 'admin' }, { id: 2, nome: 'Escritório B', papel: 'membro' }];
  const source = etapa => ({ registros: [{ grau: 'G1', classe: { nome: 'Demonstração' }, movimentos: [
    { codigo: 26, nome: 'Distribuição fictícia', dataHora: '2026-11-01T09:00:00' },
    ...(etapa ? [{ codigo: 123, nome: 'Audiência fictícia', dataHora: '2026-11-03T10:00:00' }] : [])
  ] }] });
  w.fetch = async (url, options = {}) => {
    const path = new URL(url, w.location.href), body = options.body ? JSON.parse(options.body) : {};
    events.push(path.pathname);
    let result, status = 200;
    if (path.pathname === '/api/conta/cadastro' || path.pathname === '/api/conta/login') { authenticated = true; result = { status: 'autenticado' }; }
    else if (!authenticated) { status = 401; result = { error: 'Entre na sua conta.' }; }
    else if (path.pathname === '/api/contexto') result = contexts;
    else if (path.pathname === '/api/membros') result = [{ usuario: 1, email: 'teste@example.com', papel: 'admin' }];
    else if (path.pathname === '/api/notificacoes') result = [];
    else if (path.pathname === '/api/me') result = { id: 1, email: 'teste@example.com' };
    else if (path.pathname === '/api/rotina') result = { itens: actions, total: actions.length, resumo: { minhas: actions.length, atrasadas: 0, revisar: 0 } };
    else if (path.pathname === '/api/providencias') {
      actions.push({ ...body, id: 1, org: 1, estado: 'a_fazer', revisao: 1, evidencia: '', responsavel_email: 'teste@example.com', revisor_email: 'teste@example.com', apelido: 'Exemplo fictício' }); result = { id: 1, status: 'Providência criada.' };
    }
    else if (/\/api\/providencias\/\d+\/alterar/.test(path.pathname)) { Object.assign(actions[0], body, { revisao: actions[0].revisao + 1 }); result = { status: 'Providência atualizada.' }; }
    else if (path.pathname === '/api/conta') result = {email:'teste@example.com',email_verificado:null};
    else if (path.pathname === '/api/conta/verificacao/solicitar') result = {status:'Código disponibilizado no canal configurado.'};
    else if (path.pathname === '/api/conta/verificacao/confirmar') result = {status:'E-mail confirmado.'};
    else if (path.pathname === '/api/resumo') result = {minhas:actions.length,vencidas:0,revisar:0};
    else if (path.pathname === '/api/carteira') {
      const itens=cases.filter(c=>c.org===Number(path.searchParams.get('org')));
      result={itens,total:itens.length,pagina:1,resumo:{total:itens.length,ativos:itens.length,conferir:itens.filter(c=>c.versao_id&&!c.conferido).length,falhas:0,atrasadas:0},demonstracao:itens.find(c=>c.fonte==='demo')||null};
    }
    else if (path.pathname === '/api/demonstracao') {
      if (!cases.length) cases.push({ id: 1, org: 1, numero: 'DEMO-1', tribunal: 'tjpe', apelido: 'Exemplo fictício', fonte: 'demo', etapa: 0, conferido: 0, arquivado: 0, intervalo: 0, responsavel: 1, responsavel_email: 'teste@example.com' });
      if(scenario.fonteReal)Object.assign(cases[0],{fonte:'datajud',snapshot:JSON.stringify(source(0)),versao_id:1,ultima_ok:1,erro:'Fonte temporariamente indisponível.',codigo_falha:scenario.sobrecarga ? 'fonte_sobrecarregada' : ''});
      result = { id: 1 };
    } else if(path.pathname.endsWith('/agendar')) {
      Object.assign(cases[0],{atualizacao_pendente:1,proxima_tentativa:Date.now()/1000+90});
      status=202;result={agendada:true,status:'Atualização solicitada em segundo plano.'};
    } else if (path.pathname.endsWith('/consultar')) {
      queries++;
      const c = cases[0];
      if(scenario.falharConsulta){
        c.fonte='datajud';c.erro='DataJud não respondeu no tempo de consulta.';c.proxima_tentativa=Date.now()/1000+90;
        status=504;result={error:c.erro,code:'fonte_timeout',retry_after:90};
      }else{
        c.snapshot = JSON.stringify(source(c.etapa)); c.versao_id = c.etapa ? 2 : 1; c.ultima_ok = 1; c.conferido = 0;
        result = { estado: c.etapa ? 'nova movimentação' : 'primeiro registro' };
      }
    } else if (path.pathname.endsWith('/avancar-demo')) { cases[0].etapa = 1; result = { status: 'atualizado' }; }
    else if (path.pathname.endsWith('/revisar')) { cases[0].conferido = 1; result = {}; }
    else if (path.pathname.endsWith('/historico')) result = cases[0]?.erro ? [{instante:1,estado:'falha',erro:cases[0].erro}] : [];
    else if (path.pathname.endsWith('/detalhe')) result = { versoes: cases[0].versao_id ? [{ id: cases[0].versao_id, instante: 1, dados: cases[0].snapshot, diferenca: JSON.stringify({ tipo: 'nova movimentação', novos: source(1).registros[0].movimentos.slice(1), removidos: [] }) }] : [], conferencias: [] };
    else if (path.pathname === '/api/conta/sair') { authenticated = false; result = {}; }
    else if (path.pathname === '/api/importar') result = { linhas: [{ linha: 2, status: 'válido' }] };
    else result = {};
    return { ok: status < 400, status, headers: { get: () => 'application/json' }, json: async () => structuredClone(result) };
  };
  w.eval(code + '\n' + routineCode + '\n' + pilotCode + '\n' + guideCode);
  return { dom, w, d: w.document, events, queries: () => queries };
}

function submit(w, form, submitter) {
  form.dispatchEvent(new w.SubmitEvent('submit', { bubbles: true, cancelable: true, submitter }));
}

async function login(f) {
  await waitFor(() => f.d.getElementById('status').hidden);
  const form = f.d.getElementById('auth-form');
  form.elements.email.value = 'teste@example.com'; form.elements.senha.value = 'senha-de-teste';
  submit(f.w, form, form.querySelector('[value="login"]'));
  await waitFor(() => !f.d.getElementById('workspace').hidden && !f.d.getElementById('workspace').inert);
}

function click(f, label) {
  const b = [...f.d.querySelectorAll('button')].find(b => b.textContent === label && !b.disabled);
  assert.ok(b, `Botão disponível: ${label}`); b.click();
}

test('fluxo de escritório, referência, novidade, histórico e conferência', async () => {
  const f = fixture();
  try {
    await login(f);
    assert.equal(f.d.querySelectorAll('.metric').length, 4);
    assert.equal(f.d.getElementById('pagination').hidden, true);
    click(f, 'Carregar demonstração');
    await waitFor(() => f.d.querySelector('.case-card') && !f.d.getElementById('workspace').inert);
    assert.match(f.d.getElementById('demo-help').textContent, /Passo 1/);
    assert.ok(![...f.d.querySelectorAll('.case-card button')].some(b => b.textContent === 'Linha do tempo'));
    click(f, 'Consultar referência');
    await waitFor(() => f.d.getElementById('demo-help').textContent.includes('Passo 2') && !f.d.getElementById('workspace').inert);
    click(f, 'Simular nova movimentação');
    await waitFor(() => [...f.d.querySelectorAll('button')].some(b => b.textContent === 'Consultar novidade') && !f.d.getElementById('workspace').inert);
    click(f, 'Consultar novidade');
    await waitFor(() => f.d.getElementById('demo-help').textContent.includes('Passo 3') && !f.d.getElementById('workspace').inert);
    click(f, 'Linha do tempo');
    await waitFor(() => !f.d.getElementById('history-panel').hidden && !f.d.getElementById('workspace').inert);
    assert.match(f.d.getElementById('history').textContent, /Audiência fictícia/);
    assert.equal(f.d.activeElement.id, 'history-title');
    click(f, 'Conferir esta versão');
    await waitFor(() => f.d.getElementById('demo-help').textContent.includes('Percurso concluído') && !f.d.getElementById('workspace').inert);
    assert.equal(f.queries(), 2);
  } finally { f.dom.window.close(); }
});

test('primeira consulta com falha atualiza cartão e permite ler o histórico',async()=>{
  const f=fixture({falharConsulta:true});
  try{
    await login(f);click(f,'Carregar demonstração');
    await waitFor(()=>f.d.querySelector('.case-card')&&!f.d.getElementById('workspace').inert);
    click(f,'Consultar referência');
    await waitFor(()=>f.d.querySelector('.case-card .source-notice')&&!f.d.getElementById('workspace').inert);
    assert.match(f.d.getElementById('status').textContent,/não respondeu/);
    const esperando=[...f.d.querySelectorAll('.case-card button')].find(b=>b.textContent==='Aguardando nova tentativa');
    assert.ok(esperando);assert.equal(esperando.disabled,true);
    click(f,'Histórico de consultas');
    await waitFor(()=>!f.d.getElementById('history-panel').hidden&&!f.d.getElementById('workspace').inert);
    assert.match(f.d.querySelector('.query-history').textContent,/não respondeu/);
    assert.match(f.d.getElementById('history').textContent,/Ainda não há uma versão/);
    assert.equal(f.queries(),1);
  }finally{f.dom.window.close();}
});

test('fonte real usa fila sem bloquear dados nem repetir consulta externa',async()=>{
  const f=fixture({fonteReal:true});
  try{
    await login(f);click(f,'Carregar demonstração');
    await waitFor(()=>f.d.querySelector('.case-card .source-notice')&&!f.d.getElementById('workspace').inert);
    assert.match(f.d.querySelector('.case-card').textContent,/Dados salvos disponíveis/);
    click(f,'Solicitar atualização');
    await waitFor(()=>f.d.querySelector('.case-card').textContent.includes('Atualização na fila')&&!f.d.getElementById('workspace').inert);
    assert.equal(f.queries(),0);
    assert.equal(f.events.filter(x=>x.endsWith('/agendar')).length,1);
    assert.match(f.d.querySelector('.movement-preview').textContent,/Distribuição fictícia/);
    assert.equal([...f.d.querySelectorAll('.case-card button')].find(b=>b.textContent==='Atualização solicitada').disabled,true);
    click(f,'Verificar atualização');
    await waitFor(()=>!f.d.getElementById('workspace').inert);
    assert.equal(f.queries(),0);assert.equal(f.events.filter(x=>x.endsWith('/agendar')).length,1);
  }finally{f.dom.window.close();}
});

test('sobrecarga confirmada do fornecedor tem mensagem específica sem expor diagnóstico bruto',async()=>{
  const f=fixture({fonteReal:true,sobrecarga:true});
  try{
    await login(f);click(f,'Carregar demonstração');
    await waitFor(()=>f.d.querySelector('.source-notice')&&!f.d.getElementById('workspace').inert);
    assert.match(f.d.querySelector('.source-notice strong').textContent,/serviço de buscas do CNJ está sobrecarregado/);
    assert.match(f.d.querySelector('.movement-preview').textContent,/Distribuição fictícia/);
    assert.doesNotMatch(f.d.querySelector('.source-notice').textContent,/es_rejected_execution_exception/);
  }finally{f.dom.window.close();}
});

test('troca de escritório limpa filtros e respeita o papel de membro', async () => {
  const f = fixture();
  try {
    await login(f);
    f.d.getElementById('search').value = 'consulta antiga';
    const select = f.d.getElementById('organization'); select.value = '2';
    select.dispatchEvent(new f.w.Event('change'));
    await waitFor(() => f.d.getElementById('invite-form').hidden && !f.d.getElementById('workspace').inert);
    assert.equal(f.d.getElementById('search').value, '');
    assert.equal(f.d.getElementById('office-form').hidden, true);
    assert.equal(f.d.getElementById('data-admin').hidden, true);
    assert.match(f.d.getElementById('cases').textContent, /primeiro acompanhamento/);
  } finally { f.dom.window.close(); }
});

test('painel da conta orienta confirmação sem expor código na resposta', async () => {
  const f=fixture();
  try {
    await login(f);
    assert.match(f.d.getElementById('account-panel').textContent,/Confirme seu e-mail/);
    click(f,'Enviar código de confirmação');
    await waitFor(()=>f.events.includes('/api/conta/verificacao/solicitar')&&!f.d.getElementById('workspace').inert);
    assert.match(f.d.getElementById('status').textContent,/canal configurado/);
    assert.equal(f.d.querySelector('#account-panel input').value,'');
    assert.match(f.d.querySelector('.daily-summary').textContent,/providências comigo/);
  } finally {f.dom.window.close();}
});

test('importação exige prévia e invalida aprovação quando CSV muda', async () => {
  const f = fixture();
  try {
    await login(f);
    const csv = f.d.getElementById('csv-input'), confirm = f.d.getElementById('confirm-import');
    assert.equal(confirm.disabled, true);
    csv.value = 'numero;tribunal;apelido\nexemplo;tjpe;Teste';
    click(f, 'Validar prévia');
    await waitFor(() => !confirm.disabled && !f.d.getElementById('workspace').inert);
    csv.value += '\nOutra linha'; csv.dispatchEvent(new f.w.Event('input'));
    assert.equal(confirm.disabled, true);
  } finally { f.dom.window.close(); }
});

test('marca sem ícone, recursos versionados e ações agrupadas', async () => {
  const f = fixture();
  try {
    await login(f);
    assert.equal(f.d.querySelector('.brand img'), null);
    assert.match(f.d.querySelector('link[rel="stylesheet"]').href, /v=piloto1/);
    const exportButton = [...f.d.querySelectorAll('.search-bar button')].find(b => b.textContent === 'Exportar carteira CSV');
    assert.ok(exportButton);
    assert.equal(exportButton.disabled, true);
    assert.equal(f.d.querySelectorAll('.preference-actions button').length, 2);
    assert.equal(f.d.querySelector('.page-intro h1').textContent, 'Carteira de processos.');
  } finally { f.dom.window.close(); }
});

test('processo gera providência e a rotina acompanha execução e revisão', async () => {
  const f = fixture();
  try {
    await login(f);click(f, 'Carregar demonstração');
    await waitFor(() => f.d.querySelector('.case-card') && !f.d.getElementById('workspace').inert);
    click(f, 'Criar providência');
    await waitFor(() => !f.d.getElementById('action-panel').hidden && !f.d.getElementById('workspace').inert);
    const form = f.d.getElementById('action-form');
    form.elements.titulo.value = 'Analisar movimentação';form.elements.data_interna.value = '';
    submit(f.w, form, form.querySelector('button'));
    await waitFor(() => f.d.querySelector('.action-card') && !f.d.getElementById('workspace').inert);
    assert.equal(f.d.getElementById('cases-view').hidden, true);
    assert.equal(f.d.getElementById('routine-view').hidden, false);
    assert.match(f.d.getElementById('routine-list').textContent, /Analisar movimentação/);
    assert.match(f.d.querySelector('.action-card').textContent, /Data interna: não definida/);
    assert.doesNotMatch(f.d.querySelector('.action-card').textContent, /· vencida/);
    for (const estado of ['em_andamento', 'em_revisao', 'concluida']) {
      const edit = f.d.querySelector('.action-card form');edit.querySelector('select').value = estado;
      edit.querySelector('textarea').value = 'Análise registrada no documento interno.';
      submit(f.w, edit, edit.querySelector('button'));
      await waitFor(() => f.d.getElementById('status').textContent === 'Providência atualizada.' && !f.d.getElementById('workspace').inert);
    }
    assert.match(f.d.getElementById('routine-list').textContent, /Concluída/);
  } finally { f.dom.window.close(); }
});

test('guia acompanha ações bem-sucedidas e pode pausar e retomar', async () => {
  const f = fixture();
  try {
    await login(f);click(f,'Aprender a usar');
    assert.equal(f.d.getElementById('app-guide').hidden,false);
    assert.match(f.d.getElementById('app-guide-title').textContent,/escritório/);
    click(f,'Entendi, continuar');click(f,'Carregar demonstração');
    await waitFor(()=>f.d.getElementById('app-guide-title').textContent.includes('primeira referência')&&!f.d.getElementById('workspace').inert);
    click(f,'Consultar referência');
    await waitFor(()=>f.d.getElementById('app-guide-title').textContent.includes('fonte fictícia vai mudar')&&!f.d.getElementById('workspace').inert);
    click(f,'Simular nova movimentação');
    await waitFor(()=>f.d.getElementById('app-guide-title').textContent.includes('descobrir a diferença')&&!f.d.getElementById('workspace').inert);
    click(f,'Consultar novidade');
    await waitFor(()=>f.d.getElementById('app-guide-title').textContent.includes('Abra a linha')&&!f.d.getElementById('workspace').inert);
    click(f,'Pausar ×');assert.equal(f.d.getElementById('app-guide').hidden,true);
    click(f,'Aprender a usar');assert.match(f.d.getElementById('app-guide-title').textContent,/Abra a linha/);
    const salvo=JSON.parse(f.w.localStorage.getItem('ambar.guia.aplicacao.v1'));
    assert.equal(typeof salvo.passo,'number');assert.deepEqual(Object.keys(salvo).sort(),['ativo','passo']);
    click(f,'Linha do tempo');
    await waitFor(()=>f.d.getElementById('app-guide-title').textContent.includes('Registre a leitura')&&!f.d.getElementById('workspace').inert);
    click(f,'Conferir esta versão');
    await waitFor(()=>f.d.getElementById('app-guide-title').textContent.includes('Transforme a informação')&&!f.d.getElementById('workspace').inert);
    click(f,'Criar providência');
    await waitFor(()=>f.d.getElementById('app-guide-title').textContent.includes('Defina quem faz')&&!f.d.getElementById('workspace').inert);
    const form=f.d.getElementById('action-form');form.elements.titulo.value='Treinar a providência';form.elements.data_interna.value='2026-11-15';
    submit(f.w,form,form.querySelector('button'));
    await waitFor(()=>f.d.getElementById('app-guide-title').textContent.includes('Acompanhe o trabalho')&&!f.d.getElementById('workspace').inert);
    for(let i=0;i<10&&f.d.getElementById('app-guide-next').textContent!=='Concluir orientação';i++)click(f,'Entendi, continuar');
    click(f,'Concluir orientação');
    assert.equal(f.d.getElementById('app-guide').hidden,true);
    assert.equal(f.queries(),2);
  } finally { f.dom.window.close(); }
});
