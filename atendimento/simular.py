"""
Simulador da central: popula contatos de demonstracao e dispara eventos falsos no webhook.

  1. suba a central em modo simulacao (nada sai para a Meta):
       set ATEND_SIMULAR=1 & set ATEND_SENHA=teste & uvicorn app:app --port 8077   (dentro de atendimento/)
  2. python atendimento/simular.py                      popula ~40 contatos + eventos + checagens
     python atendimento/simular.py --so-popular         so os contatos de demonstracao (sem servidor)
     python atendimento/simular.py --so-eventos         so os eventos no webhook
     python atendimento/simular.py --limpar-demo        apaga tudo que o simulador criou

Contatos do simulador tem externo_id comecando com 'demo_' ou 'sim_' e a tag 'demo'.
"""
import argparse
import hashlib
import hmac
import json
import os
import random
import sys
import time
import uuid
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import banco as db  # noqa: E402
import exportar  # noqa: E402
from ajustes import env, funil  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

USUARIOS = ['marina.fitlife', 'ju.santos', 'carol.emagrecendo', 'renata.bsantos', 'paty.oliveira', 'aline.m.costa',
            'bia_vida_leve', 'dani.rocha', 'fer.almeida', 'gabi.souza', 'karla.mendes', 'lu.prates', 'mari.lopes',
            'nanda.ribeiro', 'pri.castro', 'rafa.guaruja', 'sandra.vicente', 'tati.p.grande', 'vivi.martins',
            'cris.nogueira', 'elaine.costa', 'helo.batista', 'ingrid.sv', 'jessica.fit', 'laura.santos',
            'monica.alves', 'natalia.c', 'olivia.reis', 'paula.duarte', 'quezia.lima', 'roberta.fonseca',
            'silvia.n', 'tais.moura', 'ursula.bento', 'vanessa.rp', 'wanda.lima', 'yasmin.f', 'zelia.prado',
            'andrea.cubatao', 'bruna.peruibe', 'camila.saovicente', 'debora.praia']
ANUNCIOS = ['120210000000001', '120210000000002', '120210000000003']
PROCEDIMENTOS = [('Metodo Fenix full face', 4800, 6000), ('Metodo Fenix terco medio', 2800, 3800),
                 ('Bioestimulador de colageno', 1800, 2600), ('Preenchimento de olheiras', 1500, 2200),
                 ('Contorno mandibular', 2400, 3400)]
RESPOSTAS = {'incomodo': ['Flacidez pos emagrecer', 'Bigode chines', 'Olheiras', 'Contorno do rosto'],
             'emagrecimento': ['Ate 10 kg', '10 a 20 kg', 'Mais de 20 kg', 'perdi 18kg em 1 ano com caneta'],
             'ja_fez_harmonizacao': ['Nunca fiz', 'Ja fiz'], 'periodo': ['Manha', 'Tarde', 'Noite', 'Sabado']}


# ============================================================
# POPULAR (direto no banco, com datas espalhadas em 30 dias)
# ============================================================

def _fmt(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def popular(n=40, semente=7):
    db.init()
    rnd = random.Random(semente)
    f = funil()
    origens = [('comentario', 0.40), ('anuncio', 0.30), ('dm', 0.15), ('story', 0.10), ('formulario', 0.05)]
    finais = [(1, 0.12), (2, 0.22), (3, 0.24), (4, 0.14), (5, 0.08), (6, 0.12), (7, 0.08)]  # posicao+1 no funil
    aut_por_origem = {'comentario': ['comentario_fenix', 'comentario_fenix', 'comentario_quero'],
                      'anuncio': ['anuncio_direct'], 'dm': ['dm_palavra', 'boas_vindas'],
                      'story': ['story_resposta'], 'formulario': [None]}
    agora = datetime.now()
    criados = 0
    for i in range(n):
        origem = rnd.choices([o for o, _ in origens], [p for _, p in origens])[0]
        alvo = rnd.choices([x for x, _ in finais], [p for _, p in finais])[0] - 1
        alvo = min(alvo, len(f) - 1)
        inicio = agora - timedelta(days=rnd.uniform(0.2, 29.5))
        aut = rnd.choice(aut_por_origem[origem])
        user = USUARIOS[i % len(USUARIOS)]
        c, novo = db.obter_ou_criar('instagram', f'demo_{i:03d}', origem, quando=_fmt(inicio), username=user,
                                    ad_id=rnd.choice(ANUNCIOS) if origem == 'anuncio' else None,
                                    post_id='reel_demo_fenix' if origem == 'comentario' else None,
                                    automacao_origem=aut)
        if not novo:
            continue
        criados += 1
        cid = c['id']
        t = inicio
        db.registrar_msg(cid, 'entrada', rnd.choice(['Quero o FENIX', 'valor?', 'Oi, vi o anuncio', 'quanto custa?',
                                                    'que resultado lindo']),
                         'comentario' if origem == 'comentario' else 'texto', autor='pessoa', quando=_fmt(t))
        if aut:
            db.registrar_evento(cid, aut, origem, 'demo', quando=_fmt(t))
        t += timedelta(seconds=rnd.randint(3, 20))
        db.registrar_msg(cid, 'saida', 'Oi! Aqui e da equipe da Dra. Aline. Posso te fazer 4 perguntas rapidinhas?',
                         'private_reply' if origem == 'comentario' else 'quick_reply', automacao=aut, autor='robo',
                         quando=_fmt(t))
        campos = {}
        tags = ['demo']
        etapa_final = f[alvo]
        perdido = alvo == len(f) - 1
        ate = rnd.randint(1, 3) if perdido else alvo
        for pos in range(1, ate + 1):
            t += timedelta(hours=rnd.uniform(0.05, 2) if pos <= 2 else rnd.uniform(12, 96))
            if t > agora:
                t = agora - timedelta(minutes=rnd.randint(1, 50))
            if pos == 2:
                for k, ops in RESPOSTAS.items():
                    campos[k] = rnd.choice(ops)
                    db.registrar_msg(cid, 'entrada', campos[k], 'quick_reply', autor='pessoa', quando=_fmt(t))
                tags += ['qualificado', 'incomodo_' + campos['incomodo'].lower().replace(' ', '_')]
            db.mudar_etapa(cid, f[pos], quando=_fmt(t))
        if perdido:
            t += timedelta(days=rnd.uniform(1, 5))
            db.mudar_etapa(cid, f[-1], quando=_fmt(min(t, agora)))
            tags.append('perdido_' + rnd.choice(['preco', 'sumiu', 'distancia']))
        extra = {'tags': tags, 'campos': campos}
        if 'fech' in etapa_final.lower():
            proc, vmin, vmax = rnd.choice(PROCEDIMENTOS)
            extra.update(procedimento=proc, valor_fechado=float(round(rnd.uniform(vmin, vmax) / 50) * 50))
        if rnd.random() < 0.5:
            t2 = min(t + timedelta(minutes=rnd.randint(5, 240)), agora)
            db.registrar_msg(cid, 'saida', 'Oi! Aqui e a Aline, vi suas respostas. Tenho horario quinta a tarde, pode ser?',
                             autor='equipe', quando=_fmt(t2))
        db.atualizar(cid, **extra)
    print(f'popular: {criados} contatos de demonstracao criados')
    return criados


def limpar_demo():
    db.init()
    with db.conectar() as c:
        ids = [r['id'] for r in c.execute("SELECT id FROM contatos WHERE externo_id LIKE 'demo_%' OR externo_id LIKE 'sim_%'")]
        for t in ('mensagens', 'eventos', 'etapas_historico', 'comentarios_respondidos'):
            c.execute(f"DELETE FROM {t} WHERE contato_id IN ({','.join('?' * len(ids))})", ids) if ids else None
        c.execute(f"DELETE FROM contatos WHERE id IN ({','.join('?' * len(ids))})", ids) if ids else None
    print(f'limpar-demo: {len(ids)} contatos apagados')


# ============================================================
# EVENTOS NO WEBHOOK
# ============================================================

def _post(url, payload):
    import requests
    corpo = json.dumps(payload).encode()
    cab = {'Content-Type': 'application/json'}
    seg = env('META_APP_SECRET')
    if seg:
        cab['X-Hub-Signature-256'] = 'sha256=' + hmac.new(seg.encode(), corpo, hashlib.sha256).hexdigest()
    r = requests.post(url + '/webhook', data=corpo, headers=cab, timeout=10)
    time.sleep(0.5)
    return r.status_code


def _msg(sender, texto=None, mid=None, **extra):
    m = {'mid': mid or f'm_{sender}_{uuid.uuid4().hex[:12]}'}
    if texto is not None:
        m['text'] = texto
    m.update(extra)
    return {'object': 'instagram', 'entry': [{'id': 'IGCLINICA', 'time': int(time.time() * 1000), 'messaging': [
        {'sender': {'id': sender}, 'recipient': {'id': 'IGCLINICA'}, 'timestamp': int(time.time() * 1000),
         'message': m}]}]}


def _qr(sender, titulo, payload):
    return _msg(sender, titulo, quick_reply={'payload': payload})


def _comentario(sender, username, texto, cid):
    return {'object': 'instagram', 'entry': [{'id': 'IGCLINICA', 'time': int(time.time()), 'changes': [
        {'field': 'comments', 'value': {'id': cid, 'text': texto, 'from': {'id': sender, 'username': username},
                                        'media': {'id': 'reel_fenix_01', 'media_product_type': 'REELS'}}}]}]}


def eventos(url):
    run = str(int(time.time()))
    u = {k: f'sim_{k}_{run}' for k in ('marina', 'anuncio', 'story', 'resposta', 'dm', 'oi', 'fb')}
    passos = [
        ('comentario FENIX num reels', _comentario(u['marina'], 'marina.sim', 'Quero o FENIX!!', f'c1_{run}')),
        ('mesmo comentario de novo (deve ignorar)', _comentario(u['marina'], 'marina.sim', 'Quero o FENIX!!', f'c1_{run}')),
        ('toca "Pode sim"', _qr(u['marina'], 'Pode sim', 'OPT|Pode sim')),
        ('responde 1/4', _qr(u['marina'], 'Flacidez pos emagrecer', 'FLX|qualificacao|0|0')),
        ('clica botao antigo (ignorar)', _qr(u['marina'], 'Flacidez pos emagrecer', 'FLX|qualificacao|0|0')),
        ('responde 2/4', _qr(u['marina'], 'Mais de 20 kg', 'FLX|qualificacao|1|2')),
        ('responde 3/4', _qr(u['marina'], 'Nunca fiz', 'FLX|qualificacao|2|0')),
        ('responde 4/4', _qr(u['marina'], 'Tarde', 'FLX|qualificacao|3|1')),
        ('entrada por anuncio', _msg(u['anuncio'], 'Oi, vi o anuncio do Metodo Fenix',
                                     referral={'ad_id': '120210000000001', 'ref': 'fenix_reels', 'source': 'ADS',
                                               'type': 'OPEN_THREAD'})),
        ('anuncio: responde "sim" em texto', _msg(u['anuncio'], 'sim')),
        ('anuncio: responde "1" (numero da opcao)', _msg(u['anuncio'], '1')),
        ('anuncio: texto livre no passo 2', _msg(u['anuncio'], 'perdi 15kg em 8 meses')),
        ('anuncio: pergunta no meio (repergunta)', _msg(u['anuncio'], 'doi muito?')),
        ('anuncio: responde 3/4', _msg(u['anuncio'], 'nunca fiz')),
        ('anuncio: responde 4/4', _msg(u['anuncio'], 'noite')),
        ('mencao em story', _msg(u['story'], None, attachments=[{'type': 'story_mention',
                                                                 'payload': {'url': 'https://exemplo/story.jpg'}}])),
        ('resposta a story', _msg(u['resposta'], 'que resultado lindo', reply_to={'story': {'url': 'https://x/s', 'id': 's1'}})),
        ('Direct com palavra-chave', _msg(u['dm'], 'Quanto custa a harmonizacao?')),
        ('primeira mensagem sem palavra', _msg(u['oi'], 'boa tarde')),
        ('clinica responde pelo app (eco)', {'object': 'instagram', 'entry': [{'id': 'IGCLINICA', 'messaging': [
            {'sender': {'id': 'IGCLINICA'}, 'recipient': {'id': u['oi']},
             'message': {'mid': f'eco_{run}', 'text': 'Oi! Aqui e a Aline, como posso te ajudar?', 'is_echo': True}}]}]}),
        ('pessoa responde com humano no controle (robo calado)', _msg(u['oi'], 'quero agendar')),
        ('comentario na pagina do Facebook', {'object': 'page', 'entry': [{'id': 'PAGINA', 'changes': [
            {'field': 'feed', 'value': {'item': 'comment', 'verb': 'add', 'comment_id': f'fb_{run}',
                                        'message': 'quero saber o valor', 'post_id': 'post_1',
                                        'from': {'id': u['fb'], 'name': 'Maria Teste'}}}]}]}),
    ]
    for rot, p in passos:
        st = _post(url, p)
        print(f'  [{st}] {rot}')
    # a central processa em fila: espera o ultimo evento (comentario no Facebook) aparecer
    for _ in range(40):
        with db.conectar() as c:
            if c.execute('SELECT 1 FROM contatos WHERE externo_id=?', (u['fb'],)).fetchone():
                break
        time.sleep(0.5)
    time.sleep(0.5)
    return u


def checar(u):
    ok = True

    def contato(ext):
        with db.conectar() as c:
            r = c.execute('SELECT * FROM contatos WHERE externo_id=?', (ext,)).fetchone()
            if not r:
                return None, []
            ms = c.execute('SELECT * FROM mensagens WHERE contato_id=? ORDER BY id', (r['id'],)).fetchall()
            return db.contato_dict(r), ms

    def teste(nome, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  {'OK   ' if cond else 'FALHA'} {nome}")

    c, ms = contato(u['marina'])
    teste('comentario gerou resposta publica + privada', c and any(m['tipo'] == 'resposta_publica' for m in ms)
          and any(m['tipo'] == 'private_reply' for m in ms))
    teste('comentario duplicado nao respondeu 2x', c and sum(m['tipo'] == 'private_reply' for m in ms) == 1)
    teste('fluxo concluido -> Qualificado com 4 campos', c and c['etapa'] == 'Qualificado'
          and all(k in c['campos'] for k in ('incomodo', 'emagrecimento', 'ja_fez_harmonizacao', 'periodo')))
    teste('final mandou botao do WhatsApp', c and any('[botao:' in (m['texto'] or '') for m in ms))
    c, ms = contato(u['anuncio'])
    teste('anuncio: ad_id gravado e origem anuncio', c and c['ad_id'] == '120210000000001' and c['origem'] == 'anuncio')
    teste('anuncio: texto livre aceito no passo 2', c and c['campos'].get('emagrecimento') == 'perdi 15kg em 8 meses')
    teste('anuncio: reperguntou quando fugiu da opcao', c and any('toca numa das opcoes' in (m['texto'] or '') for m in ms))
    teste('anuncio: qualificado', c and c['etapa'] == 'Qualificado')
    c, ms = contato(u['story'])
    teste('mencao em story -> tag embaixadora', c and 'embaixadora' in c['tags'])
    c, ms = contato(u['resposta'])
    teste('resposta a story -> convite enviado', c and c['origem'] == 'story' and any(m['direcao'] == 'saida' for m in ms))
    c, ms = contato(u['dm'])
    teste('Direct com palavra-chave -> automacao dm_palavra', c and c['automacao_origem'] == 'dm_palavra')
    c, ms = contato(u['oi'])
    teste('boas-vindas na primeira mensagem', c and any(m['automacao'] == 'boas_vindas' for m in ms))
    teste('eco do app registrado e robo pausado', c and any(m['autor'] == 'app_instagram' for m in ms)
          and c['campos'].get('_robo_pausado_ate'))
    teste('robo calado depois do humano', c and ms[-1]['direcao'] == 'entrada')
    with db.conectar() as cn:
        r = cn.execute("SELECT * FROM contatos WHERE canal='messenger' AND externo_id=?", (u['fb'],)).fetchone()
    teste('comentario no Facebook tratado (canal messenger)', r is not None)
    return ok


def checar_api(url):
    import requests
    s = requests.Session()
    senha = env('ATEND_SENHA')
    r = s.post(url + '/api/login', json={'senha': senha}, timeout=10)
    ok = r.status_code == 200
    print(f"  {'OK   ' if ok else 'FALHA'} login na central")
    for rota in ('/api/conversas', '/api/automacoes', '/api/numeros?dias=30', '/'):
        r = s.get(url + rota, timeout=20)
        bom = r.status_code == 200
        ok = ok and bom
        print(f"  {'OK   ' if bom else 'FALHA'} GET {rota} ({r.status_code}, {len(r.content)} bytes)")
    r = requests.get(url + '/api/conversas', timeout=10)
    bom = r.status_code == 401
    print(f"  {'OK   ' if bom else 'FALHA'} sem login a API recusa (401)")
    return ok and bom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:8077')
    ap.add_argument('--so-popular', action='store_true')
    ap.add_argument('--so-eventos', action='store_true')
    ap.add_argument('--limpar-demo', action='store_true')
    ap.add_argument('--n', type=int, default=40)
    a = ap.parse_args()
    if a.limpar_demo:
        limpar_demo()
        return
    if not a.so_eventos:
        popular(a.n)
    if a.so_popular:
        return
    print('eventos no webhook:')
    u = eventos(a.url)
    print('checagens:')
    ok = checar(u)
    print('API da central:')
    ok = checar_api(a.url) and ok
    print('exportar.resumo (30 dias):')
    print(json.dumps(exportar.resumo(date.today() - timedelta(days=29), date.today()), ensure_ascii=False)[:1500])
    print('\nRESULTADO:', 'TUDO OK' if ok else 'HOUVE FALHAS')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
