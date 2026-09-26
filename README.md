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
logs nativos. O módulo é o mesmo nas duas branches; o arquivo de configuração
define o ambiente do pacote:

- `mode=production`: mantém somente diagnósticos críticos e não grava os dumps
  volumosos de cards e snapshots.
- `mode=development`: mantém os logs completos para investigação.
- `mode=trace`: reservado para instrumentação adicional.

A DLL lê esse modo quando o FIFA inicia. Depois de alterar a configuração,
feche e reabra o jogo.

O código-fonte e o script de compilação desta DLL ficam em
`ModCarrerMode/source/career_native`. O artefato instalado continua sendo o
`dinput8.dll` na raiz deste repositório.

## Branches

- `main` é a versão produtiva e mantém `mode=production`.
- `dev` é a versão de desenvolvimento e mantém `mode=development`.

Essa diferença é intencional: quem clonar `main` não recebe os dumps
detalhados; quem clonar `dev` recebe os logs completos para investigação.
Ao integrar código de `dev` em `main`, preserve o arquivo de configuração da
`main` com `mode=production`: código pode ser compartilhado, mas o ambiente de
desenvolvimento não deve ser publicado no pacote produtivo. O mesmo vale para
qualquer pacote ou cópia feita para a instalação do jogo.

