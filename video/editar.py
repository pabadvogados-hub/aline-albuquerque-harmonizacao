"""
Editor de video da Dra. Aline Albuquerque - um comando, do take cru ao Reels pronto.

  python video/editar.py "C:/caminho/take.mov" --slug fenix-01
  python video/editar.py take.mov --slug fenix-01 --angulo 2 --formato ambos --aviso --amostras
  python video/editar.py take.mov --slug fenix-01 --ganchos video/meus_ganchos.json --velocidade 1.15

O que faz:
  1. normaliza o video (H.264, 1080x1920, 30 fps; converte HEVC do iPhone) e aplica a velocidade
  2. transcreve local (faster-whisper, palavra por palavra) e corrige termos (Fenix, harmonizacao...)
  3. corta pausas longas pelos intervalos entre palavras
  4. acha o rosto (YuNet) para a legenda nunca cobrir olhos e boca
  5. monta os destaques pelas palavras-chave do nicho e um edit.json por gancho (teste A/B)
  6. renderiza no estudio Remotion (composicao ShortAline / ShortAline45)
  7. normaliza o audio em -14 LUFS e entrega em video/saida/<slug>/:
     <slug>_9x16_g1.mp4 ... , captions.srt, post.md (3 opcoes de legenda dentro das regras)

Estudio: env STUDIO_DIR (padrao C:/Users/Admin/pab-video/video-agent/studio).
Configuracao: video/config_video.json + config/marca.json.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
STUDIO = Path(os.getenv('STUDIO_DIR', r'C:\Users\Admin\pab-video\video-agent\studio'))
MODELO_ROSTO = AQUI / 'modelos' / 'face_detection_yunet_2023mar.onnx'
FPS = 30

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def rodar(cmd, cwd=None, shell=False):
    r = subprocess.run(cmd, cwd=cwd, shell=shell, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError(f'falhou: {cmd if isinstance(cmd, str) else " ".join(map(str, cmd))}\n{r.stderr[-2500:]}')
    return r.stdout


def sem_acento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def ler_json(p, padrao=None):
    p = Path(p)
    if not p.exists():
        return padrao if padrao is not None else {}
    return json.loads(p.read_text(encoding='utf-8'))


def whatsapp_fmt(num):
    d = re.sub(r'\D', '', num or '')
    if d.startswith('55') and len(d) >= 12:
        d = d[2:]
    if len(d) == 11:
        return f'({d[:2]}) {d[2:7]}-{d[7:]}'
    return num or ''


# ============================================================
# 1. NORMALIZAR
# ============================================================

def duracao(arq):
    out = rodar(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(arq)])
    return float(out.strip())


def normalizar(entrada, saida, velocidade):
    vf = (f'setpts=PTS/{velocidade},' if velocidade != 1 else '') + \
        'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p'
    af = f'atempo={velocidade}' if velocidade != 1 else 'anull'
    rodar(['ffmpeg', '-y', '-v', 'error', '-i', str(entrada), '-vf', vf, '-af', af,
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
           '-movflags', '+faststart', str(saida)])


# ============================================================
# 2. TRANSCREVER
# ============================================================

def transcrever(video, cfg):
    from faster_whisper import WhisperModel
    import numpy as np
    modelo = WhisperModel(os.getenv('WHISPER_MODELO', 'small'), device='cpu', compute_type='int8')
    # audio decodificado pelo ffmpeg (o PyAV instalado nao conversa com o faster-whisper)
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 's16le', '-ac', '1', '-ar', '16000', '-'],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    segs, _ = modelo.transcribe(audio, language='pt', word_timestamps=True, beam_size=5,
                                initial_prompt=cfg.get('vocabulario', ''), condition_on_previous_text=False)
    palavras = []
    for s in segs:
        for w in s.words or []:
            txt = w.word
            for padrao, troca in (cfg.get('correcoes') or {}).items():
                txt = re.sub(padrao, troca, txt)
            if not txt.strip():
                continue
            palavras.append({'text': txt if txt.startswith(' ') else ' ' + txt.strip(),
                             'startMs': int(round(w.start * 1000)), 'endMs': int(round(w.end * 1000)),
                             'confidence': round(float(w.probability or 0), 3), 'timestampMs': None})
    # "metodo" so vira "Método" quando e o nome do metodo dela
    for i, w in enumerate(palavras[:-1]):
        if sem_acento(w['text']).strip(' .,') == 'metodo' and 'fenix' in sem_acento(palavras[i + 1]['text']):
            w['text'] = ' Método'
    return palavras


# ============================================================
# 3. CORTES
# ============================================================

def cortes(palavras, dur_ms, pausa_max):
    if not palavras:
        return [{'fromMs': 0, 'toMs': dur_ms}]
    blocos, ini, fim = [], palavras[0]['startMs'], palavras[0]['endMs']
    for w in palavras[1:]:
        if w['startMs'] - fim > pausa_max:
            blocos.append((ini, fim))
            ini = w['startMs']
        fim = max(fim, w['endMs'])
    blocos.append((ini, fim))
    out = []
    for a, b in blocos:
        a, b = max(0, a - 120), min(dur_ms, b + 200)
        if out and a <= out[-1]['toMs']:
            out[-1]['toMs'] = b
        else:
            out.append({'fromMs': a, 'toMs': b})
    return out


def _frame(ms):
    return round(ms / 1000 * FPS)


def mapa_saida(ranges):
    """Mesma conta da composicao: devolve f(ms_origem) -> ms_saida ou None."""
    partes, at = [], 0
    for r in ranges:
        fr = _frame(r['fromMs'])
        n = max(1, _frame(r['toMs']) - fr)
        partes.append((r['fromMs'], r['toMs'], (at - fr) / FPS * 1000))
        at += n

    def f(ms):
        for a, b, sh in partes:
            if a <= ms < b:
                return ms + sh
        return None
    return f, at / FPS * 1000


# ============================================================
# 4. ROSTO
# ============================================================

def rostos(video, passo_ms=200):
    import cv2
    if not MODELO_ROSTO.exists():
        log('modelo de rosto ausente (video/modelos): legenda fica na posicao padrao')
        return []
    # o OpenCV nao abre caminho com acento ("AUTOMAÇÕES"): trabalha numa pasta neutra do Temp
    import tempfile
    neutro = Path(tempfile.gettempdir()) / 'aline_video'
    neutro.mkdir(exist_ok=True)
    shutil.copyfile(MODELO_ROSTO, neutro / 'yunet.onnx')
    shutil.copyfile(video, neutro / 'rosto.mp4')
    det = cv2.FaceDetectorYN.create(str(neutro / 'yunet.onnx'), '', (360, 640), 0.6, 0.3, 50)
    cap = cv2.VideoCapture(str(neutro / 'rosto.mp4'))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    out, i, passo = [], 0, max(1, round(fps * passo_ms / 1000))
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % passo == 0:
            ok, img = cap.retrieve()
            if ok:
                h, w = img.shape[:2]
                peq = cv2.resize(img, (360, 640))
                det.setInputSize((360, 640))
                _, faces = det.detect(peq)
                ms = int(round(i / fps * 1000))
                if faces is not None and len(faces):
                    f = max(faces, key=lambda x: x[2] * x[3])
                    k = h / 640
                    olhos = (f[5] + f[7]) / 2 * k
                    boca = (f[11] + f[13]) / 2 * k
                    out.append({'ms': ms, 'eye': int(olhos), 'mouth': int(boca),
                                'top': int(f[1] * k), 'bottom': int((f[1] + f[3]) * k)})
                else:
                    out.append({'ms': ms, 'eye': None, 'mouth': None, 'top': None, 'bottom': None})
        i += 1
    cap.release()
    return out


# ============================================================
# 5. EDIT.JSON
# ============================================================

def destaques(palavras, cfg, f_saida, gancho_s):
    regras = cfg.get('destaques', [])
    usados, out = set(), []
    ultimo = -1e9
    minimo = cfg.get('intervalo_min_destaques_s', 3.2) * 1000
    for w in palavras:
        t = sem_acento(w['text'])
        for r in regras:
            if r['texto'] in usados or r['procura'] not in t:
                continue
            at = f_saida(w['startMs'])
            if at is None or at < gancho_s * 1000 + 400 or at - ultimo < minimo:
                continue
            out.append({'text': r['texto'], 'atMs': w['startMs']})
            usados.add(r['texto'])
            ultimo = at
            break
        if len(out) >= cfg.get('max_destaques', 5):
            break
    return out


def carregar_ganchos(arq, angulo):
    d = ler_json(arq, {})
    if isinstance(d, list):
        return d, [], ''
    if 'angulos' in d:
        a = next((x for x in d['angulos'] if x.get('numero') == angulo), d['angulos'][0])
        return a['ganchos'], a.get('etapas', []), a.get('nome', '')
    return d.get('ganchos', []), d.get('etapas', []), d.get('nome', '')


def montar_edit(slug, ranges, cfg, marca, gancho, dests, etapas_txt, palavras, usar_aviso, f_saida, dur_saida_ms):
    reg = cfg.get('registro', '')
    reg = '' if 'PREENCHER' in reg.upper() else reg
    lt = cfg.get('lower_third') or {}
    cf = cfg.get('card_final') or {}
    etapas = []
    if etapas_txt:
        # espalha as etapas entre 25% e 75% do video (tempo de origem do primeiro corte que cair ali)
        vis = [w for w in palavras if f_saida(w['startMs']) is not None]
        for k, txt in enumerate(etapas_txt):
            alvo = dur_saida_ms * (0.25 + 0.5 * k / max(1, len(etapas_txt) - 1))
            w = min(vis, key=lambda x: abs(f_saida(x['startMs']) - alvo)) if vis else None
            if w:
                etapas.append({'text': txt, 'atMs': w['startMs']})
    return {
        'video': f'aline-{slug}.mp4',
        'captions': f'aline-{slug}.json',
        'faces': f'aline-{slug}.faces.json',
        'ranges': ranges,
        'hook': {'kicker': gancho['kicker'], 'text': gancho['text'], 'seconds': cfg.get('gancho_segundos', 2.4)} if gancho else None,
        'callouts': dests,
        'etapas': etapas,
        'lowerThird': {'nome': lt.get('nome', marca.get('nome', '')), 'linha': lt.get('linha', ''),
                       'registro': reg or None, 'seconds': lt.get('segundos', 4)} if lt else None,
        'assinatura': cfg.get('assinatura'),
        'aviso': cfg.get('aviso') if usar_aviso else None,
        'endCard': {'title': cf.get('titulo', 'Agende sua *avaliação*'), 'subtitle': cf.get('subtitulo', ''),
                    'instagram': marca.get('instagram'), 'whatsapp': whatsapp_fmt(marca.get('whatsapp')),
                    'registro': reg or None, 'seconds': cf.get('segundos', 3)},
        'zoom': True,
    }


# ============================================================
# 6. RENDER
# ============================================================

def npx():
    return shutil.which('npx.cmd') or shutil.which('npx') or 'npx'


def render(comp, props_rel, saida_rel):
    rodar(f'"{npx()}" remotion render {comp} "{saida_rel}" --props="{props_rel}" --log=error', cwd=STUDIO, shell=True)


def still(comp, props_rel, saida_rel, frame):
    rodar(f'"{npx()}" remotion still {comp} "{saida_rel}" --props="{props_rel}" --frame={frame} --log=error',
          cwd=STUDIO, shell=True)


def audio_final(entrada, saida):
    rodar(['ffmpeg', '-y', '-v', 'error', '-i', str(entrada), '-c:v', 'copy',
           '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
           '-movflags', '+faststart', str(saida)])


# ============================================================
# 7. SRT E POST
# ============================================================

def _ts(ms):
    ms = max(0, int(ms))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def srt(palavras, f_saida):
    blocos, atual = [], []
    for w in palavras:
        t = f_saida(w['startMs'])
        if t is None:
            continue
        w2 = {**w, 's': t, 'e': t + (w['endMs'] - w['startMs'])}
        if atual and (len(atual) >= 7 or w2['s'] - atual[0]['s'] > 2600 or atual[-1]['text'].strip()[-1:] in '.?!'):
            blocos.append(atual)
            atual = []
        atual.append(w2)
    if atual:
        blocos.append(atual)
    linhas = []
    for i, b in enumerate(blocos, 1):
        linhas += [str(i), f"{_ts(b[0]['s'])} --> {_ts(b[-1]['e'])}", ''.join(w['text'] for w in b).strip(), '']
    return '\n'.join(linhas)


def post_md(slug, ganchos, nome_angulo, marca, cfg, texto, usar_aviso, arquivos):
    wa = whatsapp_fmt(marca.get('whatsapp'))
    reg = cfg.get('registro', '')
    reg_ok = 'PREENCHER' not in reg.upper()
    assinatura = f"Dra. Aline Albuquerque{' - ' + reg if reg_ok else ' - [PROFISSÃO E CONSELHO]'} - Santos/SP"
    tags = '#harmonizacaofacial #santos #baixadasantista #metodofenix #derretimentofacial #esteticafacial'
    opcoes = [
        ('Educativa',
         'Quando o emagrecimento é rápido, o rosto pode perder sustentação, e não só volume. '
         'Isso tem nome: derretimento facial.\n\n'
         'No Método Fênix, a avaliação começa pela sustentação, para o plano respeitar as características de cada rosto.\n\n'
         f'Avaliação em Santos: chame no WhatsApp {wa}.'),
        ('Pergunta frequente',
         'Uma das perguntas que mais aparecem no consultório: tratar o rosto durante o emagrecimento ou esperar?\n\n'
         'A resposta depende de cada caso, e é isso que a avaliação define.\n\n'
         f'Para agendar a sua em Santos, o WhatsApp é {wa}.'),
        ('Curta (anúncio)',
         'Derretimento facial: o rosto perde sustentação depois do emagrecimento. '
         f'Avaliação com o Método Fênix em Santos. WhatsApp {wa}.'),
    ]
    lin = [f'# {slug}: post e anúncio', '',
           f'Ângulo: {nome_angulo or "-"}', '',
           '## Vídeos gerados', '']
    lin += [f'- `{a}`' for a in arquivos]
    lin += ['', '## Ganchos (teste A/B)', '',
            'Suba as variações no MESMO conjunto, cada uma como um anúncio com o sufixo no nome (_g1, _g2...). '
            'Depois de 3 a 5 dias o painel mostra qual tem a melhor taxa de gancho (quem para nos 3 primeiros segundos).', '']
    lin += [f'- g{i}: [{g["kicker"]}] {g["text"].replace("*", "")}' for i, g in enumerate(ganchos, 1)]
    lin += ['', '## Legenda: 3 opções (já dentro das regras)', '']
    for titulo, txt in opcoes:
        lin += [f'### {titulo}', '', txt, '', assinatura, '', tags, '']
    if usar_aviso:
        lin += ['**Vídeo com aviso legal no rodapé.** Se a imagem é de paciente, guardar o termo de consentimento assinado.', '']
    lin += ['## Conferência antes de publicar', '',
            f'- [{"x" if reg_ok else " "}] Profissão e número do conselho na legenda e na assinatura (preencher em video/config_video.json)',
            '- [ ] Sem antes e depois lado a lado (proibido pela Meta em antienvelhecimento)',
            '- [ ] Sem "você + condição" no texto do anúncio (ex.: "Você emagreceu e seu rosto caiu?")',
            '- [ ] Sem citar Ozempic, Mounjaro ou outra marca de remédio ou produto',
            '- [ ] Sem promessa de resultado, preço, promoção ou pacote',
            '- [ ] Sem cena do procedimento em andamento',
            '- [ ] Imagem de paciente só com termo de consentimento e aviso legal (--aviso)',
            '', '## Transcrição', '', texto.strip(), '']
    return '\n'.join(lin)


# ============================================================
# MAIN
# ============================================================

def main():
    ap = argparse.ArgumentParser(description='Editor de video da Dra. Aline')
    ap.add_argument('entrada')
    ap.add_argument('--slug', required=True)
    ap.add_argument('--velocidade', type=float, default=1.0)
    ap.add_argument('--formato', default='9x16', choices=['9x16', '4x5', 'ambos'])
    ap.add_argument('--ganchos', default=str(AQUI / 'ganchos_exemplo.json'))
    ap.add_argument('--angulo', type=int, default=1)
    ap.add_argument('--max-ganchos', type=int, default=3)
    ap.add_argument('--aviso', action='store_true', help='faixa legal no rodape (imagem de paciente)')
    ap.add_argument('--etapas', action='store_true', help='chips das etapas do Metodo Fenix (do angulo)')
    ap.add_argument('--sem-cortes', action='store_true')
    ap.add_argument('--so-preparar', action='store_true', help='gera tudo menos o render')
    ap.add_argument('--amostras', action='store_true', help='PNG de 4 momentos para revisar')
    a = ap.parse_args()

    slug = re.sub(r'[^a-z0-9-]+', '-', sem_acento(a.slug)).strip('-')
    cfg = ler_json(AQUI / 'config_video.json')
    marca = ler_json(RAIZ / 'config' / 'marca.json')
    entrada = Path(a.entrada)
    if not entrada.exists():
        sys.exit(f'arquivo nao encontrado: {entrada}')
    if not (STUDIO / 'package.json').exists():
        sys.exit(f'estudio Remotion nao encontrado em {STUDIO} (defina STUDIO_DIR)')
    if 'PREENCHER' in cfg.get('registro', 'PREENCHER').upper():
        log('ATENCAO: registro profissional nao preenchido em video/config_video.json - a linha fica de fora do video')

    trab = AQUI / 'trabalho' / slug
    entrega = AQUI / 'saida' / slug
    trab.mkdir(parents=True, exist_ok=True)
    entrega.mkdir(parents=True, exist_ok=True)
    pub = STUDIO / 'public'
    t0 = time.time()

    base = trab / 'base.mp4'
    cache = trab / 'cache.json'
    chave = {'entrada': str(entrada.resolve()), 'tamanho': entrada.stat().st_size, 'velocidade': a.velocidade}
    reusar = cache.exists() and ler_json(cache) == chave and base.exists() and (trab / 'palavras.json').exists()
    if reusar:
        log('mesmo take e velocidade: reaproveitando video normalizado e transcricao')
        palavras = ler_json(trab / 'palavras.json', [])
    else:
        log(f'normalizando ({a.velocidade}x)...')
        normalizar(entrada, base, a.velocidade)
        log('transcrevendo (local)...')
        palavras = transcrever(base, cfg)
        (trab / 'palavras.json').write_text(json.dumps(palavras, ensure_ascii=False), encoding='utf-8')
        cache.write_text(json.dumps(chave), encoding='utf-8')
    dur_ms = int(duracao(base) * 1000)
    texto = ''.join(w['text'] for w in palavras)
    log(f'{len(palavras)} palavras')

    ranges = [{'fromMs': 0, 'toMs': dur_ms}] if a.sem_cortes else cortes(palavras, dur_ms, cfg.get('pausa_max_ms', 450))
    f_saida, dur_saida = mapa_saida(ranges)
    log(f'{len(ranges)} trechos: {dur_ms / 1000:.1f}s -> {dur_saida / 1000:.1f}s')

    log('procurando o rosto...')
    faces = rostos(base)

    ganchos, etapas_txt, nome_angulo = carregar_ganchos(a.ganchos, a.angulo)
    ganchos = ganchos[:max(1, a.max_ganchos)] or [None]
    dests = destaques(palavras, cfg, f_saida, cfg.get('gancho_segundos', 2.4))

    shutil.copyfile(base, pub / f'aline-{slug}.mp4')
    (pub / f'aline-{slug}.json').write_text(json.dumps(palavras, ensure_ascii=False), encoding='utf-8')
    (pub / f'aline-{slug}.faces.json').write_text(json.dumps(faces), encoding='utf-8')

    formatos = {'9x16': ['ShortAline'], '4x5': ['ShortAline45'], 'ambos': ['ShortAline', 'ShortAline45']}[a.formato]
    arquivos = []
    for i, g in enumerate(ganchos, 1):
        edit = montar_edit(slug, ranges, cfg, marca, g, dests, etapas_txt if a.etapas else [], palavras,
                           a.aviso, f_saida, dur_saida)
        nome_props = f'aline-{slug}_g{i}.edit.json'
        (pub / nome_props).write_text(json.dumps(edit, ensure_ascii=False, indent=1), encoding='utf-8')
        shutil.copyfile(pub / nome_props, entrega / f'edit_g{i}.json')
        if a.so_preparar:
            continue
        for comp in formatos:
            fmt = '9x16' if comp == 'ShortAline' else '4x5'
            bruto = f'out/aline/{slug}_{fmt}_g{i}.mp4'
            log(f'renderizando {fmt} gancho {i}...')
            t1 = time.time()
            render(comp, f'public/{nome_props}', bruto)
            final = entrega / f'{slug}_{fmt}_g{i}.mp4'
            audio_final(STUDIO / bruto, final)
            arquivos.append(final.name)
            log(f'  ok em {time.time() - t1:.0f}s -> {final}')
            if a.amostras and i == 1:
                pasta = entrega / 'amostras'
                pasta.mkdir(exist_ok=True)
                total = round((dur_saida / 1000 + edit['endCard']['seconds']) * FPS)
                for rot, fr in (('gancho', 30), ('meio1', int(total * 0.35)), ('meio2', int(total * 0.65)),
                                ('final', total - 20)):
                    still(comp, f'public/{nome_props}', f'out/aline/{slug}_{fmt}_{rot}.png', fr)
                    shutil.copyfile(STUDIO / f'out/aline/{slug}_{fmt}_{rot}.png', pasta / f'{fmt}_{rot}.png')

    (entrega / 'captions.srt').write_text(srt(palavras, f_saida), encoding='utf-8')
    (entrega / 'post.md').write_text(post_md(slug, [g for g in ganchos if g], nome_angulo, marca, cfg, texto,
                                             a.aviso, arquivos), encoding='utf-8')
    log(f'pronto em {time.time() - t0:.0f}s -> {entrega}')


if __name__ == '__main__':
    main()
