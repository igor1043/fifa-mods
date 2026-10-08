# Banco de 12 reservas — versão 7

Prepara 12 reservas reais por equipe, preserva os sete modelos originais do banco e oculta os cinco adicionais enquanto estão fora do campo. Quando qualquer adicional entra por substituição, libera seu modelo. A quantidade de substituições permitidas pertence ao plugin separado substitution_all7_rulescan_native.

Validado pelo usuário em partida em 07/10/2026: transição funcionando e adicional visível depois de entrar. O log registrou extra_models_released=1. DLL publicada: SHA256 B3492EA95B3EEEFA88B788BE2EE4E25AAB56D09EAE1995B5A28103ECA5F953CB.

## Implementação

Mantém importação e preparação nativas 12/12, além das proteções da fila de recursos de 192 nós. O filtro identifica os cinco extras pelo ID inicial de cada equipe, pois a ordem dos objetos RNA é diferente da escalação. Usa os métodos Show/Hide originais do renderizador, sem escrever em assentos, coordenadas, ordinais, papéis AI ou propriedades de animação.

O carregador SetPlayerList fornece o estado banco/campo ao adaptar a CALL 43600A3. O FIFA também ativa um reserva sem recarregar esse descritor: a CALL 4359830 para 437CDE0 atualiza a inatividade nativa, limpando o bit 0x8, mas não a ocultação 0x2 do mod. O adaptador executa o setter original e libera somente a ocultação do adicional quando ele fica ativo. Guarda essa ativação para que um descritor antigo não volte a escondê-lo. Não há regra específica para goleiro nem coordenadas ou IDs de estádio fixos.

Os sete originais, previews e árbitros seguem o setter original. Callbacks de renderização executam no fluxo nativo; o worker apenas observa e invalida o plano quando a partida descarrega. Assinaturas, build conhecido e momento anterior ao carregamento protegem a instalação; falha reverte CALLs e a entrada Show da vtable. Não há criação de atores ou hook de assentos.

## Compilar e verificar

Execute build_bench_native12.cmd com o Visual Studio Build Tools configurado. Ele executa testes de assinaturas, importação, papéis nativos 7/12, renderer, fila, ABI, unwind e rollback e gera build/bench_native12.dll. O teste de renderer executa os 262 bytes capturados do setter original e reproduz a ativação sem novo descritor, verificando 0x1B -> 0x11, as duas equipes, IDs/slots embaralhados e igualdade dos parâmetros originais.

O build não instala automaticamente. Para publicar uma nova DLL, feche o FIFA, preserve a anterior e copie a saída para ModCarrerMode/mods/bench_native12/bench_native12.dll. A entrada bench_native12/bench_native12.dll deve permanecer única em mods/enabled.txt. Não é necessário regenerar assets.

No teste real, confira a entrada/transição, os 12 disponíveis e faça entrar um adicional (posição 8 a 12), verificando o modelo em campo. O log logs/bench_native12.log registra version=7 e os contadores de ocultação/liberação. O incremento do contador ajuda a diagnosticar; a imagem e a participação real precisam do teste da partida.
