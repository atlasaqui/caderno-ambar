# Atualização do DataJud sem interromper o trabalho

Implementado em 04/11/2026. As falhas externas não foram eliminadas: a alteração faz o aplicativo trabalhar de forma explícita com a indisponibilidade, preservando informações e organizando tentativas.

## Para quem usa

1. Abra um processo e veja a data da última consulta válida.
2. Clique em **Solicitar atualização**. A solicitação é salva e a página fica livre imediatamente.
3. Enquanto aguarda, leia os dados salvos, consulte a linha do tempo ou crie uma providência.
4. O cartão informa fila, consulta em andamento ou tentativa posterior. **Verificar atualização** apenas lê o estado local; não envia outra consulta ao CNJ.
5. Quando a fonte responder com sucesso, a referência e o histórico são atualizados. Sem mudança, a versão existente é reaproveitada.

A tela verifica o estado local a cada 15 segundos enquanto houver tarefa pendente. Essa verificação é pausada durante edição, histórico aberto, outras áreas ou aba oculta para preservar o trabalho em andamento. Nesse intervalo, a consulta externa continua no servidor. Uma tarefa interrompida por reinício pode ser retomada após expirar sua reserva.

## O que mudou no código

| Arquivo | Responsabilidade nesta revisão |
| --- | --- |
| `backend/equipes.py` | Migração aditiva 5 e método `agendar_consulta`. Salva pedido, solicitante, próxima tentativa e código de falha; recusa duplicação da fila e preserva histórico. |
| `backend/piloto.py` | Exige e-mail confirmado e expõe fila, reserva, tentativas e código na carteira, dentro do escritório autorizado. |
| `backend/aplicacao.py` | `POST /api/casos/{id}/agendar` responde HTTP 202. Isso significa aceitação da solicitação, não sucesso da consulta externa. |
| `backend/rotina.py` | O ciclo de consultas atende solicitações avulsas mesmo com periodicidade desligada e processa tarefas em sequência. Usa o solicitante para autorização e auditoria. |
| `frontend/acompanhamento.js` | Exibe dados disponíveis separadamente da situação da atualização, envia solicitações e acompanha o estado local sem travar a tela. |
| `frontend/acompanhamento.css` | Aviso contextual de atualização, com detalhe técnico recolhido e hierarquia visual. |

`tarefas` recebeu `solicitada`, `solicitante` e `codigo`. Não foram apagados casos, contas, consultas ou versões. A nova solicitação registra autoria na auditoria. O endpoint antigo de consulta síncrona permanece para compatibilidade; a interface usa a fila para dados reais e o fluxo imediato para demonstração fictícia.

## Controle das falhas

- Esperas crescentes: base de 90 segundos multiplicada conforme as falhas, até uma hora. Um Retry-After maior do fornecedor prevalece.
- Máximo de cinco falhas consecutivas; depois a execução automática pausa. Uma nova solicitação explícita pode reiniciar o ciclo, respeitando a espera persistida.
- Uma fonte real por vez, com reserva compartilhada no SQLite e pausa mínima de 30 segundos após sucesso.
- Erro de chave, configuração, TLS, proxy, formato ou processo não encontrado não gera repetição automática indefinida.
- Limite, sobrecarga, timeout, rede, erro HTTP transitório ou resultado incompleto podem ser repetidos dentro do limite. Nenhuma falha cria versão fictícia.
- Se o acesso do solicitante for revogado, a tarefa é pausada. O servidor e seu ciclo precisam permanecer ligados; `AMBAR_WORKER=0` desativa esse processamento.

## Verificação

Passaram **55 testes Python e 15 testes de interface**. Os novos cenários cobrem fila durável, duplicação da solicitação, autorização, confirmação de e-mail, processo arquivado, pausa de fonte desativada, espera do fornecedor, recuperação preservando a versão, parada após cinco falhas e HTTP 202 sem acesso imediato à rede. As fontes nesses testes são simuladas.

Na conta local de estudo, o botão foi acionado no navegador. A solicitação retornou imediatamente e a tentativa do servidor recebeu HTTP 429. A fila registrou o código `fonte_limite`, manteve a versão real com 35 movimentos e programou a próxima tentativa. Isso comprova o tratamento da falha, não um novo sucesso externo.

## O que esta alteração não garante

O aplicativo não controla a disponibilidade do CNJ. O motivo exclusivo das recusas externas não foi isolado. Não há troca silenciosa por demonstração. Um processo sem consulta bem-sucedida continua sem dados recebidos. O próximo passo operacional, se a indisponibilidade persistir, é encaminhar evidência técnica ao suporte do fornecedor, sem divulgar chave ou dados privados.

Este processamento é local e depende de um servidor supervisionado. Não é uma fila distribuída independente nem substitui um piloto em infraestrutura de produção.
