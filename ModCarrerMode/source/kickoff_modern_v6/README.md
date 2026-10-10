# Saída moderna — versão 6

Mantém a posição diagonal do receptor titular, sua orientação para a marca central e o destino correspondente do primeiro passe. Atua na navegação, no posicionamento físico nativo e na preparação desse passe. Exclui reservas (papel AI 28), árbitros e jogadores de outra equipe do receptor.

A versão 5 foi validada visualmente na sessão de teste, inclusive pulando cenas, mas o carregamento após reiniciar encontrou chamadas ainda não preparadas e desistiu. A versão 6 espera até 120 segundos pelas três chamadas e pela entrada física esperadas; exige três verificações consecutivas antes de instalar. Se existir conflito persistente, registra a recusa e mantém o código existente.

A troca da entrada física da vtable usa compare/exchange. A desativação restaura somente chamadas que ainda contêm o patch desta versão. O plugin não edita o executável em disco e não depende de Frida. Carregamento: kickoff_modern_v6/kickoff_modern_v6.dll em mods/enabled.txt. Log: logs/kickoff_modern_v6.log.

Compilação MSVC C11 /W4 /WX concluída. A abertura conjunta com banco v8, segundo tempo, saída após gol e ambos os lados ainda precisam de confirmação no jogo.

Executável analisado SHA256: 889772d3192c74ce4c1f2b7b3467cc96f9f1123aaf347bce7b199333dbac7a9d. DLL v6 SHA256: 9CEB8624E6BDEB01E918FB202E5071B472A8DEEB04D53FEB98115A290A4FA68D.
