---
name: trafego-relatorio
description: Relatório de como estão os anúncios da Dra. Aline (gasto, conversas, custo, vídeo campeão, avaliações e pacientes) e o que fazer a seguir. Use quando perguntarem "como estão os anúncios", "quanto gastou", "quantas conversas", "relatório", "resultado da semana", "manda o resumo".
---

1. **Período:** se não disseram, use os últimos 7 dias.
2. **Rode:**
   - `python painel/gerar_painel.py --resumo`: gera o painel completo e imprime o resumo em texto, pronto para WhatsApp.
   - `python trafego/painel.py diario --periodo last_14d`, para ver a tendência.
3. **Responda curto, neste formato:**
   - **Resumo em uma frase.** Exemplo: "Semana boa: 62 conversas a R$ 12,84, abaixo da meta de R$ 18."
   - Investido, conversas, conversas reais e custo por conversa, comparados com a meta e com o mercado.
   - **Vídeo campeão** e **pior anúncio**, cada um com o motivo provável (gancho, retenção, frequência).
   - Avaliações agendadas, pacientes e retorno (ROAS), se a central de atendimento estiver ligada.
   - **Uma recomendação.** Se mexer em verba, peça o OK (`/trafego-otimizar`).
4. **Para mandar à Aline:** o texto do `--resumo` e o arquivo `painel/saida/painel.html`.
