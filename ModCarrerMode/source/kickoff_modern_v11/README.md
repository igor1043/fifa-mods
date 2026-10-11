# Saída de bola moderna — v11

Ajuste de 11/10/2026 sobre a v10 que o usuário informou estar funcionando.

- A carga de força do primeiro passe para o receptor recuado recebe fator 0,75 (redução de 25%). É a carga nativa do comando; a velocidade final da bola depende da física do jogo.
- O cobrador recebe a orientação para a própria defesa já na primeira colocação, quando a posição central original do receptor permite identificar o lado. A correção continua na preparação do primeiro passe e termina quando a cobrança é encerrada.
- O receptor, o afastamento dos demais titulares e as exclusões de reservas/adversários seguem a v10.

A redução exige o objeto nativo de PassKickOff, o cobrador da saída corrente, a saída ativa e o alvo já redirecionado. O campo de força por instância (`+0x24`) é alterado somente durante a montagem nativa do comando e restaurado em seguida. Cargas não finitas, nulas, negativas ou acima de 1 ficam intactas.

O plugin aplica quatro adaptações de CALL e duas trocas de vtable guardadas somente em RAM. Além das guardas existentes de imagem/chamadas, verifica a vtable da preparação do kickoff, o destino de montagem do comando e a instrução que lê a carga. O executável em disco não é alterado. Não usa Frida.

Carregamento: `kickoff_modern_v11/kickoff_modern_v11.dll` em `ModCarrerMode/mods/enabled.txt`, com a v10 comentada. Log: `ModCarrerMode/logs/kickoff_modern_v11.log`. Apenas uma versão de kickoff deve estar habilitada. Reinicie o FIFA que já estiver aberto para carregar a v11.

Compilação: `build.cmd`, MSVC C11 `/W4 /WX`. Testes cobrem afastamento, exclusões, orientação espelhada para a própria defesa, identificação do lado a partir da pose central, redução de carga e entradas inválidas. Compilação e testes passaram. A intensidade percebida e a animação ainda precisam de confirmação em partida.

Evidência nativa lida do jogo: `fifa16.exe+0x233A3D8` aponta para `+0x52EE300`; a rotina lê a carga em `+0x52EE348` e a copia para a requisição de passe. A preparação específica está em `+0x52E5860` e usa essa mesma entrada virtual. A direção nativa continua `(cos(yaw), 0, -sin(yaw))`, com o lado da defesa identificado pela geometria da saída.

Rollback: com o jogo fechado, restaure o `enabled.txt` do backup desta entrega; a DLL v10 foi preservada. Nenhum commit ou push foi feito.
