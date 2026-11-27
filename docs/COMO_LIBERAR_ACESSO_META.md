# Como liberar o acesso da Meta (Dra. Aline → nossa equipe)

As campanhas da Aline já estão rodando. Para otimizar, precisamos **ler** a conta de anúncios, a página e o Instagram dela. Para mexer (pausar, trocar verba, subir criativo), precisamos também **gerenciar**. Tudo isso só depois do OK dela.

Leva uns 10 minutos e é feito uma vez só. Ela **não passa senha**: só compartilha os ativos com o nosso Business como **parceiro**. Ela pode tirar o acesso quando quiser.

## O que a Aline (ou quem administra o Business dela) faz

**Antes de começar:** o @dra.alinealbuquerque precisa ser **conta profissional** e estar **vinculado à página do Facebook** dela. Isso se confere no app do Instagram, em *Configurações > Central de contas*.

1. Abrir <https://business.facebook.com/settings> e escolher o portfólio dela.
2. Ir em **Usuários > Parceiros > Adicionar > Conceder acesso aos seus ativos a um parceiro**.
3. Informar o **ID do nosso Business**: `PENDENTE: o Weverton informa o ID do portfólio PAB/Casal da IA`.
4. Marcar os ativos e as permissões:

| Ativo | Permissão |
|---|---|
| Conta de anúncios | **Gerenciar campanhas** e **Ver desempenho** |
| Página do Facebook | **Conteúdo**, **Mensagens**, **Anúncios**, **Insights** e **Leads** |
| Conta do Instagram | **Acesso total**, ou pelo menos *Mensagens*, *Insights* e *Conteúdo* |

> **Se ela não tiver Business** (anuncia pelo botão "Turbinar" do Instagram), primeiro é preciso criar um em <https://business.facebook.com> e adicionar a conta de anúncios, a página e o Instagram. A gente faz isso com ela por chamada.

## O que a nossa equipe faz depois

1. Em **Configurações do negócio > Contas** do nosso portfólio, aceitar os ativos compartilhados.
2. Em **Usuários do sistema**, escolher o nosso usuário do sistema, clicar em **Atribuir ativos** e dar acesso à conta de anúncios, à página e ao Instagram dela.
3. Gerar o token permanente (validade **Nunca**) com estas permissões:
   - `ads_management`, `ads_read`, `business_management`
   - `pages_show_list`, `pages_read_engagement`, `pages_manage_ads`, `pages_manage_metadata`, `pages_messaging`
   - `leads_retrieval`, `read_insights`
   - `instagram_basic`, `instagram_manage_insights`, `instagram_manage_messages`, `instagram_manage_comments`

   Pode ser o app que já usamos para anúncios, acrescentando as permissões de Instagram.
4. Copiar `config/.env.example` para `config/.env` e preencher. O ID da conta de anúncios fica no topo do Gerenciador; o ID da página fica em *Configurações do negócio > Páginas*.
5. Testar e auditar:

```
python painel/gerar_painel.py --testar     a conta e a página dela precisam aparecer
python trafego/auditoria.py                diagnóstico das campanhas que estão rodando
python painel/gerar_painel.py --abrir      painel completo
```

## Se der erro

- **"(#200) Requires ads_read"** ou parecido: falta uma permissão no token (passo 3) ou falta atribuir o ativo ao usuário do sistema (passo 2).
- **Instagram sem acesso:** a conta não é profissional ou não está vinculada à página.
- **Formulários sem acesso:** em *Configurações do negócio > Integrações > Acesso a leads*, liberar o nosso app e o usuário do sistema.
- O painel continua funcionando com o que estiver liberado. O quadro sem acesso mostra o motivo.
