# Contratos e campanhas dos técnicos

A leitura do perfil combina placares individuais com os contadores reais das
competições, por vínculo, temporada e competição. Publicações FCE parciais ou
vazias deixam de ocultar a tabela completa da liga. A regra vale para todas as
ligas, sem lista de campeonatos permitidos.

O banco auxiliar do mod ganhou appointment_campaigns, incluída nos checkpoints
e nas ramificações da carreira. Nenhuma partida é inventada: os resultados
recentes e gols continuam vindo dos placares disponíveis. Contadores agregados
complementam jogos, vitórias, empates, derrotas e aproveitamento. Um contratado
novo recebe uma base para não herdar a campanha do antecessor; dados históricos
que não permitem essa separação não são retroativamente atribuídos.

O perfil e as passagens mostram o término do contrato; o atual também informa
dias restantes. Novas contratações podem receber um vínculo até o fim da
programação conhecida da temporada. Na ausência de calendário, aplica-se a
referência semestral/anual da liga. A chance padrão de contrato curto é 25%.
Renovações usam renewal_months (12 por padrão), em vez de contract_months (24).
No vencimento, há 15% de chance determinística de o técnico não renovar,
sair livre e permitir reposição do clube. As decisões automáticas preservam
o técnico controlado pelo usuário. Os parâmetros ficam em market_rules.

Validação: suíte managers com 88 testes, mais 13 testes específicos após o ajuste
final de seleção da fonte. Na cópia da sessão atual, 33 clubes espanhóis passaram
a apresentar campanha registrada, contra cinco na leitura anterior.

Backup dos fontes, banco auxiliar anterior à instalação, relatórios e validação
por clube: code-release/manager-complete-20261031. A instalação é local.
