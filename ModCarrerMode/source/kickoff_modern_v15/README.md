# Kickoff v15 — cobrador atrás da bola e tempo do passe

A rotação da v14 foi confirmada visualmente pelo usuário, mas o atleta ficou à frente da bola. A v15 posiciona somente o cobrador no lado contrário à sua defesa, preservando a distância original ao centro, Y e W. Colocação física, MoveHint e ManMove centrais e espera recebem esse alvo espelhado. Depois da preparação do passe, a mudança de posição termina.

O log v14 mostrou callback de velocidade ausente: a redução pretendida não foi confirmada. A v15 altera o tempo nativo do ShootRequest (+A4), que o solver +4D12D50 usa para dividir o deslocamento até o alvo. O builder do passe curto mantém 40 unidades nativas mesmo após o alvo ser recuado; agora o tempo é multiplicado por distância/6. O hook do construtor virtual +2314860 -> +510B210 filtra saída atual, alvo recuado exato e origem central. O log registra o tempo e a velocidade do solver antes/depois. Mantém redução da carga 0,75. Não afirma velocidade em m/s sem confirmação das unidades nativas.

Adoption permite atualizar a saída pausada pela RAM: XYZ do cobrador e seis campos de direção; receptor e bola preservados. Movimento em campo, reinício e força ainda precisam ser confirmados nesta versão. Compilação MSVC /W4 /WX e testes de espelhamento, posição, tempo e valores inválidos.
