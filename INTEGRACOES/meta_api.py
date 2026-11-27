"""
Leitura da Meta (Facebook + Instagram) para o painel da Dra. Aline Albuquerque.

SOMENTE LEITURA. Quem cria, pausa e mexe em orcamento e o trafego/painel.py,
sempre com confirmacao.

Le do config/.env:
  META_ACCESS_TOKEN   token de System User (permanente). Aceita tambem META_ADS_TOKEN.
  META_AD_ACCOUNT     conta de anuncio, ex: act_1234567890
  META_PAGE_ID        id da pagina do Facebook
  META_IG_USER_ID     id da conta profissional do Instagram (opcional: descoberto pela pagina)

Blocos que o painel usa (cada um devolve {'ok': False, 'erro': ...} quando a Meta recusa):
  anuncios(periodo)   totais, serie diaria, campanhas, conjuntos, anuncios com metricas de
                      video (gancho, retencao, tempo medio), ranking de qualidade, fadiga,
                      horario, dia da semana, aparelho, idade/genero, estado, posicionamento
  instagram(periodo)  perfil, metricas, seguidores/dia, posts e reels com tempo assistido
  publico_instagram() cidades, idade e genero dos seguidores, horario em que estao online
  pagina()            seguidores da pagina
  leads_formulario()  formularios instantaneos e os leads
"""
import json
import logging
import os
from datetime import date, datetime, timedelta

import requests

log = logging.getLogger('meta_api')

VERSAO = os.getenv('META_API_VERSION', 'v21.0')
BASE = f'https://graph.facebook.com/{VERSAO}'

# --- o que conta como lead numa clinica -------------------------------------
ACAO_CONVERSA = 'onsite_conversion.messaging_conversation_started_7d'
# conversa em que a pessoa mandou 2+ mensagens: separa curioso de interessado
ACAO_CONVERSA_PROFUNDA = 'onsite_conversion.messaging_user_depth_2_message_send'
ACAO_BLOQUEIO = 'onsite_conversion.messaging_block'
ACOES_FORMULARIO = ('onsite_conversion.lead_grouped', 'leadgen_grouped', 'lead')
ACAO_LEAD_SITE = 'offsite_conversion.fb_pixel_lead'
ACAO_VIDEO_3S = 'video_view'

CAMPOS_BASE = ('spend,impressions,reach,clicks,inline_link_clicks,ctr,cpc,cpm,'
               'frequency,actions')
CAMPOS_VIDEO = ('video_play_actions,video_thruplay_watched_actions,video_p25_watched_actions,'
                'video_p50_watched_actions,video_p75_watched_actions,video_p95_watched_actions,'
                'video_p100_watched_actions,video_avg_time_watched_actions')
CAMPOS_RANKING = 'quality_ranking,engagement_rate_ranking,conversion_rate_ranking'

DIAS_SEMANA = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']


class ErroMeta(Exception):
    pass


# ============================================================
# BASICO
# ============================================================

def carregar_env(caminho=None):
    caminho = caminho or os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
    if not os.path.exists(caminho):
        return False
    for linha in open(caminho, encoding='utf-8', errors='ignore'):
        linha = linha.strip()
        if '=' in linha and not linha.startswith('#'):
            k, v = linha.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return True


def cfg(nome, padrao=''):
    return (os.getenv(nome) or padrao).strip()


def _token():
    return cfg('META_ACCESS_TOKEN') or cfg('META_ADS_TOKEN')


def _get(caminho, params=None, token=None):
    token = token or _token()
    if not token:
        raise ErroMeta('META_ACCESS_TOKEN vazio no config/.env')
    params = dict(params or {})
    params['access_token'] = token
    try:
        r = requests.get(f'{BASE}/{caminho}', params=params, timeout=90)
    except requests.RequestException as e:
        raise ErroMeta(f'sem conexao com a Meta: {e}')
    try:
        dados = r.json() if r.content else {}
    except ValueError:
        raise ErroMeta(f'{caminho}: resposta invalida (HTTP {r.status_code})')
    if r.status_code != 200 or 'error' in dados:
        msg = (dados.get('error') or {}).get('message') or r.text[:200]
        raise ErroMeta(f'{caminho}: {msg}')
    return dados


def _get_paginado(caminho, params=None, token=None, limite_itens=1000):
    itens = []
    d = _get(caminho, params, token)
    while True:
        itens.extend(d.get('data', []))
        prox = (d.get('paging') or {}).get('next')
        if not prox or len(itens) >= limite_itens:
            break
        try:
            d = requests.get(prox, timeout=90).json()
        except (requests.RequestException, ValueError):
            break
        if 'error' in d:
            break
    return itens[:limite_itens]


def _bloco(func):
    def envolto(*a, **kw):
        try:
            res = func(*a, **kw)
            res['ok'] = True
            return res
        except ErroMeta as e:
            log.warning(f'{func.__name__}: {e}')
            return {'ok': False, 'erro': str(e)}
    envolto.__name__ = func.__name__
    return envolto


def _conta():
    conta = cfg('META_AD_ACCOUNT')
    if not conta:
        raise ErroMeta('META_AD_ACCOUNT vazio no config/.env')
    return conta if conta.startswith('act_') else 'act_' + conta


# ============================================================
# PERIODOS
# ============================================================

PERIODOS = {
    '7d': 'Ultimos 7 dias',
    '14d': 'Ultimos 14 dias',
    '30d': 'Ultimos 30 dias',
    'mes': 'Mes atual',
    'mes_passado': 'Mes passado',
    '90d': 'Ultimos 90 dias',
}


def intervalo(periodo, hoje=None):
    """(inicio, fim, inicio_anterior, fim_anterior) do periodo."""
    hoje = hoje or date.today()
    ontem = hoje - timedelta(days=1)
    if periodo in ('7d', '14d', '30d', '90d'):
        n = int(periodo[:-1])
        ini, fim = ontem - timedelta(days=n - 1), ontem
    elif periodo == 'mes':
        ini, fim = hoje.replace(day=1), hoje
    elif periodo == 'mes_passado':
        fim = hoje.replace(day=1) - timedelta(days=1)
        ini = fim.replace(day=1)
    else:
        raise ValueError(f'periodo desconhecido: {periodo}')
    dias = (fim - ini).days + 1
    fim_ant = ini - timedelta(days=1)
    ini_ant = fim_ant - timedelta(days=dias - 1)
    return ini, fim, ini_ant, fim_ant


def _time_range(ini, fim):
    return json.dumps({'since': ini.isoformat(), 'until': fim.isoformat()})


# ============================================================
# LEITURA DAS ACOES
# ============================================================

def _acao(lista, tipo=None):
    """Valor de uma acao. Sem tipo, soma a lista (campos de video vem como lista de 1)."""
    tot = 0.0
    for a in lista or []:
        if tipo is None or a.get('action_type') == tipo:
            try:
                tot += float(a.get('value', 0))
            except (TypeError, ValueError):
                pass
            if tipo is not None:
                break
    return tot


def leads_da_linha(linha):
    acts = linha.get('actions')
    form = 0
    for t in ACOES_FORMULARIO:
        form = int(_acao(acts, t))
        if form:
            break
    conv = int(_acao(acts, ACAO_CONVERSA))
    site = int(_acao(acts, ACAO_LEAD_SITE))
    return {'conversas': conv, 'formularios': form, 'site': site,
            'total': conv + form + site,
            'conversas_profundas': int(_acao(acts, ACAO_CONVERSA_PROFUNDA)),
            'bloqueios': int(_acao(acts, ACAO_BLOQUEIO))}


def _video(linha):
    """Metricas de video de uma linha. None quando nao e video."""
    imp = float(linha.get('impressions', 0) or 0)
    v3 = _acao(linha.get('actions'), ACAO_VIDEO_3S)
    plays = _acao(linha.get('video_play_actions'))
    thru = _acao(linha.get('video_thruplay_watched_actions'))
    if not (v3 or plays or thru):
        return None
    p = {k: _acao(linha.get(f'video_{k}_watched_actions')) for k in ('p25', 'p50', 'p75', 'p95', 'p100')}
    base = plays or v3 or 1
    gasto = float(linha.get('spend', 0) or 0)
    return {
        'plays': int(plays), 'views_3s': int(v3), 'thruplays': int(thru),
        'gancho': round(v3 / imp * 100, 1) if imp else None,          # hook rate
        'retencao': round(thru / v3 * 100, 1) if v3 else None,          # hold rate
        'tempo_medio': round(_acao(linha.get('video_avg_time_watched_actions')), 1),
        'curva': {k: round(v / base * 100, 1) for k, v in p.items()},  # % de quem deu play
        'custo_thruplay': round(gasto / thru, 2) if thru else None,
    }


def _resumir(linha):
    gasto = float(linha.get('spend', 0) or 0)
    leads = leads_da_linha(linha)
    acts = linha.get('actions')
    cliques = int(linha.get('inline_link_clicks', 0) or linha.get('clicks', 0) or 0)
    imp = int(linha.get('impressions', 0) or 0)
    out = {
        'gasto': round(gasto, 2),
        'impressoes': imp,
        'alcance': int(linha.get('reach', 0) or 0),
        'cliques': cliques,
        'ctr': round(float(linha.get('ctr', 0) or 0), 2),
        'ctr_link': round(cliques / imp * 100, 2) if imp else 0,
        'cpc': round(gasto / cliques, 2) if cliques else 0,
        'cpm': round(float(linha.get('cpm', 0) or 0), 2),
        'frequencia': round(float(linha.get('frequency', 0) or 0), 2),
        'leads': leads,
        'cpl': round(gasto / leads['total'], 2) if leads['total'] else None,
        'custo_conversa_profunda': (round(gasto / leads['conversas_profundas'], 2)
                                    if leads['conversas_profundas'] else None),
        'engajamento': {
            'reacoes': int(_acao(acts, 'post_reaction')),
            'comentarios': int(_acao(acts, 'comment')),
            'compartilhamentos': int(_acao(acts, 'post')),
            'salvos': int(_acao(acts, 'onsite_conversion.post_save')),
            'visitas_perfil': int(_acao(acts, 'ig_profile_visit') or 0),
        },
    }
    v = _video(linha)
    if v:
        out['video'] = v
    for r in ('quality_ranking', 'engagement_rate_ranking', 'conversion_rate_ranking'):
        if linha.get(r):
            out.setdefault('ranking', {})[r.split('_')[0]] = linha[r]
    return out


def _insights(conta, ini, fim, **extra):
    params = {'fields': CAMPOS_BASE, 'time_range': _time_range(ini, fim), 'limit': 500}
    params.update(extra)
    return _get_paginado(f'{conta}/insights', params)


def _quebra(conta, ini, fim, breakdowns, fields='spend,impressions,reach,clicks,inline_link_clicks,actions'):
    try:
        return _insights(conta, ini, fim, breakdowns=breakdowns, fields=fields)
    except ErroMeta as e:
        log.info(f'quebra {breakdowns}: {e}')
        return []


def _linha_quebra(l):
    gasto = round(float(l.get('spend', 0) or 0), 2)
    leads = leads_da_linha(l)['total']
    imp = int(l.get('impressions', 0) or 0)
    cli = int(l.get('inline_link_clicks', 0) or 0)
    return {'gasto': gasto, 'impressoes': imp, 'alcance': int(l.get('reach', 0) or 0),
            'cliques': cli, 'ctr_link': round(cli / imp * 100, 2) if imp else 0,
            'leads': leads, 'cpl': round(gasto / leads, 2) if leads else None}


# ============================================================
# ANUNCIOS
# ============================================================

def _detalhes_anuncios(conta):
    """Miniatura, texto, video e link de previa de cada anuncio."""
    out = {}
    try:
        lista = _get_paginado(f'{conta}/ads', {
            'fields': ('name,effective_status,created_time,preview_shareable_link,adset_id,'
                       'creative{thumbnail_url,image_url,video_id,body,title,object_type,'
                       'instagram_permalink_url,effective_object_story_id}'),
            'limit': 200}, limite_itens=600)
    except ErroMeta:
        return out
    for a in lista:
        cr = a.get('creative') or {}
        out[a['id']] = {
            'status': a.get('effective_status', '-'),
            'criado': (a.get('created_time') or '')[:10],
            'miniatura': cr.get('thumbnail_url') or cr.get('image_url') or '',
            'video_id': cr.get('video_id'),
            'texto': (cr.get('body') or '')[:600],
            'titulo': cr.get('title') or '',
            'tipo': 'Video' if cr.get('video_id') else ('Imagem' if cr.get('image_url') else
                                                        (cr.get('object_type') or '-').title()),
            'link_instagram': cr.get('instagram_permalink_url') or '',
            'previa': a.get('preview_shareable_link') or '',
        }
    return out


def _detalhes_video(video_id):
    try:
        v = _get(video_id, {'fields': 'picture,source,length,permalink_url'})
    except ErroMeta:
        return {}
    perm = v.get('permalink_url') or ''
    if perm and perm.startswith('/'):
        perm = 'https://www.facebook.com' + perm
    return {'capa': v.get('picture') or '', 'arquivo': v.get('source') or '',
            'duracao': round(float(v.get('length') or 0), 1), 'link_video': perm}


@_bloco
def anuncios(periodo):
    conta = _conta()
    ini, fim, ini_a, fim_a = intervalo(periodo)

    total = _insights(conta, ini, fim, fields=CAMPOS_BASE + ',' + CAMPOS_VIDEO)
    anterior = _insights(conta, ini_a, fim_a, fields=CAMPOS_BASE + ',' + CAMPOS_VIDEO)
    diario = _insights(conta, ini, fim, time_increment=1)

    # ---- campanhas
    linhas_camp = _insights(conta, ini, fim, level='campaign',
                            fields=CAMPOS_BASE + ',campaign_id,campaign_name')
    info_camp = {c['id']: c for c in _get_paginado(f'{conta}/campaigns', {
        'fields': 'name,effective_status,objective,daily_budget,lifetime_budget,created_time', 'limit': 200})}
    campanhas = []
    for l in linhas_camp:
        c = info_camp.get(l.get('campaign_id'), {})
        orc = c.get('daily_budget')
        campanhas.append({'id': l.get('campaign_id'), 'nome': l.get('campaign_name'),
                          'status': c.get('effective_status', '-'), 'objetivo': c.get('objective', '-'),
                          'orcamento_diario': round(int(orc) / 100, 2) if orc else None,
                          **_resumir(l)})
    vistas = {c['id'] for c in campanhas}
    for cid, c in info_camp.items():
        if cid not in vistas and c.get('effective_status') == 'ACTIVE':
            campanhas.append({'id': cid, 'nome': c.get('name'), 'status': 'ACTIVE',
                              'objetivo': c.get('objective', '-'), 'orcamento_diario': None,
                              **_resumir({})})
    campanhas.sort(key=lambda x: -x['gasto'])

    # ---- conjuntos (publico + fase de aprendizado)
    linhas_cj = _insights(conta, ini, fim, level='adset',
                          fields=CAMPOS_BASE + ',adset_id,adset_name,campaign_name')
    info_cj = {}
    try:
        for cj in _get_paginado(f'{conta}/adsets', {
                'fields': 'name,effective_status,daily_budget,optimization_goal,destination_type,'
                          'targeting,learning_stage_info', 'limit': 200}):
            info_cj[cj['id']] = cj
    except ErroMeta:
        pass
    conjuntos = []
    for l in linhas_cj:
        cj = info_cj.get(l.get('adset_id'), {})
        alvo = cj.get('targeting') or {}
        geo = alvo.get('geo_locations') or {}
        cidades = ', '.join(f"{c.get('name')} +{c.get('radius', '')}km" if c.get('radius') else c.get('name', '')
                            for c in geo.get('cities', []))
        locais = ', '.join(f"raio {c.get('radius')}km" for c in geo.get('custom_locations', []))
        aprend = (cj.get('learning_stage_info') or {}).get('status')
        orc = cj.get('daily_budget')
        conjuntos.append({
            'id': l.get('adset_id'), 'nome': l.get('adset_name'), 'campanha': l.get('campaign_name'),
            'status': cj.get('effective_status', '-'),
            'orcamento_diario': round(int(orc) / 100, 2) if orc else None,
            'otimizacao': cj.get('optimization_goal', '-'), 'destino': cj.get('destination_type', '-'),
            'publico': {'idade': f"{alvo.get('age_min', '?')}-{alvo.get('age_max', '?')}",
                        'genero': {1: 'Homens', 2: 'Mulheres'}.get((alvo.get('genders') or [0])[0], 'Todos'),
                        'local': cidades or locais or ', '.join(geo.get('countries', [])) or '-'},
            'aprendizado': {'SUCCESS': 'Concluido', 'LEARNING': 'Aprendendo',
                            'FAIL': 'Aprendizado limitado'}.get(aprend, aprend or '-'),
            **_resumir(l)})
    conjuntos.sort(key=lambda x: -x['gasto'])

    # ---- anuncios: metricas + video + ranking
    linhas_ad = _insights(conta, ini, fim, level='ad',
                          fields=CAMPOS_BASE + ',' + CAMPOS_VIDEO + ',' + CAMPOS_RANKING +
                          ',ad_id,ad_name,adset_name,campaign_name')
    det = _detalhes_anuncios(conta)
    ads = []
    for l in linhas_ad:
        d = det.get(l.get('ad_id'), {})
        ads.append({'id': l.get('ad_id'), 'nome': l.get('ad_name'), 'campanha': l.get('campaign_name'),
                    'conjunto': l.get('adset_name'), 'status': d.get('status', '-'),
                    'miniatura': d.get('miniatura', ''), 'tipo': d.get('tipo', '-'),
                    'texto': d.get('texto', ''), 'titulo': d.get('titulo', ''),
                    'criado': d.get('criado', ''), 'previa': d.get('previa', ''),
                    'link_instagram': d.get('link_instagram', ''), 'video_id': d.get('video_id'),
                    **_resumir(l)})
    ads.sort(key=lambda x: (x['cpl'] is None, x['cpl'] or 0, -x['gasto']))

    # videos: capa grande e arquivo dos que mais gastaram
    videos = sorted([a for a in ads if a.get('video')], key=lambda a: -a['gasto'])[:12]
    for a in videos:
        if a.get('video_id'):
            a.update(_detalhes_video(a['video_id']))

    # ---- fadiga: serie diaria dos 6 anuncios que mais gastaram
    fadiga = []
    top = [a['id'] for a in sorted(ads, key=lambda a: -a['gasto'])[:6]]
    if top:
        try:
            linhas = _insights(conta, ini, fim, level='ad', time_increment=1,
                               fields='ad_id,ad_name,spend,impressions,frequency,ctr,inline_link_clicks,actions',
                               filtering=json.dumps([{'field': 'ad.id', 'operator': 'IN', 'value': top}]))
            por = {}
            for l in linhas:
                r = _resumir(l)
                por.setdefault(l['ad_id'], {'id': l['ad_id'], 'nome': l.get('ad_name'), 'dias': []})['dias'].append(
                    {'data': l.get('date_start'), 'gasto': r['gasto'], 'frequencia': r['frequencia'],
                     'ctr_link': r['ctr_link'], 'cpl': r['cpl'], 'leads': r['leads']['total']})
            fadiga = list(por.values())
        except ErroMeta:
            pass

    # ---- quebras de publico
    idade_genero = [{'idade': l.get('age'), 'genero': l.get('gender'), **_linha_quebra(l)}
                    for l in _quebra(conta, ini, fim, 'age,gender')]
    regioes = sorted([{'regiao': l.get('region'), **_linha_quebra(l)}
                      for l in _quebra(conta, ini, fim, 'region')], key=lambda x: -x['gasto'])[:15]
    posicionamentos = sorted([{'plataforma': l.get('publisher_platform'), 'posicao': l.get('platform_position'),
                               **_linha_quebra(l)}
                              for l in _quebra(conta, ini, fim, 'publisher_platform,platform_position')],
                             key=lambda x: -x['gasto'])
    aparelhos = sorted([{'aparelho': l.get('impression_device'), **_linha_quebra(l)}
                        for l in _quebra(conta, ini, fim, 'impression_device')], key=lambda x: -x['gasto'])
    horas = []
    for l in _quebra(conta, ini, fim, 'hourly_stats_aggregated_by_advertiser_time_zone',
                     fields='spend,impressions,inline_link_clicks,actions'):
        faixa = l.get('hourly_stats_aggregated_by_advertiser_time_zone', '00')
        horas.append({'hora': int(faixa[:2]), **_linha_quebra(l)})
    horas.sort(key=lambda x: x['hora'])

    semana = {k: {'dia': k, 'gasto': 0.0, 'leads': 0} for k in DIAS_SEMANA}
    for l in diario:
        try:
            dsem = DIAS_SEMANA[datetime.strptime(l['date_start'], '%Y-%m-%d').weekday()]
        except (KeyError, ValueError):
            continue
        r = _resumir(l)
        semana[dsem]['gasto'] += r['gasto']
        semana[dsem]['leads'] += r['leads']['total']
    for s in semana.values():
        s['gasto'] = round(s['gasto'], 2)
        s['cpl'] = round(s['gasto'] / s['leads'], 2) if s['leads'] else None

    return {
        'periodo': {'inicio': ini.isoformat(), 'fim': fim.isoformat(),
                    'inicio_anterior': ini_a.isoformat(), 'fim_anterior': fim_a.isoformat()},
        'total': _resumir(total[0] if total else {}),
        'anterior': _resumir(anterior[0] if anterior else {}),
        'diario': [{'data': l.get('date_start'), **_resumir(l)} for l in diario],
        'campanhas': campanhas,
        'conjuntos': conjuntos,
        'anuncios': ads[:60],
        'videos': videos,
        'fadiga': fadiga,
        'publico': {'idade_genero': idade_genero, 'regioes': regioes,
                    'posicionamentos': posicionamentos, 'aparelhos': aparelhos,
                    'horas': horas, 'semana': list(semana.values())},
    }


# ============================================================
# PAGINA E INSTAGRAM
# ============================================================

_cache_pagina = {}


def _token_da_pagina():
    pid = cfg('META_PAGE_ID')
    if not pid:
        return None
    if 'token' not in _cache_pagina:
        try:
            _cache_pagina['token'] = _get(pid, {'fields': 'access_token'}).get('access_token')
        except ErroMeta:
            _cache_pagina['token'] = None
    return _cache_pagina['token']


def ig_user_id():
    ig = cfg('META_IG_USER_ID')
    if ig:
        return ig
    pid = cfg('META_PAGE_ID')
    if not pid:
        raise ErroMeta('META_IG_USER_ID e META_PAGE_ID vazios no config/.env')
    d = _get(pid, {'fields': 'instagram_business_account'})
    ig = (d.get('instagram_business_account') or {}).get('id')
    if not ig:
        raise ErroMeta('a pagina nao tem conta profissional do Instagram vinculada')
    os.environ['META_IG_USER_ID'] = ig
    return ig


@_bloco
def pagina():
    pid = cfg('META_PAGE_ID')
    if not pid:
        raise ErroMeta('META_PAGE_ID vazio no config/.env')
    d = _get(pid, {'fields': 'name,fan_count,followers_count,link'})
    return {'nome': d.get('name'), 'curtidas': d.get('fan_count'),
            'seguidores': d.get('followers_count'), 'link': d.get('link')}


def _metrica_total(ig, metrica, ini, fim):
    try:
        d = _get(f'{ig}/insights', {
            'metric': metrica, 'period': 'day', 'metric_type': 'total_value',
            'since': ini.isoformat(), 'until': (fim + timedelta(days=1)).isoformat()})
    except ErroMeta:
        return None
    for m in d.get('data', []):
        tv = m.get('total_value') or {}
        if 'value' in tv:
            return tv['value']
    return None


def _insights_post(media_id, produto):
    """Insights de um post. Reels ganham tempo assistido."""
    base = 'reach,saved,shares,total_interactions,likes,comments'
    if produto == 'REELS':
        base += ',views,ig_reels_avg_watch_time,ig_reels_video_view_total_time'
    out = {}
    for metricas in (base, 'profile_visits,follows'):
        try:
            for m in _get(f'{media_id}/insights', {'metric': metricas}).get('data', []):
                out[m['name']] = (m.get('values') or [{}])[0].get('value', 0)
        except ErroMeta:
            continue
    return out


@_bloco
def instagram(periodo):
    ig = ig_user_id()
    ini, fim, ini_a, fim_a = intervalo(periodo)
    perfil = _get(ig, {'fields': 'username,name,biography,followers_count,follows_count,media_count,'
                                 'profile_picture_url,website'})
    metricas, anteriores = {}, {}
    for m in ('reach', 'views', 'accounts_engaged', 'total_interactions', 'profile_views',
              'website_clicks', 'follows_and_unfollows', 'profile_links_taps'):
        metricas[m] = _metrica_total(ig, m, ini, fim)
        anteriores[m] = _metrica_total(ig, m, ini_a, fim_a)

    seguidores_dia = []
    try:
        d = _get(f'{ig}/insights', {'metric': 'follower_count', 'period': 'day',
                                    'since': max(ini, date.today() - timedelta(days=29)).isoformat(),
                                    'until': (fim + timedelta(days=1)).isoformat()})
        for m in d.get('data', []):
            for v in m.get('values', []):
                seguidores_dia.append({'data': v.get('end_time', '')[:10], 'novos': v.get('value', 0)})
    except ErroMeta:
        pass

    posts = []
    for p in _get_paginado(f'{ig}/media', {
            'fields': 'caption,media_type,media_product_type,permalink,thumbnail_url,media_url,'
                      'timestamp,like_count,comments_count', 'limit': 60}, limite_itens=120):
        dia = p.get('timestamp', '')[:10]
        if dia and not (ini.isoformat() <= dia <= fim.isoformat()):
            continue
        ins = _insights_post(p['id'], p.get('media_product_type'))
        formato = 'Reels' if p.get('media_product_type') == 'REELS' else {
            'CAROUSEL_ALBUM': 'Carrossel', 'VIDEO': 'Video', 'IMAGE': 'Imagem'}.get(p.get('media_type'), '-')
        alc = ins.get('reach')
        inter = ins.get('total_interactions')
        posts.append({
            'data': dia, 'formato': formato, 'link': p.get('permalink'),
            'miniatura': p.get('thumbnail_url') or p.get('media_url') or '',
            'legenda': (p.get('caption') or '')[:220],
            'curtidas': p.get('like_count', 0), 'comentarios': p.get('comments_count', 0),
            'alcance': alc, 'salvos': ins.get('saved'), 'compartilhamentos': ins.get('shares'),
            'interacoes': inter, 'visualizacoes': ins.get('views'),
            'tempo_medio': round(ins['ig_reels_avg_watch_time'] / 1000, 1) if ins.get('ig_reels_avg_watch_time') else None,
            'tempo_total_h': round(ins['ig_reels_video_view_total_time'] / 3600000, 1)
            if ins.get('ig_reels_video_view_total_time') else None,
            'visitas_perfil': ins.get('profile_visits'), 'seguiu': ins.get('follows'),
            'taxa_engajamento': round(inter / alc * 100, 2) if alc and inter is not None else None,
        })

    return {
        'perfil': {'usuario': perfil.get('username'), 'nome': perfil.get('name'),
                   'bio': perfil.get('biography'), 'site': perfil.get('website'),
                   'seguidores': perfil.get('followers_count'),
                   'seguindo': perfil.get('follows_count'), 'posts': perfil.get('media_count'),
                   'foto': perfil.get('profile_picture_url')},
        'metricas': metricas, 'anteriores': anteriores,
        'seguidores_dia': seguidores_dia, 'posts': posts,
    }


def _demografia(ig, quebra):
    for extra in ({'timeframe': 'this_month'}, {}):
        try:
            d = _get(f'{ig}/insights', {'metric': 'follower_demographics', 'period': 'lifetime',
                                        'metric_type': 'total_value', 'breakdown': quebra, **extra})
        except ErroMeta:
            continue
        out = []
        for m in d.get('data', []):
            for b in (m.get('total_value') or {}).get('breakdowns', []):
                for r in b.get('results', []):
                    out.append({'chave': ', '.join(r.get('dimension_values', [])), 'valor': r.get('value', 0)})
        return sorted(out, key=lambda x: -x['valor'])
    return []


@_bloco
def publico_instagram():
    """Quem segue o perfil: cidade, idade, genero e horario online."""
    ig = ig_user_id()
    cidades = _demografia(ig, 'city')[:15]
    idade = sorted(_demografia(ig, 'age'), key=lambda x: x['chave'])
    genero = _demografia(ig, 'gender')
    online = []
    try:
        d = _get(f'{ig}/insights', {'metric': 'online_followers', 'period': 'lifetime',
                                    'since': (date.today() - timedelta(days=2)).isoformat(),
                                    'until': date.today().isoformat()})
        for m in d.get('data', []):
            vals = m.get('values') or []
            if vals:
                horas = vals[-1].get('value') or {}
                online = [{'hora': int(h), 'seguidores': v} for h, v in sorted(horas.items(), key=lambda x: int(x[0]))]
    except ErroMeta:
        pass
    if not (cidades or idade or genero):
        raise ErroMeta('a Meta nao devolveu o publico (precisa de 100+ seguidores e da permissao instagram_manage_insights)')
    return {'cidades': cidades, 'idade': idade, 'genero': genero, 'online': online}


@_bloco
def leads_formulario(limite=60):
    pid = cfg('META_PAGE_ID')
    if not pid:
        raise ErroMeta('META_PAGE_ID vazio no config/.env')
    tok = _token_da_pagina()
    forms = _get_paginado(f'{pid}/leadgen_forms',
                          {'fields': 'id,name,status,leads_count', 'limit': 50}, token=tok)
    leads = []
    for f in forms:
        if f.get('status') != 'ACTIVE' and not f.get('leads_count'):
            continue
        try:
            for l in _get_paginado(f"{f['id']}/leads", {
                    'fields': 'created_time,field_data,ad_name,campaign_name', 'limit': 50},
                    token=tok, limite_itens=limite):
                campos = {c['name']: ', '.join(c.get('values', [])) for c in l.get('field_data', [])}
                leads.append({'data': l.get('created_time', '')[:16].replace('T', ' '),
                              'formulario': f.get('name'), 'campanha': l.get('campaign_name'),
                              'anuncio': l.get('ad_name'), 'campos': campos})
        except ErroMeta:
            continue
    leads.sort(key=lambda x: x['data'], reverse=True)
    return {'formularios': [{'nome': f.get('name'), 'status': f.get('status'),
                             'total': f.get('leads_count')} for f in forms],
            'leads': leads[:limite]}


def diagnostico():
    """O que o token enxerga (python painel/gerar_painel.py --testar)."""
    out = {}
    for nome, cam, campos in (('contas_anuncio', 'me/adaccounts', 'name,account_id,account_status'),
                              ('paginas', 'me/accounts', 'name,id,instagram_business_account')):
        try:
            out[nome] = _get_paginado(cam, {'fields': campos, 'limit': 100})
        except ErroMeta as e:
            out[nome] = f'ERRO: {e}'
    return out
