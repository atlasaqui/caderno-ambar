# Consulta real do DataJud: diagnóstico e correções

Revisão de 04/11/2026. O fluxo autenticado do aplicativo consultou a API pública, recebeu um registro do TJPE com 35 movimentações e guardou a versão no SQLite. Um novo login confirmou a persistência. Esta validação de um processo público não equivale à homologação de uma carteira empresarial.

## O problema observado

A configuração habilitada apenas informa que o servidor pode tentar consultar. Não confirma conectividade. As primeiras chamadas pelo aplicativo falharam com HTTP 429 e timeout. A comparação das requisições preparadas pelo transporte antigo e pelo teste isolado mostrou URL, corpo, cabeçalhos e opções de transporte iguais. Portanto, atribuir exclusivamente o problema ao proxy não estava comprovado.

Foram encontrados defeitos locais: consulta com campos e páginas maiores que o necessário, paginação por deslocamento, repetição manual sem respeitar a espera persistida, tratamento indistinto de respostas 429 e histórico inacessível quando a primeira consulta falhava.

Não foi isolado experimentalmente qual parâmetro causou cada falha externa. O sucesso foi obtido após o conjunto das correções abaixo; sobrecarga ou indisponibilidade do fornecedor continuam possíveis.

## Correções e finalidade

| Parte | Alteração | Por que existe |
| --- | --- | --- |
| `backend/acompanhamento.py` | Páginas de dez registros, projeção dos campos necessários, ordenação por `@timestamp` e cursor `search_after` | Reduzir carga e seguir a orientação de paginação da API pública |
| Transporte | Validar total exato, número retornado, cursor, duplicação, shards e timeout; limite de mil registros e orçamento de 90 segundos | Não gravar resposta parcial como completa |
| Erros | Distinguir credencial, rede, TLS, proxy, timeout, limite e sobrecarga | Informar o que ocorreu sem expor chave ou corpo bruto |
| `backend/equipes.py` | Espera por processo e por fonte, reserva global, retentativa com atraso e auditoria da falha | Evitar novas chamadas concorrentes ou antes do prazo e registrar autoria |
| Banco | Migração aditiva da tabela `fontes_estado`, com próxima tentativa, reserva e motivo | Compartilhar o controle da fonte entre consultas e preservar os dados antigos |
| `backend/aplicacao.py` | JSON com `error`, `code`, `retry_after` e cabeçalho `Retry-After` | Comunicar a mesma espera ao cliente HTTP |
| `backend/piloto.py` | Carteira inclui `proxima_tentativa` | Permitir que a tela explique quando consultar novamente |
| `frontend/acompanhamento.js` | Atualizar cartão após falha, bloquear tentativa precoce e mostrar histórico mesmo sem versão | Tornar o primeiro erro compreensível e acessível |

HTTP 429 pode representar limite ou sobrecarga do Elasticsearch. O transporte identifica `circuit_breaking_exception` e `es_rejected_execution_exception` como indisponibilidade temporária. As mensagens preservam o último conteúdo válido. Nenhuma resposta fictícia substitui a consulta real.

## Evidência obtida

Em 04/11/2026, às 13h13 no horário de Recife, a chamada HTTP autenticada local concluiu em aproximadamente 25 segundos. Foi usado um processo público do TJPE, da classe Procedimento Comum Cível; seu número permanece somente nas evidências locais. Foram recebidos um registro e 35 movimentos. A versão real é a de ID 3; as versões 1 e 2 pertencem a uma demonstração separada.

O banco manteve seis consultas do processo real: cinco falhas anteriores e um sucesso. A auditoria identifica a conta da consulta. Sair e entrar novamente preservou a versão. O frontend foi exercitado em DOM simulado com a API local real: processo e prévia visíveis, 35 movimentos no histórico e seis tentativas. Essa verificação não é inspeção visual em navegador.

Passaram **50 testes Python** e a suíte JavaScript tem validação registrada no relatório de testes. As regressões incluem paginação, resposta parcial, erros externos, preservação da versão, espera entre tentativas e contrato HTTP. As chamadas externas desses testes são simuladas; o ensaio público acima é uma evidência separada.

Arquivos locais de evidência ficam em `output/teste-datajud/`, ignorado pelo Git: `resultado.json`, `validacao-interface-real.json` e `comparacao-requisicoes.json`. A primeira falha foi preservada. A senha da conta técnica fica somente em `acesso-local.json`; não publique esse arquivo.

## Como estudar e conferir

1. Abra `http://127.0.0.1:8093/acompanhamento.html` e entre com a conta técnica descrita em `teste-real-datajud.md`.
2. Abra a linha do tempo do caso TJPE. Leia o conteúdo já guardado; não é necessário consultar o CNJ novamente para estudar a tela.
3. Siga `api` no JavaScript, a rota HTTP, `Piloto.consultar`, `Equipes.consultar`, a fonte e `DataJud.buscar`.
4. Observe separadamente tentativa de consulta, versão de conteúdo, conferência e providência. Uma tentativa com falha não gera versão falsa.
5. Para reiniciar, configure as variáveis no mesmo terminal que executará `INICIAR.cmd`: `AMBAR_DATAJUD_HABILITADO=1` e a chave pública atual em `DATAJUD_API_KEY`. A chave não foi gravada no repositório. O servidor que já está aberto não herda variáveis alteradas depois da inicialização.

## Limites antes de uso em escritório

Ainda faltam piloto com carteira autorizada, validação de vários graus e paginação real, SMTP e HTTPS de produção, monitoramento, backup externo, política efetiva de retenção e testes visuais/acessibilidade. A API pública oferece metadados: não fornece automaticamente autos integrais, intimação oficial ou cálculo de prazo jurídico. A ordenação por data não cria snapshot transacional no fornecedor se os dados mudarem entre páginas.

## Referências técnicas

- Acesso oficial: https://datajud-wiki.cnj.jus.br/api-publica/acesso/
- Paginação da API pública: https://datajud-wiki.cnj.jus.br/api-publica/exemplos/exemplo3/

O prompt que orientou esta execução está em `prompt-correcao-datajud.md`. Não houve commit, push ou publicação nesta revisão.
