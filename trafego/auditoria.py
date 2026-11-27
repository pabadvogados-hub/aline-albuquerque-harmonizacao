"""
Auditoria das campanhas que JA ESTAO RODANDO na conta da Dra. Aline.

SO LEITURA. Gera um relatorio com o que esta errado, a prova (numero) e a acao,
mais os comandos prontos para aplicar depois do OK.

  python trafego/auditoria.py                 audita os ultimos 30 dias
  python trafego/auditoria.py --periodo 14d   (7d, 14d, 30d, 90d)
  python trafego/auditoria.py --demo          roda em cima dos dados ficticios do painel (teste)

Saida: relatorios/AUDITORIA_<data>.md e relatorios/auditoria_<data>.json
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'INTEGRACOES'))
sys.path.insert(0, os.path.join(RAIZ, 'painel'))
import meta_api as meta  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BRL = lambda v: '-' if v is None else ('R$ ' + f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'))

# objetivos/otimizacoes que nao trazem conversa
OTIMIZACAO_RUIM = {'LINK_CLICKS': 'cliques no link', 'POST_ENGAGEMENT': 'engajamento no post',
                   'REACH': 'alcance', 'IMPRESSIONS': 'impressoes', 'THRUPLAY': 'visualizacao de video',
                   'LANDING_PAGE_VIEWS': 'visita a pagina', 'PROFILE_VISIT': 'visita ao perfil'}

# textos que derrubam anuncio na Meta ou geram problema no conselho
PROIBIDOS = [
    (r'\bozempic\b|\bmounjaro\b|\bwegovy\b|\bsaxenda\b|semaglutida|tirzepatida', 'cita remedio (politica de medicamentos da Meta)'),
    (r'\bvoc[eê]\b[^.?!]{0,60}\b(emagreceu|engordou|perdeu peso|rosto caiu|flacid|ruga|velh|feia|gord)',
     '"voce" + condicao do corpo (atributo pessoal: Meta reprova)'),
    (r'garantid|100% (seguro|eficaz)|sem riscos?|resultado (certo|imediato|definitivo)', 'promessa de resultado'),
    (r'\bo melhor\b|\ba melhor\b|n[uú]mero 1|\bunic[oa] (em|de) santos', 'superlativo / comparacao'),
    (r'r\$ ?\d|\bpromo[cç][aã]o\b|\bdesconto\b|\bpacote\b|\bblack ?friday\b|\bgr[aá]tis\b|\boff\b|\bparcel', 'preco, pacote ou promocao no anuncio'),
    (r'rejuvene[cs]\w* \d+ anos|\d+ anos mais jovem', 'promessa de rejuvenescimento'),
    (r'toxina botul[ií]nica|\bbotox\b|[aá]cido hialur[oô]nico|sculptra|radiesse|ellans[eé]', 'marca/substancia no anuncio (conselhos proibem)'),
    (r'antes e depois|antes x depois|antes/depois', 'antes e depois (lado a lado e proibido em antienvelhecimento)'),
]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ============================================================
# COLETA (so leitura)
# ============================================================

def coletar(periodo):
    meta.carregar_env()
    conta = meta._conta()
    out = {'conta': {}, 'campanhas_cfg': [], 'conjuntos_cfg': [], 'anuncios_cfg': [], 'pixels': [],
           'anuncios': meta.anuncios(periodo), 'instagram': meta.instagram(periodo)}
    try:
        out['conta'] = meta._get(conta, {'fields': 'name,currency,timezone_name,account_status,disable_reason,'
                                                   'spend_cap,amount_spent,business{name}'})
    except meta.ErroMeta as e:
        out['conta'] = {'erro': str(e)}
    for chave, caminho, campos in (
            ('campanhas_cfg', 'campaigns', 'name,objective,effective_status,daily_budget,lifetime_budget,'
                                           'bid_strategy,buying_type,special_ad_categories,created_time'),
            ('conjuntos_cfg', 'adsets', 'name,campaign_id,effective_status,daily_budget,lifetime_budget,'
                                        'optimization_goal,destination_type,billing_event,bid_strategy,'
                                        'targeting,learning_stage_info,attribution_spec,created_time'),
            ('anuncios_cfg', 'ads', 'name,adset_id,campaign_id,effective_status,created_time,ad_review_feedback,'
                                    'issues_info,creative{body,title,object_type,video_id,image_url,'
                                    'asset_feed_spec,call_to_action_type}')):
        try:
            out[chave] = meta._get_paginado(f'{conta}/{caminho}', {'fields': campos, 'limit': 200,
                                                                    'effective_status': json.dumps(
                                                                        ['ACTIVE', 'PAUSED', 'ADSET_PAUSED',
                                                                         'CAMPAIGN_PAUSED', 'WITH_ISSUES',
                                                                         'DISAPPROVED', 'PENDING_REVIEW'])})
        except meta.ErroMeta as e:
            out[chave] = []
            out.setdefault('erros', []).append(f'{caminho}: {e}')
    try:
        out['pixels'] = meta._get_paginado(f'{conta}/adspixels', {'fields': 'name,last_fired_time'})
    except meta.ErroMeta:
        pass
    return out


def dados_demo(periodo):
    """Monta uma conta ficticia com erros tipicos para testar as regras."""
    import demo
    d = demo.gerar()
    p = d['periodos'][periodo]
    a = p['anuncios']
    camp_cfg, cj_cfg, ad_cfg = [], [], []
    for k, c in enumerate(a['campanhas']):
        camp_cfg.append({'id': c['id'], 'name': c['nome'], 'objective': c['objetivo'],
                         'effective_status': c['status'], 'daily_budget': None})
    for k, cj in enumerate(a['conjuntos']):
        alvo = {'age_min': 18 if k == 0 else 28, 'age_max': 65,
                'geo_locations': {'cities': [{'name': 'Santos', 'radius': 40 if k == 1 else 25}]},
                'publisher_platforms': ['facebook', 'instagram', 'audience_network'] if k == 2 else None}
        if k != 1:
            alvo['genders'] = [2]
        cj_cfg.append({'id': cj['id'], 'name': cj['nome'], 'effective_status': cj['status'],
                       'daily_budget': str(int((cj['orcamento_diario'] or 10) * 100)),
                       'optimization_goal': 'POST_ENGAGEMENT' if k == 2 else 'CONVERSATIONS',
                       'destination_type': 'WHATSAPP', 'targeting': alvo,
                       'learning_stage_info': {'status': 'FAIL' if cj['aprendizado'] == 'Aprendizado limitado' else 'SUCCESS'}})
    textos = ['Voce emagreceu e seu rosto caiu? Avaliacao com desconto so esta semana!',
              'Antes e depois real com Ozempic: resultado garantido.']
    cj_por_camp = {cj['campanha']: cj['id'] for cj in a['conjuntos']}
    for k, ad in enumerate(a['anuncios']):
        ad_cfg.append({'id': ad['id'], 'name': ad['nome'], 'effective_status': ad['status'],
                       'adset_id': cj_por_camp.get(ad['campanha']),
                       'created_time': ad['criado'],
                       'creative': {'body': textos[k] if k < 2 else ad['texto'],
                                    'video_id': 'v' if ad['tipo'] == 'Video' else None}})
    return {'conta': {'name': 'Dra Aline (DEMO)', 'currency': 'BRL', 'account_status': 1},
            'campanhas_cfg': camp_cfg, 'conjuntos_cfg': cj_cfg, 'anuncios_cfg': ad_cfg, 'pixels': [],
            'anuncios': a, 'instagram': p['instagram'], 'demo': True}


# ============================================================
# REGRAS
# ============================================================

def auditar(d, negocio, bm):
    A = []   # achados

    def add(sev, area, titulo, prova, acao, comando=None, impacto=None):
        A.append({'sev': sev, 'area': area, 'titulo': titulo, 'prova': prova, 'acao': acao,
                  'comando': comando, 'impacto': impacto})

    ads = d['anuncios']
    if not ads.get('ok'):
        add('critico', 'Acesso', 'Sem leitura dos anuncios', ads.get('erro', ''), 'Liberar acesso (docs/COMO_LIBERAR_ACESSO_META.md).')
        return A
    t = ads['total']
    alvo = _num(negocio.get('cpl_meta')) or bm.get('custo_conversa', {}).get('bom', 15)
    teto = _num(os.getenv('TETO_DIARIO_REAIS')) or 9999
    met_cj = {c['id']: c for c in ads.get('conjuntos', [])}
    met_ad = {a['id']: a for a in ads.get('anuncios', [])}
    met_camp = {c['id']: c for c in ads.get('campanhas', [])}

    # --- conta
    c = d.get('conta', {})
    if c.get('account_status') not in (None, 1):
        add('critico', 'Conta', 'Conta de anuncio com restricao', f"status {c.get('account_status')} motivo {c.get('disable_reason')}",
            'Resolver no Gerenciador > Qualidade da conta antes de qualquer otimizacao.')

    # --- campanhas: objetivo
    for cp in d.get('campanhas_cfg', []):
        if cp.get('effective_status') != 'ACTIVE':
            continue
        if cp.get('objective') in ('OUTCOME_TRAFFIC', 'OUTCOME_AWARENESS', 'LINK_CLICKS', 'POST_ENGAGEMENT', 'REACH'):
            m = met_camp.get(cp['id'], {})
            add('critico', 'Estrutura', f'Campanha "{cp["name"]}" com objetivo errado ({cp["objective"]})',
                f"gastou {BRL(m.get('gasto'))} no periodo; a Meta entrega para quem clica/curte, nao para quem conversa",
                'Recriar como campanha de Engajamento/Leads com otimizacao para CONVERSAS no WhatsApp/Direct e pausar esta depois que a nova sair do aprendizado.')

    # --- conjuntos
    ativos = [cj for cj in d.get('conjuntos_cfg', []) if cj.get('effective_status') == 'ACTIVE']
    pequenos = []
    assinaturas = {}
    usa_remarketing = False
    for cj in ativos:
        m = met_cj.get(cj['id'], {})
        orc = (_num(cj.get('daily_budget')) or 0) / 100
        nome = cj.get('name')
        og = cj.get('optimization_goal')
        if og in OTIMIZACAO_RUIM:
            add('critico', 'Otimizacao', f'"{nome}" otimiza para {OTIMIZACAO_RUIM[og]}',
                f"{m.get('leads', {}).get('total', 0)} conversas por {BRL(m.get('gasto'))}",
                'Trocar a meta de desempenho do conjunto para "Maximizar conversas" (destino WhatsApp ou Direct). '
                'Na pratica: duplicar o conjunto com a otimizacao certa e pausar o antigo.')
        if orc and orc < 20:
            pequenos.append((nome, orc))
        st = (cj.get('learning_stage_info') or {}).get('status')
        if st == 'FAIL':
            add('atencao', 'Aprendizado', f'"{nome}" em aprendizado limitado',
                f"{m.get('leads', {}).get('total', 0)} conversas no periodo; a Meta precisa de ~50/semana por conjunto",
                'Juntar conjuntos parecidos num so (mesma verba somada) ou aumentar a verba deste.')
        tg = cj.get('targeting') or {}
        if tg.get('custom_audiences'):
            usa_remarketing = True
        amin, amax = tg.get('age_min', 18), tg.get('age_max', 65)
        if amin < 25:
            fx = [l for l in ads['publico']['idade_genero'] if l['idade'] in ('18-24',)]
            g = sum(l['gasto'] for l in fx)
            ld = sum(l['leads'] for l in fx)
            add('atencao', 'Publico', f'"{nome}" aceita a partir de {amin} anos',
                f"18-24 anos: {BRL(g)} gastos e {ld} conversas ({BRL(g / ld) if ld else 'sem conversa'})",
                'Subir idade minima para 28-30: o nicho (pos-emagrecimento, flacidez) quase nao esta abaixo dos 25.')
        if not tg.get('genders'):
            hom = sum(l['gasto'] for l in ads['publico']['idade_genero'] if l['genero'] == 'male')
            if hom > 0:
                add('atencao', 'Publico', f'"{nome}" entrega para homens tambem',
                    f"{BRL(hom)} gastos com homens no periodo (somando a conta)",
                    'Limitar o conjunto a mulheres, a nao ser que exista oferta especifica para homens.',
                    impacto=hom)
        geo = tg.get('geo_locations') or {}
        raios = [x.get('radius') for x in geo.get('cities', []) + geo.get('custom_locations', []) if x.get('radius')]
        if geo.get('regions') or geo.get('countries') or any(r and r > 25 for r in raios):
            add('atencao', 'Publico', f'"{nome}" com area grande demais',
                f"regioes={[r.get('name') for r in geo.get('regions', [])]} paises={geo.get('countries')} raios={raios}",
                'Paciente de avaliacao presencial vem de ate 15-20 km. Usar raio de 12-15 km do consultorio ou as 5 cidades da Baixada.')
        plats = tg.get('publisher_platforms')
        if plats and 'audience_network' in plats:
            an = [p for p in ads['publico']['posicionamentos'] if p['plataforma'] == 'audience_network']
            g = sum(p['gasto'] for p in an)
            add('atencao', 'Posicionamento', f'"{nome}" aparece na Audience Network',
                (f"{BRL(g)} gastos em apps/sites de terceiros com {sum(p['leads'] for p in an)} conversas" if g
                 else 'posicionamento ligado (ainda sem gasto relevante no periodo)'),
                'Remover Audience Network: clique acidental, quase nunca vira conversa de clinica.')
        ass = (amin, amax, json.dumps(geo, sort_keys=True), json.dumps(tg.get('genders')), json.dumps(tg.get('flexible_spec'), sort_keys=True))
        assinaturas.setdefault(ass, []).append(nome)

    if len(pequenos) >= 3:
        add('atencao', 'Estrutura', f'Verba picada em {len(pequenos)} conjuntos com menos de R$ 20/dia',
            ', '.join(f'{n} ({BRL(o)})' for n, o in pequenos[:5]),
            'Consolidar em 1 ou 2 conjuntos de teste com 4-6 criativos cada. Conjunto pequeno nao sai do aprendizado.')
    for ass, nomes in assinaturas.items():
        if len(nomes) >= 2:
            add('atencao', 'Estrutura', 'Conjuntos com o mesmo publico competindo entre si',
                ' x '.join(nomes), 'Unir num conjunto so e diferenciar pelos criativos.')
    if ativos and not usa_remarketing:
        add('oportunidade', 'Remarketing', 'Nenhum remarketing rodando',
            f"o Instagram dela tem {d.get('instagram', {}).get('perfil', {}).get('seguidores', '?')} seguidores e gente que ja viu os videos",
            'Criar conjunto de R$ 15/dia para quem interagiu com o perfil em 30-60 dias + assistiu 50% dos videos, '
            'com criativo de prova social e chamada para a avaliacao. Normalmente e a conversa mais barata da conta.')

    # --- verba no lugar errado
    camps = [m for m in ads['campanhas'] if m['status'] == 'ACTIVE' and m['gasto'] > 0]
    if len(camps) >= 2 and t['cpl']:
        pior = max(camps, key=lambda c: c['cpl'] or 9e9)
        melhor = min([c for c in camps if c['cpl']], key=lambda c: c['cpl'], default=None)
        if melhor and pior['cpl'] and pior['cpl'] >= 1.6 * melhor['cpl'] and pior['gasto'] >= melhor['gasto'] * 0.6:
            add('critico', 'Verba', 'Dinheiro indo para a campanha mais cara',
                f'"{pior["nome"]}" {BRL(pior["gasto"])} a {BRL(pior["cpl"])}/conversa x '
                f'"{melhor["nome"]}" {BRL(melhor["gasto"])} a {BRL(melhor["cpl"])}/conversa',
                'Tirar verba da cara e passar para a barata, em passos de 20% a cada 3 dias.',
                impacto=round(pior['gasto'] - pior['leads']['total'] * melhor['cpl'], 2))

    # --- anuncios
    por_cj = {}
    for ad in d.get('anuncios_cfg', []):
        if ad.get('effective_status') in ('DISAPPROVED', 'WITH_ISSUES'):
            fb = ad.get('ad_review_feedback') or ad.get('issues_info') or ''
            add('critico', 'Politica', f'Anuncio "{ad["name"]}" reprovado/com problema', str(fb)[:200],
                'Reescrever conforme as regras (CLAUDE.md) e subir de novo. Reprovacoes repetidas derrubam a conta.')
        if ad.get('effective_status') == 'ACTIVE':
            por_cj.setdefault(ad.get('adset_id'), []).append(ad)
        if ad.get('effective_status') not in ('ACTIVE', 'WITH_ISSUES', 'PENDING_REVIEW'):
            continue
        texto = ((ad.get('creative') or {}).get('body') or '') + ' ' + ((ad.get('creative') or {}).get('title') or '')
        motivos = [m for rx, m in PROIBIDOS if re.search(rx, texto, re.I)]
        if motivos:
            grave = any('remedio' in m or 'atributo' in m for m in motivos)
            add('critico' if grave else 'atencao', 'Politica', f'Texto arriscado em "{ad["name"]}"',
                f'"{texto.strip()[:160]}" -> ' + '; '.join(motivos),
                'Reescrever em terceira pessoa, sem remedio, preco ou promessa (use /trafego-copy). '
                'Anuncio reprovado varias vezes derruba a conta.')
    nomes_cj = {cj['id']: cj.get('name') for cj in d.get('conjuntos_cfg', [])}
    for cj_id, lista in por_cj.items():
        if not cj_id:
            continue
        nome = nomes_cj.get(cj_id) or (met_cj.get(cj_id) or {}).get('nome') or cj_id
        if len(lista) == 1:
            add('atencao', 'Criativo', f'"{nome}" com 1 anuncio so',
                'sem alternativa, a Meta nao tem o que testar', 'Subir 3-5 criativos com ganchos diferentes (video/ gera as variacoes).')
        elif len(lista) > 8:
            add('atencao', 'Criativo', f'"{nome}" com {len(lista)} anuncios ativos', 'verba diluida demais',
                'Manter os 4-6 melhores e pausar o resto.')
    sem_video = [a for a in ads['anuncios'] if a['status'] == 'ACTIVE' and a.get('tipo') != 'Video']
    if ads['anuncios'] and len(sem_video) == len([a for a in ads['anuncios'] if a['status'] == 'ACTIVE']):
        add('oportunidade', 'Criativo', 'Nenhum video rodando', 'so imagem/carrossel',
            'No nicho, Reels dela falando para a camera e o formato que mais traz conversa. Gravar 6 com o /roteiro-video.')
    for a in ads['anuncios']:
        if a['status'] != 'ACTIVE':
            continue
        ref = t['cpl'] or alvo
        if a['gasto'] >= 2 * alvo and a['leads']['total'] == 0:
            add('critico', 'Criativo', f'Pausar "{a["nome"]}"', f'{BRL(a["gasto"])} sem nenhuma conversa',
                'Pausar.', f'python trafego/painel.py pausar {a["id"]} --confirmo', impacto=a['gasto'])
        elif a['cpl'] and a['cpl'] >= 1.7 * ref and a['gasto'] >= 2.5 * alvo:
            add('atencao', 'Criativo', f'Pausar "{a["nome"]}"', f'{BRL(a["cpl"])} por conversa ({a["cpl"] / ref:.1f}x a media)',
                'Pausar e substituir por variacao do melhor anuncio.', f'python trafego/painel.py pausar {a["id"]} --confirmo')
        v = a.get('video')
        if v and a['impressoes'] >= 1500:
            if v.get('gancho') is not None and v['gancho'] < bm.get('gancho', {}).get('ruim', 21):
                add('atencao', 'Criativo', f'Gancho fraco: "{a["nome"]}" ({v["gancho"]:.0f}%)',
                    f'mercado: {bm.get("gancho", {}).get("bom", 30)}%+', 'Regravar so os 3 primeiros segundos (3 ganchos novos, mesmo corpo).')
            if v.get('retencao') is not None and v['retencao'] < bm.get('retencao', {}).get('ruim', 27) and (v.get('gancho') or 0) >= 25:
                add('atencao', 'Criativo', f'Video perde gente no meio: "{a["nome"]}"',
                    f'gancho {v["gancho"]:.0f}% mas so {v["retencao"]:.0f}% chegam ao fim', 'Cortar para 15-25 s e mostrar a explicacao/resultado mais cedo.')
        if a['frequencia'] >= bm.get('frequencia_max', {}).get('ruim', 3.5):
            add('atencao', 'Fadiga', f'"{a["nome"]}" cansado (frequencia {a["frequencia"]:.1f})',
                f'CTR {a["ctr_link"]}%', 'Subir criativo novo no mesmo conjunto; manter este ate o novo pegar.')
        rk = a.get('ranking') or {}
        if str(rk.get('quality', '')).startswith('BELOW') and a['impressoes'] >= 2000:
            add('atencao', 'Criativo', f'Meta da qualidade abaixo da media para "{a["nome"]}"', str(rk),
                'Criativo com cara de propaganda. Trocar por video nativo, dela falando.')

    # --- escala
    for cj in ads.get('conjuntos', []):
        if cj['status'] == 'ACTIVE' and cj['orcamento_diario'] and cj['leads']['total'] >= 5 and cj['cpl'] and cj['cpl'] <= 0.75 * alvo:
            novo = min(round(cj['orcamento_diario'] * 1.2, 2), teto)
            if novo > cj['orcamento_diario']:
                add('oportunidade', 'Escala', f'Escalar "{cj["nome"]}"',
                    f'{cj["leads"]["total"]} conversas a {BRL(cj["cpl"])} (meta {BRL(alvo)})',
                    f'Subir {BRL(cj["orcamento_diario"])} -> {BRL(novo)}/dia.',
                    f'python trafego/painel.py orcamento {cj["id"]} {novo} --confirmo')

    # --- qualidade da conversa
    tl = t['leads']
    if tl['conversas'] >= 10:
        prof = tl['conversas_profundas'] / tl['conversas'] * 100
        if prof < bm.get('conversa_profunda', {}).get('ruim', 35):
            add('atencao', 'Conversas', f'So {prof:.0f}% das conversas passam da 1a mensagem', f'{tl["conversas"]} conversas',
                'Mensagem de boas-vindas com pergunta ("o que mais te incomoda hoje no rosto?") e resposta em ate 5 min; ligar o robo de atendimento/.')

    # --- horario
    hs = [h for h in ads['publico'].get('horas', []) if h['leads'] >= 2]
    if len(hs) >= 6 and t['cpl']:
        caros = [h for h in hs if h['cpl'] and h['cpl'] >= 1.8 * t['cpl']]
        if caros:
            add('oportunidade', 'Horario', 'Horarios caros', ', '.join(f"{h['hora']:02d}h ({BRL(h['cpl'])})" for h in caros[:5]),
                'Se a conta usar orcamento vitalicio, programar pausa nesses horarios; senao, garantir atendimento nos horarios baratos.')

    ordem = {'critico': 0, 'atencao': 1, 'oportunidade': 2}
    A.sort(key=lambda x: (ordem[x['sev']], -(x.get('impacto') or 0)))
    return A


# ============================================================
# RELATORIO
# ============================================================

def relatorio(d, achados, periodo, negocio):
    ads = d['anuncios']
    t = ads.get('total', {}) if ads.get('ok') else {}
    hoje = date.today().strftime('%d/%m/%Y')
    crit = [a for a in achados if a['sev'] == 'critico']
    aten = [a for a in achados if a['sev'] == 'atencao']
    opo = [a for a in achados if a['sev'] == 'oportunidade']
    desperdicio = sum(a.get('impacto') or 0 for a in achados)
    L = [f"# Auditoria das campanhas - {negocio.get('nome_profissional', 'Dra. Aline')}",
         f"_{hoje} - periodo analisado: {meta.PERIODOS.get(periodo, periodo)}{' - DEMONSTRACAO' if d.get('demo') else ''}_", '']
    if t:
        L += ['## Retrato da conta', '',
              f"- Investido: **{BRL(t['gasto'])}** | Conversas: **{t['leads']['total']}** | Custo por conversa: **{BRL(t['cpl'])}** (meta {BRL(_num(negocio.get('cpl_meta')))})",
              f"- Conversas reais (2+ mensagens): {t['leads']['conversas_profundas']} | CTR de link {t['ctr_link']}% | CPM {BRL(t['cpm'])} | frequencia {t['frequencia']}",
              f"- Campanhas ativas: {len([c for c in ads['campanhas'] if c['status'] == 'ACTIVE'])} | conjuntos ativos: "
              f"{len([c for c in ads.get('conjuntos', []) if c['status'] == 'ACTIVE'])} | anuncios com entrega: {len(ads['anuncios'])}",
              f"- Desperdicio identificado (estimado): **{BRL(desperdicio)}** no periodo" if desperdicio else '', '']
    L += [f"## Resumo: {len(crit)} criticos, {len(aten)} de atencao, {len(opo)} oportunidades", '']
    for titulo, lista in (('Criticos (resolver ja)', crit), ('Atencao', aten), ('Oportunidades', opo)):
        if not lista:
            continue
        L += [f'### {titulo}', '']
        for k, a in enumerate(lista, 1):
            L.append(f"{k}. **[{a['area']}] {a['titulo']}**")
            L.append(f"   - Prova: {a['prova']}")
            L.append(f"   - Acao: {a['acao']}")
            if a.get('comando'):
                L.append(f"   - Comando (depois do OK): `{a['comando']}`")
        L.append('')
    L += ['## Plano de otimizacao', '',
          '**Semana 1 - arrumar a casa (sem mexer no que funciona):**',
          '- Pausar o que gasta sem conversa e corrigir otimizacao/objetivo errado.',
          '- Reescrever os textos arriscados (politica da Meta e do conselho).',
          '- Tirar homens, faixa 18-24 e Audience Network onde nao fazem sentido; fechar o raio na Baixada.',
          '- Ligar a mensagem de boas-vindas com pergunta e o robo de qualificacao.', '',
          '**Semana 2 - criativo:**',
          '- Gravar 6 Reels nos 5 angulos do estudo; o editor gera 3 ganchos por video.',
          '- Subir no conjunto vencedor (4-6 anuncios por conjunto). Nao mexer por 7 dias.', '',
          '**Semanas 3-4 - escala:**',
          '- Escalar +20% a cada 3 dias o conjunto com conversa abaixo da meta.',
          '- Remarketing R$ 15/dia (engajou 30-60d + viu 50% do video).',
          '- Medir no painel: custo por avaliacao e por paciente, nao so por conversa.', '',
          '> Nenhuma alteracao foi feita na conta. Os comandos acima so rodam com `--confirmo`, depois do OK.']
    return '\n'.join(x for x in L if x is not None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--periodo', default='30d', choices=['7d', '14d', '30d', '90d', 'mes', 'mes_passado'])
    ap.add_argument('--demo', action='store_true')
    a = ap.parse_args()
    neg = json.load(open(os.path.join(RAIZ, 'config', 'negocio.json'), encoding='utf-8'))
    bm = json.load(open(os.path.join(RAIZ, 'config', 'benchmarks.json'), encoding='utf-8'))
    d = dados_demo(a.periodo) if a.demo else coletar(a.periodo)
    achados = auditar(d, neg, bm)
    md = relatorio(d, achados, a.periodo, neg)
    pasta = os.path.join(RAIZ, 'relatorios')
    os.makedirs(pasta, exist_ok=True)
    suf = date.today().isoformat() + ('_DEMO' if a.demo else '')
    open(os.path.join(pasta, f'AUDITORIA_{suf}.md'), 'w', encoding='utf-8').write(md)
    json.dump({'gerado_em': datetime.now().isoformat(timespec='seconds'), 'periodo': a.periodo, 'achados': achados},
              open(os.path.join(pasta, f'auditoria_{suf}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(md)
    print(f'\nSalvo em relatorios/AUDITORIA_{suf}.md')


if __name__ == '__main__':
    main()
