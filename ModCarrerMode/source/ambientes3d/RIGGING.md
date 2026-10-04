# Esqueleto, eixos de edição e FBX

Conversão validada inicialmente na edição **rig05**; os recursos continuam disponíveis em **Ambientes3D-v19.exe**, aberto por `Visualizar.cmd`. Não precisa instalar Blender, Python, Autodesk ou qualquer programa adicional. O backup em `backups/20261004-selecao-jogadores` foi preservado.

## Testar a animação enviada

Abra **Comparar-Sad-Idle.cmd**. A vista mostra o esqueleto Mixamo em rosa à esquerda e o jogador FIFA em azul, com a malha real. Use **Reproduzir** ou a barra de tempo acima da vista; a câmera continua livre. **Sad-Idle-Tecnico.cmd** abre a mesma animação no modelo do técnico do clube.

O FBX original não foi alterado. Uma cópia idêntica está em `imports/Sad Idle.fbx`; os presets em `presets/sad-idle-jogador.xml` e `presets/sad-idle-tecnico.xml` usam essa cópia.

| Esqueleto testado | Ossos | Correspondências diretas |
|---|---:|---:|
| Mixamo enviado | 65, além do nó raiz | origem |
| Jogador FIFA | 400 | 53 |
| Técnico FIFA | 31 | 22 |

Os 400 ossos não são 400 articulações humanas independentes: há ossos de rosto, roupa, cabelo e correção. Eles permanecem na hierarquia FIFA e acompanham os seus pais. A coluna e o pescoço têm ligações extras; a rotação dessas ligações é interpolada, não copiada duas vezes do mesmo osso Mixamo.

A conversão alinha a pose-base FIFA à referência FBX pelas direções dos segmentos e pela orientação da palma quando há ossos suficientes. Mantém os comprimentos nativos, escala o deslocamento da raiz e acompanha a altura do tornozelo de apoio. O deslocamento horizontal da raiz pode ser habilitado à parte. Eixos/unidades FBX são normalizados com o [leitor ufbx incorporado](https://ufbx.github.io/elements/nodes/).

O `Sad Idle` tem 2,8 segundos, a 30 quadros por segundo. Foram conferidos 85 instantes, incluindo os extremos, nos dois modelos. Resultados detalhados: `tests/resultados/sad-idle-validacao.txt`; mapas completos: `sad-idle-mapa-jogador.tsv` e `sad-idle-mapa-tecnico.tsv` na mesma pasta. Também há capturas reais do início, de dois momentos intermediários e do final.

Isso não é garantia de conversão perfeita para qualquer humanoide: outro FBX pode usar outra referência, hierarquia, proporções ou contato. Não há animação facial importada; o técnico de 31 ossos não possui dedos individuais para reproduzir cada dedo Mixamo. Não há IK completo de contato, exportação RX3/ANT/CBAC ou instalação da animação no FIFA.

## Ajustar com setas e anéis

1. Na foto da equipe ou na sala de imprensa, clique no modelo para selecionar a pessoa. O clique considera triângulos e profundidade. Na coletiva, também é possível escolher técnico/jogador na aba Pose.
2. Abra **Pose** e habilite **Eixos na vista 3D**. Selecione o osso na lista ou clique no ponto correspondente.
3. Escolha **Mover** para as setas, ou **Girar** para os anéis. Vermelho é X, verde é Y, azul é Z. Arraste a alça para editar. **Eixos locais** alterna entre os eixos da articulação e os do mundo.
4. Enquanto arrasta uma alça, o gesto não gira a câmera nem troca a pessoa. A alteração é aplicada ao esqueleto antes de deformar a malha. Os valores numéricos permanecem disponíveis.
5. Use o botão azul **SALVAR CENA**, ou **Ctrl+S**. O XML guarda câmera, alvo, correções individuais, FBX/mapa e o tempo atual do FBX; **Salvar como** cria outro arquivo. Cada sobrescrita guarda a versão anterior em `.bak`.

Na foto, cada atleta tem seus ajustes vinculados ao ID. Na coletiva, o técnico é vinculado ao clube, separadamente do jogador. Outras pessoas da cena não são alteradas. A aba **Pessoa** move/gira/escala a pessoa inteira. O gizmo de Pose edita articulações, não vértices de topologia como no modo de edição de malha do Blender.

Está disponível para os atores reais da foto, coletiva, chegada e vistas individuais. O vestiário atual contém uniformes e equipamentos, não personagens completos: não há um esqueleto humano para selecionar nos uniformes pendurados.

Cada cena da biblioteca tem seu próprio nome de XML, para não sobrescrever acidentalmente a foto com outra cena. Abrir um XML existente preserva seu caminho como destino de salvamento.

## Repetir os testes

`Testar.cmd` executa os testes isolados de câmera, XML, modelos, seleção dos 11 jogadores, isolamento de atores, movimento do quadril e arraste das setas/anéis pela API ImGui.

Para repetir a validação do FBX:

```powershell
& '.\Ambientes3D-rig05.exe' --verify-fbx 'J:\mods\fifa 16\ambientes 3d\imports\Sad Idle.fbx'
```

Para recompilar esta edição:

```powershell
& '.\scripts\build.ps1' -OutputName 'Ambientes3D-rig05.exe'
```

Se ela estiver aberta, escolha outro nome de EXE. Cada nome possui uma pasta de compilação isolada em `build/`. Os adaptadores são privados do visualizador: **nenhum arquivo do Dev ou do jogo foi modificado por esta edição**.
