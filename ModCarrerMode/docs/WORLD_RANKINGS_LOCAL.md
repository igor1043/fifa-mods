# Rankings mundiais e seleções no globo — teste local, 29/10/2026

Sem commit, push ou mudança de saves. A instalação tem backup em
`code-release/world_rankings_20261029/before/` e manifesto próprio de rollback.

## Acessos

- Temporada → carrossel de Estatísticas dos jogadores / Estatísticas do time →
  **Ranking de clubes**.
- Temporada → carrossel de Outras ligas → **Ranking de seleções**.
- Nas telas de ranking, **Técnicos** abre a classificação dos treinadores desta carreira.
- Ver clubes → **Clubes / Seleções** no cabeçalho, por mouse ou botão indicado
  no HelpManager original. Escudos e bandeiras são lidos no FIFA, sem cópias.

Os três rankings usam APT e desenho nativo como Competições, com fundo do tema,
cards claros e seleção dourada `#B9A274`. A tabela inteira é navegável, incluindo
equipes além do top 150. A tela abre na posição do clube humano; a de seleções
foca a seleção treinada pelo usuário, se houver, ou o país do clube.

L1/R1 (LB/RB), X/C no teclado: mudar ranking. L2/R2 (LT/RT), W/E: percorrer o
filtro escolhido. O botão superior alterna região/liga. Analógico esquerdo ou
setas percorrem equipes; direito vertical ou Page Up/Down percorrem páginas.
Selecionar volta à equipe do usuário. Mouse seleciona abas, filtros e linhas;
roda do mouse rola a tabela. B/Esc retorna à carreira. As legendas vêm do FIFA.

## Método e pesos

Este é o **ranking da carreira**, não a classificação oficial baixada da internet.
Todos os valores iniciais vêm da força e reputação da DB instalada; não há lista
fixa de clubes ou de ligas autorizadas. As regras editáveis ficam em
`ModCarrerMode/data/club_browser/ranking_rules.json`.

- **Seleções:** fórmula SUM, `Pnovo = P + I × (resultado − expectativa)`, com
  divisor 600. Qualificatórios pesam 25; torneios continentais 35/40;
  Mundial 50/60. O patch não fornece a janela internacional dos amistosos: eles
  usam 10. Perdas em eliminatórias de torneios finais não retiram pontos.
- **Clubes:** Elo com K=28, ponderado pela força média dos participantes da
  competição. Pesos-base: liga 1, copa 0,9, supercopa 0,65, continental 1,6,
  mundial 2 e amistoso 0,3. Mata-mata recebe fator 1,15. Título confirmado soma
  36 × peso, com fator anual 0,8. K e bônus por título foram reduzidos para
  suavizar as mudanças entre atualizações. A pontuação inicial é exibida separadamente.
- **Técnicos:** usa somente jogos gravados com o vínculo individual do treinador
  no banco de dados da carreira. Aproveitamento é suavizado com uma referência
  neutra de 24 jogos e ponderado pela confiança da amostra; jogos dirigidos somam
  `28 × ln(1 + jogos)` pontos. Cada título registrado vale 12 pontos, até cinco.
  Assim, poucos jogos não bastam para levar um técnico ao topo. A tabela mostra
  aproveitamento, partidas atribuídas, títulos e os últimos resultados reais.
- Janela de quatro anos, limitada ao histórico que o FIFA ainda disponibiliza
  no save e na publicação nativa. Não se inventam partidas ou títulos anteriores
  que já não estejam nesses dados. Não existe um arquivo externo de resultados
  futuros que possa contaminar uma carreira mais antiga.
- Jogos simulados sem placar individual entram pela publicação nativa de
  classificações e, na ausência dela, pelos totais da **mesma carreira salva**
  em `leagueteamlinks`. A DB padrão não fornece resultados substitutos.
  `career_results.py` reutiliza a projeção global do mercado de técnicos e
  remove agregados de fases que já possuem grupos descendentes.
- A campanha agregada soma apenas a diferença em relação aos jogos individuais
  da temporada atual, sem criar adversários, datas, gols ou confrontos fictícios.
  Seu componente de pontuação é separado do Elo/SUM e vale
  `campaign_scale × peso × (3V + E − 1,25J) × min(1, 38/J)` sobre a diferença;
  `campaign_scale` é 1,5. Para seleções, o peso SUM é dividido por 25 neste
  componente próprio do mod. Portanto, o total das seleções é uma adaptação
  SUM + campanha, não uma reprodução oficial da FIFA.
- J/V/E/D e aproveitamento seguem os totais da classificação da competição.
  Esses totais podem tratar desempates por pênaltis como V/D enquanto o placar
  individual conserva o empate. O placar original é preservado para Elo e
  detalhes; gols e últimos resultados ausentes ficam indisponíveis.
- Sem cronologia individual da campanha agregada, não se inventa a seta de
  variação do ranking: ela fica neutra. Os últimos placares disponíveis são
  identificados assim, e não como se cobrissem toda a campanha.
- A **Seleção Clássica** (id 111205) fica fora do ranking de clubes por uma regra
  explícita em `ranking_rules.json`; ela não recebe pontos de força inicial por
  ser uma equipe de exibição.
- Os treinadores são lidos em modo somente leitura da base do Mercado de Técnicos
  da carreira ativa. Nenhuma campanha agregada de clube é atribuída ao treinador:
  sem vínculo individual de jogo, não há como provar quem comandou aquela partida.
  Por isso, o painel identifica quantos jogos de técnicos estão registrados.

O resumo do time na tela do técnico usa a mesma fonte para J/V/E/D, pontos e
aproveitamento geral/mandante/visitante, por competição. Uma passagem comprovada
desde o início da carreira pode receber toda a campanha. Treinadores contratados
depois conservam somente partidas com vínculo/datas identificados; totais sem
data não são atribuídos ao sucessor. Nenhum esquema SQL é alterado por essa leitura.

Uma copa só recebe bônus depois da final completa; ida sozinha não vale título.
Sem vencedor de pênaltis disponível, empate no agregado não cria um campeão.
Ligas exigem o calendário completo de pontos corridos e liderança isolada em
pontos; uma metade de temporada europeia não é tratada como temporada inteira.
São critérios conservadores para não premiar uma classificação ainda indefinida.

Fontes consultadas:

- [Procedimento SUM da FIFA](https://inside.fifa.com/en/fifa-rankings/world-ranking/procedure-men).
- [Fórmula, pesos e condições](https://digitalhub.fifa.com/m/f99da4f73212220/original/edbm045h0udbwkqew35a-pdf.pdf).
- [Critérios do Mundial de Clubes](https://www.fifa.com/en/tournaments/mens/fifa-club-world-cup/articles/fifa-council-confirms-key-details-club-world-cup-2025).

A regra do Mundial de Clubes não cobre todas as ligas domésticas. O algoritmo
de clubes desta tela é uma adaptação própria, explicitada acima.

## Catálogo e integridade

A auditoria da instalação encontrou 1.731 registros de equipes: **1.647 clubes,
83 seleções e um placeholder sem liga/elenco jogável (TIME EXTRA)**. A tela de
clubes exclui a Seleção Clássica, ficando com 1.646 equipes ranqueadas. O save
consultado tem tabelas ao vivo de 65 ligas e campanhas com jogos de 1.341 clubes;
foram 1.121 partidas com placar individual e resultados agregados adicionais.
O FC Barcelona aparece com 11 jogos, 8 vitórias, 2 empates e 1 derrota via tabela
da temporada; como não há 11 placares individuais publicados, sua sequência de
forma permanece vazia e a tela agora explica essa origem.

`teamnationlinks`, `leagueteamlinks`, `leagues` e `nations` definem os tipos e
vínculos. A inicialização do auxiliar verifica a revisão da DB e publica um
catálogo gerado; o globo recarrega quando a publicação muda. Assim uma nova liga
entra sem adicionar um ID ao código. Coordenadas/cidades já ajustadas no catálogo
são mantidas, com referência geográfica de país para os novos registros.

Os resultados em RAM só são aceitos com PID, criação do processo, clube, arquivo,
tamanho, data de gravação e data da carreira validados. Uma resposta antiga é
descartada quando a carreira/data/pedido muda. Ausência temporária da publicação
tem espera limitada e nova tentativa automática. A consulta não pede ao usuário
para salvar; o save fornece a escala histórica e a RAM sobrepõe placares atuais.

`runtime/club_browser` recebe as publicações JSON/TSV; um pedido em
`runtime/manager_market/read_request.tsv` solicita a leitura nativa dos totais.
DATA, INDEX, DB nativa,
SQL de empréstimos/finanças e catálogo de técnicos não são modificados.

## Validação da revisão anterior (29/10)

Testes de fórmula SUM, pesos, título/ida/volta, temporada cruzando janeiro,
duplicidade, retorno de calendário, mais de 150 clubes, novo campeonato sem
allowlist, navegação APT, filas obsoletas e publicação atrasada. O teste C++
`native/test_ranking.cpp` lê a projeção real, exercita filtros e seleção e desenha
as duas páginas em D3D11 WARP com os assets do jogo, conferindo restauração do
estado gráfico. As capturas ficam no diretório local de evidências.

Essa lista documenta os testes feitos na revisão de 29/10. A revisão local de
30/10 ainda precisa de conferência visual pelo usuário dentro do FIFA; os números
de campanha são recalculados ao abrir o ranking com o save atual.
