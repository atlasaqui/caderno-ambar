"""Migração aditiva, equipes, versões, tarefas e auditoria do Caderno Âmbar."""
import csv
import hashlib
import io
import json
import os
import secrets
import sqlite3
import time
import math
from acompanhamento import Caderno, FalhaAPI
from fontes import DataJudValidado, Demonstracao, diferencas, normalizar, serializar, validar_numero, versao


class Equipes(Caderno):
    def __init__(self, arquivo):
        super().__init__(arquivo)
        with self.conexao() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS migracoes(versao INTEGER PRIMARY KEY, aplicada REAL);
            CREATE TABLE IF NOT EXISTS organizacoes(id INTEGER PRIMARY KEY,nome TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS membros(org INTEGER REFERENCES organizacoes(id),usuario INTEGER REFERENCES usuarios(id),papel TEXT NOT NULL CHECK(papel IN ('admin','membro')), PRIMARY KEY(org,usuario));
            CREATE TABLE IF NOT EXISTS convites(token TEXT PRIMARY KEY,org INTEGER REFERENCES organizacoes(id),email TEXT NOT NULL,expira REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS recuperacoes(token TEXT PRIMARY KEY,usuario INTEGER REFERENCES usuarios(id),expira REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS auditoria(id INTEGER PRIMARY KEY,org INTEGER,usuario INTEGER,acao TEXT,caso INTEGER,instante REAL);
            CREATE TABLE IF NOT EXISTS versoes(id INTEGER PRIMARY KEY,caso INTEGER REFERENCES casos(id),hash TEXT,dados TEXT,diferenca TEXT,instante REAL,UNIQUE(caso,hash));
            CREATE TABLE IF NOT EXISTS conferencias(id INTEGER PRIMARY KEY,versao INTEGER REFERENCES versoes(id),usuario INTEGER REFERENCES usuarios(id),instante REAL,observacao TEXT,UNIQUE(versao,usuario));
            CREATE TABLE IF NOT EXISTS notificacoes(id INTEGER PRIMARY KEY,org INTEGER,caso INTEGER,versao INTEGER REFERENCES versoes(id),texto TEXT,instante REAL,UNIQUE(caso,versao));
            CREATE TABLE IF NOT EXISTS tarefas(caso INTEGER PRIMARY KEY REFERENCES casos(id),proxima REAL,tentativas INTEGER DEFAULT 0,lease REAL DEFAULT 0,erro TEXT);
            CREATE TABLE IF NOT EXISTS limites(chave TEXT PRIMARY KEY,inicio REAL,quantidade INTEGER);
            CREATE TABLE IF NOT EXISTS preferencias(usuario INTEGER PRIMARY KEY REFERENCES usuarios(id),email INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS emails(id INTEGER PRIMARY KEY,usuario INTEGER,versao INTEGER,estado TEXT DEFAULT 'pendente',tentativas INTEGER DEFAULT 0,proxima REAL DEFAULT 0,erro TEXT,UNIQUE(usuario,versao));
            CREATE TABLE IF NOT EXISTS fontes_estado(fonte TEXT PRIMARY KEY,proxima REAL NOT NULL DEFAULT 0,reserva REAL NOT NULL DEFAULT 0,motivo TEXT NOT NULL DEFAULT '');
            ''')
            colunas = {r['name'] for r in db.execute('PRAGMA table_info(casos)')}
            for nome, tipo in [('org','INTEGER REFERENCES organizacoes(id)'),('responsavel','INTEGER REFERENCES usuarios(id)'),
                               ('arquivado','INTEGER DEFAULT 0'),('etiquetas',"TEXT DEFAULT ''"),('observacoes',"TEXT DEFAULT ''"),
                               ('fonte',"TEXT DEFAULT 'datajud'"),('etapa','INTEGER DEFAULT 0'),('versao_id','INTEGER'),
                               ('ultima_ok','REAL'),('intervalo','INTEGER DEFAULT 0'),('erro','TEXT')]:
                if nome not in colunas:
                    db.execute(f'ALTER TABLE casos ADD COLUMN {nome} {tipo}')
            db.execute('CREATE INDEX IF NOT EXISTS idx_casos_org ON casos(org,arquivado)')
            db.execute('CREATE INDEX IF NOT EXISTS idx_auditoria_org ON auditoria(org,instante)')
            # Contas antigas recebem um escritório pessoal, sem apagar registros.
            for u in db.execute('SELECT id FROM usuarios').fetchall():
                self._org(db, u['id'])
            db.execute('INSERT OR IGNORE INTO migracoes VALUES(1,?)',(time.time(),))
            db.execute('INSERT OR IGNORE INTO migracoes VALUES(4,?)',(time.time(),))
            tarefas_colunas={r['name'] for r in db.execute('PRAGMA table_info(tarefas)')}
            for nome,tipo in [('solicitada','INTEGER NOT NULL DEFAULT 0'),('solicitante','INTEGER REFERENCES usuarios(id)'),('codigo',"TEXT DEFAULT ''")]:
                if nome not in tarefas_colunas:db.execute(f'ALTER TABLE tarefas ADD COLUMN {nome} {tipo}')
            db.execute('INSERT OR IGNORE INTO migracoes VALUES(5,?)',(time.time(),))

    def conexao(self):
        # O context manager original garante commit/rollback/close.
        return super().conexao()

    def _org(self, db, usuario):
        m = db.execute('SELECT org FROM membros WHERE usuario=? ORDER BY org LIMIT 1',(usuario,)).fetchone()
        if m: return m['org']
        org = db.execute('INSERT INTO organizacoes(nome) VALUES(?)',('Meu escritório',)).lastrowid
        db.execute('INSERT INTO membros VALUES(?,?,?)',(org,usuario,'admin'))
        db.execute('UPDATE casos SET org=?,responsavel=? WHERE usuario=? AND org IS NULL',(org,usuario,usuario))
        return org

    def org(self, db, usuario, org=None, admin=False):
        org = int(org) if org is not None else self._org(db,usuario)
        m = db.execute('SELECT papel FROM membros WHERE org=? AND usuario=?',(org,usuario)).fetchone()
        if not m or admin and m['papel'] != 'admin': raise FalhaAPI(403,'Acesso ao escritório recusado.')
        return org

    def audit(self, db, org, usuario, acao, caso=None):
        db.execute('INSERT INTO auditoria(org,usuario,acao,caso,instante) VALUES(?,?,?,?,?)',(org,usuario,acao,caso,time.time()))

    def contexto(self, usuario):
        with self.conexao() as db:
            self._org(db,usuario)
            return [dict(r) for r in db.execute('SELECT o.*,m.papel FROM organizacoes o JOIN membros m ON o.id=m.org WHERE m.usuario=?',(usuario,))]

    def listar(self, usuario, org=None):
        with self.conexao() as db:
            org=self.org(db,usuario,org)
            return [dict(r) for r in db.execute('''SELECT c.*,u.email AS responsavel_email,
                EXISTS(SELECT 1 FROM conferencias f WHERE f.versao=c.versao_id) AS conferido,
                (SELECT diferenca FROM versoes v WHERE v.id=c.versao_id) AS diferenca
                FROM casos c LEFT JOIN usuarios u ON u.id=c.responsavel WHERE c.org=? ORDER BY c.id DESC LIMIT 1000''',(org,))]

    def caso(self, db, usuario, identificador):
        c=db.execute('SELECT * FROM casos WHERE id=?',(identificador,)).fetchone()
        if not c: raise FalhaAPI(404,'Caso não encontrado.')
        self.org(db,usuario,c['org'])
        return c

    def adicionar(self, usuario, dados):
        numero=validar_numero(dados.get('numero',''),dados.get('tribunal'))
        apelido=str(dados.get('apelido','')).strip()
        if len(apelido)>120: raise FalhaAPI(400,'Apelido deve ter até 120 caracteres.')
        with self.conexao() as db:
            db.execute('BEGIN IMMEDIATE')
            org=self.org(db,usuario,dados.get('org'))
            if db.execute('SELECT id FROM casos WHERE org=? AND numero=? AND tribunal=?',(org,numero,dados['tribunal'])).fetchone():
                raise FalhaAPI(409,'Processo já cadastrado neste escritório.')
            id=db.execute('INSERT INTO casos(usuario,org,responsavel,numero,tribunal,apelido) VALUES(?,?,?,?,?,?)',(usuario,org,usuario,numero,dados['tribunal'],apelido)).lastrowid
            self.audit(db,org,usuario,'processo adicionado',id)
            return {'id':id}

    def alterar(self, usuario, id, dados):
        with self.conexao() as db:
            c=self.caso(db,usuario,id)
            responsavel=int(dados.get('responsavel',c['responsavel']))
            if not db.execute('SELECT 1 FROM membros WHERE org=? AND usuario=?',(c['org'],responsavel)).fetchone():
                raise FalhaAPI(400,'Responsável não pertence ao escritório.')
            intervalo=int(dados.get('intervalo',c['intervalo']))
            if intervalo and intervalo<900: raise FalhaAPI(400,'Intervalo mínimo: 900 segundos; zero desativa.')
            for campo, limite in [('apelido',120),('etiquetas',200),('observacoes',2000)]:
                if not isinstance(dados.get(campo,c[campo]),str) or len(dados.get(campo,c[campo]))>limite: raise FalhaAPI(400,'Texto inválido: '+campo)
            db.execute('UPDATE casos SET apelido=?,etiquetas=?,observacoes=?,responsavel=?,arquivado=?,intervalo=? WHERE id=?',
                       (dados.get('apelido',c['apelido']),dados.get('etiquetas',c['etiquetas']),dados.get('observacoes',c['observacoes']),responsavel,int(bool(dados.get('arquivado',c['arquivado']))),intervalo,id))
            if intervalo: db.execute('INSERT INTO tarefas(caso,proxima) VALUES(?,?) ON CONFLICT(caso) DO UPDATE SET proxima=excluded.proxima',(id,time.time()+intervalo))
            else: db.execute('DELETE FROM tarefas WHERE caso=?',(id,))
            self.audit(db,c['org'],usuario,'processo alterado',id)
        return {'status':'atualizado'}

    def demonstracao(self, usuario, org=None):
        with self.conexao() as db:
            org=self.org(db,usuario,org)
            existe=db.execute("SELECT id FROM casos WHERE org=? AND fonte='demo'",(org,)).fetchone()
            if existe: return {'id':existe['id']}
            id=db.execute("INSERT INTO casos(usuario,org,responsavel,numero,tribunal,apelido,fonte) VALUES(?,?,?,?,?,?,?)",(usuario,org,usuario,f'DEMO-{org}','tjpe','Audiência — demonstração fictícia','demo')).lastrowid
            self.audit(db,org,usuario,'demonstração adicionada',id)
            return {'id':id}

    def agendar_consulta(self, usuario, id):
        agora=time.time()
        with self.conexao() as db:
            db.execute('BEGIN IMMEDIATE')
            c=self.caso(db,usuario,id)
            if c['arquivado']:raise FalhaAPI(409,'Processo arquivado.')
            if c['fonte']!='datajud':raise FalhaAPI(400,'Use a consulta imediata para a demonstração.')
            if os.environ.get('AMBAR_DATAJUD_HABILITADO')!='1':
                raise FalhaAPI(503,'A fonte DataJud precisa ser habilitada no servidor.',codigo='fonte_configuracao')
            db.execute('INSERT OR IGNORE INTO tarefas(caso,proxima) VALUES(?,?)',(id,agora))
            t=db.execute('SELECT * FROM tarefas WHERE caso=?',(id,)).fetchone()
            if t['solicitada'] or t['lease']>agora:
                return {'status':'A atualização já está na fila ou em andamento. Você pode continuar trabalhando.','agendada':True}
            fonte=db.execute("SELECT * FROM fontes_estado WHERE fonte='datajud'").fetchone()
            proxima=max(agora,(t['proxima'] if t['erro'] else 0) or 0,(c['ultima_ok'] or 0)+30,
                        max(fonte['proxima'],fonte['reserva']) if fonte else 0)
            db.execute("UPDATE tarefas SET solicitada=1,solicitante=?,codigo='',proxima=?,tentativas=CASE WHEN tentativas>=5 THEN 0 ELSE tentativas END WHERE caso=?",
                       (usuario,proxima,id))
            self.audit(db,c['org'],usuario,'atualização solicitada',id)
        return {'status':'Atualização solicitada. Consultaremos o DataJud em segundo plano; os dados salvos continuam disponíveis.',
                'agendada':True,'proxima_tentativa':proxima}

    def consultar(self, usuario, id, cliente=None):
        agora=time.time()
        fonte_real=False
        with self.conexao() as db:
            db.execute('BEGIN IMMEDIATE')
            c=dict(self.caso(db,usuario,id))
            if c['arquivado']: raise FalhaAPI(409,'Processo arquivado.')
            db.execute('INSERT OR IGNORE INTO tarefas(caso,proxima) VALUES(?,?)',(id,agora))
            t=db.execute('SELECT * FROM tarefas WHERE caso=?',(id,)).fetchone()
            if t['lease']>agora: raise FalhaAPI(409,'Consulta já está em execução.')
            if c['ultima_ok'] and agora-c['ultima_ok']<30 and c['fonte']!='demo': raise FalhaAPI(429,'Aguarde 30 segundos.')
            fonte_real=c['fonte']=='datajud' and cliente is None
            if fonte_real:
                if os.environ.get('AMBAR_DATAJUD_HABILITADO')!='1':
                    raise FalhaAPI(503,'Consulta DataJud desativada. Configure a fonte após avaliar finalidade e termos de uso.',codigo='fonte_configuracao')
                if t['tentativas'] and t['proxima']>agora:
                    espera=max(1,math.ceil(t['proxima']-agora))
                    raise FalhaAPI(429,f'Aguarde {espera} segundos antes de repetir este processo.',codigo='consulta_aguardando',aguardar=espera)
                db.execute("INSERT OR IGNORE INTO fontes_estado(fonte) VALUES('datajud')")
                fonte=db.execute("SELECT * FROM fontes_estado WHERE fonte='datajud'").fetchone()
                bloqueio=max(fonte['proxima'],fonte['reserva'])
                if bloqueio>agora:
                    espera=max(1,math.ceil(bloqueio-agora))
                    raise FalhaAPI(429,f'A fonte DataJud está em consulta ou aguardando nova tentativa. Aguarde {espera} segundos.',codigo='fonte_aguardando',aguardar=espera)
                db.execute("UPDATE fontes_estado SET reserva=? WHERE fonte='datajud'",(agora+120,))
            db.execute('UPDATE tarefas SET lease=? WHERE caso=?',(agora+600,id))
        try:
            if c['fonte']=='datajud' and os.environ.get('AMBAR_DATAJUD_HABILITADO')!='1' and cliente is None:
                raise FalhaAPI(503,'Consulta DataJud desativada. Configure a fonte após avaliar finalidade e termos de uso.')
            atual=normalizar((cliente or (Demonstracao(c['etapa']) if c['fonte']=='demo' else DataJudValidado())).buscar(c['tribunal'],c['numero']))
            with self.conexao() as db:
                db.execute('BEGIN IMMEDIATE')
                c=dict(self.caso(db,usuario,id))
                anterior=json.loads(c['snapshot']) if c['snapshot'] else None
                diff=diferencas(anterior,atual)
                if diff['tipo']=='sem diferença' and c['versao_id']:
                    v=c['versao_id']
                else:
                    # Cada transição recebe uma versão, inclusive quando a fonte volta a um conteúdo antigo.
                    chave=versao(atual)+':'+str(c['versao_id'] or 0)
                    db.execute('INSERT INTO versoes(caso,hash,dados,diferenca,instante) VALUES(?,?,?,?,?)',(id,chave,serializar(atual),serializar(diff),agora))
                    v=db.execute('SELECT last_insert_rowid()').fetchone()[0]
                db.execute('UPDATE casos SET snapshot=?,versao_id=?,ultima_ok=?,erro=NULL WHERE id=?',(serializar(atual),v,agora,id))
                db.execute('INSERT INTO consultas(caso,instante,estado,anterior,atual) VALUES(?,?,?,?,?)',(id,agora,diff['tipo'],c['snapshot'],serializar(atual)))
                if diff['tipo'] not in ('primeiro registro','sem diferença'):
                    db.execute('INSERT OR IGNORE INTO notificacoes(org,caso,versao,texto,instante) VALUES(?,?,?,?,?)',(c['org'],id,v,diff['tipo'],agora))
                    for membro in db.execute('SELECT m.usuario FROM membros m JOIN preferencias p ON p.usuario=m.usuario WHERE m.org=? AND p.email=1',(c['org'],)).fetchall():
                        db.execute('INSERT OR IGNORE INTO emails(usuario,versao) VALUES(?,?)',(membro['usuario'],v))
                db.execute("UPDATE tarefas SET lease=0,tentativas=0,erro=NULL,codigo='',solicitada=0,solicitante=NULL,proxima=? WHERE caso=?",(time.time()+max(c['intervalo'],900),id))
                if fonte_real:
                    db.execute("UPDATE fontes_estado SET reserva=0,proxima=?,motivo='' WHERE fonte='datajud'",(time.time()+30,))
                self.audit(db,c['org'],usuario,'consulta: '+diff['tipo'],id)
            return {'estado':diff['tipo'],'dados':atual,'diferenca':diff,'versao_id':v}
        except Exception as exc:
            mensagem=str(exc) if isinstance(exc,FalhaAPI) else 'Erro de processamento da fonte.'
            espera=max(min(3600,90*2**min(t['tentativas'],6)),getattr(exc,'aguardar',None) or 0)
            codigo=getattr(exc,'codigo',None) or 'processamento'
            transitoria=codigo in ('fonte_limite','fonte_sobrecarregada','fonte_timeout','fonte_rede','fonte_http','fonte_incompleta')
            proxima=time.time()+espera
            with self.conexao() as db:
                db.execute('UPDATE tarefas SET lease=0,tentativas=tentativas+1,erro=?,codigo=?,proxima=?,solicitada=CASE WHEN ? THEN solicitada ELSE 0 END WHERE caso=?',
                           (mensagem,codigo,proxima,int(transitoria and t['tentativas']<4),id))
                if fonte_real:
                    db.execute("UPDATE fontes_estado SET reserva=0,proxima=?,motivo=? WHERE fonte='datajud'",(proxima,mensagem))
                db.execute('UPDATE casos SET erro=? WHERE id=?',(mensagem,id))
                db.execute('INSERT INTO consultas(caso,instante,estado,erro) VALUES(?,?,?,?)',(id,agora,'falha',mensagem))
                self.audit(db,c['org'],usuario,'falha de consulta: '+(getattr(exc,'codigo',None) or 'processamento'),id)
            if isinstance(exc,FalhaAPI):
                if fonte_real:exc.aguardar=math.ceil(espera)
                raise
            raise FalhaAPI(502,mensagem) from exc

    def revisar(self, usuario, id, versao_id, observacao=''):
        if not isinstance(observacao,str) or len(observacao)>2000: raise FalhaAPI(400,'Observação inválida.')
        with self.conexao() as db:
            c=self.caso(db,usuario,id)
            if not db.execute('SELECT 1 FROM versoes WHERE id=? AND caso=?',(versao_id,id)).fetchone(): raise FalhaAPI(409,'Versão não encontrada. Atualize a tela.')
            db.execute('INSERT OR IGNORE INTO conferencias(versao,usuario,instante,observacao) VALUES(?,?,?,?)',(versao_id,usuario,time.time(),observacao))
            self.audit(db,c['org'],usuario,'versão conferida',id)
        return {'status':'conferido','versao_id':versao_id}

    def detalhe(self, usuario, id):
        with self.conexao() as db:
            self.caso(db,usuario,id)
            return {'versoes':[dict(r) for r in db.execute('SELECT * FROM versoes WHERE caso=? ORDER BY id DESC LIMIT 100',(id,))],
                    'conferencias':[dict(r) for r in db.execute('SELECT f.*,u.email FROM conferencias f JOIN versoes v ON v.id=f.versao JOIN usuarios u ON u.id=f.usuario WHERE v.caso=? ORDER BY f.id DESC',(id,))]}

    def membros(self, usuario, org):
        with self.conexao() as db:
            org=self.org(db,usuario,org)
            return [dict(r) for r in db.execute('SELECT m.usuario,m.papel,u.email FROM membros m JOIN usuarios u ON u.id=m.usuario WHERE m.org=?',(org,))]

    def convidar(self, usuario, org, email):
        if not isinstance(email,str) or '@' not in email or len(email)>254: raise FalhaAPI(400,'E-mail inválido.')
        token=secrets.token_urlsafe(32)
        with self.conexao() as db:
            org=self.org(db,usuario,org,True)
            db.execute('INSERT INTO convites VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),org,email.lower(),time.time()+86400))
            self.audit(db,org,usuario,'convite criado')
        return {'token':token,'expira_em_segundos':86400}

    def aceitar(self, usuario, token):
        with self.conexao() as db:
            db.execute('BEGIN IMMEDIATE')
            convite=db.execute('SELECT * FROM convites WHERE token=? AND expira>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
            email=db.execute('SELECT email FROM usuarios WHERE id=?',(usuario,)).fetchone()['email']
            if not convite or convite['email']!=email: raise FalhaAPI(400,'Convite inválido ou destinado a outro e-mail.')
            db.execute("INSERT OR IGNORE INTO membros VALUES(?,?,'membro')",(convite['org'],usuario))
            db.execute('DELETE FROM convites WHERE token=?',(convite['token'],))
            self.audit(db,convite['org'],usuario,'convite aceito')
        return {'status':'aceito'}

    def revogar(self, usuario, org, alvo):
        with self.conexao() as db:
            self.org(db,usuario,org,True)
            if int(alvo)==usuario: raise FalhaAPI(400,'Não remova seu próprio acesso por esta ação.')
            db.execute('DELETE FROM membros WHERE org=? AND usuario=?',(org,alvo))
            db.execute('UPDATE casos SET responsavel=? WHERE org=? AND responsavel=?',(usuario,org,alvo))
            self.audit(db,int(org),usuario,'acesso revogado')
        return {'status':'revogado'}

    def importar(self, usuario, org, conteudo, confirmar=False):
        if not isinstance(conteudo,str) or len(conteudo)>100000: raise FalhaAPI(400,'CSV deve ter até 100 KB.')
        linhas=list(csv.DictReader(io.StringIO(conteudo),delimiter=';'))
        if len(linhas)>500: raise FalhaAPI(400,'Importe até 500 linhas por vez.')
        resultados=[]
        with self.conexao() as db:
            org=self.org(db,usuario,org)
            vistos={(c['numero'],c['tribunal']) for c in db.execute('SELECT numero,tribunal FROM casos WHERE org=?',(org,))}
        for n,d in enumerate(linhas,2):
            try:
                numero=validar_numero(d.get('numero'),d.get('tribunal'))
                if (numero,d['tribunal']) in vistos: raise FalhaAPI(409,'Duplicado na lista ou no escritório.')
                if len(d.get('apelido',''))>120: raise FalhaAPI(400,'Apelido excede 120 caracteres.')
                vistos.add((numero,d['tribunal']))
                resultado={'linha':n,'status':'válido','numero':numero}
                if confirmar: resultado.update(self.adicionar(usuario,{**d,'org':org}))
            except FalhaAPI as exc: resultado={'linha':n,'status':'rejeitado','erro':str(exc)}
            resultados.append(resultado)
        return {'confirmado':confirmar,'linhas':resultados}

    def tick(self):
        with self.conexao() as db:
            tarefas=[dict(r) for r in db.execute('''SELECT t.caso,c.responsavel FROM tarefas t JOIN casos c ON c.id=t.caso
              WHERE c.intervalo>0 AND c.arquivado=0 AND t.proxima<=? AND t.lease<=? AND t.tentativas<5 LIMIT 5''',(time.time(),time.time()))]
        for tarefa in tarefas:
            try: self.consultar(tarefa['responsavel'],tarefa['caso'])
            except FalhaAPI: pass
        self.email_tick()
        self.backup_tick()

    def backup_tick(self):
        from pathlib import Path
        from datetime import datetime, timezone
        from backup import copiar
        if os.environ.get('AMBAR_BACKUP_AUTOMATICO','0')!='1': return
        pasta=Path(os.environ.get('AMBAR_BACKUP_DIR',str(Path(self.arquivo).parent/'backups')))
        pasta.mkdir(parents=True,exist_ok=True)
        destino=pasta/(datetime.now(timezone.utc).strftime('%Y-%m-%d')+'.sqlite3')
        if not destino.exists():copiar(self.arquivo,destino)

    def email_tick(self):
        from correio import entregar
        pasta=__import__('pathlib').Path(self.arquivo).parent/'email-local'
        pasta.mkdir(exist_ok=True)
        with self.conexao() as db:
            db.execute('BEGIN IMMEDIATE')
            for e in db.execute('''SELECT e.*,u.email FROM emails e JOIN usuarios u ON u.id=e.usuario
                WHERE e.estado='pendente' AND e.tentativas<5 AND e.proxima<=? LIMIT 20''',(time.time(),)).fetchall():
                try:
                    # Nome estável evita arquivos duplicados após reinício.
                    estado=entregar(pasta.parent,e['email'],'Há uma atualização no Caderno Âmbar',{'versao':e['versao'],'orientacao':'Entre no caderno para conferir.'},f'notificacao-{e["id"]}')
                    db.execute('UPDATE emails SET estado=?,tentativas=tentativas+1 WHERE id=?',(estado,e['id']))
                except (OSError,FalhaAPI):
                    db.execute('UPDATE emails SET tentativas=tentativas+1,proxima=?,erro=? WHERE id=?',(time.time()+300,'Falha na caixa local',e['id']))
