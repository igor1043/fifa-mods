# Empréstimos do clube — 24/10/2026

Tela APT/BIG nativa com bancos, logotipos, simulação, revisão, contratos individuais e tabela de vencimentos. Teclado e controle usam o HelpManager do FIFA. Até dois contratos ativos, respeitando o limite anual e a análise de crédito. Bancos oferecem limites, prazos, taxas e tempos de resposta diferentes; valores são parâmetros de simulação.

A solicitação captura a data do clique no calendário nativo. SQLite registra data enviada, resposta prevista fixa, situação e identificadores da operação por carreira/clube. Avançar dias não redefine a data do pedido. O serviço trabalha durante a sessão sem exigir que a tela de empréstimos permaneça aberta.

A aprovação credita o orçamento uma vez, com verificação de antes/depois. Parcelas vencidas são debitadas ao detectar data atual maior ou igual ao vencimento, inclusive quando o calendário pula vários dias. Histórico e recibos impedem reaplicar a mesma operação. Trocar de clube invalida o contexto anterior e recarrega os dados do novo clube.

E-mails distintos registram pedido recebido, aprovação/recusa e lembrete de vencimento. A fila preserva a data do evento e deduplica a entrega. A inserção ocorre na thread proprietária da interface do FIFA. A atualização visual da caixa pode exigir sair e entrar caso o FIFA mantenha sua lista aberta em cache.

O save permanece gravado pelo próprio FIFA. [SAVE_SQLITE.md](SAVE_SQLITE.md) descreve o livro auxiliar, checkpoints vinculados ao save e restauração. [BANK_TERMS.md](BANK_TERMS.md) documenta as taxas simuladas e os prazos. Contratos, recibos, snapshots e caminhos pessoais nunca fazem parte do pacote.

Diagnósticos: `ModCarrerMode/runtime/club_environment/bank/runtime/`. Os testes usam memória simulada; o pacote limpo verifica importações, SQLite, poses e os dez ícones com o Server16 congelado, sem realizar transações na carreira do usuário.

## Moeda e análise de novas propostas — 25/10/2026

A moeda vem de `career_managerpref.currency`. O ID identifica uma opção do save, sem associação fixa a dólar, euro ou libra: mods de idioma podem renomear essas opções para real e euro. A tela usa `ION_Localization.LocalizeCurrencyWithType`; os corpos dos e-mails usam o mesmo formatador nativo na thread proprietária. Isso muda a apresentação, sem conversão ou alteração dos valores contábeis.

Cada nova proposta registra uma análise de crédito fictícia. A chance base de recusa varia de 8% a 18% conforme o banco e cresce com o valor em relação ao orçamento, dívidas em aberto e prazos acima de 24 meses. Esses percentuais são regras do jogo, sem relação com taxas reais de aprovação. O sorteio e as circunstâncias ficam congelados na proposta e no checkpoint SQLite. Recusar não credita dinheiro, envia a decisão pela fila existente e permite pedir a outro banco. Pedidos anteriores sem essa análise mantêm o comportamento anterior.

Os testes verificam as três opções monetárias com símbolos fornecidos pelo jogo, prefixos e valores compostos, limite de ações do APT, moeda nos e-mails, recusa sem crédito, nova tentativa, decisão persistida após salto de calendário e restauração SQLite, além da preservação dos bytes do save.

## Recuperação de cobranças — revisão local de 27/10/2026

A construção da tela foi dividida em métodos APT menores. Um contrato aprovado com valores localizados podia ultrapassar o limite do decodificador ao montar o método de atualização e encerrar o auxiliar antes das cobranças seguintes. Falhas de geração/publicação visual agora preservam a última tela válida e tentam novamente após três segundos, sem interromper o calendário financeiro nem a observação dos salvamentos.

A revisão verifica o salto de fevereiro para maio, a cobrança das duas parcelas vencidas sem duplicação, a manutenção do contrato no checkpoint da sessão e sua restauração após uma gravação nativa completa. Inclui contratos simultâneos de 48 meses, navegação, moedas, troca de clube e notificações. O serviço recupera o livro existente; não cria outro empréstimo nem reaplica seu crédito. O jogador continua responsável por salvar a carreira no FIFA para registrar o orçamento e o histórico juntos.

Esta revisão integra a entrega publicada de 28/10/2026; os testes e os limites estão em `ModCarrerMode/docs/RELEASE_20261028.md`.

A troca de slot durante Salvar como aguarda o novo DATA completo antes de trocar de contexto. Leituras transitórias ou um arquivo temporariamente ausente suspendem as transações sem descartar o contrato. Os testes reproduzem a remoção do slot anterior, preservam parcelas já pagas e mantêm a restauração independente quando outro save é efetivamente carregado.
