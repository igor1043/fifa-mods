# FIFA Friends V12 — detalhes técnicos

A DLL exclui o host ImGui, os hooks de abertura/captura das telas extras, o renderer 3D e seus provedores. O código exclusivo foi separado para a branch New Experience. Os provedores nativos de Meu Time, Competição e Próxima partida permanecem na V12, com os dados e correções mais recentes da integração.

Os eventos `FifaModsOpen*` foram retirados do NAV e dos cards. Clube e Próxima partida são informativos. A Central não tem o subcard Meu escritório nem slot adicional vazio.

## Aposentadoria pelos cards nativos

Os subcards de Configurações e os eventos `RetirementRemove`/`RetirementResetAge` foram restaurados da branch `dev`. Cada evento carrega seu fluxo NAV exclusivo e solicita `DoAutoSave`. O hook de leitura desses arquivos arma uma solicitação única; I/O de outro NAV não ativa aposentadoria.

`enabled=1`, `quiet_ms=2500`, `target_age=18` e `defer_until_game_exit=1` são os padrões. O fluxo global afeta jogadores marcados com `isretiring=1`; no segundo card ajusta também suas idades, mantendo mês/dia. Não há seleção de atleta/time pela interface dessa edição.

O aviso pede para fechar o FIFA completamente e aguardar antes de reabrir. `retirement_offline_worker.exe` espera o processo encerrar e DATA/INDEX estabilizarem, guarda backups, altera somente o DATA e verifica estrutura/CRCs. O INDEX é preservado. Falha de validação restaura o DATA anterior. Os testes de leitura/patch usam cópias isoladas, nunca a única carreira real.

## Componentes e instalação

`dinput8.dll` é a entrada única; incorpora o recurso L9.65 e materializa `dinput8_l9_chain.dll`. `dinput8_orig.dll`, `dinput8_L9.ini`, `dinput8_patch.ini` e `winmm.dll` acompanham a base. A antiga `dinput8_career_chain.dll` era recuperação e foi arquivada fora do pacote.

Os plugins ativos nas duas edições são `crowd/crowd_plugin.dll`, `bench_native12/bench_native12.dll`, `substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll` e `career_birthdate_2006/birthyear_range_2006_2012.dll`. O patch legado `global_limit_12_v2.dll` não integra a lista: ele altera a versão do interpretador APT, não o tamanho do banco.

A expansão do banco prepara até 12 jogadores reais. O plugin de substituição procura e altera os dois limites `A78C`, sem modificar os contadores `B03C`. A confirmação prática da quarta à sétima troca requer partida nova. As opções L9 `ScoutOhneLiga`, `Namensweiche` e `Poolwache` mantêm o estado desligado da base.

O instalador inclui o servidor Python e os requisitos de nascimento 2006–2012: DLL, watcher e payload `vpro_proinfo.big` na interface nativa. Confere hashes conhecidos do payload e da interface instalada antes de substituir. Arquivos escritos são comparados por SHA-256; os anteriores ficam em backup externo.

`config/edition.ini` identifica o pacote instalado. O instalador reaplica esse arquivo e `career_retirement_background.ini` mesmo quando preserva as demais configurações. Ao instalar a V12, arquiva o worker de operações, o INI do overlay e os assets exclusivos da experiência. Nunca remove `runtime/operations`, saves ou contratos.

`crowd.ini` fica na raiz de `ModCarrerMode` por compatibilidade do plugin compilado. Diagnósticos ficam em `logs/`; o nível é definido por `config/career_native_mode.ini`. Configurações antigas têm fallback, mas evite cópias divergentes.

## Compilação e conferência

```powershell
.\ModCarrerMode\source\career_native\build.cmd
.\ModCarrerMode\source\career_native\test.cmd
python .\ModCarrerMode\tools\maintenance\Test-Edition.py
.\ModCarrerMode\install-game.cmd -GameDirectory "U:\fifa 16" -VerifyOnly
```

A compilação usa o Visual Studio Build Tools já configurado e atualiza apenas o Dev. `build/` contém arquivos regeneráveis ignorados pelo Git. `.obj` são objetos C/C++ de compilação; BMP/PNG gerados por testes são prévias. Os modelos reais são malhas/texturas RX3 e pacotes BIG do FIFA; esses assets do jogo não são duplicados no repositório.

As duas pastas são checkouts de branches distintas do mesmo repositório. O histórico Git é compartilhado pelo worktree; os arquivos e binários de cada edição são separados. Commits/pushes de uma edição não mudam a referência `integracao-new-screens`.
