# FIFA Friends — New Experience 3D

Abra **Ambientes3D.exe**. A ferramenta reúne sala de imprensa, vestiário, academia, CT de treinamento, jogador, técnico, foto da equipe, poses, câmeras, objetos e importação FBX. Não exige Python para executar. Requer Windows com Direct3D 11 e uma instalação funcional do FIFA 16.

## Organização

Este diretório, dentro da branch `fifa-friends-new-experience`, é a origem dos fontes, objetos procedurais, configurações, presets e exemplos de animação do visualizador. A pasta externa `J:\mods\fifa 16\ambientes 3d` contém o EXE de acesso e os atalhos; seus diretórios de fontes e presets estão vinculados a este projeto.

- `src/viewer_press_room.cpp`: sala de imprensa, objetos, cinco participantes e plateia.
- `src/viewer_dressing_room.cpp`: vestiário, armários, uniformes e objetos.
- `src/viewer_training_center.cpp`: academia e CT.
- `src/viewer_cinematics.cpp`: cenas e movimentos de câmera.
- `src/viewer_animation.cpp`, `viewer_pose_hooks.cpp`, `viewer_team.cpp`: animações, correções e atores.
- `../career_native/src/render/`: renderer, poses e carregador de modelos compartilhados com a New Experience. O build não usa os fontes da V12.
- `presets/`: cenas e alterações salvas em XML. `imports/`: exemplo de animação importada.
- `config/visualizador.xml`: escolha do jogo, clube, cena e câmera inicial.

As mesas, cadeiras, paredes, equipamentos e outros objetos próprios dos ambientes são construídos pelos fontes do projeto. Os personagens nativos, bolas e outros recursos reutilizados requerem malhas, esqueletos, texturas e bancos RX3/BIG do FIFA, lidos da pasta definida em `origem jogo` (atualmente `U:\fifa 16`). Copiar somente texturas não substitui essa dependência.

`new-experience.ini`, ao lado do EXE externo, aponta para este diretório. Quando o EXE é aberto diretamente neste diretório, utiliza os arquivos locais. Presets com caminhos FBX relativos são resolvidos a partir do projeto.

## Trabalhar e recompilar

Use a interface para ajustar poses, pessoas, objetos e câmeras, e salve os XML em `presets/`. Use **Abrir projeto New Experience** para localizar os arquivos. Alterações nos fontes C++ precisam de recompilação; ajustes de XML são reabertos pela ferramenta.

```powershell
.\scripts\build.ps1
```

O comando gera `Ambientes3D.exe` neste projeto. Para atualizar também o acesso externo:

```powershell
.\scripts\build.ps1 -OutputDirectory "J:\mods\fifa 16\ambientes 3d"
```

A compilação exige Visual Studio Build Tools C++ e Windows SDK. ufbx e ImGuizmo são incorporados, com as licenças em `third_party/`. O executável usa as bibliotecas de sistema do Windows. `build/`, capturas, logs e backups gerados são ignorados pelo Git.

## Relação com as telas do jogo

Este EXE é a ferramenta de criação e inspeção gerenciada pela New Experience. As cenas mais recentes do visualizador foram preservadas aqui. Salvar um XML ou editar seus objetos não instala uma cena nas telas do FIFA automaticamente; integrar uma alteração ao runtime da carreira exige adaptar os seus pontos de chamada e recompilar a DLL do mod. Academia/CT e a coletiva ampliada pertencem por enquanto à ferramenta. A instalação ativa do jogo continua sendo a V12.

As opções ANT/CBAC são um inventário de recursos; reprodução de animação nativa permanece em estudo. Os exemplos FBX e poses-chave oferecem o fluxo de edição descrito no guia de rigging.

[Manual completo da ferramenta anterior](MANUAL_EDITOR.md), [rigging](RIGGING.md) e [sala de imprensa](SALA-IMPRENSA.md).
