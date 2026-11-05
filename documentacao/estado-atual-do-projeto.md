# Entregável local do Caderno Âmbar

Revisão de 4 de novembro de 2026. Consulta autenticada real do TJPE validada com 35 movimentos, versão, histórico e autoria. Veja diagnostico-e-correcao-datajud.md. Este arquivo é o estado atual; os guias V2 e de rotina preservam a explicação das etapas anteriores.

## Implementado nesta revisão

- Fila persistente DataJud: solicitação HTTP 202, processamento em segundo plano, espera crescente, até cinco falhas, pausa de erros de configuração e acompanhamento na interface. Os últimos dados válidos permanecem acessíveis. Ver `fila-atualizacoes-datajud.md`.

- Serviço `Piloto`, sobre a rotina existente, com backup anterior à reconstrução da tabela de processos.
- Restrição de duplicação por escritório, número e tribunal, preservando IDs e vínculos. A migração falha com rollback se houver conflitos ou vínculos inválidos.
- `GET /api/carteira` com busca, filtros, contagem e paginação de 20 itens no banco. A interface deixou de depender da rota legada limitada a 1.000 registros.
- Indicadores de toda a carteira e resumo das providências do usuário, vencidas e para revisão.
- Confirmação de e-mail com token aleatório, hash no banco, expiração de 30 minutos, uso único e limites de tentativas. O código não é devolvido na API.
- Confirmação exigida para criar e aceitar convites e consultar fontes reais. Demonstrações continuam disponíveis para estudo. Contas antigas não são consideradas verificadas automaticamente.
- Exportação administrativa JSON do escritório, com versões, consultas, providências e eventos. Senhas, sessões, convites e tokens não são exportados. O CSV permanece disponível.
- Registro administrativo de solicitações de retenção/exclusão. Não equivale a execução de exclusão nem a atendimento automático de uma solicitação.
- Data interna da providência opcional; ausência de data não conta como atraso. Conclusão não aceita apagar a evidência simultaneamente.
- Produção recusa inicialização sem origem HTTPS, banco configurado e SMTP. HSTS é enviado em produção. `AMBAR_WORKER=0` desativa ciclos em instâncias HTTP adicionais.

## Uso local

Execute `INICIAR.cmd` em um computador com Python instalado ou use um ambiente virtual que contenha `requirements.txt`. Abra a apresentação na porta 8093. A rota recomendada é `backend/aplicacao.py`; o servidor legado 8092 não atende ao contrato atual completo.

Na área de trabalho, expanda Minha conta e confirmação de e-mail. Solicite o código. Em desenvolvimento, abra o JSON correspondente ao seu e-mail em `output/email-local`, copie apenas `token` e confirme. Isso é simulação local de entrega; não comprova propriedade de uma caixa externa. Em produção, o canal SMTP envia a mensagem ao destinatário.

## Pendências que impedem declarar produção concluída

Fonte real autorizada e carteira consentida ainda precisam de validação externa. SMTP real, confirmação de entrega pelo provedor, hospedagem, HTTPS público e backup externo protegido não foram configurados nem testados. MFA de administrador não foi implementado. A política de retenção e a exclusão efetiva de dados e backups dependem de definição e implementação; há apenas registro de solicitação. Não existe integração de intimações oficiais, cálculo de prazo judicial, peticionamento, financeiro ou armazenamento de anexos privados.

O worker ainda roda no processo da aplicação. A flag de configuração não impede que um operador inicie dois workers por engano; as reservas existentes reduzem duplicação por tarefa, mas isso não equivale a liderança distribuída. A implantação deve ter uma única instância de ciclos, supervisão e monitoramento. A rota de carteira está tipada na entrada; as rotas legadas continuam em um roteador genérico e precisam de contratos OpenAPI individuais.

As exportações administrativas contêm dados do escritório: guarde-as em armazenamento protegido e controle o acesso. Não substituem o backup consistente do banco. A exportação não é ainda um importador de restauração.

## Escopo de validação

Os resultados atuais devem ser lidos junto de `testes-e-validacao.md`: 56 testes Python e 16 de interface aprovados na revalidação de 05/11/2026. Os testes usam SQLite temporário, HTTP local e DOM simulado. A demonstração adicional no navegador confirmou cartões, providência, solicitação em segundo plano e laboratório fictício. Isso não substitui validação completa de acessibilidade e dispositivos.

## Sequência de implantação

1. Aprovar finalidade, fonte, acesso e carteira de piloto com o escritório.
2. Definir responsável operacional, política de retenção, MFA e tratamento de incidentes.
3. Configurar domínio HTTPS, API persistente, SMTP e armazenamento de backup externo protegido. Usar segredos do serviço, sem gravá-los no Git.
4. Executar uma única instância de agendamento; instâncias HTTP adicionais usam `AMBAR_WORKER=0`. Fazer build e testar Docker no ambiente de destino antes de adotá-lo.
5. Restaurar uma cópia em ambiente isolado e percorrer o fluxo completo com duas contas e dois escritórios.
6. Testar desktop, celular, teclado, falhas de rede e expiração de sessão em navegador permitido.
7. Fazer piloto acompanhado e medir falhas, atrasos da fonte, tempo para conferir e conclusão das providências. Só ampliar após corrigir problemas observados.
