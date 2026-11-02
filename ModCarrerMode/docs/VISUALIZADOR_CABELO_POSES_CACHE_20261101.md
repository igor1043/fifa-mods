# Visualizador: cabelo, poses e cache

Revisão de 1/11/2026, estudo local `U:/mods/estudos/103_CABELO_POSES_CACHE_20261101`.
A instalação preserva os modelos, mapas originais e DLLs. Não inclui commit/push.

## Cabelo dos técnicos

A versão 3 mantinha quase todo o cartão opaco e revelava seus retângulos. A
versão 4 de `coach_surface.py` identifica o layout pelos componentes e UVs:
faixas repetidas recebem um recorte com fios curvos, pontas afiladas e espaços
entre as raízes; pinturas contínuas recebem uma chave suave do fundo, sem
sobrepor a elas a grade de outro atlas. As normals do cabelo superior convertido
são suavizadas em torno do volume da cabeça; barba, corpo e rosto opacos ficam
fora desse ajuste. O verso das mechas continua separado.

O tratamento permanece restrito aos 20 IDs e rigs de 31 ossos auditados. Não é
um filtro aplicado a jogadores. As fontes não contêm o alpha autoral, portanto
a máscara dos técnicos é uma aproximação. Os 20 pacotes da etapa anterior,
instalados no jogo, desenvolvimento e backup de modelos, não são reexportados
nesta revisão. A máscara e as normals são usadas pelo helper do visualizador.

## Cabelo dos jogadores

A comparação anterior confirmou que o tratamento dos técnicos não era executado
nos jogadores e não havia alterado suas texturas. A investigação seguinte achou
uma diferença do visualizador: `native_assets.py` dividia o coeficiente de cabelo
em valores >=166 para a primeira malha e 21..165 para a segunda. Isso removia
informação de partes diferentes, e de cabelos personalizados com uma malha só.

A versão 5 preserva o canal R completo do coeficiente original nas partes de
cabelo, mantendo o RGB e tint originais. Nenhuma máscara estimada dos técnicos
é usada nos jogadores. Partes sem coeficiente continuam usando seu alpha original.
O comportamento de materiais que não são cabelo fica inalterado.

A partida usa `hair_material`/`hair_material2` com `player_hair_kk_alphaA/B`, como
consta no `player.lua`. A tela utiliza geometria animada em GameplayProp e os
materiais `prop_alpha`; esta revisão corrige a informação de transparência
publicada para esse caminho, sem trocar o shader nativo da partida nem presumir
compatibilidade do shader de cabelo skinned com o buffer de um prop. Preservar a
máscara não prova igualdade de iluminação, brilho e ordenação com a partida.
Essa diferença ainda exige conferência visual no FIFA.

Foram comparados nove jogadores exportados (14 partes de cabelo). As páginas
que não são cabelo e os buffers RX3 permanecem idênticos. As páginas de cabelo
são verificadas contra uma compressão DXT5 de referência da máscara completa e
do RGB original, sem os dois cortes antigos. Os arquivos originais continuam
intactos. Doze combinações de três jogadores e quatro clipes geram 204 quadros
nativos, com páginas de material iguais entre as poses.

## Quatro poses para a tela individual do jogador

- `idle_crossed.json`: braços cruzados (opção anterior).
- `idle_standing.json`: postura neutra, reutilizando o clipe nativo do técnico.
- `idle_hands_on_hips.json`: `PreGameIdles_HandsOnHips`, `ant:83421448`.
- `idle_shift_weight.json`: `PreGameIdles_ShiftWeight`, `ant:174855772`.

A escolha fica estável por PID/sequência/clube/jogador e varia sem repetição
imediata nas entradas seguintes. O estado dos jogadores é independente do dos
técnicos. Nome e conteúdo do clipe e a revisão do material entram no cache.

## Acesso negado / WinError 5

O log da sessão 32108 aponta a falha em `native_assets.prepare_texture` ao
substituir uma textura compartilhada. Há ocorrências equivalentes em outras
sessões e bloqueios transitórios em request/status TSV.

`preview_files.py` publica arquivos de cache completos uma única vez, sem
substituir o inode existente. Gravadores concorrentes reutilizam o vencedor;
um cache inválido pode ser ignorado e o resultado privado continua disponível.
O hardlink para um diretório privado é criado diretamente, sem renomear um
arquivo que pode estar aberto via outro alias. A publicação de diretórios
reutiliza uma versão completa concorrente. Leituras e trocas do protocolo TSV
possuem tentativas limitadas para bloqueios temporários. O worker repete o
pedido atual até três vezes se ainda ocorrer PermissionError, e não encerra
por uma falha de publicação do próprio aviso. Permissões permanentes continuam
sendo reportadas após o limite, sem repetição infinita.

Os testes incluem um handle real do Windows sem compartilhamento de DELETE,
dois encoders sincronizados produzindo o mesmo fingerprint, estado de entrada,
alpha original, corrupção/indisponibilidade e isolamento de IDs. Foram 25 testes
aprovados e um teste antigo ignorado por ausência de sua fixture; a integração
com nove jogadores reais cobre a comparação de materiais desta revisão.

## Aplicação

Helpers e três clipes novos são instalados em jogo e desenvolvimento, após
backup dos helpers anteriores. As fontes SLC/hair/heads, minifaces, Lua, DLLs,
save e regras do mercado de técnicos não são modificados. O novo cache é
versionado; não se apagam recursos ainda carregados pelo FIFA. Reinicie o jogo
para carregar os módulos atualizados. As prévias em Blender não são capturas do
FIFA; a avaliação final de aparência no jogo permanece pendente.
