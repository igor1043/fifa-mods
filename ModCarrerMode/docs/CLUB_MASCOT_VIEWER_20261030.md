# Ver mascote em Ver clubes

Em Temporada → Outras ligas → Ver clubes, a seleção do clube abre quatro
cards: 11 iniciais, Jogadores do time, Técnico do time e Ver mascote.
Nenhum acesso novo é acrescentado ao Escritório.

O quarto card mostra o mascote do clube selecionado no centro do gramado do
estádio já carregado, com o mesmo ciclo nativo de recursos usado pelos
jogadores. É uma visualização estática: o mouse ou o analógico direito giram
a câmera em torno do mascote. Não cria uma partida, não altera o mascote da
linha de fundo e não grava dados na carreira.

Controles: arrastar o mouse ou analógico direito para girar/ajustar a altura;
roda do mouse, gatilhos, L1/R1, W/E ou −/+ para zoom. Setas esquerda/direita
ou J/L também giram. A opção Centralizar restaura o enquadramento. Voltar
retorna aos quatro cards e mantém o foco em Ver mascote.

O pacote é procurado exclusivamente em data/sceneassets/mascot/<ID do clube>/,
usando model.rx3 e textures.rx3. Sem os dois arquivos, não renderiza um
modelo e não usa mascote de outro clube. A identificação do clube observado
é separada do clube que controla a carreira. Pedidos antigos e trocas de
carreira não podem publicar um modelo no contexto seguinte.

Geometria, UVs e pixels comprimidos originais são preservados. A preparação
somente centraliza a malha e apoia seus pés no piso. As cópias adaptadas para
GameplayProp ficam no cache e na área gerada server16_club_xi. O pacote do
mascote usado durante partidas não é modificado. A câmera e a visibilidade
usam o ciclo de restauração existente ao sair.

Validação: 63 pacotes instalados passaram na leitura/conversão intermediária;
um pacote nativo completo do Criciúma foi preparado e inspecionado por dados.
Os testes APT cobrem quatro cards, atalhos, volta, foco por mouse/teclado e
controle, e encerramento. Os testes nativos cobrem câmera centralizada,
restauração, seleção de outro clube, ausência de pacote e materiais inválidos,
além dos testes de estabilidade dos jogadores/XI já existentes.

Conferência visual dentro do FIFA permanece para o teste do usuário. Revisão
local, sem commit ou push. Backups e manifestos estão em code-release,
indicados por mascot-viewer-current.txt.
