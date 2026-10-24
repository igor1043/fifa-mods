# Dados da carreira em execução

## Implementado

A DLL principal publica `Fifa16CareerContextRead`, um registro de 48 bytes,
somente para leitura. Ele identifica o processo, o serviço da carreira, seu
registro nativo, a geração do contexto e a thread que atendeu o pedido nativo.
Um contador de sequência permite rejeitar uma leitura feita durante publicação.
Python e o estádio validam também o serviço no registro, sua vtable e o clube
selecionado. A referência de leitura independe do objeto temporário dos cards.
Manter a identidade disponível não autoriza chamar esse objeto depois de sair
da Central: as proteções de ciclo de vida dos cards continuam separadas.

O calendário é lido no serviço nativo; os resultados vêm da captura estável do
motor de competições. A prévia exige a mesma data nas duas fontes, identifica
o save e escolhe o próximo jogo ainda não disputado. Os jogadores vêm das
escalações do save ativo; a escalação adversária continua sendo uma previsão.
O auxiliar reconstrói o pacote quando mudam data, save, clube ou partidas.
A publicação do pacote usa rename atômico. A recarga da tela passa pelo
dispatcher nativo, na thread verificada, apenas na própria tela de prévia.

O empréstimo mantém solicitações, contratos, parcelas e pedidos processados em
JSON por slot e clube. O envio registra uma solicitação, sem creditar dinheiro,
com análise prevista para o próximo dia da carreira. Ao chegar ou ultrapassar
essa data, a análise usa o contexto e saldo atuais. Uma aprovação exige diário
prévio, escrita do orçamento e conferência imediata na RAM.
O comando V3 inclui a data congelada no clique. A leitura posterior não usa
o dia corrente como data de envio. O histórico `applications` conserva envio,
resposta prevista, análise efetiva, decisão e saldos, inclusive após concluir
o pedido. O dia previsto nunca é recalculado com base na consulta.
O diário permite recuperar uma dívida após reinício do auxiliar sem repetir
o crédito. Um carregamento nativo posterior prevalece sobre esse diário.
Uma gravação nativa validada associa o estado financeiro ao hash daquele save.
DATA e INDEX não são editados por essa ponte.

A notificação nasce na data da análise, somente após a operação conferida
(ou recusa de regra), e usa uma fila própria. A DLL
insere uma RawEmail pelo gerenciador nativo de mensagens, com alocação nativa,
na thread e na Central verificadas. A confirmação vem após localizar a mensagem
na caixa. Um ID único evita duplicação; mensagens comuns mantêm seu conversor
original. A persistência da mensagem no save continua sendo feita pelo FIFA.
Uma confirmação de entrega pertence ao processo, contexto e geração atuais.
Depois de carregar novamente, a fila confere o ID no inbox nativo antes de
considerar entregue; assim, uma confirmação antiga não perde o e-mail nem
provoca sua duplicação.

## Evolução proposta, ainda não implementada

Um banco SQLite pode substituir os arquivos financeiros mantendo a mesma
separação: leitura, regras, fila de comandos e conferência da aplicação.
Tabelas previstas: carreiras, partidas, receitas/despesas, contratos, parcelas,
operações e notificações. Cada operação precisa de chave única, origem,
vencimento, valor, saldo anterior/posterior e estado de confirmação.

Eventos de data devem processar todos os vencimentos até o dia observado,
inclusive quando o calendário pula vários dias. Eventos de partida precisam
de ID e resultado concluído para não gerar receita na prévia, durante uma
simulação ou novamente depois de carregar. Bilheteria adicional depende de
conferir antes o crédito que o próprio FIFA já faz.

Novas escritas precisam de adaptadores específicos por estrutura nativa;
este registro não é uma API genérica de escrita arbitrária em memória.
