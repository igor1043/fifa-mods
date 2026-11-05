# Menus e Voltar — 04/11/2026

## Comportamento

- Aposentadoria e Outro clube enviam o identificador `Navigation.BACK` retornado
  pelo ION do FIFA, em vez do texto literal `Back`. ESC, o botão de retorno do
  controle e a ação Voltar seguem a mesma função. O retorno independe do
  carregamento dos dados; uma trava impede dois retornos pela mesma tecla.
- Foram auditados os 15 pacotes próprios, incluindo telas de espera, vestiário,
  jogadores, competições, rankings, mercado, técnicos, empréstimos e finanças.
  As 12 rotas NAV têm caminho de retorno ao hub; as vistas internas do
  vestiário voltam primeiro ao próprio vestiário.
- A pasta de artes recebida tem prioridade visual: ícones dos cards, novos
  desenhos dos mercados, descrições, posições e dimensões. Os seis layouts
  ativos foram comparados com a instalação. IDs, providers, destinos, estados
  e parâmetros funcionais são preservados, inclusive no calendário.
- RARs, layout alternativo `-rzm` e a cópia de trabalho de um DDS não são
  instalados. O espelho do layout da carreira acompanha o XML ativo.

## Distribuição

Os 23 ícones novos/alterados, os layouts, os dois BIGs de retorno, os fontes e os
testes desta revisão são distribuídos pelo Git. Os demais assets continuam na
base e nos complementos anteriores; esta revisão não requer um novo ZIP.

Oito ícones antes externos passaram para o Git. O manifesto retira essas entradas
dos próximos complementos; o verificador ignora suas versões antigas nos ZIPs
anteriores. Em uma extração manual, instale os ZIPs antigos primeiro e aplique
esta atualização do Git por último para conservar os ícones novos.

O manifesto `ModCarrerMode/data/catalogs/menu_layout_20261104.json` lista os
arquivos visuais desta revisão com tamanho e SHA-256. Configurações pessoais,
bancos do mod, saves, modelos, animações e lógica das simulações não são alterados.

## Validação e recuperação

O teste de retorno executa o APT instalado usando um identificador numérico de
navegação, para detectar o caso que os testes antigos com o texto `Back` não
detectavam. Também verifica ESC, ausência de dados, duplicidade de eventos,
desligamento dos listeners e os caminhos de saída dos NAVs. O pack passou pela
checagem de contratos XML e pela decodificação dos DDSs.

Foram aprovados 116 testes automatizados: navegação, menus, empréstimos,
finanças, apresentação do mercado de técnicos e distribuição dos assets.

A instalação atual foi conferida por hash entre jogo e desenvolvimento. O backup
individual anterior está em `local-review/menu-layout-back-20261104/before/`,
com relatório `installed.json` e restauração `Restaurar.ps1`. A conferência
visual dos novos menus e do retorno no FIFA ainda depende do teste em jogo.
