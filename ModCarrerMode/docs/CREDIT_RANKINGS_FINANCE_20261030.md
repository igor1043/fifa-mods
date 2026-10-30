# Crédito, rankings e conferência financeira — 30/10/2026

## Crédito simulado do clube

Até quatro empréstimos ativos e quatro contratações por ano da carreira. Intervalo de dois meses de calendário desde a última aprovação, mesmo se o contrato anterior for quitado. Contratos históricos mantêm taxa, parcelas e saldo originais.

A capacidade usa orçamento-base da DB (não o saldo inflado por empréstimos), prestígio atual, força do elenco, folha e divisão atual do save. Tetos de referência: 1ª divisão 150 milhões, 2ª 12 milhões, 3ª 4 milhões, 4ª 1,5 milhão e demais 750 mil. São limites totais de principal: a dívida existente reduz a margem, e cada banco oferece uma fração da capacidade. Um clube do porte do Flamengo pode alcançar ofertas de 100 milhões; isso não significa aprovação automática. O Criciúma da carreira inspecionada é da divisão 2 e tem capacidade total de 12 milhões.

Parâmetros ficam nas tabelas adicionais `credit_rules` e `credit_banks` do mesmo `server16_loans.sqlite3` ao lado da carreira. A primeira abertura cria um backup SQLite consistente `server16_loans.before-credit-v1.sqlite3`. IDs antigos de valores, bancos e contratos foram preservados; novas faixas foram acrescentadas sem renumerá-los.

Cada recusa bloqueia aquele banco por um mês de calendário a partir da decisão. Outros bancos continuam disponíveis, com análise própria e risco maior por recusa recente, dívida, atraso, valor e prazo. O sorteio e a cotação ficam gravados na proposta; reabrir a tela não sorteia outra resposta. Pedidos fora da capacidade são rejeitados antes de qualquer crédito. A confirmação também revalida a capacidade.

Valores usam o símbolo do slot monetário escolhido na carreira e os rótulos do patch (Real, Euro etc.). Não há conversão de câmbio nem alteração do inteiro contábil só pela formatação.

## Receitas e fluxo de caixa

TV, bilheteria e patrocínio incorporam o prestígio do clube e a força financeira/esportiva da liga principal atual, obtidas dos participantes, orçamento-base, classificação de divisão e prestígio internacional. Assim, uma liga rica pode sustentar um clube menor; rebaixamento reduz os ganhos futuros. Bilheteria continua exclusiva de jogos em casa e fora de campo neutro. A prévia usa os mesmos termos do acordo financeiro.

A revisão dos acordos existentes começa no dia seguinte à atualização. Não reprecifica partidas já contabilizadas, não refaz pagamentos e não credita retrospectivamente as diferenças do modelo novo. Salário do técnico, comissão, custos de jogos e juros continuam no livro e respeitam os switches.

Na auditoria da carreira Criciúma em 24/08/2026, o lote registrado conciliou exatamente: 13.581.316 + 414.308 = 13.995.624. As despesas de maio e junho estavam presentes no livro, pagas após o avanço do calendário; o gráfico as agrupava no mês de pagamento. Agora o gráfico/resumo usa o mês de origem, e o extrato de caixa conserva o mês efetivo de aplicação. As duas consultas têm o mesmo total acumulado.

Antes de escrever no orçamento nativo, a ponte exige que a soma assinada dos eventos corresponda exatamente à diferença de saldo. A escrita mantém os guardas de sessão/clube/data/contexto/tela e leitura de confirmação da RAM. O painel lê o próprio orçamento do FIFA. A persistência em DATA ocorre pelo salvamento nativo do jogo; o mod não escreve DATA ou INDEX diretamente.

A compilação das telas ocultas é adiada durante avanço rápido de calendário até haver pausa estável, evitando que a geração visual bloqueie o relógio financeiro. Tela visível recebe prioridade. Cobranças não realizadas por saldo insuficiente continuam pendentes, sem duplicação.

## Rankings

L1/LB volta uma aba, R1/RB avança. Quadrado/X leva ao topo; triângulo/Y leva à própria posição. Home/End fornecem atalhos adicionais no teclado. Os botões funcionam nos três rankings.

Clubes recebem maior peso por força e prestígio doméstico/internacional. Técnicos combinam porte do clube, aproveitamento suavizado pela amostra, volume de jogos e títulos confirmados. O próprio componente de clube é reduzido quando há poucos jogos. Fonte de campanha permanece a arquitetura compartilhada de resultados e tabelas de todas as ligas disponíveis; o ranking não altera essas tabelas.

## Referências de escala

Os balanços são referências de porte, não limites de crédito concedidos por bancos. Não existe um teto universal oficial dedutível apenas da divisão de um clube; os tetos e taxas deste mod são regras de simulação ajustáveis em SQL.

- Flamengo, demonstrações financeiras 31/03/2026: https://images.flamengo.com.br/public/arquivos/transparencia/19/1777579037016.pdf
- Criciúma, demonstrações financeiras 2024: https://www.criciuma.com.br/upload/financeiro/2025-balanco-patrimonial-2024-20250530145624.pdf

## Validação local

Cálculo de crédito, carência por banco, intervalo de dois meses, quatro contratos, exposição, juros congelados, SQL/salvamento, conciliação, meses de origem/caixa, liga/prestígio, controles e telas nativas verificados em testes. Leitura da carreira ativa: 1.646 clubes de ranking, 83 seleções, 195 técnicos, 52 ligas com tabelas e 1.118 clubes com jogos. Save nativo permaneceu com o mesmo SHA-256 durante a auditoria somente de leitura. Renderização nativa das três abas e restauração do estado gráfico verificadas com D3D11 WARP.

O recurso experimental de gramado foi conservado, mas o switch fica oculto e o padrão desativado. Instalação local, sem commit ou push.
