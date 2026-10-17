# FIFA Friends V12

Mods para melhorar a carreira e a apresentação das partidas no FIFA 16. Este projeto reúne os módulos nativos; o [Server16 Python](https://github.com/igor1043/CG-File-Server-16---Python-Port/tree/fifa-friends) fornece o painel de configuração, áudio e seleção de estádio.

## O que foi implementado

| Implementação | O que muda no jogo |
|---|---|
| **Próxima Partida** | Adversário, competição, data, horário, estádio e público estimado quando disponíveis. |
| **Meu Time** | Informações do clube, jogadores, líderes de estatísticas, cartões e lesões. |
| **Competição** | Classificação e informações de ligas, copas, fases e partidas. |
| **Física de roupas** | Movimento e dobras de camisas e calções. Revisão 0.8.2: desativada por padrão, escolha salva no CF16 antes e durante a partida e barra do calção até 3 mm mais alta. |
| **Cabine do VAR** | Cabine na beira do gramado nas Séries A e B do Brasileirão. |
| **Mascotes** | Mascote do mandante com caminhada, apoio e comemoração. |
| **Bolas na beira do gramado** | 13 bolas de reposição com a malha e textura da bola da partida e suportes 3D por competição: Série A, CBF para B/C/D, Paulista e dois genéricos. |
| **Objetos de abertura por competição** | Escolhe arco e placas pelo campeonato. Em amistosos, usa a liga quando os dois clubes pertencem a ela. Retira modelo e escudos juntos ao fim das escalações ou da apresentação avançada. |
| **Escudos dinâmicos** | Aplica os escudos dos clubes de cada partida com recorte do fundo transparente. |
| **Pirotecnia** | Fogos, fumaça e confete na abertura e nos gols do mandante, com as cores do clube. |
| **Máquinas de fumaça** | Adiciona 20 equipamentos físicos; disparos e cores continuam sob controle da pirotecnia. |
| **Torcida e público** | Estima a ocupação na carreira e permite ajustar o público pelo Server16. |
| **Uniformes da torcida** | Usa os uniformes disponíveis para os clubes da partida. |
| **Banco com 12 reservas** | Acrescenta os jogadores do banco e libera o atleta ao entrar em campo. |
| **Sete substituições** | Permite até sete trocas. |
| **Saída de bola moderna** | Organiza o primeiro passe para trás, receptor e jogadores fora do círculo central. |
| **Tiro de meta moderno** | Experimental: reposiciona a formação do tiro de meta e suaviza passes rasteiros curtos para zagueiros próximos. Mantém a saída de bola v20; não muda quando a bola passa a estar em jogo. |
| **Ícones da carreira** | Resolve os ícones de competições e pré-temporada. O Server16 atualizado importa PNG/JPG pelo nome ou ID da competição, converte e cadastra automaticamente, sem editar tabelas. |
| **Aposentadoria e verba** | Remoção da aposentadoria, ajuste de idade e acréscimos de verba. |
| **Criação de jogador** | Adapta o intervalo de nascimento para 2006–2012. |
| **Compatibilidade de competições** | Mantém a leitura das competições usadas pelos módulos da carreira. |

O [catálogo das implementações](implementations.json) relaciona cada recurso com seus fontes, configuração e limitações.

## Como usar

1. Use o FIFA 16 x64 compatível com os módulos e instale os assets locais desejados.
2. Instale o pacote compilado com `ModCarrerMode/install-game.cmd -GameDirectory "C:\Seu FIFA 16"`.
3. Abra o Server16 e o FIFA. No pré-jogo, use **Configurações da partida** para ligar ou desligar mascotes, pirotecnia e objetos de abertura. Os objetos de abertura começam em **Sim**.
4. Para trocar uma DLL ou a lista de mods, feche e abra o FIFA. Reiniciar só a partida mantém a DLL antiga carregada.

O instalador preserva configurações e arquivos pessoais. `-ReplaceConfiguration` aplica os padrões do pacote. `-VerifyOnly` confere sem instalar.

Para usar os mods diretamente deste desenvolvimento com um DB/DLC externo, execute `ModCarrerMode/tools/maintenance/Connect-Development.ps1 -DatabasePackage "C:\Pasta do DB e DLC" -GameDirectory "U:\fifa 16"`. O comando conecta `ModCarrerMode/mods` ao desenvolvimento e `data/db`, `data/loc` e `dlc` ao pacote escolhido. Inclui os extras de uniformes, bandeiras, escudos e retratos, preserva as configurações existentes, os mascotes, as animações e os objetos 3D, e guarda os originais em backup. Use `-VerifyOnly` para conferir o plano. Mantenha as duas pastas de origem disponíveis; reinicie o FIFA depois de recompilar uma DLL. O instalador reconhece essas conexões e preserva o DB/DLC externo nas atualizações de mods.

## Código e assets

Os fontes ficam em `ModCarrerMode/source/<mod>/`. A pasta `ModCarrerMode/mods/` contém os arquivos usados na execução e uma DLL atual por módulo. Os objetos de abertura usam `entrance_props.dll`; a cabine usa `var_cabin.dll`. As revisões internas continuam identificadas nos logs.

O pacote compilado desta branch inclui os efeitos de pirotecnia e o modelo e as texturas da máquina de fumaça. Modelos e texturas dos suportes das bolas, da cabine do VAR, mascotes e conjuntos de placas de abertura, além de áudio, vídeos, caches e backups, continuam locais. Os RX3 dos suportes permanecem instalados no jogo e são excluídos do Git. O ZIP somente de fontes não é um instalador completo.

| Recurso local | Pasta na instalação do FIFA |
|---|---|
| Mascotes | `data/sceneassets/mascot/<ID_DO_CLUBE>/` |
| Objetos de abertura | `data/sceneassets/entrance_props/competitions/<ID_DA_COMPETICAO>/` |
| Cabine do VAR — assets locais, fora do pacote | `data/sceneassets/var_cabin/` |
| Suportes das bolas de reposição — assets locais, fora do Git | `data/sceneassets/standball/<variação>/` |
| Ícones da carreira | `data/ui/imgAssets/careerCompetitionIcons/` |

Uma competição sem modelo de abertura fica sem esses objetos e a partida continua. Um mascote sem pacote válido não é exibido. Sem os assets locais da cabine, o instalador desabilita apenas o VAR na lista do destino e instala os demais mods, incluindo os fogos e a máquina de fumaça. Com os assets já instalados, preserva-os e habilita a cabine; instalar os assets e repetir a instalação também habilita o módulo. A cabine é visual, sem decisões de arbitragem. As bolas extras e seus suportes não têm física. Os cinco suportes foram convertidos dos FBX fornecidos em STANDBALL; `ModCarrerMode/mods/multiball_visual/standball.ini` seleciona-os pelos IDs da competição/fase e permite alternar ou fixar os genéricos. Sem suporte pronto, as mesmas 13 bolas permanecem no gramado.

## Fontes e conferência

- [Objetos de abertura](../source/entrance_props/README.md)
- [Cabine do VAR](../source/var_cabin/README.md)
- [Mascotes](../source/mascot_photographer/README.md)
- [Bolas de reposição](../source/multiball_visual/README.md)
- [Pirotecnia](../source/stadium_pyrotechnics/README.md)
- [Máquinas de fumaça](../mods/smoke_machine/README.txt)
- [Física de roupas](../source/cloth_motion/README.md)
- [Tiro de meta moderno](../source/goal_kick_short_pass/README.md)
- [Ícones da carreira](../source/career_ui_assets/README.md)

Para compilar, use MSVC x64 e execute o build do módulo. Copie a saída para a DLL correspondente em `ModCarrerMode/mods/`. `Verify-Package.ps1` confere o pacote compilado; `Test-Package.ps1` testa a instalação isolada, sem abrir FIFA nem usar saves. `Review-Code.py` confere os fontes. `Export-Code.py` cria um ZIP somente com código, configuração e documentação. Os scripts ficam em `ModCarrerMode/tools/maintenance/`.

O ZIP de fontes precisa ser compilado e não é um instalador completo. O [Server16](https://github.com/igor1043/CG-File-Server-16---Python-Port/tree/fifa-friends) também precisa de suas bibliotecas nativas para gerar o executável.

A **New Experience** é uma edição separada, na [outra branch](https://github.com/igor1043/fifa-mods/tree/fifa-friends-new-experience).
