# Histórico anual da carreira — revisão local de 02/11/2026

## Separação dos dados

O histórico fica no banco do mod, fora das tabelas nativas do FIFA:

- `server16_manager_market.sqlite3`: `annual_campaigns`, associada ao ramo da
  carreira, vínculo do treinador, clube, competição e ano civil.
- `server16_loans.sqlite3`: `finance_years`, associada ao checkpoint do save,
  clube e ano. O estado completo continua no JSON transacional do mesmo banco.

Não há um histórico global compartilhado entre saves diferentes. Carregar um
save antigo recupera o histórico daquele salvamento; não importa os anos futuros
de outro ramo. DATA, INDEX e a base nativa do FIFA permanecem somente para leitura.

## Técnicos

A virada do calendário não recria os vínculos do catálogo. O técnico permanece
no clube contratado, com o salário e o término acordados; transferências,
demissões, aposentadorias e renovações seguem as regras normais do mercado.

Os contadores anuais são preservados quando o FIFA zera uma campanha. Se uma liga
atravessa janeiro sem reiniciar seus contadores, somente o incremento pertence ao
ano novo. Um reinício no meio do ano também preserva os dois trechos da campanha.
IDs de partidas reutilizados em outro ano não impedem o registro dos novos jogos.

No perfil do mercado de técnicos, **Clubes e anos** reúne as passagens e os
registros anuais. Cada ano identifica também o clube: trocar de equipe não mistura
os resultados do antecessor nem apaga a passagem anterior.

Registros anteriores à atualização só são aproveitados automaticamente quando
sua data e o início do vínculo demonstram que pertencem integralmente ao mesmo
ano. Uma tabela acumulada sem datas não permite inventar sua distribuição anual.

## Finanças

**Finanças do clube → Histórico anual** abre a lista dos anos registrados.
Selecionar um ano mostra receitas extras, despesas extras, resultado operacional,
resumo mensal e a última leitura real do orçamento daquele período. A consulta
usa a formatação monetária nativa da carreira e não dispara créditos ou débitos.

O orçamento do ano novo é a verba efetivamente informada pelo FIFA. O relatório
não substitui essa verba pelo saldo antigo. Abertura e última leitura são guardadas
com suas datas; um saldo que nunca foi observado aparece como não registrado.

Os lançamentos anteriores, contratos de TV, configurações, parcelas e operações
de empréstimos permanecem no estado da carreira. Cada novo ano recebe seus
contratos financeiros sem reprecificar os termos antigos. Resultados de dezembro
retidos pelo FIFA podem ser processados após um salto para janeiro, usando a data
de origem no relatório e a data efetiva no caixa, uma única vez.

Também são conservados os negócios de jogadores observados e os dados financeiros
nativos disponíveis no período, preparando consultas históricas futuras.
Premiações e despesas nativas sem extrato confirmado continuam sem valor
inventado. Os números operacionais desta tela representam os lançamentos do mod.

## Validação e instalação

- Cenários de dezembro/janeiro, reinício de campeonato no meio do ano, mudança
  de clube, reutilização de ID de partida e restauração de checkpoint anterior.
- Preservação das configurações e dos contratos anteriores; aplicação única das
  receitas; orçamento de abertura do ano novo independente do saldo anterior.
- Histórico financeiro salvo/restaurado pelo SQLite, com rejeição de clube errado.
- Navegação pelo histórico e Voltar no interpretador APT, sem requisição bancária.
- Pacote real do mercado validado com o catálogo desta instalação, preservando os
  vínculos ativos e a quantidade de jogos durante a atualização.
- Pacotes nativos do painel financeiro e de espera compilados e validados.

A atualização é local, nas pastas do jogo e de desenvolvimento, sem commit nem
push. Os auxiliares carregam os scripts novos ao iniciar; não foi necessário
alterar o executável do Server16.

Backup de código, bancos do mod, hash do save e relatórios:
`code-release/year_history_20261102_104505/`.

O próximo teste em jogo deve salvar a carreira após a virada e reabri-la. Os
testes isolados cobrem esse ciclo; a confirmação visual na sessão nova fica para
o usuário. Progresso que não foi salvo no FIFA não deve aparecer num save antigo.
