# Banco de reservas

O pacote original WorkLab continua responsável pelo banco e suas animações.
`SubsOn.ini` deve usar `BENCH_SIZE=12` e `MIN_PLAYERS=11`. O adaptador mantém
12 como máximo e passa ao FCE, para cada equipe, o menor valor entre a regra
da competição e a quantidade de jogadores aptos além dos 11 titulares.
Exemplos: 11 aptos = nenhum reserva; 12 = um; 22 = onze; 23 ou mais = doze.
Jogadores não são duplicados e as regras globais da competição não mudam.
O teste nativo de menos de 11 aptos continua ativo.

O ponto de montagem local usa a contagem nativa já calculada em R14D, antes
da chamada do FCE que compõe a equipe. O detour verifica executável, bytes,
função/unwind e a correção de mínimo 11 do WorkLab antes de instalar.
Não usa varredura nem escrita de elencos em um worker.

`build.cmd` compila a DLL e executa testes de comandos, escopo, thunks nativos,
instalação/remoção e 1632 combinações de contagem e regra do banco.
Reinicie o FIFA depois de atualizar `subson_bridge.dll`.
Confirme `career_optional_bench_v1 ... installed` em
`ModCarrerMode/logs/subson_integration.log` e teste uma partida com elenco curto.
