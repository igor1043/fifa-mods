# Mascote na linha de fundo

Este componente parte da colocação v12 que já foi validada no jogo e acrescenta animação nativa de torcida ao mascote.

- O novo ponto de teste fica junto à bandeirinha, mais recuado e um pouco mais para o centro do gol, para tentar passar a fileira de placas. Coordenadas-base: X=±5850 cm e Z=3150 cm; em relação ao ponto anterior, recua cerca de 4,4 m e avança 0,8 m. A posição atrás das placas precisa de confirmação visual no jogo.
- Suporte de pacote: Flamengo (1043) e Palmeiras (383).
- Idle usa o comportamento em pé 26; gol do mandante usa comemoração 14 por 26 segundos. Gol do visitante e reação de tristeza ficam desativados.
- A malha animada substitui somente o modelo do mascote; as texturas do clube continuam as originais.
- O código verifica os pacotes antes de usá-los. Sem pacote de animação, tenta o modelo estático; sem pacote de mascote válido, mantém o fotógrafo normal.
- O build gera e copia mascot_goal_line_v13.dll para ModCarrerMode/mods/mascot_single.

Para compilar, execute build_mascot_single_v13.cmd nesta pasta. A instalação no jogo é feita separadamente por Install-MascotPhotographer.ps1; a restauração usa Restore-MascotPhotographer.ps1.
