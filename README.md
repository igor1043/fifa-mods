# FIFA Mods

Mods e ajustes para o modo carreira do FIFA 16.

## Instalação

Copie o conteúdo desta pasta para a raiz da instalação do FIFA 16, mantendo a estrutura de diretórios. Faça um backup dos arquivos originais antes de substituir qualquer arquivo.

## Conteúdo

- Arquivos de suporte do modo carreira
- Ajustes de interface e localização
- Plugins e configurações complementares

## Diagnóstico nativo do modo carreira

O arquivo `ModCarrerMode/career_native_mode.ini` controla a verbosidade dos
logs nativos. O padrão é `mode=production`, que mantém somente diagnósticos
críticos e não grava os dumps volumosos de cards e snapshots. Para investigar
um problema, feche o jogo, altere para `mode=development`, reproduza o caso e
volte para `mode=production` antes de jogar normalmente. `mode=trace` fica
reservado para instrumentação adicional.

O código-fonte e o script de compilação desta DLL ficam em
`ModCarrerMode/source/career_native`. O artefato instalado continua sendo o
`dinput8.dll` na raiz deste repositório.

## Branches

- `main` é a versão produtiva e mantém `mode=production`.
- `dev` é a versão de desenvolvimento e mantém `mode=development`.

Essa diferença é intencional: quem clonar `main` não recebe os dumps
detalhados; quem clonar `dev` recebe os logs completos para investigação.
Evite trocar manualmente o arquivo de configuração entre branches, porque ele
é o que define o comportamento de cada pacote.

Para desfazer somente esta troca da DLL, feche o jogo e execute
`ModCarrerMode/source/career_native/restore_previous_dinput8.ps1`.

