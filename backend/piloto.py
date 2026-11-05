"""Preparação do piloto: migração preservadora, carteira paginada e e-mail verificado.

Este serviço estende a rotina existente. Não consulta fontes por conta própria e
não transforma a demonstração em prova de integração com um tribunal.
"""
import hashlib
import json
import re
import secrets
import sqlite3
import time
from datetime import date
from pathlib import Path

from acompanhamento import FalhaAPI
from backup import copiar
from correio import entregar
from rotina import Escritorio


class Piloto(Escritorio):
    def __init__(self, arquivo):
        super().__init__(arquivo)
        self.migrar_carteira()
        with self.conexao() as db:
            colunas = {r['name'] for r in db.execute('PRAGMA table_info(usuarios)')}
            if 'email_verificado' not in colunas:
                db.execute('ALTER TABLE usuarios ADD COLUMN email_verificado REAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS verificacoes_email (
                    token TEXT PRIMARY KEY, usuario INTEGER NOT NULL REFERENCES usuarios(id),
                    expira REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS solicitacoes_dados (
                    id INTEGER PRIMARY KEY, org INTEGER NOT NULL REFERENCES organizacoes(id),
                    usuario INTEGER NOT NULL REFERENCES usuarios(id), tipo TEXT NOT NULL,
                    motivo TEXT NOT NULL, instante REAL NOT NULL, estado TEXT NOT NULL DEFAULT 'pendente');
            ''')
            db.execute('INSERT OR IGNORE INTO migracoes VALUES(3,?)', (time.time(),))

    def migrar_carteira(self):
        # A restrição do projeto pessoal impedia o mesmo criador de acompanhar
        # um processo em dois escritórios. A reconstrução conserva os IDs e FKs.
        with self.conexao() as db:
            sql = db.execute("SELECT sql FROM sqlite_master WHERE name='casos'").fetchone()[0]
        if not re.search(r'UNIQUE\s*\(\s*usuario\s*,\s*numero\s*,\s*tribunal\s*\)', sql, re.I):
            return
        destino = Path(self.arquivo).with_name(Path(self.arquivo).name + '.antes-piloto-' + secrets.token_hex(4) + '.sqlite3')
        copiar(self.arquivo, destino)
        db = sqlite3.connect(self.arquivo, timeout=15)
        try:
            db.execute('PRAGMA foreign_keys=OFF')
            db.execute('BEGIN IMMEDIATE')
            novo = re.sub(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?["\[]?casos["\]]?', 'CREATE TABLE casos_novos', sql, count=1, flags=re.I)
            novo = re.sub(r'UNIQUE\s*\(\s*usuario\s*,\s*numero\s*,\s*tribunal\s*\)', 'UNIQUE(org, numero, tribunal)', novo, flags=re.I)
            db.execute(novo)
            colunas = ','.join('"' + r[1] + '"' for r in db.execute('PRAGMA table_info(casos)'))
            db.execute(f'INSERT INTO casos_novos({colunas}) SELECT {colunas} FROM casos')
            db.execute('DROP TABLE casos')
            db.execute('ALTER TABLE casos_novos RENAME TO casos')
            db.execute('CREATE INDEX idx_casos_org ON casos(org,arquivado)')
            if db.execute('PRAGMA foreign_key_check').fetchone():
                raise RuntimeError('Migração recusada: vínculos inválidos. Banco anterior preservado.')
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def conta(self, usuario):
        with self.conexao() as db:
            u = db.execute('SELECT id,email,email_verificado FROM usuarios WHERE id=?', (usuario,)).fetchone()
            return dict(u)

    def exigir_email(self, usuario):
        if not self.conta(usuario)['email_verificado']:
            raise FalhaAPI(403, 'Confirme seu e-mail na área da conta antes de compartilhar o escritório ou consultar processos reais.')

    def solicitar_verificacao(self, usuario):
        u = self.conta(usuario)
        if u['email_verificado']:
            return {'status': 'Seu e-mail já está confirmado.'}
        segredo = secrets.token_urlsafe(32)
        digest = hashlib.sha256(segredo.encode()).hexdigest()
        with self.conexao() as db:
            db.execute('DELETE FROM verificacoes_email WHERE usuario=?', (usuario,))
            db.execute('INSERT INTO verificacoes_email VALUES(?,?,?)', (digest, usuario, time.time()+1800))
        try:
            entregar(Path(self.arquivo).parent, u['email'], 'Confirme seu e-mail no Caderno Âmbar',
                     {'tipo': 'verificacao_email', 'token': segredo, 'validade_minutos': 30,
                      'orientacao': 'Na área da conta, cole este token. Não compartilhe o token.'})
        except Exception:
            with self.conexao() as db:
                db.execute('DELETE FROM verificacoes_email WHERE token=?', (digest,))
            raise
        return {'status': 'Instruções disponibilizadas no canal de e-mail configurado. O token vale por 30 minutos.'}

    def confirmar_email(self, usuario, token):
        digest = hashlib.sha256(str(token).encode()).hexdigest()
        with self.conexao() as db:
            db.execute('BEGIN IMMEDIATE')
            r = db.execute('SELECT 1 FROM verificacoes_email WHERE token=? AND usuario=? AND expira>?',
                           (digest, usuario, time.time())).fetchone()
            if not r:
                raise FalhaAPI(400, 'Token inválido, expirado ou pertencente a outra conta.')
            db.execute('UPDATE usuarios SET email_verificado=? WHERE id=?', (time.time(), usuario))
            db.execute('DELETE FROM verificacoes_email WHERE usuario=?', (usuario,))
        return {'status': 'E-mail confirmado.'}

    def convidar(self, usuario, org, email):
        self.exigir_email(usuario)
        return super().convidar(usuario, org, email)

    def aceitar(self, usuario, token):
        self.exigir_email(usuario)
        return super().aceitar(usuario, token)

    def agendar_consulta(self, usuario, id):
        self.exigir_email(usuario)
        return super().agendar_consulta(usuario,id)

    def consultar(self, usuario, id, cliente=None):
        with self.conexao() as db:
            caso = self.caso(db, usuario, id)
        if caso['fonte'] != 'demo':
            self.exigir_email(usuario)
        return super().consultar(usuario, id, cliente)

    def carteira(self, usuario, org=None, pagina=1, busca='', filtro='all'):
        if filtro not in ('all', 'pending', 'failed', 'archived'):
            raise FalhaAPI(400, 'Situação inválida.')
        pagina = max(1, int(pagina))
        busca = str(busca).strip()[:200]
        with self.conexao() as db:
            org = self.org(db, usuario, org)
            where = ['c.org=?', 'c.arquivado=?']
            args = [org, int(filtro == 'archived')]
            if filtro == 'pending':
                where.append('c.versao_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM conferencias f WHERE f.versao=c.versao_id)')
            if filtro == 'failed':
                where.append('c.erro IS NOT NULL')
            if busca:
                where.append('(c.numero LIKE ? OR c.apelido LIKE ? OR c.etiquetas LIKE ?)')
                args.extend(['%'+busca+'%']*3)
            base = ' FROM casos c LEFT JOIN usuarios u ON u.id=c.responsavel WHERE ' + ' AND '.join(where)
            total = db.execute('SELECT count(*)'+base, args).fetchone()[0]
            pagina = min(pagina, max(1, (total+19)//20))
            itens = [dict(r) for r in db.execute('''SELECT c.*,u.email AS responsavel_email,
                (SELECT t.proxima FROM tarefas t WHERE t.caso=c.id) AS proxima_tentativa,
                (SELECT t.solicitada FROM tarefas t WHERE t.caso=c.id) AS atualizacao_pendente,
                (SELECT t.lease FROM tarefas t WHERE t.caso=c.id) AS consulta_reservada_ate,
                (SELECT t.tentativas FROM tarefas t WHERE t.caso=c.id) AS tentativas_atualizacao,
                (SELECT t.codigo FROM tarefas t WHERE t.caso=c.id) AS codigo_falha,
                EXISTS(SELECT 1 FROM conferencias f WHERE f.versao=c.versao_id) AS conferido,
                (SELECT diferenca FROM versoes v WHERE v.id=c.versao_id) AS diferenca'''+base+
                ' ORDER BY c.id DESC LIMIT 20 OFFSET ?', [*args, (pagina-1)*20])]
            resumo = dict(db.execute('''SELECT count(*) AS total,
                COALESCE(sum(arquivado=0),0) AS ativos,
                COALESCE(sum(arquivado=0 AND versao_id IS NOT NULL AND NOT EXISTS(
                    SELECT 1 FROM conferencias f WHERE f.versao=casos.versao_id)),0) AS conferir,
                COALESCE(sum(arquivado=0 AND erro IS NOT NULL),0) AS falhas,
                COALESCE(sum(arquivado=0 AND intervalo>0 AND (ultima_ok IS NULL OR ultima_ok+intervalo<?)),0) AS atrasadas
                FROM casos WHERE org=?''', (time.time(), org)).fetchone())
            demo = db.execute("SELECT id,versao_id,etapa,conferido,snapshot FROM (SELECT c.*,EXISTS(SELECT 1 FROM conferencias f WHERE f.versao=c.versao_id) AS conferido FROM casos c WHERE org=? AND fonte='demo') LIMIT 1", (org,)).fetchone()
        return {'itens': itens, 'total': total, 'pagina': pagina, 'por_pagina': 20,
                'resumo': resumo, 'demonstracao': dict(demo) if demo else None}

    def resumo_diario(self, usuario, org):
        with self.conexao() as db:
            org = self.org(db, usuario, org)
            return dict(db.execute('''SELECT
                COALESCE(sum(responsavel=? AND estado!='concluida'),0) AS minhas,
                COALESCE(sum(data_interna!='' AND data_interna<? AND estado!='concluida'),0) AS vencidas,
                COALESCE(sum(revisor=? AND estado='em_revisao'),0) AS revisar
                FROM providencias WHERE org=?''', (usuario, date.today().isoformat(), usuario, org)).fetchone())

    def solicitar_dados(self, usuario, org, tipo, motivo):
        if tipo not in ('exclusao', 'retencao') or not isinstance(motivo, str) or not 10 <= len(motivo.strip()) <= 2000:
            raise FalhaAPI(400, 'Informe tipo válido e justificativa de 10 a 2.000 caracteres.')
        with self.conexao() as db:
            org = self.org(db, usuario, org, True)
            id = db.execute('INSERT INTO solicitacoes_dados(org,usuario,tipo,motivo,instante) VALUES(?,?,?,?,?)',
                            (org, usuario, tipo, motivo.strip(), time.time())).lastrowid
            self.audit(db, org, usuario, 'solicitação de dados: '+tipo)
        return {'id': id, 'status': 'Solicitação registrada para análise administrativa. Nenhum dado foi apagado.'}

    def exportar_escritorio(self, usuario, org):
        with self.conexao() as db:
            org = self.org(db, usuario, org, True)
            dados = {'formato': 1, 'exportado_em': time.time(), 'org': org}
            for tabela in ('organizacoes', 'membros', 'casos', 'notificacoes', 'auditoria', 'providencias', 'solicitacoes_dados'):
                campo = 'id' if tabela == 'organizacoes' else 'org'
                dados[tabela] = [dict(r) for r in db.execute(f'SELECT * FROM {tabela} WHERE {campo}=?', (org,))]
            for tabela in ('versoes', 'consultas', 'tarefas'):
                dados[tabela] = [dict(r) for r in db.execute(f'SELECT t.* FROM {tabela} t JOIN casos c ON c.id=t.caso WHERE c.org=?', (org,))]
            dados['conferencias'] = [dict(r) for r in db.execute('SELECT f.* FROM conferencias f JOIN versoes v ON v.id=f.versao JOIN casos c ON c.id=v.caso WHERE c.org=?', (org,))]
            dados['eventos_providencia'] = [dict(r) for r in db.execute('SELECT e.* FROM eventos_providencia e JOIN providencias p ON p.id=e.providencia WHERE p.org=?', (org,))]
            self.audit(db, org, usuario, 'exportação administrativa preparada')
        # Senhas, sessões, convites e tokens nunca fazem parte desta exportação.
        return dados
