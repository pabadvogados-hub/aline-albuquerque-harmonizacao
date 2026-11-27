---
name: trafego-otimizar
description: Otimiza as campanhas da Dra. Aline. Decide o que pausar, trocar e escalar, e aplica só depois do OK. Use quando pedirem "otimiza", "o que eu faço", "tá caro", "posso aumentar", "pausa o que não funciona".
---

1. **Diagnóstico:** rode `python trafego/auditoria.py --periodo 7d` e `python trafego/painel.py diagnostico --periodo last_7d`. Se alguma campanha tiver menos de 7 dias, trate os números dela com cautela.
2. **Histórico:** leia `relatorios/historico_acoes.log` e não mexa de novo no que foi alterado nos últimos 3 dias.
3. **Filtro de gestor:** a regra é ponto de partida, não ordem. Anúncio ruim que é o único do conjunto só sai quando o substituto já estiver no ar.
4. **Mostre a tabela:**

   | O quê | Ação | Por quê | Efeito no gasto/dia |
   |---|---|---|---|

   Junto, o total por dia e por mês, antes e depois.
5. **Pergunte:** "Posso aplicar?". Pode ser tudo ou só algumas linhas.
6. **Aplique:** só depois do OK, rode com `--confirmo` e confirme o que foi feito.
7. **Criativo novo:** quando a ação for trocar criativo ou gancho, entregue junto 2 ou 3 anúncios novos (`/trafego-copy`) ou 3 ganchos para regravar (`/roteiro-video`). O vídeo regravado passa pelo `/editar-video`.
