"""Persistência e integração DataJud do caderno pessoal. Sem dados simulados."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

import requests


class FalhaAPI(Exception):
    def __init__(self, status, mensagem, *, codigo=None, aguardar=None):
        self.status = status
        self.codigo = codigo
        self.aguardar = aguardar
        super().__init__(mensagem)


class Caderno:
    def __init__(self, arquivo):
        self.arquivo = str(arquivo)
        Path(arquivo).parent.mkdir(parents=True, exist_ok=True)
        with self.conexao() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS usuarios (
                  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
                  salt TEXT NOT NULL, senha TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessoes (
                  token TEXT PRIMARY KEY, usuario INTEGER NOT NULL, expira REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS casos (
                  id INTEGER PRIMARY KEY, usuario INTEGER NOT NULL,
                  numero TEXT NOT NULL, tribunal TEXT NOT NULL, apelido TEXT NOT NULL,
                  snapshot TEXT, revisado INTEGER NOT NULL DEFAULT 0,
                  UNIQUE(usuario, numero, tribunal));
                CREATE TABLE IF NOT EXISTS consultas (
                  id INTEGER PRIMARY KEY, caso INTEGER NOT NULL, instante REAL NOT NULL,
                  estado TEXT NOT NULL, anterior TEXT, atual TEXT, erro TEXT);
            ''')

    @contextmanager
    def conexao(self):
        db = sqlite3.connect(self.arquivo, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def hash_senha(senha, salt):
        return hashlib.scrypt(senha.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()

    def autenticar(self, dados, cadastro=False):
        email, senha = dados.get('email'), dados.get('senha')
        if not isinstance(email, str) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(email) > 254:
            raise FalhaAPI(400, 'Informe um e-mail válido.')
        if not isinstance(senha, str) or not 10 <= len(senha) <= 128:
            raise FalhaAPI(400, 'Use uma senha de 10 a 128 caracteres.')
        with self.conexao() as db:
            if cadastro:
                salt = secrets.token_hex(16)
                try:
                    db.execute('INSERT INTO usuarios(email,salt,senha) VALUES(?,?,?)',
                               (email.lower(), salt, self.hash_senha(senha, salt)))
                except sqlite3.IntegrityError:
                    raise FalhaAPI(409, 'Não foi possível cadastrar esse e-mail.')
            u = db.execute('SELECT * FROM usuarios WHERE email=?', (email.lower(),)).fetchone()
            salt = u['salt'] if u else '00' * 16
            calculado = self.hash_senha(senha, salt)
            if not u or not hmac.compare_digest(u['senha'], calculado):
                raise FalhaAPI(401, 'E-mail ou senha inválidos.')
            token = secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessoes WHERE expira < ?', (time.time(),))
            db.execute('INSERT INTO sessoes VALUES(?,?,?)',
                       (hashlib.sha256(token.encode()).hexdigest(), u['id'], time.time() + 28800))
            return token

    def usuario(self, token):
        with self.conexao() as db:
            row = db.execute('SELECT usuario FROM sessoes WHERE token=? AND expira>?',
                             (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        if not row:
            raise FalhaAPI(401, 'Entre na sua conta para continuar.')
        return row['usuario']

    def sair(self, token):
        with self.conexao() as db:
            db.execute('DELETE FROM sessoes WHERE token=?', (hashlib.sha256(token.encode()).hexdigest(),))

    def listar(self, usuario):
        with self.conexao() as db:
            return [dict(r) for r in db.execute('SELECT * FROM casos WHERE usuario=? ORDER BY id DESC', (usuario,))]

    def adicionar(self, usuario, dados):
        numero = re.sub(r'[.\-/]', '', str(dados.get('numero', '')))
        tribunal, apelido = dados.get('tribunal'), dados.get('apelido', '')
        if not re.fullmatch(r'\d{20}', numero):
            raise FalhaAPI(400, 'Informe os 20 dígitos do número CNJ.')
        # Lista explícita impede URLs arbitrárias/SSRF. Amplie apenas após conferir a documentação.
        if tribunal not in ('tjpe', 'trt6', 'trf5'):
            raise FalhaAPI(400, 'Tribunal não suportado: escolha TJPE, TRT6 ou TRF5.')
        if not isinstance(apelido, str) or len(apelido) > 120:
            raise FalhaAPI(400, 'Apelido deve ter até 120 caracteres.')
        with self.conexao() as db:
            try:
                cur = db.execute('INSERT INTO casos(usuario,numero,tribunal,apelido) VALUES(?,?,?,?)',
                                 (usuario, numero, tribunal, apelido.strip()))
            except sqlite3.IntegrityError:
                raise FalhaAPI(409, 'Esse processo já está no seu caderno.')
            return {'id': cur.lastrowid}

    def caso(self, db, usuario, identificador):
        row = db.execute('SELECT * FROM casos WHERE id=? AND usuario=?', (identificador, usuario)).fetchone()
        if not row:
            raise FalhaAPI(404, 'Caso não encontrado.')
        return row

    def historico(self, usuario, identificador):
        with self.conexao() as db:
            self.caso(db, usuario, identificador)
            return [dict(r) for r in db.execute('SELECT * FROM consultas WHERE caso=? ORDER BY id DESC LIMIT 100', (identificador,))]

    def revisar(self, usuario, identificador):
        with self.conexao() as db:
            caso = self.caso(db, usuario, identificador)
            if not caso['snapshot']:
                raise FalhaAPI(409, 'Consulte o caso antes de conferir.')
            db.execute('UPDATE casos SET revisado=1 WHERE id=?', (identificador,))
        return {'status': 'conferido'}

    def consultar(self, usuario, identificador, cliente=None):
        with self.conexao() as db:
            caso = dict(self.caso(db, usuario, identificador))
            ultima = db.execute('SELECT instante FROM consultas WHERE caso=? ORDER BY id DESC LIMIT 1', (identificador,)).fetchone()
        if ultima and time.time() - ultima['instante'] < 30:
            raise FalhaAPI(429, 'Aguarde 30 segundos entre consultas deste caso.')
        try:
            atual = (cliente or DataJud()).buscar(caso['tribunal'], caso['numero'])
        except FalhaAPI as exc:
            with self.conexao() as db:
                db.execute('INSERT INTO consultas(caso,instante,estado,erro) VALUES(?,?,?,?)',
                           (identificador, time.time(), 'falha', str(exc)))
            raise
        serializado = json.dumps(atual, ensure_ascii=False, sort_keys=True)
        with self.conexao() as db:
            # Releitura dentro da transação: outra consulta pode ter atualizado a referência.
            db.execute('BEGIN IMMEDIATE')
            anterior = self.caso(db, usuario, identificador)['snapshot']
            estado = 'primeira consulta' if anterior is None else 'sem mudança' if anterior == serializado else 'mudança encontrada'
            db.execute('INSERT INTO consultas(caso,instante,estado,anterior,atual) VALUES(?,?,?,?,?)',
                       (identificador, time.time(), estado, anterior, serializado))
            db.execute('UPDATE casos SET snapshot=?, revisado=CASE WHEN snapshot=? THEN revisado ELSE 0 END WHERE id=?',
                       (serializado, serializado, identificador))
        return {'estado': estado, 'dados': atual}


class DataJud:
    """Consulta pública com paginação documentada e recusa de dados incompletos."""
    @staticmethod
    def tipos_erro(payload):
        """Lê causas encadeadas do Elasticsearch sem expor motivos ou dados brutos."""
        tipos=set()
        fila=[(payload.get('error'),0)] if isinstance(payload,dict) else []
        for _ in range(128):
            if not fila:break
            item,nivel=fila.pop()
            if nivel>10:continue
            if isinstance(item,list):
                fila.extend((x,nivel+1) for x in item[:32])
            elif isinstance(item,dict):
                tipo=item.get('type')
                if isinstance(tipo,str) and re.fullmatch(r'[a-z_]{1,100}',tipo):tipos.add(tipo)
                fila.extend((item.get(chave),nivel+1) for chave in ('root_cause','caused_by','failed_shards','reason') if isinstance(item.get(chave),(dict,list)))
        return tipos

    @staticmethod
    def espera(resposta, padrao=90):
        valor = str(resposta.headers.get('Retry-After', '')).strip()
        try:
            segundos = int(valor)
        except ValueError:
            try:
                segundos = int((parsedate_to_datetime(valor) - datetime.now(timezone.utc)).total_seconds()) + 1
            except (ValueError, TypeError, OverflowError):
                segundos = padrao
        return max(1, segundos)

    @staticmethod
    def corpo(numero, cursor=None):
        dados = {
            'size': 10,
            '_source': ['numeroProcesso', 'tribunal', 'grau', 'classe', 'orgaoJulgador', 'movimentos', '@timestamp'],
            'track_total_hits': True,
            'sort': [{'@timestamp': {'order': 'asc'}}],
            'query': {'match': {'numeroProcesso': numero}},
        }
        if cursor is not None:
            dados['search_after'] = cursor
        return dados

    def buscar(self, tribunal, numero):
        chave = os.environ.get('DATAJUD_API_KEY', '').strip()
        if not chave:
            raise FalhaAPI(503, 'Configure DATAJUD_API_KEY no servidor.', codigo='fonte_configuracao')
        if tribunal not in ('tjpe', 'trt6', 'trf5'):
            raise FalhaAPI(400, 'Tribunal não suportado.')
        sessao = None
        transporte = requests.post
        if os.environ.get('AMBAR_DATAJUD_USAR_PROXY', '0') != '1':
            sessao = requests.Session()
            sessao.trust_env = False
            transporte = sessao.post
        inicio = time.monotonic()
        try:
            fontes, vistos, cursor, total_esperado = [], set(), None, None
            for _ in range(100):
                restante = 90 - (time.monotonic() - inicio)
                if restante <= 0:
                    raise FalhaAPI(504, 'DataJud excedeu o tempo total de consulta. Referência preservada.',
                                   codigo='fonte_timeout', aguardar=90)
                resposta = transporte(
                    f'https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search',
                    headers={'Authorization': 'APIKey ' + chave},
                    json=self.corpo(numero, cursor), timeout=(5, min(45, restante)), allow_redirects=False)
                if resposta.status_code != 200:
                    tipos = set()
                    try:
                        tipos = self.tipos_erro(resposta.json())
                    except (ValueError, AttributeError):
                        pass
                    if resposta.status_code == 429:
                        espera = self.espera(resposta)
                        if tipos & {'circuit_breaking_exception', 'es_rejected_execution_exception'}:
                            raise FalhaAPI(503, 'O serviço de buscas do CNJ/DataJud está sobrecarregado e recusou a consulta. Seus dados salvos foram preservados; a próxima tentativa respeitará uma pausa de pelo menos cinco minutos.',
                                           codigo='fonte_sobrecarregada', aguardar=max(300,espera))
                        raise FalhaAPI(429, f'DataJud recusou temporariamente a consulta. Aguarde pelo menos {espera} segundos.',
                                       codigo='fonte_limite', aguardar=espera)
                    if resposta.status_code in (401, 403):
                        raise FalhaAPI(502, 'DataJud recusou a credencial de acesso. Confira a chave pública vigente.',
                                       codigo='fonte_credencial', aguardar=300)
                    raise FalhaAPI(502, f'DataJud respondeu HTTP {resposta.status_code}. Referência preservada.',
                                   codigo='fonte_http', aguardar=90)
                if len(resposta.content) > 5_000_000:
                    raise FalhaAPI(502, 'Resposta da fonte excedeu o limite de processamento.', codigo='fonte_formato', aguardar=90)
                payload = resposta.json()
                if not isinstance(payload, dict) or payload.get('timed_out') is True:
                    raise FalhaAPI(502, 'DataJud devolveu uma consulta incompleta. Referência preservada.',
                                   codigo='fonte_incompleta', aguardar=90)
                shards = payload.get('_shards', {})
                if not isinstance(shards, dict) or shards.get('failed', 0):
                    raise FalhaAPI(502, 'Parte da consulta falhou no DataJud. Referência preservada.',
                                   codigo='fonte_incompleta', aguardar=90)
                hits = payload['hits']
                pagina = hits['hits']
                total = hits['total']
                if isinstance(total, dict):
                    if total.get('relation') != 'eq':
                        raise FalhaAPI(502, 'DataJud não informou a contagem exata. Referência preservada.',
                                       codigo='fonte_incompleta', aguardar=90)
                    total = total['value']
                if type(total) is not int or total < 0 or not isinstance(pagina, list) or len(pagina) > 10:
                    raise ValueError('Contrato inválido de paginação.')
                if total > 1000 or (total_esperado is not None and total != total_esperado):
                    raise FalhaAPI(502, 'Resultado excedeu o limite ou mudou durante a paginação. Referência preservada.',
                                   codigo='fonte_incompleta', aguardar=90)
                total_esperado = total
                for hit in pagina:
                    fonte = hit['_source']
                    if not isinstance(fonte, dict) or fonte.get('numeroProcesso') != numero:
                        raise ValueError('Número inesperado na resposta.')
                    identidade = hit.get('_id') or json.dumps(fonte, sort_keys=True)
                    if identidade in vistos:
                        raise FalhaAPI(502, 'DataJud repetiu registros durante a paginação. Referência preservada.',
                                       codigo='fonte_incompleta', aguardar=90)
                    vistos.add(identidade)
                    fontes.append(fonte)
                if len(fontes) == total:
                    break
                if len(pagina) < 10 or len(fontes) > total:
                    raise FalhaAPI(502, 'DataJud devolveu menos registros que a contagem informada. Referência preservada.',
                                   codigo='fonte_incompleta', aguardar=90)
                proximo = pagina[-1].get('sort')
                if not isinstance(proximo, list) or not proximo or proximo == cursor:
                    raise ValueError('Cursor inválido.')
                cursor = proximo
            else:
                raise FalhaAPI(502, 'Limite de paginação alcançado. Referência preservada.', codigo='fonte_incompleta', aguardar=90)
            if not fontes:
                raise FalhaAPI(404, 'Processo não encontrado nesta fonte/tribunal. Isso não comprova sua inexistência.',
                               codigo='fonte_nao_encontrado', aguardar=300)
            registros = []
            for fonte in fontes:
                movimentos = fonte.get('movimentos', [])
                if not isinstance(movimentos, list):
                    raise ValueError('Movimentos inválidos.')
                registros.append({'grau': fonte.get('grau'), 'classe': fonte.get('classe'),
                                  'orgaoJulgador': fonte.get('orgaoJulgador'), 'movimentos': movimentos})
            registros.sort(key=lambda r: json.dumps(r, sort_keys=True))
            return {'numero': numero, 'tribunal': tribunal, 'fonte': 'CNJ / DataJud', 'registros': registros}
        except requests.exceptions.SSLError as exc:
            raise FalhaAPI(502, 'Falha ao validar a conexão segura com o DataJud. Confira os certificados da rede.',
                           codigo='fonte_tls', aguardar=90) from exc
        except requests.exceptions.ProxyError as exc:
            raise FalhaAPI(502, 'Não foi possível conectar pelo proxy configurado para o DataJud.',
                           codigo='fonte_proxy', aguardar=90) from exc
        except requests.Timeout as exc:
            raise FalhaAPI(504, 'DataJud não respondeu no tempo de consulta. A última referência foi preservada.',
                           codigo='fonte_timeout', aguardar=90) from exc
        except requests.RequestException as exc:
            raise FalhaAPI(502, 'Falha de rede na comunicação com o DataJud. Referência preservada.',
                           codigo='fonte_rede', aguardar=90) from exc
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise FalhaAPI(502, 'DataJud devolveu um formato inesperado ou incompleto. Referência preservada.',
                           codigo='fonte_formato', aguardar=90) from exc
        finally:
            if sessao is not None:
                sessao.close()
