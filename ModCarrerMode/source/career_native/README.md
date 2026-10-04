# Núcleo nativo — FIFA Friends V12

Esta edição compila o núcleo de carreira, os cards nativos de Meu Time/Competição/Próxima partida, a lógica de torcida e o fluxo legado de aposentadoria. O host das telas extras e o renderer 3D pertencem à branch `fifa-friends-new-experience`.

| Pasta | Conteúdo |
|---|---|
| `src/core/` | Contratos, modelo e leitura da carreira |
| `src/host/` | DLL, hooks, provedores dos cards e save ativo |
| `src/features/crowd/` | Cálculo e sincronização do público |
| `src/features/retirement/` | Motor legado, NAV exclusivo e avisos |
| `src/catalogs/` | Referências compartilhadas de nomes e kits |
| `src/platform/mod_paths.h` | Resolução de caminhos e fallback legado |
| `resources/` | Recurso L9 incorporado, obrigatório no build |
| `workers/` | Worker offline de aposentadoria |
| `scripts/build/` | Compilação da DLL e do worker |
| `tests/` e `scripts/tests/` | Regressões compartilhadas |
| `build/` | Objetos/binários gerados e ignorados pelo Git |

`build.cmd` compila a DLL e o worker apenas no Dev. `test.cmd` testa caminhos, estatísticas e prontidão de patches e compila o utilitário de aposentadoria. Testes sobre DATA requerem fixture isolada explícita. O teste de separação das edições fica em `../../tools/maintenance/Test-Edition.py`.

O card Clube e Próxima partida não abrem a interface adicional. Os eventos nativos de aposentadoria foram restaurados da branch dev sem regredir os layouts/dados das abas compartilhadas.
