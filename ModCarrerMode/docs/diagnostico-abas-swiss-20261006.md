# Diagnóstico da regressão do menu da carreira

Branch: `fifa-friends-v12-integracao-suico`. Base V12: `4693010`.

## Estado

O usuário relatou somente CENTRAL, MEU TIME e COMPETIÇÃO, com navegação
incorreta. A integração **ainda não está validada como funcional**. A compilação
e a comparação de arquivos da revisão de 05/10 não demonstraram funcionamento
do menu no jogo.

Em 06/10 foi aplicada uma correção no rastreamento do save e acrescentado
diagnóstico de abertura dos três arquivos do menu. As funções Swiss continuam
ativas. Esta alteração ainda exige observar uma nova execução da carreira;
não existe confirmação de que ela resolva o desaparecimento das abas.

## Evidências

- O layout externo instalado é o da V12 e declara oito painéis, com sete abas
  visíveis: CENTRAL, ELENCO, MEU TIME, COMPETIÇÃO, TRANSFERÊNCIAS, ESCRITÓRIO
  e TEMPORADA. O painel 6 de competições de clube é uma página interna.
- `careerhubwidget.big` e `mainmenuhubflow.nav` instalados são iguais aos da
  branch V12. A localização contém os textos das sete abas.
- A última execução anterior à correção instalou os 19 hooks de chamadas e os
  cinco patches de bytes da V12, além das rotinas Swiss habilitadas.
- Encontrado em `career_active_save.tsv`, PID 44176, um caminho de textura
  `data/ui/imgAssets/training/tilestateicons/train_description_inactive.dds`.
  Um arquivo DDS não pode ser publicado como o save DATA da carreira.

## Correção aplicada ao host original

Em `active_save_probe.inc`, o resolvedor deixava o caminho de um arquivo comum
preenchido mesmo ao retornar FALSE. Os chamadores ignoravam esse retorno e
consideravam a existência de texto como indicação de save. Agora:

- Um caminho rejeitado é esvaziado.
- Um HANDLE rastreado é revalidado antes de publicar seu caminho, para impedir
  que a reutilização de um HANDLE fechado produza um falso save.
- A publicação exige explicitamente o formato `FIFA16/<slot hexadecimal>/DATA`.
- Os wrappers de CreateFileA/W, ReadFile e WriteFile preservam o GetLastError
  da chamada original. O observador não deve alterar esse resultado para FIFA.
- A abertura de `careermanagerhubcfg.xml`, `careerhubwidget.big` e
  `mainmenuhubflow.nav` é registrada como `career_ui_open` em `career_loader.log`.
- O log do adaptador Swiss identifica data, hora e PID para distinguir execuções.

O marcador inválido foi arquivado como
`U:\fifa 16\ModCarrerMode\logs\career_active_save_rejected_20261006_143128.tsv`.
Nenhum save DATA foi editado por esta correção.

## Banco novo preservado

O banco solicitado pelo usuário continua instalado em `U:\fifa 16\data\db`:

- Atual: 7.591.404 bytes, SHA-256
  `b87c98cc201e5f0d2e29941c3dc63fa301bb3572e09d4de2009507f20239f44d`.
- Backup fornecido: 7.861.348 bytes, SHA-256
  `2a3f3a0d1b2af693bba549c96c0b788cd1e9ab22d850dd319c6f64a1994ab9a6`.

Ambos têm 137 tabelas e checksums válidos. Os descritores binários dos campos
permanecem iguais. No XML, a única diferença é rangehigh de facialhairtypecode,
de 19 para 31. O banco novo modifica dados de jogadores, nomes, vínculos e ligas;
as ligas 352, 355 e 356 foram removidas junto dos respectivos boardoutcomes.
Não foram encontrados vínculos de liga/time ou nomes de jogadores apontando
para IDs ausentes nesses conjuntos. Isso não constitui validação de todos os
dados de carreira nem exclui conflito com um save existente.

## Backup e aplicação

Backup anterior a esta alteração:
`J:\mods\fifa 16\estudos fifa 16\backups\diagnostico-abas-swiss-20261006_143128`.
Contém DLL anterior, fontes alterados, banco atual, configuração e marcador
inválido, com manifesto de hashes. `after-install.json` registra a aplicação.

DLL compilada e instalada: 585.216 bytes, SHA-256
`a6a0bc76c37a616e6e810a89918c5bd53a2f5591dc48b7d0a73391b1c17a60fb`.
Recompilação concluída. Não houve commit/push desta correção.

O próximo passo é observar a execução da carreira com essa DLL, conferir os
registros da abertura do menu e localizar o conflito restante. Desativar as
funções Swiss permanentemente não atende ao pedido de integração.
