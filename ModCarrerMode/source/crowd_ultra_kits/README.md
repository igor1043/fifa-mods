# Crowd Ultra Kits v4 — DLL experimental independente

Converte os registros visíveis da torcida em modelos ultra nativos, usando as malhas e materiais separados de corpo/camisa já registrados pelo FIFA 16. A configuração inicial substitui 96% dos registros visíveis; os outros 4% mantêm seus modelos originais. Entre os registros substituídos, a seleção tem como alvo kit 1 = 88%, kit 2 = 8%, kit 3 = 3%, goleiro = 1%. Mandante e visitante mantêm seus próprios clubes. A regra se aplica somente a clubes brasileiros: cada lado é verificado separadamente, inclusive em partidas internacionais. Torcedores de clubes estrangeiros usam modelos, seletor de camisas e tamanho de protótipos originais.

Os índices de uniforme do FIFA são 0, 1 e **3**. O índice 2 é uniforme de goleiro. Se o kit secundário ou terceiro solicitado não existir, o resolver tem o primeiro uniforme como alternativa. Os percentuais representam solicitações de textura: um clube sem terceiro kit terá parte dessa parcela exibida com o primeiro uniforme.

## Implementação

- DLL própria, API `Fifa16ModGetApiVersion=1`, carregada pelo host existente.
- Intercepta as quatro chamadas de torcida: criação de assets Crowd3D (`4397c47`), criação dos buffers de instâncias (`5cb9f03`), lote de camisas (`5cbc0a2`) e desenho das instâncias (`5cbc483`). A versão 4 também intercepta a resolução dos assets (`5cbd1c8`), o registro do serviço de dados (`58e2ea4`) e o resolvedor de nomes de equipes (`5b8e430`) para obter o banco do modo atual. Todas as entradas têm validação de bytes. Sem substituir outras DLLs.
- Cada registro de 23 bytes recebe somente a alteração de categoria/modelo: bit 19 e bits 20–21 da palavra no offset 12. O estado de assento, afiliação, posição, animação e demais bytes são preservados. Estado 2 é vazio e não recebe alteração.
- Conversão acontece antes da alocação nativa dos buffers por modelo. Promover personagens depois da alocação poderia ultrapassar seus buffers.
- Com a configuração atual, a categoria secundária recebe 12% das instâncias; o desenho de suas camisas é dividido em 8/12 kit 2, 3/12 kit 3 e 1/12 goleiro. Usa o início da instância que a rotina nativa já recebe. O corpo mantém uma única passagem. A textura original é restaurada após o desenho do terceiro kit.
- O recurso Lua é incorporado à DLL. Adiciona quatro bibliotecas de textura para o terceiro kit e a camisa de goleiro e usa os modelos ultra já existentes, com seus LODs. As texturas são carregadas no bind; as consultas no desenho usam o catálogo nativo em memória.
- `homecrowdsize=6/awaycrowdsize=2` mantém disponíveis os quatro protótipos ultra. A DLL preserva os estados de assentos vazios e não escreve no multiplicador de público do mod de ocupação.
- A seleção dos grupos é determinística e os percentuais podem variar ligeiramente por arredondamento dos lotes/LODs e pela câmera. Ela não constitui contagem de pessoas visíveis em uma captura.
- Os sete hooks são instalados juntos com as outras threads suspensas, validação de bytes e de endereços das chamadas. DLL fixada na sessão; desativar exige reiniciar o FIFA.

## Compilar e instalar

Execute `build.cmd` nesta pasta. `verify.cmd` verifica a preservação dos bits de assento/afiliação, repetibilidade da distribuição, desativação da conversão e divisão do terceiro uniforme.

Copie `build/crowd_ultra_kits.dll` e `crowd_ultra_kits.ini` para `ModCarrerMode/mods/crowd_ultra_kits/`. Adicione uma única linha a `ModCarrerMode/mods/enabled.txt`:

```
crowd_ultra_kits\crowd_ultra_kits.dll
```

Não substituir `crowd/crowd_plugin.dll`: esse plugin trata da ocupação e continua separado.

## Configuração e teste visual

Edite `ModCarrerMode/mods/crowd_ultra_kits/crowd_ultra_kits.ini` com o jogo fechado. `kit1_percent + kit2_percent + kit3_percent + goalkeeper_percent` deve somar 100. `replace_percent` controla quantos registros visíveis recebem a conversão. Configuração inválida usa os padrões 96/88/8/3/1.

Abra uma partida nova, de preferência com clubes que possuam três uniformes. Observe a arquibancada nas câmeras próximas e no replay. O teste visual precisa confirmar as camisas completas, ambos os clubes, posições sentadas/em pé, animações e LODs. Essa confirmação visual não é substituída pela compilação nem pela leitura dos registros.

O log `ModCarrerMode/logs/crowd_ultra_kits.log` distingue: `installed version=4`, `country_db`, `country_scope`, `crowd_asset_bind`, `instances_remapped` e `kit_variation_draw`. `country_db` informa a fonte do cadastro e quantos clubes brasileiros foram encontrados. `country_scope` registra os clubes da partida e a elegibilidade de cada lado. Quando uma biblioteca extra não resolve uma textura válida, a passagem mantém a textura secundária; o log registra quais bibliotecas resolveram.

## Desativar

Com o jogo fechado, altere `enabled=0` no INI ou remova a linha `crowd_ultra_kits\crowd_ultra_kits.dll` do `mods/enabled.txt`. Reabra o jogo. O Lua original e os arquivos de modelos do FIFA não são reescritos.

## Estado

Protótipo experimental para teste do usuário. A versão 4 mantém a substituição de 96% e a mistura 88/8/3/1, trocando o catálogo fixo pela leitura do país no banco. A DLL foi compilada com `/W4 /WX`. A captura do serviço do modo atual e o comportamento visual desta versão precisam de confirmação na próxima abertura do jogo; a instalação não confirma essas etapas.

## Restrição brasileira da versão 4

A DLL consulta `nations.nationname` para identificar Brazil/Brasil e as regiões `Brasil ...` do mod. Em seguida relaciona `leagueteamlinks.teamid` → `leagues.leagueid` → `leagues.countryid`. Também considera `rowteamnationlinks` quando essa tabela estiver disponível. Países e clubes não têm IDs fixos no código, e a competição da partida não determina a nacionalidade. Acrescentar um clube com sua associação de país/liga no banco não exige recompilar a DLL.

Quando o serviço do modo atual está disponível, a leitura usa a API de consulta do banco em memória, com liberação dos resultados e sem conservar ponteiros de linhas/textos. O log mostra `source=loaded_database`. Antes de esse serviço existir, ou se a consulta falhar, a DLL lê `data/db/fifa_ng_db.db` e `fifa_ng_db-meta.xml` da pasta do executável. O log mostra `source=installed_database`. Esse caminho acompanha o banco instalado, mas não alterações ainda não salvas de uma carreira. Se ambas as leituras falharem, o log registra `unavailable_scope_original` e a torcida mantém o comportamento original.

O cadastro é atualizado no bind e antes da resolução dos assets da cena. Lua e C++ recebem o mesmo resultado; o desenho consulta apenas o cache. O leitor de T3DB usa os identificadores de tabela/campo e os limites dos inteiros definidos nos metadados e valida os limites das tabelas e dos registros. Não escreve no banco nem nos arquivos de kits/modelos.

A identidade de mandante e visitante é lida no registro nativo de equipes da partida com validação dos tipos e índices de lado. Se a identidade não estiver disponível, a rotina passa sem converter. Teste uma partida entre brasileiros, uma entre estrangeiros e uma com um clube de cada país. Em partida mista, somente o lado brasileiro deve receber a regra 96%/88–8–3–1. A integração e a confirmação visual dessas partidas permanecem pendentes.
