# Bilheteria: renda bruta, operação e renda líquida

## Referência e regra da simulação

O [relatório financeiro oficial do Flamengo de março de 2026](https://images.flamengo.com.br/public/arquivos/transparencia/19/1777579037016.pdf),
nota 15, página 53 do PDF (índice começando em zero), divulga para o futebol
masculino profissional renda bruta de R$27,953 milhões, custos diretos de
R$10,963 milhões e resultado líquido de R$16,990 milhões. Custos/bruta = 39,22%.
Na mesma amostra, os percentuais variam entre aproximadamente 25% na Recopa,
39% no Brasileiro e 55% no Carioca. Não é uma média universal das ligas.

A base do mod é **40% da bilheteria bruta para operação direta e 60% líquida**.
É uma aproximação de jogo inspirada nessa amostra, aplicada proporcionalmente
à receita, sem atribuir despesas reais específicas a cada clube. Continua
configurável em `finance_rules.match_cost_bps` no banco auxiliar dos empréstimos
e finanças: 4000 pontos-base = 40%. Valores personalizados, inclusive zero,
são preservados. O switch “Custos de operação da bilheteria” controla débitos
novos, além da chave geral e da opção de bilheteria.

O débito usa o mesmo identificador da partida da receita e só é efetivado se o
crédito correspondente tiver sido aplicado, com dinheiro suficiente e o
contexto financeiro validado. Reabrir telas, reiniciar o auxiliar e consultar
totais não criam novas cobranças. Não há bilheteria ou operação para jogos fora
ou neutros. A moeda apenas formata os inteiros contábeis, sem aplicar câmbio.

## Histórico anterior

Contratos antigos podem não conter o percentual. Se ainda faltar em um contrato
importado de schema 2, uma revisão acrescenta somente o percentual ausente a
partir do dia seguinte à atualização. Não altera as regras antigas, o preço do
ingresso ou o valor de TV. Contratos que já possuem uma revisão futura não
recebem revisões repetidas.

Receitas antigas sem lançamento de operação não recebem uma despesa retroativa.
Na consulta aparecem custo e líquido **estimados**, com “Estimativa · não
debitada”. Os totais da consulta sinalizam quando incluem essas projeções. O
dashboard, o extrato e o orçamento continuam usando somente os pagamentos
efetivados; não incorporam estimativas históricas ao caixa.

Quando há uma despesa registrada, a consulta distingue Debitada, Pendente e
Desativada. No caso pendente, a líquida mostrada é a prevista após essa despesa.
As colunas contábeis originais permanecem separadas das projeções de exibição.

Exemplo: R$1.537.325 de renda bruta → R$614.930 de operação de referência →
R$922.395 líquidos. Para uma partida antiga sem custo registrado, esses dois
últimos valores são informativos e não geram débito no save.
