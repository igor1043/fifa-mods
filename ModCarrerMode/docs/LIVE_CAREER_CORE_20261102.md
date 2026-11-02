# Leitura da carreira e mercado de técnicos — 02/11/2026

Revisão local. Sem commit nem push. O FIFA permaneceu aberto durante o diagnóstico.

## Origem do problema

O arquivo nativo ainda estava em 01/01/2026, enquanto a sessão estava em
01/12/2026. A publicação nativa continha 6.511 registros de classificação;
o arquivo tinha 1.659. A validação antiga exigia que os slots novos também
existissem no arquivo antigo: descartava o avanço inteiro ao encontrar um slot
criado durante a simulação. Mercado e perfil do treinador ainda descartavam
explicitamente as tabelas de ligas recebidas da RAM.

## Correção instalada nos auxiliares

- `career_publication.py` valida PID, criação do processo, contexto/época, clube,
  data, caminho, tamanho e revisão do arquivo carregado. A estrutura atual não
  precisa ter os mesmos nós e slots do último salvamento.
- `derived_campaigns.py` aceita slots pertencentes ao grafo atual validado.
  Não associa gols antigos a contadores atualizados. Uma sessão inválida não
  pode recuperar o cache de progresso não salvo de uma sessão anterior.
- Mercado e perfil do treinador preservam as tabelas atuais das ligas. Não há
  lista fixa de clubes, ligas, países ou saves nesta seleção.
- O serviço não espera concluir o lote opcional de classificações estrangeiras
  para processar as partidas datadas já disponíveis. Uma publicação de ligas
  temporariamente vencida é aguardada; não provoca retorno às tabelas antigas.
- A assinatura do lote suplementar usa o conteúdo, não a data de modificação.
  Renovar a publicação sem mudar os dados não refaz a simulação/apresentação.
- Resultados datados são processados cronologicamente em saltos de calendário.
  Classificações agregadas alimentam campanha e avaliações sem inventar
  adversários, placares ou datas históricas que o FIFA não guardou.
- Resultados de pênaltis e placares de empate da mesma partida não contam duas
  vezes nas estatísticas do treinador.
- Repetir a abertura do perfil ou mudar de aba não duplica jogos ou decisões.

## Salvamento e recuperação

O histórico continua no SQLite do mod, associado ao hash do salvamento nativo
e aos recibos reais de escrita. DATA, INDEX e o banco nativo são somente lidos.
Uma escrita após salto de calendário não deve receber um checkpoint de uma data
antiga: o serviço aguarda alcançar a data exata e valida novamente o recibo,
processo, contexto, clube e conteúdo do arquivo antes de associar o histórico.

Foi mantido o ramo anterior do mercado e criada uma recuperação a partir do
checkpoint de janeiro, reproduzindo apenas resultados datados retidos na RAM.
O ramo anterior permanece no SQLite. Campanhas com decisões legítimas não são
automaticamente reescritas por essa migração.

Na sessão analisada: 965 jogos datados de 2026, 101 identificadores de ligas na
publicação primária, 82 tabelas válidas com jogos e 175 competições com evidência.
Essas contagens são desta carreira, não limites do sistema. No Flamengo, foram
confirmados 68 jogos; o usuário confirmou os perfis de um clube brasileiro e de
um clube de outra liga. Sem lista de resultados por data, não se atribuem novas
demissões retroativamente a meses específicos com base numa tabela de dezembro.

## Próximas contratações

Política aplicada apenas às novas contratações, sem mudar vínculos existentes:

- Na escala 1–10, o técnico pode superar o clube em até 1,5 ponto de reputação.
- A atratividade da liga é calculada pelos clubes da própria carreira: 65% da
  média do quartil superior + 35% da média geral, com ajuste por divisão.
- A reputação do técnico não pode superar essa atratividade em mais de 3 pontos.
  Técnicos com reputação >= 8 exigem atratividade da liga >= 5,5.
- A oferta preserva pelo menos 80% do último salário mensal do treinador e passa
  pela capacidade anual do clube. O valor aprovado é o efetivamente contratado.
- Nacionalidade, desempenho recente e aleatoriedade continuam na seleção entre
  candidatos elegíveis. Uma exceção de qualidade não ignora os limites acima.
- Sem candidato compatível, promove-se um interino, em vez de uma contratação
  de elite incompatível com o clube/liga.

Os parâmetros ficam nas regras do mercado por carreira, com inclusão aditiva
que preserva valores personalizados. A atratividade não é uma classificação
oficial externa; é uma regra do mod calculada a partir do patch carregado.

## Copas: instalado localmente em 02/11/2026

- Grupos permanecem antes do mata-mata durante a fase de grupos. Ao chegar ao
  mata-mata posterior aos grupos, ele vem primeiro e os grupos seguem abaixo.
  Eliminatórias anteriores aos grupos não antecipam essa troca.
- Melhor defesa em copas exige pelo menos 70% da maior amostra de jogos e
  prioriza a fase mais avançada entre os elegíveis, antes da média de gols.
- Melhor goleiro considera a fase alcançada, a mesma amostra mínima e nota
  ponderada pela amostra. A nota mostrada continua sendo a nota real.
- Layout original dos grupos, placares de ida/volta, zoom e navegação preservados.

O novo registro TSV `P` depende da DLL nova. Ambos foram instalados juntos após o
fechamento manual do jogo; o backup fica no diretório `installed-cups-*` da revisão.

## Validação e backup

- 110 testes do mercado executados: 109 aprovados; 1 depende de `LUA51_DLL`.
- 55 testes de publicação, perfis, campanhas e competições aprovados.
- Build nativo, testes de publicação/cena, identidade do técnico, escopo do
  modelo e navegação/layout aprovados.
- Renderização D3D11/WARP verificou os dois sentidos da ordem das fases e a
  restauração do estado gráfico, viewport e scissor.
- `PRAGMA quick_check`: `ok`; nenhum clube com dois técnicos ativos.
- Hash e data de modificação do DATA nativo permaneceram iguais durante a correção.

Backup, cópias SQL para teste, logs e build:
`code-release/live_career_core_20261102_091932/`.

O teste de mesa não substitui simulação longa e troca real entre carreiras no
FIFA. A confirmação em duas ligas foi feita na sessão atual; novos ciclos de
salvar/carregar também são cobertos por testes isolados.
