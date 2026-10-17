# Tiro de meta moderno

Este módulo adapta para o FIFA Friends os hooks do ZIP que pertencem ao tiro de meta: quatro rotinas de posicionamento/preparação e o solver de passes rasteiros. A formação do tiro de meta e os passes curtos do goleiro para os zagueiros próximos ficam em uma DLL separada da saída de bola v20.

O filtro de passe usa o cálculo de trajetória original e só reduz a velocidade de consulta quando confirma o reinício, a equipe, a formação, o par de zagueiros, o alvo, a distância e o tipo e a força do passe. A instalação exige as assinaturas exatas das rotinas de tiro de meta e confirma os cinco slots antes de publicar os hooks. Se os bytes ou qualquer slot divergirem, nada é instalado. Os hooks de saída de bola do ZIP não são publicados; a saída v20 continua independente. O mod não altera a regra que determina quando a bola passa a estar em jogo dentro da área.

## Configuração

`ModCarrerMode/mods/goal_kick_short_pass/goal_kick_short_pass.ini`:

```ini
[General]
Enabled=1

[GoalKick]
ShortPassSpeedPercent=75
```

O padrão `75` reduz em 25% a velocidade usada na consulta de trajetória. O intervalo aceito é de 50 a 100; `100` conserva a velocidade original e mantém o posicionamento. `Enabled=0` desliga o módulo inteiro. Reinicie o FIFA após alterar a configuração.

## Compilação

Execute `build.cmd` com MSVC x64 Build Tools. O build publica `goal_kick_short_pass.dll` ao lado da configuração em `ModCarrerMode/mods/goal_kick_short_pass/`.

## Compatibilidade e limites

O plugin exige o hash exato de `fifa16.exe` documentado no pacote original. Os testes registrados pelo autor usam APIs e chamadas do jogo simuladas; não comprovam o comportamento visual dentro de uma partida real. O log `ModCarrerMode/logs/goal_kick_short_pass.log` registra `APPLIED` quando os quatro hooks de posicionamento e o solver são instalados, além dos contadores `GOAL_SHORT_PASS` para passes elegíveis. A aparência da formação e a sensação do passe ainda precisam ser avaliadas em jogo.
