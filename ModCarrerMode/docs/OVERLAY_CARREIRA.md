# Overlay do modo carreira

Abra no hub da carreira com **Select + Start** ou **F12**. Este é um painel próprio;
os painéis de partida e pré-jogo continuam disponíveis nos seus contextos.

A Central usa internamente `game/screens/fluxHub/FluxHub`, o mesmo identificador
do menu principal e da pausa. Nessa página o gatilho exige leitura válida do
serviço nativo de carreira, usuário/clube ativo e sinal de partida desligado.
As leituras usam os acessores do perfil compatível, verificados antes de seguir
os ponteiros; layout desconhecido ou leitura incompleta não habilita a overlay.
Torneios identificados e pausa de partida continuam separados. A saída para o
menu principal também exige confirmação do fim do contexto antes de gravar.

A ponte nativa reconecta o canal se o Server for reaberto. Uma versão diferente
da DLL já carregada exige reiniciar o FIFA; o Server não instala outro gancho
de renderização sobre a versão antiga.

1. Salve o progresso no FIFA antes de confirmar um pedido.
2. Abra a overlay. A carreira em execução é identificada automaticamente.
3. Escolha **Transferir para outro clube** ou **Finanças > Solicitar verba**.
   País, liga e time aparecem um abaixo do outro, cada um com ícone e nome.
   Use as setas de cada linha ou esquerda/direita no controle para trocar.
4. Revise e confirme. A confirmação começa com **Voltar** selecionado.
5. Feche o painel, saia da carreira **sem salvar novamente** e aguarde no menu
   principal até aparecer **Aplicado com backup**. Carregue o mesmo slot.

O pedido também pode ser cancelado antes da aplicação. Se salvar novamente após
confirmar, o Server recusa sobrescrever esse progresso; cancele o pedido e aguarde
a atualização automática antes de refazê-lo. Durante a preparação, aguarde no menu principal.

Não existe seleção manual de save neste painel. A ponte nativa registra o arquivo
`DATA` que o FIFA leu por completo ao carregar a carreira ou gravou ao salvar.
Prévias da lista de saves e Configurações Pessoais não substituem esse registro.
O Server confere PID, criação do processo, tipo do arquivo e usuário/clube da RAM.
Não escolhe o arquivo mais recente. Ao trocar de carreira ou salvar em outro slot,
a leitura é atualizada e uma confirmação antiga exige nova revisão.

As telas abrem mesmo durante a identificação. A confirmação só fica disponível
depois da leitura da carreira. Caso apareça “Aguardando a carreira em execução”,
salve o progresso ou reabra a carreira após carregar os módulos atualizados.

## Clubes e finanças

Os países/regiões vêm da tabela `nations` instalada. Ligas, divisões, clubes e seus
vínculos são lidos da **carreira em execução**, acompanhando promoções e rebaixamentos.
As regiões adicionais do patch aparecem com os nomes existentes na base. Não há
lista fixa de clubes nem inferência de estados a partir dos nomes dos times.
O escudo usa os recursos já disponíveis ao Server.

A troca funciona para treinador e jogador. Na carreira de jogador, atualiza o
vínculo do elenco, camisa sem conflito, contratos existentes, clube anterior e
escalações salvas. Mantém o vínculo da seleção nacional. Empréstimos ativos,
elencos cheios e layouts incompatíveis são recusados com a razão no painel.
Na carreira de treinador, usa o orçamento de transferências do clube de destino.

A solicitação de verba está disponível na carreira de **treinador** e adiciona
o valor ao orçamento de transferências atual, na unidade monetária do save.
É possível digitar pelo teclado ou pelo teclado numérico da overlay com o controle.
Pedidos válidos são aceitos; o orçamento resultante é limitado a 2 bilhões.
Não foi encontrada no Python Port uma implementação anterior de probabilidade de
aceitação dos cards. Esta versão não inventa uma probabilidade ou limite por temporada.

## Integridade e arquivos

Suporta o contêiner FIFA 16 de carreira `DATA` + `INDEX` com três bancos DB v8.
Formatos diferentes são recusados. Não grava campos de carreira na memória do jogo.
Utiliza a página que o Server lê na RAM para distinguir carreira, partida e saída.
Página vazia ou desconhecida não autoriza aplicação enquanto o jogo está conectado.

O trabalho x86 é isolado em `career_save_worker.py` com a `FifaLibrary16.dll`
existente. Cada campo inteiro passa por validação do layout e do valor original;
a edição preserva os tamanhos dos blocos e recalcula os CRCs dos bancos e do DATA.
O resultado é reaberto e conferido antes de publicar. O INDEX permanece idêntico.
A publicação exige o fingerprint confirmado e bloqueio exclusivo do arquivo no Windows.
Falha na gravação tenta restaurar o conteúdo anterior pelo mesmo handle.

Pedidos e recibos: `runtime/career_overlay/`. Backups com DATA e INDEX originais:
`runtime/career_overlay/backups/<slot>_<dataUTC>/`. Para restaurar um backup,
feche o FIFA e copie os dois arquivos para o slot registrado em `receipt.json`.

## Validação e build

```powershell
python -m unittest discover -s tests -p test_career_overlay.py
cmd /c scripts\build_career_overlay.cmd
python tools/validate_career_overlay.py --game 'U:\fifa 16' --save '<snapshot>\DATA' --output '<nova-pasta>'
python tools/validate_career_overlay.py --player-only --game 'U:\fifa 16' --save '<carreira-jogador>\DATA' --output '<nova-pasta>'
```

Os verificadores offline geram cópias e conferem que o original permaneceu intacto.
O teste de jogador sintético deriva uma carreira de jogador de um snapshot de treinador;
`--player-only` também verifica uma cópia de uma carreira de jogador real.
Eles não confirmam a experiência de recarregar o resultado dentro do FIFA.

O build completo usual inclui o worker na distribuição pelo `Server16Python.spec`.
Reinicie FIFA e Server ao trocar a versão, pois o atalho de carreira usa o novo modo 3
da ponte nativa. Não execute duas instâncias do Server ao mesmo tempo.
