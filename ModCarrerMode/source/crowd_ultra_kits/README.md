# Crowd Ultra Kits v1 — DLL experimental independente

Converte os registros visíveis da torcida em modelos ultra nativos, usando as malhas e materiais separados de corpo/camisa já registrados pelo FIFA 16. A configuração inicial substitui 96% dos registros visíveis; os outros 4% mantêm seus modelos originais. Entre os registros substituídos, a seleção tem como alvo kit 1 = 85%, kit 2 = 10%, kit 3 = 5%. Mandante e visitante mantêm seus próprios clubes.

Os índices de uniforme do FIFA são 0, 1 e **3**. O índice 2 é uniforme de goleiro. Se o kit secundário ou terceiro solicitado não existir, o resolver tem o primeiro uniforme como alternativa. Os percentuais representam solicitações de textura: um clube sem terceiro kit terá parte dessa parcela exibida com o primeiro uniforme.

## Implementação

- DLL própria, API `Fifa16ModGetApiVersion=1`, carregada pelo host existente.
- Intercepta somente quatro chamadas nativas validadas: criação de assets Crowd3D (`4397c47`), criação dos buffers de instâncias (`5cb9f03`), lote de camisas (`5cbc0a2`) e desenho das instâncias (`5cbc483`). Sem substituir outras DLLs.
- Cada registro de 23 bytes recebe somente a alteração de categoria/modelo: bit 19 e bits 20–21 da palavra no offset 12. O estado de assento, afiliação, posição, animação e demais bytes são preservados. Estado 2 é vazio e não recebe alteração.
- Conversão acontece antes da alocação nativa dos buffers por modelo. Promover personagens depois da alocação poderia ultrapassar seus buffers.
- Com a configuração atual, a categoria secundária recebe 15% das instâncias; o desenho de suas camisas é dividido em aproximadamente 66,7% kit 2 e 33,3% kit 3. Usa o início da instância que a rotina nativa já recebe. O corpo mantém uma única passagem. A textura original é restaurada após o desenho do terceiro kit.
- O recurso Lua é incorporado à DLL. Adiciona duas bibliotecas de textura para o terceiro kit e usa os modelos ultra já existentes, com seus LODs. As texturas são carregadas no bind; as consultas no desenho usam o catálogo nativo em memória.
- `homecrowdsize=6/awaycrowdsize=2` mantém disponíveis os quatro protótipos ultra. A DLL preserva os estados de assentos vazios e não escreve no multiplicador de público do mod de ocupação.
- A seleção dos grupos é determinística e os percentuais podem variar ligeiramente por arredondamento dos lotes/LODs e pela câmera. Ela não constitui contagem de pessoas visíveis em uma captura.
- Os quatro hooks são instalados juntos com as outras threads suspensas, validação de bytes e de endereços das chamadas. DLL fixada na sessão; desativar exige reiniciar o FIFA.

## Compilar e instalar

Execute `build.cmd` nesta pasta. `verify.cmd` verifica a preservação dos bits de assento/afiliação, repetibilidade da distribuição, desativação da conversão e divisão do terceiro uniforme.

Copie `build/crowd_ultra_kits.dll` e `crowd_ultra_kits.ini` para `ModCarrerMode/mods/crowd_ultra_kits/`. Adicione uma única linha a `ModCarrerMode/mods/enabled.txt`:

```
crowd_ultra_kits\crowd_ultra_kits.dll
```

Não substituir `crowd/crowd_plugin.dll`: esse plugin trata da ocupação e continua separado.

## Configuração e teste visual

Edite `ModCarrerMode/mods/crowd_ultra_kits/crowd_ultra_kits.ini` com o jogo fechado. `kit1_percent + kit2_percent + kit3_percent` deve somar 100. `replace_percent` controla quantos registros visíveis recebem a conversão. Configuração inválida usa os padrões 100/85/10/5.

Abra uma partida nova, de preferência com clubes que possuam três uniformes. Observe a arquibancada nas câmeras próximas e no replay. O teste visual precisa confirmar as camisas completas, ambos os clubes, posições sentadas/em pé, animações e LODs. Essa confirmação visual não é substituída pela compilação nem pela leitura dos registros.

O log `ModCarrerMode/logs/crowd_ultra_kits.log` distingue: `installed`, `crowd_asset_bind`, `instances_remapped` e `third_kit_draw`. Quando a biblioteca do terceiro uniforme não resolve uma textura válida, a passagem mantém a textura secundária; o log de terceiros não será emitido nessa situação.

## Desativar

Com o jogo fechado, altere `enabled=0` no INI ou remova a linha `crowd_ultra_kits\crowd_ultra_kits.dll` do `mods/enabled.txt`. Reabra o jogo. O Lua original e os arquivos de modelos do FIFA não são reescritos.

## Estado

Protótipo experimental para teste do usuário. Compilação e testes da política devem passar antes da instalação. A integração inicial é auditada pelos logs nativos; comportamento visual em partida permanece dependente do teste dentro do jogo.
