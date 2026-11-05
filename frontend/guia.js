'use strict';
let guiaAtivo=false,guiaPasso=0;
const chaveGuia='ambar.guia.aplicacao.v1';
const demoGuia=()=>lista.find(c=>c.fonte==='demo'&&!c.arquivado);
const botaoCaso=nome=>{
  const c=demoGuia();
  return c ? [...document.querySelectorAll(`[data-case-id="${c.id}"] button`)].find(b=>b.textContent===nome) : null;
};
const temNovidade=c=>!!c?.snapshot&&JSON.parse(c.snapshot).registros.some(r=>r.movimentos.some(m=>m.codigo===123));
const etapasGuia=[
 {titulo:'Este é seu escritório ativo.',descricao:'Os processos, a equipe e as providências pertencem ao escritório selecionado. Uma conta pode participar de mais de um espaço.',instrucao:'Mantenha o escritório atual ou selecione outro. Depois, continue.',alvo:()=>el('organization'),manual:true},
 {titulo:'Comece com uma demonstração segura.',descricao:'Você não precisa informar um processo real para aprender. Este exemplo fica no seu escritório e está identificado como fictício.',instrucao:'Clique em Carregar demonstração ou Ver demonstração.',alvo:()=>el('demo'),evento:p=>p.includes('demonstracao'),pronto:()=>!!demoGuia()},
 {titulo:'Guarde a primeira referência.',descricao:'Consultar lê a fonte e registra a informação encontrada. A primeira consulta será a base das comparações seguintes.',instrucao:'No exemplo fictício, clique em Consultar referência.',alvo:()=>botaoCaso('Consultar referência')||botaoCaso('Consultar novamente'),evento:p=>p.some(v=>/casos\/\d+\/consultar$/.test(v)),pronto:()=>!!demoGuia()?.versao_id},
 {titulo:'Agora a fonte fictícia vai mudar.',descricao:'O botão de simulação pertence somente ao exemplo. Ele cria uma novidade na fonte de treino, sem consultar ou alterar um tribunal.',instrucao:'Clique em Simular nova movimentação.',alvo:()=>botaoCaso('Simular nova movimentação'),evento:p=>p.some(v=>v.endsWith('/avancar-demo')),pronto:()=>!!demoGuia()?.etapa},
 {titulo:'Consulte para descobrir a diferença.',descricao:'A simulação muda a fonte, mas o caderno só recebe a novidade depois da consulta. Você verá o novo movimento no cartão.',instrucao:'Clique em Consultar novidade.',alvo:()=>botaoCaso('Consultar novidade')||botaoCaso('Consultar novamente'),evento:p=>p.some(v=>/casos\/\d+\/consultar$/.test(v)),pronto:()=>temNovidade(demoGuia())},
 {titulo:'Abra a linha do tempo.',descricao:'Cada versão mostra o que foi encontrado, a diferença e as leituras já registradas. O diagnóstico técnico fica recolhido.',instrucao:'Clique em Linha do tempo no exemplo.',alvo:()=>botaoCaso('Linha do tempo'),evento:p=>p.some(v=>v.endsWith('/detalhe')),pronto:()=>!el('history-panel').hidden},
 {titulo:'Registre a leitura da versão.',descricao:'Conferir significa que você leu aquele conteúdo. Isso não conclui uma providência e não realiza um ato processual.',instrucao:'Use Conferir esta versão no cartão ou Registrar leitura desta versão na linha do tempo.',alvo:()=>botaoCaso('Conferir esta versão')||[...el('history').querySelectorAll('button')].find(b=>b.textContent==='Registrar leitura desta versão'),evento:p=>p.some(v=>v.endsWith('/revisar')),pronto:()=>!!demoGuia()?.conferido},
 {titulo:'Transforme a informação em uma ação.',descricao:'Uma providência registra o que precisa ser feito. Ela pode estar ligada ao processo inteiro ou a uma versão específica.',instrucao:'Clique em Criar providência no exemplo.',alvo:()=>botaoCaso('Criar providência'),pronto:()=>!el('action-panel').hidden},
 {titulo:'Defina quem faz e quem revisa.',descricao:'Preencha título, orientações, responsável, revisor e data interna. Essa data organiza o trabalho; não é um prazo jurídico calculado.',instrucao:'Preencha o formulário destacado e clique em Criar providência. Você pode usar um exemplo de tarefa para estudar.',alvo:()=>el('action-form'),evento:p=>p.includes('providencias'),pronto:()=>el('action-panel').hidden&&rotinaAberta},
 {titulo:'Acompanhe o trabalho em Minha rotina.',descricao:'A fazer → Em andamento → Aguardando revisão → Concluída. Enviar à revisão exige um resultado descrito, e concluir exige revisor ou administrador. O filtro Equipe mostra tarefas atribuídas a outras pessoas.',instrucao:'Explore os filtros e o formulário Atualizar providência. Você pode praticar essas etapas no exemplo e continuar quando entender.',alvo:()=>el('routine-view'),manual:true,preparar:()=>{trocarArea(true);}},
 {titulo:'A equipe trabalha no mesmo espaço.',descricao:'Administradores convidam integrantes; quem recebe aceita o convite com sua própria conta. Revogar acesso preserva os processos e reatribui responsabilidades. Não é necessário convidar alguém para concluir o treino.',instrucao:'Veja a área de equipe. Os controles disponíveis dependem da sua permissão.',alvo:()=>el('team-panel'),manual:true,preparar:()=>{el('team-panel').open=true;}},
 {titulo:'Quando tiver uma carteira real, importe com revisão.',descricao:'Você pode cadastrar um número CNJ ou selecionar um CSV. A importação exige uma prévia e só confirma as linhas válidas. Nunca use um número inventado esperando dados reais.',instrucao:'Conheça o formulário. Esta etapa é explicativa: você não precisa importar dados para terminar o guia.',alvo:()=>document.querySelector('.intake-panel'),manual:true,preparar:()=>{trocarArea(false);document.querySelector('.intake-panel').open=true;}},
 {titulo:'Saiba quando a consulta precisa de ajuda.',descricao:'Uma consulta com falha preserva a referência anterior. Administradores podem ver tentativas, próximas execuções e solicitar reprocessamento. Um resultado sem diferença não comprova que o tribunal está atualizado.',instrucao:'Se você administra o escritório, use Atualizar diagnóstico para conhecer a fila. Outros membros devem comunicar falhas ao administrador.',alvo:()=>!el('operation-panel').hidden?el('operation-panel'):el('notifications').parentElement,manual:true,preparar:()=>{if(!el('operation-panel').hidden)el('operation-panel').open=true;else el('notifications').parentElement.open=true;}},
 {titulo:'Escolha como receber os avisos.',descricao:'As novidades ficam na área da equipe. Os botões de e-mail ativam ou desativam sua preferência. No ambiente de desenvolvimento, mensagens ficam na caixa local; envio externo exige configuração.',instrucao:'Conheça os controles de aviso. Não é necessário ativar e-mail para concluir este guia.',alvo:()=>document.querySelector('.preference-actions'),manual:true,preparar:()=>{el('notifications').parentElement.open=true;}},
 {titulo:'Você sabe onde começar e onde conferir.',descricao:'Volte a Processos para acompanhar informações e a Minha rotina para executar providências. Aprender a usar retoma este guia; Recomeçar reinicia apenas a orientação, sem apagar seus dados. Use Sair da conta ao terminar em um computador compartilhado.',instrucao:'Para dados reais, confira a configuração e a cobertura da fonte com o administrador.',alvo:()=>el('show-routine'),manual:true}
];

function salvarGuia(){try{localStorage.setItem(chaveGuia,JSON.stringify({passo:guiaPasso,ativo:guiaAtivo}));}catch{}}
function limparDestaqueGuia(){document.querySelectorAll('.guide-target').forEach(n=>{n.classList.remove('guide-target');n.removeAttribute('aria-describedby');});}
function pausarGuia(){guiaAtivo=false;limparDestaqueGuia();el('app-guide').hidden=true;document.body.classList.remove('guide-active');salvarGuia();}
function mostrarGuia(){
  if(!guiaAtivo)return;
  const etapa=etapasGuia[guiaPasso];etapa.preparar?.();limparDestaqueGuia();
  el('app-guide').hidden=false;document.body.classList.add('guide-active');
  el('app-guide-progress').textContent=`GUIA DA ÁREA DE TRABALHO · ${guiaPasso+1} DE ${etapasGuia.length}`;
  el('app-guide-bar').value=(guiaPasso+1)/etapasGuia.length;
  el('app-guide-title').textContent=etapa.titulo;el('app-guide-description').textContent=etapa.descricao;
  const pronto=!!etapa.pronto?.();
  el('app-guide-instruction').textContent=pronto&&!etapa.manual?'Esta etapa já está pronta. Você pode continuar sem repetir a ação.':etapa.instrucao;
  el('app-guide-next').hidden=!etapa.manual&&!pronto;
  el('app-guide-next').textContent=guiaPasso===etapasGuia.length-1?'Concluir orientação':'Entendi, continuar';
  el('app-guide-back').disabled=guiaPasso===0;
  const alvo=etapa.alvo();
  if(alvo){alvo.classList.add('guide-target');alvo.setAttribute('aria-describedby','app-guide-description');alvo.scrollIntoView({behavior:'smooth',block:'center'});}
  salvarGuia();
}
function avancarGuia(){if(guiaPasso===etapasGuia.length-1){pausarGuia();status('Orientação concluída. Você pode retomá-la em Aprender a usar.');return;}guiaPasso++;mostrarGuia();}
function iniciarGuia(recomecar=false){
  if(busy)return;
  if(el('workspace').hidden){location.assign('acesso.html?modo=cadastro&guia=1');return;}
  if(recomecar)guiaPasso=0;
  guiaAtivo=true;mostrarGuia();
}
el('start-app-guide').onclick=()=>iniciarGuia();
el('pause-app-guide').onclick=pausarGuia;
el('app-guide-next').onclick=()=>{const e=etapasGuia[guiaPasso];if(e.manual||e.pronto?.())avancarGuia();};
el('app-guide-back').onclick=()=>{if(guiaPasso>0){guiaPasso--;mostrarGuia();}};
el('app-guide-restart').onclick=()=>iniciarGuia(true);
try{const progresso=JSON.parse(localStorage.getItem(chaveGuia)||'null');if(Number.isInteger(progresso?.passo))guiaPasso=Math.max(0,Math.min(etapasGuia.length-1,progresso.passo));}catch{}
let tentouInicio=false;
window.addEventListener('ambar:acao',event=>{
  if(!tentouInicio&&!el('workspace').hidden){tentouInicio=true;if(new URLSearchParams(location.search).get('guia')==='1')iniciarGuia(true);}
  if(!guiaAtivo)return;
  if(el('workspace').hidden){pausarGuia();return;}
  const etapa=etapasGuia[guiaPasso],paths=event.detail?.paths||[];
  if(!etapa.manual&&etapa.pronto?.()&&(!etapa.evento||etapa.evento(paths)))avancarGuia();
  else mostrarGuia();
});
if(location.hash==='#recuperar'){el('auth').querySelector('details').open=true;}
// Inicializa após os scripts de rotina e orientação estarem disponíveis.
iniciarAplicacao();
