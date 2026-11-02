# Vestiário — interior 71

Revisão local de 01/11/2026. A estrutura de armários, as posições das salas,
os pontos das câmeras e as portas abertas existentes foram preservados.
Não há alteração na carreira, no banco de dados, na lógica do mascote ou na iluminação aprovada dos jogadores.

- Retiradas as 35 barras escuras sobre os assentos.
- Cabides ficam dentro do volume das camisas comuns e de goleiro; gancho/varão permanecem ligados.
- Placas dos jogadores e setores: área do escudo na cor primária e área do texto na secundária. Fundo branco ou quase branco usa texto preto; os demais usam branco.
- Grafismos nas paredes, mural central, portas pretas abertas para os setores e saída de duas folhas fechadas.
- Teto modular de 60 cm com LEDs quadrados alinhados nos ambientes principal, técnico e médico, sem a antiga sobreposição.
- Madeira escurecida; hidratação com bancada, prateleira, toalhas, recipientes, garrafas e refrigerador com frente transparente.
- Novos obstáculos apenas na bancada e no refrigerador. A saída dupla permanece fechada e mantém a parede como limite.

## Artes por clube

Pasta: `ModCarrerMode/data/club_environment/room/clubs/<ID>/`.

`mural.png`: proporção recomendada 3:1, por exemplo 3072 × 1024. O Flamengo (1043) recebe a arte baseada na referência fornecida. Nos demais clubes, sem arquivo próprio, o mural usa as cores, o nome e o escudo corretos automaticamente.

Opcionais `sign_medical.png`, `sign_coach.png`, `sign_water.png`, `sign_exit.png`: placa inteira, proporção 4:1, por exemplo 2048 × 512. Sem esses arquivos, as placas são geradas com as cores e o escudo do clube. Trocar os PNGs dispensa recompilar a DLL; o serviço detecta a mudança e publica novos recursos. Ao trocar com a sala aberta, sair e entrar novamente permite recarregar a decoração com segurança.

As imagens editáveis ficam fora dos RX3; os RX3 gerados usam hash do conteúdo e mipmaps completos. Uniformes, fontes e estampas nativas são apenas referenciados.

## Validação e retorno

A sala completa foi montada fora do jogo: 228 grupos (limite nativo 256), 373 instâncias. Há renderizações de revisão usando as próprias malhas e texturas; elas não substituem o teste visual no FIFA.

Backup: `code-release/locker-room-interior-r71-20261101/vestiario-anterior-completo.zip`. Inclui sala anterior, arquivos fonte, recursos de inicialização e DLL anterior. `rollback.py` reverte os arquivos desta instalação após o FIFA fechar, conferindo os hashes para não sobrescrever edições posteriores. Os caches antigos permanecem disponíveis.

Sem commit ou push nesta revisão.
