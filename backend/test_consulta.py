"""Verifica comparação, falhas de fonte e contrato da API com HTTP real local."""
import json
import threading
import unittest

import requests

from consulta import ErroConsulta, consultar_fonte, extrair_e_comparar, validar_entradas
from servidor import criar_servidor


class ConsultaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = criar_servidor(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.session = requests.Session()
        cls.session.trust_env = False

    @classmethod
    def tearDownClass(cls):
        cls.session.close()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_http_extracao_e_comparacao(self):
        dados = consultar_fonte(self.base + '/portal.html', [
            {'id': 'CIV-001', 'previous': 'Aguardando agendamento'},
            {'id': 'TRA-003', 'previous': 'Aguardando documento'},
        ])
        self.assertEqual(dados['http_status'], 200)
        self.assertEqual(dados['engine'], 'python')
        self.assertEqual(dados['results'][0]['current'], 'Audiência agendada para 22/10 às 14h')
        self.assertTrue(dados['results'][0]['changed'])
        self.assertTrue(dados['results'][1]['incomplete'])

    def test_reconsulta_sem_mudanca(self):
        atual = 'Audiência agendada para 22/10 às 14h'
        dados = consultar_fonte(self.base + '/portal.html', [{'id': 'CIV-001', 'previous': atual}])
        self.assertFalse(dados['results'][0]['changed'])

    def test_404_nao_gera_sucesso(self):
        with self.assertRaises(ErroConsulta):
            consultar_fonte(self.base + '/fonte-inexistente.html', [{'id': 'CIV-001', 'previous': 'Anterior'}])

    def test_registro_ausente_nao_inventa_dado(self):
        dados = extrair_e_comparar(b'<html></html>', [{'id': 'CIV-001', 'previous': 'Anterior'}])
        self.assertFalse(dados[0]['ok'])
        self.assertNotIn('current', dados[0])

    def test_entradas_invalidas(self):
        for entrada in [[], [{'id': 'invalido', 'previous': 'x'}],
                        [{'id': 'CIV-001', 'previous': 'x'}] * 2]:
            with self.subTest(entrada=entrada), self.assertRaises(ValueError):
                validar_entradas(entrada)

    def test_api_e_rejeicao_de_json_invalido(self):
        resposta = self.session.post(self.base + '/api/consultar',
            json={'cases': [{'id': 'CON-002', 'previous': 'Versão inicial recebida'}]}, timeout=10)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()['results'][0]['current'], 'Nova versão do contrato disponibilizada')
        invalida = self.session.post(self.base + '/api/consultar', data='{',
                                    headers={'Content-Type': 'application/json'}, timeout=10)
        self.assertEqual(invalida.status_code, 400)

    def test_configuracao_ativa_python(self):
        resposta = self.session.get(self.base + '/runtime-config.js', timeout=10)
        self.assertIn('mode: "python"', resposta.text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
