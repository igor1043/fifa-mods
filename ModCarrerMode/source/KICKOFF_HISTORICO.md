# Histórico dos ajustes da saída de bola

`kickoff_modern_v20` é a versão ativa e aprovada pelo usuário em 11/10/2026. As pastas v14 a v19 são fontes recuperados da investigação, publicados para preservar o histórico. Seus builds não são instalados pelo pacote.

- v14: publicação da pose de espera nos dois caminhos nativos.
- v15: posição atrás da bola e tempo do primeiro passe ajustado à distância.
- v16 e v17: proteção da aproximação e da posição após o pedido de passe.
- v18: tentativa de ajustar o subtipo da ação original.
- v19: tentativa de trocar a ação para PassHint; afetou o receptor e foi revertida.
- v20: mantém a classe e o subtipo originais, preenchendo a direção de controle com a direção real de espera. O usuário confirmou que o primeiro toque ficou correto.

Para compilar e instalar a versão aprovada, use somente `kickoff_modern_v20/build.cmd` e a entrada `kickoff_modern_v20\kickoff_modern_v20.dll`.
