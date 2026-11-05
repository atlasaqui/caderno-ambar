# Caderno Âmbar — guia da versão de equipes

> A evolução de providências e filas está em [guia-de-providencias.md](guia-de-providencias.md). Ela acrescenta Minha rotina, comentários, revisão da execução e diagnóstico administrativo.

Implementação local de 03/11/2026, branch `feat/caderno-equipes`. Este guia substitui as instruções de execução da primeira versão; `primeiro-guia-de-estudo.md` continua útil para estudar o laboratório original.

## Abrir e apresentar

Abra esta pasta no VS Code e execute `INICIAR.cmd`. O script cria `.venv` se necessário, instala as dependências e inicia FastAPI/Uvicorn. Endereço: **http://127.0.0.1:8093/acompanhamento.html**. A porta 8092 é a versão antiga e não atende ao contrato atualizado da interface.

Para desenvolvimento pelo terminal:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe backend\aplicacao.py
```

Entre com uma conta existente ou crie uma conta. Cada conta recebe um escritório pessoal. Os casos antigos permanecem no banco `output/ambar.sqlite3` e são associados ao escritório do proprietário. O processo é aditivo e repetível. Faça backup antes de atualizar um banco que contenha dados importantes.

Você não precisa de um processo real para apresentar:

1. Clique em **Carregar demonstração**.
2. Clique em **Consultar fonte**. O sistema grava a primeira referência fictícia.
3. Clique em **Simular nova movimentação** e consulte outra vez.
4. Abra **Linha do tempo** e observe o movimento novo.
5. Clique em **Conferir esta versão** e veja o registro associado à versão.
6. Saia e entre novamente: referências, versões e conferências permanecem.

Nenhuma dessas ações consulta um tribunal. A identificação de demonstração aparece na interface e na fonte. Ações de demonstração são bloqueadas pela API em produção.

## Arquitetura e responsabilidade dos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `backend/aplicacao.py` | Aplicação FastAPI, rotas, middleware, sessão, segurança HTTP e ciclo do agendador |
| `backend/equipes.py` | Migração, escritórios, membros, casos, versões, conferências, importação, tarefas e notificações |
| `backend/fontes.py` | Contrato de fonte, validação CNJ, normalização, comparação e fonte fictícia |
| `backend/acompanhamento.py` | Persistência básica, senha/sessão e transporte DataJud reaproveitados |
| `backend/correio.py` | Caixa local e adaptador SMTP com TLS |
| `backend/backup.py` | Cópia consistente SQLite, verificação e restauração para novo caminho |
| `backend/consulta.py` | Requests e Beautiful Soup para fonte HTML do laboratório original |
| `backend/servidor.py` | Servidor legado local; não é a entrada recomendada da versão 2 |
| `backend/rpa_navegador.py` | Roteiro Playwright original, ainda referente ao laboratório antigo |
| `frontend/acompanhamento.html` | Estrutura dos formulários e áreas de trabalho |
| `frontend/acompanhamento.js` | Eventos, requisições, estado visual, filtros, paginação e linha do tempo |
| `frontend/acompanhamento.css` | Identidade, foco, responsividade e componentes da nova tela |
| `.env.example` | Referência das variáveis; não é carregado automaticamente |
| `Dockerfile` | Receita de execução Linux; requer volume persistente e proxy HTTPS |

Uma ação percorre interface → API → autenticação → autorização no escritório → serviço → banco/fonte → resposta → atualização da interface. A integração externa não pode escolher uma URL recebida do visitante: os tribunais suportados são explícitos.

## Entenda o fluxo de consulta

`Equipes.consultar` começa uma transação e verifica acesso, arquivamento e reserva da tarefa. O campo `lease` impede duas requisições de consultarem o mesmo acompanhamento simultaneamente. A reserva expira após dez minutos para permitir recuperação depois de uma queda.

A fonte pode implementar o protocolo `Fonte.buscar(tribunal, numero)`. A fonte demonstrativa retorna JSON controlado. `DataJudValidado` valida CNJ, chama o transporte HTTP e valida os registros. O transporte usa páginas de dez resultados, campos selecionados, ordenação por @timestamp e cursor search_after. Valida totais e recusa resposta parcial, cursor repetido ou limite superior a 1.000 registros. A fonte pode mudar entre páginas: não há snapshot transacional garantido. fontes_estado compartilha espera e reserva entre consultas reais. O ensaio de 04/11 recebeu 35 movimentos pelo fluxo autenticado; paginação contra vários graus reais ainda precisa de piloto.

`normalizar` rejeita formato inválido e remove movimentos exatamente repetidos. `diferencas` compara movimentos considerando o grau. Retorna primeiro registro, nenhuma diferença, novos movimentos, correções/remoções ou alteração cadastral. O sistema descreve uma correção possível sem decidir seu significado jurídico.

Na gravação final, outra transação relê a referência e insere a versão. Consultas idênticas reutilizam a versão atual. Uma transição que retorna a conteúdo antigo recebe uma nova versão, evitando reutilizar uma conferência histórica como se a pessoa tivesse lido a mudança recente.

O histórico de consultas registra também verificações sem novidade e erros. Erros preservam a última referência válida. O agendamento usa a mesma operação de consulta manual.

## Banco e relacionamentos

O banco continua SQLite nesta entrega. É adequado à demonstração e a uma instância pequena com volume persistente; vários servidores e maior concorrência exigem avaliar PostgreSQL e migrações próprias. A troca para PostgreSQL não foi implementada nem testada.

| Tabela | Função |
|---|---|
| usuarios / sessoes | Conta, hash de senha e hash do token de sessão |
| organizacoes / membros | Escritórios e acesso admin/membro |
| convites / recuperacoes | Hashes dos tokens com expiração |
| casos | Processo, responsável, organização, periodicidade e referência atual |
| consultas | Tentativas, resultado, antes/depois e falhas |
| versoes | Conteúdo normalizado e diferença de cada transição |
| conferencias | Versão lida, pessoa, data e observação |
| tarefas | Próxima execução, reserva, tentativas e erro |
| notificacoes / emails / preferencias | Alertas internos, fila de e-mails e adesão por usuário |
| auditoria | Ações por escritório e usuário |
| migracoes / limites | Evolução do schema e contadores de proteção HTTP |

A migração usa criação de tabelas, adição das colunas ausentes e registro da versão aplicada. Ela não elimina dados. A estrutura antiga de casos ainda contém uma restrição única por usuário/número/tribunal; a aplicação também verifica duplicação por escritório. A evolução para múltiplos escritórios criados pelo mesmo usuário deve revisar essa restrição com migração de reconstrução, preservando as referências.

## Segurança e equipe

Senhas usam scrypt e salt aleatório. Tokens são aleatórios e só seu hash é persistido. Cookie de sessão: HttpOnly, SameSite Strict e Secure quando `AMBAR_ENV=production`. Alteração de senha revoga sessões. O token de recuperação dura 30 minutos e só pode ser usado uma vez.

Há limite de autenticação por origem de rede e verificação de Origin/Sec-Fetch-Site. Host é validado. O proxy não é considerado confiável automaticamente. Convites duram 24 horas e ficam vinculados ao e-mail cadastrado. Quem possui o token e controla a conta com esse e-mail pode aceitá-lo: confirmação de propriedade do e-mail por verificação separada ainda é uma melhoria necessária antes de adesão pública irrestrita.

Admin pode convidar/revogar membros e alterar o nome do escritório pela API. Membros podem trabalhar nos processos do escritório. Não foi criada uma permissão granular por processo. Contas antigas recebem papel admin em seu espaço pessoal. Histórico e detalhes verificam associação ao escritório.

## Como usar as APIs

As rotas da versão 2 continuam sob `/api`. Operações POST recebem JSON e as protegidas exigem o cookie de sessão. `GET /api/docs` está disponível em desenvolvimento, mas o roteador genérico não descreve sozinho todos os campos abaixo; este guia é o contrato detalhado da aplicação atual.

| Rota | Método / campos |
|---|---|
| conta/cadastro e conta/login | POST: email, senha |
| conta/sair | POST: objeto vazio |
| conta/recuperar | POST: email; resposta não revela token |
| conta/redefinir | POST: token, senha |
| contexto | GET: escritórios acessíveis |
| organizacao/nome | POST: org, nome; admin |
| membros | GET: org na query |
| convites/criar | POST: org, email; retorna token para entrega privada |
| convites/aceitar | POST: token |
| membros/revogar | POST: org, usuario; admin |
| casos | GET: org; POST: org, numero, tribunal, apelido |
| casos/ID/alterar | POST: apelido, etiquetas, observacoes, responsavel, arquivado, intervalo |
| casos/ID/consultar | POST: objeto vazio |
| casos/ID/revisar | POST: versao_id, observacao opcional |
| casos/ID/historico e casos/ID/detalhe | GET: consultas / versões e conferências |
| demonstracao | POST: org |
| casos/ID/avancar-demo | POST: objeto vazio; somente demonstração |
| importar | POST: org, csv, confirmar |
| exportar | GET: org; resposta CSV, com proteção contra fórmulas em células |
| notificacoes e auditoria | GET: org; auditoria requer admin |
| preferencias | POST: email booleano |
| saude | GET: verifica banco e modo da aplicação |

Exemplo CSV: primeira linha `numero;tribunal;apelido`. A prévia não grava; confirmação importa linhas válidas e relata rejeitadas. Limites: 100 KB e 500 linhas. A importação é por linha, não uma transação atômica de todo o arquivo. A lista atual limita a 1.000 casos por escritório e faz paginação visual de 20; paginação de banco é trabalho posterior para volumes maiores.

## Agendamento, notificações e e-mail

Ative periodicidade no acompanhamento. Zero mantém consulta manual. O mínimo permitido pela API é 15 minutos; a interface oferece uma hora ou um dia. O agendador roda enquanto o servidor está aberto, verifica até cinco tarefas por ciclo e repete a cada 15 segundos. A fila reside no banco e sobrevive a reinícios. Falhas têm espera progressiva e cinco tentativas automáticas; uma consulta manual pode recuperar uma tarefa após corrigir sua causa.

Alertas internos são únicos por caso/versão. Preferência de e-mail é opt-in. Em desenvolvimento, as mensagens ficam em `output/email-local`. A interface permite ativar/desativar a preferência. Nenhum e-mail externo é enviado nesse modo.

Em produção, configure SMTP e remetente pelas variáveis de `.env.example`. O adaptador exige STARTTLS. `aceito_pelo_smtp` significa aceite pelo servidor, não entrega final; confirmação de entrega exige eventos do provedor e não está implementada. Após falha, a fila faz novas tentativas limitadas. A entrega externa pode se repetir se o processo cair entre o aceite SMTP e a gravação no banco; exatamente uma entrega externa exige idempotência suportada pelo provedor. Não alegue garantia absoluta de ausência de duplicação.

## Configurar DataJud

O modo de demonstração é suficiente para testar o produto. Consultas reais ficam desativadas até configuração explícita:

```powershell
$env:AMBAR_DATAJUD_HABILITADO = '1'
$env:DATAJUD_API_KEY = 'CHAVE_PUBLICA_VIGENTE'
.venv\Scripts\python.exe backend\aplicacao.py
```

Avalie finalidade e condições com a organização. A norma vigente consultada contém restrições de exploração comercial e não garante a atualidade das remessas. A implementação não autoriza uso empresarial por si só. Também não integra intimações oficiais do DJEN/Domicílio, peticionamento, processos sigilosos nem conteúdo integral dos autos.

Referências: https://atos.cnj.jus.br/atos/detalhar/3453 ; https://datajud-wiki.cnj.jus.br/api-publica/acesso/ ; https://datajud-wiki.cnj.jus.br/api-publica/exemplos/ ; https://www.cnj.jus.br/programas-e-acoes/processo-judicial-eletronico-pje/comunicacoes-processuais/ . Consulte as regras vigentes antes do piloto.

## Backup, restauração e implantação

```powershell
.venv\Scripts\python.exe backend\backup.py output\ambar.sqlite3 output\backup-manual.sqlite3
$env:AMBAR_DB = 'output\backup-manual.sqlite3'
.venv\Scripts\python.exe backend\aplicacao.py
```

O utilitário verifica integridade e recusa sobrescrita. Para backup diário enquanto a aplicação estiver aberta, configure `AMBAR_BACKUP_AUTOMATICO=1` e `AMBAR_BACKUP_DIR` em volume apropriado. Não há cópia automática para outra máquina, criptografia do arquivo ou exclusão de backups antigos. Defina isso conforme política do escritório.

O Dockerfile é uma receita preparada, ainda não validada com build Docker neste ambiente. Execute com volume persistente em `/data`, `AMBAR_ORIGIN` igual à origem HTTPS pública e proxy TLS configurado. Não publique o servidor legado. A Vercel atual serve somente `frontend`; essa configuração não hospeda a API nova. Não foi feito push, merge ou deploy.

Antes de produção: validar restauração no ambiente destino, SMTP real, política de retenção/exclusão, responsáveis operacionais, monitoramento e alertas, backup externo, proteção de conta/e-mail, revisão de segurança e adequação da fonte. Arquivar um caso não apaga dados; exclusão e retenção automatizada não foram implementadas.

## Estudar pelo código

**Sessão 1: interface e HTTP.** Abra `acompanhamento.js`, localize `api`, `run`, `load` e `render`. No DevTools/Network, acompanhe cadastro, contexto e demonstração. Explique por que a interface não lê o banco diretamente. Refaça uma chamada autenticada pelo seu próprio script Requests.

**Sessão 2: POO e fontes.** Leia `Fonte`, `Demonstracao` e `DataJudValidado`. `Protocol` descreve o contrato esperado; a implementação concreta é injetada na consulta. Compare com uma interface Java. Reescreva `diferencas` para um exemplo com duas listas e teste inserção, remoção e igualdade antes de voltar ao caso real.

**Sessão 3: persistência e concorrência.** Leia `Equipes.__init__`, `consultar` e `revisar`. Veja `BEGIN IMMEDIATE` e a reserva `lease`. Explique a diferença entre uma transação curta de reserva e a chamada HTTP externa. Rode o teste concorrente e explique por que uma conferência antiga não quita a versão nova.

**Sessão 4: segurança e equipe.** Use duas contas, crie convite e selecione o escritório compartilhado. Revogue o acesso e tente novamente. Leia cada verificação em `org`/`caso`. Explique autenticação versus autorização, hash de senha versus hash de token, token de uso único e expiração.

**Sessão 5: tarefas e evidências.** Ative a periodicidade no exemplo, estude `tick`, falhas e retentativas. Execute backup/restauração. Leia os testes HTTP completos. Demonstre o erro de fonte preservando dados e explique o que foi comprovado por mocks e o que depende do provedor real.

## Roteiro de apresentação de cinco minutos

1. Problema: consultas repetidas e dificuldade de distribuir conferências.
2. Demonstração: consulte a referência fictícia e simule a novidade.
3. Histórico: mostre o movimento novo e a conferência da versão.
4. Arquitetura: interface → API → autorização → fonte → normalização → versão → fila da equipe.
5. Decisões e limites: SQLite local, API FastAPI, tarefas persistentes, credenciais externas e validação com escritório antes de uso profissional.

Use uma descrição honesta: “Evoluí o projeto com desenvolvimento assistido, revisei os fluxos e estou reproduzindo os componentes para consolidar meu domínio.” Apresente como conhecimento seu aquilo que conseguir explicar, modificar e testar.
