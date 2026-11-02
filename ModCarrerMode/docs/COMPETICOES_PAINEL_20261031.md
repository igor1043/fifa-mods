# Painel de competições — revisão de 31/10/2026

Aplicação local, sem commit ou push. A seleção de campeonatos usa as inscrições
e os jogos da carreira ativa; não existe uma lista de ligas permitidas.
O formato e a disponibilidade dos dados seguem a própria competição.

- Artilheiros e assistências em dois cards independentes, com três jogadores
  visíveis por vez e posições em ouro, prata e bronze.
- Coluna direita com barra de rolagem: time do campeonato, prévia de jogador
  do mês e prévia de técnico do mês, com miniface e escudo quando disponíveis.
- Página de resultados com a numeração nativa das rodadas, datas, horários,
  escudos e placares. Jogos adiados permanecem na rodada original. Jogos ainda
  não disputados aparecem como agendados.
- Grupos e chaveamentos das copas preservados; esta revisão não redesenha
  a lógica de mata-mata.

## Comandos

| Ação | Controle | Teclado / mouse |
|---|---|---|
| Campeonato anterior / próximo | L1 / R1 | X / C; abas e setas do cabeçalho |
| Card anterior / próximo | L2 / R2 | W / E ou Tab / Shift+Tab; clicar no card |
| Rolar o card em foco | Direcional ou analógico esquerdo vertical | Setas para cima / baixo; roda sobre o card |
| Rolar campinho e destaques | Analógico direito vertical | PageUp / PageDown; roda e barra visível |
| Abrir resultados | Quadrado / X do Xbox | Botão “Ver rodadas” |
| Rodada anterior / próxima | L1 / R1 ou direcional horizontal | X / C ou setas; botões da página |
| Rolar jogos da rodada | Analógico direito ou direcional vertical | Roda; setas para cima / baixo |
| Ampliar tabela / chaveamento | Confirmar | Enter; título do card esquerdo |
| Voltar ao painel | Voltar | Esc; fechar no alto da página |

Nas copas, o direcional horizontal com foco na tabela continua selecionando
grupos/fases. O botão superior alterna grupos e chaves. Home / End e as setas
visíveis do card também selecionam grupos/fases.

## Apuração mensal e persistência

O jogador do mês usa as diferenças entre notas, jogos, gols e assistências
observados no mês por competição. Notas acumuladas na temporada não são
apresentadas como notas mensais. Se a instalação ocorrer no meio do mês,
o card informa a data inicial do acompanhamento. Sem evidência suficiente,
mostra “Histórico mensal em formação”. Saltos de calendário entre meses
iniciam um período parcial quando não houver observação na virada do mês.

O técnico do mês usa os resultados datados em que o técnico estava
identificado no histórico do mercado. Não atribui retrospectivamente todos
os jogos do clube ao técnico atual.

As observações são gravadas em `competition_monthly.sqlite3`, ao lado do
histórico de técnicos, e vinculadas ao ramo da carreira. O salvamento cria um
checkpoint por hash; recarregar o save restaura apenas o histórico pertencente
àquele salvamento. A leitura da tela valida processo, carreira e hash do save.
A captura ocorre no processo auxiliar em segundo plano, sem exigir esta tela
aberta. Os arquivos nativos DATA/INDEX e o banco original do FIFA não são
alterados por este painel.

## Validação

Testes de navegação APT/HelpManager, separação de carreiras e checkpoints,
apuração mensal, calendário e protocolo nativo. Renderização D3D11 WARP com
dados reais da carreira: Série B com 38 rodadas e 380 jogos; pódios, rolagem,
copas e restauração dos estados gráficos. A navegação física com controle
permanece sujeita à conferência no jogo pelo usuário.

Backup e registro da instalação em
`code-release/competition-dashboard-20261031`. Não distribuir as projeções
privadas do save contidas nessa pasta.
