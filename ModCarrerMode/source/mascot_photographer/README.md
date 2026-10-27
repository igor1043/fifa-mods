# Mascote na linha de fundo

Um mascote representa o mandante atrás das placas do gol que ele ataca. O plugin procura o pacote pelo ID nativo do clube, sem lista fixa de times. Troca o lado no intervalo e preserva sua posição lateral.

O mascote sincroniza a orientação com a troca de gol: olha para o gramado logo após o intervalo, inclusive com o relógio de animação pausado. A caminhada anterior é encerrada e a parada no novo lado recomeça com 30 segundos.

A revisão 29 mantém apoio e palmas voltados ao campo. Antes de iniciar o clipe de gol, o mascote vira para o gramado e permanece nessa direção durante a comemoração. Na caminhada continua olhando para o destino. A cada três paradas, depois da interação, faz uma olhada lateral suave de até 26 graus durante três segundos, alternando o lado e retornando ao campo. Esta revisão está instalada no jogo e publicada com testes automatizados; sua conferência visual ainda está pendente.

## Comportamento

- Dez pontos no mesmo fundo de gol, nos dois lados da meta. A caminhada escolhe pontos próximos, com percurso de até 6 metros e preferência pelos menos visitados recentemente.
- Permanência de 30 segundos por ponto, com 15 segundos de interação: palmas e dois gestos de apoio com os braços.
- Gols do mandante interrompem a rota e acionam 15 segundos de comemoração. Seis variantes capturadas da torcida incluem braços erguidos, gestos amplos e saltos. O ponto inicial da sequência varia entre gols.
- Pausa conserva a pose. No replay, o relógio nativo seleciona posições e poses já registradas, incluindo o clipe escolhido e a altura do salto.
- O módulo compensa a diferença entre o esqueleto do RX3 do clube e o esqueleto do renderizador. Essa correção trata a deformação de tronco/braços nas comemorações para todos os pacotes compatíveis.

O histórico de replay é local à sessão: até 8192 quadros, registrados no máximo 30 vezes por segundo real. Trechos fora desse histórico usam o quadro registrado mais próximo. Não é gravado nos arquivos nativos de replay; abrir um replay de outra sessão não recupera a movimentação anterior do mascote.

## Pacote de modelo no jogo

Cada clube precisa de uma pasta numérica em `data/sceneassets/mascot/<ID>/`, relativa à pasta de `FIFA16.exe`:

```text
data/sceneassets/mascot/1041/
  model.rx3
  textures.rx3
  model_animated.rx3
  locomotion_feet.bin
  club.json
```

`model.rx3` e `textures.rx3` formam o pacote básico. Para a locomoção/animação atual, mantenha também o modelo animado e seus marcadores de pés correspondentes. `club.json` registra o clube e a conversão. Preserve o pacote completo do backup local; arquivos de esqueleto e marcadores devem corresponder à mesma malha.

| Clube | ID usado no banco local |
|---|---:|
| Atlético Mineiro | 1035 |
| Athletico-PR | 1039 |
| Corinthians | 1041 |
| Flamengo | 1043 |
| Internacional | 1048 |
| Santos | 1053 |
| Palmeiras | 383 |
| Grêmio | 1629 |
| Fluminense | 567 |
| Cruzeiro | 568 |
| Vasco | 569 |
| Bahia | 1598 |
| Fortaleza | 111052 |
| Remo | 130026 |
| Santa Cruz | 111058 |
| São Paulo | 598 |
| Vitória-BA | 1719 |
| Paulista de Jundiaí | 130066 |
| Botafogo | 517 |
| Brasil (seleção) | 1370 |
| Chapecoense | 112476 |
| Coritiba | 111044 |
| Mirassol | 113163 |
| RB Bragantino | 123921 |

Remo e Paulista usam IDs do banco customizado instalado. Se o seu banco tiver outro ID, o nome da pasta deve acompanhar o ID desse banco.

Modelos, texturas, marcadores, prévias e originais de edição ficam no jogo e nos backups locais, fora da versão atual do Git. A DLL e o Lua estão incluídos no pacote publicado. Os modelos devem estar previamente instalados ou ser obtidos separadamente; sem o pacote completo do clube, permanece o fotógrafo normal. Cópias enviadas anteriormente continuam no histórico antigo.

## Pacotes da Série B

Os 20 clubes da Série B do banco local têm pacotes convertidos com `--review-body-weights`: pivôs proporcionais a cada personagem, peito superior separado do pescoço, cabeça rígida e braços em cadeias independentes. O Fortaleza usa o mesmo ID do pacote anterior, atualizado com os arquivos desta importação.

| Clube | ID usado no banco local |
|---|---:|
| América-MG | 112001 |
| Athletic SJR-MG | 130388 |
| Atlético-GO | 112119 |
| Avaí | 111976 |
| Botafogo-RP | 130028 |
| Ceará | 111059 |
| CRB | 120005 |
| Criciúma | 111046 |
| Cuiabá | 120006 |
| Fortaleza | 111052 |
| Goiás | 111042 |
| Juventude | 111041 |
| Londrina | 130021 |
| Náutico | 111050 |
| Grêmio Novorizontino | 130045 |
| Operário-PR | 113116 |
| Ponte Preta | 111043 |
| São Bernardo | 130046 |
| Sport Recife | 111057 |
| Vila Nova | 120016 |

Botafogo-SP aparece como Botafogo-RP no banco local; Athletic-MG como Athletic SJR-MG. Nos arquivos com nomes genéricos, `Prepare-AuthoredMascot.py --basecolor <imagem> --normal <imagem>` seleciona explicitamente os mapas de cor e normal. As texturas visuais fornecidas são preservadas. O Botafogo-SP tinha dois vértices sem peso; `--repair-unweighted` preencheu somente esses pontos usando vizinhos locais ponderados pela distância. Relatórios e prévias ficam no estudo local, fora do pacote de execução.

## Pacotes da Série C e extras

O envio `SERIE C.rar` contém 22 modelos: 19 clubes da Série C do banco local, Novorizontino (já presente na Série B), Jabaquara e o Chapolin do Fifa Friends Team. O usuário confirmou o ID 130248 para este último. Volta Redonda (120433) não veio no envio e não recebe modelo substituto. Santa Cruz e Novorizontino atualizam seus pacotes anteriores.

| Clube | ID usado no banco local |
|---|---:|
| Amazonas FC | 130285 |
| Anápolis | 130190 |
| Barra-SC | 130326 |
| Botafogo-PB | 120004 |
| Brusque | 113121 |
| Caxias | 120003 |
| Fifa Friends Team | 130248 |
| Confiança | 130024 |
| Ferroviária | 113101 |
| Figueirense | 111045 |
| Floresta | 130100 |
| Guarani | 111049 |
| Inter de Limeira | 130091 |
| Itabaiana | 113104 |
| Ituano | 113105 |
| Jabaquara | 130127 |
| Maranhão | 130072 |
| Maringá | 130108 |
| Grêmio Novorizontino | 130045 |
| Paysandu | 120002 |
| Santa Cruz | 111058 |
| Ypiranga | 130025 |

Os 22 modelos usam a revisão de pesos de cabeça, pescoço, peito e braços, preservando texturas e pivôs proporcionais a cada personagem. Todos os FBX fornecidos tinham um esqueleto Mixamo e nenhum vértice sem peso. No Chapolin, `--rigid-right-hand-prop` mantém a região autoral da mão e da marreta rígida no osso 24: o acessório elevado não recebe a pintura da cabeça por estar na mesma altura. A preservação da forma foi verificada em 63 poses. Essa opção é limitada ao modelo inspecionado do clube 130248. Prévia renderizada e testes offline não substituem a conferência visual dentro de uma partida.

O ZIP de distribuição deste envio contém somente `data/sceneassets/mascot/<ID>/model.rx3`, `model_animated.rx3`, `textures.rx3` e `locomotion_feet.bin`, para os 22 IDs acima. Não inclui outros mascotes, DLL, Lua, fontes, metadados de conversão ou prévias. Extraia na raiz do FIFA 16 com o mod de mascotes já instalado e IDs de banco compatíveis.

## Compilar e instalar

Na raiz do repositório, com MSVC x64 disponível:

```powershell
.\ModCarrerMode\source\mascot_photographer\build.cmd
```

O pacote já inclui `ModCarrerMode/mods/mascot_single/mascot_goal_line.dll`. Compilar é opcional; o build atualiza somente essa DLL. Os seis headers `mascot_goal_*_clip.h` entram diretamente na compilação; não é preciso recuperar os JSONs de captura.

Coloque os pacotes locais atualizados em `data/sceneassets/mascot/` do desenvolvimento, feche o FIFA e execute:

```powershell
.\ModCarrerMode\source\mascot_photographer\Install-MascotPhotographer.ps1 -GameRoot "C:\Caminho\para\FIFA 16"
```

Esse instalador copia DLL, Lua e pacotes numéricos completos; faz backup dos arquivos substituídos e mantém uma única entrada de mascote. Ele interrompe a instalação se o Lua do destino tiver uma alteração desconhecida, para preservar essa personalização. `Install-Locomotion.ps1` atualiza apenas a DLL e marcadores compatíveis: use-o somente quando o Lua e os modelos já estiverem preparados.

Arquivos necessários no jogo:

```text
ModCarrerMode/mods/mascot_single/mascot_goal_line.dll
data/fifarna/lua/assets/sle.lua
data/sceneassets/mascot/<ID>/...
```

Em `ModCarrerMode/mods/enabled.txt`, mantenha somente:

```text
mascot_single\mascot_goal_line.dll
```

Preserve as entradas dos outros mods. Para verificar a instalação:

```powershell
.\ModCarrerMode\source\mascot_photographer\Install-MascotPhotographer.ps1 -GameRoot "C:\Caminho\para\FIFA 16" -VerifyOnly
```

Para desativar, comente a entrada do mascote em `enabled.txt`. Reabra o FIFA após trocar a DLL ou alterar sua entrada.

## Atores disponíveis e desempenho

O mod escolhe a primeira categoria disponível entre fotógrafos comuns, fotógrafos de apresentação e categorias auxiliares suportadas (listas 1, 18, 0 e 22). Não depende do ID do estádio nem de uma quantidade mínima de fotógrafos comuns. Usa uma aparência dedicada em um único ator e verifica a propriedade antes de restaurar posições.

Se todas as categorias estiverem vazias, registra `placement_unavailable` e preserva a cena. Pacote ausente ou incompleto também conserva a aparência original. Identidade é consultada a cada 250 ms e pacotes pelo worker a cada segundo; não há varredura Lua nem carregamento de RX3 por quadro.

## Ferramentas e validação

### Técnico nativo: Atlético-MG

Estado local em 18/10/2026: a revisão com correção da tabela interna de texturas foi aplicada ao técnico do Atlético-MG (1035), no jogo, desenvolvimento e backup de modelos. As versões anteriores, que tiveram relatos de crash, estão preservadas em quarentena. Foi encontrado um defeito concreto no exportador: os mapas estavam em DXT5, mas a tabela duplicada de informações das texturas ainda declarava DXT1 e tamanhos menores. Essa divergência foi corrigida e a validação agora rejeita o pacote anterior. O novo dump apresenta falha em uma rotina compatível com gerenciamento de memória; o defeito de empacotamento é compatível com corrupção do heap, mas a correção da estabilidade ainda depende de teste real. O usuário fará esse teste depois.

A seleção segue o ID do time usado pelo pacote do Flamengo (1043), para técnico mandante e visitante. Reabra o FIFA após instalar: uma partida já carregada mantém o modelo anterior em memória. Prévias e testes de poses não confirmam estabilidade em partida.

`Build-NativeManager.py` converte um FBX humano com esqueleto/pesos Mixamo para os 31 ossos do técnico nativo. O modelo é ajustado à pose de descanso do técnico e mantém a seção de matrizes de referência do RX3 original byte a byte. Ele não usa o retarget de mascotes em tempo de execução. Arquivos sem esqueleto ou sem pesos são rejeitados.

A exportação agora conserva também a tabela nativa de 19 ossos ativos, byte a byte: os pesos das pontas dos pés usam os ossos dos pés. A versão anterior acrescentava dois canais a essa tabela; essa divergência foi encontrada na comparação com o técnico genérico e o pacote do Flamengo (1043), sem comprovação de que tenha causado o crash. `Validate-NativeManager.py --package <pasta_slc> --native-model <rx3_generico> --reference-model <rx3_flamengo> --tools <bundle> --output <relatorio.json>` verifica o conjunto de ossos ativos, as matrizes, o formato dos vértices, os índices, os contadores do renderizável e as texturas das duas variantes. O relatório mantém `runtimeValidated=false` até o teste real.

A revisão de Eduardo Domingues usa o novo FBX com 65 ossos e 8.827 vértices de origem. Braços/pernas recebem ajuste de comprimento axial; a circunferência dos antebraços é preservada. Mãos têm proporção própria e os pesos autorais dos dedos produzem uma pose relaxada antes de serem mapeados ao punho. O SLC nativo tem um osso por mão, sem canais independentes para animar os dedos. Cabeça, rosto e barba permanecem juntos; a transição do pescoço conserva seus pesos.

O FBX de origem tem pele na frente dos antebraços e tecido de manga comprida atrás, causando a aparência de mão saindo da camisa em algumas poses. `Build-NativeManager.py` exporta `authored_surface.json` antes do ajuste à pose nativa. `Repair-NativeManagerForearms.py --surface authored_surface.json --basecolor <cor_original> --normal <normal_original> --output <pasta>` usa essa superfície para projetar a pele original ao redor dos dois antebraços e neutralizar as dobras de tecido no mapa normal da região repintada. Passe `forearms_basecolor.png` e `forearms_normal.png` ao preparador de texturas. Essa correção mantém a geometria, os pesos e o desenho dos dedos; não altera o FBX original.

Use `--clean-cuff` nesse reparador para reconstruir uma borda estreita e contínua entre camisa e pele, em vez de manter a faixa larga de mistura de cores. Essa opção trata os dois lados da manga e amplia a margem de cor fora das ilhas UV, sem escrever nas outras ilhas. A revisão da textura também continua pendente de conferência no jogo.

`Refine-NativeManagerArms.py` é a revisão posterior da malha e dos pesos. Execute no Blender com `--input <modelo_rx3> --output <pasta> --surface authored_surface.json --skin-map source_skin_map.json --conversion conversion.json --tools <bundle>`. Suaviza os relevos dos antebraços com deslocamento limitado a 0,9 cm e uniformiza a transição dos pesos ao redor dos punhos. Mantém a topologia, UVs, matrizes nativas, rosto e dedos. Gera o RX3 revisado, o mapa de pesos atualizado, uma superfície editável em `.blend` e o relatório `forearm_geometry_review.json`; use o RX3 revisado como entrada do preparador para gerar as duas variantes. A verificação offline compara 81 poses com a versão anterior e mede o esticamento na região do punho. A aparência nas animações específicas do técnico continua dependendo de teste em partida.

`Prepare-NativeManager.py` converte os mapas de cor e normal nos slots próprios do técnico, preserva o mapa de coeficientes do material e prepara estes arquivos em `data/sceneassets/slc/`:

O preparador atualiza também as cópias dos cabeçalhos de textura na seção `0x6BD085DC`, que precisam corresponder aos primeiros 16 bytes de cada seção `0x7A0B60DA`. A verificação de cada mip isolado não detectava a divergência entre essa tabela e os dados DXT5. `Validate-NativeManager.py` verifica agora a correspondência completa e rejeita descritores de formato, dimensões ou tamanho divergentes. A comparação com os pacotes nativos confirmou que seus cabeçalhos duplicados coincidem.

```text
specificmanager_1035_0_0.rx3
specificmanager_1035_0_0_textures.rx3
specificmanager_1035_0_1.rx3
specificmanager_1035_0_1_textures.rx3
```

O Revolution Mod já procura esses arquivos pelo ID da equipe, para técnico mandante e visitante. As variantes 0/1 usam o mesmo modelo e roupa em tempo normal/frio. Não há alteração de DLL, Lua ou do mascote do Galo. Os modelos são recursos locais, fora do código versionado. As prévias usam poses capturadas compatíveis com o esqueleto comum; as reações específicas do técnico ainda precisam de conferência visual numa nova partida do Atlético-MG. O estudo local registra 81 poses verificadas e hashes de aplicação no jogo, desenvolvimento e backup de técnicos.

`Build-AuthoredMascot.py` converte os modelos autorais disponíveis localmente. `Build-MascotGoalClip.py` gera headers a partir de capturas locais. Modelos FBX originais e capturas não são necessários para executar o mod.

Para Santos, Internacional, Palmeiras, Grêmio, Fluminense, Botafogo, Brasil, Chapecoense, Coritiba, Mirassol e RB Bragantino, a conversão usa `--review-body-weights`: os pivôs seguem as proporções do personagem, a parte superior do peito fica no osso 12, o pescoço no 13 e a cabeça no 14. O rosto e o crânio recebem peso rígido; a ligação do pescoço conserva a transição e os braços mantêm suas cadeias independentes. Isso é pintura de pesos do esqueleto; a textura visual fornecida é preservada e convertida para o RX3 com seus mipmaps. A seleção usa o ID de equipe 1370 do banco instalado; o carregamento de pacotes é dinâmico e funciona também para seleções mandantes.

O argumento `--tools` aponta para o bundle local `mascot_rig_adjuster`, que contém `vendor/rx3tools`, `assets/template_model_animated.rx3` e `texture_assets.py`. Essas dependências são de conversão, não de execução no FIFA.

`Render-MascotReview.py` renderiza a malha RX3 exportada usando as mesmas referências de esqueleto e capturas nativas da animação. Gera repouso, caminhada, suporte, comemoração e detalhes de cabeça/ombros/tronco, além de quadros para uma prévia animada. Requer Blender e a textura difusa exportada do pacote. A prévia verifica a deformação da malha; ela não substitui a verificação da cena de replay dentro do jogo.

`verify.cmd` compila e executa as políticas de posição, seleção de atores, replay e animação. `verify_locomotion.cmd` verifica poses e deformação com uma pasta de fixtures contendo modelos, marcadores e matrizes de referência; essa pasta é um recurso de teste local, separado do pacote de jogo. `tests/run_performance.cmd` verifica o custo das consultas.

A compensação e a gravação/leitura das poses do replay foram testadas com os 63 pacotes locais e a matriz capturada do renderizador. As conversões novas passaram na validação offline e aguardam confirmação visual no FIFA. Os pacotes abrangem os 20 clubes da Série A, os 20 da Série B e 19 da Série C cadastrados no banco instalado, mais Brasil, Paulista de Jundiaí, Jabaquara e Fifa Friends Team. O usuário confirmou os mascotes anteriores no jogo local. A rotação relatada no replay de Flamengo/Cruzeiro não foi reproduzida na auditoria dos modelos ou na reconstrução das poses; sua causa na cena ainda precisa ser verificada no jogo. Consulte `ModCarrerMode/logs/mascot_goal_line.log` e o registro `installed version=30` para identificar o build interno; o caminho ativo não tem sufixo de versão.

Revisão 30: a atualização Lua confirma sua conclusão antes de mover o ator e pode tentar novamente após uma falha temporária, mesmo sem trocar de partida. Os wrappers do mascote são instalados uma vez por contexto, preservando os módulos carregados depois. O estado da seleção tem proteção contra reentrada com liberação em finally. Logs incluem processo e thread. Consulte `../common/README.md` para testes e limites da hipótese de concorrência.
