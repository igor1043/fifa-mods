# Saída de bola v20

Versão validada pelo usuário no jogo em 11/10/2026: o cobrador espera atrás da bola, voltado para sua defesa, e dá o primeiro passe dali, sem recuperar a postura antiga. O passe recuado para o receptor diagonal ficou mais suave. Esta é a versão ativa no jogo e no pacote FIFA Friends V12.

## Correção

O comando nativo `PlaceKickHint` conservava o valor de direção `-4,712389` em `+0x34C`, que permitia ao primeiro toque retomar a pose antiga. A v20 copia os 896 bytes da ação e altera somente esse float para a direção real do cobrador capturada ao iniciar o passe. Preserva a classe, o subtipo 22/23, a prioridade e os pedidos físicos. Valida atleta, ID, equipe, origem central, destino do receptor e uma janela de dois segundos após o pedido do primeiro passe.

A posição atrás da bola e a direção para a defesa são mantidas pelos comandos nativos de espera e aproximação. O tempo do primeiro passe é ajustado à distância (`tempo nativo × distância / 6`), evitando que o passe longo ao receptor use o tempo de uma saída curta. A carga desse primeiro passe é multiplicada por 0,75 e o valor nativo é restaurado após a construção do pedido.

## Compilação e instalação

Execute `build.cmd` com o MSVC x64 Build Tools instalado. O script compila com C11, `/W4 /WX /O2 /MT`, executa os testes e publica a DLL em `ModCarrerMode/mods/kickoff_modern_v20/`. Ajuste o caminho de `vcvars64.bat` no script caso sua instalação do compilador seja diferente.

Copie essa pasta para `ModCarrerMode/mods/` do jogo e mantenha uma única entrada de saída de bola em `mods/enabled.txt`:

```text
kickoff_modern_v20\kickoff_modern_v20.dll
```

O loader aplica o mod automaticamente ao iniciar o jogo. O executável permanece intacto. O código verifica a versão do executável e os bytes originais antes de instalar os hooks; não force a instalação em outra versão. Para desativar, comente a entrada e reinicie o jogo.

## Validação

Compilação sem avisos e testes de geometria, espelhamento, filtros, carga e tempo aprovados. O log de duas saídas registrou tempo nativo `40 → 256,00519`, velocidade calculada `0,96002 → 0,15000` (unidades nativas) e direção `-4,712389 → 0`. O usuário confirmou o primeiro toque: "funcnionou, taPERFEITO".

DLL validada, SHA256: `ae124bf1b6a82fd90eb0c929e9b26ed0eb4bee6c3d1678648d74a853f44bb004`.
Log: `ModCarrerMode/logs/kickoff_modern_v20.log`.
