"""Gera catálogo do código, manual HTML e PDF a partir das fontes revisadas.

Ferramenta de documentação, não importada pelo aplicativo. Execute com o runtime
de documentos; requer ReportLab. Nunca lê output, .env, .git ou node_modules.
"""
import ast
import html
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'documentacao'
OUT=DOCS/'para-leitura'

EXPLICACOES={
 'agendar_consulta':'Autoriza e persiste uma solicitação de atualização sem acessar o CNJ na mesma requisição. Preserva a espera existente, evita pedidos duplicados e registra autoria; Piloto exige confirmação de e-mail.',
 'post':'Auxiliar de teste que envia JSON para a API local com uma sessão Requests; não altera o transporte da aplicação.',
 'liberar':'Libera uma sincronização do cenário concorrente de teste para permitir que a consulta simulada prossiga.',
 'numero':'Gera um número de formato CNJ com dígitos verificadores para testes de validação. É dado sintético, não prova de existência de processo.',
 'confirmar':'Auxiliar de teste que solicita a confirmação, lê a caixa local temporária e consome o token da conta de teste.',
 'membro':'Auxiliar de teste que cria uma conta e associa o participante ao escritório do cenário.',
 'criar':'Auxiliar de teste que cria uma providência com participantes e dados controlados para validar suas transições.',
 'rede':'Simulação do canal externo de e-mail no teste. Serve para verificar a interação com o banco durante o envio sem transmissão externa.',
 'criar_app':'Monta a aplicação FastAPI com um serviço persistente, controles HTTP, rotas e arquivos estáticos. Permite banco temporário e ciclos desativados nos testes.',
 'agendador':'Executa uma ação síncrona em thread, registra falhas e aguarda o intervalo sem ocupar o laço assíncrono. É um ciclo local, não uma fila externa.',
 'lifespan':'Inicia e cancela os ciclos de consulta, correio e backup durante o tempo de vida da aplicação.',
 'limitar':'Conta tentativas por chave e janela no banco. Recusa excesso com erro 429 antes de executar a operação protegida.',
 'controles':'Verifica origem e tamanho da requisição e acrescenta cabeçalhos de segurança, cache e identificação. Não substitui autorização de domínio.',
 'falha':'Converte uma FalhaAPI em resposta JSON com o código HTTP da regra recusada.',
 'saude':'Executa uma consulta básica ao banco e informa o estado básico do serviço. Não comprova disponibilidade dos fornecedores.',
 'runtime':'Entrega a configuração JavaScript do laboratório quando atendido por FastAPI.',
 'dados':'Exige objeto JSON e tipo de conteúdo apropriado antes de encaminhar campos ao serviço.',
 'endpoint':'Recebe as rotas legadas, interpreta corpo e executa dispatch em thread para separar trabalho síncrono do laço HTTP.',
 'dispatch':'Escolhe a operação conforme caminho e método, aplica sessão e limites e chama o serviço de domínio. Contém contratos legados ainda não separados em rotas tipadas.',
 'conexao':'Abre SQLite com linhas nomeadas e chaves estrangeiras. O contexto confirma ou desfaz a transação e fecha a conexão.',
 'hash_senha':'Deriva hash scrypt com salt. O resultado permite validar uma senha sem armazená-la em texto.',
 'autenticar':'Valida credenciais, cadastra quando solicitado e cria sessão aleatória com hash e expiração. Login não equivale a e-mail confirmado.',
 'usuario':'Resolve um token em usuário somente quando a sessão existe e ainda é válida.',
 'sair':'Revoga a sessão correspondente ao token. Outras sessões só são eliminadas por uma ação que as revogue explicitamente.',
 'listar':'Lista processos no contrato da classe onde está definido. A versão de Equipes é legada e limitada; a interface atual usa Piloto.carteira.',
 'adicionar':'Valida entrada e grava processo no escopo autorizado. Na versão de equipes, associa escritório e responsável e recusa duplicação.',
 'caso':'Localiza o processo e verifica o escopo permitido ao usuário. É utilizado por outros métodos antes de trabalhar com IDs recebidos.',
 'historico':'Devolve tentativas de consulta do processo autorizado, incluindo falhas. Não se confunde com versões do conteúdo nem com eventos de providência.',
 'revisar':'Registra conferência. Na base antiga altera um marcador; em Equipes registra usuário e versão concreta para preservar a história da leitura.',
 'consultar':'Coordena a consulta e persistência. Em Equipes reserva, obtém fonte, compara e grava; Piloto acrescenta a confirmação de e-mail para fontes reais.',
 'buscar':'Obtém dados segundo o contrato da fonte. DataJud usa HTTP JSON; DataJudValidado acrescenta validação; Demonstracao retorna conteúdo fictício controlado.',
 '_org':'Encontra o primeiro escritório de uma conta ou cria o espaço pessoal e associa casos antigos ainda sem organização.',
 'org':'Verifica se o usuário pertence ao escritório e, quando solicitado, se é administrador. Não aceita um ID como prova de acesso.',
 'audit':'Grava ação, escritório, pessoa e instante para rastreabilidade operacional.',
 'contexto':'Lista escritórios e papéis da pessoa autenticada para seleção da área ativa.',
 'alterar':'Valida alterações organizacionais de processo e participante, atualiza arquivamento e periodicidade e ajusta sua tarefa agendada.',
 'demonstracao':'Retorna ou cria um processo explicitamente fictício para aprender o fluxo persistente sem consulta a tribunal.',
 'detalhe':'Reúne versões e conferências do processo autorizado para construir sua linha do tempo.',
 'membros':'Lista participantes e papéis de um escritório autorizado. Não fornece hashes de senha ou tokens.',
 'convidar':'Cria token temporário destinado a um e-mail e escritório. Na classe Piloto, exige confirmação do e-mail do administrador antes de delegar à base.',
 'aceitar':'Consome um convite válido para a conta de destino e cria a associação. Na classe Piloto, exige e-mail confirmado antes da operação.',
 'revogar':'Remove associação e reatribui responsabilidades na implementação atual de Escritorio. A implementação de Equipes é anterior à rotina.',
 'importar':'Lê e valida CSV, detecta duplicação e produz prévia ou processa as linhas válidas quando confirmado. O resultado é individual por linha.',
 'tick':'Ciclo legado que reúne processamento. A aplicação atual utiliza ciclos separados para reduzir dependência entre consulta, e-mail e backup.',
 'backup_tick':'Quando habilitado, prepara uma cópia consistente diária no diretório configurado. Não implementa armazenamento externo criptografado nem retenção automática.',
 'email_tick':'Processa avisos elegíveis. A implementação atual reserva e revalida em transações curtas e envia fora delas; a implementação de Equipes é legada.',
 'me':'Devolve identidade mínima e escritório autorizado para a rotina, sem fornecer dados de autenticação.',
 'carteira_exportavel':'Consulta metadados de toda a carteira para CSV, sem depender da página visível nem carregar os snapshots completos.',
 'participante':'Confirma que executor e revisor pertencem ao escritório da providência antes de aceitar a atribuição.',
 'texto':'Valida se um campo é texto e respeita limites de tamanho após remover espaços laterais.',
 'criar_providencia':'Valida processo, versão, participantes, prioridade e data interna opcional e grava a tarefa e seu primeiro evento.',
 'rotina':'Aplica filtros, busca e paginação SQL às providências e calcula contagens por responsabilidade e revisão.',
 'providencia':'Carrega a atividade e verifica o acesso ao escritório associado antes de devolver o registro.',
 'alterar_providencia':'Aplica permissão, revisão otimista e transições. Exige evidência para revisão/conclusão e comentário para reabertura.',
 'historico_providencia':'Retorna eventos da atividade autorizada, com identificação do participante e ordem histórica.',
 'consultas_tick':'Seleciona até três consultas vencidas e executa com paralelismo limitado. Cada consulta conserva sua reserva individual.',
 'executar':'Executa uma operação no contexto do chamador. No worker, chama a consulta elegível; no roteiro Playwright, conduz o percurso de navegador.',
 'operacao':'Entrega diagnóstico administrativo das consultas e mensagens recentes do escritório. Não é monitoramento externo de toda a infraestrutura.',
 'reprocessar':'Verifica administração e estado da fila antes de liberar uma nova tentativa; não confirma que a fonte ou o provedor voltou a funcionar.',
 'migrar_carteira':'Faz backup, reconstrói casos com unicidade por escritório, conserva colunas e IDs e verifica vínculos antes de confirmar. Usa rollback em falha.',
 'conta':'Fornece ID, e-mail e instante de verificação da própria conta. Não inclui dados de sessão ou senha.',
 'exigir_email':'Recusa operações protegidas enquanto a conta não possuir registro de confirmação.',
 'solicitar_verificacao':'Cria segredo aleatório de confirmação, persiste somente hash/expiração e entrega pelo canal configurado. Remove o token se o envio falhar.',
 'confirmar_email':'Verifica conta, hash e validade dentro da transação, registra confirmação e consome os tokens. O mesmo código não pode ser reutilizado.',
 'carteira':'Busca e filtra processos no banco, calcula total e retorna página de vinte itens com resumo da carteira inteira e referência à demonstração.',
 'resumo_diario':'Conta as providências atribuídas, vencidas e aguardando revisão do usuário no escritório autorizado.',
 'solicitar_dados':'Registra solicitação administrativa de retenção ou exclusão com justificativa. Não executa apagamento automático.',
 'exportar_escritorio':'Exporta dados relacionados do escritório para administração, omitindo credenciais, sessões e tokens. Não é um restaurador.',
 'validar_numero':'Remove pontuação, valida vinte dígitos, segmento/tribunal suportado e dígitos verificadores do CNJ. Não comprova existência do processo.',
 'serializar':'Produz JSON estável para comparar conteúdo sem depender da ordem das chaves ou dos espaços.',
 'versao':'Calcula SHA-256 do conteúdo serializado de forma estável para ajudar a identificar igualdade.',
 'normalizar':'Verifica o contrato da fonte, ordena registros e elimina movimentos exatamente repetidos. Não interpreta o mérito jurídico.',
 'diferencas':'Compara movimentos por grau e dados cadastrais para classificar primeiro registro, igualdade, inclusão, remoção/correção ou cadastro alterado.',
 'movimentos':'Transforma movimentos em mapa com identificação estável que inclui o grau, para comparação entre conjuntos.',
 'cadastro':'Separa os dados cadastrais de cada registro dos movimentos para comparar essas duas categorias independentemente.',
 'validar_entradas':'Exige de um a três casos de treino, códigos válidos não repetidos e texto anterior com tamanho limitado.',
 'extrair_e_comparar':'Usa Beautiful Soup e seletores conhecidos para extrair movimento/data e comparar com a referência anterior sem inventar registros ausentes.',
 'consultar_fonte':'Obtém HTML por Requests com timeout, valida HTTP e chama a extração; inclui evidência de ferramenta e hash da resposta no relatório.',
 'entregar':'Em desenvolvimento grava mensagem local. Em produção envia por SMTP com STARTTLS e distingue aceite de entrega confirmada.',
 'copiar':'Cria backup consistente SQLite em novo destino e verifica integridade da origem e cópia. Recusa sobrescrever um arquivo existente.',
 'criar_servidor':'Cria a instância HTTP do laboratório legado. Não monta a aplicação FastAPI completa de equipes.',
 'token':'Lê o cookie de sessão no servidor legado, sem validar a autorização por si só.',
 'acompanhamento':'Despacha as operações do caderno pessoal no servidor legado, anterior ao contrato atual de equipes.',
 'responder_acompanhamento':'Adapta erros e respostas do serviço pessoal para HTTP no servidor legado.',
 'json_response':'Escreve status, cabeçalhos e corpo JSON no protocolo HTTP do servidor legado.',
 'do_GET':'Trata uma requisição GET no servidor legado, servindo configuração, API pessoal ou arquivo conforme o caminho.',
 'do_POST':'Lê e valida a ação POST no laboratório legado e responde com resultado ou erro. A versão FastAPI usa outro caminho.',
 'main':'Ponto de entrada de terminal do módulo. Interpreta argumentos ou inicia o serviço específico; confira o arquivo antes de executar.',
 'passo':'Registra uma etapa de execução no relatório do roteiro de navegador.',
 'celula':'Protege valores do CSV que poderiam ser interpretados como fórmulas por um editor de planilhas.',
}

JS={
 'acompanharAtualizacoes':'Agenda leitura do estado local da fila, sem consultar o CNJ. Evita atualização durante edição, histórico aberto, aba oculta ou outra área; encerra quando não há pedido pendente.',
 'date':'Formata instantes Unix em segundos para leitura local. Um valor ausente é apresentado como ainda não consultado.',
 'movementDate':'Tenta formatar a data recebida da movimentação e conserva o valor original se não puder interpretá-lo.',
 'demoGuia':'Encontra o exemplo fictício não arquivado na página atual para orientar o percurso autenticado.',
 'botaoCaso':'Encontra a ação do caso fictício pelo rótulo para destacar o controle correto no guia.',
 'temNovidade':'Verifica no snapshot fictício a presença do movimento de demonstração que representa a etapa nova.',
 'el':'Localiza um elemento por ID para os componentes da área persistente.',
 'text':'Cria um elemento e escreve texto com textContent, sem interpretar conteúdo recebido como HTML.',
 'status':'Mostra mensagem de andamento, sucesso ou erro na região anunciada da página.',
 'signedIn':'Alterna áreas de entrada e trabalho. A autorização real continua na API.',
 'api':'Centraliza fetch, JSON, timeout e erros; identifica sessão expirada e registra caminhos bem-sucedidos para o guia.',
 'run':'Impede ações simultâneas, marca áreas como ocupadas e garante liberação e foco ao terminar, inclusive em erro.',
 'button':'Cria botão com estilo compartilhado e encaminha a ação pelo controle run.',
 'field':'Cria campo e rótulo em um formulário para manter estrutura consistente.',
 'load':'Carrega contexto, carteira paginada, membros, avisos e painéis do escritório selecionado.',
 'renderTeam':'Apresenta membros e ações de revogação conforme o papel recebido; a API ainda verifica permissão.',
 'renderMetrics':'Mostra indicadores calculados no banco inteiro e orienta o percurso de demonstração.',
 'render':'Atualiza a lista e seus controles. No laboratório usa estado local; na carteira apresenta a página obtida do servidor.',
 'caseCard':'Constrói a representação de um processo com fonte, referência, falha e ações disponíveis.',
 'review':'Registra leitura de uma versão concreta e atualiza os dados apresentados.',
 'editor':'Cria os controles de organização e arquivamento de um processo e envia alterações à API.',
 'history':'Carrega versões e tentativas, apresenta diferenças e oferece registro de leitura e providência.',
 'submit':'Converte os dados de um formulário em objeto e executa sua ação com controle de carregamento.',
 'iniciarAplicacao':'Inicializa a área de trabalho apenas uma vez depois que as dependências da página estão prontas.',
 'atualizarRotinaContexto':'Aplica papel e limpa referências da rotina quando a pessoa muda de escritório.',
 'trocarArea':'Alterna as áreas Processos e Minha rotina e os estados visuais dos controles.',
 'abrirProvidencia':'Preenche formulário com processo, versão opcional, responsáveis e contexto da ação.',
 'carregarRotina':'Consulta página/filtro de providências e atualiza resumo, lista e paginação.',
 'providenciaCard':'Cria a representação de uma atividade, transições permitidas, evidência e histórico.',
 'carregarOperacao':'Consulta diagnóstico administrativo e disponibiliza reprocessamento autorizado das filas.',
 'carregarPainelPiloto':'Atualiza estado da conta, resumo diário e visibilidade administrativa no escritório atual.',
 'salvarGuia':'Persiste somente passo e estado de atividade do tutorial no navegador.',
 'limparDestaqueGuia':'Remove indicações temporárias para não deixar controles destacados depois da orientação.',
 'pausarGuia':'Oculta a orientação e conserva ponto de retomada; não encerra sessão nem apaga processos.',
 'mostrarGuia':'Escolhe instrução e alvo da etapa atual e atualiza os controles do guia.',
 'avancarGuia':'Avança a orientação ou conclui o percurso removendo os destaques.',
 'iniciarGuia':'Inicia, retoma ou reinicia o tutorial autenticado conforme o estado da página.',
 'escapeHTML':'Escapa caracteres especiais antes de montar trechos controlados de HTML do laboratório.',
 'notify':'Apresenta aviso temporário no treino e cancela o temporizador anterior.',
 'showPage':'Alterna as seções do laboratório e seus controles de navegação.',
 'visibleCases':'Aplica busca e filtro sobre o pequeno catálogo fictício local.',
 'statusOf':'Produz o rótulo do estado do caso de treino, preservando a distinção entre falha, incompletude e conferência.',
 'renderCatalog':'Apresenta cenários fictícios e a opção de adicioná-los ao treino.',
 'log':'Acrescenta ação ao histórico da sessão do laboratório.',
 'renderHistory':'Desenha eventos do treino; esse histórico local não equivale às tabelas persistentes da equipe.',
 'moveCoachToBody':'Retira o guia de dentro de um diálogo antes de fechá-lo, evitando ocultação acidental.',
 'closeDialog':'Fecha o diálogo e coordena os eventos de avanço do tutorial.',
 'openDetail':'Apresenta comparação antes/depois de um caso do laboratório.',
 'carregarFonteTreino':'Carrega portal.html, verifica HTTP e extrai somente campos conhecidos. Mostra falha recuperável e ignora respostas antigas.',
 'configurarCasoGuiado':'Adapta as instruções ao cenário fictício escolhido, em vez de fixar apenas o caso cível.',
 'advance':'Avança uma etapa de treino quando ocorre o evento esperado.',
 'updateCoach':'Reposiciona e atualiza o guia contextual do laboratório.',
 'showMode':'Alterna cadastro e entrada e ajusta descrições, senha e ação do formulário.',
}

FILES={
 'frontend/index.html':'Apresentação pública e entrada para treino e acesso.',
 'frontend/acesso.html':'Estrutura do formulário de cadastro/login e orientação dos campos.',
 'frontend/laboratorio.html':'Estrutura das telas, diálogos e controles do treino fictício.',
 'frontend/portal.html':'Fonte HTML fictícia lida pelo laboratório; não é um portal judicial.',
 'frontend/acompanhamento.html':'Estrutura da aplicação autenticada de processos, providências e equipe.',
 'frontend/amber.css':'Apresentação do laboratório, estados e componentes históricos.',
 'frontend/acompanhamento.css':'Estilo da área persistente, campos, painéis, botões e responsividade.',
 'frontend/percurso.css':'Coerência visual de apresentação/acesso/treino e ajustes de diálogos e guia.',
 'frontend/runtime-config.js':'Configuração estática de disponibilidade da API. O servidor atual fornece versão dinâmica.',
 'frontend/assets/office.jpg':'Imagem de ambiente usada na apresentação, sem conteúdo de processo.',
 'frontend/assets/workspace.jpg':'Imagem ilustrativa de espaço de trabalho.',
 'frontend/assets/marca.svg':'Recurso vetorial histórico da marca; o cabeçalho atual utiliza composição tipográfica.',
 'package.json':'Comando de testes JavaScript e dependências de desenvolvimento.',
 'package-lock.json':'Resolução exata das dependências JavaScript.',
 'requirements.txt':'Dependências Python fixadas para reproduzir o ambiente da aplicação.',
 'Dockerfile':'Receita de contêiner Linux que ainda exige validação no destino, volume persistente e HTTPS externo.',
 '.dockerignore':'Exclusões do contexto de construção para evitar incluir arquivos desnecessários.',
 '.env.example':'Exemplo das variáveis de configuração; não contém credenciais nem é carregado automaticamente.',
 '.gitignore':'Exclusões de arquivos gerados e sensíveis no versionamento.',
 'vercel.json':'Configuração da publicação estática; não hospeda automaticamente esta API Python persistente.',
 'INICIAR.cmd':'Lançador local Windows que prepara .venv, instala dependências e inicia FastAPI.',
 'ferramentas/gerar_manual.py':'Ferramenta de documentação que produz este catálogo, HTML e PDF sem ler dados privados de output.',
 '.vscode/settings.json':'Oculta dependências e temporários no explorador do VS Code para facilitar a leitura. Não apaga esses arquivos.',
}


def catalogo():
    linhas=['# Catálogo do código do Caderno Âmbar','',
            'Gerado das fontes locais em 4 de novembro de 2026. As linhas são referências desta edição e podem mudar após novas alterações.',
            '', '## Como ler o catálogo','',
            'Cada símbolo contém localização, responsabilidade e chamadas diretas extraídas da árvore sintática ou da declaração JavaScript. Chamadas ajudam a navegar; não são prova de que todo ramo é executado em qualquer requisição. O manual principal explica os percursos completos.', '']
    for p in sorted((ROOT/'backend').glob('*.py')):
        rel=p.relative_to(ROOT).as_posix();src=p.read_text(encoding='utf-8-sig');tree=ast.parse(src)
        linhas += ['## '+rel,'', ast.get_docstring(tree) or 'Módulo de testes de comportamento do projeto.', '']
        def visitar(nodes, pais=[]):
            nonlocal linhas
            for node in nodes:
                if isinstance(node,ast.ClassDef):
                    bases=', '.join(ast.unparse(b) for b in node.bases) or 'object'
                    linhas.extend(['### '+'.'.join(pais+[node.name]),'',f'Linha {node.lineno}. Classe com base {bases}.',ast.get_docstring(node) or '', ''])
                    visitar(node.body,pais+[node.name])
                elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    nome='.'.join(pais+[node.name]);args=ast.unparse(node.args)
                    if node.name.startswith('test_'):
                        explica='Cenário automatizado: '+node.name[5:].replace('_',' ')+'. Leia os assert para identificar o resultado exigido e os mocks para distinguir dependências simuladas.'
                    elif node.name in ('setUp','setUpClass','tearDown','tearDownClass'):
                        explica='Prepara ou encerra os recursos temporários do teste. Observe a criação do banco, o servidor local e o fechamento para não contaminar execuções.'
                    elif node.name=='__init__':
                        explica={
                            'FalhaAPI':'Guarda o status HTTP e inicializa a mensagem da exceção para a camada de resposta.',
                            'Caderno':'Prepara o diretório e as tabelas originais de usuários, sessões, casos pessoais e consultas.',
                            'Equipes':'Executa a base pessoal, acrescenta tabelas e colunas de escritório e associa contas antigas sem apagar dados.',
                            'Escritorio':'Executa a base de equipes e cria providências, seus eventos e campos de reserva da fila de e-mail.',
                            'Piloto':'Executa a rotina, migra a unicidade da carteira e cria confirmação de e-mail e solicitações administrativas de dados.',
                            'Demonstracao':'Guarda a etapa fictícia que determina os movimentos retornados pelo exemplo.'
                        }.get(pais[-1] if pais else '', 'Inicializa o objeto com os parâmetros declarados; confira o corpo antes de criar uma instância.')
                    else:
                        explica=EXPLICACOES.get(node.name) or ast.get_docstring(node)
                        if not explica:
                            explica='Auxiliar local do fluxo de '+p.stem+'. Sua assinatura e as chamadas abaixo indicam os dados necessários; leia o corpo no ponto indicado e relacione-o ao método externo que o chama.'
                    chamadas=[]
                    def nome_chamada(expr):
                        if isinstance(expr,ast.Name):return expr.id
                        if isinstance(expr,ast.Attribute):return nome_chamada(expr.value)+'.'+expr.attr
                        if isinstance(expr,ast.Call):return nome_chamada(expr.func)
                        return type(expr).__name__
                    for ch in ast.walk(node):
                        if isinstance(ch,ast.Call):
                            func=nome_chamada(ch.func)
                            if func not in chamadas:chamadas.append(func)
                    linhas.extend(['### '+nome,'',f'Linhas {node.lineno} a {node.end_lineno}. Assinatura: {node.name}({args}).','',explica,''])
                    if chamadas:linhas += ['Chamadas para acompanhar no código: '+', '.join(chamadas[:14])+'.','']
                    # Nested helpers belong to the enclosing method; retain an entry too.
                    visitar([n for n in node.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))],pais+[node.name])
        visitar(tree.body)
    for p in sorted((ROOT/'frontend').glob('*.js')):
        rel=p.relative_to(ROOT).as_posix();src=p.read_text(encoding='utf-8-sig')
        linhas+=['## '+rel,'', 'JavaScript executado no navegador. Eventos de formulário e clique também aparecem no nível superior do arquivo; não são métodos Python.', '']
        matches=list(re.finditer(r'\b(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',src))
        for m in matches:
            nome=m.group(1);line=src.count('\n',0,m.start())+1
            explica=JS.get(nome,'Auxiliar do módulo '+p.stem+'. Siga as entradas e as alterações de estado no corpo antes de modificar sua chamada.')
            linhas+=['### '+nome,'',f'Linha {line}. Parâmetros: {m.group(2) or "nenhum"}.','',explica,'']
        for m in re.finditer(r'^const\s+([\w$]+)\s*=\s*(?:async\s+)?(?:\(([^)]*)\)|([\w$]+))\s*=>',src,re.M):
            nome=m.group(1);line=src.count('\n',0,m.start())+1
            linhas+=['### '+nome,'',f'Linha {line}. Função de expressão com parâmetros {m.group(2) or m.group(3) or "nenhum"}.','',JS.get(nome,'Auxiliar de transformação ou seleção do módulo. A expressão devolve seu valor ao chamador; siga o corpo no ponto indicado.'),'']
        eventos=re.findall(r"(?:submit\('([^']+)'|(?:el|get|\$)\('([^']+)'\)\.(on\w+))",src)
        if eventos:linhas+=['Eventos e formulários vinculados: '+', '.join(a or b for a,b,_ in eventos)+'.','']
        if not matches:linhas+=['Este arquivo configura valores ou utiliza callbacks/funções de expressão. Leia o módulo juntamente com o capítulo correspondente do manual.','']
    linhas+=['## Arquivos de estrutura configuração recursos e documentação','']
    for rel,desc in FILES.items():linhas += ['### '+rel,'',desc,'']
    for p in sorted([ROOT/'README.md', *DOCS.glob('*.md')]):
        if p.name in ('mapa-do-codigo.md','manual-completo.md'):continue
        title=next((l.lstrip('# ') for l in p.read_text(encoding='utf-8-sig').splitlines() if l.startswith('# ')),p.stem)
        linhas+=['### '+p.relative_to(ROOT).as_posix(),'','Documento de referência: '+title+'. Consulte a data e o escopo; registros antigos não substituem o estado atual em documentacao/estado-atual-do-projeto.md.','']
    for p in sorted((ROOT/'tests').glob('*.cjs')):
        titulos=re.findall(r"test\('([^']+)'",p.read_text(encoding='utf-8'))
        linhas+=['### '+p.relative_to(ROOT).as_posix(),'','Testes JavaScript com jsdom. Cenários declarados: '+ '; '.join(titulos)+'. Respostas de rede são simuladas; não é inspeção visual.','']
    linhas+=['## Diretórios que não são fonte para estudar linha por linha','',
             '.git guarda metadados de versionamento. node_modules e .venv são dependências instaladas. __pycache__ guarda bytecode gerado. output guarda dados privados e artefatos de execução. Este gerador não copia o conteúdo desses diretórios para o manual. O banco, backups e mensagens devem ser protegidos, não anexados a uma apresentação pública.','']
    return '\n'.join(linhas)


def renderizar(texto):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Preformatted, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    OUT.mkdir(parents=True,exist_ok=True)
    fonts=Path('C:/Windows/Fonts')
    for name,file in [('Arial','arial.ttf'),('ArialBold','arialbd.ttf'),('Consolas','consola.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='ArialBold',italic='Arial',boldItalic='ArialBold')
    styles=getSampleStyleSheet()
    for k in ['Normal','Heading1','Heading2','Heading3','Title']:
        styles[k].fontName='ArialBold' if k!='Normal' else 'Arial'
        styles[k].textColor=colors.HexColor('#182a22') if k=='Normal' else colors.black
    styles['Normal'].fontSize=10.4;styles['Normal'].leading=15.8;styles['Normal'].spaceAfter=8
    styles['Normal'].widows=2;styles['Normal'].orphans=2
    styles['Title'].fontSize=27;styles['Title'].leading=33;styles['Title'].spaceAfter=18
    styles['Heading1'].fontSize=18;styles['Heading1'].leading=24;styles['Heading1'].spaceBefore=15;styles['Heading1'].spaceAfter=11
    styles['Heading2'].fontSize=13;styles['Heading2'].leading=18;styles['Heading2'].spaceBefore=11;styles['Heading2'].spaceAfter=6
    styles['Heading3'].fontSize=11;styles['Heading3'].leading=15;styles['Heading3'].spaceBefore=8
    codeStyle=ParagraphStyle('Code',fontName='Consolas',fontSize=8.6,leading=12,spaceAfter=12,textColor=colors.HexColor('#224438'))
    pdf=OUT/'Caderno-Ambar-Manual-Completo.pdf'
    class ManualPDF(BaseDocTemplate):
        def afterFlowable(self,flowable):
            if isinstance(flowable,Paragraph) and flowable.style.name in ('Title','Heading1','Heading2'):
                level={'Title':0,'Heading1':1,'Heading2':2}[flowable.style.name]
                key='bookmark-'+str(getattr(self,'bookmark_count',0))
                self.bookmark_count=getattr(self,'bookmark_count',0)+1
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(flowable.getPlainText(),key,level=level,closed=True)
    doc=ManualPDF(str(pdf),pagesize=A4,leftMargin=51,rightMargin=51,topMargin=57,bottomMargin=52,title='Caderno Âmbar por dentro',author='Caderno Âmbar')
    def pagina(c,doc):
        c.saveState();c.setFont('Arial',8);c.setFillColor(colors.HexColor('#496456'))
        c.drawString(51,A4[1]-31,'CADERNO ÂMBAR  /  MANUAL DE ESTUDO')
        c.setStrokeColor(colors.HexColor('#b7aa91'));c.line(51,39,A4[0]-51,39)
        c.drawString(51,26,'Organização revisada 04 nov 2026  ·  Consulte os limites de validação')
        c.drawRightString(A4[0]-51,26,str(doc.page));c.restoreState()
    doc.addPageTemplates(PageTemplate(id='Normal',frames=[Frame(doc.leftMargin,doc.bottomMargin,doc.width,doc.height,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=pagina))
    blocos=[];htmlparts=[];par=[];codes=[];inc=False;outline=[]
    def safe(s):
        return html.escape(s).replace('→','-&gt;').replace('—','-').replace('–','-')
    def flush():
        if par:
            t=' '.join(par);blocos.append(Paragraph(safe(t),styles['Normal']));htmlparts.append('<p>'+html.escape(t)+'</p>');par.clear()
    for l in texto.splitlines():
        if l.startswith('```'):
            flush()
            if inc:
                blocos.append(Preformatted('\n'.join(codes),codeStyle));htmlparts.append('<pre>'+html.escape('\n'.join(codes))+'</pre>');codes=[]
            inc=not inc;continue
        if inc:codes.append(l);continue
        if l.startswith('#'):
            flush();level=len(l)-len(l.lstrip('#'));t=l[level:].strip()
            if level==1:
                if blocos:blocos.append(PageBreak())
                blocos.append(Paragraph(safe(t),styles['Title']))
            else:
                if level==2:blocos.append(Spacer(1,8))
                # Paths and signatures remain readable; permit wraps at slashes.
                display=safe(t).replace('/','/<wbr/>') if '/' in t else safe(t)
                blocos.append(Paragraph(display,styles['Heading1' if level==2 else 'Heading2']))
            ident='sec-'+str(len(outline));outline.append((level,t,ident))
            htmlparts.append(f'<h{min(level,3)} id="{ident}">'+html.escape(t)+f'</h{min(level,3)}>')
        elif not l.strip():flush()
        elif l.startswith('- '):
            flush();blocos.append(Paragraph('• '+safe(l[2:]),styles['Normal']));htmlparts.append('<p class="item">'+html.escape(l)+'</p>')
        else:par.append(l)
    flush();doc.build(blocos)
    nav=''.join(f'<a href="#{i}">'+html.escape(t)+'</a>' for level,t,i in outline if level<=2)
    css='''body{margin:0;background:#f3f0e8;color:#1f352b;font:17px/1.8 Arial,sans-serif}main{max-width:900px;margin:auto;padding:60px 35px;background:#fffdf7}h1{font-size:38px;line-height:1.2;margin-top:40px}h2{margin-top:56px;font-size:26px;line-height:1.35}h3{margin-top:30px;overflow-wrap:anywhere}p{margin:12px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#e9eee7;padding:20px;font-size:14px}nav{max-width:900px;margin:auto;padding:30px 35px;columns:2}nav a{display:block;color:#224438;font-size:14px;margin:5px 0}a:focus{outline:3px solid #a77b42}@media(max-width:650px){nav{columns:1}main{padding:25px 20px}h1{font-size:30px}}@media print{nav{display:none}main{max-width:none;padding:0}h2,h3{break-after:avoid}}'''
    (OUT/'Caderno-Ambar-Manual-Completo.html').write_text('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Caderno Âmbar por dentro</title><style>'+css+'</style><nav aria-label="Índice do manual">'+nav+'</nav><main>'+''.join(htmlparts)+'</main></html>',encoding='utf-8')
    print('PDF e HTML criados em',OUT)


if __name__=='__main__':
    mapa=catalogo();(DOCS/'mapa-do-codigo.md').write_text(mapa,encoding='utf-8')
    manual=(DOCS/'manual-completo.md').read_text(encoding='utf-8')
    texto=manual+'\n\n'+mapa+'\n\n'+(DOCS/'estado-atual-do-projeto.md').read_text(encoding='utf-8')
    renderizar(texto)
