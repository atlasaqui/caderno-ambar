# Causa confirmada da recusa DataJud

Investigação de 04/11/2026, horário de Recife. A conclusão abaixo substitui a hipótese genérica de limite para a resposta especificamente capturada às 14h00. Não explica retroativamente todos os timeouts e recusas anteriores sem os respectivos corpos de resposta.

## Resultado da comparação controlada

O ciclo automático local foi pausado durante o ensaio, mantendo o servidor e a sessão disponíveis. Foram feitos dois pedidos ao mesmo processo público TJPE, com a mesma chave pública vigente, mesmo endpoint, TLS verificado e conexão direta. A chave foi lida da documentação oficial e não foi incluída no relatório. Não houve consultas paralelas ao CNJ pelo aplicativo durante a comparação.

| Pedido | Horário local | Resultado |
| --- | --- | --- |
| Corpo mínimo do exemplo oficial, com `query.match.numeroProcesso` | 14:00:17 | HTTP 429 em 0,29 segundo, com sobrecarga explícita da fila de buscas do Elasticsearch |
| Corpo atual do aplicativo, com projeção, total exato e ordenação | 14:01:47 | HTTP 200 em 29,5 segundos, um registro e 38 movimentos; `timed_out=false`, nenhum shard com falha |

Foram aguardados 90 segundos entre os pedidos. A resposta de recusa não trouxe cabeçalho Retry-After. Os 90 segundos foram uma escolha de espera do cliente, não promessa de recuperação do CNJ.

## A causa observada

A resposta oficial apresentou `search_phase_execution_exception` no nível principal, com `es_rejected_execution_exception` nas causas internas e nos shards. A razão descreveu:

- capacidade da fila de buscas: **1.000 tarefas**;
- tarefas na fila: **1.005**;
- threads de busca: **10**, com **10 ativas**.

Isso comprova rejeição por saturação do mecanismo de buscas do fornecedor naquele pedido. Não é uma mensagem de número CNJ inválido nem de credencial recusada. A chamada posterior bem-sucedida, com a mesma chave, também comprova que o contrato usado pelo aplicativo consegue receber dados reais. A diferença temporal impede atribuir essa diferença de resultado exclusivamente ao formato do corpo.

Esse ensaio não garante disponibilidade contínua, não mede uma taxa de sucesso de produção e não determina a causa de todos os timeouts anteriores. Não foram consultados endpoints administrativos do Elasticsearch nem tentado alterar a infraestrutura do CNJ.

## Defeito local encontrado e corrigido

`DataJud.buscar` verificava apenas `error.type`. Quando a sobrecarga vinha encapsulada por `search_phase_execution_exception`, o app classificava a resposta como limite genérico. A nova função `DataJud.tipos_erro` percorre, com limites de profundidade e quantidade, as estruturas `root_cause`, `caused_by`, `failed_shards` e `reason`.

O erro é agora identificado como `fonte_sobrecarregada`, com HTTP 503 na API local e mensagem própria. A pausa inicial é de pelo menos cinco minutos, respeitando um Retry-After maior quando presente e a espera crescente já persistida. Não se expõem corpo bruto, detalhes internos do servidor ou chave na interface. O cartão informa que o serviço de buscas do CNJ está sobrecarregado, mantendo os últimos dados disponíveis.

As regressões reproduzem as três formas de encapsulamento da resposta real. Passaram **56 testes Python e 16 de interface**. As chamadas externas da suíte são simuladas; os dois pedidos descritos acima são a evidência externa separada.

## Situação operacional

O servidor local foi reiniciado com a correção e o processamento automático foi restaurado. A fila existente e seus prazos foram preservados; não foram zerados para forçar novas consultas. A resposta HTTP 200 do diagnóstico não foi importada como uma versão do aplicativo: uma atualização da carteira continua exigindo sucesso pelo fluxo normal.

É possível corrigir identificação, espera, preservação, fila e comunicação no cliente. Aumentar a capacidade ou resolver a saturação do cluster do CNJ depende do operador do serviço. A indisponibilidade persistente deve ser levada ao suporte com horários, endpoint, códigos e resumo da causa. O texto abaixo está preparado para revisão; não foi enviado.

## Texto técnico para suporte

Assunto: API pública DataJud / TJPE - rejeição da fila de buscas em 04/11/2026

Em 04/11/2026 às 14:00:17, horário de Recife (17:00:17 UTC), uma consulta POST ao endpoint api_publica_tjpe/_search, utilizando o corpo mínimo documentado para pesquisa por numeroProcesso, retornou HTTP 429. O corpo indicou search_phase_execution_exception com causa es_rejected_execution_exception, capacidade de fila 1000, tarefas em fila 1005, pool de 10 threads e 10 ativas. Não houve Retry-After. Após intervalo de 90 segundos, uma consulta ao mesmo processo e endpoint retornou HTTP 200 em 29,5 segundos, com timed_out=false e sem falhas de shard. Solicitamos orientação sobre a saturação e frequência de consulta adequada. Não incluímos chave de API ou dados privados nesta comunicação.

## Evidências e referências

- `output/teste-datajud/comparacao-controlada.json`: registro local das duas requisições, sem chave e sem conteúdo processual da resposta bem-sucedida. Não contém prova de persistência na carteira.
- Exemplo oficial: https://datajud-wiki.cnj.jus.br/api-publica/exemplos/exemplo1/
- Explicação do fornecedor do mecanismo de busca: https://www.elastic.co/docs/troubleshoot/elasticsearch/rejected-requests
- Orientação oficial sobre suporte do CNJ: https://www.cnj.jus.br/sistemas/datajud/suporte/ . A página descreve o portal de chamados e se dirige aos tribunais; é necessário verificar a possibilidade de acesso pelo solicitante externo. Nenhum chamado foi aberto.

Não houve envio de mensagem, commit, push ou publicação nesta investigação.
