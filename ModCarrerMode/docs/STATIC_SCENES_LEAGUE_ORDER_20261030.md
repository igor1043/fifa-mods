# Estabilidade dos 11 iniciais e do mascote; ordem das ligas

Os jogadores animados já usam buffers privados dinâmicos, upload DISCARD e
associação persistente ao desenho nativo do FIFA. As poses estáticas dos XI e
dos mascotes passam a usar o mesmo caminho. Dois quadros idênticos mantêm a
pose original: não são acrescentados movimentos. A preparação da GPU também
é executada nos XI, que não têm singleView ativado.

Os coeficientes de material passam a usar o mesmo payload nativo completo,
incluindo os mipmaps, usado pelo jogador estável. Geometria, UVs, normais e
texturas de cor são preservadas. A expansão e o carregamento dos buffers
acontecem fora da interface, com verificação de sequência, clube e carreira
antes de publicar. As chaves dos caches mudam para que um pacote estático
antigo não seja reutilizado sem a nova preparação. Os arquivos originais e os
saves não são alterados.

Na visualização de clubes, a ordem segue primeiro a pirâmide nacional por
divisão, depois federações/regionais e clubes independentes. A classificação
usa país e nível do banco e o rótulo regional do catálogo, sem lista fixa de
IDs de ligas. No Brasil aparecem Série A, B, C, D e Divisão de Acesso; depois
as federações. O mesmo vale para países com várias divisões instaladas.
Nenhum clube foi removido ou transferido de liga por essa alteração.

Verificações:

- 13 testes Python: preparação estática, preservação dos bytes, materiais,
  quatro cards, foco, controles, retorno e ordenação de ligas instaladas e
  novas ligas em um país adicionado.
- GPU WARP com os pacotes reais de mascote e XI: 1.200 quadros com associação
  persistente e uploads DISCARD; bytes da pose/UV/normais permanecem iguais;
  rearmamento da entrada de desenho e seleção de outro clube verificados.
- Jogador animado: regressão de 240 quadros aprovada.
- Cena nativa: 2.000 quadros; XI estático habilita a mesma preparação do
  jogador, com restauração da câmera e ocultação ao sair.
- Catálogo real: os mesmos 1.647 clubes e 83 seleções; Brasil, Inglaterra,
  Alemanha, Itália e Espanha conferidos na auditoria.

A estabilidade visual no FIFA ainda precisa ser confirmada pelo usuário.
Instalação local, sem commit ou push. Backups e manifestos em code-release,
indicados por static-scene-stability-current.txt.
