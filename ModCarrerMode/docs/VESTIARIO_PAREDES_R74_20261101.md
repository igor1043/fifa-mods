# Vestiário: acabamento arquitetônico R74

Revisão local para substituir as faixas diagonais repetidas da R73 por paredes
neutras. Referência de materiais: [AXA Training Centre, Liverpool FC](https://www.mclh.co.uk/project/liverpool-football-club-axa-training-centre/)
e [fotografias oficiais do vestiário](https://www.liverpoolfc.com/news/axa-training-centre/415758-inside-liverpool-s-new-dressing-rooms-at-the-axa-training-centre).
As fotografias foram consultadas como referência, sem incorporá-las aos assets.

## Aparência

- Pintura clara de tom quente e granulação muito discreta, sem grafismos repetidos.
- Rodapé escuro nas paredes de serviço, interrompido nas duas portas abertas.
- Cerâmica neutra de 60 x 30 cm atrás da bancada de hidratação, com juntas finas.
- Moldura de 2 cm em carvão no mural, substituindo a moldura grossa na cor primária.
- Identidade de cada clube mantida nas camisas, assentos, placas, escudos e mural.
- Porta dupla de saída corrigida: a extensão longitudinal da R72 havia alongado
  só parte da geometria. O conjunto agora é deslocado inteiro e a placa tem 4:1.

Os 40 PNGs editáveis dos clubes continuam intactos em
`ModCarrerMode/data/club_environment/room/clubs/<id>/mural.png`.
Não há alteração de save, banco, regras financeiras, câmera ou colisão.

## Carregamento

`room_interior_r72.prepare` prefere o par `interior_r74.json/rx3` quando ambos
existem. Os materiais permanecem nos mesmos slots, com um slot adicional para
a cerâmica. Ausente o par R74, continua usando o modelo R73/R72 anterior.
O recurso tem um caminho novo para evitar reaproveitar a malha R73 em cache.
O Server16 copia o novo módulo Python para o runtime na inicialização habitual.

## Validação e instalação

Pasta de revisão: `code-release/locker-room-wall-finish-r74-20261101`.
Inclui `before-r74.zip`, instalador e rollback por arquivo, revisão de buffers
RX3, montagens completas de Criciúma e Flamengo e 15 testes de regressão.
Prévias produzidas com as malhas e texturas reais em renderizador offline;
não representam uma captura da iluminação do FIFA. Validação visual no jogo
permanece pendente. Nenhum commit ou push nesta revisão.
