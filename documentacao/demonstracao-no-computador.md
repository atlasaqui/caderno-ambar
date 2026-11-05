# Demonstração no computador - 04/11/2026

Após o login realizado pelo usuário, o aplicativo foi operado no navegador visível, na conta técnica do escritório de estudo.

## Resultado observado na tela

- O caso real TJPE está separado da demonstração fictícia.
- Uma nova consulta acionada na interface às 13h38 recebeu recusa temporária do DataJud, com espera de 90 segundos. Não foi considerada sucesso.
- A versão real 3, recebida às 13h13, continuou acessível com 35 movimentos. A linha do tempo mostrou as sete tentativas, incluindo o sucesso anterior e a nova falha.
- Foi criada a providência de treinamento “Demonstração local - conferir metadados do DataJud”, vinculada à versão 3. Nenhum ato processual foi executado.
- A atividade percorreu A fazer, Em andamento, Aguardando revisão e Concluída. Evidência e comentários foram preservados.
- O histórico exibiu conta, horário e transição de cada atualização. Responsável e revisor foram a mesma conta técnica; este ensaio não comprova revisão independente por duas pessoas.
- Um recarregamento da página preservou a sessão, a atividade e a versão do processo.

## Defeito encontrado e corrigido

O cartão de providência comparava uma data vazia com a data atual e mostrava “vencida”, apesar de o resumo do backend indicar corretamente zero atrasos. `frontend/rotina.js` agora exige uma data preenchida antes da comparação e mostra “Data interna: não definida” quando ela não existe.

A regressão do fluxo em `tests/ui.test.cjs` passou a verificar esse caso sem data. Os 14 testes de interface passaram após a correção. A interface recarregada foi conferida visualmente e mostrou o texto correto.

## Evidência e limites

A captura local `output/teste-datajud/demonstracao-historico.png` mostra a atividade concluída, sua evidência e quatro eventos com autoria e horário. O aplicativo ficou aberto nesse histórico.

Este ensaio demonstra consulta, tratamento de falha externa, preservação de dados, linha do tempo e ciclo de providência. Não comprova disponibilidade contínua do DataJud nem testa todas as combinações de permissões, envio SMTP real, recuperação de conta, importação, implantação ou acessibilidade. As demais evidências automatizadas continuam descritas no relatório de testes.

Não houve commit, publicação ou alteração de credenciais nesta demonstração.
