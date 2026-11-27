---
name: roteiro-video
description: Escreve roteiros curtos (15-30 s) de Reels e anúncio para a Dra. Aline nos 5 ângulos do nicho pós-emagrecimento / Método Fênix, com 3 ganchos cada, dentro das regras da Meta e dos conselhos. Use quando pedirem "roteiro", "ideias de vídeo", "o que gravar", "ganchos", "script do reels".
---

# Roteiros de vídeo da Dra. Aline

Base: `docs/ESTUDO_DE_MERCADO.md` (seções 3, 5 e 6) e `video/ganchos_exemplo.json`.

## Os 5 ângulos
1. **Nomear o problema:** "Isso tem nome: derretimento facial. E não é só flacidez."
2. **Contra o óbvio:** encher o rosto depois de emagrecer pode deixar artificial; primeiro sustentação.
3. **Momento certo:** "Quem está emagrecendo com caneta sempre pergunta: trato o rosto agora ou espero?"
4. **Método Fênix como plano:** 3 sinais de perda de sustentação; avaliação em etapas.
5. **Prova social:** relato de paciente com autorização e sem promessa, ou bastidor da avaliação em Santos.

## Formato de entrega (para cada roteiro)
- **Ângulo e duração alvo** (15, 20 ou 30 s).
- **3 ganchos para os 2 primeiros segundos.** Cada um tem kicker de 1 a 3 palavras e texto curto com `*destaque*`. Já entregue no JSON que o `video/editar.py --ganchos` lê.
- **Fala:** frases curtas, uma por linha, como ela falaria.
- **Indicação de cena:** onde aponta no rosto, onde mostra a clínica, quando olha para a lente.
- **CTA final:** "Avaliação em Santos, chama no WhatsApp" (o card final do vídeo já mostra o número).
- **Legenda do post:** 2 a 4 linhas e hashtags.

## Regras (inegociáveis)
- **Terceira pessoa ou pergunta frequente.** Nunca "você + condição de saúde ou idade".
  - Errado: "Você emagreceu e seu rosto caiu?"
  - Certo: "Quando o emagrecimento é rápido, o rosto pode perder sustentação."
- **Sem marca de remédio ou produto:** nada de Ozempic, Mounjaro ou marca de preenchedor. Usar "canetas emagrecedoras".
- **Sem promessa de resultado,** "o melhor", "garantido", preço, promoção ou pacote no vídeo e no anúncio.
- **Sem cena de procedimento em andamento.** Antes e depois nunca lado a lado; só close de evolução, com termo de consentimento e `--aviso`.
- **Método Fênix** é protocolo de avaliação e planejamento com procedimentos reconhecidos, não "técnica nova".
- **Profissão e número do conselho** na legenda (está em `video/config_video.json`, campo `registro`).

## Tom
Elegante, acolhedor, seguro: especialista que explica sem jargão. Nada de sensacionalismo nem de autoimagem negativa ("rosto horrível", "envelhecida").
