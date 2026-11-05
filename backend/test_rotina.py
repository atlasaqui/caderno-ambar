import tempfile
import unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch
from rotina import Escritorio
from acompanhamento import FalhaAPI


class RotinaTests(unittest.TestCase):
    def setUp(self):
        pasta=Path(__file__).resolve().parents[1]/'output';pasta.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=pasta)
        self.c=Escritorio(Path(self.tmp.name)/'rotina.sqlite3')
        self.admin=self.conta('admin@example.com');self.org=self.c.contexto(self.admin)[0]['id']
        self.caso=self.c.demonstracao(self.admin)['id'];self.v=self.c.consultar(self.admin,self.caso)['versao_id']

    def tearDown(self):self.tmp.cleanup()

    def conta(self,email):return self.c.usuario(self.c.autenticar({'email':email,'senha':'senha-longa-de-teste'},True))
    def membro(self,email):
        u=self.conta(email);token=self.c.convidar(self.admin,self.org,email)['token'];self.c.aceitar(u,token);return u
    def criar(self,responsavel=None,revisor=None):
        return self.c.criar_providencia(self.admin,{'caso':self.caso,'versao':self.v,'titulo':'Analisar movimentação',
           'descricao':'Conferir os dados e indicar providências.','responsavel':responsavel or self.admin,
           'revisor':revisor or self.admin,'data_interna':date.today().isoformat(),'prioridade':'normal'})['id']

    def test_fluxo_responsavel_execucao_revisor(self):
        executor=self.membro('executor@example.com');revisor=self.membro('revisor@example.com')
        id=self.criar(executor,revisor)
        self.c.alterar_providencia(executor,id,{'revisao':1,'estado':'em_andamento'})
        with self.assertRaises(FalhaAPI):self.c.alterar_providencia(executor,id,{'revisao':2,'estado':'em_revisao'})
        self.c.alterar_providencia(executor,id,{'revisao':2,'estado':'em_revisao','evidencia':'Análise registrada no documento interno.'})
        self.assertEqual(self.c.rotina(revisor,self.org,'revisar')['total'],1)
        with self.assertRaises(FalhaAPI) as exc:self.c.alterar_providencia(executor,id,{'revisao':3,'estado':'concluida'})
        self.assertEqual(exc.exception.status,403)
        self.c.alterar_providencia(revisor,id,{'revisao':3,'estado':'concluida','comentario':'Análise revisada.'})
        self.assertEqual(self.c.rotina(executor,self.org,'minhas')['total'],0)
        self.assertEqual(self.c.rotina(executor,self.org,'concluidas')['total'],1)
        self.assertEqual(len(self.c.historico_providencia(executor,id)),4)

    def test_isolamento_e_concorrencia(self):
        id=self.criar();outro=self.conta('outro@example.com')
        with self.assertRaises(FalhaAPI):self.c.historico_providencia(outro,id)
        self.c.alterar_providencia(self.admin,id,{'revisao':1,'estado':'em_andamento'})
        with self.assertRaises(FalhaAPI) as exc:self.c.alterar_providencia(self.admin,id,{'revisao':1,'estado':'aguardando'})
        self.assertEqual(exc.exception.status,409)

    def test_email_envia_fora_da_transacao(self):
        with self.c.conexao() as db:db.execute('INSERT INTO preferencias VALUES(?,1)',(self.admin,))
        with self.c.conexao() as db:db.execute('UPDATE casos SET etapa=1 WHERE id=?',(self.caso,))
        self.c.consultar(self.admin,self.caso)
        def rede(*args,**kwargs):
            # Uma gravação concorrente falharia se email_tick mantivesse BEGIN IMMEDIATE aberto.
            with self.c.conexao() as db:db.execute('INSERT INTO limites VALUES(?,?,?)',('gravacao-durante-envio',0,1))
            return 'aceito_pelo_smtp'
        with patch('rotina.entregar',side_effect=rede) as envio:self.c.email_tick();envio.assert_called_once()
        with self.c.conexao() as db:self.assertEqual(db.execute('SELECT estado FROM emails').fetchone()[0],'aceito_pelo_smtp')

    def test_email_revogacao_e_preferencia(self):
        membro=self.membro('avisos@example.com')
        with self.c.conexao() as db:
            db.execute('INSERT INTO preferencias VALUES(?,1)',(membro,))
            db.execute('INSERT INTO emails(usuario,versao) VALUES(?,?)',(membro,self.v))
            db.execute('UPDATE preferencias SET email=0 WHERE usuario=?',(membro,))
        with patch('rotina.entregar') as envio:self.c.email_tick();envio.assert_not_called()
        with self.c.conexao() as db:self.assertEqual(db.execute('SELECT estado FROM emails').fetchone()[0],'cancelado')
        id=self.criar(membro,membro);self.c.revogar(self.admin,self.org,membro)
        p=self.c.rotina(self.admin,self.org,'equipe')['itens'][0]
        self.assertEqual(p['responsavel'],self.admin);self.assertEqual(p['revisor'],self.admin)

    def test_reprocessamento_exige_admin(self):
        membro=self.membro('membro@example.com');self.c.alterar(self.admin,self.caso,{'intervalo':3600})
        with self.c.conexao() as db:db.execute('UPDATE tarefas SET tentativas=5,erro=?',('Fonte indisponível',))
        self.assertEqual(self.c.operacao(self.admin,self.org)['consultas'][0]['tentativas'],5)
        with self.assertRaises(FalhaAPI):self.c.reprocessar(membro,self.org,'consulta',self.caso)
        self.c.reprocessar(self.admin,self.org,'consulta',self.caso)
        self.assertEqual(self.c.operacao(self.admin,self.org)['consultas'][0]['tentativas'],0)


if __name__=='__main__':unittest.main()
