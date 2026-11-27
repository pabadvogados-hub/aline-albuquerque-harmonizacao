# Central de marketing: Dra. Aline Albuquerque

Pacote de crescimento para a **Dra. Aline Albuquerque**, @dra.alinealbuquerque, harmonização facial em Santos/SP.
- **Nicho:** derretimento facial depois do emagrecimento.
- **Produto próprio:** Método Fênix.

Feito pela WP Casal da IA.

## O que tem aqui

| Pasta | O que faz |
|---|---|
| `trafego/` | **Gestão de tráfego (Meta Ads).** `auditoria.py` audita as campanhas que já rodam e diz o que está errado, com a prova e a ação. `painel.py` cria campanhas (sempre pausadas), mostra relatório e diagnóstico, liga, pausa e muda verba (só com `--confirmo`). |
| `painel/` | **Painel de relatório completo**, nas cores do consultório. Mostra: vídeo campeão com curva de retenção, gancho e fadiga; funil do anúncio até a paciente que fechou, com ROAS e custo por paciente; horários; público; Instagram orgânico com o reels campeão; quem segue o perfil; comparação com o mercado; nota de saúde e recomendações com o comando pronto. |
| `atendimento/` | **Central estilo ManyChat.** Atende comentário com palavra-chave, Direct, menção e resposta a story, e quem entrou por anúncio. O robô faz a qualificação e passa para o WhatsApp. Tem funil em kanban, caixa de entrada e números. |
| `video/` | **Editor de vídeo** com a identidade dela. Corta pausas, gera legenda que desvia do rosto, cartão de abertura, chamada final e **3 variações de gancho** por vídeo para teste no anúncio. |
| `docs/` | Estudo de mercado (benchmarks e regras de publicidade), estratégia da clínica (organograma, fluxogramas, POPs, indicadores), acesso à Meta e configuração do atendimento. |
| `.claude/` | Agentes e skills para operar tudo pelo Claude Code. Agentes: `gestor-trafego` e `estrategista-clinica`. Skills: `/trafego-auditoria`, `/trafego-otimizar`, `/trafego-relatorio`, `/trafego-copy`, `/trafego-campanha`, `/trafego-leads`, `/editar-video`, `/roteiro-video`, `/estrategista`. |

## Começo rápido

```
pip install -r requirements.txt
ver_demonstracao.bat                       painel com números fictícios
copy config\.env.example config\.env       preencher (docs/COMO_LIBERAR_ACESSO_META.md)
python painel/gerar_painel.py --testar     o token enxerga a conta?
auditar_campanhas.bat                      auditoria das campanhas que estão no ar
atualizar_painel.bat                       painel com os dados reais
```

- Central de atendimento: `docs/ATENDIMENTO_INSTAGRAM.md`.
- Editor de vídeo: `video/LEIA.md`.

## Segurança
- Nada que gasta dinheiro roda sem `--confirmo`. Tudo o que é criado nasce pausado.
- Existe um teto diário de verba (`TETO_DIARIO_REAIS`).
- Chaves ficam em `config/.env` e `atendimento/.env`, que não vão para o repositório.
- Dados de pacientes e leads (`dados/`, `leads/`, `relatorios/`) também não vão para o repositório. São dados pessoais e de saúde (LGPD).

## Pendente com a Aline
1. Compartilhar a conta de anúncios, a página e o Instagram com o nosso Business como parceiro.
2. Conselho e número do registro profissional (vai no anúncio).
3. Endereço do consultório (para o raio dos anúncios).
4. Respostas de diagnóstico da estratégia (`docs/ESTRATEGIA_CLINICA.md`).
