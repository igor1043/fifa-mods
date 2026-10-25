# Ver clubes — cena nativa

O APT transparente mantém a navegação e as legendas originais do FIFA. O
plugin desenha o globo e os seletores; bandeiras, escudos e competições são
lidos do catálogo do jogo. Apenas as imagens do globo são assets próprios.

Os pontos da liga mantêm tamanho e opacidade fixos. O globo usa
`assets/globe/earth.dds` em 8192×4096, obtido da imagem NASA Blue Marble
21600×10800, com 14 níveis de mipmap e compressão BC1. O atlas independente
`atlas-hd.png`, também em 8192×4096, usa fronteiras Natural Earth 50m.
Ele armazena os IDs exatos dos países e um campo de distâncias, carregados
como RG8. O shader suaviza a seleção e ajusta a largura dos contornos ao
zoom, sem interpolar IDs. Derivadas periódicas evitam emendas no meridiano
180°. As duas texturas usam aproximadamente 85,4 MiB de memória gráfica.
As imagens PNG antigas de baixa resolução não são usadas pelo plugin atual.
Créditos, URLs e hashes das fontes ficam em `earth-credits.json`.
`build_globe_assets.py <fontes> <assets/globe>` reproduz os arquivos offline;
`globe_world_ids.json` preserva o vínculo com os IDs existentes em catalog.tsv.

Ao abrir “Ver titulares”, o processo auxiliar lê o save ativo sem modificá-lo,
obtém onze titulares distintos e exporta a pose de seis jogadores em pé e
cinco agachados. `native_assets.py` converte essa geometria para RX3 preservando
as coordenadas UV, normais e dimensões das texturas do FIFA. Os materiais
comuns usam os pixels comprimidos originais, sem recompressão nem atlas.
Apenas cores sólidas e máscaras/tintas de cabelo precisam de preparação.
As partes opacas e transparências têm materiais separados. O renderizador GameplayProp do
FIFA coloca o grupo no centro do gramado do estádio que já está carregado.
Esta visualização é estática; não inicia partida nem animações de jogadores.

As chamadas do FIFA e o empréstimo da câmera acontecem exclusivamente no
callback nativo de cena, encadeado após o vestiário. Present apenas comunica
pedidos e desenha a interface. A instalação verifica as assinaturas das
funções e a DLL dona do callback anterior. Nenhum estádio é recarregado.
Ao voltar, o grupo é ocultado e os campos da câmera são restaurados somente
se ainda contiverem os valores escritos por esta tela.

Cada troca de elenco recebe um objeto nativo com nome e aliases imutáveis,
com 96 slots (64 opacos, 32 alpha). Slots não utilizados recebem triângulos
degenerados. `AddAsset` do FIFA acrescenta descritores: reutilizar aliases no
mesmo objeto acumulava os recursos do clube anterior e podia causar crash.
O objeto anterior é ocultado e descarregado pela função nativa de Unload,
apenas no callback da engine e após terminar seu streaming. Só um conjunto
de recursos permanece residente. O registro leve do objeto permanece no
contexto do FIFA até encerrar a sessão; não se chama um destrutor sem remover
primeiro todas as referências da engine. Atualizar o mesmo elenco pronto
reutiliza seu objeto. Cada objeto recebe apenas um Reload e um registro na
cena; pedidos antigos não podem se apresentar como o clube recém-selecionado.
Recursos completos são publicados antes do pedido de carregamento. Os
titulares refletem o último salvamento da carreira ativa.

A preparação começa exclusivamente ao selecionar “Ver titulares” ou
“Atualizar”. Abrir o globo ou percorrer os seletores não lê o save nem gera
modelos dos titulares. Não há pré-carregamento no mapa. O auxiliar consulta
pedidos a cada 30 ms, e a interface recebe o resultado em até 50 ms.
Um único processo auxiliar persistente lê os modelos originais. O cache em
`ModCarrerMode/cache/club_browser/xi/prepared/<hash>/` é reaproveitado entre
sessões, com publicação atômica por hard links quando disponíveis. A chave
inclui elenco/aparências, versão do conversor, banco instalado e exportador.
As tabelas do save são preparadas somente no primeiro pedido de titulares.
Um cache de leitura retém um único save ativo e seus índices;
mudanças na identidade, tamanho ou data de gravação do save, banco ou esquema
invalidam esse cache. Materiais idênticos são reutilizados entre clubes em
`cache/club_browser/xi/materials/`, com chave baseada nos pixels, dimensões,
coeficientes, cor, transparência e template. A conversão de cor/alpha usa
tabelas de 256 valores e produz os mesmos arquivos da versão anterior.
Um material truncado é reconstruído antes de ser publicado para a engine.
Isso não é a fábrica de atores animados da carreira jogador: a visualização
usa poses estáticas e o renderizador nativo GameplayProp. Os objetos do jogador
original, a partida, o estádio e os saves não são alterados.

`character_lighting.py` gera, no primeiro pedido, cópias próprias dos cubemaps
ambientes do FIFA com RGB neutro para reduzir o reflexo verde do material
estático. Preserva luminância direcional, seis faces, todos os mipmaps e os
blocos de alpha BC3 originais. Os pixels das camisas, rostos e demais texturas
dos jogadores não passam por essa neutralização. Os arquivos originais do
FIFA permanecem intactos; as cópias ficam em `server16_club_xi/lighting/`.

Diagnósticos por sessão: `ModCarrerMode/runtime/club_browser/<pid>/` contém
`worker.log`, `export.log`, `status.tsv`, `roster.json`, `engine.log` e
`native_status.json`. Recursos gerados ficam exclusivamente em
`data/sceneassets/server16_club_xi/<pid>/<hash>/`.
`timings.json` separa leitura do save, obtenção dos modelos e preparação nativa.
O diagnóstico nativo inclui clube exibido, sequência, objetos criados e
conjuntos residentes para detectar trocas incompletas e recursos acumulados.

Testes: `test_native.cpp` usa D3D11 WARP, sem anexar ao FIFA, para verificar
estado gráfico, navegação, projeção, zoom, jobs e restauração da câmera.
`test_native_assets.py` compara vértices/UVs antes e depois da conversão,
verifica o layout de normais e a igualdade dos pixels comprimidos originais.
`test_scene_lua.py` valida o binding e recarregamento em Lua 5.1
(dependência de teste: lupa). `test_integration.py` verifica o APT e o hub.
Nenhuma dependência de teste é necessária no jogo.
`test_character_lighting.py` verifica os cubemaps reais, seus cabeçalhos,
registros de mip, alpha exato e cache, sem alterar os originais.
O carregamento e a câmera aceitam os estados de cena 1 e 13, com projeção
finita e proporção válida. O estado 13 foi conferido no estádio aberto no
FIFA; o antigo teste de igualdade com 1 deixava os recursos prontos sem
submetê-los à cena. `native_status.json` inclui estado, etapa de espera e
contador de quadros para distinguir leitura, espera da cena e streaming.
`test_loading_cache.py` usa saves e assets reais para comparar resultados,
testar invalidação por nova gravação e recuperar material truncado, sem
modificar o save. A primeira geração de um clube ainda exige a obtenção dos
modelos; os arquivos completos são reutilizados nas aberturas seguintes.
`test_globe_assets.py <data/club_browser>` verifica mipmaps, dimensões,
IDs geográficos e precisão do campo de distâncias. O teste WARP também
compara quadros separados no tempo para impedir regressão dos pontos fixos
e exporta imagens de zoom máximo, Europa e meridiano 180°.

### Correções de vestiário e auxiliares — 25/10/2026

O vestiário tinha os modelos prontos, mas sua câmera ignorava o estado 13 de um estádio carregado. Agora aceita os estados 1 e 13, mantendo a validação da projeção e a restauração da câmera. A recuperação foi confirmada pelo usuário na sessão aberta; modelos, texturas e os demais mods foram preservados.

O auxiliar dos titulares inicia com ambiente congelado independente e herda somente seus canais de entrada/saída. O Server grava a saída de cada auxiliar em `service.log`, evitando que um stdout inválido encerre a preparação. A tela detecta quando o auxiliar termina e permite tentar novamente. Erros do exportador preservam saída e código de encerramento.

O complemento de 36 assets continua o mesmo; esta revisão altera código, DLLs e Server16. A visualização dos titulares no PC do Robson ainda precisa de validação. Para comparar os computadores, use `ModCarrerMode/tools/Coletar-Diagnostico-Carreira.ps1`: ele gera um ZIP de logs e hashes, sem copiar saves, contratos SQL, modelos ou executáveis.
