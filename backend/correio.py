"""Caixa local e SMTP com TLS; aceite pelo servidor não significa entrega final."""
import json
import os
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from acompanhamento import FalhaAPI


def entregar(pasta, destinatario, assunto, conteudo, chave=None):
    if os.environ.get('AMBAR_ENV')!='production':
        pasta=Path(pasta)/'email-local';pasta.mkdir(parents=True,exist_ok=True)
        (pasta/((chave or secrets.token_hex(12))+'.json')).write_text(json.dumps({'para':destinatario,'assunto':assunto,**conteudo},ensure_ascii=False),encoding='utf-8')
        return 'disponivel_localmente'
    required=['AMBAR_SMTP_HOST','AMBAR_SMTP_USER','AMBAR_SMTP_PASSWORD','AMBAR_EMAIL_FROM']
    if not all(os.environ.get(k) for k in required):raise FalhaAPI(503,'Canal SMTP não configurado.')
    msg=EmailMessage();msg['From']=os.environ['AMBAR_EMAIL_FROM'];msg['To']=destinatario;msg['Subject']=assunto
    msg.set_content('\n'.join(f'{k}: {v}' for k,v in conteudo.items()))
    try:
        with smtplib.SMTP(os.environ['AMBAR_SMTP_HOST'],int(os.environ.get('AMBAR_SMTP_PORT','587')),timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context());smtp.login(os.environ['AMBAR_SMTP_USER'],os.environ['AMBAR_SMTP_PASSWORD'])
            recusados=smtp.send_message(msg)
            if recusados:raise FalhaAPI(502,'Destinatário recusado pelo SMTP.')
    except (smtplib.SMTPException,OSError) as exc:raise FalhaAPI(502,'Falha de comunicação com o SMTP.') from exc
    return 'aceito_pelo_smtp'
