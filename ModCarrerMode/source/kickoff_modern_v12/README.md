# Saída moderna v12 — orientação durante a espera

Correção de 11/10/2026 após análise pela RAM da saída deixada aberta pelo usuário.

A v10 carregada corrigia a orientação na colocação, mas o comando nativo de espera fazia o cobrador olhar novamente para a bola. Na captura, a orientação era 2,072107 radianos: exatamente o ângulo da posição do cobrador `(0,889977; 1,624037)` para a bola na marca central. O receptor estava no próprio campo, em `(36,088799; -13,123200)`.

A v12 mantém a redução de 25% da carga do primeiro passe da v11 e intercepta também o CALL `fifa16.exe+0x51CDD83`, exclusivo do ramo de espera do cobrador na formação de saída. Para o cobrador identificado pela saída atual, antes da preparação do passe, substitui o comando de ficar parado olhando para a bola por um comando nativo de navegação com posição atual e orientação explícita para a defesa. O alvo de posição permanece igual ao do atleta; o comando pede apenas o giro. O ângulo usa o codificador nativo `+0x51006B0` e o mesmo formato de comando gerado pelo jogo em `+0x51CE259`.

As guardas exigem saída ativa, identidade do cobrador, receptor titular da mesma equipe, alvo recuado já estabelecido e pose central válida. A preparação do passe encerra a adaptação de espera. Demais jogadores e comandos de jogo corrido seguem os métodos originais.

O export `Fifa16ModAdoptKickoff` permite adotar a saída já aberta durante atualização pela RAM. Confere a assignment, atletas, posição recuada e seis amostras angulares observadas do cobrador. Sincroniza apenas essas amostras de orientação; posição e velocidade permanecem iguais. Isso não depende de controle da interface nem de Frida.

O plugin altera cinco CALLs e duas entradas virtuais com guardas em RAM. O FIFA em disco permanece intacto. Compilação C11 `/W4 /WX` e testes de geometria/carga passaram. A verificação da sessão aberta compara antes/depois dos campos angulares e das posições; a animação visível deve ser conferida pelo usuário ao voltar para a partida.

Carregamento: `kickoff_modern_v12/kickoff_modern_v12.dll` em `ModCarrerMode/mods/enabled.txt`. Log: `logs/kickoff_modern_v12.log`. Use apenas uma versão de kickoff. As versões anteriores e os enabled.txt anteriores ficam preservados em `J:/mods/fifa 16/estudos fifa 16/25_KICKOFF_TUNING_20261011/`.
