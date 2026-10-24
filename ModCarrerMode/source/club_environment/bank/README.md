# Empréstimos do clube — 24/10/2026

Tela APT/BIG nativa com bancos, logotipos, simulação, revisão, contratos individuais e tabela de vencimentos. Teclado e controle usam o HelpManager do FIFA. Até dois contratos ativos, respeitando o limite anual e a análise de crédito. Bancos oferecem limites, prazos, taxas e tempos de resposta diferentes; valores são parâmetros de simulação.

A solicitação captura a data do clique no calendário nativo. SQLite registra data enviada, resposta prevista fixa, situação e identificadores da operação por carreira/clube. Avançar dias não redefine a data do pedido. O serviço trabalha durante a sessão sem exigir que a tela de empréstimos permaneça aberta.

A aprovação credita o orçamento uma vez, com verificação de antes/depois. Parcelas vencidas são debitadas ao detectar data atual maior ou igual ao vencimento, inclusive quando o calendário pula vários dias. Histórico e recibos impedem reaplicar a mesma operação. Trocar de clube invalida o contexto anterior e recarrega os dados do novo clube.

E-mails distintos registram pedido recebido, aprovação/recusa e lembrete de vencimento. A fila preserva a data do evento e deduplica a entrega. A inserção ocorre na thread proprietária da interface do FIFA. A atualização visual da caixa pode exigir sair e entrar caso o FIFA mantenha sua lista aberta em cache.

O save permanece gravado pelo próprio FIFA. [SAVE_SQLITE.md](SAVE_SQLITE.md) descreve o livro auxiliar, checkpoints vinculados ao save e restauração. [BANK_TERMS.md](BANK_TERMS.md) documenta as taxas simuladas e os prazos. Contratos, recibos, snapshots e caminhos pessoais nunca fazem parte do pacote.

Diagnósticos: `ModCarrerMode/runtime/club_environment/bank/runtime/`. Os testes usam memória simulada; o pacote limpo verifica importações, SQLite, poses e os dez ícones com o Server16 congelado, sem realizar transações na carreira do usuário.
