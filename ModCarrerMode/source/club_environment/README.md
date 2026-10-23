# Ambiente do clube e telas da carreira

Requer a base FIFA Friends V12 e Server16 0.2.14. Fontes Python/CPP, auxiliares de
APT e interfaces ficam neste repositório. Modelos, texturas e poses do vestiário
são fornecidos no ZIP separado. O histórico anual está desativado.

## Instalação

1. Feche FIFA e Server16. Atualize a base pela branch `fifa-friends-v12` do GitHub,
   incluindo o Server16, DLLs, fontes, interfaces, Lua e configurações publicadas.
2. Extraia `FIFA-Friends-Assets-Complementares-20261023.zip` diretamente na raiz
   do FIFA, mesclando as pastas `data` e `ModCarrerMode`. Não há instalador.
3. Abra o Server16 atualizado e inicie o jogo. Não precisa instalar Python,
   NumPy, Pillow, ScoreboardStudio ou ferramentas de RX3 no computador do jogador.

O Server16 ativa as interfaces nos BHs locais ao iniciar o FIFA e prepara os
auxiliares automaticamente. Não substitua os índices BH pelos de outro PC.

## Organização e dados dinâmicos

- `room`, `bank`, `preview`: fontes atuais, separadas das revisões experimentais.
- `vendor`: leitores de BIG/APT/RX3 e montador APT usados pelos auxiliares.
- `ModCarrerMode/data/club_environment`: descrições estáticas e modelos de apoio.
- `ModCarrerMode/runtime/club_environment`: cópias executáveis dos auxiliares,
  caches, controle das cenas e dados locais da carreira. Não enviar ao GitHub.
- `data/sceneassets/server16_dressing_room_20261022`: caminho dos assets preservado
  para manter compatibilidade. Somente os arquivos do manifesto são necessários.

Server16 inicia processos auxiliares ocultos vinculados à sessão do FIFA. Camisas,
chuteiras, bolas, fontes, retratos e escudos vêm dos arquivos do próprio jogo,
incluindo os empacotados em BIG. O ZIP não fixa elenco, clube ou jogadores.
As três telas iniciais contêm estado de espera; a carreira válida fornece os dados
reais. Iluminação aprovada preservada byte a byte.

Empréstimos: um contrato ativo, até duas contratações por ano da carreira,
parcelas mensais, antecipação de parcela ou quitação, orçamento validado e
pedidos deduplicados. O banco é o único auxiliar que pode publicar orçamento,
depois das validações da ação da interface; testes não fazem transações reais.
Contratos antigos são migrados do protótipo para o runtime local, sem sobrescrever
um histórico financeiro mais recente.

## Panorâmica de estádio customizado

`ModCarrerMode/config/stadium_metadata.ini` usa o nome exato do pacote StadiumGBD.
Também aceita `metadata.ini`/`stadium.ini` dentro do estádio, seção `[stadium]`,
ou `[stadiumcapacity]`/`[stadiumattendance]` no `FSW/settings.ini`.
A configuração do mod tem prioridade. Valores são quantidades de pessoas;
ausentes/inválidos ficam vazios, e público superior à capacidade é descartado.
Não se aproveitam dados do slot nativo usado para renderizar o estádio.
O campo de ano de construção dos estádios originais permanece original.

Extração não executa na thread de desenho nem segura sua trava durante a espera.
Resultados de uma seleção já trocada são descartados. As transições continuam
avançando em quadros lentos. A interface preserva o fluxo nativo de continuar,
nome e escudo, acrescentando capacidade/público apenas quando informados.

## Desenvolvimento e validação

Fonte principal do Server16: `igor1043/CG-File-Server-16---Python-Port`, branch
`fifa-friends`. Este pacote contém uma cópia das fontes usadas no executável.
O modo `Server16Python.exe --club-environment-check --game-root "pasta do FIFA"`
verifica as importações e poses com o runtime embutido, sem abrir a interface.
`room/native/build.cmd` compila a DLL em uma pasta temporária com MSVC x64.
Os testes Python de `test_release.py` usam um Python de desenvolvimento com as
dependências indicadas no projeto Server16. Execute após preparar o runtime;
não abrem o jogo nem editam saves. Teste nativo de câmera em
`room/test_room_camera_r52.cpp`, com os headers em `room/native`.

O comportamento relatado no PC do Robson requer conferência nessa máquina após
atualizar e reabrir o jogo; as correções acima cobrem os defeitos reproduzidos
nos testes e a ativação da interface, sem afirmar uma causa exclusiva daquele PC.

## Confirmação de empréstimos e distribuição

Depois de confirmar, a tela aguarda o resultado da solicitação identificada por
sessão e sequência. O auxiliar só publica sucesso após conferir a escrita do
orçamento. A própria tela recarrega os dados pelo fluxo nativo, mostra o saldo,
saldo devedor e próximo vencimento e permite consultar as parcelas atualizadas.
Atualizar a tela não reenvia o pedido. Uma recusa mostra o motivo; ausência de
confirmação não é apresentada como sucesso. A persistência continua pelo Salvar
do FIFA e pelo livro financeiro específico daquele save.

`ModCarrerMode/tools/Build-PortablePackages.py` gera um único complemento com os
33 assets estáticos do ambiente e a animação SubsOn. O gerador recusa qualquer
arquivo rastreado pelo Git: código, executáveis, DLLs, interfaces, Lua, INIs e
manifestos permanecem no repositório. O ZIP contém só os caminhos finais dos
assets, sem pasta intermediária, comandos ou scripts de instalação.
Não inclui saves, histórico anual, caches de estádio ou dados pessoais.
A panorâmica recebe seus componentes pela atualização do GitHub e usa os
estádios StadiumGBD já instalados pelo destinatário.

## Pacote de recuperação do Vestiário

`ModCarrerMode/tools/Build-VestiarioPackage.py` gera
`FIFA-Friends-Vestiario-Corrigido-R61-20261023.zip` para uma base V12 já instalada.
Esse pacote de recuperação inclui também os arquivos de código necessários,
a DLL do ambiente, dependências compartilhadas, Server16 e os 33 assets
estáticos. Não contém a animação SubsOn nem modelos de outros mods.
É extraído diretamente na raiz do FIFA com jogo e Server fechados.

O gerador confere o manifesto dos assets e todos os hashes do ZIP. Antes de
compactar, executa o Server16 incluído em uma pasta nova com nome Unicode,
sem caches de desenvolvimento, e gera as três telas iniciais genéricas.
Os dados da carreira são preparados novamente no computador do jogador.
Não inclui saves, histórico financeiro, caches locais, índices BH, instaladores
ou `enabled.txt`; a habilitação do módulo na base V12 instalada é preservada.
Esse teste confirma a preparação do pacote, não a imagem renderizada na GPU
do destinatário.

Na revisão R61, nome e número usam os hotspots UV do RX3 original de cada kit,
incluindo posições diferentes no uniforme de goleiro. A numeração não usa mais
uma altura fixa da malha suspensa, que podia atravessar a região do nome.
O nome utiliza a fonte selecionada pelos arquivos nativos do FIFA, sem margens
de interface ou deslocamento XYZ; nomes longos mantêm altura e são condensados
na largura do hotspot. Sem hotspot válido, a impressão correspondente é omitida
em vez de cair numa posição genérica. Os RX3 nativos permanecem intactos.

A DLL monitora o processo auxiliar e tenta novamente se ele encerrar. A criação
usa um ambiente independente do executável congelado, sem modificar o ambiente
do FIFA. `native_helper_startup.log` registra stdout/stderr e `native_room.log`
registra o erro de criação ou código de saída. Não há novos hooks globais.
O pacote testa o runtime congelado com `--club-environment-check` e gera telas
neutras separadamente em staging; não ativa BHs nem altera a sessão aberta.
O mod de ocultar o card online da EA permanece desativado e fora deste ZIP.
