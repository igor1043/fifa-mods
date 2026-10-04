# FIFA 16 Mods

Pacote de modificações e ajustes para o FIFA 16, com foco no modo carreira.
Este README na raiz é a documentação central do repositório.

## Versão aprovada — integração New Screens

A branch `integracao-new-screens` registra o conjunto de mods instalado em
`U:\fifa 16` e aprovado pelo usuário em **04/10/2026**, após reinstalar a base
funcional do jogo. As telas personalizadas estão habilitadas em
`ModCarrerMode/config/ranking_overlay.ini` (`enabled=1`), junto dos quatro
plugins listados abaixo. A aprovação se refere a esse conjunto e aos fluxos
testados; não elimina as limitações de recursos e compatibilidade descritas
neste README.

Binários, configurações, assets, traduções e fontes necessários acompanham
esta versão. Logs, resultados de compilação, backups e dados privados da
carreira ficam fora da publicação.

A estrutura foi reorganizada por função. Comece pelo [guia da pasta do mod](ModCarrerMode/README.md) e pelo [mapa de telas, poses e cenas 3D](ModCarrerMode/source/career_native/README.md). A compilação atualiza somente o Dev; instalar no jogo é uma ação separada, feita apenas quando solicitada.

## Instalação

Instale somente os arquivos de execução, preservando a estrutura de pastas.
Não copie `source`, `tools`, `backups`, logs ou documentação para a instalação
do jogo. Antes de substituir arquivos, faça uma cópia externa em
`J:\mods\backup`; não guarde backups de tentativa dentro da pasta do FIFA.

O ponto de entrada é `dinput8.dll` na raiz do jogo. Ela incorpora o núcleo do
Career Mode e materializa `dinput8_l9_chain.dll` no primeiro uso. O arquivo
`dinput8_career_chain.dll` é mantido no repositório para recuperação e não
participa da cadeia ativa.

## Recursos do Career Mode

A DLL nativa reúne os recursos já implementados neste pacote, incluindo:

- cards e estatísticas de Meu Time, com mensagem de ausência somente em cards
  realmente vazios;
- separação dos dados de Liga e Copa na aba Competição;
- ranking mundial de clubes;
- card Próxima partida com data/hora, estádio, imagem, capacidade e público
  estimado quando os dados estão disponíveis;
- início da seleção de idioma com a bandeira do Brasil;
- fluxo de aposentadoria por idade, com alteração restrita ao banco necessário,
  validação de CRC/estrutura e restauração do arquivo se a validação falhar.

Os layouts e assets de interface ficam em `data/ui`; as bases de localização
ficam em `data/loc`. As imagens de reputação usam os IDs de liga 9900–9905,
com DDS em `data/ui/imgAssets/league/dark` e `league/light`.

## Teste: Clube / elenco 3D

Na branch `integracao-new-screens`, selecionar o card **Clube** na aba
**Meu Time** (item principal Clube ou estatísticas por competição) abre uma tela própria do
mod: titulares e reservas da carreira, prévia 3D dos 11 ou individual e 34 atributos,
incluindo potencial, além de posição, idade, altura, peso e geral.

A ficha individual usa fundo claro e sóbrio nas cores nativas do clube,
escudo e modelo 3D grande, com enquadramento de retrato/corpo inteiro.
O campinho mostra `players.preferredposition1..4`: círculo cheio na posição
principal e anéis nas secundárias, sem confundir isso com a escalação tática.
Dados ausentes permanecem como `-`; posições repetidas ou inválidas não são
desenhadas. A identidade acompanha qualquer clube, inclusive clubes cujo kit
principal é branco/preto e a cor característica vem das cores secundárias.
Abas organizam os 34 atributos. Os seis números de resumo do atleta de linha
são médias simples dos atributos indicadas na tela, não avaliações oficiais
inventadas; geral/potencial vêm diretamente do FIFA. Goleiros têm resumo
próprio com seus atributos reais. Tudo permanece somente leitura.

A prévia lê malhas/texturas RX3 reais, primeiro os arquivos soltos em
`data/sceneassets`, depois os pacotes BIG do jogo. Não depende de Blender ou de
outro programa. Cabeça, cabelo, olhos e pele têm associações próprias;
`playerskin_<ID>_textures.rx3` preserva as tatuagens existentes do jogador.
O goleiro é identificado pela posição da carreira, usa kit tipo 2 e luvas
RX3 com `gkglove_cm`, preferindo atribuições específicas do atleta/clube.
Nunca usa silenciosamente o kit de linha se o kit de goleiro estiver ausente.
A altura acompanha a carreira; o enquadramento inclui todas as mechas.
Camisa por dentro/fora, ajuste, mangas e altura das meias acompanham os códigos
individuais em `players`. As variantes de manga usam a receita nativa para
malhas de braços e peças térmicas; fallback de malha fica registrado no log.
Golas usam `teamkits.jerseycollargeometrytype` da base instalada, por clube e
tipo de kit (0 linha / 2 goleiro), com precedência das atribuições literais
`assignKitDetails` do `team_<ID>.lua`. A prévia carrega a malha `jersey_0_<gola>_...`;
não fixa mais gola 0 para todos os clubes. Não executa Lua arbitrário nem
resolve ainda variantes de torneio/ano sem contexto; fallback é registrado.
Recursos específicos ausentes usam fallback e a cabeça genérica é indicada
na tela. Não são inventadas tatuagens que não existam nos assets.

O elenco aparece por posição de campo, com titulares primeiro e banco/demais
reservas abaixo; cada linha tem retrato 2D, escudo, posição, nome e geral.
Retratos vêm de `data/ui/imgAssets/heads/p<ID>.dds`, soltos antes dos BIG de
heads (incluindo DDS comprimido com chunkzip/RefPack). Ausentes usam silhueta
neutra, nunca a foto de outro atleta. Não existem checkboxes ou seleção manual
da composição. Cima/baixo/analógico esquerdo selecionam uma linha.
Quando existem nome associado e modelo específico instalado, a seção
**Comissão técnica** acrescenta o treinador após os jogadores. O nome vem de
`ModCarrerMode/data/catalogs/club_manager_fallback.tsv`; a prévia usa
`data/sceneassets/slc/specificmanager_<clube>_0_0.rx3` e o pacote `_textures.rx3`
do mod de beira de campo. Sem essa associação, a linha fica oculta.
Clique/A/Enter abrem a ficha 3D do técnico, com rotação, zoom e B/Esc para voltar.
Ele não entra nos 11, não recebe atributos de atleta nem o esqueleto/poses dos
jogadores. Usa as 31 matrizes do próprio SLC nas seis poses de técnico:
natural, braços cruzados, mãos nas costas, orientação tática e duas sentado
(mãos apoiadas na mesa ou gesticulando). Não há ossos independentes dos dedos
nesse rig, portanto essas mãos ainda não reproduzem todos os detalhes das fotos.
X/P ou o seletor alternam essas poses. Rig não reconhecido mantém o modelo
estático original; nunca recebe um esqueleto de jogador emprestado.
O nome/modelo seguem os arquivos instalados, não o avatar de técnico criado no save.
Na equipe, LB/RB ou Q/E mudam a pose coletiva. Clique no nome, A ou Enter abrem a ficha individual,
somente leitura. A foto coletiva não gira: LT/RT ou roda do mouse dão zoom,
analógico direito ou arraste deslocam o enquadramento. R/clique no analógico
direito restauram a câmera. No jogador individual, arraste/analógico direito
giram o modelo; LB/RB ou Q/E mudam páginas, LT/RT percorrem atributos,
X/P muda a pose e Y/F alterna retrato/corpo inteiro. B/Esc volta à equipe;
um novo B/Esc na equipe fecha o mod. O host mantém input exclusivo durante
a navegação interna e proteção de 250 ms ao devolver o foco ao FIFA.
O Hub não navega para outra tela nativa.

Estado: **experimental; testes offline aprovados e conjunto validado pelo usuário no FIFA**.
Renderiza os 11 em sete poses criadas pelo mod: foto mista, mãos nos joelhos,
grupo agachado/unido, um joelho no gramado, fila em pé com mãos nas costas,
duas fileiras compactas e fila em pé de braços cruzados.
A câmera coletiva usa lente de 22 graus e fileiras próximas nas poses de duas filas,
reduzindo a diferença aparente de tamanho entre frente e fundo.
Varia mãos próximas aos joelhos
e braços apoiados nas costas dos vizinhos, sem mãos sobre ombros ou nuca. Ordena
os jogadores de linha por altura, deixando os mais baixos na frente e os
mais altos atrás; um goleiro fica numa ponta, dois ficam nas duas pontas.
A pose deforma os modelos pelo esqueleto nativo de 400 ossos e até oito pesos
por vértice, mantendo roupa, cabelo e luvas associados. O refinamento do apoio
nos joelhos afeta somente a primeira fileira: cotovelo com flexão mínima suave,
pronação no antebraço e dedos relaxados, conforme os comprimentos do rig.
Na pose 1, goleiros e demais atletas em pé mantêm sua pose. As variantes 2–4
têm receitas próprias. A pose 4 usa cotovelos baixos junto ao corpo, antebraços
cruzados em profundidades diferentes e mãos apoiadas no braço oposto, sem
alterar a primeira fileira. As doze poses individuais são postura natural,
mãos nas costas, uma mão na cintura, braços cruzados, joinha, duas mãos na
cintura, braços cruzados de perfil, saudação, aceno, mãos à frente, indicadores
levantados e mão sobre o escudo. Usam postura em três quartos, flexão
suave dos joelhos, dedos relaxados e rotação distribuída nos ossos auxiliares
do antebraço, conforme o esqueleto e a altura do jogador.
São aproximações das referências, não cópias exatas ou animações da EA.
O catálogo separa IDs 1–7 da equipe, 101–112 individuais e 201–206 de técnico,
permitindo acrescentar receitas sem alterar a tela ou criar hooks de navegação.
Não é uma animação
original reproduzida pelo FIFA, nem usa Blender ou modelos externos.
O seletor **Ambiente** na equipe (X no controle / V no teclado) permite testar
uma sala de coletiva e um vestiário branco, com cores e emblema do clube atual.
Na coletiva, o modelo do técnico associado ao clube fica sentado à mesa, com
microfone, garrafa e bloco de notas. LB/RB ou Q/E alternam suas duas poses
sentadas sem mudar a pose da equipe. Sem técnico/rig compatível, a cadeira fica
vazia; não se usa o treinador de outro clube.
O vestiário tem 11 lugares, cabides, bancos, toalhas, bolsas, garrafas e as
camisas/chuteiras RX3 dos titulares, incluindo o kit de goleiro. São protótipos
estáticos, sem entrevista interativa, animação ou edição da carreira.
Superfícies repetidas são agrupadas por material;
câmera e luz próprias das salas não alteram a foto dos jogadores.
Abrir Clube pede uma atualização do elenco ao provider já existente, fora
da thread gráfica. O log registra os IDs dos 11 e não perde a formação por
truncamento de um único bloco de diagnóstico.
Tem gramado procedural largo, parede ao fundo com faixas nas cores do clube
(`teams.teamcolor1r/g/b`, 2 e 3) e escudo DDS pelo ID em
`data/ui/imgAssets/crest/light/l<ID>.dds` ou `dark` (arquivos soltos/BIG).
Na ausência de escudo, não exibe um de outro time; cores ausentes usam painel
neutro. Troca de clube atualiza o elenco e invalida os modelos anteriores.
Preserva normais das malhas, usa luz direcional e sombras offscreen próprias,
inclusive entre jogadores. As mechas transparentes são ordenadas pela câmera;
o log lista todos os submeshes, vértices e triângulos de cabelo carregados.
Quando disponível, `hair_coeff` do mesmo pacote de `hair_cm` fornece cobertura
pelo canal vermelho, com núcleo opaco e bordas transparentes em todos os
submeshes (inclusive arquivos com só uma parte). Só na ausência desse mapa
usa o alfa difuso, normalizando faixa muito baixa. As texturas não são regravadas.
Braçadeira usa variante nativa de camisa quando `teams.captainid` identifica
o atleta; ainda não confirma o capitão de uma escalação personalizada ativa.
Chuteiras seguem tipo/desenho individual e priorizam assets `playershoe`
compatíveis com atleta/clube; fallback fica registrado. Overrides Lua de
chuteira, máscaras de recoloração e variantes de torneio não são completos.
Não reproduz ainda todos os morphs, composição de rostos genéricos, iluminação,
decalques e shaders nativos. A captura usa `teamplayerlinks.position`: 0–27 são
posições de campo, 28 banco e 29 demais reservas. Só monta a foto com exatamente
11 posições de campo e um goleiro; fonte incompleta/ambígua não inventa um XI.
Se faltar um modelo ou um rig necessário à pose, não publica uma foto parcial
como “11 titulares”: informa a indisponibilidade e mantém a lista/fichas.
Também rejeita modelos duplicados, de outro clube ou receitas incompatíveis.
Na base offline, esses IDs coincidem com `default_teamsheets` do Flamengo.
Ainda é necessário conferir no FIFA se uma escalação personalizada da carreira
é refletida nessa fonte. Não se consulta `teamsheets` não validado no Hub.
É somente leitura: não altera o banco da carreira nem o save.

Os testes `test_club_player_3d.cmd` e `test_club_player_screen.cmd`, em
`ModCarrerMode/source/career_native`, verificam assets reais, entradas inválidas,
renderização offscreen e troca/fechamento da tela. Os valores 80 e os nomes de
exemplo do teste visual são fixtures exclusivas do executável de teste;
não entram na DLL do jogo. Diagnóstico: linhas `Club3D` em
`ModCarrerMode/career_ranking_overlay.log`.

Backup anterior a esse teste: `J:\mods\backup\Club3D-20261001`.
Backup da prévia estática, antes da pose: `J:\mods\backup\Club3D-Pose-20261001`.
Backup antes dos ajustes de abraço/luz/cenário:
`J:\mods\backup\Club3D-PhotoPose-20261001_165029`.
Backup da DLL anterior à ampliação do catálogo e às salas:
`J:\mods\backup\Club3D-RosterRefresh-20261001\game-dinput8-before.dll`.

Referências visuais para as variantes (somente estudo; nenhuma foto externa
é instalada como textura): [Real Madrid](https://www.managingmadrid.com/2015/9/25/9396787/real-madrid-vs-malaga-liga-2015-16-preview),
[Liverpool](https://www.liverpoolfc.com/news/first-team/455973-match-report-ajax-champions-league)
e [Sharjah](https://www.emaratalyoum.com/sports/local/2021-07-03-1.1509779).
As novas poses individuais usam também o [media day do Manchester City](https://www.mancity.com/news/mens/media-day-gallery-63795826).
A coletiva e o vestiário foram estudados nas referências oficiais do
[Real Madrid — coletiva](https://www.realmadrid.com/en-US/news/football/first-team/press-conference/xabi-alonso-07-12-2025)
e [loja do clube — ambiente de vestiário](https://shop.realmadrid.com/pt-pt/collections/jerseys-kits-home-womens).
Essas fotos são referências de composição, não texturas instaladas no jogo.

## Plugins habilitados nesta branch

A lista efetiva está em `ModCarrerMode/mods/enabled.txt`:

- `crowd/crowd_plugin.dll` — ajuste do fator de público;
- `career_birthdate_2006/birthyear_range_2006_2012.dll` — faixa de ano no
  Player Career. A confirmação de persistência deve ser feita no jogo e após
  recarregar a carreira;
- `bench_native12/bench_native12.dll` — prepara até 12 reservas reais na
  carga da partida, preservando os limites de substituições permitidas.
  A versão 3 protege as filas nativas de recursos; o usuário relatou sucesso
  na instalação alternativa. A cobertura de todos os cenários ainda requer
  confirmação no jogo;
- `substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll`
  — localiza o par de regras da partida e grava o limite de sete trocas nos
  dois campos `A78C`. Não altera os contadores `B03C`; ainda é necessário
  confirmar da quarta à sétima substituição numa partida nova.

O plugin legado `bench12_global_limit_12_v2/global_limit_12_v2.dll` está
**desativado**. Ele sobrescreve a versão do interpretador APT em
`fifa16.exe + 0x34A0D68`, não a quantidade de reservas, e não faz parte da
expansão nativa do banco. Não reativar esse patch junto ao mod de reservas.

O `retirement_offline_worker.exe` permanece para compatibilidade com o fluxo
legado, controlado por `ModCarrerMode/config/career_retirement_background.ini`.
Os novos cards de aposentadoria e empréstimo usam `career_operations_worker.exe`.
O plugin
`easfc_hide_plugin.dll` não está habilitado.

## L9.65 e logs

`dinput8_L9.ini` configura os patches L9.65 incorporados à DLL de entrada.
As opções `ScoutOhneLiga`, `Namensweiche` e `Poolwache` permanecem desligadas
(`0`). O recurso L9 importado tem SHA-256
`B6583FC60B5058215B12E90E49E5F1D2A0B5069AA909EAB9B916621AD77AC6E2`.
`winmm.dll` é o CompData Patcher e deve permanecer na raiz; seu SHA-256 é
`B43513DDEAB5F9F0904EB76E4CB543596CA35B1AAAE3C60CE7993061B7AC1A0E`.

Os principais logs são `dinput8_L9.log`, `compdata_patcher.log` e os arquivos
específicos em `ModCarrerMode/logs`. O modo de diagnóstico fica em
`ModCarrerMode/config/career_native_mode.ini`: `production`, `development` ou `trace`.
Feche e reabra o FIFA para a DLL reler essa configuração.

## Aposentadoria e segurança do save

### Tela nova e operações financeiras (experimental)

O card de aposentadoria abre uma lista própria: time inteiro, todos os jogadores
ou seleção individual com pesquisa e checkboxes. Redefinir a idade é opcional.
Funciona com mouse/teclado e controle: LB/RB muda o escopo, A marca, X alterna a
idade, LT/RT ajusta, Y abre o teclado de pesquisa e Menu/Start revisa a operação.
A confirmação é explícita. Salve a carreira depois de confirmar, feche o FIFA
completamente e aguarde o worker antes de reabrir. Este primeiro teste exige
fechar o jogo; apenas sair da carreira não executa a gravação.

O carrossel de pedido de fundos, no Escritório, acrescenta **Pedir empréstimo**
sem substituir o pedido de fundos nativo. Planos provisórios e fictícios:
6/12/24 parcelas mensais com juros totais fixos de 5/10/20%, respectivamente.
Valores são unidades integrais nativas do orçamento de transferências do save;
o orçamento de salários não é alterado. Datas de vencimento seguem o calendário
da carreira, não o relógio do computador. Há um contrato por slot nesta versão.
As cobranças vencidas são processadas após salvar e fechar o FIFA; sem saldo
suficiente, ficam pendentes e não deixam o orçamento negativo.

O novo worker valida clube/treinador/estrutura/CRCs, altera somente os bits
permitidos, prepara diário de transação e substitui DATA atomicamente.
INDEX não é editado. Contrato e solicitações ficam em
`ModCarrerMode/runtime/operations` (privado, ignorado pelo Git); preserve essa
pasta junto com a carreira. Não renomeie/clone o slot para tentar migrar um
contrato. Recuos do calendário ou restaurações detectadas interrompem a cobrança
para reconciliação. Backups ficam exclusivamente em
`J:\mods\backup\CareerOperations`, incluindo DATA e INDEX anteriores.
Testes de crédito/débito e recuperação usaram cópias isoladas, não o save original.

### Próxima partida, coletiva e sala de troféus (experimental)

Selecionar **Próxima partida** na Central abre uma tela própria, sem navegar
para outra tela nativa. As visões **Foto dos 11**, **Escalações prováveis** e
**Técnicos 3D** usam os dois IDs da próxima partida e os elencos vivos do FIFA.
Só monta uma foto quando há exatamente 11 posições de campo válidas e um goleiro;
não completa com jogadores mais bem avaliados nem com dados de outro clube.
O nome da formação vem de `teamformationteamstylelinks`/`formations` quando
inequívoco; caso contrário, indica uma estimativa pelos grupos de posições.
São escalações disponíveis, não uma promessa do onze escolhido pela IA no jogo.
LB/RB ou Q/E muda a visão; LT/RT/roda ajusta zoom; analógico direito/arraste
move a foto ou gira o técnico; B/Esc fecha com o bloqueio de input compartilhado.

A imagem dessa nova tela é lida diretamente de
`StadiumGBD/render/thumbnail/stadium/<nome>.png`, `.jpg`, `.jpeg` ou `.dds`, nessa
ordem. PNG/JPG são decodificados em memória pelo Windows, sem gerar DDS ou copiar
arquivos. A chave vem da atribuição de competição/mandante no FSW, ou do fallback
de estádio do clube quando não existe atribuição. Sem correspondência, a imagem
fica oculta. Quando há vários estádios possíveis, a tela explica que a primeira
imagem é representativa e não inventa capacidade para o local ainda indefinido.
Essa leitura direta pertence ao overlay; o card nativo antigo mantém seu caminho.

**Sala de coletiva**, no carrossel Clube, abre técnico e um jogador sorteado do
elenco daquele clube, inclusive reservas. Há dois microfones, mesa, cadeiras e
painel com escudo/cores. A escolha permanece durante a sessão; **N/L3** ou o
botão sorteia outro sem repetir imediatamente quando há alternativas.
LB/RB alterna duas poses sentadas. Atleta e técnico usam seus próprios rigs.
Técnico ausente é informado; não é substituído pelo técnico de outro clube.
A cena também está disponível no seletor de ambientes da tela Clube.

O item **Sala de troféus** abre vestiário com modelos RX3 de taças identificadas
no histórico da carreira, 30 por página. Ainda não identifica com segurança
todas as copas domésticas/continentais; conquistas sem associação segura são
informadas, não substituídas por troféus genéricos. Prévia offline de taças usa
contagens de teste explicitamente identificadas, não conquistas reais do save.
O pedido de transferência com geração de oferta/e-mail nativo ainda está em
estudo e não está conectado: `career_transferoffer` é transferência de jogador,
não contrato de emprego do treinador. Nenhuma proposta fictícia é injetada.

As novas telas foram compiladas e verificadas offline; o conjunto instalado foi
aprovado pelo usuário no FIFA em 04/10/2026. A cobertura de outros builds, saves
e cenários continua dependente de validação. Nenhum push é automático.

### Fluxo legado

O worker só atua após uma solicitação explícita armada por um dos fluxos
exclusivos de aposentadoria no Career Hub. Ele aguarda o FIFA liberar o par
`DATA`/`INDEX`, faz cópias de segurança, modifica somente o `DATA`, recalcula
os CRCs e valida novamente o container e a tabela `CZUM`. Se a validação
falhar, restaura automaticamente o `DATA` original. Arquivos auxiliares
pequenos não são tratados como o banco da carreira.

Os modos são `remove_retirement` (limpa `isretiring`, sem alterar idade) e
`remove_and_rejuvenate` (limpa `isretiring` e ajusta a idade, preservando mês
e dia). O worker não varre nem modifica saves sem solicitação pendente. Não
teste esse fluxo com a única cópia de um save importante.

## L9, nascimento e substituições: observações de validação

- O L9 escreve `dinput8_L9.log`; confira a aplicação dos patches críticos e
  não prossiga se aparecer `NICHT weiterspielen`.
- A DLL de nascimento e seus RVAs dependem do executável/build identificado.
  Nesta branch, confirme no jogo e recarregue a carreira para validar que o
  ano escolhido foi realmente salvo.
- A DLL de sete substituições não usa endereço absoluto de heap e rearma após
  os contadores reiniciarem ou o par de regras ficar inativo. Log de carga ou
  escrita, por si só, não comprova o funcionamento durante a partida.

## Traduções e arquivos de desenvolvimento

Os textos efetivamente carregados pelo FIFA estão nas bases `data/loc/*.db`.
O gravador em `ModCarrerMode/source/localization` preserva UTF-8 e limita os
códigos Huffman a 16 bits, evitando que caracteres especiais se corrompam ao
salvar os bancos no editor. XMLs e traduções existentes são preservados.
Não converter os `.db` para ANSI/UTF-8 como arquivos de texto: são bancos
binários. Antes de instalar novas traduções, validar todas as linhas e dois
ciclos de abertura/gravação com `probe_loc_roundtrip.py`.
Código-fonte, scripts de build e testes ficam em `ModCarrerMode/source` e não
são necessários para a execução do jogo.
