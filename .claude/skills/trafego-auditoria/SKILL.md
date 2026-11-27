---
name: trafego-auditoria
description: Audita as campanhas que já estão rodando na conta da Dra. Aline e entrega o diagnóstico com prova, ação e comandos prontos. Use quando pedirem "audita", "analisa as campanhas", "o que está errado", "otimiza o que já roda", "por que está caro", ou na primeira conversa depois que o acesso for liberado.
---

1. Rode `python trafego/auditoria.py` (30 dias) e `python trafego/auditoria.py --periodo 7d`. O de 7 dias mostra se algo piorou de repente.
2. Gere o painel: `python painel/gerar_painel.py`. Abra `painel/saida/painel.html` se for mostrar a alguém.
3. Leia o relatório salvo em `relatorios/AUDITORIA_<data>.md` e filtre com bom senso:
   - Anúncio "ruim" que é o único do conjunto não se pausa antes de ter substituto.
   - Nada com menos de 7 dias de vida é julgado.
   - Não mexa de novo no que aparece no `relatorios/historico_acoes.log` dos últimos 3 dias.
4. Entregue nesta ordem:
   - **Uma frase de diagnóstico:** "A conta gasta R$ X/mês, a conversa sai a R$ Y; o maior vazamento é Z."
   - **Os 3 a 5 achados que mais pesam em dinheiro**, cada um com prova (número), ação e efeito esperado.
   - **Pacote de mudanças da semana**, em tabela: o quê, ação, por quê, efeito no gasto/dia.
   - **Textos que precisam ser reescritos:** já traga a versão nova, dentro das regras (`/trafego-copy`).
   - **Vídeos que precisam de gancho novo:** já traga 3 ganchos por vídeo (`/roteiro-video`).
5. Pergunte "Posso aplicar?". Só com o OK, rode os comandos com `--confirmo`.
6. Marque a revisão para 7 dias depois (mesmos comandos, para comparar).
