# Ícones das competições

Edite **`<ID_DO_INI>.png`** nesta pasta. O ID corresponde à competição principal
na seção `[movies]`/`[Scoreboard]` do `FSW/settings.ini` instalado.

| Competição | Imagem |
| --- | --- |
| Brasileirão Série A | `1761.png` |
| Copa do Brasil | `1620.png` |
| Libertadores | `1460.png` |
| Carioca | `2442.png` |

Calendário, Próxima Partida na Central e A seguir/Resultados na aba Competições
partem da mesma imagem. O Server16 prepara `calendar/c<ID>.dds` (canvas 128,
área proporcional 48) e `cards/c<ID>.dds` (canvas 256, logo proporcional).
As duas versões preparadas já acompanham o pacote: abrir sem Server também funciona.
Não edite essas versões; altere o PNG e abra o Server antes de iniciar o FIFA.

`competitions.tsv` e `COMPETICOES.txt` são gerados a partir da instalação, sem
edição manual. A tradução de uma carreira antiga usa a identidade visual da
própria carreira para achar o ID do INI atual. O ID de uma partida nunca escolhe
uma competição. Identidade ambígua ou imagem ausente não é substituída por outra.

Não são necessários os antigos `artAssets/cmCalendarCompetitions/cmcomp_*.big`
para estes ícones. O código reconhece o pedido antigo e o direciona ao DDS;
não lê nem extrai BIG durante o jogo. Não apague os BIG que montam as telas,
como `game/screens/career/calendar.big`, ou outros recursos do FIFA.

O pacote possui imagens para 153 competições. Cinco entradas assinaladas `***`
no INI não possuem arte de liga na instalação de origem: 1061 (Bélgica 2),
1159 (League Cup), 1257 (Costa Rica), 1277 (Honduras), 1918 (CAF CL).
Elas precisam de seu PNG correspondente; nenhuma recebe um logo de outro torneio.
