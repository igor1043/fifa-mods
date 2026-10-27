# Mercado de Transferências nativo

Novo item no carrossel do card Rede Mundial, abaixo dos olheiros, na aba
Transferências. A tela é APT/BIG,
com o mesmo controlador de ciclo de vida usado em Empréstimos. Não usa WebView.

## Entrega de 24/10/2026

Inclui card/callback nativo, tela transparente ao ciclo de vida da carreira, leitura dos negócios ainda não salvos, recarga automática após captura válida e revisão dos espaçamentos/rodapé. A integração usa o card estático GTN_STATIC para preservar os providers dos olheiros e a montagem da Central. A tela inicial distribuída aguarda dados reais, sem jogadores ou negociações da carreira do desenvolvedor.

## Dados

O auxiliar abre a RAM com `PROCESS_VM_READ | PROCESS_QUERY_INFORMATION` (0x410).
O serviço de carreira validado identifica clube, usuário e data. O evento nativo
de leitura/gravação identifica o DATA da mesma sessão, com PID e criação do
processo. O host consulta ofertas concluídas, pré-contratos, jogadores e vínculos
no banco vivo, na thread proprietária já usada pela fila de comandos da interface.
Cada resultado nativo é liberado na mesma chamada. O snapshot completo é publicado
por substituição atômica em `live_market.tsv`, com PID, clube, contexto, geração,
data e número da entrada na tela. Capturas incompletas, antigas ou de outra carreira
são rejeitadas. O DATA fornece o catálogo de referência, sem precisar ser salvo
novamente para incluir uma negociação concluída na sessão atual.
Uma compra precisa do resultado 32 e de vínculo confirmado no clube comprador.
Propostas abertas/recusadas ficam fora dos totais. Fotos, escudos e ícones são
obtidos dos assets da própria instalação.

Cada entrada mostra o carregamento automaticamente e espera uma captura recente
da carreira. Não depende de o contador de entrada mudar: enquanto a tela estiver
aberta, novas capturas podem liberar a espera mesmo com esse contador igual.
Uma publicação de atualização é limitada a cada quatro segundos; catálogo,
projeção e imagens são reutilizados quando os dados não mudaram.
Se o controlador ainda estiver ocupado, o APT repete o evento até a remoção real
da tela confirmar a recarga. Não há botão Atualizar. O calendário da janela e o clube
selecionado usam a RAM atual, inclusive após trocar de clube. O auxiliar reconstrói
o pacote após mudança dos negócios, clube, data ou entrada; a publicação é atômica
e descarta trabalho se o contexto mudar durante a geração. O APT recarrega apenas
a própria tela enquanto aguarda; ao receber os dados novos, encerra essa espera.
Nenhum arquivo DATA/INDEX, orçamento ou registro SQL é alterado pelo mercado.

## Navegação

- Setas/direcional: mover seleção; Enter/botão de confirmação: selecionar.
- Esc/botão de voltar: retornar ao nível anterior; no Resumo volta à Central.
- L1/R1 (LB/RB): abas, com retorno circular entre as cinco opções.
- No FIFA PC, os nomes internos L1/R1 correspondem a LT/RT; L2/R2 correspondem
  a LB/RB. Por isso as abas usam InputCodes.L2/R2 e o ícone original L2R2,
  para acionar os botões físicos de ombro pedidos pelo usuário.
- O teclado usa os comandos que o próprio FIFA associa a esses botões.
- Analógico esquerdo/direcional ou setas esquerda/direita: trocar as páginas
  dos negócios e dos rankings paginados. As bolinhas indicam a página atual.
- O carregamento ocorre automaticamente; Voltar funciona durante a espera.
- Legendas: HelpManager original com ADVANCE, BACK e L2R2; LAS_LR nas páginas.

O card usa apenas `TILE_NESTED` e `TILE` do FIFA, com duas entradas fixas:
Mercado de Transferências e Rede Mundial. Não depende da quantidade de
relatórios nem modifica o provider dos olheiros. Os relatórios 208/215,
a geometria do painel, os demais cards e a lista de componentes são preservados.

O clique em Mercado dispara `Server16EnterTransferMarket` pelo callback nativo
`ACTION_NAV` do card. A transição já registrada no `mainmenuhubflow.nav` entra
em `server16transfermarketflow.nav`, carrega a tela TransferMarket e usa o
retorno Calendar/ReturnToHubFromCalendar. As legendas do card são as da Central.

A primeira tentativa usou um componente auxiliar `MarketHubBootstrap` e
bloqueou a montagem visual da Central. Esse componente não participa mais do
layout nem é usado pela integração atual. O leitor nativo é incluído no host
`dinput8.dll`, preservando os demais módulos e o fluxo estável da interface.

## Execução e diagnóstico

O processo existente de próxima partida inicia um auxiliar isolado usando o
Server16Python já instalado. Builders, caches e falhas ficam separados; não
requer instalar Python. Fontes em `market/`; diagnóstico em
`ModCarrerMode/runtime/club_environment/market/`:

- `launcher.log`: erros de inicialização/importação.
- `worker.log`: contexto aguardado e pacotes preparados.
- `status.json`: PID, clube, data atual/data gravada, hash e quantidade de negócios.
- `market.json`: projeção dos negócios da carreira aberta, somente para leitura.
- `live_market.tsv`: negócios e vínculos consultados no banco em memória.

Os arquivos pessoais de diagnóstico e snapshots não devem ir ao GitHub.
`test_market.py` verifica bytecode APT real, cabeçalhos nativos, navegação,
rodapé, isolamento do fluxo, casos de carrossel e leitura sem alterações no DATA.
`test_live_market.py` cobre negócios ainda não salvos e rejeição de snapshots
inválidos. `test_career_market_read.c` cobre a consulta nativa na thread correta,
limites, mudança de contexto e publicação apenas de capturas completas.
Teste físico de teclado/controle e conferência de aparência dentro do FIFA
complementam os testes automatizados.
