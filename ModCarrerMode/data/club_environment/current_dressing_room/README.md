# Current Dressing Room

Estrutura genérica do vestiário atual (V3), com arte opcional por ID de clube.
Os armários são instâncias de um único módulo: 12 ao lado do quadro e 13 em cada
lateral, totalizando 38. As vagas restantes ficam vazias quando o elenco é menor.
O quadro, as portas, a sala do treinador e o departamento médico são preservados.

## Imagens editáveis

Crie `custom/<ID do clube>/profile.json`, usando `custom/profile.example.json`
como referência. Coloque os PNGs ou DDS nessa mesma pasta e informe os nomes em
`assets`: `cabinet` para a estrutura do armário, `backing` para seu fundo,
`corner` para as peças diagonais entre as fileiras e, opcionalmente,
`floor` para o piso e `feature_wall` para o painel atrás do quadro.
`wall_mural` indica a arte da outra parede, e `hydration_wall` a arte da área de
hidratação. Essas imagens também ficam na pasta do ID: `wall-mural.png` e
`hydration-wall.png`. O exemplo
do Flamengo está em `custom/1043/`.

As imagens continuam editáveis. O auxiliar converte o conteúdo para RX3/DXT5 com
mipmaps e guarda o cache em `data/sceneassets/server16_dressing_room_v3/`. Esse
cache pode ser recriado; mantenha os arquivos de origem. Para fundos verticais,
768 x 1536 é suficiente; pisos e madeira podem usar 512 x 512 ou 1024 x 1024.
Imagens dos materiais usam até 4 MP, com no máximo 4096 pixels por lado: uma
arte panorâmica 4096 x 1024 mantém seus detalhes, sem exigir uma imagem quadrada
gigante. Arquivos acima de 16 MP são recusados. Os escudos e uniformes continuam
vindo dos próprios assets do jogo.

As quatro faixas superiores são imagens completas. Edite `fascia-back-left.png`,
`fascia-back-right.png`, `fascia-left.png` e `fascia-right.png` na pasta do clube.
Os dois primeiros arquivos cobrem os armários ao lado do quadro; os demais
cobrem as laterais inteiras. Textos, fotos e ilustrações fazem parte desses PNGs:
não há frases no JSON nem letras 3D sobrepostas. DDS também é aceito.
O `profile.json` apenas associa cada arquivo a `assets.fascia_back_left`,
`assets.fascia_back_right`, `assets.fascia_left` e `assets.fascia_right`;
`theme.banner.panels` usa `mode: "image"` e o `asset_key` correspondente.
Mantenha a proporção do arquivo ao editar. Sem custom, o vestiário gera imagens
com o nome e as cores do clube. A opção Custom só aparece quando há arte válida.

## Configurações no jogo

O seletor geral Default/Custom controla as artes específicas do clube. Custom
só fica disponível quando há uma imagem válida no catálogo daquele ID.
Default usa nome, cores e escudo do clube no painel, sem a arte customizada.

O botão Personalização do vestiário também fica disponível durante a câmera
livre: Q no teclado padrão do FIFA ou R3 no controle. Esse atalho usa o comando
nativo `VB_FE_R3`, definido em `buttonDataKeyBoardMouse.ini`; não depende de
eventos Flash de teclado. WASD permanece reservado ao movimento.
As setas mudam composição dos armários, fundo, contorno, piso e escudo central.
Há madeira clara e escura; o contorno inicia na cor primária do clube e pode
usar branco, preto, madeira ou a cor secundária. Chão é
o padrão; chão e teto nunca são exibidos simultaneamente. As preferências ficam
por clube em `ModCarrerMode/data/club_environment/room/v3-settings/<ID>.json`,
separadas do arquivo de carreira. As setas só editam uma seleção temporária.
Voltar descarta essa seleção; Aplicar grava o conjunto inteiro em uma operação,
somente se houver diferença. Aplicar sem mudanças não recarrega a sala.

As artes da estrutura, do fundo e dos cantos usam arquivos independentes, para
evitar repetir a mesma ilustração em todas as faces. Os 20 clubes do catálogo
da Série A têm uma estrutura discreta e um painel de canto com as próprias
cores e identidade gráfica; os PNGs continuam editáveis por ID de clube.
Os arquivos são nomeados pela área: `locker-frame.png`, `locker-backing.png`,
`corner-panel.png` e `feature-wall.png`. Os dois cantos usam a mesma imagem,
ambos com leitura normal; a geometria espelhada não espelha a arte.
O estilo Default também desliga as artes customizadas do mural e da hidratação.
As faixas usam pequenos trechos da própria imagem em atlas de 1024 x 1024 ou
1024 x 2048, com bordas de proteção. A densidade dos pixels no eixo horizontal
fica próxima da vertical, evitando que o FIFA selecione uma imagem muito
reduzida por causa do antigo esticamento de uma textura alta sobre uma faixa
estreita. Não é necessário editar esses atlas: são cache gerado dos PNGs/DDS.
O material nativo original e a cadeia completa de mipmaps foram preservados;
não se usa o material auxiliar experimental nem a sobreposição de letras 3D.
As faixas atuais usam os componentes `v3_image_band_*`.
O quadro de próxima partida também continua sendo uma imagem. Sua composição é
redesenhada dos dados da carreira, com resolução proporcional aos 235 x 148 cm
do quadro, e distribuída em trechos de atlas. Isso equilibra a amostragem dos
dois eixos sem alterar sua posição, dimensões, conteúdo ou o orçamento da
textura 4096 x 4096 original. Não há letras vetoriais sobre o quadro.
O painel atrás do quadro alcança o teto e o escudo no piso mede 3,20 m.
A mesa central possui colisão para a câmera livre.

As trocas visuais reaproveitam os dados da carreira e os objetos que não foram
alterados. Os materiais fornecidos já têm cache pronto. Depois de editar imagens,
saia e entre no vestiário para recarregar. A primeira conversão de uma arte nova
demora mais que o reaproveitamento do cache. A V2
permanece preservada como entrada de compatibilidade e rollback; não aparece
como opção de versão na interface.

O comando Aplicar envia as seis escolhas de uma vez. Seus dígitos são montados
como texto, sem multiplicação de números grandes no APT do FIFA: isso evita o
arredondamento que podia trocar Custom por Default após várias ações. Salvos
de carreira e bancos de dados não participam dessas preferências visuais.
