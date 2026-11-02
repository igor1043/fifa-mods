# Recarga de carreira e navegação das competições

Revisão local de 31/10/2026, sem commit ou push.

## Falha capturada

O dump de 13:22:40 do processo 17224 contém três contextos de exceção em
`fifa16.exe+0x3a69c96`, usando o mesmo ponteiro inválido no alocador nativo.
O desenrolamento das pilhas identifica:

- Thread 30844: comando de recarga 0x18 do estádio do menu, chamado por
  `frontend_stadium_native_v11.dll` dentro da cadeia de renderização.
- Thread 24788: fábrica nativa do fundo da interface.
- Thread 18000: atualização solicitada do fundo, na thread de interface.

Há um único arquivo de dump disponível dessa sessão. Os contextos preservados
permitem analisar as falhas concorrentes que produziram as mensagens de crash.
As pilhas e a cópia do dump ficam em `code-release/reload-ui-20261031`.

## Correção

O núcleo oferece um callback separado para o estádio, executado somente na
thread publicada como dona do contexto atual e após os leitores da interface.
O renderizador apenas registra esse callback; não dispara a recarga da carreira.
Registro repetido é idempotente, outro dono é rejeitado e a execução é protegida
contra reentrada. Uma publicação instável, antiga ou de outra thread não executa
o callback.

A recarga do mesmo clube em outro contexto invalida a rota anterior. A atualização
manual da fotografia aguarda o carregamento nativo terminar e um intervalo de
estabilização. A fila confere novamente o estado do carregador ao entregar a
atualização, pois um carregamento pode ter começado depois de ela ser solicitada.

Nenhum DATA/INDEX ou banco nativo de carreira é modificado por esta correção.
É necessário reiniciar o FIFA para substituir as DLLs que já estavam carregadas.

## Tela de competições

- Foco com borda dourada contínua, integrada ao painel.
- Artilheiros e assistências: três páginas de três jogadores, totalizando os
  nove primeiros; analógico direito troca a página do ranking em foco.
- Confirmar o ranking ou clicar nele abre a lista completa, com miniface,
  clube, posição, jogos e valor. Voltar retorna ao painel.
- Resultados ocupam uma página própria. L2/R2 troca as rodadas. Até doze jogos
  cabem na página; acima disso a lista rola. O contador de concluídos aparece
  apenas enquanto existirem partidas pendentes.
- Textos do chaveamento são reutilizados por conteúdo e tamanho lógico.
  Alterar o zoom não refaz as texturas dos textos. O cache tem limite de 64 MiB.

## Validação

122 testes Python do navegador, testes nativos das telas e restauração de estado
gráfico, teste de navegação APT, bloqueio de thread incorreta, mudança de contexto,
fila de atualização, reentrada e preflight do núcleo.

Em 36 quadros de movimento e zoom repetidos no renderizador D3D11 WARP, a segunda
passagem passou de 891 ms / 5.584 uploads para 328 ms / zero uploads. Trata-se de
uma medição isolada do painel, não do FPS total do FIFA.

O ciclo completo salvar → recarregar deve ser conferido no jogo com a revisão
instalada. Backup dos arquivos anteriores e hashes da instalação permanecem em
`code-release/reload-ui-20261031`.
