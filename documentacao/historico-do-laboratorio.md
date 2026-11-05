# Caderno Âmbar

> Documento histórico da primeira versão. Para executar o aplicativo atual, leia [o README da raiz](../README.md). Todos os guias estão no [índice da documentação](README.md). As instruções antigas abaixo foram preservadas para estudo da evolução.

**Manual completo de estudo:** [Python e funcionamento do projeto](manual-completo.md), [catálogo de arquivos e funções](mapa-do-codigo.md) e [estado do piloto](estado-atual-do-projeto.md). A edição PDF e a versão HTML ficam em `documentacao/para-leitura` após executar o gerador de documentação com ReportLab. A aplicação atual usa `Piloto`, sobre a base de equipes; os guias anteriores descrevem a evolução.

**Entrada do produto:** http://127.0.0.1:8093/index.html . Apresentação, treino sem conta, acesso e área de trabalho foram separados. Veja [fluxo-das-telas.md](fluxo-das-telas.md) para o fluxo e o guia interativo.

**Versão atual de equipes:** execute `INICIAR.cmd` e abra http://127.0.0.1:8093/acompanhamento.html . Consulte [guia-de-equipes.md](guia-de-equipes.md) para arquitetura, configuração e estudo, e [testes-e-validacao.md](testes-e-validacao.md) para evidências e pendências. O restante deste README descreve o laboratório original.

Laboratório de acompanhamento de casos fictícios. Nome de trabalho para este projeto independente; sem vínculo com o QCA. Identidade de folhas sobrepostas, marfim, verde floresta e detalhes âmbar compartilhada pela apresentação e pela área de trabalho.

## Para que serve

Guardar uma informação sobre um caso, consultar a fonte e destacar o que mudou. A pessoa escolhe o que acompanhar, lê a comparação e registra sua conferência. O site não altera processos judiciais.

## Executar localmente

```powershell
python -m http.server 8086 --bind 127.0.0.1 --directory dist
```

Abra http://127.0.0.1:8086. Não abra index.html diretamente: a consulta precisa de HTTP. Não há etapa de build. Fontes do Google Fonts com alternativas de sistema. Fotografias locais.

## Tutorial ativo

Clique em “Aprender usando” e depois “Iniciar treino com a lista vazia”. Esse comando reinicia a sessão. O guia avança somente por eventos das funções reais, sem botão “Próximo”, cliques simulados ou temporizadores de execução.

1. Abra Adicionar caso.
2. Adicione CIV-001.
3. Marque a caixa de seleção.
4. Abra a fonte de treino.
5. Volte à lista.
6. Consulte o caso selecionado.
7. Abra Ver mudança.
8. Marque como conferido.
9. Volte à lista.
10. Busque CIV-001.
11. Filtre Com novidade.
12. Exporte a lista.
13. Abra Histórico.
14. Abra Como usar.

Esperado: “Aguardando agendamento” muda para “Audiência agendada para 22/10 às 14h”. A conferência reduz a contagem de pendências de leitura. O CSV exporta somente a lista visível. O histórico registra consulta, comparação, conferência e exportação.

## Comportamento e limites

- Começa vazio: não há seis casos prontos apresentados como trabalho executado.
- O catálogo contém três exemplos; cada caso só pode ser adicionado uma vez.
- Seleção determina quais casos serão consultados; busca e filtros determinam quais serão exportados.
- `fetch('portal.html')` faz uma requisição HTTP real. `DOMParser` interpreta campos de cada elemento `data-case`. O dado encontrado é comparado com o registro da sessão.
- HTTP inválido, timeout de 12 segundos ou campos ausentes não geram sucesso. A última informação conhecida é preservada. A consulta pode ser repetida.
- Uma segunda consulta à mesma fonte retorna “sem mudança”, sem criar registros duplicados.
- A data ausente em TRA-003 exige conferência humana; marcar como conferido registra a leitura e não preenche o dado ausente.
- Toda a fonte é fictícia e estática. Não há integração com tribunais, agendamento, login ou persistência. Recarregar limpa a lista e o histórico.
- A demonstração pública estática usa JavaScript. O laboratório local executa Python com Requests e Beautiful Soup; a rotina Playwright opera essa interface e verifica o resultado.

## Estrutura

- `frontend/index.html`: apresentação e aplicação sob a mesma navegação e identidade.
- `frontend/amber.css`: sistema visual responsivo e tutorial com destaque.
- `frontend/amber.js`: catálogo, estado, consulta, comparação, revisão, CSV e guia por eventos.
- `frontend/portal.html`: fonte de treinamento visível, também usada pela consulta.
- `frontend/assets/marca.svg`: marca vetorial própria do estudo.

## Fotografias

Ambientes ilustrativos do Unsplash. Não representam o escritório QCA.

- https://images.unsplash.com/photo-1497366811353-6870744d04b2
- https://images.unsplash.com/photo-1497366754035-f200968a6e72

## Laboratório Python implementado

O guia completo, com explicações e exercícios, está em [estudo-do-laboratorio.md](estudo-do-laboratorio.md).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe backend\rpa_navegador.py --visivel
```

O robô abre seu próprio servidor local e executa o fluxo completo. Sem `--visivel`, roda sem mostrar a janela. Evidências ficam em `output/rpa`: relatório JSON, capturas, CSV e trace. A pasta é ignorada pelo Git.

Para usar o painel manualmente com Python, execute `.\.venv\Scripts\python.exe backend\servidor.py` e abra http://127.0.0.1:8092. O botão Consultar chama a API Python, que busca a fonte com Requests, extrai com Beautiful Soup e compara os registros. A fonte da API é fixa no servidor; o navegador não pode escolher URLs arbitrárias.

Para executar apenas a consulta com esse servidor aberto: `.\.venv\Scripts\python.exe backend\consulta.py`.

Verificações: `.\.venv\Scripts\python.exe -m unittest discover -s backend -p "test_*.py" -v`. Os sete testes cobrem HTTP, comparação sem mudança, campos ausentes, códigos inválidos, HTTP 404, JSON inválido e configuração do modo Python. Playwright verifica também a API Python, o antes/depois, a conferência e o conteúdo do CSV baixado.

A execução foi verificada com Python 3.12, Requests 2.34.2, Beautiful Soup 4.15.0 e Playwright 1.64.0. As versões exatas estão em requirements.txt. O código foi implementado com apoio de IA; use os exercícios para praticar antes de apresentar familiaridade pessoal com as ferramentas. A hospedagem estática pública não executa esse backend.
# Atualização local — 03/11/2026

Esta etapa inicial foi sucedida pela versão de equipes na porta 8093. As instruções atuais estão em [guia-de-equipes.md](guia-de-equipes.md). O laboratório original e os dados fictícios foram preservados; esta evolução não foi publicada na Vercel.
