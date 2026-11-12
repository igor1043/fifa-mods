# FIFA Friends V12

Mods de carreira, apresentação e partidas para FIFA 16, integrados ao Server16.

## Revisão atual

As telas e módulos desta revisão acompanham a instalação validada do jogo.

- **Finanças:** premiações nativas agrupadas por competição, histórico mensal e anual, rodapé contextual e cards de orçamento e limite salarial com valores completos, inclusive centenas de milhões.
- **Orçamento inicial:** Incorporação Financeira desativada por padrão, com opções até **500 milhões**, aplicação única na criação e sincronização com o orçamento ativo e o salvamento.
- **Central da carreira:** cabeçalho compacto com aproveitamento, avaliação da diretoria e prestígio; painel à direita com data, janela de transferências e caixa na moeda da carreira.
- **Técnicos e títulos:** timeline com escudo do clube, logo da competição e troféu; registro de conquistas de ligas e copas, preservado por carreira e temporada, com proteção contra recompensas repetidas.
- **Pré-jogo:** placar e vídeo de abertura lidos dos catálogos INI, ocupação do estádio e seletor de estádio com país, busca e prévia nas opções da partida.
- **Ambientes 3D:** revisão da parede da hidratação, colisões da sala do treinador, intensidade das luzes e passeio e seleção da sala de troféus; cadastro e ajustes dos modelos de treinadores.
- **Server16 0.2.30:** fontes alinhados ao executável validado, limpeza de cache e logs com proteção de saves, assets originais e sessões em uso. Atalhos: **F12** ou **Select + Start**, conforme o contexto.

As telas iniciais distribuídas não contêm nomes, orçamento ou histórico de uma carreira pessoal. Elas são preenchidas pelo jogo ao abrir cada save. Artes, minifaces e modelos externos continuam em pacote separado; caches, logs e bancos pessoais das carreiras não fazem parte do repositório.

## Modo carreira

| Mod | O que faz |
| --- | --- |
| Central da carreira | Mostra dados da próxima partida e um cabeçalho com treinador, aproveitamento e prestígio do clube. |
| Próxima partida | Reúne escalações, dados do estádio, público previsto, bilheteria estimada e últimas partidas. |
| Meu time | Reúne informações, histórico e estatísticas do clube da carreira. |
| Competições | Exibe classificação, grupos, resultados e a situação das competições da carreira. |
| Chaveamento de copas | Mostra confrontos de mata-mata e placares de ida e volta, com zoom e navegação. |
| Estatísticas das competições | Reúne artilheiros, assistências, defesa, goleiros e o time do campeonato. |
| Rankings mundiais | Classifica clubes, seleções e treinadores com base nos resultados da carreira. |
| Ver clubes | Permite explorar clubes, seleções e ligas pelo globo 3D. |
| 11 iniciais | Exibe o time titular em uma cena 3D no estádio. |
| Jogadores do time | Lista o elenco com filtros, atributos, desempenho e visualização animada do jogador. |
| Detalhes do jogador | Apresenta as informações individuais do jogador selecionado no elenco. |
| Técnico do time | Exibe treinador, miniface, estatísticas e modelo 3D quando disponível. |
| Face do treinador na criação | Permite escolher a aparência em 3D, filtrar por país e liga e manter a escolha vinculada ao save. |
| Ver mascote | Mostra o mascote instalado para o clube selecionado. |
| Visualizar estádio | Carrega o estádio do clube com passeio panorâmico e exploração em primeira pessoa. |
| Mercado de transferências | Organiza a consulta de jogadores, valores e movimentações do mercado. |
| Mercado de técnicos | Gerencia técnicos livres, contratos, contratações, demissões e passagens pelos clubes. |
| Técnicos à beira do campo | Usa o treinador vinculado ao clube; na carreira, acompanha as mudanças do mercado. |
| Finanças do clube | Reúne receitas, despesas, transferências, salários, dívidas, orçamento e gráficos. |
| Sistema financeiro | Acrescenta receitas de TV, bilheteria e patrocínio e despesas de técnico, comissão e operação dos jogos, conforme as opções ativadas. |
| Empréstimos do clube | Permite contratar crédito, consultar contratos e acompanhar parcelas e juros. |
| Aposentadoria | Oferece o fluxo de aposentadoria dentro do modo carreira. |
| Outro clube | Oferece a navegação para mudança de clube na carreira. |
| Verba do clube | Integra a solicitação de verba ao modo carreira. |
| Incorporação Financeira | Na criação da carreira de treinador, permite escolher um acréscimo de 10 mil a 500 milhões ao orçamento inicial. Começa desativada e aplica a verba uma única vez, na moeda selecionada. |
| Histórico por carreira | Mantém os registros dos mods vinculados à carreira e ao seu salvamento, incluindo históricos anuais. |
| Ícones das competições | Aplica os ícones do patch aos cards e ao calendário da carreira. |
| Compatibilidade de competições | Ajusta a integração dos torneios do patch com os dados e telas da carreira. |
| Criação de jogadores | Amplia o intervalo de anos de nascimento disponível na criação de jogadores. |

## Vestiário, câmeras e interface

| Mod | O que faz |
| --- | --- |
| Vestiário 3D | Monta o ambiente do clube com armários, uniformes, chuteiras, quadro da próxima partida e áreas auxiliares. |
| Galeria e sala de troféus | Exibe as conquistas em galeria 2D ou sala 3D, separando o clube durante a passagem do treinador e toda a carreira do treinador, incluindo títulos por seleções. O histórico fica vinculado a cada save, com temporada, competição, data e equipe campeã; acompanha o salvamento e preserva as conquistas ao mudar de ano. Tem 30 pedestais, 15 por lado, com paginação, modelos e materiais originais do FIFA, ano e escudo da equipe vencedora, passeio automático, clique nas taças, visão de detalhe e câmera livre. Inclui banco estofado, porta no padrão do vestiário e murais próprios dos 20 clubes da Série A do patch. A parede é editável em `ModCarrerMode/data/trophy_room/custom/<ID do clube>/identity-wall.png` (1920 × 640); clubes sem imagem usam escudo e nome dinâmicos. Preserva o tamanho nativo das taças, reduzindo apenas modelos que excedem a vitrine. |
| Personalização do vestiário | Permite escolher composição, fundo e contorno dos armários, piso, posição do escudo e artes por clube. |
| Elenco no vestiário | Permite consultar jogadores e atributos mantendo o vestiário ao fundo. |
| Câmera livre | Permite caminhar pelo vestiário com mouse, teclado ou controle. |
| Fundo da carreira | Permite usar imagem estática, estádio 3D ou vestiário 3D como fundo da carreira. |
| Estádio de fundo | Carrega o estádio para os menus e para os fluxos de visualização dos clubes. |
| Panorâmica de estádio | Acrescenta enquadramentos e movimentos de câmera pelo estádio. |
| Câmera em primeira pessoa | Permite jogar partidas pela perspectiva do jogador. |
| Câmera em terceira pessoa aprimorada | Melhora o enquadramento e o acompanhamento do jogador durante as partidas. |
| Cutscenes de técnico e mascote | Insere cenas ocasionais dos dois técnicos e do mascote do mandante, com seleção aleatória e intervalo entre ocorrências. |
| Ultrawide | Amplia a área de visualização 3D nas resoluções compatíveis, mantendo os painéis centralizados. |
| Tema visual | Aplica cards claros e a cor de destaque dourada `#B9A274` às telas dos mods. |
| Identidade FIFA Friends | Aplica a marca do patch à abertura, aos menus e à carreira. |
| Comandos no rodapé | Mostra os atalhos disponíveis no contexto da tela ou do card selecionado. |

## Partidas e apresentação

| Mod | O que faz |
| --- | --- |
| Torcida e público | Ajusta a ocupação das arquibancadas conforme o contexto da partida. |
| Uniformes da torcida | Aplica as camisas dos clubes aos torcedores. |
| Mascote em campo | Posiciona o mascote do mandante nas cenas compatíveis. |
| Entrada dos times | Acrescenta elementos de apresentação e identificação dos clubes na entrada em campo. |
| Escudos em campo | Seleciona os escudos usados nos elementos de apresentação de acordo com os clubes da partida. |
| Bolas ao redor do campo | Posiciona bolas adicionais nas laterais do gramado. |
| Cabine do VAR | Acrescenta a cabine visual do VAR junto à área de publicidade do estádio. |
| Pirotecnia | Acrescenta efeitos de apresentação e comemoração conforme a configuração. |
| Máquinas de fumaça | Controla os efeitos de fumaça na entrada e nos gols. |
| Notícias de outros jogos | Mostra informações de gols de outras partidas no painel do jogo. |
| Banco de reservas ampliado | Permite até 12 jogadores no banco nas situações compatíveis. |
| Sete substituições | Amplia a quantidade de substituições nas regras compatíveis. |
| Saída de bola moderna | Ajusta o posicionamento para a saída de bola. |
| Tiro de meta curto | Permite a saída curta com os jogadores próximos à área. |
| Chute rasteiro | Acrescenta o comando de finalização rasteira. |
| Física de roupas | Acrescenta movimentação às malhas das roupas, com opção para ativar ou desativar. |

## Áudio e Server16

| Mod | O que faz |
| --- | --- |
| Hinos e cantos da torcida | Reproduz os áudios configurados para os clubes. |
| Cantos da torcida visitante | Permite identificar e reproduzir os cantos do visitante. |
| Música de gol | Reproduz a música de comemoração configurada para o clube. |
| Música de substituição | Reproduz os áudios configurados para as substituições. |
| Recursos da partida | Prepara os arquivos instalados de estádio, narração e apresentação, com indicação de carregamento. |
| Configurações dentro do jogo | F12 ou Select + Start abre o painel disponível no contexto da carreira, do pré-jogo ou da partida; os comandos aparecem no rodapé nativo. |
| Seleção de estádio | Permite escolher o estádio e as opções de apresentação da partida. |
| Scoreboard nas opções de jogo | Adiciona um seletor nativo em Partida. Aplica o placar escolhido ao voltar, com opções para o padrão do FIFA ou as regras automáticas do Server16. |
| Mapeamento de controles | Permite ajustar os comandos usados pelos mods. |
| Limpeza de cache e logs | Limita arquivos temporários, limpa sessões encerradas e oferece o botão Esvaziar cache e logs, preservando os dados das carreiras e evidências recentes de diagnóstico. |
| Diagnóstico da inicialização | Registra o carregamento do jogo e dos módulos para investigar falhas. |

## Configuração

- [Módulos carregados pelo jogo](ModCarrerMode/mods/enabled.txt).
- [Configurações dos mods](ModCarrerMode/config/).
- [Cadastro de técnicos por ID](ModCarrerMode/data/manager_market/manager_registry.ini).
