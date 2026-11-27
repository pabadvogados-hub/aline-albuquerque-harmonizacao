"""
Central de atendimento (estilo ManyChat) da Dra. Aline - servidor FastAPI.

  cd atendimento
  uvicorn app:app --host 127.0.0.1 --port 8077

Rotas:
  GET  /webhook                 verificacao da Meta (hub.verify_token = ATEND_VERIFY_TOKEN)
  POST /webhook                 eventos do Instagram e da Pagina (assinatura X-Hub-Signature-256)
  GET  /                        central web (login por ATEND_SENHA)
  /api/...                      dados da central (exigem login)
"""
import hashlib
import hmac
import json
import queue
import threading
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

import banco as db
import exportar
import motor
from ajustes import automacoes, configurar_log, env, funil, marca, salvar_automacoes, simulando

log = configurar_log()
AQUI = Path(__file__).resolve().parent
COOKIE = 'atend_sessao'
VALIDADE_SESSAO = 14 * 86400

# fila unica: eventos processados em ordem de chegada (o fluxo depende da ordem) e fora
# da requisicao, para a Meta receber o 200 na hora
_fila = queue.Queue()


def _trabalhador():
    while True:
        payload = _fila.get()
        try:
            motor.processar(payload)
        finally:
            _fila.task_done()


@asynccontextmanager
async def _ciclo(_app):
    db.init()
    threading.Thread(target=_trabalhador, daemon=True, name='webhook').start()
    log.info(f"central no ar | simulacao={'SIM' if simulando() else 'nao'}")
    yield


app = FastAPI(title='Central de atendimento', docs_url=None, redoc_url=None, lifespan=_ciclo)


# ============================================================
# WEBHOOK
# ============================================================

@app.get('/webhook')
def verificar(request: Request):
    p = request.query_params
    if p.get('hub.mode') == 'subscribe' and p.get('hub.verify_token') == env('ATEND_VERIFY_TOKEN') \
            and env('ATEND_VERIFY_TOKEN'):
        return PlainTextResponse(p.get('hub.challenge', ''))
    raise HTTPException(403, 'token de verificacao invalido')


def _assinatura_ok(corpo, cabecalho):
    segredo = env('META_APP_SECRET')
    if not segredo:
        return simulando()   # sem segredo so aceita em simulacao
    esperado = 'sha256=' + hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, cabecalho or '')


@app.post('/webhook')
async def receber(request: Request):
    corpo = await request.body()
    if not _assinatura_ok(corpo, request.headers.get('x-hub-signature-256')):
        log.warning('webhook com assinatura invalida recusado')
        raise HTTPException(403, 'assinatura invalida')
    try:
        payload = json.loads(corpo or b'{}')
    except ValueError:
        return PlainTextResponse('EVENT_RECEIVED')
    _fila.put(payload)   # responde 200 na hora, processa na fila
    return PlainTextResponse('EVENT_RECEIVED')


# ============================================================
# LOGIN
# ============================================================

def _chave():
    return (env('ATEND_CHAVE') or hashlib.sha256(('aline|' + env('ATEND_SENHA')).encode()).hexdigest()).encode()


def _token_sessao():
    exp = str(int(time.time()) + VALIDADE_SESSAO)
    return exp + '.' + hmac.new(_chave(), exp.encode(), hashlib.sha256).hexdigest()


def _logado(request):
    v = request.cookies.get(COOKIE) or ''
    exp, _, ass = v.partition('.')
    if not exp.isdigit() or int(exp) < time.time():
        return False
    return hmac.compare_digest(ass, hmac.new(_chave(), exp.encode(), hashlib.sha256).hexdigest())


@app.middleware('http')
async def _proteger(request: Request, chamar):
    if request.url.path.startswith('/api/') and request.url.path != '/api/login' and not _logado(request):
        return JSONResponse({'erro': 'faca login'}, status_code=401)
    return await chamar(request)


@app.post('/api/login')
async def login(request: Request):
    dados = await request.json()
    senha = env('ATEND_SENHA')
    if not senha:
        return JSONResponse({'erro': 'Defina ATEND_SENHA no config/.env'}, status_code=400)
    if not hmac.compare_digest(str(dados.get('senha') or ''), senha):
        time.sleep(1)
        return JSONResponse({'erro': 'Senha incorreta'}, status_code=401)
    r = JSONResponse({'ok': True})
    r.set_cookie(COOKIE, _token_sessao(), max_age=VALIDADE_SESSAO, httponly=True, samesite='lax',
                 secure=request.url.scheme == 'https')
    return r


@app.post('/api/sair')
def sair():
    r = JSONResponse({'ok': True})
    r.delete_cookie(COOKIE)
    return r


# ============================================================
# CENTRAL WEB
# ============================================================

@app.get('/', response_class=HTMLResponse)
def central():
    html = (AQUI / 'central.html').read_text(encoding='utf-8')
    if simulando():
        html = html.replace('<main id="app"></main>',
                            '<div class="sim">MODO SIMULACAO: nada e enviado para o Instagram. '
                            'As respostas do robo ficam so aqui na central.</div><main id="app"></main>')
    return html.replace('/*__MARCA__*/null', json.dumps(marca(), ensure_ascii=False).replace('</', '<\\/'))


def _contato_resumo(r):
    c = db.contato_dict(r)
    c['janela_horas'] = motor.janela(c)
    c['robo_pausado'] = motor.robo_pausado(c)
    c['campos_visiveis'] = {k: v for k, v in c['campos'].items() if not k.startswith('_')}
    return c


@app.get('/api/conversas')
def conversas(busca: str = '', etapa: str = '', limite: int = 500):
    sql = ("SELECT k.*, (SELECT texto FROM mensagens m WHERE m.contato_id=k.id ORDER BY quando DESC, id DESC LIMIT 1) "
           "ultima_msg, (SELECT direcao FROM mensagens m WHERE m.contato_id=k.id ORDER BY quando DESC, id DESC LIMIT 1) "
           "ultima_dir FROM contatos k WHERE 1=1")
    args = []
    if etapa:
        sql += ' AND k.etapa=?'
        args.append(etapa)
    if busca:
        sql += ' AND (k.username LIKE ? OR k.nome LIKE ? OR k.tags LIKE ? OR k.campos LIKE ?)'
        args += [f'%{busca}%'] * 4
    sql += ' ORDER BY COALESCE(k.ultima_msg_em, k.criado_em) DESC LIMIT ?'
    args.append(min(limite, 2000))
    with db.conectar() as c:
        linhas = c.execute(sql, args).fetchall()
    out = []
    for r in linhas:
        d = _contato_resumo(r)
        d['ultima_msg'] = r['ultima_msg']
        d['ultima_dir'] = r['ultima_dir']
        out.append(d)
    return {'contatos': out, 'funil': funil()}


@app.get('/api/contato/{cid}')
def contato(cid: int):
    with db.conectar() as c:
        r = c.execute('SELECT * FROM contatos WHERE id=?', (cid,)).fetchone()
        if not r:
            raise HTTPException(404, 'contato nao encontrado')
        msgs = [dict(x) for x in c.execute('SELECT * FROM mensagens WHERE contato_id=? ORDER BY quando, id', (cid,))]
        evs = [dict(x) for x in c.execute('SELECT * FROM eventos WHERE contato_id=? ORDER BY quando DESC LIMIT 50',
                                          (cid,))]
        hist = [dict(x) for x in c.execute('SELECT etapa, quando FROM etapas_historico WHERE contato_id=? '
                                           'ORDER BY quando, id', (cid,))]
    nomes = {a['id']: a.get('nome') for a in automacoes().get('automacoes', [])}
    d = _contato_resumo(r)
    d['automacao_origem_nome'] = nomes.get(d.get('automacao_origem'), d.get('automacao_origem'))
    return {'contato': d, 'mensagens': msgs, 'eventos': evs, 'historico': hist}


@app.post('/api/contato/{cid}/enviar')
async def enviar(cid: int, request: Request):
    texto = ((await request.json()).get('texto') or '').strip()
    if not texto:
        return JSONResponse({'ok': False, 'erro': 'mensagem vazia'}, status_code=400)
    return motor.enviar_manual(cid, texto)


@app.post('/api/contato/{cid}/etapa')
async def etapa(cid: int, request: Request):
    d = await request.json()
    nova = d.get('etapa')
    if nova not in funil():
        return JSONResponse({'ok': False, 'erro': 'etapa invalida'}, status_code=400)
    extra = {}
    if d.get('procedimento') is not None:
        extra['procedimento'] = str(d['procedimento'])[:120]
    if d.get('valor') not in (None, ''):
        try:
            extra['valor_fechado'] = float(str(d['valor']).replace('.', '').replace(',', '.')) \
                if ',' in str(d['valor']) else float(d['valor'])
        except ValueError:
            return JSONResponse({'ok': False, 'erro': 'valor invalido'}, status_code=400)
    db.mudar_etapa(cid, nova)
    if extra:
        db.atualizar(cid, **extra)
    return {'ok': True}


@app.post('/api/contato/{cid}')
async def editar(cid: int, request: Request):
    d = await request.json()
    c = db.buscar_contato(cid)
    if not c:
        raise HTTPException(404, 'contato nao encontrado')
    campos = {}
    if 'tags' in d:
        campos['tags'] = [str(t).strip()[:40] for t in d['tags'] if str(t).strip()]
    if 'campos' in d:
        internos = {k: v for k, v in c['campos'].items() if k.startswith('_')}
        campos['campos'] = {**{str(k)[:40]: str(v)[:300] for k, v in d['campos'].items()}, **internos}
    for k in ('nome', 'responsavel', 'procedimento'):
        if k in d:
            campos[k] = (str(d[k]) or '')[:120]
    db.atualizar(cid, **campos)
    if 'robo_pausado' in d:
        if d['robo_pausado']:
            motor.pausar_robo(cid, horas=24 * 365)
        else:
            db.salvar_campo(cid, '_robo_pausado_ate', None)
    return {'ok': True}


@app.get('/api/respostas-rapidas')
def respostas():
    with db.conectar() as c:
        return {'respostas': [dict(r) for r in c.execute('SELECT * FROM respostas_rapidas ORDER BY titulo')]}


@app.post('/api/respostas-rapidas')
async def nova_resposta(request: Request):
    d = await request.json()
    if not (d.get('titulo') and d.get('texto')):
        return JSONResponse({'ok': False, 'erro': 'titulo e texto'}, status_code=400)
    with db.conectar() as c:
        c.execute('INSERT INTO respostas_rapidas(titulo, texto) VALUES (?, ?)', (d['titulo'][:40], d['texto'][:1000]))
    return {'ok': True}


@app.delete('/api/respostas-rapidas/{rid}')
def apagar_resposta(rid: int):
    with db.conectar() as c:
        c.execute('DELETE FROM respostas_rapidas WHERE id=?', (rid,))
    return {'ok': True}


@app.get('/api/automacoes')
def lista_automacoes(dias: int = 30):
    cfg = automacoes()
    desde = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d %H:%M:%S')
    f = funil()
    ix_q = next((i for i, e in enumerate(f) if 'qualific' in e.lower()), 2)
    with db.conectar() as c:
        disparos = {r['automacao']: r['n'] for r in c.execute(
            'SELECT automacao, COUNT(*) n FROM eventos WHERE quando>=? GROUP BY automacao', (desde,))}
        responderam = {r['automacao']: r['n'] for r in c.execute(
            "SELECT e.automacao, COUNT(DISTINCT e.contato_id) n FROM eventos e WHERE e.quando>=? AND EXISTS "
            "(SELECT 1 FROM mensagens m WHERE m.contato_id=e.contato_id AND m.direcao='entrada' AND m.quando>e.quando) "
            "GROUP BY e.automacao", (desde,))}
        qualif = {r['a']: r['n'] for r in c.execute(
            'SELECT k.automacao_origem a, COUNT(DISTINCT k.id) n FROM contatos k JOIN etapas_historico h '
            f"ON h.contato_id=k.id WHERE k.criado_em>=? AND h.etapa IN ({','.join('?' * len(f[ix_q:-1]))}) "
            'GROUP BY k.automacao_origem', (desde, *f[ix_q:-1]))}
    out = []
    for a in cfg.get('automacoes', []):
        out.append({**a, 'disparos': disparos.get(a['id'], 0), 'responderam': responderam.get(a['id'], 0),
                    'qualificados': qualif.get(a['id'], 0)})
    return {'automacoes': out, 'expediente': cfg.get('expediente'), 'fluxos': cfg.get('fluxos'), 'dias': dias}


@app.post('/api/automacoes/{aid}')
async def salvar_automacao(aid: str, request: Request):
    d = await request.json()
    cfg = automacoes()
    a = next((x for x in cfg.get('automacoes', []) if x.get('id') == aid), None)
    if not a:
        raise HTTPException(404, 'automacao nao encontrada')
    if 'ativa' in d:
        a['ativa'] = bool(d['ativa'])
    if 'palavras' in d and a.get('gatilho', {}).get('tipo') in ('comentario', 'dm_palavra'):
        a['gatilho']['palavras'] = [str(p).strip()[:40] for p in d['palavras'] if str(p).strip()][:40]
    if 'resposta_publica' in d and a.get('gatilho', {}).get('tipo') == 'comentario':
        a['resposta_publica'] = [str(p).strip()[:300] for p in d['resposta_publica'] if str(p).strip()][:6]
    if 'texto' in d:
        a.setdefault('mensagem', {})['texto'] = str(d['texto'])[:1000]
    if 'opcoes' in d:
        a.setdefault('mensagem', {})['opcoes'] = [str(o).strip()[:20] for o in d['opcoes'] if str(o).strip()][:13]
    salvar_automacoes(cfg)
    log.info(f'automacao {aid} alterada pela central')
    return {'ok': True}


@app.get('/api/numeros')
def numeros(dias: int = 30):
    fim = date.today()
    ini = fim - timedelta(days=max(1, dias) - 1)
    r = exportar.resumo(ini, fim)
    if not r.get('ok'):
        return r
    with db.conectar() as c:
        h = c.execute(
            "SELECT AVG((julianday(s.q) - julianday(e.q)) * 1440) m FROM "
            "(SELECT contato_id, MIN(quando) q FROM mensagens WHERE direcao='entrada' AND quando>=? GROUP BY contato_id) e "
            "JOIN (SELECT contato_id, MIN(quando) q FROM mensagens WHERE direcao='saida' AND autor IN ('equipe','app_instagram') "
            "GROUP BY contato_id) s ON s.contato_id=e.contato_id AND s.q>=e.q", (f'{ini} 00:00:00',)).fetchone()
        ticket = c.execute("SELECT AVG(valor_fechado) t FROM contatos WHERE valor_fechado>0").fetchone()
        procs = [dict(x) for x in c.execute(
            "SELECT procedimento, COUNT(*) n, SUM(valor_fechado) total FROM contatos WHERE valor_fechado>0 "
            "AND procedimento IS NOT NULL GROUP BY procedimento ORDER BY total DESC LIMIT 10")]
    r['tempo_primeira_resposta_humana_min'] = round(h['m'], 1) if h and h['m'] is not None else None
    r['ticket_medio'] = round(ticket['t'], 2) if ticket and ticket['t'] else None
    r['procedimentos'] = procs
    r['dias'] = dias
    return r
