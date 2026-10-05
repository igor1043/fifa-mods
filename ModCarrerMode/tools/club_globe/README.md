# Outros clubes — globo / Nova Experiência

Prévia local para explorar os clubes da carreira num globo escuro. A tela abre com o clube ativo do save-base e apresenta seletores empilhados de país, liga/divisão e clube. Países, ligas e clubes usam os nomes localizados pelo próprio FIFA 16 instalado. A amostra configurada é o save `159706fc`, com Cruzeiro como clube ativo.

A base gerada contém **1.535 clubes, 94 ligas e 41 países/regiões**. As regiões brasileiras do banco do FIFA aparecem agrupadas sob Brasil, preservando suas ligas estaduais. Na navegação brasileira, a ordem começa por Série A, B, C, os níveis da Série D e Divisão de Acesso; depois vêm as federações estaduais. O gerador lê o save para selecionar os clubes da carreira e o clube ativo; não modifica o save. Se o slot não estiver disponível, usa o banco instalado do FIFA.

## Abrir e atualizar

Duplo clique em **Abrir.cmd** ou em **Abrir Globo de Clubes.cmd** na pasta da Nova Experiência. A prévia funciona sem internet e sem iniciar o FIFA. A pasta contém os escudos, bandeiras, emblemas de liga, fontes, geometria do mapa e catálogo.

Execute **Atualizar.cmd** para regenerar a tela. O gerador usa a instalação e o save-base indicados em `clubes.ini`.

## Localizações e dados dos clubes

`club_city_overrides.json` contém os municípios revisados por clube. As coordenadas usam [GeoNames cities15000](https://download.geonames.org/export/dump/), em WGS84, sob [CC BY 4.0](https://download.geonames.org/export/dump/readme.txt). Quando uma cidade não aparece nesse conjunto, algumas posições pontuais usam coordenadas de fontes municipais ou do próprio clube.

As 27 ligas estaduais brasileiras são associadas à sua UF. Isso impede que pontos genéricos ou inválidos do banco do FIFA coloquem clubes dessas federações em outros países ou estados. Quando não consegui confirmar o município, o ponto fica numa região aproximada da capital do estado; essa indicação não aparece no card. A liga do Distrito Federal também inclui Formosa e Luziânia, em Goiás, tratadas como exceções com cidades próprias. Exemplos conferidos em fontes oficiais: [clubes da Federação Acreana](https://www.ffac.com.br/equipes), [Independente-AP](https://independenteap.com.br/), [Federação Amapaense](https://fafamapa.com.br/), [Caravaggio FC](https://caravaggiofc.com.br/clube/), [Federação Goiana — Centro Oeste SAF](https://www.fgf.esp.br/pt/clubes/view.php?q=305), [Federação Cearense — Cariri FC](https://www.futebolcearense.com.br/2010/downloads/arquivos/arquivo_7549.pdf) e [Prefeitura de Castelo](https://castelo.es.gov.br/castelo).

O card mostra a cidade quando foi identificada, a reputação em estrelas (reputação doméstica do FIFA convertida para cinco estrelas) e ATA/MEI/DEF, vindos dos atributos do time no banco FIFA. Os marcadores apontam para a cidade ou região do clube, não para o estádio.

## Controles

- Teclado: setas para foco e seleção, Enter para confirmar, Esc para voltar ao save, R para centralizar no clube mantendo o zoom, `+`/`−` para aproximar e afastar.
- Controle: analógico esquerdo ou direcional para navegar como as setas do teclado; analógico direito para girar (sensibilidade aumentada, eixo vertical invertido), A para confirmar, B para voltar ao save, Y para recentralizar sem alterar o zoom, R1 para um passo rápido de aproximação, R2 para aproximar continuamente e L2 para afastar. A barra inferior usa indicadores circulares e minimalistas, com as letras ou os símbolos do controle reconhecido.
- A composição ocupa um único viewport sem rolagem; cabeçalho, painel do clube e legenda se compactam em janelas mais baixas.
- A roda do mouse e o arrasto também controlam o globo. O zoom manual vai até **10×**. Ao trocar país ou liga, o enquadramento volta ao centro e zoom próprios da seleção; ao trocar de clube, mantém o zoom. O componente inferior de atalhos é reutilizável em `control_hints.js`.

A tela usa Barlow Condensed e Manrope, as fontes identificadas no site [FC Mania Database](https://patchfcm.fcmania.com.br/#/ligas), com cópias locais e licenças OFL em `fonts/`. O globo usa [Natural Earth countries-110m](https://esm.sh/@d3-maps/atlas@1.0.0/world/countries/countries-110m) e D3 7.9.0, incluído em `vendor/d3.min.js` sob licença ISC.

## Arquivos editáveis

- `template.html`: tema, colunas, card do clube e controles.
- `app.js`: carrosséis, foco, gamepad, zoom e movimento do globo.
- `control_hints.js`: componente reutilizável de atalhos para teclado e controle.
- `clubes.ini`: caminho do jogo, save-base e enquadramentos personalizados.
- `club_city_overrides.json`: nomes de cidades revisadas por clube.
- `build_preview.py`: montagem da página e conversão de recursos do jogo.
- `fifa_db.py`: leitura das tabelas do jogo e do save.

## Apresentação e central da carreira

Abra `Abrir Nova Experiencia.cmd` na raiz da edição para navegar com o FIFA fechado. `home.html` tem a apresentação, o escudo da carreira e os onze titulares. **Começar** abre `central.html`, com Início, Ligas, Times, Jogadores e Transferências. A central inclui os destaques, técnico, carrossel de notícias e acesso à coletiva, vestiário, academia e CT. As operações de transferência continuam exigindo o jogo aberto.

`Atualizar.cmd` lê o save configurado em `clubes.ini`, atualiza `preview-data.js` e gera as imagens com Direct3D, sem alterar o save. A leitura offline reflete o último save em disco. As imagens de ambientes e elenco são enquadramentos estáticos; não há rotação na tela. Para atualizar o save-base, altere `sample_save_slot` e execute novamente.

As cenas e modelos dinâmicos ficam em cache separado pelo hash do save. Ao trocar de carreira, os arquivos da revisão anterior são removidos; os caches sem uso expiram após sete dias. O botão **Limpar cache 3D temporário** remove esses arquivos manualmente. Caches e fichas JSON geradas por carreira ficam fora do Git e são recriados quando necessário.

Dentro do FIFA, o card **Meu escritório** abre a mesma interface por WebView2. Nome do clube, jogadores e notícias recebem o contexto da carreira aberta. As cenas são construídas pelo renderer nativo e enviadas à interface. O construtor compartilhado `new_experience_rooms.cpp` utiliza as cenas mais recentes de `source/ambientes3d`, também usadas na prévia offline. Os recursos do FIFA são lidos da instalação configurada.

Mouse: cursor desenhado na camada HTML quando aberta no FIFA, foco ao passar pelos seletores/cards e clique para abrir. No navegador, o cursor do sistema funciona normalmente. Teclado: setas, Enter, Esc e Q/E para abas. Controle: analógico esquerdo/direcional navega, A confirma, B volta, LB/RB (L1/R1) troca abas. No globo, analógico direito gira e LT/RT (L2/R2) controla o zoom; na ficha do clube, analógico direito rola. A barra inferior usa `control_hints.js`, com indicadores circulares reutilizáveis.

Arquivos compartilhados da apresentação e central: `experience.css`, `experience.js` e `pointer_cursor.js`. Instale a edição pelo `ModCarrerMode/install-game.cmd` após compilar a DLL e fechar o FIFA.

## Perfil de jogador

O clique no jogador da central ou da aba Jogadores abre `player.html`. O perfil usa a mesma identidade visual, informações físicas, posição, camisa, potencial e atributos do save. Na prévia, os modelos individuais são exportados pelo renderizador nativo; dentro do FIFA, o modelo do jogador selecionado vem do contexto da carreira. B/Esc retorna à aba de origem e o analógico direito rola os atributos. `player_profile.js` mantém a composição reutilizável.
