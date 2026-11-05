import os
import unittest
from unittest.mock import patch
from correio import entregar
from acompanhamento import FalhaAPI


class CorreioTests(unittest.TestCase):
    def test_producao_sem_configuracao(self):
        with patch.dict(os.environ,{'AMBAR_ENV':'production'},clear=True):
            with self.assertRaises(FalhaAPI):entregar('.', 'teste@example.com','Teste',{})

    def test_aceite_smtp_nao_significa_entrega(self):
        env={'AMBAR_ENV':'production','AMBAR_SMTP_HOST':'smtp.example.com','AMBAR_SMTP_USER':'teste','AMBAR_SMTP_PASSWORD':'apenas-mock','AMBAR_EMAIL_FROM':'sistema@example.com'}
        with patch.dict(os.environ,env),patch('correio.smtplib.SMTP') as smtp:
            canal=smtp.return_value.__enter__.return_value;canal.send_message.return_value={}
            self.assertEqual(entregar('.','teste@example.com','Teste',{}),'aceito_pelo_smtp')
            canal.starttls.assert_called_once();canal.login.assert_called_once()


if __name__=='__main__':unittest.main()
