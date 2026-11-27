"""
Motor da Meta Marketing API (Facebook/Instagram Ads) da Dra. Aline Albuquerque.

Configuracao em config/.env (copiar de config/.env.example):
  META_ACCESS_TOKEN  token PERMANENTE de System User (aceita tambem META_ADS_TOKEN)
  META_AD_ACCOUNT    act_XXXXXXXXXX
  META_PAGE_ID       id da Pagina do Facebook que assina os anuncios
  META_IG_USER_ID    (opcional) id da conta do Instagram ligada
  WHATSAPP_NUMERO    55DDDNUMERO que recebe as conversas
  TETO_DIARIO_REAIS  trava: nenhum conjunto pode passar desse orcamento/dia
  META_API_VERSION   (opcional) padrao v24.0

REGRA DE SEGURANCA: tudo que e CRIADO nasce PAUSADO. Ativar, pausar e mudar
orcamento sao funcoes separadas e o agente so chama depois do OK.
"""
import json
import os
import sys
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent


def _carregar_env():
    envp = RAIZ / 'config' / '.env'
    if not envp.exists():
        return
    for linha in envp.read_text(encoding='utf-8', errors='ignore').splitlines():
        linha = linha.strip()
        if '=' in linha and not linha.startswith('#'):
            k, v = linha.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_carregar_env()

VERSAO = os.getenv('META_API_VERSION', 'v24.0')
BASE = f'https://graph.facebook.com/{VERSAO}'

# acoes que contam como "lead"
CONV_WHATS = 'onsite_conversion.messaging_conversation_started_7d'
LEAD_FORM = 'lead'              # formulario instantaneo (ou 'onsite_conversion.lead_grouped')
LEAD_TIPOS = (CONV_WHATS, 'lead', 'onsite_conversion.lead_grouped',
              'offsite_conversion.fb_pixel_lead')


class ErroMeta(Exception):
    pass


def conta():
    c = os.getenv('META_AD_ACCOUNT', '').strip()
    if c and not c.startswith('act_'):
        c = 'act_' + c
    return c


def pagina():
    return os.getenv('META_PAGE_ID', '').strip()


def teto_diario():
    try:
        return float(os.getenv('TETO_DIARIO_REAIS', '50'))
    except ValueError:
        return 50.0


def _token():
    tok = (os.getenv('META_ACCESS_TOKEN') or os.getenv('META_ADS_TOKEN') or '').strip()
    if not tok:
        raise ErroMeta('META_ACCESS_TOKEN vazio em config/.env (veja docs/COMO_LIBERAR_ACESSO_META.md).')
    return tok


def _checar(r):
    try:
        d = r.json()
    except ValueError:
        raise ErroMeta(f'HTTP {r.status_code}: {r.text[:300]}')
    if r.status_code >= 400 or 'error' in d:
        e = d.get('error', {})
        msg = e.get('error_user_msg') or e.get('message') or r.text[:300]
        raise ErroMeta(f"Meta recusou ({e.get('code')}/{e.get('error_subcode')}): {msg}")
    return d


def get(caminho, params=None, todas_paginas=False):
    params = dict(params or {})
    params['access_token'] = _token()
    d = _checar(requests.get(f'{BASE}/{caminho}', params=params, timeout=60))
    if not todas_paginas:
        return d
    dados = list(d.get('data', []))
    prox = d.get('paging', {}).get('next')
    while prox:
        d = _checar(requests.get(prox, timeout=60))
        dados += d.get('data', [])
        prox = d.get('paging', {}).get('next')
    return {'data': dados}


def post(caminho, dados=None, arquivos=None):
    dados = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
             for k, v in (dados or {}).items()}
    dados['access_token'] = _token()
    return _checar(requests.post(f'{BASE}/{caminho}', data=dados, files=arquivos, timeout=300))


# ============================================================
# LEITURA
# ============================================================

def listar_contas():
    return get('me/adaccounts', {'fields': 'name,account_id,currency,account_status,amount_spent',
                                 'limit': 100}).get('data', [])


def listar_campanhas(ativas=False):
    camps = get(f'{conta()}/campaigns', {
        'fields': 'id,name,status,effective_status,objective,daily_budget,created_time',
        'limit': 200}, todas_paginas=True)['data']
    if ativas:
        camps = [c for c in camps if c.get('effective_status') == 'ACTIVE']
    return camps


def listar_conjuntos(campanha_id):
    return get(f'{campanha_id}/adsets', {
        'fields': 'id,name,status,effective_status,daily_budget,optimization_goal,destination_type,targeting',
        'limit': 200}, todas_paginas=True)['data']


def listar_anuncios(pai_id):
    return get(f'{pai_id}/ads', {
        'fields': 'id,name,status,effective_status,adset_id,creative{id,title,body}',
        'limit': 200}, todas_paginas=True)['data']


def insights(obj_id=None, nivel='campaign', periodo='last_7d', diario=False,
             desde=None, ate=None):
    """periodo: today, yesterday, last_7d, last_14d, last_30d, this_month, last_month, maximum
    ou desde/ate no formato AAAA-MM-DD."""
    params = {'level': nivel, 'limit': 500,
              'fields': ('campaign_id,campaign_name,adset_id,adset_name,ad_id,ad_name,'
                         'spend,impressions,reach,frequency,clicks,ctr,cpc,cpm,'
                         'actions,cost_per_action_type')}
    if desde and ate:
        params['time_range'] = json.dumps({'since': desde, 'until': ate})
    else:
        params['date_preset'] = periodo
    if diario:
        params['time_increment'] = 1
    return get(f'{obj_id or conta()}/insights', params, todas_paginas=True)['data']


def leads_da_linha(linha):
    """Total de leads (conversa WhatsApp + formulario) numa linha de insights."""
    total, vistos = 0, set()
    for a in linha.get('actions') or []:
        t = a.get('action_type')
        if t in LEAD_TIPOS and t not in vistos:
            # 'lead' e 'onsite_conversion.lead_grouped' sao o mesmo lead contado 2x
            if t == 'onsite_conversion.lead_grouped' and 'lead' in vistos:
                continue
            if t == 'lead' and 'onsite_conversion.lead_grouped' in vistos:
                continue
            vistos.add(t)
            total += int(float(a.get('value', 0)))
    return total


def resumo(linha):
    gasto = float(linha.get('spend', 0) or 0)
    leads = leads_da_linha(linha)
    return {
        'campanha': linha.get('campaign_name'), 'conjunto': linha.get('adset_name'),
        'anuncio': linha.get('ad_name'),
        'id': linha.get('ad_id') or linha.get('adset_id') or linha.get('campaign_id'),
        'dia': linha.get('date_start') if linha.get('date_start') == linha.get('date_stop') else None,
        'gasto': round(gasto, 2), 'leads': leads,
        'cpl': round(gasto / leads, 2) if leads else None,
        'impressoes': int(linha.get('impressions', 0) or 0),
        'alcance': int(linha.get('reach', 0) or 0),
        'frequencia': round(float(linha.get('frequency', 0) or 0), 2),
        'cliques': int(linha.get('clicks', 0) or 0),
        'ctr': round(float(linha.get('ctr', 0) or 0), 2),
        'cpm': round(float(linha.get('cpm', 0) or 0), 2),
    }


def buscar_local(nome, tipo='city'):
    """tipo: city | region (estado) | zip. Retorna [{key, name, region, type}]."""
    d = get('search', {'type': 'adgeolocation', 'q': nome,
                       'location_types': json.dumps([tipo]), 'country_code': 'BR', 'limit': 10})
    return [{'key': x.get('key'), 'nome': x.get('name'), 'estado': x.get('region'),
             'tipo': x.get('type')} for x in d.get('data', [])]


def buscar_interesse(termo):
    d = get('search', {'type': 'adinterest', 'q': termo, 'limit': 15})
    return [{'id': x['id'], 'nome': x['name'], 'publico': x.get('audience_size_upper_bound')}
            for x in d.get('data', [])]


def _token_pagina():
    d = get(pagina(), {'fields': 'access_token'})
    return d.get('access_token') or _token()


def listar_formularios():
    tok = _token_pagina()
    r = requests.get(f'{BASE}/{pagina()}/leadgen_forms',
                     params={'access_token': tok, 'fields': 'id,name,status,leads_count,created_time',
                             'limit': 100}, timeout=60)
    return _checar(r).get('data', [])


def baixar_leads(form_id, desde_ts=None):
    """Leads de um formulario instantaneo. desde_ts = unix timestamp (opcional)."""
    tok = _token_pagina()
    params = {'access_token': tok, 'limit': 500,
              'fields': 'id,created_time,field_data,ad_name,campaign_name'}
    if desde_ts:
        params['filtering'] = json.dumps([{'field': 'time_created', 'operator': 'GREATER_THAN',
                                           'value': int(desde_ts)}])
    d = _checar(requests.get(f'{BASE}/{form_id}/leads', params=params, timeout=60))
    saida = []
    for ld in d.get('data', []):
        campos = {f['name']: ', '.join(f.get('values', [])) for f in ld.get('field_data', [])}
        saida.append({'id': ld['id'], 'quando': ld['created_time'], 'anuncio': ld.get('ad_name'),
                      'campanha': ld.get('campaign_name'), **campos})
    return saida


# ============================================================
# CRIACAO (tudo nasce PAUSADO)
# ============================================================

def subir_imagem(caminho_arquivo):
    p = Path(caminho_arquivo)
    with p.open('rb') as f:
        d = post(f'{conta()}/adimages', arquivos={'filename': (p.name, f)})
    img = list(d.get('images', {}).values())[0]
    return img['hash']


def subir_video(caminho_arquivo, titulo=None):
    p = Path(caminho_arquivo)
    with p.open('rb') as f:
        d = post(f'{conta()}/advideos', {'name': titulo or p.stem}, arquivos={'source': (p.name, f)})
    return d['id']


def criar_campanha(nome, objetivo='OUTCOME_LEADS', categorias_especiais=None):
    d = post(f'{conta()}/campaigns', {
        'name': nome, 'objective': objetivo, 'status': 'PAUSED',
        'special_ad_categories': categorias_especiais or [],
        'is_adset_budget_sharing_enabled': False,
    })
    return d['id']


def _alvo(cidades=None, estados=None, raio_km=None, idade_min=25, idade_max=65,
          interesses=None, publico_advantage=True, generos=None, local_raio=None):
    geo = {}
    if cidades:
        geo['cities'] = [{'key': str(k), **({'radius': raio_km, 'distance_unit': 'kilometer'}
                                            if raio_km else {})} for k in cidades]
    if estados:
        geo['regions'] = [{'key': str(k)} for k in estados]
    if local_raio:
        # ponto do consultorio: {"lat": -23.96, "lng": -46.33, "raio_km": 12}
        geo['custom_locations'] = [{'latitude': local_raio['lat'], 'longitude': local_raio['lng'],
                                    'radius': local_raio.get('raio_km', 12), 'distance_unit': 'kilometer'}]
    if not geo:
        geo = {'countries': ['BR']}
    idade_min = max(18, idade_min)  # Meta exige 18+ em procedimento estetico
    alvo = {'geo_locations': geo, 'age_min': idade_min, 'age_max': idade_max,
            'targeting_automation': {'advantage_audience': 1 if publico_advantage else 0}}
    if generos:
        alvo['genders'] = generos  # 1 = homens, 2 = mulheres
    if interesses:
        alvo['flexible_spec'] = [{'interests': [{'id': str(i)} for i in interesses]}]
    return alvo


def criar_conjunto(campanha_id, nome, orcamento_diario, destino='WHATSAPP', **alvo_kw):
    """destino: WHATSAPP (conversa no zap) | DIRECT (Instagram Direct) | FORMULARIO (cadastro instantaneo)."""
    if orcamento_diario > teto_diario():
        raise ErroMeta(f'Orcamento R$ {orcamento_diario:.2f}/dia passa do teto de R$ {teto_diario():.2f} '
                       '(TETO_DIARIO_REAIS no config/.env). Peca o OK para subir o teto.')
    base = {
        'name': nome, 'campaign_id': campanha_id, 'status': 'PAUSED',
        'daily_budget': int(round(orcamento_diario * 100)),
        'billing_event': 'IMPRESSIONS', 'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
        'promoted_object': {'page_id': pagina()},
        'targeting': _alvo(**alvo_kw),
    }
    if destino == 'WHATSAPP':
        base.update({'optimization_goal': 'CONVERSATIONS', 'destination_type': 'WHATSAPP'})
    elif destino == 'DIRECT':
        base.update({'optimization_goal': 'CONVERSATIONS', 'destination_type': 'INSTAGRAM_DIRECT'})
    elif destino == 'FORMULARIO':
        base.update({'optimization_goal': 'LEAD_GENERATION', 'destination_type': 'ON_AD'})
    else:
        raise ErroMeta('destino deve ser WHATSAPP, DIRECT ou FORMULARIO')
    return post(f'{conta()}/adsets', base)['id']


def criar_anuncio(conjunto_id, nome, texto, titulo, imagem_hash=None, video_id=None,
                  destino='WHATSAPP', formulario_id=None, descricao=None):
    """Cria criativo + anuncio (PAUSADO). Precisa imagem_hash OU video_id."""
    page = pagina()
    if destino == 'WHATSAPP':
        cta = {'type': 'WHATSAPP_MESSAGE', 'value': {'app_destination': 'WHATSAPP'}}
        link = 'https://api.whatsapp.com/send'
    elif destino == 'DIRECT':
        cta = {'type': 'INSTAGRAM_MESSAGE', 'value': {'app_destination': 'INSTAGRAM_DIRECT'}}
        link = 'https://www.instagram.com/'
    else:
        if not formulario_id:
            raise ErroMeta('Anuncio de FORMULARIO precisa do formulario_id (listar_formularios).')
        cta = {'type': 'SIGN_UP', 'value': {'lead_gen_form_id': formulario_id}}
        link = 'https://fb.me/'

    if video_id:
        thumb = get(video_id, {'fields': 'picture'}).get('picture')
        spec_conteudo = {'video_data': {'video_id': video_id, 'message': texto, 'title': titulo,
                                        'call_to_action': {**cta, 'value': {**cta['value'], 'link': link}},
                                        'image_url': thumb}}
        if descricao:
            spec_conteudo['video_data']['link_description'] = descricao
    elif imagem_hash:
        spec_conteudo = {'link_data': {'image_hash': imagem_hash, 'message': texto, 'name': titulo,
                                       'link': link, 'call_to_action': cta}}
        if descricao:
            spec_conteudo['link_data']['description'] = descricao
    else:
        raise ErroMeta('Informe imagem_hash (subir_imagem) ou video_id (subir_video).')

    spec = {'page_id': page, **spec_conteudo}
    ig = (os.getenv('META_IG_USER_ID') or os.getenv('META_IG_ID') or '').strip()
    if ig:
        spec['instagram_user_id'] = ig
    criativo = {'name': f'{nome} - criativo', 'object_story_spec': spec}
    # mensagem de boas-vindas do WhatsApp: configurar no Gerenciador (formato da API muda muito)
    cid = post(f'{conta()}/adcreatives', criativo)['id']
    return post(f'{conta()}/ads', {'name': nome, 'adset_id': conjunto_id,
                                   'creative': {'creative_id': cid}, 'status': 'PAUSED'})['id']


# ============================================================
# ALTERACAO NA CONTA (so com OK explicito)
# ============================================================

def ativar(obj_id):
    return post(obj_id, {'status': 'ACTIVE'}).get('success', False)


def pausar(obj_id):
    return post(obj_id, {'status': 'PAUSED'}).get('success', False)


def mudar_orcamento(conjunto_id, reais_por_dia):
    if reais_por_dia > teto_diario():
        raise ErroMeta(f'R$ {reais_por_dia:.2f}/dia passa do teto de R$ {teto_diario():.2f}.')
    return post(conjunto_id, {'daily_budget': int(round(reais_por_dia * 100))}).get('success', False)


if __name__ == '__main__':
    # teste rapido: python trafego/meta.py
    try:
        print('API', VERSAO, '| conta', conta() or '(vazia)', '| pagina', pagina() or '(vazia)')
        for c in listar_contas():
            print(' -', c.get('name'), c.get('id'), c.get('currency'))
    except ErroMeta as e:
        print('ERRO:', e)
        sys.exit(1)
