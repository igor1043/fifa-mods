# Público e bilheteria por partida

A bilheteria deixa de depender apenas da ocupação fixa por prestígio. Cada
novo jogo em casa recebe um registro com percentual, capacidade, público,
preço do ingresso, renda bruta, custo de operação e renda líquida.

- Em partidas disputadas, o auxiliar lê o percentual reconhecido pela ponte
  de público. Valida PID, mandante, visitante, fase, heartbeat e confirmação
  do comando. A leitura não altera o mod de público.
- Nos jogos simulados pelo calendário sem uma leitura confirmada, calcula uma
  estimativa individual com os pesos de crowd.ini, prestígio do clube e do
  adversário, divisão, rivalidade, fase, campanha e resultados anteriores ao
  jogo. A reconstrução é identificada como estimativa; não representa uma
  contagem nativa de torcedores que o save não registrou. Não usa o resultado
  do próprio jogo nem resultados futuros. Não sorteia outra renda ao abrir a
  tela. Percentuais iguais continuam possíveis quando os fatores coincidirem.
- O valor global atual de static_factor_percent em modo automático não é
  copiado para todos os jogos passados. Em modo manual, o percentual fixo
  escolhido pelo usuário é respeitado.
- Um salto de calendário processa cada partida concluída separadamente. Só
  jogos mandantes e sem campo neutro geram bilheteria. Renda bruta é público
  multiplicado pelo ingresso; a operação usa a política financeira vigente.
- A prévia usa o mesmo percentual exibido no seu público para projetar a
  bilheteria. O preço continua seguindo a política financeira do clube/liga.
- Registros entram no livro financeiro por clube e checkpoint do save e na
  tabela adicional finance_attendance da base server16_loans.sqlite3. DATA e
  INDEX continuam sendo gravados exclusivamente pelo FIFA. O crédito na RAM
  usa a ponte financeira existente, com conciliação dos eventos e leitura de
  confirmação. Não reprecifica, debita ou credita partidas já contabilizadas.

Verificação: 80 testes de finanças, histórico, interface, calendário e prévia
passaram; após o último ajuste, 21 testes de público, prévia e conciliação
passaram. Uma verificação mais ampla encontrou uma expectativa antiga em
test_preview_summary sobre matchInfo, removido pelo layout anterior. A mesma
falha foi reproduzida com preview_details anterior a esta revisão e não foi
alterada neste trabalho.

Auditoria de leitura: carreira Criciúma, 30/07/2026, capacidade 19.900. As
projeções variam por jogo. Histórico financeiro anterior: 87 lançamentos,
sem registros de público por partida. O histórico creditado é preservado.

Instalação local, sem commit/push. Backups e manifestos em code-release,
indicados por match-attendance-current.txt.
