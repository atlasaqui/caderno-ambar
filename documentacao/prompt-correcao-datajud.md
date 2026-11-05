# Prompt de diagnóstico e correção da consulta real

Analise e corrija o fluxo DataJud do Caderno Âmbar existente neste repositório. A demonstração fictícia funciona, uma consulta externa isolada retornou HTTP 200, mas o caminho autenticado do aplicativo recebeu HTTP 429 e falha de transporte. Descubra as diferenças com evidências antes de atribuir a causa à fonte, chave, rede ou interface.

## Auditoria e reprodução

1. Leia a estrutura atual: frontend, backend, testes, ferramentas e documentação. Preserve banco, contas, versões e modificações locais. Não faça commit, push ou publicação.
2. Trace o percurso da ação na tela até a resposta: fetch, rota, sessão, e-mail confirmado, escritório, caso, reserva, fonte habilitada, transporte, validação, normalização, comparação, persistência e renderização.
3. Compare a requisição efetivamente preparada pelo transporte com a chamada isolada: endereço, método, corpo, tipo do número CNJ, ordenação, paginação, campos solicitados, autenticação e proxy. Confirme igualdade ou registre a diferença. Não exponha chave, cookies, senha ou token.
4. Consulte somente documentação primária do CNJ e das bibliotecas. Reproduza com um processo já identificado na API pública, sem investigar partes ou buscar documentos pessoais. Limite as tentativas, respeite Retry-After e evite consultas repetidas sem novo motivo diagnóstico.

## Correção

Corrija os defeitos locais demonstrados. Verifique chave/configuração, contrato da API, erros 401/403/404/429/5xx, timeout, paginação e resultado incompleto. A confirmação de fonte habilitada no health check não equivale a conectividade comprovada.

Separe falha local e falha externa na mensagem e no diagnóstico. Preserve a última referência válida e todo o histórico. Nunca substitua a resposta real por dados fictícios, importe um resultado de teste como se viesse da rota real ou marque um teste externo como concluído apenas porque um mock passou.

Se alterar agendamento ou retentativas, garanta que consulta manual e automática respeitem o intervalo e o limite do fornecedor. Não mantenha transação de banco aberta durante rede. Evite travar a interface e não efetue várias tentativas simultâneas para o mesmo processo.

## Validação e entrega

Acrescente regressões significativas para a causa encontrada e execute a suíte apropriada. Quando possível, conclua uma chamada HTTP autenticada real do aplicativo e confirme snapshot, versão, histórico, autoria da consulta e persistência após novo login. Confirme também que o cartão do frontend consegue interpretar o formato recebido.

Se houver bloqueio externo, encerre as chamadas depois de tentativas limitadas e documente exatamente a etapa pendente; não declare sucesso do fluxo completo.

Entregue o diagnóstico com fatos observados, hipóteses descartadas, causa comprovada quando encontrada, arquivos alterados, testes executados, resultado da consulta real e instruções de reprodução. Atualize a documentação de estudo afetada pelas alterações.
