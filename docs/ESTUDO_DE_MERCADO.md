# Estudo de mercado: tráfego pago em harmonização facial (nicho pós-emagrecimento)

Feito em 26/11/2026 para a campanha da Dra. Aline Albuquerque (Santos, Método Fênix).

**Antes de tudo:** falta confirmar o conselho profissional dela (CRBM, CRO ou CRM). É ele que define o que o anúncio pode mostrar (seção 5).

**Limites deste estudo:**
- A Biblioteca de Anúncios da Meta bloqueia leitura automática. Por isso não está confirmado quais perfis abaixo estão anunciando agora; o que se diz de cada um vem do site deles, de casos publicados ou de reportagens.
- Os benchmarks são publicados pelas próprias agências. Servem como ordem de grandeza.

## 1. Referências do mercado

### Nicho pós-emagrecimento ("rosto de Ozempic")

1. **Dr. Thiago Perfeito** (médico, CRM-DF 23199, Brasília).
   - Tem um conjunto de páginas sobre "Ozempic face" para aparecer no Google.
   - O botão "Agendar Consulta" pelo WhatsApp aparece várias vezes em cada página.
   - Também vende um guia de R$ 97.
   - Ângulo: "repor volume em face deflacionada pode gerar resultado artificial". Vende protocolo combinado e não mostra preço.
   - Público: 45 a 60 anos.
2. **Dra. Stephanie Mansan** (médica, São Paulo, Tatuapé).
   - Usa WhatsApp com a mensagem já escrita ("Quero avaliar o meu rosto").
   - Abre com "Emagreceu e sente que o rosto caiu?".
   - Mostra o preço da avaliação (R$ 400, descontado depois). Como médica, pode.
3. **Roberta Boff** (biomédica, Porto Alegre).
   - Página "face derretida" com vários botões de WhatsApp e de ligação.
   - Ângulo: "o problema é sustentação, não só pele". Vende a avaliação como porta de entrada.
   - Fala das canetas sem culpar o remédio.
4. **Maíra Platero** (harmonização odontológica, Moema, São Paulo).
   - Trabalha o termo "derretimento facial" no Google, com WhatsApp flutuante.
   - Ponto fraco: o texto não termina chamando para a consulta.

### Clínicas e redes com muito tráfego

5. **Face Doctor Piedade (Recife).** Caso publicado pelo próprio WhatsApp Business.
   - Trocou arte estática por Reels que levam direto ao WhatsApp, gravados pela própria equipe.
   - Montou funis separados para antes da reserva, antes da visita e pós-venda, mais remarketing.
   - Resultado: cerca de 1.200 conversas por mês e o dobro de clientes novos.
   - **De 35% a 45% das conversas viram agendamento; no remarketing, 50%.**
6. **Royal Face** (cerca de 323 unidades). Usa celebridades como sócios e garotos-propaganda.
7. **Botoclinic** (mais de 160 unidades). Não há dados públicos dos anúncios.
8. **Clínica Lucas Miranda.** Robô no WhatsApp que filtra o lead antes da equipe atender: 30% menos trabalho. Campanha de aniversário para a base: +40% de receita.
9. **Botopremium / Dr. Alan Macário.**
   - Funil: resposta imediata, roteiro de vendas, **sinal pago para reservar o horário** e lembretes automáticos.
10. **Perfis grandes** (números não verificados): Dr. Igor Alves (@igoorcostalves) e Fernanda Figueiredo (@drafernandafigueiredo).

**Em Santos:** não apareceu nenhum concorrente posicionado em "pós-emagrecimento". Parece haver espaço livre, mas falta conferir na Biblioteca de Anúncios, logado.

## 2. Estrutura de campanha que o nicho usa

- **Objetivo:** campanha de mensagens no WhatsApp, oferecendo a avaliação.
  - Formulário instantâneo pode sair até 24% mais barato por contato (dado da Meta citado pela Clint). Em compensação, mensagem atrai mais quem "só pergunta o preço".
  - Vale testar os dois. Mandar para o site não é recomendado.
- **Segmentação:**
  - Raio de 5 a 15 km do consultório.
  - Idade de 28 a 55 anos (mínimo de 18 exigido pela Meta).
  - Público Advantage+ ou interesses de beleza e bem-estar.
  - Depois, públicos semelhantes (lookalike) a partir de quem já conversou.
  - O criativo pesa mais que a segmentação.
- **Orçamento por fase:** aprendizado R$ 25 a 35/dia; otimização R$ 40 a 60/dia; escala R$ 70 a 100/dia.
  - Mínimo útil: R$ 2.000 a 3.000/mês.
  - A agenda costuma ficar constante a partir da 3ª ou 4ª semana.
- **Ritmo:** 2 ou 3 criativos por campanha e 7 dias sem mexer.
  - Fases: teste, escala dos vencedores, remarketing para quem viu o vídeo ou interagiu com o perfil.

## 3. Criativos

- **Formato:** Reels vertical de 15 a 30 segundos, com ela falando para a câmera, mostrando o consultório e explicando sem prometer resultado.
- **Gancho dos 3 primeiros segundos:** quebrar uma crença.
  - "Encher o rosto depois de emagrecer pode deixar artificial."
  - "O problema é sustentação, não só pele."
- **Chamada:** específica ("Quero avaliar meu rosto"), com a mensagem do WhatsApp já escrita.
- **Não fazer:** vídeo do procedimento em andamento (CFO e CFBM proíbem).

## 4. Benchmarks (usados em `config/benchmarks.json`)

| Métrica | Faixa | Fonte |
|---|---|---|
| Custo por conversa no WhatsApp (estética) | R$ 8 a 25 | Trafius 2026 |
| Exemplo real de avaliação facial | R$ 600/mês, R$ 12 por conversa, 50 conversas, 20 avaliações | Valor Final |
| CPM | Feed R$ 15 a 35; Stories e Reels R$ 8 a 20; saúde R$ 30 a 60 | Trafius |
| CTR | abaixo de 0,8% é alerta; normal entre 0,95% e 1,6% | Trafius |
| Gancho (3 s ÷ impressões) | média 25%; saúde e beleza 28%; bom acima de 30%; ruim abaixo de 21% | Billo, 2026 |
| Retenção (assistiu até o fim ÷ 3 s) | média 40 a 50%; fraco abaixo de 25 a 30% | Motion, Vaizle, Billo |
| Conversa → agendamento | média 30 a 35%; bom acima de 40% | Maganha, Face Doctor |
| Agendou → compareceu | média 60 a 65%; bom acima de 70% | Maganha |
| Compareceu → fechou | média 35 a 45%; bom acima de 50% | Maganha |
| Ticket | full face R$ 6 a 15 mil; parcial R$ 3 a 7 mil; avaliação R$ 200 a 600 | Catraca Livre 2026 |
| Caso completo | R$ 7.280 de mídia, 295 contatos, 92 agendados, 38 compareceram, 21 fecharam, ticket R$ 3.979 | Odonto Results, set/2025 |

## 5. O que pode e o que não pode (para não tomar bloqueio)

### Meta: política de Saúde e Bem-estar (22/07/2026)
- Público mínimo de 18 anos.
- **Em antienvelhecimento (toxina, preenchedores), antes e depois lado a lado é proibido.** Só vale close mostrando evolução realista.
- Proibido explorar insegurança ou autoimagem negativa.
- **Não citar "Ozempic" nem "Mounjaro" no anúncio:** usar "canetas emagrecedoras" ou "emagrecimento rápido".

### Meta: atributos pessoais
- Não pode "você" junto com condição de saúde ou idade.
- **"Você emagreceu e seu rosto caiu?" tende a ser reprovado.**
- Escrever em terceira pessoa: "Quando o emagrecimento é rápido, o rosto pode perder sustentação."

### CFBM (se for biomédica, Res. 330/2020)
- O anúncio traz nome, número no CRBM, habilitação e endereço.
- Antes e depois só com termo de consentimento (TCLE) e duas legendas obrigatórias:
  - "Esta imagem não representa, em hipótese alguma, garantia de resultado. Cada ser humano tem características anatômicas e fisiológicas únicas."
  - "Divulgação autorizada pelo usuário."
- Proibido:
  - Promessa de resultado.
  - "O melhor".
  - Pacotes, promoções e preço para atrair.
  - Marca de produto.
  - Vídeo do procedimento em andamento.
  - Expor paciente para divulgar "técnica ou método" não comprovado.
- **Método Fênix:** apresentar como protocolo de avaliação e planejamento com procedimentos reconhecidos, nunca como técnica nova.
- Pena: multa de até 5 anuidades e/ou suspensão de até 12 meses.

### CFO (se for dentista, Res. 196/2019)
- Antes e depois e selfie só com TCLE.
- Proibido vídeo do procedimento em andamento.
- Nome e número no CRO obrigatórios.
- Sem sensacionalismo e sem promessa de resultado.
- Atenção: em 19/08/2026 o TRF1 anulou a Res. 198/2019, que criava a especialidade de harmonização orofacial, e ainda cabe recurso. Rever o uso de "especialista em HOF".

### CFM (se for médica, Res. 2.336/2023)
- Antes e depois educativo, mostrando também evoluções ruins e complicações, sem identificar o paciente.
- Pode divulgar o preço da consulta.

### "Dra."
- Não há norma que proíba. O risco é parecer médica: sempre colocar a profissão e o número do registro ao lado.

## 6. Plano para a Aline

### Cinco ângulos (ganchos já ajustados às regras)
1. "Isso tem nome: derretimento facial. E não é só flacidez." Ela mostra no próprio rosto onde o volume esvazia.
2. "Encher o rosto depois de emagrecer pode deixar tudo mais artificial." Em seguida, o que fazer no lugar: sustentação primeiro.
3. "Quem está emagrecendo com caneta sempre me pergunta: trato o rosto agora ou espero?"
4. "Os 3 sinais de que o rosto perdeu sustentação, não só volume." O Fênix aparece como avaliação em etapas.
5. Paciente contando como se sentiu, sem números nem promessa. Ou close de evolução com as legendas obrigatórias. Fecha com "Avaliação em Santos".

### Público e verba
- Mulheres de 30 a 60 anos, em Santos, São Vicente, Guarujá, Cubatão e Praia Grande (ou raio de 12 a 15 km do consultório).
- Comparar Advantage+ com um conjunto aberto (só cidade e idade).
- **Verba inicial: R$ 50 a 70/dia (R$ 1.500 a 2.100/mês).**
- Conta estimada:
  - R$ 1.800 a R$ 18 por conversa: cerca de 100 conversas.
  - Cerca de 30 avaliações, 18 comparecimentos e 7 a 9 fechamentos.
  - Com ticket de R$ 3 a 6 mil, o retorno fica entre 10 e 25 vezes. É estimativa.

### Plano de 30 dias
- **Dias 0 a 3 (preparação):**
  - Gravar de 6 a 8 Reels.
  - Colher os termos de consentimento.
  - Deixar a mensagem do WhatsApp já escrita.
  - Definir a pergunta de qualificação ("quanto emagreceu e em quanto tempo").
  - Cobrar sinal ou avaliação com valor descontado depois. Preço só no WhatsApp, nunca no anúncio.
- **Dias 1 a 10 (teste):**
  - Mensagens para o WhatsApp, 1 conjunto, 6 criativos, R$ 50/dia.
  - Opcional: R$ 15/dia em formulário para comparar.
  - Não mexer por 7 dias.
- **Dias 11 a 20 (corte):**
  - Pausar criativo com gancho abaixo de 20% ou conversa acima de R$ 30.
  - Fazer 3 variações do ângulo que ganhou.
  - Subir a verba cerca de 20% a cada 3 ou 4 dias.
- **Dias 21 a 30 (escala e remarketing):**
  - Remarketing de R$ 15/dia para quem interagiu nos últimos 30 a 60 dias ou viu metade do vídeo.
- **Regra de saúde:** custo por paciente abaixo de 30% do ticket.

## Fontes
- https://trafius.com.br/blog/campanha-de-mensagens-no-whatsapp-fluxo-e-metricas
- https://trafius.com.br/blog/benchmark-de-cpm-no-brasil-em-2026-por-nicho
- https://www.clint.digital/blog/?p=3691
- https://valorfinal.com.br/cursos/trafego-pago/estrategia-por-tipo-de-negocio/clinica-estetica-saude
- https://whatsappbusiness.com/pt-br/blog/face-doctor-piedade-business-growth-whatsapp/
- https://sleekflow.io/pt-br/customer-stories/clinica-lucas-miranda
- https://descomplicads.com.br/blog/trafego-pago-para-harmonizacao-facial/
- https://thiagomaganha.com.br/marketing-para-harmonizacao-facial/
- https://blog.odontoresults.com.br/post/depoimento-odonto-results-case-cliente-dobrou-faturamento-captao-digital
- https://dralanmacario.com/clinica-100-mil-ao-mes/
- https://drthiagoperfeito.com.br/conteudos/flacidez-pos-ozempic-rosto/
- https://www.drastephaniemansan.com.br/blog/rosto-de-ozempic/
- https://www.robertaboff.com.br/face-derretida-como-recuperar-o-contorno-facial
- https://mairaplatero.com.br/estetica/derretimento-facial-o-que-e/
- https://billo.app/blog/hook-rate-to-hold-rate
- https://catracalivre.com.br/saude-bem-estar/quanto-custa-fazer-uma-harmonizacao-facial-em-2026/
- https://transparency.meta.com/policies/ad-standards/content-specific-restrictions/cosmetic-procedures-and-wellness
- https://transparency.meta.com/pt-br/policies/ad-standards/objectionable-content/privacy-violations-personal-attributes/
- https://cfbm.gov.br/wp-content/uploads/2020/11/RESOLUCAO-CFBM-No-330-DE-05-DE-NOVEMBRO-DE-2020.pdf
- https://website.cfo.org.br/wp-content/uploads/2019/01/Resolu%c3%a7%c3%a3o-CFO-196-2019.pdf
- https://portal.cfm.org.br/noticias/cfm-atualiza-resolucao-da-publicidade-medica
- https://www.jb.com.br/colunistas/voce-tem-direito/2026/10/1061302-harmonizacao-orofacial-a-resolucao-caiu-a-duvida-ficou.html
