# Sala do treinador R76 — revisão local

Interior reconstruído, sem janelas, com 240 cm adicionais de profundidade.
Área útil aproximada de 10,7 x 10,3 m. Entrada na mesma posição; vestiário,
parede complementar R75, hidratação e departamento médico preservados.

## Mobiliário e decoração

- Mesa de 2,8 m com gaveteiros, cadeira do treinador e duas cadeiras de visita.
- Notebook com teclado modelado, tablet, prancheta, relatórios, canetas, squeeze,
  caneca, porta-canetas, luminária de mesa e pequeno quadro do clube.
- Estante com livros/pastas individuais, troféu decorativo e bola nativa do FIFA.
- Camisa real do clube emoldurada, mural existente em escala menor, relógio
  analógico decorativo e duas plantas com folhas curvas e vasos.
- Armário de apoio, seis quadros/telas de análise e luminárias de teto simples.
- Cores primária/secundária do clube e sobrescritas opcionais da configuração R75.

O troféu é decoração, não uma conquista atribuída à carreira. O relógio é um
objeto decorativo. Os 40 murais editáveis dos clubes não foram alterados.

## Dados dos painéis

Tática/escalação atual, campanha, desempenho em casa e fora, últimos placares,
classificação compacta da liga, destaques do elenco, notas, gols, assistências,
composição por posição, contratos e crescimento potencial.

`room_coach_data_r76.py` usa a arquitetura compartilhada `career_results` e
`manager_market.global_performance`. A mesma campanha vista por resultados
individuais e contadores agregados não é somada duas vezes. Suplementos de
classificação são unidos por slot/competição/clube da publicação validada.
Vínculos e atributos vêm do elenco da carreira. Não há escrita no save nem no
banco; resultados do banco base não são usados como jogos da temporada.

O painel de mercado representa composição e contratos do próprio elenco.
Não inventa propostas/negociações. Informações ausentes aparecem como ausentes;
não são gerados números de posse, finalizações ou rastreamento/heatmap fictícios.

## Malhas, navegação e desempenho

A remoção dos objetos antigos recorta triângulos compartilhados para preservar
a metade médica das paredes. Nenhum buffer nativo fica vazio. Pisos, tetos e
cores do clube compartilham materiais existentes; apenas quatro grupos extras
são necessários, incluindo o atlas 4096 x 4096 com oito páginas e decoração.

Há seis novas vistas em Cenas: visão geral, tática, desempenho, mercado,
destaques e classificação. Móveis e vasos têm colisores. O limite longitudinal
da câmera nativa passa a 2545 cm. As novas malhas têm caminhos R76 para evitar
recursos R75 em cache. As texturas dos painéis têm hash do conteúdo.

## Testes e rollback

`code-release/coach-room-r76-20261101`: backup `before-r76.zip`, instalador,
rollback por arquivo, 20 testes Python, testes nativos de câmera e circulação,
checagem de buffers RX3 e duas montagens completas (Criciúma e Flamengo).
As prévias são renders offline das malhas/texturas finais; validação visual
dentro do FIFA permanece pendente. Sem commit nem push.
