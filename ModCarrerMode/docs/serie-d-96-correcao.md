# Série D unificada: banco e regras alinhados

Branch: `fifa-friends-v12-integracao-suico`. Sem commit ou push.

## Alterações

- C351 e C354 passam para a árvore do Brasil, país 54, conforme o banco novo.
- C351 tem uma fase de liga e uma tabela de 96 clubes: turno único, 95 rodadas,
  48 partidas por rodada, 4.560 partidas na temporada. Primeiro colocado campeão,
  quatro primeiros sobem para a Série C, quatro últimos descem para a divisão 354.
- C354 promove quatro clubes para C351. A Série C já rebaixava quatro para C351.
- As antigas C352/C355/C356 deixam de participar. Os IDs dos objetos são mantidos
  como nós inativos para preservar os IDs das demais competições e os contratos V12.
  As quatro fases antigas de C351 ficam sob um desses nós inativos; C351 tem apenas
  sua nova fase. Esses nós não têm standings, calendário, tarefas ou encaminhamentos.
- As cinco tarefas de seleção de C351 na Copa do Brasil usam seleção sequencial
  `FillFromLeagueInOrder`. Esse padrão já existe na Copa da Itália da instalação
  V12 para dois grupos alimentados pela mesma liga. O chaveamento não foi alterado.
  A rotina nativa consulta o filtro compartilhado e registra os clubes aceitos;
  não se usam quatro seleções independentes dos mesmos primeiros 16 clubes.
- 66 referências de liga anterior apontando para ligas removidas são migradas para
  C351. As posições atuais e anteriores de 351/354 são organizadas em sequências
  de 1 a 96 e de 1 a 30. A ordem combina as antigas posições, com ID do clube como
  desempate estável; não representa resultados reais de uma temporada anterior.
- Jogadores, elencos, uniformes, estádios, formações, esquema binário e XML do banco
  novo são preservados. Somente campos numéricos de `leagueteamlinks` e seus CRCs
  mudam no DB; as outras 136 tabelas permanecem iguais.
- O instalador inclui o payload compdata e recebe `-ReplaceDatabase`, que substitui
  explicitamente o par DB/XML. Por padrão, mantém os dois arquivos existentes.

## Calendário e capacidade

Rodadas entre os dias relativos 71 e 354 da temporada, sem coincidir com as datas
atuais da Copa do Brasil, Copa do Nordeste, copa 24 e estaduais que contêm clubes
da Série D. Há ao menos dois dias entre rodadas de liga. Não se promete descanso
mínimo de dois dias em relação a todas as copas, pois 95 rodadas tornam o calendário
denso. O ajuste dinâmico por seleções internacionais continua herdado da V12.

Contagens após a mudança: 2.257 objetos, 137 competições ativas, 4.779 settings,
1.372 tarefas, 6.720 standings, 3.881 encaminhamentos, 6.101 registros de calendário.
Os limites ampliados já presentes na integração são mantidos; nenhuma DLL é trocada
por causa desta correção. Os números cabem nos limites registrados do patcher.

## Validação e limites da conclusão

O gerador confere os campos alterados, os CRCs, a preservação das outras tabelas,
96 posições consecutivas, 95 rodadas de 48 jogos, datas excluídas, vínculos de liga
removidos, nós e tarefas inativos. A instalação confere hashes das cópias e mantém
um plano de recuperação. Isso não constitui validação em execução do FIFA.

O DB de entrada ainda declara seis bits para `nummatchesplayed` e cinco para
vitórias/empates/derrotas em casa/fora. A tabela de competição FCE usa suas próprias
estruturas, mas a persistência e os consumidores da carreira durante uma temporada
de 95 jogos precisam ser observados no jogo. Não foi alterado o layout binário
desses campos sem uma alteração correspondente demonstrada nos leitores nativos.
Portanto, esta revisão não é apresentada como comprovação de uma temporada inteira.

Para avaliar: criar uma carreira nova com ABC ou outro clube da Série D; verificar
as sete abas, navegação, tabela com 96 clubes, simulação e entrada em partida.
Depois conferir contagens após a rodada 64, fim da temporada e acesso/rebaixamento.
Não usar o save que já foi criado com banco/regras incompatíveis como única avaliação.
Nenhum save foi apagado, e o jogo não foi iniciado automaticamente.

## Backup e recuperação

Snapshot anterior à correção:
`J:\mods\fifa 16\estudos fifa 16\backups\serie-d-96-correcao_20261006_154259`

Contém compdata completo do jogo, banco novo antes da migração, banco que estava
no Dev, loaders, candidato gerado, manifestos e backup da instalação.

`Restaurar-jogo-e-dev.cmd`, nessa pasta, executa `Restore-SerieD96.ps1` e recupera
os arquivos anteriores do jogo e Dev. A restauração recusa arquivos modificados
posteriormente e exige a branch de integração para o Dev. A correção retirada fica
arquivada. Os bancos anteriores do jogo e Dev eram diferentes; cada um é restaurado
ao seu próprio estado. DLLs não foram modificadas nesta revisão.

`repair_serie_d_96.py` reproduz o candidato a partir desse snapshot. Exemplo:

```powershell
python ModCarrerMode/tools/swiss_integration/repair_serie_d_96.py --backup "J:\mods\fifa 16\estudos fifa 16\backups\serie-d-96-correcao_20261006_154259" --reader ModCarrerMode/tools/swiss_integration/fifa_db_reader.py
```

Fonte externa consultada para conferir o formato dos parâmetros de tarefas:
[código do editor CompData](https://github.com/andresedu1996/CompData-Editor-FC/blob/main/taskswindow.js).
As decisões específicas de FIFA 16 se baseiam nos arquivos V12 e na DLL FCE
instalados, inclusive no padrão de seleção já usado pela Copa da Itália.
