# Técnicos: malha, cabelo e animações do visualizador

Atualização posterior do cabelo e cache: ver `VISUALIZADOR_CABELO_POSES_CACHE_20261101.md`.
A descrição da máscara v3 abaixo registra a etapa anterior; a versão ativa passa a ser v4.

Revisão de 1/11/2026 dos 20 técnicos do pacote MANANGER BR. As imagens do FIFA
mostraram que os testes anteriores com clipes de torcida não reproduziam os
defeitos da pose de braços cruzados. A revisão usa o exportador do visualizador
(`generate_lineup.exe`) e os clipes nativos de técnico.

## Geometria e pesos

`Repair-NativeManagerSurfaces.py` recebe o manifesto, fontes e mapas de vértices
da conversão, e grava um pacote separado para revisão antes de instalar.

Nos 15 FBX, os pesos da roupa são transferidos do técnico nativo usado como
referência (Jardim), ajustado às articulações de cada fonte. O campo contínuo
é compartilhado pela pele de braços/tronco e pela base escondida do pescoço.
A pele coberta recebe uma pequena folga interna para não atravessar ombros e
golas. A mandíbula é recuperada da geometria original e ligada progressivamente
à cabeça, preservando a transição do pescoço.

A rotação usada anteriormente para encaixar a articulação pé/dedos inclinava
as solas dos FBX em aproximadamente 5 graus. A revisão preserva a orientação
da sola original, ajusta sua altura pelo apoio do Jardim e faz uma transição
no tornozelo. Nos cinco modelos RX3 nativos, todas as posições originais são
preservadas, incluindo o apoio que já estava correto em Jardim e Artur Jorge.

Nos 20 modelos, a roupa recebe uma face interna, 1,5 mm abaixo da superfície,
com normal e orientação inversas e os mesmos pesos/UVs. O verso físico evita
que uma superfície fina deixe o cenário aparecer quando uma manga dobra.
A orientação das faces é conferida com as normals autorais e as tangentes são
recalculadas. As costuras revisadas na etapa anterior são mantidas. Não se
aplica transparência à roupa nem se fundem UVs de peças diferentes.

O bind de 31 ossos, a paleta ativa, as texturas opacas e as duas variantes de
clima são preservados. Interseções de mãos com um corpo mais volumoso ainda
podem depender da combinação de proporções e pose; a revisão não altera a
animação nativa para adaptar o corpo de cada técnico.

## Cabelo no visualizador

Os mapas fornecidos têm alpha 255 em todos os texels. A máscara baseada no
contraste RGB da primeira revisão apagava mechas claras e escuras, dando o
aspecto de cabelo ralo. A versão 3 de `coach_surface.py` mantém o miolo das
faixas opaco e suaviza somente uma borda estreita e a ponta. Os cartões recebem
um verso com vértices e normals independentes, para aparecerem dos dois lados.

A separação ocorre somente para os 20 IDs auditados com rig de 31 ossos, no
caminho do visualizador de técnicos. O corpo mantém a textura original opaca;
o cabelo usa outra página com alpha. Não é uma recuperação do alpha autoral:
a fonte não contém essa informação. O shader do ator SLC durante a partida
não é trocado por essa etapa; os arquivos SLC recebem as alterações geométricas.

## Alternância de animações

`coach_animation.py` escolhe uma animação por pedido de entrada na tela:

- `coach_crossed.json`: braços cruzados, DCT nativo `ant:131172280`.
- `coach_hands_on_hips.json`: mãos na cintura, DCT nativo `ant:131175124`.
- `coach_standing.json`: postura neutra de pé, DCT nativo `ant:131176848`.

As duas novas opções foram decodificadas dos bancos da instalação do FIFA,
sem gerar movimentos artificiais. A escolha é aleatória e exclui a opção
imediatamente anterior. A mesma requisição (PID, sequência e clube) mantém sua
escolha durante atualizações; uma nova entrada pode escolher outra postura.
A identidade do cache inclui nome e conteúdo do clipe, versão da superfície e
modelo do clube. Objetos antigos ainda carregados pelo jogo não são apagados.
Uma instalação com somente um dos clipes continua funcionando.

## Aplicação e validação

O estudo local e a cópia anterior estão em
`U:/mods/estudos/102_TECNICOS_COSTURAS_CABELO_20261101/`. O pacote de 80 RX3 é
aplicado no jogo, em desenvolvimento e no backup de modelos; os helpers e os
dois novos clipes vão para jogo e desenvolvimento. Minifaces e regras do
mercado de técnicos não fazem parte desta alteração.

A verificação cobre formato RX3, bind/paleta, pesos normalizados, UVs e texturas
preservadas, buffers e streams nativos dos 20 técnicos nas três animações.
Os testes do seletor cobrem estabilidade por entrada, variação sem repetição,
fallback de clipe único e estado inválido. Os da superfície cobrem corpo/RGB
preservados, preenchimento do cabelo independente da cor e versos das mechas.

As prévias em Blender usam a geometria efetivamente exportada e as poses dos
clipes nativos, com iluminação aproximada e descarte de verso na roupa. Não
são capturas do FIFA nem garantia de que todas as interseções foram eliminadas
em todas as poses. É necessário reiniciar o FIFA para recarregar os helpers e
conferir visualmente o resultado no renderizador do jogo. Não há commit/push
nesta revisão.
