# Mod de aposentadoria

O motor acompanha o `DATA` que o FIFA acabou de salvar. Quando a operação é
solicitada, ele espera o autosave e o par `DATA`/`INDEX` ficarem estáveis,
aguarda o FIFA encerrar, cria backups dos dois arquivos e troca somente o
`DATA` por uma cópia corrigida.

Antes da troca são verificados o CRC externo do container e a tabela `CZUM`.
Depois da troca o worker relê o arquivo e valida novamente o CRC e a estrutura;
se a validação falhar, o backup do `DATA` é restaurado automaticamente.

Modos aceitos:

- `remove_retirement`: limpa `isretiring` sem mexer na idade.
- `remove_and_rejuvenate`: limpa `isretiring` e ajusta a idade para
  `target_age`, mantendo mês e dia de nascimento.

O executável instalado é `ModCarrerMode/retirement_offline_worker.exe`. A DLL
principal apenas observa o I/O do FIFA; ela não altera o buffer interno do
autosave. Isso evita que o estado em memória do jogo fique diferente do DATA
que será carregado na próxima entrada.

Na tela do Career Hub, o primeiro card cria uma solicitação
`remove_retirement` e o segundo cria `remove_and_rejuvenate`. A solicitação é
de uma única execução e só é consumida quando o autosave daquele clique é
detectado. O worker não altera saves de outros autosaves sem uma solicitação
pendente.

Os testes nativos podem ser recompilados com `build_retirement_engine_test.cmd`
e `build_retirement_offline_worker.cmd`. A DLL completa é recompilada com
`build_active_chain_crashfix.cmd`.
