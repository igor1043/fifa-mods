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

O calendário precisa de um BIG/APT e das texturas com os nomes nativos.
Ao iniciar o FIFA, career_ui_assets gera `cmcomp_<1000000+ID>.big`,
`cmCalendarCompetitions<1000000+ID>.dds` e as versões light/dark do mesmo ID.
Os cards recebem `league/light|dark/l<1000000+ID>.dds` da mesma imagem.
Os BIGs gerados são necessários. Se forem apagados, a DLL os recria no
próximo início. Os DDS preparados usam cabeçalhos DXT5 compatíveis com o FIFA.

A biblioteca possui 158 competições. As raízes alternativas 1061, 1257 e 1277
usam a arte da mesma liga identificada no INI. Leagues Cup (1159) e CAF CL (1918)
usam seu próprio troféu nativo; os arquivos recebidos não contêm seus logos.
