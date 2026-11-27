---
name: estrategista
description: Estratégia e estruturação da clínica da Dra. Aline: organograma, jornada da paciente (fluxograma), POPs com mensagens prontas, indicadores, rotina e plano de implantação. Use quando pedirem "estrategista", "estrutura a clínica", "POP", "organograma", "fluxograma", "processo de atendimento", "por que a paciente não fecha", "a clínica depende de mim".
---

1. Delegue ao agente `estrategista-clinica` (`.claude/agents/estrategista-clinica.md`) com o pedido e o contexto da conversa.
2. Se já houver uma versão, ele atualiza `docs/ESTRATEGIA_CLINICA.md` em vez de começar do zero. Hipóteses confirmadas viram fato e saem do rótulo "HIPÓTESE".
3. Os POPs de atendimento precisam bater com o robô (`config/automacoes.json`): as mesmas etapas do funil e as mesmas palavras-chave.
4. Os indicadores vêm do painel (`python painel/gerar_painel.py --resumo`) quando houver dado real.
5. Entregue um resumo de 5 linhas e aponte o arquivo. Não despeje o documento inteiro na conversa.
