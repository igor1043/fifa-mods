# Empréstimos e o save

Cada pasta do save do FIFA passa a ter `server16_loans.sqlite3`, ao lado de
`DATA` e `INDEX`. O mod não altera o formato desses dois arquivos. Ao copiar um
save para outro computador, copie a pasta completa, incluindo o SQLite.

Uma gravação nativa concluída, conferida contra a carreira em memória, registra
o estado financeiro pelo SHA-256 do `DATA`. Ao carregar, apenas o histórico
daquela versão e daquele clube é restaurado. Carregar uma versão anterior não
repete créditos nem parcelas. “Salvar como” leva o histórico para o novo slot.
Os JSONs anteriores continuam disponíveis para migração e recuperação.

Tabelas:

- `snapshots`: estado confirmado em cada versão do save e fila de mensagens.
- `applications`: data fixa do pedido, resposta prevista e situação.
- `contracts`: banco, principal, juros contratados e parcelas pagas.
- `installments`: valor, vencimento, pagamento e método de cada parcela.
- `operations`: créditos e débitos já confirmados naquela versão.
- `live_operations`: operação preparada/aplicada em RAM/ainda pendente de salvar.
- `bank_catalog`: nomes e taxas das novas simulações. `rate_bps=80` significa
  0,80% ao mês. Alterações são lidas durante a sessão para propostas futuras;
  propostas enviadas e contratos preservam seus valores. IDs 0–2 são legados,
  e 3–12 correspondem aos dez bancos apresentados na tela.

As instituições e imagens servem à ambientação do mod. As taxas são simuladas.
As imagens ficam em `ModCarrerMode/data/club_environment/bank/assets/`, com
um arquivo `.source.json` para cada fonte. As dez imagens são embutidas no
APT nativo e o jogo não consulta a internet para exibi-las.


Após uma demissão ou troca de emprego, o clube atual vem do contexto nativo em
RAM, mesmo antes da próxima gravação do FIFA. `club_ledgers` conserva os estados
de todos os clubes daquela versão do save. Dívidas não acompanham o treinador.
`session_clubs` recupera o estado após reiniciar o componente durante a mesma
sessão; uma nova leitura do save descarta operações ainda não salvas. A migração
do SQLite anterior é automática e ocorre em uma transação.


A revisão 3 mantém `loan_requests` atualizado durante a sessão, antes de salvar
no FIFA: `submitted_date` e `response_date` são imutáveis para o mesmo pedido.
A decisão registra separadamente `decided_date`, situação e `credit_applied`.
`loan_outbox` registra os e-mails de recebimento, aprovação/recusa, lembrete e
pagamento, com data prevista e confirmação nativa de entrega. Esses registros
são consultáveis; a restauração continua obedecendo ao hash do save e à sessão,
sem reaplicar um crédito ao carregar uma versão anterior.

O dia previsto da resposta é o dia seguinte ao envio. Se o jogo estiver em uma
transição e só permitir a operação depois, a data prevista não muda: a execução
real aparece em `decided_date`. A Central e o calendário usam a mesma data da
carreira em RAM. O lembrete é agendado para o dia anterior ao vencimento.

Diagnóstico: `runtime/club_environment/bank/runtime/native_mail_status.tsv`
mostra a etapa da entrega; `native_mail_receipt.tsv` confirma a inserção na caixa
de mensagens pelo FIFA. O componente não marca o e-mail como entregue só por
ter gerado o arquivo de solicitação.

O clube pode manter até dois contratos ativos ao mesmo tempo, conservando o
limite de duas contratações por ano da carreira. A tela de cada contrato envia
seu identificador no pedido de pagamento V4. Com duas dívidas, um pedido legado
sem contrato explícito é recusado; ele nunca escolhe outra dívida por posição.
Os botões lado a lado dos extratos e da lista usam esquerda/direita; cima/baixo
percorrem as linhas e entram/saem da faixa de ações. As legendas continuam nativas.

As novas simulações têm limites por instituição, valores de 1 a 100 milhões e
prazos de 6 a 48 meses conforme o banco. Valores e prazos maiores elevam a taxa
simulada, exibida antes da confirmação. Pedidos já enviados e dívidas existentes
conservam a taxa e as parcelas armazenadas. O catálogo SQL continua ajustando
as taxas base; as faixas de produto são definidas em `loans.py`.

Ao pular dias ou meses no calendário, a cobrança considera vencimentos menores
ou iguais ao dia atual, sem exigir passagem pelo dia exato. O orçamento é
conferido novamente antes da escrita e a parcela só é marcada paga após leitura
do valor aplicado. Se o jogo ainda estiver avançando ou faltar saldo, o débito
aguarda; as parcelas já pagas não são cobradas novamente. O extrato e o e-mail
mostram a data efetiva do pagamento, separada do vencimento original.

Cada nova solicitação tem um recebimento e uma resposta próprios. Cada parcela
tem um lembrete D-1 com o banco contratado, o número, o valor e o vencimento
daquela parcela; o pagamento confirmado também gera um e-mail. O agendamento
segue o calendário da carreira, tanto pela Central como pela tela Calendário.
Parcelas antecipadas ou quitadas não recebem um novo lembrete. Se o calendário
pular o dia do aviso, o mod não envia depois uma mensagem incorreta de que a
parcela vence amanhã. Dívidas e avisos pertencem ao clube, e não acompanham o
treinador ao mudar de emprego. A confirmação nativa continua registrada mesmo
se Python só observar o recibo depois do vencimento.
