# Modelos de técnicos por identidade na carreira

A identidade 3D acompanha o vínculo ativo do mercado auxiliar. A troca vale para
**Ver clubes → Técnico** e para os técnicos mandante/visitante à beira do campo.

- Com modelo completo cadastrado: mostra o técnico atualmente contratado.
- Sem modelo, inclusive técnico do usuário: o perfil continua disponível sem
  personagem 3D; à beira do campo, o FIFA usa seu técnico genérico.
- Fora da carreira: permanece a lista fixa de modelos por clube do jogo/mod.
  Não se escreve em `specificmanager_<clube>` durante a simulação.

## Arquivos e instalação

O catálogo `ModCarrerMode/data/manager_market/manager_models.json` relaciona o
`coachId` estável ao `assetId` e aos SHA-256 dos quatro arquivos do personagem:

```
data/sceneassets/manager_market/<assetId>/
    model_0.rx3
    model_0_textures.rx3
    model_1.rx3
    model_1_textures.rx3
```

As duas variantes são fornecidas como conjunto. São cópias dos 20 técnicos
aprovados, com sua geometria e rig originais. Minifaces não são alteradas.
Os RX3 fazem parte da distribuição de assets, fora do Git. O código, catálogo,
exportador `generate_lineup.exe`, `club_browser.dll` e `sle.lua` devem acompanhar
esses assets. Reinicie o FIFA após atualizar a DLL ou o resolvedor Lua.

Para preparar novamente uma distribuição após revisar os modelos fixos:

```
python ModCarrerMode/source/club_environment/manager_market/prepare_model_assets.py --game "CAMINHO_DO_FIFA" --output "PASTA_VAZIA_FORA_DO_JOGO"
```

O comando somente prepara uma pasta de entrega; não altera o jogo de origem.
Extraia/copie suas pastas `data` e `ModCarrerMode` juntas na instalação de destino.
Um técnico sem modelo próprio não pode ser recuperado a partir de sua miniface.

## Seleção e isolamento

Depois do commit da simulação, o serviço do mercado publica
`runtime/manager_market/models_ready.tsv`. Somente vínculos ativos daquela
branch e data entram no mapa. PID, criação do processo, contexto, epoch, clube
controlado, calendário e o último evento nativo de leitura/escrita do save
identificam a publicação. Não há SQLite nem alteração de save no renderizador.

O perfil lê o mesmo vínculo validado, usa uma requisição `FFCOACH2` com clube
atual e asset separado, e cancela a preparação quando a revisão muda. A troca
ou ausência de personagem desativa o ator anterior e solicita um novo objeto,
mesmo quando os demais dados do perfil permanecem iguais.

`GetRMSle` redireciona somente os tipos SLC 10 e 11. O callback nativo lê o
contexto de carreira ao selecionar recursos. Um mapa ausente, incompleto ou
obsoleto em carreira confirmada usa o genérico, sem herdar a face anterior.
Um contexto fora da carreira retorna ao resolvedor original. Assistentes,
mascotes, fotógrafos, publicidade e props mantêm sua seleção existente.

A ponte usa a cadeia de frame já existente em `club_browser.dll`, sem outro
hook de renderização. Lua cria uma closure privada; sua função é publicada
somente depois de validar e registrar o callback. Não são modificadas closures
da biblioteca padrão. O módulo já permanece fixado no processo pelo carregador.
O ABI foi conferido com uma VM Lua 5.1 x64 compilada do código oficial:
[lstate.h](https://www.lua.org/source/5.1/lstate.h.html),
[lobject.h](https://www.lua.org/source/5.1/lobject.h.html),
[lstrlib.c](https://www.lua.org/source/5.1/lstrlib.c.html).

A escolha acontece ao carregar os recursos da próxima partida. Não se troca um
ator já desenhado no meio de uma partida. Na ausência de uma publicação atual,
o comportamento conservador na carreira é o técnico genérico.

## Verificação

Testes cobrem mudança de identidade no mesmo clube, técnico sem modelo,
contrato encerrado, vínculo de outra branch, arquivos ausentes/alterados,
save/data/epoch/PID divergentes, variantes de clima e modelo/textura,
delegação fora da carreira e preservação dos outros tipos SLC. A ponte numérica
foi executada numa VM Lua 5.1 real, incluindo coleta de lixo e biblioteca intacta.

Os 80 RX3 foram lidos estruturalmente e os 20 modelos exportados para outro
clube comparados aos respectivos modelos fixos: malha, pesos, rig e textura
iguais. A validação visual da nova seleção numa partida requer reiniciar o FIFA.
