# Revisão local — transições de estádio, rankings e foto da partida

## Evidência do crash

O minidump fornecido pertence ao processo 14796, iniciado em 31/10/2026 às
01:33:51 de Brasília. Registra uma violação de leitura em
`extra_scenes.dll+0x20dfd`, dentro da cópia de oito bytes a partir de
`0xffffffff`. O retorno aponta para `read+0x26`, chamado por
`native_muse::current` ao ler a implementação do adaptador da cena. O timestamp
e tamanho da DLL correspondem à versão local; a recompilação de referência
produziu a mesma seção de código da DLL instalada antes da revisão.

O ZIP de diagnóstico de 29/10 é de outra sessão (PID 6772). Termina em
`bootload`, com saída zero e sem registro de partida; não demonstra a causa
da alternância de estádios relatada. Sua lista de arquivos divergentes é uma
comparação de instalação, não uma atribuição de culpa a esses arquivos.

## Correções

- A leitura de memória das cenas usa `ReadProcessMemory` para falhar sem
  provocar uma exceção de acesso dentro dos tratadores do FIFA. Um teste
  nativo recria o adaptador inválido do dump e verifica ausência de exceção
  de primeira chance, inclusive com memória removida/protegida.
- Menus, cenas desligadas, jogo corrido e replays não consultam o agendador
  MUSE para inserir uma câmera extra. A amostra do agendador é revalidada
  contra seus proprietários antes de ser usada. As regras de probabilidade
  do técnico e do mascote permanecem as mesmas.
- O fim de partida enfileira a restauração; não copia árvores de estádio nem
  altera os arquivos ainda usados por resultados/destaques/replays. Uma
  tarefa prepara somente os arquivos diferentes. A publicação por renomeação
  acontece ao voltar a um hub elegível, com validação da geração da partida.
  Se a navegação avançar antes disso, a publicação é descartada e reagendada.
  Assets imutáveis que podem estar carregados permanecem preservados.
- A aplicação automática/manual de outro estádio aguarda essa restauração.
  O retorno ao estádio nativo deixou de copiar recursivamente a pasta inteira
  e de executar o reparo recursivo de permissões na thread dos menus. O reparo
  de permissões inicial e as rotinas de restauração com FIFA encerrado são
  preservados. A preparação não escreve em saves ou no banco nativo do FIFA.
- Na Temporada, rankings de clubes e seleções ficam consecutivos no carrossel
  das estatísticas. As outras páginas, ícones, IDs e destinos são preservados.
- A foto do estádio é recortada proporcionalmente para a área de 1050×404,
  codificada numa textura DXT5 de 2048×1024 e mapeada de volta ao tamanho do
  card. Isso evita a superfície grande sem dimensões de potência de dois,
  mantendo o enquadramento sem distorção e invalidando o cache anterior.

## Validação e instalação

Testes de cenas incluem ponteiro sentinela, página inacessível, região
desalocada e as regras existentes de câmera. Regressões Python cobrem
alternância de estádios e rotas Lua, preparação lenta sem bloquear o menu,
publicação cancelada ao começar outra partida, resultados/pênaltis/replays,
retorno ao estádio nativo, seleção manual, shutdown, rankings e imagens
horizontais/quadradas/verticais. O EXE congelado importa o novo auxiliar no
autoteste e conserva os demais módulos/recursos embarcados.

A revisão é local, com backup e manifesto em
`code-release/stadium-transition-20261031`. Não foi feito commit/push desta
revisão. A reprodução visual deve ser confirmada na instalação do Robson:
partida com estádio do Server → partida com estádio nativo → estádio do
Server, verificando também replays e o retorno ao menu. Os testes isolados
não equivalem a essa sequência executada na base dele.
