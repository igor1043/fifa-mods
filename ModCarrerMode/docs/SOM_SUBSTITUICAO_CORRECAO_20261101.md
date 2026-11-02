# Som de substituição — revisão validada em partida

## Correção

A primeira versão descartava a fase nativa 0 e classificava qualquer página
StadiumPan como pausa. A sequência real de substituição usa essa fase; o reset
apagava a comparação de jogadores antes do disparo.

A revisão mantém o elenco confirmado durante fases transitórias e lê, sem
modificar a memória, o grafo selecionado pelo MUSE. As sequências nativas
`package_sub_oop`, `package_sub_1_player` e `package_sub_interact` foram observadas
na partida. A família `package_sub_` permite confirmar a substituição mesmo na
fase 0. A página StadiumPan deixa de bloquear essa cena. Menus explícitos de
escalação, replay e saída da partida continuam protegidos.

## Validação

- 20 testes automatizados passaram, incluindo o cenário nativo observado,
  preservação do elenco entre fases, replay e menu de escalação.
- Autoteste do executável congelado passou.
- Reprodução isolada de cinco segundos confirmada pelo usuário.
- Na substituição seguinte do Flamengo, o registro detectou a entrada do jogador
  199304, saída do 240699, e acionou `FSW/Substitutions/1043.mp3` uma única vez.
- O usuário confirmou que funcionou e encerrou o escopo desta revisão.

## Instalação

Código e novo Server16 instalados no jogo e no desenvolvimento. O MP3 permanece
em `FSW/Substitutions/1043.mp3`; volume padrão 35%, som original preservado.

Para testar sem fechar o FIFA, esta sessão usa um worker temporário da mesma
implementação corrigida. Ele desativa apenas o worker antigo, mantém uma cópia
ativa da configuração e restaura a configuração normal ao encerrar a sessão
antiga do Server16. A próxima inicialização usa a integração corrigida do próprio
executável. O mutex evita duas reproduções concorrentes da revisão.

Backup anterior à correção em
`code-release/substitution-audio-fix-20261101/before`. O executável em uso da sessão
antiga foi preservado também no backup do jogo. Sem mudanças em save, banco,
regras de substituição ou áudio nativo. Sem commit nem push.
