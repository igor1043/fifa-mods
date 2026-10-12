# Bolas extras visuais — v16, somente bolas

Treze cópias estáticas usam a malha e a textura da bola atual do FIFA 16 x64.
Não possuem física. Centro a 11,1252 cm do gramado, sem cone ou suporte redondo.
Quatro bolas atrás dos gols em X ±5550 cm: recuo de exatamente 1 metro.
As demais permanecem nas laterais do campo de 105 × 68 m.

## Implementação

A DLL reutiliza os recursos gráficos já carregados da bola da partida.
Não executa Lua nem cria ou recarrega recursos RX3 durante a renderização.
Copia o objeto e seu estado gráfico de 0x820 bytes para memória privada.
Preserva os 1–3 slots originais e acrescenta 13 cópias até o limite de 16.
Não altera a bola real, a saída de bola, o banco, substituições ou mascote.
Mantém um callback anterior de pirotecnia reconhecido, quando ele já ocupa o slot.
A API Stop restaura os callbacks anteriores; a DLL permanece fixada na memória.

## Instalação e validação

`multiball_visual.dll` está habilitada no jogo e na pasta de desenvolvimento.
O arquivo contém a implementação v16; o nome fixo evita acumular revisões no pacote.
Os binários nas duas pastas têm o mesmo SHA-256.
Compilação `/W4 /WX` e testes passaram: distribuição, altura no chão, preservação
 dos slots originais, exclusão do menu, bola oculta e limite de slots ocupados.
O próximo reinício do FIFA ainda precisa de conferência visual pelo usuário.

Log: `ModCarrerMode/logs/multiball_visual.log`.
