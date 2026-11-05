import tempfile
import threading
import time
import unittest
import json
from pathlib import Path
import requests
import uvicorn
from aplicacao import criar_app


class ApiV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import socket
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));cls.port=sock.getsockname()[1]
        cls.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'output')
        cls.app=criar_app(Path(cls.tmp.name)/'api.sqlite3',worker=False)
        cls.server=uvicorn.Server(uvicorn.Config(cls.app,host='127.0.0.1',port=cls.port,log_level='error'))
        cls.th=threading.Thread(target=cls.server.run,daemon=True);cls.th.start()
        for _ in range(100):
            if cls.server.started:break
            time.sleep(.05)
        cls.base=f'http://127.0.0.1:{cls.port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit=True;cls.th.join(10);cls.tmp.cleanup()

    def setUp(self):
        self.s=requests.Session();self.s.trust_env=False
    def tearDown(self):self.s.close()
    def post(self,path,data):return self.s.post(self.base+'/api/'+path,json=data,timeout=10)

    def test_fluxo_http_completo(self):
        pagina=self.s.get(self.base+'/acompanhamento.html',timeout=5)
        self.assertEqual(pagina.status_code,200)
        self.assertEqual(pagina.headers.get('Cache-Control'),'no-store')
        self.assertEqual(self.post('conta/cadastro',{'email':'api@example.com','senha':'senha-longa-api'}).status_code,200)
        context=self.s.get(self.base+'/api/contexto',timeout=5).json();org=context[0]['id']
        id=self.post('demonstracao',{'org':org}).json()['id']
        v1=self.post(f'casos/{id}/consultar',{}).json()['versao_id']
        self.post(f'casos/{id}/avancar-demo',{})
        novidade=self.post(f'casos/{id}/consultar',{}).json()
        self.assertEqual(novidade['estado'],'nova movimentação')
        self.assertEqual(self.post(f'casos/{id}/revisar',{'versao_id':v1}).status_code,200)
        casos=self.s.get(self.base+'/api/casos',timeout=5).json();self.assertFalse(casos[0]['conferido'])
        self.post(f'casos/{id}/revisar',{'versao_id':novidade['versao_id']})
        self.assertTrue(self.s.get(self.base+'/api/casos',timeout=5).json()[0]['conferido'])
        self.assertEqual(len(self.s.get(self.base+f'/api/casos/{id}/detalhe',timeout=5).json()['versoes']),2)
        self.post('conta/sair',{})
        self.assertEqual(self.s.get(self.base+'/api/casos',timeout=5).status_code,401)
        self.assertEqual(self.post('conta/login',{'email':'api@example.com','senha':'senha-longa-api'}).status_code,200)

    def test_origem_json_e_limites(self):
        r=self.s.post(self.base+'/api/conta/login',json={},headers={'Origin':'https://outro.example'},timeout=5)
        self.assertEqual(r.status_code,403)
        self.assertEqual(self.s.post(self.base+'/api/conta/login',data='x',timeout=5).status_code,400)
        self.assertEqual(self.s.post(self.base+'/api/conta/login',data='x'*150001,timeout=5).status_code,413)

    def test_percurso_publico_separado(self):
        for pagina in ['index.html','laboratorio.html','acesso.html','acompanhamento.html','guia.js','acesso.js']:
            resposta=self.s.get(self.base+'/'+pagina,timeout=5)
            self.assertEqual(resposta.status_code,200,pagina)
        inicio=self.s.get(self.base+'/index.html',timeout=5).text
        self.assertNotIn('id="case-rows"',inicio)
        self.assertIn('laboratorio.html?treino=1',inicio)

    def test_recuperacao_uso_unico(self):
        self.post('conta/cadastro',{'email':'reset@example.com','senha':'senha-longa-api'})
        self.assertEqual(self.post('conta/recuperar',{'email':'reset@example.com'}).status_code,200)
        # Confere persistência de token sem expô-lo na API nem no log.
        with self.app.state.caderno.conexao() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM recuperacoes').fetchone()[0],1)
        self.assertEqual(self.post('conta/redefinir',{'token':'incorreto','senha':'senha-nova-longa'}).status_code,400)
        mensagens=[json.loads(p.read_text(encoding='utf-8')) for p in (Path(self.tmp.name)/'email-local').glob('*.json')]
        token=next(m['token'] for m in mensagens if m.get('tipo')=='recuperacao' and m.get('para')=='reset@example.com')
        self.assertEqual(self.post('conta/redefinir',{'token':token,'senha':'senha-nova-longa'}).status_code,200)
        self.assertEqual(self.post('conta/redefinir',{'token':token,'senha':'senha-nova-longa'}).status_code,400)
        self.assertEqual(self.s.get(self.base+'/api/casos',timeout=5).status_code,401)
        self.assertEqual(self.post('conta/login',{'email':'reset@example.com','senha':'senha-nova-longa'}).status_code,200)

    def test_rotina_http(self):
        self.post('conta/cadastro',{'email':'rotina-http@example.com','senha':'senha-longa-api'})
        org=self.s.get(self.base+'/api/contexto',timeout=5).json()[0]['id']
        me=self.s.get(self.base+f'/api/me?org={org}',timeout=5).json()['id']
        caso=self.post('demonstracao',{'org':org}).json()['id']
        versao=self.post(f'casos/{caso}/consultar',{}).json()['versao_id']
        r=self.post('providencias',{'caso':caso,'versao':versao,'titulo':'Conferir documentos',
            'descricao':'Análise interna.','responsavel':me,'revisor':me,'data_interna':'2026-11-10','prioridade':'alta'})
        self.assertEqual(r.status_code,200)
        id=r.json()['id']
        rotina=self.s.get(self.base+f'/api/rotina?org={org}',timeout=5).json()
        self.assertEqual(rotina['total'],1)
        self.assertEqual(rotina['itens'][0]['estado'],'a_fazer')
        self.assertEqual(self.post(f'providencias/{id}/alterar',{'revisao':1,'estado':'em_andamento'}).status_code,200)
        self.assertEqual(self.post(f'providencias/{id}/alterar',{'revisao':1,'estado':'aguardando'}).status_code,409)
        self.assertEqual(len(self.s.get(self.base+f'/api/providencias/{id}/historico',timeout=5).json()),2)
        self.assertEqual(self.s.get(self.base+f'/api/operacao?org={org}',timeout=5).status_code,200)

    def test_piloto_carteira_conta_e_dados_autorizados(self):
        self.assertEqual(self.s.get(self.base+'/api/carteira',timeout=5).status_code,401)
        self.post('conta/cadastro',{'email':'piloto-http@example.com','senha':'senha-longa-api'})
        org=self.s.get(self.base+'/api/contexto',timeout=5).json()[0]['id']
        self.assertIsNone(self.s.get(self.base+'/api/conta',timeout=5).json()['email_verificado'])
        self.assertEqual(self.post('convites/criar',{'org':org,'email':'membro@example.com'}).status_code,403)
        self.assertEqual(self.post('conta/verificacao/solicitar',{}).status_code,200)
        arquivos=[json.loads(p.read_text(encoding='utf-8')) for p in (Path(self.tmp.name)/'email-local').glob('*.json')]
        token=next(a['token'] for a in arquivos if a.get('tipo')=='verificacao_email' and a['para']=='piloto-http@example.com')
        self.assertEqual(self.post('conta/verificacao/confirmar',{'token':token}).status_code,200)
        self.assertEqual(self.post('conta/verificacao/confirmar',{'token':token}).status_code,400)
        self.post('demonstracao',{'org':org})
        r=self.s.get(self.base+f'/api/carteira?org={org}',timeout=5)
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['resumo']['ativos'],1)
        self.assertEqual(r.json()['total'],1)
        self.assertEqual(self.s.get(self.base+f'/api/carteira?org={org}&pagina=abc',timeout=5).status_code,422)
        self.assertEqual(self.s.get(self.base+f'/api/resumo?org={org}',timeout=5).json()['minhas'],0)
        self.assertEqual(self.post('dados/solicitar',{'org':org,'tipo':'retencao','motivo':'Revisão administrativa dos dados.'}).status_code,200)
        exportacao=self.s.get(self.base+f'/api/dados/exportar?org={org}',timeout=5)
        self.assertEqual(exportacao.status_code,200);self.assertIn('attachment',exportacao.headers['Content-Disposition'])
        self.assertNotIn('sessoes',exportacao.json())
        with requests.Session() as outra:
            outra.trust_env=False
            outra.post(self.base+'/api/conta/cadastro',json={'email':'isolado-http@example.com','senha':'senha-longa-api'},timeout=5)
            self.assertEqual(outra.get(self.base+f'/api/carteira?org={org}',timeout=5).status_code,403)
            self.assertEqual(outra.get(self.base+f'/api/dados/exportar?org={org}',timeout=5).status_code,403)

    def test_agendamento_http_aceita_sem_chamar_fonte(self):
        from unittest.mock import patch
        from test_equipes import numero
        self.post('conta/cadastro',{'email':'fila-http@example.com','senha':'senha-longa-api'})
        org=self.s.get(self.base+'/api/contexto',timeout=5).json()[0]['id']
        u=self.s.get(self.base+'/api/conta',timeout=5).json()['id']
        with self.app.state.caderno.conexao() as db:db.execute('UPDATE usuarios SET email_verificado=1 WHERE id=?',(u,))
        caso=self.post('casos',{'org':org,'numero':numero(sequencia='0000078'),'tribunal':'tjpe'}).json()['id']
        with patch.dict('os.environ',{'AMBAR_DATAJUD_HABILITADO':'1'}),patch('equipes.DataJudValidado') as fonte:
            for _ in range(2):
                r=self.post(f'casos/{caso}/agendar',{})
                self.assertEqual(r.status_code,202);self.assertTrue(r.json()['agendada'])
            fonte.assert_not_called()
        itens=self.s.get(self.base+f'/api/carteira?org={org}',timeout=5).json()['itens']
        self.assertEqual(next(c for c in itens if c['id']==caso)['atualizacao_pendente'],1)

    def test_falha_da_fonte_devolve_codigo_espera_e_historico(self):
        from unittest.mock import patch
        from acompanhamento import FalhaAPI
        from test_equipes import numero
        self.post('conta/cadastro',{'email':'fonte-http@example.com','senha':'senha-longa-api'})
        org=self.s.get(self.base+'/api/contexto',timeout=5).json()[0]['id']
        usuario=self.s.get(self.base+'/api/conta',timeout=5).json()['id']
        with self.app.state.caderno.conexao() as db:
            db.execute('UPDATE usuarios SET email_verificado=? WHERE id=?',(time.time(),usuario))
        caso=self.post('casos',{'org':org,'numero':numero(),'tribunal':'tjpe'}) .json()['id']
        erro=FalhaAPI(504,'DataJud não respondeu.',codigo='fonte_timeout',aguardar=123)
        with patch.dict('os.environ',{'AMBAR_DATAJUD_HABILITADO':'1'}),patch('equipes.DataJudValidado') as fonte:
            fonte.return_value.buscar.side_effect=erro
            r=self.post(f'casos/{caso}/consultar',{})
            self.assertEqual(r.status_code,504)
            self.assertEqual(r.json()['code'],'fonte_timeout')
            self.assertEqual(r.json()['retry_after'],123)
            self.assertEqual(r.headers['Retry-After'],'123')
            r=self.post(f'casos/{caso}/consultar',{})
            self.assertEqual(r.status_code,429)
            self.assertEqual(r.json()['code'],'consulta_aguardando')
            self.assertEqual(fonte.return_value.buscar.call_count,1)
        historico=self.s.get(self.base+f'/api/casos/{caso}/historico',timeout=5).json()
        self.assertEqual(len(historico),1)
        self.assertEqual(historico[0]['estado'],'falha')
        self.assertEqual(self.s.get(self.base+f'/api/casos/{caso}/detalhe',timeout=5).json()['versoes'],[])


if __name__=='__main__':unittest.main()
