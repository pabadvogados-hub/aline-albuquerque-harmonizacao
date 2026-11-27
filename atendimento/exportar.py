"""
Resumo da central de atendimento para o painel de relatorio.

  python atendimento/exportar.py --dias 30
  python atendimento/exportar.py --inicio 2026-11-01 --fim 2026-11-26

Uso no painel:
  sys.path.insert(0, 'atendimento'); import exportar; exportar.resumo(inicio, fim)

Regras de contagem:
  - contatos_novos / por_origem / diario: contatos criados no periodo
  - por_etapa: quem ENTROU em cada etapa no periodo (etapas_historico), na ordem do funil
  - funil: quem entrou no periodo numa etapa igual ou mais adiante (Fechou conta tambem
    como Compareceu, Agendou e Qualificado); faturamento = valor de quem fechou no periodo
  - por_anuncio / automacoes: contatos criados no periodo, com o desfecho que tiverem hoje
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ajustes import ARQ_DB, automacoes, funil  # noqa: E402


def _conectar():
    """Conexao so de leitura, fechada no fim do with."""
    import sqlite3
    from contextlib import closing
    c = sqlite3.connect(ARQ_DB, timeout=30)
    c.row_factory = sqlite3.Row
    return closing(c)


def _idx_etapas():
    f = funil()
    # posicoes das etapas-chave pelo nome (cai para a posicao padrao se o nome mudar)
    def pos(nomes, padrao):
        for i, e in enumerate(f):
            if any(n in e.lower() for n in nomes):
                return i
        return padrao
    return {'qualificado': pos(['qualific'], 2), 'agendou': pos(['agend'], 3),
            'compareceu': pos(['compare'], 4), 'fechou': pos(['fech'], 5),
            'perdido': pos(['perd'], len(f) - 1)}


def _minutos(a, b):
    try:
        da = datetime.strptime(a, '%Y-%m-%d %H:%M:%S')
        dbb = datetime.strptime(b, '%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        return None
    return (dbb - da).total_seconds() / 60


def resumo(inicio, fim):
    if not os.path.exists(ARQ_DB):
        return {'ok': False, 'erro': f'banco da central nao encontrado ({ARQ_DB}). A central ainda nao rodou.'}
    ini = f'{inicio.isoformat()} 00:00:00'
    fi = f'{fim.isoformat()} 23:59:59'
    f = funil()
    ix = _idx_etapas()
    nomes_aut = {}
    try:
        nomes_aut = {a['id']: a.get('nome', a['id']) for a in automacoes().get('automacoes', [])}
    except (OSError, ValueError):
        pass

    with _conectar() as c:
        novos = c.execute('SELECT * FROM contatos WHERE criado_em BETWEEN ? AND ?', (ini, fi)).fetchall()
        hist = c.execute('SELECT contato_id, etapa, quando FROM etapas_historico WHERE quando BETWEEN ? AND ?',
                         (ini, fi)).fetchall()
        valores = {r['id']: (r['valor_fechado'] or 0) for r in c.execute('SELECT id, valor_fechado FROM contatos')}
        max_hist = {}
        for r in c.execute('SELECT contato_id, etapa FROM etapas_historico'):
            if r['etapa'] in f and f.index(r['etapa']) != ix['perdido']:
                max_hist[r['contato_id']] = max(max_hist.get(r['contato_id'], 0), f.index(r['etapa']))
        disparos = {r['automacao']: r['n'] for r in c.execute(
            'SELECT automacao, COUNT(*) n FROM eventos WHERE automacao IS NOT NULL AND quando BETWEEN ? AND ? '
            'GROUP BY automacao', (ini, fi))}
        primeiras = c.execute(
            "SELECT m.contato_id, MIN(CASE WHEN m.direcao='entrada' THEN m.quando END) ent "
            "FROM mensagens m JOIN contatos k ON k.id=m.contato_id WHERE k.criado_em BETWEEN ? AND ? "
            "GROUP BY m.contato_id", (ini, fi)).fetchall()
        tempos = []
        for p in primeiras:
            if not p['ent']:
                continue
            s = c.execute("SELECT MIN(quando) q FROM mensagens WHERE contato_id=? AND direcao='saida' AND quando>=?",
                          (p['contato_id'], p['ent'])).fetchone()
            if s and s['q']:
                m = _minutos(p['ent'], s['q'])
                if m is not None:
                    tempos.append(m)

    # por origem
    orig = {}
    for r in novos:
        orig[r['origem'] or 'dm'] = orig.get(r['origem'] or 'dm', 0) + 1

    # por etapa (quem entrou no periodo)
    entrou = {e: set() for e in f}
    for h in hist:
        if h['etapa'] in entrou:
            entrou[h['etapa']].add(h['contato_id'])

    # funil cumulativo: maior etapa alcancada dentro do periodo
    alcance = {}
    fechou_periodo = set()
    for h in hist:
        if h['etapa'] not in f:
            continue
        i = f.index(h['etapa'])
        if i == ix['perdido']:
            continue
        alcance[h['contato_id']] = max(alcance.get(h['contato_id'], 0), i)
        if i == ix['fechou']:
            fechou_periodo.add(h['contato_id'])
    def chegou(i):
        return sum(1 for v in alcance.values() if v >= i)

    # por anuncio
    ads = {}
    for r in novos:
        if not r['ad_id']:
            continue
        a = ads.setdefault(r['ad_id'], {'ad_id': r['ad_id'], 'conversas': 0, 'agendados': 0, 'fecharam': 0,
                                        'faturamento': 0.0})
        a['conversas'] += 1
        mx = max_hist.get(r['id'], 0)
        if mx >= ix['agendou']:
            a['agendados'] += 1
        if mx >= ix['fechou']:
            a['fecharam'] += 1
            a['faturamento'] += float(r['valor_fechado'] or 0)

    # por automacao
    auts = {}
    for r in novos:
        k = r['automacao_origem']
        if not k:
            continue
        a = auts.setdefault(k, {'nome': nomes_aut.get(k, k), 'disparos': disparos.get(k, 0), 'qualificados': 0})
        if max_hist.get(r['id'], 0) >= ix['qualificado']:
            a['qualificados'] += 1
    for k, n in disparos.items():
        if k not in auts and not k.startswith(('fluxo:', 'opcao:', 'expediente')):
            auts[k] = {'nome': nomes_aut.get(k, k), 'disparos': n, 'qualificados': 0}

    # diario
    por_dia = {}
    for r in novos:
        d = r['criado_em'][:10]
        por_dia[d] = por_dia.get(d, 0) + 1
    diario, d = [], inicio
    while d <= fim:
        diario.append({'data': d.isoformat(), 'novos': por_dia.get(d.isoformat(), 0)})
        d += timedelta(days=1)

    return {
        'ok': True,
        'contatos_novos': len(novos),
        'por_origem': sorted([{'origem': k, 'total': v} for k, v in orig.items()], key=lambda x: -x['total']),
        'por_etapa': [{'etapa': e, 'total': len(entrou[e])} for e in f],
        'funil': {'conversas': len(novos), 'qualificados': chegou(ix['qualificado']),
                  'agendados': chegou(ix['agendou']), 'compareceram': chegou(ix['compareceu']),
                  'fecharam': chegou(ix['fechou']),
                  'faturamento': round(sum(float(valores.get(i) or 0) for i in fechou_periodo), 2)},
        'por_anuncio': sorted([{**a, 'faturamento': round(a['faturamento'], 2)} for a in ads.values()],
                              key=lambda x: (-x['faturamento'], -x['conversas'])),
        'automacoes': sorted(auts.values(), key=lambda x: -x['disparos']),
        'tempo_primeira_resposta_min': round(sum(tempos) / len(tempos), 1) if tempos else None,
        'diario': diario,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dias', type=int, default=30)
    ap.add_argument('--inicio')
    ap.add_argument('--fim')
    a = ap.parse_args()
    if a.inicio and a.fim:
        ini, fim = date.fromisoformat(a.inicio), date.fromisoformat(a.fim)
    else:
        fim = date.today()
        ini = fim - timedelta(days=a.dias - 1)
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    print(json.dumps(resumo(ini, fim), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
