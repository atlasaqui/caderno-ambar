"""Contratos, validação CNJ e comparação independente de HTTP/persistência."""
import hashlib
import json
import re
from typing import Protocol
from acompanhamento import DataJud, FalhaAPI

TRIBUNAIS = {'tjpe': '817', 'trt6': '506', 'trf5': '405'}


def validar_numero(valor, tribunal):
    numero = re.sub(r'[.\-/\s]', '', str(valor))
    if not re.fullmatch(r'[0-9]{20}', numero) or tribunal not in TRIBUNAIS:
        raise FalhaAPI(400, 'Informe número CNJ e tribunal suportado.')
    if numero[13:16] != TRIBUNAIS[tribunal]:
        raise FalhaAPI(400, 'O segmento e tribunal do número não correspondem ao tribunal escolhido.')
    base = numero[:7] + numero[9:] + '00'
    if 98 - int(base) % 97 != int(numero[7:9]):
        raise FalhaAPI(400, 'Dígitos verificadores do número CNJ inválidos.')
    return numero


def serializar(dado):
    return json.dumps(dado, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def versao(dado):
    return hashlib.sha256(serializar(dado).encode()).hexdigest()


class Fonte(Protocol):
    def buscar(self, tribunal: str, numero: str) -> dict: ...


def normalizar(dado):
    if not isinstance(dado, dict) or not isinstance(dado.get('registros'), list) or not dado['registros']:
        raise FalhaAPI(502, 'Fonte sem registros válidos. A referência foi preservada.')
    registros = []
    for registro in dado['registros']:
        if not isinstance(registro, dict) or not isinstance(registro.get('movimentos'), list):
            raise FalhaAPI(502, 'Formato de registro inválido.')
        movimentos = {}
        for m in registro['movimentos']:
            if not isinstance(m, dict) or not isinstance(m.get('dataHora'), str) or not m.get('codigo'):
                raise FalhaAPI(502, 'Movimentação incompleta recebida da fonte.')
            movimentos[serializar(m)] = m
        registros.append({**registro, 'movimentos': sorted(movimentos.values(), key=serializar)})
    return {**dado, 'registros': sorted(registros, key=serializar)}


def diferencas(anterior, atual):
    if not anterior:
        return {'tipo': 'primeiro registro', 'novos': [], 'removidos': [], 'cadastro': False}
    def movimentos(d):
        return {serializar({'grau': r.get('grau'), 'movimento': m}): m
                for r in d['registros'] for m in r['movimentos']}
    def cadastro(d):
        return sorted((serializar({k: v for k, v in r.items() if k != 'movimentos'}) for r in d['registros']))
    antes, depois = movimentos(anterior), movimentos(atual)
    novos, removidos = [depois[k] for k in depois.keys() - antes.keys()], [antes[k] for k in antes.keys() - depois.keys()]
    mudou = cadastro(anterior) != cadastro(atual)
    tipo = 'correção ou remoção na fonte' if removidos else 'nova movimentação' if novos else 'alteração cadastral' if mudou else 'sem diferença'
    return {'tipo': tipo, 'novos': sorted(novos, key=serializar), 'removidos': sorted(removidos, key=serializar), 'cadastro': mudou}


class DataJudValidado(DataJud):
    def buscar(self, tribunal, numero):
        validar_numero(numero, tribunal)
        return normalizar(super().buscar(tribunal, numero))


class Demonstracao:
    def __init__(self, etapa=0):
        self.etapa = etapa

    def buscar(self, tribunal, numero):
        movimentos = [{'codigo': 26, 'nome': 'Distribuição fictícia', 'dataHora': '2026-11-01T09:00:00'}]
        if self.etapa:
            movimentos.append({'codigo': 123, 'nome': 'Audiência fictícia agendada — exemplo de estudo', 'dataHora': '2026-11-03T10:00:00'})
        return {'numero': numero, 'tribunal': tribunal, 'fonte': 'DEMONSTRAÇÃO FICTÍCIA — não consulta tribunais',
                'registros': [{'grau': 'G1', 'classe': {'nome': 'Exemplo educacional'}, 'orgaoJulgador': None, 'movimentos': movimentos}]}
