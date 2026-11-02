# Orientação visual do mascote — revisão 31

A pose recebe uma correção visual de 180 graus em torno do eixo vertical.
O rumo lógico continua apontando para o destino durante a caminhada e para
o centro do campo nas paradas e comemorações. A correção é aplicada uma vez
na paleta privada, antes da compensação do bind do modelo. Os ângulos nativos
continuam neutros. Percurso, velocidade, seleção de paradas e cadência dos pés
permanecem iguais; o replay registra e restaura a pose já orientada.

Validação: testes de locomoção com os 63 pacotes locais, caminhada em ambos
os sentidos, orientação visual para o gramado nos dois gols, pausa, troca de
lado, seis comemorações e restauração do replay; testes de políticas e posição
nativa também passaram. Conferência visual na próxima sessão ainda pendente.

A DLL em uso não pôde ser sobrescrita, mas o Windows permitiu mover seu arquivo
para o backup e instalar a nova DLL no caminho original. A sessão aberta mantém
a versão 30 carregada; a revisão 31 será usada na próxima abertura do FIFA.
Nenhum controle de interface nem alteração da memória do jogo foi realizado.
Backup e build: code-release/mascot-facing-20261031.
