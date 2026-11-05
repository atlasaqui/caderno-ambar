"""Contratos e limites da fonte: testes locais, sem chamadas ao CNJ."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from acompanhamento import DataJud,FalhaAPI
from equipes import Equipes
from test_equipes import numero


def resposta(payload,status=200,headers=None):
    r=requests.Response();r.status_code=status;r.headers.update(headers or {})
    r._content=json.dumps(payload).encode();return r


def hit(i=1,n=None):
    return {'_id':str(i),'sort':[i],'_source':{'numeroProcesso':n or numero(),'grau':'G1',
        'classe':{'nome':'Classe de teste'},'movimentos':[{'codigo':26,'nome':'Movimento de teste','dataHora':'2026-11-04T10:00:00'}]}}


def pagina(itens,total=None,**extra):
    return {'hits':{'total':{'value':len(itens) if total is None else total,'relation':'eq'},'hits':itens},**extra}


class TransporteDataJudTests(unittest.TestCase):
    def chamar(self,respostas):
        sessao=Mock();sessao.post.side_effect=respostas
        with patch.dict(os.environ,{'DATAJUD_API_KEY':'chave-ficticia-de-teste','AMBAR_DATAJUD_USAR_PROXY':'0'}),patch('acompanhamento.requests.Session',return_value=sessao):
            resultado=DataJud().buscar('tjpe',numero())
        return resultado,sessao

    def test_consulta_pequena_com_ordenacao_publica_e_projecao(self):
        resultado,sessao=self.chamar([resposta(pagina([hit()]))])
        corpo=sessao.post.call_args.kwargs['json']
        self.assertEqual(corpo['size'],10)
        self.assertEqual(corpo['sort'],[{'@timestamp':{'order':'asc'}}])
        self.assertNotIn('from',corpo);self.assertNotIn('search_after',corpo)
        self.assertIn('movimentos',corpo['_source'])
        self.assertEqual(len(resultado['registros']),1)
        self.assertIs(sessao.trust_env,False);sessao.close.assert_called_once()

    def test_paginacao_cursor_preserva_todos_registros(self):
        resultado,sessao=self.chamar([resposta(pagina([hit(i) for i in range(10)],11)),resposta(pagina([hit(10)],11))])
        self.assertEqual(len(resultado['registros']),11)
        self.assertEqual(sessao.post.call_args_list[1].kwargs['json']['search_after'],[9])

    def test_pagina_cheia_com_total_exato_nao_consulta_de_novo(self):
        _,sessao=self.chamar([resposta(pagina([hit(i) for i in range(10)]))])
        self.assertEqual(sessao.post.call_count,1)

    def test_recusa_respostas_parciais_e_processo_inesperado(self):
        exemplos=[pagina([hit()],timed_out=True),pagina([hit()],_shards={'failed':1}),
            pagina([hit()],2),pagina([hit(n=numero(sequencia='0000002'))]),
            {'hits':{'total':{'value':1,'relation':'gte'},'hits':[hit()]}},
            pagina([hit()],1001)]
        for payload in exemplos:
            with self.subTest(payload=payload),self.assertRaises(FalhaAPI) as exc:self.chamar([resposta(payload)])
            self.assertEqual(exc.exception.status,502)

    def test_recusa_repeticao_de_pagina(self):
        with self.assertRaises(FalhaAPI):
            self.chamar([resposta(pagina([hit(i) for i in range(10)],11)),resposta(pagina([hit(9)],11))])

    def test_limite_e_sobrecarga_sao_distintos(self):
        for tipo,status,codigo in [('',429,'fonte_limite'),('circuit_breaking_exception',503,'fonte_sobrecarregada')]:
            with self.subTest(tipo=tipo),self.assertRaises(FalhaAPI) as exc:
                self.chamar([resposta({'error':{'type':tipo}},429,{'Retry-After':'123'})])
            self.assertEqual(exc.exception.status,status);self.assertEqual(exc.exception.codigo,codigo)
            self.assertEqual(exc.exception.aguardar,123 if codigo=='fonte_limite' else 300)

    def test_sobrecarga_encapsulada_como_resposta_real_do_cnj(self):
        causa={'type':'es_rejected_execution_exception','reason':'queue capacity = 1000, queued tasks = 1005'}
        for detalhes in [{'root_cause':[causa]},{'failed_shards':[{'reason':causa}]},
                         {'caused_by':{'type':'search_phase_execution_exception','caused_by':causa}}]:
            payload={'error':{'type':'search_phase_execution_exception','reason':'all shards failed',**detalhes}}
            with self.subTest(detalhes=detalhes),self.assertRaises(FalhaAPI) as exc:
                self.chamar([resposta(payload,429)])
            self.assertEqual(exc.exception.status,503)
            self.assertEqual(exc.exception.codigo,'fonte_sobrecarregada')
            self.assertEqual(exc.exception.aguardar,300)
            self.assertNotIn('queued tasks',str(exc.exception))
        self.assertEqual(DataJud.tipos_erro({'error':{'type':{'invalido':True}}}),set())

    def test_timeout_tls_proxy_e_rede_tem_diagnosticos(self):
        for erro,codigo in [(requests.Timeout(),'fonte_timeout'),(requests.exceptions.SSLError(),'fonte_tls'),
                            (requests.exceptions.ProxyError(),'fonte_proxy'),(requests.ConnectionError(),'fonte_rede')]:
            with self.subTest(codigo=codigo),self.assertRaises(FalhaAPI) as exc:self.chamar([erro])
            self.assertEqual(exc.exception.codigo,codigo)
            self.assertGreater(exc.exception.aguardar,0)

    def test_credencial_recusada_nao_e_processo_inexistente(self):
        with self.assertRaises(FalhaAPI) as exc:self.chamar([resposta({},401)])
        self.assertEqual(exc.exception.codigo,'fonte_credencial')
        self.assertNotIn('chave-ficticia',str(exc.exception))


class EsperaDataJudTests(unittest.TestCase):
    def test_espera_impede_repeticoes_e_preserva_referencia(self):
        with tempfile.TemporaryDirectory() as pasta:
            c=Equipes(Path(pasta)/'teste.sqlite3')
            u=c.usuario(c.autenticar({'email':'espera@example.com','senha':'senha-de-teste-longa'},True))
            org=c.contexto(u)[0]['id']
            id=c.adicionar(u,{'org':org,'numero':numero(),'tribunal':'tjpe'})['id']
            outro=c.adicionar(u,{'org':org,'numero':numero(sequencia='0000002'),'tribunal':'tjpe'})['id']
            cliente=Mock();cliente.buscar.return_value={'registros':[hit()['_source']]}
            with patch.dict(os.environ,{'AMBAR_DATAJUD_HABILITADO':'1'}),patch('equipes.DataJudValidado',return_value=cliente):
                c.consultar(u,id)
                anterior=c.listar(u,org)[1]['snapshot']
                with c.conexao() as db:
                    db.execute('UPDATE casos SET ultima_ok=0 WHERE id=?',(id,))
                    db.execute('UPDATE fontes_estado SET proxima=0')
                cliente.buscar.side_effect=FalhaAPI(429,'Fornecedor ocupado.',codigo='fonte_limite',aguardar=123)
                with self.assertRaises(FalhaAPI):c.consultar(u,id)
                self.assertEqual(cliente.buscar.call_count,2)
                with self.assertRaises(FalhaAPI) as exc:c.consultar(u,id)
                self.assertEqual(exc.exception.codigo,'consulta_aguardando')
                with self.assertRaises(FalhaAPI) as exc:c.consultar(u,outro)
                self.assertEqual(exc.exception.codigo,'fonte_aguardando')
                self.assertEqual(cliente.buscar.call_count,2)
                with c.conexao() as db:
                    atual=db.execute('SELECT snapshot FROM casos WHERE id=?',(id,)).fetchone()[0]
                    espera=db.execute('SELECT proxima FROM tarefas WHERE caso=?',(id,)).fetchone()[0]-time.time()
                self.assertEqual(atual,anterior);self.assertGreaterEqual(espera,120)
                self.assertEqual(len(c.historico(u,id)),2)


if __name__=='__main__':unittest.main()
