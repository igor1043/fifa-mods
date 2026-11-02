# Finanças: calibração e relatório completo — 02/11/2026

Revisão local para nova simulação. Nenhum DATA/INDEX, tabela da DB nativa,
resultado esportivo ou orçamento é modificado pelo instalador. O processador
financeiro existente continua sendo o único responsável pelos lançamentos.

## Calibração de jogo

| Parâmetro em `finance_rules` | Anterior | Novo |
|---|---:|---:|
| `match_cost_bps` | 4000 | 6500 |
| `sponsor_annual_bps` | 2500 | 3250 |
| `staff_annual_bps` | 3000 | 4000 |
| `facilities_annual_bps` | — | 3000 |
| `tv_match_bps` | 150 | 100 |

65% da bilheteria bruta é uma **calibração de dificuldade solicitada**, não uma
média oficial brasileira. Engloba uma estimativa agregada de operação do jogo;
não deve ser apresentada como um custo real do Flamengo. O ingresso e o público
por partida permanecem com as regras já existentes. Só há receita de bilheteria
e sua operação em jogos concluídos como mandante, fora de estádio neutro.

Patrocínio, comissão e manutenção usam orçamento-base e reputação, com o fator
de mercado da liga instalado. Manutenção/estrutura representa CT, serviços e
administração, sem repetir a operação do estádio ou a folha nativa. Há um novo
switch próprio, acrescentado ao fim do protocolo existente; empréstimos seguem
no índice 4. A chave geral continua bloqueando os novos créditos/débitos.

## Direitos de TV

Não existe uma regra universal real de pagamento de TV maior em casa e menor
fora. Os acordos variam e podem combinar valores contratuais, participação,
desempenho e audiência. O relatório oficial do Flamengo explica o reconhecimento
por contrato e, nas copas, por fase. O modelo abaixo é uma aproximação **do mod**
para liberar a verba conforme as partidas efetivamente concluídas.

- Cota-base: escala de orçamento/prestígio/divisão e força financeira da liga.
- Peso de competição: liga 1,00; copa nacional 1,25; continental 1,50;
  mundial 1,60; regional 0,25; supercopa nacional 0,90.
- Importância do campeonato: usa `match_matchimportance` do FCE instalado.
- Mando: 1,10 da cota-base em casa; 0,65 fora; 0,80 em campo neutro.
- Mata-mata: oitavas 1,05; quartas 1,15; semifinal 1,30; final 1,50.

O tipo vem de `comp_type` e da hierarquia de `compobj.txt`, comparada à liga
principal do clube. Assim o Carioca não recebe o peso do Brasileirão, e novas
ligas não exigem uma lista manual de nomes ou IDs. A copa nacional/continental
considera também o mercado da liga do clube, para que a mediana de muitos
participantes pequenos não reduza indevidamente a cota de um clube grande.
Esses repasses adicionais não criam outra premiação por título ou fase.

## Persistência e atualização

O SQLite continua ao lado do save (`server16_loans.sqlite3`), com backup
consistente `server16_loans.before-finance-v4.sqlite3`. `calibration_v4` atualiza
uma vez os valores de protótipo ainda intactos e preserva parâmetros SQL
personalizados. Não modifica snapshots, contratos de empréstimo ou lançamentos
históricos. A versão econômica 4 cria revisões a partir do dia seguinte ao
último dia financeiro observado, mantendo as condições antigas antes disso.

As despesas mensais contam somente os dias habilitados sob cada contrato.
Calendários que pulam jogos/fechamentos de mês continuam liquidando cada evento
uma única vez. Despesas sem saldo permanecem pendentes. Carregar outro checkpoint
restaura o livro daquele save, em vez de importar o caixa de outra simulação.

## Visão geral e limites dos dados nativos

O analógico direito percorre a visão geral e as páginas dos dois cards completos.
Há setas clicáveis e as legendas nativas existentes. Somente a página atual
registra ações APT; rolar a consulta nunca solicita pagamentos nem reconstrói
o pacote. Valores e ícones ficam dentro da área útil.

As categorias incluem TV, bilheteria, patrocínio, vendas/compras de jogadores,
taxas de empréstimo de jogadores, entrada de empréstimos bancários, amortização,
juros, técnico, comissão, estrutura, salários nativos e premiações/bônus.
Categorias conhecidas sem movimento mostram zero. O valor de transferências é
o acordado nos negócios concluídos do save; não comprova o pagamento de cada
parcela. Amortização e juros são separados; financiamento não é lucro.

**Limitação explícita:** nesta carreira, as tabelas T3DB lidas não fornecem o
extrato anual efetivo de premiações, bônus ou salários pagos aos jogadores.
Essas linhas exibem “Não obtido”, e não um zero inventado, nem uma estimativa
baseada no saldo, na folha atual ou nos títulos. Essa leitura ainda precisa ser
mapeada. Os KPIs/gráficos de extras continuam representando os lançamentos
efetivos do mod, claramente separados das consultas nativas.

## Referências primárias

- [Flamengo — demonstrações de março/2026](https://images.flamengo.com.br/public/arquivos/transparencia/19/1777579037016.pdf):
  custos esportivos, administrativos e bilheteria são linhas distintas; a amostra
  não autoriza tratar 65% como taxa universal.
- [Flamengo — demonstrações de março/2025](https://images.flamengo.com.br/public/arquivos/transparencia/19/174604969605.pdf),
  notas 2.10 e 17: reconhecimento de TV por contrato/fase e bilheteria por borderô.

Sem commit/push nesta revisão. Backup e comparação offline ficam em
`code-release/finance_balance_20261102_082556`.
