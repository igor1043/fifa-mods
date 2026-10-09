# Mascote na linha de fundo

Este componente parte da colocação v12 que já foi validada no jogo e acrescenta animação nativa de torcida ao mascote.

- O novo ponto de teste fica junto à bandeirinha, mais recuado e um pouco mais para o centro do gol, para tentar passar a fileira de placas. Coordenadas-base: X=±5850 cm e Z=3150 cm; em relação ao ponto anterior, recua cerca de 4,4 m e avança 0,8 m. A posição atrás das placas precisa de confirmação visual no jogo.
- Suporte de pacote: Flamengo (1043) e Palmeiras (383).
- Idle usa o comportamento em pé 26; gol do mandante usa comemoração 14 por 26 segundos. Gol do visitante e reação de tristeza ficam desativados.
- A malha animada substitui somente o modelo do mascote; as texturas do clube continuam as originais.
- O código verifica os pacotes antes de usá-los. Sem pacote de animação, tenta o modelo estático; sem pacote de mascote válido, mantém o fotógrafo normal.
- O build gera e copia mascot_goal_line_v13.dll para ModCarrerMode/mods/mascot_single.

Para compilar, execute build_mascot_single_v13.cmd nesta pasta. A instalação no jogo é feita separadamente por Install-MascotPhotographer.ps1; a restauração usa Restore-MascotPhotographer.ps1.

## Revisão de desempenho — 09/10/2026

A revisão `performance_revision=1` remove a segunda descoberta do time/estádio e a segunda varredura de fotógrafos feitas pela animação a cada quadro. A animação usa os dados já validados pelo posicionamento no mesmo callback. A identidade continua sendo conferida a cada 250 ms, e as poses nativas continuam atualizadas a cada quadro.

Cada consulta Lua também reutiliza as regiões de memória validadas dentro daquela consulta. O cache termina ao sair da função; não guarda ponteiros Lua entre quadros nem compartilha dados entre threads. As leituras mantêm a proteção SEH. Falhas de inicialização da animação têm intervalo mínimo de 250 ms, e o callback da torcida passa diretamente ao jogo quando não há mascote ativo. Mudanças de recursos/time invalidam o estado da animação.

`tests\run_performance.cmd` compila o código real com contagem de VirtualQuery e executa verificações de memória inválida, atribuição única, fotógrafo normal sem mascote, posição e tentativas de inicialização. Na tabela sintética de 1.024 nós, a consulta original fez 4.099 VirtualQuery; a revisada fez uma. Uma execução registrou 1.790,9 µs contra 18,9 µs por consulta. Esses números medem a consulta artificial, não FPS nem tempo total da partida.

A DLL foi aplicada em `U:\fifa 16` e no projeto `FIFA Friends V12`, com o jogo fechado. Cópias anteriores, resultados e hashes estão em `estudos fifa 16\14_MASCOTE_PERFORMANCE_20261009`. Não foi possível medir FPS em partida nesta revisão. Para confirmar o resultado no jogo, compare a mesma partida, câmera e opções gráficas antes/depois. A posição, troca de lado e comemoração de 26 segundos não foram alteradas.

## Reações da torcida durante a partida

O mascote agora acompanha poses nativas em pé do agente de torcida que o mod já usa como fonte. Posturas sentadas ou não verticais são rejeitadas; nessas situações, o mascote conserva a última pose válida em pé. Isso deixa o jogo conduzir gestos contextuais da torcida, inclusive a reação a uma finalização desperdiçada quando o motor de crowd emitir essa animação. A comemoração própria do time do mascote continua usando o comportamento 14 por 26 segundos; fora dela, o mod não força o comportamento de repouso 26. O espelhamento reutiliza a leitura de pose existente por quadro e registra mudança de comportamento/clip para diagnóstico. A validação de jogo real ainda é necessária para confirmar qual gesto de decepção o FIFA 16 produz nesse lance.
