# Base de competições — FIFA Friends V12

Atualização de 17/10/2026: base **DB v12.11 / Honduras**, CompData e `FSW/settings.ini` enviados pelo autor do pacote.

## Instalar o conjunto completo

Com o FIFA e o Server desta instalação fechados:

```powershell
ModCarrerMode/install-game.cmd -GameDirectory "C:\Seu FIFA 16" -UpdateCompetitionData
```

Essa opção instala DLC, CompData, settings.ini, banco e traduções da mesma versão.
Os arquivos substituídos são guardados no backup do instalador. O settings.ini
do pacote passa a ser a referência dos vínculos de competições. Configurações
pessoais dos módulos e a preferência de física das roupas ficam preservadas,
exceto quando a opção separada `-ReplaceConfiguration` é solicitada.

Para atualizar somente os mods, omita `-UpdateCompetitionData`. Um CompData e
um settings.ini já instalados ficam preservados juntos. As conexões de pastas
com um pacote externo também são preservadas; a atualização completa não grava
através dessas conexões. Atualize o pacote de origem nesse caso.

O instalador não converte nem edita carreiras salvas. A atualização instala a
base do jogo e os vínculos dos mods; a estrutura já gravada em um save continua
pertencendo àquela carreira.

## Por que os IDs mudaram

Os números dos objetos do calendário podem mudar quando competições e fases
são inseridas no CompData. Nesta atualização, por exemplo:

| Competição | Antes | Atual | Identidade visual |
|---|---:|---:|---:|
| Série A | 1738 | 1761 | 7 |
| Série B | 1741 | 1764 | 83 |
| Série C | 1747 | 1770 | 350 |
| Série D | 1757 | 1780 | 351 |
| Paulista | 2325 | 2348 | 22 |

Não se aplica uma soma fixa aos IDs. O mod lê o CompData instalado e procura a
identidade exata da competição e da fase. Identidades ausentes ou ambíguas não
recebem um recurso de outra competição.

## Ícones, suportes e aberturas

- **Ícones:** o catálogo interno agora inclui a identidade da competição. O
  carregador nativo e o Server resolvem essa identidade para o número atual.
  O nome dos DDS visuais continua igual: a Série A usa `c7.dds`.
- **Imagens novas:** coloque, por exemplo, `1761.png` na pasta dos ícones e abra
  o Server antes do FIFA. O Server gera a lista `COMPETICOES.txt`, converte a
  imagem e atualiza o índice. Não é necessário editar tabelas.
- **Suportes das bolas:** a seção interna `identities` do standball usa a
  identidade da liga (7, 83, 350, 351 e 22). Fases e amistosos verificados são
  resolvidos pelo calendário atual. A configuração numérica foi atualizada
  também para compatibilidade com os arquivos do pacote.
- **Objetos de abertura (18/10/2026):** cada pasta usa exatamente o ID atual
  da competição ou fase: `competitions/1761` para a Série A. Server e DLL
  buscam diretamente esse número, sem tabela de conversão. Quando há ID de
  fase, somente ele é consultado; uma fase sem modelo não herda o pacote da
  competição principal. Sem pacote válido para o ID selecionado, não há objetos.
  As 251 pastas foram atualizadas, com 116 modelos. Ao instalar em outra máquina,
  substitua a pasta completa de modelos pelo pacote atual para não misturar IDs.
- **VAR:** continua usando as identidades das ligas 7 e 83, sem alterar decisões
  de arbitragem. Mascotes, escudos e cores dos clubes continuam ligados aos
  IDs dos clubes do banco.

O `FSW/settings.ini` enviado permanece byte a byte como recebido. Quando um nome
de vídeo ou placar mudou entre as bases, o Server consulta o catálogo interno
`presentation_package_aliases.tsv` para localizar um pacote antigo existente.
Uma pasta com o nome atual tem prioridade. Sem pacote disponível, conserva o
comportamento original de fallback; esse vínculo não cria vídeos ou placares.

O pacote de imagens disponível não contém DDS dedicados para os IDs visuais
440, 1208, 2006, 3003 e 3034. Nesses casos o carregador mantém o caminho original
do jogo. É possível adicionar a arte depois pela importação normal do Server.

## Manutenção do código

`career_competition_icon_map.tsv` usa quatro campos internos:
`dica_numérica|ícone_visual|nome_CompData|texto_CompData`. Os dois últimos campos
identificam o objeto; a dica numérica não substitui uma identidade diferente.
Arquivos antigos com dois campos só são aceitos quando a raiz instalada já
confirma o mesmo ID visual.

Os ícones e suportes usam `source/common/competition_identity.h`; o Server
possui a resolução equivalente em `server16_py/competition_catalog.py`.
As aberturas usam IDs diretos em `entrance_selection.h` e
`server16_py/entrance_props_runtime.py`. Os testes verificam que tabelas antigas
não redirecionam a seleção e que fases sem pacote ficam sem objetos, mesmo
quando existe um modelo para a competição principal.

Ao atualizar o pacote de CompData, mantenha seus nomes e identidades coerentes.
Se essas identidades também mudarem, revise os vínculos internos; não reutilize
um número antigo para apontar silenciosamente a outro campeonato.
