# Técnicos: revisão dos pesos das pernas

Revisão dos 20 técnicos do pacote MANANGER BR a partir da imagem de Renato
Gaúcho com a parte interna da calça puxada durante a pose de mãos na cintura.
Estudo e cópia anterior: `U:/mods/estudos/104_TECNICOS_PERNAS_20261101/`.

`Repair-NativeManagerLegWeights.py` altera somente índices e pesos do skin da
calça. Posições, normals, tangentes, UVs, índices de triângulos, bind de 31 ossos,
paleta ativa e texturas permanecem idênticos. Não há redução do volume original
do corpo nem exportação de nova geometria. As duas variantes de clima são
mantidas e a alteração vale para a tela e para o ator SLC que usa esses arquivos.

A região da calça é identificada pelo atlas efetivamente usado nos vértices de
joelho/canela. A maioria usa a célula central superior; Seabra e Carpini usam a
central intermediária, e Mancini usa a superior esquerda. Usar somente a altura
também alteraria as barras dos casacos, por isso esses vértices ficam fora.

Nos modelos convertidos de FBX que exigem correção, o campo de pesos da área interna das coxas
é interpolado de um técnico nativo funcional, com amostragem
independente para cada perna e mistura limitada à costura central da virilha.
A influência da perna oposta deixa de atravessar a coxa. As transições do
quadril e tornozelo são graduais. Vértices coincidentes de costuras UV recebem
os mesmos pesos, preservando as coordenadas de textura separadas. A normalização
continua em 255 com até quatro influências, dentro da paleta existente.

Os cinco modelos RX3 nativos preservam integralmente seu skin autoral. A
comparação também preservou os pesos anteriores de Mancini: o candidato
aumentava o alongamento das arestas nas três poses, sem justificar a troca.
O pacote final revisa 20 técnicos e altera o skin de 14. Use `--preserve 15`
para reproduzir essa decisão com o conversor. Nos FBX,
a correção se concentra na parte interna das coxas e na transição da virilha;
as áreas externas, joelhos e canelas que já deformavam bem são preservadas.
As áreas abaixo de 58 cm e acima de 103 cm não mudam; sapatos e roupa superior
também ficam fora pelo atlas. O encaixe dos pés já aprovado é preservado.
A revisão anterior do cabelo, as animações aleatórias e os modelos dos jogadores
não fazem parte desta alteração.

## Conferência e aplicação

Os pacotes passam no verificador RX3 contra o bind/paleta nativos, na comparação
byte a byte de todos os campos de vértice fora do skin e na igualdade das texturas.
As três animações nativas do técnico são exportadas e seus streams são verificados
nos 20 modelos. As prévias usam os modelos efetivamente exportados e a pose do
FIFA, em Blender com iluminação aproximada; não são capturas do jogo.

Os arquivos são aplicados em `U:/fifa 16/data/sceneassets/slc`, na mesma estrutura
do desenvolvimento e em `J:/mods/fifa 16/07_Backups_e_legado/tecnicos/tecnicos no jogo/data/sceneassets/slc`.
A cópia anterior dos três destinos foi preservada antes da edição. Helpers de
cabelo/cache, DLLs, Lua, minifaces e save não são alterados. Reinicie o FIFA para
recarregar os modelos e o exportador persistente. A avaliação visual final no
renderizador do jogo permanece pendente. Esta revisão não faz commit/push.
