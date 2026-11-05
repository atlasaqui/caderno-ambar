import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock
from acompanhamento import Caderno, FalhaAPI
from equipes import Equipes
from fontes import Demonstracao, diferencas, validar_numero
from backup import copiar


def numero(tribunal='817',sequencia='0000001'):
    resto=sequencia+'2026'+tribunal+'0001'
    return sequencia+str(98-int(resto+'00')%97).zfill(2)+'2026'+tribunal+'0001'


class EquipesTests(unittest.TestCase):
    def setUp(self):
        pasta=Path(__file__).resolve().parents[1]/'output';pasta.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=pasta);self.db=Path(self.tmp.name)/'db.sqlite3'
        self.c=Equipes(self.db)
        self.u=self.usuario('admin@example.com');self.org=self.c.contexto(self.u)[0]['id']

    def tearDown(self): self.tmp.cleanup()

    def usuario(self,email):return self.c.usuario(self.c.autenticar({'email':email,'senha':'uma-senha-de-teste'},True))

    def test_cnj(self):
        self.assertEqual(validar_numero(numero(),'tjpe'),numero())
        for n,t in [('0'*20,'tjpe'),(numero(),'trf5'),('11','tjpe')]:
            with self.assertRaises(FalhaAPI):validar_numero(n,t)

    def test_migracao_preserva_conta_e_caso(self):
        antigo=Caderno(Path(self.tmp.name)/'antigo.sqlite3');u=antigo.usuario(antigo.autenticar({'email':'velho@example.com','senha':'uma-senha-de-teste'},True))
        id=antigo.adicionar(u,{'numero':numero(),'tribunal':'tjpe'})['id']
        novo=Equipes(antigo.arquivo);novo2=Equipes(antigo.arquivo)
        self.assertEqual(novo2.listar(u)[0]['id'],id)

    def test_convite_isolamento_e_revogacao(self):
        outro=self.usuario('membro@example.com')
        caso=self.c.demonstracao(self.u)['id']
        with self.assertRaises(FalhaAPI):self.c.detalhe(outro,caso)
        t=self.c.convidar(self.u,self.org,'membro@example.com')['token'];self.c.aceitar(outro,t)
        self.assertEqual(self.c.listar(outro,self.org)[0]['id'],caso)
        with self.assertRaises(FalhaAPI):self.c.convidar(outro,self.org,'x@example.com')
        self.c.revogar(self.u,self.org,outro)
        with self.assertRaises(FalhaAPI):self.c.detalhe(outro,caso)

    def test_conferencia_por_versao_e_notificacao_unica(self):
        id=self.c.demonstracao(self.u)['id']
        v1=self.c.consultar(self.u,id)['versao_id']
        with self.c.conexao() as db:db.execute('UPDATE casos SET etapa=1 WHERE id=?',(id,))
        v2=self.c.consultar(self.u,id)['versao_id'];self.assertNotEqual(v1,v2)
        self.c.revisar(self.u,id,v1)
        self.assertEqual(self.c.listar(self.u)[0]['conferido'],0)
        self.c.revisar(self.u,id,v2);self.assertEqual(self.c.listar(self.u)[0]['conferido'],1)
        self.c.consultar(self.u,id)
        with self.c.conexao() as db:self.assertEqual(db.execute('SELECT count(*) FROM notificacoes').fetchone()[0],1)

    def test_falha_preserva_referencia(self):
        id=self.c.demonstracao(self.u)['id'];self.c.consultar(self.u,id)
        antes=self.c.listar(self.u)[0]['snapshot'];cliente=Mock();cliente.buscar.side_effect=FalhaAPI(502,'Indisponível')
        with self.assertRaises(FalhaAPI):self.c.consultar(self.u,id,cliente)
        self.assertEqual(self.c.listar(self.u)[0]['snapshot'],antes)
        self.assertEqual(self.c.historico(self.u,id)[0]['estado'],'falha')

    def test_concorrencia_reserva_antes_de_consultar(self):
        id=self.c.demonstracao(self.u)['id'];entrou=threading.Event();liberar=threading.Event();erros=[]
        class Lenta:
            def buscar(s,t,n):entrou.set();liberar.wait(3);return Demonstracao().buscar(t,n)
        def executar():
            try:self.c.consultar(self.u,id,Lenta())
            except Exception as e:erros.append(e)
        th=threading.Thread(target=executar);th.start();self.assertTrue(entrou.wait(3))
        try:
            with self.assertRaises(FalhaAPI) as exc:self.c.consultar(self.u,id)
            self.assertEqual(exc.exception.status,409)
        finally:liberar.set();th.join(5)
        self.assertEqual(erros,[])

    def test_importacao_e_duplicacao(self):
        csv='numero;tribunal;apelido\n'+numero()+';tjpe;Teste\n'+numero()+';tjpe;Repetido\n11;tjpe;Inválido'
        previa=self.c.importar(self.u,self.org,csv)
        self.assertEqual([r['status'] for r in previa['linhas']],['válido','rejeitado','rejeitado'])
        self.assertEqual(self.c.listar(self.u),[])
        self.c.importar(self.u,self.org,csv,True);self.assertEqual(len(self.c.listar(self.u)),1)

    def test_agendamento_e_backup_restaurado(self):
        id=self.c.demonstracao(self.u)['id'];self.c.alterar(self.u,id,{'intervalo':3600})
        with self.c.conexao() as db:db.execute('UPDATE tarefas SET proxima=0')
        self.c.tick();self.assertTrue(self.c.listar(self.u)[0]['snapshot'])
        destino=Path(self.tmp.name)/'backup.sqlite3';copiar(self.db,destino)
        self.assertEqual(Equipes(destino).listar(self.u)[0]['snapshot'],self.c.listar(self.u)[0]['snapshot'])
        with self.assertRaises(ValueError):copiar(self.db,destino)

    def test_email_local_sem_envio_externo(self):
        id=self.c.demonstracao(self.u)['id']
        with self.c.conexao() as db:db.execute('INSERT INTO preferencias VALUES(?,1)',(self.u,))
        self.c.consultar(self.u,id)
        with self.c.conexao() as db:db.execute('UPDATE casos SET etapa=1 WHERE id=?',(id,))
        self.c.consultar(self.u,id);self.c.email_tick();self.c.email_tick()
        self.assertEqual(len(list((Path(self.tmp.name)/'email-local').glob('notificacao-*.json'))),1)


if __name__=='__main__':unittest.main()
