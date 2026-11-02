# Vestiário — revisão 72

Os 40 clubes das Séries A e B instaladas no patch recebem mural próprio. O Flamengo mantém sua arte aprovada; as outras 39 imagens foram geradas individualmente e revisadas em duas folhas de contato. O catálogo `ModCarrerMode/data/club_environment/room/clubs/serie-a-b.json` identifica clubes, divisões, IDs, dimensões e hashes. PNGs continuam substituíveis por ID, sem recompilar a DLL. A sala carrega somente a arte do clube em uso.

A área principal ganhou 360 cm no sentido longitudinal, após Z=815 cm, preservando armários, camisas e pontos de visualização do elenco. O bloco de serviços, as portas, o mural, a área médica, a sala técnica, seus quadros, escudos, sombras, obstáculos e câmeras avançam juntos. Piso e teto mantêm sua escala; a faixa adicionada recebe seis painéis de luz. A câmera livre alcança a nova parte da sala e conserva o limite externo.

Placas médica/técnica: superfícies de 132 × 33 cm, centradas em cada passagem e proporcionais às imagens 4:1. Foram removidas as deformações causadas pelas placas antigas de 205 × 29 cm.

Hidratação: recipientes laranja com tampa, frisos, alças e torneiras; squeezes verdes; copos; garrafas com ombro/gargalo/tampa e rótulos, em três famílias de bebidas; bandeja, bancada, puxadores, prateleiras e toalhas; refrigerador com vidro e interior separados. Esses materiais mantêm as cores dos produtos ao trocar de clube. Apenas a decoração usa as cores do time.

Foi convertido e instalado o modelo gratuito Water Cooler do Grab3D, 10.144 triângulos e duas partes, com suas texturas e transparência. O original GLB, a licença CC0 e a procedência ficam em `ModCarrerMode/data/club_environment/room/external/grab3d-water-cooler/`.

Referências visuais: https://www.gatorade.com/equipment e https://floridagators.com/news/2017/10/17/football-florida-and-gatorade-partner-for-innovative-fuel-truck . Modelo e licença: https://grab3d.com/models/electronics/water-cooler/ e https://grab3d.com/dl/water-cooler/LICENSE.txt . Não foram reproduzidos logotipos de fabricantes nos recipientes próprios.

Validação fora do FIFA: montagem Criciúma com 232 grupos/362 instâncias, Flamengo com 241 grupos/386 instâncias (limite 256); 15 testes Python; teste nativo de câmera/controles/colisões; prévias renderizadas com as malhas/texturas finais. A conferência visual dentro do FIFA ainda é necessária.

Backup prévio: `code-release/locker-room-interior-r72-20261101/before-r72.zip`. O backup completo anterior da revisão 71 também permanece preservado. `rollback.py` restaura somente os arquivos desta instalação, com conferência de hashes para proteger edições posteriores. Nenhum save ou banco de dados é alterado. Sem commit ou push.
