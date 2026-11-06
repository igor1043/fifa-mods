# Integração da DB: Emirados e Atlante

A base recebida acrescenta a UAE Pro League (liga 698, país 190), com 14 clubes,
e substitui o Mazatlán pelo Atlante (101116) na liga mexicana 341. O arquivo
original contém 14 registros novos de times e remove um registro anterior.

DB e LOC ficam versionados na branch `fifa-friends-v12`. Imagens, kits,
minifaces, caches, saves e bancos pessoais não fazem parte desse commit.

## Catálogos e compatibilidade

- O globo e o ranking continuam lendo os vínculos da DB. Um vínculo primário
  novo prevalece sobre as referências antigas do catálogo e os secundários.
- Clubes transferidos da associação ROW para uma liga nacional não reutilizam
  país, cidade ou coordenadas da identidade anterior.
- Catálogo publicado: 1.657 clubes e 83 seleções. O registro vazio
  `TIME EXTRA 2` não é apresentado como clube jogável.
- Dibba e Al Bataeh vieram com coordenadas 51/0. Os respectivos pontos no globo
  usam provisoriamente o centro do país; isso é uma referência aproximada.
- Metadados das tabelas mantidos. O LOC brasileiro acrescenta 57 strings e
  altera 14; as strings anteriores de interface foram preservadas.

## Correções na base recebida

A comparação de todos os elencos detectou 30 escalações que passaram a apontar
para jogadores de outros clubes depois das transferências desse pacote. Foram
reparados apenas esses registros de `default_teamsheets`: preservados os
titulares válidos, preenchidas as vagas por jogadores do próprio elenco e
recomposta a lista de reservas sem duplicatas. Os checksums foram recalculados
com FifaLibrary16. As demais tabelas permanecem idênticas às recebidas.

Os identificadores, hashes e clubes corrigidos constam de
`ModCarrerMode/data/catalogs/database_integration_20261106.json`.

## Conteúdo externo ainda necessário

O RAR recebido contém somente DB, LOC e uma pasta `ui/imgAssets` vazia.
Não contém os kits, minifaces, escudos novos nem CompData para criar a
competição 698 na simulação nativa. Esses arquivos precisam do complemento
do autor e devem ser instalados como assets locais, fora do Git.

A atualização da DB não injeta ligas, calendários ou elencos em saves antigos.
As carreiras existentes continuam usando seus próprios dados salvos.
