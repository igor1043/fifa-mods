# Revisão de finanças e vestiário — 28/10/2026

Esta revisão consolida os ajustes instalados e testados localmente após a
entrega anterior do mesmo dia. Fontes e binários correspondentes ficam no Git.
O executável do Server16 não mudou nesta revisão; continua na versão 0.2.19.

## Finanças do clube

O Escritório contém o acesso ao painel financeiro. A tela nativa oferece visão
geral, receitas, despesas, transferências, salários, dívidas, orçamento e
configurações, com os comandos originais do FIFA. Inclui gráficos mensais,
distribuição das receitas, ícones, divisórias e barras proporcionais. As listas
de jogadores e negócios usam os dados disponíveis da carreira e as imagens do
próprio jogo. O pacote inicial distribuído é genérico, sem uma carreira pessoal.

Os switches mudam no clique e aguardam confirmação do serviço. A confirmação
mantém aba/foco; erros restauram o valor confirmado. Contratos de TV calculados
por competição pagam por jogo concluído; bilheteria é adicional e estimada nos
jogos como mandante. Salário do técnico gera débito mensal proporcional. O
serviço compartilha o diário e as validações do mod de empréstimos, usando
preferências e registros SQL separados por carreira, clube e checkpoint.

Não há nova cobrança da folha nativa dos jogadores nem estimativa apresentada
como contrato comercial real. O teste econômico completo de receber uma nova
receita, fechar um mês, salvar e reabrir ainda deve ser conferido no FIFA.
Consulte [as regras e limitações](../source/club_environment/bank/FINANCAS_V1.md).

## Compatibilidade da carreira

A captura médica do vestiário espera `Fifa16CareerHooksReady`. Isso evita
alterar os setters antes da validação do núcleo e impedir a ativação do
adaptador de capacidade de memória. O usuário confirmou a abertura da carreira
antiga após a correção. Não foi necessário editar ou reparar DATA/INDEX.
[Diagnóstico e proteção da inicialização](STARTUP_MEDICAL_COMPAT_20261028.md).

## Vestiário e câmeras

O elenco usa uma posição no piso livre à frente da mesa, um único escudo no
cabeçalho e luz interna ajustável, com intensidade 2,3 confirmada no jogo.
O desenho preserva a animação e os materiais originais. As sombras de contato
sob as chuteiras são mantidas; os experimentos de sombra nativa de corpo em RAM
não fazem parte desta revisão permanente.

O teto alinha as luminárias à grade modular. Os cabides recebem um varão ligado
ao armário. A opção Câmera livre mantém a cena nativa: WASD/analógico esquerdo
anda, mouse com botão direito/analógico direito olha, Shift/clique do analógico
esquerdo acelera. A caminhada é de 1,70 m/s, a corrida de 2,80 m/s. Passos geram
um balanço visual discreto e cessam quando parado ou bloqueado.

Todas as câmeras internas — cenas, carregamento, livre e elenco — usam corte
próximo de até 5 cm. O corte de aproximadamente 83 cm herdado do estádio
recortava modelos próximos. O plano distante é preservado e a projeção original
é restaurada ao sair, respeitando outro proprietário e mudanças de cena.

A colisão da caminhada usa uma cápsula contínua e deslocamentos de até 6 cm,
incluindo tampos finos e macas. Duas caixas legadas de folhagens decorativas
ocupavam quase toda a sala do treinador. Elas são excluídas da colisão; paredes,
batentes, folha da porta e móveis mantêm seus obstáculos. A geometria não muda.

## Instalação e assets

Com FIFA/Server fechados, atualize os arquivos do Git e extraia
**FIFA-Friends-Assets-Delta-Vestiario-20261028.zip** na raiz do jogo. Preserve os
complementos anteriores de modelos e pose. O novo delta contém somente:

- `data/sceneassets/server16_dressing_room_20261022/room_roles_r68.rx3`
- `data/sceneassets/server16_dressing_room_20261022/ceiling_r68.rx3`
- `data/sceneassets/server16_dressing_room_20261022/locker_support_r68.rx3`
- `data/sceneassets/server16_club_xi/player_contact_shadow_r1.rx3`

São malhas próprias, conferidas por SHA-256 entre jogo/desenvolvimento. Não
incluem cópias das imagens nativas, saves, SQLite, caches ou testes em RAM.

## Verificação

`source/scripts/run_regressions.py` inclui os testes de colisão real, projeção
interna e inicialização médica. O teste de caminhada percorre a porta do
treinador nos dois sentidos, mantém os bloqueios laterais/porta e verifica
tampos finos, eixos, balanço e consistência a 30/120 FPS. O teste de projeção
verifica baseline, restauração, troca de proprietário/cena e plano distante.
As suítes existentes verificam finanças/empréstimos, próximas partidas, mercado,
elenco, animação, isolamento dos cards e renderização nativa. Simulações não
substituem o teste visual em cada GPU do destinatário.

Nesta revisão passaram 52 suítes da execução de regressões, incluindo 267
testes Python e os executáveis nativos. A suíte adicional do navegador nativo
(GPU WARP, animação, cards, contexto e câmeras) e o verificador do pacote com
26 plugins também passaram. A economia ainda exige o teste completo de
receita/fechamento mensal/salvar e reabrir descrito acima.
