# Tema das telas dos mods

Arquivo central: `ModCarrerMode/data/custom_ui_theme.json`.

| Token | Hexadecimal | Uso |
|---|---|---|
| `accent` | `#B9A274` | Fundo dos itens selecionados, tabs e destaques |
| `accent_text` | `#17242C` | Texto sobre a seleção dourada |
| `accent_ink` | `#76623D` | Links e números de destaque sobre os cards brancos |
| `accent_hover` | `#C8B58F` | Variação de foco |
| `accent_soft` | `#EEE7DA` | Áreas suaves do tema |
| `focus_outline` | `#E5D4B0` | Contorno da navegação |
| `surface` | `#FFFFFF` | Referência do card branco |
| `paper` | `#F4F6F7` | Referência do painel claro |

Os geradores APT usam `source/club_environment/ui_theme.py`; o desenho nativo
de clubes, elenco, técnico e competições usa `source/common/custom_ui_theme.h`.
Ambos leem o mesmo JSON. Não é necessário recompilar para editar os hexadecimais;
feche FIFA/Server e reabra para carregar a configuração e regenerar as telas.
Valores inválidos usam os padrões. Esta primeira versão centraliza os destaques;
os diferentes cards claros conservam suas variações de branco/cinza existentes.

O texto da seleção é escuro para ter contraste no dourado escolhido. Os textos
de destaque sobre branco usam uma variante mais escura do dourado. As cores de
uniformes, posições no campo e estados esportivos/financeiros (vitória, derrota,
pago, atrasado, gols etc.) mantêm seus significados.

Mercado não desenha mais um retângulo azul opaco atrás da tela; usa o fundo
personalizado do FIFA, como Empréstimos e Próxima partida. A abertura inicial usa
`data/fifarna/splash.fsh`, com a arte GOAT dourada fornecida pelo usuário.
Globo, elenco, técnico e vestiário conservam o estádio/ambiente 3D ao fundo.

O widget online EA/Q fica oculto no seu próprio APT. A atribuição existente de
visibilidade positiva é trocada por negativa, com o mesmo tamanho e pilha; o
primeiro quadro também começa transparente. Não acrescenta funções ActionScript,
interceptadores nativos nem chamadas de conexão. Texturas do layout são mantidas.
