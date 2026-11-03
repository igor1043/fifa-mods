# Mercado de técnicos — salvamento e processamento em background

Revisão R3 de 02/11/2026. Código instalado no jogo e no desenvolvimento.
Usa o Server16 0.2.19 e os complementos já distribuídos, incluindo o catálogo
visual R2. Não altera modelos, fotos ou o executável e não exige um novo ZIP.

## Salvamento

O mercado usa SQLite ao lado dos saves do FIFA; não é MySQL. Os arquivos nativos
DATA/INDEX e as tabelas do FIFA continuam sendo somente leitura para este serviço.

- A escrita nativa concluída de um `SaveType_Career` gera um recibo durável.
  PID, criação do processo, contexto, geração da carreira, data, clube, tamanho,
  CRC e hash vinculam esse recibo ao estado correto do mercado.
- Cada observação registra quando os dados foram lidos e quando o cálculo
  terminou. Salvar enquanto o auxiliar calcula não invalida uma observação
  anterior à escrita. Uma observação feita depois da escrita não é emprestada
  retroativamente a ela.
- O checkpoint guarda uma cópia completa e imutável dos vínculos, movimentações,
  resultados, salários e campanhas. Uma nova escrita confirmada pode atualizar
  esse checkpoint mesmo quando os bytes do DATA não mudaram.
- Recarregar restaura o checkpoint, incluindo o técnico de cada clube. Sair sem
  salvar descarta a linha do tempo mutável; o avanço não salvo não vira histórico
  confirmado de outra carreira. O diário temporário e limitado a 128 observações
  por processo pode permanecer para concluir a associação de recibos pendentes.
- A fila mantém observações de datas intermediárias ao passar de leitura para
  escrita na mesma sessão. Uma nova leitura de save sempre separa a linha do tempo.
- Abrir uma tela ou preparar a próxima partida não equivale a salvar. Se o FIFA
  fizer um salvamento automático nesse fluxo, o mesmo recibo confirma o estado;
  sem escrita nativa concluída, o estado continua sendo da sessão não salva.

Foi recuperado localmente um checkpoint real de 30/05/2026 a partir do diário
capturado antes da escrita: Lucas Bovaglio no Atlético-MG e Xavi Hernández no
Grêmio. A recuperação alterou somente o banco do mod. O SHA-256 do DATA permaneceu
idêntico antes e depois da instalação; o banco anterior foi preservado em backup.

## Calendário e abertura

O serviço continua ativo fora da tela do mercado. A coleta verifica as ligas a
cada 200 ms e o consumidor consulta atualizações a cada 500 ms. Esses intervalos
são de consulta, não uma promessa de conclusão nesse prazo: saltos longos ainda
precisam de cálculo. Somente datas e resultados realmente observados são usados.

A montagem APT/imagens passou a um processo persistente separado. Uma thread
leve troca pedidos por arquivos; apenas o processo principal escreve o estado
SQL e publica a interface. Os pedidos são identificados e a publicação rejeita
outra carreira, contexto ou data. Nenhuma thread de compilação disputa o GIL com
o cálculo dos contratos.

As contratações calculam a atratividade da liga uma vez por clube. O fechamento
de um vínculo retém apenas a campanha desse vínculo, evitando reler todo o
histórico mundial a cada demissão. Atualizações idênticas dos clubes são ignoradas.
Recibos sem observação correspondente não provocam a decodificação repetida de
saves antigos. O catálogo gráfico R2 aceita subconjuntos válidos de clubes de
outros saves sem recompilar todas as imagens; os bytes dos assets são verificados.

## Ligas e decisões

O modelo real contém 49 países/regiões e todas as divisões disponíveis nos dados
usados. Espanha inclui LaLiga EA Sports, Hypermotion e Primera Federación. O clique
do mouse e o evento de seleção que o FIFA ecoa agora contam como uma única ação.

As revisões continuam globais e dependem de partidas reais das ligas. O padrão
passou para intervalo mínimo de cinco dias, limiar de pressão 20, inclinação 190
e teto de probabilidade de 60% por revisão elegível; não é uma taxa diária fixa.
O Brasil conserva seu modificador de rotatividade. O limite de três demissões por
clube por ano, o período mínimo de trabalho, a proteção do clube controlado pelo
jogador e a raridade de recontratação continuam ativos. A migração reconhece os
valores padrão antigos e preserva configurações personalizadas.

## Validação e limites

- Suíte completa: 175 testes em 342,17 s, sem falhas, um teste opcional ignorado.
  Abrange checkpoint, recarga, saída sem salvar, troca de contexto, contratação,
  navegação APT e publicação concorrente.
- Dois testes adicionais cobrem salvar com datas intermediárias na fila e
  recarregar o mesmo arquivo após salvar. O conjunto de calendário/salvamento
  com esses casos passou: 22 testes em 11,78 s.
- Mesmo avanço de 20/04 a 30/05 com banco clonado, entradas reais e política igual:
  21,11 s antes, 7,34 s depois (65% menos), com o mesmo hash das nomeações ativas.
- Na sessão real, o auxiliar restaurou o checkpoint, calculou o mercado e
  publicou a tela em 27,68 s desde o pedido inicial. Entrada/cálculo: 7,05 s;
  projeção: 3,44 s; compilação isolada: 8,60 s. O restante inclui a inicialização
  do processo e a entrega no próximo ciclo. Reutilizou 574 blocos gráficos.
- Reinício do auxiliar na mesma sessão, com pacote pronto: 10,08 s até publicar,
  sem recompilar imagens. O vínculo do mercado foi preservado no reinício.

Essas medições não prometem abertura instantânea em toda máquina. A primeira
preparação ainda tem custo; o objetivo é fazê-la durante o calendário, manter a
tela pronta e preservar o salvamento independentemente da apresentação. A
revisão foi observada por logs/RAM; uma nova confirmação visual e um ciclo manual
salvar/fechar/reabrir no FIFA ainda cabem ao teste do usuário.
