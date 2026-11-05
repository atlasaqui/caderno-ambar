"""Servidor local que conecta a interface à consulta Python."""
from __future__ import annotations

import argparse
import json
import threading
import os
import re
from http.cookies import SimpleCookie
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from consulta import ErroConsulta, consultar_fonte, validar_entradas
from acompanhamento import Caderno, FalhaAPI

PROJECT = Path(__file__).resolve().parents[1]


class ServidorAmbar(ThreadingHTTPServer):
    daemon_threads = True
    audit_lock = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def token(self):
        cookie = SimpleCookie()
        cookie.load(self.headers.get('Cookie', ''))
        return cookie['ambar'].value if 'ambar' in cookie else ''

    def acompanhamento(self):
        path = urlsplit(self.path).path
        if self.command == 'POST':
            origem = self.headers.get('Origin')
            if origem and origem != 'http://' + self.headers.get('Host', ''):
                raise FalhaAPI(403, 'Origem da requisição recusada.')
            tamanho = int(self.headers.get('Content-Length', '0'))
            if not 0 < tamanho <= 8192 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise FalhaAPI(400, 'Envie JSON com até 8192 bytes.')
            dados = json.loads(self.rfile.read(tamanho))
            if not isinstance(dados, dict):
                raise FalhaAPI(400, 'Envie um objeto JSON.')
        else:
            dados = {}
        caderno = self.server.caderno
        if path in ('/api/conta/cadastro', '/api/conta/login') and self.command == 'POST':
            token = caderno.autenticar(dados, path.endswith('cadastro'))
            self.novo_cookie = f'ambar={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'
            return {'status': 'autenticado'}
        usuario = caderno.usuario(self.token())
        if path == '/api/conta/sair' and self.command == 'POST':
            caderno.sair(self.token())
            self.novo_cookie = 'ambar=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'
            return {'status': 'encerrado'}
        if path == '/api/casos':
            return caderno.listar(usuario) if self.command == 'GET' else caderno.adicionar(usuario, dados)
        match = re.fullmatch(r'/api/casos/(\d+)/(historico|consultar|revisar)', path)
        if match:
            identificador, acao = int(match[1]), match[2]
            if acao == 'historico' and self.command == 'GET':
                return caderno.historico(usuario, identificador)
            if acao in ('consultar', 'revisar') and self.command == 'POST':
                return getattr(caderno, acao)(usuario, identificador)
        raise FalhaAPI(404, 'Endpoint inexistente.')

    def responder_acompanhamento(self):
        try:
            return self.json_response(200, self.acompanhamento())
        except FalhaAPI as exc:
            return self.json_response(exc.status, {'error': str(exc)})
        except (ValueError, json.JSONDecodeError):
            return self.json_response(400, {'error': 'JSON ou tamanho inválido.'})

    def json_response(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        if getattr(self, 'novo_cookie', None):
            self.send_header('Set-Cookie', self.novo_cookie)
            del self.novo_cookie
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith(('/api/casos', '/api/conta')):
            return self.responder_acompanhamento()
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
        if urlsplit(self.path).path.startswith(('/api/casos', '/api/conta')):
            return self.responder_acompanhamento()
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


def criar_servidor(porta=8092, banco=None):
    server = ServidorAmbar(('127.0.0.1', porta), partial(Handler, directory=str(PROJECT / 'frontend')))
    server.caderno = Caderno(banco or os.environ.get('AMBAR_DB', str(PROJECT / 'output' / 'ambar.sqlite3')))
    return server


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
