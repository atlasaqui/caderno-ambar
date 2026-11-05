"""Fila persistente e recuperação da fonte, sem chamadas externas."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from acompanhamento import FalhaAPI
from piloto import Piloto
from test_equipes import numero


class FilaDataJudTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'fila.sqlite3'
        self.c=Piloto(self.path)
        self.u=self.c.usuario(self.c.autenticar({'email':'fila@example.com','senha':'senha-longa-de-teste'},True))
        self.org=self.c.contexto(self.u)[0]['id']
        with self.c.conexao() as db:db.execute('UPDATE usuarios SET email_verificado=1 WHERE id=?',(self.u,))
        self.id=self.c.adicionar(self.u,{'org':self.org,'numero':numero(),'tribunal':'tjpe'})['id']
        self.env=patch.dict(os.environ,{'AMBAR_DATAJUD_HABILITADO':'1'});self.env.start()

    def tearDown(self):self.env.stop();self.tmp.cleanup()

    def liberar(self):
        with self.c.conexao() as db:
            db.execute('UPDATE tarefas SET proxima=0')
            db.execute('UPDATE fontes_estado SET proxima=0,reserva=0')
            db.execute('UPDATE casos SET ultima_ok=0')

    def test_fila_idempotente_persistida_espera_e_recupera_sem_perder_versao(self):
        dados={'registros':[{'numeroProcesso':numero(),'grau':'G1','movimentos':[{'codigo':26,'nome':'Distribuição','dataHora':'2026-01-01T12:00:00'}]}]}
        fonte=Mock();fonte.buscar.return_value=dados
        self.c.consultar(self.u,self.id,fonte)
        anterior=self.c.carteira(self.u,self.org)['itens'][0]['snapshot']
        self.liberar()
        with patch('equipes.DataJudValidado',return_value=fonte):
            self.c.agendar_consulta(self.u,self.id)
            self.c.agendar_consulta(self.u,self.id)
            self.assertEqual(fonte.buscar.call_count,1)  # Enfileirar não consulta a rede.
            self.c=Piloto(self.path)  # A fila sobrevive à abertura de outra instância.
            fonte.buscar.side_effect=FalhaAPI(429,'Limite temporário',codigo='fonte_limite',aguardar=240)
            self.c.consultas_tick()
            self.c.consultas_tick()
            self.assertEqual(fonte.buscar.call_count,2)
            c=self.c.carteira(self.u,self.org)['itens'][0]
            self.assertEqual(c['snapshot'],anterior);self.assertEqual(c['atualizacao_pendente'],1)
            self.assertGreater(c['proxima_tentativa'],time.time()+235)
            self.liberar();fonte.buscar.side_effect=None
            self.c.consultas_tick()
            c=self.c.carteira(self.u,self.org)['itens'][0]
            self.assertEqual(c['atualizacao_pendente'],0);self.assertIsNone(c['erro'])
            self.assertEqual(c['snapshot'],anterior)
            with self.c.conexao() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM versoes WHERE caso=?',(self.id,)).fetchone()[0],1)
                self.assertEqual(db.execute('SELECT count(*) FROM consultas WHERE caso=?',(self.id,)).fetchone()[0],3)

    def test_para_em_cinco_falhas_sem_loop_e_nao_repete_credencial(self):
        fonte=Mock();fonte.buscar.side_effect=FalhaAPI(504,'Tempo esgotado',codigo='fonte_timeout')
        with patch('equipes.DataJudValidado',return_value=fonte):
            self.c.agendar_consulta(self.u,self.id)
            for _ in range(5):self.liberar();self.c.consultas_tick()
            self.liberar();self.c.consultas_tick()
            self.assertEqual(fonte.buscar.call_count,5)
            self.assertEqual(self.c.carteira(self.u,self.org)['itens'][0]['atualizacao_pendente'],0)
            self.c.agendar_consulta(self.u,self.id)
            fonte.buscar.side_effect=FalhaAPI(502,'Chave recusada',codigo='fonte_credencial')
            self.liberar();self.c.consultas_tick();self.liberar();self.c.consultas_tick()
            self.assertEqual(fonte.buscar.call_count,6)

    def test_autorizacao_email_e_arquivamento_protegem_fila(self):
        outro=self.c.usuario(self.c.autenticar({'email':'outro-fila@example.com','senha':'senha-longa-de-teste'},True))
        with self.assertRaises(FalhaAPI):self.c.agendar_consulta(outro,self.id)
        with self.c.conexao() as db:db.execute('UPDATE usuarios SET email_verificado=NULL WHERE id=?',(self.u,))
        with self.assertRaises(FalhaAPI) as exc:self.c.agendar_consulta(self.u,self.id)
        self.assertEqual(exc.exception.status,403)
        with self.c.conexao() as db:
            db.execute('UPDATE usuarios SET email_verificado=1 WHERE id=?',(self.u,))
            db.execute('UPDATE casos SET arquivado=1 WHERE id=?',(self.id,))
        with self.assertRaises(FalhaAPI) as exc:self.c.agendar_consulta(self.u,self.id)
        self.assertEqual(exc.exception.status,409)

    def test_fonte_desativada_pausa_fila_sem_busca_externa(self):
        self.c.agendar_consulta(self.u,self.id)
        with patch.dict(os.environ,{'AMBAR_DATAJUD_HABILITADO':'0'}),patch('equipes.DataJudValidado') as fonte:
            self.c.consultas_tick();fonte.assert_not_called()
        with self.c.conexao() as db:
            t=db.execute('SELECT * FROM tarefas WHERE caso=?',(self.id,)).fetchone()
            self.assertEqual(t['solicitada'],0);self.assertEqual(t['codigo'],'fonte_configuracao')
