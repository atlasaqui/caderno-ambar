"""Requests busca a fonte; Beautiful Soup extrai; Python compara os registros."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import bs4
import requests
from bs4 import BeautifulSoup


class ErroConsulta(Exception):
    """Falha real de consulta, sem substituição por dados fictícios de sucesso."""


def validar_entradas(casos: object) -> list[dict[str, str]]:
    if not isinstance(casos, list) or not 1 <= len(casos) <= 3:
        raise ValueError('Envie de um a três casos.')
    vistos = set()
    for caso in casos:
        if not isinstance(caso, dict):
            raise ValueError('Cada caso deve ter id e previous.')
        codigo, anterior = caso.get('id'), caso.get('previous')
        if not isinstance(codigo, str) or not re.fullmatch(r'[A-Z]{3}-[0-9]{3}', codigo):
            raise ValueError('Código inválido. Exemplo: CIV-001.')
        if codigo in vistos:
            raise ValueError('Não repita um código na mesma consulta.')
        if not isinstance(anterior, str) or len(anterior) > 2000:
            raise ValueError('previous deve ser o texto anterior, com até 2000 caracteres.')
        vistos.add(codigo)
    return casos


def extrair_e_comparar(html: bytes, casos: list[dict[str, str]]) -> list[dict]:
    """Esta é a etapa Beautiful Soup: seletores localizam os campos no HTML."""
    pagina = BeautifulSoup(html, 'html.parser', from_encoding='utf-8')
    resultados = []
    for caso in validar_entradas(casos):
        registro = pagina.select_one(f'article[data-case="{caso["id"]}"]')
        movimento = registro.select_one('.movement') if registro else None
        data = registro.select_one('.date') if registro else None
        atual = movimento.get_text(strip=True) if movimento else ''
        data_fonte = data.get_text(strip=True) if data else ''
        if not atual or not data_fonte:
            resultados.append({'id': caso['id'], 'ok': False,
                               'error': 'Registro ou campo obrigatório ausente na fonte.'})
            continue
        resultados.append({
            'id': caso['id'], 'ok': True, 'previous': caso['previous'],
            'current': atual, 'source_date': data_fonte,
            'changed': atual != caso['previous'],
            'incomplete': data_fonte == 'Não informada',
        })
    return resultados


def consultar_fonte(url: str, casos: list[dict[str, str]], timeout=(3, 10)) -> dict:
    """Esta é a etapa Requests: um GET HTTP real com validação e timeout."""
    validar_entradas(casos)
    try:
        with requests.Session() as sessao:
            # O laboratório consulta sua própria fonte, sem depender de proxy do sistema.
            sessao.trust_env = False
            resposta = sessao.get(url, timeout=timeout, allow_redirects=False)
            resposta.raise_for_status()
            if resposta.status_code != 200:
                raise ErroConsulta(f'A fonte respondeu HTTP {resposta.status_code}; esperado 200.')
    except requests.Timeout as exc:
        raise ErroConsulta('A fonte excedeu o tempo limite de consulta.') from exc
    except requests.RequestException as exc:
        raise ErroConsulta(f'Não foi possível obter a fonte: {exc}') from exc

    resultados = extrair_e_comparar(resposta.content, casos)
    return {
        'engine': 'python', 'source': url, 'http_status': resposta.status_code,
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'source_sha256': hashlib.sha256(resposta.content).hexdigest(),
        'tools': {'requests': requests.__version__, 'beautifulsoup4': bs4.__version__},
        'results': resultados,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8092/portal.html')
    parser.add_argument('--id', default='CIV-001')
    parser.add_argument('--anterior', default='Aguardando agendamento')
    parser.add_argument('--saida', type=Path, default=Path('output/consulta-python.json'))
    args = parser.parse_args()
    try:
        resultado = consultar_fonte(args.url, [{'id': args.id, 'previous': args.anterior}])
    except (ErroConsulta, ValueError) as exc:
        parser.exit(1, f'Consulta não concluída: {exc}\n')
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    if any(not r['ok'] for r in resultado['results']):
        parser.exit(1, 'Há registros que não puderam ser extraídos. Confira o relatório.\n')


if __name__ == '__main__':
    main()
