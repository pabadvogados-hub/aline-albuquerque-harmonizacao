# Central de atendimento do Instagram (estilo ManyChat)

A central responde sozinha quem comenta, manda Direct, marca a Dra. no story ou chega por
anúncio. Ela faz 4 perguntas de qualificação, manda o botão do WhatsApp com o resumo das
respostas e organiza todo mundo num funil. A equipe acompanha e responde pela tela web.

Para ligar é preciso: um app da Meta, as permissões, o webhook assinado e um servidor com
HTTPS. A configuração é feita uma vez só e leva cerca de 40 minutos.

---

## 1. O que precisa estar pronto antes

- **Instagram profissional** (Empresa ou Criador de conteúdo) **ligado à Página do Facebook**
  da clínica. Confira no app do Instagram em *Configurações > Central de contas*.
- **Business (Gerenciador de Negócios) da clínica** com a Página e o Instagram dentro dele.
- No app do Instagram, ligue **Configurações > Mensagens e respostas a stories > Ferramentas
  conectadas > Permitir acesso às mensagens**. Sem isso a Meta não entrega Direct para a
  central.

## 2. Criar o app da Meta

1. Acesse <https://developers.facebook.com/apps> e clique em **Criar app**, tipo **Empresa**.
   Use o nome `Atendimento Dra Aline` e **vincule o app ao Business da clínica**.
2. Adicione os produtos **Messenger** e **Instagram** (API do Instagram com login do Facebook).
3. Em **Configurações > Básico**, copie a **Chave secreta do app** para `META_APP_SECRET`.

### Acesso Padrão x Acesso Avançado (App Review)

- Se o app é **do Business da própria clínica** e quem administra a Página e o Instagram tem
  função no app (administrador), o **Acesso Padrão basta**. Não precisa passar pela revisão
  da Meta.
- O **Acesso Avançado** (App Review, com vídeo de demonstração) só é necessário quando o
  mesmo app vai atender contas de **outros** negócios, por exemplo um app da PAB servindo
  várias clínicas.

## 3. Permissões

Gere o token pelo **usuário do sistema** do Business, com validade **Nunca**, marcando:

| Permissão | Para quê |
|---|---|
| `instagram_basic` | ler o perfil e os posts |
| `instagram_manage_messages` | ler e responder o Direct |
| `instagram_manage_comments` | ler comentários e responder em público ou no privado |
| `pages_messaging` | enviar mensagens (Instagram e Messenger saem pela Página) |
| `pages_manage_metadata` | assinar o webhook da Página |
| `pages_read_engagement` | ler comentários da Página do Facebook |
| `pages_show_list` | listar a Página |
| `business_management` | ativos do Business |

Para chegar ao **token da Página**, chame `GET /me/accounts` com o token do usuário do
sistema e copie o `access_token` da Página da clínica para `ATEND_PAGE_TOKEN`. O id da Página
vai em `META_PAGE_ID`. O id do Instagram (`instagram_business_account`) vai em
`META_IG_USER_ID`.

## 4. Webhook

1. No app, em **Webhooks**:
   - **URL de retorno:** `https://atendimento.SEUDOMINIO.com.br/webhook`
   - **Verificar token:** o mesmo texto que você colocou em `ATEND_VERIFY_TOKEN`
2. Assine estes campos:
   - **Instagram:** `comments`, `messages`, `messaging_postbacks` e `messaging_referral`.
     Menção em story e resposta a story chegam dentro de `messages`.
   - **Página:** `messages`, `messaging_postbacks`, `messaging_referral` e `feed` (este último
     traz os comentários do Facebook).
3. Ligue a Página ao app (*Inscrever*) pelo painel do Messenger, ou com
   `POST /{page_id}/subscribed_apps?subscribed_fields=messages,messaging_postbacks,messaging_referral,feed`
   usando o token da Página.

Toda chamada que chega é conferida pela assinatura `X-Hub-Signature-256`, usando o
`META_APP_SECRET`. Chamada sem assinatura válida é recusada (403).

## 5. Onde hospedar

A Meta só entrega webhook em **HTTPS com certificado válido**. O caminho recomendado é uma
**VPS** (pode ser a mesma do sistema PAB) com nginx e certbot.

Exemplos prontos (não foram executados em servidor nenhum):

- `atendimento/deploy/aline-atendimento.service`: serviço systemd. Rode com **1 worker**,
  porque a fila de eventos e o SQLite são de um processo só.
- `atendimento/deploy/nginx-atendimento.conf`: proxy HTTPS para a porta 8077.

Para subir:

```
python -m venv /opt/aline/venv
/opt/aline/venv/bin/pip install -r atendimento/requirements.txt
# preencher atendimento/.env (modelo em atendimento/.env.example)
systemctl enable --now aline-atendimento
```

## 6. Variáveis (`atendimento/.env` ou `config/.env`)

O modelo completo está em `atendimento/.env.example`:

| Variável | O que é |
|---|---|
| `ATEND_SENHA` | senha da tela da central |
| `ATEND_VERIFY_TOKEN` | texto combinado com o painel do webhook |
| `META_APP_SECRET` | chave secreta do app (confere a assinatura) |
| `ATEND_PAGE_TOKEN` | token da Página (envia as mensagens) |
| `META_IG_USER_ID`, `META_PAGE_ID` | para o robô não responder a própria clínica |
| `ATEND_NOTIFICAR_URL` | opcional: recebe um POST quando um lead fica qualificado |
| `ATEND_SIMULAR` | `1` = nada sai para a Meta (testes) |

## 7. Testar sem mexer no Instagram de verdade

```
cd atendimento
set ATEND_SIMULAR=1
set ATEND_SENHA=teste
python -m uvicorn app:app --port 8077
# em outro terminal
python atendimento/simular.py           # cria cerca de 40 contatos de demonstração e simula todos os gatilhos
```

Depois abra <http://127.0.0.1:8077> (senha `teste`). Antes de ligar de verdade, apague os
dados de demonstração:

```
python atendimento/simular.py --limpar-demo
```

## 8. Regras da Meta que a central já respeita

- **Resposta privada a comentário:** 1 por comentário, até 7 dias depois dele. A central
  nunca responde o mesmo comentário duas vezes.
- **Janela de 24h:** o robô só fala com quem acabou de mandar mensagem.
  - Na tela, a resposta manual dentro das 24h sai normal.
  - Entre 24h e 7 dias, sai com a etiqueta `HUMAN_AGENT`, que é só para atendimento humano.
  - Depois de 7 dias, a central bloqueia o envio.
- **Quem só comentou** recebe uma resposta privada. O Direct só libera de verdade quando a
  pessoa responde.
- **Sem disparo em massa:** não existe botão de "enviar para todos". Isso derruba a conta.
- **Humano no controle:** quando a equipe responde pela central ou pelo app do Instagram, o
  robô fica calado com aquela pessoa por 12h. Pela tela dá para pausá-lo de vez.
- **Fora do expediente:** o robô avisa uma vez que a equipe responde quando abrir e segue
  com as perguntas.

## 9. Como mudar as respostas

- **Pela tela Automações:** ligar e desligar, palavras-chave, respostas públicas, texto do
  Direct e botões.
- **No arquivo `config/automacoes.json`:** tudo o que a tela muda, mais as perguntas do fluxo
  de qualificação e o expediente. O arquivo explica cada campo nos itens `_leia`.

Não dá para pôr preço no comentário público, nem promessa de resultado ou "antes e depois"
em mensagem automática. São regras do conselho profissional e da Meta.
