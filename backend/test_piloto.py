"""Regressões de piloto com SQLite real e tokens locais sem envio externo."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from acompanhamento import FalhaAPI
from equipes import Equipes
from piloto import Piloto
from test_equipes import numero


class PilotoTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/'teste.sqlite3'
        self.c=Piloto(self.db)
        self.u=self.usuario('admin@example.com')
        self.org=self.c.contexto(self.u)[0]['id']

    def tearDown(self): self.tmp.cleanup()

    def usuario(self,email):
        return self.c.usuario(self.c.autenticar({'email':email,'senha':'senha-segura-de-teste'},True))

    def confirmar(self,u):
        anteriores=set((Path(self.tmp.name)/'email-local').glob('*.json'))
        with patch.dict(os.environ,{'AMBAR_ENV':'development'}):
            self.c.solicitar_verificacao(u)
        email=self.c.conta(u)['email']
        arquivos=[json.loads(p.read_text(encoding='utf-8')) for p in (Path(self.tmp.name)/'email-local').glob('*.json') if p not in anteriores]
        token=next(a['token'] for a in arquivos if a['para']==email)
        self.c.confirmar_email(u,token)
        return token

    def test_token_expiracao_uso_unico_e_destinatario(self):
        outro=self.usuario('outro@example.com')
        with patch.dict(os.environ,{'AMBAR_ENV':'development'}):self.c.solicitar_verificacao(self.u)
        arquivo=next((Path(self.tmp.name)/'email-local').glob('*.json'))
        token=json.loads(arquivo.read_text(encoding='utf-8'))['token']
        with self.c.conexao() as db:
            self.assertNotEqual(db.execute('SELECT token FROM verificacoes_email').fetchone()[0],token)
        with self.assertRaises(FalhaAPI):self.c.confirmar_email(outro,token)
        with self.c.conexao() as db:db.execute('UPDATE verificacoes_email SET expira=0')
        with self.assertRaises(FalhaAPI):self.c.confirmar_email(self.u,token)
        novo=self.confirmar(self.u)
        self.assertTrue(self.c.conta(self.u)['email_verificado'])
        with self.assertRaises(FalhaAPI):self.c.confirmar_email(self.u,novo)

    def test_compartilhar_exige_email_de_ambos(self):
        outro=self.usuario('outro@example.com')
        with self.assertRaises(FalhaAPI):self.c.convidar(self.u,self.org,'outro@example.com')
        self.confirmar(self.u)
        t=self.c.convidar(self.u,self.org,'outro@example.com')['token']
        with self.assertRaises(FalhaAPI):self.c.aceitar(outro,t)
        self.confirmar(outro);self.c.aceitar(outro,t)
        caso=self.c.demonstracao(self.u,self.org)['id']
        self.c.revogar(self.u,self.org,outro)
        with self.assertRaises(FalhaAPI):self.c.detalhe(outro,caso)

    def test_migracao_preserva_ids_historico_e_permite_orgs_distintas(self):
        antigo=Equipes(Path(self.tmp.name)/'antigo.sqlite3')
        u=antigo.usuario(antigo.autenticar({'email':'velho@example.com','senha':'senha-segura-de-teste'},True))
        org=antigo.contexto(u)[0]['id']
        caso=antigo.demonstracao(u,org)['id'];v=antigo.consultar(u,caso)['versao_id']
        novo=Piloto(antigo.arquivo);Piloto(antigo.arquivo)
        self.assertEqual(novo.detalhe(u,caso)['versoes'][0]['id'],v)
        with novo.conexao() as db:
            org2=db.execute("INSERT INTO organizacoes(nome) VALUES('Segundo')").lastrowid
            db.execute("INSERT INTO membros VALUES(?,?,'admin')",(org2,u))
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
        novo.adicionar(u,{'org':org,'numero':numero(),'tribunal':'tjpe'})
        novo.adicionar(u,{'org':org2,'numero':numero(),'tribunal':'tjpe'})
        with self.assertRaises(FalhaAPI):novo.adicionar(u,{'org':org2,'numero':numero(),'tribunal':'tjpe'})
        self.assertEqual(len(list(Path(self.tmp.name).glob('antigo.sqlite3.antes-piloto-*'))),1)

    def test_paginacao_busca_mais_de_mil_e_isolamento(self):
        with self.c.conexao() as db:
            db.executemany('INSERT INTO casos(usuario,org,responsavel,numero,tribunal,apelido) VALUES(?,?,?,?,?,?)',
                          [(self.u,self.org,self.u,str(i),'tjpe',f'Caso {i}') for i in range(1005)])
        primeira=self.c.carteira(self.u,self.org)
        self.assertEqual(primeira['total'],1005);self.assertEqual(len(primeira['itens']),20)
        ultima=self.c.carteira(self.u,self.org,51)
        self.assertEqual(len(ultima['itens']),5)
        self.assertEqual(self.c.carteira(self.u,self.org,busca='Caso 0')['total'],1)
        self.assertEqual(self.c.carteira(self.u,self.org)['resumo']['ativos'],1005)
        outro=self.usuario('estranho@example.com')
        with self.assertRaises(FalhaAPI):self.c.carteira(outro,self.org)
        with self.assertRaises(FalhaAPI):self.c.exportar_escritorio(outro,self.org)

    def test_exportacao_sem_segredos_e_solicitacao_nao_apaga(self):
        self.c.demonstracao(self.u,self.org)
        self.c.solicitar_dados(self.u,self.org,'exclusao','Solicito análise da necessidade de retenção.')
        dados=self.c.exportar_escritorio(self.u,self.org)
        self.assertEqual(len(dados['casos']),1)
        self.assertEqual(dados['solicitacoes_dados'][0]['estado'],'pendente')
        for chave in ['usuarios','sessoes','convites','verificacoes_email']:
            self.assertNotIn(chave,dados)

    def test_data_opcional_nao_vence_e_conclusao_preserva_evidencia(self):
        caso=self.c.demonstracao(self.u,self.org)['id']
        p=self.c.criar_providencia(self.u,{'caso':caso,'titulo':'Preparar análise','responsavel':self.u,'revisor':self.u})['id']
        self.assertEqual(self.c.rotina(self.u,self.org,'atrasadas')['total'],0)
        self.assertEqual(self.c.resumo_diario(self.u,self.org)['vencidas'],0)
        self.c.alterar_providencia(self.u,p,{'revisao':1,'estado':'em_andamento'})
        self.c.alterar_providencia(self.u,p,{'revisao':2,'estado':'em_revisao','evidencia':'Relatório revisado internamente.'})
        with self.assertRaises(FalhaAPI):
            self.c.alterar_providencia(self.u,p,{'revisao':3,'estado':'concluida','evidencia':''})
        self.c.alterar_providencia(self.u,p,{'revisao':3,'estado':'concluida'})


if __name__=='__main__':unittest.main()
