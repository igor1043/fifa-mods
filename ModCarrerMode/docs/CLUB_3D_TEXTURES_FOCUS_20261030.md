# Clubes 3D: números, câmera e foco — 30/10/2026

## Texturas de números

O Argentinos Juniors (130160) usa `specifickitnumbers_130160_0_0_1.rx3` com textura nativa sem compressão (formato 3, 512×1024). O leitor de personalização aceitava somente DXT1/3/5. O erro de um decal opcional interrompia a preparação do jogador inteiro.

O leitor agora aceita os formatos nativos DXT1/3/5, A8R8G8B8, L8 e A8L8. Converte somente o decal gerado para o formato RGBA interno e preserva dimensões, alfa e canais, respeitando o passo entre linhas. Os pixels DXT são preservados sem recompressão na leitura. Também aceita diretórios RX3b, normalizando somente os metadados, sem ampliar o leitor geral de geometria RX3. Valida nomes, dimensões, tamanho, passo e limites antes de utilizar cada candidato.

Uma fonte de números inválida passa para o próximo candidato nativo, na precedência já existente. O relatório `kit_personalization.number_fallbacks` identifica os candidatos ignorados. O nome, o corpo, o uniforme e o save não são alterados. A versão da chave de cache dos atores foi incrementada para não reutilizar preparações antigas. Não é necessário apagar caches.

Verificação do patch instalado: 4.183 arquivos, 41.830 texturas de número, formatos 1 (26.550), 2 (90) e 3 (15.190), sem metadados inválidos. Os 447 arquivos RX3b também passaram na leitura dos dez números e na decodificação de uma imagem por arquivo. A preparação real de Brayan Cortés (215086) e Kevin Coronel (71078), no clube 130160, produziu atores completos com nome e número e preservou o hash do save.

## Onze iniciais

A câmera do jogador individual já era aplicada antes do callback original do frame. Nos onze iniciais, era aplicada somente depois. Agora ambos os modos aplicam a câmera antes de a engine calcular visibilidade/culling e mantêm a publicação do objeto entre frames. A restauração ao sair continua protegida pela comparação dos valores escritos pelo mod. A pose, a malha e a animação não foram trocadas.

O teste nativo verifica a câmera antes do callback original em 180 frames de cada modo, restauração antes do callback inativo e publicação estável do objeto por 2.000 frames. A confirmação visual no FIFA ainda deve ser feita na instalação final; esse teste isolado verifica a ordem de execução e o estado, não grava uma sessão real de vídeo.

## Foco dos três cards

APT é a única origem do foco para mouse, teclado e controle. Movimento, clique e retorno publicam o índice absoluto (`focus_xi`, `focus_roster`, `focus_coach`), em vez de manter duas cópias incrementais independentes. Os métodos de abrir card registram o próprio índice, mesmo quando o clique não é precedido por hover. Eventos de hover de cards ocultos são ignorados. O detector nativo independente de posição do mouse foi removido dessa escolha; o desenho usa o foco publicado pelo APT.

A volta publica primeiro o comando de retorno e depois o foco do card, mantendo a ordem na fila. O fluxo dedicado do vestiário, os detalhes do jogador, os rodapés e as rotas existentes foram preservados.

## Validação e instalação

22 testes Python passaram, incluindo leitura de números, fallback, ciclos de mouse/teclado/controle, fotos e navegação de técnicos, coeficientes e rotas do vestiário. A integração executou o bytecode APT gerado para navegador e vestiário, com retorno e ciclo de vida equilibrados. O teste nativo de foco fez 200 ciclos pelas três opções. A DLL de produção foi recompilada com os mesmos compilador, SDK e dependências da instalação anterior.

Instalação local no jogo e no desenvolvimento com backup e manifesto SHA-256 em `code-release/club_3d_fix_20261030_152643`. Nenhum arquivo DATA/INDEX, DB, kit original ou catálogo de técnicos é escrito por esta revisão. Sem commit ou push.
