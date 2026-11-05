'use strict';
// Usa os componentes e o controle de sessão da aplicação existente.
const painelConta = text('details', '', 'real-panel');
painelConta.id = 'account-panel';
painelConta.append(text('summary', 'Minha conta e confirmação de e-mail'));
const contaInfo = text('p', '', 'helper');
const verificar = button('Enviar código de confirmação', async () => {
  status((await api('conta/verificacao/solicitar', {})).status);
});
const confirmarForm = text('form', '');
const codigo = field(confirmarForm, 'Código recebido no e-mail');
codigo.required = true; codigo.autocomplete = 'off'; codigo.maxLength = 128;
const confirmarBtn = text('button', 'Confirmar meu e-mail', 'button dark');
confirmarForm.append(confirmarBtn);
confirmarForm.onsubmit = event => {
  event.preventDefault();
  run(async () => {
    const resposta = await api('conta/verificacao/confirmar', {token:codigo.value});
    codigo.value = ''; await load(); status(resposta.status);
  });
};
painelConta.append(contaInfo, verificar, confirmarForm,
  text('p', 'Em desenvolvimento, os códigos ficam em output/email-local. Em produção, o envio depende do canal de e-mail configurado.', 'helper'));
el('workspace').prepend(painelConta);

const diario = text('section', '', 'daily-summary real-panel');
diario.setAttribute('aria-labelledby', 'daily-title');
const diarioTitulo = text('h2', 'O que precisa de atenção hoje'); diarioTitulo.id='daily-title';
const diarioTexto = text('p', '', 'helper');
const diarioAcoes = text('div', '', 'real-actions');
diario.append(diarioTitulo, diarioTexto, diarioAcoes);
el('metrics').after(diario);

const dadosPainel = text('details', '', 'real-panel');
dadosPainel.id = 'data-admin';
dadosPainel.append(text('summary', 'Dados do escritório'),
  text('p', 'Exporte o histórico para guarda administrativa ou registre uma solicitação de retenção e exclusão. A solicitação exige análise; ela não apaga registros automaticamente.', 'helper'));
dadosPainel.append(button('Exportar dados do escritório', async () => {
  const response = await fetch('/api/dados/exportar?org='+org);
  if (!response.ok) throw Error('Não foi possível exportar os dados. Verifique seu acesso.');
  const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');
  link.href=url;link.download='escritorio-ambar.json';link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);status('Exportação preparada. Guarde o arquivo em local protegido.');
}));
const pedidoDados = text('form', '');
const tipoDados = field(pedidoDados,'Tipo de solicitação','','select');
for (const [value,label] of [['retencao','Revisar retenção dos dados'],['exclusao','Solicitar exclusão dos dados']]) {
  const option=text('option',label);option.value=value;tipoDados.append(option);
}
const motivoDados = field(pedidoDados,'Justificativa','','textarea');motivoDados.required=true;motivoDados.minLength=10;motivoDados.maxLength=2000;
pedidoDados.append(text('button','Registrar solicitação','button outline'));
pedidoDados.onsubmit=event=>{event.preventDefault();run(async()=>{
  const r=await api('dados/solicitar',{org,tipo:tipoDados.value,motivo:motivoDados.value});
  pedidoDados.reset();status(r.status);
});};
dadosPainel.append(pedidoDados);el('workspace').append(dadosPainel);

async function carregarPainelPiloto(contexto) {
  const [conta,resumo]=await Promise.all([api('conta'),api('resumo?org='+org)]);
  contaInfo.textContent=conta.email+(conta.email_verificado?' · E-mail confirmado.':' · Confirme seu e-mail para compartilhar o escritório e consultar fontes reais. O exemplo fictício continua disponível.');
  verificar.hidden=Boolean(conta.email_verificado);confirmarForm.hidden=Boolean(conta.email_verificado);
  dadosPainel.hidden=contexto.papel!=='admin';
  diarioTexto.textContent=`${resumo.minhas} providências comigo · ${resumo.vencidas} com data interna vencida · ${resumo.revisar} para minha revisão. As contagens de processos acima abrangem toda a carteira.`;
  diarioAcoes.replaceChildren(...[['Ver minhas providências','minhas'],['Revisar atividades','revisar'],['Ver datas internas vencidas','atrasadas']].map(([label,filtro])=>button(label,async()=>{
    trocarArea(true);el('routine-filter').value=filtro;rotinaPagina=1;await carregarRotina();status(null);
  })));
}
