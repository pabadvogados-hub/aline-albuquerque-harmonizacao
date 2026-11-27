"""
Motor de automacoes: recebe o JSON do webhook da Meta e decide o que responder.

Ordem de decisao para cada mensagem recebida:
  1. eco (mensagem enviada pela clinica pelo app do Instagram) -> registra e pausa o robo
  2. robo pausado para o contato (humano conversando) -> so registra
  3. botao clicado (quick reply / postback) -> passo do fluxo ou opcao global
  4. contato no meio de um fluxo -> trata como resposta da pergunta atual
  5. entrada por anuncio, mencao em story, resposta a story, palavra-chave no Direct
  6. primeira mensagem -> boas-vindas

Regras da Meta respeitadas aqui:
  - resposta privada: 1 por comentario (tabela comentarios_respondidos), so ate 7 dias
  - Direct automatico so em resposta a mensagem da pessoa (sempre dentro das 24h)
  - depois de uma resposta privada, nada mais e enviado ate a pessoa responder
  - nenhum disparo em massa: o robo so fala com quem acabou de falar com a clinica
"""
import json
import logging
import random
import threading
import unicodedata
import urllib.parse
from datetime import datetime, timedelta

import requests

import banco as db
import meta_envio as envio
from ajustes import automacoes, env, funil, marca, simulando

log = logging.getLogger('atendimento')
_trava = threading.RLock()

PAUSA_HUMANO_HORAS = 12
FLUXO_PENDENTE = -1          # fluxo combinado, esperando a pessoa aceitar


# ============================================================
# UTEIS
# ============================================================

def normalizar(txt):
    txt = unicodedata.normalize('NFKD', str(txt or '')).encode('ascii', 'ignore').decode()
    return ' '.join(txt.lower().split())


def slug(txt):
    return '_'.join(normalizar(txt).replace('/', ' ').split())[:40]


def casa(texto, palavras):
    t = f' {normalizar(texto)} '
    for p in palavras or []:
        p = normalizar(p)
        if p and (f' {p} ' in t or (len(p) > 4 and p in t)):
            return p
    return None


def _dt(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        return None


def primeiro_nome(c):
    nome = (c.get('nome') or '').strip()
    if nome:
        return nome.split()[0].title()
    return c.get('username') or 'tudo bem'


def renderizar(texto, c, extra=None):
    vals = {'nome': c.get('nome') or c.get('username') or '', 'primeiro_nome': primeiro_nome(c),
            'username': c.get('username') or '', 'resumo': '', 'whatsapp_link': ''}
    vals.update(extra or {})
    out = texto or ''
    for k, v in vals.items():
        out = out.replace('{' + k + '}', str(v))
    return out


def dentro_expediente(cfg, quando=None):
    e = cfg.get('expediente') or {}
    quando = quando or datetime.now()
    if e.get('dias') is not None and quando.weekday() not in e['dias']:
        return False
    hm = quando.strftime('%H:%M')
    return e.get('inicio', '00:00') <= hm < e.get('fim', '23:59')


def robo_pausado(c):
    ate = _dt((c.get('campos') or {}).get('_robo_pausado_ate'))
    return bool(ate and ate > datetime.now())


def pausar_robo(cid, horas=PAUSA_HUMANO_HORAS):
    ate = (datetime.now() + timedelta(hours=horas)).strftime('%Y-%m-%d %H:%M:%S')
    db.salvar_campo(cid, '_robo_pausado_ate', ate)


def notificar(c, motivo):
    log.info(f"[EQUIPE] {motivo} | contato {c['id']} @{c.get('username') or c.get('externo_id')}")
    url = env('ATEND_NOTIFICAR_URL')
    if not url or simulando():
        return

    def _enviar():
        try:
            requests.post(url, json={'motivo': motivo, 'contato_id': c['id'], 'username': c.get('username'),
                                     'nome': c.get('nome'), 'etapa': c.get('etapa'),
                                     'campos': {k: v for k, v in (c.get('campos') or {}).items()
                                                if not k.startswith('_')}}, timeout=10)
        except requests.RequestException as e:
            log.warning(f'notificacao falhou: {e}')
    threading.Thread(target=_enviar, daemon=True).start()


# ============================================================
# ENVIO (sempre registrado no banco)
# ============================================================

def _opcoes(titulos, prefixo='OPT'):
    return [{'titulo': t, 'payload': f'{prefixo}|{t}'} for t in titulos or []]


def enviar(c, texto, opcoes=None, botao=None, automacao=None, autor='robo', tag=None):
    mid = envio.enviar_dm(c['externo_id'], texto, opcoes=opcoes, botao=botao, tag=tag)
    corpo = texto + (('\n[' + ' | '.join(o['titulo'] for o in opcoes) + ']') if opcoes else '') + \
        (f"\n[botao: {botao['titulo']}]" if botao else '')
    db.registrar_msg(c['id'], 'saida', corpo, 'texto' if not opcoes else 'quick_reply',
                     meta_id=mid, automacao=automacao, autor=autor)
    return mid


def aplicar_acoes(c, acoes, automacao=None):
    if not acoes:
        return
    if acoes.get('tags'):
        db.adicionar_tags(c['id'], acoes['tags'])
    if acoes.get('etapa'):
        db.avancar_etapa(c['id'], acoes['etapa'])
    for k, v in (acoes.get('campos') or {}).items():
        db.salvar_campo(c['id'], k, v)
    if acoes.get('notificar'):
        notificar(db.buscar_contato(c['id']), f'automacao {automacao or ""}')


def _aviso_fora(c, cfg):
    if dentro_expediente(cfg):
        return
    ultimo = _dt((c.get('campos') or {}).get('_aviso_fora_em'))
    if ultimo and datetime.now() - ultimo < timedelta(hours=12):
        return
    texto = (cfg.get('expediente') or {}).get('mensagem_fora')
    if texto:
        enviar(c, renderizar(texto, c), automacao='expediente')
        db.salvar_campo(c['id'], '_aviso_fora_em', db.agora())


# ============================================================
# FLUXO DE QUALIFICACAO
# ============================================================

def _fluxo(cfg, nome):
    return (cfg.get('fluxos') or {}).get(nome)


def iniciar_fluxo(c, cfg, nome, automacao=None):
    f = _fluxo(cfg, nome)
    if not f:
        log.warning(f'fluxo inexistente: {nome}')
        return
    fim = _dt(c.get('fluxo_fim_em'))
    if fim and datetime.now() - fim < timedelta(days=7):
        # ja respondeu as perguntas ha pouco: nao recomeca, so reenvia o caminho do WhatsApp
        _enviar_final(c, cfg, nome, f, reenvio=True, automacao=automacao)
        return
    db.atualizar(c['id'], fluxo=nome, fluxo_passo=0)
    c = db.buscar_contato(c['id'])
    _perguntar(c, f, 0, nome, automacao)


def _perguntar(c, f, passo, nome, automacao=None):
    p = f['passos'][passo]
    ops = [{'titulo': o, 'payload': f'FLX|{nome}|{passo}|{i}'} for i, o in enumerate(p.get('opcoes') or [])]
    enviar(c, renderizar(p['pergunta'], c), opcoes=ops, automacao=automacao or f'fluxo:{nome}')


def _resumo(c, f):
    campos = c.get('campos') or {}
    partes = []
    for p in f['passos']:
        v = campos.get(p['campo'])
        if v:
            partes.append(f"{p['campo'].replace('_', ' ').capitalize()}: {v}")
    return ' | '.join(partes)


def _enviar_final(c, cfg, nome, f, reenvio=False, automacao=None):
    fin = f.get('final') or {}
    resumo = _resumo(c, f)
    numero = ''.join(ch for ch in (marca().get('whatsapp') or '') if ch.isdigit())
    wtxt = renderizar(fin.get('whatsapp_texto') or '', c, {'resumo': resumo})
    link = f'https://wa.me/{numero}?text={urllib.parse.quote(wtxt)}' if numero else ''
    if reenvio:
        texto = renderizar('Ja estou com as suas respostas aqui, {primeiro_nome}. Para escolher o horario da '
                           'avaliacao e so tocar no botao abaixo.', c)
    else:
        texto = renderizar(fin.get('texto') or '', c, {'resumo': resumo, 'whatsapp_link': link})
    botao = {'titulo': fin.get('botao') or 'WhatsApp', 'url': link} if link else None
    enviar(c, texto, botao=botao, automacao=automacao or f'fluxo:{nome}')
    if reenvio:
        return
    db.atualizar(c['id'], fluxo=None, fluxo_passo=None, fluxo_fim_em=db.agora())
    db.salvar_campo(c['id'], '_resumo', resumo)
    if fin.get('tags'):
        db.adicionar_tags(c['id'], fin['tags'])
    if fin.get('etapa'):
        db.avancar_etapa(c['id'], fin['etapa'])
    db.registrar_evento(c['id'], c.get('automacao_origem') or f'fluxo:{nome}', 'fluxo_concluido', resumo)
    if fin.get('notificar'):
        notificar(db.buscar_contato(c['id']), f'lead qualificado: {resumo}')


def responder_fluxo(c, cfg, texto, payload=None):
    """Trata a resposta da pergunta atual. Devolve True se consumiu a mensagem."""
    nome, passo = c.get('fluxo'), c.get('fluxo_passo')
    f = _fluxo(cfg, nome)
    if not f or passo is None:
        return False
    if passo == FLUXO_PENDENTE:
        # pessoa respondeu algo depois do convite: vale como "pode sim"
        if casa(texto, ['agora nao', 'nao quero', 'nao obrigada', 'depois']):
            db.atualizar(c['id'], fluxo=None, fluxo_passo=None)
            return False
        db.atualizar(c['id'], fluxo_passo=0)
        _perguntar(db.buscar_contato(c['id']), f, 0, nome)
        return True
    if passo >= len(f['passos']):
        return False
    p = f['passos'][passo]
    ops = p.get('opcoes') or []
    resposta = None
    if payload and payload.startswith('FLX|'):
        _, pn, pp, pi = (payload.split('|') + ['', '', ''])[:4]
        if pn == nome and pp.isdigit() and int(pp) == passo and pi.isdigit() and int(pi) < len(ops):
            resposta = ops[int(pi)]
        elif pp.isdigit() and int(pp) < passo:
            return True          # clicou num botao antigo: ignora sem repetir pergunta
    if resposta is None and texto:
        n = normalizar(texto)
        for i, o in enumerate(ops):
            if n == normalizar(o) or n == str(i + 1) or (len(n) > 3 and n in normalizar(o)):
                resposta = o
                break
    if resposta is None:
        chave = f'_reperguntou_{nome}_{passo}'
        if ops and not p.get('aceita_texto') and not (c.get('campos') or {}).get(chave):
            db.salvar_campo(c['id'], chave, '1')
            enviar(c, 'Para eu anotar certinho, toca numa das opcoes abaixo:',
                   opcoes=[{'titulo': o, 'payload': f'FLX|{nome}|{passo}|{i}'} for i, o in enumerate(ops)],
                   automacao=f'fluxo:{nome}')
            return True
        resposta = (texto or '').strip()[:200]
    db.salvar_campo(c['id'], p['campo'], resposta)
    if p.get('tag_prefixo') and resposta in ops:
        db.adicionar_tags(c['id'], [p['tag_prefixo'] + slug(resposta)])
    prox = passo + 1
    c = db.buscar_contato(c['id'])
    if prox < len(f['passos']):
        db.atualizar(c['id'], fluxo_passo=prox)
        _perguntar(c, f, prox, nome)
    else:
        _enviar_final(c, cfg, nome, f)
    return True


# ============================================================
# AUTOMACOES
# ============================================================

def _ativas(cfg, tipo):
    return [a for a in cfg.get('automacoes', []) if a.get('ativa', True) and (a.get('gatilho') or {}).get('tipo') == tipo]


def disparar(c, cfg, a, gatilho, detalhe='', via_private_reply=None):
    """Executa uma automacao. via_private_reply = comment_id quando a resposta vai como privada."""
    if not c.get('automacao_origem'):
        db.atualizar(c['id'], automacao_origem=a['id'])
        c['automacao_origem'] = a['id']
    db.registrar_evento(c['id'], a['id'], gatilho, detalhe)
    msg = a.get('mensagem') or {}
    fluxo = a.get('inicia_fluxo')
    em_fluxo = c.get('fluxo') and (c.get('fluxo_passo') or 0) >= 0
    ops = _opcoes(msg.get('opcoes'))

    if via_private_reply:
        texto = renderizar(msg.get('texto') or '', c)
        if em_fluxo:
            texto = renderizar('Oi, {primeiro_nome}! Ja estamos conversando no Direct, te espero por la.', c)
            ops = []
        mid = envio.private_reply(via_private_reply, texto, opcoes=ops or None)
        db.registrar_msg(c['id'], 'saida', texto + (('\n[' + ' | '.join(o['titulo'] for o in ops) + ']') if ops else ''),
                         'private_reply', meta_id=mid, automacao=a['id'], autor='robo')
        if fluxo and not em_fluxo:
            db.atualizar(c['id'], fluxo=fluxo, fluxo_passo=FLUXO_PENDENTE)
        aplicar_acoes(c, a.get('acoes'), a['id'])
        return

    if em_fluxo:
        # nao reinicia: repete a pergunta em que a pessoa parou
        f = _fluxo(cfg, c['fluxo'])
        if f and c['fluxo_passo'] < len(f['passos']):
            _perguntar(c, f, c['fluxo_passo'], c['fluxo'], a['id'])
        return
    if msg.get('texto'):
        enviar(c, renderizar(msg['texto'], c), opcoes=ops or None, automacao=a['id'])
    aplicar_acoes(c, a.get('acoes'), a['id'])
    if fluxo:
        if ops:
            db.atualizar(c['id'], fluxo=fluxo, fluxo_passo=FLUXO_PENDENTE)
        else:
            iniciar_fluxo(db.buscar_contato(c['id']), cfg, fluxo, a['id'])


def opcao_global(c, cfg, titulo):
    og = (cfg.get('opcoes_globais') or {}).get(titulo)
    if not og or not isinstance(og, dict):
        return False
    if og.get('tags'):
        db.adicionar_tags(c['id'], og['tags'])
    if og.get('texto'):
        enviar(c, renderizar(og['texto'], c), automacao='opcao:' + slug(titulo))
    if og.get('notificar'):
        notificar(c, f'clicou em "{titulo}"')
    if og.get('inicia_fluxo'):
        iniciar_fluxo(db.buscar_contato(c['id']), cfg, og['inicia_fluxo'], c.get('automacao_origem'))
    elif c.get('fluxo_passo') == FLUXO_PENDENTE:
        db.atualizar(c['id'], fluxo=None, fluxo_passo=None)
    return True


# ============================================================
# EVENTOS DA META
# ============================================================

def _contato(canal, externo_id, origem, **extra):
    c, novo = db.obter_ou_criar(canal, externo_id, origem, **extra)
    if novo and not (c.get('nome') or c.get('username')):
        p = envio.perfil(externo_id, canal)
        if p:
            db.atualizar(c['id'], **{k: v for k, v in p.items() if v})
            c = db.buscar_contato(c['id'])
    return c, novo


def tratar_comentario(canal, comment_id, texto, autor_id, username=None, post_id=None, ad_id=None):
    proprio = env('META_IG_USER_ID') if canal == 'instagram' else env('META_PAGE_ID')
    if not comment_id or not autor_id or autor_id == proprio:
        return
    if db.comentario_ja_respondido(comment_id):
        return
    cfg = automacoes()
    c, _ = _contato(canal, autor_id, 'comentario',
                    username=username if canal == 'instagram' else None,
                    nome=username if canal == 'messenger' else None,
                    post_id=post_id, ad_id=ad_id)
    db.registrar_msg(c['id'], 'entrada', texto, 'comentario', meta_id=f'cmt_{comment_id}', autor='pessoa')
    for a in _ativas(cfg, 'comentario'):
        p = casa(texto, (a.get('gatilho') or {}).get('palavras'))
        if not p:
            continue
        db.marcar_comentario(comment_id, c['id'], a['id'])
        variacoes = a.get('resposta_publica') or []
        if variacoes:
            pub = renderizar(random.choice(variacoes), c)
            rid = envio.responder_comentario(comment_id, pub, canal)
            db.registrar_msg(c['id'], 'saida', pub, 'resposta_publica', meta_id=rid, automacao=a['id'], autor='robo')
        disparar(c, cfg, a, 'comentario', f'"{p}" em {post_id or "-"}', via_private_reply=comment_id)
        return


def tratar_mensagem(canal, sender_id, recipient_id, m, quando=None):
    mid = m.get('mid')
    if m.get('is_echo'):
        # mensagem que saiu da conta da clinica: se nao foi o robo, foi alguem pelo app
        if db.mensagem_existe(mid):
            return
        c, _ = _contato(canal, recipient_id, 'dm')
        db.registrar_msg(c['id'], 'saida', m.get('text') or '[midia]', 'texto', meta_id=mid, autor='app_instagram')
        pausar_robo(c['id'])
        return
    if m.get('is_deleted') or db.mensagem_existe(mid):
        return

    texto = m.get('text') or ''
    anexos = m.get('attachments') or []
    tipo = 'texto'
    gatilho = None
    if any(a.get('type') == 'story_mention' for a in anexos):
        tipo, gatilho = 'story_mencao', 'story_mencao'
        texto = texto or '[mencionou a clinica no story]'
    elif (m.get('reply_to') or {}).get('story'):
        tipo, gatilho = 'story_resposta', 'story_resposta'
    elif anexos and not texto:
        texto = '[' + ', '.join(a.get('type', 'anexo') for a in anexos) + ']'
    qr = (m.get('quick_reply') or {}).get('payload')
    if qr:
        tipo = 'quick_reply'
    referral = m.get('referral')

    origem = 'anuncio' if referral and referral.get('ad_id') else ('story' if gatilho else 'dm')
    c, novo = _contato(canal, sender_id, origem,
                       ad_id=(referral or {}).get('ad_id'), ref=(referral or {}).get('ref'))
    db.registrar_msg(c['id'], 'entrada', texto, tipo, meta_id=mid, autor='pessoa')
    c = db.buscar_contato(c['id'])
    if robo_pausado(c):
        return
    cfg = automacoes()
    _aviso_fora(c, cfg)

    if referral and referral.get('ad_id'):
        if not c.get('ad_id'):
            db.atualizar(c['id'], ad_id=referral.get('ad_id'), ref=referral.get('ref'))
        for a in _ativas(cfg, 'anuncio'):
            disparar(c, cfg, a, 'anuncio', f"anuncio {referral.get('ad_id')}")
            return
    if qr:
        if qr.startswith('FLX|') and responder_fluxo(c, cfg, texto, qr):
            return
        if qr.startswith('OPT|') and opcao_global(c, cfg, qr[4:]):
            return
    if c.get('fluxo') and responder_fluxo(c, cfg, texto, qr):
        return
    if gatilho:
        for a in _ativas(cfg, gatilho):
            disparar(c, cfg, a, gatilho)
            return
    if texto and opcao_global(c, cfg, next((k for k in (cfg.get('opcoes_globais') or {})
                                            if normalizar(k) == normalizar(texto)), '')):
        return
    for a in _ativas(cfg, 'dm_palavra'):
        p = casa(texto, (a.get('gatilho') or {}).get('palavras'))
        if p:
            disparar(c, cfg, a, 'dm_palavra', f'"{p}"')
            return
    if novo:
        for a in _ativas(cfg, 'primeira_mensagem'):
            disparar(c, cfg, a, 'primeira_mensagem')
            return


def tratar_postback(canal, sender_id, postback):
    payload = postback.get('payload') or ''
    titulo = postback.get('title') or ''
    c, _ = _contato(canal, sender_id, 'dm')
    db.registrar_msg(c['id'], 'entrada', titulo or payload, 'quick_reply', meta_id=postback.get('mid'), autor='pessoa')
    c = db.buscar_contato(c['id'])
    if robo_pausado(c):
        return
    cfg = automacoes()
    if payload.startswith('FLX|') and responder_fluxo(c, cfg, titulo, payload):
        return
    opcao_global(c, cfg, payload[4:] if payload.startswith('OPT|') else titulo)


def tratar_referral(canal, sender_id, referral):
    """Entrada por anuncio sem mensagem (OPEN_THREAD)."""
    if not referral.get('ad_id'):
        return
    c, _ = _contato(canal, sender_id, 'anuncio', ad_id=referral.get('ad_id'), ref=referral.get('ref'))
    if not c.get('ad_id'):
        db.atualizar(c['id'], ad_id=referral.get('ad_id'), ref=referral.get('ref'))
    db.registrar_evento(c['id'], None, 'referral', json.dumps(referral)[:300])


def processar(payload):
    """Ponto de entrada do webhook. Nunca levanta excecao."""
    with _trava:
        try:
            _processar(payload)
        except Exception:
            log.exception('erro processando webhook')


def _processar(payload):
    obj = payload.get('object')
    canal = 'instagram' if obj == 'instagram' else 'messenger'
    for entry in payload.get('entry', []):
        for ch in entry.get('changes', []):
            v = ch.get('value') or {}
            if ch.get('field') == 'comments' and canal == 'instagram':
                media = v.get('media') or {}
                tratar_comentario('instagram', v.get('id'), v.get('text') or '', (v.get('from') or {}).get('id'),
                                  (v.get('from') or {}).get('username'), media.get('id'), media.get('ad_id'))
            elif ch.get('field') == 'feed' and v.get('item') == 'comment' and v.get('verb') == 'add':
                tratar_comentario('messenger', v.get('comment_id'), v.get('message') or '',
                                  (v.get('from') or {}).get('id'), (v.get('from') or {}).get('name'),
                                  v.get('post_id'))
        for ev in entry.get('messaging', []):
            s = (ev.get('sender') or {}).get('id')
            r = (ev.get('recipient') or {}).get('id')
            if 'message' in ev:
                m = dict(ev['message'])
                if ev.get('referral') and not m.get('referral'):
                    m['referral'] = ev['referral']
                tratar_mensagem(canal, s, r, m)
            elif 'postback' in ev:
                tratar_postback(canal, s, ev['postback'])
            elif 'referral' in ev:
                tratar_referral(canal, s, ev['referral'])


# ============================================================
# ENVIO MANUAL PELA CENTRAL
# ============================================================

def enviar_manual(cid, texto):
    """Resposta da equipe pela central. Respeita a janela de 24h / 7 dias."""
    c = db.buscar_contato(cid)
    if not c:
        return {'ok': False, 'erro': 'contato nao encontrado'}
    ultima = _dt(c.get('ultima_entrada_em'))
    if not ultima:
        return {'ok': False, 'erro': 'A pessoa ainda nao mandou mensagem no Direct (so comentou). '
                                     'A Meta so libera o Direct depois que ela responder.'}
    idade = datetime.now() - ultima
    tag = None
    if idade > timedelta(days=7):
        return {'ok': False, 'erro': 'Passaram mais de 7 dias desde a ultima mensagem dela: a Meta nao '
                                     'permite responder. Espere ela chamar de novo.'}
    if idade > timedelta(hours=24):
        tag = 'HUMAN_AGENT'
    mid = enviar(c, texto, automacao=None, autor='equipe', tag=tag)
    pausar_robo(cid)
    if mid is None:
        return {'ok': False, 'erro': 'A Meta recusou o envio (veja dados/atendimento.log).'}
    return {'ok': True, 'tag': tag}


def janela(c):
    """Horas restantes da janela de 24h (None = fechada / nunca abriu)."""
    ultima = _dt(c.get('ultima_entrada_em'))
    if not ultima:
        return None
    resto = (ultima + timedelta(hours=24) - datetime.now()).total_seconds() / 3600
    return round(resto, 1) if resto > 0 else 0
