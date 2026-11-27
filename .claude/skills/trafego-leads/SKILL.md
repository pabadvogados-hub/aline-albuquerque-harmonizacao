---
name: trafego-leads
description: Puxa os leads que preencheram formulário instantâneo nos anúncios da Dra. Aline e entrega numa planilha. Use quando pedirem "puxa os leads", "quem se cadastrou", "lista de contatos do anúncio".
---

1. `python trafego/painel.py formularios` lista os formulários e quantos leads cada um tem.
2. `python trafego/painel.py leads <FORM_ID> --dias 7 --csv` grava em `leads/` (abre no Excel).
3. Diga quantos leads entraram, de qual anúncio vieram mais, e lembre: **lead de formulário tem que receber contato em minutos, no máximo no mesmo dia**, senão esfria.
4. Leads de **WhatsApp** e **Direct** não ficam aqui: chegam como conversa (Direct e comentários ficam na central de `atendimento/`). O relatório só conta quantos foram.
5. Nunca mande lista de leads para fora (e-mail, grupo, outro sistema) sem a Aline pedir: são dados pessoais e de saúde (LGPD).
