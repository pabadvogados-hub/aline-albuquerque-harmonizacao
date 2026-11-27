"""
Banco SQLite da central (dados/atendimento.db).

Datas gravadas em horario local, texto 'AAAA-MM-DD HH:MM:SS' (ordena e compara como texto).
"""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

from ajustes import ARQ_DB, funil

_trava = threading.RLock()

ESQUEMA = """
CREATE TABLE IF NOT EXISTS contatos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  canal TEXT NOT NULL,                -- instagram | messenger | whatsapp
  externo_id TEXT NOT NULL,           -- IGSID (instagram) ou PSID (messenger)
  username TEXT, nome TEXT, foto TEXT,
  etapa TEXT NOT NULL DEFAULT 'Novo',
  tags TEXT NOT NULL DEFAULT '[]',
  campos TEXT NOT NULL DEFAULT '{}',
  origem TEXT,                        -- comentario | dm | story | anuncio | formulario
  ad_id TEXT, post_id TEXT, ref TEXT,
  automacao_origem TEXT,              -- primeira automacao que capturou o contato
  fluxo TEXT, fluxo_passo INTEGER,    -- fluxo de qualificacao em andamento
  fluxo_fim_em TEXT,
  criado_em TEXT NOT NULL,
  ultima_msg_em TEXT,
  ultima_entrada_em TEXT,             -- ultima mensagem DA PESSOA (janela de 24h)
  valor_fechado REAL, procedimento TEXT, responsavel TEXT,
  UNIQUE(canal, externo_id)
);
CREATE TABLE IF NOT EXISTS mensagens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contato_id INTEGER NOT NULL,
  direcao TEXT NOT NULL,              -- entrada | saida
  texto TEXT, tipo TEXT,              -- texto | quick_reply | story_mencao | story_resposta | comentario | resposta_publica | private_reply | template
  meta_id TEXT, quando TEXT NOT NULL,
  automacao TEXT,                     -- id da automacao que enviou (null = humano)
  autor TEXT                          -- robo | equipe | app_instagram | pessoa
);
CREATE INDEX IF NOT EXISTS ix_msg_contato ON mensagens(contato_id, quando);
CREATE INDEX IF NOT EXISTS ix_msg_meta ON mensagens(meta_id);
CREATE TABLE IF NOT EXISTS eventos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contato_id INTEGER, automacao TEXT, gatilho TEXT, detalhe TEXT, quando TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ev_aut ON eventos(automacao, quando);
CREATE TABLE IF NOT EXISTS comentarios_respondidos (
  comment_id TEXT PRIMARY KEY, contato_id INTEGER, automacao TEXT, quando TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS etapas_historico (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contato_id INTEGER NOT NULL, etapa TEXT NOT NULL, quando TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_hist ON etapas_historico(etapa, quando);
CREATE TABLE IF NOT EXISTS respostas_rapidas (
  id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, texto TEXT NOT NULL
);
"""

RESPOSTAS_PADRAO = [
    ('Endereco', 'Atendo em Santos. Te mando a localizacao certinha pelo WhatsApp quando agendarmos.'),
    ('Avaliacao', 'A avaliacao e o primeiro passo: analiso seu rosto, entendo o que mudou com o '
                  'emagrecimento e te explico o plano do Metodo Fenix com calma.'),
    ('Valores', 'Os valores dependem do plano montado na avaliacao, porque cada rosto perdeu volume '
                'em lugares diferentes. Posso te passar os horarios livres?'),
    ('Horarios', 'Tenho horarios nesta semana. Prefere manha, tarde ou noite?'),
]


def agora():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


@contextmanager
def conectar():
    """Conexao curta: commit no fim, rollback em erro e SEMPRE fecha."""
    c = sqlite3.connect(ARQ_DB, timeout=30, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def init():
    with _trava, conectar() as c:
        c.executescript(ESQUEMA)
        if not c.execute('SELECT 1 FROM respostas_rapidas LIMIT 1').fetchone():
            c.executemany('INSERT INTO respostas_rapidas(titulo, texto) VALUES (?, ?)', RESPOSTAS_PADRAO)


def contato_dict(r):
    if r is None:
        return None
    d = dict(r)
    d['tags'] = json.loads(d.get('tags') or '[]')
    d['campos'] = json.loads(d.get('campos') or '{}')
    return d


def buscar_contato(cid):
    with conectar() as c:
        return contato_dict(c.execute('SELECT * FROM contatos WHERE id=?', (cid,)).fetchone())


def obter_ou_criar(canal, externo_id, origem=None, quando=None, **extra):
    """Devolve (contato, novo?)."""
    quando = quando or agora()
    with _trava, conectar() as c:
        r = c.execute('SELECT * FROM contatos WHERE canal=? AND externo_id=?', (canal, externo_id)).fetchone()
        if r:
            # completa dados que faltavam (ex.: username chegou depois)
            sets = {k: v for k, v in extra.items() if v and not r[k]} if extra else {}
            if sets:
                c.execute(f"UPDATE contatos SET {', '.join(k + '=?' for k in sets)} WHERE id=?",
                          (*sets.values(), r['id']))
                r = c.execute('SELECT * FROM contatos WHERE id=?', (r['id'],)).fetchone()
            return contato_dict(r), False
        etapa = funil()[0]
        campos = {k: v for k, v in extra.items() if k in ('username', 'nome', 'foto', 'ad_id', 'post_id', 'ref',
                                                          'automacao_origem')}
        cols = ['canal', 'externo_id', 'origem', 'etapa', 'criado_em', *campos.keys()]
        cur = c.execute(f"INSERT INTO contatos({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                        (canal, externo_id, origem, etapa, quando, *campos.values()))
        cid = cur.lastrowid
        c.execute('INSERT INTO etapas_historico(contato_id, etapa, quando) VALUES (?, ?, ?)', (cid, etapa, quando))
        return contato_dict(c.execute('SELECT * FROM contatos WHERE id=?', (cid,)).fetchone()), True


def atualizar(cid, **campos):
    if not campos:
        return
    for k in ('tags', 'campos'):
        if k in campos and not isinstance(campos[k], str):
            campos[k] = json.dumps(campos[k], ensure_ascii=False)
    with _trava, conectar() as c:
        c.execute(f"UPDATE contatos SET {', '.join(k + '=?' for k in campos)} WHERE id=?", (*campos.values(), cid))


def mudar_etapa(cid, etapa, quando=None):
    """Muda a etapa e registra no historico (so se mudou)."""
    quando = quando or agora()
    with _trava, conectar() as c:
        r = c.execute('SELECT etapa FROM contatos WHERE id=?', (cid,)).fetchone()
        if not r or r['etapa'] == etapa:
            return False
        c.execute('UPDATE contatos SET etapa=? WHERE id=?', (etapa, cid))
        c.execute('INSERT INTO etapas_historico(contato_id, etapa, quando) VALUES (?, ?, ?)', (cid, etapa, quando))
        return True


def avancar_etapa(cid, etapa, quando=None):
    """Muda so se for para frente no funil (robo nunca puxa lead para tras)."""
    f = funil()
    c = buscar_contato(cid)
    if not c or etapa not in f:
        return False
    atual = f.index(c['etapa']) if c['etapa'] in f else 0
    if c['etapa'] == f[-1] or f.index(etapa) <= atual:
        return False
    return mudar_etapa(cid, etapa, quando)


def adicionar_tags(cid, tags):
    c = buscar_contato(cid)
    if not c:
        return
    novas = list(dict.fromkeys(c['tags'] + [t for t in tags if t]))
    if novas != c['tags']:
        atualizar(cid, tags=novas)


def salvar_campo(cid, nome, valor):
    c = buscar_contato(cid)
    if not c:
        return
    campos = c['campos']
    campos[nome] = valor
    atualizar(cid, campos=campos)


def registrar_msg(cid, direcao, texto, tipo='texto', meta_id=None, automacao=None, autor=None, quando=None):
    quando = quando or agora()
    with _trava, conectar() as c:
        if meta_id and c.execute('SELECT 1 FROM mensagens WHERE meta_id=?', (meta_id,)).fetchone():
            return None
        cur = c.execute('INSERT INTO mensagens(contato_id, direcao, texto, tipo, meta_id, quando, automacao, autor) '
                        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (cid, direcao, texto, tipo, meta_id, quando, automacao, autor))
        if direcao == 'entrada' and tipo != 'comentario':
            # so mensagem no Direct abre a janela de 24h (comentario nao abre)
            c.execute('UPDATE contatos SET ultima_msg_em=?, ultima_entrada_em=? WHERE id=?', (quando, quando, cid))
        else:
            c.execute('UPDATE contatos SET ultima_msg_em=? WHERE id=?', (quando, cid))
        return cur.lastrowid


def registrar_evento(cid, automacao, gatilho, detalhe='', quando=None):
    with _trava, conectar() as c:
        c.execute('INSERT INTO eventos(contato_id, automacao, gatilho, detalhe, quando) VALUES (?, ?, ?, ?, ?)',
                  (cid, automacao, gatilho, detalhe, quando or agora()))


def comentario_ja_respondido(comment_id):
    with conectar() as c:
        return bool(c.execute('SELECT 1 FROM comentarios_respondidos WHERE comment_id=?', (comment_id,)).fetchone())


def marcar_comentario(comment_id, cid, automacao, quando=None):
    with _trava, conectar() as c:
        c.execute('INSERT OR IGNORE INTO comentarios_respondidos(comment_id, contato_id, automacao, quando) '
                  'VALUES (?, ?, ?, ?)', (comment_id, cid, automacao, quando or agora()))


def mensagem_existe(meta_id):
    if not meta_id:
        return False
    with conectar() as c:
        return bool(c.execute('SELECT 1 FROM mensagens WHERE meta_id=?', (meta_id,)).fetchone())
