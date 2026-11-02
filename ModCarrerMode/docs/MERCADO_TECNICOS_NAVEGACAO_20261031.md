# Mercado de técnicos: navegação e trajetória

Revisão de apresentação e comandos, sem mudança das regras de demissão,
contratação, salários ou persistência da carreira.

- Navegação espacial dos cards: cima/baixo acompanha as linhas; esquerda/direita
  acompanha as colunas. Na aba de clubes, baixo leva aos filtros de país e liga
  antes dos técnicos. Em movimentações, as duas colunas permanecem acessíveis.
- Filtro de nacionalidade com a bandeira correspondente. O filtro de idade foi
  retirado do painel, preservando a idade informada nos perfis.
- Analógico direito troca páginas das listas. Em movimentações, rola a coluna
  de contratações ou demissões conforme o foco, uma linha por vez.
- Passagens pelos clubes mostram clube, datas, vínculo atual/encerrado, jogos,
  vitórias, empates, derrotas, gols e aproveitamento geral, com uma única barra.
- Histórico avança uma passagem por vez, com três entradas visíveis e indicador
  vertical de rolagem. Direcional, analógico direito, setas de histórico e evento
  de roda do mouse movimentam a lista. Títulos preservam sua aba independente.

O painel informa o clube atual apenas quando existe contrato ativo. Os dados
continuam restritos às passagens e partidas atribuídas ao técnico nesta carreira.

Backup e relatórios em `code-release/manager-navigation-20261031`.

## Revisão de rolagem, mouse e foto

- L2/R2 muda o mês compartilhado pelas contratações e demissões. Cada coluna
  mantém sua própria posição de rolagem e tem barra visível; roda do mouse,
  direcional e analógico direito também movimentam a coluna selecionada.
- Sem setas de paginação nas listas principais nem atalhos de ano na interface.
  Clubes da liga usam dots para até 16 páginas, com o atual em dourado.
  Livres no mercado mantém o contador e os comandos de paginação, sem dots.
- Hover do mouse atualiza apenas o foco, preservando o card entre pressionar
  e soltar o botão; o clique abre o perfil correspondente.
- A foto do perfil conserva a arte nas cores do clube, sem a moldura decorativa
  externa dourada e cinza. O tema das outras partes do painel foi preservado.

Validação: 83 testes do grupo managers passaram, incluindo clique após hover,
navegação espacial, dots, mudança de mês e rolagem independente.
Backup desta revisão: `code-release/manager-scroll-20261031/before`.
