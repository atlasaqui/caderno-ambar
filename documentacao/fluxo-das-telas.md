# Percurso do usuário — Caderno Âmbar

## Correção do diálogo de fonte

O iframe do portal de treino era bloqueado pela política `frame-ancestors 'none'` da aplicação. O laboratório agora busca a mesma fonte por HTTP e apresenta os campos em cartões de texto dentro do diálogo, sem incorporar outra página nem relaxar a política de segurança. Há estado de carregamento, mensagem de falha, nova tentativa e link para abrir o portal separadamente.

O caso selecionado fica destacado. O guia só avança quando a fonte carrega; o botão de retorno permanece acessível. A caixa de orientação foi compactada e posicionada antes da ação de continuidade. O seletor inicial ganhou rótulo em bloco, largura completa e área de interação maior. Validação: 12 testes de comportamento em DOM simulado aprovados, incluindo os três casos e falha seguida de nova tentativa. A inspeção visual em navegador continua pendente pela configuração de acesso local.

## Onde começar

Abra **http://127.0.0.1:8093/index.html**. A página inicial apresenta o problema, o resultado esperado e quatro etapas de uso. Não contém cadastro, listagem operacional nem aviso de implementação Python.

1. **Conhecer:** `index.html` explica acompanhamento → comparação → providência.
2. **Treinar sem conta:** `laboratorio.html?treino=1` abre a escolha de um exemplo e o início do guia.
3. **Criar acesso ou entrar:** `acesso.html` separa os dois modos, explica os campos e não armazena a senha no navegador.
4. **Usar com orientação:** `acompanhamento.html?guia=1` abre o guia dentro da área de trabalho depois da autenticação.

## Exemplos do primeiro treino

- Cível: audiência fictícia agendada após o registro inicial.
- Contratual: informação sobre uma nova versão de contrato; o treino não revisa cláusulas.
- Trabalhista: documento recebido com data ausente; marcar leitura não resolve a informação incompleta.

O usuário escolhe o exemplo no diálogo inicial. O guia adapta código, seleção, comparação, busca e explicações à escolha. Os três exemplos continuam disponíveis para exploração livre. O botão de continuidade leva à página de acesso.

O laboratório permanece sem persistência de carteira e usa dados fictícios. O guia informa quando reiniciar o treino limpa a lista temporária. Ele não limpa acompanhamentos da área autenticada.

## Guia dentro da aplicação

**Aprender a usar** abre ou retoma 15 etapas: escritório, demonstração, referência, simulação, nova consulta, linha do tempo, leitura, criação de providência, preenchimento, Minha rotina, equipe, importação, saúde das filas, avisos e encerramento.

O guia destaca o controle e explica o motivo da ação. Etapas operacionais avançam após a conclusão das solicitações e atualização da interface. Explicações de equipe, importação e avisos permitem continuar sem enviar convites nem dados reais. Uma ação já realizada é identificada e pode ser reconhecida sem repeti-la.

Pausar mantém os dados e guarda somente o número do passo e o estado do guia no armazenamento local. Recomeçar reinicia a orientação, sem apagar processos, contas ou providências. Saída da conta pausa a orientação. Não são persistidos senha, token, conteúdo processual ou dados do formulário no progresso do guia.

## Implementação para estudar

- `frontend/index.html`: apresentação pública.
- `frontend/laboratorio.html` e `frontend/amber.js`: treino original separado, agora com escolha de cenário.
- `frontend/acesso.html` e `frontend/acesso.js`: tela de acesso com explicação contextual dos campos.
- `frontend/guia.js`: estados, alvos, condições de avanço, progresso e pausa da área autenticada.
- `frontend/percurso.css`: apresentação, acesso e continuidade visual.
- `frontend/acompanhamento.js`: emite o evento `ambar:acao` depois de concluir uma operação. O evento informa apenas os caminhos bem-sucedidos; não contém senhas ou corpos de requisição.
- `tests/percurso.test.cjs`, `tests/treino.test.cjs` e `tests/ui.test.cjs`: separação de páginas, modos de acesso, três exemplos e percurso do guia.

O script Playwright original foi ajustado para abrir `laboratorio.html`; ele não foi executado nesta revisão, pois o navegador local está desativado nas configurações do ambiente. Os testes de DOM usam respostas simuladas e verificam comportamento, não aparência ou layout real.

## Limites de aprendizado e validação

O guia não força completar uma tarefa profissional, convidar pessoas ou importar dados. A prática da consulta usa a demonstração; execução e revisão de providências são explicadas e permanecem disponíveis para treino dentro da aplicação. Permissões reais do usuário continuam sendo aplicadas pelo backend.

Ainda é necessária a inspeção visual em navegador, com teclado e telas menores, quando o acesso estiver habilitado. Esse limite não deve ser confundido com aprovação visual do fluxo.
