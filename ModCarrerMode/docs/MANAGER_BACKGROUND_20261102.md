# Mercado de técnicos: serviço de calendário e abertura — 02/11/2026

Revisão local. Sem commit/push. Backup, comparações e logs:
`code-release/manager_background_20261102`.

## Causa da espera

A captura das campanhas percorria repetidamente todos os vínculos e registros
anteriores para cada observação de uma competição. Além desse custo quadrático,
mudanças na ordem física das tabelas e nas estatísticas dos jogadores reabriam
o processamento dos contratos, mesmo sem um resultado de futebol novo.

O auxiliar só processava quando o grafo completo das competições estivesse
publicado. Durante o avanço rápido do calendário, isso acumulava trabalho.
A apresentação pronta ainda aguardava uma nova transação antes de ser entregue.
O progresso recarregava a tela a cada dez segundos para trocar o relógio.

## Alterações

- Índices em memória por clube, vínculo, temporada e competição substituem as
  varreduras completas. Observações idênticas já preservadas nas campanhas e no
  histórico anual dispensam novas gravações. Novos jogos, gols, datas, fontes e
  viradas de temporada continuam sendo processados.
- O serviço usa as tabelas primárias de todas as ligas publicadas pela thread
  proprietária do FIFA para atualizar os contratos durante o calendário. Ele
  funciona independentemente da abertura da tela. O amostrador existente guarda
  observações intermediárias enquanto SQL/apresentação estão ocupados.
- Sem o grafo completo, o serviço não inventa placares, gols ou confrontos de
  copas. Esses detalhes entram quando a publicação completa fica disponível.
  Um grafo parcial não é publicado como uma tela completa.
  Uma leitura parcial também preserva a campanha nativa mais rica e a base do
  vínculo já registrada; não zera os jogos do técnico ao trocar de fonte.
- A identidade dos dados é canônica: reordenar linhas ou mudar apenas minutos
  de jogadores não recalcula contratos. O observador de estatísticas mensais
  dos jogadores permanece independente.
- Uma apresentação terminada é entregue antes de iniciar outra transação.
- A barra avança apenas por etapas reais, sem regressões na mesma carreira/data.
  Uma atualização em segundo plano não substitui por carregamento uma tela já
  concluída. O relógio permanece nos diagnósticos, sem recarregar o painel a cada
  dez segundos. O pacote só muda quando muda a etapa ou o contexto proprietário.

## Isolamento e persistência

Cada leitura continua vinculada a PID, criação do processo, contexto, época,
clube, data e recibo nativo do save. Dados de outra carreira, outra sessão ou
outra data não podem iniciar esse processamento. Checkpoints continuam ligados
ao salvamento nativo: avançar sem salvar não substitui o estado recuperado em
uma leitura futura do mesmo arquivo DATA.

Esta revisão não altera o arquivo DATA, não altera a política de demissões,
não recompila a DLL e não modifica modelos, materiais ou animações. A instalação
reinicia somente os auxiliares de mercado/progresso, preservando a sessão não
salva pelo handoff validado. O FIFA permanece aberto.

## Validação

Comparação do motor anterior e do otimizado em cópias isoladas do mesmo estado,
com o mesmo contexto observado em RAM; hashes dos fatos antes/depois conferidos.
O cálculo de contratos passou de 13,110 s para 1,375 s nessa comparação, mantendo
os mesmos fatos. Os tempos e a igualdade constam em `benchmark-comparable.json`. Não representam
uma garantia de tempo de carregamento de qualquer máquina ou recurso 3D frio.

A suíte cobre a publicação nativa, etapas de progresso, processamento sem grafo
completo, rejeição de dados antigos/estrangeiros, descarte de avanço não salvo,
virada de ano, campanhas atribuídas ao técnico correto e todas as ligas.
Resultado: 157 testes na suíte completa, sem falhas e com um opcional ignorado
(`full-tests-final.log`). A proteção adicional contra troca de fonte foi
verificada junto às regressões de campanhas/ano/worker: 29 testes sem falhas
(`partial-preservation-tests.log`). A instalação registra hashes dos
arquivos sincronizados e do DATA, e a conferência de execução fica em
`verification.json` no backup.

Na sessão aberta de 14/08/2026, a primeira publicação após a instalação terminou
em 11,815 s, aproveitando o pacote visual válido já existente. Em seguida, a
observação contínua não repetiu a transação enquanto os dados ficaram iguais.
A conferência encontrou 1.730 clubes, preservou o mesmo branch e confirmou o
hash inalterado do DATA. Esse tempo de publicação não é a medição de um modelo
3D frio; a identidade/modelo do técnico continua no fluxo próprio do navegador.
