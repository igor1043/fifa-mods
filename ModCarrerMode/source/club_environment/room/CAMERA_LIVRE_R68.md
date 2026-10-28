Vestiário — revisão local 68
===========================

O menu contém Cenas, Jogadores do time e Câmera livre, com foco de mouse,
teclado e controle. A câmera livre mantém a sala renderizada pelo FIFA e usa
os mesmos obstáculos das cenas. Não há avatar adicional nem controle de um
jogador de futebol: a visão é em primeira pessoa, a 1,65 m do piso.

Controles: WASD anda; segurar o botão direito do mouse permite olhar; as setas
também viram a câmera; Shift acelera. No controle, o analógico esquerdo anda,
o direito olha e pressionar o esquerdo acelera. Voltar/Esc/B retorna às cenas.
As legendas de controle são do HelpManager original do FIFA. O mouse não é
reposicionado nem preso à janela. Ao perder o foco, nenhum movimento é lido.

A movimentação divide deslocamentos em passos de até 6 cm, testa paredes e
móveis com uma cápsula contínua de 23 cm de raio e desliza ao longo dos obstáculos. Não atravessa o
chão nem voa. A saída restaura a posição da cena anterior. Os comandos -4 e -5
usam a mesma validação de clube, sequência e nonce das cenas existentes.

Os cabides recebem varão e dois suportes presos ao fundo do armário, aplicados
pelas mesmas matrizes das camisas de cada clube. O teto usa módulos de 60 cm:
as luminárias ocupam dois módulos e compartilham a origem da grade da textura.
A área médica mantém seu teto separado. As malhas/material slots não ligados
ao teto permanecem byte a byte iguais. `room_visual_r68.py` gera somente os
assets próprios do ambiente a partir das malhas do vestiário instaladas.

Testes: `native/test_room_free_camera.cpp`, `test_room_visual_r62.py`,
`test_room_visual_r68.py`, `test_room_ready.py` e o teste de inicialização médica.
Nenhum desses testes escreve na carreira ou altera a base de dados do jogo.

Refinamento 69: o deslocamento lateral e o giro seguem o eixo direito da matriz
real da câmera do FIFA. W avança, S recua, A desloca à esquerda e D à direita
em qualquer orientação. A caminhada passou a 1,70 m/s e a corrida a 2,80 m/s.
Um balanço visual inferior a 1,1 cm acompanha a distância efetivamente andada,
sem alterar a altura do corpo usada nas colisões nem a direção de mira. Ele
suaviza ao começar/parar, não continua ao pressionar contra uma parede e fica
zero quando parado. Testes comparam as direções à matriz nativa e verificam
movimento/passos a 30 e 120 FPS.

Refinamento 70: todas as câmeras do vestiário (cenas, carregamento, câmera
livre e visualização do elenco) usam corte próximo de no máximo 5 cm. Isso
evita recortar os armários, macas e jogadores com o plano de ~83 cm herdado
do estádio. O plano distante não muda; ao sair, o corte original é restaurado
se ainda pertencer ao mod. As câmeras externas permanecem com a projeção do FIFA.

A colisão do corpo é contínua entre 30 e 165 cm, com raio de 23 cm, cobrindo
também tampos finos entre as antigas amostras. Duas caixas legadas que reuniam
folhagens decorativas espalhadas pela sala do treinador são excluídas da
colisão: seus limites ocupavam quase 8 m e fechavam a passagem aberta. Paredes,
batentes, folha da porta, móveis e macas conservam suas colisões. A geometria
visível não é alterada. Os testes usam os obstáculos reais da sala para verificar
entrada/saída pela porta, bloqueio das paredes e colisão contínua de móveis finos.
