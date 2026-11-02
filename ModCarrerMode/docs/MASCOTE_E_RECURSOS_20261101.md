# Orientação do mascote e recuperação de recursos incompletos

## Mascote

A versão anterior acrescentava 180° à orientação da paleta e seu teste usava
um eixo frontal idealizado. A revisão 32 utiliza o eixo corporal do esqueleto
convertido. Durante caminhada e giro, compensa também o ângulo da pose animada
e da transição: o corpo fica alinhado à direção do próximo ponto. Parado, volta
a olhar para o campo. Os clipes, a cadência dos pés, as posições do trajeto e o
histórico de replay mantêm seus mecanismos existentes.

Os testes percorreram as poses reais da caminhada e a compensação do esqueleto
do renderizador para os 63 pacotes instalados. Também passaram os percursos nos
dois sentidos, pausa, mudança de lado, comemorações e histórico de replay.
A conferência visual da nova DLL no FIFA ainda está pendente.

## Jogadores invisíveis

Na partida examinada, o mapa nativo identificou dois titulares do Fluminense
com recursos vazios: jogador 50182, slot 24, e Hulk 189362, slot 29. A informação
de jogador pronto estava em cache, mas os quatro LODs estavam sem preparação
concluída e sem pedidos de assets em andamento. Os arquivos da face e do cabelo
do Hulk existiam. Isso é evidência de estado incompleto de carregamento, não
uma conclusão sobre qual rotina deixou o estado assim.

O callback de cena agora verifica esse estado específico. Depois de uma janela
de estabilidade, solicita a preparação pela função original do FIFA. Não força
visibilidade, não fabrica um estado pronto e não substitui modelos ou texturas.
Há limite de tentativas, intervalo, validação de identidade e bloqueio enquanto
uma transação nativa de assets estiver aberta. Menus externos e pós-jogo não
acionam a recuperação. Os testes verificam o limite/intervalo e a rejeição de
recursos prontos, pedidos em andamento, estruturas inválidas e mundo ausente.
A recuperação real precisa ser confirmada nos registros após a instalação.

## Placa de substituição

O usuário relatou o árbitro animando com as mãos vazias. A placa atual usa o
modelo 100 e a competição 7. O arquivo `prop_7_100.rx3` existe e contém os cinco
submeshes esperados, incluindo estrutura e números. Fora da cutscene, a placa
foi encontrada descarregada; isso isoladamente não prova defeito, porque o
FIFA pode liberá-la fora de uso. Depois, com o usuário na própria cena, uma
segunda captura confirmou `package_sub_oop`, replay ativo e a placa ainda sem
pedidos de assets preparados. A evidência está em
`code-release/substitution-board-audit-20261101/paused-cutscene-board-actual.json`.

A revisão inclui uma preparação antecipada limitada do recurso da placa quando
ele está vazio, usando a publicação de parâmetros e a preparação originais do
renderizador, e conclui a inicialização original quando os arquivos estiverem
prontos. Não altera visibilidade, números, animação ou seleção de cutscene.
O resultado visual ainda precisa ser conferido durante uma substituição.

## Relação com o som

As alterações publicadas do mod de som não incluíram arquivos `data/`, placa,
modelos de jogadores ou DLLs dos efeitos de cena. O leitor abre a partida com
permissões de consulta/leitura e o MP3 toca via MCI fora do processo do FIFA.
Não foi demonstrada relação causal entre o som e as falhas visuais.

## Instalação e rollback

Build de revisão e backup da versão anterior em
`code-release/mascot-route-orientation-20261101`.
Até a instalação/reinicialização, o FIFA já aberto continua usando a DLL antiga.
O relatório de instalação deve registrar os hashes e o estado real da validação.
Sem commit nem push.
