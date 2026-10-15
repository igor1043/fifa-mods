Tournament compatibility native - versao 4

Corrige o carregamento de torneios personalizados com IDs de competicao que
ultrapassam o campo compacto do save, e a leitura desse mesmo ID pelo card
nativo de classificacao ao reabrir o torneio.

A resolucao usa o catalogo compobj.txt, a mascara do campo primarycompobjid
no esquema instalado e as duas selecoes ativas do CompetitionManager.
Nao ha lista de excecoes por liga, clube ou ID de competicao. Casos ambiguos
ou selecoes divergentes preservam a leitura original.

O ajuste do card atua na consulta de identidade anterior a CM_STANDINGS_DP.
Nao altera a classificacao, o registro do usuario, o banco ou o arquivo de save.
O provedor original continua montando a tabela e a pagina de artilheiros.

Ativacao: tournament_compat_native\tournament_compat_native.dll em enabled.txt.
Reinicie o FIFA para carregar uma DLL atualizada.
Log: ModCarrerMode\logs\tournament_compat_native.log.
Fonte e testes: ModCarrerMode\source\tournament_compat_native.
