# Mercado de técnicos

No FIFA: **Transferências → M. TÉCNICOS**, em card próprio.
As abas são **Clubes e ligas**, **Movimentações** e **Livres no mercado**.
País e liga usam os dois cards do padrão Ver clubes; a grade apresenta seis
clubes por página. Movimentações reúne contratações e demissões lado a lado,
filtradas pelo mesmo mês, com contagens e paginação independente. As setas
simples mudam o mês e as duplas mudam o ano, dentro do histórico da carreira.
Renovações e elenco inicial não são apresentados como novas contratações.
Clubes e livres usam duas colunas e seis cards por página. Bandeira e nacionalidade aparecem nos
cards, nas movimentações e no perfil; informações desconhecidas são indicadas.
Mouse seleciona os botões; ↑/↓ percorrem opções, ←/→ mudam páginas, Enter/A abre
o perfil, Esc/B volta e os botões de ombro mudam abas. O perfil também tem páginas
para consultar todas as passagens e títulos.

O painel mantém o fundo do jogo, cartões brancos e o destaque `#B9A274`.
A reputação interna 1–10 aparece em cinco estrelas, inclusive meias estrelas.
Os filtros de idade e nacionalidade respondem dentro da tela.

## Dados e limites da primeira versão

- `ModCarrerMode/data/manager_market/catalog.sqlite3` é o catálogo editável.
  Contém pessoas, clubes, vínculo inicial, aliases de IDs e parâmetros padrão.
- `server16_manager_market.sqlite3`, na pasta FIFA16 que contém os slots da
  carreira, guarda contratos, movimentações, resultados, análises, salários,
  indenizações, títulos e checkpoints por save. O banco é separado dos arquivos
  DATA/INDEX e de `fifa_ng_db.db`.
- O catálogo inicial combina o CSV fornecido e os nomes da base instalada. Os
  vínculos legados não são uma confirmação de que o técnico trabalha nesse clube
  na vida real na data atual. Nomes fictícios identificados no perfil cobrem
  clubes sem uma pessoa única; o mesmo técnico não ocupa dois clubes.
- A posse inicial começa em `career_calendar.startdate`, a primeira data do
  calendário da carreira; novas contratações usam a data real do evento. Uma
  migração corrige apenas vínculos iniciais do primeiro pacote. A data inicial
  das estatísticas continua sendo a ativação do mercado. Não são atribuídos
  a um técnico atual resultados de uma passagem passada sem evidência. Cada novo
  jogo guarda IDs do técnico e do contrato que estavam ativos naquele momento.
- A análise cruza todas as partidas detalhadas publicadas, contadores de
  vitórias/empates/derrotas de todas as competições FCE e os resumos globais de
  `leagueteamlinks` da carreira aberta. A DLL publica todas as ligas em RAM
  usando a mesma API de consulta do mercado de jogadores, na thread proprietária
  do FIFA. O auxiliar solicita a leitura com PID, criação do processo, contexto,
  clube e data; publicações de outra sessão ou com mais de 12 segundos são
  rejeitadas. Grupos de uma mesma liga são avaliados separadamente;
  grupos de preparação vazios não escondem grupos ativos. Contadores não viram
  partidas fictícias nem estatísticas de gols sem placares. Se a DLL ainda não
  oferecer a leitura global, o fallback do arquivo mantém explicitamente a data
  gravada; ele não substitui a leitura atual de ligas em RAM.
  Uma liga que o FIFA não simulou não recebe resultados inventados para provocar
  trocas. Promoções, rebaixamentos e clubes novos acompanham os vínculos do save.
- Salários e indenizações dos clubes CPU são valores simulados, em moeda da
  carreira, registrados no banco do mercado. A verba nativa dos clubes CPU não é
  alterada. O salário do técnico controlado pelo jogador continua vindo do FIFA
  e sendo cobrado pelo sistema financeiro existente, uma única vez.
- As trocas atualizam este mercado. A gravação de nomes na tabela nativa
  `manager`/DATA ainda não foi habilitada: não existe uma operação de escrita
  validada para todos os técnicos CPU. Os nomes originais do save e os modelos
  3D ligados a cada clube permanecem sob controle do FIFA.
- Títulos são registrados por temporada, ID de competição, raiz e clube quando
  há vencedor confirmado. Um agregado empatado sem evidência dos pênaltis fica
  pendente, em vez de inventar um campeão.

## Regras da simulação

1. Uma diretoria só avalia demissão depois de **60 dias e oito jogos** do novo
   contrato. As avaliações ficam separadas por pelo menos sete dias e dependem
   de um novo resultado. Essa proteção também vale para um treinador que volta
   a um clube onde já trabalhou.
2. A expectativa de posição deriva da reputação do clube em relação aos demais
   participantes. A pressão combina distância dessa expectativa, pontos por
   jogo, últimos cinco resultados e risco de rebaixamento.
3. Uma eliminação nos últimos 30 dias de copa com prestígio pelo menos 7 aumenta
   a pressão quando o desempenho na liga também está abaixo da expectativa.
   O prestígio inicial deriva dos participantes e das ligas da competição;
   `competition_policies` permite ajustar cada ID no banco da carreira.
4. Acima de 30 pontos de pressão começa uma chance determinística de demissão,
   com 1 ponto percentual por ponto de pressão excedente, limitada por padrão
   a 30% por avaliação. A revisão 3 atualiza os padrões antigos uma única vez,
   preservando parâmetros que já foram personalizados. **O limite absoluto é três demissões
   por clube em cada ano de calendário**, mesmo se o parâmetro SQL for maior.

5. Pedido de demissão tem chance baixa (4 em 10.000 por avaliação elegível).
   Clubes podem buscar um técnico empregado em um projeto de menor reputação
   após 90 dias, com aproveitamento pelo menos 58%, sujeito ao peso de aliciamento.
6. A seleção compara reputação, aproveitamento registrado, nacionalidade e custo.
   Técnicos recém-demitidos ficam 14 dias sem voltar ao mercado automático.
   A vaga aberta é preenchida com candidato elegível e financeiramente compatível;
   sem uma opção acessível, um interino fictício da comissão técnica assume.
   O clube controlado pelo jogador fica excluído de demissões, contratações,
   aposentadorias, aliciamento e renovações automáticas. Essa proteção é aplicada
   também nos pontos centrais de contratação e saída, além da avaliação.
7. O novo clube negocia outro salário, que pode subir ou cair. Renovações podem
   ajustar reputação e remuneração; contratos anteriores mantêm seus valores.
   Um título confirmado também melhora a reputação. Folha e indenizações ficam
   discriminadas em `salary_events`.
8. Há envelhecimento e aposentadoria (80 anos por padrão). Para pessoas sem
   nascimento conhecido, o limite simulado é 35 anos a partir da ativação, sem
   inventar uma idade biográfica. Novos técnicos fictícios surgem conforme o
   mercado precisa preencher vagas e manter uma reserva mínima de 60 livres.
   Isso mantém o sistema utilizável depois de muitas temporadas; os parâmetros
   `retirement_age`, `minimum_free_coaches` e `regens_enabled` são editáveis.

Os pesos são escolhas da simulação, não uma reprodução de contratos reais.
Os técnicos livres conhecidos recebem uma calibração inicial de reputação para
o jogo; os demais começam com uma referência neutra, editável em `coaches`.
A rotatividade foi contextualizada com os relatórios da
[UEFA](https://www.uefa.com/news-media/news/02a9-21aca98834ff-f54c73c29132-1000--the-key-trends-at-the-heart-of-european-club-football/)
e a relação contratual com o material público da
[FIFA sobre treinadores](https://inside.fifa.com/en/legal/news/fifa-steps-up-protection-of-female-players-and-football-coaches).

## Saves e histórico

O auxiliar verifica processo, carreira, clube, data, arquivo carregado e a
publicação nativa dos resultados. Cada gravação completa associa o SHA-256 do
DATA ao estado do mercado. Carregar um hash já conhecido restaura o respectivo
checkpoint antes de continuar; resultados futuros de uma sessão não são
emprestados a um save anterior. Checkpoints compactados evitam uma cópia completa
das tabelas em cada save; as tabelas relacionais da sessão continuam consultáveis.

Gravações manuais e automáticas produzem recibos nativos duráveis em
`runtime/manager_market/save_events/`. Cada recibo identifica processo, contexto,
época, instante monotônico, tamanho e CRC do DATA completo. Uma leitura de
verificação do FIFA não substitui esse recibo. O auxiliar relaciona a gravação
ao último estado SQL confirmado **antes** dela, mesmo quando estava montando a
tela ou quando o jogo foi fechado antes da próxima consulta. A associação é
retomada no próximo início do auxiliar. `session_states` mantém até 128 estados
recentes por sessão; `save_receipts` registra as associações já processadas.
Uma nova gravação explícita atualiza o checkpoint mesmo se os bytes do FIFA não
mudarem; apenas carregar o arquivo nunca regrava o checkpoint. O SQL é confirmado
antes da criação da interface, para uma falha visual não reiniciar o mercado.
Os arquivos DATA/INDEX e a base do FIFA continuam somente para leitura.

`state_ready.json` publica o vínculo da sessão com a `branch` depois do commit
SQL, independentemente da preparação da interface. O resumo do técnico em Ver
clubes usa essa identidade para consultar a passagem atual em modo somente
leitura. Confere também o evento de carregamento/gravação, evitando reutilizar
uma passagem de outra carreira com clube e data coincidentes.

## Confiança da diretoria e perfil completo

A confiança dos técnicos simulados vale `clamp(100 - pressão, 0, 100)`, usando
a pressão da última avaliação do próprio vínculo. A avaliação do antecessor
no dia da contratação é descartada. Sem avaliação própria, a confiança inicial
é 75% e a interface indica “Em avaliação”. Renovações mantêm a passagem; retornos
após uma saída começam outra. O técnico humano usa a confiança registrada pelo
FIFA e continua protegido de movimentações automáticas.

O perfil tem Visão geral, Passagens pelos clubes e Títulos. O modelo cruza os
IDs das nomeações com os resultados e as conquistas do SQL, separa casa/fora,
conserva a duração dos vínculos e mostra os escudos por ID. Títulos incluem o ID
da competição e o clube; a interface usa esse ID para localizar a arte. Dados
anteriores sem registro verificável não são atribuídos ao técnico atual.
A preparação do catálogo e das artes ocorre em lotes limitados de AVM.

O perfil também apresenta Estilo de jogo, com as preferências táticas e o
diagrama da formação cadastrada. A visão geral usa ícones desenhados, fotografia
em proporção preservada, taxas de vitória/empate/derrota, médias de gols e barras
de aproveitamento. A trajetória inclui o vínculo mais recente e até dez partidas
atribuídas ao técnico; seu filtro alterna entre todos os jogos, mandante e
visitante. O direcional ↑/↓ muda esse filtro na visão geral, e o mouse permite
clicar no seletor. As outras abas mantêm a paginação pelas setas horizontais.

Tabelas principais: `coaches`, `clubs`, `appointments`, `movements`, `results`,
`honours`, `reviews`, `competition_policies`, `salary_events`, `market_rules`,
`branches` e `save_checkpoints`. Todas as relações da simulação carregam a chave
`branch`. Uma passagem/contrato tem ID próprio e cada lado da partida aponta
para esse contrato, permitindo separar duas passagens do mesmo técnico no clube.

`performance_evidence` registra os últimos contadores de cada competição/grupo
com data e origem; `appointment_baselines` impede que um recém-contratado herde
os jogos do antecessor. Contadores iguais não provocam outro sorteio, mesmo
depois de mudar o mês. O schema 4 preserva checkpoints anteriores. O diagnóstico
`runtime/manager_market/engine_status.json` informa cobertura, avaliações,
movimentações e confirma ausência de eventos automáticos no clube protegido.

## Ampliar o catálogo

Use um ID estável e exclusivo. Um novo registro no catálogo é importado como
livre na próxima atualização da carreira, sem reescrever contratos existentes:

```sql
INSERT INTO coaches(coach_id,name,nationality,birth_date,reputation,salary,style,image,eligible,fictional)
VALUES('COACH-MEU-0001','Nome do técnico','Brasil','1980-06-15',6,90000,
       'Pressão alta','minifaces/NOTFOUND_DEFAULT.png',1,0);
```

Adicione o PNG transparente com um nome numérico próprio e atualize `image` antes
da primeira importação. Nome, nacionalidade, nascimento, estilo e imagem do
catálogo também podem ser corrigidos em registros existentes; salários e
reputações já evoluídos na carreira são preservados. Técnicos sem foto compartilham um único
`NOTFOUND_DEFAULT.png`. `club_seed` só controla a distribuição em novas carreiras.
Para mudar pesos numa carreira em andamento, edite `market_rules` da respectiva
`branch`; os eventos já registrados não são recalculados. `enabled=0` interrompe
as novas movimentações automáticas e preserva os resultados e contratos.

`country_catalog` relaciona nomes e IDs de bandeiras; `league_catalog` mantém
país, nome localizado e nível. O cruzamento lê a base do FIFA e o catálogo de
Ver clubes, gravando esses metadados apenas no nosso SQLite. `coach_preferences`
permite cadastrar formação e um segundo estilo por ID do técnico, sem inventar
dados biográficos. Formação sem referência aparece como pendente. Nacionalidades
regionais brasileiras são exibidas como Brasil, com a bandeira brasileira.

Não edite pessoas/contratos ativos para simular uma saída manual: termine o
contrato e registre uma nova nomeação com o núcleo, preservando os IDs históricos.
As imagens têm origem no material fornecido e na pesquisa anterior; casos sem
correspondência segura usam o padrão genérico.

## Construção e validação

`import_catalog.py` reconstrói o catálogo de distribuição; **não rode sobre um
catálogo que você já editou manualmente**. `prepare_install.py` lê o save em modo
somente leitura e prepara uma cópia de revisão em `outputs/`. `validate_package.py`
executa o APT gerado e renderiza os estados para conferência. `install.py` guarda
backup e manifesto dos arquivos instalados; `--rollback` restaura o pacote.

Os auxiliares usam o Python já embarcado no Server16, por um processo próprio
iniciado pelo preparador da prévia. O carregamento automático usa a mesma fila
nativa de navegação das telas financeiras, validando processo, clube e data.
Esta revisão requer a DLL com suporte a `ManagerMarket`; depois disso os
auxiliares e o layout continuam carregados por arquivos externos.
Os logs ficam em `ModCarrerMode/runtime/manager_market/`.

A interface carrega as listas em blocos a cada quadro. Não construa arrays de
centenas de itens como um único literal no construtor: a pilha nativa do APT é
limitada, embora o verificador Python comum aceite essa construção. O teste de
inicialização com 2.100 registros impõe o mesmo orçamento conservador de 128
valores das telas financeiras. A assinatura do gerador também faz parte da chave
de cache, para que um pacote antigo não volte após uma correção da interface.

O cache de apresentação em `runtime/manager_market/artwork_cache/` contém apenas
PNG e JSON. A identidade dos arquivos de imagem, arquivos BIG, banco original,
tema e geradores invalida esse cache automaticamente. Contratos, movimentações,
resultados e estatísticas continuam exclusivamente no SQLite da carreira. A
chave do pacote APT também considera a revisão das imagens. Os registros
`published` incluem tempos separados de leitura/motor, modelo e construção.

O mercado usa compressão DEFLATE nível 1 no mesmo contêiner nativo; as outras
telas mantêm o nível padrão. O ajuste de texto compartilha fontes por tamanho.
O APT processa dois blocos limitados por quadro, mantendo a pilha conservadora
de 128 valores. Todas as imagens DXT recebem preenchimento transparente até
múltiplos de quatro pixels: dimensões como 202×202 ou 318×52 são rejeitadas pelo
carregador Direct3D do jogo sem esse cuidado. Os ícones são preparados em
resolução superior à apresentação. As cores dos cantos das faces vêm dos RGBs
do clube na base FIFA, em leitura; as minifaces originais não são modificadas.
As abas selecionadas usam dourado e texto escuro. O retorno é feito pelo ESC
ou botão de voltar do controle, sem duplicar botões dentro do painel.

### Revisão local de 30/10/2026

As contratações comparam a reputação do clube e do antecessor, o desempenho
real nos dez jogos mais recentes de cada candidato, o salário e a situação de
mercado. Há uma pequena preferência pela nacionalidade do antecessor e pelo
país do clube; traduções e dupla nacionalidade são normalizadas. Técnicos
livres recebem uma vantagem sobre uma contratação de outro clube de qualidade
equivalente. A escolha ponderada entre os candidatos próximos mantém variação
determinística por carreira. Clubes de elite usam faixa de qualidade mais
exigente; em 10% das seleções podem considerar uma faixa um ponto mais baixa.
Falta de candidatos acessíveis pode resultar em um interino, sem duplicar um
técnico já empregado. O técnico controlado pelo jogador permanece protegido.

A simulação roda no auxiliar, acompanhando o calendário mesmo com a tela
fechada. A montagem do APT agora roda em uma tarefa separada da simulação.
Uma atualização da mesma carreira/data mantém o painel validado disponível;
carreira, carregamento de save, clube ou data diferentes exigem validação nova.
Um APT só vira cache publicável depois da validação completa.

A abertura instancia os dados compactos das listas; históricos e títulos são
instanciados somente quando o respectivo perfil é aberto. As imagens de catálogo
ficam em grupos de até 512 controles, evitando estourar o quadro APT com mais
de dez mil imagens. O cache DDS reutiliza as texturas já codificadas e valida
cabeçalho, dimensões e tamanho antes de usá-las. Dados e estatísticas continuam
separados desse cache de apresentação.

O template visual compilado também é reutilizado: geometria, fotos, escudos,
bandeiras e cartões não são reconstruídos quando apenas os dados da carreira
mudam. O controlador recebe a data, os vínculos e as estatísticas atuais. O
template é invalidado por mudança de código, tema, fotos ou conjuntos de
imagens, e tem sua integridade conferida antes de reutilizar. Uma falha de cache
provoca reconstrução validada, sem publicar um arquivo incompleto.

O plano para refletir contratações nos modelos de beira do campo está em
[SIDELINE_MODELS.md](SIDELINE_MODELS.md).

### Catálogo ampliado e limite do pacote

Os retratos usados pelo APT são limitados a 204 pixels, acima dos 202 pixels
da maior apresentação. As minifaces originais permanecem intactas. A leitura
dos retratos distintos usa quatro tarefas; a simulação e o SQLite conservam
um único responsável. Isso mantém o pacote completo abaixo do limite de
128 MiB do carregador, sem relaxar a proteção de memória. Templates e DDS
validados continuam reutilizados. A primeira preparação de um catálogo novo
é mais lenta e acontece em segundo plano; a tela pronta é reutilizada.
