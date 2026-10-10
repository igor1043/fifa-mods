# Mascote na linha de fundo

Compile com build.cmd. Plugin: ModCarrerMode/mods/mascot_single/mascot_goal_line.dll.
A DLL usa o ID do mandante e procura pacotes em data/sceneassets/mascot/<ID>/.
Não há lista fixa de clubes. Pacotes ausentes ou incompletos mantêm o fotógrafo normal.

## Modelos versionados

Cada pasta numérica precisa de model.rx3 e textures.rx3; model_animated.rx3 é opcional para animação. club.json pode registrar a origem da conversão. IDs: Atlético Mineiro 1035, Flamengo 1043, Palmeiras 383, Cruzeiro 568, Vasco 569. Copie os arquivos convertidos e validados para a pasta do jogo. Modelos/texturas não são distribuídos neste repositório. O instalador copia somente pacotes completos encontrados localmente; nenhum pacote é obrigatório para instalar a DLL.

## Comportamento e desempenho

Uma instância ocupa a área atrás das placas no gol atacado pelo mandante. Troca de lado no intervalo. A posição aprovada (X=±5850 cm, Z=3150 cm) tem 75% de probabilidade na primeira escolha; os demais pontos ficam na mesma linha de fundo, em ambos os lados do mesmo gol. Reinícios reconhecidos no mesmo estádio/clube evitam repetir imediatamente o ponto anterior. A escolha é estável durante a partida. Gol do mandante ativa comemoração por 26 segundos.

Identidade conferida a cada 250 ms, pacotes pelo worker a cada segundo; animação reutiliza o contexto de posicionamento. Não há varredura Lua ou recarga de recursos por quadro.

Idle usa somente o clipe em pé incluído na DLL. Na comemoração do mandante, somente a pose nativa 14:109, confirmada em pé, pode ser copiada; na ausência dela, usa o clipe de comemoração em pé incluído. O filtro atua também depois da adaptação. Poses genéricas da torcida, inclusive transições de sentar, não são utilizadas. CrowdAI é somente lido para o relógio de pausa e a comemoração permitida. Não há hook de atribuição na torcida.

verify.cmd verifica política de posição/postura; tests/run_performance.cmd verifica memória e custo de consultas. Consulte PROMPT_CONVERTER_MASCOTE_FIFA16.md para UV, mipmaps e conversão segura. A transformação UV é V=1-V uma única vez; cada mip DXT5 precisa do seu descritor de 16 bytes.


## Correção de posição — 10/10/2026

A confirmação do lado atacado preserva agora a coordenada lateral sorteada. A escolha deixou de depender exclusivamente da reconstrução dos fotógrafos: o worker de placar publica uma sessão confirmada e o render usa apenas esse contador, sem novas consultas Lua ou recargas por quadro.

Sinais: mudança da identidade nativa; retorno a 0:0 após placar positivo; retorno a 0:0 depois de pelo menos 1,5 s sem identidade válida. Transições precisam persistir 750 ms. Troca de lado não sorteia outro ponto. É necessária validação de reinício, replay e intervalo no jogo; reinício em 0:0 que reutilize todos os objetos nativos e não interrompa a leitura ainda requer um sinal de relógio/estado confirmado.

A locomoção tem estados de idle, virar, andar e comemorar. A espera é de 4–8 s. Antes de sair, vira para o destino sem deslocar. O avanço é calculado a partir dos pés na pose adaptada do modelo, com clipe a 1x; não utiliza a curva antiga de 35,6 cm nem a aceleração artificial de 3x. O registro de entrada +0x1c e o de saída +0x2c recebem o ângulo mantido pelo controlador. Ao chegar, volta a olhar o campo. O relógio de pausa já confirmado pelo usuário foi preservado.


## Dez pontos de referência

X mantém o gol atacado pelo mandante, com módulo de 5850 cm. Z seleciona o lado lateral: +3150, +2700, +2100, +1500, +900, -900, -1500, -2100, -2700, -3150 cm. Coordenadas negativas ficam no outro lado do mesmo gol; não no gol oposto. No intervalo, muda o sinal de X e o ponto lateral é conservado.

A lista única mascotGoalLineDestinations alimenta a seleção de spawn e a caminhada curta entre pontos vizinhos do mesmo fundo de gol.

Validação do sorteio com cinco pontos: logs da nova sessão registraram Z=3150 -> Z=1500 após reiniciar (sessão 1 -> 2). O usuário confirmou a mudança de posição e pés corretos. A ampliação para dez pontos requer nova abertura do FIFA para carregar a DLL atualizada.


## Caminhada, poses em pé e braços — 10/10/2026

Clipes usados: slow_walk_loop_D95 para caminhada; idle_variant e celebrate para poses em pé. O relógio continua sendo uma aproximação pelo movimento observado nas matrizes CrowdAI a cada 50 ms, com janela de 250 ms. Não equivale ao tempo real de replay/câmera lenta. O cache descarta fontes ausentes e reinicia quando a geração da cena ou o objeto da torcida muda.

O Galo (1035) recebeu pintura independente dos dois braços. O classificador usa o lado e a projeção dos vértices sobre as cadeias ombro → braço → antebraço → mão, com transições suaves no ombro, cotovelo e punho. Foram alterados 1.873 vértices (926 de um lado e 947 do outro); pesos somam 255. Cabeça, pernas, posições, normais, UVs, índices e matrizes bind permaneceram iguais. repair_galo_arm_weights.py reproduz o candidato a partir do modelo guardado. Os RX3 do jogo e desenvolvimento são idênticos; backups anteriores estão em U:/fifa 16/ModCarrerMode/source/mascot_arm_repair/backups/20261010_before_arm_weights.

Pré-visualizações de pesos e movimento estão em J:/mods/fifa 16/estudos fifa 16/18_MASCOTE_POSICAO_MOVIMENTO_20261010/. DLL compilada com build.cmd; falta conferir no jogo reiniciado a amplitude dos braços, o giro para caminhar e a ausência de pose sentada.

## Proteção de cena e retirada do hook CrowdAI — 10/10/2026

A revisão 18 remove o CALL interceptado em 4f530aa e todas as escritas de comportamento/dirty no objeto CrowdAI. Fontes ausentes não conservam ponteiros da cena anterior. A leitura de pose usa uma única amostra coerente de matrizes, postura, comportamento e clipe; fontes inválidas interrompem o avanço. Recuperação de falhas não restaura posições por ponteiros antigos. A restauração normal exige renderer, vetor e binding confirmados no callback atual.

O dump das 16:11 registrou execução inválida em dados fora dos módulos. Ele não comprova que o hook do mascote foi a causa. Estas alterações removem os riscos encontrados na revisão 17; a ausência de novo crash precisa ser validada em partida após reiniciar o FIFA. Backup da DLL anterior: U:/fifa 16/ModCarrerMode/backups/mascot_crash_fix_20261010/.

## Locomoção por contato — revisão 19

A antiga seleção do pé mais baixo escolhia o pé em balanço em parte do ciclo. A nova seleção usa o recuo local do pé após skinning. locomotion_feet.bin (1.012 bytes por clube) armazena os centros ponderados de vértices dos dois pés; é opcional, lido uma vez e deve ser gerado novamente após editar malha, rig ou pesos. Sem ele, a DLL usa os ossos dos pés. O mod mantém descoberta por ID sem limitar clubes.

Para gerar marcadores e auditoria: execute audit_locomotion.py com --tools (mascot_rig_adjuster), --study (pasta contendo walk_baked.json), --game (raiz com data/sceneassets/mascot), --output (JSON de auditoria) e --marker-dir (destino por ID). O gerador atual usa a primeira parte da malha, que precisa conter os dois pés. Copie somente locomotion_feet.bin para cada pacote correspondente.

verify_locomotion.cmd recebe a raiz da fixture offline contendo data/sceneassets/mascot/<ID>/bind.bin e locomotion_feet.bin. Exercita os cinco rigs disponíveis, três clipes interpolados, dois sentidos de percurso, giro, chegada, pausa e restauração do ângulo. Esses testes não substituem validação visual no jogo. Estudo completo: J:/mods/fifa 16/estudos fifa 16/18_MASCOTE_POSICAO_MOVIMENTO_20261010/ESTUDO_LOCOMOCAO_E_POSTURA_20261010.md.

Não há foot IK, clipe de virada com pivô, mistura dedicada de contatos ou navegação com colisão por estádio. O corredor permanece atrás das placas na mesma linha de fundo. Validar o trajeto que atravessa o centro do gol antes de afirmar que todos os pontos são seguros em todo estádio.

Install-Locomotion.ps1 instala a DLL e os marcadores com o FIFA fechado, guarda backup e confere os hashes dos modelos antes de copiar dados dos pés. Não inclui modelos/texturas novos.

## Novo Flamengo e transições — revisão 20

O novo pacote 1043 conserva a malha, UV e basecolor JPEG do FBX fornecido em FLAMENGO. O rig Mixamo é mapeado aos 31 ossos FIFA; os dedos são agrupados na mão. A cabeça é rígida com transição restrita ao pescoço. Pesos originais dos braços são conservados, removendo influências do lado oposto. A pose de referência T do FBX é convertida para a pose A do FIFA junto com as matrizes bind, posições, normais e tangentes, antes da exportação. A altura final é 1,80 m. O pacote inclui marcadores de pés recalculados; modelos e texturas est�o versionados.

A pose de caminhada passa para idle com mistura de 450 ms; outras trocas usam 350 ms. As rotações são interpoladas por quaternion e as posições por interpolação linear com curva suave. A correção vertical dos centros dos pés usa filtro de 80 ms. O giro é aplicado uma vez às matrizes privadas do mascote, com os dois ângulos nativos do registro zerados. As transições e o giro usam o relógio de animação já existente, preservando a pausa. A comemoração da torcida 14:109 continua disponível, com alternativa em pé e duração de 26 segundos.

Renders, conversor, auditoria RX3 e originais de backup: J:/mods/fifa 16/estudos fifa 16/19_FLAMENGO_NOVO_MASCOTE_20261010. A DLL compilou; a conferência visual de tremor, giro e chegada com esta revisão ainda depende de teste no jogo reiniciado.

## Revis�o 21 � paradas e percurso

Cada chegada e o in�cio do percurso t�m 20 segundos de espera no rel�gio de anima��o: idle durante 4 segundos, intera��o/comemora��o em p� durante 12 segundos e idle nos 4 segundos finais. A comemora��o de gol do mandante continua com prioridade e dura��o de 26 segundos. Depois dela come�a uma nova espera de 20 segundos.

O sorteio usa uma bolsa dos dez destinos: nenhum destino se repete antes de visitar os demais; a posi��o atual � exclu�da tamb�m na mudan�a de ciclo. Destinos distantes podem exigir caminhada por pontos intermedi�rios.

Replay: pausar congela posi��o, fase e espera. A leitura atual das matrizes da torcida n�o informa o sentido do tempo. Duas capturas pausadas antes/depois do recuo n�o confirmaram um rel�gio de replay; retroceder as anima��es ainda n�o � implementado. Nenhum endere�o de rel�gio n�o confirmado foi aplicado ao jogo.

As malhas RX3, texturas e marcadores dos cinco clubes est�o em data/sceneassets/mascot/. assets/originals/FLAMENGO preserva o FBX e as texturas de origem; assets/animations guarda os tr�s clipes baked, canais de caminhada, idle e comemora��o e refer�ncia de rig. assets/manifest.json registra tamanho e SHA256 dos arquivos. Os modelos originais dos demais clubes n�o foram localizados nesta etapa; os RX3 convertidos est�o preservados.

## Revis�o 22 � Vasco e novos tempos

A espera passou para 30 segundos por destino: 7,5 segundos de idle, 15 segundos de intera��o/comemora��o em p� e 7,5 segundos de idle. Gol do mandante tem prioridade e tamb�m usa 15 segundos de comemora��o. O sorteio continua sem repetir destinos antes de passar pelos dez pontos. A limita��o de recuo no replay permanece.

Vasco da Gama usa o ID 569. O novo FBX tem um �nico esqueleto Mixamo de 65 ossos e pintura de pesos. A malha e UV originais foram preservadas; os pesos existentes foram mapeados para 31 ossos FIFA, agrupando dedos na m�o. Face/barba/chap�u usam a cabe�a r�gida com transi��o no pesco�o, cujos limites s�o obtidos do pr�prio esqueleto. O ajuste da pose T para A foi aplicado a malha, normais, tangentes e bind. Altura final: 1,80 m.

Os RX3 e texturas est�o em data/sceneassets/mascot/569; o FBX e mapas originais, em assets/originals/VASCO; convers�o, inspe��o, auditoria e tr�s renders de poses, em assets/conversion/VASCO. Os scripts de convers�o registram os caminhos das ferramentas e do estudo locais; a compila��o da DLL n�o depende deles. Os marcadores de p�s foram recalculados para esta malha. A auditoria offline verifica 5.803 v�rtices, 9.562 tri�ngulos, pesos somando 255, 31 ossos, mipmaps e poses finitas. A confer�ncia visual final em partida depende de iniciar o jogo.

### Ajuste da barba do Vasco

A regi�o conectada da barba, incluindo seus tons escuros e a ponta, acompanha o osso da cabe�a. Foram modificados somente os �ndices/pesos de 272 v�rtices; o contorno da barba cont�m 482 v�rtices j� r�gidos ou corrigidos. A sele��o usa posi��o frontal, cor e componente espacial para excluir o escudo da camisa. A transi��o original do pesco�o fora da barba foi preservada. A auditoria confirma pesos somando 255 e aus�ncia de mudan�as na malha, normais, tangentes, UV, �ndices e bind.

repair_vasco_beard_weights.py recebe --package (pasta contendo o modelo animado e texturas) e --output (pasta separada). Para regenerar, execute-o ap�s convert_vasco.py e antes de prepare_package.py; substitua os dois modelos do pacote pelos candidatos validados. A ferramenta RX3 local pode ser indicada em FIFA_RX3_TOOLS. Renders de idle, caminhada e comemora��o foram conferidos novamente.
