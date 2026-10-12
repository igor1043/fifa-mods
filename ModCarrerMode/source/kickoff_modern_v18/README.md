# Kickoff v18 — remover a ação que força a postura antiga

A captura de 11/10/2026 confirmou o retorno durante PlayKick: o ManMove continuava apontando para (-1,83616; 0), mas a ação de prioridade 1,0 e vtable +2332B98 carregava tipo 22 em +360. O atleta saiu da posição atrás da bola para a frente enquanto essa ação executava. O PassKickOff tem getter +4F65BE0, que retorna 22; a ação PlayKick trata 22/23 especialmente (+51FF2C0).

A v18 copia somente a ação de primeiro passe validada (0x380 bytes, um pedido, cobrador/ID/equipe, origem no ponto capturado, alvo no receptor recuado, vtable do pedido +2314850) e muda +360 de 22/23 para o passe normal 0. Os demais 892 bytes ficam iguais, incluindo origem, destino, carga e informações físicas. Mantém os alvos de movimento e colocação atrás da bola e o limite temporal de dois segundos para essa transição.

Mantém o ajuste de tempo da v15, confirmado no solver 40 -> 256 e 0,96 -> 0,15, e a redução de carga 0,75. Validação visual da postura ao executar o primeiro toque permanece pendente desta versão. Um evento por saída evita log repetido. Compilar build.cmd, MSVC /W4 /WX; backups no estudo 25_KICKOFF_TUNING_20261011.
