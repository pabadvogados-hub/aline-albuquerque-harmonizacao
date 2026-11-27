"""
Trafego da Dra. Aline Albuquerque (linha de comando) - o agente usa este arquivo para tudo.
O painel visual de relatorio e outro: painel/gerar_painel.py.

LEITURA (livre):
  python trafego/painel.py contas
  python trafego/painel.py campanhas [--ativas]
  python trafego/painel.py estrutura CAMPANHA_ID
  python trafego/painel.py relatorio [--periodo last_7d] [--nivel campaign|adset|ad] [--salvar]
  python trafego/painel.py diario [--periodo last_14d]
  python trafego/painel.py diagnostico [--periodo last_7d]
  python trafego/painel.py cidade "Santos"              (acha a key da cidade)
  python trafego/painel.py estado "Sao Paulo"
  python trafego/painel.py interesse "harmonizacao facial"
  python trafego/painel.py formularios
  python trafego/painel.py leads FORM_ID [--dias 7] [--csv]

CRIACAO (nasce tudo PAUSADO - nao gasta nada):
  python trafego/painel.py criar campanhas/plano_xxx.json

GASTA DINHEIRO (exige --confirmo, so depois do OK):
  python trafego/painel.py ativar ID --confirmo
  python trafego/painel.py pausar ID --confirmo
  python trafego/painel.py orcamento CONJUNTO_ID REAIS --confirmo
"""
import argparse
import csv
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meta  # noqa: E402

RAIZ = meta.RAIZ
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def negocio():
    p = RAIZ / 'config' / 'negocio.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}


def brl(v):
    if v is None:
        return '-'
    return f'R$ {v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def tabela(linhas, colunas):
    if not linhas:
        print('(nada no periodo)')
        return
    larg = {c: max(len(c), *(len(str(l.get(c, ''))) for l in linhas)) for c in colunas}
    larg = {c: min(w, 42) for c, w in larg.items()}
    print('  '.join(c.upper().ljust(larg[c]) for c in colunas))
    for l in linhas:
        print('  '.join(str(l.get(c, '') if l.get(c) is not None else '-')[:42].ljust(larg[c])
                        for c in colunas))


# ------------------------------------------------------------------ leitura

def cmd_contas(_):
    tabela(meta.listar_contas(), ['name', 'id', 'currency', 'account_status'])


def cmd_campanhas(a):
    camps = meta.listar_campanhas(ativas=a.ativas)
    for c in camps:
        c['orcamento'] = brl(int(c['daily_budget']) / 100) if c.get('daily_budget') else 'nos conjuntos'
    tabela(camps, ['id', 'name', 'effective_status', 'objective', 'orcamento'])


def cmd_estrutura(a):
    for cj in meta.listar_conjuntos(a.id):
        orc = brl(int(cj['daily_budget']) / 100) if cj.get('daily_budget') else '-'
        print(f"\nCONJUNTO {cj['id']}  {cj['name']}  [{cj['effective_status']}]  {orc}/dia  "
              f"{cj.get('optimization_goal')} -> {cj.get('destination_type')}")
        for ad in meta.listar_anuncios(cj['id']):
            print(f"   ANUNCIO {ad['id']}  {ad['name']}  [{ad['effective_status']}]")


def _linhas(periodo, nivel, diario=False):
    return [meta.resumo(l) for l in meta.insights(nivel=nivel, periodo=periodo, diario=diario)]


def _texto_relatorio(linhas, periodo, nivel):
    neg = negocio()
    meta_cpl = neg.get('cpl_meta')
    gasto = sum(l['gasto'] for l in linhas)
    leads = sum(l['leads'] for l in linhas)
    cpl = gasto / leads if leads else None
    out = [f'# Trafego da {neg.get("nome_curto", "Aline")} - {periodo} ({date.today():%d/%m/%Y})', '',
           f'- Investido: **{brl(gasto)}**',
           f'- Leads (WhatsApp + formulario): **{leads}**',
           f'- Custo por lead: **{brl(cpl)}**' + (f' (meta {brl(meta_cpl)})' if meta_cpl else ''), '',
           f'## Por {nivel}', '',
           '| Nome | Gasto | Leads | CPL | CTR | Freq. |', '|---|---:|---:|---:|---:|---:|']
    chave = {'campaign': 'campanha', 'adset': 'conjunto', 'ad': 'anuncio'}[nivel]
    for l in sorted(linhas, key=lambda x: -x['gasto']):
        out.append(f"| {l[chave]} | {brl(l['gasto'])} | {l['leads']} | {brl(l['cpl'])} | "
                   f"{l['ctr']}% | {l['frequencia']} |")
    return '\n'.join(out)


def cmd_relatorio(a):
    linhas = _linhas(a.periodo, a.nivel)
    txt = _texto_relatorio(linhas, a.periodo, a.nivel)
    print(txt)
    if a.salvar:
        pasta = RAIZ / 'relatorios'
        pasta.mkdir(exist_ok=True)
        arq = pasta / f'{date.today():%Y-%m-%d}_{a.periodo}_{a.nivel}.md'
        arq.write_text(txt, encoding='utf-8')
        print(f'\nSalvo em {arq}')


def cmd_diario(a):
    linhas = _linhas(a.periodo, 'account', diario=True)
    for l in linhas:
        l['cpl_fmt'] = brl(l['cpl'])
        l['gasto_fmt'] = brl(l['gasto'])
    tabela(linhas, ['dia', 'gasto_fmt', 'leads', 'cpl_fmt', 'ctr', 'cpm'])


def cmd_diagnostico(a):
    """Regras de otimizacao. So SUGERE - quem aplica e o gestor, com OK."""
    neg = negocio()
    alvo = float(neg.get('cpl_meta') or 18)
    teto = meta.teto_diario()
    sugestoes = []

    for l in _linhas(a.periodo, 'ad'):
        nome = f"anuncio '{l['anuncio']}' ({l['id']})"
        if l['gasto'] >= 2 * alvo and l['leads'] == 0:
            sugestoes.append(('PAUSAR', nome, f"gastou {brl(l['gasto'])} e nao trouxe lead nenhum",
                              f"python trafego/painel.py pausar {l['id']} --confirmo"))
        elif l['cpl'] and l['cpl'] > 1.5 * alvo and l['gasto'] >= 3 * alvo:
            sugestoes.append(('PAUSAR', nome, f"lead a {brl(l['cpl'])}, meta e {brl(alvo)}",
                              f"python trafego/painel.py pausar {l['id']} --confirmo"))
        if l['frequencia'] >= 3.5:
            sugestoes.append(('TROCAR CRIATIVO', nome,
                              f"frequencia {l['frequencia']}: o mesmo publico ja viu demais", None))
        if l['impressoes'] >= 2000 and l['ctr'] < 0.8:
            sugestoes.append(('MELHORAR CRIATIVO', nome,
                              f"CTR {l['ctr']}% (abaixo de 0,8%): imagem/primeira frase nao para o dedo", None))

    conjuntos = {cj['id']: cj for c in meta.listar_campanhas(ativas=True)
                 for cj in meta.listar_conjuntos(c['id'])}
    for l in _linhas(a.periodo, 'adset'):
        cj = conjuntos.get(l['id'])
        if not cj or not cj.get('daily_budget'):
            continue
        atual = int(cj['daily_budget']) / 100
        if l['leads'] >= 5 and l['cpl'] and l['cpl'] <= 0.7 * alvo:
            novo = min(round(atual * 1.2, 2), teto)
            if novo > atual:
                sugestoes.append(('ESCALAR', f"conjunto '{l['conjunto']}' ({l['id']})",
                                  f"{l['leads']} leads a {brl(l['cpl'])} (bem abaixo da meta). "
                                  f"Subir {brl(atual)} -> {brl(novo)}/dia (+20%, maximo seguro)",
                                  f"python trafego/painel.py orcamento {l['id']} {novo} --confirmo"))
            else:
                sugestoes.append(('NO TETO', f"conjunto '{l['conjunto']}'",
                                  f"esta indo bem mas ja bateu o teto de {brl(teto)}/dia", None))

    print(f'Diagnostico {a.periodo} | meta de custo por lead {brl(alvo)} | teto {brl(teto)}/dia\n')
    if not sugestoes:
        print('Nada para mexer: tudo dentro da meta (ou ainda sem dados suficientes).')
    for acao, alvo_txt, motivo, comando in sugestoes:
        print(f'[{acao}] {alvo_txt}\n    motivo: {motivo}')
        if comando:
            print(f'    para aplicar: {comando}')
        print()


def cmd_cidade(a):
    tabela(meta.buscar_local(a.nome, 'city'), ['key', 'nome', 'estado', 'tipo'])


def cmd_estado(a):
    tabela(meta.buscar_local(a.nome, 'region'), ['key', 'nome', 'tipo'])


def cmd_interesse(a):
    tabela(meta.buscar_interesse(a.termo), ['id', 'nome', 'publico'])


def cmd_formularios(_):
    tabela(meta.listar_formularios(), ['id', 'name', 'status', 'leads_count'])


def cmd_leads(a):
    desde = time.time() - a.dias * 86400
    leads = meta.baixar_leads(a.form_id, desde)
    if not leads:
        print('Nenhum lead no periodo.')
        return
    if a.csv:
        pasta = RAIZ / 'leads'
        pasta.mkdir(exist_ok=True)
        arq = pasta / f'leads_{a.form_id}_{date.today():%Y-%m-%d}.csv'
        cols = sorted({k for l in leads for k in l})
        with arq.open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=cols, delimiter=';')
            w.writeheader()
            w.writerows(leads)
        print(f'{len(leads)} leads salvos em {arq}')
    else:
        for l in leads:
            print(json.dumps(l, ensure_ascii=False))


# ------------------------------------------------------------------ criacao

def cmd_criar(a):
    """Cria campanha completa a partir de um plano JSON. Tudo PAUSADO."""
    plano = json.loads(Path(a.plano).read_text(encoding='utf-8'))
    pasta_plano = Path(a.plano).resolve().parent
    log = {'plano': str(a.plano), 'criado_em': datetime.now().isoformat(timespec='seconds')}

    cid = meta.criar_campanha(plano['campanha'], plano.get('objetivo', 'OUTCOME_LEADS'),
                              plano.get('categorias_especiais'))
    log['campanha_id'] = cid
    print(f"Campanha criada (PAUSADA): {cid}  {plano['campanha']}")

    midias = {}
    for cj in plano['conjuntos']:
        destino = cj.get('destino', plano.get('destino', 'WHATSAPP'))
        sid = meta.criar_conjunto(
            cid, cj['nome'], float(cj['orcamento_diario']), destino=destino,
            cidades=cj.get('cidades'), estados=cj.get('estados'), raio_km=cj.get('raio_km'),
            idade_min=cj.get('idade_min', 25), idade_max=cj.get('idade_max', 65),
            interesses=cj.get('interesses'), publico_advantage=cj.get('publico_advantage', True),
            generos=cj.get('generos'), local_raio=cj.get('local_raio'))
        print(f"  Conjunto (PAUSADO): {sid}  {cj['nome']}  {brl(float(cj['orcamento_diario']))}/dia")
        log.setdefault('conjuntos', []).append({'id': sid, 'nome': cj['nome']})

        for ad in cj['anuncios']:
            arq = ad.get('imagem') or ad.get('video')
            caminho = (pasta_plano / arq) if not Path(arq).is_absolute() else Path(arq)
            if not caminho.exists():
                caminho = RAIZ / arq
            if str(caminho) not in midias:
                midias[str(caminho)] = (meta.subir_video(caminho) if ad.get('video')
                                        else meta.subir_imagem(caminho))
            m = midias[str(caminho)]
            aid = meta.criar_anuncio(
                sid, ad['nome'], ad['texto'], ad['titulo'],
                imagem_hash=None if ad.get('video') else m, video_id=m if ad.get('video') else None,
                destino=destino, formulario_id=ad.get('formulario_id') or cj.get('formulario_id'),
                descricao=ad.get('descricao'))
            print(f"    Anuncio (PAUSADO): {aid}  {ad['nome']}")
            log['conjuntos'][-1].setdefault('anuncios', []).append({'id': aid, 'nome': ad['nome']})

    saida = Path(a.plano).with_suffix('.criado.json')
    saida.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nTudo criado PAUSADO. IDs salvos em {saida}')
    print(f'Para ligar (depois do OK): python trafego/painel.py ativar {cid} --confirmo '
          '(e ative tambem os conjuntos e anuncios)')


# ------------------------------------------------------------------ gasta dinheiro

def _exigir_ok(a):
    if not a.confirmo:
        print('BLOQUEADO: esta acao mexe no dinheiro da Aline. Mostre o que vai mudar, '
              'peca o OK e rode de novo com --confirmo.')
        sys.exit(2)
    pasta = RAIZ / 'relatorios'
    pasta.mkdir(exist_ok=True)
    with (pasta / 'historico_acoes.log').open('a', encoding='utf-8') as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M}  {' '.join(sys.argv[1:])}\n")


def cmd_ativar(a):
    _exigir_ok(a)
    print('Ativado.' if meta.ativar(a.id) else 'Meta nao confirmou.')


def cmd_pausar(a):
    _exigir_ok(a)
    print('Pausado.' if meta.pausar(a.id) else 'Meta nao confirmou.')


def cmd_orcamento(a):
    _exigir_ok(a)
    ok = meta.mudar_orcamento(a.id, float(a.reais))
    print(f'Orcamento agora {brl(float(a.reais))}/dia.' if ok else 'Meta nao confirmou.')


def main():
    p = argparse.ArgumentParser(description='Trafego da Dra. Aline (Meta Ads)')
    s = p.add_subparsers(dest='cmd', required=True)
    s.add_parser('contas').set_defaults(f=cmd_contas)
    x = s.add_parser('campanhas'); x.add_argument('--ativas', action='store_true'); x.set_defaults(f=cmd_campanhas)
    x = s.add_parser('estrutura'); x.add_argument('id'); x.set_defaults(f=cmd_estrutura)
    x = s.add_parser('relatorio'); x.add_argument('--periodo', default='last_7d')
    x.add_argument('--nivel', default='campaign', choices=['campaign', 'adset', 'ad'])
    x.add_argument('--salvar', action='store_true'); x.set_defaults(f=cmd_relatorio)
    x = s.add_parser('diario'); x.add_argument('--periodo', default='last_14d'); x.set_defaults(f=cmd_diario)
    x = s.add_parser('diagnostico'); x.add_argument('--periodo', default='last_7d'); x.set_defaults(f=cmd_diagnostico)
    x = s.add_parser('cidade'); x.add_argument('nome'); x.set_defaults(f=cmd_cidade)
    x = s.add_parser('estado'); x.add_argument('nome'); x.set_defaults(f=cmd_estado)
    x = s.add_parser('interesse'); x.add_argument('termo'); x.set_defaults(f=cmd_interesse)
    s.add_parser('formularios').set_defaults(f=cmd_formularios)
    x = s.add_parser('leads'); x.add_argument('form_id'); x.add_argument('--dias', type=int, default=7)
    x.add_argument('--csv', action='store_true'); x.set_defaults(f=cmd_leads)
    x = s.add_parser('criar'); x.add_argument('plano'); x.set_defaults(f=cmd_criar)
    for nome, fn in (('ativar', cmd_ativar), ('pausar', cmd_pausar)):
        x = s.add_parser(nome); x.add_argument('id'); x.add_argument('--confirmo', action='store_true')
        x.set_defaults(f=fn)
    x = s.add_parser('orcamento'); x.add_argument('id'); x.add_argument('reais')
    x.add_argument('--confirmo', action='store_true'); x.set_defaults(f=cmd_orcamento)

    a = p.parse_args()
    try:
        a.f(a)
    except meta.ErroMeta as e:
        print('ERRO:', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
