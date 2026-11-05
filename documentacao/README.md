# Documentação do Caderno Âmbar

Todos os documentos de estudo, funcionamento e evolução estão reunidos nesta pasta. Comece pelos três primeiros; os guias específicos ajudam quando você precisar se aprofundar.

## Ordem recomendada

1. [Manual completo](manual-completo.md): Python para quem vem de Java, arquitetura, funcionamento, arquivos, API e exercícios.
2. [Mapa do código](mapa-do-codigo.md): localização e responsabilidade de classes e funções.
3. [Estado atual do projeto](estado-atual-do-projeto.md): implementações, limites e pendências do piloto.
4. [Fluxo das telas](fluxo-das-telas.md): apresentação, treino, acesso e área de trabalho.
5. [Guia de providências](guia-de-providencias.md): responsáveis, revisão, estados, evidências e filas.
6. [Guia de equipes](guia-de-equipes.md): estrutura do servidor, banco, escritórios e configuração da versão de equipes.
7. [Testes e validação](testes-e-validacao.md): o que foi efetivamente testado e o que ainda precisa de verificação.
8. [Revisão da interface](revisao-da-interface.md): ajustes anteriores de experiência e layout.
9. [Teste real do DataJud](teste-real-datajud.md): conta de estudo, consulta pública, resultados e falhas externas observadas.

## Para ler como um livro

- [Manual em PDF](para-leitura/Caderno-Ambar-Manual-Completo.pdf).
- [Manual em HTML com índice navegável](para-leitura/Caderno-Ambar-Manual-Completo.html).

Essas versões incluem o manual principal, o catálogo do código e o estado do piloto. As fontes editáveis são os arquivos Markdown desta pasta. O gerador fica em `ferramentas/gerar_manual.py` e exige ReportLab no ambiente usado para documentação.

## Guias da primeira versão

Estes arquivos explicam a evolução e os exercícios iniciais. Para executar o aplicativo atual, siga o README da raiz.

- [Primeiro guia de estudo](primeiro-guia-de-estudo.md): caderno pessoal anterior à versão de equipes.
- [Estudo do laboratório](estudo-do-laboratorio.md): Requests, Beautiful Soup e roteiro Playwright com fonte fictícia.
- [Histórico do laboratório](historico-do-laboratorio.md): README original, preservado como histórico.

## Organização das pastas

Antes, a interface ficava em `dist`, o servidor em `laboratorio` e o gerador em `tools`. Agora eles ficam em `frontend`, `backend` e `ferramentas`. As referências e comandos foram atualizados. `laboratorio.html` continua sendo o nome da página de treino; ela fica dentro de `frontend`.

Os comandos apresentados nos documentos devem ser executados na raiz do projeto. Caminhos como `backend/aplicacao.py` partem dessa raiz, não desta pasta de documentação. O nome da disciplina e os limites de implantação continuam descritos conforme o escopo de cada documento.

## Revisão DataJud de 04/11

- [Prompt executado](prompt-correcao-datajud.md).
- [Diagnóstico, correções e resultado real](diagnostico-e-correcao-datajud.md).
- [Fila de atualizações e funcionamento durante indisponibilidade](fila-atualizacoes-datajud.md).
- [Causa confirmada da recusa e comparação com o exemplo oficial](causa-confirmada-datajud.md).
