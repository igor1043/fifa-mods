# Técnicos: cadastro e modelos SLC

O mercado usa o cadastro legível em
`ModCarrerMode/data/manager_market/manager_registry.ini`. Cada técnico tem um
ID estável, seus dados pessoais e, quando houver um modelo original disponível,
o `source_slc_club_id` que identifica o arquivo SLC do FIFA. Não há uma cópia
do modelo em uma pasta própria do mod.

## Campos que podem ser editados

- `name`, `nationality`, `birth_date` (`AAAA-MM-DD`) e `birthplace` descrevem o
  técnico. A idade é calculada para a data atual da carreira.
- `reputation`, `salary`, `style` e `image` definem os dados iniciais do perfil.
- `market_enabled` tira o técnico das novas contratações quando `false`.
- `default_club_id` define apenas o clube inicial ao criar uma carreira nova;
  `0` deixa o técnico sem vínculo inicial. O banco da carreira passa a controlar
  as nomeações depois disso.
- `source_slc_club_id` escolhe o modelo nativo usado como referência visual.
  `source_slc_club_name` e `default_club_name` são rótulos para facilitar a
  edição; os IDs numéricos são os valores usados pelo jogo.
- `model_enabled = false` deixa o perfil no mercado, mas usa o técnico genérico
  em cena.

Para cadastrar alguém, copie uma seção `[coach:COACH-...]`, dê a ela um ID novo
e preencha os campos. Para remover alguém de um cadastro novo, apague a seção
ou use `market_enabled = false`. Não reutilize um ID antigo: saves mantêm
histórico por identidade. Um registro novo só terá aparência 3D se o jogo já
tiver os arquivos SLC correspondentes; um INI não cria um modelo que não existe.

## Arquivos nativos usados

O modelo e as texturas permanecem na pasta original do FIFA:

```
data/sceneassets/slc/specificmanager_<source_slc_club_id>_0_0.rx3
data/sceneassets/slc/specificmanager_<source_slc_club_id>_0_0_textures.rx3
data/sceneassets/slc/specificmanager_<source_slc_club_id>_0_1.rx3
data/sceneassets/slc/specificmanager_<source_slc_club_id>_0_1_textures.rx3
```

O último número seleciona a variante climática. Esses arquivos não são
alterados pelo mod nem copiados para `data/sceneassets/manager_market`.
`prepare_model_assets.py` valida os arquivos originais e prepara somente o INI
para distribuição.

## Separação entre cadastro e carreira

Ao criar uma branch para um save novo, o serviço lê o INI e grava os perfis e
clubes iniciais no banco da carreira. Esse banco, separado dos arquivos DATA e
INDEX do FIFA, guarda contratos, movimentações, resultados, passagens e
checkpoints associados ao save.

Ao reabrir um save conhecido, o checkpoint é restaurado antes de qualquer
semeadura inicial. Portanto, alterações em `default_club_id` não recolocam um
técnico no clube antigo nem desfazem movimentações. Contratações e demissões
continuam a atualizar o banco da carreira, e o resolvedor seleciona o SLC pelo
ID do técnico que está ativo em cada clube naquele save/data.

Somente nomeações ativas da branch e da data confirmadas pelo evento de save
são publicadas para o jogo. O resolvedor nativo valida PID, contexto, data e
evento de leitura/escrita. Fora da carreira, a seleção fixa original por clube
continua sob controle do FIFA. O mod não escreve na tabela nativa `manager` nem
modifica os SLCs.
