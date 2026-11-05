import tempfile
import threading
import unittest
from unittest.mock import patch, Mock
from pathlib import Path
import requests
from acompanhamento import Caderno, DataJud, FalhaAPI
from servidor import criar_servidor


class IntegracaoTests(unittest.TestCase):
    def setUp(self):
        pasta = Path(__file__).resolve().parents[1] / 'output'
        pasta.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=pasta)
        self.server = criar_servidor(0, Path(self.tmp.name) / 'teste.sqlite3')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.http = requests.Session()
        self.http.trust_env = False

    def tearDown(self):
        self.http.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def post(self, path, dados):
        return self.http.post(self.base + path, json=dados)

    def test_fluxo_persistente_e_isolamento(self):
        self.assertEqual(self.http.get(self.base+'/api/casos').status_code, 401)
        cred = {'email':'teste@example.com','senha':'senha-teste-123'}
        self.assertEqual(self.post('/api/conta/cadastro',cred).status_code,200)
        dado = {'numero':'00000000020268060001','tribunal':'tjpe','apelido':'Meu caso'}
        caso = self.post('/api/casos',dado).json()['id']
        self.assertEqual(self.post('/api/casos',dado).status_code,409)
        fonte = {'fonte':'CNJ / DataJud','registros':[]}
        with patch.object(DataJud,'buscar',return_value=fonte):
            self.assertEqual(self.post(f'/api/casos/{caso}/consultar',{}).json()['estado'],'primeira consulta')
        self.assertEqual(self.post(f'/api/casos/{caso}/revisar',{}).status_code,200)
        reaberto = Caderno(self.server.caderno.arquivo)
        usuario = reaberto.usuario(self.http.cookies['ambar'])
        self.assertEqual(reaberto.listar(usuario)[0]['revisado'],1)
        self.assertEqual(len(reaberto.historico(usuario,caso)),1)
        self.post('/api/conta/sair',{})
        self.assertEqual(self.http.get(self.base+'/api/casos').status_code,401)
        self.post('/api/conta/cadastro',{'email':'outro@example.com','senha':'senha-teste-123'})
        self.assertEqual(self.http.get(self.base+f'/api/casos/{caso}/historico').status_code,404)
        self.assertEqual(self.post(f'/api/casos/{caso}/revisar',{}).status_code,404)

    def test_comparacao_e_falha_preservam_snapshot(self):
        c = self.server.caderno
        u = c.usuario(c.autenticar({'email':'x@example.com','senha':'senha-teste-123'},True))
        id = c.adicionar(u,{'numero':'0'*20,'tribunal':'tjpe'})['id']
        cliente = Mock()
        cliente.buscar.return_value={'movimentos':['A']}
        self.assertEqual(c.consultar(u,id,cliente)['estado'],'primeira consulta')
        def liberar():
            with c.conexao() as db: db.execute('UPDATE consultas SET instante=0')
        liberar()
        self.assertEqual(c.consultar(u,id,cliente)['estado'],'sem mudança')
        liberar()
        cliente.buscar.return_value={'movimentos':['A','B']}
        self.assertEqual(c.consultar(u,id,cliente)['estado'],'mudança encontrada')
        anterior=c.listar(u)[0]['snapshot']
        liberar()
        cliente.buscar.side_effect=FalhaAPI(502,'Fonte indisponível')
        with self.assertRaises(FalhaAPI): c.consultar(u,id,cliente)
        self.assertEqual(c.listar(u)[0]['snapshot'],anterior)
        self.assertEqual(c.historico(u,id)[0]['estado'],'falha')

    def test_datajud_configuracao_e_resposta(self):
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaises(FalhaAPI): DataJud().buscar('tjpe','0'*20)
        resposta=Mock(status_code=200)
        resposta.content=b'{}'
        resposta.json.return_value={'hits':{'total':{'value':1,'relation':'eq'},'hits':[{'_source':{'numeroProcesso':'0'*20,'grau':'G1','movimentos':[{'codigo':1,'nome':'Distribuição','dataHora':'2026-01-01'}]}}]}}
        with patch.dict('os.environ',{'DATAJUD_API_KEY':'teste','AMBAR_DATAJUD_USAR_PROXY':'1'}), patch('acompanhamento.requests.post',return_value=resposta) as chamada:
            self.assertEqual(DataJud().buscar('tjpe','0'*20)['registros'][0]['grau'],'G1')
            self.assertTrue(chamada.call_args.args[0].endswith('api_publica_tjpe/_search'))

    def test_datajud_conexao_direta_e_limite_temporario(self):
        sessao=Mock();resposta=Mock();resposta.status_code=429;resposta.headers={'Retry-After':'60'}
        sessao.post.return_value=resposta
        with patch.dict('os.environ',{'DATAJUD_API_KEY':'teste','AMBAR_DATAJUD_USAR_PROXY':'0'}), patch('acompanhamento.requests.Session',return_value=sessao):
            with self.assertRaises(FalhaAPI) as exc:DataJud().buscar('tjpe','0'*20)
        self.assertEqual(exc.exception.status,429)
        self.assertIn('60 segundos',str(exc.exception))
        self.assertIs(sessao.trust_env,False)
        sessao.close.assert_called_once()

    def test_origem_e_senha(self):
        self.assertEqual(self.http.post(self.base+'/api/conta/login',json={},headers={'Origin':'https://outro.example'}).status_code,403)
        self.assertEqual(self.post('/api/conta/cadastro',{'email':'a@example.com','senha':'curta'}).status_code,400)


if __name__ == '__main__': unittest.main()
