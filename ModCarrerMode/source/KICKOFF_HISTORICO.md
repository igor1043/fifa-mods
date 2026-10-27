# Histórico dos ajustes da saída de bola

O comportamento da v20 é a versão ativa e aprovada pelo usuário em 11/10/2026. Em 12/10/2026, fontes e DLL foram consolidados em `kickoff_modern`, com uma única versão no pacote. As revisões anteriores foram retiradas do projeto e preservadas na pasta externa de estudos, em `33_MODS_VERSAO_UNICA_20261012`. O histórico de commits anteriores permanece no Git.

- v14: publicação da pose de espera nos dois caminhos nativos.
- v15: posição atrás da bola e tempo do primeiro passe ajustado à distância.
- v16 e v17: proteção da aproximação e da posição após o pedido de passe.
- v18: tentativa de ajustar o subtipo da ação original.
- v19: tentativa de trocar a ação para PassHint; afetou o receptor e foi revertida.
- v20: mantém a classe e o subtipo originais, preenchendo a direção de controle com a direção real de espera. O usuário confirmou que o primeiro toque ficou correto.

Para compilar e instalar a versão aprovada, use somente `kickoff_modern/build.cmd` e a entrada `kickoff_modern\kickoff_modern.dll`.
