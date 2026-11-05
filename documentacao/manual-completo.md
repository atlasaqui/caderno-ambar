# Caderno Âmbar por dentro

Manual de estudo de Python, arquitetura e funcionamento do projeto

Edição revisada em 4 de novembro de 2026, com a organização das pastas atualizada. Preparado para Victor Monteiro, com base nos arquivos locais desta revisão.

## 1 Como estudar este documento

Este manual explica como o Caderno Âmbar foi montado, onde cada responsabilidade está localizada e como acompanhar uma ação do usuário até o banco e a fonte de dados. Ele serve para estudar, modificar e demonstrar o projeto. Não é uma declaração de que o aplicativo está homologado para operação jurídica em produção.

A primeira leitura deve seguir os capítulos 2 a 8. Eles constroem a visão geral e ensinam o vocabulário Python usado no código. Depois, estude os arquivos do servidor nos capítulos 9 a 15, a interface nos capítulos 16 a 19 e os testes e exercícios finais. O catálogo complementar mapa-do-codigo.md lista os símbolos encontrados no código e suas responsabilidades, com linhas de referência da revisão.

Abra o projeto no VS Code ao lado do manual. Não tente decorar nomes de métodos. Para cada fluxo, procure responder: quem chama, o que entra, o que é validado, o que é gravado, o que sai e o que acontece se falhar. Saber responder a essas perguntas mostra mais domínio do que repetir nomes de bibliotecas.

Os exemplos de código deste manual são recortes ou simplificações didáticas. Quando houver diferença, o arquivo local é a implementação de referência. Não copie exemplos para um banco real sem compreender o efeito. Os exemplos não contêm credenciais reais.

## 2 O problema que o aplicativo resolve

Um escritório acompanha vários processos e precisa saber quando uma informação mudou, quem leu essa mudança e qual trabalho foi feito a partir dela. Consultar a fonte é apenas uma parte do problema. Também é necessário preservar a referência anterior, distribuir responsabilidades e registrar a conclusão.

O Caderno Âmbar organiza esse ciclo: cadastrar processo, consultar, comparar, conferir e criar uma providência. Uma versão representa um conteúdo recebido da fonte. Uma conferência registra a leitura humana de uma versão. Uma providência representa trabalho que alguém deve executar e outra pessoa pode revisar. Esses três conceitos têm registros e estados próprios.

Exemplo fictício: a primeira consulta informa distribuição. Outra consulta encontra uma audiência. O aplicativo guarda uma versão nova, mostra a diferença e registra uma pendência de leitura. A pessoa confere a informação e cria a providência “Preparar documentos para análise”, atribui responsável e revisor e informa uma data interna. A revisão da tarefa não substitui a leitura da fonte e não é uma prática de ato judicial.

O produto atual é focado em acompanhamento e rotina. Não oferece acesso integral aos autos, peticionamento, financeiro, validação jurídica ou contagem automática de prazos. O módulo de treino utiliza dados fictícios. O transporte DataJud está preparado no código, mas o uso real depende de configuração, condições de acesso e validação com uma carteira autorizada.

## 3 Arquitetura em uma página

Há quatro camadas principais. A interface é HTML, CSS e JavaScript no navegador. A API é a porta HTTP do servidor, construída com FastAPI. Os serviços Python aplicam regras e acessam persistência. As fontes externas ou fictícias fornecem a informação consultada. O SQLite guarda contas, processos, versões e tarefas em um arquivo local.

O caminho normal é navegador → FastAPI → sessão e autorização → serviço → SQLite ou fonte → serviço → JSON → interface. A tela não acessa o SQLite diretamente. A chave de uma fonte pertence ao servidor; não deve aparecer em JavaScript enviado ao visitante.

O projeto contém duas gerações de servidor. backend/servidor.py é o laboratório legado na porta 8092. backend/aplicacao.py é a entrada recomendada da aplicação de equipes na porta 8093. Manter os dois arquivos ajuda a estudar a evolução, mas eles não têm os mesmos recursos. Abrir a tela atual sobre o servidor antigo pode provocar erros de contrato.

A parte persistente usa uma cadeia de herança: Caderno → Equipes → Escritorio → Piloto. Caderno contém a base de contas e armazenamento. Equipes acrescenta escritórios, versões, importação e tarefas. Escritorio acrescenta providências e processamento de filas. Piloto acrescenta confirmação de e-mail, carteira paginada, resumo e exportação administrativa. A API instancia Piloto; ao chamar um método, Python procura primeiro nessa classe e depois nas bases.

Essa evolução evita reescrever todo o sistema, mas também tem um custo: para entender um método herdado, pode ser necessário abrir mais de um arquivo. Uma refatoração futura pode separar repositórios, autenticação e serviços de domínio por composição. Não é necessário trocar a arquitetura inteira para corrigir uma função pequena.

## 4 Pastas e arquivos da raiz

backend contém o servidor Python, regras, integrações e testes Python. frontend contém as páginas e recursos entregues ao navegador. tests contém os testes JavaScript em DOM simulado. ferramentas reúne utilitários de documentação. documentacao reúne os guias, o catálogo e as versões de leitura do manual. output contém banco, mensagens locais, backups e resultados de execução; não deve ser versionada como código público.

requirements.txt fixa versões das dependências Python usadas no ambiente. FastAPI constrói a aplicação HTTP; Uvicorn executa o servidor ASGI; Requests faz chamadas HTTP de saída; Beautiful Soup extrai HTML; Playwright automatiza o navegador no roteiro de estudo. Algumas dependências são transitivas, como certifi e urllib3, usadas pelo transporte HTTP. Ter Playwright instalado não significa que ele participa de todas as consultas.

package.json descreve os comandos dos testes de interface e a dependência jsdom. package-lock.json registra a resolução dessas dependências. node_modules contém os pacotes instalados e não é fonte autoral do projeto. Não é necessário estudar cada arquivo de uma biblioteca para entender o aplicativo, mas é necessário saber o contrato que ela fornece.

INICIAR.cmd prepara um ambiente .venv, instala requirements.txt e inicia a aplicação. .venv isola bibliotecas Python do projeto; ela não contém o código de negócio. O lançador exige Python disponível e acesso aos pacotes quando a instalação ainda não foi feita. Não é um instalador de produção.

.env.example documenta variáveis esperadas. O programa atual lê os valores do ambiente do processo com os.environ; ele não carrega esse arquivo automaticamente. Copiar .env.example para .env, sem configurar um carregador, não ativa os valores. A configuração pode ser passada pelo terminal ou pelo serviço de hospedagem.

.gitignore impede que arquivos sensíveis ou gerados sejam incluídos normalmente no Git. Ele não remove um segredo que já tenha sido publicado. .dockerignore reduz o contexto enviado ao Docker. Dockerfile descreve uma execução Linux com usuário sem privilégios e banco em /data. A receita ainda precisa ser construída e verificada no ambiente de destino.

vercel.json pertence à publicação estática existente. Servir frontend pela Vercel não coloca automaticamente a aplicação Python persistente no ar. Para a versão completa, é necessário hospedar a API e o armazenamento de forma compatível e revisar origem, rotas e HTTPS.

README.md apresenta o projeto. primeiro-guia-de-estudo.md documenta o primeiro laboratório. guia-de-equipes.md explica a evolução de equipes. guia-de-providencias.md detalha providências e filas. revisao-da-interface.md registra ajustes de experiência. fluxo-das-telas.md explica a divisão entre apresentação, treino, acesso e uso. testes-e-validacao.md reúne evidências por etapa. estado-atual-do-projeto.md é o estado atual de implementação e pendências. Este manual integra a explicação para estudo; os registros anteriores permanecem como histórico.

## 5 Python para quem vem de Java

Python usa indentação para delimitar blocos. Uma definição começa com def e dois pontos; o corpo fica recuado. Diferentemente de Java, uma variável não precisa declarar o tipo antes do nome. Isso não significa ausência de tipos: cada valor tem um tipo em tempo de execução. As anotações auxiliam leitura e ferramentas, mas não substituem validação dos dados de uma requisição.

```python
def saudacao(nome: str) -> str:
    return 'Olá, ' + nome
```

def cria a função; nome é um parâmetro; str indica intenção de receber texto; a seta indica retorno textual; return entrega um resultado ao chamador. Uma chamada saudacao('Victor') devolve um novo texto. Se uma função apenas exibe algo com print, isso não equivale a devolver um resultado para a API.

Listas representam sequências, como as movimentações. Dicionários associam chaves a valores, como um processo com numero e tribunal. Tuplas são sequências imutáveis frequentemente usadas como parâmetros SQL. Conjuntos ajudam a comparar ou eliminar duplicações. None representa ausência de valor. True e False são booleanos, com inicial maiúscula em Python.

```python
caso = {'numero': 'DEMO-1', 'tribunal': 'tjpe'}
numero = caso.get('numero', '')
movimentos = [{'codigo': 26}, {'codigo': 123}]
codigos = {m['codigo'] for m in movimentos}
```

caso['numero'] exige que a chave exista. caso.get('numero', '') devolve uma alternativa quando ela não existe. A compreensão de conjunto percorre a lista e extrai códigos únicos. No projeto, compreensões aparecem em validação de schema, transformação de resultados e comparação de movimentos. Para estudar, reescreva uma compreensão como um for com append ou add e compare os resultados.

Operadores and e or podem devolver os próprios operandos, não apenas booleanos. Por isso cliente or Demonstracao() escolhe cliente quando ele existe; caso contrário, constrói uma fonte demonstrativa. Já is None verifica ausência de maneira explícita. Não confunda texto vazio, número zero e None quando o campo de negócio distingue essas situações.

f-strings interpolam valores: f'casos/{id}/consultar'. Use-as para textos e caminhos controlados. Em SQL, valores recebidos devem ser parâmetros com ?, não interpolação. Um identificador de tabela dinâmico exige lista interna controlada, porque parâmetros SQL normalmente representam valores, não nomes de tabelas.

## 6 Classes e herança no projeto

Uma classe agrupa estado e comportamento. self é a referência à instância atual, comparável ao this de Java. __init__ inicializa o objeto. super() chama comportamento da classe base. Métodos com @staticmethod não recebem self porque não dependem do estado da instância.

```python
class Piloto(Escritorio):
    def __init__(self, arquivo):
        super().__init__(arquivo)
        self.migrar_carteira()
```

Nesse recorte, Piloto recebe o caminho do banco. O construtor da base prepara as estruturas anteriores; depois a nova classe aplica a própria migração. Não copie uma criação de objeto para dentro de cada requisição: isso repetiria verificações de schema desnecessariamente. criar_app cria o serviço e o guarda no estado da aplicação.

Quando Piloto sobrescreve convidar, ele exige e-mail confirmado e chama super().convidar para aproveitar a regra já existente de administrador, token e destino. Um teste apenas de Equipes não comprova essa nova exigência: é necessário um teste de Piloto ou da API que o utiliza.

Fonte, em fontes.py, usa Protocol. Ele descreve a forma esperada de uma fonte: disponibilizar buscar(tribunal, numero). Demonstracao e DataJudValidado podem atender a esse contrato sem herdar uma mesma implementação concreta. Isso permite injetar uma fonte de teste, simulando falha ou demora sem depender da internet.

## 7 Erros e recursos com fechamento garantido

FalhaAPI carrega um status HTTP e uma mensagem compreensível. O serviço pode lançar FalhaAPI(403, 'Acesso recusado.'); a camada HTTP converte a falha em JSON e código de resposta. raise interrompe o caminho normal. try e except tratam erros esperados. finally executa a limpeza mesmo quando há erro.

O bloco with representa um gerenciador de contexto. Em conexao, o projeto abre sqlite3, configura o tipo das linhas e garante fechamento ao sair. O with db confirma a transação quando tudo dá certo e desfaz alterações quando ocorre uma exceção. O decorador @contextmanager transforma uma função com yield em um contexto utilizável por with.

```python
with self.conexao() as db:
    db.execute('BEGIN IMMEDIATE')
    registro = db.execute('SELECT id FROM casos WHERE id=?', (id,)).fetchone()
```

O ? recebe o parâmetro id separadamente. (id,) é uma tupla com um elemento; a vírgula faz diferença. fetchone retorna uma linha ou None. fetchall devolve as linhas encontradas. dict(linha) transforma uma sqlite3.Row em dicionário para serialização e uso no serviço.

Não use except Exception para transformar qualquer erro em sucesso. O projeto registra erros inesperados e preserva a referência anterior. Nas fronteiras, uma mensagem pública deve evitar revelar senha, token, conexão ou caminho interno. O log técnico deve permitir investigação sem expor conteúdo sensível desnecessário.

## 8 HTTP e comunicação entre interface e servidor

HTTP é o protocolo entre navegador e API. GET consulta informação; POST envia uma ação ou dados. O corpo JSON é uma representação de objetos, listas, textos, números e booleanos. JSON não é uma conexão com o banco e não executa Python no navegador.

No frontend, fetch chama /api/carteira com parâmetros como org, pagina, busca e filtro. No servidor, FastAPI identifica a rota, converte parâmetros tipados, lê o cookie e chama o serviço. A resposta vira JSON. O JavaScript lê a resposta, verifica response.ok e atualiza o DOM.

Códigos usados no projeto: 200 indica resposta bem-sucedida; 400 indica dados inadequados; 401 exige autenticação; 403 recusa uma ação ou escritório; 404 indica recurso inexistente ou indisponível naquele escopo; 409 indica conflito, duplicação ou revisão desatualizada; 413 recusa corpo grande; 422 pode vir da validação tipada do FastAPI; 429 aplica limite temporário; 502 descreve falha do serviço externo; 503 indica configuração ou serviço indisponível.

O navegador recebe um cookie de sessão HttpOnly. Ele o envia em chamadas da mesma origem, mas o JavaScript não deve ler seu conteúdo. O SQLite guarda o hash do token. Autenticar é descobrir quem é a pessoa; autorizar é verificar se aquela pessoa pode trabalhar naquele escritório ou alterar aquela providência. Esconder um botão não substitui a autorização no servidor.

## 9 aplicacao.py e a entrada recomendada

criar_app é uma fábrica: recebe um banco opcional e a opção de executar ciclos, cria Piloto, define rotas, middleware e recursos estáticos e devolve FastAPI. Isso permite criar uma aplicação de teste com banco temporário e sem tarefas de fundo. No uso local, o bloco __main__ chama Uvicorn.

Em produção, a fábrica exige origem HTTPS e configuração de banco e SMTP. Essa verificação evita iniciar uma instalação claramente incompleta, mas não comprova que o domínio, o certificado, o banco e o provedor funcionam. AMBAR_WORKER permite desativar os ciclos em processos HTTP extras.

lifespan cria tarefas assíncronas para consultas, e-mails e backups. Ao encerrar, cancela e aguarda as tarefas. agendador repete uma função em intervalos, registra falhas e usa run_in_threadpool para executar trabalho síncrono sem bloquear diretamente o laço assíncrono. asyncio.sleep cede execução; não é uma espera ocupada.

controles é o middleware aplicado às requisições. Ele verifica origem, tamanho do corpo e características de requisições entre sites. Também acrescenta identificador de requisição, política de conteúdo, proteção contra interpretação incorreta de tipo e regras de cache. O TrustedHostMiddleware restringe hosts aceitos. Essas proteções não constituem uma auditoria completa de segurança.

limitar grava contadores temporários no SQLite, dentro de uma transação. É usado em autenticação, recuperação, confirmação e consultas. Esse mecanismo local atende ao desenho atual de uma instância, mas pode exigir outra estratégia em uma implantação distribuída. O IP considerado vem da conexão; confiar em cabeçalhos de proxy exige configuração deliberada.

dados verifica application/json e exige objeto JSON. endpoint encaminha rotas legadas para dispatch em uma thread. dispatch organiza autenticação, contexto, processos, equipe, rotina e exportações. A rota nova /api/carteira tem parâmetros explícitos no FastAPI. As demais rotas ainda estão agrupadas em um roteador genérico; não existe documentação OpenAPI detalhada de cada uma.

saude verifica uma conexão básica com o banco. Retornar status ok não comprova a saúde do SMTP ou a disponibilidade do tribunal. runtime serve a configuração JavaScript do laboratório. StaticFiles entrega as páginas de frontend. Em desenvolvimento, HTML, CSS e JavaScript recebem no-store para reduzir problemas de cache durante revisão.

## 10 acompanhamento.py e a base persistente

FalhaAPI é a exceção de domínio usada pela API. Caderno.__init__ prepara o caminho do banco e cria a estrutura original: usuarios, sessoes, casos e consultas. Essa base pessoal nasceu antes dos escritórios. Seu listar e seu revisar representam o contrato antigo; na versão atual, parte dessas operações é sobrescrita por classes mais recentes.

hash_senha usa scrypt com salt aleatório. Salt é um valor associado à senha para impedir que duas senhas iguais produzam automaticamente o mesmo resultado armazenado. O banco não precisa guardar a senha original para conferir login. hmac.compare_digest compara os resultados de forma apropriada para esse contexto. Hash não é criptografia reversível.

autenticar valida e-mail e tamanho da senha. No cadastro, insere usuário com hash. No login, procura a conta e compara a senha calculada. Ao autenticar, gera token aleatório, armazena apenas SHA-256 do token e registra expiração. O token original é devolvido à camada HTTP para virar cookie; não deve aparecer em logs.

usuario resolve um token de sessão válido em um ID de usuário. sair elimina essa sessão. Alterar a senha pelo fluxo de recuperação elimina as sessões existentes, obrigando novo login. A confirmação de e-mail é uma regra posterior, em Piloto, e não deve ser confundida com o sucesso do login.

DataJud.buscar faz a requisição ao endpoint oficial correspondente ao tribunal. Envia Authorization no servidor, consulta o número exato, pagina os resultados, preserva os graus retornados e organiza movimentações. Há limites de tempo, volume e quantidade de páginas. Atingir o limite gera falha em vez de gravar uma resposta truncada como completa.

O transporte não abre navegador e não utiliza Beautiful Soup, porque recebe JSON. Requests é a biblioteca HTTP usada nesse caminho. O código de extração Beautiful Soup pertence ao laboratório HTML de consulta.py. Essa distinção é importante para explicar corretamente o projeto na entrevista.

A conexão do DataJud é direta por padrão e mantém a validação TLS. Para herdar os proxies configurados no ambiente, use AMBAR_DATAJUD_USAR_PROXY=1. O transporte diferencia limite e sobrecarga, respeita Retry-After e preserva a referência anterior. Consulta páginas de dez registros com projeção de campos e search_after ordenado por @timestamp. Respostas parciais são recusadas. A tabela fontes_estado guarda a espera e a reserva da fonte, também respeitadas pela consulta manual. Em 04/11, o fluxo autenticado recebeu 35 movimentos do TJPE e gravou uma versão real, preservada após novo login. Veja diagnostico-e-correcao-datajud.md para evidências e limites.

### Atualização em segundo plano

O botão Solicitar atualização usa POST /api/casos/{id}/agendar. HTTP 202 significa que o pedido foi salvo na fila; não significa que o CNJ já respondeu. Piloto verifica e-mail e escopo. Equipes.agendar_consulta registra solicitante e momento da próxima tentativa, sem fazer rede nessa requisição. A migração 5 acrescenta solicitada, solicitante e codigo à tabela tarefas.

Escritorio.consultas_tick processa solicitações avulsas e periódicas em sequência, respeitando reserva e espera. Após erro transitório, a espera cresce e considera Retry-After. Após cinco falhas consecutivas, o ciclo pausa. Falhas de credencial ou configuração exigem atenção, sem repetição automática indefinida. O sucesso limpa o pedido e reaproveita a versão quando não há diferença. Um reinício preserva a fila no banco.

O frontend mostra fila e última consulta válida separadamente. Pode ler o estado local a cada 15 segundos sem consultar o CNJ, evitando recarregar durante edição ou histórico aberto. Os dados anteriores continuam disponíveis e um processo ainda sem resposta não recebe conteúdo inventado. O servidor precisa permanecer ligado e com worker ativo. Veja fila-atualizacoes-datajud.md para o roteiro e seus limites.

## 11 fontes.py e comparação das informações

validar_numero remove pontuação e espaços, exige vinte dígitos, confere o segmento e tribunal suportados e calcula os dígitos verificadores. Um número com formato válido não comprova que o processo existe, que está público ou que está disponível naquela fonte.

serializar produz JSON com ordenação de chaves e separadores estáveis. Isso reduz diferenças causadas apenas pela forma de representar um objeto. versao calcula SHA-256 dessa representação. Hash de conteúdo ajuda a identificar igualdade; ele não comprova autenticidade jurídica da fonte.

normalizar valida o contrato mínimo: objeto com registros, registros com lista de movimentos e movimentos com código e data textual. Remove movimentos exatamente repetidos e ordena os resultados de maneira estável. Ela não interpreta o significado jurídico de uma movimentação, nem garante que uma data textual seja um prazo.

diferencas monta conjuntos de movimentos considerando o grau do registro, encontra inclusões e remoções e compara dados cadastrais separados dos movimentos. O retorno classifica primeiro registro, sem diferença, nova movimentação, correção ou remoção e alteração cadastral. Uma remoção pode ser correção da fonte; a interface não deve anunciar uma conclusão jurídica automática.

DataJudValidado reaproveita DataJud e acrescenta validação do número e normalização. Demonstracao devolve conteúdo fictício controlado por etapa. O primeiro estado tem uma distribuição; o segundo acrescenta uma audiência fictícia. Trocar a fonte por uma demonstrativa nunca pode ser uma recuperação silenciosa de erro real.

## 12 equipes.py e o trabalho compartilhado

Equipes.__init__ cria tabelas de organização e acrescenta colunas ao cadastro antigo de processos. _org associa uma conta antiga a um escritório pessoal se ela ainda não tiver vínculo. Isso preserva contas e casos anteriores. Uma migração muda a estrutura do banco; não é o mesmo que importar uma carteira de processos.

org verifica associação e, quando necessário, papel de administrador. caso encontra o processo e verifica acesso ao escritório dele. Esses métodos são pontos importantes do isolamento: um ID de processo não é uma autorização. contexto lista os escritórios aos quais a pessoa pertence; membros informa integrantes do escritório autorizado.

adicionar valida CNJ e apelido, recusa duplicação dentro do escritório e cria o processo com responsável. alterar permite organizar apelido, etiquetas, observações, responsável, arquivamento e periodicidade. O responsável precisa ser membro. Um intervalo não nulo precisa respeitar o mínimo de 900 segundos. Arquivar muda a seleção de trabalho, não apaga o histórico.

consultar começa com uma transação curta que verifica acesso, arquivamento e reserva. A reserva lease impede duas consultas simultâneas de ocuparem a mesma tarefa. A chamada à rede ocorre depois dessa transação. Ao receber a fonte, outra transação relê o estado, compara, grava versão e consulta, atualiza referência e agenda a próxima tentativa.

Quando o conteúdo é idêntico, a versão atual é reutilizada. Quando o conteúdo volta a um estado antigo após uma mudança intermediária, uma nova transição recebe nova versão. Isso evita tratar uma leitura antiga como se alguém tivesse lido o retorno recente da fonte.

Se houver novidade, notificacoes registra o evento do escritório e emails recebe mensagens para membros que aderiram à preferência. Se ocorrer falha, consultas registra o erro, tarefas recebe tentativa e próxima execução e casos conserva o snapshot anterior com a informação da falha. É necessário mostrar a falha na interface para não transmitir falsa atualidade.

revisar registra pessoa, versão, instante e observação. detalhe reúne versões e conferências para a linha do tempo. historico é herdado da base e usa a verificação de caso sobrescrita. audit registra ações de organização e trabalho. Auditoria operacional não significa assinatura digital nem trilha inviolável: um operador com acesso ao arquivo SQLite tem poderes que a interface não tem.

convidar gera um token de 24 horas vinculado a e-mail e escritório; aceitar confere destinatário e validade e consome o convite. Na classe Piloto, ambos exigem e-mail confirmado. revogar tem uma versão antiga neste arquivo e uma versão efetiva em Escritorio, com reatribuição de responsabilidades.

importar lê CSV separado por ponto e vírgula, valida até 500 linhas, identifica duplicados e permite prévia sem gravação. A confirmação processa as linhas válidas e informa rejeições. Não é uma transação única de tudo ou nada; a interface precisa apresentar o resultado por linha. Um processo inválido não deve ser anunciado como importado.

tick e email_tick deste arquivo são legados da primeira versão de equipes. A aplicação atual usa consultas_tick e email_tick de Escritorio em ciclos separados. backup_tick continua herdado e usa o utilitário consistente de cópia. Saber qual implementação é efetivamente chamada evita estudar um método legado como se ele fosse o caminho atual.

## 13 rotina.py e as providências

Escritorio cria providencias e eventos_providencia e acrescenta os campos de reserva da fila de e-mails. ESTADOS enumera os estados aceitos. TRANSICOES informa os caminhos permitidos, impedindo saltos arbitrários de uma atividade recém-criada para concluída.

criar_providencia valida título, descrição, prioridade, responsáveis e data interna opcional. Confere se a versão pertence ao processo e se responsável e revisor pertencem ao escritório. Grava o estado inicial e um evento. A providência pode ser geral ou ligada a uma versão específica que motivou a ação.

rotina consulta as atividades com filtros minhas, equipe, atrasadas, revisar e concluídas. Faz busca e paginação de 25 resultados no banco. O resumo informa contagens de trabalho. Uma atividade sem data não é vencida. A data interna é um compromisso administrativo; não há calendário de feriados ou contagem de prazo processual.

alterar_providencia verifica acesso, participante autorizado, revisão apresentada e transição de estado. A revisão é um inteiro incrementado a cada alteração. Se duas pessoas abrem a revisão 1, a primeira salva e cria revisão 2. A segunda recebe conflito 409 ao tentar gravar revisão 1. Isso evita perda silenciosa de trabalho.

Enviar para revisão exige evidência textual. Concluir exige revisor ou administrador e mantém a exigência de evidência. Reabrir exige comentário. A mesma pessoa pode ser executor e revisor para uso individual; separação obrigatória entre duas pessoas ainda não é uma política configurável. historico_providencia mostra eventos autorizados do registro.

consultas_tick busca até três tarefas elegíveis e usa ThreadPoolExecutor para consultas paralelas limitadas. Não cria uma thread ilimitada por processo. A reserva da consulta continua sendo o controle individual. O limite global de consultas manuais da API não é, por si só, um limitador distribuído de todos os workers.

email_tick reserva uma mensagem dentro de transação curta, revalida membro e preferência, faz o envio fora da transação e grava resultado depois. Uma chamada de rede lenta não deve manter o SQLite com uma transação de escrita aberta. A reserva expirada permite recuperação após interrupção.

Ainda existe uma janela de incerteza externa: o provedor pode aceitar a mensagem e o processo cair antes de registrar esse aceite. Uma retentativa pode duplicar o envio. O sistema não promete exatamente uma entrega externa. Para melhorar essa garantia, o provedor precisa oferecer um mecanismo compatível de idempotência e acompanhamento.

operacao lista diagnóstico administrativo de consultas e e-mails recentes. reprocessar confere administração e elegibilidade antes de agendar nova tentativa. revogar remove o membro, transfere processos e funções para o administrador e cancela mensagens pendentes. Uma mensagem que já começou a ser transmitida não pode ser desfeita retroativamente.

## 14 piloto.py e as melhorias desta revisão

Piloto é a classe concreta criada pela API atual. Seu construtor executa as bases e acrescenta a evolução de identidade e carteira. migrar_carteira procura a restrição antiga UNIQUE(usuario, numero, tribunal). Antes de reconstruir a tabela, cria uma cópia consistente com nome exclusivo no mesmo diretório.

A reconstrução copia todas as colunas e conserva os IDs, troca a unicidade para escritório, número e tribunal e verifica referências com PRAGMA foreign_key_check antes do commit. Se houver conflito ou vínculo inválido, ocorre rollback. O backup local da migração não substitui uma cópia externa protegida. A operação deve acontecer com inicialização controlada, sem iniciar simultaneamente várias instâncias migradoras.

conta devolve somente ID, e-mail e instante de confirmação. solicitar_verificacao gera segredo aleatório, guarda hash e expiração de trinta minutos e entrega o código pelo adaptador de correio. Se o envio falhar, remove o token correspondente e propaga o erro. Não devolve código de confirmação na resposta da API.

confirmar_email exige token pertencente à conta autenticada, válido e ainda não consumido. Atualiza email_verificado e elimina os tokens da conta em transação. Contas antigas não são marcadas como verificadas automaticamente. exigir_email bloqueia compartilhamento e consulta real sem essa confirmação; treino e demonstração permanecem disponíveis.

Em desenvolvimento, a mensagem fica em um arquivo local. Ler esse arquivo ensina o fluxo, mas não prova que a pessoa controla uma caixa de e-mail externa. Em produção, a comprovação depende de entrega pelo canal configurado. A confirmação de e-mail não é segundo fator de autenticação em cada login.

carteira recebe escritório, página, busca e filtro. Monta condições SQL parametrizadas, conta resultados e devolve vinte itens da página, indicadores completos e referência à demonstração. Não depende da lista legada limitada a mil registros. A busca usa LIKE e pode precisar de índices ou busca especializada se a carteira crescer muito.

resumo_diario calcula providências do usuário, vencidas e aguardando revisão. solicitar_dados registra um pedido administrativo de retenção ou exclusão; não executa eliminação. exportar_escritorio organiza dados relacionados do escritório em JSON, sem hashes de senha, sessões, convites ou tokens. É exportação administrativa, não um formato de restauração já implementado.

## 15 consulta.py correio.py backup.py e scripts de execução

consulta.py é o exemplo mais direto para aprender Requests e Beautiful Soup. validar_entradas exige de um a três casos, códigos no formato do catálogo e referência anterior textual. consultar_fonte faz GET da fonte HTML local, com timeout e sem depender do proxy do sistema, verifica HTTP e chama extrair_e_comparar.

extrair_e_comparar usa seletores CSS para encontrar article[data-case], .movement e .date. Extrai texto e compara com previous. Um registro ausente recebe ok falso e erro; não vira sucesso fictício. main usa argparse para permitir execução pelo terminal e grava um relatório JSON. A data da fonte ausente continua sendo uma informação incompleta mesmo quando o usuário registra que leu.

correio.py concentra entregar. Em desenvolvimento, grava JSON em output/email-local. Em produção, exige configurações SMTP, inicia STARTTLS, autentica e envia EmailMessage. O retorno aceito_pelo_smtp comprova apenas aceite pelo servidor, não leitura ou entrega final. Nenhum provedor específico de eventos de entrega está integrado nesta versão.

backup.py oferece copiar e interface de terminal. Abre origem em modo somente leitura, executa integrity_check, usa o mecanismo backup do SQLite e verifica o destino. Recusa sobrescrever arquivo existente. Restaurar significa apontar uma execução isolada para uma cópia verificada, não substituir às cegas um banco em uso.

rpa_navegador.py contém o roteiro Playwright: inicia servidor de laboratório, abre navegador, adiciona caso fictício, consulta, compara, registra conferência, baixa CSV e grava evidências. Requests realiza HTTP sem navegador; Beautiful Soup interpreta HTML recebido; Playwright opera uma página como usuário. O roteiro não equivale a integração com sistemas judiciais reais e não foi executado nesta revisão, porque o acesso ao navegador local está desativado.

servidor.py implementa o servidor legado com ThreadingHTTPServer e Handler. Ele é útil para estudar requisições sem FastAPI e para o roteiro histórico, mas não é a entrada do piloto. iniciar_datajud.py também é legado: busca uma chave pública na documentação e chama o servidor antigo. Não o use como lançador do aplicativo atual. AMBAR_DATAJUD_HABILITADO e DATAJUD_API_KEY pertencem à configuração explícita da aplicação atual.

## 16 As páginas da interface

index.html é a apresentação pública. Explica o produto e separa conhecer, treinar, criar acesso e usar. Não é o painel de processos e não deve concentrar todos os formulários. As imagens office.jpg e workspace.jpg são recursos visuais; não representam dados de processos. marca.svg é um recurso de marca legado; o cabeçalho atual usa composição tipográfica.

laboratorio.html é o treino sem conta, com os cenários cível, contratual e trabalhista fictícios. portal.html é a fonte HTML controlada usada pelo treino. Esses códigos de treino não são números CNJ de processos reais. runtime-config.js indica o modo disponível quando servido estaticamente; o FastAPI fornece sua versão dinâmica na mesma rota.

acesso.html contém formulário de cadastro e login em modos separados. acesso.js alterna o modo, orienta os campos, evita reenvio simultâneo, faz POST, apresenta erro e encaminha para acompanhamento.html após sucesso. O guia da área de trabalho pode ser solicitado após o acesso. A senha é limpa do formulário e não é persistida em localStorage pelo código.

acompanhamento.html estrutura a área persistente: entrada, escritório, processos, rotina, equipe, notificações, histórico e providência. Parte dos painéis novos é inserida por piloto.js. Cada botão precisa ter ação, estado de carregamento, erro e possibilidade de recuperação. Só apresentar uma tela bonita sem lidar com falhas tornaria o fluxo incompleto.

amber.css estiliza o laboratório original. acompanhamento.css contém a identidade e os componentes da aplicação de equipes. percurso.css conecta apresentação, acesso e treino e ajusta diálogos. CSS decide apresentação, não autorização. Alterar uma classe não pode liberar uma ação que o servidor proíbe.

## 17 acompanhamento.js e a comunicação da aplicação

el encontra um elemento pelo ID. text cria um elemento e atribui textContent, evitando interpretar texto recebido como HTML. button e field constroem controles consistentes. status informa andamento, sucesso ou falha. signedIn alterna a apresentação autenticada, mas a API continua responsável pelo acesso real.

api centraliza fetch, método, JSON, timeout, verificação de tipo de resposta e tratamento de 401. eventosDaAcao guarda caminhos de ações concluídas para o tutorial; não inclui corpos com senha ou token. run evita duas ações simultâneas, marca áreas como ocupadas, trata erro e restaura controles e foco ao terminar.

load obtém escritórios, mantém uma seleção válida, carrega carteira paginada e membros, atualiza os painéis e busca notificações. renderMetrics usa as contagens completas devolvidas pelo servidor. render desenha apenas os itens da página e os controles de paginação. A busca espera um pequeno intervalo antes de enviar nova consulta, evitando chamada a cada tecla imediata.

caseCard monta identidade, fonte, estado, última consulta válida, prévia e ações do processo. history carrega histórico técnico e versões, apresenta diferenças e permite leitura ou criação de providência. review registra a leitura de uma versão concreta. editor permite organizar responsável, etiquetas, observações, periodicidade e arquivamento.

submit converte FormData em objeto e encaminha para a ação correspondente. Os eventos de cadastro, importação, equipe e recuperação usam esse padrão. A exportação CSV trata download de um arquivo por Blob e revoga a URL temporária. iniciarAplicacao evita que a inicialização aconteça duas vezes enquanto os scripts do guia terminam de carregar.

Os scripts compartilham funções no mesmo contexto de página; a ordem de carregamento importa. Acompanhamento vem antes de rotina, piloto e guia. Esse desenho é simples para o projeto atual, mas uma evolução com módulos JavaScript poderia tornar dependências mais explícitas. Não mude a ordem sem testar a inicialização e o tutorial.

## 18 rotina.js piloto.js e guia.js

rotina.js cria o seletor de CSV, abre o formulário de providência e gerencia a área Minha rotina. atualizarRotinaContexto limpa dados quando o escritório muda e aplica visibilidade de administração. trocarArea alterna processos e rotina. abrirProvidencia preenche processo, versão e participantes. carregarRotina consulta filtros e paginação do servidor.

providenciaCard desenha a tarefa, os estados permitidos, comentário, evidência e histórico. A API ainda verifica tudo o que a tela oferece. carregarOperacao mostra filas e reprocessamento para administradores. Um erro 409 significa atualizar a referência antes de insistir no envio; não deve ser escondido como sucesso.

piloto.js acrescenta Minha conta, confirmação de e-mail, resumo diário e Dados do escritório. O formulário de confirmação envia token apenas no corpo do POST. A exportação baixa JSON autenticado. A solicitação de dados mostra expressamente que não apaga registros. carregarPainelPiloto atualiza identidade, contagens e visibilidade conforme o papel da pessoa no escritório.

guia.js descreve etapas da área autenticada e relaciona uma orientação com um controle existente e, quando aplicável, uma ação bem-sucedida da API. Guarda apenas passo e estado de atividade no navegador. pausarGuia remove destaques; iniciarGuia retoma ou reinicia; mostrarGuia apresenta instrução e alvo; avancarGuia progride. Pausar o guia não encerra a sessão.

O guia não deve substituir o design normal. Uma pessoa precisa conseguir usar o aplicativo sem seguir todas as etapas. Não preencha ou envie convites, exclusões ou dados reais apenas para avançar uma instrução. Ações opcionais de demonstração devem ser distinguidas de ações com efeitos no escritório.

## 19 amber.js e o laboratório de treino

amber.js mantém catálogo, seleção, referências e histórico da sessão de treino. visibleCases aplica busca e filtro local porque o catálogo fictício é pequeno. statusOf transforma o estado de um caso em texto. render e renderCatalog atualizam lista e catálogo. openDetail mostra antes e depois; closeDialog fecha o diálogo e coordena o guia.

carregarFonteTreino busca portal.html, verifica sucesso e extrai campos conhecidos com DOMParser, construindo novos elementos com conteúdo textual. Não injeta o HTML completo da fonte no aplicativo. A tentativa anterior de usar iframe foi retirada porque a política frame-ancestors proíbe incorporação. A correção preservou essa proteção e tornou a visualização interna independente do iframe.

O carregamento tem identificação de requisição para ignorar respostas antigas sobrepostas. A etapa da fonte avança apenas após carregamento válido. Falha mostra erro e permite tentar novamente. A fonte também pode ser aberta separadamente. Isso ensina um princípio de interface: o próximo passo só deve depender de uma ação cuja conclusão foi realmente observada.

configurarCasoGuiado adapta instruções ao cenário selecionado. advance e updateCoach coordenam eventos e apresentação do guia. O cenário trabalhista inclui informação incompleta para ensinar a diferença entre registrar leitura e resolver a ausência de dados. A lista e o histórico desse laboratório não são a carteira persistente do escritório.

## 20 Banco de dados e relações

usuarios guarda identidade e hash de senha; sessoes guarda hashes de tokens e expiração; verificacoes_email e recuperacoes guardam tokens de uso temporário em forma de hash. organizacoes e membros definem escritórios e papéis. convites guarda destino, escritório e expiração. Esses registros são de controle de acesso, não de movimentação judicial.

casos liga um processo a escritório e responsável e guarda referência atual, versão, periodicidade e erro. consultas registra cada tentativa e seu resultado. versoes guarda conteúdo normalizado e diferenças. conferencias liga uma pessoa à versão lida. notificacoes liga a novidade ao escritório. tarefas controla quando consultar novamente e quem reservou a execução por tempo limitado.

providencias guarda estado atual, pessoas, evidência e revisão. eventos_providencia guarda a sequência de ações. auditoria registra ações relevantes do escritório. preferencias controla adesão aos avisos; emails registra a fila. limites controla contadores temporários. migracoes registra evolução do schema. solicitacoes_dados guarda pedidos administrativos pendentes.

Chave primária identifica uma linha. Chave estrangeira relaciona uma linha com outra. UNIQUE impede combinações repetidas. Índice melhora consultas compatíveis com suas colunas. Uma transação agrupa alterações que precisam ser confirmadas ou desfeitas juntas. SQLite permite diversos leitores, mas a escrita requer cuidado com concorrência e duração da transação.

Nunca edite manualmente IDs e vínculos de um banco de uso real para “consertar a tela”. Reproduza o problema em cópia, escreva uma migração e teste a preservação. O arquivo de backup deve ser protegido como o banco original, porque contém as mesmas informações sensíveis.

## 21 Percursos completos para acompanhar no código

Cadastro e entrada: acesso.js envia email e senha → aplicacao.dispatch aplica limite → Caderno.autenticar valida e grava → resposta define cookie → load consulta contexto → API resolve usuário → organização e carteira são carregadas. O hash da senha e o token de sessão têm finalidades distintas.

Confirmação: piloto.js solicita → API limita → Piloto gera segredo e hash → correio entrega instruções → usuário envia token autenticado → confirmar_email valida conta e validade → banco registra confirmação e consome token. No modo local, a entrega é arquivo; em produção, depende de SMTP real.

Consulta: caseCard chama consultar → API verifica sessão e limite → Piloto exige e-mail se fonte real → Equipes reserva tarefa → fonte retorna → normalizar e diferencas processam → transação grava versão, referência, consulta e fila → frontend recarrega a carteira. Em erro, histórico e falha são registrados e o snapshot é preservado.

Providência: processo ou versão abre formulário → rotina.js envia responsáveis, título e contexto → Escritorio valida pertencimento → banco grava providência e evento → responsável inicia → evidencia resultado → revisor aprova → evento e revisão são incrementados. O banco e a API não dependem de um botão estar visível para proteger o fluxo.

Importação: arquivo CSV é lido no navegador → conteúdo é enviado para prévia → servidor verifica linhas e duplicados → pessoa revisa → confirmação revalida e processa → relatório distingue aceitas e rejeitadas. Uma mudança no conteúdo invalida a aprovação anterior da prévia.

## 22 Segurança e limites da versão

O projeto contém validação de entrada, hashes, sessões com expiração, autorização por escritório, proteção de origem, política de conteúdo e limites de algumas operações. Isso reduz riscos específicos; não equivale a certificação de segurança. A separação entre escritórios precisa ser testada em cada nova rota, inclusive arquivos e exportações.

A aplicação ainda não tem MFA, política executável de exclusão/retencão, armazenamento privado de documentos ou isolamento granular de cada processo entre membros do mesmo escritório. Membros têm acesso ao espaço da equipe conforme o desenho atual. Um escritório que precise de compartimentos confidenciais exige um modelo de autorização adicional.

Os backups automáticos atuais são locais e diários quando habilitados. Não há rotação criptografada externa pronta. A fila não inclui confirmação de entrega do provedor. O worker depende do processo estar rodando. Não existe homologação de dados reais, provedor, domínio e infraestrutura nesta revisão. Os testes de DOM não avaliam visualmente páginas.

O novo registro de solicitação de exclusão é uma entrada administrativa, não um mecanismo que elimina dados e backups. O novo parâmetro AMBAR_WORKER não é um sistema distribuído de eleição de líder. O JSON administrativo é exportação, não um restaurador. Essas distinções precisam aparecer na apresentação para não atribuir ao sistema garantias que ele ainda não oferece.

## 23 Testes e o que cada arquivo comprova

test_consulta.py testa entrada, extração HTML, comparação, falha de fonte e resposta do laboratório. test_acompanhamento.py testa a base pessoal e o servidor legado, incluindo sessão e isolamento inicial. Eles preservam o aprendizado e as regressões da primeira versão; não cobrem sozinhos a aplicação de equipes.

test_equipes.py testa CNJ, migração, convite, isolamento, conferência por versão, referência preservada, reserva concorrente, importação, fila e restauração. test_rotina.py testa executor e revisor, conflito de revisão, reprocessamento, envio fora de transação e revalidação de acesso. test_correio.py usa simulação de SMTP e verifica que aceite não significa entrega.

test_piloto.py testa o token de confirmação, conta correta, expiração, uso único, exigência de e-mail nos convites, reconstrução preservadora, duplicação por escritório, carteira com 1.005 registros, exportação sem segredos e solicitação sem apagamento automático. test_api_v2.py sobe FastAPI com banco temporário e faz chamadas HTTP reais para sessões, rotina e rotas de piloto.

tests/ui.test.cjs simula o DOM com jsdom e respostas de rede controladas, exercitando escritório, versões, rotina, importação, guia e conta. tests/percurso.test.cjs testa separação da apresentação e modos de acesso. tests/treino.test.cjs percorre os três cenários e recupera falha ao carregar a fonte. Nenhum desses arquivos executa um navegador visual real.

Execute Python com um ambiente que contenha requirements.txt e use python -m unittest discover -s backend -v. Execute npm ci quando necessário e depois npm run test:ui. Testes usam bancos temporários; não devem apontar para output/ambar.sqlite3 de uso pessoal. Registre resultado, data, ambiente e limites. Um teste com mock comprova sua regra sob respostas controladas, não o funcionamento atual do provedor externo.

Na revalidação de 05/11/2026, passaram 56 testes Python e 16 testes JavaScript. As chamadas HTTP da suíte são locais e SMTP é simulado. O ensaio externo do DataJud e a demonstração visual ficam em relatórios separados e não homologam uma carteira empresarial. A interface foi operada no navegador local, incluindo histórico, providências, fila e laboratório fictício. A preparação para publicação no GitHub inclui README e capturas públicas; o banco e as credenciais permanecem locais.

## 24 Como executar e investigar um problema

Use uma versão de Python compatível com as dependências e crie .venv com py -m venv .venv. Instale requirements.txt com o Python dessa pasta e inicie backend/aplicacao.py. No Windows, INICIAR.cmd automatiza esses comandos. Se a porta estiver ocupada, identifique o processo antes de encerrar qualquer aplicativo.

Abra http://127.0.0.1:8093/index.html para apresentação, /laboratorio.html?treino=1 para treino e /acompanhamento.html para área persistente. Ao configurar outra porta, ajuste AMBAR_PORT e AMBAR_ORIGIN coerentemente. Não misture localhost e 127.0.0.1 ao testar cookies e origem sem compreender as diferenças.

Se uma ação falhar, comece pela mensagem da tela e pelo identificador da requisição. Na aba Network do navegador, veja método, caminho, status e resposta. No terminal do servidor, procure o erro correspondente. Em um banco copiado, confirme se a conta, organização, versão ou revisão esperada realmente existe.

Erro 401 pede login. Erro 403 exige conferir permissão, origem ou e-mail confirmado. Erro 409 pede examinar duplicação, reserva ou revisão desatualizada. Erro 503 pode indicar fonte ou SMTP desativado. Resposta HTML onde o frontend espera JSON frequentemente indica caminho ou servidor errado. Não resolva isso silenciando a validação de resposta.

## 25 Trilha prática de estudo em dez sessões

Sessão 1: execute apresentação e treino e explique a diferença para a carteira persistente. Abra HTML e localize os IDs usados pelo JavaScript. Exercício: altere um texto de ajuda, recarregue e identifique qual arquivo o forneceu.

Sessão 2: estude funções, listas, dicionários, None, condições e exceções. Reescreva validar_entradas com mensagens próprias em arquivo de exercício. Teste uma lista vazia, um código repetido e um caso válido. Explique por que rejeitar entrada evita erros posteriores.

Sessão 3: execute extrair_e_comparar com um HTML pequeno. Retire a data e observe o resultado. Troque o texto da movimentação. Explique como o seletor CSS se relaciona com uma tag HTML e por que uma mudança de estrutura externa pode quebrar extração.

Sessão 4: leia fontes.py e crie duas listas fictícias de movimentos. Teste inclusão, repetição, remoção e mudança de grau. Explique quais alterações geram diferença e quais apenas mudam a ordem. Não consulte processos reais para fazer esse exercício.

Sessão 5: estude SQLite em banco temporário. Crie uma tabela simples, insira dados parametrizados e provoque uma exceção dentro de uma transação. Confirme rollback. Compare com o fluxo de gravação de uma versão.

Sessão 6: percorra cadastro, cookie e usuario. Explique hash de senha, salt, token de sessão e expiração com suas próprias palavras. Não exiba tokens reais na apresentação. Teste saída e tentativa de consulta sem sessão.

Sessão 7: crie duas contas e dois escritórios de teste. Confirme e-mails pelo canal local, crie convite, aceite e revogue. Tente acessar o escritório errado. Observe a diferença entre não mostrar um botão e receber uma recusa da API.

Sessão 8: crie uma providência, inicie execução, envie evidência e revise. Abra o mesmo registro em duas sessões de teste e provoque conflito de revisão. Explique por que a segunda gravação não pode substituir a primeira silenciosamente.

Sessão 9: estude filas, leases e retentativas. Faça uma fonte de teste falhar e preserve a referência. Leia o teste que grava no banco durante o mock de envio e explique por que isso detecta uma transação longa durante a rede.

Sessão 10: faça backup e abra uma cópia isolada. Demonstre o fluxo completo em cinco minutos e responda às perguntas seguintes sem ler. Só apresente como domínio pessoal as partes que conseguir explicar, reproduzir e alterar.

## 26 Perguntas para treinar a apresentação técnica

O que o projeto automatiza? Resposta esperada: consulta e comparação de informações, registro de versões e organização de trabalho; a interpretação e a conferência permanecem humanas.

Por que Python? Neste projeto, ele reúne HTTP com Requests, extração com Beautiful Soup, API com FastAPI e ferramentas de automação e persistência com bibliotecas adequadas ao aprendizado. Isso descreve a escolha local, não significa que Java seja incapaz de fazer o mesmo.

Onde entra Playwright? No roteiro de operação da interface. A consulta DataJud usa Requests e JSON. O laboratório HTML usa Requests e Beautiful Soup. Não atribua as três ferramentas a uma mesma função se o código não as chama naquele caminho.

Como evita misturar escritórios? A sessão identifica usuário; o serviço valida associação e papel usando org e caso antes de acessar ou alterar dados. Testes de acesso cruzado precisam acompanhar qualquer nova rota. Filtros no frontend não oferecem essa garantia.

Como sabe que mudou? Normaliza a resposta, organiza os movimentos e compara conteúdos por grau, incluindo inclusões, remoções e cadastro. Uma versão nova não herda automaticamente a conferência de outra transição. O aplicativo mostra evidências, não decide o significado jurídico.

O que acontece se a fonte cair? Registra a tentativa e o erro, preserva a referência válida e agenda nova tentativa limitada. A tela precisa deixar claro que os dados exibidos são da consulta anterior. O sistema não inventa uma atualização para manter aparência de funcionamento.

Já está pronto para um escritório usar sem acompanhamento? Ainda não. Há fluxo local e testes, mas faltam homologação de fonte e infraestrutura, validação visual, MFA e políticas efetivas de dados, entre outros itens do entregável. A proposta responsável é um piloto controlado após resolver os bloqueios aplicáveis.

## 27 Referências para aprofundamento

Python tutorial: https://docs.python.org/3/tutorial/ . Consulte funções, estruturas, classes, exceções e módulos enquanto acompanha os exemplos locais.

SQLite em Python: https://docs.python.org/3/library/sqlite3.html . Estude conexões, parâmetros e transações. FastAPI: https://fastapi.tiangolo.com/ . Estude requisições, dependências, validação e implantação. Requests: https://requests.readthedocs.io/en/latest/ . Estude Session, timeout, erros e JSON.

Beautiful Soup: https://www.crummy.com/software/BeautifulSoup/bs4/doc/ . Estude seletores e extração de texto. Playwright Python: https://playwright.dev/python/docs/intro . Estude locators, assertions, rastreamento e isolamento de contextos. DataJud: https://datajud-wiki.cnj.jus.br/api-publica/acesso/ . Confirme sempre as condições vigentes antes de habilitar uso real.

Segurança entre organizações: https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html . Use como referência de revisão; a existência de controles no projeto não significa conformidade completa com a orientação.

## 28 O que você deve conseguir explicar ao terminar

Você deve conseguir partir de um clique e indicar o evento JavaScript, a rota HTTP, a sessão, a autorização, o método Python, a consulta SQL, a fonte envolvida e a resposta apresentada. Também deve conseguir indicar o que foi testado, onde há simulação e quais limitações permanecem.

O próximo passo de aprendizado não é memorizar todo o repositório. É reproduzir um fluxo pequeno sem copiar, modificar uma regra, escrever um teste que falhe antes da correção e explicar por que a mudança preserva os outros percursos. Use o catálogo complementar para localizar cada símbolo e este manual para entender a relação entre eles.

## 29 Guia das rotas da aplicação atual

Todas as rotas abaixo começam por /api. As operações de escritório exigem sessão, e as administrativas exigem também papel apropriado. Um caminho aceito não significa que qualquer usuário pode executá-lo. GET usa parâmetros na URL; POST envia um objeto JSON. A lista descreve o contrato local atual e complementa o roteador genérico, que ainda não expõe contratos individuais completos em OpenAPI.

GET /saude: verifica acesso básico ao banco e devolve status, engine, version e indicação da flag de fonte. Não verifica o provedor externo. POST /consultar: recebe cases com id e previous para o laboratório HTML. É desativada em produção e não é a consulta persistente de um processo CNJ.

POST /conta/cadastro e POST /conta/login: recebem email e senha e definem cookie de sessão. POST /conta/sair revoga o cookie e a sessão apresentada. POST /conta/recuperar recebe email e responde de maneira genérica para não informar diretamente se a conta existe. POST /conta/redefinir recebe token e senha, consome a recuperação e revoga sessões.

GET /conta: devolve id, email e email_verificado da própria pessoa. POST /conta/verificacao/solicitar não recebe código; gera um novo e entrega pelo correio configurado. POST /conta/verificacao/confirmar recebe token e exige que ele pertença à conta autenticada. Não use query string para enviar senha ou token, porque URLs podem aparecer em histórico e logs.

GET /contexto: devolve os escritórios e papéis disponíveis. GET /me?org=ID: devolve identidade mínima após conferir acesso ao escritório. POST /organizacao/nome recebe org e nome e exige administração. GET /membros?org=ID lista integrantes. POST /membros/revogar recebe org e usuario e transfere responsabilidades na implementação atual.

POST /convites/criar recebe org e email, exige administrador com e-mail confirmado e devolve token destinado ao convidado. POST /convites/aceitar recebe token e exige conta com e-mail confirmado correspondente ao convite. O token de convite é uma capacidade temporária de ingresso; não deve ser divulgado publicamente.

GET /carteira recebe org, pagina, busca e filtro. filtro aceita all, pending, failed e archived. O resultado possui itens, total, pagina, por_pagina, resumo e demonstracao. Os indicadores do resumo são calculados sobre o escritório inteiro; total representa a seleção atual. A página contém até vinte processos.

GET /casos é compatibilidade legada e continua limitado. POST /casos recebe org, numero, tribunal e apelido para criar um processo. O frontend atual lê por /carteira, mas cria por /casos. POST /demonstracao recebe org e retorna o identificador do exemplo fictício; a criação de demonstração pela API é desativada em produção.

POST /casos/ID/consultar consulta uma referência persistente e devolve estado, dados, diferenca e versao_id. POST /casos/ID/avancar-demo altera a etapa fictícia e só funciona na demonstração fora de produção. GET /casos/ID/historico devolve tentativas. GET /casos/ID/detalhe devolve versões e conferências. POST /casos/ID/revisar recebe versao_id e observacao opcional para registrar leitura.

POST /casos/ID/alterar aceita organização interna do processo: apelido, etiquetas, observacoes, responsavel, arquivado e intervalo. Ele não altera dados no tribunal. Intervalo zero desativa agendamento; os demais precisam respeitar o mínimo. O servidor verifica associação do responsável e acesso ao processo.

GET /rotina recebe org, filtro, pagina e busca. filtro aceita minhas, equipe, atrasadas, revisar e concluidas. O resultado contém itens, total, pagina e resumo. POST /providencias recebe caso, versao opcional, titulo, descricao, responsavel, revisor, data_interna opcional e prioridade. A organização é obtida do próprio processo, não confiada a um campo arbitrário do visitante.

POST /providencias/ID/alterar recebe revisao e os campos de alteração, como estado, comentario e evidencia. Um número de revisão antigo recebe conflito. GET /providencias/ID/historico lista eventos autorizados. O formato interno dos estados usa a_fazer, em_andamento, aguardando, em_revisao e concluida; os textos da tela podem ser diferentes e mais legíveis.

POST /importar recebe org, csv e confirmar. Sem confirmação, devolve prévia. GET /exportar?org=ID gera CSV da carteira completa. GET /dados/exportar?org=ID exige administrador e devolve JSON com histórico relacionado. POST /dados/solicitar recebe org, tipo e motivo, registrando pedido de exclusao ou retencao sem executar eliminação.

GET /notificacoes?org=ID lista avisos recentes; GET /auditoria?org=ID exige administração e lista ações registradas. POST /preferencias recebe email booleano para adesão aos avisos. GET /operacao?org=ID é diagnóstico administrativo. POST /operacao/reprocessar recebe org, tipo e id e valida se a tarefa pode ser reprocessada.

## 30 Leitura comentada de pequenos trechos

### Parâmetros SQL e o formato da tupla

```python
with self.conexao() as db:
    linha = db.execute(
        'SELECT id,email FROM usuarios WHERE id=?',
        (usuario,)
    ).fetchone()
```

A primeira linha abre um contexto que fecha a conexão ao sair. A segunda inicia uma operação de leitura. O texto SQL define estrutura e seleção; o valor de usuario é entregue separadamente na tupla. O driver trata esse valor como dado. fetchone pede um resultado. Se não houver registro, linha será None e deve ser tratada antes de acessar linha['email'].

Trocar (usuario,) por uma interpolação de texto é uma mudança de segurança, não uma simplificação inocente. Trocar fetchone por fetchall também muda o contrato: o chamador passa a receber uma lista em vez de um registro. Ao modificar, procure todos os chamadores e atualize testes.

### Token de confirmação e armazenamento

```python
segredo = secrets.token_urlsafe(32)
digest = hashlib.sha256(segredo.encode()).hexdigest()
```

segredo é um valor aleatório para ser entregue ao destinatário pelo canal adequado. encode transforma texto em bytes. sha256 calcula um resumo desses bytes. hexdigest representa o resultado como texto hexadecimal para armazenamento. O banco recebe digest, não segredo. Ao confirmar, a aplicação calcula o hash do token apresentado e procura a correspondência válida.

O hash sozinho não implementa expiração: por isso o registro tem expira. Também não implementa uso único: por isso o registro é eliminado após sucesso. A vinculação a usuario impede que outra conta autenticada consuma o token. A mensagem local do ambiente de estudo contém o segredo porque simula a mensagem recebida; ela não deve ser publicada no repositório.

### Uma transição que pode falhar

```python
if dados.get('revisao') != p['revisao']:
    raise FalhaAPI(409, 'Esta providência mudou.')
```

dados representa a alteração enviada. p é o registro atual do banco. A condição compara a revisão apresentada com a atual. Quando são diferentes, raise interrompe antes da gravação. O frontend deve mostrar conflito e pedir atualização. Apenas repetir o POST automaticamente com a revisão nova pode esconder uma mudança que a pessoa ainda não leu.

### Um campo opcional bem definido

```python
valor_data = dados.get('data_interna', '')
data = date.fromisoformat(valor_data).isoformat() if valor_data else ''
```

A primeira linha lê o campo com alternativa vazia. A segunda usa expressão condicional: só interpreta uma data quando há valor. Se o formato recebido for inválido, a operação lança ValueError, tratado como entrada inadequada pelo método. Vazio é uma ausência aceita, e por isso o filtro de vencidas deve excluir explicitamente data_interna vazia.

### Resposta de API na interface

```javascript
const response = await fetch('/api/conta');
const data = await response.json();
if (!response.ok) throw new Error(data.error);
```

fetch devolve uma Promise. await aguarda seu resultado dentro de uma função async sem transformar o servidor em código local. A resposta HTTP e o corpo JSON são objetos diferentes: response contém status e cabeçalhos; data é o corpo interpretado. Uma resposta 403 pode ter JSON perfeitamente válido e ainda representar uma ação recusada. Por isso verificar apenas se json() funcionou é insuficiente.

O api real do projeto acrescenta timeout, verificação de tipo de conteúdo e tratamento de sessão. O run real cuida de estado ocupado e restauração dos controles. Este recorte mostra a lógica central, não deve substituir essas proteções.

### Uma fonte substituível para teste

```python
class FonteComFalha:
    def buscar(self, tribunal, numero):
        raise FalhaAPI(502, 'Fonte temporariamente indisponível.')
```

Esse objeto oferece a forma buscar esperada pelo serviço. Quando injetado em um teste de consulta, produz erro controlado sem acessar tribunal. Depois da chamada, o teste precisa verificar que o snapshot anterior permanece e que a falha foi registrada. Um teste que apenas espera uma exceção não comprova preservação dos dados.

## 31 Roteiro de demonstração e autoavaliação

Comece pela apresentação e diga qual problema será mostrado: acompanhar uma mudança e encaminhar um trabalho, com histórico. Abra o treino se a pessoa quiser aprender sem conta. Depois mostre o escritório autenticado e a identificação explícita da demonstração fictícia. Isso evita que alguém interprete o exemplo como consulta real a um processo.

Consulte a primeira referência, simule a novidade e consulte outra vez. Abra a linha do tempo. Mostre o que mudou e registre leitura da versão. Crie uma providência com título concreto e responsáveis. Inicie, descreva evidência e revise. Termine mostrando as contagens e a possibilidade de consultar o histórico depois de novo login.

Para explicar a implementação, abra primeiro a função de evento no frontend, depois a rota de dispatch, depois o método do serviço e por último o teste. Ao apresentar código, use um fluxo com começo e resultado observável; não percorra arquivos em ordem alfabética sem relacioná-los à ação.

Você está pronto para explicar uma parte quando consegue responder sem leitura: qual dado entra; quem pode executar; qual validação impede erro; o que muda no banco; qual resultado a tela recebe; qual teste comprova a regra; qual limitação permanece. Se alguma resposta depender apenas do nome de uma biblioteca, volte ao trecho e reproduza um exemplo menor.

Para a entrevista, descreva o desenvolvimento assistido com precisão e destaque o que você revisou, testou e consegue reproduzir. A confiança técnica vem de demonstrar um comportamento e explicar uma decisão, incluindo suas limitações, sem atribuir ao projeto integrações ou garantias que ele ainda não tem.
