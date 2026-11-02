# Som de substituição por clube

Implementação no Server16, independente do módulo de cânticos. Arquivos em `FSW/Substitutions/<ID>.mp3`; Flamengo `1043.mp3`. A reprodução usa um alias MCI próprio e mistura a faixa com o som original. O áudio fornecido foi validado pelo decodificador do Windows (27,586 s), sem tocar nem converter o arquivo durante a validação.

## Detecção

Leitura externa com `PROCESS_QUERY_INFORMATION | PROCESS_VM_READ`. Resolve o mundo, o registro da partida, as duas equipes e os jogadores a cada sessão; valida vtables, proprietários, IDs, lados e estabilidade das referências. Não usa endereços de heap fixos, varredura contínua, escrita de RAM, detours ou alteração de regras/banco/save.

Compara os IDs ativos e a entrada de reservas. Duas amostras estáveis confirmam a transição. Mudança de posição dos mesmos jogadores, preparação cancelada nos menus, replay, nova partida e relógio reiniciado não devem disparar áudio. Várias entradas observadas no mesmo lote geram um evento; a faixa já em execução do mesmo clube não é reiniciada. Um mutex por instalação impede dois reprodutores do mod.

Configuração em `ModCarrerMode/config/substitution_audio.ini`; recarga automática. O worker usa uma conexão própria de leitura, libera-a ao encerrar e reencontra o FIFA quando ele é reaberto. Shutdown do Server16 encerra o áudio. Logs em `ModCarrerMode/logs/substitution_audio.log`.

## Validação e limite atual

- 13 testes: detecção e agrupamento, menus/cancelamento, replay, troca de partida, relógio, troca em amostras separadas, lados independentes, faixa ausente, pausa sem reiniciar, timeout, configuração.
- A leitura da partida aberta foi validada: Flamengo 1043 × Macaé 567, 46 jogadores, relógio 106, fase 14 e página StadiumPan.
- O jogo permaneceu parado nessa tela durante a observação. O usuário informou estar sem acesso ao computador. **O disparo em uma substituição real continua pendente de teste interativo.** Não foi criado um evento artificial no FIFA para simular essa validação.
- Novo executável validado por autoteste. Publicação preserva os offsets e bytes dos módulos antigos do PYZ, com teste dos 1.038 importadores em cache; o processo do Server16 já aberto conserva seus módulos e a próxima inicialização recebe a integração nova.
- Um acompanhante temporário com a mesma implementação fica ativo enquanto esta sessão antiga do Server16 existir, sem fechar nem controlar a tela do FIFA. Na próxima inicialização do Server16 o próprio aplicativo inicia o mod.

Sem commit nem push. Backup em `code-release/substitution-audio-20261031/before`.
