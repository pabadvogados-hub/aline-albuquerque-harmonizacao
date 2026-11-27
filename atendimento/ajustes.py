"""
Configuracao da central de atendimento (estilo ManyChat) da Dra. Aline.

Le, nesta ordem (o que vier primeiro vale):
  1. variaveis de ambiente ja definidas
  2. atendimento/.env
  3. config/.env

Arquivos de configuracao:
  config/marca.json        cores, fontes, funil, whatsapp (compartilhado com o painel)
  config/automacoes.json   gatilhos, respostas e fluxos de qualificacao
"""
import json
import logging
import os
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
DADOS = RAIZ / 'dados'
DADOS.mkdir(exist_ok=True)

ARQ_MARCA = RAIZ / 'config' / 'marca.json'
ARQ_AUTOMACOES = RAIZ / 'config' / 'automacoes.json'
ARQ_DB = Path(os.getenv('ATEND_DB') or (DADOS / 'atendimento.db'))
ARQ_LOG = DADOS / 'atendimento.log'


def _carregar_env(caminho):
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding='utf-8', errors='ignore').splitlines():
        linha = linha.strip()
        if '=' in linha and not linha.startswith('#'):
            k, v = linha.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_carregar_env(AQUI / '.env')
_carregar_env(RAIZ / 'config' / '.env')


def env(nome, padrao=''):
    return (os.getenv(nome) or padrao).strip()


def simulando():
    return env('ATEND_SIMULAR') in ('1', 'true', 'sim')


VERSAO_API = env('META_API_VERSION', 'v21.0')
GRAPH = f'https://graph.facebook.com/{VERSAO_API}'


def marca():
    try:
        return json.loads(ARQ_MARCA.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'nome': 'Clinica', 'funil': ['Novo', 'Conversando', 'Qualificado', 'Agendou avaliacao',
                                             'Compareceu', 'Fechou', 'Perdido'],
                'escuro': {}, 'claro': {}, 'fontes': {}}


def funil():
    return marca().get('funil') or ['Novo']


def automacoes():
    return json.loads(ARQ_AUTOMACOES.read_text(encoding='utf-8'))


def salvar_automacoes(dados):
    tmp = ARQ_AUTOMACOES.with_suffix('.tmp')
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(ARQ_AUTOMACOES)


def configurar_log():
    log = logging.getLogger('atendimento')
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh = logging.FileHandler(ARQ_LOG, encoding='utf-8')
    fh.setFormatter(fmt)
    log.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(sh)
    return log
