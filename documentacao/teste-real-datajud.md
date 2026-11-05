# Teste real do DataJud em 04/11/2026

## Resultado confirmado

O fluxo autenticado do Caderno Âmbar concluiu uma consulta pública do TJPE, retornou 35 movimentações e gravou uma versão real no banco. Um novo login confirmou a persistência. A classe recebida foi Procedimento Comum Cível. O número do processo foi omitido da documentação pública; as evidências ficam no ambiente local. Não foram consultados nomes de partes ou PDFs dos autos.

## Conta local de estudo

Escritório: **Teste real DataJud — estudo local**. E-mail e senha aleatória estão somente em `output/teste-datajud/acesso-local.json`, ignorado pelo Git e ausente no repositório público. A confirmação usou a caixa local de desenvolvimento; não comprova propriedade de uma caixa externa. Quem clonar o projeto deve criar sua própria conta.

Abra `http://127.0.0.1:8093/acompanhamento.html`. O caso real tem a versão 3 e seis consultas: cinco falhas e um sucesso. A demonstração fictícia é outro caso, com duas versões e uma providência demonstrativa com quatro eventos.

## Verificações

- Consulta pela rota HTTP real autenticada, sem importar snapshot de teste.
- Uma versão real, 35 movimentos, histórico e auditoria com autoria.
- Persistência após sair e entrar novamente.
- Frontend com API local real em DOM simulado: prévia, processo, 35 movimentos e seis consultas acessíveis.
- Cinquenta testes Python aprovados. A validação JavaScript e seus limites estão no relatório de testes.

As primeiras falhas permanecem registradas. A causa externa exclusiva não foi isolada; após corrigir transporte, espera e interface, o fluxo concluiu. Não se deve afirmar que apenas o proxy era responsável.

## Evidências e limites

`output/teste-datajud/resultado.json` contém o último sucesso; `resultado-primeira-tentativa.json` preserva a falha inicial; `validacao-interface-real.json` contém a verificação de DOM; `resumo-do-teste.json` separa caso real e demonstração. Esses arquivos são locais e não devem ser publicados com credenciais.

O servidor permanece na porta 8093 com a fonte habilitada. Reiniciar em outro terminal exige configurar novamente as variáveis antes de iniciar o processo. Uma consulta pública bem-sucedida não homologa o uso empresarial ou a disponibilidade contínua do fornecedor. Veja [diagnóstico completo](diagnostico-e-correcao-datajud.md).
