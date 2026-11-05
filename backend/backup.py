"""Backup consistente e restauração para um NOVO caminho, sem sobrescrever banco."""
import argparse
import sqlite3
from pathlib import Path


def copiar(origem, destino):
    origem,destino=Path(origem),Path(destino)
    if not origem.is_file(): raise ValueError('Banco de origem não encontrado.')
    if destino.exists(): raise ValueError('Destino já existe. Escolha um novo caminho.')
    destino.parent.mkdir(parents=True,exist_ok=True)
    src=sqlite3.connect(origem.resolve().as_uri()+'?mode=ro',uri=True)
    dst=sqlite3.connect(destino)
    try:
        if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Banco de origem falhou na integridade.')
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Backup falhou na integridade.')
    finally: src.close();dst.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('origem');p.add_argument('destino');a=p.parse_args()
    copiar(a.origem,a.destino);print('Cópia verificada. Para restaurar, inicie a aplicação com AMBAR_DB apontando ao novo arquivo.')
