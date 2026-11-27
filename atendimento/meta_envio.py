"""
Envio para a Meta (Instagram Direct, Messenger e respostas em comentario).

Usa o token DA PAGINA (ATEND_PAGE_TOKEN). Pela Plataforma do Messenger, o mesmo endpoint
/me/messages atende Instagram e Messenger: a Meta sabe o canal pelo id de quem recebe.

Com ATEND_SIMULAR=1 nada sai: cada envio so vai para o log e devolve um id falso.
Nenhuma funcao aqui levanta excecao: erro da Graph API vira log + retorno None, para o
webhook nunca cair por causa de uma resposta recusada.
"""
import logging
import uuid

import requests

from ajustes import GRAPH, env, simulando

log = logging.getLogger('atendimento')


def _token():
    return env('ATEND_PAGE_TOKEN') or env('META_PAGE_TOKEN')


def _post(caminho, dados):
    if simulando():
        falso = f'sim_{uuid.uuid4().hex[:12]}'
        log.info(f'[SIMULACAO] POST {caminho} {dados} -> {falso}')
        return {'message_id': falso, 'id': falso}
    tok = _token()
    if not tok:
        log.error('ATEND_PAGE_TOKEN vazio: nada foi enviado')
        return None
    try:
        r = requests.post(f'{GRAPH}/{caminho}', params={'access_token': tok}, json=dados, timeout=30)
        d = r.json() if r.content else {}
    except (requests.RequestException, ValueError) as e:
        log.error(f'falha de rede em {caminho}: {e}')
        return None
    if r.status_code >= 400 or 'error' in d:
        e = d.get('error', {})
        log.error(f"Meta recusou {caminho} ({e.get('code')}/{e.get('error_subcode')}): "
                  f"{e.get('error_user_msg') or e.get('message')}")
        return None
    return d


def _mensagem(texto, opcoes=None, botao=None):
    """Monta o corpo: texto + quick replies, ou texto + botao de link (template)."""
    if botao and botao.get('url'):
        return {'attachment': {'type': 'template', 'payload': {
            'template_type': 'button', 'text': texto[:640],
            'buttons': [{'type': 'web_url', 'url': botao['url'], 'title': (botao.get('titulo') or 'Abrir')[:20]}]}}}
    msg = {'text': texto[:1000]}
    if opcoes:
        msg['quick_replies'] = [{'content_type': 'text', 'title': o['titulo'][:20], 'payload': o['payload'][:1000]}
                                for o in opcoes[:13]]
    return msg


def enviar_dm(destino_id, texto, opcoes=None, botao=None, tag=None):
    """Mensagem no Direct/Messenger. tag='HUMAN_AGENT' so para humano, entre 24h e 7 dias."""
    corpo = {'recipient': {'id': destino_id}, 'message': _mensagem(texto, opcoes, botao)}
    if tag:
        corpo.update({'messaging_type': 'MESSAGE_TAG', 'tag': tag})
    else:
        corpo['messaging_type'] = 'RESPONSE'
    d = _post('me/messages', corpo)
    return (d or {}).get('message_id')


def private_reply(comment_id, texto, opcoes=None, botao=None):
    """Resposta privada a um comentario (1 por comentario, ate 7 dias depois dele)."""
    corpo = {'recipient': {'comment_id': comment_id}, 'message': _mensagem(texto, opcoes, botao)}
    d = _post('me/messages', corpo)
    return (d or {}).get('message_id')


def responder_comentario(comment_id, texto, canal='instagram'):
    """Resposta publica embaixo do comentario."""
    if canal == 'instagram':
        d = _post(f'{comment_id}/replies', {'message': texto})
    else:
        d = _post(f'{comment_id}/comments', {'message': texto})
    return (d or {}).get('id')


def perfil(externo_id, canal='instagram'):
    """Nome, @ e foto de quem mandou mensagem. Falha silenciosa."""
    if simulando() or not _token():
        return {}
    campos = 'name,username,profile_pic' if canal == 'instagram' else 'first_name,last_name,profile_pic'
    try:
        r = requests.get(f'{GRAPH}/{externo_id}', params={'fields': campos, 'access_token': _token()}, timeout=20)
        d = r.json()
    except (requests.RequestException, ValueError):
        return {}
    if 'error' in d:
        return {}
    nome = d.get('name') or ' '.join(x for x in (d.get('first_name'), d.get('last_name')) if x)
    return {'nome': nome or None, 'username': d.get('username'), 'foto': d.get('profile_pic')}
