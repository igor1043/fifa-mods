# Origem do tema global no Server16

O Server16 copia `FSW/ScoreBoard` para `data/ui/game` ao preparar o jogo e ao
restaurar o placar padrão. Portanto, atualizar somente
`data/ui/game/globalcomponents/globalcomponents.big` é temporário: a próxima
inicialização restaura o arquivo que está em FSW.

A integração visual de 29/10/2026 mantém o mesmo `globalcomponents.big` nas
duas pastas e na variante instalada que também o fornece:

- `data/ui/game/globalcomponents/globalcomponents.big`
- `FSW/ScoreBoard/globalcomponents/globalcomponents.big`
- `ScoreBoardGBD/XXX - EI Maxx CN/game/globalcomponents/globalcomponents.big`

O arquivo corresponde ao layout recebido do Robson: 41 imagens e a constante
de estilo `COLOR_TEXT_UNHIGHLIGHT` em vez de `COLOR_TEXT_HIGHLIGHT` no índice
1002. O recurso APT de scripts é idêntico ao da base anterior; imports,
exports, funções e callbacks são preservados. Os outros arquivos próprios
dos placares não foram substituídos. Os overlays de resultados em tempo real
e as DLLs dos mods não fazem parte desta alteração.

As três cópias pertencem à distribuição. Novos pacotes de placar que incluírem
outro globalcomponents.big precisam ser comparados antes da integração: não
se deve copiar uma versão antiga por cima do tema atual.

Regressão: `source/tests/test_scoreboard_theme_baseline.py` confere igualdade,
decodificação APT e executa as cópias reais do bootstrap/runtime em pasta
temporária, inclusive após três reaplicações de um placar atribuído.

Esta correção não altera o código nem o executável do Server16. O tema das
telas customizadas continua configurado em `data/custom_ui_theme.json`.
