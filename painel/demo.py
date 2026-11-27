"""
Dados FICTICIOS para mostrar o painel antes do acesso a Meta.
O painel mostra a faixa "DEMONSTRACAO" sempre que estes dados estao em uso.
Os numeros seguem as faixas reais de harmonizacao facial em cidade media (Baixada Santista).
"""
import random
from datetime import date, timedelta

import meta_api as meta

# nome, objetivo, orcamento/dia, custo/conversa base, ctr base, frequencia, status
CAMPANHAS = [
    ('[FENIX] Derretimento facial pos-emagrecimento - WhatsApp', 'OUTCOME_ENGAGEMENT', 45, 13.5, 1.6, 1.9, 'ACTIVE'),
    ('[FENIX] Canetas emagrecedoras - rosto caido - WhatsApp', 'OUTCOME_ENGAGEMENT', 30, 16.8, 1.4, 2.2, 'ACTIVE'),
    ('[FENIX] Corporal - flacidez pos-emagrecimento', 'OUTCOME_ENGAGEMENT', 20, 24.5, 1.0, 2.6, 'ACTIVE'),
    ('[DIRECT] Avaliacao Metodo Fenix - Instagram Direct', 'OUTCOME_ENGAGEMENT', 15, 11.2, 1.9, 1.7, 'ACTIVE'),
    ('[REMARKETING] Engajou 30d + visitou perfil', 'OUTCOME_ENGAGEMENT', 12, 9.4, 2.2, 3.8, 'ACTIVE'),
    ('[TESTE] Full face 40+ - formulario', 'OUTCOME_LEADS', 0, 29.0, 0.8, 1.6, 'PAUSED'),
]

# nome, tipo, gancho base, retencao base, duracao(s)
ANUNCIOS = {
    0: [('Reels - "Isso tem nome: derretimento facial"', 'Video', 38, 46, 24),
        ('Reels - Dra. Aline explica o derretimento facial', 'Video', 29, 33, 41),
        ('Carrossel - 3 sinais de rosto derretido', 'Carrossel', None, None, None)],
    1: [('Reels - "Trato o rosto agora ou espero a caneta?"', 'Video', 41, 24, 32),
        ('Video - depoimento paciente -18kg', 'Video', 19, 44, 28)],
    2: [('Reels - Fenix corporal braco e abdomen', 'Video', 22, 29, 37),
        ('Imagem - antes e depois corporal', 'Imagem', None, None, None)],
    3: [('Reels - bastidor da avaliacao na clinica', 'Video', 33, 41, 19)],
    4: [('Reels - "Voce ja me segue, falta a avaliacao"', 'Video', 35, 52, 15),
        ('Imagem - agenda de dezembro aberta', 'Imagem', None, None, None)],
    5: [('Imagem - full face 40+', 'Imagem', None, None, None)],
}

POSTS = [
    ('Reels', 'Emagreceu e o rosto caiu? Isso tem nome: derretimento facial. Te explico o Metodo Fenix.', 18.4),
    ('Carrossel', '5 sinais de que seu rosto perdeu sustentacao depois do emagrecimento', None),
    ('Reels', 'Antes e depois real: paciente -22kg, 3 sessoes do Fenix facial', 21.7),
    ('Imagem', 'Agenda de avaliacoes aberta para dezembro', None),
    ('Reels', 'Caneta emagrecedora e rosto: o que ninguem te conta', 16.2),
    ('Carrossel', 'Mitos sobre preenchimento depois de emagrecer', None),
    ('Reels', 'Um dia comigo na clinica em Santos', 9.8),
    ('Imagem', 'Depoimento da paciente Renata', None),
    ('Reels', 'Bioestimulador x preenchimento: qual o seu caso?', 14.1),
    ('Reels', 'Minha historia: por que criei o Metodo Fenix', 23.5),
]


def _linha(gasto, cpl, ctr, freq, rnd, tipo='conversa', video=None):
    leads = int(round(gasto / cpl * rnd.uniform(0.85, 1.15))) if gasto and cpl else 0
    cpm = rnd.uniform(17, 27)
    imp = int(gasto / cpm * 1000) if gasto else 0
    cliques = int(imp * ctr / 100)
    alcance = int(imp / freq) if freq else 0
    conv, form = (leads, 0) if tipo == 'conversa' else (0, leads)
    prof = int(conv * rnd.uniform(0.52, 0.71))
    out = {
        'gasto': round(gasto, 2), 'impressoes': imp, 'alcance': alcance, 'cliques': cliques,
        'ctr': round(ctr * 1.6, 2) if gasto else 0, 'ctr_link': round(ctr, 2) if gasto else 0,
        'cpc': round(gasto / cliques, 2) if cliques else 0, 'cpm': round(cpm, 2) if gasto else 0,
        'frequencia': round(freq, 2) if gasto else 0,
        'leads': {'conversas': conv, 'formularios': form, 'site': 0, 'total': conv + form,
                  'conversas_profundas': prof, 'bloqueios': int(conv * rnd.uniform(0, 0.03))},
        'cpl': round(gasto / (conv + form), 2) if conv + form else None,
        'custo_conversa_profunda': round(gasto / prof, 2) if prof else None,
        'engajamento': {'reacoes': int(imp * rnd.uniform(0.006, 0.012)),
                        'comentarios': int(imp * rnd.uniform(0.0004, 0.0012)),
                        'compartilhamentos': int(imp * rnd.uniform(0.0003, 0.001)),
                        'salvos': int(imp * rnd.uniform(0.0005, 0.0016)),
                        'visitas_perfil': int(imp * rnd.uniform(0.002, 0.005))},
    }
    if video and gasto:
        gancho, ret, dur = video
        g = gancho * rnd.uniform(0.9, 1.1)
        r = ret * rnd.uniform(0.9, 1.1)
        v3 = int(imp * g / 100)
        plays = int(v3 * 1.45)
        thru = int(v3 * r / 100)
        queda = 0.45 + (r / 200)
        p25 = 100 * min(0.92, queda)
        curva = {'p25': round(p25, 1), 'p50': round(p25 * 0.62, 1), 'p75': round(p25 * 0.42, 1),
                 'p95': round(p25 * 0.27, 1), 'p100': round(p25 * 0.22, 1)}
        out['video'] = {'plays': plays, 'views_3s': v3, 'thruplays': thru, 'gancho': round(g, 1),
                        'retencao': round(r, 1), 'tempo_medio': round(dur * (0.12 + r / 220), 1),
                        'curva': curva, 'custo_thruplay': round(gasto / thru, 2) if thru else None}
    return out


def _soma(linhas):
    g = sum(l['gasto'] for l in linhas)
    imp = sum(l['impressoes'] for l in linhas)
    alc = int(sum(l['alcance'] for l in linhas) * 0.74)
    cli = sum(l['cliques'] for l in linhas)
    leads = {k: sum(l['leads'][k] for l in linhas)
             for k in ('conversas', 'formularios', 'site', 'total', 'conversas_profundas', 'bloqueios')}
    vids = [l['video'] for l in linhas if l.get('video')]
    out = {'gasto': round(g, 2), 'impressoes': imp, 'alcance': alc, 'cliques': cli,
           'ctr': round(cli / imp * 160, 2) if imp else 0, 'ctr_link': round(cli / imp * 100, 2) if imp else 0,
           'cpc': round(g / cli, 2) if cli else 0, 'cpm': round(g / imp * 1000, 2) if imp else 0,
           'frequencia': round(imp / alc, 2) if alc else 0, 'leads': leads,
           'cpl': round(g / leads['total'], 2) if leads['total'] else None,
           'custo_conversa_profunda': round(g / leads['conversas_profundas'], 2) if leads['conversas_profundas'] else None,
           'engajamento': {k: sum(l['engajamento'][k] for l in linhas) for k in linhas[0]['engajamento']}}
    if vids:
        v3 = sum(v['views_3s'] for v in vids)
        thru = sum(v['thruplays'] for v in vids)
        imp_v = sum(l['impressoes'] for l in linhas if l.get('video'))
        out['video'] = {'plays': sum(v['plays'] for v in vids), 'views_3s': v3, 'thruplays': thru,
                        'gancho': round(v3 / imp_v * 100, 1) if imp_v else None,
                        'retencao': round(thru / v3 * 100, 1) if v3 else None,
                        'tempo_medio': round(sum(v['tempo_medio'] for v in vids) / len(vids), 1),
                        'curva': {k: round(sum(v['curva'][k] for v in vids) / len(vids), 1)
                                  for k in ('p25', 'p50', 'p75', 'p95', 'p100')},
                        'custo_thruplay': None}
    return out


def _anuncios_bloco(periodo, rnd):
    ini, fim, ini_a, fim_a = meta.intervalo(periodo)
    dias = (fim - ini).days + 1
    campanhas, conjuntos, ads = [], [], []
    for idx, (nome, obj, orc, cpl, ctr, freq, st) in enumerate(CAMPANHAS):
        ativo = dias if st == 'ACTIVE' else (min(dias, 5) if periodo in ('mes_passado', '90d') else 0)
        gasto = (orc or 35) * ativo * rnd.uniform(0.9, 1.0)
        tipo = 'formulario' if obj == 'OUTCOME_LEADS' else 'conversa'
        ads_c = []
        if gasto:
            pesos = [rnd.uniform(0.5, 1.6) for _ in ANUNCIOS[idx]]
            for (nome_ad, tp, gch, ret, dur), p in zip(ANUNCIOS[idx], pesos):
                gg = gasto * p / sum(pesos)
                video = (gch, ret, dur) if tp == 'Video' else None
                fator = 0.75 if (gch or 0) >= 35 else (1.35 if tp == 'Imagem' else 1.0)
                l = _linha(gg, cpl * fator * rnd.uniform(0.85, 1.2), ctr * rnd.uniform(0.8, 1.25),
                           freq * rnd.uniform(0.85, 1.2), rnd, tipo, video)
                rk = 'ABOVE_AVERAGE' if (gch or 0) >= 35 else ('BELOW_AVERAGE_35' if tp == 'Imagem' and idx == 2 else 'AVERAGE')
                ad = {'id': f'demo_a{idx}_{len(ads) + len(ads_c)}', 'nome': nome_ad, 'campanha': nome,
                      'conjunto': f'{nome.split(" - ")[0]} | Santos +25km | 28-55 | Mulheres',
                      'status': st, 'miniatura': '', 'tipo': tp, 'titulo': '', 'previa': '', 'link_instagram': '',
                      'texto': 'Quando o emagrecimento e rapido, o rosto pode perder sustentacao. Isso tem nome: '
                               'derretimento facial. No Metodo Fenix a avaliacao comeca pela sustentacao, '
                               'nao so pelo volume. Avaliacao em Santos: chama no WhatsApp.',
                      'criado': (fim - timedelta(days=rnd.randint(5, 60))).isoformat(),
                      'ranking': {'quality': rk, 'engagement': 'AVERAGE' if rk == 'AVERAGE' else rk,
                                  'conversion': 'ABOVE_AVERAGE' if (gch or 0) >= 38 else 'AVERAGE'},
                      **l}
                if tp == 'Video':
                    ad.update({'capa': '', 'arquivo': '', 'duracao': dur, 'link_video': ''})
                ads_c.append(ad)
        ads += ads_c
        tot_c = _soma(ads_c) if ads_c else _linha(0, 0, 0, 0, rnd)
        campanhas.append({'id': f'demo_c{idx}', 'nome': nome, 'status': st, 'objetivo': obj,
                          'orcamento_diario': orc or None, **tot_c})
        if ads_c:
            conjuntos.append({'id': f'demo_s{idx}', 'nome': f'{nome.split(" - ")[0]} | Santos +25km | 28-55',
                              'campanha': nome, 'status': st, 'orcamento_diario': orc or None,
                              'otimizacao': 'CONVERSATIONS' if tipo == 'conversa' else 'LEAD_GENERATION',
                              'destino': 'WHATSAPP' if idx != 3 else 'INSTAGRAM_DIRECT',
                              'publico': {'idade': '28-55', 'genero': 'Mulheres',
                                          'local': 'Santos +25km' if idx != 4 else 'Publico personalizado: engajou 30d'},
                              'aprendizado': 'Aprendizado limitado' if idx == 2 else 'Concluido', **tot_c})
    campanhas.sort(key=lambda c: -c['gasto'])
    ads.sort(key=lambda x: (x['cpl'] is None, x['cpl'] or 0))
    total = _soma([a for a in ads if a['gasto']])

    diario = []
    for d in range(dias):
        dia = ini + timedelta(days=d)
        fator = 1.15 if dia.weekday() in (0, 1, 2) else (0.78 if dia.weekday() == 6 else 0.95)
        g = total['gasto'] / dias * rnd.uniform(0.88, 1.1)
        diario.append({'data': dia.isoformat(),
                       **_linha(g, (total['cpl'] or 15) / fator, total['ctr_link'] * rnd.uniform(0.85, 1.15),
                                1.08, rnd)})

    ant = dict(total)
    ant['gasto'] = round(total['gasto'] * 0.92, 2)
    lt = int(total['leads']['total'] * 0.81)
    ant['leads'] = {**total['leads'], 'total': lt, 'conversas': lt,
                    'conversas_profundas': int(lt * 0.55)}
    ant['cpl'] = round(ant['gasto'] / lt, 2) if lt else None
    ant['alcance'] = int(total['alcance'] * 0.88)
    ant['ctr_link'] = round(total['ctr_link'] * 0.93, 2)
    ant['cpm'] = round(total['cpm'] * 1.04, 2)
    ant['frequencia'] = round(total['frequencia'] * 0.95, 2)

    videos = sorted([a for a in ads if a.get('video')], key=lambda a: -a['gasto'])[:12]

    fadiga = []
    for a in sorted(ads, key=lambda a: -a['gasto'])[:5]:
        serie, freq = [], 1.0
        for d in range(min(dias, 30)):
            freq += a['frequencia'] / max(min(dias, 30), 1) * rnd.uniform(0.7, 1.3)
            ctr = a['ctr_link'] * (1.25 - 0.4 * d / max(min(dias, 30), 1)) * rnd.uniform(0.9, 1.1)
            serie.append({'data': (ini + timedelta(days=d)).isoformat(), 'gasto': round(a['gasto'] / dias, 2),
                          'frequencia': round(freq, 2), 'ctr_link': round(ctr, 2),
                          'cpl': round((a['cpl'] or 20) * (0.85 + 0.35 * d / max(min(dias, 30), 1)), 2),
                          'leads': rnd.randint(0, 3)})
        fadiga.append({'id': a['id'], 'nome': a['nome'], 'dias': serie})

    def q(gasto_frac, leads_frac, cpl_fator=1.0):
        g = round(total['gasto'] * gasto_frac, 2)
        lds = max(0, int(total['leads']['total'] * leads_frac))
        imp = int(total['impressoes'] * gasto_frac)
        cli = int(total['cliques'] * gasto_frac * rnd.uniform(0.85, 1.15))
        return {'gasto': g, 'impressoes': imp, 'alcance': int(total['alcance'] * gasto_frac), 'cliques': cli,
                'ctr_link': round(cli / imp * 100, 2) if imp else 0, 'leads': lds,
                'cpl': round(g / lds, 2) if lds else None}

    idade_genero = []
    for fx, pg, pl in (('18-24', .05, .03), ('25-34', .27, .29), ('35-44', .37, .42),
                       ('45-54', .22, .20), ('55-64', .07, .05), ('65+', .02, .01)):
        for gen, pgg in (('female', 0.94), ('male', 0.05), ('unknown', 0.01)):
            idade_genero.append({'idade': fx, 'genero': gen, **q(pg * pgg, pl * pgg)})
    regioes = [{'regiao': r, **q(p, p * rnd.uniform(0.9, 1.1))}
               for r, p in (('Sao Paulo', 0.985), ('Rio de Janeiro', 0.008), ('Minas Gerais', 0.007))]
    posic = [{'plataforma': pl, 'posicao': ps, **q(gp, lp)} for pl, ps, gp, lp in (
        ('instagram', 'reels', .41, .49), ('instagram', 'feed', .24, .22), ('instagram', 'story', .19, .18),
        ('facebook', 'feed', .09, .07), ('facebook', 'facebook_reels', .05, .03), ('instagram', 'instagram_explore', .02, .01))]
    aparelhos = [{'aparelho': ap, **q(gp, lp)} for ap, gp, lp in (
        ('iphone', .58, .61), ('android_smartphone', .38, .36), ('desktop', .03, .02), ('ipad', .01, .01))]
    horas = []
    curva_h = [.2, .1, .05, .03, .03, .08, .35, .7, .95, 1.1, 1.15, 1.2, 1.35, 1.25, 1.1, 1.05, 1.0, 1.05,
               1.2, 1.45, 1.6, 1.5, 1.05, .55]
    soma_h = sum(curva_h)
    for h, w in enumerate(curva_h):
        eff = 1.25 if h in (12, 19, 20, 21) else (0.7 if h < 7 else 1.0)
        horas.append({'hora': h, **q(w / soma_h, w / soma_h * eff * 0.97)})
    semana = []
    for k, nome in enumerate(meta.DIAS_SEMANA):
        g = sum(d['gasto'] for d in diario if date.fromisoformat(d['data']).weekday() == k)
        l = sum(d['leads']['total'] for d in diario if date.fromisoformat(d['data']).weekday() == k)
        semana.append({'dia': nome, 'gasto': round(g, 2), 'leads': l, 'cpl': round(g / l, 2) if l else None})

    return {'ok': True,
            'periodo': {'inicio': ini.isoformat(), 'fim': fim.isoformat(),
                        'inicio_anterior': ini_a.isoformat(), 'fim_anterior': fim_a.isoformat()},
            'total': total, 'anterior': ant, 'diario': diario, 'campanhas': campanhas,
            'conjuntos': conjuntos, 'anuncios': ads, 'videos': videos, 'fadiga': fadiga,
            'publico': {'idade_genero': idade_genero, 'regioes': regioes, 'posicionamentos': posic,
                        'aparelhos': aparelhos, 'horas': horas, 'semana': semana}}


def _instagram_bloco(periodo, rnd):
    ini, fim, _, _ = meta.intervalo(periodo)
    dias = (fim - ini).days + 1
    posts = []
    n = max(3, int(dias / 2.2))
    for k in range(n):
        formato, legenda, tmed = POSTS[k % len(POSTS)]
        dia = fim - timedelta(days=int(k * dias / n))
        base = {'Reels': 6800, 'Carrossel': 2300, 'Imagem': 1200}[formato]
        alc = int(base * rnd.uniform(0.45, 2.1))
        inter = int(alc * rnd.uniform(0.05, 0.11))
        posts.append({'data': dia.isoformat(), 'formato': formato, 'link': '#', 'miniatura': '',
                      'legenda': legenda, 'curtidas': int(inter * 0.78),
                      'comentarios': int(inter * rnd.uniform(0.04, 0.12)), 'alcance': alc,
                      'salvos': int(alc * rnd.uniform(0.006, 0.03)),
                      'compartilhamentos': int(alc * rnd.uniform(0.003, 0.02)),
                      'interacoes': inter, 'visualizacoes': int(alc * 1.7) if formato == 'Reels' else None,
                      'tempo_medio': round(tmed * rnd.uniform(0.85, 1.15), 1) if tmed else None,
                      'tempo_total_h': round(alc * 1.7 * (tmed or 0) / 3600, 1) if tmed else None,
                      'visitas_perfil': int(alc * rnd.uniform(0.01, 0.03)),
                      'seguiu': int(alc * rnd.uniform(0.001, 0.006)),
                      'taxa_engajamento': round(inter / alc * 100, 2)})
    reach = int(sum(p['alcance'] for p in posts) * 1.7)
    m = {'reach': reach, 'views': int(reach * 3.1), 'accounts_engaged': int(reach * 0.072),
         'total_interactions': sum(p['interacoes'] for p in posts),
         'profile_views': int(reach * 0.05), 'website_clicks': int(reach * 0.007),
         'follows_and_unfollows': int(dias * 9.5), 'profile_links_taps': int(reach * 0.009)}
    return {'ok': True,
            'perfil': {'usuario': 'dra.alinealbuquerque', 'nome': 'Aline | Harmonizacao Facial em Santos',
                       'bio': 'Trato o derretimento facial da perda de peso. Esp. em harmonizacao para o emagrecimento. '
                              'Criadora do Metodo Fenix.',
                       'site': 'wa.me/5513988171698', 'seguidores': 9931, 'seguindo': 1511, 'posts': 377, 'foto': ''},
            'metricas': m, 'anteriores': {k: int(v * rnd.uniform(0.78, 0.95)) for k, v in m.items()},
            'seguidores_dia': [{'data': (ini + timedelta(days=d)).isoformat(), 'novos': int(rnd.uniform(4, 17))}
                               for d in range(min(dias, 30))],
            'posts': posts}


def _atendimento_bloco(periodo, ads, rnd):
    ini, fim, _, _ = meta.intervalo(periodo)
    dias = (fim - ini).days + 1
    conv = int(ads['total']['leads']['total'] * 1.22)   # anuncio + organico
    qual = int(conv * 0.47)
    ag = int(conv * 0.31)
    comp = int(ag * 0.68)
    fech = int(comp * 0.36)
    fat = round(sum(rnd.choice([1500, 1900, 2400, 2800, 3200, 4500]) for _ in range(fech)), 2)
    por_ad = []
    for a in sorted(ads['anuncios'], key=lambda x: -(x['leads']['total']))[:8]:
        c = a['leads']['total']
        agd = int(c * rnd.uniform(0.12, 0.3))
        fc = int(agd * rnd.uniform(0.25, 0.45))
        por_ad.append({'ad_id': a['id'], 'conversas': c, 'agendados': agd, 'fecharam': fc,
                       'faturamento': round(fc * rnd.uniform(2400, 3600), 2)})
    return {'ok': True, 'contatos_novos': conv,
            'por_origem': [{'origem': o, 'total': int(conv * p)} for o, p in (
                ('anuncio', .58), ('comentario', .17), ('dm', .13), ('story', .08), ('formulario', .04))],
            'por_etapa': [{'etapa': e, 'total': t} for e, t in (
                ('Novo', conv), ('Conversando', int(conv * .72)), ('Qualificado', qual),
                ('Agendou avaliacao', ag), ('Compareceu', comp), ('Fechou', fech), ('Perdido', int(conv * .18)))],
            'funil': {'conversas': conv, 'qualificados': qual, 'agendados': ag, 'compareceram': comp,
                      'fecharam': fech, 'faturamento': fat},
            'por_anuncio': por_ad,
            'automacoes': [{'nome': n, 'disparos': int(conv * p), 'qualificados': int(conv * p * q)} for n, p, q in (
                ('Comentou FENIX no reels', .21, .52), ('Boas-vindas do anuncio', .55, .41),
                ('Mencao em story', .07, .33), ('Palavra VALOR no Direct', .09, .38))],
            'tempo_primeira_resposta_min': 6.4,
            'diario': [{'data': (ini + timedelta(days=d)).isoformat(), 'novos': max(0, int(conv / dias * rnd.uniform(.6, 1.4)))}
                       for d in range(dias)]}


def gerar():
    rnd = random.Random(7)
    periodos = {}
    for p, rot in meta.PERIODOS.items():
        a = _anuncios_bloco(p, rnd)
        periodos[p] = {'rotulo': rot, 'anuncios': a, 'instagram': _instagram_bloco(p, rnd),
                       'atendimento': _atendimento_bloco(p, a, rnd)}
    hoje = date.today()
    nomes = ['Juliana S.', 'Patricia M.', 'Fernanda O.', 'Camila R.', 'Renata C.', 'Bianca L.',
             'Tatiane F.', 'Priscila A.', 'Daniela B.', 'Simone G.', 'Larissa P.', 'Vanessa T.']
    queixas = ['Flacidez no rosto depois de emagrecer', 'Bigode chines', 'Olheira funda', 'Contorno do rosto']
    leads = [{'data': f"{(hoje - timedelta(days=k // 3)).isoformat()} {9 + (k * 5) % 11:02d}:{(k * 17) % 60:02d}",
              'formulario': 'Avaliacao Metodo Fenix', 'campanha': '[TESTE] Full face 40+ - formulario',
              'anuncio': 'Imagem - full face 40+',
              'campos': {'full_name': nomes[k % len(nomes)],
                         'phone_number': f'+55 13 9{rnd.randint(1000, 9999)}-{rnd.randint(1000, 9999)}',
                         'o_que_mais_te_incomoda?': queixas[k % len(queixas)]}} for k in range(10)]
    return {'demo': True,
            'pagina': {'ok': True, 'nome': 'Dra. Aline Albuquerque', 'curtidas': 1240, 'seguidores': 1388, 'link': '#'},
            'leads_formulario': {'ok': True, 'formularios': [{'nome': 'Avaliacao Metodo Fenix', 'status': 'ACTIVE',
                                                              'total': 47}], 'leads': leads},
            'publico_instagram': {'ok': True,
                                  'cidades': [{'chave': c, 'valor': v} for c, v in (
                                      ('Santos, Sao Paulo', 3410), ('Sao Vicente, Sao Paulo', 1180),
                                      ('Guaruja, Sao Paulo', 760), ('Praia Grande, Sao Paulo', 690),
                                      ('Sao Paulo, Sao Paulo', 640), ('Cubatao, Sao Paulo', 210),
                                      ('Bertioga, Sao Paulo', 120))],
                                  'idade': [{'chave': k, 'valor': v} for k, v in (
                                      ('18-24', 610), ('25-34', 2890), ('35-44', 3720), ('45-54', 1820),
                                      ('55-64', 640), ('65+', 250))],
                                  'genero': [{'chave': 'F', 'valor': 8830}, {'chave': 'M', 'valor': 1101}],
                                  'online': [{'hora': h, 'seguidores': int(2100 + 2400 * (
                                      1 if h in (12, 13, 19, 20, 21) else 0.6 if 8 <= h <= 22 else 0.15))} for h in range(24)]},
            'periodos': periodos,
            'metas': {'cpl_alvo': 18.0, 'orcamento_mensal': 3600.0}}
