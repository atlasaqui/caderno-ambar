# Revisão de experiência — 03/11/2026

## Refinamento após os prints

Retirado o ícone de documento da marca e do favicon. A composição usa assinatura tipográfica, título de carteira mais direto e ritmo editorial. Escritório e ações têm alinhamento comum; métricas usam cartões; cadastro individual e importação ficam separados, com importação recolhida por padrão. Exportação passou à barra de busca, fica desativada na carteira vazia e preferências de e-mail têm um grupo com espaçamento próprio.

CSS e JavaScript receberam identificador de versão. O servidor local envia `Cache-Control: no-store` para HTML/CSS/JS em desenvolvimento. A conferência HTTP confirmou que os três recursos entregues correspondem aos arquivos locais. O serviço foi reiniciado na porta 8093 para aplicar a política de cache.

Validação adicional: quatro testes de interface em DOM simulado e três testes HTTP da API aprovados. A conferência visual em navegador continua pendente pela configuração já registrada abaixo.

## Problemas corrigidos

A tela operacional importava o CSS da landing page, incluindo regras globais de navegação e uma classe de métricas usada com estrutura diferente. O painel passou a usar uma folha independente e mantém a paleta marfim, verde e âmbar.

O resumo foi dividido em três cartões. Cabeçalho, escritório, demonstração, busca, lista, histórico e equipe têm hierarquia própria. O tamanho do título diminui depois do login. Formulários têm larguras, respiro, foco visível e disposição responsiva. A linha do tempo separa novidades de conteúdo completo e diagnóstico.

## Comportamento revisado

- Entrar sem sessão apresenta o formulário sem erro de autenticação desnecessário.
- Operações bloqueiam temporariamente os controles para impedir cliques concorrentes.
- A demonstração orienta consulta inicial, simulação, nova consulta e conferência.
- Histórico aparece como ação depois da primeira versão. A simulação aparece após a referência e deixa de ser oferecida depois de aplicada.
- Conferir registra a versão que foi apresentada. A ação deixa de aparecer como pendência depois da leitura.
- Trocar escritório limpa busca, filtros, prévia CSV, histórico e token de convite da área anterior.
- Formulários administrativos ficam ocultos para membros; o backend também aplica autorização.
- Importação exige prévia e invalida a confirmação se o CSV mudar.
- Paginação só aparece quando necessária e desativa extremidades.
- Exportação permanece na página e comunica falhas sem navegar para uma resposta JSON.
- O histórico direciona o foco ao título depois do carregamento e pode ser fechado.

## Evidência

25 testes Python passaram, incluindo chamadas HTTP reais locais e persistência. Três testes JavaScript em jsdom passaram: fluxo demonstrativo completo; troca de escritório/permissões visuais; prévia de importação. Sintaxe JavaScript e `git diff --check` foram verificados.

Esses testes de interface usam respostas simuladas e não são screenshots nem testes de layout. O navegador local retornou `Local browser use is disabled in Work settings`, impedindo a inspeção visual e os cliques reais solicitados. Não foi usado outro navegador para contornar a configuração. A conferência visual desktop/mobile permanece necessária quando o acesso for habilitado.

## Reproduzir

Execute `INICIAR.cmd` e abra http://127.0.0.1:8093/acompanhamento.html . Atualize a página para carregar os novos arquivos. Entre na conta, selecione o escritório e siga o bloco da demonstração.

Para repetir os testes de comportamento, execute `npm ci --ignore-scripts` e `npm run test:ui`. Para a API, execute `.venv\Scripts\python.exe -m unittest discover -s backend -v`.
