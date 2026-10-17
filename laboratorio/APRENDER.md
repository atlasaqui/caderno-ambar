# Caderno Âmbar: aprenda usando as três bibliotecas

## O que foi implementado

Você tem duas formas de usar a interface:

- **Site público:** consulta feita em JavaScript, sem backend Python.
- **Laboratório local:** o botão de consulta chama a API Python. Requests busca o portal, Beautiful Soup extrai a movimentação e Python compara os registros. Playwright pode operar a interface automaticamente.

O laboratório usa a mesma aparência e os mesmos casos fictícios do site. Não acessa tribunais.

## 1. Preparar o ambiente uma vez

Abra um terminal na pasta que contém `requirements.txt`, `dist` e `laboratorio`. Requer Python 3.10 ou mais recente. A execução verificada usou Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Não é necessário ativar a venv: os comandos usam diretamente o Python dela. Você precisa de internet para instalar os pacotes e o navegador. Depois, a consulta usa somente o portal local. As fontes externas são opcionais; a interface tem fontes alternativas.

## 2. Usar a consulta Python pelo site

```powershell
.\.venv\Scripts\python.exe laboratorio\servidor.py
```

Abra **http://127.0.0.1:8092**. A faixa “Laboratório Python ativo” identifica o modo correto.

1. Clique em Explorar sozinho.
2. Clique em Adicionar caso e adicione CIV-001.
3. Leia o registro inicial: Aguardando agendamento.
4. Marque a caixa Selecionar CIV-001.
5. Clique em Consultar selecionados.
6. O novo texto será Audiência agendada para 22/10 às 14h.
7. Abra Ver mudança, compare e marque como conferido.

No terminal aparece uma linha com Requests, Beautiful Soup e a resposta HTTP. Em Histórico aparece que a consulta foi executada em Python. O arquivo `output/consultas.jsonl` registra as respostas para conferência.

Para encerrar o servidor, pressione Ctrl+C no terminal.

## 3. Entender Requests + Beautiful Soup sem o navegador

Deixe o servidor do passo anterior aberto. Em um segundo terminal, na mesma pasta:

```powershell
.\.venv\Scripts\python.exe laboratorio\consulta.py
```

Leia o JSON mostrado no terminal e salvo em `output/consulta-python.json`:

```json
{
  "previous": "Aguardando agendamento",
  "current": "Audiência agendada para 22/10 às 14h",
  "changed": true
}
```

O relatório completo também inclui o código do caso, as versões das bibliotecas, o horário, o endereço da fonte e seu hash.

Abra `laboratorio/consulta.py` e acompanhe estas funções:

1. `validar_entradas`: confere os códigos, os textos anteriores e as duplicidades.
2. `consultar_fonte`: usa `sessao.get(...)` de **Requests** para buscar a página. Verifica status e limita o tempo de espera.
3. `extrair_e_comparar`: cria `BeautifulSoup(...)`, encontra o caso com `select_one(...)` e extrai os textos com `get_text(...)`.
4. `atual != caso['previous']`: o Python decide se houve mudança. Essa comparação não precisa de IA.

**Experimento:** repita a consulta informando como registro anterior o próprio texto atual:

```powershell
.\.venv\Scripts\python.exe laboratorio\consulta.py --anterior "Audiência agendada para 22/10 às 14h" --saida output\sem-mudanca.json
```

Agora `changed` deve ser `false`. Você comprovou que a atualização é calculada, não inventada.

## 4. Ver Playwright trabalhar

Este comando inicia seu próprio servidor, abre o Chromium e realiza as ações. Não depende de manter o servidor anterior aberto.

```powershell
.\.venv\Scripts\python.exe laboratorio\rpa_navegador.py --visivel
```

Observe: abrir a interface → adicionar → selecionar → consultar → comparar → conferir → buscar → filtrar → baixar o CSV → abrir o histórico. A janela fecha quando a execução termina.

Abra `laboratorio/rpa_navegador.py`:

- `chromium.launch(...)` inicia o navegador.
- `get_by_role(...).click()` aciona botões identificados pelo nome.
- `.check()` marca a caixa de seleção.
- `expect_response(...)` aguarda a resposta real da API e verifica que foi executada por Python.
- `expect(...)` verifica o que apareceu na interface. As esperas acompanham condições reais, sem pausas arbitrárias.
- `expect_download()` captura o CSV; o script abre e confere seu conteúdo.

O modo sem janela, útil para repetição automática, é:

```powershell
.\.venv\Scripts\python.exe laboratorio\rpa_navegador.py
```

Evidências geradas em `output/rpa/`:

- `comparacao.png`: antes e depois lidos da interface.
- `historico.png`: ações registradas.
- `casos.csv`: resultado exportado.
- `relatorio.json`: etapas, versões, resposta Python e sucesso ou falha.
- `trace.zip`: registro de execução do Playwright. Pode conter código e respostas do laboratório; não use dados reais de terceiros.

Para abrir o trace:

```powershell
.\.venv\Scripts\python.exe -m playwright show-trace output\rpa\trace.zip
```

## 5. Verificar os cenários de falha

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s laboratorio -p "test_*.py" -v
```

São sete verificações: HTTP real e extração, segunda consulta sem mudança, HTTP 404, campo ausente, entradas inválidas, API com JSON inválido e configuração Python ativa.

**Experimento manual:** com o servidor aberto, rode:

```powershell
.\.venv\Scripts\python.exe laboratorio\consulta.py --url http://127.0.0.1:8092/nao-existe.html
```

O programa deve falhar com HTTP 404. Não deve dizer que não houve movimentação: falha de consulta e ausência de mudança são situações diferentes.

## 6. Como explicar o projeto depois de praticar

“No laboratório local do Caderno Âmbar, Requests faz a consulta HTTP à fonte fictícia. Beautiful Soup interpreta o HTML e extrai os campos. Python compara a movimentação anterior com a atual e retorna o resultado ao painel. Também há uma automação com Playwright que opera o navegador e verifica o fluxo, incluindo o CSV. A implementação foi feita com apoio de IA, e eu pratiquei e estudei seu funcionamento.”

Use a última frase sobre sua prática somente depois de executar os exercícios. Não diga que integra tribunais, roda Python no site público ou que você domina as bibliotecas só porque o código está pronto.

## Referências oficiais

- Requests: https://requests.readthedocs.io/en/latest/user/quickstart/
- Beautiful Soup: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- Playwright Python: https://playwright.dev/python/docs/library
