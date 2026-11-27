---
name: editar-video
description: Edita vídeo da Dra. Aline (Reels, Stories, anúncio) com a identidade dela - legenda, cortes, gancho, destaques, card final e variações de gancho para teste A/B. Use quando pedirem "edita esse vídeo", "faz o reels", "monta o anúncio", "variações de gancho", "corta e legenda".
---

# Editar vídeo da Dra. Aline

Ferramenta: `python video/editar.py "<take>" --slug <nome-curto>` (opções em `video/LEIA.md`). Não monte edição à mão por fora disso.

## Passo a passo

1. **Entenda o vídeo.**
   - Qual ângulo (1 a 5 em `video/ganchos_exemplo.json`)?
   - É para anúncio (15 a 30 s, `--max-ganchos 3`) ou para o orgânico (1 gancho)?
   - Aparece paciente ou antes e depois? Se sim, use `--aviso` e confirme que existe termo de consentimento.
   - Se não souber o ângulo, ouça a transcrição primeiro com `--so-preparar` e escolha.
2. **Confira `video/config_video.json`.** Se `registro` ainda tiver PREENCHER, avise que a linha de profissão e conselho fica de fora e peça o dado.
3. **Ganchos novos:** se os do arquivo não servem para este vídeo, crie um JSON com 3 ganchos (formato `{"ganchos":[{"kicker":"...","text":"... *destaque* ..."}]}`), usando a skill `roteiro-video`.
4. **Rode o pipeline com `--amostras`.** Formato: `ambos` para anúncio, `9x16` para Reels orgânico.
5. **Revise de verdade:** abra (Read) as imagens de `video/saida/<slug>/amostras/` e confira:
   - legenda fora do rosto e legível;
   - gancho sem cortar palavra;
   - destaques fazendo sentido no momento em que aparecem;
   - card final com o WhatsApp certo;
   - acentos corretos.
   Se algo estiver errado, ajuste o `edit_g*.json` (ou `public/aline-<slug>_g*.edit.json` no estúdio) e renderize de novo só aquele, com `npx remotion render ShortAline ...` em `C:\Users\Admin\pab-video\video-agent\studio`.
6. **Regras de publicidade.** Confira o checklist do `post.md` contra o vídeo e o texto:
   - sem antes e depois lado a lado;
   - sem "você + condição" no texto do anúncio;
   - sem marca de remédio (Ozempic, Mounjaro);
   - sem promessa de resultado, preço ou promoção;
   - sem procedimento em andamento.
   Detalhes em `docs/ESTUDO_DE_MERCADO.md`, seção 5.
7. **Entregue** com o caminho completo dos mp4, as 3 opções de legenda do `post.md` e qual gancho é qual (g1, g2, g3), lembrando de subir as versões no mesmo conjunto com o sufixo no nome.

## Não fazer

- Não publicar nem enviar o vídeo para ninguém sem pedido explícito.
- Não pôr música, efeito sonoro ou moldura fixa sem pedido. O padrão é limpo e elegante.
- Não inventar as etapas do Método Fênix. As do ângulo 4 são exemplo até a Aline confirmar.
