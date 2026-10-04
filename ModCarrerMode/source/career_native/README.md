# Código nativo do modo carreira

## Estrutura

```text
career_native/
├── src/
│   ├── core/                 dados, contratos e leitura da carreira
│   ├── host/                 DLL, hooks, cards nativos e save ativo
│   ├── platform/             entrada, overlays e resolução de caminhos
│   ├── features/             regras de torcida, empréstimos e aposentadoria
│   ├── catalogs/             listas geradas de clubes, nomes e uniformes
│   ├── screens/              telas, separadas por assunto
│   ├── ui/common/            componentes visuais compartilhados
│   ├── render/               modelos, poses, cenas e renderização 3D
│   └── experimental/         experiências desativadas, fora da DLL final
├── workers/                  processos auxiliares de operações e aposentadoria
├── resources/                dados binários incorporados à DLL
├── scripts/
│   ├── build/                compilação
│   ├── tests/                execução dos testes
│   └── previews/             geração de prévias e galerias
├── tests/                    código dos testes por assunto
├── tools/                    geradores de catálogos e prévias
├── third_party/              ImGui e miniz; bibliotecas externas incorporadas
└── build/                    SOMENTE resultados gerados
    ├── production/           objetos e DLL de produção
    ├── workers/              compilação isolada de cada worker
    ├── tests/                um diretório por teste
    ├── previews/             prévias atuais e histórico
    └── legacy/               resultados antigos, preservados
```

## Mapa das telas

Os caminhos abaixo são relativos a `src/`. Os arquivos `*_provider.inc` fornecem dados reais da carreira às telas; não são layouts independentes.

| O que você quer alterar | Onde procurar |
|---|---|
| Meu clube, elenco e integração das cenas do escritório | `screens/club/club_player_screen.cpp` |
| Cabeçalho, menus e cards de Meu escritório | `screens/office/my_office_view.inc` |
| Perfil de jogador | `screens/player/player_profile_view.h` e integração em `screens/club/` |
| Pesquisa de jogadores | `screens/player/player_search_screen.cpp` |
| Perfil de técnico | `screens/coach/coach_profile_screen.cpp` |
| Ver outros clubes | `screens/clubs/clubs_browser.cpp` |
| Ver outras ligas | `screens/leagues/leagues_browser.cpp` |
| Liga, grupos e chaveamento de copas | `screens/competitions/club_competitions_screen.cpp` |
| Próxima partida | `screens/next_match/next_match_screen.cpp` |
| Ranking mundial | `screens/ranking/ranking_overlay.cpp` |
| Empréstimos e lista de aposentadoria | `screens/operations/career_operations.cpp` |
| Dados dos aposentandos e abertura do perfil | `screens/retirement/retirement_screen_provider.inc` |
| Patrocinadores | `screens/sponsors/sponsor_screen.cpp` |
| Sala de troféus | `screens/trophies/trophy_room_screen.cpp` |
| Transferências | `screens/transfers/transfer_center_screen.cpp` |
| Campinho, imagens, estrelas e estilo compartilhado | `ui/common/` |
| Navegação do controle, mouse e teclado | `platform/input/` e `platform/overlay/` |
| Cards originais do FIFA e redirecionamentos | `host/native_cards.inc` |

Algumas telas ainda compartilham a integração de `club_player_screen.cpp` e `career_operations.cpp`. A reorganização preserva essa divisão interna para não mudar o comportamento; seus componentes e provedores agora ficam identificados por pasta.

## Modelos, poses e cenas 3D

| Parte | Arquivo |
|---|---|
| Buscar rosto, uniforme, técnico do clube e modelos | `render/assets/fifa_player_assets.cpp` |
| Lista de poses e ajustes de braços, cotovelos e mãos | `render/poses/fifa_player_pose.cpp` |
| Estruturas e identificadores públicos das poses | `render/assets/fifa_player_assets.h` |
| Sala de coletiva, vestiário, foto dos 11 e cena do escritório | `render/scenes/fifa_club_room.cpp` |
| Câmera, iluminação, zoom e desenho 3D | `render/renderer/fifa_player_renderer.cpp` |
| Fotos/cache de estádio já usados pelo menu | `render/stadium_thumbnails/stadium_preview.cpp` |

Os IDs das poses foram mantidos: poses de grupo começam em `1`; individuais em `101`; técnico em pé a partir de `201`; técnico sentado inclui `205` e `206`; chegada à coletiva é `207`. O catálogo completo está no início de `fifa_player_pose.cpp`.

**A visualização livre 3D do estádio continua desativada.** Seu código foi preservado em `experimental/stadium_3d/`, mas não entra no build de produção.

## Regras e processos auxiliares

- `features/finance/`: cálculo das parcelas, juros e total do empréstimo.
- `features/operations/`: solicitações, contratos, diário de recuperação e operações sobre cópias/arquivos de carreira.
- `features/retirement/`: regras da aposentadoria e operação auxiliar após salvar.
- `features/crowd/`: público, reputação e regras de torcida.
- `features/ranking/`: cálculo e catálogo do ranking mundial.
- `workers/`: executáveis auxiliares. Não executá-los contra saves reais para fazer testes.

## Comandos

```bat
build.cmd
test.cmd
test.cmd test_club_player_screen
test.cmd test_coach_profile_screen "U:\fifa 16" "."
```

`build.cmd` compila a DLL e os dois workers somente no Dev. É necessário ter o Visual Studio Build Tools já usado por este projeto. Não há dependências novas para executar o jogo.

`test.cmd` sem argumentos executa a regressão de lógica, provedores e controle e compila o utilitário legado de teste de aposentadoria. Testes visuais e de operações sobre save devem ser chamados explicitamente. `test_career_operations_io` aceita somente fixtures isoladas em `J:\mods\backup\CareerOps-Test-*`, nunca o save original.

Cada teste usa seu próprio diretório de compilação e pode sobrescrever seus objetos locais sem contaminar os objetos da DLL. Os scripts de prévias estão em `scripts/previews/`; o atalho `preview.cmd` recebe o nome do script e seus argumentos.

Os testes visuais precisam dos arquivos originais do FIFA (BIG/RX3 e texturas) na pasta indicada. Eles não recriam nem instalam esses arquivos. O diretório `.` do exemplo é a pasta isolada daquele teste em `build/tests/`.

## O que pode e o que não pode ser removido

- `build/`: resultados regeneráveis e histórico, não são necessários no jogo.
- `resources/active_chain_resource.bin`: **obrigatório para compilar a DLL**, não é arquivo temporário.
- `third_party/`: obrigatório para compilar, não mover isoladamente.
- `src/catalogs/`: código gerado usado no build, não é banco de save.
- `ModCarrerMode/runtime/operations/`: contratos e solicitações privadas, não apagar.
- Os bancos em `data/loc/` da raiz do Dev são importantes e foram mantidos.

O mapa completo dos caminhos antigos e novos está em `../../docs/source-migration-20261003.json`.
