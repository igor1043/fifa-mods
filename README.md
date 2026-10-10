# FIFA Friends V12

FIFA Friends V12 é um mod para FIFA 16 que acrescenta recursos ao modo carreira e ajustes de jogo. O pacote inclui cards de carreira, automações para o save, melhorias de torcida, banco de reservas e substituições.

## Recursos

### Modo carreira

- **Meu Time:** estatísticas dos jogadores e informações do clube, como desempenho, uniformes, estádio, capacidade e prestígio.
- **Competição:** informações de Liga e Copa separadas, com classificação, fases e partidas disponíveis.
- **Próxima partida:** adversário, competição, data, horário, estádio e público estimado quando esses dados estão disponíveis.
- **Remover aposentadoria:** limpa a marca de aposentadoria dos jogadores sinalizados.
- **Remover aposentadoria e redefinir idade:** limpa a marca e ajusta a idade para 18 anos por padrão, preservando mês e dia.
- **Solicitar verba:** acrescenta 1.000.000 ou 3.000.000 à verba de transferências.

As ações de aposentadoria e verba são processadas depois que você sai do save. Aguarde o autosave; na aposentadoria, escolha sair sem salvar. Permaneça no menu enquanto a camada mostra o andamento e reabra a carreira após a confirmação. O FIFA pode continuar aberto no menu durante o processamento.

### Mods incluídos

- **Mascote:** uma instância por mandante com pacote local; troca de gol no intervalo e comemoração de 26 segundos. [Instalação dos modelos e limitações](ModCarrerMode/source/mascot_photographer/README.md).
- **Bolas extras:** 13 cópias visuais da bola da partida ao redor do campo, sem física de gameplay.
- **Saída de bola moderna:** receptor na diagonal, passe para trás e demais cobradores fora do círculo.
- **Ícones da carreira:** resolução dinâmica de competições e pré-temporada, com catálogo compartilhado.


- **Torcida:** estima a ocupação do estádio com base em reputação, adversário, desempenho, competição, rivalidade e importância da partida.
- **Banco de reservas:** prepara até 12 jogadores reais. O tamanho do banco é independente do limite de substituições.
- **Sete substituições:** permite até sete trocas por partida.
- **Player Career 2006–2012:** permite criar jogadores nessa faixa de nascimento e mantém a data no save com o watcher incluído.
- **Server16Python / CR16:** ajustes de escolha de estádio, público ao iniciar e volume da torcida.

## Requisitos

- FIFA 16 instalado, com `FIFA16.exe` na pasta do jogo.
- Windows com PowerShell, usado pelo instalador incluído.

## Instalação

1. Baixe o pacote da [branch FIFA Friends V12](https://github.com/igor1043/fifa-mods/tree/fifa-friends-v12) e extraia os arquivos mantendo a estrutura de pastas.
2. Feche o FIFA 16 e o Server16Python.
3. Abra um terminal na pasta extraída e execute, substituindo o caminho pelo local onde o FIFA 16 está instalado:

   ```powershell
   .\ModCarrerMode\install-game.cmd -GameDirectory "C:\Caminho\para\FIFA 16"
   ```

O instalador verifica a pasta escolhida e cria backups dos arquivos que substituir. Não remova esses backups até confirmar que o jogo iniciou corretamente.

## Como usar

- Os cards de carreira ficam nas abas e áreas indicadas no próprio jogo. Para aposentadoria ou verba, selecione o card correspondente e siga a orientação exibida na camada.
- Para criar um jogador com nascimento entre 2006 e 2012, inicie `ModCarrerMode/mods/career_birthdate_2006/dist/Fifa16BirthdateWatcher2006.exe` antes de criar o jogador.
- As estimativas de torcida são aplicadas automaticamente durante a carreira.

## New Experience

A New Experience é uma edição separada, com um card **Meu Escritório** que abre telas próprias de carreira: central e calendário, notícias, busca de clubes e ligas, competições, perfis de clube, jogador e treinador, visualização 3D, ranking, operações, transferências, patrocinadores, próxima partida e sala de troféus. Ela está disponível na [branch FIFA Friends New Experience](https://github.com/igor1043/fifa-mods/tree/fifa-friends-new-experience) e não faz parte deste pacote V12.