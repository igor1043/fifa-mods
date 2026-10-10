# Mascote na linha de fundo

Compile com build.cmd. Plugin: ModCarrerMode/mods/mascot_single/mascot_goal_line.dll.
A DLL usa o ID do mandante e procura pacotes em data/sceneassets/mascot/<ID>/.
Não há lista fixa de clubes. Pacotes ausentes ou incompletos mantêm o fotógrafo normal.

## Modelos locais, fora do Git

Cada pasta numérica precisa de model.rx3 e textures.rx3; model_animated.rx3 é opcional para animação. club.json pode registrar a origem da conversão. IDs: Atlético Mineiro 1035, Flamengo 1043, Palmeiras 383, Cruzeiro 568, Vasco 569. Copie os arquivos convertidos e validados para a pasta do jogo. Modelos/texturas não são distribuídos neste repositório. O instalador copia somente pacotes completos encontrados localmente; nenhum pacote é obrigatório para instalar a DLL.

## Comportamento e desempenho

Uma instância ocupa a área atrás das placas no gol atacado pelo mandante. Troca de lado no intervalo. A posição aprovada (X=±5850 cm, Z=3150 cm) tem 75% de probabilidade; os demais pontos ficam na mesma linha de fundo. A escolha é estável durante a partida. Gol do mandante ativa comemoração por 26 segundos.

Identidade conferida a cada 250 ms, pacotes pelo worker a cada segundo; animação reutiliza o contexto de posicionamento. Não há varredura Lua ou recarga de recursos por quadro.

**Limitação confirmada:** a filtragem de postura e geometria ainda deixa passar animação sentada no jogo. Os testes sintéticos passam, mas não comprovam essa correção visual. Problema pendente.

verify.cmd verifica política de posição/postura; tests/run_performance.cmd verifica memória e custo de consultas. Consulte PROMPT_CONVERTER_MASCOTE_FIFA16.md para UV, mipmaps e conversão segura. A transformação UV é V=1-V uma única vez; cada mip DXT5 precisa do seu descritor de 16 bytes.
