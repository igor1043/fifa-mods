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

`Build-AuthoredMascot.py` converte os modelos autorais disponíveis localmente. `Build-MascotGoalClip.py` gera headers a partir de capturas locais. Modelos FBX originais e capturas não são necessários para executar o mod.

Para Santos, Internacional, Palmeiras, Grêmio, Fluminense, Botafogo, Brasil, Chapecoense, Coritiba, Mirassol e RB Bragantino, a conversão usa `--review-body-weights`: os pivôs seguem as proporções do personagem, a parte superior do peito fica no osso 12, o pescoço no 13 e a cabeça no 14. O rosto e o crânio recebem peso rígido; a ligação do pescoço conserva a transição e os braços mantêm suas cadeias independentes. Isso é pintura de pesos do esqueleto; a textura visual fornecida é preservada e convertida para o RX3 com seus mipmaps. A seleção usa o ID de equipe 1370 do banco instalado; o carregamento de pacotes é dinâmico e funciona também para seleções mandantes.

O argumento `--tools` aponta para o bundle local `mascot_rig_adjuster`, que contém `vendor/rx3tools`, `assets/template_model_animated.rx3` e `texture_assets.py`. Essas dependências são de conversão, não de execução no FIFA.

`Render-MascotReview.py` renderiza a malha RX3 exportada usando as mesmas referências de esqueleto e capturas nativas da animação. Gera repouso, caminhada, suporte, comemoração e detalhes de cabeça/ombros/tronco, além de quadros para uma prévia animada. Requer Blender e a textura difusa exportada do pacote. A prévia verifica a deformação da malha; ela não substitui a verificação da cena de replay dentro do jogo.

`verify.cmd` compila e executa as políticas de posição, seleção de atores, replay e animação. `verify_locomotion.cmd` verifica poses e deformação com uma pasta de fixtures contendo modelos, marcadores e matrizes de referência; essa pasta é um recurso de teste local, separado do pacote de jogo. `tests/run_performance.cmd` verifica o custo das consultas.

A compensação e a gravação/leitura das poses do replay foram testadas com os 43 pacotes locais e a matriz capturada do renderizador. As conversões novas passaram na validação offline e aguardam confirmação visual no FIFA. Os pacotes abrangem os 20 clubes da Série A e os 20 da Série B cadastrados no banco instalado, mais Brasil, Santa Cruz e Paulista de Jundiaí. O usuário confirmou os mascotes anteriores no jogo local. A rotação relatada no replay de Flamengo/Cruzeiro não foi reproduzida na auditoria dos modelos ou na reconstrução das poses; sua causa na cena ainda precisa ser verificada no jogo. Consulte `ModCarrerMode/logs/mascot_goal_line.log` e o registro `installed version=30` para identificar o build interno; o caminho ativo não tem sufixo de versão.

Revisão 30: a atualização Lua confirma sua conclusão antes de mover o ator e pode tentar novamente após uma falha temporária, mesmo sem trocar de partida. Os wrappers do mascote são instalados uma vez por contexto, preservando os módulos carregados depois. O estado da seleção tem proteção contra reentrada com liberação em finally. Logs incluem processo e thread. Consulte `../common/README.md` para testes e limites da hipótese de concorrência.
