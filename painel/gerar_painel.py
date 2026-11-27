"""
Gera o painel de marketing da Dra. Aline Albuquerque.

  python painel/gerar_painel.py            puxa tudo da Meta + central de atendimento
  python painel/gerar_painel.py --demo     numeros ficticios (para mostrar antes do acesso)
  python painel/gerar_painel.py --abrir    gera e abre no navegador
  python painel/gerar_painel.py --resumo   imprime o resumo dos ultimos 7 dias (texto para WhatsApp)
  python painel/gerar_painel.py --testar   mostra o que o token enxerga

Saida: painel/saida/painel.html (arquivo unico) e painel/saida/dados.json.
"""
import argparse
import json
import os
import sys
import webbrowser
from datetime import date, datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, 'INTEGRACOES'))
sys.path.insert(0, os.path.join(RAIZ, 'atendimento'))
sys.path.insert(0, AQUI)

import meta_api as meta  # noqa: E402

SAIDA = os.path.join(AQUI, 'saida')
TEMPLATE = os.path.join(AQUI, 'template.html')

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def _json(nome):
    p = os.path.join(RAIZ, 'config', nome)
    if not os.path.exists(p):
        return {}
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _var(atual, anterior):
    a, b = _num(atual), _num(anterior)
    if a is None or not b:
        return None
    return round((a - b) / b * 100, 1)


def brl(v):
    if v is None:
        return '-'
    return 'R$ ' + f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


# ============================================================
# COMERCIAL: anuncio -> conversa -> avaliacao -> fechamento
# ============================================================

def comercial(ads, atend, bm):
    """Junta o gasto da Meta com o que aconteceu na central de atendimento."""
    if not ads.get('ok'):
        return {'ok': False, 'erro': 'sem dados de anuncio'}
    t = ads['total']
    out = {'ok': True, 'gasto': t['gasto'], 'conversas_meta': t['leads']['total'],
           'conversas_profundas': t['leads']['conversas_profundas'], 'tem_atendimento': False}
    if atend and atend.get('ok'):
        f = atend['funil']
        out.update({'tem_atendimento': True, **f})
        g = t['gasto']
        out['custo_agendamento'] = round(g / f['agendados'], 2) if f.get('agendados') else None
        out['custo_paciente'] = round(g / f['fecharam'], 2) if f.get('fecharam') else None
        out['roas'] = round(f['faturamento'] / g, 2) if g and f.get('faturamento') else None
        out['ticket_medio'] = round(f['faturamento'] / f['fecharam'], 2) if f.get('fecharam') else None
        out['lucro_bruto'] = round(f['faturamento'] - g, 2) if f.get('faturamento') else None
        base = f.get('conversas') or t['leads']['total']
        out['taxas'] = {
            'conversa_agendamento': round(f['agendados'] / base * 100, 1) if base else None,
            'comparecimento': round(f['compareceram'] / f['agendados'] * 100, 1) if f.get('agendados') else None,
            'fechamento': round(f['fecharam'] / f['compareceram'] * 100, 1) if f.get('compareceram') else None,
        }
    else:
        # sem central: projeta pelo benchmark para mostrar o potencial
        tk = bm.get('ticket_medio') or 0
        conv = t['leads']['total']
        ag = conv * (bm.get('conversa_agendamento', {}).get('bom', 25) / 100)
        comp = ag * (bm.get('comparecimento', {}).get('bom', 75) / 100)
        fech = comp * (bm.get('fechamento', {}).get('bom', 45) / 100)
        out['projecao'] = {'agendados': round(ag), 'compareceram': round(comp), 'fecharam': round(fech),
                           'faturamento': round(fech * tk, 2),
                           'roas': round(fech * tk / t['gasto'], 1) if t['gasto'] else None}
    return out


# ============================================================
# NOTA DE SAUDE + RECOMENDACOES
# ============================================================

def _faixa(valor, ref):
    """0 (ruim) .. 1 (bom) comparando com a faixa do benchmark."""
    if valor is None or not ref:
        return None
    bom, ruim = ref['bom'], ref['ruim']
    if ref.get('menor_melhor'):
        if valor <= bom:
            return 1.0
        if valor >= ruim:
            return 0.0
        return (ruim - valor) / (ruim - bom)
    if valor >= bom:
        return 1.0
    if valor <= ruim:
        return 0.0
    return (valor - ruim) / (bom - ruim)


def nota_saude(ads, com, bm):
    if not ads.get('ok') or not ads['total']['gasto']:
        return None
    t = ads['total']
    v = t.get('video') or {}
    itens = [
        ('Custo por conversa', _faixa(t['cpl'], bm.get('custo_conversa')), 3),
        ('Taxa de clique', _faixa(t['ctr_link'], bm.get('ctr_link')), 1.5),
        ('Custo de alcance (CPM)', _faixa(t['cpm'], bm.get('cpm')), 1),
        ('Frequencia', _faixa(t['frequencia'], bm.get('frequencia_max')), 1),
        ('Gancho dos videos', _faixa(v.get('gancho'), bm.get('gancho')), 1.5),
        ('Retencao dos videos', _faixa(v.get('retencao'), bm.get('retencao')), 1),
    ]
    tot_l = t['leads']['total']
    if tot_l:
        itens.append(('Qualidade das conversas',
                      _faixa(t['leads']['conversas_profundas'] / tot_l * 100 if t['leads']['conversas'] else None,
                             bm.get('conversa_profunda')), 1.5))
    if com.get('tem_atendimento'):
        tx = com.get('taxas', {})
        itens += [('Conversa -> avaliacao', _faixa(tx.get('conversa_agendamento'), bm.get('conversa_agendamento')), 2),
                  ('Comparecimento', _faixa(tx.get('comparecimento'), bm.get('comparecimento')), 1),
                  ('Fechamento', _faixa(tx.get('fechamento'), bm.get('fechamento')), 2),
                  ('Retorno (ROAS)', _faixa(com.get('roas'), bm.get('roas')), 3)]
    validos = [(n, s, p) for n, s, p in itens if s is not None]
    if not validos:
        return None
    nota = round(sum(s * p for _, s, p in validos) / sum(p for _, _, p in validos) * 100)
    return {'nota': nota, 'itens': [{'nome': n, 'nota': round(s * 100)} for n, s, _ in validos]}


def recomendacoes(ads, ig, com, metas, bm, periodo):
    """Lista do que fazer, em ordem de prioridade. Cada item: nivel, area, titulo, texto, comando."""
    out = []

    def add(nivel, area, titulo, texto, comando=None):
        out.append({'nivel': nivel, 'area': area, 'titulo': titulo, 'texto': texto, 'comando': comando})

    alvo = metas.get('cpl_alvo') or (bm.get('custo_conversa') or {}).get('bom')
    if ads.get('ok'):
        t, ant = ads['total'], ads['anterior']
        cpl = t['cpl']
        if cpl and alvo and cpl > alvo * 1.2:
            add('atencao', 'Custo', f'Conversa a {brl(cpl)}, acima da meta de {brl(alvo)}',
                'Antes de aumentar verba, troque os anuncios com pior custo (lista abaixo) e teste novos ganchos.')
        v = _var(cpl, ant['cpl'])
        if v is not None and v >= 25:
            add('atencao', 'Custo', f'Custo por conversa subiu {v:.0f}%',
                'Normalmente e cansaco de criativo (frequencia alta) ou publico saturado. Veja a secao de fadiga.')
        elif v is not None and v <= -15:
            add('bom', 'Custo', f'Custo por conversa caiu {abs(v):.0f}%', 'O que mudou neste periodo esta funcionando: manter.')

        # anuncios
        for a in ads['anuncios']:
            if a['status'] != 'ACTIVE':
                continue
            ref = alvo or (cpl or 30)
            if a['gasto'] >= 2 * ref and a['leads']['total'] == 0:
                add('critico', 'Anuncio', f'Pausar "{a["nome"]}"',
                    f'Gastou {brl(a["gasto"])} e nao trouxe nenhuma conversa.',
                    f'python trafego/painel.py pausar {a["id"]} --confirmo')
            elif a['cpl'] and a['cpl'] > 1.6 * ref and a['gasto'] >= 3 * ref:
                add('atencao', 'Anuncio', f'Pausar "{a["nome"]}"',
                    f'Conversa a {brl(a["cpl"])}, {a["cpl"] / ref:.1f}x a meta.',
                    f'python trafego/painel.py pausar {a["id"]} --confirmo')
            vd = a.get('video')
            if vd and a['impressoes'] >= 1500:
                g = vd.get('gancho')
                if g is not None and g < bm.get('gancho', {}).get('ruim', 21):
                    add('atencao', 'Criativo', f'Gancho fraco em "{a["nome"]}" ({g:.0f}%)',
                        'Pouca gente para nos 3 primeiros segundos. Regrave so o inicio com um gancho que quebra '
                        'crenca ("encher o rosto depois de emagrecer pode deixar artificial") ou com ela apontando '
                        'no proprio rosto onde o volume esvazia. Sem antes/depois lado a lado (proibido pela Meta).')
                r = vd.get('retencao')
                if g and g >= bm.get('gancho', {}).get('bom', 30) and r is not None and r < bm.get('retencao', {}).get('ruim', 27):
                    add('atencao', 'Criativo', f'"{a["nome"]}" prende no inicio mas perde no meio',
                        f'Gancho bom ({g:.0f}%) e so {r:.0f}% assistem ate o fim. Corte o video para 15-25s e '
                        'mostre o resultado mais cedo.')
            rk = a.get('ranking') or {}
            if rk.get('quality', '').startswith('BELOW') and a['impressoes'] >= 2000:
                add('atencao', 'Criativo', f'Meta classifica "{a["nome"]}" abaixo da media em qualidade',
                    'Anuncio com cara de anuncio ou texto exagerado. Prefira video nativo, dela falando para a camera.')
            if a['frequencia'] >= bm.get('frequencia_max', {}).get('ruim', 3.5):
                add('atencao', 'Fadiga', f'"{a["nome"]}" com frequencia {a["frequencia"]:.1f}',
                    'O mesmo publico ja viu demais. Suba um criativo novo neste conjunto.')

        # conjuntos
        teto = _num(os.getenv('TETO_DIARIO_REAIS')) or 9999
        for cj in ads.get('conjuntos', []):
            if cj['status'] != 'ACTIVE':
                continue
            if cj['aprendizado'] == 'Aprendizado limitado':
                add('atencao', 'Conjunto', f'"{cj["nome"]}" em aprendizado limitado',
                    'Poucas conversas por semana para a Meta aprender. Junte conjuntos parecidos ou aumente a verba.')
            if (cj['orcamento_diario'] and cj['leads']['total'] >= 5 and cj['cpl'] and alvo
                    and cj['cpl'] <= 0.75 * alvo):
                novo = min(round(cj['orcamento_diario'] * 1.2, 2), teto)
                if novo > cj['orcamento_diario']:
                    add('bom', 'Escala', f'Escalar "{cj["nome"]}"',
                        f'{cj["leads"]["total"]} conversas a {brl(cj["cpl"])}. Subir de {brl(cj["orcamento_diario"])} '
                        f'para {brl(novo)}/dia (+20%, o maximo seguro de uma vez).',
                        f'python trafego/painel.py orcamento {cj["id"]} {novo} --confirmo')

        # publico, horario, posicionamento
        pub = ads['publico']
        fx = {}
        for l in pub['idade_genero']:
            d = fx.setdefault(l['idade'], {'gasto': 0, 'leads': 0})
            d['gasto'] += l['gasto']
            d['leads'] += l['leads']
        faixas = [(k, d['gasto'] / d['leads']) for k, d in fx.items() if d['leads'] >= 3]
        if len(faixas) >= 2 and cpl:
            k_m, c_m = min(faixas, key=lambda x: x[1])
            k_p, c_p = max(faixas, key=lambda x: x[1])
            if c_p >= 1.8 * c_m:
                add('info', 'Publico', f'{k_m} anos e a faixa mais barata ({brl(c_m)})',
                    f'{k_p} anos sai {c_p / c_m:.1f}x mais caro ({brl(c_p)}). Vale criativo especifico para a faixa barata '
                    'ou limitar a idade no conjunto.')
        pos = [p for p in pub['posicionamentos'] if p['leads'] >= 2]
        if len(pos) >= 2:
            m = min(pos, key=lambda p: p['cpl'] or 9e9)
            add('info', 'Posicionamento', f'Onde a conversa sai mais barata: {m["plataforma"]} {m["posicao"]}',
                f'{m["leads"]} conversas a {brl(m["cpl"])}. Faca criativos pensados para esse formato.')
        hs = [h for h in pub['horas'] if h['leads'] >= 2]
        if len(hs) >= 4:
            melhores = sorted(hs, key=lambda h: h['cpl'] or 9e9)[:3]
            add('info', 'Horario', 'Horarios com conversa mais barata: ' +
                ', '.join(f"{h['hora']:02d}h" for h in sorted(melhores, key=lambda h: h['hora'])),
                'Garanta alguem respondendo o Direct e o WhatsApp nesses horarios: lead respondido em 5 minutos '
                'agenda muito mais.')
        tl = t['leads']
        if tl['conversas'] >= 10:
            prof = tl['conversas_profundas'] / tl['conversas'] * 100
            if prof < bm.get('conversa_profunda', {}).get('ruim', 35):
                add('atencao', 'Conversas', f'So {prof:.0f}% das conversas passam da primeira mensagem',
                    'Muita gente clica e some. Ajuste a mensagem de boas-vindas do WhatsApp com uma pergunta simples '
                    '("o que mais te incomoda hoje no rosto?") e responda rapido.')
            if tl['bloqueios'] >= 3:
                add('atencao', 'Conversas', f'{tl["bloqueios"]} pessoas bloquearam a conversa',
                    'Sinal de abordagem insistente ou publico errado. Revise o roteiro de atendimento.')
        orc = metas.get('orcamento_mensal')
        if orc and periodo in ('mes',) and t['gasto'] > orc:
            add('atencao', 'Verba', 'Investimento passou do orcamento do mes',
                f'{brl(t["gasto"])} de {brl(orc)}.')

    if com.get('tem_atendimento'):
        tx = com.get('taxas', {})
        ca = tx.get('conversa_agendamento')
        if ca is not None and ca < bm.get('conversa_agendamento', {}).get('ruim', 10):
            add('critico', 'Comercial', f'So {ca:.0f}% das conversas viram avaliacao',
                'O anuncio esta trazendo gente, o gargalo e o atendimento. Revise tempo de resposta, roteiro e '
                'a oferta de avaliacao.')
        cp = tx.get('comparecimento')
        if cp is not None and cp < bm.get('comparecimento', {}).get('ruim', 55):
            add('atencao', 'Comercial', f'Comparecimento de {cp:.0f}%',
                'Confirme a avaliacao na vespera e 2h antes, e mande a localizacao.')
        fe = tx.get('fechamento')
        if fe is not None and fe < bm.get('fechamento', {}).get('ruim', 25):
            add('atencao', 'Comercial', f'Fechamento de {fe:.0f}% nas avaliacoes',
                'Paciente chega mas nao fecha: na consulta, mostre o plano do Metodo Fenix em etapas, casos '
                'parecidos (com consentimento) e as condicoes de pagamento.')
        if com.get('custo_paciente') and bm.get('ticket_medio'):
            tk = com.get('ticket_medio') or bm['ticket_medio']
            pct = com['custo_paciente'] / tk * 100
            lim = bm.get('custo_paciente_max_pct_ticket', 30)
            if pct > lim:
                add('atencao', 'Resultado', f'Cada paciente custou {pct:.0f}% do ticket em anuncio',
                    f'{brl(com["custo_paciente"])} por paciente para ticket de {brl(tk)}. O saudavel e ficar abaixo '
                    f'de {lim}%.')
        if com.get('roas'):
            add('bom' if com['roas'] >= bm.get('roas', {}).get('bom', 5) else 'info', 'Resultado',
                f'Cada R$ 1 em anuncio voltou R$ {com["roas"]:.2f}'.replace('.', ','),
                f'Faturamento atribuido {brl(com.get("faturamento"))} para {brl(com["gasto"])} investidos.')

    if ig.get('ok') and ig['posts']:
        reels = [p for p in ig['posts'] if p['formato'] == 'Reels' and p.get('alcance')]
        if reels:
            top = max(reels, key=lambda p: p['alcance'])
            add('info', 'Organico', 'Reels campeao pode virar anuncio',
                f'"{top["legenda"][:70]}..." alcancou {int(top["alcance"]):,} pessoas no organico. '
                'Conteudo que performa organico costuma baratear o anuncio.'.replace(',', '.'))

    ordem = {'critico': 0, 'atencao': 1, 'bom': 2, 'info': 3}
    out.sort(key=lambda x: ordem[x['nivel']])
    return out


# ============================================================
# COLETA
# ============================================================

def _atendimento(periodo):
    try:
        import exportar
    except Exception:
        return None
    ini, fim, _, _ = meta.intervalo(periodo)
    try:
        return exportar.resumo(ini, fim)
    except Exception as e:
        return {'ok': False, 'erro': str(e)}


def _metas():
    return {'cpl_alvo': _num(meta.cfg('META_CPL_ALVO')),
            'orcamento_mensal': _num(meta.cfg('META_ORCAMENTO_MENSAL'))}


def coletar():
    meta.carregar_env()
    pag = meta.pagina()
    leads = meta.leads_formulario()
    pub_ig = meta.publico_instagram()
    periodos = {}
    for p in meta.PERIODOS:
        print(f'  puxando {meta.PERIODOS[p].lower()}...')
        periodos[p] = {'rotulo': meta.PERIODOS[p], 'anuncios': meta.anuncios(p),
                       'instagram': meta.instagram(p), 'atendimento': _atendimento(p)}
    return {'demo': False, 'pagina': pag, 'leads_formulario': leads, 'publico_instagram': pub_ig,
            'periodos': periodos, 'metas': _metas()}


def analisar(dados):
    bm = _json('benchmarks.json')
    dados['benchmarks'] = bm
    for chave, p in dados['periodos'].items():
        com = comercial(p['anuncios'], p.get('atendimento'), bm)
        p['comercial'] = com
        p['saude'] = nota_saude(p['anuncios'], com, bm)
        p['recomendacoes'] = recomendacoes(p['anuncios'], p['instagram'], com, dados['metas'], bm, chave)
    return dados


def montar(dados):
    marca = _json('marca.json')
    dados['marca'] = marca
    dados['clinica'] = marca.get('nome') or 'Dra. Aline Albuquerque'
    dados['gerado_em'] = datetime.now().strftime('%d/%m/%Y %H:%M')
    os.makedirs(SAIDA, exist_ok=True)
    with open(os.path.join(SAIDA, 'dados.json'), 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    html = open(TEMPLATE, encoding='utf-8').read()
    carga = json.dumps(dados, ensure_ascii=False).replace('</', '<\\/')
    html = html.replace('/*__DADOS__*/null', carga)
    destino = os.path.join(SAIDA, 'painel.html')
    with open(destino, 'w', encoding='utf-8') as f:
        f.write(html)
    return destino


# ============================================================
# RESUMO EM TEXTO (WhatsApp)
# ============================================================

def resumo_texto(dados, periodo='7d'):
    p = dados['periodos'][periodo]
    a, c = p['anuncios'], p['comercial']
    linhas = [f"*{dados['clinica']}* - {p['rotulo'].lower()}"]
    if a.get('ok'):
        t = a['total']
        linhas += ['', '*Anuncios*', f"Investido: {brl(t['gasto'])}",
                   f"Conversas: {t['leads']['total']} (custo {brl(t['cpl'])})",
                   f"Conversas reais (2+ mensagens): {t['leads']['conversas_profundas']}",
                   f"Alcance: {t['alcance']:,}".replace(',', '.')]
        if c.get('tem_atendimento'):
            linhas += [f"Avaliacoes agendadas: {c.get('agendados', 0)}",
                       f"Fecharam: {c.get('fecharam', 0)} | Faturamento: {brl(c.get('faturamento'))}",
                       f"Retorno: {c.get('roas') or '-'}x"]
        if a.get('videos'):
            v = max(a['videos'], key=lambda x: (x['leads']['total'], -(x['cpl'] or 0)))
            linhas.append(f"Video campeao: {v['nome']} ({v['leads']['total']} conversas)")
    if p.get('saude'):
        linhas.append(f"Nota de saude da conta: {p['saude']['nota']}/100")
    recs = [r for r in p['recomendacoes'] if r['nivel'] in ('critico', 'atencao')][:4]
    if recs:
        linhas += ['', '*O que fazer*'] + [f"- {r['titulo']}" for r in recs]
    return '\n'.join(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo', action='store_true')
    ap.add_argument('--abrir', action='store_true')
    ap.add_argument('--resumo', action='store_true')
    ap.add_argument('--testar', action='store_true')
    args = ap.parse_args()

    if args.testar:
        meta.carregar_env()
        print(json.dumps(meta.diagnostico(), ensure_ascii=False, indent=2))
        return

    if args.demo:
        import demo
        dados = demo.gerar()
    else:
        print('Puxando dados da Meta...')
        dados = coletar()
    analisar(dados)
    destino = montar(dados)
    print(f'Painel gerado: {destino}')
    if args.resumo:
        print()
        print(resumo_texto(dados))
    if args.abrir:
        webbrowser.open('file:///' + destino.replace('\\', '/'))


if __name__ == '__main__':
    main()
