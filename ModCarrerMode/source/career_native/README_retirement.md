# Mod de aposentadoria

O motor acompanha o `DATA` que o FIFA acabou de salvar. Quando a operação é
solicitada, ele espera o autosave e o par `DATA`/`INDEX` ficarem estáveis e
liberados pelo FIFA, cria backups dos dois arquivos e troca somente o `DATA`
por uma cópia corrigida. Arquivos auxiliares menores que 1 MB são ignorados;
somente o banco de carreira é processado.

Antes da troca são verificados o CRC externo do container e a tabela `CZUM`.
Depois da troca o worker relê o arquivo e valida novamente o CRC e a estrutura;
se a validação falhar, o backup do `DATA` é restaurado automaticamente.

Modos aceitos:

- `remove_retirement`: limpa `isretiring` sem mexer na idade.
- `remove_and_rejuvenate`: limpa `isretiring` e ajusta a idade para
  `target_age`, mantendo mês e dia de nascimento.

O executável instalado é `ModCarrerMode/retirement_offline_worker.exe`. A DLL
principal é `dinput8.dll` na raiz do jogo; não deve existir outra cópia com
esse nome dentro de `ModCarrerMode`. O worker externo aplica a alteração somente
depois que o FIFA libera o save, sem forçar o desbloqueio enquanto a carreira
está aberta.

Na tela do Career Hub, o primeiro card entra no fluxo exclusivo
`retirementremoveflow.nav` e cria uma solicitação `remove_retirement`; o
segundo entra em `retirementresetageflow.nav` e cria
`remove_and_rejuvenate`. A DLL só arma a solicitação quando o FIFA abre um
desses dois arquivos NAV exclusivos. Portanto, abrir o save, entrar em
negociações, abrir outro card ou executar um autosave comum não arma a
operação. Cada fluxo carrega `CareerAutosaveViewModel` e chama `DoAutoSave`
uma única vez. A solicitação é consumida pela primeira gravação válida desse
autosave; novas aberturas do mesmo fluxo são ignoradas até o retorno ao
`mainmenuhubflow.nav`, quando um novo clique pode armar a ação novamente. O
worker não varre nem altera saves sem uma solicitação pendente.

O primeiro sinal ocorre no clique, confirmando que a solicitação foi preparada
e que o usuário pode sair do save. O segundo sinal só ocorre depois de o worker
concluir e validar o save com sucesso; nesse momento a DLL mostra o aviso não
bloqueante e o worker emite o beep de conclusão. Em caso de erro não há aviso
de sucesso. Diagnósticos com tempo
(`elapsed_ms`) só são gravados quando existe, na instalação local,
`ModCarrerMode/career_retirement_background.local.ini` com `logging=1`. Esse
arquivo é ignorado pelo Git e não faz parte do pacote distribuído.

Os testes nativos podem ser recompilados com `build_retirement_engine_test.cmd`
e `build_retirement_offline_worker.cmd`. A DLL completa é recompilada com
`build_active_chain_crashfix.cmd`.
