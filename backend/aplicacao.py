"""API FastAPI local: contratos HTTP, sessões e tarefas com persistência."""
import asyncio
import hashlib
import json
import logging
import os
import secrets
import sqlite3
import time
import csv
import io
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware
from acompanhamento import FalhaAPI
from consulta import consultar_fonte, validar_entradas
from equipes import Equipes
from correio import entregar
from rotina import Escritorio
from piloto import Piloto

ROOT=Path(__file__).resolve().parents[1]
logger=logging.getLogger('ambar')


def criar_app(banco=None, worker=True):
    producao=os.environ.get('AMBAR_ENV')=='production'
    origem=os.environ.get('AMBAR_ORIGIN','http://127.0.0.1:8093')
    if producao:
        from urllib.parse import urlsplit
        if urlsplit(origem).scheme != 'https':
            raise RuntimeError('Produção exige AMBAR_ORIGIN com HTTPS.')
        obrigatorias=['AMBAR_DB','AMBAR_SMTP_HOST','AMBAR_SMTP_USER','AMBAR_SMTP_PASSWORD','AMBAR_EMAIL_FROM']
        if not all(os.environ.get(k) for k in obrigatorias):
            raise RuntimeError('Produção exige banco persistente e canal SMTP configurados.')
    caderno=Piloto(banco or os.environ.get('AMBAR_DB',str(ROOT/'output'/'ambar.sqlite3')))
    worker = worker and os.environ.get('AMBAR_WORKER','1')=='1'

    async def agendador(acao, intervalo):
        while True:
            try: await run_in_threadpool(acao)
            except Exception: logger.exception('Falha no ciclo: %s',acao.__name__)
            await asyncio.sleep(intervalo)

    @asynccontextmanager
    async def lifespan(app):
        tasks=[asyncio.create_task(agendador(acao,intervalo)) for acao,intervalo in
               [(caderno.consultas_tick,15),(caderno.email_tick,10),(caderno.backup_tick,60)]] if worker else []
        yield
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)

    app=FastAPI(title='Caderno Âmbar',version='2.0',lifespan=lifespan,docs_url=None if producao else '/api/docs')
    app.state.caderno=caderno
    from urllib.parse import urlsplit
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost',urlsplit(origem).hostname or 'localhost'])

    def limitar(chave, maximo, janela):
        with caderno.conexao() as db:
            db.execute('BEGIN IMMEDIATE')
            r=db.execute('SELECT * FROM limites WHERE chave=?',(chave,)).fetchone()
            if r and time.time()-r['inicio']<janela:
                if r['quantidade']>=maximo: raise FalhaAPI(429,'Limite temporário atingido. Tente mais tarde.')
                db.execute('UPDATE limites SET quantidade=quantidade+1 WHERE chave=?',(chave,))
            else: db.execute('INSERT OR REPLACE INTO limites VALUES(?,?,1)',(chave,time.time()))

    def resposta_falha(exc):
        corpo={'error':str(exc)}
        if exc.codigo:corpo['code']=exc.codigo
        if exc.aguardar:corpo['retry_after']=exc.aguardar
        resposta=JSONResponse(corpo,status_code=exc.status)
        if exc.aguardar:resposta.headers['Retry-After']=str(exc.aguardar)
        return resposta

    @app.middleware('http')
    async def controles(request, call_next):
        identificador=secrets.token_hex(8)
        try:
            if request.method in ('POST','PATCH','DELETE'):
                if request.headers.get('origin') not in (None,origem): raise FalhaAPI(403,'Origem recusada.')
                if request.headers.get('sec-fetch-site')=='cross-site': raise FalhaAPI(403,'Requisição entre sites recusada.')
                tamanho=int(request.headers.get('content-length','0'))
                if tamanho<0 or tamanho>150000: raise FalhaAPI(413,'Requisição excede 150 KB.')
                # Controla também requisições sem Content-Length antes de entregar ao roteador.
                recebido=bytearray()
                async for parte in request.stream():
                    recebido.extend(parte)
                    if len(recebido)>150000: raise FalhaAPI(413,'Requisição excede 150 KB.')
                request._body=bytes(recebido)
            resposta=await call_next(request)
        except FalhaAPI as exc: resposta=resposta_falha(exc)
        except Exception:
            logger.exception('Erro de requisição %s',identificador)
            resposta=JSONResponse({'error':'Erro interno. Consulte o identificador da requisição.'},status_code=500)
        resposta.headers['X-Request-ID']=identificador
        resposta.headers['X-Content-Type-Options']='nosniff'
        resposta.headers['Referrer-Policy']='same-origin'
        resposta.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if producao: resposta.headers['Strict-Transport-Security']='max-age=31536000'
        if request.url.path.startswith('/api/'): resposta.headers['Cache-Control']='no-store'
        if not producao and request.url.path.endswith(('.html','.css','.js')):
            resposta.headers['Cache-Control']='no-store'
        return resposta

    @app.exception_handler(FalhaAPI)
    async def falha(request, exc): return resposta_falha(exc)

    @app.get('/api/saude')
    def saude():
        with caderno.conexao() as db: db.execute('SELECT 1')
        return {'status':'ok','engine':'python','version':'2.0','datajud':os.environ.get('AMBAR_DATAJUD_HABILITADO')=='1'}

    @app.get('/runtime-config.js')
    def runtime(): return Response('window.AMBAR_RUNTIME={mode:"python",api:"/api/consultar"};',media_type='text/javascript')

    @app.get('/api/carteira', tags=['Processos'])
    def carteira(request: Request, org: int | None = None, pagina: int = 1, busca: str = '', filtro: str = 'all'):
        """Carteira paginada no banco. Contagens abrangem o escritório inteiro."""
        usuario=caderno.usuario(request.cookies.get('ambar',''))
        return caderno.carteira(usuario,org,pagina,busca,filtro)

    async def dados(request):
        if request.headers.get('content-type','').split(';')[0]!='application/json': raise FalhaAPI(400,'Envie application/json.')
        try: d=await request.json()
        except ValueError: raise FalhaAPI(400,'JSON inválido.')
        if not isinstance(d,dict): raise FalhaAPI(400,'Envie um objeto JSON.')
        return d

    @app.api_route('/api/{caminho:path}',methods=['GET','POST'])
    async def endpoint(caminho,request:Request):
        d=await dados(request) if request.method=='POST' else {}
        try: return await run_in_threadpool(dispatch,caminho,request,d)
        except (ValueError,TypeError): raise FalhaAPI(400,'Campos inválidos na solicitação.')

    def dispatch(path,request,d):
        post=request.method=='POST'
        token=request.cookies.get('ambar','')
        ip=request.client.host if request.client else 'local'
        if path in ('conta/cadastro','conta/login') and post:
            limitar('auth:'+ip,20,900)
            token=caderno.autenticar(d,path.endswith('cadastro'))
            r=JSONResponse({'status':'autenticado'})
            r.set_cookie('ambar',token,max_age=28800,httponly=True,secure=producao,samesite='strict')
            return r
        if path=='conta/recuperar' and post:
            if producao and not all(os.environ.get(k) for k in ['AMBAR_SMTP_HOST','AMBAR_SMTP_USER','AMBAR_SMTP_PASSWORD','AMBAR_EMAIL_FROM']):
                raise FalhaAPI(503,'Recuperação indisponível: canal SMTP não configurado.')
            limitar('recuperar:'+ip,5,3600)
            segredo=None
            with caderno.conexao() as db:
                u=db.execute('SELECT id FROM usuarios WHERE email=?',(str(d.get('email','')).lower(),)).fetchone()
                if u:
                    segredo=secrets.token_urlsafe(32)
                    db.execute('DELETE FROM recuperacoes WHERE usuario=?',(u['id'],))
                    db.execute('INSERT INTO recuperacoes VALUES(?,?,?)',(hashlib.sha256(segredo.encode()).hexdigest(),u['id'],time.time()+1800))
            if segredo:
                entregar(Path(caderno.arquivo).parent,d['email'],'Recuperação do Caderno Âmbar',{'token':segredo,'tipo':'recuperacao','validade_minutos':30})
            return {'status':'Se houver uma conta, as instruções serão disponibilizadas no canal configurado.'}
        if path=='conta/redefinir' and post:
            senha=d.get('senha','')
            if not isinstance(senha,str) or not 10<=len(senha)<=128: raise FalhaAPI(400,'Senha deve ter 10 a 128 caracteres.')
            with caderno.conexao() as db:
                db.execute('BEGIN IMMEDIATE')
                hash_token=hashlib.sha256(str(d.get('token','')).encode()).hexdigest()
                r=db.execute('SELECT * FROM recuperacoes WHERE token=? AND expira>?',(hash_token,time.time())).fetchone()
                if not r: raise FalhaAPI(400,'Token inválido ou expirado.')
                salt=secrets.token_hex(16)
                db.execute('UPDATE usuarios SET salt=?,senha=? WHERE id=?',(salt,caderno.hash_senha(senha,salt),r['usuario']))
                db.execute('DELETE FROM sessoes WHERE usuario=?',(r['usuario'],))
                db.execute('DELETE FROM recuperacoes WHERE usuario=?',(r['usuario'],))
            return {'status':'Senha alterada; entre novamente.'}
        if path=='consultar' and post:
            if producao: raise FalhaAPI(404,'Laboratório desativado.')
            return consultar_fonte(origem+'/portal.html',validar_entradas(d.get('cases')))
        usuario=caderno.usuario(token)
        org=d.get('org') if post else request.query_params.get('org')
        if path=='conta' and not post:return caderno.conta(usuario)
        if path=='conta/verificacao/solicitar' and post:
            limitar('verificar:'+str(usuario),3,3600)
            return caderno.solicitar_verificacao(usuario)
        if path=='conta/verificacao/confirmar' and post:
            limitar('confirmar:'+str(usuario),10,900)
            return caderno.confirmar_email(usuario,d.get('token'))
        if path=='resumo' and not post:return caderno.resumo_diario(usuario,org)
        if path=='dados/solicitar' and post:return caderno.solicitar_dados(usuario,org,d.get('tipo'),d.get('motivo'))
        if path=='dados/exportar' and not post:
            return Response(json.dumps(caderno.exportar_escritorio(usuario,org),ensure_ascii=False),media_type='application/json',
                            headers={'Content-Disposition':'attachment; filename=escritorio-ambar.json'})
        if path=='conta/sair' and post:
            caderno.sair(token);r=JSONResponse({'status':'encerrado'});r.delete_cookie('ambar');return r
        if path=='contexto' and not post: return caderno.contexto(usuario)
        if path=='me' and not post:return caderno.me(usuario,org)
        if path=='rotina' and not post:
            return caderno.rotina(usuario,org,request.query_params.get('filtro','minhas'),int(request.query_params.get('pagina',1)),request.query_params.get('busca',''))
        if path=='providencias' and post:return caderno.criar_providencia(usuario,d)
        if path=='operacao' and not post:return caderno.operacao(usuario,org)
        if path=='operacao/reprocessar' and post:return caderno.reprocessar(usuario,org,d.get('tipo'),int(d['id']))
        segmento=path.split('/')
        if len(segmento)==3 and segmento[0]=='providencias' and segmento[1].isdigit():
            if segmento[2]=='alterar' and post:return caderno.alterar_providencia(usuario,int(segmento[1]),d)
            if segmento[2]=='historico' and not post:return caderno.historico_providencia(usuario,int(segmento[1]))
        if path=='organizacao/nome' and post:
            nome=d.get('nome','')
            if not isinstance(nome,str) or not 1<=len(nome.strip())<=120:raise FalhaAPI(400,'Nome deve ter de 1 a 120 caracteres.')
            with caderno.conexao() as db:
                org=caderno.org(db,usuario,org,True)
                db.execute('UPDATE organizacoes SET nome=? WHERE id=?',(nome.strip(),org))
                caderno.audit(db,org,usuario,'nome do escritório alterado')
            return {'status':'Nome atualizado.'}
        if path=='preferencias' and post:
            with caderno.conexao() as db:
                db.execute('INSERT OR REPLACE INTO preferencias VALUES(?,?)',(usuario,int(d.get('email') is True)))
            return {'status':'Preferência salva. Desenvolvimento usa caixa local; produção requer SMTP configurado.'}
        if path=='membros' and not post: return caderno.membros(usuario,org)
        if path=='convites/criar' and post: return caderno.convidar(usuario,org,d.get('email'))
        if path=='convites/aceitar' and post: return caderno.aceitar(usuario,str(d.get('token','')))
        if path=='membros/revogar' and post: return caderno.revogar(usuario,org,int(d['usuario']))
        if path=='casos': return caderno.adicionar(usuario,d) if post else caderno.listar(usuario,org)
        if path=='exportar' and not post:
            arquivo=io.StringIO();w=csv.writer(arquivo,delimiter=';')
            w.writerow(['numero','tribunal','apelido','responsavel','ultima_consulta','conferido','erro'])
            def celula(v):
                s=str(v or '')
                return "'"+s if s.startswith(('=','+','-','@','\t','\r')) else s
            for c in caderno.carteira_exportavel(usuario,org):w.writerow([celula(c[k]) for k in ['numero','tribunal','apelido','responsavel_email','ultima_ok','conferido','erro']])
            return Response('\ufeff'+arquivo.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=caderno-ambar.csv'})
        if path=='demonstracao' and post:
            if producao: raise FalhaAPI(404,'Demonstração desativada em produção.')
            return caderno.demonstracao(usuario,org)
        if path=='importar' and post: return caderno.importar(usuario,org,d.get('csv'),bool(d.get('confirmar')))
        if path in ('notificacoes','auditoria') and not post:
            with caderno.conexao() as db:
                org=caderno.org(db,usuario,org,admin=path=='auditoria')
                return [dict(r) for r in db.execute(f'SELECT * FROM {path} WHERE org=? ORDER BY id DESC LIMIT 200',(org,))]
        partes=path.split('/')
        if len(partes)==3 and partes[0]=='casos' and partes[1].isdigit():
            id=int(partes[1]);acao=partes[2]
            if acao=='agendar' and post:
                limitar('consultas:agendar:'+str(usuario),30,60)
                return JSONResponse(caderno.agendar_consulta(usuario,id),status_code=202)
            if acao=='consultar' and post:
                limitar('consultas:global',60,60)
                return caderno.consultar(usuario,id)
            if acao=='alterar' and post: return caderno.alterar(usuario,id,d)
            if acao=='revisar' and post: return caderno.revisar(usuario,id,int(d['versao_id']),d.get('observacao',''))
            if acao=='historico' and not post: return caderno.historico(usuario,id)
            if acao=='detalhe' and not post: return caderno.detalhe(usuario,id)
            if acao=='avancar-demo' and post:
                if producao: raise FalhaAPI(404,'Demonstração desativada.')
                with caderno.conexao() as db:
                    c=caderno.caso(db,usuario,id)
                    if c['fonte']!='demo': raise FalhaAPI(400,'Ação disponível somente na demonstração.')
                    db.execute('UPDATE casos SET etapa=1 WHERE id=?',(id,))
                return {'status':'Fonte fictícia atualizada. Consulte novamente.'}
        raise FalhaAPI(404,'Endpoint inexistente.')

    app.mount('/',StaticFiles(directory=str(ROOT/'frontend'),html=True),name='interface')
    return app


if __name__=='__main__':
    import uvicorn
    uvicorn.run(criar_app(),host='127.0.0.1',port=int(os.environ.get('AMBAR_PORT','8093')),proxy_headers=False)
