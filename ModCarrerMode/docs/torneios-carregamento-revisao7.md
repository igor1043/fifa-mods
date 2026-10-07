# Reabertura de torneios adicionais: revisão 7

Atualização: a execução seguinte confirmou `61/61, 400 entries` e a criação
e gravação do torneio. A reabertura revelou outra falha, no ID persistido em
11 bits. O diagnóstico e a correção do banco estão em
`torneios-schema-revisao8.md`; a revisão 7 continua necessária para a lista.

Branch: `fifa-friends-v12-integracao-suico`. Base publicada: `c277b8f`.

## Falha capturada em 06/10/2026

Processo 12676. `crash.dmp` gerado às 18:08:36 do host. A exceção ocorre em
`exe+05B17AAE`: `movups xmm0, [rax]`, com RAX igual a zero. A pilha desenrolada
entra por `exe+05953030`, no fluxo de preparação/carregamento de torneio, e chama
`exe+05B17A40` com a competição 2235 (`0x8BB`). Esse objeto aparece na posição
136 da lista atual de 137 competições de `compids.txt` (índice 135).

A chamada anterior ao erro, `exe+05BB57C0`, busca esse ID em registros de 92
bytes, mas `exe+05BB57DC` ainda contém `cmp eax, 100`. A busca não encontra o
registro e retorna NULL. O chamador tenta copiar o registro sem verificar o
ponteiro. Isso identifica o mecanismo da exceção capturada; não implica que IDs
numéricos maiores que 100 sejam proibidos. O limite é da busca na lista.

## Por que a ampliação estava bloqueada

O worker L9-10 original só aplica o conjunto completo quando suas 61 assinaturas
estão prontas. A inspeção da tabela em `dinput8_l9_chain.dll+239A0` encontrou
59 assinaturas anteriores corretas, duas diferentes e nenhuma aplicada.

| Descritor | Imediato no EXE | Esperado pela L9 | Observado |
|---|---|---|---|
| 31, construtor | `05B383E0` | `3CB15E54` | `3CB1F554` |
| 32, limpeza | `05B5C4DE` | `3C6F5E55` | `3C6FF555` |

Esses imediatos são somados a sementes em instruções anteriores. Com as sementes
efetivamente observadas, os valores presentes decodificam para 99 e 100:

- `C34E0B0F + 3CB1F554 = 99`, módulo 2^32;
- `C3900B0F + 3C6FF555 = 100`, módulo 2^32.

As duas assinaturas incompatíveis bloqueavam também o restante do conjunto:
layout do objeto, inicialização, limpeza, contadores e buscas. Não foi identificado
o motivo original da diferença de codificação entre o EXE e a tabela da entrega.
Não se atribui a exceção ao banco, à configuração do alocador ou ao calendário.

## Alteração implementada

Novo adaptador C: `tournament_list_compat.c/.h`. Ele é iniciado pelo host após os
sinais de prontidão já usados na integração. Reconhece o executável suportado, a
L9 original, os dois descritores, os opcodes e as contagens decodificadas.

Somente os dados dos descritores 31 e 32 são adaptados à codificação encontrada:
os valores posteriores ficam 300 acima dos anteriores, produzindo 399 e 400.
Os dois valores posteriores são publicados antes dos anteriores, com barreira
de memória, preservando a condição de prontidão do worker original.

A própria L9 aplica o conjunto completo de 61 alterações. O adaptador não cria
um segundo patcher para esses endereços e não mascara o NULL com um registro
inventado. A expansão reúne as 400 entradas no layout já implementado pela L9,
incluindo seu trampoline de construção e buscas.

Após a aplicação, o adaptador compara todos os 61 locais com os descritores
posteriores e registra a confirmação, ou erro/assinatura indisponível.

Configuração acrescentada ao INI:

```ini
[TournamentListCompat]
Aktiv=1
```

Log no jogo: `ModCarrerMode/logs/tournament_list_compat.log`.
Confirmação esperada: `APPLIED original L9-10 complete: 61/61, 400 entries`.
O log original `dinput8_L9.log` deve também confirmar `L9-10 Turnierliste`.

## Escopo e conferência

Recompilação do host com a adaptação nova. A DLL preserva os recursos originais
101 (L9.65) e 102 (funções Swiss selecionadas), além da correção anterior de
consultas em lotes para os 96 clubes. A adaptação modifica dados da L9 carregada;
os bytes do recurso original embutido continuam iguais.

Não modifica banco, XML, compdata, calendário, winmm, memoryfw, saves ou física.
Compilação concluída; a instalação deve substituir somente DLL e INI.
Nenhum teste automatizado ou inicialização automática do FIFA foi executado.
A aplicação das 61 alterações e a reabertura do torneio precisam ser confirmadas
na nova execução do jogo. A revisão não comprova todos os 400 torneios nem o
funcionamento de toda uma temporada.

É necessário fechar a execução que já falhou e abrir novamente o jogo. O save
que o usuário deseja testar deve ser mantido; nenhum save foi apagado ou editado.
Na pasta de saves consultada (`Documents/FIFA 16/0/FIFA16`), a gravação mais
recente era das 16:36:52; não foi identificado nela um novo arquivo de torneio
gravado durante esta reprodução. A captura confirma o ID 2235 no fluxo que
falhou, sem provar por si só qual arquivo de save o usuário tentou carregar.

## Backup e evidências

Backup anterior à mudança:
`J:/mods/fifa 16/estudos fifa 16/backups/torneios-reabertura_20261006_181442`.
Inclui DLL/INI anteriores, fontes alterados e uma cópia dos saves existentes na
pasta consultada (27 arquivos DATA/INDEX/CONTAINERS, sem copiar o replay).

Captura da falha e diagnóstico:
`J:/mods/fifa 16/estudos fifa 16/07_TORNEIOS_SAVE_20261006/captura_20261006_180918`.
Contém dump, contexto, módulos, pilha com unwind, instruções e 61 descritores
comparados com o processo. Esses snapshots são do PID 12676, não fazem parte
do pacote publicado e não devem ser tratados como dados de uma nova execução.
