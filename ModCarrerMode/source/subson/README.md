# Banco de reservas

Configuração: `BENCH_SIZE=12` e `MIN_PLAYERS=11`. Reinicie o FIFA e o
Server16 depois de atualizar as DLLs. A entrada na partida e o retorno pelos
resultados até a caixa de mensagens foram conferidos no FIFA com essa
configuração em 23/10/2026.

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

## Validação da partida (v5)

`subson_match_gate_v5.dll` é um módulo separado, adicionado depois da ponte na
lista de mods. O módulo preserva a ponte original e não altera os provedores
dos cards nem os dados dos jogadores.

A correção anterior ajustava a montagem do banco, mas não a consulta anterior
que decide o W.O. A nova DLL redireciona somente três chamadas de
`GetSquadStatusForTeam` na entrada da partida e no retorno da seleção do time.
Essas consultas recebem zero reservas obrigatórias. O verificador original
continua exigindo 11 titulares; a montagem continua limitada aos jogadores
aptos restantes, até 12. A regra de 12 da competição continua intacta.

O redirecionamento troca instruções CALL completas de cinco bytes. O destino
altera apenas R8D (numSubs) e salta para a função original, preservando flags,
pilha, demais argumentos e resultado. A DLL recusa os patches antigos nas
instruções `05910569` e `05C449AC`, confirma os bytes/unwind de todos os
chamadores e só instala depois de verificar o ajuste de montagem já ativo.
Se a instalação inicial da ponte falhar, o novo módulo instala a mesma montagem
variável com validação de assinatura e tenta novamente em falhas transitórias.
Isso evita que a checagem fique desativada após reiniciar, como ocorreu no teste
da revisão v4. O log registra a montagem e a validação separadamente.

Validação local: a rotina nativa emulada sobre uma cópia da RAM da carreira
retornou 4 (insuficiente) para o adversário da carreira com 12 reservas obrigatórios e 0
(apto) com zero obrigatórios. Nenhum save foi escrito nessa reprodução.
`test_match_gate.c` testa 1632 combinações, os argumentos/flags/pilha,
instalação/retirada e rejeição de conflitos; os testes anteriores da ponte e
do limite variável também continuam passando. A entrada na partida com elenco
curto e a saída pelos resultados foram confirmadas no teste dentro do FIFA.

Confira `career_match_gate_v5 ... installed` em
`ModCarrerMode/logs/subson_match_gate.log`. O módulo pode ser desativado
retirando sua linha de `enabled.txt` e reabrindo o FIFA.

## Retorno da partida e carregamento dos cards

O `dinput8.dll` desta revisão vincula a atualização adiada dos cards à tela
nativa da Central. Ao abrir resultados, salvamento, preparação da partida ou
outro ambiente, a referência anterior é descartada antes de chamar novamente
o provedor nativo de estatísticas. Isso evita reutilizar o componente da
Central durante a reconstrução dos dados de outra tela.

A instalação dos cards também procura outra página livre para os desvios
quando um mod já ocupou o endereço preferido. Os testes de escopo, conflito
real de alocação, inicialização nativa, transferências e agendamento estão em
`../career_native/scripts/tests/`. Saves e logs não fazem parte do pacote.
