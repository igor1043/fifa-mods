# Ambientes 3D — FIFA 16

Execute **Visualizar.cmd** ou **Ambientes3D-v20.exe**. **Academia.cmd** e **CT-Treinamento.cmd** abrem os novos ambientes; **Vestiario.cmd** abre diretamente o vestiário e **Cenas-Vestiario.cmd** abre sua biblioteca cinematográfica. Não precisa abrir o FIFA nem instalar Python, navegador ou programa adicional. Os fontes e backups foram preservados; executáveis movidos pelo usuário não foram restaurados. Os recursos de edição de esqueleto e FBX continuam disponíveis; veja **RIGGING.md**.

O executável reutiliza o decodificador RX3/BIG, as receitas de poses e o renderizador Direct3D 11 do mod. Modelos, uniformes, rostos, texturas, escudos e cadastro de clubes/jogadores são lidos de `U:\fifa 16`. Os ambientes são cenas 3D procedurais; não são ambientes originais extraídos do FIFA nem imagens geradas por IA. O vestiário possui uma construção própria do visualizador.

## Biblioteca

Para a revisão da **coletiva**, abra **Sala-Imprensa.cmd** (press08). São cinco lugares configuráveis, 48 assentos de público, modelos nativos variados, palco/saída lateral, iluminação interna e patrocinadores sem achatamento. **Coletiva-Final-Exemplo.cmd** abre o exemplo com cinco participantes e troféu. Veja [SALA-IMPRENSA.md](SALA-IMPRENSA.md).

A biblioteca tem três áreas: **Ambientes**, **Cenas** e **Animações**. Um ambiente reúne sua sala e os objetos; as cenas definem enquadramentos e movimentos da câmera; as animações são movimentos/esqueletos das pessoas. Os IDs das visualizações mantidas continuam compatíveis com os XML existentes. **Chegada à coletiva foi retirada da biblioteca**; seu antigo ID 2 permanece reservado e XML dessa cena recebe um aviso, sem ser reinterpretado como academia.

- Sala de imprensa: técnico do clube e jogador à mesa, quando os respectivos modelos estiverem disponíveis.
- Vestiário: 24 armários em U, uniformes de costas com nome/numeração, bancos acolchoados, quadro tático e quadro negro, mesa do técnico, bolas nativas, hidratação e área médica.
- Academia: dois andares, mezanino com escada e guarda-corpo, força, cardio, mobilidade, pesos, bolas, hidratação e fachada de vidro.
- CT de treinamento: campo completo, gols com redes, marcações, cercamento, arquibancada, bancos, refletores, barreiras, cones, bolas e apoio do treinador.
- Jogador individual: todas as poses individuais do catálogo.
- Técnico individual: poses em pé e sentado do modelo específico do clube.
- Foto da equipe: até onze jogadores do elenco instalado e as poses coletivas disponíveis.

Escolha o clube e, quando aplicável, o jogador. Um técnico ausente não é trocado por um modelo de outro clube. O elenco é o **banco instalado**, não a progressão do save de carreira aberto.

## Academia e CT integrado

Os ambientes são construções 3D genéricas, personalizadas com as cores e o escudo do clube escolhido. **Não são uma reprodução do CT real do Flamengo ou de outro clube.** A academia e o campo pertencem ao mesmo espaço: a vista através da vidraça é geometria real, não uma imagem de fundo. A academia mede aproximadamente 27 × 18 m, com pé-direito de 7,2 m; o campo tem 105 × 68 m.

A academia tem quatro racks com bancos e barras, três estações de cabos, dois conjuntos de halteres, quatro esteiras, quatro bicicletas, seis tapetes de mobilidade, rolos, kettlebells, dez medicine balls e hidratação. O CT inclui seis bonecos de barreira, 24 cones, dez mini-barreiras, escada de agilidade, 19 bolas FIFA, carrinho de bolas, lousa móvel e carrinho do treinador. A bola reutiliza a resolução de liga do vestiário, com fallback nativo; não acompanha automaticamente uma copa do save.

**Vistas do ambiente** oferece cinco enquadramentos para cada ambiente. **Ir para o CT externo / Ir para a academia** alterna entre os dois; também é possível percorrer tudo com câmera livre. **Abrir teto e paredes da academia** facilita a inspeção. Os ajustes de objetos são independentes por XML, com grupos por equipamento. Salve antes de trocar de ambiente para conservar suas alterações. Os aparelhos são modelos estáticos: não há atletas treinando ou animação das máquinas nesta versão.

Há três cenas cinematográficas na academia (visita completa, mezanino/cardio e travessia da vidraça) e três no CT (apresentação, finalização e apoio do treinador). Play, pausa, repetição, linha do tempo e edição dos pontos continuam disponíveis. **Parar / câmera livre** devolve o controle manual.

Luz interna e luz do dia usam cálculos distintos. A sombra principal vem do teto na visualização da academia e do sol na visualização externa; as outras luminárias são preenchimento, sem mapas de sombra individuais. Não é ray tracing. As texturas procedurais do novo ambiente têm mipmaps e as capturas da interface usam supersampling para melhorar linhas e detalhes.

Fontes: `src/viewer_training_center.{h,cpp}`; catálogo de filmagens: `src/viewer_cinematics.cpp`. Presets: `academia.xml` (tipo 6) e `ct-treinamento.xml` (tipo 7), criados ao salvar. Backup anterior: `backups/20261004-academia-ct`. `Testar-Academia-CT.cmd` valida dois clubes, geometria, transparência, dez vistas, seis filmagens e XML. Nada foi instalado no Dev ou no jogo.

## Cenas cinematográficas

Em **Ambientes → Vestiário → Cenas**, selecione uma composição e clique em **Reproduzir cena**. Há oito cenas prontas: apresentação da sala, passeio pelos armários, uniforme em destaque, mesa e plano de jogo, hidratação e equipamentos, cuidados e recuperação, quadros de análise e uma sequência completa de TV com cortes/fade. A sala de imprensa também oferece duas composições de câmera.

**Pausar**, **Parar / câmera livre**, repetição, velocidade e linha do tempo ficam acima do render. Durante o play, a câmera livre e os ajustes são bloqueados; ao pausar, é possível inspecionar. Parar restaura a câmera anterior. O uniforme em destaque acompanha o atleta escolhido entre os 24 armários carregados. Não há jogador andando dentro do vestiário: essa tomada foca sua camisa, número e nome.

Para criar uma cena:

1. Na aba de edição **Cenas**, crie uma cena com a câmera atual ou duplique uma composição pronta.
2. Escolha o ponto, posicione a câmera livre e clique em **Gravar câmera neste ponto**.
3. Adicione pontos e ajuste seus tempos. O primeiro fica em zero; os demais precisam ser crescentes. Escolha movimento suave, linear ou corte com fade para chegar ao ponto.
4. Reproduza a cena e use **SALVAR CENA**. O botão fica separado do painel rolável de edição.

Os enquadramentos ficam no XML da cena e em `presets/biblioteca-cenas.xml`, que é reaberto automaticamente. A biblioteca reúne cenas personalizadas por ambiente; um XML explicitamente aberto tem prioridade sobre a cópia da biblioteca. Os arquivos anteriores são preservados em `.bak` ao sobrescrever. Limites: 100 cenas personalizadas, 256 pontos por cena e 10 minutos por cena. XML com cenas de câmera usa versão 3; os formatos 1/2 continuam aceitos.

As curvas interpolam posição, alvo e lente, com aceleração/desaceleração suave e sem ultrapassar os pontos por eixo. Cortes usam um fade curto. A reprodução muda apenas a câmera: não reconstrói nem envia toda a geometria a cada quadro. Cenas personalizadas usam coordenadas absolutas; ajuste seus pontos se mover objetos do ambiente. Não há exportação de vídeo; os PNG são capturas reais do renderizador.

O código está separado em `viewer_dressing_room` (ambiente), `viewer_cinematics` (catálogo, curvas e biblioteca), `viewer_animation` (poses-chave/FBX) e `viewer_core` (câmera e XML), com interface em `main.cpp`. Backup anterior: `backups/20261004-biblioteca-cenas`.

## Vestiário

O ambiente usa as cores e o escudo do clube escolhido, com base branca e piso emborrachado. O chão exibe somente o escudo, sem círculo ou moldura. Camisas, chuteiras, fontes de numeração e bolas reutilizam recursos do FIFA; os números e nomes vêm do elenco instalado. O cabide acompanha a gola e os ombros da malha real. Clubes com menos de 24 modelos mantêm os armários restantes como reserva.

A bola é resolvida pela liga do clube e pelas atribuições do jogo, com recurso nativo padrão como fallback. Essa seleção não acompanha automaticamente a copa da próxima partida de um save. O quadro negro e a tela do notebook são elementos decorativos de análise, não estatísticas reais do save.

As vistas **Sala**, **Armários**, **Quadro** e **Diagonal** ficam disponíveis em **Inspeção e vistas fixas**. Em **Mais vistas**, escolha hidratação, área médica, escudo no piso, mesa ou quadro negro. **Ver vestiário completo** abre uma vista de inspeção sem teto/laterais, mantendo os objetos; também é possível percorrer a sala com câmera livre.

As vistas fixas ficam agrupadas em **Inspeção e vistas fixas**. A parede do quadro negro, junto à porta, foi recuada em 1,60 m com porta, placas, primeiros socorros e hidratação. Piso, teto e iluminação acompanham a extensão; o banco em frente à lousa foi removido. A hidratação tem bancada mais larga, bandeja, toalhas, copos, refrigerador e bebedouro separado. A mesa principal usa textura de madeira de 1024×512 com veios/poros, UVs proporcionais ao tampo, borda arredondada e apoio do notebook.

O sombreamento usa uma luz de teto com sombra real, luzes de preenchimento internas e luminárias emissivas. Não é iluminação solar nem ray tracing; as luzes secundárias não possuem mapas de sombra individuais. As bordas dos estofados, maca, carrinhos e mesa têm geometria arredondada.

Backup anterior a estas mudanças: `backups/20261004-vestiario-hidratacao-medica-piso`. Nada é instalado no jogo ou no Dev automaticamente.

## Câmera

- Arrastar com o botão esquerdo: orbitar, no modo órbita.
- Arrastar com o botão direito: mudar a direção da câmera.
- Roda: aproximar e afastar; no modo livre, desloca a câmera para a frente/trás.
- Botão do meio: deslocar lateralmente e verticalmente.
- Clique na vista para dar foco. **WASD**: deslocamento; **Q/E**: descer/subir; **Shift**: acelerar.
- **F**: alternar livre/órbita. **R**: reenquadrar.
- Com a vista em foco, controle Xbox: analógico esquerdo desloca; direito olha; gatilhos descem/sobem.
- A câmera livre não tem colisão: é possível entrar no ambiente e nos objetos para inspeção.

## Ajustes e arquivos

Aba **Pose**: selecione uma articulação e ajuste rotação local X/Y/Z, deslocamento e escala. O ajuste ocorre no esqueleto real antes da deformação da malha, sem editar o RX3. Mostrar ossos ajuda a inspecionar mãos, braços e cotovelos; clique em um ponto na vista para selecioná-lo. Ossos auxiliares podem ser habilitados à parte. Na coletiva, escolha técnico ou jogador. Deslocamento e escala podem deformar a anatomia: use pequenos ajustes e o botão de restauração.

Aba **Objetos**: visibilidade, deslocamento, rotação e escala por peça/nome da cena. Peças agrupadas com o mesmo nome são transformadas juntas. Isso não é um editor de topologia ou de texturas.

**Salvar cena XML** guarda câmera, seleção, correções de pose e objetos. **Abrir XML** reaplica os ajustes. Cada sobrescrita guarda o XML anterior em `.bak`. Presets não são aplicados ao jogo; para levar uma correção aprovada ao mod é necessária uma mudança explícita no Dev.

Na coletiva, o XML também preserva se os ajustes pertencem ao técnico ou ao jogador. Salve os presets dentro desta pasta; destinos na pasta do jogo são recusados. Ao abrir um XML externo, use **Salvar como** para guardá-lo em `presets/`.

**Exportar imagem PNG** salva a renderização real da vista atual em `renders/`. Não confundir essas imagens com os conceitos gerados anteriormente.

## Editar jogadores dentro da foto da equipe

1. Abra **Foto da equipe** e clique no corpo ou na cabeça de um jogador. A seleção considera os triângulos 3D e a profundidade; clicar no vazio não troca o jogador. Arrastar continua orbitando a câmera, sem trocar a seleção.
2. O jogador fica destacado com seu **nome e número**, e pode ser selecionado também na lista **Jogador na foto**.
3. Na aba **Pessoa**, ajuste a posição, rotação ou escala do jogador inteiro. **Pose individual** permite substituir apenas sua postura; **Manter pose da foto** conserva sua posição em pé/agachado e o estilo coletivo original.
4. Clique em **Editar esqueleto**, ou abra **Pose**, para ajustar suas articulações. Os ossos mostrados são apenas os do jogador selecionado, nas mesmas coordenadas do modelo. Clique em um ponto para selecionar o osso. Cada jogador possui correções independentes.
5. **Enquadrar pessoa** aproxima a câmera desse atleta. **Restaurar esta pessoa** desfaz apenas os ajustes dele.
6. Use **Salvar cena XML** para salvar no arquivo atual, ou **Salvar como** para criar outra cena. Ao entrar pela biblioteca, a foto usa `presets/foto-equipe.xml`; ao abrir um XML existente, salvar atualiza esse mesmo XML, com backup `.bak`.

As correções são vinculadas ao ID do jogador, não à posição na lista. Mover ou ajustar um atleta não altera os outros, e a pose-base das outras telas não é modificada. Os presets com ajustes individuais usam o formato XML 2; esta versão também abre presets antigos de formato 1. Executáveis anteriores recusam o formato 2, para evitar perder as correções ao resalvar.

Na foto, use **Jog.** para mover o jogador inteiro, em vez de alterar globalmente peças com nomes iguais. O editor por peças da aba Objetos fica disponível nas outras cenas. O elenco ainda vem do banco instalado, não do save de carreira. Nenhuma correção é gravada automaticamente no jogo ou no Dev.

## Poses-chave e animações

Nas cenas **Jogador individual** e **Técnico individual**, a aba **Anim.** oferece linha do tempo, reprodução, pausa, repetição e velocidade.

Para criar um movimento:

1. Escolha a pose-base. Na aba Pose, faça os ajustes iniciais.
2. Na aba Anim., coloque o tempo em 0 e clique em **Gravar pose neste tempo**.
3. Avance o tempo, volte a Pose, altere as articulações e grave outro quadro.
4. Com pelo menos dois quadros, clique em **Reproduzir**. Rotações, deslocamentos e escalas são interpolados entre as poses-chave.
5. Salve um XML para preservar o movimento. Para substituir um quadro, grave novamente no mesmo tempo. Para excluí-lo, use X ao lado do quadro.

`presets/exemplo-movimento-braco.xml` é um exemplo mínimo de movimento criado com poses-chave. **Não é uma animação original do FIFA.** Abra-o na ferramenta e selecione Anim. para reproduzir. Os quadros são correções sobre a pose-base escolhida, não um novo arquivo nativo de animação.

### Importar FBX / Mixamo — experimental

**Importar FBX...** lê FBX ASCII/binário com o leitor ufbx incorporado ao executável. Não exige instalação de Blender, Python ou Autodesk. Apenas o esqueleto e a animação são utilizados: a malha externa não substitui a malha FIFA.

O mapeamento reconhece nomes comuns do Mixamo, como `mixamorig:LeftArm`, e permite corrigir manualmente cada correspondência FIFA/origem. Escolha o clip do arquivo, ajuste o tempo e habilite **Aplicar movimento importado**. A transferência preserva os comprimentos dos ossos do FIFA; o deslocamento horizontal da raiz é opcional. O XML guarda o caminho do FBX e o mapa de ossos, não uma cópia embutida do FBX. Mantenha o arquivo original nesse caminho ao reabrir o preset.

Estado da validação: o leitor foi testado com fixtures animadas ASCII/binário e com o humanoide **Sad Idle.fbx** enviado pelo usuário. A edição `rig05` alinha a referência, coluna, braços e mãos e preserva comprimentos: 85 instantes conferidos no jogador e no técnico FIFA. Consulte **RIGGING.md** para métricas, diferenças entre os esqueletos e limitações. Não há garantia automática de compatibilidade com qualquer rig. Não há exportação/conversão para RX3, ANT ou CBAC, nem aplicação no jogo.

### Animações originais do FIFA

A aba **FIFA → Buscar nos arquivos do jogo** cataloga bancos de animação presentes nos arquivos BIG e na pasta data. Na instalação testada foram encontrados 52 recursos. **É somente um inventário: ANT/CBAC ainda não têm decodificação/reprodução validada neste visualizador.** A lista não representa 52 clipes individuais; cada banco pode conter vários movimentos. Não confundir a reprodução FBX ou as poses-chave do editor com esses bancos originais.

```text
ambientes 3d/
├── Ambientes3D-v20.exe    edição atual com academia e CT
├── Ambientes3D-v*.exe     etapas recentes preservadas
├── Visualizar.cmd        atalho para abrir
├── Vestiario.cmd         abre diretamente o vestiário
├── Academia.cmd          academia, mezanino e vista do campo
├── CT-Treinamento.cmd    campo e equipamentos de treino
├── Compilar.cmd          recompilar (somente desenvolvimento)
├── Testar.cmd            executar verificações isoladas
├── config/               caminho do FIFA e cena inicial
├── presets/              configurações XML salvas pelo usuário
├── renders/              imagens exportadas
├── src/                  visualizador, dados, câmera e ajustes
├── third_party/ufbx/     leitor FBX, licença e origem
├── scripts/              build isolado
├── tests/fixtures/        arquivos de teste FBX (não são assets FIFA)
├── tests/resultados/     testes e prévias reais
├── backups/              versões preservadas antes das mudanças
└── build/                objetos compilados e adaptadores privados
```

## Desenvolvimento

`Compilar.cmd` usa os Build Tools já instalados. Lê o código organizado em `ModCarrerMode/source/career_native`, mas não altera nenhum arquivo do Dev ou do jogo. Os adaptadores privados ficam em `build/<nome-do-executável>/engine`; mudanças inesperadas no renderizador interrompem a compilação, em vez de aplicar substituições silenciosas. A origem e hashes ficam em `build/<nome-do-executável>/engine-origin.json`.

Depois de compilado, o executável não depende da pasta de código do mod, somente da pasta do jogo indicada no XML e, opcionalmente, do FBX importado. Usa bibliotecas do Windows e CRT estático. Os testes ficam separados: `Ambientes3D-v20.exe --self-test` e `--test-training`. Prévia da interface: `Ambientes3D-v20.exe --capture-ui "caminho-absoluto.png" --scene 6 --library scenes --cinematic gym-gallery`. Também aceita `--preset "arquivo.xml"`, `--tab pose|animation|fifa`, `--bones` e `--time 1`. As capturas são quadros do renderizador real. As duas suítes passaram nesta edição; resultados em `tests/resultados/testes.txt` e `academia-ct-testes.txt`.

Nenhuma DLL é injetada, nenhum processo do FIFA é modificado, e nenhum banco, save ou recurso instalado é escrito. Reprodução de animações originais do FIFA e exportação de animações ao jogo ainda não estão disponíveis.
