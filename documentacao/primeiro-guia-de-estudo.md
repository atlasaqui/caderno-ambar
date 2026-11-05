# Caderno Âmbar — código, prática e apresentação

> A versão de equipes está documentada em [guia-de-equipes.md](guia-de-equipes.md). Inicie `backend/aplicacao.py` e use a porta 8093. As instruções abaixo descrevem a versão inicial e o laboratório original.

Versão local de 03/11/2026. Leia com o VS Code aberto na pasta deste projeto.

## 1. O que foi construído

O problema é acompanhar mudanças sem repetir manualmente a leitura de uma fonte. O caderno guarda uma referência anterior, consulta novamente, normaliza a resposta, compara e registra o resultado. A conferência final continua com a pessoa.

Há dois percursos. `index.html` oferece o laboratório fictício original: Requests obtém HTML, Beautiful Soup extrai os campos e Python compara. `acompanhamento.html` oferece contas e persistência: o servidor consulta JSON da API Pública do DataJud. Nesta segunda parte, Beautiful Soup não é necessário para os processos, porque a API já devolve dados estruturados. Playwright é usado pelo roteiro de automação/teste do laboratório; não é necessário abrir um navegador para consumir a API.

## 2. Executar no Windows

Abra esta pasta no VS Code. Execute `INICIAR.cmd`, que cria um ambiente virtual quando necessário e instala as dependências. Depois visite http://127.0.0.1:8092/acompanhamento.html . O laboratório fica em http://127.0.0.1:8092/index.html . Mantenha o terminal aberto; Ctrl+C encerra o servidor.

O inicializador busca a chave **pública** vigente na documentação do CNJ e a mantém somente no processo. Se a documentação estiver indisponível ou mudar de formato, o sistema informa a necessidade de configuração. Alternativa no PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DATAJUD_API_KEY = 'CHAVE_PUBLICA_VIGENTE_DA_WIKI_CNJ'
.venv\Scripts\python.exe backend\servidor.py
```

O arquivo de banco padrão é `output/ambar.sqlite3`. Defina `AMBAR_DB` antes de iniciar se desejar outro caminho. Faça backup com o servidor encerrado. `output/` não é versionado. Cadastre uma conta local, adicione um número público que você tenha autorização para acompanhar e selecione seu tribunal: TJPE, TRT6 ou TRF5. Não invente um número esperando receber resultados reais. A ausência de resultados não comprova inexistência de um processo.

## 3. Mapa dos arquivos

| Arquivo | Responsabilidade | O que estudar |
|---|---|---|
| `frontend/index.html` | Telas e tutorial originais | HTML semântico, botões, diálogos e IDs |
| `frontend/amber.css` | Identidade e layout originais | Cascata, seletores, responsividade |
| `frontend/amber.js` | Estado do laboratório, eventos, comparação visual, CSV | Arrays, Set, promises, fetch, renderização |
| `frontend/runtime-config.js` | Modo estático; servidor substitui a resposta em modo Python | Configuração por ambiente |
| `frontend/portal.html` | HTML fictício com campos conhecidos | Contrato da fonte e seletores |
| `frontend/acompanhamento.html` | Conta, formulário de processo e lista persistente | Forms, labels, validação e acessibilidade |
| `frontend/acompanhamento.css` | Layout do caderno persistente | Componentes visuais e leitura de conteúdo longo |
| `frontend/acompanhamento.js` | Ponte entre interface e API própria | async/await, erros HTTP e DOM seguro |
| `backend/servidor.py` | Servidor HTTP, roteamento, cookies e validação de requisições | Herança, métodos HTTP e respostas JSON |
| `backend/acompanhamento.py` | Classes Caderno, DataJud e FalhaAPI | POO, SQL, transações, integração externa |
| `backend/consulta.py` | Requests e Beautiful Soup do laboratório | Parsing, timeout, hash e tratamento de erros |
| `backend/rpa_navegador.py` | Automação original do navegador | Locators, ações, evidências e trace |
| `backend/iniciar_datajud.py` | Configura chave pública e inicia servidor | Ambiente, regex, dependência externa |
| `backend/test_consulta.py` | Testes do laboratório original | HTTP local e casos de falha |
| `backend/test_acompanhamento.py` | Testes do caderno persistente | Sessão, autorização, SQLite e mocks |
| `requirements.txt` | Versões das dependências Python | Reprodutibilidade do ambiente |
| `vercel.json` | Publicação estática existente | Limite entre site estático e backend |

## 4. Siga uma ação do início ao fim

Ao adicionar um processo, o formulário gera `FormData`. O JavaScript transforma os campos em objeto, envia JSON para `POST /api/casos` e aguarda. O navegador inclui automaticamente o cookie da mesma origem. `Handler` lê o corpo e identifica o usuário por `Caderno.usuario`. `Caderno.adicionar` valida tamanho do número, tribunal permitido e apelido; executa SQL com parâmetros; a restrição UNIQUE rejeita duplicação por conta. A resposta retorna o ID. A interface chama `load()` para buscar a lista novamente.

Ao consultar, `POST /api/casos/{id}/consultar` primeiro verifica se o caso pertence ao usuário. `DataJud.buscar` monta uma URL de tribunal permitido, envia o número CNJ com Requests e cabeçalho Authorization. Há limites de tempo e nenhum redirecionamento automático. O adaptador mantém somente registros cujo número é exatamente o solicitado, organiza os movimentos e preserva os graus retornados.

O resultado vira JSON com chaves ordenadas. A primeira consulta estabelece a referência. Nas seguintes, JSON igual significa “sem mudança”; JSON diferente significa “mudança encontrada”. As consultas registram o conteúdo anterior e o novo. Em falha, o snapshot anterior permanece e o histórico recebe o erro. Há intervalo de 30 segundos por caso. Campos voláteis como horário de consulta não entram na comparação, para evitar novidades falsas a cada execução.

Marcar como conferido atualiza apenas o registro local; não altera um processo no tribunal. A nova movimentação remove a conferência anterior. O histórico mostra datas completas, estado, antes e depois. A listagem resume o último movimento de cada grau retornado.

## 5. POO e banco, em termos que você já conhece de Java

`Caderno` é uma classe: reúne operações de usuários, sessões, processos e consultas. `self` aponta para a instância, equivalente ao papel de `this` em Java. O construtor `__init__` recebe o caminho do banco e cria tabelas quando ausentes. `DataJud` concentra o conhecimento sobre o serviço externo. `FalhaAPI` carrega mensagem e status HTTP para o servidor responder corretamente.

`with self.conexao()` abre uma conexão, confirma a transação em sucesso, desfaz em exceção e fecha a conexão. SQL usa `?` e uma tupla de parâmetros: o valor não é concatenado como comando SQL. `BEGIN IMMEDIATE` protege a atualização de referência contra gravações concorrentes durante a comparação final.

| Tabela | Dados | Relação |
|---|---|---|
| usuarios | ID, e-mail, salt e hash de senha | Uma conta tem vários casos |
| sessoes | Hash do token, usuário e expiração | Sessão válida por 8 horas |
| casos | Número, tribunal, apelido, snapshot e conferência | Cada caso pertence a um usuário |
| consultas | Data, estado, antes, depois ou erro | Cada consulta pertence a um caso |

Senhas passam por scrypt com salt aleatório; não são guardadas em texto puro. O token de sessão é aleatório; só seu hash fica no banco. O cookie é HttpOnly e SameSite=Strict. O servidor verifica a propriedade de cada caso. O servidor local escuta somente 127.0.0.1 e usa HTTP local; publicação exige HTTPS e cookie Secure, além das medidas listadas adiante.

## 6. Contrato da API própria

| Método e rota | Entrada | Resultado |
|---|---|---|
| POST /api/conta/cadastro | email, senha | Cria conta e cookie |
| POST /api/conta/login | email, senha | Inicia sessão |
| POST /api/conta/sair | objeto vazio | Revoga sessão |
| GET /api/casos | cookie | Lista da conta |
| POST /api/casos | numero, tribunal, apelido | ID novo |
| POST /api/casos/ID/consultar | objeto vazio | Estado e dados oficiais |
| GET /api/casos/ID/historico | cookie | Até 100 consultas recentes |
| POST /api/casos/ID/revisar | objeto vazio | Conferência local |
| POST /api/consultar | casos fictícios com id e previous | Laboratório Requests + Beautiful Soup |
| GET /api/saude | nenhuma | Estado do servidor |

400 indica entrada inválida; 401 exige sessão; 403 recusa origem; 404 indica recurso não encontrado; 409 indica conflito; 429 pede espera; 502 indica falha externa; 503 indica configuração ausente.

## 7. Como comprovar o que funciona

```powershell
.venv\Scripts\python.exe -m unittest discover -s backend -v
```

Os testes criam banco temporário real, executam chamadas HTTP autenticadas, verificam persistência, bloqueio de outra conta, duplicação, comparação e preservação em falha. A resposta do CNJ é simulada nos testes determinísticos: passar nesses testes não comprova disponibilidade da API pública. Para validar a integração externa, é preciso consultar com a chave vigente e um processo público conhecido. O script original `rpa_navegador.py` documenta o roteiro do laboratório; ele não cobre automaticamente a nova tela persistente.

## 8. Plano de estudo de três sessões

**Sessão 1 — o caminho HTTP (60–90 min).** Abra a tela com DevTools/Network. Faça cadastro e adicione um processo. Anote método, URL, corpo e status de cada requisição. Leia `api`, `load` e os listeners do JavaScript. Depois acompanhe `do_POST`, `acompanhamento` e `adicionar` em Python. Exercício: acrescente um apelido e explique onde ele é validado e persistido.

**Sessão 2 — integração e comparação (90 min).** Leia `DataJud.buscar` e `Caderno.consultar`. Desenhe entrada, transformação e saída. Execute os testes e altere apenas o mock de movimentos para criar “sem mudança” e “mudança encontrada”. Exercício: explique por que incluir `checked_at` no snapshot causaria uma mudança falsa. Depois faça uma consulta autorizada real e compare sua resposta com o mock.

**Sessão 3 — segurança e apresentação (60–90 min).** Leia autenticação, sessão e verificações de propriedade. Use duas contas e confirme que uma não vê casos da outra. Leia `consulta.py` e compare HTML/Beautiful Soup com JSON/DataJud. Execute o roteiro Playwright original conforme `estudo-do-laboratorio.md`. Exercício: reconstrua uma função de comparação simples sem copiar o código e escreva um teste que demonstre erro da fonte preservando o último dado.

## 9. Como apresentar com domínio e honestidade

“Eu comecei com um laboratório que compara registros de uma fonte HTML controlada. Para evoluir, acrescentei uma API Python, contas locais e persistência em SQLite. O adaptador DataJud consulta metadados públicos, normaliza os movimentos e guarda versões para identificar diferenças. Separei a consulta externa da regra de comparação para conseguir testar falhas e mudanças sem depender da internet. A automação reúne informações; a conferência continua com a pessoa.”

Mostre: entrar, lista persistente, adicionar processo, consultar, histórico e conferir. Se o CNJ estiver indisponível, mostre a falha preservando a referência e use o laboratório fictício para explicar a comparação. Apresente desenvolvimento assistido quando perguntarem como produziu: destaque as decisões que você entende e os exercícios que conseguiu reproduzir. Afirme domínio de uma parte depois de conseguir explicá-la e alterá-la sem copiar.

Perguntas para treinar: por que uma API em vez de Playwright? Porque JSON oficial evita depender de layout. Onde usa Beautiful Soup? Na leitura HTML do laboratório e da documentação da chave pública. Por que SQLite? Execução local sem serviço adicional. O que faria em produção? Framework apropriado, banco gerenciado, migrações, proteção contra tentativas de login, backups, HTTPS e observabilidade. Qual o limite da comparação? Uma mudança no conjunto normalizado exige leitura humana; não implica urgência nem prazo jurídico automaticamente.

## 10. Limites e próxima evolução

Verificação desta entrega: 11 testes passaram, a API local respondeu saudável e a nova página retornou HTTP 200. A autenticação e conectividade do endpoint TJPE/DataJud também responderam HTTP 200 em consulta sem retorno de documentos (`size: 0`). Isso verifica acesso ao serviço, mas ainda falta validar um processo conhecido com dados reais. A inspeção visual pelo navegador integrado não ocorreu porque o uso local do navegador está desativado nas configurações do ambiente.

Esta entrega é um MVP local. O servidor usa a biblioteca padrão HTTP, e a persistência é SQLite; não foram introduzidos FastAPI, JWT nem PostgreSQL porque a base existente já executava Python e a prioridade é um fluxo local compreensível. A Vercel continua publicando somente os arquivos estáticos existentes. A nova página exige o servidor local. Nenhum deploy ou push foi feito nesta etapa.

Ainda faltam: recuperação de senha, edição/exclusão de casos, exportação do caderno real (o CSV original é do laboratório), agendamento, notificações, paginação completa de processos com muitos registros, limites globais de consulta e proteção de login, migrações de banco e operação em produção. A query limita a dez registros por número; valide a suficiência antes de uso profissional. O intervalo por caso não é um limite global contra concorrência. Metadados do DataJud não equivalem ao conteúdo integral dos autos, nem garantem atualização em tempo real. Não há acesso a processos sigilosos ou peticionamento.

Antes de uso em escritório, revise os termos vigentes com a organização e determine a fonte autorizada e a finalidade. As regras do CNJ consultadas na conversa incluem restrições de exploração comercial e exigência de atribuição. O projeto não interpreta prazos nem oferece aconselhamento jurídico.

Referências oficiais: https://datajud-wiki.cnj.jus.br/api-publica/acesso/ ; https://datajud-wiki.cnj.jus.br/api-publica/endpoints/ ; https://atos.cnj.jus.br/atos/detalhar/3453 .
