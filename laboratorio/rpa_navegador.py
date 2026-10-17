"""Playwright opera o Caderno Âmbar e verifica a consulta Python de ponta a ponta."""
from __future__ import annotations

import argparse
import csv
import json
import threading
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from servidor import criar_servidor


def executar(visivel=False, diretorio=Path('output/rpa')):
    diretorio.mkdir(parents=True, exist_ok=True)
    etapas = []
    relatorio = {'status': 'iniciado', 'started_at': datetime.now(timezone.utc).isoformat(),
                 'playwright_version': version('playwright'), 'steps': etapas}
    servidor = criar_servidor(0)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{servidor.server_port}'
    relatorio['url'] = url

    def passo(texto):
        etapas.append(texto)
        print(f'{len(etapas):02d}. {texto}', flush=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not visivel, slow_mo=350 if visivel else 0)
            context = browser.new_context(viewport={'width': 1280, 'height': 900},
                                          accept_downloads=True, locale='pt-BR')
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.set_default_timeout(15000)
            try:
                page.goto(url, wait_until='domcontentloaded')
                expect(page.get_by_text('Laboratório Python ativo', exact=True)).to_be_visible()
                passo('Abrir a interface conectada ao backend Python')
                page.get_by_role('button', name='Explorar sozinho ↗', exact=True).click()
                page.get_by_role('button', name='+ Adicionar caso', exact=True).click()
                page.get_by_role('button', name='Adicionar CIV-001 →', exact=True).click()
                expect(page.locator('.movement > span')).to_have_text('Aguardando agendamento')
                passo('Adicionar CIV-001 e verificar o registro anterior')
                page.get_by_role('checkbox', name='Selecionar CIV-001', exact=True).check()
                passo('Selecionar o caso a consultar')

                with page.expect_response(lambda r: r.url.endswith('/api/consultar')
                                          and r.request.method == 'POST') as response_event:
                    page.get_by_role('button', name='Consultar selecionados (1)', exact=True).click()
                resposta = response_event.value
                assert resposta.status == 200, f'API respondeu HTTP {resposta.status}'
                dados = resposta.json()
                assert dados['engine'] == 'python'
                assert dados['tools']['requests'] and dados['tools']['beautifulsoup4']
                assert dados['results'][0]['changed'] is True
                relatorio['python_response'] = dados
                expect(page.locator('.movement > span')).to_have_text('Audiência agendada para 22/10 às 14h')
                passo('Consultar e verificar a resposta real de Requests + Beautiful Soup')

                page.get_by_role('button', name='Ver mudança ↗', exact=True).click()
                expect(page.locator('.comparison article').first).to_contain_text('Aguardando agendamento')
                expect(page.locator('.comparison .after')).to_contain_text('Audiência agendada')
                page.screenshot(path=str(diretorio / 'comparacao.png'))
                passo('Conferir o antes e depois e salvar a captura')
                page.get_by_role('button', name='✓ Marcar como conferido', exact=True).click()
                page.get_by_role('button', name='Voltar à lista →', exact=True).click()
                expect(page.locator('.badge')).to_have_text('Conferido por você')
                passo('Registrar a conferência de leitura')

                page.get_by_role('searchbox', name='Buscar código ou assunto', exact=True).fill('CIV-001')
                page.get_by_role('button', name='Com novidade', exact=True).click()
                with page.expect_download() as download_event:
                    page.get_by_role('button', name='↓ Exportar lista (1)', exact=True).click()
                csv_path = diretorio / 'casos.csv'
                download_event.value.save_as(str(csv_path))
                with csv_path.open(encoding='utf-8-sig', newline='') as arquivo:
                    linhas = list(csv.DictReader(arquivo, delimiter=';'))
                assert len(linhas) == 1 and linhas[0]['Caso'] == 'CIV-001'
                assert linhas[0]['Conferência'] == 'Conferido por você'
                assert linhas[0]['Movimentação atual'] == dados['results'][0]['current']
                passo('Buscar, filtrar, baixar o CSV e validar seu conteúdo')

                page.get_by_role('button', name='Histórico', exact=True).click()
                expect(page.get_by_role('heading', name='CIV-001: mudança encontrada', exact=True)).to_be_visible()
                expect(page.get_by_role('heading', name='Lista exportada', exact=True)).to_be_visible()
                page.screenshot(path=str(diretorio / 'historico.png'))
                passo('Conferir o histórico das ações')
                relatorio['status'] = 'sucesso'
            except Exception as exc:
                relatorio['status'] = 'falha'
                relatorio['error'] = str(exc)
                page.screenshot(path=str(diretorio / 'falha.png'))
                raise
            finally:
                context.tracing.stop(path=str(diretorio / 'trace.zip'))
                browser.close()
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=5)
        relatorio['finished_at'] = datetime.now(timezone.utc).isoformat()
        (diretorio / 'relatorio.json').write_text(
            json.dumps(relatorio, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Concluído. Evidências em: {diretorio.resolve()}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--visivel', action='store_true', help='Mostrar o navegador durante as ações.')
    parser.add_argument('--saida', type=Path, default=Path('output/rpa'))
    args = parser.parse_args()
    executar(visivel=args.visivel, diretorio=args.saida)
