# Chaveamento por fases

Revisão local de 31/10/2026. Mantém os participantes, os vínculos de avanço,
os jogos de ida e volta e os agregados lidos da carreira. Não inventa
classificados em disputas empatadas ou ainda não encerradas.

O cabeçalho usa o nome e o logo da competição. A final possui um card próprio
no centro, com o troféu do ID da competição encontrado em `trophy256x256` ou
`trophy128x128`. Não há substituição por um troféu genérico quando o arquivo
não existir. Finalistas, placares e datas aparecem quando registrados.

As fases têm abas e colunas. As fases finais recebem o enquadramento inicial
para manter o texto legível em copas com muitos jogos. Selecionar uma fase
enquadra seus confrontos e dá preferência ao confronto do clube da carreira,
quando presente. Todos os confrontos continuam acessíveis por movimentação.
As conexões usam exclusivamente os vínculos nativos de avanço.

## Indicadores inferiores

- Maior goleada: maior diferença de gols em uma partida já disputada.
- Artilheiro e líder de assistências: estatísticas da competição ativa.
- Melhor goleiro: maior nota média validada, exigindo pelo menos metade do
  número de jogos do goleiro mais utilizado. Não confunde gols sofridos do
  clube com partidas individuais sem sofrer gols.
- Melhor defesa: menor média de gols sofridos por jogo, com no mínimo metade
  da quantidade de jogos do clube que mais jogou. O card mostra também o
  total sofrido e a quantidade de jogos.
- Melhor ataque: maior total de gols marcados nos jogos registrados.

Os jogos futuros, os placares desconhecidos e as repetições de um mesmo jogo
não entram nas contas. Dados ausentes aparecem como indisponíveis.

## Controles na visualização ampliada

| Ação | Mouse | Teclado | Controle |
|---|---|---|---|
| Mover | Arrastar com botão esquerdo | Setas | Direcional / analógicos |
| Zoom | Roda sobre o chaveamento; botões − / + | − / +, W / E, PageDown / PageUp | L2 / R2 |
| Escolher fase | Abas; setas ao lado das abas extensas | X / C | L1 / R1 |
| Ajustar enquadramento | Ajustar | Enter | Confirmar |
| Voltar ao painel | Fechar | Esc | Voltar |

O zoom do mouse preserva o ponto sob o cursor; os analógicos têm zona morta
progressiva e o movimento considera o tempo entre quadros. A câmera é
limitada à área do chaveamento para evitar se perder no fundo vazio.

## Validação e recuperação

Testes de resultados válidos, deduplicação, notas de goleiros, seleção de
fases, zoom ancorado, movimento, protocolo e navegação APT. Renderização D3D11
WARP com os dados reais do save, incluindo Copa do Brasil e Catarinense;
restauração dos estados gráficos do FIFA conferida pelo teste nativo.

Backup anterior e registro da instalação em
`code-release/bracket-design-20261031`. As projeções do save nessa pasta são
privadas. Nenhum arquivo nativo DATA/INDEX ou banco original do FIFA é
modificado por esta tela. Sem commit ou push nesta revisão.
