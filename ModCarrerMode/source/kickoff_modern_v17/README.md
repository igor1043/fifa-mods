# Kickoff v17 — preservar o cobrador durante a transição para o passe

A v16 perdeu sua guarda quando a assignment de saída foi encerrada no clique do passe; o log registrou a preparação e a captura seguinte não encontrou assignment ativa. A v17 mantém o ponto capturado por até dois segundos mesmo nessa transição. Exige o mesmo ator, vtable de jogador, ID e equipe capturados. Apenas alvos centrais de MoveHint/ManMove e resets físicos deste cobrador são redirecionados para o ponto em que já esperava. Não altera o comando nativo de executar o chute. A orientação da colocação continua voltada para a própria defesa. A identidade e o prazo encerram a intervenção no jogo corrido.

O ajuste de tempo do passe também admite esse curto período após a saída, com alvo recuado e origem central exatos. Mantém tempo proporcional à distância e a redução da carga. Logs da v15/v16 confirmaram 40 -> 256 unidades de tempo e 0,96 -> 0,15 no solver; o usuário confirmou passe mais suave, mas ainda informou retorno da pose ao clicar. A execução completa sem retorno à pose antiga precisa ser confirmada na v17.

MSVC /W4 /WX e testes de geometria, posição, espelhamento, carga, tempo e entradas inválidas. Versões anteriores preservadas; somente uma versão de kickoff em enabled.txt. Operação por RAM e arquivos, sem controle da interface.
