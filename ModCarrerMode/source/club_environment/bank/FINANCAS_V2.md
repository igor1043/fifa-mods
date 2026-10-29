# Finanças do clube — revisão local, 29/10/2026

Tela APT nativa. Mantém os cards claros e o tema central #B9A274. Gráficos
mantêm 2× a resolução de exibição; ícones, anéis, switches e barras mantêm
3×. O empacotador apenas acrescenta padding BC3 de quatro pixels, sem
redimensionar a arte para baixo. Os textos e valores dos cards continuam
campos nativos, e não texto pintado dentro de uma imagem. O arquivo usa
compressão de arquivo sem perdas no nível 1 para acelerar as atualizações.

## Receitas e despesas

- TV: um crédito por partida concluída do clube, em casa ou fora. Usa a
  mediana dos orçamentos-base dos participantes, o prestígio e a divisão.
  O coeficiente padrão `tv_match_bps` passa de 75 para 150. Não é calculado
  sobre o saldo atual: empréstimos/vendas não aumentam a cota de TV.
- Bilheteria: apenas mandante, sem estádio neutro, jogo concluído e capacidade
  conhecida. Público **estimado** = capacidade × ocupação, limitada pela regra.
  A ocupação usa a reputação do próprio clube. Ingresso padrão: 8 unidades
  contábeis da carreira, em vez de 25. É uma simulação proporcional ao jogo,
  não uma reprodução de preço nominal atual de ingresso em reais/euros.
- Custos da partida: 40% da renda bruta estimada, separadamente no extrato.
  Só existem junto à bilheteria do clube e só são debitados após seu crédito.
  A tabela de bilheteria mostra data, adversário/escudo, competição, público,
  bruta, custo pago, líquido e situação. Registros antigos são exibidos com
  os seus valores originais: não se inventam custos históricos.
- Patrocínio: **um contrato por clube e temporada**, recebido em parcelas
  mensais. Estimativa anual = orçamento-base × 25% × fator de reputação.
- Comissão técnica: estimativa anual = orçamento-base × 30% × o mesmo fator.
  O fator é `(40 + 3 × prestígio)/100`, com prestígio limitado a 1–20.
  Exemplo de escala: orçamento-base de 28 milhões e prestígio 20 → patrocínio
  de 7 milhões/ano e comissão de 8,4 milhões/ano, proporcionais aos dias ativos.
  São parâmetros de balanceamento do mod, não contratos reais dos clubes.
- Técnico: continua usando o salário semanal real do contrato do save, ×52/12.
- Empréstimos: continuam com o cálculo e a cobrança existentes. As parcelas
  incluem principal e juros no caixa; o resultado operacional mostra apenas
  os juros. A folha dos jogadores é informativa: o FIFA mantém sua cobrança
  nativa, sem uma segunda cobrança desse salário pelo mod.

TV, ingresso, ocupação, patrocínio, comissão e custos são editáveis em
`finance_rules` no **mesmo** `server16_loans.sqlite3` dos empréstimos. Novas
ligas/clubes usam a DB e os participantes existentes, sem lista fixa de IDs.
Uma edição manual das regras SQL é preservada na migração se ela difere do
protótipo. A calibração automática tem marcador `calibration_v2`.

Cada opção tem um switch próprio; a chave geral continua bloqueando novas
movimentações. O débito/recebimento mensal conta somente dias habilitados.
Desligar bilheteria também impede os custos daquele jogo. Desligar empréstimos
não apaga a dívida. Meses/vencimentos atravessados são processados uma vez,
mesmo que o calendário não pare no dia exato. Despesas sem saldo ficam pendentes.

## Moeda, navegação e desempenho

Todos os valores monetários passam por
`ION_Localization.LocalizeCurrencyWithType(False, amount, save_currency)`.
Os slots 0/1/2 pertencem ao FIFA e podem ser renomeados pelo idioma/mod;
nada fixa Real, Dólar ou Euro por ID do clube. Não há conversão cambial externa
nem uma segunda multiplicação do saldo do jogo. Logos/escudos são lidos dos
assets instalados no próprio FIFA; não é criado catálogo duplicado.

Os ombros físicos L1/R1 (LB/RB, códigos PC L2/R2) trocam as abas. Analógico
direito para cima/baixo percorre páginas de listas; os botões ‹/› permitem
mouse/teclado. Os códigos e legendas vêm do HelpManager nativo. Paginação evita
renderizar listas ilimitadas ou reconstruir o pacote a cada movimento.

## Persistência e limites da alteração

O livro financeiro continua no estado por clube/checkpoint dos empréstimos.
A nova tabela aditiva `finance_commercial` permite consultar o contrato
comercial estimado de cada temporada. A versão dos empréstimos permanece 3;
o schema SQL financeiro permanece compatível com os leitores anteriores.
Antes da calibração existe backup SQLite consistente
`server16_loans.before-finance-v2.sqlite3`, além do backup v1.

Migração do livro de 1 para 2: preserva entradas e quantias pagas, e começa
patrocínio/comissão na data atual da carreira. As cotas de TV existentes
recebem uma revisão com data de vigência. Jogos anteriores continuam usando
as condições antigas. Não se devolve nem se retira dinheiro retrospectivamente.

O mesmo publicador validado de orçamento é usado; esta revisão não muda seu
protocolo de escrita, as DLLs, o calendário, os provedores ou a DB nativa. O
serviço observa uma gravação completa do FIFA para associar o histórico ao
hash do DATA. Não escreve em DATA nem INDEX. Consultar a tela não gera outro
pagamento. Salvar como, restaurar checkpoint e mudar de clube mantêm o escopo.

## Referência da calibração

O balanço de 2024 do Flamengo separa bilheteria bruta, custos e renda líquida
por competição; o relatório de 2025 do Fluminense distingue TV, comercial e
receitas de jogos. Essas separações orientam o modelo; os coeficientes acima
são uma adaptação deliberada para a economia do FIFA, não valores auditados.

- https://images.flamengo.com.br/public/arquivos/transparencia/173/1743457659033.pdf
- https://static.fluminense.com.br/noticia/fluminense-divulga-balanco-com-receita-recorde-de-r-1-bilhao-superavit-pelo-quarto-ano-seguido-e-investimento-inedito-em-jogadores
