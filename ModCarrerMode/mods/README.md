# Módulos do FIFA Friends V12

O pacote usa 26 DLLs ativas, com uma DLL atual em cada pasta. `enabled.txt`
define os caminhos e a ordem de carregamento. `mod_host.dll` é o carregador
compartilhado e fica na raiz desta pasta.

| Pasta / DLL | Recurso | Configuração |
|---|---|---|
| [crowd/crowd_plugin.dll](crowd/crowd_plugin.dll) | Público do estádio | [crowd.ini](../crowd.ini) |
| [career_birthdate_2006/birthyear_range_2006_2012.dll](career_birthdate_2006/birthyear_range_2006_2012.dll) | Intervalo de nascimento do jogador | Payload na própria pasta |
| [substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll](substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll) | Até sete substituições | Regras nativas |
| [subson/subson_bridge.dll](subson/subson_bridge.dll) | Integração do banco com 12 reservas | [SubsOn.ini](../../SubsOn.ini), ao lado de [SubsOn.dll](../../SubsOn.dll) |
| [mascot_single/mascot_goal_line.dll](mascot_single/mascot_goal_line.dll) | Mascotes dos clubes | [match_presentation.ini](../config/match_presentation.ini) |
| [tournament_compat_native/tournament_compat_native.dll](tournament_compat_native/tournament_compat_native.dll) | Identidade das competições | Base de competições instalada |
| [career_ui_assets/career_ui_assets.dll](career_ui_assets/career_ui_assets.dll) | Ícones e assets da carreira | Catálogos e imagens do pacote |
| [kickoff_modern/kickoff_modern.dll](kickoff_modern/kickoff_modern.dll) | Saída de bola moderna | Comportamento nativo do módulo |
| [goal_kick_short_pass/goal_kick_short_pass.dll](goal_kick_short_pass/goal_kick_short_pass.dll) | Tiro de meta curto experimental | [goal_kick_short_pass.ini](goal_kick_short_pass/goal_kick_short_pass.ini) |
| [multiball_visual/multiball_visual.dll](multiball_visual/multiball_visual.dll) | Bolas de reposição e suportes | [standball.ini](multiball_visual/standball.ini) |
| [stadium_pyrotechnics/stadium_pyrotechnics.dll](stadium_pyrotechnics/stadium_pyrotechnics.dll) | Fogos, fumaça e confete; bloqueio durante a disputa de pênaltis | [pyro.ini](stadium_pyrotechnics/pyro.ini) e [match_presentation.ini](../config/match_presentation.ini) |
| [crowd_ultra_kits/crowd_ultra_kits.dll](crowd_ultra_kits/crowd_ultra_kits.dll) | Uniformes da torcida | [crowd_ultra_kits.ini](crowd_ultra_kits/crowd_ultra_kits.ini) |
| [entrance_props/entrance_props.dll](entrance_props/entrance_props.dll) | Objetos da apresentação | [entrance_props.ini](entrance_props/entrance_props.ini) |
| [var_cabin/var_cabin.dll](var_cabin/var_cabin.dll) | Cabine visual do VAR | [var_cabin.ini](var_cabin/var_cabin.ini) |
| [smoke_machine/smoke_machine.dll](smoke_machine/smoke_machine.dll) | Máquinas visuais de fumaça | [smoke_machine.ini](smoke_machine/smoke_machine.ini) |
| [cloth_motion/cloth_motion.dll](cloth_motion/cloth_motion.dll) | Física das roupas | [cloth_motion.ini](cloth_motion/cloth_motion.ini) |
| [frontend_stadium/frontend_stadium_native_v11.dll](frontend_stadium/frontend_stadium_native_v11.dll) | Estádio de fundo do menu e da carreira | [frontend_stadium.ini](../config/frontend_stadium.ini) |
| [panorama_drone/panorama_drone_v5.dll](panorama_drone/panorama_drone_v5.dll) | 39 tomadas da panorâmica | [panorama_drone.ini](../config/panorama_drone.ini) |
| [goal_news/goal_news.dll](goal_news/goal_news.dll) | Placares simultâneos no painel nativo; exibição confirmada localmente, sem trocar a narração | [goal_news.ini](../config/goal_news.ini) |

## Carregamento pelo host — 26/10/2026

- `server16_overlay/cgfs16_overlay.dll`: canal de progresso/controles do Server.
- `first_person/server16_first_person_v14.dll`: câmeras do Server, carregadas pelo host e ativadas conforme a opção do usuário.
- `career_jobs/career_jobs_runtime.dll`: contexto e propostas da carreira.

Esses três plugins entram em `enabled.txt`; o Server conecta os canais existentes.
O executável externo `cgfs16_inject.exe` foi retirado do pacote. Não substitua
somente o EXE sem atualizar esta lista e as DLLs. Vestiário nesta entrega usa APT R64.

## Ambiente do clube — 24/10/2026

- `club_environment/native_dressing_room.dll`: vestiário R62, cenas e retorno do fundo. Fontes/apoio em `source/club_environment`; modelos e poses no ZIP complementar.
- `club_browser/club_browser.dll`: globo, seletores e escolha entre 11 iniciais estáticos e elenco com jogador animado; render GameplayProp nativo, buffer dinâmico próprio com WRITE_DISCARD, filtros/detalhes, aliases imutáveis por seleção e sem pré-carregamento no mapa. A animação individual exige o delta de assets de 27/10/2026.
- `subson/subson_match_gate_v5.dll`: guarda adicional de elegibilidade da partida, preservando os 12 lugares máximos do banco.
- `dinput8.dll`, na raiz: serviços de contexto, atualização das telas, snapshot do mercado e e-mails, na thread da interface. Não distribua DLLs de revisão anteriores em paralelo.

## Organização e dependências

Os caminhos de execução e os nomes das DLLs permanecem fixos. O preparador do
estádio de fundo fica em `ModCarrerMode/tools/frontend_stadium_prepare.exe`.
Os fontes ficam em `ModCarrerMode/source/`, incluindo `source/native_mods/`
para estádio de fundo, panorâmica e cenas extras.

SubsOn mantém sua DLL e seu INI na raiz do jogo, onde o módulo os procura.
O [ZIP complementar](../docs/COMPLEMENTO_SUBSON.md) entrega o arquivo grande
`data/ant.cbac` e a compdata. As DLLs e configurações ficam nesta branch.

`entrance_props` precede `var_cabin` em `enabled.txt`; `frontend_stadium`
precede `panorama_drone`. Preserve a ordem da lista ao instalar.

As cenas extras de técnico e mascote usam `extra_scenes/extra_scenes.dll`:
cinco variações frontais, 40% por parada elegível, intervalo mínimo de 10 s e
continuidade nos fragmentos da sequência nativa. O Server16 0.2.18 oferece
controles separados dos dois personagens. A sala interna experimental do VAR
foi retirada; as anotações estão em `source/docs/VAR_ROOM_DEFERRED_20261025.md`.
A cabine do VAR na beira do campo continua disponível.

O seletor de narrador e seus avisos continuam ocultos.

Backups pertencem a `ModCarrerMode/backups/`, fora do Git. Arquivos de estado
gerados pelos módulos são locais; o instalador não os distribui. Atualizações
arquivam revisões antigas conhecidas e preservam módulos adicionais do usuário.

Antes de publicar, execute `ModCarrerMode/tools/maintenance/Verify-Package.ps1`.
O teste de instalação é `Test-Package.ps1 -SupplementalAssetDirectory "PASTA_DO_FIFA"`,
usando uma instalação com o complemento SubsOn para fornecer o asset à fixture.

## Revisão de clubes e competições — 28/10/2026

`club_browser/club_browser.dll` reúne mapa de clubes, onze titulares, elenco,
perfil do técnico e competições da carreira. O acesso ao elenco do clube também
existe no vestiário. Grupos e chaveamentos são definidos pelo CompData instalado;
notas e estatísticas vêm da publicação validada da carreira. A DLL de vestiário,
o overlay compartilhado e `dinput8.dll` acompanham a revisão. Consulte as
[notas da entrega](../docs/RELEASE_20261028.md) e os
[fontes e testes](../source/club_browser/README.md).
