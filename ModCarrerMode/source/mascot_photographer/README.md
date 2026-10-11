# Mascote na linha de fundo

Compile com build.cmd. Plugin ativo: ModCarrerMode/mods/mascot_single/mascot_goal_line_v22.dll.
Somente uma versão do plugin deve estar em enabled.txt. A cópia sem sufixo é mantida como artefato de compilação.
A DLL usa o ID do mandante e procura pacotes em data/sceneassets/mascot/<ID>/.
Não há lista fixa de clubes. Pacotes ausentes ou incompletos mantêm o fotógrafo normal.

## Modelos versionados

Cada pasta numérica precisa de model.rx3 e textures.rx3; model_animated.rx3 é opcional para animação. club.json registra a origem da conversão. Os modelos, texturas e marcadores estão versionados em data/sceneassets/mascot/. IDs: Atlético Mineiro 1035, Athletico-PR 1039, Corinthians 1041, Flamengo 1043, Palmeiras 383, Cruzeiro 568, Vasco 569, Bahia 1598, Fortaleza 111052, Remo 130026, Santa Cruz 111058, São Paulo 598, Vitória-BA 1719 e Paulista de Jundiaí 130066. Os IDs novos foram conferidos nos bancos locais do jogo e do desenvolvimento; Remo e Paulista usam IDs do banco customizado. Copie os pacotes completos para a pasta do jogo antes de usar Install-Locomotion.ps1.

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

O novo pacote 1043 conserva a malha, UV e basecolor JPEG do FBX fornecido em FLAMENGO. O rig Mixamo Ã© mapeado aos 31 ossos FIFA; os dedos sÃ£o agrupados na mÃ£o. A cabeÃ§a Ã© rÃ­gida com transiÃ§Ã£o restrita ao pescoÃ§o. Pesos originais dos braÃ§os sÃ£o conservados, removendo influÃªncias do lado oposto. A pose de referÃªncia T do FBX Ã© convertida para a pose A do FIFA junto com as matrizes bind, posiÃ§Ãµes, normais e tangentes, antes da exportaÃ§Ã£o. A altura final Ã© 1,80 m. O pacote inclui marcadores de pÃ©s recalculados; modelos e texturas estão versionados.

A pose de caminhada passa para idle com mistura de 450 ms; outras trocas usam 350 ms. As rotações são interpoladas por quaternion e as posições por interpolação linear com curva suave. A correção vertical dos centros dos pés usa filtro de 80 ms. O giro é aplicado uma vez às matrizes privadas do mascote, com os dois ângulos nativos do registro zerados. As transições e o giro usam o relógio de animação já existente, preservando a pausa. A comemoração da torcida 14:109 continua disponível, com alternativa em pé e duração de 26 segundos.

Renders, conversor, auditoria RX3 e originais de backup: J:/mods/fifa 16/estudos fifa 16/19_FLAMENGO_NOVO_MASCOTE_20261010. A DLL compilou; a conferência visual de tremor, giro e chegada com esta revisão ainda depende de teste no jogo reiniciado.

## Revisão 21 — paradas e percurso

Cada chegada e o início do percurso têm 20 segundos de espera no relógio de animação: idle durante 4 segundos, interação/comemoração em pé durante 12 segundos e idle nos 4 segundos finais. A comemoração de gol do mandante continua com prioridade e duração de 26 segundos. Depois dela começa uma nova espera de 20 segundos.

O sorteio usa uma bolsa dos dez destinos: nenhum destino se repete antes de visitar os demais; a posição atual é excluída também na mudança de ciclo. Destinos distantes podem exigir caminhada por pontos intermediários.

Replay: pausar congela posição, fase e espera. A leitura atual das matrizes da torcida não informa o sentido do tempo. Duas capturas pausadas antes/depois do recuo não confirmaram um relógio de replay; retroceder as animações ainda não é implementado. Nenhum endereço de relógio não confirmado foi aplicado ao jogo.

As malhas RX3, texturas e marcadores dos cinco clubes estão em data/sceneassets/mascot/. assets/originals/FLAMENGO preserva o FBX e as texturas de origem; assets/animations guarda os três clipes baked, canais de caminhada, idle e comemoração e referência de rig. assets/manifest.json registra tamanho e SHA256 dos arquivos. Os modelos originais dos demais clubes não foram localizados nesta etapa; os RX3 convertidos estão preservados.

## Revisão 22 — Vasco e novos tempos

A espera passou para 30 segundos por destino: 7,5 segundos de idle, 15 segundos de interação/comemoração em pé e 7,5 segundos de idle. Gol do mandante tem prioridade e também usa 15 segundos de comemoração. O sorteio continua sem repetir destinos antes de passar pelos dez pontos. A limitação de recuo no replay permanece.

Vasco da Gama usa o ID 569. O novo FBX tem um único esqueleto Mixamo de 65 ossos e pintura de pesos. A malha e UV originais foram preservadas; os pesos existentes foram mapeados para 31 ossos FIFA, agrupando dedos na mão. Face/barba/chapéu usam a cabeça rígida com transição no pescoço, cujos limites são obtidos do próprio esqueleto. O ajuste da pose T para A foi aplicado a malha, normais, tangentes e bind. Altura final: 1,80 m.

Os RX3 e texturas estão em data/sceneassets/mascot/569; o FBX e mapas originais, em assets/originals/VASCO; conversão, inspeção, auditoria e três renders de poses, em assets/conversion/VASCO. Os scripts de conversão registram os caminhos das ferramentas e do estudo locais; a compilação da DLL não depende deles. Os marcadores de pés foram recalculados para esta malha. A auditoria offline verifica 5.803 vértices, 9.562 triângulos, pesos somando 255, 31 ossos, mipmaps e poses finitas. A conferência visual final em partida depende de iniciar o jogo.

### Ajuste da barba do Vasco

A região conectada da barba, incluindo seus tons escuros e a ponta, acompanha o osso da cabeça. Foram modificados somente os índices/pesos de 272 vértices; o contorno da barba contém 482 vértices já rígidos ou corrigidos. A seleção usa posição frontal, cor e componente espacial para excluir o escudo da camisa. A transição original do pescoço fora da barba foi preservada. A auditoria confirma pesos somando 255 e ausência de mudanças na malha, normais, tangentes, UV, índices e bind.

repair_vasco_beard_weights.py recebe --package (pasta contendo o modelo animado e texturas) e --output (pasta separada). Para regenerar, execute-o após convert_vasco.py e antes de prepare_package.py; substitua os dois modelos do pacote pelos candidatos validados. A ferramenta RX3 local pode ser indicada em FIFA_RX3_TOOLS. Renders de idle, caminhada e comemoração foram conferidos novamente.

## Seis clubes adicionais — 10/10/2026

Bahia (1598), Fortaleza (111052), Remo (130026), Santa Cruz (111058), São Paulo (598) e Vitória-BA (1719) usam os FBX fornecidos. Cada arquivo tem um esqueleto Mixamo de 65 ossos e pesos pintados; esses pesos foram preservados e adaptados aos 31 ossos FIFA. Cabeça/face e membros usam limites derivados do próprio esqueleto. UVs, pintura de cor e mapa normal são conservados; a pose T foi convertida para A e a altura normalizada para 1,80 m. Difusão usa DXT5 com mipmaps até 1x1, no máximo 2048; normal usa até 1024. Os marcadores dos pés foram recalculados por modelo.

Originais em assets/originals/<pasta>; auditoria e imagens em assets/conversion/<pasta>. Cada preview compara o FBX original com repouso, caminhada e comemoração calculados a partir do RX3 final. A revisão visual é offline, não uma captura do FIFA. Os seis rigs passaram em teste de locomoção nos dois sentidos, postura em pé, contato dos pés, pausa, giro, parada de 30 segundos, interação de 15 segundos e dez destinos antes de repetição. A confirmação final de render/material e posicionamento no estádio depende de abrir uma partida de cada mandante.

A evidência do banco, inspeção de origem e hashes da instalação estão em assets/conversion/six_clubs_20261010/. Nenhum banco foi alterado. O plugin descobre os pacotes pelo ID sem recompilar uma lista de clubes.

### Reproduzir a conversão

São necessários Blender 4.4, Python com NumPy/Pillow e a ferramenta local mascot_rig_adjuster (Build-MascotFromFbx.py, assets/template_model_animated.rx3, vendor/rx3tools e texture_assets.py). O caminho das ferramentas é parâmetro; neste computador ficam em J:/mods/fifa 16/02_Ferramentas/mascot_rig_adjuster. Use uma saída separada, valide e só então copie os cinco arquivos do pacote para jogo e desenvolvimento.

Exemplo a partir da raiz do repositório, no PowerShell:

```powershell
$taskTools = 'J:/mods/fifa 16/02_Ferramentas/mascot_rig_adjuster'
$taskScripts = 'ModCarrerMode/source/mascot_photographer'
$taskSource = "$taskScripts/assets/originals/BAHIA"
$taskClips = "$taskScripts/assets/animations"
$taskOutput = 'J:/mods/fifa 16/estudos fifa 16/rebuild_bahia'
& 'C:/Program Files/Blender Foundation/Blender 4.4/blender.exe' --background --factory-startup --python-exit-code 1 --python "$taskScripts/Build-AuthoredMascot.py" -- --source $taskSource --output $taskOutput --tools $taskTools --clips $taskClips --club-id 1598 --club-name Bahia
python "$taskScripts/Prepare-AuthoredMascot.py" --source $taskSource --output $taskOutput --tools $taskTools --clips $taskClips --club-id 1598 --club-name Bahia --texture-template 'data/sceneassets/mascot/1035/textures.rx3'
```

Os parâmetros correspondentes dos outros clubes constam em assets/conversion/six_clubs_20261010/clubs.json. Render-AuthoredMascot.py refaz as quatro imagens com --source, --output e --tools, após os dois passos acima.

verify_locomotion.cmd aceita a raiz da fixture e uma lista opcional de IDs; sem lista mantém os cinco clubes anteriores. Os binds das fixtures são as 31 matrizes do RX3 em float32, conservando a disposição original com translação nos índices 12–14; os marcadores são cópias dos respectivos pacotes. A execução desta etapa usou os seis IDs acima.

### Ativação da revisão 22

A DLL atual foi preparada como mascot_goal_line_v22.dll em jogo e desenvolvimento. O enabled.txt tem uma única entrada de mascote e conserva as outras DLLs. O processo aberto não recebeu uma segunda injeção; a nova DLL passa a valer na próxima abertura do FIFA. Install-Locomotion.ps1 continua exigindo o jogo fechado para futuras substituições e normaliza entradas de versões anteriores para evitar duplicação. Espera atual: 30 segundos por ponto, com 15 segundos de interação; comemoração de gol também dura 15 segundos. Pausa congela o mascote; recuo das animações no replay continua sem implementação.

## Novos modelos e pintura — 11/10/2026

Athletico-PR (1039), Corinthians (1041) e Paulista de Jundiaí (130066) foram adicionados. Cruzeiro (568) e Atlético Mineiro (1035) receberam os novos FBX fornecidos. Santa Cruz (111058) conserva o FBX anterior e usa a nova pintura PNG da subpasta SANTA+CRUZ, conforme solicitado. A escolha explícita de textura fica em input_selection.json; Prepare-AuthoredMascot.py e Render-AuthoredMascot.py aceitam --basecolor para reproduzir essa escolha. Os IDs foram conferidos nos dois bancos locais, usando o deslocamento +1 definido na metadata; nenhum banco foi alterado.

Os seis originais estão em assets/originals, incluindo o ZIP do Paulista. Auditorias, renders e parâmetros estão em assets/conversion/<clube>. A pasta histórica five_clubs_20261011 reúne também o Atlético Mineiro, totalizando seis modelos nesta etapa. Cada pacote tem cinco arquivos; os 14 clubes instalados totalizam 70 arquivos conferidos entre jogo e desenvolvimento. O plugin continua descobrindo os pacotes por ID, sem nova DLL para cada mascote.

### Mandíbula do Corinthians

A frente do queixo já acompanhava a cabeça, mas vértices laterais ainda recebiam influência do pescoço e dos ombros, inclusive pontos com peso de cabeça zero. repair_corinthians_head_weights.py remove essas influências na mandíbula/barba e no contorno inferior do cabelo dentro de uma região delimitada, preservando a geometria, UV, normais, tangentes, índices, bind e pesos do restante do corpo. O osso da cabeça não foi deslocado. São 383 vértices corrigidos; pesos somam 255. A auditoria independente inclui 192 vértices de pele da face inferior. Em 12 poses dos três clipes, o erro máximo de forma dos pontos corrigidos caiu de até 5,65 cm para menos de 0,0001 cm.

Para reproduzir, execute a conversão genérica em uma pasta separada, prepare suas texturas, depois execute assets/conversion/CORINTHIANS/repair_corinthians_head_weights.py com --package, --output e --tools. Copie os dois modelos candidatos para o pacote e rode Prepare-AuthoredMascot.py novamente para recalcular poses, marcadores e hashes; Render-AuthoredMascot.py produz a revisão visual. head_weights_report.json e head_comparison.png documentam a correção final. A validação é offline; reinicie o FIFA para descarregar os recursos antigos e conferir a animação em partida.

### Novo Atlético Mineiro

O modelo aprovado tem 6.356 vértices exportados, 10.004 triângulos e rig adaptado a 31 ossos. O FBX tinha um único vértice sem pintura na cintura. Build-AuthoredMascot.py --repair-unweighted interpolou somente esse ponto a partir de três vizinhos já pintados a menos de 1,36 cm; o arquivo original foi preservado. A opção é explícita e rejeita vizinhos além de 2 cm. O rig e a locomoção passaram nos testes offline em ambos os sentidos, incluindo pausa, giro, parada de 30 segundos, interação de 15 segundos e dez destinos antes de repetir. Use --python-exit-code 1 ao executar os scripts no Blender para que erros de Python também interrompam a conversão.
