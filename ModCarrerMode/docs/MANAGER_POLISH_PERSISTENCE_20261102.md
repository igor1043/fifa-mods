# Mercado: filtros, observações e salvamentos — revisão local de 02/11/2026

## Interface

- Nomes dos títulos resolvidos pela localização instalada e pelos nomes
  personalizados já utilizados na prévia da partida. O ID 1009 desta instalação
  é CONMEBOL Recopa Sudamericana; `TrophyName` tem prioridade sobre o nome de liga
  que reutiliza esse número. Títulos já registrados também recebem o nome correto.
- Retirado o card de formação preferida da aba Estilo de jogo.
- Nacionalidade principal individual nos cards e no seletor de técnicos livres.
  Países concatenados de fontes do catálogo não viram uma nacionalidade composta.
- País/região e liga têm seletores separados. Mudar o país restringe as ligas e
  reinicia o filtro dependente, sem alterar o mês escolhido.
- Barras com área de clique maior, `onPress`/`onReleaseOutside` no próprio
  controle e atualização durante o arraste. O cálculo só redesenha se a posição
  realmente mudar. A roda do mouse e os comandos existentes continuam disponíveis.

## Distribuição das movimentações

O coletor leve solicita e guarda leituras validadas das ligas enquanto o serviço
principal trabalha. Cada observação carrega sua data real e a identidade do
processo, contexto, clube e carregamento do save. Leituras são comprimidas e
limitadas em memória. A simulação consome essas observações cronologicamente;
uma tabela de dezembro nunca é aplicada como se fosse a tabela de março.

Essa mudança é prospectiva. Não redistribui demissões antigas para preencher
meses vazios e não inventa placares de ligas para as quais o FIFA só publicou
contadores. Observações ainda não processadas pertencem exclusivamente à sessão.

Ajuste de balanceamento: limiar global 23, inclinação 150 pontos-base e teto de
50% por avaliação elegível sob pressão. No Brasil, o multiplicador é 1,3, com
limiar três pontos menor, mínimo padrão de 45 dias/6 jogos; nas outras ligas,
continuam 60 dias/8 jogos. Configurações personalizadas são respeitadas. Limite
anual e proteção do clube do usuário permanecem. Esses valores são parâmetros
da simulação do mod, não taxas estatísticas reais prometidas para cada liga.

## Salvar e descartar

O armazenamento é SQLite, em `server16_manager_market.sqlite3`.

O estado mutável da sessão e os checkpoints concluídos do save são separados.
O recibo nativo de escrita deve corresponder ao arquivo DATA completo, CRC,
hash, clube, data, PID/contexto e estado do mod. Abrir a carreira restaura o
payload desse checkpoint; não escolhe o ramo de data mais recente.

- Salvar e reabrir recupera os vínculos, jogos, títulos e registros anuais daquele
  salvamento.
- Carregar um save anterior descarta as linhas mutáveis da sessão abandonada.
- Encerrar sem salvar não atualiza o checkpoint. Registros temporários restantes
  de encerramento forçado são limpos ao iniciar, em pequenos lotes, preservando
  o estado das outras sessões ativas e checkpoints legados ainda sem payload.
- DATA, INDEX e a base nativa do FIFA permanecem somente para leitura.

Testes cobrem restauração após escrita, escrita seguida imediatamente de leitura,
salvamento de bytes idênticos, salto do calendário, retorno sem salvar, mudança
de PID/contexto, persistência anual e isolamento de outra carreira.

## Prêmio de técnico do mês

A tabela nativa `career_managerawards` foi localizada. A correspondência dos
tipos e a obtenção dos registros da sessão ainda não salva não foram confirmadas
nesta revisão. Nenhuma contagem de prêmio mensal foi inventada a partir de e-mail
ou confundida com títulos de competição. Essa contagem continua pendente.

Backup e relatórios em `code-release/manager_polish_20261102_132212/`.
Instalação local no jogo e no desenvolvimento, sem commit nem push.
