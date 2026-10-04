# Mod do modo carreira — comece aqui

Esta pasta Dev é a versão principal do mod. O jogo recebe somente os arquivos necessários à execução; fontes, testes e prévias ficam no Dev.

## O que existe em cada pasta

| Pasta | Para que serve | Necessária no jogo? |
|---|---|---|
| `assets/` | Imagens e fundos usados pelas telas | Sim |
| `config/` | Configurações de carreira, ranking e aposentadoria | Sim |
| `data/catalogs/` | Referências de clubes, técnicos, formações e estádios | Sim |
| `mods/` | Plugins compilados, lista de plugins ativos e carregador | Sim |
| `runtime/` | Estado da carreira, contratos, solicitações e snapshot de lesões | Gerada/preservada no jogo |
| `logs/` | Diagnósticos; não são bancos nem saves | Gerada no jogo |
| `source/` | Código-fonte dos módulos | Não |
| `tools/` | Ferramentas de instalação, localização e estudos de formatos | Não |
| `docs/` | Guias e mapas da reorganização | Não, mas pode acompanhar a instalação |
| `backups/` | Backup histórico anterior à reorganização, preservado | Não |
| `retirement_candidates/` | Listagens auxiliares de aposentadoria, caminho legado preservado | Conforme o recurso utilizado |

Os dois executáveis na raiz (`career_operations_worker.exe` e `retirement_offline_worker.exe`) e o `crowd.ini` permanecem aqui de propósito: a DLL e plugins antigos conhecem esses caminhos. Não são arquivos de teste. O plugin de torcida já compilado exige esse `crowd.ini`; movê-lo quebraria suas configurações.

Os bancos de idiomas ficam no **`data/loc/` da raiz do repositório**, fora desta pasta. Foram preservados, sem conversão de codificação. Não devem ser confundidos com os catálogos `.tsv`.

## Onde editar telas, poses e cenas

Abra [o guia do código nativo](source/career_native/README.md). Ele lista cada tela e separa renderização, poses, provedores de dados, regras de negócio e controle de entrada.

## Compilar e testar

Na pasta `source/career_native`:

```bat
build.cmd
test.cmd
```

A compilação atualiza a DLL na raiz **do Dev**, nunca na pasta do jogo. Os executáveis auxiliares também são atualizados somente no Dev.

Prévias e resultados de testes ficam em `source/career_native/build/`, separados do código-fonte. Não é necessário instalar esses arquivos para jogar.

## Instalar quando solicitado

Com o FIFA fechado, na pasta `ModCarrerMode`:

```bat
install-game.cmd -GameDirectory "U:\fifa 16"
```

O instalador verifica os arquivos, cria backup dos arquivos substituídos e preserva configurações existentes, saves e contratos. Ele não copia fontes, testes, logs ou prévias do Dev para o jogo. Não instala automaticamente após compilar.

Depois de resetar a pasta do jogo, para reaplicar também os bancos de idioma preservados no Dev:

```bat
install-game.cmd -GameDirectory "U:\fifa 16" -RestoreLocalization
```

Sem `-RestoreLocalization`, bancos `.db` já existentes não são sobrescritos. `-ReplaceConfiguration` reaplica as configurações Dev, se isso for desejado. `-VerifyOnly` apenas confere o que seria instalado, sem alterar o jogo.

## Backup desta reorganização

Backup anterior às mudanças:

`J:\mods\backup\ModCarrerMode_antes_reorganizacao_20261003_080145`

Contém a pasta completa Dev, a instalação anterior do mod no jogo, as duas DLLs e os arquivos `data/` do Dev. Consulte [como restaurar](docs/RESTORE.md). Não apague esse backup se quiser poder voltar à organização anterior.
