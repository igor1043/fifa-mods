# Persistência dos IDs de competição: revisão 8

Branch: `fifa-friends-v12-integracao-suico`. Alteração instalada no Dev e no
jogo em 06/10/2026 às 18:46, após a reprodução com a DLL da revisão 7.
Em 07/10/2026, o usuário relatou "acho que corrigiu" e autorizou o commit e
push. Esse relato indica melhora no uso; não houve confirmação detalhada de
todos os torneios ou de carreiras antigas.

## Evidência da nova falha

A execução 38792 confirmou nos logs a aplicação das 61 alterações originais
L9-10, ampliando a lista para 400 entradas. O torneio foi criado e gravado.
Ao carregar `Tournament20261006183001`, o dump das 18:30:58 aponta escrita em
NULL em `FootballCompEngzf.dll+884F0`. A pilha passa pelo carregamento do motor
de competições e seu setter tenta escrever em um objeto não encontrado.

No primeiro banco T3DB embutido no save (offset 160), `career_users` tem uma
linha e `primarycompobjid=187`. O objeto escolhido na captura anterior é 2235.
O campo do banco está definido com 11 bits e limite XML de 2000.
`2235 & 2047 = 187`: o ID escolhido perdeu seus bits excedentes na gravação.
Na ocorrência atual, o pacote de carregamento também contém 187. A expansão
do número de entradas não amplia, por si só, os campos persistidos no banco.

A referência a “100” relaciona-se ao antigo tamanho da lista. Não significa
que qualquer ID numérico acima de 100 falhe. A segunda falha está relacionada
ao limite de representação de 11 bits, não à quantidade de clubes na Série D.

## Correção restrita ao banco e XML

Converter os seguintes campos de 11 para 13 bits, conforme o esquema entregue
pelo Swiss, preservando `rangelow`:

| Tabela | Campo | Novo intervalo |
|---|---|---|
| career_users | primarycompobjid | 0..8191 |
| career_competitionprogress | compobjid | 0..8191 |
| career_competitionprogress | stageid | -1..8190 |
| career_managerawards | compobjid | 0..8191 |
| career_newsban | compobjid | 0..8191 |
| career_playerawards | compobjid | 0..8191 |
| persistent_events | compobjid | -1..8190 |

Arquivos de execução: `data/db/fifa_ng_db.db` e `data/db/fifa_ng_db-meta.xml`.
Banco e metadados devem sempre ser instalados juntos.

Conversor existente: `ModCarrerMode/tools/swiss_integration/fifa_db_l9schema.py`.
Invocação usada sobre o banco atual da Série D corrigida, com saída em uma pasta
separada de preparação:

```text
python fifa_db_l9schema.py fifa_ng_db.db fifa_ng_db-meta.xml PASTA_SAIDA --ohne-formationen4096 --nur "(compobjid|stageid)$"
```

A auditoria confirmou exatamente os sete campos acima. Não se aplicou o
restante do esquema Swiss nem a remoção de formações. O gerador anterior
`repair_serie_d_96.py` produz a revisão anterior do banco: se esse banco for
regenerado, esta conversão restrita deve ser aplicada em seguida. O manifesto
histórico da Série D continua documentando a sua própria revisão.

## Conferências antes da instalação

- Checksums internos válidos no banco anterior e convertido.
- Valores de todos os campos das 137 tabelas preservados, incluindo bytes de
  campos de texto. Os sete campos modificados pertencem a seis tabelas vazias
  no banco base; os valores serão preenchidos em novos saves.
- 131 tabelas restantes também preservadas em representação binária, exceto
  checksums de encadeamento.
- XML: somente `depth` e `rangehigh` dos sete campos foram alterados.
- Tamanhos iguais aos anteriores: banco 7.591.404 bytes; XML 408.767 bytes.
- Nenhuma nova alteração de DLL, INI, calendário, compdata, clubes ou elencos.

Hashes e auditoria completa: `torneios-schema-revisao8.json`.
Essas conferências não comprovam, sozinhas, a reabertura no jogo.

Instalação restrita a dois arquivos, total de 8.000.171 bytes (8,00 MB,
7,63 MiB). Cópias verificadas por SHA256. A DLL, o INI e todos os TXT de
compdata presentes no jogo foram conferidos antes e depois e permaneceram
iguais. Recibo: `application-receipt.json` no backup desta revisão.

## Saves e validação necessária

O save que já gravou 187 continua contendo esse ID truncado; ampliar o esquema
do banco não recupera automaticamente o ID original. Criar um novo torneio,
salvar, sair e carregá-lo novamente para confirmar a correção. Nenhum save foi
apagado ou modificado. Não se afirma compatibilidade de todos os saves antigos
com o esquema ampliado; a leitura de carreiras existentes deve ser conferida.

Backups do banco, XML e saves consultados:
`J:/mods/fifa 16/estudos fifa 16/backups/torneios-schema_20261006_183828`.
`Restaurar-banco-anterior.cmd` restaura os dois arquivos no jogo e no Dev,
exige FIFA fechado e a branch de integração, e preserva uma cópia antes de
restaurar. O script não restaura saves nem altera as branches V12 e V12-backup.

Captura desta falha:
`J:/mods/fifa 16/estudos fifa 16/07_TORNEIOS_SAVE_20261006/captura_20261006_183229`.
