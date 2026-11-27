# Editor de vídeo: Dra. Aline Albuquerque

Do take cru ao Reels pronto, com um comando: legenda palavra por palavra, cortes de pausa, gancho, destaques, apresentação com nome e registro, card final com WhatsApp, áudio nivelado e as versões de gancho para o teste A/B do anúncio. Tudo na identidade dela: preto, nude rosé, rose gold e o coral da fênix.

## Como gravar (faz toda a diferença)

- **Vertical**, em 1080p ou mais (no iPhone: 4K ou 1080p a 30 fps).
- **Luz de frente**: janela ou ring light na frente dela, nunca atrás.
- **Olhando na lente**, com o celular na altura dos olhos e o rosto no terço de cima da tela.
- **Frases curtas.** Pode errar e repetir a frase: a pausa longa é cortada sozinha.
- **15 a 30 segundos** para anúncio (até 60 para orgânico).
- **Ambiente quieto e sem música de fundo.** A música entra depois, se for o caso.
- **Não gravar o procedimento em andamento** (proibido pelos conselhos).
- **Antes e depois de paciente:** só com termo de consentimento assinado, nunca lado a lado, e sempre com `--aviso`.

## Como rodar

```
python video/editar.py "C:/caminho/take.mov" --slug fenix-01
```

| Opção | O que faz |
|---|---|
| `--angulo 1..5` | escolhe o ângulo de `ganchos_exemplo.json` (padrão 1) |
| `--ganchos arquivo.json` | usa outro arquivo de ganchos |
| `--max-ganchos 3` | quantas versões de gancho gerar (_g1, _g2, _g3) |
| `--formato 9x16, 4x5 ou ambos` | Reels/Stories (9x16) e Feed (4x5) |
| `--velocidade 1.15` | acelera sem mudar o tom da voz |
| `--aviso` | faixa legal no rodapé (obrigatória em imagem de paciente) |
| `--etapas` | chips das etapas do Método Fênix (confirmar as etapas reais com ela) |
| `--sem-cortes` | não corta as pausas |
| `--amostras` | salva 4 imagens para revisar (gancho, meio, meio, final) |
| `--so-preparar` | monta tudo sem renderizar (para ajustar o edit.json à mão) |

Entrega em `video/saida/<slug>/`:

- `<slug>_9x16_g1.mp4`, `_g2.mp4`... (e `_4x5_` se pedido)
- `captions.srt`
- `post.md`, com 3 opções de legenda dentro das regras e o checklist de publicação
- `edit_g*.json`: ajuste fino (textos, tempos) e renderize de novo no estúdio com:
  `npx remotion render ShortAline out/x.mp4 --props=public/aline-<slug>_g1.edit.json`

## Antes do primeiro vídeo

1. Preencher `registro` em `video/config_video.json` (profissão e número do conselho). Sem isso a linha não aparece no vídeo.
2. Confirmar com ela as etapas reais do Método Fênix (`ganchos_exemplo.json`, ângulo 4).

## Requisitos (já instalados no PC do Weverton)

- Python com `faster-whisper` e `opencv-python`.
- ffmpeg no PATH.
- Node e o estúdio Remotion em `C:\Users\Admin\pab-video\video-agent\studio`, com as composições `ShortAline` e `ShortAline45`. Outro local: definir `STUDIO_DIR`.
- Modelo de rosto em `video/modelos/face_detection_yunet_2023mar.onnx` (do opencv_zoo).

## Teste A/B de gancho (liga com o painel de tráfego)

Os vídeos `_g1`, `_g2` e `_g3` têm o mesmo corpo e só mudam o gancho dos 2 primeiros segundos.

1. Suba os três no mesmo conjunto, com o sufixo no nome do anúncio.
2. Depois de 3 a 5 dias, olhe a coluna **Gancho** (quem para nos 3 s) do painel.
3. Fique com o vencedor e grave mais vídeos naquele ângulo.

## Estúdio Remotion (a composição visual)

O `editar.py` renderiza no estúdio Remotion apontado por `STUDIO_DIR`. O padrão é `C:\Users\Admin\pab-video\video-agent\studio`.

A composição com a identidade da Aline está versionada aqui em `video/estudio/ShortAline/index.tsx`. Para montar o estúdio em outra máquina:
1. Crie um projeto Remotion (template TikTok). Ele precisa ter `@remotion/captions` e `@remotion/google-fonts`.
2. Copie a pasta `ShortAline/` para `src/`.
3. Registre as composições `ShortAline` (9:16) e `ShortAline45` (4:5) no `src/Root.tsx`, conforme `video/estudio/Root_trecho_ShortAline.tsx`.
