# Kickoff v19 — usar PassHint do ponto atual

Alternativa solicitada: forçar o passe de onde o cobrador está, sem voltar ao ponto/pose antigos. A captura v17/v18 mostrou alvos ManMove atrás da bola, mas uma PlaceKickHint (+2332B98), tipo de comando 10, executando a postura de bola parada. Mudar apenas o subtipo em +360 não mudou essa classe.

A v19 substitui somente a primeira PlaceKickHint validada por uma PassHint nativa (+2314A00, tipo 6). Inicializa os 0x4B0 bytes com o construtor nativo +539BCD0. Copia cabeçalho, lista de pedidos e dica de entrada até +357; mantém a cauda própria de PassHint e seu formato, em vez da cauda de pose de PlaceKickHint. A prioridade original, origem, destino e carga são preservados; tamanho atualizado para 0x4B0 e alvo +470 recebe o receptor recuado. As guardas exigem mesmo cobrador/ID/equipe, dois segundos da primeira solicitação, um pedido, origem no ponto atrás da bola e alvo recuado exato.

Mantém a espera orientada e a posição atrás da bola e o ajuste de tempo do primeiro passe (40 -> ~256; velocidade do solver ~0,96 -> 0,15 nos testes anteriores). O giro antes do passe e a força foram confirmados pelo usuário; executar desse ponto sem reposicionar ainda requer validação v19. MSVC /W4 /WX e testes nativos passaram. Operação exclusivamente por RAM/arquivos, sem controle de interface.
