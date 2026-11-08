# Novos técnicos — 06/11/2026

Importação dos doze modelos nativos enviados em MANANGER BR. O cadastro segue
`manager_registry.ini`: um ID estável por pessoa e um ID SLC independente do
clube. Sete identidades já existiam no catálogo; cinco pessoas foram adicionadas.
Os vinte brasileiros já instalados foram reconhecidos e seus RX3 preservados.

Os IDs de origem 200–211 usam IDs SLC 190200–190211, verificados contra o catálogo
de clubes e os arquivos já instalados. Não representam clubes com esses números.
Sete clubes/seleções mantêm o vínculo inicial que já estava no catálogo e recebem
a aparência nova fora da carreira. Os cinco sem vínculo conhecido ficam livres.
A importação não modifica contratos, histórico ou atribuições de saves existentes.

O pacote atualiza 32 retratos a partir das imagens fornecidas, preservando os
caminhos já usados pelos perfis existentes. O INI continua editável; não é necessário
alterar um JSON de hashes para cadastrar um personagem.

Foram preservados o rig nativo de 31 ossos, a forma da cabeça/queixo, o UV e as
coordenadas. Houve revisão localizada do peso medial das calças em dez modelos,
remoção de placeholders cinzas em Arteta/Arbeloa e limpeza de pele encoberta no
Arbeloa. Os buffers BC3 dos últimos mips vieram inválidos nos doze pacotes: foram
reconstruídos com seus descritores, sem mudar a imagem de maior resolução. A
transparência já existente no cabelo é preservada nos novos modelos.

O renderizador FFCOACH2 foi recompilado para ler o SLC indicado no INI, mantendo
clube de destino e identidade do personagem separados. Os auxiliares do jogo
foram alinhados à revisão S16MGR2 já presente na DLL. Nenhuma nova DLL é necessária.
Reinicie FIFA/Server16 para usar a revisão completa.

Verificação: exportação dos doze modelos para um clube de teste distinto; 252
instantes em três animações nativas; prévias de corpo e cabeça; checagem dos RX3,
buffers, paleta, pesos e retratos; testes de preservação de contratos ao importar
novas identidades e restaurar checkpoint. A avaliação visual dentro da partida
continua pendente. Não houve commit/push.

[Lista de técnicos e IDs](TREINADORES_INSERIDOS_20261106.txt)
