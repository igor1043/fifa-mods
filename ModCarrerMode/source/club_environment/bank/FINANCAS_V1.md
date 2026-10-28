# Finanças do clube — primeira versão local, 28/10/2026

Entrada: Escritório → carrossel de Solicitar verba/Empréstimos → **Finanças do clube**.
Tela APT nativa com Visão geral, Receitas, Despesas, Transferências, Salários,
Dívidas, Orçamento e Configurações. Receitas abre os contratos de TV; Orçamento
abre o extrato mensal.
As legendas de teclado/controle usam o HelpManager do próprio FIFA. Os ombros
físicos L1/R1 (LB/RB) mudam as abas, conforme os códigos originais do FIFA PC.

## Regras da versão de teste

- Tudo vem ativado por padrão, com preferências por carreira/clube/checkpoint.
- Contratos de TV são gerados automaticamente para as competições da carreira.
  O valor por jogo usa a mediana dos orçamentos-base dos participantes, prestígio
  e divisão, com limites e coeficientes ajustáveis no SQL. Não usa a verba atual
  do manager, portanto empréstimos e vendas não aumentam o contrato de TV.
- Um crédito de TV por partida concluída em que o clube efetivamente joga.
  Jogos futuros, adversários e competições em que o clube não joga não pagam.
- Bilheteria adicional nos jogos como mandante. A primeira versão usa público
  pagante **estimado** a partir da capacidade da DB e ocupação calculada. Fases
  com estádio neutro configurado em CompData não recebem renda de mandante.
- TV e bilheteria são receitas adicionais deste mod. As premiações/receitas
  nativas não são reclassificadas nem substituídas. Não há afirmação de que esta
  versão tenha mapeado toda receita comercial ou de bilheteria interna do FIFA.
- Salário do técnico: o valor semanal do contrato da carreira é convertido em
  obrigação mensal (`wage × 52/12`), cobrada ao fechar o mês. O primeiro mês e os
  dias com o recurso desligado são proporcionais. O débito sai da verba de
  transferências, conforme a proposta de teste autorizada. A folha dos jogadores
  continua sob as regras nativas; esta versão não cria outra cobrança dela.
- Meses e vencimentos atravessados pelo calendário são processados em ordem.
  Falta de saldo mantém a despesa pendente; ela só é paga após confirmação do
  saldo aplicado. O extrato mensal é uma soma, nunca outro pagamento.
- A ativação ignora os resultados já conhecidos naquele momento. Não paga toda
  a temporada passada e não cria cobranças anteriores ao início do acompanhamento.

## Configurações

Chave geral: bloqueia os créditos, débitos e operações dos empréstimos. O serviço
continua lendo contexto e configurações para permitir reativar; ele não aplica
dinheiro enquanto a chave estiver desligada.

Subitens: receitas de TV, bilheteria, cobrança do técnico e cobrança automática
dos empréstimos. Desligar uma receita faz os jogos observados nesse período
ficarem sem esse crédito; reativar não concede esses valores retroativamente.
O técnico não é cobrado pelos dias desativados. Valores já aplicados não são
desfeitos ao mudar uma configuração.

Desligar a cobrança automática dos empréstimos não perdoa a dívida e não marca
parcelas como pagas. Ao reativar, vencimentos ainda devidos são cobrados com a
regra existente. Pagamentos manuais continuam disponíveis se a chave geral está
ligada. Pedidos em análise ficam aguardando se a chave geral estiver desligada;
a data original da proposta não muda.

## Persistência e integração

Somente o worker de empréstimos publica o orçamento. Novas operações usam o
mesmo diário com verificação de contexto/saldo e leitura após escrita. O livro
`finance` está dentro do estado por clube já restaurado por `save_sidecar.py`.
Assim ele acompanha o save confirmado, Salvar como e a restauração de um save
anterior, sem reexecutar seus créditos.

O mesmo `server16_loans.sqlite3` recebe tabelas aditivas: `finance_meta`,
`finance_rules`, `finance_preferences`, `finance_agreements`, `finance_entries`.
O schema financeiro tem versão 1 própria; `user_version=3` dos empréstimos é
preservado. A primeira inicialização faz backup consistente do SQLite anterior
em `server16_loans.before-finance-v1.sqlite3`. Não altera DATA/INDEX diretamente.

Salve a carreira normalmente no FIFA após operações ou alterações de opções.
Para transferir a carreira a outro PC, preserve seu SQLite junto a DATA/INDEX.
Não incluir esses dados pessoais no pacote genérico do mod.

Logs: `runtime/club_environment/bank/runtime/bank_loans.log`,
`club_finance_view.json` e as tabelas SQL. Eventos `club_finance` identificam as
movimentações novas; `finance_settings` registra mudanças de configuração.
Falha no painel não interrompe empréstimos nem o observador de saves.

## Limites e validação

Esta é uma economia adicional para teste e balanceamento, não valores reais de
contratos comerciais. A capacidade pode ser a da DB/modelo quando um estádio
externo não fornece outro valor. O salário depende de contrato validado do clube;
se indisponível após trocar de emprego, o débito aguarda informação válida.

Os testes novos cobrem jogos concluídos/fora/neutros, deduplicação, calendário,
proporcionalidade, opções e dívida preservada, moeda nativa, navegação, SQL,
restauração e Salvar como. A suíte anterior de empréstimos e a do mercado são
executadas junto aos testes nativos para verificar regressões.

O teste em partida real de uma nova receita e de um fechamento mensal deve
conferir antes/depois no orçamento, extrato e SQL, seguido de salvar/reabrir.
Simulação e bytecode validados não substituem essa confirmação no FIFA.

Esta primeira versão é registrada no Git após autorização do usuário. O teste
completo de receitas e fechamento mensal na carreira permanece descrito acima.

## Revisão visual local

A abertura executa `BeginAnimateIn` na sequência de apresentação do FIFA,
antes de concluir o ciclo da tela. O teste do APT verifica essa chamada.

O resumo segue quatro indicadores, evolução mensal com barras de receitas e
despesas e linha de resultado, distribuição de receitas em rosca, orçamento da
temporada, limite salarial semanal e tabelas de categorias. Empréstimos mantêm
principal e financiamento separados do resultado operacional; somente seus
juros compõem a despesa desse demonstrativo.

Os gráficos são imagens calculadas com os valores registrados e embutidas no
APT nativo. Suas superfícies DXT5 são alinhadas em blocos 4×4; a disposição dos
cards mantém as dimensões de exibição. Campos monetários continuam usando a
moeda e o formatador do FIFA. Meses futuros não prolongam a linha do realizado.
Sem receitas, o gráfico de distribuição permanece vazio; não são gerados dados
fictícios para preencher o painel.

## Jogadores e navegação — revisão local

Salários lista somente jogadores do elenco atual, com foto original, posição,
idade, overall, salário semanal, projeção mensal (`semanal × 52/12`) e ano final
do contrato disponível no save. Propostas de salário não substituem o contrato
atual. Salários ausentes ou duplicados permanecem sem valor informado. A folha
é consultiva, sem um segundo débito no orçamento de transferências.

Transferências mostra chegadas e saídas confirmadas na temporada, incluindo
empréstimos de atletas, jogador, data, clube e valor. Reutiliza a validação do
Mercado de Transferências: negociação concluída e destino confirmado pelo
elenco. Negócios pendentes não compõem a lista. São valores do negócio, sem
afirmar que todo o montante foi liberado pela diretoria nem reaplicá-lo ao saldo.
As fotos e escudos vêm dos assets instalados do FIFA, decodificados em memória;
não é criado outro catálogo de imagens. Metadados de contratos/negócios são
recarregados quando o save ou o clube muda. Avançar o calendário continua usando
os metadados em cache; sua falha não bloqueia as cobranças.

A seleção agora encerra o despacho APT após tratar uma ação. Antes, mudar de
página podia executar a ação da página seguinte e voltar ao resumo no mesmo
clique. Os testes cobrem todas as abas por clique, confirmação e ombros,
paginação e acesso às configurações. Fontes, interface inicial genérica e núcleo
compilado acompanham a revisão; dados pessoais da carreira ficam no próprio PC.

## Switches, gráficos e ícones — revisão local

Configurações usa switches gráficos com resposta no próprio clique. O estado
solicitado é provisório até o retorno do serviço; a tela mostra “Aplicando
configuração…”, impede envios duplicados e restaura o estado confirmado se a
alteração for recusada. A confirmação mantém a aba e o foco, sem precisar sair
e entrar manualmente. O estado só é declarado aplicado após publicar o ledger.

O Calendar nativo ignora eventos personalizados de navegação enviados por
`SendSystemEvent`. A confirmação agora usa a mesma fila de navegação executada
pela thread proprietária já usada pelo Mercado e Próxima partida. O registro
de prontidão valida processo, instante de criação, clube, contexto, epoch,
registro de serviços e data; a mesma revisão não recarrega em loop.

Evolução mensal foi simplificada para barras de receitas e despesas extras,
com a mesma escala e sem uma curva negativa comprimindo as receitas. “Ver mês
a mês” abre os valores monetários de receitas, despesas e resultado, com a
moeda nativa e paginação. Meses futuros permanecem sem valores realizados.

Os cards possuem ícones de categoria, barras proporcionais e divisórias. O
orçamento mostra inicial, variação e disponível; a porcentagem compara saldo
atual com o inicial e pode ultrapassar 100%. Não equivale a “orçamento gasto”,
pois vendas, premiações e empréstimos também mudam o saldo. O limite salarial
mostra folha semanal, limite (= folha + margem) e margem disponível.
