# FIFA Friends V12 — pasta do mod

Consulte o [README da edição](../README.md), o [guia técnico](docs/TECHNICAL.md) e o [código nativo](source/career_native/README.md).

`config/` contém as configurações; `data/catalogs/` contém as referências de clube/estádio/formação/técnico; `mods/` contém os quatro plugins ativos e o watcher de nascimento. `crowd.ini` fica aqui por compatibilidade do plugin. `retirement_offline_worker.exe` acompanha o fluxo legado. Esta edição compila somente os cards nativos e o fluxo legado de aposentadoria.

`runtime/` e `logs/` são gerados na instalação. Preserve dados privados e contratos em runtime; não versionar saves. `source/`, `tools/`, `docs/`, backups e resultados de build ficam no Dev.

Use `install-game.cmd -GameDirectory "U:\fifa 16"` para instalar esta edição. A compilação pelo `source/career_native/build.cmd` atualiza somente esta pasta Dev. A instalação cria backup externo antes de substituir arquivos e identifica a edição no jogo por `config/edition.ini`.
