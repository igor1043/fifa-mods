# Ordem de inicialização da carreira e captura médica — correção local

O vestiário iniciava sua captura dos setters da lista de lesões enquanto o
núcleo ainda aguardava a validação de todos os pontos da carreira. Se o
vestiário entrasse primeiro, o preflight encontrava um destino diferente em
`injury_player_id_capture` e suspendia a instalação inteira. A sequência também
deixava de sinalizar o adaptador de compatibilidade de memória.

Na sessão com falha, o log do vestiário registra a captura antes do timeout do
preflight. O log do L9 registra capacidade de carreira de 2.500.000, enquanto o
INI instalado requer 3.600.000. Um save novo dessa sessão ficou 1.100.000 bytes
menor. O DATA antigo preserva o hash registrado antes da revisão financeira,
checksum válido e seus três bancos internos. Esses testes não substituem a
confirmação de carregamento pelo FIFA.

O host agora exporta `Fifa16CareerHooksReady` somente após instalar todos os
hooks. O vestiário espera esse sinal e valida os destinos pertencentes ao host
antes de encadear seus setters. Com host antigo, setters ainda originais também
permanecem intactos, e a tentativa é repetida. A captura não toma posse dos
pontos durante o preflight nem aceita callbacks de outra DLL.

Testes: `test_room_medical_startup.cmd` reproduz a ordem invertida, conserva os
bytes originais antes da prontidão e verifica encadeamento/restauração.
`test_native_patch_preflight.cmd` mantém a rejeição de destinos desconhecidos e
verifica o novo sinal. As DLLs e fontes ficam sincronizadas no jogo e no
desenvolvimento. Não há reparo ou escrita de DATA/INDEX nesta correção.

Após reiniciar pelo Server16, confirmar nos logs: instalação dos hooks da
carreira, sinal do adaptador Swiss, handover da capacidade 2.500.000 → 3.600.000
e captura médica posterior. Retestar o save antigo preservado; não converter
silenciosamente a carreira criada com o limite incorreto.
