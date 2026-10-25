# Notícias de gols — placares nativos

Revisão de 25/10/2026. Reaproveita os dados produzidos por `ConcurrentMatchManager` e o overlay 75 do FIFA, mantendo o idioma da narração. Não usa WebView, resultados fictícios, leitura de resultados finais antecipados ou gravação no save.

O módulo observa a saída da consulta nativa de incidentes em dois caminhos existentes (serviço de simulação e carreira). Quando recebe um gol ou um resumo nativo de placar, agenda sua apresentação na atualização original de overlays. A chamada da interface ocorre no callback do FIFA; o auxiliar só instala os desvios e grava diagnóstico.

O aviso usa o título localizado `ScoreUpdate`; não depende do nome do artilheiro que a fala suplementar colocaria na interface. Os campos da saída do simulador e da mensagem da interface têm layouts diferentes e são traduzidos explicitamente. Avisos já enviados pelo FIFA são aproveitados e resultados repetidos são descartados. A fila aguarda o aviso anterior sair e é limpa quando muda o conjunto de incidentes ou reinicia a partida.

## Estado da validação

Testes de tradução, repetição, troca de partida e fila podem ser executados sem o jogo pelo script `source/scripts/build_goal_news.cmd`. O teste de hooks executa as quatro pontes contra funções próprias, verificando preservação das chamadas originais, thread de entrega, fila ocupada, desativação e restauração das instruções. Avisos nativos de outros tipos passam sem filtragem. `verify_sites.py <fifa16.bin>` confere separadamente as assinaturas contra o binário de referência offline.

**A exibição em partida foi confirmada pelo usuário em 25/10/2026**, após encaminhamentos de placares reais e repetição solicitada para observação. Essa confirmação é da instalação local; outros computadores e competições continuam sujeitos à simulação que o próprio FIFA produz. O módulo não cria partidas paralelas que estejam ausentes desse simulador.

### Leitura dos jogos paralelos

A sessão de 25/10 mostrou consultas sem incidentes retornados pela narração, enquanto o pool de simulação continha cinco confrontos com gols. O módulo agora também lê esse pool, elimina referências repetidas ao mesmo jogo e conta exclusivamente eventos de gol com minuto menor ou igual ao relógio nativo atual. Nunca usa o placar final já simulado, gols futuros ou eventos de cartões. Não aplica filtro por liga, país ou idioma; só pode mostrar confrontos que o próprio FIFA está simulando em paralelo.

Não há temporizador fixo de notícias. Um novo placar fica disponível após a consulta nativa e entra na fila visual com a espera configurada (250 ms por padrão). O painel anterior deve terminar antes de outro aviso. Um placar repetido é descartado; um aviso pendente há mais de 60 segundos expira. Ao entrar numa partida já em andamento, a primeira leitura pode informar o placar corrente dos jogos paralelos. Essa recuperação pode omitir os placares intermediários que já passaram.

Os testes nativos percorrem o caminho completo de consulta, leitura do pool, fila e callback visual, incluindo jogo de outra competição, referências repetidas e gols futuros. A tentativa de diagnóstico manual da sessão foi retirada após uma falha de endereçamento do código temporário; ela não faz parte do módulo distribuído. A chamada visual permanente usa somente as funções compiladas deste módulo e o callback original do FIFA, sem thread remota nem chamada de áudio.

O export de desenvolvimento `Fifa16GoalNewsReplay` apenas pede uma repetição de um placar já observado. A entrega aguarda avanço do relógio no callback original. A repetição não é acionada no uso automático do mod.

## Arquivos

- `mods/goal_news/goal_news.dll` e uma entrada em `mods/enabled.txt`.
- `config/goal_news.ini`: `enabled=0` desliga o encaminhamento visual; reiniciar o jogo também remove todos os desvios em RAM.
- `logs/goal_news.log`: instalação, eventos aceitos e envio à interface.
- `runtime/goal_news_status.json`: contadores de consultas, eventos, avisos originais, encaminhados e falhas.

Para validar, entrar numa rodada com outras partidas no mesmo horário, deixar a narração em português e jogar até haver gols nos outros jogos. Conferir os placares e o diagnóstico, inclusive após pausa, intervalo e nova partida. Uma rodada sem jogos simultâneos não comprova nem refuta o funcionamento.
