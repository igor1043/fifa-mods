# Carregamento e isolamento da carreira — revisão local de 02/11/2026

## Problemas corrigidos

- **Técnico do time preso em carregamento:** a carreira aberta estava em
  01/01/2026, mas os vínculos iniciais de catálogo tinham início em 09/01/2026,
  a data de `career_calendar.startdate`. O leitor rejeitava o ocupante atual
  e repetia a espera. Vínculos iniciais legados agora são interpretados desde
  o início observado da carreira, sem escrever no save nem alterar a consulta
  SQL. Novos vínculos iniciais não podem começar depois da data corrente.
  Contratações futuras efetivas continuam indisponíveis antes de sua data.
- **Mercado reconstruindo o catálogo ao voltar a janeiro:** as artes de
  competições passam a considerar o catálogo instalado, independentemente
  dos títulos conquistados na sessão descartada. Formação preferida não
  invalida imagens estáticas. Fotos, ícones, tema ou geradores alterados
  continuam invalidando o cache visual corretamente.
- **Atualização de dados do mercado:** o caminho de template já validado
  verifica o hash da geometria e impede qualquer alteração dos bytes
  existentes; valida os dois novos blocos de código antes de escrever.
  A leitura completa de geometria e recursos permanece no caminho de criação
  do template e na validação de regressão. Não recompila os milhares de
  elementos gráficos a cada atualização de dados.
- **Pacote ultrapassado na fila:** um resultado de preparação cujo modelo
  já foi substituído não é apresentado antes do mais recente.
- **Perfil e modelo 3D:** em uma exportação 3D fria, o perfil verificado pode
  aparecer antes do ator. A entrega posterior utiliza o protocolo nativo
  existente de identidade de modelo. Pedidos quentes entregam o ator direto.
- **Finanças de outra sessão:** a leitura agora exige a época do contexto,
  identidade do processo, data, clube, caminho, tamanho e modificação do save
  da publicação nativa atual. Recarregar o mesmo slot também invalida o cache
  de jogadores e transferências. A prontidão e o painel anterior são retirados
  ao trocar/recarregar a carreira; uma tela genérica aguarda os dados atuais.
  O nonce de comandos é renovado na recarga, impedindo pedidos da tela antiga.

## Persistência preservada

O arquivo `DATA` do FIFA não foi editado. O SHA-256 antes/depois da instalação
e da verificação foi `fe8607324b7b8e33262e1ecbfb9035704957fb083194309b95018b22ef9a651e`.
O banco auxiliar conserva o checkpoint correspondente ao save; a sessão
descartada de dezembro não é adotada pela carreira recarregada em janeiro.
O reinício do auxiliar do mercado utilizou handoff validado da mesma sessão,
sem restaurar por engano um checkpoint mais antigo durante a atualização.

## Validação

- Mercado: 147 testes executados, 146 aprovados e 1 opcional ignorado.
- Finanças, checkpoints, troca de slot e perfil: 32 testes aprovados.
- Rechecagem do último ajuste de cache financeiro: 7 testes aprovados
  (subconjunto dos testes acima).
- Pacote nativo instalado: 1.980 perfis, 1.730 clubes, 19 quadros de
  inicialização e nenhum erro na VM de revisão.
- Perfil de Botafogo/Tite lido da sessão aberta em 1,75 s, na data correta
  de 01/01/2026; o auxiliar posteriormente publicou perfil e ator animado.
- Mercado: publicação medida de 77,815 s antes para 12,216 s após preparar
  o catálogo reutilizável; a construção do pacote foi reaproveitada nessa
  medição. Atualização de dados com template quente foi medida em 9,117 s.
- Finanças: leitura somente de consulta da sessão aberta retornou janeiro,
  clube 1043 e 50 partidas de calendário em 4,548 s.

São medições locais, não um prazo garantido em outras máquinas. A criação
inicial do catálogo após mudança de arte/código ainda é custosa; ela foi
preparada nesta instalação. A validação visual de saída sem salvar e nova
entrada será feita pelo usuário. O agente não controlou a interface do FIFA.

Instalado no jogo e no desenvolvimento, sem commit nem push. Backup, logs,
hashes e cópia de segurança do banco auxiliar em
`code-release/screen_load_20261102_1435`.
