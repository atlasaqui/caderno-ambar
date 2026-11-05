"""Providências jurídicas e processamento de fila sem rede em transações SQLite."""
import hashlib
import json
import secrets
import time
from datetime import date, datetime
from pathlib import Path

from acompanhamento import FalhaAPI
from equipes import Equipes
from correio import entregar

ESTADOS = ('a_fazer','em_andamento','aguardando','em_revisao','concluida')
TRANSICOES = {
    'a_fazer': {'em_andamento','aguardando'},
    'em_andamento': {'aguardando','em_revisao'},
    'aguardando': {'a_fazer','em_andamento'},
    'em_revisao': {'em_andamento','concluida'},
    'concluida': {'a_fazer'},
}


class Escritorio(Equipes):
    def __init__(self, arquivo):
        super().__init__(arquivo)
        with self.conexao() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS providencias(
              id INTEGER PRIMARY KEY, org INTEGER NOT NULL REFERENCES organizacoes(id),
              caso INTEGER NOT NULL REFERENCES casos(id),versao INTEGER REFERENCES versoes(id),
              titulo TEXT NOT NULL,descricao TEXT NOT NULL DEFAULT '',
              responsavel INTEGER NOT NULL REFERENCES usuarios(id),revisor INTEGER NOT NULL REFERENCES usuarios(id),
              data_interna TEXT NOT NULL,prioridade TEXT NOT NULL CHECK(prioridade IN ('normal','alta','baixa')),
              estado TEXT NOT NULL DEFAULT 'a_fazer',evidencia TEXT NOT NULL DEFAULT '',
              criado_por INTEGER NOT NULL REFERENCES usuarios(id),criado REAL NOT NULL,atualizado REAL NOT NULL,
              revisao INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS eventos_providencia(
              id INTEGER PRIMARY KEY,providencia INTEGER NOT NULL REFERENCES providencias(id),
              usuario INTEGER NOT NULL REFERENCES usuarios(id),instante REAL NOT NULL,acao TEXT NOT NULL,detalhes TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_providencias_org ON providencias(org,estado,data_interna);
            ''')
            cols={r['name'] for r in db.execute('PRAGMA table_info(emails)')}
            for nome,tipo in [('lease','REAL DEFAULT 0'),('claim',"TEXT DEFAULT ''")]:
                if nome not in cols:db.execute(f'ALTER TABLE emails ADD COLUMN {nome} {tipo}')
            db.execute('INSERT OR IGNORE INTO migracoes VALUES(2,?)',(time.time(),))

    def me(self, usuario, org):
        with self.conexao() as db:
            org=self.org(db,usuario,org)
            u=db.execute('SELECT email FROM usuarios WHERE id=?',(usuario,)).fetchone()
            return {'id':usuario,'email':u['email'],'org':org}

    def carteira_exportavel(self, usuario, org):
        with self.conexao() as db:
            org=self.org(db,usuario,org)
            return [dict(r) for r in db.execute('''SELECT c.numero,c.tribunal,c.apelido,u.email AS responsavel_email,
              c.ultima_ok,c.erro,EXISTS(SELECT 1 FROM conferencias f WHERE f.versao=c.versao_id) AS conferido
              FROM casos c LEFT JOIN usuarios u ON u.id=c.responsavel WHERE c.org=? ORDER BY c.id''',(org,))]

    def participante(self, db, org, usuario):
        if not db.execute('SELECT 1 FROM membros WHERE org=? AND usuario=?',(org,usuario)).fetchone():
            raise FalhaAPI(400,'Responsável e revisor devem pertencer ao escritório.')

    @staticmethod
    def texto(dados, campo, minimo, maximo):
        valor=dados.get(campo,'')
        if not isinstance(valor,str) or not minimo<=len(valor.strip())<=maximo:
            raise FalhaAPI(400,f'{campo}: informe de {minimo} a {maximo} caracteres.')
        return valor.strip()

    def criar_providencia(self, usuario, dados):
        titulo=self.texto(dados,'titulo',3,160)
        descricao=self.texto(dados,'descricao',0,4000)
        try:
            valor_data=dados.get('data_interna','')
            data=date.fromisoformat(valor_data).isoformat() if valor_data else ''
            responsavel=int(dados['responsavel']);revisor=int(dados['revisor']);caso=int(dados['caso'])
        except (ValueError,TypeError,KeyError):raise FalhaAPI(400,'Informe processo, responsável e revisor válidos. A data interna é opcional, no formato AAAA-MM-DD.')
        prioridade=dados.get('prioridade','normal')
        if prioridade not in ('normal','alta','baixa'):raise FalhaAPI(400,'Prioridade inválida.')
        with self.conexao() as db:
            db.execute('BEGIN IMMEDIATE')
            c=self.caso(db,usuario,caso)
            if c['arquivado']:raise FalhaAPI(409,'Reative o processo antes de criar uma providência.')
            self.participante(db,c['org'],responsavel);self.participante(db,c['org'],revisor)
            v=dados.get('versao') or None
            if v is not None and not db.execute('SELECT 1 FROM versoes WHERE caso=? AND id=?',(caso,v)).fetchone():
                raise FalhaAPI(400,'Versão não pertence ao processo.')
            agora=time.time()
            id=db.execute('''INSERT INTO providencias(org,caso,versao,titulo,descricao,responsavel,revisor,data_interna,prioridade,criado_por,criado,atualizado)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(c['org'],caso,v,titulo,descricao,responsavel,revisor,data,prioridade,usuario,agora,agora)).lastrowid
            db.execute('INSERT INTO eventos_providencia(providencia,usuario,instante,acao,detalhes) VALUES(?,?,?,?,?)',
                       (id,usuario,agora,'criada',json.dumps({'titulo':titulo,'responsavel':responsavel,'revisor':revisor,'data_interna':data},ensure_ascii=False)))
            self.audit(db,c['org'],usuario,'providência criada',caso)
        return {'id':id,'status':'Providência criada.'}

    def rotina(self, usuario, org, filtro='minhas', pagina=1, busca=''):
        if filtro not in ('minhas','equipe','atrasadas','revisar','concluidas'):raise FalhaAPI(400,'Filtro de rotina inválido.')
        pagina=max(1,int(pagina));busca=str(busca)[:200]
        with self.conexao() as db:
            org=self.org(db,usuario,org)
            where=['p.org=?'];args=[org]
            if filtro=='minhas':where+=['p.responsavel=?',"p.estado!='concluida'"];args.append(usuario)
            if filtro=='atrasadas':where += ["p.estado!='concluida'","p.data_interna!=''",'p.data_interna<?'];args.append(date.today().isoformat())
            if filtro=='revisar':where += ["p.estado='em_revisao'",'p.revisor=?'];args.append(usuario)
            if filtro=='concluidas':where += ["p.estado='concluida'"]
            if filtro=='equipe':where += ["p.estado!='concluida'"]
            if busca:where += ['(p.titulo LIKE ? OR c.apelido LIKE ? OR c.numero LIKE ?)'];args.extend(['%'+busca+'%']*3)
            base=' FROM providencias p JOIN casos c ON c.id=p.caso JOIN usuarios u ON u.id=p.responsavel JOIN usuarios r ON r.id=p.revisor WHERE '+' AND '.join(where)
            total=db.execute('SELECT count(*)'+base,args).fetchone()[0]
            itens=[dict(r) for r in db.execute('SELECT p.*,c.apelido,c.numero,u.email AS responsavel_email,r.email AS revisor_email'+base+
                  " ORDER BY p.data_interna,CASE p.prioridade WHEN 'alta' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,p.id LIMIT 25 OFFSET ?",[*args,(pagina-1)*25])]
            resumo=dict(db.execute('''SELECT count(*) AS total,
              COALESCE(sum(CASE WHEN responsavel=? AND estado!='concluida' THEN 1 ELSE 0 END),0) AS minhas,
              COALESCE(sum(CASE WHEN data_interna!='' AND data_interna<? AND estado!='concluida' THEN 1 ELSE 0 END),0) AS atrasadas,
              COALESCE(sum(CASE WHEN revisor=? AND estado='em_revisao' THEN 1 ELSE 0 END),0) AS revisar
              FROM providencias WHERE org=?''',(usuario,date.today().isoformat(),usuario,org)).fetchone())
        return {'itens':itens,'total':total,'pagina':pagina,'resumo':resumo}

    def providencia(self, db, usuario, id):
        p=db.execute('SELECT * FROM providencias WHERE id=?',(id,)).fetchone()
        if not p:raise FalhaAPI(404,'Providência não encontrada.')
        self.org(db,usuario,p['org'])
        return p

    def alterar_providencia(self, usuario, id, dados):
        with self.conexao() as db:
            db.execute('BEGIN IMMEDIATE')
            p=self.providencia(db,usuario,id)
            if dados.get('revisao')!=p['revisao']:raise FalhaAPI(409,'Esta providência mudou. Atualize a rotina antes de continuar.')
            admin=db.execute('SELECT papel FROM membros WHERE org=? AND usuario=?',(p['org'],usuario)).fetchone()['papel']=='admin'
            if usuario not in (p['responsavel'],p['revisor']) and not admin:raise FalhaAPI(403,'Somente responsável, revisor ou administrador pode alterar a providência.')
            estado=dados.get('estado',p['estado'])
            comentario=self.texto(dados,'comentario',0,2000)
            evidencia=dados.get('evidencia',p['evidencia'])
            if not isinstance(evidencia,str) or len(evidencia)>4000:raise FalhaAPI(400,'Evidência deve ter até 4000 caracteres.')
            if estado!=p['estado']:
                if estado not in TRANSICOES.get(p['estado'],set()):raise FalhaAPI(409,'Transição de estado não permitida.')
                if estado=='em_revisao' and not evidencia.strip():raise FalhaAPI(400,'Descreva o resultado ou a evidência antes de enviar à revisão.')
                if estado=='concluida' and usuario!=p['revisor'] and not admin:raise FalhaAPI(403,'A conclusão precisa ser aprovada pelo revisor ou administrador.')
                if estado=='concluida' and not evidencia.strip():raise FalhaAPI(409,'Providência sem evidência para revisar.')
                if p['estado']=='concluida' and not comentario:raise FalhaAPI(400,'Informe o motivo da reabertura.')
            if estado==p['estado'] and not comentario and evidencia==p['evidencia']:raise FalhaAPI(400,'Informe uma alteração ou comentário.')
            agora=time.time()
            db.execute('UPDATE providencias SET estado=?,evidencia=?,atualizado=?,revisao=revisao+1 WHERE id=?',(estado,evidencia.strip(),agora,id))
            db.execute('INSERT INTO eventos_providencia(providencia,usuario,instante,acao,detalhes) VALUES(?,?,?,?,?)',
                       (id,usuario,agora,'atualizada',json.dumps({'antes':p['estado'],'depois':estado,'comentario':comentario,'evidencia':evidencia.strip()},ensure_ascii=False)))
            self.audit(db,p['org'],usuario,'providência: '+estado,p['caso'])
        return {'status':'Providência atualizada.'}

    def historico_providencia(self, usuario, id):
        with self.conexao() as db:
            self.providencia(db,usuario,id)
            return [dict(r) for r in db.execute('''SELECT e.*,u.email FROM eventos_providencia e JOIN usuarios u ON u.id=e.usuario
              WHERE e.providencia=? ORDER BY e.id DESC''',(id,))]

    def consultas_tick(self):
        with self.conexao() as db:
            tarefas=[dict(r) for r in db.execute('''SELECT t.caso,c.responsavel,t.solicitante FROM tarefas t JOIN casos c ON c.id=t.caso
              WHERE (c.intervalo>0 OR t.solicitada=1) AND c.arquivado=0 AND t.proxima<=? AND t.lease<=? AND t.tentativas<5
              AND COALESCE(t.codigo,'') NOT IN ('fonte_credencial','fonte_configuracao','fonte_tls','fonte_proxy','fonte_formato','fonte_nao_encontrado','processamento')
              ORDER BY t.proxima,t.caso LIMIT 3''',(time.time(),time.time()))]
        for t in tarefas:
            try:self.consultar(t['solicitante'] or t['responsavel'],t['caso'])
            except FalhaAPI as exc:
                if exc.codigo in ('fonte_aguardando','consulta_aguardando'):
                    with self.conexao() as db:
                        db.execute('UPDATE tarefas SET proxima=max(proxima,?) WHERE caso=?',(time.time()+(exc.aguardar or 90),t['caso']))
                elif exc.status in (403,404) or exc.codigo=='fonte_configuracao':
                    with self.conexao() as db:
                        db.execute("UPDATE tarefas SET solicitada=0,codigo='fonte_configuracao',erro=? WHERE caso=?",('Confira acesso ao escritório e confirmação de e-mail.',t['caso']))

    def email_tick(self):
        agora=time.time()
        for _ in range(5):
            claim=secrets.token_hex(16)
            with self.conexao() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute("UPDATE emails SET estado='pendente',claim='' WHERE estado='enviando' AND lease<?",(agora,))
                e=db.execute("SELECT * FROM emails WHERE estado='pendente' AND tentativas<5 AND proxima<=? ORDER BY proxima,id LIMIT 1",(agora,)).fetchone()
                if not e:return
                db.execute("UPDATE emails SET estado='enviando',lease=?,claim=?,tentativas=tentativas+1 WHERE id=?",(agora+120,claim,e['id']))
            # Revalida o destinatário imediatamente antes do envio, em conexão curta.
            with self.conexao() as db:
                destinatario=db.execute('''SELECT u.email FROM emails e JOIN usuarios u ON u.id=e.usuario
                  JOIN versoes v ON v.id=e.versao JOIN casos c ON c.id=v.caso
                  JOIN membros m ON m.org=c.org AND m.usuario=e.usuario
                  JOIN preferencias p ON p.usuario=e.usuario AND p.email=1
                  WHERE e.id=? AND e.claim=? AND e.estado='enviando' ''',(e['id'],claim)).fetchone()
            if not destinatario:
                with self.conexao() as db:db.execute("UPDATE emails SET estado='cancelado',lease=0,erro=? WHERE id=? AND claim=?",('Acesso ou preferência revogados.',e['id'],claim))
                continue
            try:
                estado=entregar(Path(self.arquivo).parent,destinatario['email'],'Há uma atualização no Caderno Âmbar',
                                {'versao':e['versao'],'orientacao':'Entre no caderno para conferir.'},f'notificacao-{e["id"]}')
                with self.conexao() as db:db.execute('UPDATE emails SET estado=?,lease=0,erro=NULL WHERE id=? AND claim=?',(estado,e['id'],claim))
            except (OSError,FalhaAPI):
                with self.conexao() as db:
                    db.execute("UPDATE emails SET estado='pendente',lease=0,proxima=?,erro=? WHERE id=? AND claim=?",
                               (time.time()+min(3600,60*2**min(e['tentativas'],5)),'Falha no canal de e-mail.',e['id'],claim))

    def operacao(self, usuario, org):
        with self.conexao() as db:
            org=self.org(db,usuario,org,True)
            return {'consultas':[dict(r) for r in db.execute('''SELECT t.*,c.apelido,c.numero FROM tarefas t JOIN casos c ON c.id=t.caso
               WHERE c.org=? AND c.intervalo>0 ORDER BY t.tentativas DESC,t.proxima LIMIT 100''',(org,))],
               'emails':[dict(r) for r in db.execute('''SELECT e.id,e.estado,e.tentativas,e.erro,e.proxima FROM emails e
               JOIN versoes v ON v.id=e.versao JOIN casos c ON c.id=v.caso WHERE c.org=? ORDER BY e.id DESC LIMIT 100''',(org,))]}

    def revogar(self, usuario, org, alvo):
        with self.conexao() as db:
            db.execute('BEGIN IMMEDIATE')
            org=self.org(db,usuario,org,True)
            if int(alvo)==usuario:raise FalhaAPI(400,'Não remova seu próprio acesso por esta ação.')
            db.execute('DELETE FROM membros WHERE org=? AND usuario=?',(org,alvo))
            db.execute('UPDATE casos SET responsavel=? WHERE org=? AND responsavel=?',(usuario,org,alvo))
            tarefas=db.execute('SELECT * FROM providencias WHERE org=? AND (responsavel=? OR revisor=?)',(org,alvo,alvo)).fetchall()
            for p in tarefas:
                db.execute('''UPDATE providencias SET responsavel=CASE WHEN responsavel=? THEN ? ELSE responsavel END,
                   revisor=CASE WHEN revisor=? THEN ? ELSE revisor END,revisao=revisao+1,atualizado=? WHERE id=?''',
                   (alvo,usuario,alvo,usuario,time.time(),p['id']))
                db.execute('INSERT INTO eventos_providencia(providencia,usuario,instante,acao,detalhes) VALUES(?,?,?,?,?)',
                           (p['id'],usuario,time.time(),'reatribuída após revogação',json.dumps({'usuario_removido':int(alvo)})))
            db.execute('''UPDATE emails SET estado='cancelado',erro='Acesso revogado.' WHERE usuario=? AND estado='pendente'
              AND versao IN (SELECT v.id FROM versoes v JOIN casos c ON c.id=v.caso WHERE c.org=?)''',(alvo,org))
            self.audit(db,org,usuario,'acesso revogado e responsabilidades reatribuídas')
        return {'status':'Acesso revogado; responsabilidades reatribuídas ao administrador.'}

    def reprocessar(self, usuario, org, tipo, id):
        with self.conexao() as db:
            org=self.org(db,usuario,org,True)
            if tipo=='consulta':
                c=self.caso(db,usuario,id)
                if c['org']!=org:raise FalhaAPI(403,'Escritório incompatível.')
                t=db.execute('SELECT * FROM tarefas WHERE caso=?',(id,)).fetchone()
                if not t or t['lease']>time.time():raise FalhaAPI(409,'Tarefa inexistente ou em execução.')
                db.execute('UPDATE tarefas SET tentativas=0,proxima=?,erro=NULL WHERE caso=?',(time.time(),id))
            elif tipo=='email':
                e=db.execute('''SELECT e.* FROM emails e JOIN versoes v ON v.id=e.versao JOIN casos c ON c.id=v.caso
                  WHERE e.id=? AND c.org=?''',(id,org)).fetchone()
                if not e:raise FalhaAPI(404,'Mensagem não encontrada.')
                if e['estado']!='pendente':raise FalhaAPI(409,'Somente mensagens pendentes podem ser reprocessadas.')
                db.execute('UPDATE emails SET tentativas=0,proxima=?,erro=NULL WHERE id=?',(time.time(),id))
            else:raise FalhaAPI(400,'Tipo de fila inválido.')
            self.audit(db,org,usuario,'reprocessamento: '+tipo)
        return {'status':'Reprocessamento solicitado.'}
