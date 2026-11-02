# Campanhas globais, vínculo com o save e classificação nativa

## Diagnóstico confirmado

No DATA a3a9db15 de 10/08/2026, o Barcelona tem um jogo na tabela
leagueteamlinks e os contadores FCE da La Liga estão zerados. A tela nativa
mostra cinco jogos e 15 pontos. O slot é o mesmo (3099).

A rotina ResponseStandingsList do FootballCompEng (+0x6a810) verifica se há
resultados na fase. Se não há, chama o cálculo nativo +0x40ce0, que usa a
definição da temporada/calendário e o simulador do próprio FIFA. Esses cinco
jogos não estão serializados como cinco placares individuais naquele DATA.

## Implementação

- O parser continua lendo o DATA validado por CRC para calendário, vínculos,
  clubes, competições, contadores e placares disponíveis. Inclui gols a favor
  e contra por mando. O byte 9 do registro salvo é seed/rank, não vitórias.
- A integração FCE percorre automaticamente todas as fases de liga/grupos
  ativas, identificadas por match_stagetype=LEAGUE no compdata, sem lista fixa
  de países, nomes de fase ou IDs. Onde faltam contadores, executa o
  mesmo cálculo do FIFA. Onde há campanha jogada, preserva os dados reais.
- O processamento ocorre após FCE::Update, no proprietário da engine, uma
  fase por vez. Não depende de abrir Outras ligas ou o mercado de técnicos.
  A troca de contexto, data ou contadores invalida o trabalho anterior.
- A publicação de derivados independe da tela Statistics, por meio de
  runtime/career_derived_standings.json. Não escreve o DATA nem o INDEX.
- O consumidor valida processo, criação do processo, epoch FCE, data,
  caminho/tamanho/mtime do save, slots, clubes e competições. Guarda uma
  cópia auxiliar por SHA256 do DATA e data em server16_competition_views,
  junto dos dados auxiliares das carreiras. Um rollback não usa dados futuros
  ou de outra carreira.
- Mercado, Ver clubes e apuração compartilhada usam essa mesma evidência.
  Liga e copas são somadas; pai/filho e FCE/DB sobrepostos não são duplicados.
- Contadores e gols são atribuídos ao contrato. Um novo técnico não herda
  automaticamente a campanha do antecessor. Não são inventados adversários,
  placares individuais, datas de jogos ou títulos a partir de agregados.

## Validação e limites

O primeiro teste instalado encontrou uma falha de inicialização: o objeto
simulador (tipo 5) continha data inválida (-1) e impedia o início da fila.
Agora a captura usa CalendarManager +0x34, através da identidade corrente
CareerContextRead, validando processo/epoch/registro/serviço/sequence. A
leitura da execução real pid 12976 confirmou 10/08/2026 nesse calendário.
O teste C cobre avanço da data, data inválida, troca de contexto e sequence.
Os logs derived_standings_started/complete identificam fases e linhas; neste
save foram identificadas 145 fases LEAGUE, incluindo a 933 da La Liga e
temporada regular/Apertura/Clausura.

A conferência offline com os 20 registros da tabela nativa aberta confirmou
Barcelona: La Liga 5 J / 15 PTS / 13 GP / 1 GC, Supercopa 1 J / 3 GP / 1 GC;
total de seis jogos. A comparação preservou o hash do save original.

Passaram os testes C da fila por fase/contexto/data e do ABI de chamadas,
90 testes do mercado e 129 do navegador em grupos isolados (125 + 4).
A execução monolítica do navegador apresenta colisão de imports entre os
build_package de banco/mercado: test_ranking_navigation recebe o read_nav
errado. Os quatro testes de navegação passam isoladamente. Esse arquivo de
navegação não foi alterado por esta correção.

Na execução real pid 4476, o cálculo automático terminou e publicou 1.151
campanhas derivadas. A apuração compartilhada cobriu 175 competições e
1.549 clubes com jogos. Barcelona teve contadores 3 vitórias em casa e 2
fora na liga, mais a Supercopa, totalizando 6 jogos e gols 16–2.
O modelo publicado do mercado e o banco appointment_campaigns foram
conferidos com esses totais. O usuário confirmou seis jogos nas duas telas.

A primeira abertura ainda podia exibir o pacote parcial de dois jogos
enquanto o pacote completo era construído em background. O mercado agora
aguarda a publicação global concluída, validada por carreira/processo/epoch/
data, antes de apurar demissões ou gerar perfis. O teste do worker verifica
que a espera não abre o banco, não avalia técnicos e não publica o perfil
parcial. A proteção foi instalada com o FIFA aberto, reiniciando apenas o
auxiliar isolado com handoff para preservar o branch atual.

Instalação local, sem commit ou push. O backup da instalação anterior e o
manifesto dos arquivos estão em code-release/coach-global-install-20261031.
