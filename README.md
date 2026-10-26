# FIFA Friends V12

Mais vida na carreira, nos uniformes e na apresentação das partidas do FIFA 16.

O FIFA Friends V12 reúne melhorias para acompanhar seu clube, personalizar a experiência e dar mais identidade a cada competição. O [Server16](https://github.com/igor1043/CG-File-Server-16---Python-Port/tree/fifa-friends) é o painel que acompanha o projeto e permite escolher os recursos antes e durante a partida.

**Edição:** FIFA Friends V12 · **Atualizado em:** 25/10/2026

**Server16 incluído:** 0.2.16. As DLLs compiladas ficam nesta branch, organizadas em uma pasta por mod. O [índice dos módulos ativos](ModCarrerMode/mods/README.md) informa arquivos, funções e configurações.

A combinação Git + ZIP é agora verificada em uma pasta vazia, sem caches do desenvolvedor, incluindo igualdade entre o módulo embutido no EXE e o fonte publicado.

### Revisão local de áudio e texturas — 25/10/2026

O hino de gol usa a fase nativa da partida para distinguir comemoração/replay da volta ao jogo. O relógio lento da comemoração não encerra mais o áudio. Pausar preserva a posição; voltar ao jogo encerra o hino com fade. Torcida visitante vem ativa no INI de distribuição e nas configurações sem essa opção; um desligamento manual salvo continua sendo respeitado.

Os estádios recebem um conjunto de modelo e texturas identificado pelo conteúdo, com caminhos próprios para a engine. O conjunto e sua rota são publicados antes da troca do ID; a rota confere mandante e visitante e é limpa ao encerrar a partida. Pacotes sem texturas são recusados; um pacote que traz apenas dia ou noite usa essa textura nos dois horários. Os testes cobrem trocas consecutivas, iluminação, falha de publicação e restauração. A validação visual desta revisão entre duas partidas ainda está pendente. Os placares nativos permanecem iguais à versão confirmada.

### Revisão de estabilidade, empréstimos e placares — 25/10/2026

Também foi revisado o [carregamento de Próxima partida e Mercado](ModCarrerMode/source/docs/CAREER_VIEWS_20261025.md): espera por publicação da carreira atual, carrossel no analógico esquerdo, recuperação de escalações prováveis desatualizadas e eliminação do retorno indevido à cobertura de carregamento do Mercado. Próxima partida agora abre pela fila nativa de navegação, corrigindo o evento que o controlador do calendário ignorava; escalações, estádio, resultados e troca de páginas foram confirmados no FIFA aberto. Os cabeçalhos das escalações têm a largura do campo e ficam encostados nele. Testes da interface gerada e do consumidor nativo estão incluídos nos fontes.

O erro `failed to open archive file` ocorria antes do Python: o carregador não conseguia reabrir o próprio Server16 durante a extração. O carregador passa a repetir essa leitura por até cinco segundos. O pacote dispensa pip e caches de desenvolvimento da ponte x86, mantendo seus módulos de execução; os demais módulos embutidos foram preservados byte a byte. Aberturas isoladas e simultâneas, leitura da base pela ponte x86 e preparação dos titulares foram verificadas.

O auxiliar dos titulares inicia ao abrir a visualização e recupera até duas falhas de inicialização do carregador, preservando clube e pedido. Não prepara modelos no mapa. Saves, contratos, texturas e demais mods mantêm seus fluxos existentes.

As [notícias nativas de gols](ModCarrerMode/source/native_mods/goal_news/README.md) mostram placares dos jogos simulados em paralelo, sem filtro adicional por liga ou idioma da narração. A leitura respeita o relógio, aguarda o painel anterior e descarta repetições. A exibição em partida foi confirmada pelo usuário nesta revisão.

Empréstimos passam a usar a moeda escolhida no save e a formatação monetária do próprio FIFA, inclusive nos e-mails. Novas propostas têm uma chance simulada de recusa que varia por banco, exposição financeira e prazo. A decisão é fixada no pedido e guardada no SQLite; reabrir telas ou carregar o mesmo estado não sorteia novamente. Contratos e pedidos anteriores mantêm suas condições. [Testes, limites da cobertura e entrega](ModCarrerMode/docs/RELEASE_20261025.md).

### Correções de vestiário e auxiliares — 25/10/2026

O vestiário tinha os modelos prontos, mas sua câmera ignorava o estado 13 de um estádio carregado. Agora aceita os estados 1 e 13, mantendo a validação da projeção e a restauração da câmera. A recuperação foi confirmada pelo usuário na sessão aberta; modelos, texturas e os demais mods foram preservados.

O auxiliar dos titulares inicia com ambiente congelado independente e herda somente seus canais de entrada/saída. O Server grava a saída de cada auxiliar em `service.log`, evitando que um stdout inválido encerre a preparação. A tela detecta quando o auxiliar termina e permite tentar novamente. Erros do exportador preservam saída e código de encerramento.

O complemento de 36 assets continua o mesmo; esta revisão altera código, DLLs e Server16. A visualização dos titulares no PC do Robson ainda precisa de validação. Para comparar os computadores, use `ModCarrerMode/tools/Coletar-Diagnostico-Carreira.ps1`: ele gera um ZIP de logs e hashes, sem copiar saves, contratos SQL, modelos ou executáveis.

### Correção de primeira inicialização — 24/10/2026

Auxiliares iniciados diretamente por plugins agora preparam o runtime antes de executar sua entrada. Isso corrige `FileNotFoundError` em `ModCarrerMode/runtime/club_environment/preview/prepare.py` quando o supervisor ainda não iniciou ou a cópia gerada foi removida. A sincronização preserva contratos e dados da carreira.

Atualize o Server16Python.exe e a pasta ModCarrerMode/source pela branch FIFA Friends V12, com jogo e Server fechados. O ZIP complementar de assets continua o mesmo. Se também faltar `ModCarrerMode/source/club_environment/preview/prepare.py`, a atualização do código está incompleta: o ZIP de modelos não substitui os fontes do GitHub.

Teste da revisão: o executável congelado criou os runtimes ausentes e executou as entradas de vestiário, banco e próxima partida em três pastas novas com nomes Unicode, sem iniciar FIFA nem instalar drivers. Testes de recuperação verificam também a preservação do livro financeiro. Os demais módulos e recursos embutidos foram preservados.

## Atualização — 24/10/2026

- **Empréstimos:** tela nativa com bancos e logotipos, contratos individuais, tabela de parcelas e até dois contratos ativos. Datas da solicitação/resposta ficam fixas no SQLite por carreira e clube; parcelas vencidas são processadas mesmo ao pular dias. Pedido, decisão e lembretes usam e-mails da carreira. [Funcionamento e persistência](ModCarrerMode/source/club_environment/bank/README.md).
- **Próxima partida:** contexto e calendário atualizam os campinhos, escalações e adversário após avançar pela Central ou pelo calendário, sem reutilizar a partida anterior.
- **Vestiário:** revisão R62 com modelos e poses completos, ajuste de impressão dos kits, transição das cenas e preservação da visão 3D ao retornar. [Ambiente do clube](ModCarrerMode/source/club_environment/README.md).
- **Estádio e panorâmica:** respeitam o estádio definido para o clube e a preferência de fundo, com preparação fora da thread de desenho. [Revisão do cenário](ModCarrerMode/source/native_mods/frontend_stadium/README.md).
- **Mercado de Transferências:** novo item no carrossel Rede Mundial; dados ao vivo e carregamento automático, cinco abas e controles/legendas nativos. [Detalhes](ModCarrerMode/source/club_environment/market/README.md).
- **Ver clubes e onze titulares:** carrossel em Outras ligas, globo 8K com pontos fixos, imagens dos clubes lidas do FIFA e onze titulares em pose estática desenhados pela engine no estádio. Carregamento somente ao abrir Ver titulares; recursos isolados por seleção evitam misturar clubes. [Arquitetura e testes](ModCarrerMode/source/club_browser/README.md).
- **Server16 0.2.15:** compatibilidade ReShade API 17, controles genéricos opcionais e sincronização dos auxiliares. Executável atualizado incluído neste repositório; fontes canônicos na branch `fifa-friends` do [Server16](https://github.com/igor1043/CG-File-Server-16---Python-Port/tree/fifa-friends).

**Para atualizar:** com FIFA/Server fechados, copie esta branch e extraia **FIFA-Friends-Assets-Complementares-20261025.zip** diretamente na pasta do FIFA. O ZIP contém só assets fora do GitHub: os 33 arquivos estáticos do vestiário, duas texturas do globo e `data/ant.cbac`. Server16, DLLs, código e interfaces vêm desta branch. Não há instalador no ZIP. [Conteúdo e conferência](ModCarrerMode/docs/RELEASE_20261025.md).

## Atualização — 21/10/2026

- **Câmeras — revisão 14:** corrigido o arrasto dos cantos preservando a escala central, confirmado pelo usuário em RAM. A primeira pessoa busca a bola com mais suavidade e olha brevemente para os pés em condução. Sem posse, a terceira pessoa gira mais rápido. Os movimentos novos aguardam validação visual.

- **Diagnóstico por sessão:** logs ativos zerados antes de abrir pelo Server e arquivos separados por mod. O ZIP da tentativa reúne arquivos/DLLs, última tela e dados do dump quando disponível. Fica em `runtime/diagnostics/`. [Como coletar e interpretar](ModCarrerMode/docs/DIAGNOSTICO_INICIALIZACAO.md).
- **Câmeras — revisão 13:** lente da primeira pessoa mais leve e sem ampliação adicional, com nitidez confirmada em RAM; proteção da cabeça nas viradas rápidas. A terceira pessoa acompanha mais a bola sem a posse, preservando a órbita suave. Ajustes finais aguardam validação visual no jogo.

- **Câmeras — revisão 12:** acompanhamento nas cobranças e reinícios, correção da pose após a transição nativa e flags de desfoque desligadas nos quadros modificados. A terceira pessoa reduz oscilações e limita as viradas; no modo de um jogador, o vínculo do atleta permanece fixo. Testes isolados aprovados; usuário relatou melhora significativa. Casos específicos ainda aguardam validação.
- **Física de roupas:** começa desligada e mantém a escolha salva, inclusive ao atualizar a instalação.
- **Layouts do Server16:** corrigidas as sobreposições no painel da carreira e no rodapé da fumaça; textos respeitam o espaço dos atalhos, switches e botões. A busca de estádio usa teclado QWERTY com fileiras escalonadas e navegação por posição. São 117 testes aprovados e 52 estados renderizados; conferência visual dentro do FIFA pendente.
- **Ano de nascimento:** corrigida a prioridade da interface que removia o cadeado e listava 2006–2012. O instalador agora ativa essa tela no índice BH local, com backup, sem substituir o índice de outros mods. [Detalhes e reparo manual](ModCarrerMode/source/tools/birthyear_ui/README.md). Desbloqueio e lista confirmados pelo usuário.
- **Estádio de fundo:** pacote completo do módulo v11, preparador, scripts e interface nativa ajustada para o menu e a carreira. O recurso começa desligado; atualizações preservam as escolhas salvas. Os estádios continuam nos pacotes locais do usuário.
- **Panorâmica:** módulo v5, revisão de tomadas 6, com 39 cenas. A órbita alta leva cerca de 99 segundos, com rotação mais lenta e o tempo de parada preservado. Há uma nova órbita a 65 m para ver o perfil do estádio e uma travessia completa dos 68 m da linha central.
- **Pênaltis:** o Server mantém o placar durante a disputa, e a pirotecnia bloqueia os disparos nessa fase.
- **Próxima partida:** os nomes usam `teams.teamid` da carreira, mantendo a identidade dos clubes junto aos escudos, inclusive nos times adicionados pelo mod. O teste do publicador reproduz a troca por nomes de países no código antigo e passa com a correção; conferência visual após reiniciar o FIFA pendente.
- **Logo nos hubs:** troca da faixa online pela logo desativada para isolar o crash recorrente do Robson. A interface anterior foi restaurada; os arquivos modificados e seus fontes foram preservados.
- **Instalação:** as DLLs atuais entram no Git; versões antigas, caches e diagnósticos locais ficam fora da distribuição. SubsOn acompanha o pacote no lugar do banco antigo.
- **Cenas extras:** mod de técnicos e mascotes desativado e removido dos menus. Seu código permanece no desenvolvimento.
- **Narração:** seleção de narrador, aplicação automática, progresso e aviso de narração aplicada ocultos nesta versão. O código e os recursos embarcados permanecem disponíveis para uma futura ativação.
- **Complemento SubsOn:** `data/ant.cbac` acompanha um ZIP separado de 131 MB; o instalador verifica o arquivo já extraído no jogo. Veja as [instruções do complemento](ModCarrerMode/docs/COMPLEMENTO_SUBSON.md).

## Atualização — 19/10/2026

- **Carreira:** painel do Server16 para transferência de clube, proposta nativa de treinador, solicitação de verba e aposentadoria, com identificação automática da carreira aberta.
- **Ícones:** calendário e cards usam a mesma imagem por competição. Foram corrigidos os DDS e os BIGs necessários ao calendário; o teste no jogo confirmou os ícones após reiniciar.
- **Entradas e bolas:** prioridade da fase com herança da competição principal da base Robson 12.12 e tradução dos IDs de carreiras antigas. A exibição 3D ainda aguarda confirmação em partida.
- **Público e estádio:** pesos por competição na ocupação automática e suporte à foto nativa do estádio no card.
- **Técnico nativo:** ferramentas de conversão e reparo de braços, pesos e texturas para Eduardo Domingues/Atlético-MG. Os modelos ficam no pacote local; a estabilidade em partida continua pendente de teste.

Veja a [lista de arquivos e recursos publicados](ModCarrerMode/docs/ATUALIZACAO_2026-10-19.md).

## Aberturas — 18/10/2026

- **Base Robson 12.12:** o pacote da fase tem prioridade; uma fase sem pacote próprio herda o modelo da competição principal. A identidade de carreiras antigas é traduzida para a base instalada.

## Ícones por ID da competição — 18/10/2026

Calendário, card Próxima Partida da Central e cards de Competições compartilham
[uma pasta de ícones](data/ui/imgAssets/careerCompetitionIcons/README.md).
Use `<ID_DO_INI>.png`; o pacote já inclui as versões proporcionais para cada área.
Carreiras antigas são resolvidas pela identidade da competição, preservando o
mesmo logo em todos os meses. A DLL gera o BIG/APT e as texturas nativas de cada ícone ao iniciar.

### Atualização sobre a base do Robson

Com FIFA e Server fechados, copie os arquivos atualizados preservando os caminhos:

- `dinput8.dll` e os módulos `career_ui_assets`, `entrance_props` e `multiball_visual` em `ModCarrerMode/mods/`.
- A biblioteca `data/ui/imgAssets/careerCompetitionIcons/`, incluindo `calendar/`, `cards/` e `competitions.tsv`.
- Os BIGs e DDS de `data/ui/artAssets/cmCalendarCompetitions/`, `data/ui/imgAssets/cmCalendarCompetitions/` e os novos arquivos `l100*.dds` de `data/ui/imgAssets/league/light/` e `dark/` que acompanham a atualização.

Os BIGs do calendário são necessários; não os apague. A DLL os recria no próximo
início se faltarem. Para trocar a arte, edite `<ID_DO_INI>.png`, como `1761.png`
para a Série A e `1460.png` para a Libertadores nesta base. Confira os IDs aceitos
em `COMPETICOES.txt`. O Server prepara as texturas antes da próxima abertura do FIFA.

A atualização preserva os modelos de `entrance_props` e `standball` já instalados.
Após reiniciar, confira calendário, Central e cards de Competições; depois confira
a entrada e os suportes numa partida. Os ícones já tiveram confirmação visual
nesta instalação; entradas e suportes ainda aguardam essa confirmação.

## Câmeras do jogador — 18/10/2026

O Server16 incluído no pacote traz **Primeira pessoa** e **Terceira pessoa · carreira**.
No FIFA, escolha a câmera **Profissional**. Durante a partida, abra **Select + Start / F12 → Câmera**.
Ativação, modo e campo de visão ficam salvos. A primeira pessoa permite ajustar de 75° até 150°;
a terceira pessoa mantém a faixa de 60° a 90°. A abertura padrão é 85° nos dois modos, com suavização
Forte e enquadramento de campo e bola fixos. O acompanhamento inclui a espera para
reiniciar a jogada com a bola parada. Na terceira pessoa, Distância oferece Perto,
Intermediária e Afastada, com escolha salva e transição suave. O módulo da câmera está embutido no executável
do Server; o instalador do pacote distribui esse mesmo executável com os demais recursos.
O acompanhamento em terceira pessoa suaviza a translação e as viradas, com entrada
gradual dos movimentos e transição entre jogadores próximos.
A recuperação da câmera salva aguarda a inicialização nativa do FIFA antes de
consultar os ossos do jogador, evitando o crash durante a abertura do jogo.

## Destaques desta atualização — 17/10/2026

- **Base v12.11 com Honduras:** calendário e configuração sincronizados com o pacote oficial. Ícones e suportes reconhecem as identidades instaladas; as pastas de abertura foram alinhadas aos IDs atuais.

- **Camisas e calções com movimento:** física de roupas 0.8.2, com dobras, ajuste na barra do calção e controle pelo Server. Sua escolha fica salva. O recurso é experimental e começa desligado.
- **Goleiro com o uniforme correto:** corrigida a miniatura que aparecia branca no campo da aba Elenco e nas rotinas de escalação.
- **Ícones das competições corrigidos:** vínculos ajustados ao calendário instalado, evitando associações antigas entre competições e fases.
- **Novos ícones sem planilhas:** coloque uma imagem com o nome ou ID da competição; o Server atualizado prepara e cadastra o ícone automaticamente.
- **Bolas de reposição e suportes:** seleção por competição, identificação da liga em amistosos e suportes com tamanho reduzido.
- **Server com preferência de física salva e encerramento revisado:** mantém sua escolha e conclui a limpeza dos próprios recursos ao sair.
- **Tiro de meta em desenvolvimento:** posicionamento e passe curto ajustados em um módulo experimental.

## Melhorias disponíveis

### Acompanhe sua carreira

- **Próxima Partida:** adversário, competição, data, horário, estádio e estimativa de público, conforme os dados do jogo.
- **Meu Time:** jogadores, informações do clube, estatísticas, cartões e lesões.
- **Competição:** classificação, ligas, copas, fases e partidas.
- **Calendário com identidade:** ícones próprios para competições e pré-temporada, com importação automática de novas imagens pelo Server.
- **Gestão da carreira:** ferramentas de aposentadoria, idade e verba, seguindo as instruções exibidas no jogo.
- **Criação de jogador:** intervalo de nascimento adaptado para 2006–2012.
- **Compatibilidade de competições:** leitura das identidades e fases usadas pelos recursos da carreira.

### Mais identidade em campo

- **Física de roupas:** movimento de camisas e calções, com opção de ativar ou desativar antes e durante a partida.
- **Mascotes dos clubes:** caminhada, apoio e comemoração do mascote do mandante.
- **Abertura por competição:** arcos e placas do campeonato; em amistosos entre clubes da mesma liga, usa o conjunto dessa liga.
- **Escudos dinâmicos:** escudos dos clubes aplicados aos objetos da apresentação.
- **Bolas extras:** 13 bolas de reposição com o visual da bola da partida e suportes por competição.
- **Cabine do VAR:** objeto visual na beira do gramado nas Séries A e B do Brasileirão.
- **Pirotecnia:** fogos, fumaça e confete na abertura e nos gols do mandante, com cores do clube.
- **Máquinas de fumaça:** 20 equipamentos acompanham os efeitos do estádio.
- **Torcida:** uniformes dos clubes, estimativa de ocupação e ajuste de público pelo Server.

### Mais opções na partida

- **Banco com 12 reservas.**
- **Até sete substituições.**
- **Saída de bola moderna:** primeiro passe para trás e organização dos jogadores em volta do círculo central.
- **Tiro de meta moderno — experimental:** reposicionamento e passe rasteiro curto para zagueiros próximos; ainda precisa de avaliação em partida.

## Como começar

1. Use a instalação compatível do **FIFA 16 para Windows, 64 bits** e os pacotes de imagens, modelos e áudio desejados. Para o banco de 12 reservas, extraia primeiro o [complemento SubsOn](ModCarrerMode/docs/COMPLEMENTO_SUBSON.md): ele entrega `data/ant.cbac` e a compdata; DLLs e configuração acompanham esta branch.
2. Com os programas fechados, instale o pacote compilado: `ModCarrerMode/install-game.cmd -GameDirectory "C:\Seu FIFA 16" -UpdateCompetitionData`.
3. Abra o **Server16 atualizado** e depois o FIFA.
4. No pré-jogo, entre em **Configurações da partida**, escolha as opções e confirme em **Aplicar**. Durante a partida, use o painel de **F12**.

Para ativar o movimento das roupas, escolha **Física de roupas > Aplicar** no Server. A opção controla camisa e calção juntos e fica salva para as próximas aberturas. Depois de atualizar o executável ou os módulos, reinicie o Server e o FIFA.

## Colocar outro ícone ficou simples

1. Com o FIFA fechado, coloque um **PNG ou JPG** em `data/ui/imgAssets/careerCompetitionIcons/`, dentro da pasta do jogo.
2. Use o nome ou ID da competição. Nesta edição, por exemplo: **`1761.png`** para a Série A. O arquivo **`COMPETICOES.txt`**, criado pelo Server nessa pasta, lista os nomes aceitos.
3. Abra o Server atualizado, aguarde alguns segundos e inicie o FIFA.

O Server cuida do tamanho, do formato e do cadastro. **Não é preciso editar o index.tsv nem converter a imagem manualmente.** Para trocar um logo, substitua a imagem original. Prefira PNG com fundo transparente e mantenha apenas uma imagem por competição.

Para instalar apenas os mods mantendo sua base atual, omita `-UpdateCompetitionData`. Essa opção instala a base oficial completa e guarda backup do DLC, settings.ini, banco e traduções substituídos. Consulte o [guia da base de competições](ModCarrerMode/docs/COMPDATA.md).

## Pacotes e disponibilidade

Os recursos visuais dependem dos respectivos modelos, texturas e imagens instalados. Mascotes, objetos de abertura, cabine do VAR, suportes das bolas e ícones são distribuídos em pacotes locais separados do código. Narração, músicas e vídeos também usam bibliotecas próprias. Sem um pacote visual válido, o objeto correspondente não aparece.

A cabine do VAR é visual: não altera decisões de arbitragem. As bolas de reposição e seus suportes são elementos de cenário. A física de roupas e o tiro de meta moderno são experimentais; aparência e desempenho podem variar conforme a instalação.

## Para quem desenvolve ou monta o pacote

- [Guia técnico, instalação e estrutura dos arquivos](ModCarrerMode/docs/GUIA_TECNICO.md).
- [Índice dos módulos ativos e suas configurações](ModCarrerMode/mods/README.md).
- [Catálogo completo das implementações](ModCarrerMode/docs/implementations.json).
- [Detalhes da física de roupas](ModCarrerMode/source/cloth_motion/README.md).
- [Server16: configuração, áudio e personalização](https://github.com/igor1043/CG-File-Server-16---Python-Port/tree/fifa-friends).

A edição **New Experience** tem sua [própria branch](https://github.com/igor1043/fifa-mods/tree/fifa-friends-new-experience).

## Atualização de 25/10/2026

Server16 0.2.18: cenas nativas de técnico e mascote, cinco ângulos frontais,
40% de chance por parada elegível e intervalo mínimo de 10 segundos. A tomada
mantém o personagem nos fragmentos compatíveis da sequência e libera a câmera
na retomada nativa. Cada personagem pode ser desligado nas Cenas extras.

Também inclui revisão do hino/replay, torcida visitante ativa por padrão e
isolamento das texturas de estádios entre partidas. O complemento de assets
agora reúne vestiário, globo, SubsOn, mascotes e objetos de apresentação.

- [Changelog completo e instalação para o Robson](ModCarrerMode/docs/RELEASE_20261025.md).
- [Cenas extras: funcionamento e testes](ModCarrerMode/source/native_mods/extra_scenes/README.md).
- [Sala interna do VAR adiada: anotações para retomada](ModCarrerMode/source/docs/VAR_ROOM_DEFERRED_20261025.md).
