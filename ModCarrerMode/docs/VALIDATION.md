# Validação da reorganização — 03/10/2026

## Concluído

- Backup completo antes das mudanças: `J:\mods\backup\ModCarrerMode_antes_reorganizacao_20261003_080145`.
- Compilação completa da DLL e dos dois workers pelo novo `build.cmd`.
- Includes locais e 511 destinos do mapa de movimentação conferidos.
- Hash dos 63 arquivos `data/` do Dev idêntico ao backup, incluindo os 18 bancos de idioma `.db`.
- Configurações, catálogos, snapshot de lesões e recurso binário incorporado preservados byte a byte.
- Testes de ranking, líderes, empréstimos, estatísticas por competição e provedores passaram.
- Testes de aposentadoria/perfil, lifecycle das telas, captura de controle e preflight dos hooks passaram.
- Testes dos caminhos organizados e fallback dos caminhos antigos passaram.
- Pacote de instalação validado numa fixture isolada em `J:\mods\backup\ModCarrerMode_PackageTest_20261003_082922_713`, sem instalar no jogo real.
- Instalação de teste preservou configurações pessoais, DB existente e contratos; restauração opcional de localização e reinstalação idempotente passaram.

As poses, geometrias e cenas não foram redesenhadas nesta reorganização. Foram movidos seus arquivos e ajustados os includes. Plugins de terceiros e seus caminhos obrigatórios foram preservados.

## Validação visual pendente

O teste visual `test_club_player_screen` compilou, mas não pôde completar a execução: os assets originais necessários em `U:\fifa 16`, incluindo `data_front_end.big`, não estavam disponíveis durante o teste. A verificação das setas nativas de classificação depende desse arquivo.

A validação visual/in-game deve ser repetida quando os arquivos originais forem restaurados e a instalação no jogo for solicitada. Nenhuma instalação no jogo real foi realizada nesta tarefa.
