# Tráfego, painel e atendimento: Dra. Aline Albuquerque

Esta pasta é a central de marketing da **Dra. Aline Albuquerque**, @dra.alinealbuquerque, harmonização facial em Santos/SP.
- **Nicho:** derretimento facial depois do emagrecimento.
- **Produto próprio:** Método Fênix (facial e corporal).

Quem opera é a equipe do Weverton (Casal da IA / PAB). A Aline é a cliente. Fale simples, em português, com números em reais.

## Antes de qualquer coisa
1. Leia `config/negocio.json` (oferta, público, ticket, metas, o que nunca dizer) e `docs/ESTUDO_DE_MERCADO.md` (benchmarks e regras de publicidade).
2. Sem `config/.env`? Siga `docs/COMO_LIBERAR_ACESSO_META.md`.

## Situação atual: ela JÁ TEM campanha rodando
A prioridade é **otimizar o que está no ar**, não criar do zero.
- Primeiro passo, assim que o acesso for liberado: `python trafego/auditoria.py`. O relatório sai em `relatorios/AUDITORIA_<data>.md`.
- Depois, aplicar as mudanças da semana com OK.
- Campanha nova só para o que a auditoria apontar como faltando (por exemplo, remarketing ou um ângulo novo).

## As 4 peças
| Peça | O que faz | Como roda |
|---|---|---|
| `trafego/auditoria.py` | Auditoria das campanhas que já rodam: o que está errado, a prova e a ação | `python trafego/auditoria.py [--periodo 7d]` |
| `trafego/painel.py` | Cria campanha (sempre pausada), relatório, diagnóstico, liga e pausa, muda verba | `python trafego/painel.py <comando>` |
| `painel/` | Painel visual completo (vídeo campeão, funil até paciente, horários, público, x mercado) | `python painel/gerar_painel.py [--demo] [--resumo]` |
| `atendimento/` | Central estilo ManyChat: comentário, Direct, story, robô de qualificação, funil kanban | ver `docs/ATENDIMENTO_INSTAGRAM.md` |
| `video/` | Editor de vídeo com a marca dela e variações de gancho para teste | `python video/editar.py <take> --slug x` (`video/LEIA.md`) |

Não chame a API da Meta por fora dessas ferramentas.

## Regras de dinheiro (inegociáveis)
- **Ler é livre:** relatório, diagnóstico, painel, busca de cidade e de interesse.
- **Criar é seguro:** `criar` monta tudo **pausado**.
- **Ligar, pausar e mudar verba só com OK explícito naquela conversa.** Antes, mostre o que muda e o custo por dia e por mês. Depois do OK, rode com `--confirmo`.
- Nunca passe de `TETO_DIARIO_REAIS`.
- Escale no máximo 20% por vez, a cada 3 dias por conjunto.
- Não julgue campanha com menos de 7 dias ou com menos de 2x a meta de custo por conversa gasta.

## Regras de publicidade (anúncio reprovado ou processo no conselho custam caro)
O detalhe está em `docs/ESTUDO_DE_MERCADO.md`, seção 5.
- **Meta, antienvelhecimento:** NÃO usar antes e depois lado a lado. Só close de evolução realista.
- **Meta, atributos pessoais:** nada de "você" + condição. "Você emagreceu e seu rosto caiu?" é reprovado. Escreva em terceira pessoa: "Quando o emagrecimento é rápido, o rosto pode perder sustentação."
- **Não citar Ozempic, Mounjaro** nem nenhum remédio. Usar "canetas emagrecedoras" ou "emagrecimento rápido".
- **Sem promessa de resultado**, "o melhor", "garantido", "rejuvenesça 10 anos".
- **Sem preço, pacote ou promoção no anúncio.** Condição só no atendimento.
- **Sem vídeo do procedimento em andamento.**
- **Registro profissional:** nome + conselho + número no anúncio e na bio. O campo `registro` em `negocio.json` ainda está PENDENTE.
- **Antes e depois:** só com termo de consentimento da paciente e as legendas obrigatórias do conselho.
- **Método Fênix:** é um protocolo de avaliação e planejamento com procedimentos reconhecidos, nunca uma "técnica nova".
- **Idade mínima 18.** O padrão de público é mulheres de 30 a 60 anos.

## Como o tráfego dela funciona (use para decidir)
- **Destino padrão:** WhatsApp, oferecendo a **avaliação**. Direct do Instagram é o segundo destino: o robô de `atendimento/` qualifica.
- **Formulário:** só como teste paralelo.
- **Local:** raio de 12 a 15 km do consultório, ou as cidades da Baixada (Santos, São Vicente, Guarujá, Cubatão, Praia Grande).
- **Criativo é o que segmenta:** Reels de 15 a 30 s com ela falando para a câmera, 5 ângulos (estudo, seção 6) e 3 ganchos por vídeo (o `video/` gera as variações).
- **Fases:**
  - teste: R$ 50/dia, 6 criativos, 7 dias sem mexer;
  - corte: pausar gancho abaixo de 20% ou conversa acima de R$ 30;
  - escala: +20% a cada 3 dias;
  - remarketing: R$ 15/dia para quem engajou ou viu 50% do vídeo.
- **O que manda é paciente fechado, não conversa barata.** Compare o custo por paciente com o ticket: o saudável é ficar abaixo de 30%. O painel faz essa conta quando a central de atendimento registra os fechamentos.

## Onde fica cada coisa
- `config/`:
  - `.env`: chaves; nunca mostrar nem enviar.
  - `negocio.json`, `marca.json` (cores), `benchmarks.json`, `automacoes.json` (robô).
- `campanhas/`: planos JSON e os `.criado.json` com os IDs.
- `criativos/`: mídia para anúncio. `video/saida/`: vídeos editados.
- `relatorios/`: relatórios e `historico_acoes.log`.
- `painel/saida/painel.html`: o painel gerado.

## Comandos rápidos (skills)
- **Tráfego:** `/trafego-auditoria` (comece por aqui), `/trafego-relatorio`, `/trafego-otimizar`, `/trafego-campanha`, `/trafego-copy`, `/trafego-leads`.
- **Vídeo:** `/editar-video`, `/roteiro-video`.
- Para conversas longas de tráfego, use o agente `gestor-trafego`.
