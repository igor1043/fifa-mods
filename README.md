# FIFA Friends V12

Melhorias para o FIFA 16 com navegação pelos cards e abas do próprio jogo. Esta edição reúne os ajustes compartilhados de carreira, torcida, banco e substituições, com a aposentadoria pelo fluxo nativo de dois cards.

## O que muda nesta versão

A aba **Meu Time** reúne os principais dados do clube e dos jogadores na interface do FIFA. O card **Clube** é informativo, sem clique para abrir perfil de jogador, técnico ou elenco 3D. Na Central, **Próxima partida** permanece como card informativo. O carrossel extra de **Meu escritório** pertence à New Experience.

A aposentadoria volta aos dois cards em **Escritório > Configurações**: **Remover aposentadoria** e **Remover aposentadoria e redefinir idade**. O primeiro limpa a marca de aposentadoria dos jogadores sinalizados; o segundo também ajusta a idade desses jogadores para o valor configurado (18 anos por padrão), preservando mês e dia. Esse fluxo não oferece seleção individual ou por clube.

Ao clicar, o fluxo faz autosave e exibe a orientação para fechar o FIFA completamente. Aguarde o worker terminar antes de abrir o jogo e carregar a carreira novamente. A operação faz backup e valida os CRCs do save.

## Melhorias compartilhadas

- **Meu Time:** artilheiros, assistências, jogadores mais bem avaliados, minutos, cartões, lesões e resumo do elenco. O card Clube reúne escudo, uniformes, desempenho, estádio, capacidade e prestígio.
- **Competição:** separação das informações de Liga e Copa, classificação, fases e partidas da carreira. Dados não disponíveis são indicados sem inventar números.
- **Próxima partida:** adversário, competição, data, horário, estádio, imagem e público estimado, conforme os dados disponíveis da carreira e da instalação.
- **Torcida:** cálculo automático de ocupação considerando reputação dos clubes, adversário, desempenho, competição, rivalidade e importância do jogo. A capacidade do estádio é exibida separadamente do percentual estimado.
- **Banco de reservas:** plugin nativo para preparar até 12 reservas reais. O tamanho do banco e a quantidade de trocas são ajustes distintos.
- **Substituições:** plugin nativo para o limite de sete substituições por partida.
- **Player Career:** faixa de nascimento 2006–2012, com interface, DLL e watcher para persistência da data no save.
- **Idiomas e base nativa:** seleção de idioma começando pelo Brasil, traduções de carreira e integração L9.65/CompData Patcher.

## Servidor Python / CR16

O `Server16Python.exe` acompanha as duas edições. Ele mantém os ajustes de escolha de estádio, público ao iniciar e volume da torcida. Os estádios disponíveis dependem do conteúdo instalado no FIFA/FSW/StadiumGBD; o pacote não contém os arquivos completos do jogo ou todos os estádios.

O ajuste manual do servidor e a estimativa automática do mod são controles diferentes. O mod usa `ModCarrerMode/crowd.ini`; `automatic_dynamic_controller=1` mantém o cálculo automático. Para usar um percentual manual, desative esse controlador e configure o modo manual adequado à sua instalação.

## Instalação

Use uma instalação funcional do FIFA 16 com os assets de base. Feche o FIFA e o servidor antes de substituir executáveis. Na pasta deste pacote, execute:

```powershell
.\ModCarrerMode\install-game.cmd -GameDirectory "U:\fifa 16"
```

O instalador instala esta edição, incluindo `Server16Python.exe`, plugins e payload de nascimento. Faz backup externo dos arquivos substituídos e arquiva componentes exclusivos da New Experience quando instala a V12. Preserva saves, contratos e configurações pessoais; a identificação da edição e a configuração do fluxo de aposentadoria são reaplicadas para corresponder ao pacote escolhido.

Para restaurar também os bancos de idioma, acrescente `-RestoreLocalization`. Para reaplicar todas as configurações, use `-ReplaceConfiguration`. `-VerifyOnly` mostra diferenças sem instalar.

Antes de criar jogador com nascimento 2006–2012, inicie `ModCarrerMode/mods/career_birthdate_2006/dist/Fifa16BirthdateWatcher2006.exe`. Confira a data após reabrir a carreira.

Instale os arquivos de execução pelo instalador. Fontes, testes, galerias, objetos de compilação, documentação e backups ficam fora da instalação do FIFA.

## Desenvolvimento e validação

Branch: `fifa-friends-v12`. Pasta: `J:\mods\fifa 16\fifa-mods-dev\fifa-mods-dev`.

O código das telas extras e do renderer 3D foi separado para a New Experience. A DLL da V12 compila somente o núcleo, os provedores dos cards nativos, a torcida e o motor legado de aposentadoria. [Guia técnico](ModCarrerMode/docs/TECHNICAL.md) e [código nativo](ModCarrerMode/source/career_native/README.md).

As verificações automatizadas cobrem a separação de arquivos, ações dos cards, navegação, configuração e lógica compartilhada. A divisão em edições precisa ser confirmada dentro do FIFA: confira os dois cards de aposentadoria e valide banco/substituições em uma partida nova. Não considere a compilação como confirmação de todos os cenários do jogo.

As referências `dev` e `integracao-new-screens` são preservadas no Git. Esta edição é desenvolvida em uma branch separada.
