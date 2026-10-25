# Próxima partida e Mercado — revisão local de 25/10/2026

Próxima partida interrompia todas as páginas quando um titular gravado não pertencia mais ao elenco. Na carreira examinada, a escalação padrão do Botafogo continha o jogador 208670, ausente dos vínculos do clube. A projeção agora preserva titulares válidos, prioriza outra escalação completa disponível e, quando necessário, completa uma escalação **provável** com jogadores reais vinculados ao clube, considerando posição e overall. Não altera escalações nem saves. Se faltarem onze jogadores, informa a indisponibilidade dessa escalação e mantém estádio e histórico acessíveis. O provider nativo continua substituindo a prévia do próprio time pela escalação atual em RAM.

Os nomes usam o decodificador de texto comprimido já utilizado pelo Mercado, consultando só IDs ausentes do cache. Isso remove a espera por um auxiliar x86/.NET de até 45 segundos. Cache incompleto é reconstruído; a publicação é atômica.

O carrossel usa `LAS_LEFT`/`LAS_RIGHT`, com a legenda original `LAS_LR`. Os três cards continuam usando as setas e os indicadores nativos. O teste executa o APT gerado, incluindo um elenco incompleto, percorre os três cards e rejeita os eventos do analógico direito.

As duas telas passam primeiro por uma visualização de espera própria, sem exibir dados antigos por baixo. Um único consumidor no ciclo existente da interface verifica PID, identidade de criação do processo, clube, contexto, registry, época, data e frescor da publicação. Próxima partida também compara o jogo agendado com o modelo atual da carreira. Só então envia o evento para carregar a tela preparada. A navegação recarrega exclusivamente a view; mantém o controller e os modelos existentes. O consumidor não roda durante callbacks de StatisticsData e não chama a interface a partir de auxiliares.

No Mercado, um token repetido não recoloca dados prontos atrás da cobertura de carregamento. Capturas equivalentes renovam `view_ready.tsv` sem reconstruir o APT ou reiniciar a navegação. Mudanças reais invalidam o cache. Aberturas ignoradas temporariamente pelo controller são tentadas novamente enquanto a view de espera continuar ativa.

## Correção confirmada na sessão aberta

A preparação já publicava Flamengo x Botafogo, mas a interface permanecia em `MatchPreviewLoading`. A inspeção da RAM mostrou que o consumidor enviava repetidamente `SendSystemEvent(Calendar, Server16RefreshMatchPreview)`. O controlador nativo do calendário só trata `DONE_LOADING` nesse caminho e ignora o evento personalizado. Os testes anteriores substituíam esse controlador por um mock permissivo e, por isso, não detectavam a falha real.

O consumidor agora constrói um `FCEGameModes::External::NavEventMessage` com o alocador do FIFA e o entrega à fila nativa, como faz a navegação do menu. Resolve o barramento pelas registries da sessão e valida seus métodos antes de alocar. O barramento assume a propriedade da mensagem e faz a transição fora do callback atual; não destrói controller, view model ou provider dentro do callback. Continuam obrigatórias todas as validações de sessão, clube, data, partida e thread. A espera dá dois segundos para a fila executar antes de repetir; uma tela pronta com a mesma revisão não recarrega.

No FIFA aberto, essa troca de caminho mudou a página de `MatchPreviewLoading` para `MatchPreview`. O usuário confirmou escalações, estádio, últimos resultados e troca de páginas pelo analógico esquerdo. A confirmação visual ocorreu antes da instalação permanente. O cabeçalho de cada escalação também passou a ter a mesma largura e posição horizontal do campo, tocando seu limite superior. A espera não repete Esc/B em texto; mantém a legenda original no rodapé.

Verificações adicionais: 18 testes Python para projeção/progressão, elencos incompletos, três páginas, input, cabeçalho e tela de espera; teste nativo da fila, propriedade/liberação das mensagens, thread, escopo e proteção dos providers; compilação completa da DLL. Logs da fila: `career_preview_view_queued_on_ui_owner` e `career_market_view_queued_on_ui_owner` em `career_loader.log`. Prontidão em `runtime/club_environment/{preview/runtime,market}/view_ready.tsv`.
