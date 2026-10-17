"""Servidor local que conecta a interface à consulta Python."""
from __future__ import annotations

import argparse
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from consulta import ErroConsulta, consultar_fonte, validar_entradas

PROJECT = Path(__file__).resolve().parents[1]


class ServidorAmbar(ThreadingHTTPServer):
    daemon_threads = True
    audit_lock = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def json_response(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/saude':
            return self.json_response(200, {'engine': 'python', 'status': 'ok'})
        if path == '/runtime-config.js':
            body = b'window.AMBAR_RUNTIME = {mode: "python", api: "/api/consultar"};'
            self.send_response(200)
            self.send_header('Content-Type', 'text/javascript; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != '/api/consultar':
            return self.json_response(404, {'error': 'Endpoint inexistente.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192:
                raise ValueError('Corpo da requisição ausente ou grande demais.')
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Envie application/json.')
            payload = json.loads(self.rfile.read(length))
            casos = validar_entradas(payload.get('cases') if isinstance(payload, dict) else None)
        except (ValueError, json.JSONDecodeError) as exc:
            return self.json_response(400, {'error': str(exc)})

        # A URL vem da configuração do servidor, nunca do navegador do visitante.
        source_url = f'http://127.0.0.1:{self.server.server_port}/portal.html'
        try:
            resultado = consultar_fonte(source_url, casos)
        except ErroConsulta as exc:
            return self.json_response(502, {'error': str(exc)})

        audit_file = PROJECT / 'output' / 'consultas.jsonl'
        try:
            with self.server.audit_lock:
                audit_file.parent.mkdir(parents=True, exist_ok=True)
                with audit_file.open('a', encoding='utf-8') as out:
                    out.write(json.dumps(resultado, ensure_ascii=False) + '\n')
        except OSError:
            # Informar a falha de registro sem alegar que o histórico foi gravado.
            resultado['audit_warning'] = 'Consulta concluída; não foi possível gravar o log local.'
        print(f'[Python] Requests HTTP {resultado["http_status"]} -> Beautiful Soup -> '
              f'{len(resultado["results"])} resultado(s)', flush=True)
        return self.json_response(200, resultado)


def criar_servidor(porta=8092):
    return ServidorAmbar(('127.0.0.1', porta), partial(Handler, directory=str(PROJECT / 'dist')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--porta', type=int, default=8092)
    args = parser.parse_args()
    with criar_servidor(args.porta) as server:
        print(f'Caderno Âmbar com Python: http://127.0.0.1:{server.server_port}', flush=True)
        print('Consultar selecionados executa Requests + Beautiful Soup.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\nServidor encerrado.')


if __name__ == '__main__':
    main()
