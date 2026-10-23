# Ambiente do clube e telas da carreira

Requer a base FIFA Friends V12 e Server16 0.2.14. Fontes Python/CPP, auxiliares de
APT e interfaces ficam neste repositório. Modelos, texturas e poses do vestiário
são fornecidos no ZIP separado. O histórico anual continua como experimento local.

## Instalação

1. Feche FIFA e Server16. Atualize os arquivos da base V12.
2. Extraia o ZIP `FIFA-Friends-Ambiente-Clube-20261022.zip` na raiz do FIFA,
   preservando `data` e `ModCarrerMode`.
3. Execute `ModCarrerMode/install-club-environment.cmd`.
   Ele verifica cada asset por SHA-256, prepara as telas iniciais e libera apenas
   as entradas da interface nos índices BH locais, com backup.
4. Abra o Server16 atualizado e inicie o jogo. Não precisa instalar Python,
   NumPy, Pillow, ScoreboardStudio ou ferramentas de RX3 no computador do jogador.

O instalador geral `ModCarrerMode/install-game.cmd` também inclui as fontes
necessárias em tempo de execução. Não substitua os índices BH pelos de outro PC.

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
