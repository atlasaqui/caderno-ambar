# Minha rotina — evolução do Caderno Âmbar

## Usar a versão local

Execute `INICIAR.cmd` e abra http://127.0.0.1:8093/acompanhamento.html . Entre e escolha o escritório. Na aba **Processos**, carregue a demonstração, consulte a referência e simule uma novidade.

Em um processo, clique em **Criar providência**. Na linha do tempo, use **Criar providência desta versão** para manter o vínculo com o conteúdo que motivou a decisão. Preencha título, orientações, responsável, revisor, data interna e prioridade. A data é de organização do trabalho; não é um prazo processual calculado.

Na aba **Minha rotina**, escolha: minhas providências, pendências da equipe, datas internas vencidas, minha revisão ou concluídas. Busque por título, nome do caso ou número. A listagem usa paginação no banco, com 25 resultados por página.

O fluxo é: **A fazer → Em andamento → Aguardando revisão → Concluída**. Também existe **Aguardando informação**. Enviar para revisão exige evidência ou descrição do resultado; a conclusão depende do revisor designado ou administrador. Reabrir uma providência concluída exige um comentário.

Conferir uma versão apenas registra leitura. Criar uma providência organiza a decisão. Concluir uma providência registra execução revisada. São estados separados. Criar uma providência não marca a versão como conferida automaticamente.

## Equipe e segurança

Membros do escritório podem visualizar a rotina da equipe. Só responsável, revisor ou administrador altera uma providência. Uma conta de outro escritório não pode acessar histórico ou alterações. Mudanças usam um número de revisão: se outra pessoa atualizou a providência, a API responde 409 e pede atualização da lista antes de prosseguir.

Ao revogar um membro, processos e responsabilidades são transferidos ao administrador que realizou a revogação, com histórico. Mensagens ainda pendentes daquele escritório são canceladas. Antes de cada envio, a fila revalida associação ao escritório e preferência de e-mail. Um envio já iniciado não pode ser desfeito pela revogação posterior.

Responsável e revisor podem ser a mesma pessoa para viabilizar uso individual; dupla checagem obrigatória por pessoas distintas ainda depende de regra específica do escritório.

## Saúde das filas

Administradores encontram **Saúde das consultas e notificações**, com próxima tentativa, reserva de execução, falhas e número de tentativas. Após cinco falhas, aparece necessidade de intervenção; o administrador pode solicitar reprocessamento. Reprocessamento não garante disponibilidade da fonte. Mensagens aceitas ou canceladas não são reenviadas por esse botão.

Consulta, e-mail e backup têm ciclos independentes. Consultas executam até três tarefas simultaneamente, preservando a reserva individual no banco. E-mails são reservados em transações curtas, enviados fora da transação e finalizados em outra transação. A recuperação de senha também envia fora da transação de gravação do token.

A fila de e-mail recupera reservas expiradas. O aceite SMTP não comprova entrega. Se o processo cair após o provedor aceitar a mensagem e antes de registrar o resultado, pode haver reenvio; a garantia de idempotência externa continua dependendo de um provedor que a suporte.

## Código para estudar

| Arquivo | O que ler |
|---|---|
| `backend/rotina.py` | Migração, regras das providências, permissão, revisão otimista, filas, diagnóstico e reprocessamento |
| `backend/aplicacao.py` | Rotas de rotina e três ciclos independentes de processamento |
| `frontend/rotina.js` | Criação a partir do processo/versão, filtros, edição, comentários e diagnóstico |
| `frontend/acompanhamento.js` | Pontos que abrem uma providência e atualizam o contexto do escritório |
| `backend/test_rotina.py` | Execução/revisão, isolamento, concorrência, e-mail sem bloqueio do banco e revogação |
| `backend/test_api_v2.py` | Fluxo HTTP de criação e atualização com cookie de sessão |
| `tests/ui.test.cjs` | Fluxo em DOM simulado do processo até a rotina |

`Escritorio` herda a persistência existente e acrescenta a rotina. A tabela `providencias` guarda estado atual, responsáveis, evidência e revisão. `eventos_providencia` guarda o histórico da criação, comentários, transições e reatribuições. A migração é aditiva e registra a versão 2; os dados anteriores são preservados.

`alterar_providencia` começa uma transação, verifica escritório e papel, compara a revisão apresentada e valida a transição. Só depois grava o estado e seu evento. Duas pessoas com a mesma revisão não conseguem gravar silenciosamente por cima uma da outra.

## Rotas adicionadas

| Rota | Contrato |
|---|---|
| GET /api/me?org=ID | Conta atual no escritório |
| GET /api/rotina | org, filtro, pagina e busca; retorna itens, total e resumo |
| POST /api/providencias | caso, versao opcional, titulo, descricao, responsavel, revisor, data_interna, prioridade |
| POST /api/providencias/ID/alterar | revisao, estado, comentario opcional, evidencia |
| GET /api/providencias/ID/historico | Histórico autorizado |
| GET /api/operacao?org=ID | Diagnóstico administrativo de consultas e e-mails |
| POST /api/operacao/reprocessar | org, tipo (`consulta`/`email`), id |

Estados da API: `a_fazer`, `em_andamento`, `aguardando`, `em_revisao`, `concluida`. Prioridades: `baixa`, `normal`, `alta`.

## Outras melhorias

O formulário de importação aceita selecionar um arquivo CSV local de até 100 KB, mantendo prévia e confirmação. A verificação de duplicação da prévia consulta todos os números existentes no escritório. A exportação deixou de usar a listagem visual limitada e consulta a carteira completa, sem carregar snapshots de movimentos.

## Limites que permanecem

A tela de processos ainda usa a listagem legada limitada a 1.000 registros; a paginação de banco foi implementada para providências, não para toda a carteira. A configuração de fonte autorizada, validação externa do DataJud, SMTP real, infraestrutura, verificação de e-mail/MFA e política de retenção continuam necessárias antes de uso empresarial. A área administrativa mostra até 100 itens recentes por fila.

Não foram acrescentados financeiro, gestão documental integral, integração com intimações oficiais, cálculo de prazo judicial ou novos fornecedores de dados. Os testes de interface usam DOM simulado: a inspeção visual em navegador continua impedida pela configuração de acesso local.

## Exercícios e apresentação

1. Crie uma providência de uma versão fictícia e explique a diferença entre ler e executar.
2. Use dois membros, atribuindo um como executor e outro como revisor. Tente concluir como executor e explique a recusa.
3. Abra a mesma providência em duas sessões; altere uma e tente salvar a revisão antiga na outra.
4. Leia o teste que grava no banco dentro do mock de envio: explique por que ele detectaria uma transação mantida aberta durante a rede.
5. Revogue um membro e confira reatribuição e histórico.

Na entrevista: “Acrescentei um fluxo de providências para transformar uma mudança recebida em trabalho atribuído e revisado. Separei leitura da versão de conclusão da ação. Corrigi o processamento de e-mail para não manter o banco bloqueado durante a rede e acrescentei revalidação de acesso antes dos envios. A implementação é assistida e eu uso testes e reprodução dos fluxos para consolidar meu entendimento.”
