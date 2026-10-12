# Kickoff v16 — executar o passe do ponto de espera

O usuário confirmou melhora do passe na v15 e informou que, ao chutar, o cobrador voltava para a posição original. A v16 captura a posição real do cobrador atrás da marca no instante em que o passe é solicitado. Durante os dois segundos iniciais da preparação, redireciona apenas os MoveHint/ManMove centrais deste cobrador e os resets de colocação para esse mesmo ponto. Os comandos de executar o chute continuam nativos. O prazo e a identidade da saída limitam a intervenção à aproximação inicial; não prende o atleta no jogo corrido.

Mantém o giro/posição atrás da bola e o ajuste de tempo do ShootRequest da v15. No teste real v15, o log confirmou tempo nativo 40 -> 256,00519 e velocidade do solver 0,96002 -> 0,15000; usuário confirmou melhora da força. A v16 registra apenas uma amostra por saída para evitar I/O repetido durante simulações internas. Confirmação do passe sem retorno à posição antiga ainda depende do teste v16.

Compilar: build.cmd, MSVC /W4 /WX. O FIFA em disco é preservado. Uma versão de kickoff ativa por vez; versões anteriores e enabled.txt salvos no estudo 25_KICKOFF_TUNING_20261011.
