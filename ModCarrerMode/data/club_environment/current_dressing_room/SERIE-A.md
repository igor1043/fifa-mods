# Coleção Série A — vestiários custom

20 artes originais criadas com a ferramenta integrada `image_gen`, usando os
20 clubes da liga 7 da base instalada do patch. São interpretações artísticas,
não fotografias de vestiários oficiais. Os escudos permanecem nos assets do FIFA.

Cada pasta `custom/<ID>/` contém:

- `locker-frame.png`: estrutura dos armários;
- `locker-backing.png`: fundo de nicho, 768 × 1536;
- `corner-panel.png`: painéis diagonais dos cantos;
- `feature-wall.png`: painel atrás do quadro, 1024 × 1280;
- `wall-mural.png`: mural da outra parede, quando disponível;
- `hydration-wall.png`: arte da hidratação, quando disponível;
- `fascia-*.png`: quatro imagens das faixas superiores;
- `profile.json`: associação das imagens às áreas e acabamentos do clube.

As frases foram escritas para esta coleção, sem pretensão de serem lemas
oficiais; o Flamengo mantém as quatro frases da customização já aprovada.
Preferências existentes do usuário têm prioridade sobre os defaults do perfil.
Selecione **Custom do clube** no estilo geral e no fundo dos nichos para usar
as novas imagens. A composição dos armários pode continuar branca, preta,
cinza ou amadeirada. Basta sair e entrar no vestiário para recarregar a arte.

| ID | Clube | Conceito |
| --- | --- | --- |
| 1039 | Athletico-PR | Furacão urbano |
| 1035 | Atlético-MG | Pedra e galo |
| 1598 | Bahia | Mar e mosaico |
| 517 | Botafogo | Céu alvinegro |
| 112476 | Chapecoense | Floresta e renovação |
| 1041 | Corinthians | Gravura urbana |
| 111044 | Coritiba | Raízes e araucárias |
| 568 | Cruzeiro | Mapa celeste |
| 1043 | Flamengo | Asas rubro-negras |
| 567 | Fluminense | Jardim tricolor |
| 1629 | Grêmio | Trama do Sul |
| 1048 | Internacional | Arcos colorados |
| 113163 | Mirassol | Voo amarelo-verde |
| 383 | Palmeiras | Palmeiras e mosaico |
| 123921 | RB Bragantino | Energia gráfica |
| 130026 | Remo | Rios e leão |
| 1053 | Santos | Mar e porto |
| 598 | São Paulo | Arquitetura tricolor |
| 569 | Vasco da Gama | Carta náutica |
| 1719 | Vitória | Garra rubro-negra |

O cache RX3/DXT5 com mipmaps foi preparado previamente para evitar a primeira
conversão ao trocar os acabamentos. Ele é derivado dos PNGs; os PNGs e perfis
são as fontes editáveis para manutenção e redistribuição do pack.

## Faixas superiores por clube

`theme.banner.panels` associa quatro imagens nesta ordem: fundo esquerdo,
fundo direito, lateral esquerda e lateral direita. Cada item usa `mode: "image"`
e um `asset_key` com o nome da entrada em `assets`. Por exemplo:

```json
{"mode":"image","asset_key":"fascia_back_left"}
```

As ilustrações são composições do catálogo autoral, sem retratar um vestiário
oficial. O Flamengo mantém suas quatro frases anteriores. Nos outros clubes,
a composição varia conforme a identidade visual. Textos e ilustrações são
editados no PNG, sem frases em JSON ou letras na malha. O modo geral Default
usa imagens geradas com a identidade genérica do clube. Os registros de geração
das artes foram retirados das pastas de uso; não são dependências do jogo.
