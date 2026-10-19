# Base Robson — 19/10/2026

A origem deste projeto é o ModCarrerMode v12.12.rar enviado pelo Robson.
Os módulos corrigidos foram compilados dentro da extração dessa base,
com as mudanças integradas por arquivo. O manifesto local BASE_ROBSON.json
fica fora da publicação por conter caminhos específicos desta máquina.

settings.ini, DB v12.11 - HONDURAS e o DLC/CompData enviados pelo usuário
foram conferidos por SHA-256 e sincronizados com jogo e desenvolvimento.
O CompData ativo está em dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata.
A subpasta duplicada FootballCompEng/FootballCompEng é uma cópia histórica.

As correções de calendário/cards preservam a identidade da competição do save
e geram o BIG/APT necessário. As entradas mantêm a prioridade de fase e a
herança da competição principal da 12.12. Os suportes usam os IDs diretos
do standball.ini original do autor, com tradução de identidades de saves antigos.

Os ajustes recentes de público/overlay e os demais trabalhos locais foram
integrados explicitamente. Saves e estado de execução não vieram do RAR.
As imagens e pacotes 3D externos continuam sendo os instalados localmente:
eles não faziam parte dos arquivos enviados pelo Robson. Compatibilidade
de IDs foi conferida; identidade visual pixel a pixel com o jogo dele depende
da cópia desses assets.
