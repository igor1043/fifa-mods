# Bolas extras visuais — protótipo v3

DLL independente para FIFA 16 x64, executável PE timestamp `577DE45C`.
Reutiliza os recursos de modelo/material da bola da partida (renderizador índice 1).
Não cria entidades, colisões, jogadores, scripts de IA ou bolas de gameplay.

Distribuição inicial: 13 cópias, duas atrás de cada gol e nove nas laterais.
Coordenadas em centímetros para campo de 105 × 68 m; posições em `ball_layout.h`.
Centro da bola elevado em 5,2 cm, com suporte baixo arredondado embaixo.
Sem cones. As cópias são estáticas; o primeiro protótipo não acrescenta sombras.

## Implementação

- Slot virtual `+2205EC0`: desenho nativo `+436B530`, fase 0.
- Slot virtual `+2205F98`: registro de limites visuais `+436B350`.
- Objetos de renderização e estado de 0x820 bytes copiados na pilha, alinhados.
- Estado original protegido pela seção crítica nativa somente durante captura.
- Preserva os 1–3 slots gráficos já ocupados pelo jogo; cópias usam os próximos
  13 slots livres, respeitando o limite nativo de 16. Se não houver espaço, pula.
- O desenho original é executado normalmente, seguido do desenho das cópias.
- Não modifica posição/matriz/contagem da bola original nem seus recursos.
- Não altera os hooks de saída de bola, banco, substituição ou mascote.
- Slots verificados antes da instalação, troca atômica, rollback e API Stop.
- DLL fixada na memória para callbacks em andamento após desativação.

`build.cmd` compila os testes de disposição/guardas e a DLL com `/W4 /WX`.
Log: `ModCarrerMode/logs/multiball_visual.log`.

Estado: compilado e carregado ao vivo em 10/10/2026. Captura mostrou bolas
fora do campo; conferência de perto pelo usuário e reinício ainda pendentes.
Habilitado em `mods/enabled.txt` no jogo e na pasta de desenvolvimento.
Código e DLL publicados na branch fifa-friends-v12. Validação visual de perto permanece pendente.
