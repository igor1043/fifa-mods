# Conferência das pendências — 11/10/2026

## V12 e jogo local

A saída de bola v20 permanece ativa e validada pelo usuário. O instalador agora inclui sua pasta versionada e exclui arquivos `.bak`. A DLL no caminho antigo `kickoff_modern` é uma cópia de compatibilidade da mesma v20 e permanece desabilitada.

A revisão 29 do mascote já estava instalada no jogo, mas suas alterações de fontes, instalador e DLL não tinham commit. A comparação SHA256 confirmou a mesma DLL nas duas pastas: `1861b6b3511e109c586eace870f6ece1ec684bba9769095c46beabb2e43c27dd`. O verificador confirmou Lua, registro único do plugin e 70 arquivos de assets locais.

Passaram os testes de políticas e de locomoção com os 14 pacotes da fixture, incluindo orientação nas duas metades, palmas para o campo, giro antes da comemoração, pausa e olhadas laterais. A conferência visual específica da revisão 29 continua pendente.

A instalação complementar copiou o catálogo de ícones que faltava no jogo, alinhou o registro de plugins e atualizou a DLL no caminho antigo. Saves e configurações pessoais foram preservados. Backup externo: `J:\mods\fifa 16\estudos fifa 16\32_PUBLICACAO_PENDENCIAS_20261011`.

## Histórico e outras branches

Os fontes intermediários `kickoff_modern_v14` a `kickoff_modern_v19` são conservados como histórico de investigação. Seus comportamentos não são aprovados para uso; somente a v20 fica habilitada. Objetos, DLLs de builds intermediários e capturas permanecem locais.

O stash de 06/10 da integração suíça foi recuperado em `archive/swiss-stash-20261006`, incluindo os fontes VP8 que estavam sem rastreamento. A branch documenta a regressão nas abas e a ausência de validação em jogo. Ela não foi aplicada à V12 atual. O stash original foi preservado.

A New Experience tem seu próprio pacote, jogo local e branch. Suas pendências são registradas naquela edição, sem substituir a V12 por outra interface de carreira.
