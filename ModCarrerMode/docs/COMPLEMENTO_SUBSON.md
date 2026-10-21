# Complemento SubsOn

O pacote `FIFA_Friends_V12_Subson_assets.zip` acompanha esta edição separadamente.
Ele contém `data/ant.cbac`, com 141.909.975 bytes (cerca de 142 MB), e também:

- `SubsOn.dll` e `SubsOn.ini`, com `BENCH_SIZE=12`.
- `ModCarrerMode/mods/subson/subson_bridge.dll`.
- `dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata/settings.txt`, com `rule_numsubsbench=12`.
- Instruções e um manifesto SHA-256 dos arquivos.

O ZIP tem aproximadamente 131 MB e fica fora do repositório Git.

Com FIFA e Server16 fechados, guarde uma cópia do `data/ant.cbac` anterior e
extraia o complemento na pasta do jogo, preservando todos os caminhos.
Depois execute o instalador normal do FIFA Friends V12.

Quem já tem o arquivo correto não precisa extraí-lo novamente. O instalador
confere tamanho e SHA-256 antes de alterar a instalação e preserva esse arquivo
nas atualizações. O manifesto está em `ModCarrerMode/data/catalogs/subson_assets.json`.

SHA-256 do arquivo extraído:

`abde4d8f5246b5082321e16900905e48cfc70026dbd652749534b53f858dfa98`
