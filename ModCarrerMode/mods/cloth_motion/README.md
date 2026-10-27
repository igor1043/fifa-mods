# Cloth Motion para FIFA 16 — experimental 0.8.2

Simulação própria de partículas XPBD para as camisas e os calções do FIFA 16.
O jogo fornece a pose e as malhas físicas, transfere a deformação para os modelos
visíveis e reconstrói suas normais. A DLL e o shader do PES são referências de
comportamento; nenhum deles é carregado, copiado ou modificado por este módulo.

## Alterações da 0.8.2

A física vem **desativada por padrão** (`enabled=0`). O usuário pode ativar no
Server16, nos painéis de F12 ou por F6; a escolha fica salva nas próximas
aberturas. Configuração ausente ou sem uma escolha válida começa desligada.
Esta instalação também desativa a opção já existente, conforme solicitado.
Atualizações posteriores preservam a escolha salva; `--reset-disabled` permite
um reset explícito durante a instalação.

A elevação gradual da barra do calção passa de 12 para 15 mm: são até **3 mm
adicionais**, seguindo a direção animada de cada perna. Cintura e pontos presos
mantêm a posição; os demais parâmetros do calção e da camisa continuam iguais.
O teste das duas malhas de calção mede esse deslocamento em três poses e verifica
os pontos presos e a atualização do cache. As comparações do solver antigo usam
a mesma elevação para separar o ajuste de corte do comportamento da física.

## Alterações da 0.8

A atualização 0.8.1 integra o controle ao layout do Server16: no pré-jogo,
**Configurações da partida > Física de roupas** salva junto de **Aplicar**;
durante a partida, o painel de **F12 > Ajustes da partida** tem uma opção que
aplica imediatamente. Camisa e calção são controlados juntos. O módulo lê a
opção a cada 250 ms fora da thread de simulação e publica confirmação da sessão.
O painel confirma a mudança ou informa que não recebeu resposta da versão
carregada. Depois de instalar esta atualização, reinicie FIFA e Server uma vez.

Desativar seleciona o solver original. A pequena ponte de controle continua
na lista de carregamento para permitir reativação durante a mesma sessão;
a simulação XPBD não roda quando está desligada. F6 também persiste a escolha.
A 0.8.1 manteve a física e os parâmetros numéricos da 0.8.

A barra ganha uma proteção local de curvatura baseada nos vizinhos estruturais
da própria malha. Dobras amplas continuam livres; quando um arco de dois
segmentos se fecha demais, a correção se distribui pelos três pontos, respeitando
os pontos presos. A relação mínima entre corda e arco é 0,82, com correções de
até 4 mm por ponto e subpasso. Isso reduz vincos muito fechados sem aumentar
a largura ou o comprimento da camisa.

Há separação de 4 mm entre partículas não vizinhas da região inferior da camisa.
Uma tabela espacial restringe a busca às células próximas. Vizinhos até dois
passos da malha e costuras coincidentes na referência são excluídos. É uma
autocolisão local de partículas: ainda não cobre todos os triângulos, segmentos
e atravessamentos rápidos da roupa. As correções acompanham o histórico de
posição para não acrescentar um impulso artificial ao quadro seguinte.

O contato final com o calção tem um refinamento quando os planos próximos
alternam entre si numa dobra. Após as três correções usuais, ele pode avançar
na direção externa da camisa, sem desfazer os planos já atendidos. As passagens
adicionais só acontecem se ainda houver penetração. A margem continua em 6 mm.

Os limites das cápsulas são preparados uma vez por passagem. No calção, códigos
de seis lados por vértice descartam segmentos que estão totalmente fora do
volume; os códigos são atualizados imediatamente quando um extremo se move.
Essa seleção mantém os mesmos testes e a mesma ordem dos contatos aceitos.
O perfil do calção aprovado na 0.5 e o tamanho da camisa da 0.7 são preservados.

O novo teste compara a 0.7 arquivada com esta revisão no cálculo completo do
par, incluindo pernas, braços e publicação da superfície de contato. Há oito
cenários de mangas curtas/longas, masculino/feminino, com e sem compressão da
barra e intervalos de 47/59/60/61/70/120 quadros/s. O tempo local não representa
FPS da partida. O log passa a amostrar uma chamada completa a cada 64 por peça,
com médias separadas para camisa e calção, permitindo avaliar o custo no jogo.

## Base mantida da 0.7

A parte livre da camisa recebe uma redução proporcional de 1% ao redor do
encaixe dos ombros, acompanhando a pose. A transição junto dos pontos presos
é gradual; gola e punhos presos não são deslocados. A redução alcança tronco,
largura e comprimento, levantando a barra alguns milímetros sem cortar só a
parte inferior. O ajuste anterior de 3 mm no tronco permanece.

A estabilização do peito passa a abranger os dois lados da região frontal.
O volume adicional cai de 3 para 1 mm. A ancoragem local fica mais forte e a
folga normal é reduzida no peito, enquanto a barra conserva sua liberdade.
`jersey_size_reduction=0.010` controla a redução proporcional;
`jersey_chest_max_offset_m=0.022` limita a amplitude local, com transição gradual.
Esses números não significam que toda a região se desloca por essa distância.

O contato camisa/calção usa agora normais estimadas da superfície simulada do
calção e uma margem de 6 mm. A posição do plano considera o apoio das amostras,
evitando que a média fique para dentro de uma região convexa. Segmentos
estruturais da barra maiores que 3 cm também recebem uma correção no meio;
depois são conferidos novamente os pontos que se moveram. O perfil físico do
calção permanece o mesmo; a nova superfície serve apenas ao contato da camisa.

Para as superfícies pequenas do jogo, a busca filtra quatro amostras de cada
vez com SIMD/SSE. Superfícies com mais de 256 amostras usam uma árvore k-d;
ambos os caminhos selecionam os mesmos quatro vizinhos da busca completa,
incluindo os critérios de orientação e desempate. Os testes comparam os planos
resultantes, as consultas próximas e distantes e os dois tamanhos de superfície.
Ancoragens e resistências estáticas também são reutilizadas, com invalidação
quando a peça ou sua configuração muda. Nas mangas, uma passagem extra é
reservada para correções maiores.

O benchmark local compara o mesmo cálculo com a busca otimizada e a completa.
Ele não mede o FPS da partida. O contato mais completo acrescenta trabalho;
um ganho nessa busca não equivale ao mesmo ganho no tempo total da simulação.

| Item | 0.6 | 0.7 |
|---|---|---|
| Tamanho da parte livre da camisa | Ajuste local de 3 mm | Mesmo ajuste e redução proporcional de 1% |
| Volume adicional no peito | Até 3 mm | Até 1 mm |
| Região estabilizada | Máscara central | Ambos os lados do peito |
| Contato com o calção | Vértices e normais da pose | Normais deformadas e verificação de segmentos maiores |
| Busca de contato | Percorre as amostras | SIMD ou árvore k-d |
| Calção e resolução das malhas | Perfil aprovado | Preservados |

## Base mantida da 0.6

O perfil do calção da 0.5 é preservado. O teste comparativo executa o solver
arquivado da 0.5 e o atual sobre os mesmos calções, poses e volumes de pernas,
a 30, 60 e 120 quadros/s, verificando posições e velocidades.

A camisa recebe um ajuste gradual de até 3 mm para dentro no tronco e na
cintura, sem estreitar isoladamente a barra. O volume adicional central do
peito cai de 7 para 3 mm. A região central recebe ancoragem e amortecimento
mais fortes, menor limite de deslocamento e menos espaço para dobras para
dentro. A barra conserva sua liberdade e ganha menor resistência local à
dobra. As mudanças são graduais para não criar uma linha de transição rígida.

A colisão com volumes do corpo passa a ser aplicada também às mangas. Camisas
com volumes nativos de braço usam esses volumes animados; as mangas longas,
cujas definições frequentemente não têm esses volumes, recebem aproximações
por segmentos entre seções da manga de referência animada. Essas aproximações
não usam o tecido já simulado, evitando crescimento por realimentação. São uma
aproximação do braço, não uma leitura dos triângulos da pele. A margem é de
4 mm, e o limite local da manga permite só 1 mm para dentro da referência.
Pontos presos continuam presos; vértices e segmentos estruturais livres recebem contato.

O contato final da camisa com o calção admite uma terceira correção e para
assim que o ponto já está fora, para reduzir o pequeno resíduo entre as peças.
O log separa `arm_solves`, `arm_contacts` e `arm_edge_contacts` dos contatos
de pernas. Os testes de mangas incluem braços animados e penetrações provocadas
nas 16 camisas, de mangas curtas e longas, masculinas e femininas.

| Item | 0.5 | 0.6 |
|---|---|---|
| Volume adicional no centro do peito | Até 7 mm | Até 3 mm |
| Ajuste de tronco e cintura | Sem redução adicional | Até 3 mm por superfície |
| Movimento central do peito | Liberdade geral da camisa | Estabilização localizada |
| Contato das mangas | Apenas limite da referência animada | Volumes nativos e aproximações nas mangas longas |
| Calção | Perfil aprovado da 0.5 | Mesmo perfil |
| Resolução física das camisas | 821–1291 pontos nas malhas testadas | Mesma resolução |
| Resolução física dos calções | 319 / 358 pontos | Mesma resolução |

Novas configurações: `jersey_torso_inset_m`, `jersey_chest_stability`,
`sleeve_collision_inset_m` e `arm_collision_margin_m`. A estabilidade é um
coeficiente de ajuste, não uma porcentagem garantida de redução de movimento.

## Base mantida da 0.5

A camisa deixa de ter um limite praticamente plano a apenas 2 mm para dentro da
malha animada. O novo limite permite até mais 10 mm nas regiões livres. Essa
malha representa a roupa, não a superfície exata da pele. A ancoragem suave fica
progressivamente mais livre longe da gola e dos ombros, a resistência à dobra
é menor e a resistência à compressão é maior. O material pode formar dobras em
vez de simplesmente encurtar quando comprimido. Os comprimentos estruturais
não acompanham mais 85% do encurtamento da animação nas costuras e articulações.

Na 0.5, o corte de referência da cintura e da barra da camisa mantinha sua largura
original; a 0.6 acrescenta o pequeno ajuste descrito acima. A distância de contato com
o calção cai de 10 para 5 mm; com um calção associado, não há uma segunda camada
obrigatória de afastamento em relação à pose da camisa. Permanecem a redução
gradual dos ombros de até 12 mm por lado; o volume central do peito foi reduzido
para até 3 mm na 0.6.

O calção passa de uma redução interna de 5 para 2 mm, oferecendo aproximadamente
3 mm adicionais nas áreas antes mais ajustadas. Sua barra sobe gradualmente até
15 mm, na direção animada de cada perna. Cintura e pontos presos não sobem.
A gravidade efetiva cai de 1,2 para 1,05 vez a gravidade padrão.

A colisão usa as cápsulas regulares e afuniladas das pernas animadas pelo FIFA.
Além dos vértices, verifica os segmentos estruturais e de cisalhamento entre
eles. Isso cobre o caso em que dois vértices estão fora da perna e o tecido
entre eles passa por dentro dela. A margem é de 10 mm. Os vértices são corrigidos
em cada subpasso; os segmentos, no último subpasso do quadro. Há descarte por
caixas de volume e refinamento adicional apenas perto de pontos presos.
Volumes nativos podem invadir a cintura presa em passos amplos; o ponto preso
tem prioridade e seu vizinho livre continua recebendo colisão de vértice.

O contato camisa/calção usa a identidade da mesma pose de ossos, não proximidade
entre jogadores. O cache expira em 250 ms. Sem um parceiro válido, permanece o
limite local conservador da camisa. Cabelo e outras peças usam o solver nativo;
árbitros com as mesmas classes de uniforme também podem receber a simulação.

## Limites e verificação

Esta revisão não adiciona vértices às malhas do FIFA, não importa modelos do PES
e não garante aparência idêntica. Dobras menores que a resolução da malha física
continuam limitadas por ela. A autocolisão é restrita às partículas inferiores;
não há colisão completa de todos os triângulos da roupa contra a pele ou entre
si. Os volumes do corpo e o contato amostrado
entre roupas são aproximações. Permanecem possíveis atravessamentos em poses
não cobertas por esses volumes, perto de pontos presos ou entre superfícies.

Os testes locais cobrem 18 malhas RX3 do próprio FIFA, a 30, 60 e 120 quadros/s:
pontos presos, massas, limites, pausa, teleporte, identidade reciclada e retorno
ao solver original. Um painel comprimido compara dobras e encurtamento com o
perfil anterior, mantendo a mesma largura imposta. Há teste de segmento
atravessando uma perna com ambos os extremos fora dela e teste das seis cápsulas
nativas, com passos de cerca de 49 graus, giros e penetrações provocadas, nos
calções masculino e feminino. O teste do par inclui contato do quadro anterior.

Esses testes medem estabilidade e geometria, não aparência ou FPS da partida.
A colisão de segmentos acrescenta trabalho em relação à 0.4; a frequência fica
em 120 Hz e uma iteração. Aparência, ausência de clipping em todas as animações
e desempenho precisam de avaliação dentro do jogo.

Registros e backups desta revisão:
`J:/mods/fifa 16/estudos fifa 16/80_CLOTH_SHORTS_DEFAULT_OFF_20261016/`.

## Como usar

1. A opção começa desligada. No CF16/Server16, em **Módulos**, ative **Física de roupas**. A opção vale
   no jogo aberto e nas próximas aberturas. Desmarcar usa a física original;
   mantém a ponte para que a opção possa ser reativada durante a partida.
2. Feche e abra o FIFA para carregar a DLL atualizada. A instalação não abre o jogo.
3. **F6** alterna entre esta simulação e o solver original.
4. **F7** relê `cloth_motion.ini`; `enabled=0` seleciona o solver original.

A seleção de camisa regular nos dois pontos `getKitFit` de
`data/fifarna/lua/assets/player.lua` permanece na comparação de F6. Uniformes
especiais e calças de goleiro dependem da malha física disponível no jogo.

Novos parâmetros da 0.5: `jersey_fold_inset_m`, `jersey_fabric_freedom` e
`shorts_hem_lift_m`. Distâncias em metros. Os valores são validados antes do uso.

DLL: `ModCarrerMode/mods/cloth_motion/cloth_motion.dll`.
Log: `ModCarrerMode/logs/cloth_motion.log`.
`installed version=0.8.2` identifica esta revisão; `particle_binding_active`
confirma leitura e escrita da malha. `xpbd_steps` conta atualizações;
`binding_failures` e `native_fallbacks`, retornos ao FIFA. `paired_solves` e
`waist_contacts` registram o contato entre peças; `body_solves`, `body_contacts`
e `edge_contacts`, as verificações de pernas e suas correções. Contadores não
comprovam qualidade visual.

A linha `hem` registra `fold_contacts`, `self_contacts` e
`waist_outward_refinements`. `jersey_mean_us` e `shorts_mean_us` são médias
cumulativas em microssegundos das chamadas amostradas, incluindo leitura,
simulação, contatos e escrita. Não incluem espera pelo bloqueio da peça, o
solver original, reconstrução visual nativa ou o restante do quadro. Cargas
iniciais e rebinding também podem aparecer na amostra; não são um contador de FPS.

## Compilação e recuperação

`build.cmd` compila e executa os testes antes da DLL, sem abrir o FIFA.
`python install.py --verify-only` confere a instalação; `--upgrade` atualiza os
arquivos do módulo com o jogo fechado, guardando backups. `--rollback` remove o
módulo e os dois blocos de seleção regular, preservando outras entradas.
O manifesto da primeira instalação conserva seus backups originais.

O executável x64 deve ter timestamp `577de45c` e as assinaturas esperadas.
As chamadas nativas de parâmetros, animação e solver são conectadas em memória;
o executável e os pacotes BIG não são regravados nesta revisão. Os parâmetros
originais ficam intactos para F6 e para modelos incompatíveis.

As restrições XPBD seguem a formulação geral de
[Macklin, Müller e Chentanez](https://matthias-research.github.io/pages/publications/XPBD.pdf),
com implementação independente neste código.
