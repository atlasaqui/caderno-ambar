"""Obtém a chave pública publicada pelo CNJ e inicia o servidor local."""
import os
import re
import requests
from bs4 import BeautifulSoup
from servidor import main

if __name__ == '__main__':
    if not os.environ.get('DATAJUD_API_KEY'):
        try:
            response = requests.get('https://datajud-wiki.cnj.jus.br/api-publica/acesso/', timeout=15)
            response.raise_for_status()
            texto = BeautifulSoup(response.content, 'html.parser').get_text(' ', strip=True)
            match = re.search(r'Authorization:\s*APIKey\s+([A-Za-z0-9+/=]{30,})', texto)
            if not match:
                raise ValueError('Formato da documentação mudou.')
            os.environ['DATAJUD_API_KEY'] = match[1]
            print('Chave pública obtida da documentação oficial do CNJ. Não foi gravada em arquivo.')
        except (requests.RequestException, ValueError):
            print('Não foi possível obter a chave pública. Configure DATAJUD_API_KEY e reinicie para consultar o DataJud.')
    main()
