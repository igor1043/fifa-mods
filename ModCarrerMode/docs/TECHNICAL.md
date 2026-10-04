# FIFA Friends - New Experience — detalhes técnicos

A edição mantém o código de telas, provedores e renderização da integração. Próxima partida e Clube abrem suas telas; Meu escritório abre o painel principal. O host compartilha a captura de mouse, teclado e controle e aplica a guarda de liberação de 250 ms ao devolver o foco ao FIFA.

O carrossel Próxima partida declara um subcard adicional, Meu escritório. Foi corrigida a declaração anterior de dois subcards com apenas um implementado.

## Telas e operações

O mapa de código está em `source/career_native/README.md`: telas em `src/screens`, renderização em `src/render`, entrada em `src/platform/input` e host em `src/host`. Modelos/texturas são lidos da instalação FIFA, sem depender de Blender ou copiar galerias de build para o jogo.

A aposentadoria nova usa `career_operations_worker.exe`, com seleção individual/por escopo e idade opcional. A lista e o perfil vêm de cópias dos dados obtidos pela thread nativa do provider. Confirme, salve e feche o FIFA completamente antes de aguardar o processamento.

Empréstimos usam planos provisórios de 6/12/24 parcelas e juros totais de 5/10/20%, em unidades integrais do orçamento de transferências. O orçamento de salários permanece separado. Há um contrato por slot; vencimentos acompanham o calendário da carreira. Sem saldo, as cobranças ficam pendentes. Solicitações, contratos e diário de recuperação em `runtime/operations` são dados privados ignorados pelo Git e devem ser preservados.

O worker valida clube, treinador, estrutura e CRCs e substitui o DATA atomicamente, com backups em `J:\mods\backup\CareerOperations`. A geração de oferta/e-mail de emprego do técnico não está conectada. A visualização livre de estádio permanece fora do build; imagens de estádio e as outras cenas 3D são mantidas.

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
