# Editor de cenas FIFA Friends

Bancada local fora da instalação do FIFA. Abra **Abrir bancada.cmd** ou o endereço
aberto pelo iniciador. A biblioteca inicial tem os 11 titulares do Flamengo
extraídos para este estudo, com os modelos e esqueletos reais de 400 ossos.

## Montar uma cena

- **Adicionar jogador** usa o jogador escolhido na biblioteca. **Duplicar** cria
  uma cópia com esqueleto independente. **Remover**, **Cena vazia** e **Os 11**
  permitem organizar a composição.
- Clique no corpo ou no nome na lista para selecionar. **Jogador** movimenta o
  ator inteiro. **Esqueleto** permite selecionar pontos das articulações ou um
  nome na lista de ossos. O filtro começa nos braços e mãos; desmarque-o para
  acessar o restante do corpo.
- **W** move, **E** gira e **R** altera a escala. Os eixos podem ser **Local** ou
  **Global**. Arraste o manipulador na vista 3D. O painel da direita permite digitar
  posição em metros, orientação em graus e escala do jogador. Os controles de
  rotação local do osso usam a pose original como referência.
- **Ctrl+Z** desfaz. **Ctrl+X** refaz, conforme solicitado; Ctrl+Y e Ctrl+Shift+Z
  também refazem. Dentro dos campos de texto, os atalhos de edição do campo são
  preservados. Há 25 passos de histórico, incluindo adição, exclusão e poses.
- **F** foca o selecionado. **Frente**, **Lado**, **Topo** e **Enquadrar cena** ajudam
  na inspeção. Guarde até 20 enquadramentos por cena.
- Mouse esquerdo gira a vista, roda aproxima, botão direito desloca a vista.
  Os eixos do manipulador têm prioridade sobre a navegação da câmera.
- **Repor osso** e **Repor pose** restauram a base do selecionado. A bancada não
  modifica a pose do jogo: todos os ajustes ficam nesta cena.

## IK para punhos e pés

Os botões **Punho E**, **Punho D**, **Pé E** e **Pé D** selecionam o alvo e ativam
**W · Mover** com IK. Arraste os eixos: o braço ou a perna acompanha o alvo,
dobrando o cotovelo ou o joelho. Também pode clicar em `LeftHand`, `RightHand`,
`LeftFoot` ou `RightFoot` no esqueleto. Os atalhos para os pés abrem o filtro de
ossos para mostrar as pernas.

**Direção da dobra** orienta o cotovelo/joelho ao redor do membro. **Inverter dobra**
troca o lado dessa orientação. **Manter orientação da mão ou pé** conserva a
direção da palma/sola ao reposicionar o membro. Use **E · Girar** para ajustar a
orientação diretamente ou desative o IK para mover cada osso separadamente.

O IK altera as rotações dos ossos, preserva seus comprimentos e limita o alvo ao
alcance do membro. Não desloca o tronco e não faz colisão automática com o corpo
ou com o piso. **Repor membro** restaura os três ossos principais à pose de base.
Desfazer/refazer, JSON e RX3 conservam a pose resolvida; nenhum controle temporário
de IK precisa ser instalado no FIFA.

## Importar poses de uma imagem

Use **Importar imagem · IA local** na coluna esquerda:

1. Escolha uma imagem PNG, JPG ou WebP e clique em **Analisar imagem**.
2. Confira as pessoas detectadas, marque as que deseja e escolha um jogador
   para representar cada uma. A IA extrai a pose; não identifica quem é a pessoa.
3. Na aba **Imagem e pontos**, selecione uma pessoa e arraste as articulações
   para corrigir a detecção. **Adicionar por recorte** permite desenhar uma caixa
   em torno de alguém que não foi detectado e analisar somente aquela região.
4. A aba **Esqueleto 3D** mostra a pessoa selecionada. Ajuste a confiança mínima,
   a profundidade e o espelhamento para conferir a transferência.
5. **Criar cena com as poses** monta os jogadores marcados. Para uma única pose,
   também é possível aplicar ao jogador já selecionado no editor.

Depois, ajuste os 400 ossos ou use o IK dos punhos/pés. **Ctrl+Z** desfaz a
importação inteira; **Ctrl+X** refaz. Na prévia da imagem, os mesmos atalhos
desfazem/refazem as correções dos pontos. **Exportar mapa** salva os pontos 2D/3D
corrigidos em JSON; **Importar mapa** os reabre sem executar a IA novamente.
O JSON normal da cena e a exportação RX3 conservam as poses transferidas.

O RTMW3D-X usa 133 pontos por pessoa e está instalado localmente com o detector
YOLOX HumanArt. Nesta máquina, o modelo de poses foi testado na RTX 3060 via
DirectML. As imagens não são enviadas a serviços externos. A primeira análise
carrega os modelos; análises seguintes reutilizam o processo, liberado após
90 segundos sem uso. Detalhes, modelos e testes estão em `local_ai/README.md`.

Uma foto fornece uma estimativa da profundidade. Partes escondidas, contatos
entre pessoas e dedos pequenos podem exigir correção. O esqueleto 3D é uma
prévia dessa estimativa. O resultado é uma pose estática e totalmente editável.
O conteúdo da cena atual é substituído somente ao clicar em **Criar cena**.
Nenhuma pose é aplicada automaticamente à instalação do FIFA.

## Arquivos da cena

**Salvar cena** baixa um JSON editável. **Abrir cena** recupera jogadores,
transformações, ossos e enquadramentos. Há também um rascunho no navegador,
recuperável pelo botão **Recuperar último rascunho**. Esse rascunho depende do
navegador e do endereço local; o JSON é o arquivo durável.

**Salvar imagem** baixa um PNG da vista. **Gerar pacote FIFA · RX3** processa a
cena em segundo plano e fornece um ZIP na pasta `exports/<identificador>/` com:

- `scene.json`: cena articulada editável;
- `scene.ff3d`: malha intermediária com a pose congelada;
- `native/`: geometria e materiais RX3 para o carregador GameplayProp do mod;
- `scene-native.json`: manifesto, unidades, jogadores e câmeras;
- `LEIA-ME.txt`: detalhes de integração.

O pacote contém uma **pose estática**, sem linha do tempo ou animação EA.
A associação à tela, ao estádio ou a uma cutscene exige integração no carregador
nativo. Gerar o pacote não instala nada no jogo. As luzes e sombras da bancada
servem à inspeção; não definem a iluminação que o FIFA usará.

O editor aceita até 48 jogadores na cena. A exportação também respeita os limites
de 512 partes, 256 texturas e 96 materiais do carregador; cenas que excedem os
limites precisam ser divididas. A biblioteca desta revisão é a do Flamengo deste
estudo, sem busca automática de outros elencos.

## Execução e verificação

O servidor Python escuta apenas em `127.0.0.1`, serve esta pasta e recebe cenas
JSON para exportação. Usa NumPy e Pillow. `settings.json` aponta para a instalação
do FIFA, usada **apenas para ler dois templates RX3**. As saídas e o cache dos
materiais ficam aqui na bancada.

Testes locais:

```text
node --experimental-default-type=module test_scene_state.mjs
node --experimental-default-type=module --experimental-loader ./node_loader.mjs test_scene_geometry.mjs
node --experimental-default-type=module --experimental-loader ./node_loader.mjs test_limb_ik.mjs
node --experimental-default-type=module test_pose_capture.mjs
node --experimental-default-type=module --experimental-loader ./node_loader.mjs test_pose_retarget.mjs
python -B -m unittest test_pose_service -v
python -B -m unittest test_scene_export -v
```

Os testes conferem histórico, validação do JSON, independência dos esqueletos das
cópias, oito pesos por vértice, reprodução da pose original, transformações do
ator e geração/reabertura de RX3 e ZIP. Os resultados de geometria ficam em
`build/tests/geometry-validation.json`.
O IK tem cobertura dos quatro membros dos 11 jogadores, alvos fora de alcance,
alvo na origem da cadeia, direção da dobra, escala/rotação do ator e histórico;
os resultados ficam em `build/tests/ik-validation.json`.

O editor anterior está preservado em `versions/pose-editor-v1/`. O arquivo Blender
e as comparações anteriores também continuam nesta pasta. Nenhum arquivo foi
instalado no FIFA, comitado ou enviado ao GitHub por esta revisão.
