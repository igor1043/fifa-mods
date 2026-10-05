# FIFA Friends - New Experience

Edição do FIFA 16 que reúne os mods compartilhados e a interface adicional de carreira. **Meu escritório** abre a tela principal dessa experiência, com navegação própria, ilustrações e visualizações 3D.

## O que muda nesta versão

- **Meu escritório:** tela principal com resumo do clube, navegação e cenas de apresentação.
- **Clube e jogadores:** clicar em Clube, na aba Meu Time, abre o elenco; a ficha individual mostra atributos, retratos, poses e modelos 3D lidos dos assets do FIFA.
- **Explorar o futebol:** ranking mundial, outros clubes, perfil de técnico, ligas, competições e busca de jogadores.
- **Próxima partida:** o card abre uma tela com foto dos 11, escalações disponíveis, técnicos e imagem do estádio.
- **Ambientes:** cenas de escritório, foto coletiva, vestiário, coletiva de imprensa e sala de troféus, com dados e modelos disponíveis na instalação.
- **Aposentadoria:** tela própria com seleção de jogadores, escopo de clube ou global e opção de redefinir idade. A confirmação cria uma solicitação; salve e feche o FIFA para o worker processar.
- **Finanças:** interface de empréstimos, parcelas e operações sobre o orçamento de transferências, com processamento após salvar e fechar o jogo.
- **Transferências:** telas de mercado, minhas transferências e consultas por liga. A geração de uma proposta nativa de emprego para trocar o clube do técnico continua em estudo; não é apresentada como recurso pronto.

O carrossel da Central contém **Próxima partida** e **Meu escritório**. A contagem foi corrigida para não criar um terceiro card vazio.

As telas extras e operações financeiras são experimentais. Ausência de assets ou dados é indicada; não se usa o modelo de outro clube/jogador como se fosse o solicitado. A visualização livre do estádio 3D continua desativada.

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

O público escolhido no painel do Server16Python vale somente para a partida atual. Ao voltar ao menu da carreira, esse ajuste é descartado; na próxima partida, o mod dinâmico volta a determinar o público. Para alterar novamente, aplique um novo percentual no painel antes dessa partida. O servidor não salva esse percentual no `ModCarrerMode/crowd.ini`.

Mantenha `automatic_dynamic_controller=1` para o cálculo automático do mod. Não é necessário desativá-lo para fazer uma escolha temporária no painel do servidor. O modo manual permanente do `crowd.ini` é uma configuração diferente.

Revisão de 04/10/2026: conferida a liberação do público manual entre partidas, inclusive quando o próximo confronto tem os mesmos times. O `Server16Python.exe` deste pacote contém também os ajustes recentes de tamanho do painel, navegação por F2/controle e cursor visível. A revisão automatizada não substitui a confirmação dentro do FIFA.

## Instalação

Use uma instalação funcional do FIFA 16 com os assets de base. Feche o FIFA e o servidor antes de substituir executáveis. Na pasta deste pacote, execute:

```powershell
.\ModCarrerMode\install-game.cmd -GameDirectory "U:\fifa 16"
```

O instalador instala esta edição, incluindo `Server16Python.exe`, plugins e payload de nascimento. Faz backup externo dos arquivos substituídos e arquiva componentes exclusivos da New Experience quando instala a V12. Preserva saves, contratos e configurações pessoais; a identificação da edição e a configuração do fluxo de aposentadoria são reaplicadas para corresponder ao pacote escolhido.

Para restaurar também os bancos de idioma, acrescente `-RestoreLocalization`. Para reaplicar todas as configurações, use `-ReplaceConfiguration`. `-VerifyOnly` mostra diferenças sem instalar.

Antes de criar jogador com nascimento 2006–2012, inicie `ModCarrerMode/mods/career_birthdate_2006/dist/Fifa16BirthdateWatcher2006.exe`. Confira a data após reabrir a carreira.

Instale os arquivos de execução pelo instalador. Fontes, testes, galerias, objetos de compilação, documentação e backups ficam fora da instalação do FIFA.

## Editor e visualizador 3D

O [New Experience 3D](ModCarrerMode/source/ambientes3d/README.md) reúne os fontes e o EXE do editor externo. Seus ambientes de imprensa, vestiário, academia e CT, com objetos, poses, câmeras e presets, agora são gerenciados nesta branch. Execute `ModCarrerMode/source/ambientes3d/Ambientes3D.exe`; no computador de desenvolvimento, o acesso também fica em `J:\mods\fifa 16\ambientes 3d`.

O editor busca malhas, esqueletos e texturas nativas na instalação do FIFA. Os ambientes são definidos pelos fontes do projeto. As versões ampliadas de imprensa, vestiário, academia e CT do editor precisam de integração específica para aparecerem nas telas da carreira; salvar presets não instala alterações automaticamente no jogo.

## Desenvolvimento e validação

Branch: `fifa-friends-new-experience`. Pasta: `J:\mods\fifa 16\fifa-mods-dev\experiencia nova`.

Esta edição mantém o host das telas extras, os provedores, o renderer 3D, ImGui e as ferramentas de prévia. [Guia técnico](ModCarrerMode/docs/TECHNICAL.md) e [mapa das telas e renderização](ModCarrerMode/source/career_native/README.md).

O card **Meu escritório** abre a apresentação HTML dentro do FIFA por WebView2. **Começar** leva à central Início/Ligas/Times/Jogadores/Transferências, com navegação por mouse, teclado e controle. Os onze titulares, o perfil individual e os ambientes atualizados de coletiva, vestiário, academia e CT são renderizados nativamente e enviados ao HTML. O clique num jogador abre o perfil no mesmo tema. Para visualizar sem abrir o FIFA, execute `Abrir Nova Experiencia.cmd`; `ModCarrerMode/tools/club_globe/Atualizar.cmd` recompõe os dados do save configurado e os renders. A prévia offline reflete o último save em disco. O runtime WebView2 do Edge é necessário para a interface dentro do jogo.

A nova edição foi separada da base `integracao-new-screens`; a validação feita anteriormente nessa base não substitui o teste das edições após a divisão. A ponte HTML/Direct3D está instalada como build experimental no jogo de desenvolvimento; confirme o fluxo dentro do FIFA antes de distribuir a edição.

As referências `dev` e `integracao-new-screens` são preservadas no Git. [Registro técnico da integração original](ModCarrerMode/docs/INTEGRACAO_NEW_SCREENS_REFERENCIA.md).

### Perfis HTML e visualização 3D

A central abre os perfis de jogador e treinador pelos cards. A tela de clube abre sobre a liga; B/Esc fecha essa página e preserva a seleção. O foco usa a posição visual dos cards nas quatro direções, por teclado, direcional e analógico esquerdo.

Nos perfis, mantenha Y pressionado para manipular o 3D: analógico direito gira, analógico esquerdo desloca, LT/RT dão zoom e Y + R3 + analógico direito permite a inclinação lateral. Soltar Y devolve os analógicos à navegação. X troca para outra pose sorteada; F ou o botão da tela alterna retrato/modelo. Mouse: arrastar gira, Shift + arrastar inclina lateralmente, roda aproxima quando a área 3D está em foco e duplo clique restaura a câmera.

A visualização interativa usa malhas e texturas reais do FIFA, exportadas pelo motor nativo para WebGL. Funciona com o FIFA fechado, a partir do save configurado em `ModCarrerMode/tools/club_globe/clubes.ini`, usando `Abrir Nova Experiencia.cmd`. Não reproduz as animações em execução do motor do jogo. As poses são as do catálogo do mod.

O servidor é local (127.0.0.1:8876), lê o save sem alterá-lo e mantém o leitor nativo aberto. Reaproveita modelos e texturas entre poses. As estatísticas por competição dos jogadores usam a fonte nativa na carreira aberta; campos não encontrados no save ficam indisponíveis, sem valores simulados. O instalador inclui o servidor, o leitor e as telas na instalação do jogo.
