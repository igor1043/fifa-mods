# Ver clubes — cena nativa

Revisão local de 25/10: o auxiliar só inicia ao entrar nos titulares. Se o carregador do Server16 encerrar com código -1 antes de iniciar Python, a tela tenta novamente até duas vezes, com espera progressiva, mantendo o mesmo clube e sequência. Erros de exportação continuam visíveis e não geram um ciclo de reinicializações. `test_worker_process.cpp` simula falha transitória, falha permanente e encerramento comum, além de validar ambiente, captura da saída e restrição dos handles herdados. O Server16 atualizado também trata a falha de reabertura do seu arquivo durante a extração.

O APT transparente mantém a navegação e as legendas originais do FIFA. O
plugin desenha o globo e os seletores; bandeiras, escudos e competições são
lidos do catálogo do jogo. Apenas as imagens do globo são assets próprios.

Os pontos da liga mantêm tamanho e opacidade fixos. O globo usa
`assets/globe/earth.dds` em 8192×4096, obtido da imagem NASA Blue Marble
21600×10800, com 14 níveis de mipmap e compressão BC1. O atlas independente
`atlas-hd.png`, também em 8192×4096, usa fronteiras Natural Earth 50m.
Ele armazena os IDs exatos dos países e um campo de distâncias, carregados
como RG8. O shader suaviza a seleção e ajusta a largura dos contornos ao
zoom, sem interpolar IDs. Derivadas periódicas evitam emendas no meridiano
180°. As duas texturas usam aproximadamente 85,4 MiB de memória gráfica.
As imagens PNG antigas de baixa resolução não são usadas pelo plugin atual.
Créditos, URLs e hashes das fontes ficam em `earth-credits.json`.
`build_globe_assets.py <fontes> <assets/globe>` reproduz os arquivos offline;
`globe_world_ids.json` preserva o vínculo com os IDs existentes em catalog.tsv.

Ao abrir “Ver titulares”, o processo auxiliar lê o save ativo sem modificá-lo,
obtém onze titulares distintos e exporta a pose de seis jogadores em pé e
cinco agachados. `native_assets.py` converte essa geometria para RX3 preservando
as coordenadas UV, normais e dimensões das texturas do FIFA. Os materiais
comuns usam os pixels comprimidos originais, sem recompressão nem atlas.
Apenas cores sólidas e máscaras/tintas de cabelo precisam de preparação.
As partes opacas e transparências têm materiais separados. O renderizador GameplayProp do
FIFA coloca o grupo no centro do gramado do estádio que já está carregado.
Esta visualização é estática; não inicia partida nem animações de jogadores.

As chamadas do FIFA e o empréstimo da câmera acontecem exclusivamente no
callback nativo de cena, encadeado após o vestiário. Present apenas comunica
pedidos e desenha a interface. A instalação verifica as assinaturas das
funções e a DLL dona do callback anterior. Nenhum estádio é recarregado.
Ao voltar, o grupo é ocultado e os campos da câmera são restaurados somente
se ainda contiverem os valores escritos por esta tela.

Cada troca de elenco recebe um objeto nativo com nome e aliases imutáveis,
com 96 slots (64 opacos, 32 alpha). Slots não utilizados recebem triângulos
degenerados. `AddAsset` do FIFA acrescenta descritores: reutilizar aliases no
mesmo objeto acumulava os recursos do clube anterior e podia causar crash.
O objeto anterior é ocultado e descarregado pela função nativa de Unload,
apenas no callback da engine e após terminar seu streaming. Só um conjunto
de recursos permanece residente. O registro leve do objeto permanece no
contexto do FIFA até encerrar a sessão; não se chama um destrutor sem remover
primeiro todas as referências da engine. Atualizar o mesmo elenco pronto
reutiliza seu objeto. Cada objeto recebe apenas um Reload e um registro na
cena; pedidos antigos não podem se apresentar como o clube recém-selecionado.
Recursos completos são publicados antes do pedido de carregamento. Os
titulares refletem o último salvamento da carreira ativa.

A preparação começa exclusivamente ao selecionar “Ver titulares” ou
“Atualizar”. Abrir o globo ou percorrer os seletores não lê o save nem gera
modelos dos titulares. Não há pré-carregamento no mapa. O auxiliar consulta
pedidos a cada 30 ms, e a interface recebe o resultado em até 50 ms.
Um único processo auxiliar persistente lê os modelos originais. O cache em
`ModCarrerMode/cache/club_browser/xi/prepared/<hash>/` é reaproveitado entre
sessões, com publicação atômica por hard links quando disponíveis. A chave
inclui elenco/aparências, versão do conversor, banco instalado e exportador.
As tabelas do save são preparadas somente no primeiro pedido de titulares.
Um cache de leitura retém um único save ativo e seus índices;
mudanças na identidade, tamanho ou data de gravação do save, banco ou esquema
invalidam esse cache. Materiais idênticos são reutilizados entre clubes em
`cache/club_browser/xi/materials/`, com chave baseada nos pixels, dimensões,
coeficientes, cor, transparência e template. A conversão de cor/alpha usa
tabelas de 256 valores e produz os mesmos arquivos da versão anterior.
Um material truncado é reconstruído antes de ser publicado para a engine.
Isso não é a fábrica de atores animados da carreira jogador: a visualização
usa poses estáticas e o renderizador nativo GameplayProp. Os objetos do jogador
original, a partida, o estádio e os saves não são alterados.

`character_lighting.py` gera, no primeiro pedido, cópias próprias dos cubemaps
ambientes do FIFA com RGB neutro para reduzir o reflexo verde do material
estático. Preserva luminância direcional, seis faces, todos os mipmaps e os
blocos de alpha BC3 originais. Os pixels das camisas, rostos e demais texturas
dos jogadores não passam por essa neutralização. Os arquivos originais do
FIFA permanecem intactos; as cópias ficam em `server16_club_xi/lighting/`.

Diagnósticos por sessão: `ModCarrerMode/runtime/club_browser/<pid>/` contém
`worker.log`, `export.log`, `status.tsv`, `roster.json`, `engine.log` e
`native_status.json`. Recursos gerados ficam exclusivamente em
`data/sceneassets/server16_club_xi/<pid>/<hash>/`.
`timings.json` separa leitura do save, obtenção dos modelos e preparação nativa.
O diagnóstico nativo inclui clube exibido, sequência, objetos criados e
conjuntos residentes para detectar trocas incompletas e recursos acumulados.

Testes: `test_native.cpp` usa D3D11 WARP, sem anexar ao FIFA, para verificar
estado gráfico, navegação, projeção, zoom, jobs e restauração da câmera.
`test_native_assets.py` compara vértices/UVs antes e depois da conversão,
verifica o layout de normais e a igualdade dos pixels comprimidos originais.
`test_scene_lua.py` valida o binding e recarregamento em Lua 5.1
(dependência de teste: lupa). `test_integration.py` verifica o APT e o hub.
Nenhuma dependência de teste é necessária no jogo.
`test_character_lighting.py` verifica os cubemaps reais, seus cabeçalhos,
registros de mip, alpha exato e cache, sem alterar os originais.
O carregamento e a câmera aceitam os estados de cena 1 e 13, com projeção
finita e proporção válida. O estado 13 foi conferido no estádio aberto no
FIFA; o antigo teste de igualdade com 1 deixava os recursos prontos sem
submetê-los à cena. `native_status.json` inclui estado, etapa de espera e
contador de quadros para distinguir leitura, espera da cena e streaming.
`test_loading_cache.py` usa saves e assets reais para comparar resultados,
testar invalidação por nova gravação e recuperar material truncado, sem
modificar o save. A primeira geração de um clube ainda exige a obtenção dos
modelos; os arquivos completos são reutilizados nas aberturas seguintes.
`test_globe_assets.py <data/club_browser>` verifica mipmaps, dimensões,
IDs geográficos e precisão do campo de distâncias. O teste WARP também
compara quadros separados no tempo para impedir regressão dos pontos fixos
e exporta imagens de zoom máximo, Europa e meridiano 180°.

### Correções de vestiário e auxiliares — 25/10/2026

O vestiário tinha os modelos prontos, mas sua câmera ignorava o estado 13 de um estádio carregado. Agora aceita os estados 1 e 13, mantendo a validação da projeção e a restauração da câmera. A recuperação foi confirmada pelo usuário na sessão aberta; modelos, texturas e os demais mods foram preservados.

O auxiliar dos titulares inicia com ambiente congelado independente e herda somente seus canais de entrada/saída. O Server grava a saída de cada auxiliar em `service.log`, evitando que um stdout inválido encerre a preparação. A tela detecta quando o auxiliar termina e permite tentar novamente. Erros do exportador preservam saída e código de encerramento.

O complemento de assets dessa revisão permanece compatível; esta revisão altera código, DLLs e Server16. A visualização dos titulares no PC do Robson ainda precisa de validação. Para comparar os computadores, use `ModCarrerMode/tools/Coletar-Diagnostico-Carreira.ps1`: ele gera um ZIP de logs e hashes, sem copiar saves, contratos SQL, modelos ou executáveis.

### Pose autoral dos onze — entrega de 26/10/2026

A foto usa a pose salva pelo usuário em `cena-fifa-friends (15).json`. A cena
editável fica em `ModCarrerMode/data/club_browser/poses/starting_eleven.scene.json`;
`starting_eleven.pose` é a receita compacta FFPOSE02 consumida pelo exportador.
Os onze slots recebem os jogadores da escalação do clube atual, na ordenação
nativa de altura, com o goleiro no início da fileira de trás. Nomes e IDs do
Flamengo no arquivo de autoria servem à referência e não selecionam jogadores
de outros clubes durante a execução.

As transformações dos 400 ossos são aplicadas aos modelos originais, com oito
pesos por vértice. O tamanho acompanha o modelo de cada jogador, e o apoio dos
calçados é alinhado ao chão antes da posição de cada slot. Aparências, uniformes,
UVs e pixels das texturas continuam vindo da instalação e da carreira ativa.
A chave do cache inclui o conteúdo da receita, além do elenco e do exportador.
Uma receita modificada durante a preparação não é publicada como pronta.

`exporter/` contém o código-fonte isolado do exportador e a referência numérica
do esqueleto, permitindo reconstruir o executável sem o outro projeto local.
Para atualizar uma pose: salve o JSON, execute `exporter/prepare_pose.py <cena>
<starting_eleven.pose>` e copie a receita completa. `exporter/build.cmd` reconstrói
`generate_lineup.exe`. O protocolo persistente `--web-worker` continua aceitando
fixture, destino e pose 1 por linha. A interface e o renderizador nativo do FIFA
mantêm seu fluxo; somente o preparador da foto recebe a receita nova.

Testes locais: receita reproduzível, rejeição de cena incompleta ou inválida,
invalidação do cache, exportador persistente, comparação de todas as 108 partes
com a cena autoral e geração dos elencos reais de Flamengo, Grêmio e Internacional.
Vértices, normais, UVs e texturas foram comparados. Evidências de instalação e
verificação: `code-release/xi_pose_20261026/`. A conferência visual fica para a
próxima abertura de Ver titulares/Atualizar. O JSON de autoria e o exportador são
versionados; a receita compilada acompanha o complemento de 26/10. Metadados
validam o hash e mostram um erro claro se faltar a receita ou ela for antiga.


### Elenco individual — teste local de 26/10/2026

Selecionar um clube no globo abre duas opções: **11 iniciais**, mantendo a foto
existente, e **Jogadores do time**. A segunda lê o elenco completo do clube no
save ativo, incluindo reservas, nome editado, número, posição, nacionalidade,
altura, peso e 34 atributos. A projeção e o preparador são compartilhados com o
fluxo existente, sem escrever no save. Os escudos e retratos são consultados na
própria instalação. O globo não faz pré-carregamento de modelos.

A tela usa APT transparente, a barra original de ajuda do FIFA e cards nativos
claros. A lista muda com cima/baixo ou analógico esquerdo; X/C ou LB/RB mudam as
abas, o analógico direito gira o jogador e W/E ou LT/RT ajustam a aproximação.
O retorno é Elenco/Onze → escolha das opções → globo → carreira. O APT publica
comandos limitados por uma fila; somente o callback verificado da engine toca
na cena e na câmera. A seleção rápida cancela a preparação anterior e oculta o
modelo antigo para não exibir um jogador de outro clube.

O modelo individual também é desenhado pelo FIFA como GameplayProp, com os
materiais e UVs originais. Não há WebView/WebGL no jogador em jogo. O preparador
retargeta o clipe ANT original
`F13_B196A1_Sideline_MNGR_idle_ArmsCrossed_EDIT_02_Player_1` para o esqueleto
original de 400 ossos e oito pesos. A sequência compacta de vértices é interpolada
por quadro e enviada apenas aos buffers cujo conteúdo inicial corresponde
exatamente ao modelo validado. Outros buffers e texturas ficam fora da seleção.
Isso não é a fábrica completa de atores do FIFA e não adiciona sombras dinâmicas.
A aba Desempenho informa a indisponibilidade dos registros individuais; não cria
estatísticas fictícias.

O primeiro preparo gera os materiais e a animação; as visitas seguintes usam
cache por jogador, aparência, uniforme, clipe e exportador. Medição isolada:
exportação individual 0,12–0,37 s; preparação da animação de referência cerca de
5 s com cache de materiais. São medidas de laboratório, não garantia de tempo
no FIFA. Erros têm diagnóstico e não reaproveitam o modelo da seleção anterior.
`native_status.json` registra jogador, buffers animados e atualizações.

Validação local: elencos reais de três clubes; um jogador e o XI no mesmo
exportador persistente; animação e UVs no D3D11 WARP, buffers alheios intactos;
rolagem, retorno e três abas renderizadas; emulador APT; 23 regressões de
finanças, vestiário e próxima partida. Evidências e cópia de segurança em
`code-release/club_roster_local_20261026/`. A instalação é local para teste:
**sem commit, push ou publicação**. A conferência visual no FIFA ainda depende
da abertura do jogo após substituir as DLLs.


### Correção do piscar em modo janela — teste local de 27/10/2026

O desenho nativo pronto deixa de ser despublicado no início de cada atualização.
A identidade e a visibilidade dos titulares permanecem válidas durante um quadro
sem mudanças. Sair da tela, trocar de carreira, iniciar outra seleção ou perder
a cena válida continua desabilitando o desenho explicitamente.

A captura de estado da interface agora conserva todos os 128 slots de recursos
nos seis estágios de shader e os UAVs do pixel/compute. O Direct3D pode limpar
esses vínculos automaticamente quando a textura da apresentação passa a ser
um render target; conservar apenas PS 0/1 não desfazia essa limpeza. A restauração
remove primeiro os outputs da interface, recupera os outputs nativos com os
contadores preservados e então recupera os inputs, sem alterar texturas, materiais
ou iluminação dos modelos.

O teste anterior à correção perdeu 24 vínculos em três tamanhos de apresentação.
O mesmo teste passou após o ajuste, incluindo buffers alternados, inputs dos
seis estágios, UAVs e render target. O teste da cena falhava durante o quadro
sem mudanças; agora mantém a publicação por 2.000 quadros e confirma que as
saídas e contextos inválidos continuam ocultando o modelo. Ambos fazem parte
de `test_native.cmd`. Evidências e cópia anterior estão em
`code-release/club_windowed_flicker_20261027/`. A revisão é local, sem commit/push;
a confirmação visual do piscar no FIFA em modo janela ainda precisa ser feita.


### Elenco individual, revisão 2 — local de 27/10/2026

A câmera permanece sob controle da tela de elenco durante a preparação e a
troca de jogador, mantendo zoom, altura e órbita. A rotação altera a câmera
nativa em torno do jogador e do estádio; o objeto do jogador continua com a
transformação identidade. Gatilhos/W/E ou +/− aproximam, analógico direito e
arraste orbitam e ajustam a altura. A roda sobre a lista percorre jogadores;
sobre o jogador controla o zoom. A faixa do cabeçalho foi removida somente
nesta tela, preservando os textos e o escudo.

A lista possui ordenação por Elenco, Geral, Idade e Titulares. A ordenação mantém
o jogador que está sendo visualizado e não gera outro pedido de modelo. As
idades usam a data da carreira e o nascimento gravado no DB; titularidade vem
da escalação favorita/default validada. O campo mostra área, linha central,
círculos e pontos de posição, com a posição principal e as secundárias do DB.
Os dois cards da escolha de visualização recebem foco com o mouse, mantendo
a seleção do APT e a do renderizador sincronizadas.

Desempenho consulta a publicação nativa já existente `career_fce_snapshot.json`,
validando PID, criação do processo, clube da carreira, identidade/versão do save
e data atual do calendário na RAM. Jogos, minutos, gols e assistências são
agregados por competição sem somar uma totalização raiz novamente às fases.
Registros conflitantes ou de outra sessão não viram números. Quando não existe
publicação confirmada para o clube, a tela mostra valores indisponíveis; não
cria partidas. Teste com a sessão real confirmou duas aparições/180 minutos para
os titulares do Flamengo. O Grêmio não tinha registros nessa publicação.

O transporte do elenco passa a S16ROSTER2 (52 campos), com leitura compatível da
versão anterior. O rodapé continua usando HelpManager e os símbolos originais
do FIFA. Há atualização imediata e novas atualizações após a entrada/troca de
página, para aguardar a barra nativa. LB/RB mudam abas; Y/triângulo/tecla original
de ação superior alterna ordenação. Nenhum ícone de controle foi redesenhado.

A animação agora reconhece interfaces de dispositivo D3D11 adicionais, faixas
exatas de um mesh dentro de buffers agrupados e recursos DEFAULT preenchidos
posteriormente por cópia da GPU. A leitura de descoberta é limitada por quadro,
por tentativas e a 32 MiB de candidatos; somente bytes iguais ao mesh validado
podem ser animados. Updates alteram apenas a faixa própria, preservando as
outras regiões, UVs e materiais. O cache de recursos confirmados é limitado a
64 MiB. Não há atualização de um buffer alheio baseada só em tamanho. O status
inclui contadores de criação, descoberta e atualização para validação no FIFA.

O cálculo da pose reutiliza as matrizes locais dos ossos não animados. O mesmo
caso isolado passou de aproximadamente 5,2 s para 2,9 s, mantendo 23 amostras e
os materiais originais. Auxiliar e exportador usam prioridade normal; a seleção
substituída é cancelada sem publicar erro de renderização. Não há pré-carregamento
no globo.

Evidências em `code-release/club_roster_r2_20261027/`: 14 testes Python, teste APT
com hover/retorno/abas/ordenação e atualização da ajuda, dados reais e save
imutável, três abas renderizadas, ordenações, câmera durante espera, buffers
agrupados/cópia tardia/interfaces D3D11 e preservação dos demais recursos. A
animação, a órbita e a barra de ajuda ainda precisam de conferência visual no
FIFA após instalar e reabrir. Sem commit ou push nesta revisão.


### Elenco individual, revisão 3 — teste local de 27/10/2026

Cima no primeiro jogador leva o foco às ordenações; esquerda/direita alteram
Elenco/GER/Idade/Titulares e baixo devolve o foco à lista. A/Enter abre os
detalhes individuais. Voltar retorna ao elenco sem recarregar o ator, sem
reiniciar a animação e sem mudar a órbita da câmera aprovada.

A câmera preserva sua matriz original durante reaplicações sucessivas e só a
restaura ao sair da visualização. O teste cobre 120 reaplicações e a restauração
exata, além da publicação estável do ator em 2.000 quadros. A confirmação visual
do piscar continua pendente no FIFA; não é declarada corrigida só pelo teste.

Nome e número seguem os hotspots UV, fontes nativas e dígitos RX3 do jogo.
São superfícies com os pesos do esqueleto da própria camisa; a textura original
da camisa permanece intacta e os pixels comprimidos dos dígitos são mantidos.
A projeção seleciona `teamkits.year == 0`, correspondente ao asset atual
`kit_<clube>_<tipo>_0`. O caso Flamengo tinha também uma linha de 1989: a seleção
anterior por tipo apenas sobrescrevia a fonte atual 201/cor 7 pela clássica
248/cor 13. A escolha é agora independente da ordem das linhas. Regras Lua
avaliadas são consultadas por leitura da RAM, quando disponíveis, sem executar
scripts no processo para essa consulta. O cache inclui as regras da impressão.

O diagnóstico da animação utiliza uma flag temporária em
`ModCarrerMode/runtime/club_browser/enable_vertex_probe`. Ele registra no máximo
64 amostras dos buffers do renderizador (até 1 MiB cada), apenas para comparar
o layout real aos streams próprios do ator. Não usa depurador. As leituras GPU
são assíncronas e usam DO_NOT_WAIT para não bloquear Present. Nenhum buffer é
animado só pelo tamanho: a posse continua dependendo da correspondência dos
bytes da geometria. Na última sessão anterior à revisão, a animação tinha zero
buffers reconhecidos; esta revisão ainda precisa confirmar a captura real.
A barra de ações segue o HelpManager original e ainda exige validação visual.

Testes: foco e ordenações sem novos pedidos de modelo, detalhe/retorno sem
recarga, APT com navegação aninhada, todas as abas renderizadas em WARP,
restauração D3D11, câmera, leitura de save imutável, seleção de uniforme atual,
superfícies com skinning e bake completo do clipe com nome/número. Evidências em
`code-release/club_roster_r3_20261027`. Somente instalação local; sem commit,
push ou ZIP de distribuição nesta revisão.


### Revisão 4 — formato real da GPU e uniformes no vestiário

A captura da sessão 14520 confirmou dez malhas nativas completas: o FIFA
expande normal e tangente 3s10n para half4, mantendo posições/UVs e passando
de 20 para 28 bytes por vértice. A conversão trunca a mantissa half em direção
a zero. `test_native_gpu_layout.cpp` compara a conversão inteira às amostras
reais, byte por byte. O animador reconhece ambos os formatos e atualiza somente
as faixas próprias verificadas. O teste D3D11 cobre também buffers imutáveis no
formato expandido, preservação das UVs e recursos alheios. A flag de captura é
removida na instalação desta revisão; os contadores de animação permanecem no
status para conferir a execução real.

A seleção de uniformes agora é compartilhada com o vestiário por
`club_environment/kit_selection.py`. A verificação percorreu os 1.863 clubes da
base: elimina os anos clássicos e mantém a primeira chave primária nativa em
caso de repetição do tipo atual. A ordem de consulta não altera o resultado.
Números, nomes, cores e fontes continuam sendo determinados por clube/tipo e
regras do jogo, sem constante específica para o Flamengo no código de produção.

A leitura do HelpManager original confirmou que Update não exibe uma barra
oculta. A tela passa seu getHelpContext como fonte local pela API nativa
SetCustomSource e chama Show, além de Update; Clear libera a fonte ao sair.
Os ícones continuam sendo os originais do jogo, sem imagens de botões próprias.
Validação visual da animação/rodapé após instalação ainda é necessária.
Sem commit, push ou ZIP. Evidências adicionais em
`code-release/club_roster_r4_20261027` e nos logs da revisão 3.


### Correção do piscar preto — teste local de 27/10/2026

As imagens e a captura da sessão 38656 confirmaram que a geometria permanece
visível como silhueta preta. Os 4.096 registros da captura tiveram os mesmos
coeficientes de iluminação; o patch não altera a luz, as texturas ou a animação.

Foi reproduzido um defeito na restauração do estado D3D11 da interface: a API
PSGetConstantBuffers/PSSetConstantBuffers preservava o ponteiro do buffer, mas
perdia o intervalo D3D11.1 definido por PSSetConstantBuffers1. Os testes com
intervalos 16/16, 64/16 e 256/16 voltavam como 0/4096. Assim, um shader nativo
podia ler outra região do mesmo buffer, inclusive zeros. Um teste renderizado
reproduz a passagem de uma cor válida para preto com a restauração antiga.

SavedState agora consulta ID3D11DeviceContext1 e preserva FirstConstant e
NumConstants do PS b0, único slot de constantes modificado pela interface.
A restauração usa SetConstantBuffers1 para intervalos e mantém a API base para
buffers inteiros/nulos ou contexto sem suporte à interface. Os testes de
intervalo passaram; o teste renderizado manteve exatamente os pixels coloridos
por 120 quadros consecutivos após o desenho da interface. Ambos integram
`test_native.cmd`, junto à preservação de recursos dos seis estágios, UAVs,
câmera e publicação do modelo em 2.000 quadros.

A correção vale para o renderizador compartilhado pelo elenco e pelos 11
iniciais. A animação confirmada na revisão 4, a câmera e os assets são mantidos.
O status nativo inclui packed_constant_restores, ps_constant_first e
ps_constant_count para confirmar o uso de intervalos reais no jogo. A captura
experimental e seus hooks foram retirados do código de produção; a flag de
captura é removida na instalação. Fontes experimentais e evidências permanecem
somente em `code-release/club_roster_flicker_20261027`. A confirmação visual
após reiniciar o FIFA ainda é necessária. Sem commit ou push.


### Jogador animado sem silhueta preta — revisão local de 27/10/2026

A correção de intervalos D3D11.1 acima resolve um defeito do salvamento de
estado, mas não resolveu o piscar observado nesta sessão. O teste A/B em RAM
comprovou que pausar uploads removia o movimento e estabilizava a textura. O
usuário confirmou animação e textura estáveis após trocar o caminho dos uploads.

O modo individual não atualiza mais buffers de vértices nativos em Present,
nem muda o descriptor de buffers IMMUTABLE do FIFA. Na chamada GPU real de
desenho, a malha completa é conferida contra o primeiro quadro do clipe. Uma
cópia própria recebe a animação, é ligada somente nesse desenho e a ligação
original é restaurada em seguida. Materiais, shaders, texturas, câmera e
estádio continuam no renderizador nativo do jogo; não há render WebGL.
A comparação usa todos os bytes da malha, além do layout e das dimensões,
sem clube ou jogador fixado. Recursos de outro jogador são rejeitados e o
cache da associação é descartado ao trocar o clipe ou sair da visualização.

O contexto D3D11 atualiza sua própria tabela de despacho conforme o estado.
O callback nativo rearma somente as duas entradas observadas antes de submeter
o modelo. Mudanças feitas pelo próprio módulo nativo são acompanhadas;
entradas de outro módulo não são sobrescritas. No encerramento, somente
entradas que ainda apontam para esta revisão são restauradas. Os 11 iniciais
continuam na visualização estática, sem esse caminho de animação.

`test_player_animation.cpp`, agora em `test_native.cmd`, reproduz a perda da
entrada após o primeiro desenho, valida o rearme, movimenta vértices reais na
GPU WARP e confere que o buffer original permanece IMMUTABLE e idêntico após
240 desenhos. Verifica os dois tipos de desenho, restauração da ligação,
coordenadas UV, estado oculto/desativado, recursos alheios e troca de jogador
ou clube. O teste padrão gera uma fixture pequena, sem modelos externos;
aceita um animation.bin real como argumento para verificação adicional.
O status registra `animation_backend`, `animation_private_uploads`,
`animation_draw_matches`, `animation_dispatch_rearms` e rejeições de malha.

A validação visual confirmada corresponde ao teste em RAM no jogador atual;
a instalação permanente deve ser conferida após reabrir e em outros clubes.
Sem commit, push, ZIP ou novos assets. Evidências em
`code-release/club_player_animation_ab_20261027`.


### Continuidade da animação — revisão adicional de 27/10/2026

Após reiniciar, a revisão anterior ainda piscou em preto e alternou brevemente
a posição. A RAM confirmou um único objeto e a mesma sequência: não ocorria
recriação do jogador. Ocultar somente os cards, mantendo a animação, não
removeu o defeito. A ligação contínua sozinha também não o resolveu.

O novo teste em RAM manteve o buffer animado ligado e passou a escrever em
buffers próprios DYNAMIC/CPU_WRITE com Map(WRITE_DISCARD). O driver pode
renomear o armazenamento em vez de sobrescrever uma região ainda usada por
um quadro anterior. O usuário confirmou que pararam as piscadas e o salto,
com a animação ativa e os cards visíveis. A implementação permanente usa
esse mesmo caminho: substitui somente o buffer verificado na ligação de
vértices e não retorna à pose zero após cada desenho. Os materiais, texturas,
shaders, câmera e recursos originais permanecem no FIFA.

As malhas expandidas são preparadas junto ao clipe na tarefa assíncrona.
Cada instante da animação é escrito uma vez por buffer, antes da submissão
nativa. A restauração da interface pode religar o próprio buffer animado sem
provocar nova captura, nova cópia ou retorno à pose inicial. Mudanças de
jogador/clube continuam invalidando o cache por identidade completa do clipe.
Os 11 iniciais mantêm seu caminho estático.

O teste padrão e o teste com um animation.bin real verificam 240 quadros com
o buffer dinâmico permanentemente ligado, imutabilidade da origem, UVs,
interpolação, escrita única por instante, religação pela interface, entradas
nativas atualizadas, visibilidade e troca de jogador/clube. A suíte completa
inclui estado D3D11, navegação, recuperação do auxiliar e publicação da cena.
O status identifica `animation_backend: dynamic_discard_persistent_binding`.
A confirmação em RAM é do jogador atual; a instalação deve ser conferida
após reabrir e ao percorrer outros clubes. Sem commit, push, ZIP ou assets
novos. Evidências em `code-release/club_player_render_followup_20261027`.


### Acesso pelo vestiário — revisão local de 27/10/2026

O vestiário oferece Cenas e Jogadores do time, com foco por mouse, setas e
analógico esquerdo. Selecionar o elenco mantém a página DressingRoom e o
ambiente 3D carregados. A lista e os detalhes reutilizam o mesmo componente,
os filtros, dados da carreira, uniformes e animação da visualização pelo globo.
O jogador é colocado no piso do vestiário, na origem isolada do ambiente,
com a câmera orbitando o jogador e o cenário juntos. Não há outro WebView.

O APT envia o comando direto Server16ClubBrowser/room_roster pelo transporte
nativo já instalado. A tentativa anterior de SendEvent para outra página não
ativou o fluxo em jogo; este acesso não depende dessa transição. O plugin
aceita a abertura apenas na página do vestiário e com clube atual válido.
Uma seleção antiga no globo não determina o elenco da carreira.

Enquanto o elenco está aberto, o vestiário mantém suas geometrias e texturas,
mas cede a câmera ao renderizador do jogador. A câmera das cenas continua
reservada e é retomada ao sair. As legendas usam o HelpManager original do
FIFA: detalhes, voltar, elenco, abas, giro e zoom. Voltar nos detalhes retorna
à lista; voltar na lista retorna às cenas. Reabrir/fechar a página limpa o
modo do elenco para não deixar outro clube ou uma câmera antiga ativos.

HEADER_REVISION 66 atualiza o APT do vestiário. Testes verificam mouse/controle,
comandos diretos, retorno em duas etapas, materiais e animação com DISCARD,
clube atual, origem do jogador no ambiente e órbita da câmera. A animação e a
pose dos 11 iniciais e os assets existentes permanecem os mesmos. Revisão
local, aguardando confirmação visual após instalar; sem commit ou push.

### Isolamento gráfico e rodapé — revisão local de 27/10/2026

O desenho dos cards usa um estado de contexto D3D11 separado. Ao terminar,
limpa as ligações do estado da interface e restaura o estado completo do FIFA
antes de apresentar o quadro. Assim, a restauração dos cards não repassa as
ligações de vértices pela atualização da animação nem retém o render target
da janela durante ResizeBuffers. O overlay do Server16 usa a mesma proteção.
A câmera escolhida pelo usuário também é aplicada antes da atualização nativa
da cena, além da publicação posterior já existente.

A implementação usa CreateDeviceContextState/SwapDeviceContextState, com
fallback para a proteção anterior quando a API não está disponível. Referência:
https://learn.microsoft.com/en-us/windows/win32/api/d3d11_1/nf-d3d11_1-id3d11devicecontext1-swapdevicecontextstate

As legendas continuam no HelpManager original. Somente durante o elenco,
mcHelpItemsHolder e mcTextScroller são posicionados em Y=1030 no APT 1920x1080,
abaixo dos cards; a posição anterior volta ao sair. Vale para o globo e o vestiário.

A regressão gráfica verifica 300 mudanças de conteúdo preservando vértices,
texturas e intervalos de constantes do jogador e liberando as referências do
render target da interface. Na tentativa em RAM, o usuário confirmou melhora
e autorizou prosseguir, ainda relatando pequena piscada em transições. Isso
permanece uma limitação a confirmar na instalação, não uma garantia de ausência
total de flicker. Sem commit, push ou novos assets nesta revisão.


### Coeficientes do jogador animado — revisão local de 27/10/2026

O jogador individual usa o mapa auxiliar de coeficientes original do FIFA,
com todos os pixels comprimidos e oito níveis de mip preservados. Apenas o
nome de consulta no contêiner é adaptado ao material nativo existente. As
imagens de camisa, pele e cabelo, a geometria, os UVs e a animação continuam
iguais. A geração dos 11 iniciais estáticos mantém o comportamento anterior.

No diagnóstico em jogo, os quadros pretos corresponderam a valores inválidos
no alvo HDR do jogador. A revisão elimina o mapa zerado no caminho animado e
invalida o cache de preparação pela identidade v3, para não reutilizar a
versão anterior. Não recarrega materiais de um objeto que já está desenhando.
O caminho é compartilhado pelo elenco no estádio e no vestiário, por clube.

A validação em RAM registrou 0 silhuetas pretas em 2.048 amostras do goleiro
e outras 2.048 do jogador de linha; o usuário também confirmou a melhora.
A regressão compara o mapa auxiliar com o payload nativo e verifica que a
troca não modifica geometria nem texturas de cor. Isso não constitui uma
garantia absoluta para todos os drivers e cenários. Revisão local, sem commit
ou push, e sem alteração de DATA, INDEX ou tabelas da carreira.


### Técnico do time (revisão local, 27/10/2026)

Em Ver clubes, o clube selecionado agora tem três cards: **11 iniciais**,
**Jogadores do time** e **Técnico do time**. O terceiro abre uma tela clara com
o estádio ao fundo e o técnico nativo em 3D à direita. Teclado, controle e mouse
usam o mesmo fluxo; as legendas são do HelpManager original do FIFA. Voltar
retorna à escolha do clube. A câmera orbita o técnico e mantém zoom e movimento.

Abas: **Resumo** (identidade, país, clube, competição, confiança, reputação,
salário mensal, formação, estádio, capacidade e desempenho do clube),
**Temporada** (competições, aproveitamento, gols e histórico registrado no save,
com rolagem), **Escalação** (os 11 titulares do clube na carreira). Resultados
do clube são identificados como tais, sem inventar um currículo do técnico.
Salário, confiança e reputação do usuário exigem a junção exata de userid e
clubteamid; não são copiados para outros clubes. Ausência de dados aparece como
travessão. Os valores de salário mantêm a unidade monetária da carreira.

`coach_data.py` apenas lê a carreira validada e o snapshot nativo da sessão;
não altera DATA, INDEX, tabelas da carreira ou o banco SQL dos empréstimos.
`coach_worker.py` prepara fora da thread gráfica e publica somente resultados
completos do clube/solicitação/contexto ainda atuais. O modo **402** do exportador
aceita a ABI dedicada FFCOACH1: ID e cores do clube, sem jogador fictício.
Carrega apenas `specificmanager_<clube>_0_0.rx3` e sua textura da instalação.
O esqueleto compacto SLC é próprio do técnico; não usa o rig dos jogadores.
A animação `coach_crossed.json` vem da referência Nova Experiência. O desenho
final usa GameplayProp no motor do FIFA, sem WebView ou WebGL dentro do jogo.
Se um clube não tiver o modelo instalado, o perfil continua disponível e
informa a ausência do 3D; não substitui pelo técnico de outro time.

Cache separado em `ModCarrerMode/cache/club_browser/coach`, invalidado por clube,
modelo, textura, animação e exportador. Escudos, bandeiras e ícones de competição
são lidos da biblioteca do próprio jogo. O material auxiliar mantém o payload
nativo e seus mipmaps, preservando a correção de renderização dos jogadores.
Os testes cobrem dados de clubes distintos, calendário, partidas futuras,
duplicidade, identidade, protocolo nativo e navegação sem regredir XI/elenco.

## Competições da carreira — revisão local de 28/10

O card **Classificação** da aba Competições abre a tela nativa
`CareerCompetitions`, com o mesmo isolamento gráfico usado pelos outros cards.
O destino antigo `EnterStandings` continua disponível para outros fluxos.
L1/R1 (LB/RB) muda a competição; L2/R2 (LT/RT) alterna artilheiros e assistências.
As legendas são produzidas pelo HelpManager original do FIFA, conforme o dispositivo.

A lista usa as inscrições reais do clube na carreira e mantém competições
eliminadas no fim. A tabela comporta vinte equipes, mostra a movimentação desde
a última rodada e lê as faixas de classificação/rebaixamento do CompData instalado.
Não deduz regras pelo número de equipes nem pelo nome do campeonato.

Copas leem `match_stagetype` (LEAGUE, KO1LEG, KO2LEGS) e os vínculos de
`advancement.txt`. Os grupos são navegáveis, inclusive os que não contêm o usuário.
**Ver chaveamento** ou A/Enter abre uma vista ampliada, com final no centro,
confrontos nos dois lados, escudos originais e placares de ida, volta e agregado.
Analógico esquerdo/setas movimentam; gatilhos/W/E ou roda do mouse ampliam;
mouse arrasta; A/Enter centraliza; B/Esc fecha primeiro a vista ampliada.
Clubes e fases ainda não sorteados ficam como **A definir**. Não há vencedores
de pênaltis inventados nem classificação antecipada após só a ida.

`competitions_worker.py` espera pela publicação da sessão/data atuais, descarta
leituras quando a carreira muda e sinaliza nova tentativa se o snapshot ainda não
estiver pronto. A exportação usa o auxiliar existente; a thread gráfica não lê o
save inteiro. Entradas e respostas têm clube/PID/sequência validados.

O snapshot JSON mantém seus oito campos originais de estatísticas e acrescenta
`rating_sum` e `profile_valid`, já calculados pelo núcleo. O time do campeonato
usa somente médias reais por posição, com onze jogadores distintos. Na ausência
de notas válidas, informa a indisponibilidade; overall não substitui a nota.

Nenhum DATA, INDEX, banco da carreira ou SQL é alterado por esta tela. Escudos,
fotos e ícones vêm da instalação do jogo. Os testes portáveis de copas e de
publicação estão em `test_competition_cups.py` e `test_competitions_worker.py`.
Esta revisão integra a entrega de 28/10/2026, publicada com fontes, binários e animações. Não exige novo ZIP além dos complementos anteriores.

### Refinamento visual das competições — 28/10

A coluna de artilheiros/assistências passou de 292 para 352 unidades no desenho
nativo de 1600 × 900. Exibe a posição no ranking, foto, nome, posição em campo,
clube e total, com cards claros e cantos suaves. A posição vem do cadastro do
jogador; o leitor aceita tanto o protocolo anterior de nove campos quanto o
campo opcional novo, sem invalidar uma publicação anterior.

O card do time do campeonato passou de 476 para 416 unidades de largura.
Somente esse campinho ganhou um escudo do clube junto à foto de cada atleta,
sempre lido do acervo original do FIFA. A disposição reserva espaço para foto,
nota e nome, inclusive para o goleiro. `native/test_competitions_layout.cpp`
valida os limites e a ausência de sobreposição nas cinco formações suportadas.
Navegação, calendário, critérios de seleção e arquivos da carreira permanecem
sob o mesmo fluxo de leitura da revisão anterior.

Acabamento local: a coluna de resultados recentes é identificada por
**ÚLTIMAS 5**, com indicadores circulares tanto na classificação compacta e
nos grupos quanto na tabela ampliada. Artilheiros e assistências exibem apenas
o total, sem repetir a unidade abaixo de cada número. No campinho, o escudo
fica à esquerda da nota na própria faixa, com o nome abaixo e espaço reservado
para o goleiro.
