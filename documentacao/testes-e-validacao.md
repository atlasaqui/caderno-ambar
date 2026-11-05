# Relatório de validação — versão de equipes

## Revalidação para publicação — 05/11/2026

Na versão preparada para o GitHub, passaram **56 testes Python e 16 testes de interface**. A suíte usa bancos temporários e respostas externas simuladas; não executa consultas de produção no CNJ. O laboratório também foi percorrido no navegador para capturar apresentação, consulta fictícia concluída e comparação antes/depois. As imagens públicas ficam em `documentacao/imagens/`, sem credenciais ou processos reais.

## Investigação posterior: causa interna da recusa

Em 04/11, às 14h00, o corpo mínimo oficial retornou 429 com `es_rejected_execution_exception` encadeado em `search_phase_execution_exception`: fila de capacidade 1.000 com 1.005 tarefas e dez threads ativas. Às 14h01, após 90 segundos, o corpo usado pelo app retornou 200 com 38 movimentos em 29,5 segundos. A comparação não mede disponibilidade contínua nem foi importada como versão na carteira. O parser foi corrigido para ler as causas internas e aplicar pausa mínima de cinco minutos à sobrecarga. Passaram **56 testes Python e 16 de interface**. Veja [causa-confirmada-datajud.md](causa-confirmada-datajud.md). As contagens das seções seguintes pertencem às revisões anteriores.

## Revisão mais recente: fila de atualização em 04/11

Passaram **55 testes Python e 15 testes JavaScript** após a inclusão da fila persistente. No navegador local, a solicitação retornou imediatamente, os dados anteriores continuaram disponíveis e uma recusa HTTP 429 foi registrada e reagendada pelo servidor. Não houve novo sucesso externo nessa tentativa. Veja [fila-atualizacoes-datajud.md](fila-atualizacoes-datajud.md) e [demonstracao-no-computador.md](demonstracao-no-computador.md). As seções abaixo preservam resultados de etapas anteriores.

## Teste de DataJud em 04 de novembro

Resultado atual: **50 testes Python e 14 testes JavaScript aprovados**. O fluxo HTTP autenticado real consultou o TJPE, recebeu 35 movimentos e persistiu uma versão com histórico e autoria, preservada após novo login. O frontend foi exercitado em DOM simulado com a API local real e mostrou os 35 movimentos e seis tentativas. A suíte usa fontes simuladas; o ensaio externo é separado. Não houve inspeção visual em navegador. Veja `diagnostico-e-correcao-datajud.md`. As seções seguintes registram etapas anteriores e suas contagens históricas.

## Organização de pastas em 04 de novembro

Os caminhos atuais são `backend`, `frontend`, `ferramentas` e `documentacao`. O lançador, os testes, a configuração Docker, a publicação estática e o gerador do manual foram ajustados. Nenhum dado do banco foi movido. Os testes de e-mail passaram a selecionar a mensagem correspondente ao cenário e a solicitação atual, evitando depender da ordem aleatória dos arquivos da caixa local.

## Revisão atual do piloto e manual

Em 03/11/2026, passaram **39 testes Python e 13 testes JavaScript em DOM simulado**. A suíte Python inclui chamadas HTTP locais autenticadas e SQLite temporário. Há cobertura de carteira com 1.005 registros, migração preservando vínculos, duplicação por escritório, confirmação de e-mail com expiração/uso único/conta correta, convites protegidos, exportação sem tokens e data interna opcional. A conclusão de providência não aceita remover a evidência simultaneamente.

A aplicação atual instancia `Piloto` e a interface utiliza `/api/carteira` para paginação no banco. As observações anteriores sobre limite de 1.000 itens descrevem a rota legada `/api/casos`, preservada para compatibilidade, não o caminho atual da interface. A restrição antiga de duplicação foi migrada com backup anterior e verificação de vínculos.

O servidor local foi reiniciado na porta 8093. Não houve publicação, commit ou push. E-mail externo, fonte real autorizada, domínio HTTPS, MFA, exclusão efetiva/retencão, backup externo e inspeção visual no navegador continuam pendentes. Registro de solicitação de dados não equivale a exclusão implementada. O estado consolidado está em `estado-atual-do-projeto.md`.

## Atualização: percurso e orientação interativa

Resultado desta revisão: **32 testes Python e 11 testes de interface em DOM simulado aprovados**. O início foi separado em apresentação, treino sem conta, acesso e aplicação. Os três cenários de treino foram testados. O guia da área de trabalho foi percorrido até a conclusão, incluindo pausa e retomada, com respostas simuladas.

As páginas `index.html`, `laboratorio.html`, `acesso.html` e `acompanhamento.html` foram verificadas por HTTP. O roteiro Playwright legado foi atualizado para a nova página de treino, mas não executado. O navegador local segue desativado nas configurações, portanto a inspeção visual e os testes reais de teclado/telas menores continuam pendentes. Veja [fluxo-das-telas.md](fluxo-das-telas.md).

## Atualização: Minha rotina e filas

Resultado atual: **31 testes Python e 5 testes de interface em DOM simulado aprovados**. Incluem fluxo HTTP de providências, permissão de revisão, estado desatualizado recusado, histórico, reatribuição após revogação, reprocessamento administrativo e gravação concorrente durante envio de e-mail. Os testes de interface cobrem criar uma providência a partir de um processo e acompanhar execução/revisão na nova aba.

O serviço atual é `Escritorio` em `backend/rotina.py`, usado por FastAPI. O módulo antigo `Equipes` permanece como base e referência; seus métodos legados de processamento não são os ciclos usados na aplicação atual. A versão em execução separa consultas, e-mail e backup; o envio real de mensagens não mantém uma transação aberta no banco.

Documentação e limites específicos: [guia-de-providencias.md](guia-de-providencias.md). A exportação consulta a carteira completa e a prévia de duplicados deixa de depender da lista visual de 1.000 registros. A própria tela de processos ainda precisa de paginação no banco. O navegador local segue indisponível para inspeção visual; a validação de DOM não substitui essa etapa.

## Implementado

FastAPI/Uvicorn; migração aditiva; escritórios e membros; convites com token; revogação; responsável, etiquetas e observações; validação CNJ; CSV de importação com prévia; exportação; demonstração persistente; histórico legível; comparação por movimento; versões e conferências; reserva concorrente; agendamento e retentativas; alertas internos; caixa local e SMTP configurável; recuperação de senha; rate limit; backup consistente e configuração Docker.

## Evidência automatizada

Resultado final desta execução: **25 testes aprovados**; sintaxe JavaScript verificada. O SMTP foi validado com mock, sem transmissão externa. A restauração foi comprovada reabrindo o banco copiado e comparando a referência persistida.

Execute `python -m unittest discover -s backend -v`. Os testes cobrem o laboratório antigo, persistência real em SQLite, migração preservando conta/caso, convites, isolamento/revogação, versão antiga conferida, notificações internas únicas, reserva concorrente, importação, tarefa agendada, restauração, caixa local e chamadas HTTP com cookie à aplicação FastAPI. Os testes SMTP usam mock; nenhum e-mail externo é enviado.

Verificação sintática do frontend: `node --check frontend/acompanhamento.js`.

## Limites de evidência

O uso do navegador local está desativado nas configurações deste ambiente. Não houve aprovação visual nem execução do fluxo novo em navegador automatizado. HTTP e sintaxe não substituem esse teste. O roteiro Playwright antigo continua sendo do laboratório original.

A revisão de 04/11 validou uma consulta pública real pelo fluxo completo. Paginação contra múltiplos graus e carteira autorizada de escritório continuam sem homologação. A demonstração fictícia não comprova essas integrações.

Docker, HTTPS público, SMTP real, backup fora da máquina e PostgreSQL não foram executados/validados. Nenhum push, merge ou deploy foi feito.

## Pendências para uso empresarial

Validar finalidade/termos e fonte autorizada; validar com uma carteira consentida; verificar e-mail de novas contas; completar contratos tipados/OpenAPI por rota; paginação no banco além de 1.000 casos; migração da restrição legada por usuário; estratégia para PostgreSQL/múltiplas instâncias quando necessária; política implementada de exclusão/retenção; eventos de entrega do provedor; observabilidade operacional; teste visual e acessibilidade em navegador; build e piloto na infraestrutura destino.

Há recuperação após expiração da reserva de tarefas. Requisições à fonte não são transações externas atômicas. A fila SMTP distingue aceite de entrega; uma queda após aceite pode produzir reenvio. Um agendador precisa permanecer em execução: fechar o servidor interrompe consultas até o próximo início.
