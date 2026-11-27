---
name: trafego-campanha
description: Monta uma campanha nova de anúncios para a Dra. Aline (avaliação do Método Fênix), do briefing até deixar pronta (pausada). Use quando pedirem "cria uma campanha", "sobe um anúncio", "campanha de remarketing". As campanhas que já rodam passam primeiro pela /trafego-auditoria.
---

## 1. Briefing (pergunte só o que não estiver em `config/negocio.json`)
- Qual oferta? (Fênix facial, Fênix corporal, remarketing; uma por campanha)
- Quanto por dia? (respeitar `TETO_DIARIO_REAIS`)
- Só a cidade base com raio, ou outras cidades?
- Tem vídeo? Se não, passe roteiro (`/roteiro-video`); vídeo cru passa no `/editar-video` (3 ganchos por vídeo).
- WhatsApp (padrão), Direct (o robô qualifica) ou formulário?

## 2. Plano
- Copie `campanhas/EXEMPLO_plano_fenix.json` para `campanhas/plano_<oferta>_<aaaa-mm>.json`.
- Nome da campanha começa com `[AGENTE]` para ficar claro o que foi criado aqui.
- Cidades: `python trafego/painel.py cidade "<nome>"` e coloque a `key` no plano.
- Estrutura padrão para começar:
  - 1 conjunto, mulheres 30-60, raio de 12-15 km do consultório (`local_raio`) ou as cidades da Baixada, Advantage+, de 4 a 6 anúncios em ângulos diferentes
  - opcional: um 2º conjunto com interesse (`python trafego/painel.py interesse "<termo>"`) para comparar
  - orçamento: R$ 50/dia no teste (estudo de mercado); remarketing R$ 15/dia; nunca abaixo de R$ 20/dia por conjunto de prospecção
- Textos: siga `/trafego-copy`. O registro profissional vai no campo `descricao`.
- Mídia: arquivos em `criativos/`; o caminho no plano é relativo à raiz da pasta.

## 3. Mostre o plano
Em linguagem simples: oferta, onde aparece, para quem, quanto por dia e no mês, e os textos. Ajuste o que pedirem.

## 4. Criar (pausado)
`python trafego/painel.py criar campanhas/plano_<...>.json`
Isso cria tudo **pausado** e grava os IDs em `campanhas/plano_<...>.criado.json`. Dá para conferir no Gerenciador de Anúncios.

## 5. Ligar (só com OK)
Depois do "pode ligar", ative campanha, conjuntos e anúncios (IDs no `.criado.json`) com `ativar <id> --confirmo`. Lembre que a Meta revisa o anúncio antes de rodar (em geral até 24h) e marque de olhar o primeiro resultado em 7 dias.
