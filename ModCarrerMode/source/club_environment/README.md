# Ambiente do clube e telas da carreira

Requer a base FIFA Friends V12 e Server16 0.2.15. Fontes Python/CPP, auxiliares de
APT e interfaces ficam neste repositório. Modelos, texturas e poses do vestiário
são fornecidos no ZIP separado. O histórico anual está desativado.

## Revisão de 24/10/2026

R62 mantém as poses e texturas estáticas no complemento, incluindo `jersey_pose_0.npz` e `jersey_pose_2.npz`, para funcionar em instalação limpa. Kits seguem os hotspots originais; a troca de cenas e a liberação do fundo preservam o ambiente 3D. A próxima partida invalida o contexto anterior quando clube, data ou confronto mudam. Empréstimos e e-mails têm serviço de fundo e persistência por clube/save. Mercado e Ver clubes mantêm seus próprios auxiliares, sem interferir no ciclo do vestiário.

As telas distribuídas são neutras, aguardando dados da carreira. A preparação delas foi executada em uma pasta nova com nome Unicode usando o executável Server16 incluído. Não são copiadas telas, elencos ou extratos gerados na sessão do desenvolvedor.

### Correção de primeira inicialização — 24/10/2026

Auxiliares iniciados diretamente por plugins agora preparam o runtime antes de executar sua entrada. Isso corrige `FileNotFoundError` em `ModCarrerMode/runtime/club_environment/preview/prepare.py` quando o supervisor ainda não iniciou ou a cópia gerada foi removida. A sincronização preserva contratos e dados da carreira.

Atualize o Server16Python.exe e a pasta ModCarrerMode/source pela branch FIFA Friends V12, com jogo e Server fechados. O ZIP complementar de assets continua o mesmo. Se também faltar `ModCarrerMode/source/club_environment/preview/prepare.py`, a atualização do código está incompleta: o ZIP de modelos não substitui os fontes do GitHub.

Teste da revisão: o executável congelado criou os runtimes ausentes e executou as entradas de vestiário, banco e próxima partida em três pastas novas com nomes Unicode, sem iniciar FIFA nem instalar drivers. Testes de recuperação verificam também a preservação do livro financeiro. Os demais módulos e recursos embutidos foram preservados.

## Instalação

1. Feche FIFA e Server16. Atualize a base pela branch `fifa-friends-v12` do GitHub,
   incluindo o Server16, DLLs, fontes, interfaces, Lua e configurações publicadas.
2. Extraia `FIFA-Friends-Assets-Complementares-20261024.zip` diretamente na raiz
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

Empréstimos: até dois contratos ativos, até duas contratações por ano da carreira,
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
33 assets estáticos do ambiente, duas texturas do globo e a animação SubsOn. O gerador recusa qualquer
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


### Conferência sem o runtime do desenvolvedor

O gerador do complemento agora só publica o ZIP depois de exportar os arquivos do commit Git para uma pasta nova, extrair o próprio complemento e executar os testes nessa combinação. Confere todos os módulos habilitados, 191 arquivos do manifesto, poses, geometria, texturas, mipmaps e iluminação do vestiário, importações do Server16 e a recuperação dos auxiliares antes de existir runtime.

Também compara o módulo de inicialização realmente embutido no executável com seu fonte publicado, evitando distribuir um EXE antigo junto de fontes corrigidos. O relatório do complemento registra o commit de código e o SHA-256 do Server16 compatível. Nenhum runtime, cache ou contrato do PC do desenvolvedor entra nesse teste. O teste anterior de importação preparava o runtime antecipadamente e não cobria essa ordem do primeiro início; a regressão foi adicionada após o erro relatado pelo Robson.

Ferramenta de desenvolvimento: `ModCarrerMode/tools/Verify-PortablePackage.py`. Não é um instalador e não precisa ser executada pelo jogador. O ZIP continua com 36 assets e sem arquivos de código repetidos. O código e o executável corrigido precisam ser atualizados pela mesma entrega do GitHub.

### Correções de vestiário e auxiliares — 25/10/2026

O vestiário tinha os modelos prontos, mas sua câmera ignorava o estado 13 de um estádio carregado. Agora aceita os estados 1 e 13, mantendo a validação da projeção e a restauração da câmera. A recuperação foi confirmada pelo usuário na sessão aberta; modelos, texturas e os demais mods foram preservados.

O auxiliar dos titulares inicia com ambiente congelado independente e herda somente seus canais de entrada/saída. O Server grava a saída de cada auxiliar em `service.log`, evitando que um stdout inválido encerre a preparação. A tela detecta quando o auxiliar termina e permite tentar novamente. Erros do exportador preservam saída e código de encerramento.

O complemento de 36 assets continua o mesmo; esta revisão altera código, DLLs e Server16. A visualização dos titulares no PC do Robson ainda precisa de validação. Para comparar os computadores, use `ModCarrerMode/tools/Coletar-Diagnostico-Carreira.ps1`: ele gera um ZIP de logs e hashes, sem copiar saves, contratos SQL, modelos ou executáveis.
